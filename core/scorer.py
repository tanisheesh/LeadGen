import asyncio
import aiohttp
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Groq API (Fast + Free!)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
AI_MODEL = "llama-3.3-70b-versatile"  # Fast + Free on Groq

# Fallback to OpenRouter if Groq fails
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


# ─────────────────────────────────────────────
# RULE-BASED SCORING
# ─────────────────────────────────────────────

def rule_based_score(lead: dict) -> dict:
    """
    Fast rule-based scoring. Returns score 1-10 + gap analysis.
    No website / Instagram-only → auto 9-10.
    Has website → score based on missing signals.
    """
    gaps = []
    score = 0

    no_website = lead.get('no_website', False)
    raw_url = lead.get('raw_url', '')
    website = lead.get('website', '')

    # ── Tier 1: No digital presence at all
    if no_website or (not website and not raw_url):
        return {
            'rule_score': 10,
            'rule_gaps': ['No website', 'No online booking', 'No WhatsApp integration',
                          'No SSL', 'No mobile optimization', 'No chatbot', 'No payment gateway'],
            'rule_tier': 'NO_WEBSITE',
            'ai_needed': False,  # Rule is enough — obvious lead
        }

    # ── Tier 2: Weak site (Instagram/Facebook only)
    weak_domains = ['instagram.com', 'facebook.com', 'sites.google.com', 'linktr.ee']
    if raw_url and any(d in raw_url for d in weak_domains):
        return {
            'rule_score': 9,
            'rule_gaps': ['Only social media page (no real website)', 'No booking system',
                          'No WhatsApp integration', 'No SSL'],
            'rule_tier': 'WEAK_SITE',
            'ai_needed': False,
        }

    # ── Tier 3: Has website — score by missing signals
    if not lead.get('has_ssl'):
        score += 2
        gaps.append('No SSL certificate')
    if not lead.get('has_mobile_viewport'):
        score += 2
        gaps.append('Not mobile optimized')
    if not lead.get('has_whatsapp'):
        score += 1.5
        gaps.append('No WhatsApp integration')
    if not lead.get('has_booking_form'):
        score += 1.5
        gaps.append('No online booking/scheduling')
    if not lead.get('has_chatbot'):
        score += 0.5
        gaps.append('No live chat / chatbot')
    if not lead.get('has_online_payment'):
        score += 0.5
        gaps.append('No online payment')
    if not lead.get('has_contact_form'):
        score += 0.5
        gaps.append('No contact form')
    if not lead.get('has_gallery'):
        score += 0.5
        gaps.append('No gallery/portfolio')
    if not lead.get('has_testimonials'):
        score += 0.5
        gaps.append('No testimonials/reviews section')

    # Copyright year penalty — old site
    cy = lead.get('copyright_year')
    if cy and cy < 2020:
        score += 1
        gaps.append(f'Website last updated {cy} (very outdated)')

    # Tech stack bonus info
    tech = lead.get('tech_stack_detected', [])
    if 'WordPress' in tech:
        gaps.append('WordPress site (easy to modernize)')

    # Clamp to 1-8 range (rule-based max 8, AI can push to 9-10)
    rule_score = min(8, max(1, round(score)))

    # Decide if AI needed
    ai_needed = rule_score >= 5  # Only send good candidates to AI

    return {
        'rule_score': rule_score,
        'rule_gaps': gaps,
        'rule_tier': 'HAS_WEBSITE',
        'ai_needed': ai_needed,
    }


# ─────────────────────────────────────────────
# AI SCORING
# ─────────────────────────────────────────────

AI_SYSTEM_PROMPT = """You are an expert digital marketing consultant specializing in helping Indian local businesses improve their online presence. You analyze business data and identify the most promising leads for web/digital services.

Respond ONLY with valid JSON. No markdown, no explanation outside JSON."""

def build_ai_prompt(lead: dict) -> str:
    signals = {
        'SSL': lead.get('has_ssl'),
        'Mobile Optimized': lead.get('has_mobile_viewport'),
        'WhatsApp Button': lead.get('has_whatsapp'),
        'Online Booking': lead.get('has_booking_form'),
        'Live Chat': lead.get('has_chatbot'),
        'Online Payment': lead.get('has_online_payment'),
        'Contact Form': lead.get('has_contact_form'),
        'Gallery/Portfolio': lead.get('has_gallery'),
        'Testimonials': lead.get('has_testimonials'),
        'Blog/Content': lead.get('has_blog'),
    }
    signal_str = '\n'.join([f"  {k}: {'✓' if v else '✗'}" for k, v in signals.items()])

    tech = ', '.join(lead.get('tech_stack_detected', [])) or 'Unknown'
    cy = lead.get('copyright_year', 'Unknown')

    return f"""Analyze this Indian local business as a potential digital services lead:

BUSINESS INFO:
  Name: {lead.get('company_name', 'N/A')}
  Type: {lead.get('business_type', 'N/A')}
  City: {lead.get('city', 'N/A')}
  Website: {lead.get('website') or lead.get('raw_url') or 'NONE'}
  Phone: {lead.get('phone', 'N/A')}
  Google Rating: {lead.get('google_rating', 'N/A')} ({lead.get('google_reviews', 0)} reviews)

WEBSITE SIGNALS:
{signal_str}
  Tech Stack: {tech}
  Copyright Year: {cy}

WEBSITE CONTENT PREVIEW:
  Title: {lead.get('page_title', '')[:100]}
  Description: {lead.get('meta_desc', '')[:150]}
  Content: {lead.get('page_snippet', '')[:300]}

PRE-ANALYSIS GAPS: {', '.join(lead.get('rule_gaps', []))}

Respond with JSON:
{{
  "lead_score": <integer 1-10>,
  "service_opportunity": "<primary service: Website/SEO/WhatsApp/Redesign/etc>",
  "gaps_found": "<2-3 sentence summary of digital gaps>",
  "reasoning": "<why this score — business potential + digital gap severity>",
  "recommended_pitch": "<1 sentence cold outreach hook in conversational Hindi-English>",
  "urgency": "<HIGH/MEDIUM/LOW — how urgently do they need help>",
  "estimated_deal_size": "<small/medium/large>"
}}"""


async def ai_score_lead(session: aiohttp.ClientSession, lead: dict, api_key: str, retries: int = 3) -> dict:
    """Call Groq AI to score a single lead (fast + free!)"""
    prompt = build_ai_prompt(lead)

    for attempt in range(retries):
        try:
            payload = {
                "model": AI_MODEL,
                "max_tokens": 400,
                "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Try Groq first (faster + free)
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            async with session.post(GROQ_URL, json=payload, headers=headers,
                                     timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 429:
                    wait = (attempt + 1) * 5
                    logger.warning(f"Rate limited, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                if resp.status != 200:
                    logger.error(f"Groq API error {resp.status}")
                    # Don't return empty, let it retry or fallback
                    if attempt < retries - 1:
                        await asyncio.sleep(2)
                        continue
                    return {}

                data = await resp.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                content = content.strip().replace('```json', '').replace('```', '').strip()
                return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"AI JSON parse error: {e}")
            return {}
        except Exception as e:
            logger.error(f"AI scoring error (attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                await asyncio.sleep(3)

    return {}


# ─────────────────────────────────────────────
# COMBINED SCORING PIPELINE
# ─────────────────────────────────────────────

async def score_lead(session: aiohttp.ClientSession, lead: dict, openrouter_key: str) -> dict:
    """Full scoring pipeline: rule-based → AI if needed"""

    # Step 1: Rule-based fast scoring
    rule_result = rule_based_score(lead)
    lead.update(rule_result)

    # Step 2: AI scoring for promising leads
    if rule_result.get('ai_needed') and openrouter_key:
        ai_result = await ai_score_lead(session, lead, openrouter_key)
        if ai_result:
            # AI score takes precedence, but we keep rule gaps too
            lead['lead_score'] = ai_result.get('lead_score', rule_result['rule_score'])
            lead['service_opportunity'] = ai_result.get('service_opportunity', '')
            lead['gaps_found'] = ai_result.get('gaps_found', '')
            lead['reasoning'] = ai_result.get('reasoning', '')
            lead['recommended_pitch'] = ai_result.get('recommended_pitch', '')
            lead['urgency'] = ai_result.get('urgency', 'MEDIUM')
            lead['estimated_deal_size'] = ai_result.get('estimated_deal_size', 'medium')
            lead['scored_by'] = 'AI'
        else:
            # AI failed — use rule score
            lead['lead_score'] = rule_result['rule_score']
            lead['service_opportunity'] = 'Digital Presence Upgrade'
            lead['gaps_found'] = ', '.join(rule_result['rule_gaps'][:3])
            lead['reasoning'] = f"Rule-based score: {rule_result['rule_score']}/10 based on {len(rule_result['rule_gaps'])} missing signals"
            lead['recommended_pitch'] = f"Aapke business ki digital presence mein improvements ki zaroorat hai — {', '.join(rule_result['rule_gaps'][:2])}"
            lead['urgency'] = 'MEDIUM'
            lead['estimated_deal_size'] = 'medium'
            lead['scored_by'] = 'RULE_FALLBACK'
    else:
        # No website / weak site → use rule score directly
        lead['lead_score'] = rule_result['rule_score']
        tier = rule_result.get('rule_tier', '')
        if tier == 'NO_WEBSITE':
            lead['service_opportunity'] = 'Website Development'
            lead['gaps_found'] = 'Business has no website — completely invisible online'
            lead['recommended_pitch'] = f"{lead.get('company_name', 'Aapka business')} ka koi website nahi hai — hum 7 din mein professional website bana sakte hain jo WhatsApp pe directly customers bheje."
            lead['urgency'] = 'HIGH'
            lead['estimated_deal_size'] = 'medium'
        elif tier == 'WEAK_SITE':
            lead['service_opportunity'] = 'Professional Website'
            lead['gaps_found'] = 'Only Instagram/Facebook page — no professional web presence'
            lead['recommended_pitch'] = f"Sirf Instagram se business chalana risky hai — ek professional website aapko Google pe visible karega."
            lead['urgency'] = 'HIGH'
            lead['estimated_deal_size'] = 'medium'
        lead['reasoning'] = f"Auto-scored {lead['lead_score']}/10: {tier}"
        lead['scored_by'] = 'RULE_AUTO'

    return lead

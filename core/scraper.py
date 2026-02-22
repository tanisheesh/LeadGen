import asyncio
import aiohttp
import re
from urllib.parse import urlparse
from typing import Optional
import logging

logger = logging.getLogger(__name__)

SKIP_DOMAINS = [
    'justdial.com', 'sulekha.com', 'indiamart.com', 'practo.com',
    'lybrate.com', 'urbanclap.com', 'google.com', 'facebook.com',
    'instagram.com', 'twitter.com', 'youtube.com', 'wikipedia.org',
    'quora.com', 'reddit.com', '99acres.com', 'magicbricks.com',
    'housing.com', 'yellowpages.in', 'tradeindia.com', 'linktr.ee',
    'linktree.com', 'sites.google.com', 'zomato.com', 'swiggy.com',
    'amazon.in', 'flipkart.com', 'naukri.com', 'linkedin.com',
    'olx.in', 'quikr.com', 'clickindia.com', 'vivastreet.co.in'
]

WEAK_DOMAINS = ['instagram.com', 'facebook.com', 'sites.google.com', 'linktr.ee', 'linktree.com']

# Industry-specific search modifiers for better targeting
LOCATION_MODIFIERS = {
    'Mumbai': ['Bandra', 'Andheri', 'Powai', 'Juhu', 'Colaba'],
    'Delhi': ['South Delhi', 'Connaught Place', 'Saket', 'Dwarka', 'Rohini'],
    'Bangalore': ['Koramangala', 'Indiranagar', 'Whitefield', 'HSR Layout', 'Jayanagar'],
    'Pune': ['Koregaon Park', 'Hinjewadi', 'Viman Nagar', 'Kothrud', 'Aundh'],
    'Hyderabad': ['Banjara Hills', 'Jubilee Hills', 'Gachibowli', 'Hitech City', 'Madhapur'],
    'Chennai': ['T Nagar', 'Anna Nagar', 'Velachery', 'Adyar', 'Nungambakkam'],
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-IN,en;q=0.9',
}


def extract_domain(url: str) -> str:
    if not url:
        return ''
    try:
        if not url.startswith('http'):
            url = 'https://' + url
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '').lower()
        return domain
    except Exception:
        return ''


def is_weak_site(url: str) -> bool:
    if not url:
        return True
    domain = extract_domain(url)
    return any(w in domain for w in WEAK_DOMAINS)


def is_directory_site(url: str) -> bool:
    domain = extract_domain(url)
    return any(s in domain for s in SKIP_DOMAINS)


async def fetch_serpapi_results(session: aiohttp.ClientSession, query: str, api_key: str, num_results: int = 20) -> list:
    """Fetch Google Maps results from SerpAPI"""
    params = {
        'engine': 'google_maps',
        'q': query,
        'type': 'search',
        'num': num_results,
        'api_key': api_key,
        'hl': 'en',
        'gl': 'in'
    }
    try:
        async with session.get('https://serpapi.com/search', params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return parse_serpapi_response(data, query)
            else:
                logger.error(f"SerpAPI error {resp.status} for query: {query}")
                return []
    except Exception as e:
        logger.error(f"SerpAPI fetch failed for '{query}': {e}")
        return []


def parse_serpapi_response(data: dict, query: str) -> list:
    """Parse SerpAPI response into lead dicts"""
    results = (
        data.get('local_results') or
        (data.get('local_results', {}) or {}).get('places', []) or
        data.get('places_results', []) or
        []
    )
    if isinstance(results, dict):
        results = results.get('places', [])

    city = ''
    business_type = query
    city_list = [
        'Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Hyderabad', 'Pune',
        'Ahmedabad', 'Jaipur', 'Surat', 'Lucknow', 'Indore', 'Bhopal',
        'Nagpur', 'Vadodara', 'Chandigarh', 'Kochi', 'Thane', 'Noida',
        'Gurgaon', 'Coimbatore', 'Ernakulam', 'Kolkata', 'Patna'
    ]
    for c in city_list:
        if c.lower() in query.lower():
            city = c
            business_type = re.sub(r'\bin\b', '', query.replace(c, ''), flags=re.IGNORECASE).strip()
            break

    leads = []
    seen = set()

    for place in results:
        name = (place.get('title') or place.get('name') or '').strip()
        if not name or len(name) < 3:
            continue

        name_key = re.sub(r'[^a-z0-9]', '', name.lower())
        if name_key in seen:
            continue
        seen.add(name_key)

        raw_url = place.get('website') or place.get('link') or ''
        website = ''
        if raw_url and not is_directory_site(raw_url):
            website = extract_domain(raw_url)

        phone = re.sub(r'[\s\-()]', '', place.get('phone') or '')

        leads.append({
            'company_name': name,
            'website': website,
            'raw_url': raw_url,
            'phone': phone,
            'email': '',
            'city': city,
            'country': 'India',
            'business_type': business_type,
            'contact_name': '',
            'address': place.get('address') or '',
            'google_rating': place.get('rating'),
            'google_reviews': place.get('reviews') or place.get('reviews_count') or 0,
            'source': 'GoogleMaps',
            'raw_snippet': place.get('type') or place.get('description') or '',
        })

    return leads


async def scrape_website(session: aiohttp.ClientSession, url: str) -> dict:
    """Scrape a website and extract signals"""
    if not url:
        return _empty_signals(no_website=True)

    if not url.startswith('http'):
        url = 'https://' + url

    if is_weak_site(url):
        return _empty_signals(no_website=True)

    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=12), allow_redirects=True, ssl=False) as resp:
            if resp.status >= 400:
                return _empty_signals(scrape_failed=True)

            html = await resp.text(errors='ignore')
            final_url = str(resp.url)
            return extract_signals(html, final_url)

    except asyncio.TimeoutError:
        return _empty_signals(scrape_failed=True, reason='timeout')
    except Exception as e:
        return _empty_signals(scrape_failed=True, reason=str(e)[:100])


def extract_signals(html: str, url: str) -> dict:
    """Extract digital presence signals from HTML"""
    html_lower = html.lower()

    # Basic meta
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    page_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()[:120] if title_match else ''

    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
    meta_desc = desc_match.group(1).strip()[:200] if desc_match else ''

    headings = re.findall(r'<h[1-3][^>]*>(.*?)</h[1-3]>', html, re.IGNORECASE | re.DOTALL)
    headings_text = ' | '.join([re.sub(r'<[^>]+>', '', h).strip() for h in headings[:5]])

    # Plain text snippet
    plain = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    plain = re.sub(r'<style[^>]*>.*?</style>', '', plain, flags=re.DOTALL | re.IGNORECASE)
    plain = re.sub(r'<[^>]+>', ' ', plain)
    plain = re.sub(r'\s+', ' ', plain).strip()[:600]

    # Signals
    has_ssl = url.startswith('https://')
    has_mobile_viewport = 'viewport' in html_lower and 'width=device-width' in html_lower
    has_whatsapp = any(x in html_lower for x in ['wa.me', 'api.whatsapp', 'whatsapp.com/send'])
    has_booking = any(x in html_lower for x in ['calendly', 'book now', 'book appointment', 'schedule', 'typeform', 'hubspot'])
    has_chatbot = any(x in html_lower for x in ['tawk.to', 'livechat', 'freshchat', 'intercom', 'crisp.chat', 'tidio'])
    has_payment = any(x in html_lower for x in ['razorpay', 'paytm', 'upi', 'phonepay', 'instamojo', 'cashfree'])

    # Copyright year
    copyright_match = re.search(r'©\s*(\d{4})', html)
    copyright_year = int(copyright_match.group(1)) if copyright_match else None

    # Tech stack
    tech_stack = []
    if 'wp-content' in html_lower or 'wordpress' in html_lower:
        tech_stack.append('WordPress')
    if 'shopify' in html_lower:
        tech_stack.append('Shopify')
    if 'wix.com' in html_lower:
        tech_stack.append('Wix')
    if 'squarespace' in html_lower:
        tech_stack.append('Squarespace')
    if 'webflow' in html_lower:
        tech_stack.append('Webflow')
    if 'react' in html_lower or 'next.js' in html_lower:
        tech_stack.append('React/Next')

    # Quality signals
    has_contact_form = any(x in html_lower for x in ['contact form', 'contact us', '<form', 'contact-form'])
    has_gallery = any(x in html_lower for x in ['gallery', 'portfolio', 'our work', 'projects'])
    has_testimonials = any(x in html_lower for x in ['testimonial', 'review', 'what our clients'])
    has_blog = any(x in html_lower for x in ['/blog', '/news', '/articles', 'blog post'])
    has_social_links = any(x in html_lower for x in ['instagram.com', 'facebook.com', 'twitter.com', 'linkedin.com'])

    return {
        'page_title': page_title,
        'meta_desc': meta_desc,
        'headings': headings_text,
        'page_snippet': plain,
        'has_ssl': has_ssl,
        'has_mobile_viewport': has_mobile_viewport,
        'has_whatsapp': has_whatsapp,
        'has_booking_form': has_booking,
        'has_chatbot': has_chatbot,
        'has_online_payment': has_payment,
        'has_contact_form': has_contact_form,
        'has_gallery': has_gallery,
        'has_testimonials': has_testimonials,
        'has_blog': has_blog,
        'has_social_links': has_social_links,
        'copyright_year': copyright_year,
        'tech_stack_detected': tech_stack,
        'no_website': False,
        'scrape_failed': False,
    }


def _empty_signals(no_website=False, scrape_failed=False, reason='') -> dict:
    return {
        'page_title': '', 'meta_desc': '', 'headings': '', 'page_snippet': '',
        'has_ssl': False, 'has_mobile_viewport': False, 'has_whatsapp': False,
        'has_booking_form': False, 'has_chatbot': False, 'has_online_payment': False,
        'has_contact_form': False, 'has_gallery': False, 'has_testimonials': False,
        'has_blog': False, 'has_social_links': False,
        'copyright_year': None, 'tech_stack_detected': [],
        'no_website': no_website, 'scrape_failed': scrape_failed,
        'scrape_error': reason,
    }

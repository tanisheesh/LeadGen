import asyncio
import aiohttp
import logging
from typing import Optional, Callable
from datetime import datetime

from core.scraper import fetch_serpapi_results, scrape_website
from core.scorer import score_lead
from core.sheets import get_sheets_client, save_leads_to_sheet, lookup_email_hunter

logger = logging.getLogger(__name__)

# Default search targets — mix of cities + business types
DEFAULT_QUERIES = [
    ("wedding planner", "Mumbai"),
    ("skin clinic", "Hyderabad"),
    ("dental clinic", "Pune"),
    ("fitness center", "Bangalore"),
    ("interior designer", "Delhi"),
    ("ca firm", "Chennai"),
    ("photography studio", "Jaipur"),
    ("event management", "Kochi"),
    ("restaurant", "Indore"),
    ("coaching institute", "Lucknow"),
]


async def run_pipeline(
    config: dict,
    queries: list[tuple[str, str]] = None,
    progress_callback: Optional[Callable] = None,
    min_score: int = 7,
    max_concurrent_scrapes: int = 5,
) -> dict:
    """
    Full lead generation pipeline.
    
    config keys:
        serpapi_key, openrouter_key, hunter_key,
        sheets_service_account_json, sheet_id
    
    queries: list of (business_type, city) tuples
    progress_callback: fn(stage, current, total, message)
    """

    results = {
        'total_scraped': 0,
        'total_scored': 0,
        'qualified_leads': [],
        'saved_to_sheet': 0,
        'skipped_duplicates': 0,
        'errors': [],
        'started_at': datetime.now().isoformat(),
        'finished_at': None,
    }

    if not queries:
        queries = DEFAULT_QUERIES

    def progress(stage, current, total, msg=''):
        if progress_callback:
            progress_callback(stage, current, total, msg)
        logger.info(f"[{stage}] {current}/{total} — {msg}")

    connector = aiohttp.TCPConnector(limit=10, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:

        # ─── STAGE 1: Search ───────────────────────────
        progress('search', 0, len(queries), 'Starting SerpAPI searches...')
        all_leads = []
        seen_names = set()

        for i, (biz_type, city) in enumerate(queries):
            query = f"{biz_type} in {city}"
            progress('search', i + 1, len(queries), f"Searching: {query}")
            leads = await fetch_serpapi_results(session, query, config['serpapi_key'])

            # Global dedup by name
            for lead in leads:
                key = lead['company_name'].lower().replace(' ', '')[:30]
                if key not in seen_names:
                    seen_names.add(key)
                    all_leads.append(lead)

            await asyncio.sleep(0.5)  # polite delay

        results['total_scraped'] = len(all_leads)
        progress('search', len(queries), len(queries), f"Found {len(all_leads)} unique leads")

        # ─── STAGE 2: Scrape websites ──────────────────
        progress('scrape', 0, len(all_leads), 'Scraping websites...')
        semaphore = asyncio.Semaphore(max_concurrent_scrapes)

        async def scrape_one(i, lead):
            async with semaphore:
                url = lead.get('raw_url') or lead.get('website') or ''
                signals = await scrape_website(session, url)
                lead.update(signals)
                progress('scrape', i + 1, len(all_leads), f"Scraped: {lead['company_name'][:40]}")
                return lead

        scrape_tasks = [scrape_one(i, lead) for i, lead in enumerate(all_leads)]
        all_leads = await asyncio.gather(*scrape_tasks)

        # ─── STAGE 3: Rule-based filter ────────────────
        progress('score', 0, len(all_leads), 'Rule-based pre-filtering...')
        from core.scorer import rule_based_score
        pre_filtered = []
        for lead in all_leads:
            rule = rule_based_score(lead)
            lead.update(rule)
            if rule['rule_score'] >= 4:  # Only send decent candidates to AI
                pre_filtered.append(lead)

        progress('score', 0, len(pre_filtered), f"Pre-filter: {len(pre_filtered)} candidates for AI scoring")

        # ─── STAGE 4: AI scoring ───────────────────────
        ai_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent AI calls

        async def score_one(i, lead):
            async with ai_semaphore:
                scored = await score_lead(session, lead, config.get('openrouter_key', ''))
                progress('score', i + 1, len(pre_filtered), f"Scored {lead['company_name'][:35]}: {scored.get('lead_score', '?')}/10")
                await asyncio.sleep(0.3)
                return scored

        score_tasks = [score_one(i, lead) for i, lead in enumerate(pre_filtered)]
        scored_leads = await asyncio.gather(*score_tasks)
        results['total_scored'] = len(scored_leads)

        # ─── STAGE 5: Filter qualified leads ──────────
        qualified = [l for l in scored_leads if l.get('lead_score', 0) >= min_score]
        # Sort by score desc, then by google reviews desc
        qualified.sort(key=lambda x: (x.get('lead_score', 0), x.get('google_reviews', 0)), reverse=True)

        progress('enrich', 0, len(qualified), f"Enriching {len(qualified)} qualified leads...")

        # ─── STAGE 6: Hunter.io email enrichment ──────
        async def enrich_one(i, lead):
            if config.get('hunter_key') and lead.get('website'):
                hunter_data = await lookup_email_hunter(session, lead['website'], config['hunter_key'])
                if hunter_data:
                    lead.update(hunter_data)
            progress('enrich', i + 1, len(qualified), f"Enriched: {lead['company_name'][:40]}")
            return lead

        enrich_tasks = [enrich_one(i, lead) for i, lead in enumerate(qualified)]
        qualified = await asyncio.gather(*enrich_tasks)
        results['qualified_leads'] = list(qualified)

        # ─── STAGE 7: Save to Google Sheets ───────────
        if config.get('sheets_service_account_json') and config.get('sheet_id'):
            progress('save', 0, 1, 'Saving to Google Sheets...')
            gc = get_sheets_client(config['sheets_service_account_json'])
            if gc:
                stats = save_leads_to_sheet(gc, config['sheet_id'], qualified)
                results['saved_to_sheet'] = stats['saved']
                results['skipped_duplicates'] = stats['skipped_dup']
                progress('save', 1, 1, f"Saved {stats['saved']} leads, skipped {stats['skipped_dup']} duplicates")
            else:
                results['errors'].append('Google Sheets auth failed')

    results['finished_at'] = datetime.now().isoformat()
    return results


# ─── Entry point for cron ─────────────────────
if __name__ == '__main__':
    import os
    import json

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    config = {
        'serpapi_key': os.environ.get('SERPAPI_KEY', ''),
        'openrouter_key': os.environ.get('OPENROUTER_KEY', ''),
        'hunter_key': os.environ.get('HUNTER_KEY', ''),
        'sheets_service_account_json': os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', ''),
        'sheet_id': os.environ.get('SHEET_ID', ''),
    }

    # Custom queries from env or use defaults
    queries_env = os.environ.get('SEARCH_QUERIES', '')
    queries = None
    if queries_env:
        try:
            queries = [tuple(q) for q in json.loads(queries_env)]
        except Exception:
            pass

    print("🚀 Starting Lead Gen Pipeline...")
    result = asyncio.run(run_pipeline(config, queries=queries))

    print(f"\n✅ Done!")
    print(f"   Scraped: {result['total_scraped']}")
    print(f"   Qualified: {len(result['qualified_leads'])}")
    print(f"   Saved to Sheet: {result['saved_to_sheet']}")
    print(f"   Skipped (dup): {result['skipped_duplicates']}")

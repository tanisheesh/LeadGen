#!/usr/bin/env python3
"""
Cron job for daily lead generation.
Schedule on Render: 0 6 * * * (6 AM IST daily)
"""

import asyncio
import os
import json
import logging
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline import run_pipeline
from config import get_config, validate_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# ── Rotating query schedule (different targets each day) ──
WEEKLY_SCHEDULE = {
    0: [  # Monday
        ("dental clinic", "Mumbai"), ("skin clinic", "Delhi"),
        ("physiotherapy", "Pune"), ("eye clinic", "Bangalore"),
        ("hair salon", "Chennai"),
    ],
    1: [  # Tuesday
        ("wedding planner", "Kochi"), ("wedding photographer", "Jaipur"),
        ("wedding venue", "Hyderabad"), ("bridal makeup", "Chandigarh"),
        ("event management", "Ahmedabad"),
    ],
    2: [  # Wednesday
        ("gym", "Mumbai"), ("yoga studio", "Delhi"),
        ("fitness center", "Lucknow"), ("crossfit", "Indore"),
        ("personal trainer", "Surat"),
    ],
    3: [  # Thursday
        ("ca firm", "Mumbai"), ("chartered accountant", "Delhi"),
        ("tax consultant", "Bangalore"), ("legal services", "Chennai"),
        ("financial advisor", "Hyderabad"),
    ],
    4: [  # Friday
        ("interior designer", "Mumbai"), ("architect", "Delhi"),
        ("renovation contractor", "Bangalore"), ("vastu consultant", "Jaipur"),
        ("modular kitchen", "Pune"),
    ],
    5: [  # Saturday
        ("coaching institute", "Lucknow"), ("ias coaching", "Delhi"),
        ("neet coaching", "Chennai"), ("jee coaching", "Kota"),
        ("spoken english", "Patna"),
    ],
    6: [  # Sunday
        ("restaurant", "Kochi"), ("cafe", "Bangalore"),
        ("bakery", "Mumbai"), ("catering services", "Delhi"),
        ("cloud kitchen", "Hyderabad"),
    ],
}


async def main():
    start = datetime.now()
    day_of_week = start.weekday()
    queries = WEEKLY_SCHEDULE.get(day_of_week, WEEKLY_SCHEDULE[0])

    logger.info(f"=== CRON RUN STARTED ===")
    logger.info(f"Day: {start.strftime('%A %Y-%m-%d %H:%M')}")
    logger.info(f"Queries: {queries}")

    # Load config from .env or environment
    config = get_config()

    # Validate
    errors = validate_config(config, require_sheets=True)
    if errors:
        logger.error("Configuration errors:")
        for err in errors:
            logger.error(f"  - {err}")
        sys.exit(1)

    def progress(stage, current, total, message):
        logger.info(f"[{stage.upper()}] {current}/{total} — {message}")

    try:
        result = await run_pipeline(
            config,
            queries=queries,
            progress_callback=progress,
            min_score=config['min_score'],
            max_concurrent_scrapes=config['max_concurrent_scrapes'],
        )

        elapsed = (datetime.now() - start).seconds
        logger.info(f"=== CRON RUN COMPLETE ===")
        logger.info(f"Time taken: {elapsed}s")
        logger.info(f"Scraped: {result['total_scraped']}")
        logger.info(f"Qualified: {len(result['qualified_leads'])}")
        logger.info(f"Saved to Sheet: {result['saved_to_sheet']}")
        logger.info(f"Skipped (dup): {result['skipped_duplicates']}")
        logger.info(f"Errors: {len(result['errors'])}")

        if result['errors']:
            for err in result['errors']:
                logger.warning(f"Error: {err}")

        # Print top 5 leads
        leads = result['qualified_leads'][:5]
        if leads:
            logger.info("=== TOP LEADS ===")
            for l in leads:
                logger.info(f"  [{l.get('lead_score')}/10] {l.get('company_name')} | {l.get('city')} | {l.get('service_opportunity')}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

"""パイプライン CLI実行制御

使用例:
  python -m app.pipeline.runner --pipeline all --session 213
  python -m app.pipeline.runner --pipeline members --session 213
  python -m app.pipeline.runner --pipeline speeches --session 213
  python -m app.pipeline.runner --pipeline bills --session 213
  python -m app.pipeline.runner --pipeline votes --session 213
  python -m app.pipeline.runner --pipeline scoring --session 213
"""

import argparse
import logging
import sys

from app.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_members(db, session_number: int):
    from app.pipeline.kokkai_api import fetch_speeches

    logger.info(f"=== Fetching member data from speeches (session {session_number}) ===")
    count = fetch_speeches(db, session_number)
    logger.info(f"Processed {count} speech records (members extracted)")


def run_speeches(db, session_number: int):
    from app.pipeline.kokkai_api import fetch_speeches, get_last_run

    resume_from = get_last_run(db, session_number)
    if resume_from:
        logger.info(f"Resuming from record {resume_from}")
    logger.info(f"=== Fetching speeches (session {session_number}) ===")
    count = fetch_speeches(db, session_number, resume_from=resume_from)
    logger.info(f"Processed {count} speeches")


def run_bills(db, session_number: int):
    from app.pipeline.shugiin_scraper import scrape_bills_list

    logger.info(f"=== Scraping bills list from Shugiin (session {session_number}) ===")
    count = scrape_bills_list(db, session_number)
    logger.info(f"Scraped {count} bills")


def run_votes(db, session_number: int):
    from app.pipeline.sangiin_scraper import scrape_votes

    logger.info(f"=== Scraping Sangiin votes (session {session_number}) ===")
    count = scrape_votes(db, session_number)
    logger.info(f"Scraped {count} vote records")


def run_shugiin(db, session_number: int):
    from app.pipeline.shugiin_scraper import scrape_bills

    logger.info(f"=== Scraping Shugiin bills (session {session_number}) ===")
    count = scrape_bills(db, session_number)
    logger.info(f"Scraped {count} bill details")


def run_scoring(db, session_number: int):
    from app.services.scoring import compute_scores_for_session

    logger.info(f"=== Computing scores (session {session_number}) ===")
    count = compute_scores_for_session(db, session_number)
    logger.info(f"Computed scores for {count} members")


def run_smartnews(db, session_number: int):
    from app.pipeline.smartnews_loader import load_bills_csv

    logger.info("=== Loading bills from SmartNews CSV ===")
    count = load_bills_csv(db)
    logger.info(f"Loaded {count} bills from CSV")


def run_profiles(db, session_number: int):
    from app.pipeline.member_profile_scraper import scrape_member_profiles

    logger.info("=== Scraping member profiles (district, reading) ===")
    count = scrape_member_profiles(db)
    logger.info(f"Updated {count} member profiles")


def run_all(db, session_number: int):
    """全パイプラインを順番に実行する。"""
    logger.info(f"=== Running ALL pipelines for session {session_number} ===")
    run_bills(db, session_number)
    run_speeches(db, session_number)
    run_votes(db, session_number)
    run_shugiin(db, session_number)
    run_scoring(db, session_number)
    logger.info("=== All pipelines completed ===")


PIPELINES = {
    "all": run_all,
    "members": run_members,
    "speeches": run_speeches,
    "bills": run_bills,
    "votes": run_votes,
    "shugiin": run_shugiin,
    "scoring": run_scoring,
    "smartnews": run_smartnews,
    "profiles": run_profiles,
}


def main():
    parser = argparse.ArgumentParser(description="GiinScore Data Pipeline Runner")
    parser.add_argument(
        "--pipeline",
        choices=list(PIPELINES.keys()),
        required=True,
        help="Pipeline to run",
    )
    parser.add_argument(
        "--session",
        type=int,
        default=213,
        help="Diet session number (default: 213)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        pipeline_func = PIPELINES[args.pipeline]
        pipeline_func(db, session_number=args.session)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

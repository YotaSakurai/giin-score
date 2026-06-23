"""パイプライン CLI実行制御

使用例:
  python -m app.pipeline.runner --pipeline all --session 213
  python -m app.pipeline.runner --pipeline speeches --session 213
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

# ---------------------------------------------------------------------------
# 定期実行パイプライン（この順序で実行される）
# 新しいパイプラインを定期実行に追加するには、ここに1行追加するだけ
# ※ scoring は収集データに依存するため末尾に配置すること
# ---------------------------------------------------------------------------
SCHEDULED_PIPELINES: list[str] = [
    "bills",
    "speeches",
    "votes",
    "shugiin",
    "written_questions",
    "profiles",
    "speech_quality",
    "scoring",
    "analyze",
]


# ---------------------------------------------------------------------------
# 個別パイプライン関数
# ---------------------------------------------------------------------------
def run_members(db, session_number: int):
    from app.pipeline.kokkai_api import fetch_speeches

    logger.info(f"=== Fetching member data from speeches (session {session_number}) ===")
    count = fetch_speeches(db, session_number)
    logger.info(f"Processed {count} speech records (members extracted)")
    return count


def run_speeches(db, session_number: int):
    from app.pipeline.kokkai_api import fetch_speeches, get_last_run

    resume_from = get_last_run(db, session_number)
    if resume_from:
        logger.info(f"Resuming from record {resume_from}")
    logger.info(f"=== Fetching speeches (session {session_number}) ===")
    count = fetch_speeches(db, session_number, resume_from=resume_from)
    logger.info(f"Processed {count} speeches")
    return count


def run_bills(db, session_number: int):
    from app.pipeline.shugiin_scraper import scrape_bills_list

    logger.info(f"=== Scraping bills list from Shugiin (session {session_number}) ===")
    count = scrape_bills_list(db, session_number)
    logger.info(f"Scraped {count} bills")
    return count


def run_votes(db, session_number: int):
    from app.pipeline.sangiin_scraper import scrape_votes

    logger.info(f"=== Scraping Sangiin votes (session {session_number}) ===")
    count = scrape_votes(db, session_number)
    logger.info(f"Scraped {count} vote records")
    return count


def run_shugiin(db, session_number: int):
    from app.pipeline.shugiin_scraper import scrape_bills

    logger.info(f"=== Scraping Shugiin bills (session {session_number}) ===")
    count = scrape_bills(db, session_number)
    logger.info(f"Scraped {count} bill details")
    return count


def run_scoring(db, session_number: int):
    from app.services.scoring import compute_scores_for_session

    logger.info(f"=== Computing scores (session {session_number}) ===")
    count = compute_scores_for_session(db, session_number)
    logger.info(f"Computed scores for {count} members")
    return count


def run_smartnews(db, session_number: int):
    from app.pipeline.smartnews_loader import load_bills_csv

    logger.info("=== Loading bills from SmartNews CSV ===")
    count = load_bills_csv(db)
    logger.info(f"Loaded {count} bills from CSV")
    return count


def run_profiles(db, session_number: int):
    from app.pipeline.member_profile_scraper import scrape_member_profiles

    logger.info("=== Scraping member profiles (district, reading) ===")
    count = scrape_member_profiles(db)
    logger.info(f"Updated {count} member profiles")
    return count


def run_written_questions(db, session_number: int):
    from app.pipeline.shitsumon_scraper import scrape_written_questions

    logger.info(
        f"=== Scraping written questions (session {session_number}) ==="
    )
    count = scrape_written_questions(db, session_number)
    logger.info(f"Scraped {count} written questions")
    return count


def run_speech_quality(db, session_number: int):
    from app.pipeline.speech_quality import analyze_speeches_for_session

    logger.info(f"=== Analyzing speech quality (session {session_number}) ===")
    count = analyze_speeches_for_session(db, session_number)
    logger.info(f"Analyzed {count} speeches")
    return count


def run_sleeping(db, session_number: int):
    from app.pipeline.sleeping_detector import detect_sleeping_for_session

    logger.info(f"=== Detecting sleeping in videos (session {session_number}) ===")
    count = detect_sleeping_for_session(db, session_number)
    logger.info(f"Detected {count} sleeping candidates")
    return count


def run_analyze(db, session_number: int):
    from app.pipeline.analyze import analyze_data_quality

    logger.info(f"=== Running data quality analysis (session {session_number}) ===")
    count = analyze_data_quality(db, session_number)
    logger.info(f"Analysis complete (reports sent: {count})")
    return count


def run_all(db, session_number: int):
    """SCHEDULED_PIPELINES に登録された全パイプラインを順番に実行する。"""
    import time

    from app.pipeline.notify import (
        notify_batch_complete,
        notify_batch_start,
        notify_pipeline_failure,
        notify_pipeline_success,
    )

    logger.info(f"=== Running ALL scheduled pipelines for session {session_number} ===")
    notify_batch_start(session_number, SCHEDULED_PIPELINES)

    results: list[dict] = []
    batch_start = time.monotonic()

    for name in SCHEDULED_PIPELINES:
        logger.info(f"--- Starting pipeline: {name} ---")
        t0 = time.monotonic()
        try:
            count = PIPELINES[name](db, session_number)
            elapsed = time.monotonic() - t0
            records = count if isinstance(count, int) else 0
            results.append({"name": name, "status": "ok", "records": records, "elapsed": elapsed})
            notify_pipeline_success(name, records, elapsed)
        except Exception as e:
            elapsed = time.monotonic() - t0
            results.append(
                {"name": name, "status": "error", "records": 0, "error": str(e), "elapsed": elapsed}
            )
            notify_pipeline_failure(name, str(e), elapsed)
            logger.error(f"Pipeline {name} failed: {e}", exc_info=True)

    total_elapsed = time.monotonic() - batch_start
    notify_batch_complete(session_number, results, total_elapsed)
    logger.info("=== All scheduled pipelines completed ===")


# CLI から個別実行できるパイプライン一覧
PIPELINES: dict[str, object] = {
    "all": run_all,
    "members": run_members,
    "speeches": run_speeches,
    "bills": run_bills,
    "votes": run_votes,
    "shugiin": run_shugiin,
    "scoring": run_scoring,
    "smartnews": run_smartnews,
    "profiles": run_profiles,
    "written_questions": run_written_questions,
    "speech_quality": run_speech_quality,
    "sleeping": run_sleeping,
    "analyze": run_analyze,
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
        default=221,
        help="Diet session number (default: 221)",
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

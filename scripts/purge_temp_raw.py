"""
DataShuddi -- 24-Hour Temporary Raw Files Auto-Purge Script.

Purges unmasked temporary raw document files older than 24 hours from data/temp/
to ensure data retention compliance (GDPR & EU AI Act).
"""
import time

import click
from loguru import logger

from src.utils.config import settings

RETENTION_SECONDS: float = 24 * 3600  # 24 hours


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="List files eligible for purging without deleting them.",
)
def purge_temp_files(dry_run: bool) -> None:
    """Purge temporary raw files older than 24 hours."""
    temp_dir = settings.raw_data_dir.parent / "temp"
    if not temp_dir.exists():
        logger.info("Temp directory {} does not exist. Nothing to purge.", temp_dir)
        return

    now = time.time()
    purged_count = 0

    for file_path in temp_dir.iterdir():
        if file_path.is_file() and file_path.name != ".gitkeep":
            mtime = file_path.stat().st_mtime
            age = now - mtime

            if age > RETENTION_SECONDS:
                if dry_run:
                    logger.info("[DRY RUN] Would purge expired temp file: {} (age: {:.1f}h)", file_path.name, age / 3600)
                else:
                    file_path.unlink()
                    logger.info("Purged expired temp file: {} (age: {:.1f}h)", file_path.name, age / 3600)
                    purged_count += 1

    logger.info("Purge complete. Total files deleted: {}", purged_count)


if __name__ == "__main__":
    purge_temp_files()

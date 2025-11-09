#!/usr/bin/env python3
"""
Quick script to run the review ingestion command.
Usage: python scripts/ingest_mock_reviews.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.cli_commands.main import cli

if __name__ == "__main__":
    # Run the ingest command
    sys.argv = ["needleai", "reviews", "ingest-mock"]
    cli()


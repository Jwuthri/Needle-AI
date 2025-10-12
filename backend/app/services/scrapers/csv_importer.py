"""
CSV file importer for custom data.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import aiofiles

from app.exceptions import ValidationError
from app.utils.logging import get_logger

from .base import BaseReviewScraper, ScrapedReview

logger = get_logger("csv_importer")


class CSVImporter(BaseReviewScraper):
    """
    CSV file importer for user-uploaded review data.
    
    Expected CSV format:
    - content (required): Review text
    - author (optional): Author name
    - url (optional): Source URL
    - date (optional): Review date (ISO format or common formats)
    - sentiment (optional): Sentiment score
    
    Additional columns are stored in metadata.
    """

    def __init__(self, settings: Any):
        super().__init__(settings)
        self.cost_per_review = settings.csv_review_cost  # Usually free

    async def scrape(
        self,
        file_path: str,
        limit: int = None,
        **kwargs
    ) -> List[ScrapedReview]:
        """
        Import reviews from CSV file.
        
        Args:
            file_path: Path to CSV file
            limit: Maximum number of reviews to import (None = all)
            **kwargs: Additional parameters (encoding, delimiter)
            
        Returns:
            List of imported reviews
        """
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(f"File not found: {file_path}")

        if path.suffix.lower() not in ['.csv', '.txt']:
            raise ValidationError(f"Invalid file type. Expected CSV, got: {path.suffix}")

        encoding = kwargs.get('encoding', 'utf-8')
        delimiter = kwargs.get('delimiter', ',')

        try:
            reviews = []
            row_count = 0

            async with aiofiles.open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = await f.read()
                
            # Parse CSV
            reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
            
            # Validate required columns
            if not reader.fieldnames:
                raise ValidationError("Empty CSV file")

            if 'content' not in reader.fieldnames:
                raise ValidationError(
                    "CSV must have a 'content' column. "
                    f"Found columns: {', '.join(reader.fieldnames)}"
                )

            for row in reader:
                row_count += 1
                
                # Skip empty rows
                if not row.get('content', '').strip():
                    continue

                try:
                    review = self._parse_row(row, reader.fieldnames)
                    if review:
                        reviews.append(review)
                        
                        # Check limit
                        if limit and len(reviews) >= limit:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error parsing row {row_count}: {e}")
                    continue

            logger.info(f"Imported {len(reviews)} reviews from CSV (processed {row_count} rows)")
            return reviews

        except csv.Error as e:
            logger.error(f"CSV parsing error: {e}")
            raise ValidationError(f"Invalid CSV format: {e}")
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error: {e}")
            raise ValidationError(
                f"File encoding error. Try specifying encoding parameter (e.g., 'utf-8', 'latin-1')"
            )
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            raise ValidationError(f"Failed to import CSV: {e}")

    def _parse_row(self, row: Dict[str, str], fieldnames: List[str]) -> ScrapedReview:
        """Parse CSV row into ScrapedReview."""
        content = row.get('content', '').strip()
        if not content:
            return None

        # Parse optional fields
        author = row.get('author', '').strip() or None
        url = row.get('url', '').strip() or None
        
        # Parse date
        date_str = row.get('date', '').strip()
        review_date = self._parse_date(date_str) if date_str else None

        # Collect additional columns as metadata
        metadata = {}
        standard_columns = {'content', 'author', 'url', 'date'}
        
        for field in fieldnames:
            if field not in standard_columns and row.get(field):
                metadata[field] = row[field]

        return ScrapedReview(
            content=self.clean_content(content),
            author=author,
            url=url,
            review_date=review_date,
            metadata=metadata
        )

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime (supports multiple formats)."""
        if not date_str:
            return None

        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%m/%d/%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            pass

        logger.warning(f"Could not parse date: {date_str}")
        return None

    async def estimate_cost(self, limit: int) -> float:
        """Estimate cost for CSV import (usually free)."""
        return limit * self.cost_per_review

    def get_source_name(self) -> str:
        """Get source name."""
        return "CSV Import"

    async def validate_query(self, query: str) -> bool:
        """Validate file path."""
        path = Path(query)
        return path.exists() and path.suffix.lower() in ['.csv', '.txt']


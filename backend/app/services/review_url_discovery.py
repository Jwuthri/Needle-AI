"""
Service for discovering review URLs using DuckDuckGo search.

Automatically finds G2, Trustpilot, and TrustRadius review pages for a company.
"""

import re
from typing import Dict, Optional

import httpx

from app.utils.logging import get_logger

logger = get_logger("review_url_discovery")

# DuckDuckGo HTML search URL
DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"

# Patterns to extract review URLs from search results
URL_PATTERNS = {
    "g2": r'https?://(?:www\.)?g2\.com/products/([^/\s"\']+)(?:/reviews)?',
    "trustpilot": r'https?://(?:www\.)?trustpilot\.com/review/([^/\s"\']+)',
    "trustradius": r'https?://(?:www\.)?trustradius\.com/products/([^/\s"\']+)(?:/reviews)?',
}


async def search_duckduckgo(query: str) -> str:
    """
    Search DuckDuckGo and return HTML results.
    
    Args:
        query: Search query
        
    Returns:
        HTML content of search results
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            DUCKDUCKGO_URL,
            data={"q": query, "b": ""},
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        response.raise_for_status()
        return response.text


def extract_url(html: str, platform: str) -> Optional[str]:
    """
    Extract review URL for a specific platform from HTML.
    
    Args:
        html: HTML content to search
        platform: Platform name (g2, trustpilot, trustradius)
        
    Returns:
        Review URL if found, None otherwise
    """
    pattern = URL_PATTERNS.get(platform)
    if not pattern:
        return None
    
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        full_url = match.group(0)
        # Normalize URLs
        if platform == "g2":
            # Ensure it ends with /reviews
            if not full_url.endswith("/reviews"):
                full_url = full_url.rstrip("/") + "/reviews"
        elif platform == "trustradius":
            if not full_url.endswith("/reviews"):
                full_url = full_url.rstrip("/") + "/reviews"
        return full_url
    return None


async def discover_review_urls(company_name: str) -> Dict[str, Optional[str]]:
    """
    Discover review URLs for a company across multiple platforms.
    
    Searches DuckDuckGo for:
    - "{company_name}" g2 reviews
    - "{company_name}" trustpilot reviews
    - "{company_name}" trustradius reviews
    
    Args:
        company_name: Company/product name to search for
        
    Returns:
        Dict with platform names as keys and URLs (or None) as values
    """
    results = {
        "g2": None,
        "trustpilot": None,
        "trustradius": None,
    }
    
    search_queries = {
        "g2": f'"{company_name}" g2 reviews site:g2.com',
        "trustpilot": f'"{company_name}" trustpilot reviews site:trustpilot.com',
        "trustradius": f'"{company_name}" trustradius reviews site:trustradius.com',
    }
    
    for platform, query in search_queries.items():
        try:
            logger.debug(f"Searching for {platform} URL: {query}")
            html = await search_duckduckgo(query)
            url = extract_url(html, platform)
            
            if url:
                results[platform] = url
                logger.info(f"Found {platform} URL for {company_name}: {url}")
            else:
                logger.debug(f"No {platform} URL found for {company_name}")
                
        except Exception as e:
            logger.warning(f"Error searching {platform} for {company_name}: {e}")
            continue
    
    return results


async def discover_single_url(company_name: str, platform: str) -> Optional[str]:
    """
    Discover review URL for a specific platform.
    
    Args:
        company_name: Company/product name
        platform: Platform name (g2, trustpilot, trustradius)
        
    Returns:
        Review URL if found, None otherwise
    """
    if platform not in URL_PATTERNS:
        logger.warning(f"Unknown platform: {platform}")
        return None
    
    query = f'"{company_name}" {platform} reviews site:{platform}.com'
    
    try:
        html = await search_duckduckgo(query)
        return extract_url(html, platform)
    except Exception as e:
        logger.warning(f"Error searching {platform} for {company_name}: {e}")
        return None


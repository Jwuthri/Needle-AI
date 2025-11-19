# Real Review Scraping Implementation

This document describes the implementation of real review scraping from Twitter/X, Reddit, G2, and Trustpilot using Apify.

## Overview

The system now supports scraping authentic reviews from four major platforms:
- **Twitter/X**: Social media sentiment and mentions
- **Reddit**: Community discussions and opinions
- **G2**: B2B software reviews with detailed ratings
- **Trustpilot**: Customer reviews with star ratings

All scrapers use Apify actors for reliable, scalable data collection.

## Architecture

### Backend Components

1. **Scrapers** (`backend/app/services/scrapers/`)
   - `twitter_scraper.py`: Twitter/X scraper using Apify
   - `reddit_scraper.py`: Reddit scraper using Apify
   - `g2_scraper.py`: G2 scraper using Apify (NEW)
   - `trustpilot_scraper.py`: Trustpilot scraper using Apify (NEW)
   - `base.py`: Base scraper interface

2. **Database Models**
   - `SourceTypeEnum`: Extended with `G2` and `TRUSTPILOT` types
   - `ReviewSource`: Stores scraper configurations
   - Migration `018`: Adds new enum values

3. **Configuration** (`backend/app/core/config/settings.py`)
   ```python
   # Apify Actor IDs
   apify_reddit_actor_id: str = "trudax/reddit-scraper"
   apify_twitter_actor_id: str = "apidojo/tweet-scraper"
   apify_g2_actor_id: str = "epctex/g2-scraper"
   apify_trustpilot_actor_id: str = "compass/trustpilot-scraper"
   
   # Costs per review
   reddit_review_cost: float = 0.01
   twitter_review_cost: float = 0.01
   g2_review_cost: float = 0.02
   trustpilot_review_cost: float = 0.015
   ```

4. **API Endpoints** (`backend/app/api/v1/scraping.py`)
   - `GET /api/v1/scraping/sources`: Lists sources grouped by real/fake
   - `POST /api/v1/scraping/jobs`: Creates scraping job
   - Automatically routes to real scraper or fake generator

### Frontend Components

1. **Data Sources Page** (`frontend/src/app/data-sources/page.tsx`)
   - Separate sections for real and fake sources
   - Real sources displayed in 4-column grid
   - Fake sources for testing/demos
   - CSV upload for custom data

## Setup Instructions

### 1. Get Apify API Token

1. Sign up at [Apify Console](https://console.apify.com/)
2. Navigate to Settings → Integrations
3. Copy your API token

### 2. Configure Environment

Add to your `.env` file:

```bash
# Apify Configuration
APIFY_API_TOKEN=your_apify_token_here

# Actor IDs (defaults provided, can be customized)
APIFY_REDDIT_ACTOR_ID=trudax/reddit-scraper
APIFY_TWITTER_ACTOR_ID=apidojo/tweet-scraper
APIFY_G2_ACTOR_ID=epctex/g2-scraper
APIFY_TRUSTPILOT_ACTOR_ID=compass/trustpilot-scraper

# Costs (in credits per review)
REDDIT_REVIEW_COST=0.01
TWITTER_REVIEW_COST=0.01
G2_REVIEW_COST=0.02
TRUSTPILOT_REVIEW_COST=0.015
```

### 3. Run Database Migration

```bash
cd backend
alembic upgrade head
```

### 4. Seed Review Sources

Run the seed script to populate the database with source configurations:

```bash
cd backend
python scripts/seed_real_sources.py
```

This creates:
- Reddit scraping source
- Twitter/X scraping source
- G2 scraping source
- Trustpilot scraping source

Optionally, seed fake sources for testing:

```bash
python scripts/seed_fake_sources.py
```

### 5. Restart Services

```bash
# Backend
cd backend
./scripts/start.sh

# Frontend
cd frontend
npm run dev
```

## Usage

### From the UI

1. Navigate to **Data Sources** page
2. Select a company
3. Choose a source from:
   - **Real Review Scraping**: Twitter, Reddit, G2, Trustpilot
   - **AI-Generated Reviews**: For testing
4. Configure job:
   - Enter number of reviews OR maximum cost
   - Review estimate
5. Start job

### From the API

```bash
# List available sources
curl http://localhost:8000/api/v1/scraping/sources

# Start scraping job
curl -X POST http://localhost:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "company_id": "comp_123",
    "source_id": "source_reddit",
    "review_count": 50
  }'
```

## Apify Actors

### Recommended Actors

1. **Reddit**: [trudax/reddit-scraper](https://apify.com/trudax/reddit-scraper)
   - Scrapes posts and comments
   - Supports search queries and subreddits
   - Returns metadata (score, subreddit, etc.)

2. **Twitter/X**: [apidojo/tweet-scraper](https://apify.com/apidojo/tweet-scraper)
   - Scrapes tweets and replies
   - Supports search terms and hashtags
   - Returns engagement metrics

3. **G2**: [epctex/g2-scraper](https://apify.com/epctex/g2-scraper)
   - Scrapes product reviews
   - Includes ratings, pros, cons
   - Company and user metadata

4. **Trustpilot**: [compass/trustpilot-scraper](https://apify.com/compass/trustpilot-scraper)
   - Scrapes customer reviews
   - Star ratings and verification status
   - Company replies included

### Custom Actors

You can use different actors by updating the environment variables:

```bash
APIFY_REDDIT_ACTOR_ID=your-username/your-actor
```

## Cost Structure

### Apify Costs

Apify charges based on compute units (CU). Typical costs:
- Reddit: ~0.01-0.02 CU per 100 items
- Twitter: ~0.01-0.02 CU per 100 items
- G2: ~0.02-0.03 CU per 100 items
- Trustpilot: ~0.015-0.025 CU per 100 items

### Platform Credits

Our platform charges users in credits:
- 1 credit = $0.01
- Reddit: 0.01 credits/review
- Twitter: 0.01 credits/review
- G2: 0.02 credits/review
- Trustpilot: 0.015 credits/review

## Data Flow

1. **User initiates scraping job**
   - Selects source and company
   - Specifies review count or max cost
   - System checks credit balance

2. **Job creation**
   - Creates `ScrapingJob` record
   - Deducts credits from user account
   - Queues Celery task

3. **Scraping execution**
   - Celery worker picks up task
   - Scraper calls Apify API
   - Polls for completion (max 5 minutes)
   - Retrieves results

4. **Data processing**
   - Parses reviews into standard format
   - Stores in `Review` table
   - Links to company and source
   - Generates embeddings (async)

5. **Job completion**
   - Updates job status
   - Records actual review count
   - Refunds unused credits (if applicable)

## Error Handling

### Common Issues

1. **Apify API token not configured**
   - Error: "Apify API token not configured"
   - Solution: Add `APIFY_API_TOKEN` to `.env`

2. **Actor run timeout**
   - Error: "Apify actor run timeout"
   - Solution: Increase timeout or reduce review count

3. **Insufficient credits**
   - Error: "Insufficient credits"
   - Solution: Purchase more credits via Stripe

4. **Invalid query**
   - Error: "Invalid query"
   - Solution: Check query format (URL for G2/Trustpilot, keywords for Reddit/Twitter)

### Retry Logic

- Network errors: Automatic retry with exponential backoff
- Actor failures: Job marked as failed, credits refunded
- Timeout: Job marked as failed, credits refunded

## Monitoring

### Job Status

Track job progress:
- `pending`: Job queued
- `running`: Scraping in progress
- `completed`: Successfully finished
- `failed`: Error occurred

### Logs

Check logs for debugging:

```bash
# Celery worker logs
tail -f backend/logs/celery.log

# Application logs
tail -f backend/logs/app.log
```

### Metrics

Monitor via `/metrics` endpoint:
- `scraping_jobs_total`: Total jobs created
- `scraping_jobs_completed`: Successful jobs
- `scraping_jobs_failed`: Failed jobs
- `reviews_scraped_total`: Total reviews collected

## Testing

### Unit Tests

```bash
cd backend
pytest tests/unit/test_scrapers.py
```

### Integration Tests

```bash
cd backend
pytest tests/integration/test_scraping_flow.py
```

### Manual Testing

1. Use fake sources first to test workflow
2. Test with small review counts (5-10)
3. Verify data appears in analytics
4. Check credit deductions

## Best Practices

1. **Start small**: Test with 10-20 reviews first
2. **Monitor costs**: Check Apify dashboard regularly
3. **Rate limiting**: Don't scrape too aggressively
4. **Query optimization**: Use specific search terms
5. **Data quality**: Review scraped data for accuracy

## Troubleshooting

### Scraper Not Working

1. Check Apify API token is valid
2. Verify actor IDs are correct
3. Check Celery workers are running
4. Review error logs

### No Results Returned

1. Verify search query is valid
2. Check if content exists for query
3. Try different search terms
4. Reduce review count

### Slow Performance

1. Reduce concurrent jobs
2. Increase Celery workers
3. Optimize database queries
4. Check Apify actor performance

## Future Enhancements

- [ ] Add more platforms (Yelp, Amazon, App Store)
- [ ] Implement caching for repeated queries
- [ ] Add bulk scraping for multiple companies
- [ ] Support scheduled/recurring scraping
- [ ] Add data quality scoring
- [ ] Implement deduplication logic
- [ ] Add sentiment analysis on scrape
- [ ] Support custom actor configurations

## Support

For issues or questions:
1. Check logs: `backend/logs/`
2. Review Apify actor documentation
3. Check actor run details in Apify Console
4. Contact support with job ID and error message

## License

This implementation uses Apify actors which have their own terms of service. Review each actor's license before use.


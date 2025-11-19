# Quick Start: Real Review Scraping

Get started with real review scraping in 5 minutes.

## Prerequisites

- Apify account (free tier available)
- Running NeedleAI instance
- At least one company created

## Step 1: Get Apify API Token (2 minutes)

1. Go to [Apify Console](https://console.apify.com/sign-up)
2. Sign up for free account
3. Navigate to **Settings** → **Integrations**
4. Copy your **API token**

## Step 2: Configure Environment (1 minute)

Add to your `backend/.env` file:

```bash
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxx
```

That's it! The actor IDs and costs are pre-configured.

## Step 3: Run Migration & Seed (1 minute)

```bash
cd backend

# Run migration to add new source types
alembic upgrade head

# Seed real review sources
python scripts/seed_real_sources.py

# Optional: Seed fake sources for testing
python scripts/seed_fake_sources.py
```

## Step 4: Restart Services (1 minute)

```bash
# Restart backend
cd backend
./scripts/stop.sh
./scripts/start.sh

# Frontend should auto-reload
```

## Step 5: Start Scraping! (30 seconds)

1. Open app at `http://localhost:3000`
2. Go to **Data Sources** page
3. Select a company
4. Choose a source:
   - **Twitter/X**: Social media mentions
   - **Reddit**: Community discussions
   - **G2**: B2B software reviews
   - **Trustpilot**: Customer reviews
5. Enter review count (start with 10)
6. Click **Start Job**
7. Go to **Jobs** page to monitor progress

## What You Get

Each scraped review includes:
- **Content**: Full review text
- **Author**: Username/handle
- **Date**: When posted
- **URL**: Link to original
- **Metadata**: Platform-specific data
  - Twitter: likes, retweets, replies
  - Reddit: score, subreddit, comments
  - G2: rating, pros, cons, company size
  - Trustpilot: stars, verified status

## Cost Example

Scraping 100 reviews:
- **Reddit**: 100 × $0.01 = $1.00
- **Twitter**: 100 × $0.01 = $1.00
- **G2**: 100 × $0.02 = $2.00
- **Trustpilot**: 100 × $0.015 = $1.50

## Tips

1. **Start small**: Test with 5-10 reviews first
2. **Use specific queries**: Better results
3. **Check credits**: Make sure you have enough
4. **Monitor jobs**: Watch progress in Jobs page
5. **Review data**: Check Analytics after completion

## Troubleshooting

### "Apify API token not configured"
→ Add `APIFY_API_TOKEN` to `.env` and restart

### "No scraping sources configured"
→ Run `python scripts/seed_real_sources.py`

### "Insufficient credits"
→ Purchase credits via Settings → Billing

### Job stuck in "pending"
→ Check Celery workers are running: `./scripts/status.sh`

## Next Steps

- Analyze reviews in **Analytics** page
- Chat with your data in **Chat** page
- Export data from **Datasets** page
- Set up recurring scraping (coming soon)

## Support

Need help? Check:
- [Full Documentation](./REAL_REVIEW_SCRAPING_IMPLEMENTATION.md)
- [Apify Actor Docs](https://docs.apify.com/)
- Logs: `backend/logs/celery.log`

Happy scraping! 🚀


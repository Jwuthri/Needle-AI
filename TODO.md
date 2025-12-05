# TODO List

## Features & Enhancements

### Review Scraping Optimization
- [ ] **Implement smart review deduplication before scraping**
  - When a user runs the review scraping task for a **company name** and requests **N reviews**, the system should:
    1. First check the global `reviews` table for existing reviews for that company
    2. Query the user's `__user_{id}_reviews` table to see which reviews they already have
    3. Copy any missing reviews from the global `reviews` table to the user's table (no scraping needed)
    4. Calculate remaining reviews needed: `reviews_to_scrape = N - transferred_count`
    5. Only run scraping for the remaining number of reviews needed
    6. After scraping, store new reviews in the global `reviews` table
    7. Finally, sync the newly scraped reviews to the user's `__user_{id}_reviews` table
  - **Example**: User requests 100 reviews for "CompanyX"
    - Global `reviews` table has 10 reviews for "CompanyX"
    - User's table has 0 of those reviews
    - Transfer 10 reviews → user table
    - Scrape only 90 more reviews (100 - 10 = 90)
  - **Benefits**: Reduces scraping costs, faster response times, and better resource utilization
  - **Files to modify**:
    - `backend/app/tasks/scraping_tasks.py` - Add pre-scraping check logic
    - `backend/app/services/user_reviews_service.py` - Add method to check for missing reviews and return count
    - `backend/app/database/repositories/review.py` - Add method to find reviews by company name

---

**Legend:**
- [ ] Not started
- [x] Completed


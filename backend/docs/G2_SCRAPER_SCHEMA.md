# G2 Product Scraper Schema

Apify Actor: `omkar-cloud/g2-product-scraper`

## Overview

Scrapes product information and reviews from G2.com. Returns an array of product objects.

---

## Product Object Schema

### Core Product Info

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | `int` | G2 internal product ID |
| `product_name` | `string` | Product name |
| `product_logo` | `string \| null` | URL to product logo image |
| `product_website` | `string \| null` | Product website URL |
| `product_description` | `string \| null` | Full product description |
| `what_is` | `string \| null` | Short product description |
| `positioning_against_competitor` | `string \| null` | Competitive positioning statement |

### G2 Links

| Field | Type | Description |
|-------|------|-------------|
| `g2_link` | `string` | G2 product reviews page URL |
| `g2_reviews_link` | `string \| null` | G2 reviews section URL |
| `discussions_link` | `string` | G2 discussions page URL |
| `seller` | `string` | G2 seller page URL |

### Ratings & Reviews

| Field | Type | Description |
|-------|------|-------------|
| `rating` | `float` | Overall rating (1-5) |
| `reviews` | `int` | Total number of reviews |
| `medal_image` | `string \| null` | URL to G2 medal/badge image |
| `star_distribution` | `object` | Review count per star rating |

**star_distribution example:**
```json
{
  "1": 2,
  "2": 2,
  "3": 16,
  "4": 112,
  "5": 386
}
```

### Company Info

| Field | Type | Description |
|-------|------|-------------|
| `company_id` | `int` | G2 internal company ID |
| `company_website` | `string \| null` | Company website URL |
| `company_phone` | `string \| null` | Company phone number |
| `company_location` | `string \| null` | Company HQ location |
| `company_founded_year` | `int \| null` | Year founded |
| `company_annual_revenue` | `string \| null` | Revenue range |
| `total_revenue_usd_mm` | `float \| null` | Revenue in millions USD |
| `company_ownership` | `string \| null` | Ownership type |
| `is_claimed` | `bool` | Whether product is claimed on G2 |

### Social Links

| Field | Type | Description |
|-------|------|-------------|
| `twitter` | `string \| null` | Twitter profile URL |
| `number_of_followers_on_twitter` | `int \| null` | Twitter follower count |
| `linkedin` | `string \| null` | LinkedIn page URL |
| `number_of_employees_on_linkedin` | `int \| null` | LinkedIn employee count |

### Categories

| Field | Type | Description |
|-------|------|-------------|
| `category` | `object` | Primary category |
| `parent_category` | `object \| null` | Parent category |
| `categories` | `array` | All associated categories |

**category object:**
```json
{
  "name": "Help Desk Software",
  "link": "https://www.g2.com/categories/help-desk"
}
```

### Other

| Field | Type | Description |
|-------|------|-------------|
| `supported_languages` | `string \| null` | Comma-separated language list |
| `services_offered` | `array \| null` | Services offered |
| `screenshots` | `array` | Screenshot URLs |
| `videos` | `array` | Video URLs |
| `download_links` | `array` | Download URLs |
| `popular_mentions` | `array` | Frequently mentioned topics in reviews |

---

## Nested Objects

### pricing_plans

```json
{
  "plan_name": "Pro",
  "plan_price": "$300.00",
  "plan_description": "Includes 2,000 tickets/mo",
  "plan_features": ["Feature 1", "Feature 2"]
}
```

### alternatives

```json
{
  "name": "Zendesk Support Suite",
  "link": "https://www.g2.com/products/zendesk-support-suite/reviews",
  "rating": 4,
  "reviews": 6006
}
```

### comparisons

```json
{
  "link": "https://www.g2.com/compare/gorgias-vs-zendesk-support-suite",
  "name": "Zendesk Support Suite",
  "logo": "https://images.g2crowd.com/..."
}
```

### features

Basic feature grouping:
```json
{
  "name": "Ticket and Case Management",
  "features": ["Ticket Creation", "Workflow", "Automated Response"]
}
```

### detailed_features

Feature with review stats:
```json
{
  "name": "Platform",
  "features": [
    {
      "name": "Mobile User Support",
      "content": "Allows software to be easily used on mobile devices...",
      "percentage": 74,
      "based_on_number_of_reviews": 89
    }
  ]
}
```

---

## Reviews Schema

### initial_reviews / all_reviews

```json
{
  "review_id": 9920899,
  "review_title": "CRM for Ecommerce",
  "review_content": "Full review text...",
  "review_rating": 5,
  "publish_date": "2024-07-24T00:00:00",
  "review_link": "https://www.g2.com/products/gorgias/reviews/gorgias-review-9920899",
  "video_link": null,
  "reviewer_company_size": "Mid-Market(51-1000 emp.)",
  "review_question_answers": [
    {
      "question": "What do you like best about Gorgias?",
      "answer": "..."
    },
    {
      "question": "What do you dislike about Gorgias?",
      "answer": "..."
    },
    {
      "question": "What problems is Gorgias solving and how is that benefiting you?",
      "answer": "..."
    }
  ],
  "reviewer": {
    "reviewer_name": "Christyl Faith G.",
    "reviewer_job_title": "Property Manager",
    "reviewer_link": "https://www.g2.com/users/..."
  }
}
```

---

## Company Size Values

Common `reviewer_company_size` values:
- `"Small-Business(50 or fewer emp.)"`
- `"Mid-Market(51-1000 emp.)"`
- `"Enterprise(> 1000 emp.)"`

---

## Usage Notes

1. **initial_reviews** contains ~10 reviews, **all_reviews** contains all scraped reviews
2. `product_logo` may return `"Proxied content"` instead of a URL
3. Nullable fields are common - always check for `null`
4. `rating` is 1-5 scale with one decimal precision
5. `publish_date` is ISO 8601 format


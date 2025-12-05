# TrustRadius Scraper Schema

Apify Actor: `scraped/trustradius-review-scraper`

## Overview

Scrapes B2B software reviews from TrustRadius.com for a specific product. Returns an array of detailed review objects with reviewer info, ratings, pros/cons, and feature ratings.

---

## Review Object Schema

### Core Review Info

| Field | Type | Description |
|-------|------|-------------|
| `Review ID` | `string` | TrustRadius review ID |
| `Title` | `string` | Review title (auto-generated format: "Product YYYY-MM-DD HH:MM:SS") |
| `Heading` | `string` | Product name |
| `Synopsis` | `string` | Short summary (often empty) |
| `Rating` | `int` | Overall rating (1-10 scale) |
| `Grade` | `string` | Letter grade: `"A"`, `"B"`, `"C"`, `"D"`, `"F"` |
| `Grade Numeric` | `int` | Numeric grade (1-5) |
| `Status` | `string` | Review status: `"published"`, `"pending"` |
| `Points` | `int` | Review points/score |

### Visibility

| Field | Type | Description |
|-------|------|-------------|
| `Show Public` | `bool` | Whether reviewer is public |
| `Show Public Numeric` | `int` | `0` = private, `1` = public |

### Dates

```json
{
  "Submitted Date": "2025-10-02T15:07:35.300Z",
  "Published Date": "2025-10-15T18:57:15.993Z",
  "Modified": "2025-11-12T20:28:15.829Z",
  "Last Updated": "2025-11-12T20:28:15.803Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `Submitted Date` | `string` | Original submission date (ISO 8601) |
| `Published Date` | `string` | Public publish date (ISO 8601) |
| `Modified` | `string` | Last modification date |
| `Last Updated` | `string` | Last update timestamp |
| `Read Count` | `int \| null` | Number of reads (often null) |

---

## Reviewer Information

| Field | Type | Description |
|-------|------|-------------|
| `Reviewer Name` | `string \| null` | Full name (null if anonymous) |
| `Reviewer First Name` | `string \| null` | First name |
| `Reviewer Last Name` | `string \| null` | Last name |
| `Reviewer Job Title` | `string \| null` | Job title |
| `Reviewer Job Type` | `string` | Role type: `"Consultant"`, `"Employee"`, etc. |
| `Reviewer Department` | `string` | Department: `"Marketing"`, `"IT"`, `"Engineering"`, etc. |
| `Reviewer Years Experience` | `int` | Years of experience |
| `Reviewer Roles` | `string` | Comma-separated roles: `"user, manager, consultant, decisionMaker"` |
| `Reviewer Picture` | `string \| null` | Profile picture URL |
| `Reviewer LinkedIn` | `string \| null` | LinkedIn profile URL |

---

## Company Information

| Field | Type | Description |
|-------|------|-------------|
| `Company Name` | `string \| null` | Reviewer's company name |
| `Company Size` | `string` | Size description: `"1-10 employees"`, `"11-50 employees"`, etc. |
| `Company Size Group` | `string` | Size category: `"small"`, `"medium"`, `"enterprise"` |
| `Company Size Minimum` | `int` | Minimum employee count for size range |
| `Company Industry` | `string` | Industry name |
| `Company Industry Code` | `string` | Industry code |

---

## Product Information

| Field | Type | Description |
|-------|------|-------------|
| `Product Name` | `string` | Product being reviewed |
| `Product Slug` | `string` | URL slug for product |
| `Product ID` | `string` | TrustRadius product ID |
| `Product Logo` | `string` | Product logo URL |
| `Vendor Name` | `string` | Vendor/company name |
| `Vendor Slug` | `string` | Vendor URL slug |
| `Vendor ID` | `string` | TrustRadius vendor ID |
| `Categories` | `string` | Comma-separated category names |
| `Other Products` | `string` | Other products reviewer uses |

---

## Review Content (Q&A Format)

TrustRadius reviews are structured as question/answer pairs. Each section has 4 fields:

- `*_question` - The question text
- `*_answer` - The answer text (concatenated)
- `*_values` - Array of individual answers
- `*_followup` - Follow-up comment (often null)

### Product Usage

```json
{
  "product-usage_question": "Use Cases and Deployment Scope",
  "product-usage_answer": "Working in a remote team, Slack is essential...",
  "product-usage_values": ["Working in a remote team..."],
  "product-usage_followup": null
}
```

### Pros (Things Done Well)

```json
{
  "things-done-well,pros-and-cons_question": "Pros",
  "things-done-well,pros-and-cons_answer": "Community\nCommunication\nReminders",
  "things-done-well,pros-and-cons_values": ["Community", "Communication", "Reminders"],
  "things-done-well,pros-and-cons_followup": null
}
```

### Cons (Things Done Poorly)

```json
{
  "things-done-poorly,pros-and-cons_question": "Cons",
  "things-done-poorly,pros-and-cons_answer": "Sometimes miss notifications.\nMessages disordered.",
  "things-done-poorly,pros-and-cons_values": ["Sometimes miss notifications.", "Messages disordered."],
  "things-done-poorly,pros-and-cons_followup": null
}
```

### Likelihood to Recommend (NPS)

```json
{
  "likelihood-to-recommend_question": "Likelihood to Recommend",
  "likelihood-to-recommend_answer": "9",
  "likelihood-to-recommend_values": [9],
  "likelihood-to-recommend_followup": "Any company's internal communication..."
}
```

### Return on Investment

```json
{
  "operational-benefits_question": "Return on Investment",
  "operational-benefits_answer": "Helped us stay connected...",
  "operational-benefits_values": ["Helped us stay connected...", "Manage communications..."],
  "operational-benefits_followup": null
}
```

### Usability Score

```json
{
  "product-usability_question": "Usability",
  "product-usability_answer": "10",
  "product-usability_values": [10],
  "product-usability_followup": "It's just easy to use and works."
}
```

### Alternatives Evaluated

```json
{
  "alternatives-evaluated_question": "Alternatives Considered",
  "alternatives-evaluated_answer": "Discord and Microsoft Teams",
  "alternatives-evaluated_values": ["Discord", "Microsoft Teams"],
  "alternatives-evaluated_followup": "Slack is the best, hands down..."
}
```

### Other Software Used

```json
{
  "other-software-used_question": "Other Software Used",
  "other-software-used_answer": "n8n, Google Meet, Brevo",
  "other-software-used_values": [
    {"productId": "...", "productName": "n8n", "value": 10, "submitted": true}
  ],
  "other-software-used_followup": null
}
```

---

## Feature Ratings

Feature-specific ratings with product-dependent feature IDs:

```json
{
  "feature-ratings_question": "Slack Feature Ratings",
  "feature-ratings_answer": "",
  "feature-ratings_values": [
    {"featureId": "54e4c721b938ba170044e78e", "value": 8, "na": false},
    {"featureId": "56006a47fc55761b006b558c", "value": 10, "na": false},
    {"featureId": "56006ad35c5002100042db1e", "value": 0, "na": true}
  ],
  "feature-ratings_followup": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `featureId` | `string` | TrustRadius feature ID |
| `value` | `int` | Rating (0-10) |
| `na` | `bool` | Not applicable flag |

### Common Feature Rating Fields (Product-Specific)

Depending on the product, you may also see individual feature columns:

| Field | Type | Description |
|-------|------|-------------|
| `feature_search_rating` | `int \| null` | Search feature rating |
| `feature_chat_rating` | `int \| null` | Chat feature rating |
| `feature_notifications_rating` | `int \| null` | Notifications rating |
| `feature_video_rating` | `int \| null` | Video feature rating |
| `feature_audio_rating` | `int \| null` | Audio feature rating |
| `feature_discussions_rating` | `int \| null` | Discussions rating |
| `feature_device-sync_rating` | `int \| null` | Device sync rating |

---

## Rating Scales

### Overall Rating
- **Scale**: 1-10
- **Conversion to 5-star**: Divide by 2

### Grade Scale

| Grade | Numeric | Rating Range |
|-------|---------|--------------|
| `A` | 5 | 9-10 |
| `B` | 4 | 7-8 |
| `C` | 3 | 5-6 |
| `D` | 2 | 3-4 |
| `F` | 1 | 1-2 |

### Company Size Groups

| Group | Employee Range |
|-------|---------------|
| `small` | 1-50 |
| `medium` | 51-500 |
| `enterprise` | 500+ |

---

## Usage Notes

1. All dates are ISO 8601 format in UTC
2. Rating is 1-10 scale (divide by 2 for 5-star equivalent)
3. Reviewer info may be null if anonymous
4. `*_values` arrays contain individual bullet points from the answer
5. `*_followup` contains additional context when reviewer elaborates
6. Feature ratings are product-specific with unique feature IDs
7. `Other Products` shows competitor/complementary products reviewer uses
8. `Alternatives Evaluated` is valuable for competitive analysis

---

## Actor Input

```json
{
  "url": "https://www.trustradius.com/products/slack/reviews",
  "maxReviews": 100
}
```

| Field | Type | Description |
|-------|------|-------------|
| `url` | `string` | TrustRadius product reviews URL |
| `maxReviews` | `int` | Maximum reviews to fetch (optional) |


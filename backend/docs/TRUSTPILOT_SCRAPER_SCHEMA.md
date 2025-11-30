# Trustpilot Scraper Schema

Apify Actor: `canadesk/trustpilot`

## Overview

Scrapes reviews from Trustpilot.com for a specific business. Returns an array of review objects.

---

## Review Object Schema

### Core Review Info

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Trustpilot review ID |
| `title` | `string` | Review title |
| `text` | `string` | Full review text |
| `rating` | `int` | Rating (1-5) |
| `likes` | `int` | Number of likes on the review |
| `language` | `string` | Review language code (e.g., `"en"`) |
| `opinion` | `string` | Sentiment: `"Positive"`, `"Negative"`, `"Neutral"` |
| `link` | `string` | Direct URL to the review |
| `website` | `string` | Reviewed business domain |

### Review Status

| Field | Type | Description |
|-------|------|-------------|
| `filtered` | `bool` | Whether review is filtered |
| `pending` | `bool` | Whether review is pending approval |
| `hasUnhandledReports` | `bool` | Whether review has unhandled reports |
| `report` | `object \| null` | Report details if any |

### Dates

```json
{
  "experiencedDate": "2025-09-29T00:00:00.000Z",
  "publishedDate": "2025-09-29T17:41:53.000Z",
  "updatedDate": null,
  "submittedDate": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `experiencedDate` | `string` | Date of experience (ISO 8601) |
| `publishedDate` | `string` | Review publish date (ISO 8601) |
| `updatedDate` | `string \| null` | Last update date |
| `submittedDate` | `string \| null` | Original submission date |

---

## Nested Objects

### consumer

Reviewer information:

```json
{
  "id": "5615c2ae0000ff0001e16b7c",
  "displayName": "Miss Danila Mega",
  "imageUrl": "https://user-images.trustpilot.com/5615c2ae0000ff0001e16b7c/73x73.png",
  "numberOfReviews": 6,
  "countryCode": "AU",
  "hasImage": true,
  "isVerified": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Trustpilot user ID |
| `displayName` | `string` | Display name |
| `imageUrl` | `string` | Profile image URL |
| `numberOfReviews` | `int` | Total reviews by user |
| `countryCode` | `string` | ISO country code |
| `hasImage` | `bool` | Has profile image |
| `isVerified` | `bool` | Verified user |

### labels.verification

Review verification details:

```json
{
  "isVerified": false,
  "createdDateTime": "2025-11-25T07:48:39.000Z",
  "reviewSourceName": "Organic",
  "verificationSource": "invitation",
  "verificationLevel": "not-verified",
  "hasDachExclusion": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `isVerified` | `bool` | Whether review is verified |
| `createdDateTime` | `string` | Verification timestamp |
| `reviewSourceName` | `string` | Source: `"Organic"`, `"Invitation"` |
| `verificationSource` | `string` | Verification method |
| `verificationLevel` | `string` | `"verified"`, `"not-verified"` |
| `hasDachExclusion` | `bool` | DACH region exclusion flag |

### reply

Business reply (if exists):

```json
{
  "message": "We're truly sorry for the delay...",
  "publishedDate": "2025-07-23T08:35:55.000Z",
  "updatedDate": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | `string` | Reply text |
| `publishedDate` | `string` | Reply date (ISO 8601) |
| `updatedDate` | `string \| null` | Last update date |

---

## Other Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | `string` | Review source: `"Organic"`, `"Invitation"` |
| `location` | `object \| null` | Location data (rarely populated) |
| `productReviews` | `array` | Product-specific reviews (usually empty) |
| `consumersReviewCountOnSameDomain` | `int` | User's review count for this business |
| `consumersReviewCountOnSameLocation` | `int \| null` | User's review count at same location |
| `labels.merged` | `object \| null` | Merged review info |

---

## Opinion Values

| Value | Description |
|-------|-------------|
| `"Positive"` | Rating 4-5 |
| `"Neutral"` | Rating 3 |
| `"Negative"` | Rating 1-2 |

---

## Usage Notes

1. All dates are ISO 8601 format in UTC
2. `reply` is `null` when business hasn't responded
3. `opinion` is derived from `rating` by the scraper
4. `consumer.countryCode` uses ISO 3166-1 alpha-2 codes
5. Reviews are returned newest first
6. `productReviews` is typically empty for service reviews


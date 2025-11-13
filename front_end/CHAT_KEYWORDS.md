# Chat Message Keyword Highlighting

## Overview

The enhanced chat interface now includes intelligent keyword highlighting similar to Elysia, making important terms stand out in conversations.

## Keyword Categories

### 🔵 Actions (Blue)
Words that describe operations or commands:
- `count`, `sum`, `average`, `calculate`, `analyze`
- `show`, `list`, `find`, `get`, `search`
- `filter`, `group`, `aggregate`

**Example**: "**Count** transactions by payment method"

### 🟢 Entities (Emerald/Green)
Data objects and business entities:
- `transactions`, `users`, `customers`, `payments`
- `reviews`, `products`, `orders`, `data`, `records`

**Example**: "Analyze customer **reviews** for product feedback"

### 🟣 Methods (Purple)
Payment methods and specific types:
- `card`, `paypal`, `cash`, `credit`, `debit`
- `bank`, `transfer`, `wallet`

**Example**: "Show **paypal** and **card** transaction volumes"

### 🟡 Metrics (Yellow)
Measurements and KPIs:
- `total`, `revenue`, `sales`, `amount`, `quantity`
- `rate`, `percentage`, `ratio`, `score`

**Example**: "Calculate **total revenue** by **percentage**"

## Customizing Keywords

Edit `/frontend/src/components/chat/enhanced-message.tsx`:

```typescript
const KEYWORDS = {
  actions: ['count', 'sum', 'average', ...], // Add your action words
  entities: ['transactions', 'users', ...],   // Add your entity names
  methods: ['card', 'paypal', ...],           // Add payment/method types
  metrics: ['total', 'revenue', ...],         // Add metric names
}
```

## Color Customization

Change colors by modifying the color mapping:

```typescript
const color = 
  category === 'actions' ? 'text-blue-400' :      // Change to text-cyan-400, etc.
  category === 'entities' ? 'text-emerald-400' :  // Change to text-green-400, etc.
  category === 'methods' ? 'text-purple-400' :    // Change to text-pink-400, etc.
  'text-yellow-400'                                // Default for metrics
```

## Features

### User Messages (Questions)
- Large, prominent display with gradient text
- Keyword highlighting in the title
- Query type indicator
- Copy button for easy reference

### Assistant Messages (Answers)
- Structured formatting with headers and bullet points
- Automatic keyword detection and highlighting
- Summary section for quick overview
- Expandable sources with relevance scores
- Related questions for follow-up queries

### Smart Formatting
The system automatically detects and formats:
- **Headers**: Lines ending with `:` become section headers
- **Bullet points**: Lines starting with `-` or `•`
- **Summaries**: First short line becomes a summary
- **Keywords**: Automatically highlighted based on category

## Examples

### Question Display
```
Count transactions by payment method.
↓
"Count transactions by payment method."
 ^^^^  ^^^^^^^^^^^^    ^^^^^^^
 blue     green         purple
```

### Answer Display
```
Transaction Counts:
• Card: 403 transactions
• Paypal: 162 transactions
↓
Transaction Counts:  (with emerald bullet)
• Card: 403 transactions
  ^^^^  ^^^
  purple yellow
```

## Tips for Best Results

1. **Use descriptive questions**: Include entities and actions
2. **Be specific**: Mention exact metrics and methods
3. **Follow-up naturally**: Click related questions for context-aware conversations
4. **Review sources**: Check the sources section for data backing

## Technical Details

- **Regex-based matching**: Case-insensitive word boundary detection
- **Overlap prevention**: Conflicts resolved by position priority
- **Performance**: Optimized for real-time highlighting
- **Accessibility**: Maintains semantic HTML structure


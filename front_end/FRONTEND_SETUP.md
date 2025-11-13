# Frontend Setup Guide

## Overview

This is the frontend for the NeedleAI Product Review Analysis Platform, built with Next.js 14, TypeScript, and styled with a dark theme featuring emerald/green accents.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS (custom theme with emerald colors)
- **Authentication**: Clerk
- **UI Components**: Custom components with Framer Motion animations
- **Icons**: Lucide React
- **HTTP Client**: Native Fetch API
- **State Management**: React Context + Custom Hooks

## Environment Variables

Create a `.env.local` file in the frontend directory with:

```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_key_here

# Clerk Routes
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket URL (for real-time features)
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Installation

```bash
cd frontend
npm install
```

## Development

```bash
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

## Project Structure

```
src/
├── app/                      # Next.js App Router pages
│   ├── layout.tsx           # Root layout with providers
│   ├── page.tsx             # Landing page (public)
│   ├── dashboard/           # Dashboard (protected)
│   ├── companies/           # Company management
│   ├── chat/                # Chat interface with dual view
│   ├── analytics/           # Analytics dashboard
│   ├── data-sources/        # Scraping & data import
│   ├── credits/             # Credits & billing
│   └── sign-in/             # Clerk sign-in
│   └── sign-up/             # Clerk sign-up
├── components/
│   ├── layout/              # Sidebar, AppLayout
│   ├── companies/           # Company cards, forms
│   ├── chat/                # Chat UI, terminal input, tree view
│   ├── providers/           # Context providers
│   └── ui/                  # Reusable UI components
├── hooks/                   # Custom React hooks
├── lib/                     # Utilities & API client
├── types/                   # TypeScript type definitions
└── middleware.ts            # Clerk auth middleware
```

## Key Features

### 1. Dashboard
- Overview statistics (companies, reviews, credits)
- Recent activity feed
- Quick actions

### 2. Companies Management
- List all companies
- Create/edit/delete companies
- Company detail pages with quick actions
- Navigate to chat, analytics, or data import

### 3. Chat Interface (Dual View)
**Chat View:**
- Terminal-style input with ZSH aesthetics
- Message history with sources
- Related questions
- Real-time AI responses with RAG

**Tree View:**
- Visual pipeline representation
- Shows query processing steps:
  - Query preprocessing
  - Vector search
  - RAG retrieval
  - LLM generation
- Timing and metadata for each step

### 4. Analytics
- Table and graph view toggle
- Sentiment distribution
- Reviews by source
- Date range filtering
- Export functionality

### 5. Data Sources
- Start scraping jobs (Reddit, Twitter, etc.)
- CSV/JSON file upload
- Active jobs with progress tracking
- Real-time job status updates

### 6. Credits & Billing
- Current balance display
- Purchase credit tiers
- Transaction history
- Stripe integration

## Design System

### Colors
- **Background**: Dark grays (`gray-950`, `gray-900`, `gray-800`)
- **Primary**: Emerald/Green (`emerald-500`, `green-400`)
- **Accent**: Blue-gray tones
- **Text**: White with varying opacity

### Typography
- **Headings**: Space Grotesk
- **Body**: Inter
- **Code/Terminal**: JetBrains Mono

### Theme Features
- Custom scrollbars with emerald accent
- Terminal cursor animations
- Green glow effects on focus
- Dark gradient backgrounds
- Smooth transitions and animations

## Authentication Flow

1. **Public Routes**: Landing page, sign-in, sign-up
2. **Protected Routes**: All app pages (dashboard, companies, chat, etc.)
3. **Auto-redirect**: Unauthenticated users → sign-in page
4. **After Sign-in**: Redirect to dashboard

## API Integration

The frontend communicates with the backend via the `ApiClient` class in `src/lib/api.ts`. It automatically:
- Adds Clerk auth tokens to requests
- Handles errors consistently
- Manages session state

Example usage:
```typescript
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'

const { getToken } = useAuth()
const token = await getToken()
const api = createApiClient(token)

// Use API methods
const companies = await api.listCompanies()
const analytics = await api.getAnalyticsOverview(companyId)
```

## Custom Hooks

- `use-chat.ts`: Chat state management
- `use-debounce.ts`: Input debouncing
- `use-local-storage.ts`: Persistent local storage

## Building for Production

```bash
npm run build
npm start
```

## Type Safety

All API responses and components are fully typed. Types are defined in `src/types/`:
- `chat.ts`: Chat messages, pipeline steps, sources
- `company.ts`: Company data structures
- `scraping.ts`: Scraping jobs, sources, reviews
- `analytics.ts`: Analytics data, insights
- `credits.ts`: Credit balance, transactions

## Performance Optimizations

- Lazy loading for analytics visualizations
- Pagination for large data tables
- WebSocket for real-time scraping progress
- Debounced search and filter inputs
- Optimized images with Next.js Image component

## Styling Guidelines

1. Use Tailwind utility classes
2. Emerald-500 for primary actions and active states
3. Gray-800/50 with border-gray-700/50 for cards
4. Add subtle green border glow on hover/focus
5. Maintain dark gradient backgrounds
6. Use Framer Motion for animations

## Common Issues

### 1. Clerk Auth Not Working
- Ensure environment variables are set correctly
- Check Clerk dashboard settings
- Verify public/protected routes in middleware.ts

### 2. API Calls Failing
- Check backend is running on correct port
- Verify NEXT_PUBLIC_API_URL is set
- Check browser console for CORS issues

### 3. Styling Issues
- Run `npm run build` to regenerate Tailwind
- Check for conflicting class names
- Verify custom fonts are loading

## Next Steps

1. Set up Clerk account and add API keys
2. Start backend server
3. Run frontend dev server
4. Create a test company
5. Import or scrape some reviews
6. Start chatting with your data!

## Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Clerk Documentation](https://clerk.com/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Framer Motion](https://www.framer.com/motion/)


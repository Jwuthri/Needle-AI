# Product Review Analysis Platform - Frontend Implementation

## Design System & Theme

**Color Scheme (Elysia-inspired):**

- Background: Dark grays (`gray-950`, `gray-900`, `gray-800`)
- Primary accent: Emerald/Green (`emerald-500`, `green-400`)
- Secondary: Blue-gray tones
- Text: White with varying opacity
- Borders: Subtle green glows on focus

**Typography:**

- Headings: Space Grotesk (already configured)
- Body: Inter (already configured)
- Terminal/Code: Monospace font (JetBrains Mono or Fira Code)

**Keep from existing:**

- Dark gradient backgrounds (`from-gray-950 via-blue-950 to-purple-950`)
- Framer Motion animations
- Current component patterns
- Clerk auth integration (enable it in layout.tsx)

## Phase 1: Cleanup & Core Layout

**Remove cookiecutter demo files:**

- Current `src/app/page.tsx` (generic AI chat landing)
- Current `src/app/chat/page.tsx` (simple chat)
- `src/components/chat/*` (will be replaced)
- Keep: `src/components/providers/*`, `src/components/ui/*`, `src/hooks/*`, `src/lib/*`

**Create new core layout structure:**

`src/components/layout/sidebar.tsx` - Left navigation with:

- Logo/branding at top
- Navigation items: Companies, Chat, Analytics, Data Sources, Credits
- Active conversation list (for Chat section)
- User profile at bottom (Clerk UserButton)
- Icons from lucide-react with emerald accent colors

`src/components/layout/app-layout.tsx` - Wrapper for authenticated pages:

- Fixed sidebar on left (similar to Elysia screenshots)
- Main content area with dark background
- Responsive: collapsible sidebar on mobile

## Phase 2: Type Definitions

**Update `src/types/chat.ts`:**

```typescript
// Enhanced chat with RAG and pipeline visualization
export interface ReviewSource {
  review_id: string
  content: string
  author: string
  source: string // reddit/twitter/csv
  sentiment: float
  url?: string
  relevance_score: float
}

export interface QueryPipelineStep {
  name: string // "Query preprocessing", "Vector search", etc.
  duration_ms: number
  status: string
  metadata: Record<string, any>
}

export interface EnhancedChatMessage extends ChatMessage {
  query_type?: string
  pipeline_steps?: QueryPipelineStep[]
  sources?: ReviewSource[]
  related_questions?: string[]
}
```

**Create `src/types/company.ts`:**

```typescript
export interface Company {
  id: string
  name: string
  domain: string
  industry: string
  created_at: string
  total_reviews?: number
  last_scrape?: string
}
```

**Create `src/types/scraping.ts`:**

```typescript
export interface ScrapingSource {
  id: string
  name: string
  source_type: 'reddit' | 'twitter' | 'custom'
  cost_per_review: number
  is_active: boolean
}

export interface ScrapingJob {
  id: string
  company_id: string
  source_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress_percentage: number
  total_reviews_target: number
  reviews_fetched: number
  cost: number
  started_at?: string
  completed_at?: string
  error_message?: string
}
```

**Create `src/types/analytics.ts`:**

```typescript
export interface AnalyticsOverview {
  total_reviews: number
  reviews_by_source: Record<string, number>
  sentiment_distribution: {
    positive: number
    neutral: number
    negative: number
  }
  date_range: {
    start: string
    end: string
  }
}

export interface CompanyInsights {
  common_themes: string[]
  product_gaps: string[]
  top_competitors: string[]
  top_feature_requests: string[]
}
```

## Phase 3: API Client Extensions

**Update `src/lib/api.ts`:**

- Keep existing `ApiClient` class structure
- Add company endpoints: `createCompany`, `listCompanies`, `getCompany`, `deleteCompany`
- Add scraping endpoints: `startScrapingJob`, `getJobStatus`, `listSources`, `estimateCost`
- Add analytics endpoints: `getAnalyticsOverview`, `getCompanyInsights`, `getReviews`
- Add credits endpoints: `getCreditBalance`, `createCheckoutSession`
- Update chat methods to handle `EnhancedChatMessage` types

## Phase 4: Dashboard Page (Landing after login)

**Create `src/app/dashboard/page.tsx`:**

- Overview statistics cards (total companies, total reviews, credits remaining)
- Recent activity feed (recent scraping jobs, chat sessions)
- Quick actions: "New Company", "Start Chat", "Import Data"
- Stats visualizations: reviews over time chart, sentiment pie chart
- Use existing gradient backgrounds and card components

## Phase 5: Companies Management

**Create `src/app/companies/page.tsx`:**

- Grid or list of user's companies
- Each card shows: name, domain, review count, last scrape date
- "Add Company" button (opens modal)
- Click company → navigate to company detail page

**Create `src/app/companies/[id]/page.tsx`:**

- Company header with edit/delete actions
- Tabs: Overview, Reviews, Analytics, Settings
- Overview tab: key metrics, recent reviews, quick chat access
- Integration with analytics and chat for this specific company

**Create `src/components/companies/company-card.tsx`:**

- Reusable company card component
- Shows metrics and status indicators

**Create `src/components/companies/company-form-modal.tsx`:**

- Form to create/edit company
- Fields: name, domain, industry
- Use Clerk user ID for `created_by`

## Phase 6: Chat Interface (Dual View)

**Create `src/app/chat/page.tsx`:**

- Main chat interface with company selector at top
- Toggle between "Chat" and "Tree" views (buttons in header)
- Terminal-style input at bottom
- Uses new chat components

**Create `src/components/chat/chat-view.tsx`:**

- Normal Q&A interface (like current but enhanced)
- Messages show sources as expandable cards
- Related questions as clickable suggestions
- Message actions: like, dislike, copy, view sources

**Create `src/components/chat/tree-view.tsx`:**

- Visualization of query pipeline (like Elysia screenshots)
- Shows steps: Query preprocessing → Vector search → RAG retrieval → LLM generation
- Each step is a node with timing and status
- Green highlights for active/completed steps
- Dotted lines connecting steps (like image 4)
- Click node to see details/metadata

**Create `src/components/chat/terminal-input.tsx`:**

- ZSH-style terminal input
- Features:
  - Prompt prefix: `user@company-name ~ $` in green
  - Monospace font (JetBrains Mono)
  - Blinking cursor
  - Command history (up/down arrows)
  - Auto-suggestions as you type
  - Syntax highlighting for special commands
  - Dark background with subtle border glow

**Create `src/components/chat/message-with-sources.tsx`:**

- Message display with expandable source cards
- Each source shows: excerpt, author, source type, sentiment badge
- Click to see full review

**Create `src/components/chat/pipeline-visualizer.tsx`:**

- Reusable component for rendering pipeline steps
- SVG-based flow diagram with animated connections
- Timing indicators and status badges

**Create `src/hooks/use-pipeline-data.ts`:**

- Custom hook to manage pipeline visualization state
- Parse `pipeline_steps` from message metadata

## Phase 7: Analytics Dashboard

**Create `src/app/analytics/page.tsx`:**

- Company selector dropdown
- View toggle: Table / Graph (tabs)
- Date range picker
- Export data button

**Create `src/components/analytics/analytics-table.tsx`:**

- DataTable showing reviews (like image 3)
- Columns: author, content, source, sentiment, timestamp
- Sortable, filterable, paginated
- Search functionality

**Create `src/components/analytics/analytics-graph.tsx`:**

- Interactive graph visualizations:
  - Sentiment over time (line chart)
  - Reviews by source (bar chart)
  - Word cloud of common themes
  - Competitor mentions network

**Create `src/components/analytics/insights-panel.tsx`:**

- AI-generated insights display
- Categories: Product Gaps, Feature Requests, Competitors
- Expandable sections with detailed findings

**Create `src/components/analytics/filters-sidebar.tsx`:**

- Filter by source, sentiment, date range
- Save filter presets

## Phase 8: Data Sources & Scraping

**Create `src/app/data-sources/page.tsx`:**

- Two sections: "Start Scraping" and "Import Data"
- Available sources list (Reddit, Twitter, etc.) with costs
- "Start Scraping" form: select source, set review count, see cost estimate
- Upload CSV/JSON section
- Active jobs list with progress bars

**Create `src/components/scraping/source-selector.tsx`:**

- Cards for each scraping source
- Shows: name, cost per review, status (active/inactive)
- Click to configure scraping job

**Create `src/components/scraping/scraping-job-card.tsx`:**

- Job progress visualization
- Status indicator (pending/running/completed/failed)
- Progress bar with percentage
- Cost display
- Cancel button for running jobs

**Create `src/components/scraping/csv-uploader.tsx`:**

- Drag & drop CSV upload
- Preview data before import
- Column mapping interface

**Create `src/hooks/use-scraping-job.ts`:**

- Custom hook for polling job status
- Real-time progress updates
- Handle job completion/failure

## Phase 9: Credits & Billing

**Create `src/app/credits/page.tsx`:**

- Current balance display (large, prominent)
- Purchase credits button (opens Stripe checkout)
- Transaction history table
- Usage breakdown by source

**Create `src/components/credits/credit-balance-card.tsx`:**

- Shows available credits
- Visual indicator (progress bar or gauge)
- Quick buy button

**Create `src/components/credits/transaction-history.tsx`:**

- List of credit purchases and usage
- Filterable by date, type

**Create `src/components/credits/pricing-tiers.tsx`:**

- Credit purchase options
- Shows $ amount → credits conversion
- "Buy Now" buttons → Stripe checkout

## Phase 10: Custom Hooks & Utilities

**Create `src/hooks/use-company.ts`:**

- Manage company CRUD operations
- Fetch company list, create, update, delete
- Cache and state management

**Create `src/hooks/use-analytics.ts`:**

- Fetch analytics data for selected company
- Handle date range filters
- Cache results

**Create `src/hooks/use-credits.ts`:**

- Fetch credit balance
- Listen for credit updates after purchases/usage
- Display warnings when low

**Create `src/hooks/use-terminal-input.ts`:**

- Manage terminal input state
- Command history (up/down navigation)
- Auto-suggestions

**Update `src/hooks/use-chat.ts`:**

- Support company context
- Handle enhanced message types with sources
- Manage dual view state (chat/tree)

## Phase 11: Theme & Styling Updates

**Update `src/app/globals.css`:**

- Add terminal-specific styles (monospace font, cursor animation)
- Add green glow effects for borders/focus states
- Pipeline visualization styles (SVG animations)
- Scrollbar styling (dark theme)
- Custom data table styles

**Update `tailwind.config.js`:**

- Add emerald/green color palette variations
- Add custom animations (pulse, glow, typing cursor)
- Add monospace font family
- Custom shadows for terminal aesthetic

## Phase 12: Authentication & Protected Routes

**Update `src/app/layout.tsx`:**

- Enable `ClerkProvider` (uncomment existing code)
- Add Clerk environment variables to `.env.local`

**Update `src/middleware.ts`:**

- Protect all routes except landing page
- Redirect unauthenticated users to sign-in

**Create `src/app/page.tsx` (new landing page):**

- Marketing landing page for unauthenticated users
- Hero section with product description
- Features showcase
- "Sign In" and "Get Started" buttons (Clerk)
- Keep existing purple/blue gradient aesthetic

**Create `src/app/sign-in/[[...sign-in]]/page.tsx`:**

- Clerk sign-in page

**Create `src/app/sign-up/[[...sign-up]]/page.tsx`:**

- Clerk sign-up page

## Implementation Notes

**Preserve existing:**

- All provider components in `src/components/providers/`
- Toast system for notifications
- Theme provider setup
- Existing utility functions in `src/lib/utils.ts`
- Loading and error UI components

**Design consistency:**

- Use emerald-500 for primary actions and active states
- Use gray-800/50 with border-gray-700/50 for cards
- Add subtle green border glow on hover/focus
- Maintain dark gradient backgrounds
- Keep existing animation patterns (framer-motion)
- Use lucide-react icons throughout

**Responsive design:**

- Mobile: collapsible sidebar, stacked layouts
- Tablet: condensed sidebar
- Desktop: full sidebar with labels

**Performance:**

- Lazy load analytics visualizations
- Pagination for large data tables
- WebSocket for real-time scraping progress
- Debounce search/filter inputs
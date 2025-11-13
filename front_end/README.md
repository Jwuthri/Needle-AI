# NeedleAi Frontend

A FastAPI + Next.js AI agent application with OpenRouter and Agno

A modern, responsive Next.js frontend for AI-powered chat applications with real-time messaging, beautiful UI components, and seamless backend integration.

## 🚀 Features

### Core Features

- **💬 Interactive Chat Interface**: Beautiful, responsive chat UI with message history
- **🔐 Authentication**: Clerk.com integration with Google social login support
- **🚀 Real-time Messaging**: HTTP-based messaging with optimized polling
- **🎨 Modern UI Components**: Custom-built components with consistent design system
- **📱 Responsive Design**: Mobile-first approach that works on all devices
- **⚡ Fast Performance**: Optimized with Next.js 14+ App Router for lightning-fast loading
- **🔄 State Management**: Efficient context-based state management for chat sessions

### User Experience

- **👤 User Authentication**: Secure sign-in/sign-up with Google social login
- **🔒 Protected Routes**: Automatic redirection for unauthenticated users
- **💭 Typing Indicators**: Visual feedback during AI response generation
- **🔍 Message Search**: Find previous conversations quickly
- **💾 Session Persistence**: Automatic session saving and restoration
- **🌙 Dark Theme**: Modern dark gradient theme with beautiful UI
- **♿ Accessibility**: WCAG compliant with keyboard navigation support
- **📧 Toast Notifications**: User-friendly error and success messages

### Technical Features

- **📦 Component Library**: Reusable UI components built with TypeScript
- **🎣 Custom Hooks**: Specialized React hooks for chat functionality
- **🔧 Configuration Management**: Environment-based settings
- **🛡️ Error Handling**: Graceful error recovery and user feedback
- **🎯 Performance Optimized**: Code splitting, lazy loading, and caching strategies

## 🏗️ Architecture

### Project Structure

```
├── src/
│   ├── app/                    # Next.js 13+ App Router
│   │   ├── globals.css        # Global styles
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   ├── chat/              # Chat interface pages
│   │   └── api/               # API routes (if needed)
│   │
│   ├── components/            # Reusable UI components
│   │   ├── ui/               # Base UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   └── ...
│   │   ├── chat/             # Chat-specific components
│   │   │   ├── chat-container.tsx
│   │   │   └── message-item.tsx
│   │   ├── layout/           # Layout components
│   │   └── providers/        # Context providers
│   │
│   ├── hooks/                # Custom React hooks
│   │   ├── use-chat.ts       # Chat functionality
│   │   ├── use-local-storage.ts
│   │   └── use-debounce.ts
│   │
│   ├── lib/                  # Utilities and configurations
│   │   ├── api.ts           # Backend API client
│   │   ├── utils.ts         # Helper functions
│   │   └── constants.ts     # App constants
│   │
│   └── types/               # TypeScript type definitions
│       ├── chat.ts
│       └── api.ts
```

### Key Components

**Chat Components**:

- `ChatContainer`: Complete chat interface with header, messages, and input
- `MessageItem`: Individual message display with role-based styling and animations

**UI Components**:

- `Button`: Customizable button with variants
- `Input`: Form input with validation states
- `Card`: Container component for content sections
- `Avatar`: User/AI avatar display
- `Toast`: Notification system

**Providers**:

- `ChatProvider`: Global chat state management
- `ThemeProvider`: Theme switching functionality
- `ToastProvider`: Notification management

## 🚦 Quick Start

### Prerequisites

- **Node.js**: 18.0+
- **npm/yarn/pnpm**: Latest version
- **Backend API**: NeedleAi Backend running on port 8000

### 1. Installation

```bash
# Install dependencies
npm install
# or
yarn install
# or
pnpm install
```

### 2. Environment Setup

Create a `.env.local` file:

```bash
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your-clerk-publishable-key-here

# Backend API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=# WebSocket not enabled

# App Configuration
NEXT_PUBLIC_APP_NAME=NeedleAi
NEXT_PUBLIC_APP_VERSION=0.1.0

# Optional: Analytics, monitoring, etc.
# NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
# NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
```

### 3. Development Server

```bash
# Start development server
npm run dev
# or
yarn dev
# or
pnpm dev
```

Visit [http://localhost:3000](http://localhost:3000) to see your application.

### 4. Backend Connection

Make sure your backend is running:

```bash
# In backend directory
./scripts/start.sh development
```

The frontend will automatically connect to your backend API.

## 🎨 Styling & Theming

### Design System

The application uses a custom design system built on top of modern CSS:

**Colors**:

- Primary: Blue gradient (#3B82F6 → #1D4ED8)
- Secondary: Gray scale (#F8FAFC → #0F172A)
- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Error: Red (#EF4444)

**Typography**:

- Font Family: Inter (system fallback)
- Scale: 12px → 48px with consistent rhythm
- Weight: 400, 500, 600, 700

**Spacing**:

- Base unit: 4px
- Scale: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px

### Theme Configuration

```typescript
// src/lib/theme.ts
export const theme = {
  colors: {
    primary: "hsl(221.2 83.2% 53.3%)",
    secondary: "hsl(210 40% 98%)",
    // ... more colors
  },
  fonts: {
    sans: ["Inter", "system-ui", "sans-serif"],
  },
  // ... more theme options
};
```

### Dark Mode

Built-in dark mode support with system preference detection:

```typescript
// Automatic theme detection
const { theme, setTheme } = useTheme()

// Manual theme switching
<button onClick={() => setTheme('dark')}>
  Switch to Dark Mode
</button>
```

## 💬 Chat Features

### Message Types

The chat interface supports various message types:

```typescript
type MessageRole = "user" | "assistant" | "system";

interface ChatMessage {
  id: string;
  content: string;
  role: MessageRole;
  timestamp: string;
  metadata?: Record<string, any>;
}
```

### Session Management

Automatic session handling:

```typescript
// Custom hook for chat functionality
const { messages, sendMessage, isLoading, error, clearChat, sessionId } =
  useChat();

// Send a message
await sendMessage("Hello, how can you help me?");
```

### Real-time Updates


**HTTP Polling**:

```typescript
// Optimized polling for message updates
const { messages, refresh } = useChatPolling({
  interval: 1000, // 1 second
  enabled: isActive,
});
```



### Message Features

- **Rich Text Support**: Markdown rendering for AI responses
- **Code Syntax Highlighting**: Automatic language detection
- **Link Detection**: Clickable URLs with security measures
- **Image Support**: Display images in messages (configurable)
- **Copy to Clipboard**: Easy message copying

## 🔧 Configuration

### API Configuration

```typescript
// src/lib/api.ts
export const apiConfig = {
  baseURL:
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000",
  timeout: 30000,
  retries: 3,
  retryDelay: 1000,
};
```

### Chat Settings

```typescript
// src/lib/constants.ts
export const CHAT_SETTINGS = {
  MAX_MESSAGE_LENGTH: 2000,
  AUTO_SAVE_INTERVAL: 5000,
  MAX_MESSAGES_DISPLAY: 100,
  TYPING_INDICATOR_DELAY: 500,
  RECONNECT_ATTEMPTS: 5,
};
```

### Feature Flags

```typescript
// src/lib/features.ts
export const FEATURES = {
  WEBSOCKETS: false,
  DARK_MODE: true,
  MESSAGE_SEARCH: true,
  FILE_UPLOAD: false, // Future feature
  VOICE_INPUT: false  // Future feature
}
```

## 🧪 Development

### Available Scripts

```bash
# Development server
npm run dev

# Production build
npm run build

# Start production server
npm run start

# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix

# Testing
npm run test
npm run test:watch
npm run test:e2e
```

### Code Quality

**ESLint Configuration**:

```json
{
  "extends": ["next/core-web-vitals", "@typescript-eslint/recommended"],
  "rules": {
    "no-unused-vars": "error",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

**TypeScript Strict Mode**:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

### Testing

**Unit Testing** (Jest + Testing Library):

```bash
# Run unit tests
npm run test
```

**End-to-End Testing** (Playwright):

```bash
# Run E2E tests
npm run test:e2e
```

## 🐳 Docker Support

### Development with Docker

```dockerfile
# Dockerfile included in project
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
```

```bash
# Build and run
docker build -t needleai-frontend .
docker run -p 3000:3000 needleai-frontend
```

### Docker Compose Integration

The frontend works seamlessly with the backend Docker setup:

```yaml
# docker-compose.yml (in project root)
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

## 🚀 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Set environment variables in Vercel dashboard
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

### Netlify

```bash
# Build command
npm run build

# Publish directory
out

# Environment variables
NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

### Self-Hosted

```bash
# Build for production
npm run build

# Start production server
npm run start

# Or export static files
npm run build && npm run export
```

### Environment Variables for Production

**Required**:

```bash
# Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_your-clerk-publishable-key

# Backend API
NEXT_PUBLIC_API_URL=https://your-backend-api.com
NEXT_PUBLIC_WS_URL=wss://your-backend-api.com  # if WebSocket enabled
```

**Optional**:

```bash
NEXT_PUBLIC_APP_NAME="Your App Name"
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
NEXT_PUBLIC_ENVIRONMENT=production
```

## 🔧 Customization

### Adding New Components

```typescript
// src/components/ui/new-component.tsx
import { cn } from '@/lib/utils'

interface NewComponentProps {
  className?: string
  children: React.ReactNode
}

export function NewComponent({ className, children }: NewComponentProps) {
  return (
    <div className={cn('base-styles', className)}>
      {children}
    </div>
  )
}
```

### Custom Hooks

```typescript
// src/hooks/use-custom-hook.ts
import { useState, useEffect } from "react";

export function useCustomHook() {
  const [state, setState] = useState(null);

  useEffect(() => {
    // Custom logic
  }, []);

  return { state, setState };
}
```

### Styling Components

```tsx
// Using Tailwind CSS classes
<div className="flex items-center justify-between p-4 bg-white dark:bg-gray-900 rounded-lg shadow-sm">
  <span className="text-gray-900 dark:text-gray-100">Content</span>
</div>;

// Using CSS modules (optional)
import styles from "./component.module.css";
<div className={styles.container}>Content</div>;
```

## 🐛 Troubleshooting

### Common Issues

**Backend Connection Issues**:

```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify environment variables
echo $NEXT_PUBLIC_API_URL
```

**Build Errors**:

```bash
# Clear Next.js cache
rm -rf .next

# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**TypeScript Errors**:

```bash
# Run type checking
npm run type-check

# Generate type definitions
npm run build
```

**WebSocket Connection Issues**:


```bash
# WebSocket not enabled in this configuration
# Messages use HTTP polling instead
```



### Debug Mode

```bash
# Enable debug logging
NEXT_PUBLIC_DEBUG=true npm run dev

# Check browser console for detailed logs
# Network tab shows API calls and responses
```

### Performance Issues

```bash
# Analyze bundle size
npm run analyze

# Check performance metrics
# Lighthouse audit in Chrome DevTools

# Monitor memory usage in React DevTools
```

## 🤝 Contributing

### Development Workflow

1. **Create Feature Branch**: `git checkout -b feature/awesome-feature`
2. **Make Changes**: Follow code style guidelines
3. **Run Tests**: `npm run test`
4. **Type Check**: `npm run type-check`
5. **Lint Code**: `npm run lint:fix`
6. **Commit Changes**: Use conventional commits
7. **Push & PR**: Create pull request

### Code Guidelines

- **TypeScript**: Use strict typing, avoid `any`
- **Components**: Functional components with hooks
- **Styling**: Tailwind CSS with semantic class names
- **Testing**: Write tests for new components
- **Accessibility**: Follow WCAG guidelines

### Commit Messages

```bash
# Use conventional commits
feat: add message search functionality
fix: resolve WebSocket connection issues
docs: update README with deployment guide
style: improve chat message styling
test: add unit tests for chat components
```

## 📊 Performance

### Core Web Vitals

The application is optimized for:

- **Largest Contentful Paint (LCP)**: < 2.5s
- **First Input Delay (FID)**: < 100ms
- **Cumulative Layout Shift (CLS)**: < 0.1

### Optimization Features

- **Code Splitting**: Automatic route-based splitting
- **Image Optimization**: Next.js Image component
- **Font Optimization**: Automatic font loading
- **Bundle Analysis**: Webpack bundle analyzer
- **Caching**: Static asset caching with CDN support

## 📚 API Integration

### Backend Endpoints

```typescript
// Chat API
POST /api/v1/chat/              // Send message
GET  /api/v1/chat/sessions      // List sessions
GET  /api/v1/chat/sessions/:id  // Get session
DELETE /api/v1/chat/sessions/:id // Delete session

// Health & Status
GET  /api/v1/health/            // Health check
```

### API Client Usage

```typescript
import { apiClient } from "@/lib/api";

// Send message
const response = await apiClient.post("/chat/", {
  message: "Hello",
  session_id: sessionId,
});

// Handle errors
try {
  const data = await apiClient.get("/chat/sessions");
} catch (error) {
  console.error("API Error:", error.message);
}
```

## 🔐 Security

### Best Practices

- **Environment Variables**: Never expose secrets in client code
- **API Security**: Validate all inputs, sanitize outputs
- **XSS Protection**: Use React's built-in XSS protection
- **Content Security Policy**: Configure CSP headers
- **HTTPS Only**: Always use HTTPS in production

### Security Headers

```javascript
// next.config.js
const securityHeaders = [
  {
    key: "X-DNS-Prefetch-Control",
    value: "on",
  },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  {
    key: "X-Frame-Options",
    value: "SAMEORIGIN",
  },
];
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🏢 Support

- **Documentation**: Check component storybook at `/storybook`
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Backend API**: See backend README for API documentation

---

**Built with ❤️ using [Next.js](https://nextjs.org/) and [TypeScript](https://www.typescriptlang.org/)**

**Generated by [cookiecutter-fastapi-nextjs-llm](https://github.com/your-org/cookiecutter-fastapi-nextjs-llm)**

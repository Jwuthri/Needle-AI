# Frontend User Sync Integration

## How It Works

When a user logs in with Clerk, they need to make an authenticated API call to the backend to sync their user data to the database.

## Implementation

### After Login - Call `/api/v1/auth/me`

In your frontend, after Clerk authentication completes, call the `/me` endpoint:

```typescript
// Example: src/hooks/useUserSync.ts
import { useAuth } from '@clerk/nextjs';
import { useEffect } from 'react';

export function useUserSync() {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    const syncUser = async () => {
      if (!isSignedIn) return;

      try {
        const token = await getToken();
        
        const response = await fetch('http://localhost:8000/api/v1/auth/me', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          console.log('User synced to database:', data);
        } else {
          console.error('Failed to sync user:', response.status);
        }
      } catch (error) {
        console.error('Error syncing user:', error);
      }
    };

    syncUser();
  }, [isSignedIn, getToken]);
}
```

### In Your Layout or App Component

```typescript
// src/app/layout.tsx
'use client';

import { useUserSync } from '@/hooks/useUserSync';

export default function RootLayout({ children }) {
  // This will automatically sync user after login
  useUserSync();

  return (
    <html>
      <body>{children}</body>
    </html>
  );
}
```

### Or After Sign-In Redirect

```typescript
// src/app/dashboard/page.tsx
'use client';

import { useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';

export default function Dashboard() {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    // Sync user when landing on dashboard after login
    if (isSignedIn) {
      getToken().then(token => {
        fetch('http://localhost:8000/api/v1/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
      });
    }
  }, [isSignedIn, getToken]);

  return <div>Dashboard</div>;
}
```

## What Happens

1. **User logs in** → Clerk authenticates, JWT token issued
2. **Frontend calls `/api/v1/auth/me`** → Includes JWT token in Authorization header
3. **Backend verifies token** → Extracts user info from Clerk JWT
4. **Backend syncs to database**:
   - If new user: Creates record in `users` table
   - If existing user: Updates `last_login_at` and any changed fields
5. **Backend returns user data** → Includes `database_synced: true` in metadata

## API Endpoint

**GET** `/api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <clerk-jwt-token>
```

**Response:**
```json
{
  "id": "user_xxx",
  "email": "user@example.com",
  "username": "user",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "image_url": "https://...",
  "created_at": "2025-10-11T...",
  "updated_at": "2025-10-11T...",
  "metadata": {
    "database_synced": true,
    "database_id": "user_xxx",
    "last_login": "2025-10-11T20:00:00"
  }
}
```

## Testing

1. **Start the backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Log in on frontend**

3. **Check logs** - You should see:
   ```
   [20:00:00] INFO     Synced user user_xxx (user@example.com) to database
   ```

4. **Verify in database**:
   ```sql
   SELECT id, email, last_login_at FROM users;
   ```

## Alternative: Automatic Sync on Any Endpoint

Any endpoint using `require_current_db_user` or `get_current_db_user` will automatically sync users:

```typescript
// Any authenticated API call will sync the user
await fetch('http://localhost:8000/api/v1/companies/', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

If the endpoint uses the database user dependencies, the user will be automatically synced on first call.

## Troubleshooting

### User Not Syncing

1. **Check Authorization Header**:
   ```javascript
   // Should be: Authorization: Bearer <token>
   const token = await getToken();
   console.log('Token:', token);
   ```

2. **Check Backend Logs**:
   ```bash
   # Look for sync messages
   grep "Synced user" backend/logs/app.log
   ```

3. **Check for Errors**:
   ```bash
   # Look for sync errors
   grep "Failed to sync user" backend/logs/app.log
   ```

### 401 Unauthorized

- Token not included in request
- Token expired
- Clerk configuration mismatch

### 500 Server Error

- Database connection issue
- Check backend logs for details

## Best Practices

1. **Sync on Login** - Call `/me` right after successful Clerk authentication
2. **Handle Errors** - Don't block user flow if sync fails
3. **Silent Sync** - Don't show loading states for sync
4. **Use Hook** - Create a reusable hook for all authenticated pages

## Complete Example

```typescript
// src/hooks/useUserSync.ts
import { useAuth } from '@clerk/nextjs';
import { useEffect, useState } from 'react';

interface SyncStatus {
  synced: boolean;
  error: string | null;
}

export function useUserSync(): SyncStatus {
  const { getToken, isSignedIn } = useAuth();
  const [status, setStatus] = useState<SyncStatus>({
    synced: false,
    error: null,
  });

  useEffect(() => {
    let mounted = true;

    const syncUser = async () => {
      if (!isSignedIn) {
        setStatus({ synced: false, error: null });
        return;
      }

      try {
        const token = await getToken();
        if (!token) return;

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        if (mounted) {
          if (response.ok) {
            setStatus({ synced: true, error: null });
          } else {
            setStatus({
              synced: false,
              error: `Sync failed: ${response.status}`,
            });
          }
        }
      } catch (error) {
        if (mounted) {
          setStatus({
            synced: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      }
    };

    syncUser();

    return () => {
      mounted = false;
    };
  }, [isSignedIn, getToken]);

  return status;
}
```

## Summary

✅ User sync happens automatically when calling authenticated endpoints  
✅ `/api/v1/auth/me` is the simplest endpoint to call after login  
✅ User is created on first call, updated on subsequent calls  
✅ Frontend doesn't need to handle user creation logic  
✅ Works seamlessly with existing Clerk authentication  

Call `/api/v1/auth/me` after Clerk login completes, and the user will be synced! 🎉


# Authentication System Documentation

## Overview

Molt Server implements a secure, multi-user authentication system using OAuth 2.0. This allows users to sign in with their Google or WeChat accounts while maintaining complete data isolation between users.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Molt Server                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Google    │  │   WeChat    │  │   Session Manager   │  │
│  │    OAuth    │  │    OAuth    │  │   (Secure Cookies)  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┴─────────────────────┘             │
│                           │                                   │
│                  ┌────────▼────────┐                         │
│                  │   Auth Module   │                         │
│                  │    (auth.py)    │                         │
│                  └────────┬────────┘                         │
│                           │                                   │
│         ┌─────────────────┼─────────────────┐                │
│         │                 │                 │                │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐          │
│  │    Users    │  │  Sessions   │  │   Settings  │          │
│  │   Table     │  │   Table     │  │   Table     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                           │                                   │
│                  ┌────────▼────────┐                         │
│                  │  SQLite (auth.db)│                        │
│                  └─────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Features

- ✅ **OAuth 2.0 Authentication**: Google and WeChat login
- ✅ **Session Management**: Secure, HTTP-only cookies with expiration
- ✅ **CSRF Protection**: Token-based protection for state-changing operations
- ✅ **Multi-User Support**: Complete data isolation per user
- ✅ **SQLite Database**: Lightweight, file-based storage
- ✅ **User Settings**: Per-user preferences (theme, language, timezone)

## Configuration

### Environment Variables

Set these environment variables before starting the server:

```bash
# Google OAuth 2.0
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export GOOGLE_REDIRECT_URI="http://your-domain.com/auth/google/callback"

# WeChat OAuth 2.0
export WECHAT_APP_ID="your-wechat-app-id"
export WECHAT_APP_SECRET="your-wechat-app-secret"
export WECHAT_REDIRECT_URI="http://your-domain.com/auth/wechat/callback"
```

### Obtaining OAuth Credentials

#### Google OAuth 2.0

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable "Google+ API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Choose "Web application"
6. Add authorized redirect URI: `http://your-domain.com/auth/google/callback`
7. Copy Client ID and Client Secret

#### WeChat OAuth 2.0

1. Go to [WeChat Open Platform](https://open.weixin.qq.com/)
2. Create a website application
3. Complete verification process
4. Get AppID and AppSecret from application details
5. Set redirect URI: `http://your-domain.com/auth/wechat/callback`

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    avatar TEXT,
    provider TEXT NOT NULL,          -- 'google' or 'wechat'
    provider_uid TEXT NOT NULL,       -- OAuth provider's user ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

### Sessions Table

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,       -- Secure random token
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### User Settings Table

```sql
CREATE TABLE user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    theme TEXT DEFAULT 'light',
    language TEXT DEFAULT 'en',
    timezone TEXT DEFAULT 'UTC',
    notifications_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## API Endpoints

### Authentication

#### GET /login
Displays the login page with OAuth provider buttons.

#### GET /auth/google/callback
Google OAuth callback handler.
- Query params: `code`, `state`
- Creates/updates user, sets session cookie
- Redirects to home page

#### GET /auth/wechat/callback
WeChat OAuth callback handler.
- Query params: `code`, `state`
- Creates/updates user, sets session cookie
- Redirects to home page

#### GET/POST /logout
Logs out the current user by deleting session.
- Clears session cookies
- Redirects to login page

#### GET /api/auth/me
Returns current user information.

**Response (authenticated):**
```json
{
  "authenticated": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "avatar": "https://...",
    "provider": "google"
  }
}
```

**Response (not authenticated):**
```json
{
  "authenticated": false
}
```

### Protected Endpoints

When authentication is enabled, these endpoints require a valid session:

- `GET /api/gtd/tasks` - Returns user's GTD tasks
- `POST /api/gtd/tasks` - Add new task
- `PUT /api/gtd/tasks` - Update tasks
- `DELETE /api/gtd/tasks` - Clear all tasks

Unauthenticated requests are redirected to `/login` (GET) or return 401 (POST/PUT/DELETE).

## Security Features

### Session Management

- **Secure Tokens**: 32-byte cryptographically secure random tokens
- **HTTP-Only Cookies**: Prevents XSS attacks from accessing session tokens
- **SameSite=Lax**: Protects against CSRF while allowing legitimate cross-site requests
- **Expiration**: Sessions expire after 24 hours (configurable)
- **Automatic Cleanup**: Expired sessions are removed on authentication operations

### CSRF Protection

- **State Parameter**: OAuth flows use state parameter to prevent CSRF
- **Token Validation**: State tokens expire after 10 minutes
- **HttpOnly Cookies**: Session cookies cannot be accessed by JavaScript

### Data Isolation

Each user's data is completely isolated:

```
data/
├── auth.db                    # Authentication database
└── users/
    ├── 1/                     # User ID 1
    │   ├── gtd/
    │   │   └── tasks.json
    │   └── files/
    └── 2/                     # User ID 2
        ├── gtd/
        │   └── tasks.json
        └── files/
```

## File Structure

```
molt_server/
├── auth.py                      # Main authentication module
├── database.py                  # Database layer (users, sessions, settings)
├── server_auth_integration.py   # Server integration patch
├── molt-server-unified.py       # Main server (patched for auth)
├── static/
│   └── auth/
│       └── login.html          # Login page with OAuth buttons
├── data/
│   ├── auth.db                 # SQLite database
│   └── users/                  # User-specific data directories
└── docs/
    └── AUTHENTICATION.md       # This documentation
```

## Usage

### Starting the Server

```bash
cd /home/admin/Code/molt_server
python3 molt-server-unified.py 8081
```

### Testing Authentication

1. Navigate to `http://localhost:8081/login`
2. Click "Continue with Google" or "Continue with WeChat"
3. Complete OAuth flow
4. You'll be redirected to home page with session cookie
5. Access `/api/auth/me` to verify authentication
6. Access `/gtd` to manage your tasks (isolated per user)

### Programmatic Usage

```python
from auth import (
    init_database,
    create_user,
    get_user_by_provider,
    create_session,
    get_session,
    logout,
    get_user_gtd_path,
    get_user_files_path
)

# Initialize database
init_database()

# Create session for user
session_token = create_session(user_id=1, ip_address='127.0.0.1')

# Get session (returns None if expired/invalid)
session = get_session(session_token)

# Get user-specific paths
gtd_path = get_user_gtd_path(user_id=1)
files_path = get_user_files_path(user_id=1)

# Logout (delete session)
logout(session_token)
```

## Multi-User GTD Integration

The GTD module automatically uses user-specific task files when authentication is enabled:

```python
# In GTD handler methods
def serve_gtd_tasks(self):
    # Automatically sets current_user_id from session
    user_id = getattr(self, 'current_user_id', None)
    tasks = load_tasks(user_id)  # Loads user-specific tasks
    # ...
```

Each user gets their own `tasks.json` file in their data directory.

## Troubleshooting

### "Authentication not configured" error

Ensure environment variables are set correctly:
```bash
echo $GOOGLE_CLIENT_ID
echo $WECHAT_APP_ID
```

### OAuth callback errors

1. Verify redirect URIs match exactly in OAuth provider settings
2. Check that the callback URL is accessible from the internet (for production)
3. Ensure state parameter is being passed correctly

### Session not persisting

1. Check that cookies are being set (inspect browser dev tools)
2. Verify `HttpOnly` and `SameSite` settings are compatible with your setup
3. Check session expiration time

### Database errors

1. Ensure `data/` directory is writable
2. Check SQLite database file permissions
3. Try deleting `auth.db` to reset (will lose all users/sessions)

## Security Best Practices

1. **Use HTTPS in production**: Always use HTTPS to encrypt cookies and OAuth tokens
2. **Secure environment variables**: Never commit OAuth secrets to version control
3. **Regular session cleanup**: The system automatically cleans expired sessions
4. **Monitor failed auth attempts**: Consider adding rate limiting for production
5. **Keep dependencies updated**: Regularly update `requests` and other dependencies

## Future Enhancements

- [ ] Add refresh token support for longer sessions
- [ ] Implement 2FA (TOTP)
- [ ] Add session management UI (view/revoke active sessions)
- [ ] Support additional OAuth providers (GitHub, Microsoft)
- [ ] Add role-based access control (RBAC)
- [ ] Implement audit logging for security events

## Support

For authentication-related issues or questions:
1. Check this documentation
2. Review the `auth.py` source code for implementation details
3. Check server logs for error messages
4. Verify OAuth provider configuration

---

**Last Updated**: 2026-03-02  
**Version**: 1.0.0  
**Author**: Molt Server Authentication Module

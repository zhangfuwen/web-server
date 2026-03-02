# Molt Server Authentication - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Configure OAuth (Required)

You need at least **one** OAuth provider configured. Google is easiest for testing.

#### Option A: Google OAuth (Recommended for Testing)

1. Go to https://console.cloud.google.com/apis/credentials
2. Create new project or select existing
3. Click "Create Credentials" → "OAuth 2.0 Client ID"
4. Select "Web application"
5. Add redirect URI: `http://localhost:8000/auth/google/callback` (for testing)
6. Copy Client ID and Secret

#### Option B: WeChat OAuth (Production)

1. Register at https://open.weixin.qq.com/
2. Complete business verification
3. Create website application
4. Wait for approval (1-3 days)
5. Get AppID and AppSecret

### Step 2: Create Configuration File

```bash
cd /home/admin/Code/molt_server/config
cp oauth.example oauth.env
```

Edit `oauth.env`:

```bash
# For Google OAuth testing:
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Generate session key:
python3 -c "import secrets; print(secrets.token_hex(32))"
# Copy output to:
SESSION_SECRET_KEY=your_generated_key_here
```

### Step 3: Load Configuration

```bash
cd /home/admin/Code/molt_server
source config/oauth.env
```

### Step 4: Start Server

```bash
python3 molt-server-unified-auth.py 8000
```

### Step 5: Test Login

1. Open http://localhost:8000/auth/login
2. Click "Continue with Google"
3. Sign in with your Google account
4. You'll be redirected to GTD app

## 📁 File Locations

```
molt_server/
├── auth.py                      # Authentication logic
├── database.py                  # Database layer
├── molt-server-unified-auth.py  # Main server (use this!)
├── molt-server-unified.py       # Original server (backup)
├── gtd.py                       # GTD module (updated for multi-user)
├── static/auth/login.html       # Login page
├── config/oauth.env             # Your OAuth config (create this!)
├── data/auth.db                 # User database (auto-created)
└── gtd/users/                   # Per-user GTD data
```

## 🔧 Common Issues

### "Authentication not available"
- Make sure you're running `molt-server-unified-auth.py` (not the old version)
- Check that `auth.py` and `database.py` exist
- Run: `pip install requests`

### OAuth callback error
- Verify redirect URI matches exactly (http vs https, port, path)
- For local testing use: `http://localhost:8000/auth/google/callback`
- For production use: `https://yourdomain.com/auth/google/callback`

### Session not working
- Check cookies are enabled in browser
- Ensure `SESSION_SECRET_KEY` is set
- Try clearing browser cookies

## 🎯 Next Steps

1. **Test with Google OAuth** - Easiest for development
2. **Set up HTTPS** - Required for production
3. **Configure WeChat OAuth** - For Chinese users
4. **Deploy to production** - See AUTHENTICATION.md

## 📚 Documentation

- **Full Guide**: `docs/AUTHENTICATION.md`
- **Config Template**: `config/oauth.example`
- **API Reference**: See AUTHENTICATION.md → API Endpoints

## 💡 Tips

- Keep `oauth.env` secure - never commit to git
- Use different OAuth apps for dev and production
- Backup `data/auth.db` regularly
- Test OAuth flow thoroughly before deploying

---

**Need help?** Check `docs/AUTHENTICATION.md` for detailed documentation.

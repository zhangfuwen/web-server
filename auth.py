#!/usr/bin/env python3
"""
Authentication module for Molt Server.
Implements Google OAuth 2.0 and WeChat OAuth 2.0 login flows.
"""

import os
import json
import secrets
import hashlib
import hmac
import base64
import time
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import requests

# Import database functions
from database import (
    init_database, create_user, get_user_by_provider, get_user_by_id,
    create_session, get_session, delete_session, delete_user_sessions,
    get_user_settings, update_user_settings, cleanup_expired_sessions
)

# Base directory of this module
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration - Load from environment variables
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')

WECHAT_APP_ID = os.environ.get('WECHAT_APP_ID', '')
WECHAT_APP_SECRET = os.environ.get('WECHAT_APP_SECRET', '')
WECHAT_REDIRECT_URI = os.environ.get('WECHAT_REDIRECT_URI', 'http://localhost:8000/auth/wechat/callback')

# Session configuration
SESSION_COOKIE_NAME = 'molt_session'
SESSION_EXPIRY_HOURS = 24
CSRF_COOKIE_NAME = 'molt_csrf'
CSRF_HEADER_NAME = 'X-CSRF-Token'

# OAuth state storage (in-memory for now, should use Redis in production)
_oauth_states = {}


class OAuthError(Exception):
    """OAuth authentication error."""
    pass


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, session_token: str) -> bool:
    """Validate CSRF token."""
    if not token or not session_token:
        return False
    # In a more secure implementation, store CSRF tokens per session
    # For now, we validate the token format
    return len(token) >= 32


def generate_oauth_state() -> str:
    """Generate OAuth state parameter for CSRF protection."""
    state = secrets.token_urlsafe(32)
    # Store with timestamp (expires in 10 minutes)
    _oauth_states[state] = {
        'created_at': time.time(),
        'expires_at': time.time() + 600
    }
    return state


def validate_oauth_state(state: str) -> bool:
    """Validate OAuth state parameter."""
    if state not in _oauth_states:
        return False
    
    state_data = _oauth_states[state]
    if time.time() > state_data['expires_at']:
        del _oauth_states[state]
        return False
    
    # Clean up after validation
    del _oauth_states[state]
    return True


def cleanup_oauth_states():
    """Clean up expired OAuth states."""
    now = time.time()
    expired = [s for s, data in _oauth_states.items() if now > data['expires_at']]
    for state in expired:
        del _oauth_states[state]


# ============================================================================
# Google OAuth 2.0
# ============================================================================

def get_google_auth_url(state: str) -> str:
    """Get Google OAuth authorization URL."""
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'offline',
        'prompt': 'consent'
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_google_code(code: str) -> Dict[str, Any]:
    """Exchange Google authorization code for tokens."""
    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': GOOGLE_REDIRECT_URI
    }
    
    response = requests.post(token_url, data=data, timeout=10)
    if response.status_code != 200:
        raise OAuthError(f"Google token exchange failed: {response.text}")
    
    return response.json()


def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """Get user info from Google."""
    userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(userinfo_url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise OAuthError(f"Google userinfo failed: {response.text}")
    
    return response.json()


# ============================================================================
# WeChat OAuth 2.0
# ============================================================================

def get_wechat_auth_url(state: str) -> str:
    """Get WeChat OAuth authorization URL (for website login)."""
    params = {
        'appid': WECHAT_APP_ID,
        'redirect_uri': WECHAT_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'snsapi_login',  # snsapi_login for website, snsapi_userinfo for mobile
        'state': state
    }
    return f"https://open.weixin.qq.com/connect/qrconnect?{urlencode(params)}"


def exchange_wechat_code(code: str) -> Dict[str, Any]:
    """Exchange WeChat authorization code for tokens."""
    token_url = 'https://api.weixin.qq.com/sns/oauth2/access_token'
    params = {
        'appid': WECHAT_APP_ID,
        'secret': WECHAT_APP_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    }
    
    response = requests.get(token_url, params=params, timeout=10)
    if response.status_code != 200:
        raise OAuthError(f"WeChat token exchange failed: {response.text}")
    
    result = response.json()
    if 'errcode' in result and result['errcode'] != 0:
        raise OAuthError(f"WeChat error: {result.get('errmsg', 'Unknown error')}")
    
    return result


def get_wechat_user_info(access_token: str, openid: str) -> Dict[str, Any]:
    """Get user info from WeChat."""
    userinfo_url = 'https://api.weixin.qq.com/sns/userinfo'
    params = {
        'access_token': access_token,
        'openid': openid,
        'lang': 'zh_CN'
    }
    
    response = requests.get(userinfo_url, params=params, timeout=10)
    if response.status_code != 200:
        raise OAuthError(f"WeChat userinfo failed: {response.text}")
    
    result = response.json()
    if 'errcode' in result and result['errcode'] != 0:
        raise OAuthError(f"WeChat error: {result.get('errmsg', 'Unknown error')}")
    
    return result


# ============================================================================
# User Authentication
# ============================================================================

def authenticate_or_create_user(provider: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """Authenticate existing user or create new user."""
    
    if provider == 'google':
        provider_uid = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0] if email else 'User')
        avatar = user_info.get('picture')
    elif provider == 'wechat':
        provider_uid = user_info.get('openid')
        email = f"wechat_{provider_uid}@wechat.local"  # WeChat doesn't provide email
        name = user_info.get('nickname', 'WeChat User')
        avatar = user_info.get('headimgurl')
    else:
        raise OAuthError(f"Unknown provider: {provider}")
    
    # Try to find existing user
    user = get_user_by_provider(provider, provider_uid)
    
    if user:
        # Update user info if changed
        update_user(user['id'], name=name, avatar=avatar)
        return user
    
    # Check if email already exists (for Google users who might have switched providers)
    if email and provider == 'google':
        existing_user = get_user_by_email(email)
        if existing_user:
            # Link this provider to existing account
            update_user(existing_user['id'], 
                       provider=provider, 
                       provider_uid=provider_uid,
                       name=name,
                       avatar=avatar)
            return existing_user
    
    # Create new user
    user = create_user(
        email=email,
        name=name,
        provider=provider,
        provider_uid=provider_uid,
        avatar=avatar
    )
    
    if not user:
        raise OAuthError("Failed to create user")
    
    return user


def create_user_session(user_id: int, ip_address: Optional[str] = None, 
                        user_agent: Optional[str] = None) -> str:
    """Create a session for authenticated user."""
    # Cleanup expired sessions periodically
    cleanup_expired_sessions()
    cleanup_oauth_states()
    
    return create_session(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_hours=SESSION_EXPIRY_HOURS
    )


def logout(session_token: str) -> bool:
    """Logout user by deleting session."""
    return delete_session(session_token)


# ============================================================================
# Request Handler Mixin
# ============================================================================

class AuthHandler:
    """Authentication handler mixin for HTTP request handlers."""
    
    def get_session_from_request(self) -> Optional[Dict]:
        """Extract and validate session from request cookies."""
        cookie_header = self.headers.get('Cookie', '')
        cookies = self.parse_cookies(cookie_header)
        
        session_token = cookies.get(SESSION_COOKIE_NAME)
        if not session_token:
            return None
        
        return get_session(session_token)
    
    def parse_cookies(self, cookie_header: str) -> Dict[str, str]:
        """Parse cookie header into dictionary."""
        cookies = {}
        if cookie_header:
            for cookie in cookie_header.split(';'):
                if '=' in cookie:
                    key, value = cookie.split('=', 1)
                    cookies[key.strip()] = value.strip()
        return cookies
    
    def require_auth(self) -> Optional[Dict]:
        """Require authentication for request. Returns user session or sends 401."""
        session = self.get_session_from_request()
        
        if not session:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }).encode('utf-8'))
            return None
        
        return session
    
    def get_csrf_token_from_request(self) -> Optional[str]:
        """Get CSRF token from request headers or body."""
        # Check header first
        token = self.headers.get(CSRF_HEADER_NAME)
        if token:
            return token
        
        # For POST requests, also check body
        if self.command == 'POST':
            content_type = self.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode('utf-8')
                    data = json.loads(body)
                    return data.get('_csrf')
                except:
                    pass
            elif 'application/x-www-form-urlencoded' in content_type:
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length).decode('utf-8')
                    params = parse_qs(body)
                    return params.get('_csrf', [None])[0]
                except:
                    pass
        
        return None
    
    def validate_csrf(self) -> bool:
        """Validate CSRF token. Returns True if valid, sends 403 if invalid."""
        session = self.get_session_from_request()
        if not session:
            return False
        
        csrf_token = self.get_csrf_token_from_request()
        if not validate_csrf_token(csrf_token, session['token']):
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': 'CSRF token invalid',
                'message': 'Invalid or missing CSRF token'
            }).encode('utf-8'))
            return False
        
        return True
    
    def set_session_cookie(self, session_token: str, secure: bool = False):
        """Set session cookie in response."""
        expires = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
        expires_str = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        cookie = f"{SESSION_COOKIE_NAME}={session_token}; Path=/; HttpOnly; SameSite=Lax; Expires={expires_str}"
        if secure:
            cookie += "; Secure"
        
        self.send_header('Set-Cookie', cookie)
    
    def set_csrf_cookie(self, csrf_token: str, secure: bool = False):
        """Set CSRF token cookie."""
        expires = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)
        expires_str = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        cookie = f"{CSRF_COOKIE_NAME}={csrf_token}; Path=/; SameSite=Strict; Expires={expires_str}"
        if secure:
            cookie += "; Secure"
        
        self.send_header('Set-Cookie', cookie)
    
    def clear_auth_cookies(self):
        """Clear authentication cookies (logout)."""
        # Set cookies to expire in the past
        expired = 'Thu, 01 Jan 1970 00:00:00 GMT'
        self.send_header('Set-Cookie', f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; Expires={expired}")
        self.send_header('Set-Cookie', f"{CSRF_COOKIE_NAME}=; Path=/; SameSite=Strict; Expires={expired}")
    
    def send_login_page(self):
        """Send the login page."""
        try:
            login_html_path = os.path.join(os.path.dirname(__file__), 'static', 'auth', 'login.html')
            if os.path.exists(login_html_path):
                with open(login_html_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Inject OAuth URLs
                google_state = generate_oauth_state()
                wechat_state = generate_oauth_state()
                
                google_url = get_google_auth_url(google_state)
                wechat_url = get_wechat_auth_url(wechat_state)
                
                content = content.replace('{{GOOGLE_OAUTH_URL}}', google_url)
                content = content.replace('{{WECHAT_OAUTH_URL}}', wechat_url)
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(500, "Login page not found")
        except Exception as e:
            self.send_error(500, f"Error serving login page: {str(e)}")
    
    def handle_google_callback(self, query_params: Dict):
        """Handle Google OAuth callback."""
        try:
            code = query_params.get('code', [None])[0]
            state = query_params.get('state', [None])[0]
            error = query_params.get('error', [None])[0]
            
            if error:
                raise OAuthError(f"Google OAuth error: {error}")
            
            if not code:
                raise OAuthError("No authorization code received")
            
            if not validate_oauth_state(state):
                raise OAuthError("Invalid OAuth state")
            
            # Exchange code for tokens
            token_response = exchange_google_code(code)
            access_token = token_response.get('access_token')
            
            if not access_token:
                raise OAuthError("No access token received")
            
            # Get user info
            user_info = get_google_user_info(access_token)
            
            # Authenticate or create user
            user = authenticate_or_create_user('google', user_info)
            
            # Create session
            ip_address = self.client_address[0] if hasattr(self, 'client_address') else None
            user_agent = self.headers.get('User-Agent', '')
            session_token = create_user_session(user['id'], ip_address, user_agent)
            
            # Generate CSRF token
            csrf_token = generate_csrf_token()
            
            # Redirect to home page with cookies
            self.send_response(302)
            self.set_session_cookie(session_token)
            self.set_csrf_cookie(csrf_token)
            self.send_header('Location', '/')
            self.end_headers()
            
        except OAuthError as e:
            self.send_error(400, str(e))
        except Exception as e:
            self.send_error(500, f"Google OAuth error: {str(e)}")
    
    def handle_wechat_callback(self, query_params: Dict):
        """Handle WeChat OAuth callback."""
        try:
            code = query_params.get('code', [None])[0]
            state = query_params.get('state', [None])[0]
            error = query_params.get('errcode', [None])[0]
            
            if error and error != '0':
                raise OAuthError(f"WeChat OAuth error: {error}")
            
            if not code:
                raise OAuthError("No authorization code received")
            
            if not validate_oauth_state(state):
                raise OAuthError("Invalid OAuth state")
            
            # Exchange code for tokens
            token_response = exchange_wechat_code(code)
            access_token = token_response.get('access_token')
            openid = token_response.get('openid')
            
            if not access_token or not openid:
                raise OAuthError("No access token or openid received")
            
            # Get user info
            user_info = get_wechat_user_info(access_token, openid)
            
            # Authenticate or create user
            user = authenticate_or_create_user('wechat', user_info)
            
            # Create session
            ip_address = self.client_address[0] if hasattr(self, 'client_address') else None
            user_agent = self.headers.get('User-Agent', '')
            session_token = create_user_session(user['id'], ip_address, user_agent)
            
            # Generate CSRF token
            csrf_token = generate_csrf_token()
            
            # Redirect to home page with cookies
            self.send_response(302)
            self.set_session_cookie(session_token)
            self.set_csrf_cookie(csrf_token)
            self.send_header('Location', '/')
            self.end_headers()
            
        except OAuthError as e:
            self.send_error(400, str(e))
        except Exception as e:
            self.send_error(500, f"WeChat OAuth error: {str(e)}")
    
    def handle_logout(self):
        """Handle logout request."""
        session = self.get_session_from_request()
        
        if session:
            logout(session['token'])
        
        self.send_response(302)
        self.clear_auth_cookies()
        self.send_header('Location', '/login')
        self.end_headers()


# ============================================================================
# User Data Isolation Helpers
# ============================================================================

def get_user_data_path(user_id: int, subpath: str = '') -> str:
    """Get user-specific data path for file isolation."""
    base_data_dir = os.path.join(os.path.dirname(__file__), 'data', 'users', str(user_id))
    os.makedirs(base_data_dir, exist_ok=True)
    
    if subpath:
        return os.path.join(base_data_dir, subpath)
    return base_data_dir


def get_user_gtd_path(user_id: int) -> str:
    """Get user-specific GTD tasks file path."""
    gtd_dir = get_user_data_path(user_id, 'gtd')
    os.makedirs(gtd_dir, exist_ok=True)
    return os.path.join(gtd_dir, 'tasks.json')


def get_user_files_path(user_id: int, subpath: str = '') -> str:
    """Get user-specific files directory path."""
    files_dir = get_user_data_path(user_id, 'files')
    os.makedirs(files_dir, exist_ok=True)
    
    if subpath:
        full_path = os.path.join(files_dir, subpath)
        # Security: prevent directory traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(files_dir)):
            raise ValueError("Invalid path")
        return full_path
    return files_dir


# Initialize database on module load
init_database()
print("Auth module loaded successfully")

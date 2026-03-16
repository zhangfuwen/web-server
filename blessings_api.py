#!/usr/bin/env python3
"""
Blessings API Handler - 祝福/禅语 API 接口

RESTful API endpoints:
- GET    /api/blessings              - List blessings (with pagination & filters)
- POST   /api/blessings              - Create new blessing
- GET    /api/blessings/{id}         - Get single blessing
- PUT    /api/blessings/{id}         - Update blessing
- DELETE /api/blessings/{id}         - Delete blessing
- GET    /api/blessings/{id}/comments - List comments
- POST   /api/blessings/{id}/comments - Add comment
- POST   /api/blessings/{id}/like    - Toggle like
- POST   /api/blessings/{id}/favorite - Toggle favorite
- GET    /api/blessings/stats        - Get statistics
"""

import json
import re
from urllib.parse import parse_qs, urlparse
from typing import Optional, Dict, Any
import logging

import blessings_db as db

logger = logging.getLogger(__name__)


class BlessingsAPIHandler:
    """Handler for blessings API endpoints"""
    
    def __init__(self):
        pass
    
    def handle_request(self, handler, method: str, path: str) -> bool:
        """
        Handle blessings API request
        
        Args:
            handler: HTTP request handler instance
            method: HTTP method (GET, POST, PUT, DELETE)
            path: URL path
            
        Returns:
            True if handled, False otherwise
        """
        
        # Match API routes
        if path == '/api/blessings':
            if method == 'GET':
                return self.list_blessings(handler)
            elif method == 'POST':
                return self.create_blessing(handler)
                
        elif path == '/api/blessings/stats':
            if method == 'GET':
                return self.get_statistics(handler)
        
        # Match /api/blessings/{id} routes
        match = re.match(r'^/api/blessings/(\d+)(?:/(comments|like|favorite))?$', path)
        if match:
            blessing_id = int(match.group(1))
            subpath = match.group(2)
            
            if subpath is None:
                # /api/blessings/{id}
                if method == 'GET':
                    return self.get_blessing(handler, blessing_id)
                elif method == 'PUT':
                    return self.update_blessing(handler, blessing_id)
                elif method == 'DELETE':
                    return self.delete_blessing(handler, blessing_id)
                    
            elif subpath == 'comments':
                # /api/blessings/{id}/comments
                if method == 'GET':
                    return self.list_comments(handler, blessing_id)
                elif method == 'POST':
                    return self.create_comment(handler, blessing_id)
                    
            elif subpath == 'like':
                # /api/blessings/{id}/like
                if method == 'POST':
                    return self.toggle_like(handler, blessing_id)
                    
            elif subpath == 'favorite':
                # /api/blessings/{id}/favorite
                if method == 'POST':
                    return self.toggle_favorite(handler, blessing_id)
        
        return False
    
    # ============== Blessing CRUD ==============
    
    def list_blessings(self, handler) -> bool:
        """GET /api/blessings - List blessings with pagination"""
        try:
            # Parse query parameters
            parsed = urlparse(handler.path)
            params = parse_qs(parsed.query)
            
            limit = int(params.get('limit', [20])[0])
            offset = int(params.get('offset', [0])[0])
            category = params.get('category', [None])[0]
            user_id = params.get('user_id', [None])[0]
            
            # Enforce reasonable limits
            limit = min(limit, 100)
            
            blessings = db.get_blessings(
                limit=limit,
                offset=offset,
                category=category,
                user_id=user_id
            )
            
            # Get user interactions if user_id provided
            if user_id and blessings:
                blessing_ids = [b['id'] for b in blessings]
                interactions = db.get_user_interactions(user_id, blessing_ids)
                for blessing in blessings:
                    user_interactions = interactions.get(blessing['id'], {})
                    blessing['is_liked'] = user_interactions.get('is_liked', False)
                    blessing['is_favorited'] = user_interactions.get('is_favorited', False)
            
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': blessings,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'count': len(blessings)
                }
            }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error listing blessings: {e}")
            handler.send_error(500, f"Error listing blessings: {str(e)}")
            return True
    
    def get_blessing(self, handler, blessing_id: int) -> bool:
        """GET /api/blessings/{id} - Get single blessing"""
        try:
            blessing = db.get_blessing_by_id(blessing_id)
            
            if not blessing:
                handler.send_response(404)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Blessing not found'
                }).encode('utf-8'))
                return True
            
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': blessing
            }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error getting blessing: {e}")
            handler.send_error(500, f"Error getting blessing: {str(e)}")
            return True
    
    def create_blessing(self, handler) -> bool:
        """POST /api/blessings - Create new blessing"""
        try:
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Validate required fields
            required = ['text', 'user_id', 'user_name']
            for field in required:
                if field not in data:
                    handler.send_response(400)
                    handler.send_header('Content-Type', 'application/json')
                    handler.end_headers()
                    handler.wfile.write(json.dumps({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }).encode('utf-8'))
                    return True
            
            blessing = db.create_blessing(
                user_id=data['user_id'],
                user_name=data['user_name'],
                text=data['text'],
                source=data.get('source', ''),
                practice=data.get('practice', ''),
                category=data.get('category', '禅宗'),
                font_path=data.get('font_path', ''),
                bg_path=data.get('bg_path', '')
            )
            
            handler.send_response(201)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': blessing
            }).encode('utf-8'))
            return True
            
        except json.JSONDecodeError:
            handler.send_response(400)
            handler.send_header('Content-Type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': False,
                'error': 'Invalid JSON'
            }).encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Error creating blessing: {e}")
            handler.send_error(500, f"Error creating blessing: {str(e)}")
            return True
    
    def update_blessing(self, handler, blessing_id: int) -> bool:
        """PUT /api/blessings/{id} - Update blessing"""
        try:
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Validate user_id
            if 'user_id' not in data:
                handler.send_response(400)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing user_id'
                }).encode('utf-8'))
                return True
            
            blessing = db.update_blessing(
                blessing_id=blessing_id,
                user_id=data['user_id'],
                text=data.get('text'),
                source=data.get('source'),
                practice=data.get('practice'),
                category=data.get('category')
            )
            
            if blessing:
                handler.send_response(200)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': True,
                    'data': blessing
                }).encode('utf-8'))
            else:
                handler.send_response(403)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Not authorized or blessing not found'
                }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error updating blessing: {e}")
            handler.send_error(500, f"Error updating blessing: {str(e)}")
            return True
    
    def delete_blessing(self, handler, blessing_id: int) -> bool:
        """DELETE /api/blessings/{id} - Delete blessing"""
        try:
            # Get user_id from query or body
            content_length = int(handler.headers.get('Content-Length', 0))
            if content_length > 0:
                body = handler.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
                user_id = data.get('user_id')
            else:
                parsed = urlparse(handler.path)
                params = parse_qs(parsed.query)
                user_id = params.get('user_id', [None])[0]
            
            if not user_id:
                handler.send_response(400)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing user_id'
                }).encode('utf-8'))
                return True
            
            success = db.delete_blessing(blessing_id, user_id)
            
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': success,
                'message': 'Blessing deleted' if success else 'Delete failed'
            }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error deleting blessing: {e}")
            handler.send_error(500, f"Error deleting blessing: {str(e)}")
            return True
    
    # ============== Comments ==============
    
    def list_comments(self, handler, blessing_id: int) -> bool:
        """GET /api/blessings/{id}/comments - List comments"""
        try:
            parsed = urlparse(handler.path)
            params = parse_qs(parsed.query)
            
            limit = int(params.get('limit', [50])[0])
            offset = int(params.get('offset', [0])[0])
            
            comments = db.get_comments_by_blessing(blessing_id, limit, offset)
            
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': comments,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'count': len(comments)
                }
            }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error listing comments: {e}")
            handler.send_error(500, f"Error listing comments: {str(e)}")
            return True
    
    def create_comment(self, handler, blessing_id: int) -> bool:
        """POST /api/blessings/{id}/comments - Add comment"""
        try:
            # Verify blessing exists
            blessing = db.get_blessing_by_id(blessing_id)
            if not blessing:
                handler.send_response(404)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Blessing not found'
                }).encode('utf-8'))
                return True
            
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            # Validate required fields
            if not all(k in data for k in ['content', 'user_id', 'user_name']):
                handler.send_response(400)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing required fields: content, user_id, user_name'
                }).encode('utf-8'))
                return True
            
            comment = db.create_comment(
                blessing_id=blessing_id,
                user_id=data['user_id'],
                user_name=data['user_name'],
                content=data['content'],
                parent_id=data.get('parent_id')
            )
            
            handler.send_response(201)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': comment
            }).encode('utf-8'))
            return True
            
        except json.JSONDecodeError:
            handler.send_response(400)
            handler.send_header('Content-Type', 'application/json')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': False,
                'error': 'Invalid JSON'
            }).encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Error creating comment: {e}")
            handler.send_error(500, f"Error creating comment: {str(e)}")
            return True
    
    # ============== Interactions ==============
    
    def toggle_like(self, handler, blessing_id: int) -> bool:
        """POST /api/blessings/{id}/like - Toggle like"""
        try:
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            user_id = data.get('user_id')
            if not user_id:
                handler.send_response(400)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing user_id'
                }).encode('utf-8'))
                return True
            
            result = db.toggle_interaction(user_id, blessing_id, 'like')
            
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': result
            }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error toggling like: {e}")
            handler.send_error(500, f"Error toggling like: {str(e)}")
            return True
    
    def toggle_favorite(self, handler, blessing_id: int) -> bool:
        """POST /api/blessings/{id}/favorite - Toggle favorite"""
        try:
            content_length = int(handler.headers.get('Content-Length', 0))
            body = handler.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            user_id = data.get('user_id')
            if not user_id:
                handler.send_response(400)
                handler.send_header('Content-Type', 'application/json')
                handler.end_headers()
                handler.wfile.write(json.dumps({
                    'success': False,
                    'error': 'Missing user_id'
                }).encode('utf-8'))
                return True
            
            result = db.toggle_interaction(user_id, blessing_id, 'favorite')
            
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': result
            }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error toggling favorite: {e}")
            handler.send_error(500, f"Error toggling favorite: {str(e)}")
            return True
    
    # ============== Statistics ==============
    
    def get_statistics(self, handler) -> bool:
        """GET /api/blessings/stats - Get statistics"""
        try:
            stats = db.get_blessing_statistics()
            
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(json.dumps({
                'success': True,
                'data': stats
            }).encode('utf-8'))
            return True
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            handler.send_error(500, f"Error getting statistics: {str(e)}")
            return True

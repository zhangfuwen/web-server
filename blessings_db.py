#!/usr/bin/env python3
"""
Blessings Database Module - 祝福/禅语数据库管理

Supports:
- Blessings CRUD (发布、查看、编辑、删除祝福/禅语)
- Comments (评论功能)
- Interactions (点赞、收藏)
- Categories (分类：禅宗、儒家、道家、佛经等)
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Database path - store in /var/www/html/data/ for persistence
DB_PATH = os.path.join(os.getenv('WEB_ROOT', '/var/www/html'), 'data', 'blessings.db')

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_db_connection():
    """Get database connection with context manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize blessings database with schema"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create blessings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blessings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT,
                practice TEXT,
                category TEXT DEFAULT '禅宗',
                like_count INTEGER DEFAULT 0,
                favorite_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0
            )
        ''')
        
        # Create comments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                blessing_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                content TEXT NOT NULL,
                parent_id INTEGER,
                like_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY (blessing_id) REFERENCES blessings(id) ON DELETE CASCADE
            )
        ''')
        
        # Create interactions table (for tracking user likes/favorites)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blessing_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                blessing_id INTEGER NOT NULL,
                interaction_type TEXT NOT NULL,  -- 'like' or 'favorite'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, blessing_id, interaction_type),
                FOREIGN KEY (blessing_id) REFERENCES blessings(id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_blessings_category ON blessings(category)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_blessings_created_at ON blessings(created_at DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_blessings_user_id ON blessings(user_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_comments_blessing_id ON comments(blessing_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_interactions_blessing_id ON blessing_interactions(blessing_id)
        ''')
        
        conn.commit()
        logger.info("Blessings database initialized successfully")


def create_blessing(user_id: str, user_name: str, text: str, 
                   source: str = "", practice: str = "", category: str = "禅宗") -> Optional[Dict]:
    """Create a new blessing"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO blessings (user_id, user_name, text, source, practice, category)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, user_name, text, source, practice, category))
        conn.commit()
        
        blessing_id = cursor.lastrowid
        return get_blessing_by_id(blessing_id)


def get_blessing_by_id(blessing_id: int) -> Optional[Dict]:
    """Get a single blessing by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM blessings WHERE id = ? AND is_deleted = 0
        ''', (blessing_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_blessings(limit: int = 20, offset: int = 0, category: str = None, 
                  user_id: str = None) -> List[Dict]:
    """Get blessings list with pagination and filters"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM blessings WHERE is_deleted = 0
        '''
        params = []
        
        if category and category != "全部":
            query += ' AND category = ?'
            params.append(category)
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_blessing(blessing_id: int, user_id: str, 
                   text: str = None, source: str = None, 
                   practice: str = None, category: str = None) -> Optional[Dict]:
    """Update a blessing (owner only)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Build dynamic update query
        updates = []
        params = []
        
        if text is not None:
            updates.append('text = ?')
            params.append(text)
        if source is not None:
            updates.append('source = ?')
            params.append(source)
        if practice is not None:
            updates.append('practice = ?')
            params.append(practice)
        if category is not None:
            updates.append('category = ?')
            params.append(category)
        
        if not updates:
            return get_blessing_by_id(blessing_id)
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.extend([blessing_id, user_id])
        
        query = f'''
            UPDATE blessings 
            SET {', '.join(updates)}
            WHERE id = ? AND user_id = ? AND is_deleted = 0
        '''
        
        cursor.execute(query, params)
        conn.commit()
        
        if cursor.rowcount > 0:
            return get_blessing_by_id(blessing_id)
        return None


def delete_blessing(blessing_id: int, user_id: str) -> bool:
    """Soft delete a blessing (owner only)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE blessings 
            SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (blessing_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ============== Comments Functions ==============

def create_comment(blessing_id: int, user_id: str, user_name: str, 
                  content: str, parent_id: int = None) -> Optional[Dict]:
    """Create a new comment"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO comments (blessing_id, user_id, user_name, content, parent_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (blessing_id, user_id, user_name, content, parent_id))
        conn.commit()
        
        comment_id = cursor.lastrowid
        return get_comment_by_id(comment_id)


def get_comment_by_id(comment_id: int) -> Optional[Dict]:
    """Get a single comment by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM comments WHERE id = ? AND is_deleted = 0
        ''', (comment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_comments_by_blessing(blessing_id: int, limit: int = 50, offset: int = 0) -> List[Dict]:
    """Get all comments for a blessing"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM comments 
            WHERE blessing_id = ? AND is_deleted = 0
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
        ''', (blessing_id, limit, offset))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_comment(comment_id: int, user_id: str) -> bool:
    """Soft delete a comment (owner only)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE comments 
            SET is_deleted = 1
            WHERE id = ? AND user_id = ?
        ''', (comment_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# ============== Interactions Functions ==============

def toggle_interaction(user_id: str, blessing_id: int, interaction_type: str) -> Dict:
    """Toggle like or favorite (returns new state)"""
    if interaction_type not in ['like', 'favorite']:
        raise ValueError("Invalid interaction type")
    
    count_field = f"{interaction_type}_count"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if interaction exists
        cursor.execute('''
            SELECT id FROM blessing_interactions 
            WHERE user_id = ? AND blessing_id = ? AND interaction_type = ?
        ''', (user_id, blessing_id, interaction_type))
        
        existing = cursor.fetchone()
        
        if existing:
            # Remove interaction (unlike/unfavorite)
            cursor.execute('''
                DELETE FROM blessing_interactions 
                WHERE user_id = ? AND blessing_id = ? AND interaction_type = ?
            ''', (user_id, blessing_id, interaction_type))
            
            cursor.execute(f'''
                UPDATE blessings SET {count_field} = MAX(0, {count_field} - 1)
                WHERE id = ?
            ''', (blessing_id,))
            
            conn.commit()
            return {'active': False, 'count': max(0, get_blessing_by_id(blessing_id)[count_field] - 1)}
        else:
            # Add interaction (like/favorite)
            cursor.execute('''
                INSERT OR REPLACE INTO blessing_interactions (user_id, blessing_id, interaction_type)
                VALUES (?, ?, ?)
            ''', (user_id, blessing_id, interaction_type))
            
            cursor.execute(f'''
                UPDATE blessings SET {count_field} = {count_field} + 1
                WHERE id = ?
            ''', (blessing_id,))
            
            conn.commit()
            blessing = get_blessing_by_id(blessing_id)
            return {'active': True, 'count': blessing[count_field]}


def get_user_interactions(user_id: str, blessing_ids: List[int]) -> Dict[int, Dict]:
    """Get user's interactions for multiple blessings"""
    interactions = {}
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for blessing_id in blessing_ids:
            cursor.execute('''
                SELECT interaction_type FROM blessing_interactions 
                WHERE user_id = ? AND blessing_id = ?
            ''', (user_id, blessing_id))
            
            rows = cursor.fetchall()
            interactions[blessing_id] = {
                'is_liked': any(row['interaction_type'] == 'like' for row in rows),
                'is_favorited': any(row['interaction_type'] == 'favorite' for row in rows)
            }
    
    return interactions


# ============== Statistics Functions ==============

def get_blessing_statistics() -> Dict:
    """Get overall statistics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Total blessings
        cursor.execute('SELECT COUNT(*) as count FROM blessings WHERE is_deleted = 0')
        stats['total_blessings'] = cursor.fetchone()['count']
        
        # Total comments
        cursor.execute('SELECT COUNT(*) as count FROM comments WHERE is_deleted = 0')
        stats['total_comments'] = cursor.fetchone()['count']
        
        # Blessings by category
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM blessings WHERE is_deleted = 0 
            GROUP BY category
        ''')
        stats['by_category'] = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Top blessings by likes
        cursor.execute('''
            SELECT id, text, like_count FROM blessings 
            WHERE is_deleted = 0 
            ORDER BY like_count DESC 
            LIMIT 5
        ''')
        stats['top_liked'] = [dict(row) for row in cursor.fetchall()]
        
        return stats


def seed_initial_blessings():
    """Seed initial blessings from the Android app"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if already seeded
        cursor.execute('SELECT COUNT(*) as count FROM blessings')
        if cursor.fetchone()['count'] > 0:
            logger.info("Blessings already seeded, skipping")
            return
        
        initial_blessings = [
            ("心本无生因境有，境若无时心亦无。", "《楞严经》", "心随境转是凡夫，境随心转是圣贤。今日练习：观察一个升起的念头，不跟随，不压抑，只是看着它来去。", "禅宗"),
            ("应无所住而生其心。", "《金刚经》", "不执着于任何事物，心才能自由。今日练习：做一件事时，全然投入；做完后，全然放下。", "禅宗"),
            ("一切有为法，如梦幻泡影，如露亦如电，应作如是观。", "《金刚经》", "世间万物皆无常，如露如电。今日练习：当烦恼生起时，默念'这也是无常的'，观察它的变化。", "禅宗"),
            ("菩提本无树，明镜亦非台。本来无一物，何处惹尘埃。", "六祖慧能", "自性本净，无需外求。今日练习：静坐五分钟，问自己'正在烦恼的是谁？'", "禅宗"),
            ("行到水穷处，坐看云起时。", "王维", "绝境处自有转机。今日练习：遇到困难时，停下来，深呼吸三次，再问'还有另一种可能吗？'", "禅宗"),
            ("宠辱不惊，看庭前花开花落；去留无意，望天上云卷云舒。", "陈继儒", "得失随缘，心无增减。今日练习：今天遇到赞美或批评时，都当作耳边风。", "禅宗"),
            ("知止而后有定，定而后能静，静而后能安，安而后能虑，虑而后能得。", "《大学》", "知止是智慧的第一步。今日练习：在说话或行动前，停顿三秒，问'这是必要的吗？'", "儒家"),
            ("上善若水，水善利万物而不争。", "《道德经》", "柔能克刚，不争而胜。今日练习：今天遇到冲突时，尝试像水一样，绕行而不硬碰。", "道家"),
            ("制心一处，无事不办。", "佛经", "专注的力量无穷。今日练习：选择一件事，用 100% 的注意力完成它。", "佛经"),
            ("日日是好日。", "禅宗公案", "好坏皆由心生。今日练习：无论今天发生什么，睡前都说'今天是好日'。", "禅宗"),
        ]
        
        for text, source, practice, category in initial_blessings:
            cursor.execute('''
                INSERT INTO blessings (user_id, user_name, text, source, practice, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('system', '系统', text, source, practice, category))
        
        conn.commit()
        logger.info(f"Seeded {len(initial_blessings)} initial blessings")


if __name__ == '__main__':
    # Test the module
    init_database()
    seed_initial_blessings()
    
    # Test get blessings
    blessings = get_blessings(limit=5)
    print(f"Loaded {len(blessings)} blessings")
    for b in blessings:
        print(f"  - {b['text'][:30]}... ({b['category']})")

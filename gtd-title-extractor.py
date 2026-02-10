#!/usr/bin/env python3
"""
GTD Title Extractor - Extract clean titles from URLs for GTD task management
"""

import requests
from bs4 import BeautifulSoup
import re
import sys

def extract_clean_title(url):
    """
    Extract and clean title from a URL
    Returns: Clean title string or None if failed
    """
    try:
        # Add headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the page
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to get title from <title> tag
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        else:
            # Try meta og:title
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content'].strip()
            else:
                # Try h1 tag
                h1_tag = soup.find('h1')
                if h1_tag and h1_tag.string:
                    title = h1_tag.string.strip()
                else:
                    # Fallback to URL path
                    title = url.split('/')[-1] or url
        
        # Clean the title - remove common website suffixes and prefixes
        cleaned_title = clean_title(title)
        return cleaned_title
        
    except Exception as e:
        print(f"Error extracting title from {url}: {e}", file=sys.stderr)
        return None

def clean_title(title):
    """
    Clean title by removing common website suffixes, prefixes, and patterns
    """
    if not title:
        return title
    
    original_title = title
    
    # Common patterns to remove (prefixes and suffixes)
    patterns = [
        # Remove prefixes like "GitHub - ", "YouTube - ", etc.
        r'^[A-Za-z\s]+[-|–]\s*',  
        # Remove suffixes like " - GitHub", " | SiteName", etc.
        r'\s*[-|–]\s*[A-Za-z\s]+$',  
        r'\s*\|.*$',                  
        r'\s*».*$',                   
        r'\s*•.*$',                   
        r'\s*—.*$',                   
        r'\s*—\s*[A-Za-z\s]+$',      
        # Remove leading/trailing whitespace
        r'^\s*',                      
        r'\s*$',                      
    ]
    
    cleaned = title
    
    # Apply each pattern
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned)
    
    # If after cleaning we get an empty string or just whitespace, return original
    if not cleaned.strip():
        return original_title
    
    # Additional cleanup for common cases
    cleaned = cleaned.strip()
    
    # Handle GitHub specifically: "repo/name: description" is usually what we want
    if 'github.com' in original_title.lower():
        # If it starts with "GitHub - " and has a colon, keep everything after "GitHub - "
        github_match = re.match(r'^GitHub\s*[-|–]\s*(.+)$', original_title, re.IGNORECASE)
        if github_match:
            potential_clean = github_match.group(1)
            # If the potential clean version looks reasonable, use it
            if len(potential_clean) > 5 and ':' in potential_clean:
                cleaned = potential_clean
    
    # Handle YouTube specifically
    if 'youtube.com' in original_title.lower() or 'youtu.be' in original_title.lower():
        youtube_match = re.match(r'^(.+?)\s*[-|–]\s*YouTube$', original_title, re.IGNORECASE)
        if youtube_match:
            cleaned = youtube_match.group(1)
    
    return cleaned if cleaned.strip() else original_title

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 gtd-title-extractor.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    title = extract_clean_title(url)
    if title:
        print(title)
    else:
        print(f"Could not extract title from: {url}")
        sys.exit(1)
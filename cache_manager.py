#!/usr/bin/env python3
"""
Cache Manager Module for Sports Monitor

Implements a cache system with expiry timestamps to prevent redundant fetches.
Provides functions for caching sports data with configurable TTL based on data type.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


# Constants
MODULE_DIR = Path(__file__).parent
CACHE_DIR = MODULE_DIR / "cache"
CACHE_FILE_PATH = CACHE_DIR / "freshness_cache.json"

# TTL (Time To Live) in hours for different data types
TTL_HOURS = {
    'live_scores': 1,      # Live scores expire quickly
    'schedule': 24,        # Schedules are stable for a day
    'standings': 6,        # Standings change moderately
    'default': 6           # Default TTL for unknown types
}


def _load_cache() -> Dict[str, Any]:
    """
    Load cache from JSON file.
    
    Returns:
        Dict containing cached entries, or empty dict if file doesn't exist
    """
    if not CACHE_FILE_PATH.exists():
        return {}
    
    try:
        with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_cache(cache_data: Dict[str, Any]) -> None:
    """
    Save cache to JSON file.
    
    Args:
        cache_data: Dict containing cache entries to save
    """
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)


def _get_cache_key(sport_key: str, data_type: str) -> str:
    """
    Generate a consistent cache key for a sport and data type.
    
    Args:
        sport_key: Sport identifier (e.g., 'nba', 'f1')
        data_type: Type of data (e.g., 'live_scores', 'schedule')
    
    Returns:
        Cache key string in format "sport_key:data_type"
    """
    return f"{sport_key}:{data_type}"


def get_ttl_hours(data_type: str) -> int:
    """
    Get TTL in hours for a specific data type.
    
    Args:
        data_type: Type of data (e.g., 'live_scores', 'schedule')
    
    Returns:
        TTL in hours
    """
    return TTL_HOURS.get(data_type, TTL_HOURS['default'])


def is_expired(cache_entry: Dict[str, Any]) -> bool:
    """
    Check if a cache entry has expired.
    
    Args:
        cache_entry: Cache entry dict with 'expires_at' field
    
    Returns:
        True if expired, False if still valid
    """
    if not cache_entry or 'expires_at' not in cache_entry:
        return True
    
    try:
        expires_at = datetime.fromisoformat(cache_entry['expires_at'])
        return datetime.now(expires_at.tzinfo) > expires_at
    except (ValueError, TypeError):
        return True


def get_cached(sport_key: str, data_type: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached data if it exists and is not expired.
    
    Args:
        sport_key: Sport identifier (e.g., 'nba', 'f1')
        data_type: Type of data (e.g., 'live_scores', 'schedule')
    
    Returns:
        Cached data dict if valid, None if expired or missing
    """
    cache = _load_cache()
    cache_key = _get_cache_key(sport_key, data_type)
    
    if cache_key not in cache:
        return None
    
    cache_entry = cache[cache_key]
    
    if is_expired(cache_entry):
        return None
    
    return cache_entry.get('data')


def set_cached(sport_key: str, data_type: str, data: Dict[str, Any], 
               ttl_hours: Optional[int] = None,
               source_urls: Optional[list] = None,
               confidence: Optional[int] = None) -> None:
    """
    Store data in cache with timestamp and expiry.
    
    Args:
        sport_key: Sport identifier (e.g., 'nba', 'f1')
        data_type: Type of data (e.g., 'live_scores', 'schedule')
        data: Data to cache
        ttl_hours: TTL in hours (optional, auto-calculated from data_type if not provided)
        source_urls: List of source URLs used (optional)
        confidence: Confidence score 0-100 (optional)
    """
    if ttl_hours is None:
        ttl_hours = get_ttl_hours(data_type)
    
    cache = _load_cache()
    cache_key = _get_cache_key(sport_key, data_type)
    
    now = datetime.now()
    expires_at = now + timedelta(hours=ttl_hours)
    
    cache_entry = {
        'data': data,
        'fetched_at': now.isoformat(),
        'expires_at': expires_at.isoformat(),
        'source_urls': source_urls or [],
        'confidence': confidence or 0
    }
    
    cache[cache_key] = cache_entry
    _save_cache(cache)


def cleanup() -> Dict[str, Any]:
    """
    Remove expired entries from cache.
    
    Returns:
        Dict with cleanup stats (removed_count, remaining_count)
    """
    cache = _load_cache()
    original_count = len(cache)
    
    # Filter out expired entries
    cleaned_cache = {
        key: entry for key, entry in cache.items()
        if not is_expired(entry)
    }
    
    removed_count = original_count - len(cleaned_cache)
    
    if removed_count > 0:
        _save_cache(cleaned_cache)
    
    return {
        'removed_count': removed_count,
        'remaining_count': len(cleaned_cache),
        'original_count': original_count
    }


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Dict with total_entries, expired_count, oldest_entry, newest_entry
    """
    cache = _load_cache()
    
    if not cache:
        return {
            'total_entries': 0,
            'expired_count': 0,
            'oldest_entry': None,
            'newest_entry': None,
            'cache_file': str(CACHE_FILE_PATH)
        }
    
    total_entries = len(cache)
    expired_count = sum(1 for entry in cache.values() if is_expired(entry))
    
    # Find oldest and newest entries by fetched_at
    entries_with_dates = []
    for key, entry in cache.items():
        if 'fetched_at' in entry:
            try:
                fetched_at = datetime.fromisoformat(entry['fetched_at'])
                entries_with_dates.append((key, fetched_at, entry))
            except (ValueError, TypeError):
                continue
    
    oldest_entry = None
    newest_entry = None
    
    if entries_with_dates:
        entries_with_dates.sort(key=lambda x: x[1])
        oldest_key, oldest_date, oldest_data = entries_with_dates[0]
        newest_key, newest_date, newest_data = entries_with_dates[-1]
        
        oldest_entry = {
            'key': oldest_key,
            'fetched_at': oldest_data.get('fetched_at'),
            'expires_at': oldest_data.get('expires_at'),
            'data_type': oldest_data.get('data', {}).get('data_type', 'unknown')
        }
        newest_entry = {
            'key': newest_key,
            'fetched_at': newest_data.get('fetched_at'),
            'expires_at': newest_data.get('expires_at'),
            'data_type': newest_data.get('data', {}).get('data_type', 'unknown')
        }
    
    return {
        'total_entries': total_entries,
        'expired_count': expired_count,
        'oldest_entry': oldest_entry,
        'newest_entry': newest_entry,
        'cache_file': str(CACHE_FILE_PATH)
    }


def clear_cache() -> None:
    """
    Clear all cache entries.
    """
    _save_cache({})


def get_cache_info(sport_key: str, data_type: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata about a specific cache entry without returning the data.
    
    Args:
        sport_key: Sport identifier
        data_type: Type of data
    
    Returns:
        Cache entry metadata or None if not found
    """
    cache = _load_cache()
    cache_key = _get_cache_key(sport_key, data_type)
    
    if cache_key not in cache:
        return None
    
    entry = cache[cache_key]
    return {
        'key': cache_key,
        'fetched_at': entry.get('fetched_at'),
        'expires_at': entry.get('expires_at'),
        'is_expired': is_expired(entry),
        'source_urls': entry.get('source_urls', []),
        'confidence': entry.get('confidence', 0)
    }


# Integration helper for fetch_with_verification
def fetch_from_cache_or_compute(sport_key: str, data_type: str, 
                                 compute_fn, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch data from cache if available and not expired, otherwise compute and cache.
    
    Args:
        sport_key: Sport identifier
        data_type: Type of data
        compute_fn: Function to call if cache miss (should return data dict)
        force_refresh: If True, skip cache and recompute
    
    Returns:
        Dict with data and metadata (from_cache flag, etc.)
    """
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_data = get_cached(sport_key, data_type)
        if cached_data is not None:
            cache_info = get_cache_info(sport_key, data_type)
            return {
                'success': True,
                'data': cached_data,
                'from_cache': True,
                'cache_hit': True,
                'fetched_at': cache_info.get('fetched_at'),
                'expires_at': cache_info.get('expires_at'),
                'source_urls': cache_info.get('source_urls', []),
                'confidence': cache_info.get('confidence', 0)
            }
    
    # Cache miss or force refresh - compute fresh data
    result = compute_fn()
    
    if result.get('success'):
        # Cache the result
        set_cached(
            sport_key=sport_key,
            data_type=data_type,
            data=result.get('merged_data', result.get('data', {})),
            source_urls=result.get('sources_used', []),
            confidence=result.get('confidence', 0)
        )
    
    result['from_cache'] = False
    result['cache_hit'] = False
    
    return result


# CLI interface for testing
if __name__ == '__main__':
    import sys
    
    print("Cache Manager Test")
    print("=" * 50)
    
    # Test 1: Get initial stats
    print("\n1. Initial cache stats:")
    stats = get_cache_stats()
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Expired count: {stats['expired_count']}")
    
    # Test 2: Set some test data
    print("\n2. Setting test cache entries...")
    test_data_nba = {
        'sport_name': 'NBA',
        'scores': {'lakers': 102, 'warriors': 98},
        'data_type': 'live_scores'
    }
    set_cached('nba', 'live_scores', test_data_nba, source_urls=['nba.com'], confidence=98)
    print("   Cached NBA live_scores")
    
    test_data_f1 = {
        'sport_name': 'Formula 1',
        'races': [{'name': 'Bahrain GP', 'date': '2026-03-15'}],
        'data_type': 'schedule'
    }
    set_cached('f1', 'schedule', test_data_f1, source_urls=['formula1.com'], confidence=95)
    print("   Cached F1 schedule")
    
    # Test 3: Get cache info
    print("\n3. Cache info for NBA:")
    info = get_cache_info('nba', 'live_scores')
    if info:
        print(f"   Key: {info['key']}")
        print(f"   Fetched: {info['fetched_at']}")
        print(f"   Expires: {info['expires_at']}")
        print(f"   Expired: {info['is_expired']}")
    
    # Test 4: Retrieve cached data
    print("\n4. Retrieving cached NBA data:")
    cached = get_cached('nba', 'live_scores')
    if cached:
        print(f"   Data retrieved: {cached.get('sport_name')}")
        print(f"   Scores: {cached.get('scores')}")
    
    # Test 5: Get updated stats
    print("\n5. Updated cache stats:")
    stats = get_cache_stats()
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Expired count: {stats['expired_count']}")
    if stats['oldest_entry']:
        print(f"   Oldest: {stats['oldest_entry']['key']}")
    if stats['newest_entry']:
        print(f"   Newest: {stats['newest_entry']['key']}")
    
    # Test 6: Cleanup
    print("\n6. Running cleanup:")
    cleanup_result = cleanup()
    print(f"   Removed: {cleanup_result['removed_count']}")
    print(f"   Remaining: {cleanup_result['remaining_count']}")
    
    print("\n" + "=" * 50)
    print("Cache manager tests complete!")

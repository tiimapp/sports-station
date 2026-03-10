#!/usr/bin/env python3
"""
Multi-Source Data Verification Module for Sports Monitor

Provides functions for fetching, comparing, and verifying sports data
from multiple sources (Western + Chinese) with confidence scoring.
Includes cache layer with expiry to prevent redundant fetches.
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

# Import cache manager
from cache_manager import (
    get_cached,
    set_cached,
    is_expired,
    cleanup,
    get_cache_stats,
    get_cache_info,
    get_ttl_hours
)


# Constants
MODULE_DIR = Path(__file__).parent
SOURCES_REGISTRY_PATH = MODULE_DIR / "sources_registry.json"
CACHE_DIR = MODULE_DIR / "cache"


def load_sources_registry() -> Dict[str, Any]:
    """Load the sources registry JSON file."""
    with open(SOURCES_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def fetch_url(url: str) -> Dict[str, Any]:
    """
    Fetch content from a URL using web_fetch tool.
    Returns a dict with 'success', 'content', and 'error' keys.
    """
    try:
        # Use OpenClaw's web_fetch tool via subprocess
        # Note: In production, this would be called via the tool API directly
        result = subprocess.run(
            ['openclaw', 'web_fetch', '--url', url, '--extractMode', 'text'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                'success': True,
                'content': result.stdout,
                'url': url,
                'fetch_time': datetime.now().isoformat()
            }
        else:
            return {
                'success': False,
                'content': None,
                'error': result.stderr,
                'url': url,
                'fetch_time': datetime.now().isoformat()
            }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'content': None,
            'error': 'Timeout',
            'url': url,
            'fetch_time': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'content': None,
            'error': str(e),
            'url': url,
            'fetch_time': datetime.now().isoformat()
        }


def fetch_with_verification(sport_key: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Main entry point for fetching data with multi-source verification.
    Checks cache first and only fetches if cache miss or expired.
    
    Args:
        sport_key: Key from sources_registry (e.g., 'nba', 'f1', 'premier_league')
        force_refresh: If True, skip cache and fetch fresh data
    
    Returns:
        Dict with merged data, confidence score, and metadata
    """
    registry = load_sources_registry()
    
    if sport_key not in registry:
        return {
            'success': False,
            'error': f'Sport key "{sport_key}" not found in registry',
            'confidence': 0
        }
    
    source_config = registry[sport_key]
    data_type = source_config.get('data_type', 'unknown')
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_data = get_cached(sport_key, data_type)
        if cached_data is not None:
            cache_info = get_cache_info(sport_key, data_type)
            return {
                'success': True,
                'sport_key': sport_key,
                'sport_name': source_config.get('name', sport_key),
                'data_type': data_type,
                'merged_data': cached_data,
                'confidence': cache_info.get('confidence', 0) if cache_info else 0,
                'from_cache': True,
                'cache_hit': True,
                'fetched_at': cache_info.get('fetched_at') if cache_info else None,
                'expires_at': cache_info.get('expires_at') if cache_info else None,
                'sources_used': cache_info.get('source_urls', []) if cache_info else [],
                'message': 'Data served from cache'
            }
    
    if sport_key not in registry:
        return {
            'success': False,
            'error': f'Sport key "{sport_key}" not found in registry',
            'confidence': 0
        }
    
    source_config = registry[sport_key]
    urls_to_fetch = []
    url_types = []
    
    # Collect all URLs with their types
    if 'primary_url' in source_config:
        urls_to_fetch.append(source_config['primary_url'])
        url_types.append('primary')
    
    if 'backup_urls' in source_config:
        for url in source_config['backup_urls']:
            urls_to_fetch.append(url)
            url_types.append('backup')
    
    if 'chinese_urls' in source_config:
        for url in source_config['chinese_urls']:
            urls_to_fetch.append(url)
            url_types.append('chinese')
    
    # Fetch all URLs in parallel
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_url, url): (url, url_type) 
                        for url, url_type in zip(urls_to_fetch, url_types)}
        
        for future in as_completed(future_to_url):
            url, url_type = future_to_url[future]
            try:
                fetch_result = future.result()
                fetch_result['type'] = url_type
                results.append(fetch_result)
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e),
                    'url': url,
                    'type': url_type,
                    'fetch_time': datetime.now().isoformat()
                })
    
    # Separate western and chinese data for comparison
    western_data = [r for r in results if r['type'] in ('primary', 'backup') and r['success']]
    chinese_data = [r for r in results if r['type'] == 'chinese' and r['success']]
    
    # Compare sources if we have both western and chinese data
    match_percentage = None
    discrepancies = []
    if western_data and chinese_data:
        comparison = compare_sources(western_data[0], chinese_data[0])
        match_percentage = comparison['match_percentage']
        discrepancies = comparison['discrepancies']
    
    # Merge all successful results
    merged = merge_results(results)
    
    # Calculate confidence score
    confidence = calculate_confidence(
        total_sources=len(urls_to_fetch),
        successful_sources=len([r for r in results if r['success']]),
        match_percentage=match_percentage,
        has_primary=any(r['type'] == 'primary' and r['success'] for r in results)
    )
    
    # Build source URLs list for caching
    source_urls = [r.get('url') for r in results if r.get('success')]
    
    # Cache the fresh result
    set_cached(
        sport_key=sport_key,
        data_type=data_type,
        data=merged,
        source_urls=source_urls,
        confidence=confidence
    )
    
    return {
        'success': True,
        'sport_key': sport_key,
        'sport_name': source_config.get('name', sport_key),
        'data_type': data_type,
        'merged_data': merged,
        'confidence': confidence,
        'match_percentage': match_percentage,
        'discrepancies': discrepancies,
        'sources_used': len([r for r in results if r['success']]),
        'total_sources': len(urls_to_fetch),
        'fetch_time': datetime.now().isoformat(),
        'raw_results': results,
        'from_cache': False,
        'cache_hit': False,
        'message': 'Fresh data fetched and cached'
    }


def compare_sources(western_data: Dict[str, Any], chinese_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cross-verification between western and chinese sources.
    
    Args:
        western_data: Content dict from western source
        chinese_data: Content dict from chinese source
    
    Returns:
        Dict with match_percentage (0-100) and discrepancies list
    """
    if not western_data.get('success') or not chinese_data.get('success'):
        return {
            'match_percentage': 0,
            'discrepancies': ['One or both sources failed to fetch'],
            'comparable': False
        }
    
    western_content = western_data.get('content', '')
    chinese_content = chinese_data.get('content', '')
    
    if not western_content or not chinese_content:
        return {
            'match_percentage': 0,
            'discrepancies': ['Empty content from one or both sources'],
            'comparable': False
        }
    
    discrepancies = []
    match_points = 0
    total_checks = 0
    
    # Extract and compare dates
    western_dates = extract_dates(western_content)
    chinese_dates = extract_dates(chinese_content)
    total_checks += 1
    if western_dates and chinese_dates:
        # Check if any dates overlap (allowing for timezone differences)
        if dates_overlap(western_dates, chinese_dates):
            match_points += 1
        else:
            discrepancies.append(f'Date mismatch: Western={western_dates[:3]}, Chinese={chinese_dates[:3]}')
    
    # Extract and compare team names (simplified heuristic)
    western_teams = extract_team_names(western_content)
    chinese_teams = extract_team_names(chinese_content)
    total_checks += 1
    if western_teams and chinese_teams:
        # Check for any common entities (simplified)
        if have_common_entities(western_teams, chinese_teams):
            match_points += 1
        else:
            discrepancies.append(f'Team names do not match between sources')
    
    # Extract and compare scores (numbers that look like scores)
    western_scores = extract_scores(western_content)
    chinese_scores = extract_scores(chinese_content)
    total_checks += 1
    if western_scores and chinese_scores:
        if scores_match(western_scores, chinese_scores):
            match_points += 1
        else:
            discrepancies.append(f'Score mismatch: Western={western_scores[:5]}, Chinese={chinese_scores[:5]}')
    
    # Check content similarity (basic text overlap)
    total_checks += 1
    similarity = calculate_text_similarity(western_content, chinese_content)
    if similarity > 0.3:  # 30% similarity threshold
        match_points += 1
    else:
        discrepancies.append(f'Low text similarity: {similarity:.2%}')
    
    # Calculate match percentage
    match_percentage = (match_points / total_checks * 100) if total_checks > 0 else 0
    
    return {
        'match_percentage': round(match_percentage, 2),
        'discrepancies': discrepancies,
        'comparable': True,
        'checks_performed': total_checks,
        'checks_passed': match_points
    }


def merge_results(results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine data from multiple sources.
    
    Args:
        results_list: List of fetch results from different sources
    
    Returns:
        Merged data with metadata
    """
    successful_results = [r for r in results_list if r.get('success')]
    
    if not successful_results:
        return {
            'merged_content': None,
            'sources_used': [],
            'confidence': 0,
            'error': 'No successful sources'
        }
    
    # Prioritize: primary > backup > chinese
    priority_order = {'primary': 0, 'backup': 1, 'chinese': 2}
    sorted_results = sorted(
        successful_results,
        key=lambda x: priority_order.get(x.get('type', 'chinese'), 3)
    )
    
    # Use primary source as base
    primary_content = sorted_results[0].get('content', '')
    sources_used = [r.get('url', 'unknown') for r in sorted_results]
    
    return {
        'merged_content': primary_content,
        'sources_used': sources_used,
        'source_count': len(sources_used),
        'primary_source': sorted_results[0].get('url'),
        'fetch_time': datetime.now().isoformat(),
        'all_contents': [r.get('content') for r in sorted_results if r.get('content')]
    }


def detect_freshness(content: str, current_date: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Detect if content is fresh or stale.
    
    Args:
        content: Text content to analyze
        current_date: Reference date (defaults to now)
    
    Returns:
        Dict with status ("fresh"|"stale"|"unknown") and days_old
    """
    if current_date is None:
        current_date = datetime.now()
    
    if not content:
        return {
            'status': 'unknown',
            'days_old': None,
            'reason': 'Empty content'
        }
    
    # Extract dates from content
    dates_found = extract_dates(content)
    
    if not dates_found:
        return {
            'status': 'unknown',
            'days_old': None,
            'reason': 'No dates found in content'
        }
    
    # Find the most recent date
    most_recent = max(dates_found)
    
    # Calculate age in days
    days_old = (current_date - most_recent).days
    
    # Determine freshness status
    if days_old < 0:
        # Future date - might be a schedule
        status = 'fresh'
    elif days_old == 0:
        status = 'fresh'
    elif days_old <= 1:
        status = 'fresh'
    elif days_old <= 7:
        status = 'fresh'
    else:
        status = 'stale'
    
    return {
        'status': status,
        'days_old': max(0, days_old),
        'most_recent_date': most_recent.isoformat(),
        'dates_found_count': len(dates_found)
    }


def get_cache_key(sport_key: str, data_type: str) -> str:
    """
    Generate a consistent cache key for a sport and data type.
    
    Args:
        sport_key: Sport identifier (e.g., 'nba', 'f1')
        data_type: Type of data (e.g., 'live_scores', 'schedule')
    
    Returns:
        Hash-based cache key string
    """
    key_string = f"{sport_key}:{data_type}"
    hash_obj = hashlib.md5(key_string.encode('utf-8'))
    return f"sports_{sport_key}_{data_type}_{hash_obj.hexdigest()[:12]}"


# Helper functions

def extract_dates(content: str) -> List[datetime]:
    """Extract date objects from text content."""
    dates = []
    
    # Common date patterns
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        r'(\d{2}/\d{2}/\d{4})',  # MM/DD/YYYY
        r'(\d{2}-\d{2}-\d{4})',  # MM-DD-YYYY
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',  # 1 Jan 2024
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            try:
                if re.match(r'\d{4}-\d{2}-\d{2}', match):
                    dates.append(datetime.strptime(match, '%Y-%m-%d'))
                elif re.match(r'\d{2}/\d{2}/\d{4}', match):
                    dates.append(datetime.strptime(match, '%m/%d/%Y'))
                elif re.match(r'\d{2}-\d{2}-\d{4}', match):
                    dates.append(datetime.strptime(match, '%m-%d-%Y'))
                else:
                    # Try parsing natural language dates
                    for fmt in ['%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y']:
                        try:
                            dates.append(datetime.strptime(match, fmt))
                            break
                        except ValueError:
                            continue
            except ValueError:
                continue
    
    return dates


def dates_overlap(dates1: List[datetime], dates2: List[datetime], tolerance_days: int = 1) -> bool:
    """Check if any dates from two lists overlap within tolerance."""
    for d1 in dates1:
        for d2 in dates2:
            if abs((d1 - d2).days) <= tolerance_days:
                return True
    return False


def extract_team_names(content: str) -> List[str]:
    """Extract potential team names from content (simplified)."""
    # Look for capitalized words that might be team names
    # This is a simplified heuristic
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    matches = re.findall(pattern, content)
    return matches[:20]  # Limit to top 20


def have_common_entities(list1: List[str], list2: List[str]) -> bool:
    """Check if two lists have common entities (case-insensitive)."""
    set1 = {item.lower() for item in list1}
    set2 = {item.lower() for item in list2}
    return len(set1 & set2) > 0


def extract_scores(content: str) -> List[str]:
    """Extract potential scores from content."""
    # Look for score patterns like "100-98", "3-1", etc.
    pattern = r'\b(\d{1,3}-\d{1,3})\b'
    return re.findall(pattern, content)


def scores_match(scores1: List[str], scores2: List[str]) -> bool:
    """Check if any scores match between two lists."""
    return len(set(scores1) & set(scores2)) > 0


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate basic text similarity (Jaccard index on words)."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union) if union else 0.0


def calculate_confidence(total_sources: int, successful_sources: int, 
                        match_percentage: Optional[float], has_primary: bool) -> float:
    """
    Calculate overall confidence score (0-100).
    
    Factors:
    - Source availability (how many sources succeeded)
    - Cross-verification match (western vs chinese agreement)
    - Primary source availability
    """
    # Base score from source availability
    availability_score = (successful_sources / total_sources * 50) if total_sources > 0 else 0
    
    # Cross-verification score
    verification_score = (match_percentage * 0.3) if match_percentage is not None else 25
    
    # Primary source bonus
    primary_bonus = 20 if has_primary else 0
    
    # Cap at 100
    confidence = min(100, availability_score + verification_score + primary_bonus)
    
    return round(confidence, 2)


# Cache utility functions (re-exported from cache_manager for convenience)

def get_cache_statistics() -> Dict[str, Any]:
    """
    Get comprehensive cache statistics.
    
    Returns:
        Dict with cache stats from cache_manager
    """
    return get_cache_stats()


def cleanup_expired_cache() -> Dict[str, Any]:
    """
    Remove expired entries from cache.
    
    Returns:
        Dict with cleanup stats
    """
    return cleanup()


def get_entry_info(sport_key: str, data_type: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata about a specific cache entry.
    
    Args:
        sport_key: Sport identifier
        data_type: Type of data
    
    Returns:
        Cache entry metadata or None
    """
    return get_cache_info(sport_key, data_type)


def clear_all_cache() -> None:
    """
    Clear all cache entries.
    """
    from cache_manager import clear_cache
    clear_cache()


# CLI interface for testing
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_freshness.py <command> [args]")
        print("")
        print("Commands:")
        print("  fetch <sport_key>       - Fetch data with verification (checks cache first)")
        print("  refresh <sport_key>     - Force refresh, skip cache")
        print("  cache-stats             - Show cache statistics")
        print("  cache-cleanup           - Remove expired cache entries")
        print("  cache-info <sport_key> <data_type> - Show cache entry info")
        print("  cache-clear             - Clear all cache")
        print("")
        print("Available sport keys: f1, nba, cba, premier_league, la_liga, serie_a, bundesliga")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'cache-stats':
        print("Cache Statistics")
        print("=" * 50)
        stats = get_cache_stats()
        print(f"Total entries: {stats['total_entries']}")
        print(f"Expired count: {stats['expired_count']}")
        print(f"Cache file: {stats['cache_file']}")
        if stats['oldest_entry']:
            print(f"\nOldest entry:")
            print(f"  Key: {stats['oldest_entry']['key']}")
            print(f"  Fetched: {stats['oldest_entry']['fetched_at']}")
            print(f"  Expires: {stats['oldest_entry']['expires_at']}")
        if stats['newest_entry']:
            print(f"\nNewest entry:")
            print(f"  Key: {stats['newest_entry']['key']}")
            print(f"  Fetched: {stats['newest_entry']['fetched_at']}")
            print(f"  Expires: {stats['newest_entry']['expires_at']}")
    
    elif command == 'cache-cleanup':
        print("Running cache cleanup...")
        result = cleanup()
        print(f"Removed: {result['removed_count']} expired entries")
        print(f"Remaining: {result['remaining_count']} entries")
    
    elif command == 'cache-clear':
        print("Clearing all cache...")
        clear_all_cache()
        print("Cache cleared!")
    
    elif command == 'cache-info' and len(sys.argv) >= 4:
        sport_key = sys.argv[2]
        data_type = sys.argv[3]
        info = get_entry_info(sport_key, data_type)
        if info:
            print(f"Cache info for {sport_key}:{data_type}")
            print("=" * 50)
            print(f"Key: {info['key']}")
            print(f"Fetched: {info['fetched_at']}")
            print(f"Expires: {info['expires_at']}")
            print(f"Expired: {info['is_expired']}")
            print(f"Confidence: {info['confidence']}%")
            print(f"Source URLs: {info['source_urls']}")
        else:
            print(f"No cache entry found for {sport_key}:{data_type}")
    
    elif command in ('fetch', 'refresh'):
        sport_key = sys.argv[2] if len(sys.argv) > 2 else None
        if not sport_key:
            print("Error: sport_key required")
            sys.exit(1)
        
        force_refresh = (command == 'refresh')
        print(f"{'Refreshing' if force_refresh else 'Fetching'} data for: {sport_key}")
        print("-" * 50)
        
        result = fetch_with_verification(sport_key, force_refresh=force_refresh)
        
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Sport: {result['sport_name']}")
            print(f"Data Type: {result['data_type']}")
            print(f"Confidence: {result['confidence']}%")
            print(f"From Cache: {result.get('from_cache', False)}")
            if result.get('from_cache'):
                print(f"Expires At: {result.get('expires_at', 'N/A')}")
            else:
                print(f"Sources Used: {result['sources_used']}/{result['total_sources']}")
                if result['match_percentage'] is not None:
                    print(f"Cross-verification Match: {result['match_percentage']}%")
                if result['discrepancies']:
                    print(f"Discrepancies: {result['discrepancies']}")
            
            # Test freshness detection
            if result['merged_data'].get('merged_content'):
                freshness = detect_freshness(result['merged_data']['merged_content'])
                print(f"Freshness: {freshness['status']} ({freshness.get('days_old', 'N/A')} days old)")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see usage")
        sys.exit(1)

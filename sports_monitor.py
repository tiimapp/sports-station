#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sports Monitor - 体育赛事监控技能 v3.0.0
全自动实时赛程获取，基于阿里云 WebSearch

支持：NBA, CBA, 中超，欧洲五大联赛，F1, 奥运会
数据源：阿里云 Dashscope WebSearch + NBA.com CDN
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import requests
from dateutil import parser as date_parser

# ============================================================================
# 配置路径
# ============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.json')
INTERESTS_PATH = os.path.join(SCRIPT_DIR, 'interests.json')

# ============================================================================
# 阿里云配置
# ============================================================================

ALIYUN_CONFIG = {
    'api_key': 'sk-9fd1be825af0419c88382485d119451c',
    'model': 'qwen-plus',
    'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
}

# ============================================================================
# 阿里云 WebSearch 实时搜索
# ============================================================================

def aliyun_web_search(query: str, enable_search: bool = True, timeout: int = 10, show_progress: bool = False) -> str:
    """
    使用阿里云 Dashscope WebSearch 获取实时信息 (v3.0.3 优化版)
    
    Args:
        query: 搜索查询
        enable_search: 启用搜索插件
        timeout: 超时时间（秒），默认 10 秒 (v3.0.3 从 20s 优化到 10s)
        show_progress: 显示进度提示
    
    Returns:
        搜索结果文本，失败返回空字符串
    """
    if show_progress:
        print(f"⏳ 搜索中：{query[:40]}...")
    
    headers = {
        "Authorization": f"Bearer {ALIYUN_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": ALIYUN_CONFIG['model'],
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "enable_search": enable_search
    }
    
    try:
        response = requests.post(ALIYUN_CONFIG['base_url'], headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        
        if result.get('choices'):
            if show_progress:
                print(f"✅ 搜索完成")
            return result['choices'][0]['message']['content']
        return ""
    except requests.exceptions.Timeout:
        if show_progress:
            print(f"⚠️  搜索超时 ({timeout}秒)")
        return ""
    except Exception as e:
        if show_progress:
            print(f"⚠️  搜索失败：{e}")
        return ""


def parse_football_fixtures(search_result: str, date: str) -> dict:
    """
    解析阿里云返回的足球赛程文本为结构化数据
    
    Args:
        search_result: 阿里云返回的文本
        date: 日期字符串
    
    Returns:
        {
            'csl': [{'time': '15:30', 'home': '山东泰山', 'away': '辽宁铁人', ...}],
            'premier_league': [...],
            ...
        }
    """
    fixtures = {
        'csl': [],
        'premier_league': [],
        'la_liga': [],
        'serie_a': [],
        'bundesliga': [],
        'ligue_1': []
    }
    
    # 使用正则表达式提取比赛信息
    # 匹配模式：时间 + 主队 + vs/VS + 客队 + (可选备注)
    pattern = r'(\d{1,2}:\d{2})\s*[:：]?\s*([^\s]+(?:队 | 联 | 城 | 联)?)\s*(?:vs|VS|vs\.|对阵)\s*([^\s]+(?:队 | 联 | 城 | 联)?)'
    
    lines = search_result.split('\n')
    current_league = None
    
    for line in lines:
        line = line.strip()
        
        # 检测联赛名称
        if '中超' in line or 'CSL' in line:
            current_league = 'csl'
        elif '英超' in line:
            current_league = 'premier_league'
        elif '西甲' in line:
            current_league = 'la_liga'
        elif '意甲' in line:
            current_league = 'serie_a'
        elif '德甲' in line:
            current_league = 'bundesliga'
        elif '法甲' in line:
            current_league = 'ligue_1'
        elif '拜仁' in line or '多特' in line:
            current_league = 'bundesliga'
        elif '皇马' in line or '巴萨' in line or '巴塞罗那' in line:
            current_league = 'la_liga'
        
        # 匹配比赛
        match = re.search(pattern, line)
        if match and current_league:
            time = match.group(1)
            home = match.group(2).strip()
            away = match.group(3).strip()
            
            # 清理队名
            home = re.sub(r'[（\(].*?[）\)]', '', home).strip()
            away = re.sub(r'[（\(].*?[）\)]', '', away).strip()
            
            # 检测备注信息
            note = ''
            if '升班马' in line:
                note = '升班马'
            elif '大胜' in line or '4-1' in line or '3-0' in line:
                note = '大胜'
            elif '冷门' in line:
                note = '冷门'
            
            # 检测比分
            score_match = re.search(r'(\d+-\d+|\d+-\d+)', line)
            score = score_match.group(1) if score_match else ''
            status = 'FT' if score else ''
            
            fixtures[current_league].append({
                'time': time,
                'home': home,
                'away': away,
                'note': note,
                'score': score,
                'status': status,
                'priority': 'high' if note else 'medium'
            })
    
    return fixtures


def fetch_football_fixtures_auto(date: str) -> dict:
    """
    自动获取足球赛程（阿里云搜索 + 解析）
    """
    query = f"{date} 足球赛程 中超 英超 西甲 意甲 德甲 法甲 比赛时间 对阵"
    search_result = aliyun_web_search(query, enable_search=True)
    
    if not search_result:
        return {}
    
    fixtures = parse_football_fixtures(search_result, date)
    return fixtures


def fetch_all_sports_schedule_auto(date: str) -> dict:
    """
    自动获取热门赛事赛程（v3.0.4 简化版）
    
    只搜索核心项目，避免超时：
    - 第 1 批：篮球（NBA + CBA 全明星）
    - 第 2 批：电竞（LPL + LCK）
    """
    result = {
        'basketball': {'nba': [], 'cba_allstar': []},
        'esports': {'lpl': [], 'lck': []}
    }
    
    # ========== 第 1 批：篮球（15秒超时）==========
    query1 = f"{date} NBA 赛程 CBA 全明星"
    search1 = aliyun_web_search(query1, enable_search=True, timeout=10)
    
    if search1:
        for line in search1.split('\n'):
            line = line.strip()
            if len(line) < 10 or '根据' in line:
                continue
            
            # CBA 全明星
            if any(kw in line for kw in ['CBA 全明星', '星锐']):
                time_match = re.search(r'(\d{1,2}:\d{2})', line)
                time = time_match.group(1) if time_match else 'TBD'
                result['basketball']['cba_allstar'].append({
                    'time': time,
                    'event': 'CBA 全明星',
                    'description': line[:60]
                })
    
    # ========== 第 2 批：电竞（15秒超时）==========
    query2 = f"{date} LPL LCK 赛程"
    search2 = aliyun_web_search(query2, enable_search=True, timeout=10)
    
    if search2:
        for line in search2.split('\n'):
            line = line.strip()
            if len(line) < 10 or '根据' in line:
                continue
            
            # LPL
            if 'LPL' in line or any(t in line for t in ['WBG', 'EDG', 'BLG', 'JDG']):
                time_match = re.search(r'(\d{1,2}:\d{2})', line)
                time = time_match.group(1) if time_match else 'TBD'
                result['esports']['lpl'].append({
                    'time': time,
                    'description': line[:60]
                })
            
            # LCK
            if 'LCK' in line or any(t in line for t in ['GEN', 'T1']):
                time_match = re.search(r'(\d{1,2}:\d{2})', line)
                time = time_match.group(1) if time_match else 'TBD'
                result['esports']['lck'].append({
                    'time': time,
                    'description': line[:60]
                })
    
    return result


def fetch_nba_schedule_auto(date: str) -> List[dict]:
    """
    自动获取 NBA 赛程（NBA 官方 CDN）
    
    Args:
        date: 日期字符串
    
    Returns:
        比赛列表
    """
    url = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_2.json'
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        # 转换为美国日期格式
        us_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%m/%d/%Y')
        target_dates = [us_date]
        
        for target_date in target_dates:
            for game_date in data.get('leagueSchedule', {}).get('gameDates', []):
                game_date_str = game_date.get('gameDate', '')
                if game_date_str.startswith(target_date):
                    for game in game_date.get('games', []):
                        home_team = game.get('homeTeam', {})
                        away_team = game.get('awayTeam', {})
                        
                        time_utc = game.get('gameDateTimeUTC', '')
                        try:
                            dt_utc = date_parser.parse(time_utc)
                            dt_beijing = dt_utc.replace(tzinfo=timezone.utc) + timedelta(hours=8)
                            time_beijing = dt_beijing.strftime('%Y-%m-%d %H:%M')
                        except:
                            time_beijing = time_utc[:16].replace('T', ' ')
                        
                        games.append({
                            'home': f"{home_team.get('teamCity', '')} {home_team.get('teamName', '')}",
                            'away': f"{away_team.get('teamCity', '')} {away_team.get('teamName', '')}",
                            'time': time_beijing,
                            'arena': game.get('arenaName', ''),
                        })
        
        games.sort(key=lambda x: x['time'])
        return games
    except Exception as e:
        print(f"⚠️  获取 NBA 赛程失败：{e}")
        return []


# ============================================================================
# 时间工具函数
# ============================================================================

def get_beijing_now() -> datetime:
    """获取当前北京时间"""
    return datetime.now()


def get_beijing_date_str() -> str:
    """获取北京时间日期字符串"""
    return datetime.now().strftime('%Y-%m-%d')


def is_within_days(event_date: datetime, max_days: int = 30) -> bool:
    """检查事件是否在指定天数范围内"""
    now = get_beijing_now()
    days_diff = (event_date - now).days
    return 0 <= days_diff <= max_days


# ============================================================================
# 配置加载
# ============================================================================

def load_config() -> dict:
    """加载系统配置"""
    default = {
        'language': 'zh',
    }
    
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return {**default, **json.load(f)}
    return default


def load_interests() -> dict:
    """加载用户兴趣列表"""
    default = {
        'version': '3.0.0',
        'sports': {
            'basketball': {'name': '篮球', 'priority': 1, 'enabled': True, 'leagues': {
                'nba': {'priority': 1, 'teams': ['Golden State Warriors']},
                'cba': {'priority': 2, 'teams': ['广东宏远', '辽宁本钢']},
                'fiba': {'priority': 3, 'tournaments': ['奥运会', '世界杯']}
            }},
            'football': {'name': '足球', 'priority': 2, 'enabled': True, 'leagues': {
                'europe_top5': {'priority': 1, 'teams': ['Real Madrid', 'Barcelona']},
                'csl': {'priority': 2, 'teams': []},
                'fifa': {'priority': 3}
            }},
            'motorsport': {'name': '赛车', 'priority': 3, 'enabled': True, 'leagues': {
                'f1': {'priority': 1, 'teams': ['Red Bull Racing', 'Mercedes']}
            }},
            'olympics': {'name': '奥运会', 'priority': 4, 'enabled': True, 'show_within_days': 30}
        },
        'display_rules': {
            'only_today': True,
            'max_future_days': 30,
            'hide_completed': True,
            'sort_by_priority': True
        }
    }
    
    if os.path.exists(INTERESTS_PATH):
        with open(INTERESTS_PATH, 'r', encoding='utf-8') as f:
            return {**default, **json.load(f)}
    return default


# ============================================================================
# 其他赛事信息（静态）
# ============================================================================

def get_cba_info() -> dict:
    """获取 CBA 联赛信息"""
    return {
        'name': 'CBA 中国男子篮球职业联赛 2025-2026 赛季',
        'status': '常规赛进行中（预计 10 月 - 次年 3 月）',
        'hot_teams': ['广东宏远', '辽宁本钢', '北京首钢', '浙江广厦'],
        'key_matchups': ['广东 vs 辽宁（辽粤大战）', '北京 vs 广东（京粤大战）'],
        'broadcast': 'CCTV5、咪咕视频、腾讯体育',
        'popularity': 75
    }


def get_olympics_info(olympic_type: str = 'winter') -> dict:
    """获取奥运会信息"""
    if olympic_type == 'winter':
        start_date = datetime(2026, 2, 6)
        end_date = datetime(2026, 2, 22)
        now = get_beijing_now()
        
        if now < start_date:
            status = 'upcoming'
            days_left = (start_date - now).days
        elif now > end_date:
            status = 'completed'
            days_left = -(now - end_date).days
        else:
            status = 'ongoing'
            days_left = (end_date - now).days
        
        return {
            'name': '2026 年米兰 - 科尔蒂纳丹佩佐冬奥会',
            'dates': '2026 年 2 月 6 日 - 2 月 22 日',
            'location': '意大利 米兰 - 科尔蒂纳丹佩佐',
            'hot_sports': ['冰球', '冰壶', '高山滑雪', '速度滑冰', '短道速滑', '花样滑冰'],
            'china_events': ['短道速滑', '花样滑冰', '自由式滑雪', '单板滑雪'],
            'popularity': 95,
            'status': status,
            'days_left': days_left
        }
    else:
        start_date = datetime(2028, 7, 14)
        end_date = datetime(2028, 7, 30)
        now = get_beijing_now()
        
        if now < start_date:
            status = 'upcoming'
            days_left = (start_date - now).days
        elif now > end_date:
            status = 'completed'
            days_left = -(now - end_date).days
        else:
            status = 'ongoing'
            days_left = (end_date - now).days
        
        return {
            'name': '2028 年洛杉矶夏奥会',
            'dates': '2028 年 7 月 14 日 - 7 月 30 日',
            'location': '美国 洛杉矶',
            'hot_sports': ['篮球', '足球', '游泳', '田径', '乒乓球', '跳水'],
            'china_events': ['乒乓球', '跳水', '举重', '体操'],
            'popularity': 90,
            'status': status,
            'days_left': days_left
        }


# ============================================================================
# 格式化输出
# ============================================================================

def format_star_rating(score: int) -> str:
    """生成星级评分"""
    stars = '⭐' * min(max(score // 20, 1), 5)
    return stars


def get_popularity_stars(popularity: int) -> str:
    """根据热门程度生成星级"""
    if popularity >= 90:
        return '⭐⭐⭐⭐⭐'
    elif popularity >= 70:
        return '⭐⭐⭐⭐'
    elif popularity >= 50:
        return '⭐⭐⭐'
    elif popularity >= 30:
        return '⭐⭐'
    else:
        return '⭐'


def format_basketball_game(game: dict, favorite_teams: List[str], priority: str = 'medium') -> str:
    """格式化篮球比赛"""
    home = game.get('home', 'Unknown')
    away = game.get('away', 'Unknown')
    time_beijing = game.get('time', '')
    arena = game.get('arena', '')
    
    try:
        dt = date_parser.parse(time_beijing)
        time_str = dt.strftime('%m-%d %H:%M')
    except:
        time_str = time_beijing[:16].replace('T', ' ') if time_beijing else 'TBD'
    
    score = 50
    if priority == 'high':
        score += 10
    if home in favorite_teams or away in favorite_teams:
        score += 30
    
    stars = format_star_rating(score)
    
    return f"{stars} {time_str} | {away} @ {home}\n   📍 {arena}\n   🔥 推荐指数：{score}/100"


def format_football_fixture(fixture: dict, favorite_teams: List[str]) -> str:
    """格式化足球比赛"""
    time = fixture.get('time', 'TBD')
    home = fixture.get('home', 'Unknown')
    away = fixture.get('away', 'Unknown')
    score = fixture.get('score', '')
    status = fixture.get('status', '')
    note = fixture.get('note', '')
    priority = fixture.get('priority', 'medium')
    
    score_val = 50
    if priority == 'high':
        score_val += 20
    if any(t in home for t in favorite_teams) or any(t in away for t in favorite_teams):
        score_val += 25
    
    stars = format_star_rating(score_val)
    
    if score and status:
        time_str = f"{time} ({status})"
    else:
        time_str = time
    
    result = f"{stars} {time_str} | {home} vs {away}"
    
    if note:
        result += f"\n   📝 {note}"
    
    result += f"\n   🔥 推荐指数：{score_val}/100"
    
    return result


# ============================================================================
# 查询功能（v3.0.0 全自动）
# ============================================================================

def query_today_matches(config: dict, interests: dict) -> str:
    """查询今天的比赛（v3.0.1 综合搜索）"""
    today = get_beijing_date_str()
    display_rules = interests.get('display_rules', {})
    
    # 执行综合搜索（一次性获取所有赛事）
    all_sports_data = fetch_all_sports_schedule_auto(today)
    # 获取足球赛程（单独搜索更准确）
    football_data = fetch_football_fixtures_auto(today)
    # 获取 NBA 赛程（官方 CDN）
    nba_games = fetch_nba_schedule_auto(today)
    
    result = []
    result.append(f"📅 今日热门赛事推荐 ({today})\n{'='*60}")
    result.append(f"🤖 数据来源：阿里云 WebSearch 实时搜索 + NBA.com CDN")
    result.append(f"⚡ 自动获取，无需手动配置")
    result.append("")
    
    sports_config = interests.get('sports', {})
    sorted_sports = sorted(
        [(k, v) for k, v in sports_config.items() if v.get('enabled', False)],
        key=lambda x: x[1].get('priority', 999)
    )
    
    has_content = False
    
    for sport_key, sport_config in sorted_sports:
        sport_name = sport_config.get('name', sport_key)
        sport_priority = sport_config.get('priority', 999)
        leagues = sport_config.get('leagues', {})
        
        # ========== 篮球 ==========
        if sport_key == 'basketball':
            basketball_content = []
            sport_has_content = False
            
            sorted_leagues = sorted(
                [(k, v) for k, v in leagues.items() if v.get('enabled', False)],
                key=lambda x: x[1].get('priority', 999)
            )
            
            for league_key, league_config in sorted_leagues:
                league_name = league_config.get('name', league_key)
                teams = league_config.get('teams', [])
                
                # NBA - 自动获取
                if league_key == 'nba':
                    nba_games = fetch_nba_schedule_auto(today)
                    
                    if nba_games:
                        sport_has_content = True
                        basketball_content.append(f"\n🏀 {league_name}")
                        basketball_content.append(f"   热门程度：{get_popularity_stars(85)} (85/100)")
                        basketball_content.append("-" * 50)
                        basketball_content.append(f"📅 今日 {len(nba_games)} 场比赛")
                        basketball_content.append("")
                        
                        for game in nba_games:
                            home = game.get('home', '')
                            away = game.get('away', '')
                            
                            if teams and (any(t in home for t in teams) or any(t in away for t in teams)):
                                basketball_content.append("💚 " + format_basketball_game(game, teams, 'high'))
                            else:
                                basketball_content.append(format_basketball_game(game, [], 'medium'))
                            basketball_content.append("")
                
                # CBA - 静态信息 + 全明星
                elif league_key == 'cba':
                    cba_info = get_cba_info()
                    sport_has_content = True
                    basketball_content.append(f"\n🏀 {league_name}")
                    basketball_content.append(f"   热门程度：{get_popularity_stars(75)} (75/100)")
                    basketball_content.append("-" * 50)
                    
                    # 检查是否有全明星赛
                    cba_allstar = all_sports_data.get('basketball', {}).get('cba_allstar', [])
                    if cba_allstar:
                        basketball_content.append(f"🔴 CBA 全明星周末（今日）")
                        for event in cba_allstar:
                            basketball_content.append(f"   ⏰ {event.get('time', 'TBD')} | {event.get('event', '')}")
                            basketball_content.append(f"   📝 {event.get('description', '')[:80]}")
                        basketball_content.append(f"📺 直播平台：CCTV5、央视频、抖音")
                    else:
                        basketball_content.append(f"📌 {cba_info['status']}")
                        basketball_content.append(f"🔥 焦点球队：{', '.join(cba_info['hot_teams'][:4])}")
                        basketball_content.append(f"⚔️ 焦点对决：{', '.join(cba_info['key_matchups'])}")
                        basketball_content.append(f"📺 直播平台：{cba_info['broadcast']}")
                    
                    if teams:
                        basketball_content.append(f"💚 您关注的球队：{', '.join(teams)}")
                
                # FIBA
                elif league_key == 'fiba':
                    tournaments = league_config.get('tournaments', [])
                    basketball_content.append(f"\n🏀 {league_name}")
                    basketball_content.append(f"   关注赛事：{', '.join(tournaments)}")
                    basketball_content.append(f"💚 关注球队：{', '.join(teams) if teams else '中国男篮/女篮'}")
            
            if sport_has_content:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"🏀 {sport_name} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                result.extend(basketball_content)
        
        # ========== 足球 ==========
        elif sport_key == 'football':
            football_content = []
            sport_has_content = False
            
            # 自动获取足球赛程
            auto_fixtures = fetch_football_fixtures_auto(today)
            
            sorted_leagues = sorted(
                [(k, v) for k, v in leagues.items() if v.get('enabled', False)],
                key=lambda x: x[1].get('priority', 999)
            )
            
            for league_key, league_config in sorted_leagues:
                league_name = league_config.get('name', league_key)
                teams = league_config.get('teams', [])
                
                # 欧洲五大联赛 - 自动获取
                if league_key == 'europe_top5':
                    all_fixtures = []
                    for src_league in ['bundesliga', 'la_liga', 'serie_a', 'ligue_1', 'premier_league']:
                        if src_league in auto_fixtures:
                            all_fixtures.extend(auto_fixtures[src_league])
                    
                    if all_fixtures:
                        sport_has_content = True
                        football_content.append(f"\n⚽ {league_name}")
                        football_content.append(f"   热门程度：{get_popularity_stars(85)} (85/100)")
                        football_content.append("-" * 50)
                        
                        for fixture in all_fixtures:
                            football_content.append(format_football_fixture(fixture, teams))
                            football_content.append("")
                    else:
                        football_content.append(f"\n⚽ {league_name}")
                        football_content.append(f"   热门程度：{get_popularity_stars(85)} (85/100)")
                        football_content.append("-" * 50)
                        football_content.append("📌 今日暂无比赛或搜索未获取到数据")
                
                # 中超 - 自动获取
                elif league_key == 'csl':
                    csl_fixtures = auto_fixtures.get('csl', [])
                    
                    if csl_fixtures:
                        sport_has_content = True
                        football_content.append(f"\n⚽ {league_name}")
                        football_content.append(f"   热门程度：{get_popularity_stars(80)} (80/100)")
                        football_content.append("-" * 50)
                        football_content.append(f"📌 2026 赛季")
                        football_content.append("")
                        
                        for fixture in csl_fixtures:
                            football_content.append(format_football_fixture(fixture, []))
                    else:
                        football_content.append(f"\n⚽ {league_name}")
                        football_content.append(f"   热门程度：{get_popularity_stars(70)} (70/100)")
                        football_content.append("-" * 50)
                        football_content.append("📌 搜索未获取到赛程数据")
                
                # FIFA
                elif league_key == 'fifa':
                    tournaments = league_config.get('tournaments', [])
                    football_content.append(f"\n⚽ {league_name}")
                    football_content.append(f"   关注赛事：{', '.join(tournaments)}")
            
            if sport_has_content:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"⚽ {sport_name} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                result.extend(football_content)
        
        # ========== 羽毛球 ==========
        elif sport_key == 'badminton':
            tournaments = sport_config.get('tournaments', {})
            badminton_data = all_sports_data.get('badminton', [])
            
            if badminton_data:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"🏸 {sport_name} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                
                for tournament_key, tournament_config in tournaments.items():
                    if tournament_config.get('enabled', False):
                        tournament_name = tournament_config.get('name', tournament_key)
                        players = tournament_config.get('players', [])
                        
                        result.append(f"\n🏸 {tournament_name}")
                        result.append(f"   热门程度：⭐⭐⭐⭐⭐ (90/100)")
                        result.append("-" * 50)
                        
                        for match in badminton_data:
                            if tournament_name in match.get('tournament', ''):
                                result.append(f"⏰ {match.get('time', 'TBD')} | {match.get('description', '')[:80]}")
                        
                        if players:
                            result.append(f"💚 中国选手：{', '.join(players[:6])}")
        
        # ========== 网球 ==========
        elif sport_key == 'tennis':
            tournaments = sport_config.get('tournaments', {})
            tennis_data = all_sports_data.get('tennis', [])
            
            if tennis_data:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"🎾 {sport_name} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                
                for tournament_key, tournament_config in tournaments.items():
                    if tournament_config.get('enabled', False):
                        tournament_name = tournament_config.get('name', tournament_key)
                        
                        result.append(f"\n🎾 {tournament_name}")
                        result.append(f"   热门程度：⭐⭐⭐⭐ (80/100)")
                        result.append("-" * 50)
                        
                        for match in tennis_data:
                            result.append(f"⏰ {match.get('time', 'TBD')} | {match.get('description', '')[:80]}")
        
        # ========== 电竞 ==========
        elif sport_key == 'esports':
            leagues = sport_config.get('leagues', {})
            esports_data = all_sports_data.get('esports', {})
            
            has_esports = False
            esports_content = []
            
            for league_key, league_config in leagues.items():
                if league_config.get('enabled', False):
                    league_name = league_config.get('name', league_key)
                    teams = league_config.get('teams', [])
                    league_data = esports_data.get(league_key, [])
                    
                    if league_data:
                        has_esports = True
                        esports_content.append(f"\n🎮 {league_name}")
                        esports_content.append(f"   热门程度：⭐⭐⭐⭐⭐ (85/100)")
                        esports_content.append("-" * 50)
                        
                        for match in league_data:
                            esports_content.append(f"⏰ {match.get('time', 'TBD')} | {match.get('description', '')[:80]}")
                        
                        if teams:
                            esports_content.append(f"💚 关注战队：{', '.join(teams)}")
            
            if has_esports:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"🎮 {sport_config.get('name', '电竞')} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                result.extend(esports_content)
        
        # ========== 高尔夫 ==========
        elif sport_key == 'golf':
            tournaments = sport_config.get('tournaments', {})
            golf_data = all_sports_data.get('golf', [])
            
            if golf_data:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"⛳ {sport_name} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                
                for tournament_key, tournament_config in tournaments.items():
                    if tournament_config.get('enabled', False):
                        tournament_name = tournament_config.get('name', tournament_key)
                        
                        result.append(f"\n⛳ {tournament_name}")
                        result.append(f"   热门程度：⭐⭐⭐ (70/100)")
                        result.append("-" * 50)
                        
                        for match in golf_data:
                            result.append(f"⏰ {match.get('time', 'TBD')} | {match.get('description', '')[:80]}")
        
        # ========== 冰球 ==========
        elif sport_key == 'ice_hockey':
            leagues = sport_config.get('leagues', {})
            hockey_data = all_sports_data.get('ice_hockey', {})
            
            has_hockey = False
            hockey_content = []
            
            for league_key, league_config in leagues.items():
                if league_config.get('enabled', False):
                    league_name = league_config.get('name', league_key)
                    league_data = hockey_data.get(league_key, [])
                    
                    if league_data:
                        has_hockey = True
                        hockey_content.append(f"\n🏒 {league_name}")
                        hockey_content.append(f"   热门程度：⭐⭐⭐ (65/100)")
                        hockey_content.append("-" * 50)
                        
                        for match in league_data:
                            hockey_content.append(f"⏰ {match.get('time', 'TBD')} | {match.get('description', '')[:80]}")
            
            if has_hockey:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"🏒 {sport_config.get('name', '冰球')} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                result.extend(hockey_content)
        
        # ========== 赛车 ==========
        elif sport_key == 'motorsport':
            f1_config = leagues.get('f1', {})
            if f1_config.get('enabled', False):
                f1_teams = f1_config.get('teams', [])
                
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"🏎️ {sport_config.get('name', '赛车')} (优先级：{['最高', '高', '中', '低'][min(sport_priority-1, 3)]})")
                result.append('='*60)
                result.append(f"\n🏎️ F1 一级方程式")
                result.append(f"   热门程度：{get_popularity_stars(75)} (75/100)")
                result.append("-" * 50)
                result.append("ℹ️  F1 赛程需配置 API Key（可选）")
        
        # ========== 奥运会 ==========
        elif sport_key == 'olympics':
            show_within_days = sport_config.get('show_within_days', 30)
            olympic_types = sport_config.get('types', ['summer', 'winter'])
            
            olympics_content = []
            has_upcoming_olympics = False
            
            for olympic_type in olympic_types:
                olympic_info = get_olympics_info(olympic_type)
                status = olympic_info.get('status', 'upcoming')
                days_left = abs(olympic_info.get('days_left', 999))
                
                if status == 'completed':
                    continue
                if status == 'upcoming' and days_left > show_within_days:
                    continue
                
                has_upcoming_olympics = True
                
                olympics_content.append(f"\n{olympic_info['name']}")
                olympics_content.append(f"   热门程度：{get_popularity_stars(olympic_info['popularity'])} ({olympic_info['popularity']}/100)")
                
                if status == 'ongoing':
                    olympics_content.append(f"🔴 正在进行中 (还剩{days_left}天)")
                else:
                    olympics_content.append(f"⏳ 距离开始还有{days_left}天")
                
                olympics_content.append(f"📅 日期：{olympic_info['dates']}")
                olympics_content.append(f"📍 地点：{olympic_info['location']}")
            
            if has_upcoming_olympics:
                has_content = True
                result.append(f"\n{'='*60}")
                result.append(f"🏅 {sport_config.get('name', '奥运会')}")
                result.append('='*60)
                result.extend(olympics_content)
    
    if not has_content:
        result.append("\n⚠️  今日暂无您关注的赛事")
    
    result.append(f"\n{'='*60}")
    result.append("💡 提示：数据来自阿里云 WebSearch 实时搜索，如有偏差请告知")
    
    return '\n'.join(result)


# ============================================================================
# 主程序
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='🏆 Sports Monitor v3.0.0 - 全自动体育赛事监控',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--today', action='store_true', help='查看今天的比赛')
    parser.add_argument('--config-check', action='store_true', help='检查配置')
    
    args = parser.parse_args()
    
    config = load_config()
    interests = load_interests()
    
    if args.config_check:
        print("📋 配置检查")
        print("=" * 50)
        print(f"阿里云 API Key: {'✅ 已配置' if ALIYUN_CONFIG.get('api_key') else '❌ 未配置'}")
        print(f"兴趣配置文件：{'✅ 存在' if os.path.exists(INTERESTS_PATH) else '❌ 不存在'}")
        return
    
    if args.today:
        result = query_today_matches(config, interests)
        print(result)
    else:
        result = query_today_matches(config, interests)
        print(result)


if __name__ == '__main__':
    main()

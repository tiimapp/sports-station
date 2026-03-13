#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sports Station - 体育赛事监控技能 v4.0.2
固定输出格式版本 - 每个比赛一行，格式稳定

支持：NBA, CBA, 中超，欧洲五大联赛，F1
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import requests
from dateutil import parser as date_parser

# Tavily 支持
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

# ============================================================================
# 配置路径
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INTERESTS_PATH = os.path.join(SCRIPT_DIR, 'interests.json')
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'config.json')

# ============================================================================
# 阿里云配置
# ============================================================================
ALIYUN_CONFIG = {
    'api_key': 'sk-9fd1be825af0419c88382485d119451c',
    'model': 'qwen-plus',
    'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
}

# ============================================================================
# 网络搜索函数
# ============================================================================
def mcp_web_search(query: str, timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            ['mcporter', 'call', 'exa.web_search_exa', f'query={query}'],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            try:
                mcp_result = json.loads(result.stdout)
                if 'results' in mcp_result:
                    texts = []
                    for item in mcp_result['results'][:5]:
                        title = item.get('title', '')
                        text = item.get('text', '')
                        url = item.get('url', '')
                        texts.append(f"{title}\n{text}\n来源：{url}")
                    return '\n\n'.join(texts)
                return result.stdout
            except json.JSONDecodeError:
                return result.stdout
    except:
        pass
    return ""


def tavily_web_search(query: str, timeout: int = 15) -> str:
    if not TAVILY_AVAILABLE:
        return ""
    try:
        client = TavilyClient()
        response = client.search(
            query=query, search_depth="advanced", max_results=5,
            include_answer=True, timeout=timeout * 1000
        )
        if response.get('results'):
            texts = []
            if response.get('answer'):
                texts.append(f"答案摘要:\n{response['answer']}\n")
            for item in response['results'][:5]:
                title = item.get('title', '')
                text = item.get('content', '')
                url = item.get('url', '')
                texts.append(f"{title}\n{text}\n来源：{url}")
            return '\n\n'.join(texts)
    except:
        pass
    return ""


def aliyun_web_search(query: str, timeout: int = 10) -> str:
    headers = {
        "Authorization": f"Bearer {ALIYUN_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": ALIYUN_CONFIG['model'],
        "messages": [{"role": "user", "content": query}],
        "enable_search": True
    }
    try:
        response = requests.post(ALIYUN_CONFIG['base_url'], headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        if result.get('choices'):
            return result['choices'][0]['message']['content']
    except:
        pass
    return ""


def dashscope_web_search(query: str, timeout: int = 10, count: int = 5) -> str:
    """使用 Dashscope MCP 服务器进行搜索 (AI 优化，无广告，结果精准)"""
    config_path = os.path.expanduser('~/.openclaw/workspace/config/mcporter.json')
    try:
        result = subprocess.run(
            ['mcporter', '--config', config_path, 'call', 'dashscope-websearch.bailian_web_search', f'query:{query}', f'count:{count}'],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            try:
                mcp_result = json.loads(result.stdout)
                texts = []
                
                # 尝试 pages 字段（列表）
                if 'pages' in mcp_result and isinstance(mcp_result['pages'], list):
                    for item in mcp_result['pages'][:count]:
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        url = item.get('url', '')
                        hostname = item.get('hostname', '')
                        if title or snippet:
                            texts.append(f"{title}\n{snippet}\n来源：{url} ({hostname})")
                
                # 尝试 tools 字段（工具结果）
                if 'tools' in mcp_result and isinstance(mcp_result['tools'], list):
                    for tool in mcp_result['tools']:
                        tool_result = tool.get('result', '')
                        if tool_result:
                            texts.append(f"[Tool Result]\n{tool_result}")
                
                # 如果 pages 和 tools 都为空，返回原始输出
                if not texts:
                    return result.stdout
                
                return '\n\n'.join(texts)
            except json.JSONDecodeError:
                return result.stdout
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    return ""


def multi_source_search(query: str, timeout: int = 15, config: dict = None) -> str:
    """
    多源搜索策略（可配置优先级）
    Phase 2: Refactored to support configurable search tools
    
    Args:
        query: 搜索查询
        timeout: 默认超时时间
        config: 配置字典（从 load_config() 获取）
    
    Returns:
        搜索结果文本
    """
    # 如果没有提供配置，使用默认配置
    if not config:
        config = load_config()
    
    # 获取搜索工具配置
    search_tools_config = config.get('search_tools', {})
    
    # 检查搜索工具是否全局启用
    if not search_tools_config.get('enabled', True):
        return ""
    
    # 获取优先级列表和工具配置
    priority = search_tools_config.get('priority', ['dashscope_mcp', 'aliyun', 'tavily'])
    tools_config = search_tools_config.get('tools', {})
    
    # 按优先级顺序尝试搜索
    for tool_name in priority:
        # 获取工具配置
        tool_cfg = tools_config.get(tool_name, {})
        
        # 检查工具是否启用 (Phase 2.3)
        if not tool_cfg.get('enabled', True):
            continue
        
        # 获取工具超时时间 (Phase 2.4)
        tool_timeout = tool_cfg.get('timeout', timeout)
        
        # 调用对应的搜索函数 (Phase 2.2)
        result = ""
        try:
            if tool_name == 'dashscope_mcp':
                result = dashscope_web_search(query, timeout=tool_timeout)
            elif tool_name == 'aliyun':
                # 使用配置中的 API key（如果有）
                api_key = tool_cfg.get('api_key', ALIYUN_CONFIG['api_key'])
                if api_key != ALIYUN_CONFIG['api_key']:
                    # 临时更新 ALIYUN_CONFIG
                    old_key = ALIYUN_CONFIG['api_key']
                    ALIYUN_CONFIG['api_key'] = api_key
                    result = aliyun_web_search(query, timeout=tool_timeout)
                    ALIYUN_CONFIG['api_key'] = old_key
                else:
                    result = aliyun_web_search(query, timeout=tool_timeout)
            elif tool_name == 'tavily':
                result = tavily_web_search(query, timeout=tool_timeout)
            else:
                # 未知工具，跳过
                continue
        except Exception as e:
            # 搜索失败，尝试下一个工具
            continue
        
        # 如果搜索成功，返回结果
        if result and len(result) > 50:
            return result
    
    # 所有工具都失败，返回空字符串
    return ""


# ============================================================================
# 足球数据解析 - 严格版
# ============================================================================
# 有效球队名关键词（用于验证）
VALID_TEAMS = {
    # 中超
    'csl': ['泰山', '国安', '海港', '蓉城', '三镇', '浙江', '武汉', '上海海港', '北京国安', '广州', '深圳', '河南', '成都', '长春', '南通', '南通支云', '沧州', '青岛', '大连', '梅州', '青岛海牛', '青岛西海岸', '深圳新鹏城', '云南玉昆', '辽宁铁人', '天津', '天津津门虎', '重庆', '重庆两江竞技'],
    # 英超
    'premier_league': ['曼城', '利物浦', '阿森纳', '曼联', '切尔西', '热刺', '纽卡', '布莱顿', '维拉', '埃弗顿', '水晶宫', '富勒姆', '狼队', '布伦特福德', '森林', '诺丁汉森林', 'Manchester', 'Liverpool', 'Arsenal', 'Chelsea', 'Tottenham', 'City', 'United', 'Newcastle', 'Brighton', 'Aston', 'Villa', 'Everton', 'Crystal', 'Fulham', 'Wolves', 'Brentford', 'Nottingham'],
    # 英冠/英甲
    'championship': ['Leicester', 'Bristol', 'Leeds', 'Southampton', 'West Brom', 'Middlesbrough', 'Sunderland', 'Mansfield', 'Reading', 'Derby', '谢菲尔德联', '谢菲联', '莱斯特', '布里斯托', '利兹', '南安普顿'],
    # 西甲
    'la_liga': ['皇马', '巴萨', '马竞', '巴塞罗那', '塞维利亚', '瓦伦西亚', '皇家社会', '比利亚雷亚尔', '贝蒂斯', '毕尔巴鄂', 'Madrid', 'Barcelona', 'Atletico', 'Sevilla', 'Valencia', 'Real', 'Barca', 'Villarreal', 'Bilbao', 'Sociedad', 'Betis'],
    # 意甲
    'serie_a': ['尤文', '国米', 'AC米兰', '米兰', '罗马', '那不勒斯', '拉齐奥', '亚特兰大', '佛罗伦萨', 'Juventus', 'Inter', 'Milan', 'Roma', 'Napoli', 'Lazio', 'Atalanta', 'Fiorentina', 'Torino', 'Bologna', 'Monza'],
    # 德甲
    'bundesliga': ['拜仁', '多特', '勒沃', '莱比锡', '法兰克福', '弗赖堡', '门兴', '霍芬海姆', '斯图加特', 'Bayern', 'Dortmund', 'Leverkusen', 'Leipzig', 'Frankfurt', 'Freiburg', 'Monchengladbach', 'Hoffenheim', 'Stuttgart', 'Wolfsburg', 'Union'],
    # 法甲
    'ligue_1': ['巴黎', '马赛', '摩纳哥', '里昂', '里尔', '雷恩', '尼斯', 'PSG', 'Monaco', 'Lyon', 'Marseille', 'Lille', 'Rennes', 'Nice', 'Lens', 'Lorient', 'Brest'],
}

# 国家/地区名（非球队，用于过滤）
NON_TEAM_NAMES = ['中国', '美国', '英国', '德国', '法国', '日本', '韩国', '澳大利亚', '巴西', '阿根廷', '西班牙', '意大利', '香港', '湖北', '湖南', '广东', '北京', '上海', '香港金牛']


def is_valid_team_name(name: str) -> bool:
    """检查是否是有效的球队名 - 宽松版"""
    name = name.strip()
    
    # 排除非球队名称
    for non_team in NON_TEAM_NAMES:
        if name == non_team:
            return False
    
    # 检查是否包含有效球队关键词
    for league, teams in VALID_TEAMS.items():
        for team in teams:
            if team in name or name in team:
                return True
    
    # 宽松验证：队名长度合理就接受
    if len(name) >= 2 and len(name) <= 25:
        # 排除明显不是队名的
        skip = ['暂无', '没有', '赛事', '联赛', '直播', '对阵', '足球', 'VS', 'vs']
        if not any(s in name for s in skip):
            return True
        
    return False


def parse_football_fixtures(search_result: str, date: str) -> dict:
    fixtures = {
        'csl': [], 'premier_league': [], 'la_liga': [],
        'serie_a': [], 'bundesliga': [], 'ligue_1': [], 'championship': []
    }
    
    if not search_result:
        return fixtures
    
    lines = search_result.split('\n')
    
    league_keywords = {
        'csl': ['中超', 'CSL'],
        'premier_league': ['英超', 'Premier League'],
        'la_liga': ['西甲', 'La Liga'],
        'serie_a': ['意甲', 'Serie A'],
        'bundesliga': ['德甲', 'Bundesliga'],
        'ligue_1': ['法甲', 'Ligue 1'],
        'championship': ['英甲', '英冠', ' Championship', 'League One'],
    }
    
    league_display = {
        'csl': '中超', 'premier_league': '英超', 'la_liga': '西甲',
        'serie_a': '意甲', 'bundesliga': '德甲', 'ligue_1': '法甲',
        'championship': '英冠/英甲'
    }
    
    for line in lines:
        line = line.strip()
        if len(line) < 15:
            continue
        
        # 跳过无效行
        skip_keywords = ['根据', '知识库', '搜索结果', '暂无', '没有', '不安排', '#', '来源', 'http', '<', '>', '[']
        if re.search(r'<[^>]+>', line):
            continue
        if any(kw in line for kw in skip_keywords):
            continue
        
        # 查找联赛
        current_league = None
        for league_key, keywords in league_keywords.items():
            for kw in keywords:
                if kw in line:
                    current_league = league_key
                    break
            if current_league:
                break
        
        # 查找时间
        time_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?(?:分)?)', line)
        if not time_match:
            continue
        match_time = time_match.group(1)
        if ':' in match_time:
            parts = match_time.split(':')
            if len(parts) >= 2:
                match_time = f'{parts[0]}:{parts[1]}'
        
        # 查找对阵 - 支持带空格的英文队名
        # 查找对阵 - 支持多种格式
        vs_patterns = [
            # 格式1: "队名 vs 队名"
            r'([^\s,，:：()（）]+(?:[a-zA-Z][\w\s]*)?)\s*[Vv][Ss]\.?\s*([^\s,，:：()（）]+)',
            # 格式2: "队名 比分 队名"
            r'([^\s,，:：()（）]+)\s+\d+:\d+\s+([^\s,，:：()（）]+)',
        ]
        match_found = False
        for pattern in vs_patterns:
            vs_match = re.search(pattern, line)
            if vs_match:
                away = vs_match.group(1).strip()
                home = vs_match.group(2).strip()
                
                # 清理队名
                home = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', home).strip()
                away = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', away).strip()
                home = re.sub(r'\s+', ' ', home)
                away = re.sub(r'\s+', ' ', away)
                skip_names = ['对阵', '双方', '暂无', '信息', '赛事', '联赛', '直播']
                if any(n in home for n in skip_names) or any(n in away for n in skip_names):
                    continue

                
                # 验证队名有效性
                home_valid = is_valid_team_name(home)
                away_valid = is_valid_team_name(away)
                # 放宽验证：队名长度合理也接受
                if not home_valid and 2 <= len(home) <= 20:
                    home_valid = True
                if not away_valid and 2 <= len(away) <= 20:
                    away_valid = True

                
                if home_valid and away_valid:
                    match_found = True
                    break
                elif not home_valid and not away_valid:
                    # 两个都无效才放弃
                    break
        
        if match_found:
            # 推断联赛（如果搜索结果没有明确联赛名）
            if not current_league:
                for league_key, teams in VALID_TEAMS.items():
                    for team in teams:
                        if team in home or team in away:
                            current_league = league_key
                            break
                    if current_league:
                        break
                if not current_league:
                    current_league = 'championship'
            
            if current_league:
                fixtures[current_league].append({
                    'time': match_time,
                    'home': home,
                    'away': away,
                    'league': league_display.get(current_league, '足球'),
                    'priority': 'medium'
                })
    
    return fixtures


def fetch_football_fixtures(date: str, config: dict = None) -> dict:
    """
    获取足球赛程
    Phase 5.2.1: Enhanced with strict date context (UTC+8)
    """
    # 构建严格的日期上下文
    date_context = format_search_date_context(date)
    
    # 构建查询，明确指定日期和时区
    query = f"{date_context} 足球赛程 五大联赛 中超 英超 西甲 意甲 德甲 法甲 对阵时间 UTC+8 北京时间"
    
    search_result = multi_source_search(query, timeout=15, config=config)
    
    if search_result:
        return parse_football_fixtures(search_result, date)
    return {}


# ============================================================================
# NBA 赛程获取
# ============================================================================
def fetch_nba_schedule(date: str) -> List[dict]:
    """
    获取 NBA 赛程
    Phase 5.2.2: Enhanced with strict UTC+8 timezone validation
    """
    url = 'https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_2.json'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        
        # 解析目标日期（UTC+8）
        target_date = datetime.strptime(date, '%Y-%m-%d')
        target_date_str = target_date.strftime('%Y-%m-%d')
        
        # NBA API 使用美国日期（UTC-5 到 UTC-8），需要检查前一天
        us_date = (target_date - timedelta(days=1)).strftime('%m/%d/%Y')
        
        for game_date in data.get('leagueSchedule', {}).get('gameDates', []):
            game_date_str = game_date.get('gameDate', '')
            if game_date_str.startswith(us_date):
                for game in game_date.get('games', []):
                    home_team = game.get('homeTeam', {})
                    away_team = game.get('awayTeam', {})
                    
                    time_utc = game.get('gameDateTimeUTC', '')
                    try:
                        # 转换为 UTC+8 北京时间
                        dt_utc = date_parser.parse(time_utc)
                        dt_beijing = dt_utc.replace(tzinfo=timezone.utc) + timedelta(hours=8)
                        time_beijing = dt_beijing.strftime('%Y-%m-%d %H:%M')
                        
                        # Phase 5.2.3: 严格过滤 - 只保留目标日期的比赛
                        game_date_beijing = dt_beijing.strftime('%Y-%m-%d')
                        if game_date_beijing != target_date_str:
                            continue
                        
                        games.append({
                            'home': home_team.get('teamName', ''),
                            'away': away_team.get('teamName', ''),
                            'time': time_beijing,
                        })
                    except:
                        # 时间解析失败，跳过
                        continue
        
        games.sort(key=lambda x: x['time'])
        return games
    except:
        return []


# ============================================================================
# F1 赛程
# ============================================================================
def fetch_f1_schedule() -> List[dict]:
    default_schedule = [
        {'date': '03/13-15', 'title': '中国大奖赛', 'location': '上海'},
        {'date': '03/27-29', 'title': '日本大奖赛', 'location': '铃鹿'},
        {'date': '04/10-12', 'title': '巴林大奖赛', 'location': '萨基尔'},
        {'date': '04/24-26', 'title': '沙特大奖赛', 'location': '吉达'},
    ]
    return default_schedule


# ============================================================================
# 辅助函数 - 时区处理
# ============================================================================
def get_beijing_datetime() -> datetime:
    """获取北京时间（UTC+8）"""
    return datetime.now(timezone(timedelta(hours=8)))


def get_beijing_date_str() -> str:
    """获取北京日期字符串 YYYY-MM-DD"""
    return get_beijing_datetime().strftime('%Y-%m-%d')


def get_beijing_date_display() -> str:
    """获取北京日期显示格式 YYYY年MM月DD日"""
    return get_beijing_datetime().strftime('%Y年%m月%d日')


def get_beijing_weekday() -> str:
    """获取北京时间星期几"""
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    return weekdays[get_beijing_datetime().weekday()]


def format_search_date_context(date_str: str) -> str:
    """
    格式化搜索日期上下文
    为搜索工具提供明确的时间范围
    
    Args:
        date_str: YYYY-MM-DD 格式的日期
    
    Returns:
        包含日期上下文的字符串
    """
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        # 中文日期
        cn_date = target_date.strftime('%Y年%m月%d日')
        # 星期几
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        weekday = weekdays[target_date.weekday()]
        
        # 构建时间范围（当天 00:00 - 23:59 UTC+8）
        date_context = f"{cn_date}({weekday}) 北京时间 今日赛程"
        
        return date_context
    except:
        return f"{date_str} 今日"


def load_interests() -> dict:
    default = {
        'version': '4.0.2',
        'sports': {
            'basketball': {'name': '篮球', 'enabled': True, 'leagues': {'nba': {'enabled': True, 'teams': []}}},
            'football': {'name': '足球', 'enabled': True, 'leagues': {'europe_top5': {'enabled': True}, 'csl': {'enabled': True}}},
            'motorsport': {'name': 'F1', 'enabled': True, 'leagues': {'f1': {'enabled': True}}}
        }
    }
    if os.path.exists(INTERESTS_PATH):
        with open(INTERESTS_PATH, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            return {**default, **user_config}
    return default


def load_config() -> dict:
    """
    加载配置文件 (config.json)
    Phase 1.1: Configuration Loading
    """
    default_config = {
        'version': '4.0.3',
        'search_tools': {
            'enabled': True,
            'priority': ['dashscope_mcp', 'aliyun', 'tavily'],
            'tools': {
                'dashscope_mcp': {
                    'enabled': True,
                    'timeout': 10,
                    'config_path': '~/.openclaw/workspace/config/mcporter.json'
                },
                'aliyun': {
                    'enabled': True,
                    'timeout': 10,
                    'api_key': ALIYUN_CONFIG['api_key'],
                    'model': ALIYUN_CONFIG['model'],
                    'base_url': ALIYUN_CONFIG['base_url']
                },
                'tavily': {
                    'enabled': True,
                    'timeout': 15,
                    'search_depth': 'advanced',
                    'max_results': 5
                }
            }
        }
    }
    
    # 尝试加载用户配置
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # 合并配置（用户配置覆盖默认配置）
                if 'search_tools' in user_config:
                    # 合并 search_tools
                    for key in user_config['search_tools']:
                        if key == 'tools':
                            # 合并每个工具的配置
                            for tool_name, tool_cfg in user_config['search_tools']['tools'].items():
                                if tool_name in default_config['search_tools']['tools']:
                                    default_config['search_tools']['tools'][tool_name].update(tool_cfg)
                                else:
                                    default_config['search_tools']['tools'][tool_name] = tool_cfg
                        else:
                            default_config['search_tools'][key] = user_config['search_tools'][key]
                return default_config
        except Exception as e:
            print(f"⚠️  配置文件加载失败，使用默认配置: {e}")
            return default_config
    
    return default_config


# ============================================================================
# 固定格式输出
# ============================================================================
def is_favorite_team(team_name: str, favorite_teams: List[str]) -> bool:
    if not favorite_teams:
        return False
    team_lower = team_name.lower()
    for fav in favorite_teams:
        if fav.lower() in team_lower or team_lower in fav.lower():
            return True
    return False



# ============================================================================
# Discord 推送函数
# ============================================================================
def get_discord_webhook_url() -> str:
    """获取 Discord webhook URL"""
    # 从环境变量获取
    webhook_url = os.environ.get('DISCORD_GAMEDAY_WEBHOOK')
    if webhook_url and webhook_url != 'YOUR_DISCORD_WEBHOOK_URL_HERE':
        return webhook_url
    
    # 从配置文件获取
    config_path = os.path.join(SCRIPT_DIR, 'discord_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                webhook_url = config.get('webhook_url', '')
                if webhook_url and webhook_url != 'YOUR_DISCORD_WEBHOOK_URL_HERE':
                    return webhook_url
        except:
            pass
    
    return ""

def send_discord_message(message: str, webhook_url: str = None) -> bool:
    """
    发送消息到 Discord
    
    Args:
        message: 要发送的消息内容
        webhook_url: Discord webhook URL，如果为 None 则从环境变量或配置文件获取
    
    Returns:
        bool: 发送成功返回 True，否则返回 False
    """
    if not webhook_url:
        webhook_url = get_discord_webhook_url()
    
    if not webhook_url:
        print("警告: Discord webhook URL 未配置，跳过推送")
        print("请在环境变量中设置 DISCORD_GAMEDAY_WEBHOOK 或在 discord_config.json 中配置 webhook_url")
        return False
    
    try:
        # Discord 单条消息最大长度限制为 2000 字符
        content = message[:1990] if len(message) > 1990 else message
        
        # 使用 requests 发送 POST 请求
        response = requests.post(
            webhook_url,
            json={"content": content},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 204:
            print("✓ 成功发送到 Discord")
            return True
        else:
            print(f"✗ 发送失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("✗ 发送超时")
        return False
    except Exception as e:
        print(f"✗ 发送过程中出错: {e}")
        return False

def format_nba_game(game: dict, favorite_teams: List[str]) -> str:
    home = game.get('home', '')
    away = game.get('away', '')
    time_str = game.get('time', '')
    
    try:
        dt = date_parser.parse(time_str)
        date_str = dt.strftime('%m-%d')
        time_only = dt.strftime('%H:%M')
    except:
        date_str = datetime.now().strftime('%m-%d')
        time_only = time_str[:5] if time_str else 'TBD'
    
    is_fav = is_favorite_team(home, favorite_teams) or is_favorite_team(away, favorite_teams)
    
    if is_fav:
        return f"💚 ⭐⭐⭐⭐ {date_str} {time_only} | {away} @ {home} | 腾讯体育"
    else:
        return f"⭐⭐ {date_str} {time_only} | {away} @ {home} | 腾讯体育"


def format_football_fixture(fixture: dict, favorite_teams: List[str]) -> str:
    time = fixture.get('time', 'TBD')
    home = fixture.get('home', '')
    away = fixture.get('away', '')
    league = fixture.get('league', '足球')
    
    date_str = datetime.now().strftime('%m-%d')
    time_only = str(time)
    
    is_fav = is_favorite_team(home, favorite_teams) or is_favorite_team(away, favorite_teams)
    
    if is_fav:
        return f"💚 ⭐⭐⭐⭐ {date_str} {time_only} | {league} | {away} vs {home} | 咪咕体育"
    else:
        return f"⭐⭐ {date_str} {time_only} | {league} | {away} vs {home} | 咪咕体育"


def format_f1_race(race: dict) -> str:
    date = race.get('date', 'TBD')
    location = race.get('location', '')
    title = race.get('title', 'F1大奖赛')
    
    return f"📅 {date} | {title} | {location} | CCTV5"


# ============================================================================
# 主查询函数
# ============================================================================
def query_today_matches(interests: dict, config: dict = None, date: str = None) -> str:
    """
    查询指定日期的比赛
    Phase 3.2: Updated to accept and pass config parameter
    Phase 5.4.2: Updated to accept explicit date parameter
    
    Args:
        interests: 兴趣配置
        config: 搜索工具配置
        date: 查询日期（YYYY-MM-DD 格式），如果为 None 则使用今天
    """
    # 使用指定日期或今天的日期（UTC+8）
    query_date = date if date else get_beijing_date_str()
    sports = interests.get('sports', {})
    
    lines = []
    lines.append(f"📅 {query_date} 赛事汇总")
    lines.append("=" * 60)
    lines.append("")
    
    # ========== NBA ==========
    nba_config = sports.get('basketball', {}).get('leagues', {}).get('nba', {})
    if nba_config.get('enabled', False):
        favorite_teams = nba_config.get('teams', [])
        nba_games = fetch_nba_schedule(query_date)
        
        if nba_games:
            lines.append("🏀 NBA")
            for game in nba_games:
                lines.append(format_nba_game(game, favorite_teams))
            lines.append("")
    
    # ========== 足球 ==========
    football_config = sports.get('football', {})
    if football_config.get('enabled', False):
        leagues_config = football_config.get('leagues', {})
        football_data = fetch_football_fixtures(query_date, config=config)
        
        # 收集所有有效足球比赛
        all_football = []
        
        europe_config = leagues_config.get('europe_top5', {})
        if europe_config.get('enabled', False):
            fav_teams = europe_config.get('teams', [])
            for league_key in ['bundesliga', 'la_liga', 'serie_a', 'ligue_1', 'premier_league', 'championship']:
                if league_key in football_data:
                    for f in football_data[league_key]:
                        f['favorite_teams'] = fav_teams
                        all_football.append(f)
        
        csl_config = leagues_config.get('csl', {})
        if csl_config.get('enabled', False):
            if 'csl' in football_data:
                for f in football_data['csl']:
                    f['favorite_teams'] = []
                    all_football.append(f)
        
        if all_football:
            lines.append("⚽ 足球")
            all_football.sort(key=lambda x: x.get('time', '99:99'))
            for fixture in all_football[:10]:
                fav_teams = fixture.get('favorite_teams', [])
                lines.append(format_football_fixture(fixture, fav_teams))
            lines.append("")
    
    # ========== F1 ==========
    f1_config = sports.get('motorsport', {}).get('leagues', {}).get('f1', {})
    if f1_config.get('enabled', False):
        f1_data = fetch_f1_schedule()
        
        if f1_data:
            lines.append("🏎️ F1")
            for race in f1_data[:5]:
                lines.append(format_f1_race(race))
            lines.append("")
    
    if len(lines) <= 2:
        lines.append("⚠️ 今日暂无赛事数据")
    
    return '\n'.join(lines)


# ============================================================================
# 主程序
# ============================================================================

def main():
    """
    主程序
    Phase 3.1: Load config and pass to query functions
    Phase 5.4: Add explicit date parameter support
    """
    parser = argparse.ArgumentParser(description='Sports Station v4.0.3 - 可配置搜索工具 + 严格时区控制')
    parser.add_argument('--today', action='store_true', help='查看今天的比赛（UTC+8）')
    parser.add_argument('--date', type=str, help='查看指定日期的比赛（格式：YYYY-MM-DD 或 YYYY/MM/DD，UTC+8）')
    parser.add_argument('--push-discord', action='store_true', help='将比赛摘要推送到 Discord')
    args = parser.parse_args()
    
    # Phase 3.1: Load configuration
    config = load_config()
    interests = load_interests()
    
    # Phase 5.4: 确定查询日期
    query_date = None
    if args.date:
        # 使用指定日期（支持 YYYY-MM-DD 或 YYYY/MM/DD 格式）
        date_str = args.date.replace('/', '-')
        try:
            # 验证日期格式
            datetime.strptime(date_str, '%Y-%m-%d')
            query_date = date_str
        except ValueError:
            print(f"❌ 错误：日期格式无效。请使用 YYYY-MM-DD 或 YYYY/MM/DD 格式（例如：2026-03-13 或 2026/03/13）")
            return
    elif args.today:
        # 使用今天的日期（UTC+8）
        query_date = get_beijing_date_str()
    
    if query_date:
        # 显示查询的日期
        date_display = format_search_date_context(query_date)
        print(f"🔍 查询日期：{date_display}")
        print()
        
        # Phase 5.4.4: Pass config and date to query function
        result = query_today_matches(interests, config=config, date=query_date)
        print(result)
        
        # 如果指定了 --push-discord 参数，则推送消息
        if args.push_discord:
            send_discord_message(result)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

# Sports Station Skill

**Version**: 4.0.3  
**Type**: Sports Event Monitoring  
**Timezone**: UTC+8 (Beijing Time)

## Overview

Sports Station monitors sports events and intelligently recommends matches worth watching. All operations are strictly based on UTC+8 (Beijing Time) to ensure accurate date range control.

## Capabilities

### Current Features (Phase 1)

- **NBA**: Track specific teams (e.g., Warriors, Lakers) with automatic UTC+8 timezone conversion
- **European Football**: Premier League, La Liga, Serie A, Bundesliga, Ligue 1
- **Chinese Super League**: CSL matches
- **Formula 1**: F1 Grand Prix schedule
- **Smart Recommendations**: Recommend "worth watching" matches based on user interests
- **Discord Integration**: Auto-push event summaries to Discord channels
- **Strict Timezone Control**: All searches and filters based on UTC+8 for accurate date ranges

### Planned Features (Phase 2)

CBA, Badminton, Tennis, Esports (LPL/LCK), Golf, Ice Hockey, Olympics

## Usage

### Command Syntax

```bash
# Query matches for a specific date (explicit date required, UTC+8)
python3 sports_station.py --date YYYY-MM-DD

# Push to Discord
python3 sports_station.py --date YYYY-MM-DD --push-discord
```

### Examples

```bash
# Query today's matches
python3 sports_station.py --date 2026-03-13

# Alternative date format (slash separator)
python3 sports_station.py --date 2026/03/13

# Push to Discord
python3 sports_station.py --date 2026-03-13 --push-discord
```

## Parameters

| Parameter | Required | Format | Description |
|-----------|----------|--------|-------------|
| `--date` | Yes | YYYY-MM-DD or YYYY/MM/DD | Target date in UTC+8 timezone |
| `--push-discord` | No | Flag | Push results to Discord webhook |

## Timezone Handling

### Core Principles

All time processing is strictly based on **UTC+8 (Beijing Time)**:

1. **Date Definition**: 
   - "Today" means UTC+8 current date (YYYY-MM-DD)
   - Example: Beijing Time 2026-03-13 00:00 - 23:59

2. **NBA Schedule Filtering**:
   - UTC times from NBA API automatically converted to UTC+8
   - Strict filtering: only show matches where converted date equals target date
   - Avoids cross-date confusion (e.g., US 23:00 vs Beijing next day 12:00)

3. **Football Schedule Search**:
   - Search queries include explicit date context:
     - Chinese date: "2026年03月13日(星期四)"
     - Timezone identifier: "UTC+8 北京时间"
     - Keywords: "今日赛程"
   - Ensures search engines return correct date results

### Agent Integration

**⚠️ Important**: When calling this skill from an agent, you MUST provide explicit date format (YYYY-MM-DD). Do NOT use ambiguous terms like "today", "tomorrow", or "yesterday".

```python
# ✅ Correct: Use explicit date format
from datetime import datetime, timezone, timedelta

# Get UTC+8 current date
beijing_tz = timezone(timedelta(hours=8))
today = datetime.now(beijing_tz).strftime('%Y-%m-%d')

result = subprocess.run(
    ['python3', 'sports_station.py', '--date', today],
    capture_output=True,
    text=True
)
```

## Configuration

### User Interests (`interests.json`)

```json
{
  "version": "4.0.3",
  "sports": {
    "basketball": {
      "name": "篮球",
      "enabled": true,
      "leagues": {
        "nba": {
          "name": "NBA",
          "enabled": true,
          "teams": ["Golden State Warriors", "Los Angeles Lakers"]
        }
      }
    },
    "football": {
      "name": "足球",
      "enabled": true,
      "leagues": {
        "europe_top5": {
          "name": "欧洲五大联赛",
          "enabled": true,
          "teams": ["Real Madrid", "Barcelona", "Manchester City"]
        },
        "csl": {
          "name": "中超联赛",
          "enabled": true,
          "teams": []
        }
      }
    },
    "motorsport": {
      "name": "F1",
      "enabled": true,
      "leagues": {
        "f1": {
          "name": "F1",
          "enabled": true
        }
      }
    }
  }
}
```

### Discord Webhook (`discord_config.json`)

```json
{
  "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
}
```

Or use environment variable:
```bash
export DISCORD_GAMEDAY_WEBHOOK="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
```

### Search Tools (`config.json`)

```json
{
  "search_tools": {
    "priority": ["dashscope_mcp", "aliyun", "tavily"],
    "dashscope_mcp": {
      "enabled": true,
      "timeout": 30
    },
    "aliyun": {
      "enabled": true,
      "timeout": 20
    },
    "tavily": {
      "enabled": true,
      "timeout": 15
    }
  }
}
```

## Output Format

### Terminal Output

```
📅 2026-03-13 赛事汇总
============================================================

🏀 NBA
💚 ⭐⭐⭐⭐ 03-13 08:00 | Celtics @ Warriors | 腾讯体育
⭐⭐ 03-13 10:30 | Heat @ Bucks | 腾讯体育

⚽ 足球
💚 ⭐⭐⭐⭐ 03-13 20:00 | 英超 | Liverpool vs Man City | 咪咕体育
⭐⭐ 03-13 22:00 | 西甲 | Sevilla vs Valencia | 咪咕体育

🏎️ F1
📅 03/13-15 | 中国大奖赛 | 上海 | CCTV5
```

### Rating System

- 💚 ⭐⭐⭐⭐ (4 stars): User's favorite teams
- ⭐⭐ (2 stars): Regular matches

## Data Sources

- **NBA.com CDN**: Official NBA schedule data
- **Dashscope MCP**: AI-optimized web search (Chinese priority)
- **Aliyun WebSearch**: Chinese sports event data
- **Tavily**: Deep search backup

## Dependencies

```bash
pip install requests python-dateutil tavily-python
```

## Automation

### Cron Job Example

```bash
# Push daily at 9:00 AM (use date command to get current date)
0 9 * * * cd /path/to/sports-station && python3 sports_station.py --date $(date +\%Y-\%m-\%d) --push-discord
```

### Python Integration

```python
import subprocess
from datetime import datetime, timezone, timedelta

beijing_tz = timezone(timedelta(hours=8))
today = datetime.now(beijing_tz).strftime('%Y-%m-%d')

result = subprocess.run(
    ['python3', 'sports_station.py', '--date', today],
    capture_output=True,
    text=True
)
print(result.stdout)
```

## Error Handling

- **Missing --date parameter**: Returns error message requiring explicit date
- **Invalid date format**: Returns format error with examples
- **No matches found**: Returns empty summary with date confirmation
- **API failures**: Automatically falls back to alternative search tools based on priority

## Notes

- All match times displayed in Beijing Time (UTC+8)
- Date filtering strictly follows UTC+8 calendar days
- Search results based on UTC+8 time ranges
- Avoids cross-timezone date confusion

---

**Last Updated**: 2026-03-13  
**Maintainer**: Sports Station Team

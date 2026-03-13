# Sports Station Skill - 体育赛事监控

监控用户感兴趣的体育赛事赛程，智能推荐值得观看的比赛。

**⚠️ 重要**: 本技能严格基于 **UTC+8（北京时间）** 运行，所有日期和时间查询均以北京时间为准。

## 功能

### Phase 1 核心功能（当前版本）
- **NBA 监控**: 跟踪指定球队（如勇士队、湖人队）的比赛，UTC+8 时区自动转换
- **欧洲五大联赛**: 英超、西甲、意甲、德甲、法甲关键场次
- **中超联赛**: 中国足球超级联赛
- **F1 赛车**: 一级方程式大奖赛赛程
- **智能推荐**: 基于用户关注球队推荐"值得看"的比赛
- **Discord 推送**: 自动推送赛事摘要到 Discord 频道
- **严格时区控制**: 所有搜索和过滤基于 UTC+8，确保日期范围准确

### Phase 2 计划功能（未来版本）
- CBA 中国男子篮球职业联赛
- 羽毛球国际赛事
- 网球四大满贯
- 电竞 LPL、LCK
- 高尔夫赛事
- 冰球 KHL、NHL
- 奥运会

## 使用方式

### 基本命令

```bash
# 查看指定日期的比赛（必须使用明确日期，UTC+8）
python3 sports_station.py --date 2026-03-13
python3 sports_station.py --date 2026/03/13  # 也支持斜杠格式

# 推送到 Discord
python3 sports_station.py --date 2026-03-13 --push-discord
```

### ⚠️ 时区处理说明（Agent 调用必读）

**核心原则**: 本技能的所有时间处理严格基于 **UTC+8（北京时间）**。

#### 日期范围控制

1. **"今天"的定义**: 
   - 使用 UTC+8 当前日期（YYYY-MM-DD）
   - 例如：北京时间 2026-03-13 00:00 - 23:59

2. **NBA 比赛过滤**:
   - 从 NBA API 获取的 UTC 时间自动转换为 UTC+8
   - 严格过滤：只显示转换后日期等于目标日期的比赛
   - 避免跨日期混淆（如美国 23:00 vs 北京次日 12:00）

3. **足球赛程搜索**:
   - 搜索查询包含明确的日期上下文：
     - 中文日期："2026年03月13日(星期四)"
     - 时区标识："UTC+8 北京时间"
     - 关键词："今日赛程"
   - 确保搜索引擎返回正确日期的结果

#### Agent 调用建议

```python
# ✅ 正确：使用明确的日期格式（YYYY-MM-DD）
from datetime import datetime, timezone, timedelta

# 获取 UTC+8 当前日期
beijing_tz = timezone(timedelta(hours=8))
today = datetime.now(beijing_tz).strftime('%Y-%m-%d')

result = subprocess.run(['python3', 'sports_station.py', '--date', today], ...)

# ⚠️ 注意：必须传递明确的日期，不接受 "today" 等模糊术语
```

#### 时区处理保证

- ✅ 所有比赛时间显示为北京时间（UTC+8）
- ✅ 日期过滤严格按 UTC+8 日历日
- ✅ 搜索结果基于 UTC+8 时间范围
- ✅ 避免跨时区日期混淆

## 配置

在 `interests.json` 中设置：

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
          "teams": ["Golden State Warriors", "Los Angeles Lakers", "Boston Celtics"]
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
          "teams": ["Real Madrid", "Barcelona", "Manchester City", "Liverpool"]
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

## Discord 配置

在 `discord_config.json` 中配置 webhook:

```json
{
  "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
}
```

或设置环境变量:
```bash
export DISCORD_GAMEDAY_WEBHOOK="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
```

## API 数据源

- **NBA.com CDN**: NBA 官方赛程数据
- **Dashscope MCP**: AI 优化的网络搜索（中文优先）
- **阿里云 WebSearch**: 中文赛事数据
- **Tavily**: 深度搜索备用

## 推荐算法

比赛"值得看"的评分标准：
1. **用户关注球队**: 💚 ⭐⭐⭐⭐ (4星)
2. **普通比赛**: ⭐⭐ (2星)

## 依赖

```bash
pip install requests python-dateutil tavily-python
```

## 输出格式

### 终端文本输出

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

### Discord 消息格式

相同的文本格式，通过 webhook 推送到 Discord 频道。

## 集成示例

### Python 调用

```python
import subprocess
from datetime import datetime, timezone, timedelta

# 获取 UTC+8 当前日期
beijing_tz = timezone(timedelta(hours=8))
today = datetime.now(beijing_tz).strftime('%Y-%m-%d')

result = subprocess.run(
    ['python3', 'sports_station.py', '--date', today],
    capture_output=True,
    text=True
)
print(result.stdout)
```

### Cron 定时任务

```bash
# 每天早上 9 点推送（使用 date 命令获取当前日期）
0 9 * * * cd /path/to/sports-station && python3 sports_station.py --date $(date +\%Y-\%m-\%d) --push-discord
```

## 版本信息

**当前版本**: v4.0.3  
**更新日期**: 2026-03-13  
**作者**: Sports Station Team

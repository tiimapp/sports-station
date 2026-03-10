# 🏆 Sports Monitor - 体育赛事监控技能 v1.1.0

智能监控你感兴趣的体育赛事，推荐值得观看的精彩比赛！

## ✨ 功能特点

### 核心功能
- **NBA 赛程追踪**: 关注勇士队等指定球队的比赛
- **CBA 赛程追踪**: 支持广东宏远、辽宁本钢等球队
- **欧洲五大联赛**: 英超、西甲、意甲、德甲、法甲全覆盖
- **中超联赛**: 中国足球超级联赛支持
- **F1 一级方程式**: 大奖赛赛程 + 车队积分榜
- **奥运会/冬奥会**: 框架预留（数据源待实现）

### 智能功能
- **智能推荐算法**: 基于球队排名、对阵实力、用户兴趣自动评分
- **自然语言查询**: "今天周六，有哪些值得看的比赛？"
- **兴趣列表分离**: 系统配置与用户兴趣独立管理
- **多格式输出**: 终端文本、JSON、Discord/微信消息格式

## 🚀 快速开始

### 1. 获取 API Key

访问 [API-Sports](https://api-sports.io) 注册并获取免费 API Key（每月 100 次请求）

### 2. 安装依赖

```bash
cd ~/.agents/skills/sports-monitor
pip3 install -r requirements.txt --break-system-packages
```

### 3. 配置

```bash
# 系统配置（API Key 等）
cp config.example.json config.json
# 编辑 config.json，填入你的 API Key

# 兴趣列表（关注的球队/联赛）
cp interests.example.json interests.json
# 编辑 interests.json，配置你关注的球队和联赛
```

### 4. 使用

```bash
# 查看今天值得看的比赛
python3 sports_monitor.py --today

# 查看勇士队赛程
python3 sports_monitor.py --team "Golden State Warriors"

# 自然语言查询
python3 sports_monitor.py --query "今天周六，我想了解有哪些值得看的比赛"

# 检查配置
python3 sports_monitor.py --config-check
```

## 📋 使用示例

### 示例 1: 查询今日比赛
```bash
$ python3 sports_monitor.py --today

📅 今日赛事推荐 (2026-03-08)
==================================================

⚽ 欧洲五大联赛
----------------------------------------
⭐⭐⭐⭐⭐ 20:00 | Manchester City vs Liverpool
   📍 Etihad Stadium | 🏆 Premier League
   🔥 推荐指数：95/100

⭐⭐⭐⭐ 22:00 | Real Madrid vs Barcelona
   📍 Santiago Bernabéu | 🏆 La Liga
   🔥 推荐指数：88/100

🏀 NBA
----------------------------------------
⭐⭐⭐⭐⭐ 08:00 | Lakers @ Warriors
   📍 Chase Center
   🔥 推荐指数：90/100
```

### 示例 2: 关注球队赛程
```bash
$ python3 sports_monitor.py --team "Golden State Warriors"

📋 Golden State Warriors 近期赛程
==================================================

🕐 03-08 08:00 | 主场 vs Lakers
🕐 03-10 10:30 | 客场 @ Suns
🕐 03-12 09:00 | 主场 vs Celtics
```

### 示例 3: 自然语言查询
```bash
$ python3 sports_monitor.py --query "今天有哪些足球比赛"

📅 今日赛事推荐 (2026-03-08)
...
```

## ⚙️ 配置说明

### 系统配置 (config.json)

```json
{
  "api_key": "your-api-key-here",
  "language": "zh",
  "cache_enabled": false,
  "notifications": {
    "enabled": true,
    "channel": "discord",
    "remind_before_minutes": 60
  }
}
```

### 兴趣列表 (interests.json)

```json
{
  "version": "1.1.0",
  "sports": {
    "nba": {
      "enabled": true,
      "teams": ["Golden State Warriors", "Lakers"],
      "priority": "high"
    },
    "cba": {
      "enabled": true,
      "teams": ["广东宏远", "辽宁本钢"],
      "priority": "high"
    },
    "soccer_europe": {
      "enabled": true,
      "leagues": ["premier_league", "la_liga"],
      "teams": ["Real Madrid", "Barcelona"],
      "priority": "high"
    },
    "soccer_china": {
      "enabled": true,
      "leagues": ["csl"],
      "teams": [],
      "priority": "medium"
    },
    "f1": {
      "enabled": true,
      "teams": ["Red Bull Racing", "Mercedes"],
      "priority": "medium"
    },
    "olympics": {
      "enabled": true,
      "types": ["summer", "winter"],
      "sports": ["basketball", "diving", "table-tennis"],
      "priority": "high"
    }
  }
}
```

### 优先级说明

| 优先级 | 说明 | 推荐指数加成 |
|--------|------|-------------|
| high | 高度关注，必看赛事 | +10 分 |
| medium | 一般关注，有空就看 | +5 分 |
| low | 低优先级 | 无加成 |

## 🎯 推荐算法

比赛评分标准 (0-100 分):

| 因素 | 加分 |
|------|------|
| 基础分 | 50 |
| 用户关注球队 | +25 |
| 联赛前 4 名 | +30 |
| 联赛前 8 名 | +20 |
| 强强对话 (双方前 6) | +20 |
| 排名接近 (相差≤3) | +10 |

**评分解读**:
- ⭐⭐⭐⭐⭐ (80-100): 必看经典战
- ⭐⭐⭐⭐ (60-79): 值得关注
- ⭐⭐⭐ (40-59): 普通比赛
- ⭐⭐ (20-39): 一般比赛
- ⭐ (0-19): 不推荐

## 🔌 集成到 OpenClaw

在 OpenClaw 中调用:

```python
import subprocess
result = subprocess.run(
    ['python3', '~/.agents/skills/sports-monitor/sports_monitor.py', '--today'],
    capture_output=True,
    text=True
)
print(result.stdout)
```

或通过 cron 定时推送:

```bash
# 每天早上 9 点推送今日比赛
0 9 * * * python3 ~/.agents/skills/sports-monitor/sports_monitor.py --today >> /tmp/sports.log
```

## 📝 待开发功能

- [ ] 指定日期查询 (--date)
- [ ] 比赛提醒通知
- [ ] 实时比分推送
- [ ] 更多体育项目 (NFL, F1, 网球)
- [ ] 中文解说频道信息

## 🙏 致谢

数据源：[API-Sports](https://api-sports.io)

---

**作者**: ClawBot  
**版本**: 1.0.0  
**许可**: MIT

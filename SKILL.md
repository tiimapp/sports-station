# Sports Monitor Skill - 体育赛事监控

监控用户感兴趣的体育赛事赛程，智能推荐值得观看的比赛。

## 功能

- **NBA 监控**: 跟踪指定球队（如勇士队）的比赛
- **欧洲五大联赛**: 英超、西甲、意甲、德甲、法甲关键场次
- **智能推荐**: 基于球队排名、对阵双方实力、比赛重要性推荐"值得看"的比赛
- **日期查询**: 查询特定日期（如"今天"、"周六"）的比赛

## 使用方式

```bash
# 查看今天值得看的比赛
python3 sports_monitor.py --today

# 查看指定日期的比赛
python3 sports_monitor.py --date 2026-03-08

# 查看勇士队近期赛程
python3 sports_monitor.py --team "Golden State Warriors" --sport nba

# 查看欧洲五大联赛本周末比赛
python3 sports_monitor.py --league "五大联赛" --weekend

# 交互式查询（自然语言）
python3 sports_monitor.py --query "今天周六，我想了解有哪些值得看的比赛"
```

## 配置

在 `config.json` 中设置：

```json
{
  "api_key": "your-api-sports-key",
  "favorite_teams": {
    "nba": ["Golden State Warriors", "Los Angeles Lakers"],
    "soccer": ["Real Madrid", "Barcelona", "Manchester City"]
  },
  "leagues": {
    "nba": "12",
    "premier_league": "39",
    "la_liga": "140",
    "serie_a": "135",
    "bundesliga": "78",
    "ligue_1": "61"
  }
}
```

## API 数据源

- **API-Sports** (https://api-sports.io): NBA + 足球赛程、比分、排名
- **The Odds API** (备选): 赔率数据辅助判断比赛重要性

## 推荐算法

比赛"值得看"的评分标准：
1. **球队实力**: 联赛排名靠前的球队
2. **对阵双方**: 强队 vs 强队 = 高分
3. **比赛重要性**: 争冠、保级、德比战
4. **用户兴趣**: 用户关注的球队比赛加权

## 依赖

```bash
pip install requests python-dateutil
```

## 输出格式

支持：
- 终端文本输出
- JSON 格式（用于其他程序调用）
- Discord/微信消息格式

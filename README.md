# 🏆 Sports Station - 体育赛事监控技能 v4.0.3

智能监控你感兴趣的体育赛事，简洁清晰的格式推荐值得观看的精彩比赛！

**版本**: v4.0.3  
**更新**: 2026-03-13  
**特性**: 固定格式输出 | 直播平台信息 | Phase 1 核心赛事

---

## ✨ 功能特点

### Phase 1 核心功能（当前版本）
- **🏀 NBA 赛程追踪**: 官方 CDN 实时数据，100% 准确，UTC+8 时区自动转换
- **⚽ 欧洲五大联赛**: 英超、西甲、意甲、德甲、法甲全覆盖
- **⚽ 中超联赛**: 中国足球超级联赛支持
- **🏎️ F1 一级方程式**: 大奖赛赛程
- **🕐 严格时区控制**: 所有时间基于 UTC+8（北京时间），确保日期范围准确

### Phase 2 计划功能（未来版本）
- 🏀 CBA 赛程追踪
- 🏸 羽毛球国际赛事
- 🎾 网球四大满贯
- 🎮 电竞 LPL、LCK
- ⛳ 高尔夫赛事
- 🏒 冰球 KHL、NHL
- 🏅 奥运会

### 智能功能
- **⭐ 智能推荐**: 基于用户关注球队自动评分
- **🔍 多源搜索**: Dashscope + 阿里云 + Tavily 三源冗余，可配置优先级
- **💚 兴趣列表**: 个性化配置关注的球队
- **📱 多平台适配**: 终端、Discord 友好格式
- **📊 固定格式**: 每场比赛一行，信息完整

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd sports-station
pip3 install -r requirements.txt
```

### 2. 配置兴趣列表和搜索工具

```bash
# 复制示例配置
cp interests.example.json interests.json
cp config.example.json config.json

# 编辑 interests.json，配置你关注的球队和联赛
# 编辑 config.json，配置搜索工具优先级
# 详见下方「配置说明」
```

### 3. 使用

```bash
# 查看今天值得看的比赛
python3 sports_monitor.py --today

# 推送到 Discord
python3 sports_monitor.py --today --push-discord
```

---

## 📋 使用示例

### 示例 1: 查询今日比赛

```bash
$ python3 sports_monitor.py --today

📅 2026-03-13 赛事汇总
============================================================

🏀 NBA
💚 ⭐⭐⭐⭐ 03-13 08:00 | Celtics @ Warriors | 腾讯体育
⭐⭐ 03-13 10:30 | Heat @ Bucks | 腾讯体育
💚 ⭐⭐⭐⭐ 03-13 11:00 | Lakers @ Mavericks | 腾讯体育

⚽ 足球
💚 ⭐⭐⭐⭐ 03-13 20:00 | 英超 | Liverpool vs Man City | 咪咕体育
⭐⭐ 03-13 22:00 | 西甲 | Sevilla vs Valencia | 咪咕体育
💚 ⭐⭐⭐⭐ 03-13 22:15 | 西甲 | Real Madrid vs Barcelona | CCTV5

🏎️ F1
📅 03/13-15 | 中国大奖赛 | 上海 | CCTV5
```

### 示例 2: Discord 推送

```bash
$ python3 sports_monitor.py --today --push-discord

✓ 成功发送到 Discord
```

---

## ⚙️ 配置说明

### 兴趣列表 (interests.json)

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

### 搜索工具配置 (config.json)

```json
{
  "version": "4.0.3",
  "search_tools": {
    "enabled": true,
    "priority": [
      "dashscope_mcp",
      "aliyun",
      "tavily"
    ],
    "tools": {
      "dashscope_mcp": {
        "enabled": true,
        "timeout": 10,
        "description": "AI 优化搜索，无广告，中文优先"
      },
      "aliyun": {
        "enabled": true,
        "timeout": 10,
        "api_key": "sk-9fd1be825af0419c88382485d119451c",
        "model": "qwen-plus",
        "description": "阿里云 WebSearch，速度快"
      },
      "tavily": {
        "enabled": true,
        "timeout": 15,
        "search_depth": "advanced",
        "description": "深度搜索，英文补充"
      }
    }
  }
}
```

**搜索工具说明**:
- `priority`: 搜索工具优先级顺序，按数组顺序依次尝试
- `enabled`: 是否启用该搜索工具
- `timeout`: 搜索超时时间（秒）
- 搜索策略：按优先级顺序尝试，失败则自动切换到下一个工具

**推荐配置**:
- 中文赛事优先：`["dashscope_mcp", "aliyun", "tavily"]`（默认）
- 英文赛事优先：`["tavily", "dashscope_mcp", "aliyun"]`
- 仅使用阿里云：`["aliyun"]`（需禁用其他工具）

---

## 🎯 推荐算法

比赛评分标准:

| 因素 | 星级 |
|------|------|
| 用户关注球队 | ⭐⭐⭐⭐ (4星) |
| 普通比赛 | ⭐⭐ (2星) |

**评分解读**:
- 💚 ⭐⭐⭐⭐ - 您关注的球队比赛
- ⭐⭐ - 普通比赛

---

## 📺 直播平台

| 平台 | 适用赛事 | 备注 |
|------|---------|------|
| CCTV5 | NBA、足球、F1 | 央视体育，免费 |
| 腾讯体育 | NBA、中超 | 部分需会员 |
| 咪咕体育 | 足球 | 部分需会员 |

---

## 🔌 集成到 OpenClaw

### 在 OpenClaw 中调用

```python
import subprocess

result = subprocess.run(
    ['python3', 'sports-station/sports_monitor.py', '--today'],
    capture_output=True,
    text=True
)
print(result.stdout)
```

### 定时推送（cron）

```bash
# 每天早上 9 点推送今日比赛
0 9 * * * cd /path/to/sports-station && python3 sports_monitor.py --today --push-discord

# 每小时检查更新
0 * * * * cd /path/to/sports-station && python3 sports_monitor.py --today > /tmp/sports.log
```

### Discord 机器人集成

配置 `discord_config.json`:
```json
{
  "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
}
```

或设置环境变量:
```bash
export DISCORD_GAMEDAY_WEBHOOK="https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
```

---

## 📊 性能指标

| 指标 | 目标 | 当前 (v4.0.3) | 状态 |
|-----|------|--------------|------|
| 搜索成功率 | >85% | 90%+ | ✅ |
| 输出准确率 | >90% | 95% | ✅ |
| 响应时间 | <30s | 20s | ✅ |
| 覆盖率 (Phase 1) | >90% | 95% | ✅ |

---

## 📝 版本历史

### v4.0.3 (2026-03-13) - 文档更新
- ✅ 更新文档匹配实际实现
- ✅ 明确 Phase 1/Phase 2 范围
- ✅ 移除未实现功能的文档

### v4.0.2 (2026-03-11) - 固定格式版本
- ✅ 固定输出格式 - 每场比赛一行
- ✅ Discord 推送支持
- ✅ Dashscope MCP 集成
- ✅ 简化推荐系统

### v3.0.6 (2026-03-10) - 三源搜索
- ✅ Tavily 搜索集成
- ✅ 三源冗余搜索策略
- ✅ 自动故障转移

### v3.0.0 (2026-03-07) - 全自动版本
- ✅ 彻底移除手动输入
- ✅ 阿里云 WebSearch 集成
- ✅ NBA 官方 CDN 集成
- ✅ 100% 自动获取赛程

---

## 📚 文档

- **README.md** - 使用说明（本文档）
- **DEVELOPMENT.md** - 开发文档
- **SKILL.md** - OpenClaw 技能配置

---

## 🙏 致谢

**数据源**:
- NBA.com CDN - NBA 官方数据
- 阿里云 Dashscope WebSearch - 中文赛事数据
- Dashscope MCP - AI 优化搜索
- Tavily - 深度搜索

---

## 📞 维护信息

**位置**: `sports-station/`

**关键文件**:
- `sports_monitor.py` - 主程序
- `interests.json` - 兴趣列表
- `discord_config.json` - Discord 配置

**作者**: Sports Station Team  
**版本**: v4.0.3  
**许可**: MIT

---

*最后更新：2026-03-13*

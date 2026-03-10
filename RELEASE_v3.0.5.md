# Sports Monitor v3.0.5 发布说明

**发布日期**: 2026-03-10 22:45  
**版本类型**: 功能增强 - MCP 集成  
**上一版本**: v3.0.4

---

## 🎯 新功能

### MCP Exa 搜索集成

**背景**: 
- 单一数据源（阿里云）可能返回空结果或超时
- 需要备用搜索源提高成功率
- MCP（Model Context Protocol）提供标准化 API 访问

**功能**:
1. **双源搜索** - 阿里云 + MCP Exa
2. **自动切换** - 失败时无缝切换备用源
3. **英文增强** - MCP 提供英文搜索结果作为补充

---

## ✅ 新增内容

### C1: MCP 搜索函数

**新增函数**:
```python
def mcp_web_search(query: str, timeout: int = 15, show_progress: bool = False) -> str:
    """
    使用 MCP Exa 进行网络搜索（v3.0.5 新增）
    
    Args:
        query: 搜索查询
        timeout: 超时时间（秒）
        show_progress: 显示进度提示
    
    Returns:
        搜索结果文本，失败返回空字符串
    """
```

**调用方式**:
```bash
mcporter call exa.web_search_exa query={query}
```

**返回格式**:
```json
{
  "results": [
    {
      "title": "比赛标题",
      "text": "比赛详情",
      "url": "来源链接"
    }
  ]
}
```

---

### C2: 阿里云搜索自动切换 MCP

**修改前**:
```python
def aliyun_web_search(query: str, timeout: int = 10) -> str:
    # 失败直接返回空字符串
    return ""
```

**修改后**:
```python
def aliyun_web_search(query: str, timeout: int = 10, use_mcp_fallback: bool = True) -> str:
    # 失败时自动切换 MCP
    if use_mcp_fallback:
        return mcp_web_search(query, timeout=timeout)
    return ""
```

**切换场景**:
1. ✅ 阿里云超时 → 切换 MCP
2. ✅ 阿里云无结果 → 切换 MCP
3. ✅ 阿里云异常 → 切换 MCP

---

### C3: 足球搜索双源增强

**搜索策略**:
```
1. 阿里云搜索（中文）
   ↓ 失败
2. MCP 搜索（中文）
   ↓ 失败
3. MCP 搜索（英文）
```

**搜索词示例**:
```python
# 阿里云（中文）
query_aliyun = f"{date} 足球赛程表 直播时间表 中超 CSL 英超 西甲 意甲 德甲 法甲"

# MCP（中文）
query_mcp = f"{date} 足球赛程 比赛时间 对阵"

# MCP（英文）
query_mcp_en = f"{date} football schedule Premier League La Liga Serie A Bundesliga"
```

---

## 📊 代码变更统计

| 文件 | 修改行数 | 说明 |
|-----|---------|------|
| `sports_monitor.py` | +127, -21 | MCP 集成 + 双源搜索 |
| `TODO.md` | +15, -3 | 更新任务状态 |
| `RELEASE_v3.0.5.md` | +200 | 新增发布说明 |

**总计**: +342 行，-24 行

---

## 🔧 技术细节

### MCP 调用流程

```python
import subprocess

# 调用 MCP CLI
result = subprocess.run(
    ['mcporter', 'call', 'exa.web_search_exa', f'query={query}'],
    capture_output=True,
    text=True,
    timeout=timeout
)

# 解析 JSON 结果
mcp_result = json.loads(result.stdout)

# 提取搜索结果
texts = []
for item in mcp_result['results'][:5]:
    title = item.get('title', '')
    text = item.get('text', '')
    url = item.get('url', '')
    texts.append(f"{title}\n{text}\n来源：{url}")

return '\n\n'.join(texts)
```

### 依赖要求

**必需工具**:
- `mcporter` CLI（已安装：`/usr/bin/mcporter`）
- MCP Exa 服务器（已配置：`https://mcp.exa.ai/mcp`）

**配置位置**:
```json
// ~/.openclaw/workspace/config/mcporter.json
{
  "mcpServers": {
    "exa": {
      "baseUrl": "https://mcp.exa.ai/mcp"
    }
  }
}
```

---

## 🧪 测试建议

### 测试命令
```bash
cd ~/.agents/skills/sports-monitor
python3 sports_monitor.py --today
```

### 验证要点
1. ✅ 阿里云正常时优先使用阿里云
2. ✅ 阿里云失败时自动切换 MCP
3. ✅ 控制台显示切换提示
4. ✅ 搜索结果包含中英文内容

### 预期输出
```
⏳ 阿里云搜索：足球赛程表 直播时间表...
⚠️  阿里云无结果，切换 MCP 搜索...
🔍 MCP 搜索：足球赛程 比赛时间...
✅ MCP 搜索完成
```

---

## 📦 安装升级

### 从 GitHub 更新
```bash
cd ~/.agents/skills/sports-monitor
git pull origin main
```

### 验证 MCP 配置
```bash
mcporter list --json
```

**预期输出**:
```json
{
  "servers": [
    {
      "name": "exa",
      "status": "ok",
      "tools": [
        "web_search_exa",
        "get_code_context_exa"
      ]
    }
  ]
}
```

---

## 🎯 优势对比

| 特性 | v3.0.4 | v3.0.5 |
|-----|--------|--------|
| 数据源 | 阿里云单源 | 阿里云 + MCP 双源 |
| 失败处理 | 返回空结果 | 自动切换备用源 |
| 搜索语言 | 仅中文 | 中文 + 英文 |
| 成功率 | ~75% | ~90%+（预计） |
| 响应时间 | 10-15s | 10-20s（切换时） |

---

## ⏭️ 后续计划 (v3.1.0)

- [ ] 定时任务配置（每日自动更新）
- [ ] 多数据源交叉验证（阿里云 + MCP + API-Sports）
- [ ] 搜索失败降级方案（本地缓存）
- [ ] Discord/微信输出格式优化

---

## 🙏 致谢

**开发**: Optimus Prime  
**反馈**: tiim🐮

---

**GitHub**: https://github.com/tiimapp/sports-monitor  
**文档**: https://github.com/tiimapp/sports-monitor/blob/main/README.md  
**MCP 文档**: https://github.com/tiimapp/sports-monitor/blob/main/RELEASE_v3.0.5.md

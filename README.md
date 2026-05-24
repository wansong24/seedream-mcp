# 🏍 Seedream MCP Server

> 火山引擎 Seedream 5.0 图片生成 MCP 连接器
> 让 Claude Desktop 在需要生图时**自动调用** Seedream AI，无需手动操作。

## ✨ 功能

| 工具 | 说明 |
|------|------|
| `seedream_generate_image` | 文字生图，生成单张高质量图片 |
| `seedream_generate_batch` | 批量生图，同一 prompt 并行生成多张供选择 |
| `seedream_list_sizes` | 查看所有支持的图片尺寸及适用场景 |

配置完成后，直接对 Claude 说「帮我生成一张...的图片」，Claude 就会自动调用 Seedream 5.0 生成并保存到本地。

## 📐 支持的图片尺寸

| 尺寸 | 比例 | 适用场景 |
|------|------|----------|
| **2048×2048** | 1:1 | 社交头像、封面（⭐ 推荐） |
| **2560×1440** | 16:9 | 视频封面、PPT 背景 |
| **1440×2560** | 9:16 | 手机壁纸、短视频封面 |
| **2400×1600** | 3:2 | 横版摄影风配图 |
| **1600×2400** | 2:3 | 竖版海报、书籍封面 |
| **2560×1080** | 21:9 | 超宽横幅、网站顶图 |
| **1920×1920** | 1:1 | 标准正方形大图 |

> ⚠️ Seedream 5.0 Lite 要求最小像素数 **3,686,400**，低于此要求会报错。

## 🚀 安装步骤

### 第一步：获取火山引擎 API 凭证

1. 登录 [火山引擎方舟控制台](https://console.volcengine.com/ark)
2. **开通管理 → 视觉模型** → 找到 `Doubao-Seedream-5.0-lite` → 点击「开通服务」
3. **在线推理 → 创建推理接入点** → 选 Seedream-5.0-lite → 创建后复制 `ep-xxx` ID
4. **API Key 管理 → 创建 API Key** → 复制 Key

### 第二步：安装 Python 依赖

```bash
# 需要 Python 3.10+（推荐用 Homebrew 安装）
brew install python@3.12

# 创建虚拟环境
python3 -m venv ~/.seedream_venv
source ~/.seedream_venv/bin/activate

# 安装依赖
pip install "mcp[cli]" openai
```

### 第三步：下载脚本

```bash
mkdir -p ~/.seedream
curl -o ~/.seedream/seedream_mcp_server.py \
  https://raw.githubusercontent.com/wansong24/seedream-mcp/main/seedream_mcp_server.py
```

### 第四步：配置 Claude Desktop

打开（或创建）配置文件：

**macOS**：`~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "seedream": {
      "command": "/opt/homebrew/bin/python3.12",
      "args": ["/Users/你的用户名/.seedream/seedream_mcp_server.py"],
      "env": {
        "ARK_API_KEY": "你的-API-Key",
        "ARK_MODEL_ID": "ep-你的接入点ID",
        "ARK_BASE_URL": "https://ark.cn-beijing.volces.com/api/v3",
        "IMAGE_SAVE_DIR": "/Users/你的用户名/Desktop/seedream_images"
      }
    }
  }
}
```

### 第五步：重启 Claude Desktop

完全退出并重新打开 Claude Desktop，即可生效。

## 💬 使用示例

```
帮我生成一张夕阳下停在山顶的摩托车图片，电影质感
帮我生成 3 张科技感头像供选择
帮我生成一张 16:9 的 PPT 背景图，深蓝色科技风
```

## ⚙️ 环境变量

| 变量 | 说明 | 是否必填 |
|------|------|----------|
| `ARK_API_KEY` | 火山引擎 API Key | ✅ 必填 |
| `ARK_MODEL_ID` | 推理接入点 ID（ep-xxx） | ✅ 必填 |
| `ARK_BASE_URL` | API 地址（默认北京区） | 可选 |
| `IMAGE_SAVE_DIR` | 图片保存目录（默认桌面） | 可选 |

## 📦 依赖

```
mcp[cli] >= 1.0
openai >= 1.0
Python >= 3.10
```

## 📄 许可证

MIT License

---

> 由 [Claude](https://claude.ai) + [Seedream 5.0](https://www.volcengine.com/docs/82379) 驱动

# 🏍 Seedream MCP Server

> 火山引擎 Seedream 5.0 图片生成 MCP 连接器，让 Claude Desktop 直接调用 Seedream AI 生成图片。

## 功能介绍

- 📸 **文字生图**：用中文或英文描述，Seedream 5.0 直接生成高质量图片
- 📐 **多种尺寸**：支持 11 种尺寸，从正方形到宽屏、竖屏、手机屏幕比例均可
- 💾 **本地保存**：生成的图片自动保存到你指定的本地目录
- 🔌 **MCP 协议**：标准 MCP 接口，与 Claude Desktop 无缝集成

## 效果展示

在 Claude Desktop 中说「帮我生成一张夕阳下的摩托车图片」，Claude 会自动调用本服务，生成图片并保存到本地。

## 安装步骤

### 第一步：获取火山引擎 API 凭证

1. 登录 [火山引擎控制台](https://console.volcengine.com/ark)
2. 进入「开通管理」→「视觉模型」，找到 **Doubao-Seedream-5.0-lite**，点击「开通服务」
3. 进入「在线推理」→「创建推理接入点」，选择 Seedream-5.0-lite，创建后复制 `ep-xxx` 格式的接入点 ID
4. 进入「API Key 管理」→「创建 API Key」，复制生成的 Key

### 第二步：安装 Python 依赖

打开终端，运行以下命令：

```bash
# 创建虚拟环境（推荐）
python3 -m venv ~/.seedream_venv
source ~/.seedream_venv/bin/activate

# 安装依赖
pip install "mcp[cli]" openai
```

### 第三步：下载 MCP Server 脚本

```bash
mkdir -p ~/.seedream
curl -o ~/.seedream/seedream_mcp_server.py \
  https://raw.githubusercontent.com/wansong24/seedream-mcp/main/seedream_mcp_server.py
```

### 第四步：配置 Claude Desktop

找到 Claude Desktop 配置文件（macOS 路径）：

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

添加以下内容（替换为你自己的 Key 和 Endpoint ID）：

```json
{
  "mcpServers": {
    "seedream": {
      "command": "/path/to/your/python3",
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

完全退出并重新打开 Claude Desktop，配置即可生效。

## 使用方法

配置完成后，直接在 Claude Desktop 对话框中用自然语言描述你想要的图片：

```
帮我生成一张夜晚城市霓虹灯的摩托车图片，1024x1024
帮我生成一张产品宣传图，背景是海边日落，16:9比例
```

## 支持的图片尺寸

| 比例 | 尺寸 | 适用场景 |
|------|------|----------|
| 1:1  | 1024×1024 | 社交媒体头像、封面 |
| 1:1  | 2048×2048 | 高清正方形大图 |
| 16:9 | 1280×720  | 视频封面、PPT背景 |
| 9:16 | 720×1280  | 手机竖屏、短视频封面 |
| 4:3  | 1152×864  | 横版配图 |
| 3:4  | 864×1152  | 竖版配图、书籍封面 |
| 3:2  | 1248×832  | 摄影风格横图 |
| 2:3  | 832×1248  | 摄影风格竖图 |
| 21:9 | 1512×648  | 超宽屏横幅 |

> ⚠️ **注意**：Seedream-5.0-lite 要求图片最小像素数为 3,686,400（约 2048×2048），推荐使用 2048×2048 尺寸。

## 可用工具

| 工具名 | 功能 |
|--------|------|
| `generate_image` | 根据文字描述生成图片 |
| `list_supported_sizes` | 列出所有支持的图片尺寸 |

## 环境变量说明

| 变量名 | 说明 | 必填 |
|--------|------|------|
| `ARK_API_KEY` | 火山引擎 API Key | ✅ |
| `ARK_MODEL_ID` | 推理接入点 ID（ep-xxx格式） | ✅ |
| `ARK_BASE_URL` | API 基础地址 | 可选（有默认值） |
| `IMAGE_SAVE_DIR` | 图片保存目录 | 可选（默认桌面） |

## 依赖

- Python 3.10+
- `mcp[cli]` >= 1.0
- `openai` >= 1.0

## 许可证

MIT License

## 关于 Seedream

Seedream 是字节跳动旗下即梦平台的图片生成模型，通过火山引擎方舟平台提供 API 服务。

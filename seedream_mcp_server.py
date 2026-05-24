#!/usr/bin/env python3
"""
seedream_mcp — 火山引擎 Seedream 图片生成 MCP Server

通过火山引擎方舟 API 提供 AI 图片生成能力，让 Claude 在需要生图时直接调用。
支持文字生图、批量生图等功能。

环境变量：
    ARK_API_KEY    火山引擎 API Key（必填）
    ARK_MODEL_ID   推理接入点 ID，格式 ep-xxx（必填）
    ARK_BASE_URL   API 地址（可选，默认北京区）
    IMAGE_SAVE_DIR 图片保存目录（可选，默认桌面）
"""

import os
import sys
import json
import base64
import asyncio
import logging
import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP
from openai import AsyncOpenAI

# ── 日志（输出到 stderr，不污染 stdio 协议）────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("seedream_mcp")

# ── 常量 ──────────────────────────────────────────────────────────────────────
ARK_BASE_URL   = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
ARK_API_KEY    = os.environ.get("ARK_API_KEY", "")
ARK_MODEL_ID   = os.environ.get("ARK_MODEL_ID", "")
IMAGE_SAVE_DIR = os.environ.get("IMAGE_SAVE_DIR", str(Path.home() / "Desktop" / "seedream_images"))

# Seedream 5.0 Lite 最小像素要求：3,686,400 px（约 1920×1920）
VALID_SIZES = [
    "2048x2048",  # 1:1  推荐（最高清）
    "2560x1440",  # 16:9 视频封面、PPT
    "1440x2560",  # 9:16 手机竖屏、短视频
    "2400x1600",  # 3:2  横版摄影风
    "1600x2400",  # 2:3  竖版摄影风
    "2560x1080",  # 21:9 超宽横幅
    "1920x1920",  # 1:1  标准大图
]

# ── MCP 服务 ──────────────────────────────────────────────────────────────────
mcp = FastMCP("seedream_mcp")


# ── 枚举 & Pydantic 模型 ───────────────────────────────────────────────────────
class ImageSize(str, Enum):
    """支持的图片尺寸（Seedream 5.0 Lite 要求最小 3,686,400 像素）"""
    SQ_2048  = "2048x2048"
    W_2560   = "2560x1440"
    H_1440   = "1440x2560"
    W_2400   = "2400x1600"
    H_1600   = "1600x2400"
    UW_2560  = "2560x1080"
    SQ_1920  = "1920x1920"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON     = "json"


class GenerateImageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    prompt: str = Field(..., description="图片描述，支持中英文。越详细效果越好。", min_length=2, max_length=2000)
    size: ImageSize = Field(default=ImageSize.SQ_2048, description="图片尺寸。2048x2048=正方形(推荐); 2560x1440=16:9宽屏; 1440x2560=9:16竖屏")
    seed: int = Field(default=-1, description="随机种子。-1 表示随机；指定相同种子可复现相似结果。", ge=-1)
    watermark: bool = Field(default=False, description="是否添加水印，默认不添加。")
    file_prefix: str = Field(default="seedream", description="保存文件的名称前缀，仅限英文字母、数字和下划线。", pattern=r"^[a-zA-Z0-9_]+$", max_length=50)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="返回格式：markdown 或 json")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt 不能为空")
        return v.strip()


class GenerateBatchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    prompt: str = Field(..., description="图片描述，支持中英文。", min_length=2, max_length=2000)
    count: int = Field(default=3, description="生成图片数量，1-6 张。", ge=1, le=6)
    size: ImageSize = Field(default=ImageSize.SQ_2048, description="图片尺寸，同 seedream_generate_image。")
    watermark: bool = Field(default=False, description="是否添加水印，默认不添加。")
    file_prefix: str = Field(default="batch", description="文件名前缀。", pattern=r"^[a-zA-Z0-9_]+$", max_length=50)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt 不能为空")
        return v.strip()


# ── 共享工具函数 ───────────────────────────────────────────────────────────────
def _get_client() -> AsyncOpenAI:
    if not ARK_API_KEY:
        raise RuntimeError("ARK_API_KEY 未设置。请在 claude_desktop_config.json 的 env 中添加该变量。")
    if not ARK_MODEL_ID:
        raise RuntimeError("ARK_MODEL_ID 未设置。请在火山引擎控制台创建推理接入点，获取 ep-xxx 格式 ID。")
    return AsyncOpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)


def _ensure_save_dir() -> Path:
    save_dir = Path(IMAGE_SAVE_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def _save_image(b64_data: str, prefix: str, save_dir: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]
    filepath = save_dir / f"{prefix}_{ts}.png"
    filepath.write_bytes(base64.b64decode(b64_data))
    return filepath


def _handle_api_error(e: Exception) -> str:
    msg = str(e)
    if "InvalidParameter" in msg and "size" in msg:
        return f"❌ 图片尺寸不符合要求。Seedream 5.0 Lite 要求最小 3,686,400 像素。\n请使用以下尺寸之一：{', '.join(VALID_SIZES)}"
    if "InvalidParameter" in msg and "guidance_scale" in msg:
        return "❌ 当前模型不支持 guidance_scale 参数，已自动跳过。"
    if "401" in msg or "Unauthorized" in msg or "authentication" in msg.lower():
        return "❌ API Key 验证失败。请检查 ARK_API_KEY 是否正确，并确认火山引擎账户有足够余额。"
    if "404" in msg or "model" in msg.lower():
        return "❌ 模型接入点不存在。请检查 ARK_MODEL_ID 格式是否为 ep-xxx，并确认已在火山引擎控制台创建对应的推理接入点。"
    if "429" in msg or "rate" in msg.lower():
        return "❌ 请求过于频繁，请稍等片刻再试。"
    if "timeout" in msg.lower():
        return "❌ 请求超时。图片生成通常需要 10-30 秒，请重试。"
    return f"❌ 生成失败：{msg}"


# ── 工具：文字生图 ─────────────────────────────────────────────────────────────
@mcp.tool(
    name="seedream_generate_image",
    annotations={"title": "Seedream AI 文字生图", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def seedream_generate_image(params: GenerateImageInput) -> str:
    """
    使用 Seedream 5.0 根据文字描述生成一张图片，并保存到本地。
    每当需要生成图片、插图、背景图、封面图时请调用此工具。
    """
    logger.info(f"生成图片 | size={params.size.value} | prompt={params.prompt[:50]}...")
    try:
        client = _get_client()
        save_dir = _ensure_save_dir()
        extra_body: dict = {"size": params.size.value, "watermark": params.watermark}
        if params.seed != -1:
            extra_body["seed"] = params.seed
        response = await client.images.generate(
            model=ARK_MODEL_ID,
            prompt=params.prompt,
            response_format="b64_json",
            extra_body=extra_body,
        )
        b64 = response.data[0].b64_json
        filepath = _save_image(b64, params.file_prefix, save_dir)
        logger.info(f"图片已保存：{filepath}")
        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"path": str(filepath), "filename": filepath.name, "prompt": params.prompt, "size": params.size.value, "seed": params.seed}, ensure_ascii=False, indent=2)
        return (
            f"## ✅ 图片生成成功\n\n"
            f"- **文件路径**：`{filepath}`\n"
            f"- **尺寸**：{params.size.value}\n"
            f"- **Prompt**：{params.prompt[:100]}{'...' if len(params.prompt) > 100 else ''}\n"
            f"- **种子**：{params.seed if params.seed != -1 else '随机'}\n"
        )
    except Exception as e:
        logger.error(f"生成失败：{e}")
        return _handle_api_error(e)


# ── 工具：批量生图 ─────────────────────────────────────────────────────────────
@mcp.tool(
    name="seedream_generate_batch",
    annotations={"title": "Seedream AI 批量生图", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": True},
)
async def seedream_generate_batch(params: GenerateBatchInput) -> str:
    """
    使用 Seedream 5.0 批量生成多张图片（同一 prompt，并行生成）。
    当用户需要多个版本供选择时使用。
    """
    logger.info(f"批量生图 | count={params.count} | size={params.size.value}")
    try:
        client = _get_client()
        save_dir = _ensure_save_dir()
        extra_body_base: dict = {"size": params.size.value, "watermark": params.watermark}

        async def _generate_one(index: int) -> tuple[int, Optional[Path], Optional[str]]:
            try:
                response = await client.images.generate(
                    model=ARK_MODEL_ID, prompt=params.prompt,
                    response_format="b64_json", extra_body=extra_body_base,
                )
                b64 = response.data[0].b64_json
                filepath = _save_image(b64, f"{params.file_prefix}_{index + 1:02d}", save_dir)
                return index, filepath, None
            except Exception as e:
                return index, None, str(e)

        results = await asyncio.gather(*[_generate_one(i) for i in range(params.count)])
        success_count = sum(1 for _, fp, _ in results if fp is not None)
        lines = [f"## ✅ 批量生图完成（{success_count}/{params.count} 成功）\n"]
        for idx, filepath, error in sorted(results, key=lambda x: x[0]):
            if filepath:
                lines.append(f"{idx + 1}. `{filepath}` — {params.size.value}")
            else:
                lines.append(f"{idx + 1}. ❌ 失败：{_handle_api_error(Exception(error))}")
        if success_count < params.count:
            lines.append(f"\n> ⚠️ {params.count - success_count} 张生成失败，其余已保存成功。")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"批量生图失败：{e}")
        return _handle_api_error(e)


# ── 工具：列出支持的尺寸 ───────────────────────────────────────────────────────
@mcp.tool(
    name="seedream_list_sizes",
    annotations={"title": "列出 Seedream 支持的图片尺寸", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def seedream_list_sizes() -> str:
    """列出 Seedream 5.0 Lite 支持的所有图片尺寸及适用场景。"""
    return (
        "## Seedream 5.0 支持的图片尺寸\n\n"
        "> ⚠️ Seedream 5.0 Lite 最小像素要求：**3,686,400 px**（约 1920×1920）\n\n"
        "| 尺寸 | 比例 | 像素数 | 适用场景 |\n"
        "|------|------|--------|----------|\n"
        "| **2048×2048** | 1:1 | 4,194,304 | 社交头像、封面、通用（⭐ 推荐默认） |\n"
        "| **2560×1440** | 16:9 | 3,686,400 | 视频封面、PPT背景、横幅广告 |\n"
        "| **1440×2560** | 9:16 | 3,686,400 | 手机壁纸、短视频封面、竖版海报 |\n"
        "| **2400×1600** | 3:2 | 3,840,000 | 横版摄影风、新闻配图 |\n"
        "| **1600×2400** | 2:3 | 3,840,000 | 竖版摄影风、书籍封面 |\n"
        "| **2560×1080** | 21:9 | 2,764,800 | 超宽横幅、网站顶部图 |\n"
        "| **1920×1920** | 1:1 | 3,686,400 | 标准正方形大图 |\n"
    )


# ── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("seedream_mcp 启动")
    logger.info(f"模型接入点：{ARK_MODEL_ID or '⚠️ 未设置 ARK_MODEL_ID'}")
    logger.info(f"图片保存目录：{IMAGE_SAVE_DIR}")
    mcp.run(transport="stdio")

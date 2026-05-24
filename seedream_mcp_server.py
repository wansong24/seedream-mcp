#!/usr/bin/env python3
"""
Seedream MCP Server
调用火山引擎方舟 API 的 Seedream 5.0 图片生成 MCP 服务
"""

import os
import sys
import base64
import asyncio
import logging
import datetime
from pathlib import Path
from typing import Optional

# MCP
from mcp.server.fastmcp import FastMCP

# 火山引擎 Ark SDK (OpenAI-compatible)
from openai import OpenAI

# ── 日志 ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("seedream-mcp")

# ── 配置（从环境变量读取）────────────────────────────────────────────────────
ARK_API_KEY   = os.environ.get("ARK_API_KEY", "")
ARK_MODEL_ID  = os.environ.get("ARK_MODEL_ID", "")           # ep-xxxx
ARK_BASE_URL  = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
IMAGE_SAVE_DIR = os.environ.get("IMAGE_SAVE_DIR", str(Path.home() / "Desktop" / "seedream_images"))

# ── 支持的尺寸 ────────────────────────────────────────────────────────────────
SUPPORTED_SIZES = [
    "512x512", "768x768", "1024x1024",
    "864x1152", "1152x864",
    "1280x720", "720x1280",
    "832x1248", "1248x832",
    "1512x648",
    "2048x2048",
]

# ── MCP 服务实例 ──────────────────────────────────────────────────────────────
mcp = FastMCP("Seedream Image Generator")


def _get_client() -> OpenAI:
    if not ARK_API_KEY:
        raise RuntimeError("ARK_API_KEY 环境变量未设置")
    if not ARK_MODEL_ID:
        raise RuntimeError("ARK_MODEL_ID 环境变量未设置（应为 ep-xxx 格式）")
    return OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)


def _ensure_save_dir() -> Path:
    save_dir = Path(IMAGE_SAVE_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def _save_image(b64_data: str, prefix: str, save_dir: Path) -> str:
    """将 base64 图片数据保存为 PNG 文件，返回文件路径"""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{ts}.png"
    filepath = save_dir / filename
    filepath.write_bytes(base64.b64decode(b64_data))
    return str(filepath)


# ── 工具：生成图片 ─────────────────────────────────────────────────────────────
@mcp.tool()
def generate_image(
    prompt: str,
    size: str = "1024x1024",
    seed: int = -1,
    guidance_scale: float = 2.5,
    watermark: bool = False,
    file_prefix: str = "seedream",
) -> str:
    """
    使用 Seedream 5.0 生成图片。

    Args:
        prompt:         图片描述（支持中英文）
        size:           图片尺寸，可选值见下方列表，默认 1024x1024
                        支持: 512x512, 768x768, 1024x1024, 864x1152, 1152x864,
                              1280x720, 720x1280, 832x1248, 1248x832, 1512x648, 2048x2048
        seed:           随机种子（-1 表示自动随机）
        guidance_scale: 引导强度 1.0-10.0，越高越贴近 prompt，默认 2.5
        watermark:      是否添加水印，默认 False
        file_prefix:    保存文件的名称前缀，仅英文字母和数字

    Returns:
        生成图片的本地文件路径
    """
    # 参数校验
    if size not in SUPPORTED_SIZES:
        return f"❌ 不支持的尺寸 '{size}'，请从以下选择：{', '.join(SUPPORTED_SIZES)}"

    guidance_scale = max(1.0, min(10.0, float(guidance_scale)))

    logger.info(f"开始生成图片 | prompt={prompt[:60]}... | size={size}")

    try:
        client = _get_client()
        save_dir = _ensure_save_dir()

        # 构建请求体（Seedream-5.0-lite 不支持 guidance_scale）
        extra_body: dict = {
            "size": size,
            "watermark": watermark,
        }
        if seed != -1:
            extra_body["seed"] = seed

        response = client.images.generate(
            model=ARK_MODEL_ID,
            prompt=prompt,
            response_format="b64_json",
            extra_body=extra_body,
        )

        # 取第一张图
        image_data = response.data[0]
        b64 = image_data.b64_json

        # 保存
        filepath = _save_image(b64, file_prefix, save_dir)
        logger.info(f"图片已保存: {filepath}")

        return (
            f"✅ 图片生成成功！\n"
            f"📁 文件路径: {filepath}\n"
            f"📐 尺寸: {size}\n"
            f"🎨 Prompt: {prompt}"
        )

    except Exception as e:
        logger.error(f"生成失败: {e}")
        return f"❌ 生成失败: {str(e)}"


# ── 工具：列出支持的尺寸 ───────────────────────────────────────────────────────
@mcp.tool()
def list_supported_sizes() -> str:
    """列出 Seedream 5.0 支持的所有图片尺寸"""
    lines = [
        "Seedream 5.0 支持的图片尺寸：",
        "",
        "正方形：",
        "  512x512   (1:1 小正方形)",
        "  768x768   (1:1 标准)",
        "  1024x1024 (1:1 大图，默认)",
        "  2048x2048 (1:1 超大图)",
        "",
        "横版：",
        "  1152x864  (4:3 横版)",
        "  1280x720  (16:9 宽屏)",
        "  1248x832  (3:2 横版)",
        "  1512x648  (21:9 超宽)",
        "",
        "竖版：",
        "  864x1152  (3:4 竖版)",
        "  720x1280  (9:16 手机竖屏)",
        "  832x1248  (2:3 竖版)",
    ]
    return "\n".join(lines)


# ── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Seedream MCP Server 启动中...")
    logger.info(f"Model ID: {ARK_MODEL_ID or '(未设置)'}")
    logger.info(f"图片保存目录: {IMAGE_SAVE_DIR}")
    mcp.run(transport="stdio")

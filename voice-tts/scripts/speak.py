#!/usr/bin/env python3
"""
语音合成与发送脚本 - 自包含，无需额外安装包（仅需 edge-tts、httpx）

用法：
    python speak.py --text "你好" --target "ou_xxx" --platform feishu
    python speak.py --text "你好" --target test --platform local --output-dir /tmp/voice
    python speak.py --text "克隆" --target "ou_xxx" --engine fish --fish-model-id "model_id"
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ============================================================
# 依赖检查
# ============================================================

def check_deps():
    """检查必要依赖是否已安装"""
    missing = []
    try:
        import edge_tts
    except ImportError:
        missing.append("edge-tts")
    try:
        import httpx
    except ImportError:
        missing.append("httpx")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg (系统工具)")
    if missing:
        print(f"缺少依赖: {', '.join(missing)}", file=sys.stderr)
        print("请执行: pip install edge-tts httpx", file=sys.stderr)
        print("ffmpeg 安装: brew install ffmpeg (macOS) 或 yum install ffmpeg (CentOS)", file=sys.stderr)
        sys.exit(1)

check_deps()

import edge_tts
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-tts")

# ============================================================
# 音频转换
# ============================================================

def to_opus(input_path: str, output_path: str = None) -> str:
    """将音频转换为 opus/ogg 格式（飞书语音消息要求）"""
    output_path = output_path or str(Path(input_path).with_suffix(".ogg"))
    cmd = ["ffmpeg", "-i", input_path, "-c:a", "libopus", "-b:a", "48k", "-vn", "-y", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 转换失败: {result.stderr}")
    return output_path


def get_duration(file_path: str) -> float:
    """获取音频时长（秒）"""
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr}")
    return float(json.loads(result.stdout)["format"]["duration"])

# ============================================================
# TTS 引擎
# ============================================================

async def edge_tts_synthesize(text: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural",
                               rate: str = "+0%", pitch: str = "+0Hz") -> str:
    """Edge TTS 合成（免费，无需 GPU）"""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)
    logger.info(f"Edge TTS 合成完成: {output_path}")
    return output_path


async def fish_audio_synthesize(text: str, output_path: str, api_key: str,
                                 model_id: str = None, reference_audio: str = None,
                                 reference_text: str = None) -> str:
    """Fish Audio 合成/克隆（免费额度 1 万字/天）"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {"Authorization": f"Bearer {api_key}"}
        if model_id:
            resp = await client.post(
                "https://api.fish.audio/v1/tts",
                headers=headers,
                json={"text": text, "reference_id": model_id, "format": "mp3"},
            )
        elif reference_audio:
            with open(reference_audio, "rb") as f:
                data = {"text": text, "format": "mp3"}
                if reference_text:
                    data["reference_text"] = reference_text
                resp = await client.post(
                    "https://api.fish.audio/v1/tts",
                    headers=headers,
                    data=data,
                    files={"file": ("ref.wav", f, "audio/wav")},
                )
        else:
            print("Fish Audio 需要 --fish-model-id 或 --reference-audio", file=sys.stderr)
            sys.exit(1)

        resp.raise_for_status()
        Path(output_path).write_bytes(resp.content)
    logger.info(f"Fish Audio 合成完成: {output_path}")
    return output_path

# ============================================================
# 飞书发送
# ============================================================

async def feishu_send_voice(audio_path: str, target_id: str, receive_id_type: str = "open_id"):
    """上传音频并通过飞书发送语音消息"""
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("需要设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET", file=sys.stderr)
        sys.exit(1)

    base = "https://open.feishu.cn/open-apis"

    async with httpx.AsyncClient() as client:
        # 获取 access_token
        resp = await client.post(
            f"{base}/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
        )
        token_data = resp.json()
        if token_data.get("code") != 0:
            raise RuntimeError(f"获取飞书 token 失败: {token_data}")
        token = token_data["tenant_access_token"]

        # 转换为 opus
        if not audio_path.endswith(".ogg"):
            ogg_path = str(Path(audio_path).with_suffix(".ogg"))
            to_opus(audio_path, ogg_path)
            audio_path = ogg_path

        duration = get_duration(audio_path)

        # 上传音频
        with open(audio_path, "rb") as f:
            resp = await client.post(
                f"{base}/im/v1/files",
                headers={"Authorization": f"Bearer {token}"},
                data={"file_type": "opus", "file_name": Path(audio_path).name, "duration": str(int(duration))},
                files={"file": (Path(audio_path).name, f, "audio/ogg")},
            )
        upload_data = resp.json()
        if upload_data.get("code") != 0:
            raise RuntimeError(f"上传音频失败: {upload_data}")
        file_key = upload_data["data"]["file_key"]

        # 发送语音消息
        resp = await client.post(
            f"{base}/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "receive_id": target_id,
                "msg_type": "audio",
                "content": json.dumps({"file_key": file_key}),
            },
        )
        send_data = resp.json()
        if send_data.get("code") != 0:
            raise RuntimeError(f"发送语音消息失败: {send_data}")

    logger.info(f"语音消息已发送给 {target_id}")
    return send_data

# ============================================================
# 本地保存
# ============================================================

async def local_save(audio_path: str, target_id: str, output_dir: str = "./voice_output"):
    """保存音频到本地目录"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{target_id}_{Path(audio_path).name}"
    shutil.copy2(audio_path, dest)
    logger.info(f"音频已保存: {dest}")
    return {"status": "ok", "path": str(dest)}

# ============================================================
# 主流程
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="语音合成与发送")
    parser.add_argument("--text", required=True, help="要合成的文字")
    parser.add_argument("--target", required=True, help="接收人 ID（open_id 或 chat_id）")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="音色名称（默认 zh-CN-XiaoxiaoNeural）")
    parser.add_argument("--engine", default="edge", choices=["edge", "fish"], help="TTS 引擎")
    parser.add_argument("--platform", default="feishu", choices=["feishu", "local"], help="发送平台")
    parser.add_argument("--receive-type", default="open_id", choices=["open_id", "chat_id"], help="接收人 ID 类型")
    parser.add_argument("--output-dir", default="./voice_output", help="本地保存目录（platform=local 时使用）")
    parser.add_argument("--rate", default="+0%", help="语速调节（如 +20%%、-10%%）")
    parser.add_argument("--pitch", default="+0Hz", help="音调调节（如 +5Hz、-3Hz）")
    # Fish Audio 参数
    parser.add_argument("--fish-api-key", default=os.environ.get("FISH_AUDIO_API_KEY", ""), help="Fish Audio API Key")
    parser.add_argument("--fish-model-id", default="", help="Fish Audio 声音模型 ID")
    parser.add_argument("--reference-audio", default="", help="参考音频路径（语音克隆用，10-30秒）")
    parser.add_argument("--reference-text", default="", help="参考音频文字内容（提高克隆质量）")

    args = parser.parse_args()

    # 合成
    tmp_dir = tempfile.mkdtemp(prefix="voice_tts_")
    ext = ".mp3" if args.engine == "edge" else ".wav"
    audio_path = os.path.join(tmp_dir, f"output{ext}")

    if args.engine == "edge":
        await edge_tts_synthesize(args.text, audio_path, voice=args.voice, rate=args.rate, pitch=args.pitch)
    elif args.engine == "fish":
        if not args.fish_api_key:
            print("Fish Audio 需要 --fish-api-key 或设置 FISH_AUDIO_API_KEY 环境变量", file=sys.stderr)
            sys.exit(1)
        await fish_audio_synthesize(
            args.text, audio_path, api_key=args.fish_api_key,
            model_id=args.fish_model_id or None,
            reference_audio=args.reference_audio or None,
            reference_text=args.reference_text or None,
        )

    # 发送
    if args.platform == "feishu":
        result = await feishu_send_voice(audio_path, args.target, args.receive_type)
    else:
        result = await local_save(audio_path, args.target, args.output_dir)

    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 清理临时文件
    shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())

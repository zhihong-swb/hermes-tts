#!/usr/bin/env python3
"""
声音克隆 - 通过 Fish Audio API 创建/管理声音模型

用法：
    python clone_voice.py --audio prepared.wav --name "模型名称"
    python clone_voice.py --audio a.wav b.wav --name "多样本模型"
    python clone_voice.py --list
    python clone_voice.py --delete "模型ID"
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("缺少依赖: httpx", file=sys.stderr)
    print("请执行: pip install httpx", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-clone")

FISH_API_BASE = "https://api.fish.audio"


def get_api_key() -> str:
    key = os.environ.get("FISH_AUDIO_API_KEY", "")
    if not key:
        # 尝试从 hermes .env 读取
        env_file = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("FISH_AUDIO_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not key:
        print("需要设置 FISH_AUDIO_API_KEY 环境变量", file=sys.stderr)
        print("在 https://fish.audio 免费注册获取", file=sys.stderr)
        sys.exit(1)
    return key


async def create_model(audio_paths: list, name: str, description: str = ""):
    """上传音频创建声音模型"""
    api_key = get_api_key()

    # 验证文件存在
    for p in audio_paths:
        if not os.path.exists(p):
            print(f"文件不存在: {p}", file=sys.stderr)
            sys.exit(1)
        size = os.path.getsize(p)
        logger.info(f"音频文件: {p} ({size // 1024}KB)")

    logger.info(f"创建声音模型: {name}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # 准备上传文件
        files = []
        open_files = []
        for p in audio_paths:
            f = open(p, "rb")
            open_files.append(f)
            files.append(("files", (Path(p).name, f, "audio/wav")))

        data = {"visibility": "private", "type": "tts", "title": name}
        if description:
            data["description"] = description

        try:
            resp = await client.post(
                f"{FISH_API_BASE}/model",
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files=files,
            )
        finally:
            for f in open_files:
                f.close()

        if resp.status_code == 401:
            print("API Key 无效，请检查 FISH_AUDIO_API_KEY", file=sys.stderr)
            sys.exit(1)

        resp.raise_for_status()
        result = resp.json()

    model_id = result.get("_id", result.get("id", "未知"))
    print(f"\n声音模型创建成功！")
    print(f"  模型名称: {name}")
    print(f"  模型 ID:  {model_id}")
    print(f"\n使用方式：")
    print(f'  python voice-tts/scripts/speak.py --text "要说的话" --target "ou_xxx" --engine fish --fish-model-id "{model_id}"')

    return model_id


async def list_models():
    """列出已创建的声音模型"""
    api_key = get_api_key()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{FISH_API_BASE}/model",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"page_size": 100, "page_number": 1},
        )
        resp.raise_for_status()
        result = resp.json()

    items = result.get("items", result) if isinstance(result, dict) else result
    if not items:
        print("暂无声音模型")
        return

    print(f"\n已创建的声音模型：\n")
    print(f"{'模型 ID':<30} {'名称':<20} {'创建时间':<20}")
    print("-" * 75)

    if isinstance(items, list):
        for item in items:
            model_id = item.get("_id", item.get("id", ""))
            title = item.get("title", item.get("name", "未知"))
            created = item.get("created_at", "")[:19]
            print(f"{model_id:<30} {title:<20} {created:<20}")
        print(f"\n共 {len(items)} 个模型")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


async def delete_model(model_id: str):
    """删除声音模型"""
    api_key = get_api_key()

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.delete(
            f"{FISH_API_BASE}/model/{model_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if resp.status_code == 404:
            print(f"模型不存在: {model_id}", file=sys.stderr)
            sys.exit(1)
        resp.raise_for_status()

    print(f"模型已删除: {model_id}")


async def test_model(model_id: str, text: str = "你好，这是声音克隆测试。"):
    """测试声音模型（合成一段音频到本地）"""
    api_key = get_api_key()

    logger.info(f"测试模型 {model_id}...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{FISH_API_BASE}/v1/tts",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"text": text, "reference_id": model_id, "format": "mp3"},
        )
        resp.raise_for_status()

        output = f"clone_test_{model_id[:8]}.mp3"
        Path(output).write_bytes(resp.content)

    print(f"测试音频已保存: {output} ({len(resp.content) // 1024}KB)")
    return output


def main():
    parser = argparse.ArgumentParser(description="声音克隆 - 创建/管理 Fish Audio 声音模型")
    parser.add_argument("--audio", nargs="+", help="音频文件路径（可多个）")
    parser.add_argument("--name", help="声音模型名称")
    parser.add_argument("--description", default="", help="模型描述")
    parser.add_argument("--list", action="store_true", help="列出已有模型")
    parser.add_argument("--delete", metavar="MODEL_ID", help="删除指定模型")
    parser.add_argument("--test", metavar="MODEL_ID", help="测试指定模型")
    parser.add_argument("--test-text", default="你好，这是声音克隆测试。", help="测试用文本")

    args = parser.parse_args()

    if args.list:
        asyncio.run(list_models())
    elif args.delete:
        asyncio.run(delete_model(args.delete))
    elif args.test:
        asyncio.run(test_model(args.test, args.test_text))
    elif args.audio and args.name:
        asyncio.run(create_model(args.audio, args.name, args.description))
    else:
        parser.print_help()
        print("\n示例：")
        print('  创建模型: python clone_voice.py --audio prepared.wav --name "我的声音"')
        print("  列出模型: python clone_voice.py --list")
        print('  测试模型: python clone_voice.py --test "模型ID"')
        print('  删除模型: python clone_voice.py --delete "模型ID"')


if __name__ == "__main__":
    main()

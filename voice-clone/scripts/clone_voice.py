#!/usr/bin/env python3
"""
声音克隆 - 创建/管理声音模型

引擎优先级（自动选择）：
  1. Qwen3-TTS（本地，需要 GPU + qwen-tts 包）→ 3秒音频即可克隆
  2. Fish Audio（云端，需要 API Key）→ 免费额度每天1万字

用法：
    # 克隆声音（自动选引擎）
    python clone_voice.py --audio prepared.wav --name "模型名称"

    # 指定引擎
    python clone_voice.py --audio prepared.wav --name "名称" --engine qwen
    python clone_voice.py --audio prepared.wav --name "名称" --engine fish

    # 使用克隆声音合成语音（Qwen3-TTS 本地）
    python clone_voice.py --tts --model "模型名称" --text "你好世界" --output hello.wav

    # 管理 Fish Audio 模型
    python clone_voice.py --list
    python clone_voice.py --delete "模型ID"
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-clone")

# 本地模型存储目录
LOCAL_MODELS_DIR = os.path.expanduser("~/.hermes/voice-models")


# ─── 引擎检测 ──────────────────────────────────────────────

def _has_gpu() -> bool:
    """检测是否有可用的 NVIDIA GPU"""
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            pass
    return False


def _has_qwen_tts() -> bool:
    """检测是否安装了 qwen-tts"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import qwen_tts; print('ok')"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0 and "ok" in result.stdout
    except Exception:
        return False


def _get_fish_api_key() -> str:
    """获取 Fish Audio API Key"""
    key = os.environ.get("FISH_AUDIO_API_KEY", "")
    if not key:
        env_file = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("FISH_AUDIO_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return key


def detect_engine() -> str:
    """自动检测可用的克隆引擎，返回 'qwen' 或 'fish'"""
    if _has_gpu() and _has_qwen_tts():
        logger.info("检测到 GPU + Qwen3-TTS，使用本地克隆")
        return "qwen"
    if _get_fish_api_key():
        if not _has_qwen_tts():
            logger.info("未检测到 Qwen3-TTS，使用 Fish Audio 云端克隆")
        else:
            logger.info("未检测到 GPU，使用 Fish Audio 云端克隆")
        return "fish"
    # 都没有
    if _has_qwen_tts():
        logger.warning("检测到 Qwen3-TTS 但无 GPU，将使用 CPU 推理（较慢）")
        return "qwen"
    print("错误: 没有可用的克隆引擎", file=sys.stderr)
    print("方案 1 (推荐): pip install qwen-tts  (需要 GPU)", file=sys.stderr)
    print("方案 2: 设置 FISH_AUDIO_API_KEY 环境变量 (https://fish.audio)", file=sys.stderr)
    sys.exit(1)


# ─── Qwen3-TTS 本地克隆 ───────────────────────────────────

def _qwen_clone_voice(audio_paths: list, name: str, text: str = "", output: str = ""):
    """使用 Qwen3-TTS 本地克隆声音并合成"""
    # 用第一个音频作为参考音频
    ref_audio = audio_paths[0]

    # 保存模型配置（引用音频路径），方便后续使用
    os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)
    model_config = {
        "name": name,
        "engine": "qwen",
        "ref_audio": [os.path.abspath(p) for p in audio_paths],
        "ref_text": "",  # 可后续补充
    }

    # 复制参考音频到模型目录
    model_dir = os.path.join(LOCAL_MODELS_DIR, name)
    os.makedirs(model_dir, exist_ok=True)
    for p in audio_paths:
        dest = os.path.join(model_dir, Path(p).name)
        if os.path.abspath(p) != os.path.abspath(dest):
            shutil.copy2(p, dest)
        model_config["ref_audio"] = [
            os.path.join(model_dir, Path(pp).name) for pp in audio_paths
        ]

    config_path = os.path.join(model_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(model_config, f, ensure_ascii=False, indent=2)

    logger.info(f"声音模型已保存: {model_dir}")

    # 如果提供了文本，直接合成测试
    if text:
        output = output or os.path.join(model_dir, "test.wav")
        _qwen_synthesize(ref_audio, text, output)

    print(f"\n声音模型创建成功！")
    print(f"  模型名称: {name}")
    print(f"  存储路径: {model_dir}")
    print(f"  引擎: Qwen3-TTS (本地)")
    print(f"\n使用方式：")
    print(f'  python clone_voice.py --tts --model "{name}" --text "要说的话" --output output.wav')
    print(f'  或配合 voice-tts:')
    print(f'  python voice-tts/scripts/speak.py --text "要说的话" --target "ou_xxx" --engine qwen --ref-audio "{model_config["ref_audio"][0]}"')

    return name


def _qwen_synthesize(ref_audio: str, text: str, output: str):
    """使用 Qwen3-TTS 合成语音"""
    logger.info(f"Qwen3-TTS 合成: {text[:30]}...")

    # 通过子进程调用，避免在主进程加载大模型
    script = f"""
import sys
try:
    from qwen_tts import Qwen3TTSModel
except ImportError:
    print("ERROR: qwen-tts not installed", file=sys.stderr)
    sys.exit(1)

model = Qwen3TTSModel("Qwen/Qwen3-TTS-0.6B-CustomVoice")
model.synthesize(
    text={repr(text)},
    ref_audio={repr(ref_audio)},
    output_path={repr(output)},
)
print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0 or "ERROR" in result.stderr:
        logger.error(f"Qwen3-TTS 合成失败: {result.stderr[:300]}")
        return None

    if os.path.exists(output):
        size = os.path.getsize(output)
        logger.info(f"合成完成: {output} ({size // 1024}KB)")
        return output
    return None


def _qwen_tts_from_model(model_name: str, text: str, output: str):
    """从已保存的本地模型合成语音"""
    model_dir = os.path.join(LOCAL_MODELS_DIR, model_name)
    config_path = os.path.join(model_dir, "config.json")

    if not os.path.exists(config_path):
        print(f"模型不存在: {model_name}", file=sys.stderr)
        print(f"已有模型:", file=sys.stderr)
        _list_local_models()
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    ref_audio = config["ref_audio"][0]
    if not os.path.exists(ref_audio):
        print(f"参考音频丢失: {ref_audio}", file=sys.stderr)
        sys.exit(1)

    return _qwen_synthesize(ref_audio, text, output)


def _list_local_models():
    """列出本地保存的声音模型"""
    if not os.path.isdir(LOCAL_MODELS_DIR):
        print("暂无本地声音模型")
        return

    models = []
    for d in os.listdir(LOCAL_MODELS_DIR):
        config_path = os.path.join(LOCAL_MODELS_DIR, d, "config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            models.append(config)

    if not models:
        print("暂无本地声音模型")
        return

    print(f"\n本地声音模型（Qwen3-TTS）：\n")
    print(f"{'名称':<20} {'引擎':<10} {'音频数':<8}")
    print("-" * 40)
    for m in models:
        name = m.get("name", "未知")
        engine = m.get("engine", "?")
        n_audio = len(m.get("ref_audio", []))
        print(f"{name:<20} {engine:<10} {n_audio:<8}")
    print(f"\n共 {len(models)} 个模型")


# ─── Fish Audio 云端克隆 ───────────────────────────────────

FISH_API_BASE = "https://api.fish.audio"


async def _fish_create_model(audio_paths: list, name: str, description: str = ""):
    """通过 Fish Audio API 创建声音模型"""
    try:
        import httpx
    except ImportError:
        print("缺少依赖: httpx\n请执行: pip install httpx", file=sys.stderr)
        sys.exit(1)

    api_key = _get_fish_api_key()
    if not api_key:
        print("需要设置 FISH_AUDIO_API_KEY", file=sys.stderr)
        sys.exit(1)

    for p in audio_paths:
        if not os.path.exists(p):
            print(f"文件不存在: {p}", file=sys.stderr)
            sys.exit(1)
        logger.info(f"音频文件: {p} ({os.path.getsize(p) // 1024}KB)")

    logger.info(f"[Fish Audio] 创建声音模型: {name}")

    async with httpx.AsyncClient(timeout=120.0) as client:
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
    print(f"  引擎: Fish Audio (云端)")
    print(f"\n使用方式：")
    print(f'  python voice-tts/scripts/speak.py --text "要说的话" --target "ou_xxx" --engine fish --fish-model-id "{model_id}"')

    return model_id


async def _fish_list_models():
    """列出 Fish Audio 已创建的声音模型"""
    try:
        import httpx
    except ImportError:
        print("缺少依赖: httpx", file=sys.stderr)
        return

    api_key = _get_fish_api_key()
    if not api_key:
        print("未配置 FISH_AUDIO_API_KEY，跳过云端模型", file=sys.stderr)
        return

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
        print("暂无 Fish Audio 云端模型")
        return

    print(f"\nFish Audio 云端模型：\n")
    print(f"{'模型 ID':<30} {'名称':<20} {'创建时间':<20}")
    print("-" * 75)

    if isinstance(items, list):
        for item in items:
            model_id = item.get("_id", item.get("id", ""))
            title = item.get("title", item.get("name", "未知"))
            created = item.get("created_at", "")[:19]
            print(f"{model_id:<30} {title:<20} {created:<20}")
        print(f"\n共 {len(items)} 个云端模型")


async def _fish_delete_model(model_id: str):
    """删除 Fish Audio 声音模型"""
    try:
        import httpx
    except ImportError:
        print("缺少依赖: httpx", file=sys.stderr)
        sys.exit(1)

    api_key = _get_fish_api_key()
    if not api_key:
        print("需要设置 FISH_AUDIO_API_KEY", file=sys.stderr)
        sys.exit(1)

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


# ─── 入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="声音克隆 - 自动选择本地(Qwen3-TTS)或云端(Fish Audio)",
    )

    # 创建模型
    parser.add_argument("--audio", nargs="+", help="音频文件路径（可多个）")
    parser.add_argument("--name", help="声音模型名称")
    parser.add_argument("--description", default="", help="模型描述")
    parser.add_argument("--engine", choices=["auto", "qwen", "fish"], default="auto",
                        help="克隆引擎（默认 auto: 有GPU用qwen，否则fish）")

    # 合成（本地 Qwen3-TTS 模型）
    parser.add_argument("--tts", action="store_true", help="使用本地模型合成语音")
    parser.add_argument("--model", help="本地模型名称（配合 --tts 使用）")
    parser.add_argument("--text", help="合成文本（配合 --tts 使用）")
    parser.add_argument("--output", default="output.wav", help="输出文件（配合 --tts 使用）")

    # 管理
    parser.add_argument("--list", action="store_true", help="列出所有模型")
    parser.add_argument("--delete", metavar="MODEL_ID", help="删除 Fish Audio 模型")

    args = parser.parse_args()

    if args.list:
        _list_local_models()
        print()
        asyncio.run(_fish_list_models())

    elif args.delete:
        asyncio.run(_fish_delete_model(args.delete))

    elif args.tts and args.model and args.text:
        _qwen_tts_from_model(args.model, args.text, args.output)

    elif args.audio and args.name:
        engine = args.engine
        if engine == "auto":
            engine = detect_engine()

        if engine == "qwen":
            _qwen_clone_voice(args.audio, args.name)
        else:
            asyncio.run(_fish_create_model(args.audio, args.name, args.description))

    else:
        parser.print_help()
        print("\n示例：")
        print('  创建模型:  python clone_voice.py --audio prepared.wav --name "我的声音"')
        print('  指定引擎:  python clone_voice.py --audio a.wav --name "名称" --engine qwen')
        print('  本地合成:  python clone_voice.py --tts --model "我的声音" --text "你好" --output hi.wav')
        print('  列出模型:  python clone_voice.py --list')
        print('  删除模型:  python clone_voice.py --delete "Fish Audio 模型ID"')


if __name__ == "__main__":
    main()

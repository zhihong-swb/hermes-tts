#!/usr/bin/env python3
"""
声音克隆 - 创建/管理声音模型（Qwen3-TTS 本地）

支持设备：
  - NVIDIA GPU (CUDA)
  - Apple Silicon (MPS) - M1/M2/M3/M4 Mac
  - CPU (较慢，不推荐)

用法：
    # 克隆声音
    python clone_voice.py --audio prepared.wav --name "模型名称"

    # 使用克隆声音合成语音
    python clone_voice.py --tts --model "模型名称" --text "你好世界" --output hello.wav

    # 管理模型
    python clone_voice.py --list
    python clone_voice.py --delete "模型名称"
"""

import argparse
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


# ─── 设备检测 ──────────────────────────────────────────────

def _has_nvidia_gpu() -> bool:
    """检测是否有可用的 NVIDIA GPU"""
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            pass
    return False


def _has_apple_mps() -> bool:
    """检测是否有 Apple Silicon MPS（Metal Performance Shaders）"""
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "import torch; print('mps' if torch.backends.mps.is_available() else 'no')"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0 and "mps" in result.stdout
    except Exception:
        return False


def _detect_device() -> str:
    """检测最佳推理设备: cuda / mps / cpu"""
    if _has_nvidia_gpu():
        return "cuda"
    if _has_apple_mps():
        return "mps"
    return "cpu"


def _check_qwen_tts():
    """检测 qwen-tts 是否可用，不可用则报错退出"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import qwen_tts; print('ok')"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and "ok" in result.stdout:
            return
    except Exception:
        pass
    print("错误: 未安装 qwen-tts", file=sys.stderr)
    print("请执行: pip install qwen-tts", file=sys.stderr)
    print("详见: voice-clone/setup.md", file=sys.stderr)
    sys.exit(1)


# ─── 克隆（保存参考音频） ─────────────────────────────────

def clone_voice(audio_paths: list, name: str, text: str = "", output: str = ""):
    """保存参考音频为声音模型，可选立即合成测试"""
    _check_qwen_tts()

    os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)
    model_dir = os.path.join(LOCAL_MODELS_DIR, name)
    os.makedirs(model_dir, exist_ok=True)

    # 复制参考音频到模型目录
    saved_paths = []
    for p in audio_paths:
        if not os.path.exists(p):
            print(f"文件不存在: {p}", file=sys.stderr)
            sys.exit(1)
        dest = os.path.join(model_dir, Path(p).name)
        if os.path.abspath(p) != os.path.abspath(dest):
            shutil.copy2(p, dest)
        saved_paths.append(dest)

    # 保存配置
    config = {
        "name": name,
        "engine": "qwen",
        "ref_audio": saved_paths,
    }
    config_path = os.path.join(model_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    logger.info(f"声音模型已保存: {model_dir}")

    # 如果提供了文本，直接合成测试
    if text:
        output = output or os.path.join(model_dir, "test.wav")
        synthesize(saved_paths[0], text, output)

    print(f"\n声音模型创建成功！")
    print(f"  模型名称: {name}")
    print(f"  存储路径: {model_dir}")
    print(f"  参考音频: {len(saved_paths)} 个")
    print(f"\n合成语音：")
    print(f'  python clone_voice.py --tts --model "{name}" --text "要说的话" --output output.wav')

    return name


# ─── 合成（子进程加载模型，用完即退） ─────────────────────

def synthesize(ref_audio: str, text: str, output: str):
    """使用 Qwen3-TTS 合成语音。通过子进程运行，合成完自动退出释放显存/内存。"""
    device = _detect_device()
    logger.info(f"Qwen3-TTS 合成 (device={device}): {text[:30]}...")

    # 子进程脚本：加载模型 → 合成 → 退出（释放资源）
    script = f"""
import sys
import os
import gc

try:
    from qwen_tts import Qwen3TTSModel
except ImportError:
    print("ERROR: qwen-tts not installed", file=sys.stderr)
    sys.exit(1)

device = {repr(device)}

# MPS 部分算子可能需要 CPU fallback
if device == "mps":
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

# 加载模型
model = Qwen3TTSModel("Qwen/Qwen3-TTS-0.6B-CustomVoice", device=device)

# 合成
model.synthesize(
    text={repr(text)},
    ref_audio={repr(ref_audio)},
    output_path={repr(output)},
)

# 显式释放模型和显存
del model
gc.collect()

try:
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        torch.mps.empty_cache()
except Exception:
    pass

print("OK")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0 or "ERROR" in result.stderr:
        logger.error(f"Qwen3-TTS 合成失败: {result.stderr[:500]}")
        return None

    if os.path.exists(output):
        size = os.path.getsize(output)
        logger.info(f"合成完成: {output} ({size // 1024}KB)")
        return output
    return None


def synthesize_from_model(model_name: str, text: str, output: str):
    """从已保存的本地模型合成语音"""
    model_dir = os.path.join(LOCAL_MODELS_DIR, model_name)
    config_path = os.path.join(model_dir, "config.json")

    if not os.path.exists(config_path):
        print(f"模型不存在: {model_name}", file=sys.stderr)
        list_models()
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    ref_audio = config["ref_audio"][0]
    if not os.path.exists(ref_audio):
        print(f"参考音频丢失: {ref_audio}", file=sys.stderr)
        sys.exit(1)

    return synthesize(ref_audio, text, output)


# ─── 模型管理 ──────────────────────────────────────────────

def list_models():
    """列出本地保存的声音模型"""
    if not os.path.isdir(LOCAL_MODELS_DIR):
        print("暂无本地声音模型")
        return

    models = []
    for d in sorted(os.listdir(LOCAL_MODELS_DIR)):
        config_path = os.path.join(LOCAL_MODELS_DIR, d, "config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            models.append(config)

    if not models:
        print("暂无本地声音模型")
        return

    print(f"\n本地声音模型：\n")
    print(f"{'名称':<20} {'音频数':<8} {'路径'}")
    print("-" * 60)
    for m in models:
        name = m.get("name", "未知")
        n_audio = len(m.get("ref_audio", []))
        path = os.path.join(LOCAL_MODELS_DIR, name)
        print(f"{name:<20} {n_audio:<8} {path}")
    print(f"\n共 {len(models)} 个模型")


def delete_model(model_name: str):
    """删除本地声音模型"""
    model_dir = os.path.join(LOCAL_MODELS_DIR, model_name)
    if not os.path.isdir(model_dir):
        print(f"模型不存在: {model_name}", file=sys.stderr)
        list_models()
        sys.exit(1)

    shutil.rmtree(model_dir)
    print(f"模型已删除: {model_name}")


# ─── 入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="声音克隆 - Qwen3-TTS 本地克隆（支持 NVIDIA GPU / Apple Silicon / CPU）",
    )

    # 创建模型
    parser.add_argument("--audio", nargs="+", help="参考音频文件路径（可多个）")
    parser.add_argument("--name", help="声音模型名称")

    # 合成
    parser.add_argument("--tts", action="store_true", help="使用已保存的模型合成语音")
    parser.add_argument("--model", help="模型名称（配合 --tts 使用）")
    parser.add_argument("--text", help="合成文本（配合 --tts 使用）")
    parser.add_argument("--output", default="output.wav", help="输出文件（默认: output.wav）")

    # 管理
    parser.add_argument("--list", action="store_true", help="列出所有本地模型")
    parser.add_argument("--delete", metavar="NAME", help="删除本地模型")

    args = parser.parse_args()

    if args.list:
        list_models()

    elif args.delete:
        delete_model(args.delete)

    elif args.tts and args.model and args.text:
        synthesize_from_model(args.model, args.text, args.output)

    elif args.audio and args.name:
        clone_voice(args.audio, args.name)

    else:
        parser.print_help()
        print("\n示例：")
        print('  克隆声音:  python clone_voice.py --audio prepared.wav --name "雷军"')
        print('  合成语音:  python clone_voice.py --tts --model "雷军" --text "你好" --output hi.wav')
        print('  列出模型:  python clone_voice.py --list')
        print('  删除模型:  python clone_voice.py --delete "雷军"')


if __name__ == "__main__":
    main()

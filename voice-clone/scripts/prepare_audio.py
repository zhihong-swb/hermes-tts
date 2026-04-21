#!/usr/bin/env python3
"""
音频预处理 - 格式转换、裁剪、降噪

将原始音频/视频处理为适合声音克隆的格式：
- 转为 WAV（16kHz, 单声道）
- 裁剪指定时长（建议 10-30 秒）
- 可选降噪处理

用法：
    python prepare_audio.py --input raw.mp4 --duration 25
    python prepare_audio.py --input noisy.mp3 --denoise --start 10 --duration 20
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-clone")


def check_deps():
    if not shutil.which("ffmpeg"):
        print("缺少依赖: ffmpeg", file=sys.stderr)
        print("请安装: brew install ffmpeg (macOS) 或 yum install ffmpeg (CentOS)", file=sys.stderr)
        sys.exit(1)


def get_duration(file_path: str) -> float:
    """获取音频时长"""
    import json
    cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    return float(json.loads(result.stdout)["format"]["duration"])


def prepare_audio(input_path: str, output_path: str, start: float, duration: float, denoise: bool):
    """处理音频文件"""
    if not os.path.exists(input_path):
        print(f"文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    total_duration = get_duration(input_path)
    logger.info(f"原始文件: {input_path} (时长: {total_duration:.1f}秒)")

    # 构建 ffmpeg 命令
    cmd = ["ffmpeg", "-i", input_path]

    # 裁剪
    if start > 0:
        cmd.extend(["-ss", str(start)])
    if duration > 0:
        cmd.extend(["-t", str(duration)])

    # 音频参数：WAV, 16kHz, 单声道
    cmd.extend([
        "-ar", "16000",     # 采样率 16kHz
        "-ac", "1",         # 单声道
        "-c:a", "pcm_s16le",  # 16bit PCM
        "-vn",              # 去除视频
    ])

    # 降噪滤镜
    if denoise:
        # 使用 ffmpeg 的 highpass + lowpass 滤波去除极端频率噪声
        # 再用 afftdn 做频域降噪
        cmd.extend([
            "-af", "highpass=f=80,lowpass=f=8000,afftdn=nf=-25",
        ])

    cmd.extend(["-y", output_path])

    logger.info(f"处理参数: start={start}s, duration={duration}s, denoise={denoise}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"音频处理失败: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # 输出信息
    out_duration = get_duration(output_path)
    out_size = os.path.getsize(output_path)
    logger.info(f"处理完成: {output_path}")
    print(f"\n输出文件: {output_path}")
    print(f"  时长: {out_duration:.1f}秒")
    print(f"  大小: {out_size // 1024}KB")
    print(f"  格式: WAV (16kHz, 单声道, 16bit)")

    if out_duration < 5:
        print("\n注意: 音频时长不足 5 秒，克隆效果可能较差。建议 10-30 秒。")
    elif out_duration > 60:
        print("\n注意: 音频时长超过 60 秒，建议裁剪到 10-30 秒以获得最佳效果。")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="音频预处理（格式转换、裁剪、降噪）")
    parser.add_argument("--input", required=True, help="原始音频/视频文件路径")
    parser.add_argument("--output", default="prepared.wav", help="输出文件路径（默认: prepared.wav）")
    parser.add_argument("--start", type=float, default=0, help="裁剪起始时间（秒，默认: 0）")
    parser.add_argument("--duration", type=float, default=30, help="裁剪时长（秒，默认: 30）")
    parser.add_argument("--denoise", action="store_true", help="是否降噪处理")

    args = parser.parse_args()
    check_deps()
    prepare_audio(args.input, args.output, args.start, args.duration, args.denoise)


if __name__ == "__main__":
    main()

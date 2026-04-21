#!/usr/bin/env python3
"""
从网络搜索公众人物音频并下载

用法：
    python search_audio.py --name "雷军" --keyword "演讲"
    python search_audio.py --name "Elon Musk" --keyword "interview"
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-clone")


def check_deps():
    missing = []
    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if missing:
        print(f"缺少依赖: {', '.join(missing)}", file=sys.stderr)
        print("请执行: pip install yt-dlp && brew install ffmpeg", file=sys.stderr)
        sys.exit(1)


def search_and_download(name: str, keyword: str, output_dir: str, max_results: int):
    """通过 yt-dlp 搜索并下载音频"""
    os.makedirs(output_dir, exist_ok=True)

    query = f"{name} {keyword}"
    logger.info(f"搜索: {query} (最多 {max_results} 条)")

    # 先搜索列出结果
    search_cmd = [
        "yt-dlp",
        f"ytsearch{max_results}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
    ]
    result = subprocess.run(search_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"搜索失败: {result.stderr}")
        sys.exit(1)

    entries = []
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        logger.warning("未找到相关音频")
        return []

    # 展示搜索结果
    print(f"\n找到 {len(entries)} 条结果：\n")
    for i, entry in enumerate(entries):
        title = entry.get("title", "未知")
        duration = entry.get("duration")
        url = entry.get("url", entry.get("id", ""))
        dur_str = f"{int(duration)}秒" if duration else "未知时长"
        print(f"  [{i+1}] {title} ({dur_str})")

    # 下载所有结果的音频
    downloaded = []
    for i, entry in enumerate(entries):
        video_id = entry.get("id", entry.get("url", ""))
        title = entry.get("title", f"audio_{i+1}").replace("/", "_").replace(" ", "_")[:50]
        output_template = os.path.join(output_dir, f"{title}.%(ext)s")

        url = f"https://www.youtube.com/watch?v={video_id}" if not video_id.startswith("http") else video_id

        logger.info(f"下载 [{i+1}/{len(entries)}]: {entry.get('title', '')}")
        dl_cmd = [
            "yt-dlp",
            url,
            "-x",                          # 仅提取音频
            "--audio-format", "wav",        # 转为 wav
            "--audio-quality", "0",         # 最高质量
            "-o", output_template,
            "--no-playlist",
            "--max-filesize", "50M",        # 限制大小
        ]
        dl_result = subprocess.run(dl_cmd, capture_output=True, text=True)
        if dl_result.returncode == 0:
            # 找到下载的文件
            for f in os.listdir(output_dir):
                full_path = os.path.join(output_dir, f)
                if title in f and full_path not in downloaded:
                    downloaded.append(full_path)
                    logger.info(f"  已下载: {full_path}")
        else:
            logger.warning(f"  下载失败: {dl_result.stderr[:200]}")

    print(f"\n共下载 {len(downloaded)} 个音频文件到 {output_dir}/")
    for f in downloaded:
        size = os.path.getsize(f)
        print(f"  {f} ({size // 1024}KB)")

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="搜索公众人物音频并下载")
    parser.add_argument("--name", required=True, help="公众人物姓名")
    parser.add_argument("--keyword", default="演讲", help="附加搜索关键词（默认: 演讲）")
    parser.add_argument("--output-dir", default="./audio_samples", help="音频保存目录")
    parser.add_argument("--max-results", type=int, default=5, help="最大结果数（默认: 5）")

    args = parser.parse_args()
    check_deps()
    search_and_download(args.name, args.keyword, args.output_dir, args.max_results)


if __name__ == "__main__":
    main()

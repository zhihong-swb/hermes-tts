#!/usr/bin/env python3
"""
从多个平台搜索公众人物音频并下载

支持平台：
  - bilibili (B站，默认) - 中文内容首选，通过 yt-dlp bilisearch
  - youtube - 国际内容，通过 yt-dlp ytsearch
  - url     - 直接提供链接下载（支持 yt-dlp 所有平台）

用法：
    python search_audio.py --name "雷军" --keyword "演讲"
    python search_audio.py --name "雷军" --source bilibili
    python search_audio.py --name "Elon Musk" --source youtube --keyword "interview"
    python search_audio.py --url "https://www.bilibili.com/video/BVxxxxxx"
"""

import argparse
import json
import logging
import os
import re
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
        print("请执行: pip install yt-dlp  (ffmpeg 需单独安装)", file=sys.stderr)
        sys.exit(1)


def _search_via_ytdlp(search_prefix: str, query: str, max_results: int):
    """通用 yt-dlp 搜索，返回条目列表"""
    search_query = f"{search_prefix}{max_results}:{query}"
    cmd = [
        "yt-dlp",
        search_query,
        "--dump-json",
        "--flat-playlist",
        "--no-download",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        logger.error(f"搜索失败: {result.stderr[:300]}")
        return []

    entries = []
    for line in result.stdout.strip().split("\n"):
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


# ─── B站搜索 ───────────────────────────────────────────────

def search_and_download_bilibili(name: str, keyword: str, output_dir: str, max_results: int):
    """从 B站搜索并下载音频（通过 yt-dlp bilisearch）"""
    os.makedirs(output_dir, exist_ok=True)
    query = f"{name} {keyword}"
    logger.info(f"[B站] 搜索: {query} (最多 {max_results} 条)")

    entries = _search_via_ytdlp("bilisearch", query, max_results)
    if not entries:
        logger.warning("B站未找到相关视频")
        return []

    print(f"\n找到 {len(entries)} 条B站结果：\n")
    for i, e in enumerate(entries):
        title = e.get("title", "未知")
        duration = e.get("duration")
        dur_str = f"{int(duration)}秒" if duration else "未知时长"
        uploader = e.get("uploader", e.get("channel", ""))
        print(f"  [{i+1}] {title} ({dur_str}) UP:{uploader}")

    return _download_entries(entries, output_dir, platform="bilibili")


# ─── YouTube 搜索 ──────────────────────────────────────────

def search_and_download_youtube(name: str, keyword: str, output_dir: str, max_results: int):
    """从 YouTube 搜索并下载音频"""
    os.makedirs(output_dir, exist_ok=True)
    query = f"{name} {keyword}"
    logger.info(f"[YouTube] 搜索: {query} (最多 {max_results} 条)")

    entries = _search_via_ytdlp("ytsearch", query, max_results)
    if not entries:
        logger.warning("YouTube 未找到相关音频")
        return []

    print(f"\n找到 {len(entries)} 条 YouTube 结果：\n")
    for i, e in enumerate(entries):
        title = e.get("title", "未知")
        duration = e.get("duration")
        dur_str = f"{int(duration)}秒" if duration else "未知时长"
        print(f"  [{i+1}] {title} ({dur_str})")

    return _download_entries(entries, output_dir, platform="youtube")


# ─── 直接 URL 下载 ─────────────────────────────────────────

def download_from_url(url: str, output_dir: str):
    """从任意 yt-dlp 支持的 URL 下载音频"""
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"[URL] 直接下载: {url}")

    entries = [{"title": "audio", "url": url, "webpage_url": url}]
    return _download_entries(entries, output_dir, platform="url")


# ─── 通用下载 ──────────────────────────────────────────────

def _get_download_url(entry: dict, platform: str) -> str:
    """根据平台构造下载 URL"""
    webpage_url = entry.get("webpage_url", "")
    if webpage_url and webpage_url.startswith("http"):
        return webpage_url

    url = entry.get("url", "")
    video_id = entry.get("id", "")

    if platform == "bilibili":
        if video_id and not video_id.startswith("http"):
            return f"https://www.bilibili.com/video/{video_id}"
    elif platform == "youtube":
        if video_id and not video_id.startswith("http"):
            return f"https://www.youtube.com/watch?v={video_id}"

    return url if url.startswith("http") else ""


def _download_entries(entries: list, output_dir: str, platform: str = ""):
    """下载音频列表，返回已下载的文件路径"""
    downloaded = []
    for i, entry in enumerate(entries):
        title = entry.get("title", f"audio_{i+1}")
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title).strip()[:50]
        output_template = os.path.join(output_dir, f"{safe_title}.%(ext)s")

        url = _get_download_url(entry, platform)
        if not url:
            logger.warning(f"  [{i+1}] 无法获取下载地址，跳过")
            continue

        logger.info(f"下载 [{i+1}/{len(entries)}]: {title}")
        dl_cmd = [
            "yt-dlp",
            url,
            "-x",                          # 仅提取音频
            "--audio-format", "wav",        # 转为 wav
            "--audio-quality", "0",         # 最高质量
            "-o", output_template,
            "--no-playlist",
            "--max-filesize", "50M",
        ]
        dl_result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
        if dl_result.returncode == 0:
            for f in os.listdir(output_dir):
                full_path = os.path.join(output_dir, f)
                if safe_title in f and full_path not in downloaded:
                    downloaded.append(full_path)
                    logger.info(f"  已下载: {full_path}")
        else:
            logger.warning(f"  下载失败: {dl_result.stderr[:200]}")

    print(f"\n共下载 {len(downloaded)} 个音频文件到 {output_dir}/")
    for f in downloaded:
        size = os.path.getsize(f)
        print(f"  {f} ({size // 1024}KB)")

    return downloaded


# ─── 入口 ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="从多个平台搜索公众人物音频并下载",
        epilog="支持平台: bilibili(B站,默认), youtube, url(直接链接,支持B站/YouTube/抖音等)"
    )
    parser.add_argument("--name", help="公众人物姓名（搜索模式）")
    parser.add_argument("--keyword", default="演讲", help="附加搜索关键词（默认: 演讲）")
    parser.add_argument("--source", default="bilibili",
                        choices=["bilibili", "youtube", "url"],
                        help="音频来源平台（默认: bilibili）")
    parser.add_argument("--url", help="直接提供视频/音频链接（支持 B站/YouTube/抖音等）")
    parser.add_argument("--output-dir", default="./audio_samples", help="音频保存目录")
    parser.add_argument("--max-results", type=int, default=5, help="最大结果数（默认: 5）")

    args = parser.parse_args()
    check_deps()

    if args.url:
        download_from_url(args.url, args.output_dir)
    elif args.name:
        if args.source == "bilibili":
            search_and_download_bilibili(args.name, args.keyword, args.output_dir, args.max_results)
        elif args.source == "youtube":
            search_and_download_youtube(args.name, args.keyword, args.output_dir, args.max_results)
        else:
            parser.error("--source url 模式必须提供 --url 参数")
    else:
        parser.error("必须提供 --name（搜索模式）或 --url（直接下载模式）")


if __name__ == "__main__":
    main()

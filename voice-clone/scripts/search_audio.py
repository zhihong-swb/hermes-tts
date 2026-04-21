#!/usr/bin/env python3
"""
从多个平台搜索公众人物音频并下载

搜索方式：
  - web（默认）  - 通过公开搜索引擎查找视频，无需登录/cookie
  - bilibili     - 通过 yt-dlp bilisearch（有 cookie 效果更好）
  - youtube      - 通过 yt-dlp ytsearch
  - url          - 直接提供链接下载（支持 B站/抖音/YouTube 等）

Cookie 支持：
  将浏览器导出的 cookie 放到 ~/.hermes/cookies/ 目录：
    bilibili.txt  - B站 cookie（Netscape 格式）
    youtube.txt   - YouTube cookie
    douyin.txt    - 抖音 cookie
  脚本会自动检测并加载对应平台的 cookie，绕过反爬限制。
  也可通过 --cookies 参数手动指定 cookie 文件。

用法：
    python search_audio.py --name "雷军" --keyword "演讲"
    python search_audio.py --name "雷军" --source bilibili
    python search_audio.py --name "雷军" --source bilibili --cookies /path/to/cookies.txt
    python search_audio.py --url "https://www.bilibili.com/video/BVxxxxxx"
    python search_audio.py --url "https://www.douyin.com/video/xxxxxx"
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-clone")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Cookie 目录和平台映射
COOKIE_DIR = os.path.expanduser("~/.hermes/cookies")
PLATFORM_COOKIE_FILES = {
    "bilibili": ["bilibili.txt", "bilibili_cookies.txt"],
    "youtube": ["youtube.txt", "youtube_cookies.txt"],
    "douyin": ["douyin.txt", "douyin_cookies.txt"],
}


def _find_cookie_file(platform: str, explicit_path: str = "") -> str:
    """查找平台的 cookie 文件。优先使用显式指定的路径，其次自动检测。"""
    if explicit_path:
        if os.path.isfile(explicit_path):
            logger.info(f"使用指定 cookie 文件: {explicit_path}")
            return explicit_path
        logger.warning(f"指定的 cookie 文件不存在: {explicit_path}")
        return ""

    candidates = PLATFORM_COOKIE_FILES.get(platform, [])
    for fname in candidates:
        path = os.path.join(COOKIE_DIR, fname)
        if os.path.isfile(path):
            logger.info(f"自动加载 {platform} cookie: {path}")
            return path

    return ""


def _detect_platform_from_url(url: str) -> str:
    """从 URL 检测平台"""
    if "bilibili.com" in url or "b23.tv" in url:
        return "bilibili"
    elif "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "douyin.com" in url:
        return "douyin"
    return ""


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


# ─── 公开网络搜索（默认方式，无需 cookie）──────────────────

def _web_search_videos(query: str, max_results: int):
    """通过 DuckDuckGo HTML 搜索视频链接（无需 API key）"""
    search_query = urllib.parse.quote(f"{query} site:bilibili.com OR site:douyin.com OR site:youtube.com")
    search_url = f"https://html.duckduckgo.com/html/?q={search_query}"

    req = urllib.request.Request(search_url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"网络搜索失败: {e}")
        return []

    # 从 DuckDuckGo HTML 结果中提取链接和标题
    url_pattern = re.compile(r'class="result__a"\s+href="([^"]+)"')
    title_pattern = re.compile(r'class="result__a"[^>]*>(.+?)</a>', re.DOTALL)

    urls = url_pattern.findall(html)
    titles = title_pattern.findall(html)

    video_domains = ["bilibili.com/video/", "b23.tv/", "douyin.com/video/",
                     "youtube.com/watch", "youtu.be/"]

    entries = []
    for i, url in enumerate(urls):
        # DuckDuckGo 的 URL 可能有重定向包装
        if "uddg=" in url:
            match = re.search(r'uddg=([^&]+)', url)
            if match:
                url = urllib.parse.unquote(match.group(1))

        if any(d in url for d in video_domains):
            title = ""
            if i < len(titles):
                title = re.sub(r'<[^>]+>', '', titles[i]).strip()
            entries.append({
                "title": title or f"视频 {len(entries)+1}",
                "url": url,
                "webpage_url": url,
            })
            if len(entries) >= max_results:
                break

    return entries


def search_and_download_web(name: str, keyword: str, output_dir: str, max_results: int,
                            cookies: str = ""):
    """通过公开搜索引擎查找视频并下载音频"""
    os.makedirs(output_dir, exist_ok=True)
    query = f"{name} {keyword}"
    logger.info(f"[网络搜索] {query} (最多 {max_results} 条)")

    entries = _web_search_videos(query, max_results)

    if not entries:
        logger.warning("未搜索到视频结果")
        logger.warning(f"替代方案: 手动找到视频链接后用 --url 下载")
        return []

    print(f"\n找到 {len(entries)} 条视频结果：\n")
    for i, e in enumerate(entries):
        domain = urllib.parse.urlparse(e["url"]).netloc
        print(f"  [{i+1}] {e['title'][:60]} ({domain})")

    return _download_entries(entries, output_dir, cookies=cookies)


# ─── yt-dlp 平台搜索 ──────────────────────────────────────

def _search_via_ytdlp(search_prefix: str, query: str, max_results: int,
                      cookie_file: str = ""):
    """通用 yt-dlp 搜索"""
    cmd = [
        "yt-dlp",
        f"{search_prefix}{max_results}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
    ]
    if cookie_file:
        cmd.extend(["--cookies", cookie_file])

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


def search_and_download_bilibili(name: str, keyword: str, output_dir: str, max_results: int,
                                 cookies: str = ""):
    """从 B站搜索并下载音频"""
    os.makedirs(output_dir, exist_ok=True)
    query = f"{name} {keyword}"

    cookie_file = _find_cookie_file("bilibili", cookies)
    if cookie_file:
        logger.info(f"[B站] 搜索: {query} (使用 cookie)")
    else:
        logger.info(f"[B站] 搜索: {query} (无 cookie，可能触发反爬)")

    entries = _search_via_ytdlp("bilisearch", query, max_results, cookie_file=cookie_file)
    if not entries:
        logger.warning("B站搜索失败（可能触发反爬），自动切换到网络搜索...")
        if not cookie_file:
            logger.warning("提示: 提供 B站 cookie 可避免反爬限制，详见 setup.md")
        return search_and_download_web(name, keyword, output_dir, max_results, cookies=cookies)

    print(f"\n找到 {len(entries)} 条B站结果：\n")
    for i, e in enumerate(entries):
        title = e.get("title", "未知")
        duration = e.get("duration")
        dur_str = f"{int(duration)}秒" if duration else "未知时长"
        uploader = e.get("uploader", e.get("channel", ""))
        print(f"  [{i+1}] {title} ({dur_str}) UP:{uploader}")

    return _download_entries(entries, output_dir, platform="bilibili", cookies=cookies)


def search_and_download_youtube(name: str, keyword: str, output_dir: str, max_results: int,
                                cookies: str = ""):
    """从 YouTube 搜索并下载音频"""
    os.makedirs(output_dir, exist_ok=True)
    query = f"{name} {keyword}"

    cookie_file = _find_cookie_file("youtube", cookies)
    if cookie_file:
        logger.info(f"[YouTube] 搜索: {query} (使用 cookie)")
    else:
        logger.info(f"[YouTube] 搜索: {query}")

    entries = _search_via_ytdlp("ytsearch", query, max_results, cookie_file=cookie_file)
    if not entries:
        logger.warning("YouTube 未找到相关音频")
        return []

    print(f"\n找到 {len(entries)} 条 YouTube 结果：\n")
    for i, e in enumerate(entries):
        title = e.get("title", "未知")
        duration = e.get("duration")
        dur_str = f"{int(duration)}秒" if duration else "未知时长"
        print(f"  [{i+1}] {title} ({dur_str})")

    return _download_entries(entries, output_dir, platform="youtube", cookies=cookies)


# ─── 直接 URL 下载 ─────────────────────────────────────────

def download_from_url(url: str, output_dir: str, cookies: str = ""):
    """从任意 yt-dlp 支持的 URL 下载音频"""
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"[URL] 直接下载: {url}")

    # 自动检测 URL 对应平台的 cookie
    platform = _detect_platform_from_url(url)

    entries = [{"title": "audio", "url": url, "webpage_url": url}]
    return _download_entries(entries, output_dir, platform=platform, cookies=cookies)


# ─── 通用下载 ──────────────────────────────────────────────

def _get_download_url(entry: dict, platform: str = "") -> str:
    """根据平台构造下载 URL"""
    webpage_url = entry.get("webpage_url", "")
    if webpage_url and webpage_url.startswith("http"):
        return webpage_url

    url = entry.get("url", "")
    video_id = entry.get("id", "")

    if platform == "bilibili" and video_id and not video_id.startswith("http"):
        return f"https://www.bilibili.com/video/{video_id}"
    elif platform == "youtube" and video_id and not video_id.startswith("http"):
        return f"https://www.youtube.com/watch?v={video_id}"

    return url if url.startswith("http") else ""


def _download_entries(entries: list, output_dir: str, platform: str = "",
                      cookies: str = ""):
    """下载音频列表，返回已下载的文件路径"""
    # 下载时也加载对应平台的 cookie
    cookie_file = ""
    if platform:
        cookie_file = _find_cookie_file(platform, cookies)
    elif cookies and os.path.isfile(cookies):
        cookie_file = cookies

    downloaded = []
    for i, entry in enumerate(entries):
        title = entry.get("title", f"audio_{i+1}")
        safe_title = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', title).strip()[:50]
        if not safe_title:
            safe_title = f"audio_{i+1}"
        output_template = os.path.join(output_dir, f"{safe_title}.%(ext)s")

        url = _get_download_url(entry, platform)
        if not url:
            logger.warning(f"  [{i+1}] 无法获取下载地址，跳过")
            continue

        # 如果 entry 里没有 platform 但 URL 可以检测到，也尝试加载 cookie
        if not cookie_file:
            detected = _detect_platform_from_url(url)
            if detected:
                cookie_file = _find_cookie_file(detected, cookies)

        logger.info(f"下载 [{i+1}/{len(entries)}]: {title[:50]}")
        dl_cmd = [
            "yt-dlp",
            url,
            "-x",
            "--audio-format", "wav",
            "--audio-quality", "0",
            "-o", output_template,
            "--no-playlist",
            "--max-filesize", "50M",
        ]
        if cookie_file:
            dl_cmd.extend(["--cookies", cookie_file])

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
        epilog="支持: web(默认,无需登录), bilibili, youtube, url(直接链接). "
               "Cookie: 放到 ~/.hermes/cookies/ 目录或用 --cookies 指定"
    )
    parser.add_argument("--name", help="公众人物姓名（搜索模式）")
    parser.add_argument("--keyword", default="演讲", help="附加搜索关键词（默认: 演讲）")
    parser.add_argument("--source", default="web",
                        choices=["web", "bilibili", "youtube", "url"],
                        help="搜索方式（默认: web，通过搜索引擎，无需登录）")
    parser.add_argument("--url", help="直接提供视频/音频链接（支持 B站/抖音/YouTube 等）")
    parser.add_argument("--cookies", default="",
                        help="cookie 文件路径（Netscape 格式）。不指定时自动查找 ~/.hermes/cookies/")
    parser.add_argument("--output-dir", default="./audio_samples", help="音频保存目录")
    parser.add_argument("--max-results", type=int, default=5, help="最大结果数（默认: 5）")

    args = parser.parse_args()
    check_deps()

    if args.url:
        download_from_url(args.url, args.output_dir, cookies=args.cookies)
    elif args.name:
        if args.source == "web":
            search_and_download_web(args.name, args.keyword, args.output_dir,
                                    args.max_results, cookies=args.cookies)
        elif args.source == "bilibili":
            search_and_download_bilibili(args.name, args.keyword, args.output_dir,
                                         args.max_results, cookies=args.cookies)
        elif args.source == "youtube":
            search_and_download_youtube(args.name, args.keyword, args.output_dir,
                                        args.max_results, cookies=args.cookies)
        else:
            parser.error("--source url 模式必须提供 --url 参数")
    else:
        parser.error("必须提供 --name（搜索模式）或 --url（直接下载模式）")


if __name__ == "__main__":
    main()

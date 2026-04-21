#!/usr/bin/env python3
"""
列出可用的 TTS 音色

用法：
    python voices.py               # 列出所有中文音色
    python voices.py --locale zh   # 所有中文（含粤语、台湾）
    python voices.py --locale en   # 英文音色
    python voices.py --all         # 列出所有音色
"""

import argparse
import asyncio
import sys

try:
    import edge_tts
except ImportError:
    print("缺少依赖: edge-tts", file=sys.stderr)
    print("请执行: pip install edge-tts", file=sys.stderr)
    sys.exit(1)


async def list_voices(locale: str = "zh", show_all: bool = False):
    voices = await edge_tts.list_voices()

    if not show_all and locale:
        voices = [v for v in voices if locale.lower() in v["Locale"].lower()]

    if not voices:
        print(f"没有找到 locale={locale} 的音色")
        return

    print(f"{'音色名称':<38} {'性别':<8} {'语言区域':<15}")
    print("-" * 65)
    for v in sorted(voices, key=lambda x: x["Locale"]):
        gender = "男" if v["Gender"] == "Male" else "女"
        print(f"{v['ShortName']:<38} {gender:<8} {v['Locale']:<15}")

    print(f"\n共 {len(voices)} 个音色")


def main():
    parser = argparse.ArgumentParser(description="列出可用的 TTS 音色")
    parser.add_argument("--locale", default="zh", help="语言区域过滤（默认 zh）")
    parser.add_argument("--all", action="store_true", help="列出所有音色")
    args = parser.parse_args()
    asyncio.run(list_voices(locale=args.locale, show_all=args.all))


if __name__ == "__main__":
    main()

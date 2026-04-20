"""CLI entry point for hermes-tts."""

import asyncio
import json
import logging

from hermes_tts.engines import EdgeTTSEngine
from hermes_tts.service import create_service


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hermes TTS - Voice Synthesis & Delivery")
    parser.add_argument("text", nargs="?", default="", help="Text to synthesize")
    parser.add_argument("--engine", default="edge", choices=["edge", "fish", "cosyvoice", "gpt-sovits"])
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural", help="Voice name (edge-tts)")
    parser.add_argument("--platform", default="local", choices=["feishu", "local"])
    parser.add_argument("--target", default="test", help="Target ID")
    parser.add_argument("--output-dir", default="./voice_output", help="Output dir (local platform)")
    parser.add_argument("--list-voices", action="store_true", help="List available Chinese voices")
    parser.add_argument("--locale", default="zh", help="Voice locale filter (default: zh)")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    if args.list_voices:
        asyncio.run(_list_voices(args.locale))
        return

    if not args.text:
        parser.error("text is required when not using --list-voices")

    asyncio.run(_synthesize(args))


async def _list_voices(locale: str):
    voices = await EdgeTTSEngine.list_voices(locale=locale)
    for v in voices:
        print(f"  {v['name']:35s} {v['gender']:8s} {v['locale']}")


async def _synthesize(args):
    svc = create_service(
        engine_type=args.engine,
        platform=args.platform,
        voice=args.voice,
        output_dir=args.output_dir,
    )
    result = await svc.speak(text=args.text, target_id=args.target)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

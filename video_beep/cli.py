"""video-beep 命令行入口。

用法示例：
  python -m video_beep 视频.mp4 -o 处理后的.mp4            # 默认静音
  python -m video_beep 视频.mp4 -o 处理后的.mp4 --beep     # 用哔声盖住
  python -m video_beep 视频.mp4 -o 处理后的.mp4 --model small --lang zh
"""
from __future__ import annotations

import argparse
import sys
import time

from . import __version__
from .censor import censor


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="video-beep",
        description="自动去除视频中的脏话（静音或用哔声盖住）。")
    p.add_argument("video", help="输入视频路径（支持 mp4/mkv/avi/webm 等）")
    p.add_argument("-o", "--output", help="输出视频路径（默认在原文件名后加 _censored）")
    p.add_argument("--model", default="base",
                   help="Whisper 模型大小：tiny/base/small/medium/large（越大越准、越慢），默认 base")
    p.add_argument("--lang", default=None,
                   help="强制识别语言，如 zh / en（默认自动检测）")
    p.add_argument("--mode", choices=["mute", "beep"], default="mute",
                   help="处理方式：mute=静音（默认），beep=用哔声盖住")
    p.add_argument("--beep", action="store_true",
                   help="快捷开关：等同于 --mode beep")
    p.add_argument("--pad", type=float, default=0.3,
                   help="脏话前后各多静音/哔声的秒数（默认 0.3）")
    p.add_argument("--thorough", action="store_true",
                   help="彻底模式：包含脏话的整个句子整段静音，更干净但会多静音一些上下文")
    p.add_argument("--no-beep-dry", action="store_true", help="（保留）")
    p.add_argument("--version", action="version", version=f"video-beep {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    mode = "beep" if args.beep else args.mode

    if args.output is None:
        from pathlib import Path
        src = Path(args.video)
        args.output = str(src.with_name(src.stem + "_censored" + src.suffix))

    print(f"[video-beep] 正在处理: {args.video}")
    print(f"  -> 输出: {args.output}")
    print(f"  -> 模型: {args.model} | 模式: {mode} | 语言: {args.lang or '自动'}"
          f"{' | 彻底模式' if args.thorough else ''}")
    t0 = time.time()

    try:
        stats = censor(
            args.video, args.output,
            model=args.model, language=args.lang,
            mode=mode, pad=args.pad, thorough=args.thorough,
        )
    except FileNotFoundError:
        print("[错误] 找不到输入视频，请检查路径。", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[错误] 处理失败: {e}", file=sys.stderr)
        return 2

    print(f"\n完成，耗时 {time.time() - t0:.1f} 秒")
    if stats["copied"]:
        print("未检测到脏话，已直接复制输出。")
    else:
        print(f"检测到并处理 {stats['profanity_count']} 处脏话：")
        for w in stats["windows"]:
            print(f"  - {w['start']:.2f}s ~ {w['end']:.2f}s")
    if stats["transcript"]:
        print(f"\n语音转写片段:\n  {stats['transcript'][:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

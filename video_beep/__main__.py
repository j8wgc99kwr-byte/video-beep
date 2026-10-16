"""支持 `python -m video_beep` 作为命令行入口。"""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())

# video-beep

自动去除视频中的脏话：用语音识别定位脏话出现的时间段，然后把那一段**静音**或用**哔声**盖住。画面原样保留，只改音频。支持中英文。

## 特性

- 🎯 逐词时间戳，精确定位脏话，前后可加缓冲（默认 0.15 秒）
- 🗣️ 中英文双语脏话识别（faster-whisper，可换模型提升准确度）
- 🔇 `mute` 静音 / `🔊 beep` 哔声两种处理方式
- ⚡ 未检测到脏话时直接复制，零重编码

## 工作原理

```
输入视频 ──► 抽取音轨(ffmpeg) ──► faster-whisper 逐词转写
                                        │
                                        ▼
输出视频 ◄── ffmpeg 静音/哔声 ◄── 定位脏话时间段 ◄── 中英文词库匹配
```

## 安装

需要 Python 3.9+ 和 [FFmpeg](https://ffmpeg.org/download.html)（已加入 PATH）。

```bash
git clone https://github.com/<你的用户名>/video-beep.git
cd video-beep
pip install -r requirements.txt
```

首次运行会下载 Whisper 模型（base 约 150MB）。

> 🇨🇳 国内用户：huggingface.co 可能无法直连。先设置镜像再运行：
>
> ```bash
> # Windows (PowerShell)
> $env:HF_ENDPOINT="https://hf-mirror.com"
> # macOS / Linux
> export HF_ENDPOINT="https://hf-mirror.com"
> ```

## 使用

```bash
# 基本用法：静音掉脏话
python -m video_beep 视频.mp4 -o 处理后.mp4

# 用哔声盖住
python -m video_beep 视频.mp4 -o 处理后.mp4 --beep

# 提升识别准确度（更慢）
python -m video_beep 视频.mp4 -o 处理后.mp4 --model small

# 指定语言（默认自动检测）
python -m video_beep 视频.mp4 -o 处理后.mp4 --lang zh
```

### 参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `-o, --output` | 输出路径 | 原文件名后加 `_censored` |
| `--model` | Whisper 模型 `tiny/base/small/medium/large` | `base` |
| `--lang` | 识别语言 `zh`/`en` 等 | 自动检测 |
| `--mode` | `mute` 静音 / `beep` 哔声 | `mute` |
| `--pad` | 脏话前后多处理的秒数 | `0.15` |

## 词库

脏话词条在 `video_beep/lexicon.py`，支持中英文及常见屏蔽写法（如 `f*ck`、`s**t`）。可自行增删。

## 开发者

```bash
pip install -r requirements.txt
python -m video_beep 测试.mp4
```

## 许可

MIT

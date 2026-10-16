"""核心处理逻辑：语音识别 -> 脏话定位 -> FFmpeg 静音/哔声。

依赖：ffmpeg 需在 PATH 中；faster-whisper 需 pip 安装。
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .lexicon import PROFANITY_ZH, PROFANITY_EN_TOKENS, PROFANITY_EN_PHRASES

_ALNUM = re.compile(r"[^a-z0-9]")


@dataclass
class Window:
    """一个需要处理的音频时间段（秒）。"""
    start: float
    end: float


def _norm_en(text: str) -> str:
    """英文归一化：小写并去掉非字母数字字符（同时抹掉屏蔽符号）。"""
    return _ALNUM.sub("", text.lower())


def _find_english_hits(full_text: str) -> list[tuple[int, int]]:
    """在（小写、连续）文本中定位英文脏话，返回 [start, end) 字符区间。"""
    hits: list[tuple[int, int]] = []

    # 1) 单词 token 匹配（需要词边界，防止 "class" 命中 "ass"）
    for m in re.finditer(r"[a-z]+", full_text):
        token = m.group(0)
        if token in PROFANITY_EN_TOKENS:
            hits.append((m.start(), m.end()))

    # 2) 多词短语匹配（带词边界）
    for phrase in PROFANITY_EN_PHRASES:
        for m in re.finditer(rf"\b{re.escape(phrase)}\b", full_text):
            hits.append((m.start(), m.end()))

    return hits


def _find_chinese_hits(full_text: str) -> list[tuple[int, int]]:
    """在文本中定位中文脏话词组，返回 [start, end) 字符区间。"""
    hits: list[tuple[int, int]] = []
    for phrase in PROFANITY_ZH:
        for m in re.finditer(re.escape(phrase), full_text):
            hits.append((m.start(), m.end()))
    return hits


def _merge_hits(hits: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """合并重叠/相邻的命中区间。"""
    if not hits:
        return []
    ordered = sorted(hits)
    merged = [ordered[0]]
    for s, e in ordered[1:]:
        if s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return merged


def _char_to_words(words: list, positions: list[tuple[int, int]]) -> list[Window]:
    """把字符区间映射回 Whisper 的逐词时间戳，得到音频时间窗。"""
    if not words or not positions:
        return []

    # 累计每个词的字符区间
    spans = []
    pos = 0
    for w in words:
        length = len(w.word)
        spans.append((pos, pos + length, w.start, w.end))
        pos += length

    windows: list[Window] = []
    for cs, ce in positions:
        seg_start = seg_end = None
        for ws, we, t_start, t_end in spans:
            if we <= cs:
                continue
            if ws >= ce:
                break
            if seg_start is None or t_start < seg_start:
                seg_start = t_start
            if seg_end is None or t_end > seg_end:
                seg_end = t_end
        if seg_start is not None:
            windows.append(Window(seg_start, seg_end))
    return windows


def locate_profanity_words(words: list, full_text: str) -> list[Window]:
    """从 Whisper 词列表和拼接文本中定位脏话时间段。"""
    low = full_text.lower()
    hits = _find_english_hits(low) + _find_chinese_hits(low)
    hits = _merge_hits(hits)
    return _char_to_words(words, hits)


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _has_video_stream(path: str) -> bool:
    """判断输入文件是否包含视频流（没有则按纯音频处理）。"""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, text=True)
    return bool(out.stdout.strip())


def _audio_codec_args(output: str) -> list[str]:
    """按输出扩展名选择音频编码参数（纯音频输出时使用）。"""
    ext = Path(output).suffix.lower()
    if ext == ".mp3":
        return ["-c:a", "libmp3lame", "-b:a", "192k"]
    if ext in (".m4a", ".mp4"):
        return ["-c:a", "aac", "-b:a", "192k"]
    if ext == ".flac":
        return ["-c:a", "flac"]
    return ["-c:a", "pcm_s16le"]  # .wav 及默认


def extract_audio(video: str, wav: str, sample_rate: int = 16000) -> None:
    """抽取视频音轨为 16k 单声道 wav（Whisper 的输入要求）。"""
    _run(["ffmpeg", "-y", "-i", video, "-vn",
          "-acodec", "pcm_s16le", "-ar", str(sample_rate), "-ac", "1", wav])


def transcribe(wav: str, model_name: str, language: str | None = None):
    """用 faster-whisper 转写，返回 (拼接文本, 词列表)。"""
    from faster_whisper import WhisperModel  # 延迟导入，加快 --help
    model = WhisperModel(model_name, device="auto", compute_type="int8")
    segments, _ = model.transcribe(
        wav, word_timestamps=True, language=language, vad_filter=True)
    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append(w)
    full_text = "".join(w.word for w in words)
    return full_text, words


def _window_expr(windows: list[Window], pad: float) -> str:
    """把时间窗拼成 ffmpeg 的 enable 表达式（+ 表示 OR）。"""
    parts = []
    for w in windows:
        parts.append(f"between(t,{max(0.0, w.start - pad):.3f},"
                     f"{w.end + pad:.3f})")
    return "+".join(parts)


def _filter_mute(input_idx: int, windows: list[Window], pad: float) -> list[str]:
    expr = _window_expr(windows, pad)
    return [
        f"[{input_idx}:a]volume=enable='({expr})':volume=0[muted]",
    ]


def _render_beep_beeps(windows: list[Window], pad: float, tmpdir: Path) -> list[str]:
    """为每个时间窗生成一段延迟到位的 1000Hz 哔声，返回 (路径, 滤波说明)。"""
    beep_paths = []
    for i, w in enumerate(windows):
        start = max(0.0, w.start - pad)
        dur = max(0.05, (w.end + pad) - start)
        out = tmpdir / f"beep_{i}.wav"
        _run(["ffmpeg", "-y", "-f", "lavfi",
              "-i", f"sine=frequency=1000:duration={dur:.3f}",
              "-af", f"adelay={int(start * 1000)}|{int(start * 1000)}",
              "-acodec", "pcm_s16le", str(out)])
        beep_paths.append(str(out))
    return beep_paths


def _filter_beep(input_idx: int, beep_paths: list[str]) -> list[str]:
    filters = [f"[{input_idx}:a]anull[base]"]
    for i, _ in enumerate(beep_paths):
        filters.append(
            f"[{i + 1}:a]volume=0.5,apad[beep{i}]")
    inputs = "[base]" + "".join(f"[beep{i}]" for i in range(len(beep_paths)))
    filters.append(
        f"{inputs}amix=inputs={len(beep_paths) + 1}:duration=first:normalize=0[muted]")
    return filters


def build_audio_filter(input_idx: int, windows: list[Window],
                       pad: float, mode: str, tmpdir: Path):
    """构造 ffmpeg 音频滤镜。返回 (filter_text, 需要的额外输入文件列表)。"""
    if not windows:
        return None, []
    if mode == "mute":
        return ";".join(_filter_mute(input_idx, windows, pad)), []
    if mode == "beep":
        beep_paths = _render_beep_beeps(windows, pad, tmpdir)
        return ";".join(_filter_beep(input_idx, beep_paths)), beep_paths
    raise ValueError(f"未知模式: {mode}")


def censor(video: str, output: str, model: str = "base",
           language: str | None = None, mode: str = "mute",
           pad: float = 0.15, sample_rate: int = 16000) -> dict:
    """主入口：处理视频/音频并返回统计信息。

    输入可以是视频（mp4/mkv 等）也可以是纯音频（mp3/wav/m4a 等）；
    纯音频输入时输出仅含处理后的音轨。
    """
    video = str(Path(video).resolve())
    output = str(Path(output).resolve())

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        wav = tmpdir / "audio.wav"

        extract_audio(video, wav, sample_rate)
        full_text, words = transcribe(str(wav), model, language)
        windows = locate_profanity_words(words, full_text)

        filter_text, extra_inputs = build_audio_filter(0, windows, pad, mode, tmpdir)

        if filter_text is None:
            # 没有脏话：直接复制，最快
            _run(["ffmpeg", "-y", "-i", video, "-c", "copy", output])
            return {"profanity_count": 0, "windows": [], "copied": True,
                    "transcript": full_text.strip()}

        has_video = _has_video_stream(video)
        cmd = ["ffmpeg", "-y", "-i", video]
        for b in extra_inputs:
            cmd += ["-i", b]
        cmd += ["-filter_complex", filter_text]
        if has_video:
            # 有视频流：保留画面，仅重编码音频
            cmd += ["-map", "0:v", "-map", "[muted]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
        else:
            # 纯音频：只输出处理后的音轨
            cmd += ["-map", "[muted]"] + _audio_codec_args(output)
        cmd += [output]
        _run(cmd)

    return {
        "profanity_count": len(windows),
        "windows": [{"start": w.start, "end": w.end} for w in windows],
        "copied": False,
        "transcript": full_text.strip(),
    }

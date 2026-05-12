import json
import os
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel

from app.srt import segments_to_srt
from app.voice_clone import generate_cloned_dub 

MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
DEVICE = os.getenv("DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")

_model = None


def get_model() -> WhisperModel:
    global _model

    if _model is None:
        _model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)

    return _model


def extract_audio(input_path: Path, audio_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(audio_path),
    ]

    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def format_time(seconds: float) -> str:
    milliseconds = int(seconds * 1000)

    hours = milliseconds // 3600000
    milliseconds %= 3600000

    minutes = milliseconds // 60000
    milliseconds %= 60000

    secs = milliseconds // 1000
    ms = milliseconds % 1000

    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def write_txt_with_timestamps(segments, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        for segment in segments:
            start = format_time(segment["start"])
            end = format_time(segment["end"])
            speaker = segment.get("speaker", "Speaker 0")
            text = segment["text"].strip()

            f.write(f"{start} --> {end} [{speaker}]\n")
            f.write(f"{text}\n\n")


def transcribe_file(
    input_path: Path,
    result_dir: Path,
    language: str | None = "fr",
    make_translation: bool = False,
    make_dubbing: bool = False,
    target_languages: list[str] | None = None,
) -> dict:
    result_dir.mkdir(parents=True, exist_ok=True)

    target_languages = target_languages or []

    audio_path = result_dir / "audio.wav"
    extract_audio(input_path, audio_path)

    model = get_model()

    segments_iterator, info = model.transcribe(
        str(audio_path),
        language=None if language == "auto" else language,
        vad_filter=False,
        beam_size=5,
    )

    whisper_segments = list(segments_iterator)

    print("NOMBRE DE SEGMENTS WHISPER =", len(whisper_segments))
    for s in whisper_segments[:10]:
        print(s.start, s.end, s.text)

    segments = []

    for segment in whisper_segments:
        segments.append(
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "speaker": "Spe aker 0",
                "text": segment.text.strip(),
            }
        )

    txt_path = result_dir / "transcription.txt"
    srt_path = result_dir / "subtitles.srt"
    json_path = result_dir / "segments.json"

    srt = segments_to_srt(segments)

    write_txt_with_timestamps(segments, txt_path)
    srt_path.write_text(srt, encoding="utf-8")
    json_path.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")

    translated_files = {}

    if make_translation:
        from app.translator import translate_segments

        for lang in target_languages:
            translated_segments = translate_segments(segments, lang)
            translated_srt = segments_to_srt(translated_segments)

            translated_path = result_dir / f"subtitles_{lang}.srt"
            translated_path.write_text(translated_srt, encoding="utf-8")

            translated_files[lang] = str(translated_path)

    dub_files = {}

 

    if audio_path.exists():
        audio_path.unlink()

    return {
        "language": info.language,
        "duration": info.duration,
        "segments": segments,
        "txt_file": str(txt_path),
        "srt_file": str(srt_path),
        "json_file": str(json_path),
        "translated_files": translated_files,
        "dub_files": dub_files,
    }
import json
import os
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel
from app.srt import segments_to_srt

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


# ✅ FUSION SEGMENTS POUR TXT
def merge_segments_for_txt(segments, max_gap=0.3, max_duration=15):
    if not segments:
        return []

    merged = []
    current = segments[0].copy()

    for segment in segments[1:]:
        same_speaker = segment.get("speaker") == current.get("speaker")
        gap = segment["start"] - current["end"]
        duration = segment["end"] - current["start"]

        if same_speaker and gap <= max_gap and duration <= max_duration:
            current["end"] = segment["end"]
            current["text"] = current["text"].strip() + " " + segment["text"].strip()
        else:
            merged.append(current)
            current = segment.copy()

    merged.append(current)
    return merged


def write_txt_with_timestamps(segments, output_path: Path) -> None:
    merged_segments = merge_segments_for_txt(segments)

    with output_path.open("w", encoding="utf-8") as f:
        for segment in merged_segments:
            start = format_time(segment["start"])
            end = format_time(segment["end"])
            speaker = segment.get("speaker", "Speaker_0")
            text = segment["text"].strip()

            f.write(f"{start} --> {end} [{speaker}]\n")
            f.write(f"{text}\n\n")


# ✅ DIARISATION
def get_diarization(audio_path: Path):
    hf_token = os.getenv("HF_TOKEN")

    if not hf_token:
        raise RuntimeError("HF_TOKEN manquant pour la diarisation")

    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        revision="main",
        token=hf_token,
    )

    return pipeline(str(audio_path))


def find_speaker(diarization, start: float, end: float) -> str:
    mid = (start + end) / 2

    speaker_tracks = getattr(diarization, "speaker_diarization", diarization)

    for turn, _, speaker in speaker_tracks.itertracks(yield_label=True):
        if turn.start <= mid <= turn.end:
            return speaker

    return "Speaker_0"


# 🔥 FONCTION PRINCIPALE
def transcribe_file(
    input_path: Path,
    result_dir: Path,
    language: str | None = "fr",
    make_translation: bool = False,
    make_dubbing: bool = False,
    target_languages: list[str] | None = None,
    status_callback=None,
) -> dict:

    result_dir.mkdir(parents=True, exist_ok=True)
    target_languages = target_languages or []

    audio_path = result_dir / "audio.wav"
    if status_callback:
     status_callback("Extraction audio")
     extract_audio(input_path, audio_path)

    model = get_model()

    segments_iterator, info = model.transcribe(
        str(audio_path),
        language=None if language == "auto" else language,
        vad_filter=False,
        beam_size=5,
    )
    if status_callback:
     status_callback("Transcription")
    whisper_segments = list(segments_iterator)

    print("NOMBRE DE SEGMENTS WHISPER =", len(whisper_segments))

    # 🔥 DIARISATION (OBLIGATOIRE)
    diarization = get_diarization(audio_path)

    segments = []

    for segment in whisper_segments:
        start = float(segment.start)
        end = float(segment.end)
        if status_callback:
         status_callback("Détection des interlocuteurs")
        speaker = find_speaker(diarization, start, end)

        segments.append(
            {
                "start": start,
                "end": end,
                "speaker": speaker,
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
    if status_callback:
     status_callback("Traduction")
    if make_translation:
        from app.translator import translate_segments

        for lang in target_languages:
            translated_segments = translate_segments(segments, lang)
            translated_srt = segments_to_srt(translated_segments)

            translated_path = result_dir / f"subtitles_{lang}.srt"
            translated_path.write_text(translated_srt, encoding="utf-8")

            translated_files[lang] = str(translated_path)

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
    }
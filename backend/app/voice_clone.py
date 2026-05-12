from TTS.api import TTS
from pydub import AudioSegment
import tempfile
from pathlib import Path

# Chargement modèle une seule fois
_tts = None

def get_tts():
    global _tts
    if _tts is None:
        _tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
    return _tts


def clone_segment(text: str, speaker_wav: Path, output_path: Path, lang: str):
    get_tts().tts_to_file(
        text=text,
        speaker_wav=str(speaker_wav),
        language=lang,
        file_path=str(output_path),
    )


def generate_cloned_dub(segments, audio_path: Path, output_path: Path, lang: str):
    original_audio = AudioSegment.from_wav(audio_path)
    full_audio = AudioSegment.silent(duration=0)

    for segment in segments:
        start = int(segment["start"] * 1000)
        end = int(segment["end"] * 1000)

        text = segment["text"].strip()
        if not text:
            continue

        # extrait audio original du segment
        segment_audio = original_audio[start:end]

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as ref:
            ref_path = Path(ref.name)
            segment_audio.export(ref_path, format="wav")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out:
            out_path = Path(out.name)

        try:
            clone_segment(text, ref_path, out_path, lang)
            generated = AudioSegment.from_wav(out_path)

            full_audio += generated

        finally:
            if ref_path.exists():
                ref_path.unlink()
            if out_path.exists():
                out_path.unlink()

    full_audio.export(output_path, format="wav")
import subprocess
import tempfile
from pathlib import Path
from pydub import AudioSegment


VOICE_BY_LANG = {
    "fr": "Thomas",
    "en": "Samantha",
    "es": "Monica",
    "ar": "Maged",
}


def text_to_speech(text: str, output_path: Path, lang: str = "fr"):
    voice = VOICE_BY_LANG.get(lang, "Thomas")

    aiff_path = output_path.with_suffix(".aiff")

    subprocess.run(
        ["say", "-v", voice, "-o", str(aiff_path), text],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(aiff_path), str(output_path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if aiff_path.exists():
        aiff_path.unlink()


def generate_dub_audio(segments, output_path: Path, lang: str = "fr"):
    full_audio = AudioSegment.silent(duration=0)

    for segment in segments:
        text = segment["text"].strip()
        if not text:
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = Path(tmp.name)

        try:
            text_to_speech(text, tmp_path, lang=lang)
            audio = AudioSegment.from_wav(tmp_path)
            full_audio += audio
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    full_audio.export(output_path, format="wav")
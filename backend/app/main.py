import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.transcriber import transcribe_file
from app.srt import segments_to_srt

DEFAULT_STORAGE = Path(__file__).resolve().parents[2] / "storage"
BASE_DIR = Path(os.getenv("STORAGE_DIR", str(DEFAULT_STORAGE))).resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
RESULT_DIR = BASE_DIR / "results"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Internal Transcription & Subtitles API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, dict] = {}


def format_time(seconds: float) -> str:
    milliseconds = int(seconds * 1000)
    hours = milliseconds // 3600000
    milliseconds %= 3600000
    minutes = milliseconds // 60000
    milliseconds %= 60000
    secs = milliseconds // 1000
    ms = milliseconds % 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def write_txt_with_timestamps(segments: list, txt_path: Path) -> None:
    with txt_path.open("w", encoding="utf-8") as f:
        for segment in segments:
            start = format_time(float(segment["start"]))
            end = format_time(float(segment["end"]))
            speaker = segment.get("speaker", "Speaker 0")
            text = segment["text"].strip()

            f.write(f"{start} --> {end} [{speaker}]\n")
            f.write(f"{text}\n\n")


@app.get("/health")
def health():
    return {"status": "ok", "storage": str(BASE_DIR)}


@app.post("/transcribe")
def transcribe(
    file: UploadFile = File(...),
    language: str = "fr",
    make_translation: bool = Form(False),
    make_dubbing: bool = Form(False),
    target_languages: str = Form("[]"),
):
    job_id = str(uuid.uuid4())
    extension = Path(file.filename or "media").suffix or ".mp4"
    input_path = UPLOAD_DIR / f"{job_id}{extension}"
    job_result_dir = RESULT_DIR / job_id

    try:
        languages = json.loads(target_languages)
        if not isinstance(languages, list):
            languages = []
    except Exception:
        languages = []

    with input_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    JOBS[job_id] = {
        "status": "processing",
        "filename": file.filename,
    }

    try:
        result = transcribe_file(
            input_path=input_path,
            result_dir=job_result_dir,
            language=language,
            make_translation=make_translation,
            make_dubbing=make_dubbing,
            target_languages=languages,
        )

        JOBS[job_id] = {
            "status": "done",
            "filename": file.filename,
            "result": result,
        }

        return {"job_id": job_id, **JOBS[job_id]}

    except Exception as exc:
        JOBS[job_id] = {
            "status": "error",
            "filename": file.filename,
            "error": str(exc),
        }
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    return JOBS[job_id]


@app.post("/jobs/{job_id}/update")
def update_segments(job_id: str, segments: list = Body(...)):
    job_dir = RESULT_DIR / job_id
    json_path = job_dir / "segments.json"
    txt_path = job_dir / "transcription.txt"
    srt_path = job_dir / "subtitles.srt"

    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    json_path.write_text(
        json.dumps(segments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_txt_with_timestamps(segments, txt_path)

    srt = segments_to_srt(segments)
    srt_path.write_text(srt, encoding="utf-8")

    if job_id in JOBS:
        JOBS[job_id]["result"]["segments"] = segments

    return {"status": "saved"}


@app.get("/media/{job_id}")
def media(job_id: str):
    matches = list(UPLOAD_DIR.glob(f"{job_id}.*"))

    if not matches:
        raise HTTPException(status_code=404, detail="Media not found")

    return FileResponse(matches[0])


@app.get("/download/{job_id}/txt")
def download_txt(job_id: str):
    path = RESULT_DIR / job_id / "transcription.txt"

    if not path.exists():
        raise HTTPException(status_code=404, detail="TXT not found")

    return FileResponse(
        path,
        media_type="text/plain",
        filename="transcription.txt",
    )


@app.get("/download/{job_id}/srt")
def download_srt(job_id: str):
    path = RESULT_DIR / job_id / "subtitles.srt"

    if not path.exists():
        raise HTTPException(status_code=404, detail="SRT not found")

    return FileResponse(
        path,
        media_type="application/x-subrip",
        filename="subtitles.srt",
    )


@app.get("/download/{job_id}/json")
def download_json(job_id: str):
    path = RESULT_DIR / job_id / "segments.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail="JSON not found")

    return FileResponse(
        path,
        media_type="application/json",
        filename="segments.json",
    )


@app.get("/download/{job_id}/srt/{lang}")
def download_translated_srt(job_id: str, lang: str):
    path = RESULT_DIR / job_id / f"subtitles_{lang}.srt"

    if not path.exists():
        raise HTTPException(status_code=404, detail="SRT translated not found")

    return FileResponse(
        path,
        media_type="application/x-subrip",
        filename=f"subtitles_{lang}.srt",
    )

@app.get("/download/{job_id}/video-subtitled")
def download_video_subtitled(job_id: str):
    output_path = RESULT_DIR / job_id / "video_subtitled.mp4"

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Video subtitled not found")

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="video_subtitled.mp4",
    )
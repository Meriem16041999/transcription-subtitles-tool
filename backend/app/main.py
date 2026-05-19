import json
import os
import shutil
import uuid
from pathlib import Path
import shutil
from fastapi import BackgroundTasks, Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import select

from app.database import Job, get_session, init_db
from app.srt import segments_to_srt
from app.transcriber import transcribe_file

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


@app.on_event("startup")
def on_startup():
    init_db()


def update_job_status(job_id: str, status: str):
    if job_id in JOBS:
        JOBS[job_id]["status"] = status

    with get_session() as session:
        job_db = session.get(Job, job_id)
        if job_db:
            job_db.status = status
            session.add(job_db)
            session.commit()


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
            speaker = segment.get("speaker", "Speaker_0")
            text = segment["text"].strip()

            f.write(f"{start} --> {end} [{speaker}]\n")
            f.write(f"{text}\n\n")


def run_transcription_job(
    job_id: str,
    input_path: Path,
    job_result_dir: Path,
    language: str,
    make_translation: bool,
    make_dubbing: bool,
    languages: list[str],
    filename: str,
):
    try:
        result = transcribe_file(
            input_path=input_path,
            result_dir=job_result_dir,
            language=language,
            make_translation=make_translation,
            make_dubbing=make_dubbing,
            target_languages=languages,
            status_callback=lambda status: update_job_status(job_id, status),
        )

        JOBS[job_id] = {
            "status": "Terminé",
            "filename": filename,
            "result": result,
        }

        with get_session() as session:
            job_db = session.get(Job, job_id)
            if job_db:
                job_db.status = "Terminé"
                job_db.language = result.get("language")
                job_db.duration = result.get("duration")
                session.add(job_db)
                session.commit()

    except Exception as exc:
     print("ERREUR JOB:", str(exc))

    JOBS[job_id] = {
        "status": "Erreur",
        "filename": filename,
        "error": str(exc),
    }

    with get_session() as session:
        job_db = session.get(Job, job_id)

        if job_db:
            job_db.status = "Erreur"
            session.add(job_db)
            session.commit()


@app.get("/health")
def health():
    return {"status": "ok", "storage": str(BASE_DIR)}


@app.post("/transcribe")
def transcribe(
    background_tasks: BackgroundTasks,
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
    filename = file.filename or "media"

    try:
        languages = json.loads(target_languages)
        if not isinstance(languages, list):
            languages = []
    except Exception:
        languages = []

    with input_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    JOBS[job_id] = {
           "job_id": job_id,
    "status": "En attente",
    "filename": filename,
    }

    with get_session() as session:
        session.add(Job(id=job_id, filename=filename, status="En attente"))
        session.commit()

    background_tasks.add_task(
        run_transcription_job,
        job_id,
        input_path,
        job_result_dir,
        language,
        make_translation,
        make_dubbing,
        languages,
        filename,
    )

    return {
        "job_id": job_id,
        "status": "En attente",
        "filename": filename,
    }


@app.get("/jobs")
def list_jobs():
    with get_session() as session:
        jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()

        return [
            {
                "job_id": job.id,
                "filename": job.filename,
                "status": job.status,
                "duration": job.duration,
                "language": job.language,
                "created_at": job.created_at.isoformat(),
            }
            for job in jobs
        ]


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    if job_id in JOBS:
        return JOBS[job_id]

    with get_session() as session:
        job_db = session.get(Job, job_id)
        if not job_db:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "job_id": job_db.id,
            "filename": job_db.filename,
            "status": job_db.status,
            "duration": job_db.duration,
            "language": job_db.language,
        }


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

    if job_id in JOBS and "result" in JOBS[job_id]:
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

@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    job_dir = RESULT_DIR / job_id

    matches = list(UPLOAD_DIR.glob(f"{job_id}.*"))
    for file_path in matches:
        file_path.unlink(missing_ok=True)

    if job_dir.exists():
        shutil.rmtree(job_dir)

    if job_id in JOBS:
        del JOBS[job_id]

    with get_session() as session:
        job_db = session.get(Job, job_id)
        if job_db:
            session.delete(job_db)
            session.commit()

    return {"status": "deleted"}
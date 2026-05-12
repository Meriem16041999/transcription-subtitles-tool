# 🎬 Transcription & Sous-titres Tool

Outil interne pour :
- 🎤 Transcription audio / vidéo
- 📝 Génération de sous-titres (SRT)
- 🌍 Traduction multilingue
- ✏️ Édition interactive des sous-titres
- 🎯 Synchronisation texte ↔ vidéo

---

## 🚀 Fonctionnalités

- Upload vidéo ou audio
- Transcription avec Whisper
- Export :
  - TXT
  - SRT
  - JSON
- Sous-titres multilingues (EN, ES, AR…)
- Édition des segments directement dans l’interface
- Navigation vidéo via la transcription

---

## 🧰 Stack technique

**Backend**
- FastAPI
- faster-whisper
- FFmpeg

**Frontend**
- React + Vite

---

## ⚙️ Installation

### 1. Cloner le projet

```bash
git clone https://github.com/Meriem16041999/transcription-subtitles-tool.git
cd transcription-subtitles-tool
```

### 2. Backend

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Installer FFmpeg :

```bash
brew install ffmpeg
```

### 3. Frontend

```bash
cd frontend
npm install
cd ..
```

---

## ▶️ Lancer l’application

### Backend

```bash
./run_backend.sh
```

ou :

```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend

```bash
./run_frontend.sh
```

ou :

```bash
cd frontend
npm run dev
```

---

## 🌐 Accès

- Frontend : http://localhost:5173  
- API : http://localhost:8000/docs  

---

## 📦 Structure du projet

```text
backend/
  app/
    main.py
    transcriber.py
    translator.py
frontend/
storage/
  uploads/
  results/
```

---

## 🧠 Améliorations futures

- Authentification interne
- Jobs asynchrones
- Interface édition avancée
- Amélioration qualité traduction
- Support multi-speakers
- Export pour Premiere / Avid

---

## 👤 Auteur

Meriem Boussaadia

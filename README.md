# Outil interne de transcription et sous-titres - sans Docker

Projet MVP pret a ouvrir dans Visual Studio Code.

## Fonctionnalites

- Upload video ou audio
- Extraction audio avec FFmpeg
- Transcription avec faster-whisper
- Generation TXT, SRT et JSON
- API FastAPI
- Interface web React/Vite
- Lancement local sans Docker

## Prerequis

Installe sur ton ordinateur :

1. Python 3.10 ou 3.11
2. Node.js LTS
3. FFmpeg
4. Visual Studio Code

### Installer FFmpeg sur Mac

Avec Homebrew :

```bash
brew install ffmpeg
```

Verifier :

```bash
ffmpeg -version
```

## Installation locale

Depuis le dossier du projet :

```bash
./setup_local.sh
```

## Lancer le backend

Dans un premier terminal :

```bash
./run_backend.sh
```

API : http://localhost:8000/docs

## Lancer le frontend

Dans un deuxieme terminal :

```bash
./run_frontend.sh
```

Frontend : http://localhost:5173

## Utilisation dans VS Code

1. Ouvre le dossier `transcription-subtitles-tool` dans VS Code.
2. Ouvre le terminal integre.
3. Lance `./setup_local.sh` une seule fois.
4. Lance `./run_backend.sh`.
5. Ouvre un deuxieme terminal et lance `./run_frontend.sh`.

Tu peux aussi utiliser `Terminal > Run Task` :

- Setup local sans Docker
- Lancer backend FastAPI
- Lancer frontend React

## Configuration du modele

Par defaut, le projet utilise :

```bash
WHISPER_MODEL=small
DEVICE=cpu
COMPUTE_TYPE=int8
```

Pour une meilleure qualite :

```bash
WHISPER_MODEL=medium ./run_backend.sh
```

Pour un Mac Apple Silicon, tu peux rester en CPU. Le premier lancement telecharge le modele Whisper, donc il peut etre lent.

## Structure

```text
backend/       API FastAPI + transcription
frontend/      Interface React
storage/       fichiers uploads et resultats
.vscode/       configuration VS Code
setup_local.sh installation locale
run_backend.sh lancement API
run_frontend.sh lancement interface
```

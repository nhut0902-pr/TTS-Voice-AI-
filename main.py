from fastapi import FastAPI
from fastapi.responses import FileResponse
import edge_tts
import uuid
import os
import asyncio
from datetime import datetime, timedelta

app = FastAPI()

TMP_DIR = "tmp"
os.makedirs(TMP_DIR, exist_ok=True)

# =========================
# VOICE MAP (ngôn ngữ → voice)
# =========================
VOICE_MAP = {
    "vi": {
        "male": "vi-VN-NamMinhNeural",
        "female": "vi-VN-HoaiMyNeural"
    },
    "en": {
        "male": "en-US-GuyNeural",
        "female": "en-US-AriaNeural"
    },
    "ja": {
        "male": "ja-JP-KeitaNeural",
        "female": "ja-JP-NanamiNeural"
    },
    "ko": {
        "male": "ko-KR-InJoonNeural",
        "female": "ko-KR-SunHiNeural"
    }
}

# =========================
# CLEANUP OLD FILES
# =========================
def cleanup_files():
    now = datetime.now()
    for file in os.listdir(TMP_DIR):
        path = os.path.join(TMP_DIR, file)
        if os.path.isfile(path):
            created = datetime.fromtimestamp(os.path.getctime(path))
            if now - created > timedelta(hours=24):
                os.remove(path)

# chạy cleanup mỗi lần gọi API
@app.middleware("http")
async def auto_cleanup(request, call_next):
    cleanup_files()
    response = await call_next(request)
    return response

# =========================
# TTS API
# =========================
@app.get("/tts")
async def tts(
    text: str,
    lang: str = "vi",
    gender: str = "female"
):
    file_id = str(uuid.uuid4())
    file_path = f"{TMP_DIR}/{file_id}.mp3"

    voice = VOICE_MAP.get(lang, VOICE_MAP["vi"])[gender]

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

    return FileResponse(file_path, media_type="audio/mpeg")

import os
import asyncio
import hashlib
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
import edge_tts
from edge_tts.exceptions import NoAudioReceived
from gtts import gTTS

app = FastAPI(title="Stable TTS API")

# =====================
# CONFIG
# =====================
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

queue = asyncio.Queue()
worker_started = False

VOICE_MAP = {
    "en-female": "en-US-AriaNeural",
    "en-male": "en-US-GuyNeural",
    "vi-female": "vi-VN-HoaiMyNeural",
    "vi-male": "vi-VN-NamMinhNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}

# =====================
# UTIL
# =====================
def clean_text(text: str):
    if not text:
        return None
    text = text.strip()
    if len(text) < 1:
        return None
    return text[:250]

def cache_key(text, voice):
    return hashlib.md5(f"{text}::{voice}".encode()).hexdigest()

def file_ok(path):
    return os.path.exists(path) and os.path.getsize(path) > 1000

# =====================
# TTS ENGINES
# =====================
async def edge_tts_run(text, voice, path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)

def google_tts_run(text, path, lang="vi"):
    tts = gTTS(text=text, lang=lang)
    tts.save(path)

async def generate_tts(text, voice, path):
    last_err = None

    # try EDGE first
    for _ in range(2):
        try:
            await edge_tts_run(text, voice, path)
            if file_ok(path):
                return path
        except NoAudioReceived as e:
            last_err = e
            await asyncio.sleep(0.5)
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.5)

    # fallback GOOGLE
    try:
        lang = "vi" if "vi" in voice else "en"
        google_tts_run(text, path, lang)
        if file_ok(path):
            return path
    except Exception as e:
        last_err = e

    raise last_err or Exception("TTS FAILED")

# =====================
# WORKER (QUEUE)
# =====================
async def worker():
    while True:
        job = await queue.get()

        try:
            await generate_tts(
                job["text"],
                job["voice"],
                job["path"]
            )
        except:
            # fail silent → tránh 500 chết server
            open(job["path"], "wb").close()

        queue.task_done()

@app.on_event("startup")
async def startup():
    global worker_started
    if not worker_started:
        asyncio.create_task(worker())
        worker_started = True

# =====================
# API
# =====================
@app.get("/tts")
async def tts(text: str = Query(...), voice: str = Query("en-female")):

    text = clean_text(text)
    if not text:
        return JSONResponse({"error": "empty text"}, status_code=400)

    voice = VOICE_MAP.get(voice, "en-US-AriaNeural")

    key = cache_key(text, voice)
    path = os.path.join(CACHE_DIR, f"{key}.mp3")

    # CACHE HIT
    if file_ok(path):
        return FileResponse(path, media_type="audio/mpeg")

    # PUSH TO QUEUE
    await queue.put({
        "text": text,
        "voice": voice,
        "path": path
    })

    # WAIT FOR RESULT (short polling)
    for _ in range(25):
        if file_ok(path):
            return FileResponse(path, media_type="audio/mpeg")
        await asyncio.sleep(0.2)

    # NO 500 EVER
    return JSONResponse(
        {
            "status": "processing",
            "message": "try again"
        },
        status_code=202
    )

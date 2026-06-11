from fastapi import FastAPI
from fastapi.responses import FileResponse
import edge_tts
import uuid
import os

app = FastAPI()

TMP_DIR = "tmp"
os.makedirs(TMP_DIR, exist_ok=True)

@app.get("/")
def home():
    return {"status": "ok", "message": "Edge TTS API running"}

@app.get("/tts")
async def tts(text: str, voice: str = "vi-VN-NamMinhNeural"):
    file_id = str(uuid.uuid4())
    file_path = f"{TMP_DIR}/{file_id}.mp3"

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

    return FileResponse(file_path, media_type="audio/mpeg")

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
import edge_tts
import uuid
import os

app = FastAPI()

TMP_DIR = "tmp"
os.makedirs(TMP_DIR, exist_ok=True)

# =====================
# VOICE LIST
# =====================
VOICES = {
    "vi-male": "vi-VN-NamMinhNeural",
    "vi-female": "vi-VN-HoaiMyNeural",
    "en-male": "en-US-GuyNeural",
    "en-female": "en-US-AriaNeural"
}

# =====================
# MODEL
# =====================
class TTSRequest(BaseModel):
    text: str
    voice: str = "vi-female"

# =====================
# CORE GENERATE
# =====================
async def generate(text, voice_key):
    voice = VOICES.get(voice_key, VOICES["vi-female"])

    file_path = f"{TMP_DIR}/{uuid.uuid4()}.mp3"

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file_path)

    return file_path

# =====================
# GET API
# =====================
@app.get("/tts")
async def tts_get(text: str, voice: str = "vi-female"):
    file_path = await generate(text, voice)
    return FileResponse(file_path, media_type="audio/mpeg")

# =====================
# POST API
# =====================
@app.post("/tts")
async def tts_post(req: TTSRequest):
    file_path = await generate(req.text, req.voice)
    return FileResponse(file_path, media_type="audio/mpeg")

# =====================
# WEB UI
# =====================
@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
    <head>
        <title>Edge TTS UI</title>
    </head>
    <body style="font-family: Arial; max-width: 600px; margin: auto; padding-top: 50px;">
        <h2>🎙 Edge TTS Web UI</h2>

        <textarea id="text" style="width:100%;height:100px;">xin chào</textarea>

        <br><br>

        <select id="voice">
            <option value="vi-female">🇻🇳 Nữ Việt</option>
            <option value="vi-male">🇻🇳 Nam Việt</option>
            <option value="en-female">🇺🇸 Nữ Anh</option>
            <option value="en-male">🇺🇸 Nam Anh</option>
        </select>

        <br><br>

        <button onclick="speak()">▶ Generate</button>

        <br><br>

        <audio id="audio" controls></audio>

        <script>
        async function speak() {
            const text = document.getElementById("text").value;
            const voice = document.getElementById("voice").value;

            const res = await fetch(`/tts?text=${encodeURIComponent(text)}&voice=${voice}`);
            const blob = await res.blob();

            const url = URL.createObjectURL(blob);
            document.getElementById("audio").src = url;
        }
        </script>
    </body>
    </html>
    """

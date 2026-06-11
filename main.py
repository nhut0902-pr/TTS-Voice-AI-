import os
import hashlib
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
import edge_tts

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="TTS API",
    version="1.0.0"
)

CACHE_DIR = Path("tts_cache")
CACHE_DIR.mkdir(exist_ok=True)

VOICE_MAP = {
    "vi-female": "vi-VN-HoaiMyNeural",
    "vi-male": "vi-VN-NamMinhNeural",
    "en-female": "en-US-AriaNeural",
    "en-male": "en-US-GuyNeural",
    "ja-female": "ja-JP-NanamiNeural",
    "ja-male": "ja-JP-KeitaNeural",
    "ko-female": "ko-KR-SunHiNeural",
    "ko-male": "ko-KR-InJoonNeural",
}

FALLBACK_VOICES = [
    "vi-VN-HoaiMyNeural",
    "en-US-AriaNeural",
    "vi-VN-NamMinhNeural",
    "en-US-GuyNeural"
]


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "TTS API",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {
        "ok": True
    }


@app.get("/voices")
async def voices():
    try:
        data = await edge_tts.list_voices()

        return {
            "count": len(data),
            "voices": data
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


async def generate_audio(text: str, voice: str):

    resolved_voice = VOICE_MAP.get(
        voice.lower(),
        voice
    )

    cache_key = hashlib.md5(
        f"{text}|{resolved_voice}".encode("utf-8")
    ).hexdigest()

    file_path = CACHE_DIR / f"{cache_key}.mp3"

    if file_path.exists() and file_path.stat().st_size > 0:
        return file_path

    candidate_voices = [resolved_voice]

    for v in FALLBACK_VOICES:
        if v not in candidate_voices:
            candidate_voices.append(v)

    last_error = None

    for current_voice in candidate_voices:

        for retry in range(3):

            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=current_voice
                )

                await communicate.save(str(file_path))

                if (
                    file_path.exists()
                    and file_path.stat().st_size > 0
                ):
                    return file_path

            except Exception as e:
                last_error = e
                logging.warning(
                    f"Voice={current_voice} Retry={retry+1} Error={e}"
                )
                await asyncio.sleep(1)

    raise Exception(
        f"Generate failed: {last_error}"
    )


@app.get("/tts")
async def tts(
    text: str = Query(...),
    voice: str = Query("vi-female")
):

    text = text.strip()

    if not text:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Text empty"
            }
        )

    if len(text) > 300:
        text = text[:300]

    try:

        audio_file = await generate_audio(
            text=text,
            voice=voice
        )

        return FileResponse(
            path=str(audio_file),
            media_type="audio/mpeg",
            filename=audio_file.name
        )

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e)
            }
        )

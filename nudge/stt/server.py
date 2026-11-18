"""Small self-hosted speech-to-text server for Nudge (faster-whisper, English model).

Speaks the OpenAI-style API:  POST /v1/audio/transcriptions  (multipart: file, model, language, prompt)
Recordings are processed in memory and never written to disk.

WHISPER_MODEL   small.en (default, good with Indian English accents) | base.en (faster, lighter) | medium.en
WHISPER_THREADS CPU threads to use (default: all)
"""
import io
import logging
import os
import threading

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

log = logging.getLogger("whisper")
logging.basicConfig(level=logging.INFO)

MODEL_NAME = os.environ.get("WHISPER_MODEL", "small.en")
THREADS = int(os.environ.get("WHISPER_THREADS", "0"))
MAX_BYTES = 25 * 1024 * 1024

app = FastAPI(title="Nudge speech-to-text")
_model = None
_error = ""
_lock = threading.Lock()


def _load() -> None:
    """Download (first start only) and load the model in the background so the API comes up at once."""
    global _model, _error
    try:
        from faster_whisper import WhisperModel

        log.info("Loading Whisper model %s ...", MODEL_NAME)
        _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8", cpu_threads=THREADS,
                              download_root="/models")
        log.info("Whisper model ready")
    except Exception as e:  # keep serving /health so the app can show the reason
        _error = str(e)
        log.exception("Could not load the Whisper model")


threading.Thread(target=_load, daemon=True).start()


@app.get("/health")
def health():
    return {"ready": _model is not None, "model": MODEL_NAME, "error": _error}


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(""),
    language: str = Form("en"),
    prompt: str = Form(""),
    response_format: str = Form("json"),
):
    if _model is None:
        raise HTTPException(503, "The speech model is still loading" if not _error else f"Model failed: {_error}")
    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty recording")
    if len(audio) > MAX_BYTES:
        raise HTTPException(413, "Recording too large")
    with _lock:  # one at a time keeps memory predictable on a small server
        segments, info = _model.transcribe(
            io.BytesIO(audio),
            language=language or "en",
            initial_prompt=prompt or None,
            vad_filter=True,
            beam_size=5,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
    return {"text": text, "language": info.language, "duration": round(info.duration, 2)}

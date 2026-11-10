"""SOPilot API + UI. Bind to 0.0.0.0 so phones on the same Wi-Fi can open it."""



from __future__ import annotations

import socket
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from QueryProcessor import process_user_query
from documents import SUGGESTIONS

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="SOPilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class Message(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[Message] = Field(default_factory=list)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/suggestions")
def suggestions():
    return {"suggestions": SUGGESTIONS}


@app.post("/api/ask")
def ask(body: AskRequest):
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty")
    history_dicts = [{"role": m.role, "content": m.content} for m in body.history]
    try:
        return process_user_query(question, history=history_dicts)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach Ollama. Is it running? ({exc})",
        ) from exc


def lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "YOUR-LAPTOP-IP"


if __name__ == "__main__":
    import uvicorn

    host = "0.0.0.0"
    port = 8000
    ip = lan_ip()
    print(f"\n  On this laptop:  http://127.0.0.1:{port}")
    print(f"  On your phone:   http://{ip}:{port}")
    print("  Same Wi-Fi. Allow incoming connections if macOS asks.\n")
    uvicorn.run("app:app", host=host, port=port, reload=False)

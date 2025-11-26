import os
import sys
import shutil
import subprocess, tempfile
from threading import Lock
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse


PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "body_pose_picture"))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
RUN_SCRIPT = os.path.join(PROJECT_DIR, "src", "run_image.py")


###
PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable) # it's better to put PYTHON_BIN in isula container command (-e PYTHON_BIN=/opt/venv/bin/python3)
###

print("=== server.py LOADED, PYTHON_BIN =", PYTHON_BIN)


app = FastAPI(title="pose-model-server", version="0.5") # for debug
_INFER_LOCK = Lock()


def _filter_stdout(raw: str) -> str:
    if not raw:
        return ""
    posture = ""
    for line in raw.splitlines():
        s = line.strip()
        if s == "Incorrect posture":
            posture = "Incorrect posture"
        elif s == "Correct posture":
            posture = "Correct posture"

    return posture


def _clean_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    for name in os.listdir(path):
        p = os.path.join(path, name)
        try:
            if (os.path.isfile(p) or os.path.islink(p)):
                os.unlink(p)
            elif (os.path.isdir(p)):
                shutil.rmtree(p)
        except Exception:
            pass


def _inference(jpeg_bytes: bytes) -> str:
    _clean_directory(DATA_DIR)
    _clean_directory(OUTPUT_DIR)

    in_path = os.path.join(DATA_DIR, "test.jpg")
    with open(in_path, "wb") as f:
        f.write(jpeg_bytes)
        f.flush()
        os.fsync(f.fileno())

    abs_image = os.path.abspath(in_path)

    try:
        with _INFER_LOCK:
            proc = subprocess.run(
                [PYTHON_BIN, RUN_SCRIPT,
                "--frames_input_src", abs_image,
                "--output_dir", OUTPUT_DIR],
                cwd=PROJECT_DIR, check=True, text=True,
                capture_output=True, timeout=90
            )
    
    except subprocess.CalledProcessError as e:
        err = (e.stderr or str(e)).strip()
        print("run_image FAILED, stderr:\n", err)
        return "run_image error:\n" + err
    
    out = _filter_stdout(proc.stdout or "")

    if not out:
        tail_err = "\n".join((proc.stderr or "").splitlines()[-12:])
        out = (tail_err or "ok").strip()
    return out


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/infer")
async def infer(image: UploadFile = File(...)):
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty_body")
    # try:
    txt = _inference(data)
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

    return PlainTextResponse(txt + "\n", media_type="text/plain; charset=utf-8")

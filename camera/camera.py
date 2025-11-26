import os, time, requests, cv2
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["TG_BOT_TOKEN"]
MODEL_URL = "http://127.0.0.1:8000/infer"
CHAT_ID = os.environ["CHAT_ID"]
PERIOD = float(os.environ.get("PERIOD_SEC", "10"))
HTTP_TO = int(os.environ.get("HTTP_TIMEOUT", "20"))
PROXY_SETTING = {"http": None, "https": None}
 

TG_SEND = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


def send_text(txt: str):
    try:
        requests.post(TG_SEND, data={"chat_id": CHAT_ID, "text": txt[:4096]}, timeout=HTTP_TO)
    except Exception:
        pass

def take_jpeg() -> bytes:
    cap = cv2.VideoCapture(0) # camera initialize
    if not cap.isOpened():
        raise RuntimeError(f"camera 0 open failed")
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(r'C:\Users\Vika.VITUHA\Desktop\edge\EDGE_AI_2025_REPO-vituha\body_pose_picture\data\test.jpg', frame)
        print("Saved")
    else:
        print("Couldn't save")
    cap.release()
    ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


def inference(jpg: bytes) -> str:
    r = requests.post(MODEL_URL, files={"image": ("test.jpg", jpg, "image/jpeg")}, timeout=HTTP_TO, proxies=PROXY_SETTING)
    r.raise_for_status()
    return r.text.strip()


def main():
    last = None
    send_text("Camera is in work!")
    while True:
        try:
            jpg = take_jpeg()
            txt = inference(jpg)
            send_text(txt)
        except Exception as e:
            send_text(f"Error: {e}")
        time.sleep(PERIOD)


if __name__ == "__main__":
    main()


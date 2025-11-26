import requests

proxies = {"http": None, "https": None}

jpg = open(r"body_pose_picture\data\test.jpg", "rb").read()
r = requests.post(
    "http://127.0.0.1:8000/infer",
    files={"image": ("test.jpg", jpg, "image/jpeg")},
    proxies=proxies,   
)
print("status:", r.status_code)
print("text:\n", r.text)

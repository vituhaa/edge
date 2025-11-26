import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
model_dir = ROOT / "body_pose_picture" / "model"
model_dir.mkdir(exist_ok=True)

url = "https://obs-9be7.obs.cn-east-2.myhuaweicloud.com/003_Atc_Models/AE/ATC%20Model/body_pose_picture/OpenPose_light.pb"
out_path = model_dir / "OpenPose_light.pb"

print("Downloading from:", url)
urllib.request.urlretrieve(url, out_path)
print("Saved to:", out_path)

import sys
import subprocess
from pathlib import Path

# путь к корню проекта
ROOT = Path(__file__).resolve().parent

pb_path = ROOT / "body_pose_picture" / "model" / "OpenPose_light.pb"
onnx_path = ROOT / "body_pose_picture" / "model" / "pose_heatmap.onnx"

cmd = [
    sys.executable, "-m", "tf2onnx.convert",
    "--graphdef", str(pb_path),
    '--inputs', "input001:0[1,368,368,3]",
    '--outputs', "light_openpose/stage_1/cpm/BiasAdd:0",
    "--opset", "13",
    "--output", str(onnx_path),
]

print("Running:", " ".join(cmd))
subprocess.run(cmd, check=True)
print("Done, saved to:", onnx_path)

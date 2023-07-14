import json
from ParticleDetection.reconstruct_3D.calibrate_cameras import stereo_calibrate

cam1 = "./datasets/calibration_imgs/camera1"
cam2 = "./datasets/calibration_imgs/camera2"
results = stereo_calibrate(cam1, cam2)
to_json = {
    "CM1": results[1].tolist(),
    "dist1": results[2].tolist(),
    "CM2": results[3].tolist(),
    "dist2": results[4].tolist(),
    "R": results[5].tolist(),
    "T": results[6].tolist(),
    "E": results[7].tolist(),
    "F": results[8].tolist(),
}

with open("calibration_cam12.json", "w") as f:
    json.dump(to_json, f, indent=2)

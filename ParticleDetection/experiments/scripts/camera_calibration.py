import json
from ParticleDetection.reconstruct_3D.calibrate_cameras import stereo_calibrate


def cam1_2():
    """Stereocalibrate two cameras and save the results to a *.json file."""
    gp1 = "../datasets/calibration_imgs/gp1"
    gp2 = "../datasets/calibration_imgs/gp2"
    results = stereo_calibrate(gp1, gp2)
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

    with open("OpenCV_calibration_gp12.json", "w") as f:
        json.dump(to_json, f, indent=2)
    print(results)


def cam3_4():
    """Stereocalibrate two cameras and save the results to a *.json file."""
    gp3 = "../../datasets/calibration_imgs/gp3_alt"
    gp4 = "../../datasets/calibration_imgs/gp4_alt"
    results = stereo_calibrate(gp3, gp4)
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

    with open("OpenCV_calibration_gp34_alt.json", "w") as f:
        json.dump(to_json, f, indent=2)
    print(results)


if __name__ == "__main__":
    cam3_4()

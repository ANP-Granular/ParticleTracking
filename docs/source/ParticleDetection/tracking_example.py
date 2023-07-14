from pathlib import Path
import numpy as np
from ParticleDetection.reconstruct_3D import matchND

output_main_folder = Path("./out").resolve()

calibration_file = "./calibration_data/calibration_cam12.json"
transformation_file = "./calibration_data/transformation_cam12.json"
colors = ["blue", "brown", "green", "red", "yellow"]
frame_numbers = np.arange(1, 321)
base_folder = str(Path(".").resolve())
out_folder = str(Path("./out").resolve())
errs, lens = matchND.assign(base_folder, out_folder, colors, "cam1", "cam2",
                            frame_numbers, calibration_file,
                            transformation_file)

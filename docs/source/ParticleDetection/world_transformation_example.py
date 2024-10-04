import numpy as np
from pathlib import Path
from ParticleDetection.utils.helper_funcs import find_world_transform

# Input - path to stereo camera calibration file
calibration_file = Path(
    "ParticleDetection/src/ParticleDetection/reconstruct_3D/example_calibration/Matlab/gp12.json"
).resolve()

# Output - path to resulting transformation file
transformation_file = Path(
    "ParticleDetection/src/ParticleDetection/reconstruct_3D/example_calibration/Matlab/world_transformation_gp12.json"
).resolve()

# 2D pixel coordinates of box edges on first camera
# [front: left up, left down, right up, right down,
# back: left up, left down, right up, right down]
edges_cam1_dist = np.array(
    [
        [27, 36],
        [30, 904],
        [1235, 27],
        [1240, 903],
        [183, 149],
        [188, 900],
        [1096, 140],
        [1098, 790],
    ]
).astype(float)

# 2D pixel coordinates of box edges on second camera
# [front: left up, left down, right up, right down,
# back: left up, left down, right up, right down]
edges_cam2_dist = np.array(
    [
        [26, 923],
        [149, 834],
        [1243, 916],
        [1118, 833],
        [30, 63],
        [149, 146],
        [1245, 57],
        [1120, 144],
    ]
).astype(float)

# Corresponding 3D world coordinates of the box edges
# ([0,0,0] is the center of the box)
edges_3D = np.array(
    [
        [-58, 40, 40],
        [-58, -40, 40],
        [58, 40, 40],
        [58, -40, 40],
        [-58, 40, -40],
        [-58, -40, -40],
        [58, 40, -40],
        [58, -40, -40],
    ]
).astype(float)

if __name__ == "__main__":
    rot_comb, trans_vec = find_world_transform(
        str(calibration_file),
        edges_cam1_dist,
        edges_cam2_dist,
        edges_3D,
        str(transformation_file),
    )

import numpy as np
import reconstruct_3D.matching as mt
from reconstruct_3D import result_visualizations


def rematch_dbg():
    input_folder = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-3-len2"
    output = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-3-len2_rematched"
    frames = np.arange(100, 905, 1)
    calibration_file = "../../reconstruct_3D/calibration_data/Matlab/gp12.json"
    transformation_file = "../../reconstruct_3D/calibration_data/Matlab/" \
                          "world_transformation.json"
    errs, lens = mt.match_csv_complex(input_folder, output, ["blue"], "gp1",
                                      "gp2", frames, calibration_file,
                                      transformation_file, rematching=False)
    err_vis = np.array([])
    len_vis = np.array([])
    for err, l in zip(errs, lens):
        err_vis = np.concatenate([err_vis, err.flatten()])
        len_vis = np.concatenate([len_vis, l.flatten()])
    result_visualizations.matching_results(err_vis, len_vis)


if __name__ == "__main__":
    rematch_dbg()

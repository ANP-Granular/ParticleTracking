from time import perf_counter
import numpy as np
import pandas as pd
from reconstruct_3D import matching, result_visualizations, tracking


def test_assignment():
    raw_data = "../../datasets/100-904_3Dt_13_blue/rand_endp"
    calibration_file = "../../reconstruct_3D/calibration_data/Matlab/gp12.json"
    transformation_file = "../../reconstruct_3D/calibration_data/Matlab/" \
                          "world_transformation.json"
    colors = ["blue", ]
    out_folder = "./assign2d"
    start_frame = 100
    end_frame = 904
    frame_numbers = np.arange(start_frame, end_frame+1)

    start = perf_counter()
    errs, lens = matching.match_csv_complex(
        raw_data, out_folder, colors, "gp1", "gp2", frame_numbers,
        calibration_file, transformation_file, rematching=True)
    print(f"Matching duration: {perf_counter()-start} s")

    err_vis = np.array([])
    len_vis = np.array([])
    for err, l in zip(errs, lens):
        err_vis = np.concatenate([err_vis, err.flatten()])
        len_vis = np.concatenate([len_vis, l.flatten()])
    result_visualizations.matching_results(err_vis, len_vis)

    data = pd.read_csv(out_folder + "/rods_df_blue.csv", index_col=0)
    tracked, _ = tracking.tracking_global_assignment(data)
    tracked.to_csv(out_folder + "/tracked_rods_df_blue.csv")

    no_particles = len(tracked.particle.unique())
    data_3d = np.zeros((len(frame_numbers), no_particles, 3, 2))
    for idx_f, f in enumerate(tracked.frame.unique()):
        frame_data = tracked.loc[tracked.frame == f]
        idx_p = frame_data["particle"].to_numpy()
        data_3d[idx_f, idx_p, :, 0] = frame_data[["x1", "y1", "z1"]].to_numpy()
        data_3d[idx_f, idx_p, :, 1] = frame_data[["x2", "y2", "z2"]].to_numpy()

    result_visualizations.displacement_fwise(data_3d)

    print("done")


if __name__ == "__main__":
    test_assignment()

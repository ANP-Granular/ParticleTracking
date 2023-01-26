from typing import List
from pathlib import Path
import numpy as np
import pandas as pd
import reconstruct_3D.result_visualizations as rv


def test_displacement():
    # raw_data = "../example/debug_world/rods_df_blue.csv"
    # raw_data = "../../datasets/assembled_200-906_2D/rods_df_blue.csv"
    raw_data = "../../datasets/100-904_3Dt_13_blue/rods_df_blue.csv"
    raw_data = "../example/debug_100-904_3Dt_13_blue/"\
        "rand_endp/rods_df_blue.csv"
    raw_data = "../scripts/assign2d/tracked_rods_df_blue.csv"
    df_data = pd.read_csv(raw_data, sep=",", index_col=0)
    no_frames = len(df_data.frame.unique())
    no_particles = len(df_data.particle.unique())
    data3d = np.zeros((no_frames, no_particles, 3, 2))
    for idx_f, f in enumerate(df_data.frame.unique()):
        frame_data = df_data.loc[df_data.frame == f]
        idx_p = frame_data["particle"].to_numpy()
        data3d[idx_f, idx_p, :, 0] = frame_data[["x1", "y1", "z1"]].to_numpy()
        data3d[idx_f, idx_p, :, 1] = frame_data[["x2", "y2", "z2"]].to_numpy()
    rv.displacement_fwise(data3d)


def compare_displacements(data_paths: List[Path], names: List[str]):
    data_out = []
    for file in data_paths:
        df_data = pd.read_csv(file, sep=",", index_col=0)
        no_frames = len(df_data.frame.unique())
        no_particles = len(df_data.particle.unique())
        data3d = np.zeros((no_frames, no_particles, 3, 2))
        for idx_f, f in enumerate(df_data.frame.unique()):
            frame_data = df_data.loc[df_data.frame == f]
            idx_p = frame_data["particle"].to_numpy()
            data3d[idx_f, idx_p, :, 0] = frame_data[
                ["x1", "y1", "z1"]].to_numpy()
            data3d[idx_f, idx_p, :, 1] = frame_data[
                ["x2", "y2", "z2"]].to_numpy()
        data_out.append(data3d)
    rv.compare_diplacements(data_out, names)


def compare_all():
    hand_adjusted_raw = "../../datasets/100-904_3Dt_13_blue/rods_df_blue.csv"
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "rand_endp/rods_df_blue.csv"
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "rand_both/rods_df_blue.csv"
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching/rods_df_blue.csv"
    assign_2d_raw = "../scripts/assign2d/tracked_rods_df_blue.csv"
    assign_3d_simple = "../example/debug_100-904_3Dt_13_blue/"\
        "rand_both/rods_df_blue.csv"
    compare_files = [hand_adjusted_raw, assign_3d_raw, assign_2d_raw,
                     assign_3d_simple]
    names = ["Manual", "3D-assigned-new", "2D-assigned", "3D-assigned-old"]
    compare_displacements(compare_files, names)


def compare_3d_simple():
    hand_adjusted_raw = "../../datasets/100-904_3Dt_13_blue/rods_df_blue.csv"
    assign_3d_simple = "../example/debug_100-904_3Dt_13_blue/"\
        "rand_both/rods_df_blue.csv"
    compare_files = [hand_adjusted_raw, assign_3d_simple]
    names = ["Manual", "3D-assigned-old"]
    compare_displacements(compare_files, names)


def compare_3d_advanced():
    hand_adjusted_raw = "../../datasets/100-904_3Dt_13_blue/rods_df_blue.csv"
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching/rods_df_blue.csv"
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_onlydisp/rods_df_blue.csv"
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_debug/rods_df_blue.csv"
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_rematched/rods_df_blue.csv"

    # FIXME: both are problematic, although the 3D plot is looking good
    #        seems to be a problem with numbers jumping between rods
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-2_rematched/rods_df_blue.csv"
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-2/rods_df_blue.csv"

    # FIXME: looks alright, but 3D plot is horrible
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-2_disp_rematched/rods_df_blue.csv"
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_debug_v4-2_disp/rods_df_blue.csv"

    # TODO: looks good, except for the beginning
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-3_rematched/rods_df_blue.csv"
    # TODO: looks extremly good, except for the beginning
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-3/rods_df_blue.csv"

    # TODO: looks good, except for the beginning
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-1_rematched/rods_df_blue.csv"
    # TODO: looks extremely good, except for the beginning
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-1/rods_df_blue.csv"

    # # BUG: very bad performance
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_debug_v5-2-len_rematched/rods_df_blue.csv"
    # assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_debug_v5-2-len/rods_df_blue.csv"

    # BUG: looks very similar to the previous best
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-3-len2/rods_df_blue.csv"
    assign_3d_raw = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-3-len2_rematched/rods_df_blue.csv"

    compare_files = [hand_adjusted_raw, assign_3d_raw]
    names = ["Manual", "3D-assigned-new"]
    compare_displacements(compare_files, names)


def compare_displacements2():
    hand_adjusted_raw = "../../datasets/100-904_3Dt_13_blue/rods_df_blue.csv"
    assign_3d_rand_end = "../example/debug_100-904_3Dt_13_blue/"\
        "rand_endp/rods_df_blue.csv"
    assign_3d_rand_p = "../example/debug_100-904_3Dt_13_blue/"\
        "randomized/rods_df_blue.csv"
    assign_3d_rand_both = "../example/debug_100-904_3Dt_13_blue/"\
        "rand_both/rods_df_blue.csv"
    assign_3d_no_rand = "../example/debug_100-904_3Dt_13_blue/"\
        "rods_df_blue.csv"
    compare_files = [hand_adjusted_raw, assign_3d_no_rand, assign_3d_rand_p,
                     assign_3d_rand_end, assign_3d_rand_both]
    data_out = []
    for file in compare_files:
        df_data = pd.read_csv(file, sep=",", index_col=0)
        no_frames = len(df_data.frame.unique())
        no_particles = len(df_data.particle.unique())
        data3d = np.zeros((no_frames, no_particles, 3, 2))
        for idx_f, f in enumerate(df_data.frame.unique()):
            frame_data = df_data.loc[df_data.frame == f]
            idx_p = frame_data["particle"].to_numpy()
            data3d[idx_f, idx_p, :, 0] = frame_data[
                ["x1", "y1", "z1"]].to_numpy()
            data3d[idx_f, idx_p, :, 1] = frame_data[
                ["x2", "y2", "z2"]].to_numpy()
        data_out.append(data3d)
    rv.compare_diplacements(data_out, ["Manual", "3D-no-rand", "3D-rand-part",
                                       "3D-rand-end", "3D-rand-both"])


def vis_3D():
    # # BUG: Here the 3D coordinates are "all-over the place"
    # file = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_onlydisp/rods_df_blue.csv"

    # # FIXME: 3D coordinates look "alright", but might need rematching
    # file = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching/rods_df_blue.csv"

    # # BUG: Here the 3D coordinates are "all-over the place"
    # file = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_debug/rods_df_blue.csv"

    # # BUG: Here the 3D coordinates are "all-over the place"
    # file = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_debug-len_rematched/rods_df_blue.csv"

    # TODO: matching in 3D with bug, that 1 rod is selected multiple times,
    #       cost function is 3D-displacement * reprojection error
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_good_rematched/rods_df_blue.csv"

    # TODO: The next file looks good in 3D in comparison to the "manual"
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_rematched/rods_df_blue.csv"

    # # BUG: Here the 3D coordinates are "all-over the place"
    # file = "../example/debug_100-904_3Dt_13_blue/"\
    #     "advanced_matching_onlydisp/rods_df_blue.csv"

    # FIXME: Look good, but still some wiggle, displacement is horrible
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-2_rematched/rods_df_blue.csv"

    # FIXME: looks horrible
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-2_disp_rematched/rods_df_blue.csv"
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-2_disp/rods_df_blue.csv"

    # TODO: looks very good
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-3_rematched/rods_df_blue.csv"
    # FIXME: close but still a bit strange, might be due to endpoint switching
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v4-3/rods_df_blue.csv"

    # BUG: the first (3D)point always looks good, the second moves a lot
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-1/rods_df_blue.csv"

    # TODO: looks good, some jumping of 90° rotations
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-1_rematched/rods_df_blue.csv"

    # BUG: horrible
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-2-len/rods_df_blue.csv"
    # BUG: much worse than best solutions
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-2-len_rematched/rods_df_blue.csv"

    # BUG: eval
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-3-len2/rods_df_blue.csv"
    # BUG: eval
    file = "../example/debug_100-904_3Dt_13_blue/"\
        "advanced_matching_debug_v5-3-len2_rematched/rods_df_blue.csv"

    df_data = pd.read_csv(file, sep=",", index_col=0)
    no_frames = len(df_data.frame.unique())
    no_particles = len(df_data.particle.unique())
    data3d = np.zeros((no_frames, no_particles, 3, 2))
    for idx_f, f in enumerate(df_data.frame.unique()):
        frame_data = df_data.loc[df_data.frame == f]
        idx_p = frame_data["particle"].to_numpy()
        data3d[idx_f, idx_p, :, 0] = frame_data[
            ["x1", "y1", "z1"]].to_numpy()
        data3d[idx_f, idx_p, :, 1] = frame_data[
            ["x2", "y2", "z2"]].to_numpy()

    orig_f = "/home/niemann/Documents/ParticleDetection/datasets/"\
        "100-904_3Dt_13_blue/rods_df_blue.csv"
    df_orig = pd.read_csv(orig_f, sep=",", index_col=0)
    no_frames = len(df_orig.frame.unique())
    no_particles = len(df_orig.particle.unique())
    data_orig = np.zeros((no_frames, no_particles, 3, 2))
    for idx_f, f in enumerate(df_orig.frame.unique()):
        frame_data = df_orig.loc[df_orig.frame == f]
        idx_p = frame_data["particle"].to_numpy()
        data_orig[idx_f, idx_p, :, 0] = frame_data[
            ["x1", "y1", "z1"]].to_numpy()
        data_orig[idx_f, idx_p, :, 1] = frame_data[
            ["x2", "y2", "z2"]].to_numpy()

    rv.show_3D(data3d, data_orig)
    rv.animate_3D(data3d, data_orig)


if __name__ == "__main__":
    # test_displacement()
    # compare_displacements2()
    # compare_all()
    # compare_3d_simple()
    compare_3d_advanced()
    vis_3D()

from typing import List
import numpy as np
import matplotlib.pyplot as plt


def matching_results(reprojetion_errors: np.ndarray, rod_lengths: np.ndarray):
    """Plot the key performances for the matching process.

    Parameters
    ----------
    reprojetion_errors : np.ndarray
    rod_lengths : np.ndarray
    """
    # rep_norm = (112/1082)   # scaling constant taken from MATLAB script
    # reprojetion_errors *= rep_norm

    plt.figure()
    plt.hist(reprojetion_errors, alpha=.5,
             bins=np.arange(0, 50, 0.25), edgecolor="black")
    plt.axvline(np.median(reprojetion_errors), color="r")
    plt.xlim(left=0)
    plt.legend(["median", "errors"])
    plt.xlabel("Reprojection error (in px)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of reprojection errors.")

    plt.figure()
    plt.hist(rod_lengths, alpha=.5, bins=np.arange(0, rod_lengths.max(), 0.1),
             edgecolor="black")
    plt.axvline(np.median(rod_lengths), color="r")
    plt.xlim(left=0)
    plt.legend(["median", "lengths"])
    plt.xlabel("Rod length (in mm)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of detected particle lengths")
    plt.show()
    return


def displacement_fwise(data_3d: np.ndarray):
    """_summary_

    Parameters
    ----------
    data_3d : np.ndarray
        [frame, particle, coordinate(3), endpoint(2)]
    """
    combo1 = np.linalg.norm(
        np.diff(data_3d, axis=0).squeeze(), axis=2).squeeze()
    switched_data_3d = data_3d[:, :, :, ::-1]
    combo2 = np.linalg.norm(
        (switched_data_3d[:-1, :, :, :] - data_3d[1:, :, :, :]).squeeze(),
        axis=2
    ).squeeze()
    displacements = np.stack([np.sum(combo1, axis=-1),
                              np.sum(combo2, axis=-1)])
    min_disp = np.min(displacements, axis=0)
    plt.plot(min_disp, alpha=0.3,
             label=[f"p{p}" for p in range(min_disp.shape[1])])
    plt.plot(np.mean(min_disp, axis=-1), color="black", label="mean")
    # plt.yscale("log")
    # plt.xscale("log")
    # plt.ylim((0, 25))
    plt.xlabel("Frame")
    plt.ylabel("Displacement [mm]")
    plt.legend()
    plt.show()


def compare_diplacements(data: List[np.ndarray], labels: List[str] = None):
    plt.figure()
    for data_3d in data:
        combo1 = np.linalg.norm(
            np.diff(data_3d, axis=0).squeeze(), axis=2).squeeze()
        switched_data_3d = data_3d[:, :, :, ::-1]
        combo2 = np.linalg.norm(
            (switched_data_3d[:-1, :, :, :] - data_3d[1:, :, :, :]).squeeze(),
            axis=2
        ).squeeze()
        displacements = np.stack([np.sum(combo1, axis=-1),
                                  np.sum(combo2, axis=-1)])
        min_disp = np.min(displacements, axis=0)
        plt.plot(np.mean(min_disp, axis=-1), alpha=0.5)
    # plt.yscale("log")
    # plt.xscale("log")
    # plt.ylim((0, 50))
    plt.xlabel("Frame")
    plt.ylabel("Displacement [mm]")
    plt.legend(labels)
    plt.show()


if __name__ == "__main__":
    pass

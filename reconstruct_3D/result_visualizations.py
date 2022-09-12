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
             bins=np.arange(0, reprojetion_errors.max(), 0.5))
    plt.axvline(np.mean(reprojetion_errors), color="g")
    plt.axvline(np.median(reprojetion_errors), color="r")
    plt.xlim(left=0)
    plt.legend(["mean", "median", "errs"])
    plt.xlabel("Reprojection error (in mm)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of reprojection errors.")

    plt.figure()
    plt.hist(rod_lengths, alpha=.5, bins=np.arange(0, rod_lengths.max(), 0.25))
    plt.axvline(np.mean(rod_lengths), color="g")
    plt.axvline(np.median(rod_lengths), color="r")
    plt.xlim(left=0)
    plt.legend(["mean", "median", "errs"])
    plt.xlabel("Rod length (in mm)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of detected particle lengths")
    plt.show()
    return


if __name__ == "__main__":
    pass

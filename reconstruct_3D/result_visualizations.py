import numpy as np
import matplotlib.pyplot as plt


def matching_results(reprojetion_errors: np.ndarray, rod_lengths: np.ndarray):
    rep_norm = (112/1082)   # scaling constant taken from MATLAB script
    reprojetion_errors *= rep_norm

    plt.figure()
    hist = plt.hist(reprojetion_errors, alpha=.3)
    plt.axvline(np.mean(reprojetion_errors), color="g")
    plt.axvline(np.median(reprojetion_errors), color="r")
    plt.legend(["mean", "median", "errs"])
    plt.xlabel("Reprojection error (in mm)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of reprojection errors.")
    plt.show()

    plt.figure()
    plt.hist(rod_lengths, alpha=.2)
    plt.axvline(np.mean(rod_lengths), color="g")
    plt.axvline(np.median(rod_lengths), color="r")
    plt.legend(["mean", "median", "errs"])
    plt.xlabel("Rod length (in mm)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of detected particle lengths")
    plt.show()
    return


if __name__ == "__main__":
    pass

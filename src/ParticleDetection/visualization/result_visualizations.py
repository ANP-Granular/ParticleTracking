from typing import List
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d.art3d import Line3D
import matplotlib.animation as animation


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
    frames = len(data[0])
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
    plt.ylim((0, 25))
    plt.xlim((0, frames))
    plt.xlabel("Frame")
    plt.ylabel("Displacement [mm]")
    plt.legend(labels)
    plt.show()


def show_3D(data: np.ndarray, comparison: np.ndarray = None):
    f1 = data[0]
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")
    rod_lines: List[Line3D] = []
    for rod in f1:
        l_curr = ax.plot(*rod, color="blue")
        rod_lines.append(l_curr)

    ax_frame = fig.add_axes([0.25, 0.1, 0.65, 0.03])
    sframe = Slider(
        ax_frame, "Frame", 0, len(data), 0, valstep=list(range(0, len(data))),
        color="green"
    )

    orig_lines: List[Line3D] = []
    if comparison is not None:
        for rod in comparison[0]:
            l_orig = ax.plot(*rod, color="green")
            orig_lines.append(l_orig)

    def update(val):
        ax.set_title(f"Frame: {val}")
        curr_data = data[val]
        for line, rod in zip(rod_lines, curr_data):
            line[0].set_data_3d(*rod)

        if comparison is not None:
            for line, rod in zip(orig_lines, comparison[val]):
                line[0].set_data_3d(*rod)

        fig.canvas.draw_idle()

    def arrow_key_image_control(event):
        if event.key == 'left':
            new_val = sframe.val - 1
            if new_val < 0:
                return
            sframe.set_val(new_val)
        elif event.key == 'right':
            new_val = sframe.val + 1
            if new_val >= len(data):
                return
            sframe.set_val(new_val)
        else:
            pass

    sframe.on_changed(update)
    fig.canvas.mpl_connect('key_press_event', arrow_key_image_control)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    plt.show()


def animate_3D(data: np.ndarray, comparison: np.ndarray = None):
    f1 = data[0]
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")

    def update_lines(num, walks, lines, orig_lines):
        ax.set_title(f"Frame: {num}")
        rods = walks[num]
        if orig_lines is not None:
            rods_orig = comparison[num]
            for line, orig_line, rod, rod_orig in \
                    zip(lines, orig_lines, rods, rods_orig):
                line.set_data_3d(*rod)
                orig_line.set_data_3d(*rod_orig)

        for line, rod in zip(lines, rods):
            line.set_data_3d(*rod)
        return lines

    # Create lines initially without data
    lines = [ax.plot([], [], [], color="blue")[0] for _ in f1]
    orig_lines = None
    if comparison is not None:
        orig_lines = [ax.plot([], [], [], color="green")[0] for _ in f1]

    # Setting the axes properties
    ax.set(xlim3d=(data[:, :, 0, :].min(), data[:, :, 0, :].max()), xlabel='X')
    ax.set(ylim3d=(data[:, :, 1, :].min(), data[:, :, 1, :].max()), ylabel='Y')
    ax.set(zlim3d=(data[:, :, 2, :].min(), data[:, :, 2, :].max()), zlabel='Z')

    # Creating the Animation object
    anim = animation.FuncAnimation(                             # noqa: F841
        fig, update_lines, len(data), fargs=(data, lines, orig_lines),
        interval=50)
    plt.show()


if __name__ == "__main__":
    pass

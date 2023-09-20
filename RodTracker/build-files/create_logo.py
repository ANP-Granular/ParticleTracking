from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mpl_colors
from matplotlib import patches
from matplotlib.transforms import Bbox
from mpl_toolkits.mplot3d import art3d
from PIL import Image


if __name__ == "__main__":
    output_path = Path(__file__).parent / "../src/RodTracker/resources"
    my_colors = ["black", "blue", "green", "purple", "red", "yellow"]
    my_colors = [mpl_colors.to_rgba(c, alpha=1.0) for c in my_colors]
    my_colors_proj = [mpl_colors.to_rgba(c, alpha=0.5) for c in my_colors]
    num_rod = 4
    c_list = []
    c_list_proj = []
    for c in my_colors:
        c_list.extend(num_rod * [c])
    for c in my_colors_proj:
        c_list_proj.extend(num_rod * [c])

    # np.random.seed(1)
    np.random.seed(5)
    with_projection = True

    rod_len = 0.2
    x = np.random.rand(num_rod * len(my_colors), 2)
    y = np.random.rand(num_rod * len(my_colors), 2)
    z = np.random.rand(num_rod * len(my_colors), 2)
    dx = np.diff(x, axis=1)
    dy = np.diff(y, axis=1)
    dz = np.diff(z, axis=1)

    vec_lens = np.sqrt(dx**2 + dy**2 + dz**2)
    # scale_fs = np.reshape(rod_len/vec_lens, 2*len(my_colors))
    scale_fs = rod_len / vec_lens
    x[:, 1] = x[:, 0] + np.reshape(dx * scale_fs, num_rod * len(my_colors))
    y[:, 1] = y[:, 0] + np.reshape(dy * scale_fs, num_rod * len(my_colors))
    z[:, 1] = z[:, 0] + np.reshape(dz * scale_fs, num_rod * len(my_colors))

    fig = plt.figure()
    ax = fig.add_subplot(projection="3d", zorder=1)
    if with_projection:
        a_off = 0.2
        # Bottom plane
        verts_bot = [
            (-0.1, -0.1, -a_off),
            (-0.1, 1.1, -a_off),
            (1.1, 1.1, -a_off),
            (1.1, -0.1, -a_off),
        ]
        # Top plane
        verts_top = [
            (-0.1, -0.1, 1.0 + a_off),
            (-0.1, 1.1, 1.0 + a_off),
            (1.1, 1.1, 1.0 + a_off),
            (1.1, -0.1, 1.0 + a_off),
        ]
        # Left plane
        verts_left = [
            (-a_off, -0.1, 1.1),
            (-a_off, 1.1, 1.1),
            (-a_off, 1.1, -0.1),
            (-a_off, -0.1, -0.1),
        ]

        ax.add_collection3d(
            art3d.Poly3DCollection(
                [verts_bot, verts_left],
                color="gray",
                alpha=0.15,
                edgecolor="None",
            )
        )

    # frame in background
    ax.plot([0, 0], [0, 1], [0, 0], color="black")
    ax.plot([0, 1], [1, 1], [0, 0], color="black")
    ax.plot([0, 0], [1, 1], [0, 1], color="black")
    # "rods"
    for i in range(x.shape[0]):
        ax.plot(x[i, :], y[i, :], z[i, :], linewidth=3, color=c_list[i])

        if with_projection:
            # projections
            ax.plot(
                x[i, :], y[i, :], zs=-a_off, linewidth=3, color=c_list_proj[i]
            )
            ax.plot(
                y[i, :],
                z[i, :],
                zs=-a_off,
                zdir="x",
                linewidth=3,
                color=c_list_proj[i],
            )
            # ax.plot(x[i, :], z[i, :], zs=1, zdir="y", linewidth=3,
            #         color=c_list_proj[i])

    # Frame in foreground
    ax.plot([0, 0], [0, 0], [0, 1], color="black")
    ax.plot([0, 0], [0, 1], [1, 1], color="black")
    ax.plot([0, 1], [1, 1], [1, 1], color="black")
    ax.plot([1, 1], [1, 1], [1, 0], color="black")
    ax.plot([1, 1], [1, 0], [1, 1], color="black")
    ax.plot([1, 0], [0, 0], [1, 1], color="black")
    ax.plot([1, 1], [0, 0], [1, 0], color="black")
    ax.plot([1, 0], [0, 0], [0, 0], color="black")
    ax.plot([1, 1], [0, 1], [0, 0], color="black")

    ax.set_axis_off()

    # Save Logo for display in App
    plt.savefig(
        output_path / "logo.png",
        facecolor="none",
        format="png",
        transparent=True,
        pad_inches=0,
        bbox_inches=Bbox([[1.50, 0.6], [5.0, 4.11]]),  # w: 6.4, h: 4.8
    )
    logo = Image.open(output_path / "logo.png")
    logo.resize((100, 100), Image.LANCZOS).save(output_path / "logo_small.png")

    # Add background
    ax2 = fig.add_axes([0, 0, 1, 1], zorder=0)
    box_color = "white"
    box_color = "#fefcf5"  # 'warm-white' 3
    box_color = "#cccccc"

    box_style = patches.BoxStyle("round", rounding_size=0.12)  # best
    # box_style = patches.BoxStyle("round", rounding_size=0.36)  # max radius
    bg_rect = patches.FancyBboxPatch(
        [0.45, 0.43],
        0.12,
        0.12,
        boxstyle=box_style,
        facecolor=box_color,
        edgecolor=box_color,
    )
    ax2.add_patch(bg_rect)

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.set_aspect("equal")
    ax2.set_axis_off()

    # save icon
    plt.savefig(
        output_path / "icon.png",
        facecolor="none",
        format="png",
        transparent=True,
        bbox_inches=Bbox([[1.50, 0.6], [5.0, 4.11]]),  # w: 6.4, h: 4.8
    )
    icon = Image.open(output_path / "icon.png")
    icon.save(output_path / "icon_windows.ico", sizes=[(256, 256)])
    icon.save(output_path / "icon_macOS.icns")

    bg_rect.remove()

    # Splash screen
    splash_color = "#3C3F41"  # dark
    # splash_color = "#AFB1B3"  # light
    # splash_color = "#fefcf5"  # 'warm-white' 3
    # splash_color = "#fdf5e0"  # 'warm-white' 2

    text_color = "#fefcf5"  # 'warm-white' 3
    # text_color = "black"

    splash_style = patches.BoxStyle("round", rounding_size=0.12)
    splash_rect = patches.FancyBboxPatch(
        [0.34, 0.35],
        0.36,
        0.3,
        boxstyle=splash_style,
        facecolor=splash_color,
        edgecolor=splash_color,
    )
    ax2.add_patch(splash_rect)
    ax2.text(
        x=0.53,
        y=0.87,
        s="RodTracker",
        color=text_color,
        horizontalalignment="center",
        verticalalignment="center",
        fontsize=32,
        family="monospace",
        weight="bold",
    )

    plt.savefig(
        output_path / "splash.png",
        facecolor="none",
        format="png",
        transparent=True,
        bbox_inches=Bbox([[0.98, 0.22], [5.61, 4.57]]),  # w: 6.4, h: 4.8
    )

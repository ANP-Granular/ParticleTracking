"""
Collection of plotting functions to evaluate automatic 3D rod position
reconstruction from images of a stereocamera system.

Authors:    Adrian Niemann (adrian.niemann@ovgu.de)
Date:       01.11.2022

"""
from typing import List, Tuple
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.widgets import Slider
from mpl_toolkits.mplot3d.art3d import Line3D
import matplotlib.animation as animation


def matching_results(reprojetion_errors: np.ndarray,
                     rod_lengths: np.ndarray, show: bool = True)\
        -> None | Tuple[Figure]:
    """Plot the reprojection errors and rod lengths after the matching process.

    Plots histograms for the rod endpoint reprojection errors and the rod
    lengths, especially for evaluation of a rod matching process.

    Parameters
    ----------
    reprojetion_errors : np.ndarray
    rod_lengths : np.ndarray
    show : bool, optional
        Flag, whether to show the figure immediately or to return it instead.
        Default is True.

    Returns
    -------
    None | Tuple[Figure]
        Returns the figures only, if `show` was set to False.
        -> [0]: reprojection errors histogram
        -> [1]: rod lengths histogram
    """
    # rep_norm = (112/1082)   # scaling constant taken from MATLAB script
    # reprojetion_errors *= rep_norm

    fig1 = plt.figure()
    plt.hist(reprojetion_errors, alpha=.5,
             bins=np.arange(0, 50, 0.25), edgecolor="black")
    plt.axvline(np.median(reprojetion_errors), color="r")
    plt.xlim(left=0)
    plt.legend(["median", "errors"])
    plt.xlabel("Reprojection error (in px)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of reprojection errors.")

    fig2 = plt.figure()
    plt.hist(rod_lengths, alpha=.5, bins=np.arange(0, rod_lengths.max(), 0.1),
             edgecolor="black")
    plt.axvline(np.median(rod_lengths), color="r")
    plt.xlim(left=0)
    plt.legend(["median", "lengths"])
    plt.xlabel("Rod length (in mm)")
    plt.ylabel("Number of rods")
    plt.title("Distribution of detected particle lengths")

    if not show:
        return fig1, fig2
    plt.show()
    return


def displacement_fwise(data_3d: np.ndarray, show: bool = True)\
        -> None | Figure:
    """Plot the frame-wise (minimum) displacement per rod and average of rods.

    From the 3D positions of rods the between frames displacement is calculated
    for each of the given rods. Both rod endpoint combinations are used to
    calculate the displacement and the respective minimum is chosen for
    plotting. The resulting plot then consists of one line per given particle,
    as well as, the average displacement of all particles between the frames.

    Parameters
    ----------
    data_3d : np.ndarray
        [frame, particle, coordinate(3), endpoint(2)]
    show : bool, optional
        Flag, whether to show the figure immediately or to return it instead.
        Default is True.

    Returns
    -------
    None | Figure
        Returns the figure only, if `show` was set to False.
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
    fig = plt.figure()
    plt.plot(min_disp, alpha=0.3,
             label=[f"p{p}" for p in range(min_disp.shape[1])])
    plt.plot(np.mean(min_disp, axis=-1), color="black", label="mean")
    plt.xlabel("Frame")
    plt.ylabel("Displacement [mm]")
    plt.legend()

    if not show:
        return fig
    plt.show()
    return


def compare_diplacements(data: List[np.ndarray], labels: List[str] = None,
                         show: bool = True) -> None | Figure:
    """Compare the frame-wise, average displacement between multiple datasets.

    From the 3D positions of rods the between frames displacement is calculated
    for each of the given rods. Both rod endpoint combinations are used to
    calculate the displacement and the respective minimum is chosen for
    plotting. The resulting plot then consists of the average displacement for
    of the given 'datasets'.

    Parameters
    ----------
    data : List[np.ndarray]
        Dimensions: [dataset, frame, particle, coordinate(3), endpoint(2)]
    labels : List[str], optional
        List of names/IDs for the datasets given.
        By default None.
    show : bool, optional
        Flag, whether to show the figure immediately or to return it instead.
        Default is True.

    Returns
    -------
    None | Figure
        Returns the figure only, if `show` was set to False.
    """
    fig = plt.figure()
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
    plt.ylim((0, 25))
    plt.xlim((0, frames))
    plt.xlabel("Frame")
    plt.ylabel("Displacement [mm]")
    plt.legend(labels)

    if not show:
        return fig
    plt.show()
    return


def show_3D(data: np.ndarray, comparison: np.ndarray = None,
            show: bool = True) -> None | Figure:
    """Create/show a plot of rods in 3D with/without a comparison dataset.

    The data will be plotted in blue and the comparison in green. `Right` and
    `Left` can control the displayed frame.

    Parameters
    ----------
    data : np.ndarray
        3D coordinates of rods over multiple frames.
        Dimensions: [frame, 3, 2]
    comparison : np.ndarray, optional
        3D coordinates of comparison rods over the same frames as `data`.
        Dimensions: [frame, 3, 2]
        By default None.
    show : bool, optional
        Flag, whether to show the figure immediately or to return it instead.
        Default is True.

    Returns
    -------
    None | Figure
        Returns the figure only, if `show` was set to False.
    """
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
    if comparison is not None:
        ax.legend([orig_lines[0], rod_lines[0]], ["manual", "auto"])
    else:
        ax.legend([rod_lines[0]], ["auto"])

    if not show:
        return fig
    plt.show()
    return


def animate_3D(data: np.ndarray, comparison: np.ndarray = None,
               show: bool = True) -> None | Figure:
    """Create/show an animation of rods in 3D with/out a comparison dataset.

    The data will be plotted in blue and the comparison in green.

    Parameters
    ----------
    data : np.ndarray
        3D coordinates of rods over multiple frames.
        Dimensions: [frame, particle, 3, 2]
    comparison : np.ndarray, optional
        3D coordinates of comparison rods over the same frames as `data`.
        Dimensions: [frame, particle, 3, 2]
        By default None.
    show : bool, optional
        Flag, whether to show the figure immediately or to return it instead.
        Default is True.

    Returns
    -------
    None | Figure
        Returns the figure only, if `show` was set to False.
    """
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
    if comparison is not None:
        ax.legend([orig_lines[0], lines[0]], ["manual", "auto"])
    else:
        ax.legend([lines[0]], ["auto"])

    # Creating the Animation object
    anim = animation.FuncAnimation(                             # noqa: F841
        fig, update_lines, len(data), fargs=(data, lines, orig_lines),
        interval=50)

    if not show:
        writer = animation.PillowWriter(fps=30)
        anim.save("./animate_3D.gif", writer=writer)
        return fig
    plt.show()
    return


def match_nd(weights: np.ndarray, whr: tuple[np.ndarray], show: bool = True)\
        -> None | Figure:
    """Plot the result `npartite_matching` as all nodes with edges between the
    matched nodes.

    Parameters
    ----------
    weights : np.ndarray
        Multidimensional weight matrix used for ND_matching.
        Example dimensions (dictates `whr` dimensions):
        a) [12, 4, 8]
        b) [12, 12, 12, 48]
    whr : tuple[np.ndarray]
        Output of the `npartite_matching` process, i.e. the matched indeces
        per dimension.
        Example dimensions (see `weights` dimensions):
        a) (4, 4, 4) -> tuple of 3 arrays with len=4
        b) (12, 12, 12, 12) -> tuple of 4 arrays with len=12
    show : bool, optional
        Flag, whether to show the figure immediately or to return it instead.
        Default is True.

    Returns
    -------
    None | Figure
        Returns the figure only, if `show` was set to False.

    Note
    ----
    Taken from:
    https://stackoverflow.com/questions/60940781/solving-the-assignment-problem-for-3-groups-instead-of-2
    """
    dims = weights.shape

    # create list of node positions for plotting and labeling
    pon = [(idi, idv) for idi, dim in enumerate(dims) for idv in range(dim)]
    # convert to dictionary
    pos = {tuple(poi): poi for poi in pon}

    # create empty graph
    graph = nx.empty_graph(len(pos))
    # rename labels according to plot position
    mapping = {idp: tuple(poi) for idp, poi in enumerate(pon)}
    graph = nx.relabel_nodes(graph, mapping)

    # set edges from maximum n-partite matching
    edges = []
    # loop over paths
    for whi in np.array(whr).T:
        weight = weights[tuple(np.array(whj) for whj in whi)]
        pairs = list(zip(whi[:-1], whi[1:]))
        # loop over consecutive node pairs along path
        for idp, (id0, id1) in enumerate(pairs):
            edges.append(((idp+0, id0), (idp+1, id1), {'weight': weight}))
    graph.add_edges_from(edges)

    # set path weights as edge widths for plotting
    width = np.array([edge['weight'] for id0, id1, edge in
                      graph.edges(data=True)])
    width = 3.0*width/max(width)

    # plot network
    fig = plt.figure(figsize=(16, 9))
    obj = weights[whr].sum()
    plt.title('total matching weight = %.2f' % obj)
    nx.draw_networkx(graph, pos=pos, width=width, node_color='orange',
                     node_size=700)
    plt.axis('off')

    if not show:
        return fig
    plt.show()
    return

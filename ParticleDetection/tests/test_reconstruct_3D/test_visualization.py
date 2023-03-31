import os
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import pandas as pd
import pytest
import ParticleDetection.reconstruct_3D.visualization as vis
import ParticleDetection.utils.data_loading as dl
from conftest import EXAMPLES


@pytest.fixture(scope="session")
def plotting_data() -> pd.DataFrame:
    colors = ["black", "green"]
    data_folder = EXAMPLES
    data = pd.DataFrame()
    for color in colors:
        data_file = data_folder.joinpath(f"rods_df_{color}.csv")
        tmp = pd.read_csv(data_file, index_col=0)
        tmp["color"] = color
        data = pd.concat([data, tmp])
    data.sort_values(["color", "frame", "particle"], inplace=True)
    return data


def test_matching_results(plotting_data: pd.DataFrame):
    lengths = plotting_data["l"]
    errs = np.random.random((2, 10)) * 55
    result = vis.matching_results(errs, lengths, show=False)
    assert len(result) == 2
    for res in result:
        assert isinstance(res, Figure)
    plt.close("all")


def test_matching_results_show(monkeypatch: pytest.MonkeyPatch,
                               plotting_data: pd.DataFrame):
    show_called = False

    def show(*args, **kwargs):
        nonlocal show_called
        show_called = True

    monkeypatch.setattr(plt, "show", show)
    lengths = plotting_data["l"]
    errs = np.random.random((2, 10)) * 55
    result = vis.matching_results(errs, lengths, show=True)
    assert result is None
    assert show_called is True
    plt.close("all")


def test_length_hist(plotting_data: pd.DataFrame):
    lengths = plotting_data["l"].to_numpy()
    result = vis.length_hist(lengths)
    assert isinstance(result, Figure)
    plt.close("all")


def test_length_hist_wide_range(monkeypatch: pytest.MonkeyPatch):
    called = 0

    def failing_plot(*args, **kwargs):
        nonlocal called
        if called == 1:
            assert kwargs.get("bins") == "doane"
            called += 1
            return plt.figure()
        else:
            called += 1
            raise ValueError("Maximum allowed size exceeded")

    monkeypatch.setattr(plt, "hist", failing_plot)

    result = vis.length_hist(np.random.random((2, 10)))
    assert isinstance(result, Figure)
    plt.close("all")


def test_length_hist_break(monkeypatch: pytest.MonkeyPatch,
                           plotting_data: pd.DataFrame):
    def failing_plot(*args, **kwargs):
        raise ValueError("test")

    monkeypatch.setattr(plt, "hist", failing_plot)
    with pytest.raises(ValueError) as err:
        vis.length_hist(plotting_data["l"].to_numpy())
    assert err.value.args[0] == "test"
    plt.close("all")


@pytest.mark.parametrize("data_shape", [(2, 10), (16,), (15, 3)])
def test_reprojection_errors_hist(data_shape: tuple):
    data = np.random.random(data_shape) * 55
    result = vis.reprojection_errors_hist(data)
    assert isinstance(result, Figure)
    plt.close("all")


def test_repr_err_hist_wide_range(monkeypatch: pytest.MonkeyPatch):
    called = 0
    previous_bins = None

    def failing_plot(*args, **kwargs):
        nonlocal called, previous_bins
        if called == 1:
            bins = kwargs.get("bins")
            assert isinstance(bins, np.ndarray)
            assert len(bins) < len(previous_bins)
            called += 1
            return plt.figure()
        else:
            previous_bins = kwargs.get("bins")
            called += 1
            raise ValueError("Maximum allowed size exceeded")

    data = np.random.random((2, 10)) * 1e4
    monkeypatch.setattr(plt, "hist", failing_plot)
    result = vis.reprojection_errors_hist(data)
    assert isinstance(result, Figure)
    plt.close("all")


def test_repr_err_break(monkeypatch: pytest.MonkeyPatch):
    def failing_plot(*args, **kwargs):
        raise ValueError("test")

    monkeypatch.setattr(plt, "hist", failing_plot)
    with pytest.raises(ValueError) as err:
        vis.reprojection_errors_hist(np.random.random((2, 10)))
    assert err.value.args[0] == "test"
    plt.close("all")


def test_displacement_fwise(plotting_data: pd.DataFrame):
    data = dl.extract_3d_data(plotting_data)
    result = vis.displacement_fwise(data, show=False)
    assert isinstance(result, Figure)
    plt.close("all")


def test_displacement_fwise_show(monkeypatch: pytest.MonkeyPatch,
                                 plotting_data: pd.DataFrame):
    data = dl.extract_3d_data(plotting_data)
    show_called = False

    def show(*args, **kwargs):
        nonlocal show_called
        show_called = True

    monkeypatch.setattr(plt, "show", show)
    result = vis.displacement_fwise(data, show=True)
    assert result is None
    assert show_called is True
    plt.close("all")


def test_compare_displacements(plotting_data: pd.DataFrame):
    data = dl.extract_3d_data(plotting_data)
    comp_data = np.random.random(data.shape)
    names = ["test", "comparison"]
    result = vis.compare_diplacements([data, comp_data], names, show=False)
    assert isinstance(result, Figure)
    assert len(result.axes[0].lines) == 2
    plt.close("all")


def test_compare_displacements_labels(plotting_data: pd.DataFrame):
    data = dl.extract_3d_data(plotting_data)
    comp_data = np.random.random(data.shape)
    result = vis.compare_diplacements([data, comp_data], show=False)
    assert isinstance(result, Figure)
    assert len(result.axes[0].lines) == 2
    plt.close("all")


def test_compare_displacements_show(monkeypatch: pytest.MonkeyPatch):
    show_called = False

    def show(*args, **kwargs):
        nonlocal show_called
        show_called = True

    data = np.random.random((5, 6, 3, 2))
    names = ["test0", "test1"]
    monkeypatch.setattr(plt, "show", show)
    result = vis.compare_diplacements([data, data], names, show=True)
    assert result is None
    assert show_called is True
    plt.close("all")


def test_show_3D():
    data0 = np.random.random((5, 6, 3, 2))
    data1 = data0 + 2
    result = vis.show_3D(data0, data1, show=False)
    assert isinstance(result, Figure)
    assert isinstance(result.axes[0], Axes3D)
    plt.close("all")


def test_show_3D_show(monkeypatch: pytest.MonkeyPatch):
    show_called = False

    def show(*args, **kwargs):
        nonlocal show_called
        show_called = True

    monkeypatch.setattr(plt, "show", show)
    data0 = np.random.random((5, 6, 3, 2))
    data1 = data0 + 2
    result = vis.show_3D(data0, data1, show=True)
    assert result is None
    assert show_called is True
    plt.close("all")


def test_animate_3D(tmp_path: Path):
    data0 = np.random.random((5, 6, 3, 2))
    data1 = data0 + 2
    previous_dir = os.getcwd()
    os.chdir(tmp_path)
    result = vis.animate_3D(data0, data1, show=False)
    os.chdir(previous_dir)

    assert isinstance(result, Figure)
    assert isinstance(result.axes[0], Axes3D)
    assert Path(tmp_path / "animate_3D.gif").exists()
    plt.close("all")


@pytest.mark.filterwarnings("ignore::UserWarning:matplotlib.animation")
def test_animate_3D_show(monkeypatch: pytest.MonkeyPatch):
    show_called = False

    def show(*args, **kwargs):
        nonlocal show_called
        show_called = True

    monkeypatch.setattr(plt, "show", show)
    data0 = np.random.random((5, 6, 3, 2))
    data1 = data0 + 2
    result = vis.animate_3D(data0, data1, show=True)
    assert result is None
    assert show_called is True
    plt.close("all")

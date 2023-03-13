import sys
import pytest
from pytest import MonkeyPatch
from pytestqt.qtbot import QtBot
import pandas as pd
from RodTracker.backend import detection
import ParticleDetection.utils.detection as p_detection
import ParticleDetection.utils.helper_funcs as hf
import ParticleDetection.utils.datasets as ds
if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources


@pytest.fixture()
def default_detector(monkeypatch: MonkeyPatch) -> detection.Detector:
    img_folder = importlib_resources.files(
        "RodTracker.resources.example_data.images.gp3")
    cam_id = "gp3"
    model = None
    frames = list(range(500, 503))
    images = [img_folder.joinpath(f"{frame:04d}.jpg") for frame in frames]
    classes = {
        0: ["test0", 5],
        1: ["test1", 6],
        3: ["test2", 7],
    }
    threshold = 0.5

    monkeypatch.setattr(p_detection, "_run_detection",
                        lambda *args, **kwargs: {"pred_masks": None})
    monkeypatch.setattr(hf, "rod_endpoints",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(ds, "add_points",
                        lambda *args, **kwargs: pd.DataFrame())

    yield detection.Detector(cam_id, model, images, frames, classes, threshold)


@pytest.mark.parametrize(("threshold"), (1.1, -1., 0.23, 0.))
def test_init_threshold(threshold: float):
    img_folder = importlib_resources.files(
        "RodTracker.resources.example_data.images.gp3")
    cam_id = "gp3"
    model = None
    frames = list(range(500, 503))
    images = [img_folder.joinpath(f"{frame:04d}.jpg") for frame in frames]
    classes = {
        0: ["test0", 5],
        1: ["test1", 6],
        3: ["test2", 7],
    }
    detector = detection.Detector(cam_id, model, images, frames, classes,
                                  threshold)
    assert detector.threshold <= 1.0
    assert detector.threshold >= 0.0
    if threshold <= 1.0 and threshold >= 0.0:
        assert threshold == detector.threshold
    elif threshold > 1.:
        assert detector.threshold == 1.0
    elif threshold < 0.:
        assert detector.threshold == 0.
    else:
        raise ValueError(f"Impossible threshold value: {threshold}")


def test_init_data():
    img_folder = importlib_resources.files(
        "RodTracker.resources.example_data.images.gp3")
    cam_id = "gp3"
    model = None
    frames = list(range(500, 502))
    images = [img_folder.joinpath(f"{frame:04d}.jpg") for frame in
              list(range(500, 503))]
    classes = {
        0: ["test0", 5],
        1: ["test1", 6],
        3: ["test2", 7],
    }
    threshold = 0.5
    with pytest.raises(ValueError):
        detection.Detector(cam_id, model, images, frames, classes,
                           threshold)


def test_abort(qtbot: QtBot, default_detector: detection.Detector):
    detection.abort_requested = True
    with qtbot.assert_not_emitted(
            default_detector.signals.progress, wait=1000):
        with qtbot.wait_signal(default_detector.signals.finished):
            default_detector.run()
    detection.abort_requested = False


def test_finished(qtbot: QtBot, default_detector: detection.Detector):
    expected_emitted = len(
        default_detector.frames) * [default_detector.signals.progress]
    expected_emitted.append(default_detector.signals.finished)
    with qtbot.wait_signals(expected_emitted, order='strict'):
        default_detector.run()

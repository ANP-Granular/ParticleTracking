import importlib
import os
import sys
from pytest import MonkeyPatch
import RodTracker.backend.file_locations as fl


def test_icon_exists():
    assert os.path.exists(fl.icon_path())


def test_readme_exists():
    assert os.path.exists(fl.readme_path())


def test_undo_icon_exists():
    assert os.path.exists(fl.undo_icon_path())


def test_readme_bundled(monkeypatch: MonkeyPatch):
    with monkeypatch.context() as m:
        m.setattr(sys, "_MEIPASS", "test_path", raising=False)
        import RodTracker.backend.file_locations as fl
        # Force reload to achieve code execution with proper environment
        importlib.reload(fl)
        readme_path = fl.readme_path()
    assert readme_path.startswith("test_path")

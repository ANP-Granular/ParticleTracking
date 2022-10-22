import sys
import pathlib
import importlib
import pytest


def test_path_addition():
    import RodTracker.RodTracker
    assert str(pathlib.Path(RodTracker.RodTracker.__file__).parent.parent)\
        in sys.path


def test_has_splash(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, 'pyi_splash',
                        __import__('mock_pyi_splash'))
    import RodTracker.RodTracker
    # Force reload to avoid "results" from imports in previous tests
    importlib.reload(RodTracker.RodTracker)
    assert RodTracker.RodTracker.HAS_SPLASH


@pytest.mark.skip(reason="Requires user interaction and therefore blocks "
                  "further automatic test execution")
def test_tmp_dir_create(tmpdir, monkeypatch: pytest.MonkeyPatch):
    import RodTracker.backend.logger as lg
    import RodTracker.RodTracker as RT
    lg.TEMP_DIR = tmpdir / "Rodtracker"
    assert not lg.TEMP_DIR.exists()
    with monkeypatch.context() as m:
        m.setattr(sys, "exit", lambda x: x)
        # TODO: autoclose window
        RT.main()
    assert lg.TEMP_DIR.exists()

import logging
import pathlib
import tempfile

TEMP_DIR: pathlib.Path = pathlib.Path(tempfile.gettempdir()) / "RodTracker"
if not TEMP_DIR.exists():
    TEMP_DIR.mkdir()
LOG_PATH = TEMP_DIR / "RodTracker.log"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
f_handle = logging.FileHandler(LOG_PATH, mode="a")
f_handle.setLevel(logging.INFO)
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%m/%d %H:%M:%S"
)
f_handle.setFormatter(formatter)
logger.addHandler(f_handle)

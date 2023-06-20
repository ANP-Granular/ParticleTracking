#  Copyright (c) 2023 Adrian Niemann Dmitry Puzyrev
#
#  This file is part of RodTracker.
#  RodTracker is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RodTracker is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RodTracker.  If not, see <http://www.gnu.org/licenses/>.

import logging
from pathlib import Path
import platformdirs


APPNAME = "RodTracker"
APPAUTHOR = "ANP-Granular"

LOG_DIR: Path = platformdirs.user_log_path(APPNAME, APPAUTHOR, opinion=False,
                                           ensure_exists=True)
LOG_FILE = LOG_DIR / "RodTracker.log"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
f_handle = logging.FileHandler(LOG_FILE, mode="a")
f_handle.setLevel(logging.INFO)
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%m/%d %H:%M:%S"
)
f_handle.setFormatter(formatter)
logger.addHandler(f_handle)
logging.captureWarnings(True)

CONFIG_DIR = platformdirs.user_config_path(APPNAME, APPAUTHOR, roaming=False,
                                           ensure_exists=True)
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DATA_DIR = platformdirs.user_data_path(APPNAME, APPAUTHOR, roaming=False,
                                       ensure_exists=True)

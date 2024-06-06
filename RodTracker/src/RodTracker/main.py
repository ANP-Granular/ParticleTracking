# Copyright (c) 2023-24 Adrian Niemann, and others
#
# This file is part of RodTracker.
# RodTracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RodTracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, List

import importlib_resources
from PyQt5 import QtCore, QtGui, QtWidgets

import RodTracker
from RodTracker import ExtensionState

_logger = logging.getLogger(RodTracker.APPNAME)


def main():
    currentdir = Path(inspect.getfile(inspect.currentframe())).resolve().parent
    parentdir = currentdir.parent
    sys.path.insert(0, str(parentdir))

    # Setup error handling before main window is running
    sys.excepthook = lambda t, val, tb: RodTracker.exception_logger(
        t, val, tb, use_exec=False
    )

    from RodTracker.backend.settings import Settings, UnknownSettingError

    try:
        val = Settings().get_setting("internal.log_level")
        RodTracker._set_log_level(val)
        RodTracker.LOG_LEVEL = val
    except UnknownSettingError:
        Settings().add_setting("internal.log_level", RodTracker.LOG_LEVEL)

    app = QtWidgets.QApplication(sys.argv)
    pixmap = QtGui.QPixmap(
        str(
            importlib_resources.files("RodTracker.resources").joinpath(
                "splash.png"
            )
        )
    )
    align = QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter
    color = QtGui.QColorConstants.White
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    splash.showMessage("Updating environment ...", align, color)
    import RodTracker.backend.logger as lg

    lg.MainLogger()

    splash.showMessage("Loading UI ...", align, color)
    import RodTracker.ui.mainwindow as mw

    main_window = mw.RodTrackWindow()

    # Load extensions
    discovered_exts: Dict[str, List[RodTracker.ExtensionState, dict, Path]] = (
        {}
    )
    extension_folder = Path(__file__).parent.parent / "extensions"
    if hasattr(sys, "_MEIPASS"):
        extension_folder = Path(__file__).parent / "extensions"

    # Discover available extensions
    for entry in extension_folder.iterdir():
        if not entry.is_dir() or entry.stem == "__pycache__":
            continue
        ext = entry.stem
        discovered_exts[ext] = [
            ExtensionState.UNDEFINED,
            {},
            entry,
        ]
        if list(entry.glob("DEACTIVATED")):
            # Skip loading if a file named 'DEACTIVATED' is present
            _logger.info(f"Extension '{ext}' is deactived.")
            discovered_exts[ext][0] = ExtensionState.DEACTIVATED
            continue

    def _try_loading(
        ext: str, discovered_exts, circ_prevention_list: List[str]
    ) -> ExtensionState:
        nonlocal splash, align, color, main_window
        if discovered_exts[ext][0] not in [
            ExtensionState.UNDEFINED,
            ExtensionState.DELAYED_LOADING,
        ]:
            return discovered_exts[ext][0]
        try:
            spec = importlib.util.spec_from_file_location(
                ext, discovered_exts[ext][2] / "__init__.py"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[ext] = module
            spec.loader.exec_module(module)

            # check extension dependencies
            break_loading = False
            for dep in module.REQUIRED_EXTENSIONS:
                if dep not in discovered_exts.keys():
                    break_loading = True
                    discovered_exts[ext][1][dep] = ExtensionState.UNAVAILABLE
                    discovered_exts[ext][0] = ExtensionState.MISSING_DEPENDENCY
                    _logger.warning(
                        f"Extension {ext} cannot be loaded due to missing "
                        f"dependency {dep}."
                    )
                    continue

                dep_state = discovered_exts[dep][0]
                discovered_exts[ext][1][dep] = dep_state
                if dep_state is ExtensionState.ACTIVE:
                    # Dependency is fulfilled
                    pass
                elif dep_state is ExtensionState.DELAYED_LOADING:
                    # WARNING: potential for circular dependency
                    discovered_exts[ext][0] = ExtensionState.DELAYED_LOADING
                    if dep in circ_prevention_list:
                        discovered_exts[ext][
                            0
                        ] = ExtensionState.CIRCULAR_DEPENDENCY
                        break_loading = True
                        continue
                    result = _try_loading(
                        dep, discovered_exts, [*circ_prevention_list, dep]
                    )
                    if result is not ExtensionState.ACTIVE:
                        break_loading = True
                        discovered_exts[ext][
                            0
                        ] = ExtensionState.MISSING_DEPENDENCY
                        _logger.warning(
                            f"Extension {ext} cannot be loaded due to a "
                            f"problem with dependency {dep}."
                        )
                elif dep_state is ExtensionState.CIRCULAR_DEPENDENCY:
                    break_loading = True
                    discovered_exts[ext][0] = ExtensionState.MISSING_DEPENDENCY
                    _logger.warning(
                        f"Extension {ext} cannot be loaded due to dependency "
                        f"{dep} having a circular dependency."
                    )
                elif dep_state is ExtensionState.BROKEN:
                    break_loading = True
                    discovered_exts[ext][0] = ExtensionState.MISSING_DEPENDENCY
                    _logger.warning(
                        f"Extension {ext} cannot be loaded due to broken "
                        f"dependency {dep}."
                    )
                elif dep_state is ExtensionState.DEACTIVATED:
                    break_loading = True
                    discovered_exts[ext][0] = ExtensionState.MISSING_DEPENDENCY
                    _logger.warning(
                        f"Extension {ext} cannot be loaded due to deactivated "
                        f"dependency {dep}."
                    )
                elif dep_state is ExtensionState.MISSING_DEPENDENCY:
                    break_loading = True
                    discovered_exts[ext][0] = ExtensionState.MISSING_DEPENDENCY
                    _logger.warning(
                        f"Extension {ext} cannot be loaded due to dependency "
                        f"{dep} missing a dependency."
                    )
                elif dep_state is ExtensionState.UNDEFINED:
                    # WARNING: potential for circular dependency
                    if dep in circ_prevention_list:
                        discovered_exts[ext][
                            0
                        ] = ExtensionState.CIRCULAR_DEPENDENCY
                        break_loading = True
                        continue
                    discovered_exts[ext][0] = ExtensionState.DELAYED_LOADING
                    # recursively load the dependency
                    result = _try_loading(
                        dep, discovered_exts, [*circ_prevention_list, dep]
                    )
                    if result is not ExtensionState.ACTIVE:
                        break_loading = True
                        discovered_exts[ext][
                            0
                        ] = ExtensionState.MISSING_DEPENDENCY
                        _logger.warning(
                            f"Extension {ext} cannot be loaded due to a "
                            f"problem with dependency {dep}."
                        )
                else:
                    # WARNING: this should never occur!
                    raise ValueError(
                        "Unknown state discovered during extension loading: "
                        f"{result}."
                    )
            if break_loading:
                return discovered_exts[ext][0]

            # attempt loading the extension
            splash.showMessage(f"Loading extension: {ext}", align, color)
            module.setup(splash, main_window=main_window)
            _logger.info(f"Successfully loaded extension: {ext}")
            discovered_exts[ext][0] = ExtensionState.ACTIVE
            return ExtensionState.ACTIVE

        except Exception:
            _logger.error(
                f"Failed to load extension '{ext}':",
                exc_info=sys.exc_info(),
            )
            discovered_exts[ext][0] = ExtensionState.BROKEN
            return ExtensionState.BROKEN

    for ext in discovered_exts.keys():
        loading_result = _try_loading(ext, discovered_exts, [ext])
        if loading_result in [
            ExtensionState.BROKEN,
            ExtensionState.CIRCULAR_DEPENDENCY,
            ExtensionState.MISSING_DEPENDENCY,
        ]:
            # TODO: add popup for extensions failing to load
            pass

    splash.showMessage("Loading settings ...", align, color)
    main_window.settings.propagate_all_settings()

    splash.showMessage("Starting ...", align, color)
    main_window.ensure_usable()
    splash.finish(main_window)

    # Changing behavior of ErrorDialog
    sys.excepthook = RodTracker.exception_logger

    main_window.show()
    main_window.raise_()
    main_window.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

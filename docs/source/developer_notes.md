# Developer notes
## RodTracker

The different tasks described below require additional libraries compared to the default installation. Please make sure that you install the correct extras before attempting the tasks below (see [Installation options](installation/rodtracker.md#installation-options)).

### PyQt UI files
Please make sure that the dependencies from the `DEV` extra are installed.
The main GUI-layout is modeled in [mainwindow_layout.ui](../../RodTracker/src/RodTracker/ui/mainwindow_layout.ui) and can be changed using QtDesigner. 
Generate the [Python file](../../RodTracker/src/RodTracker/ui/mainwindow_layout.py) after changing the [UI-File](../../RodTracker/src/RodTracker/ui/mainwindow_layout.ui) using:
```shell
pyuic5 -o path/to/mainwindow_layout.py path/to/mainwindow_layout.ui
```

Do **not** change the [Python file](../../RodTracker/src/RodTracker/ui/mainwindow_layout.py) containing the GUI-Layout manually as all changes will be lost when generating it automatically again.

### Running tests

Please make sure that the dependencies from `TEST` or `DEV` extra are installed.
Run the tests with `pytest` from within the `RodTracker` directory:
```shell
YOUR/REPO/PATH/RodTracker$ pytest
```

```{note}
Some tests require a display (see [pytest-qt](https://pytest-qt.readthedocs.io/en/latest/troubleshooting.html#tox-invocationerror-without-further-information))! Make sure the machine either has a screen connected or use [pytest-xvfb](https://pypi.org/project/pytest-xvfb/).
```

### Building the docs
Please make sure that the dependencies of the `DOCS`, `BUILD`, or `DEV` extra are installed.
1. Clean the build directory:
   ```shell
   YOUR/REPO/PATH/docs$ make clean
   ```
2. (Re-)Build the documentation:
   ```shell
   YOUR/REPO/PATH/docs$ make html
   ```

Refer to the [Sphinx documentation](https://www.sphinx-doc.org/) for further options.

```{warning}
On Windows make sure that no other process, e.g. Dropbox, attempts to access files necessary for the build during this. Otherwise an `OSError: [WinError 110]` might occur and break the process.

On Linux this problem does not seem to occur.
```

### Bundling the app

Please make sure that the dependencies of the `BUILD`, or `DEV` extra are installed. On Linux there are additional requirements to be able to run the bundling script. Refer to the [PyInstaller documentation](https://pyinstaller.org/en/stable/requirements.html#gnu-linux) for that.

There is a script to generate an executable for both Windows and Linux. Prior to bundling it will also (re-)build the documentation because this is supposed to be contained in the bundled app.

**On Windows**: 
```shell
YOUR/REPO/PATH/RodTracker/build-files> build_app.bat
```
**On Linux**:
```shell
YOUR/REPO/PATH/RodTracker/build-files$ build_app.sh
```

There are two command line options `-onedir`(default)/`-onefile`. 
Both will generate a `.\RodTracker\build` and a `.\RodTracker\dist` folder. 
The generated executables are located in the `.\RodTracker\dist` folder.

In the first case everything is bundled into one folder named `RodTracker` 
which can be copied or moved as a whole. Run the executable
`dist\RodTracker\RodTrackerApp.exe` inside this folder to start the program.

The second script on the other hand generates only one file, i.e. 
`dist\RodTracker.exe`, that holds all necessary files to run the program 
and unpacks those during run-time.

```{warning}
On Windows make sure that no other process, e.g. Dropbox, attempts to access files necessary for the build during this. Otherwise an `OSError: [WinError 110]` might occur and break the process.

On Linux this problem does not seem to occur.
```

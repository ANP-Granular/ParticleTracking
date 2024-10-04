# Developer notes

## Building the docs
The documentation is a combined for the `ParticleDetection` and the `RodTracker` packages.
Please make sure that `ParticleDetection` is installed. It is not necessary to install the `DETECTRON` extra.
Please make sure that the `RodTracker` with the dependencies of the `DOCS`, `BUILD`, or `DEV` extra are installed.

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

On Linux/macOS this problem does not seem to occur.
```

```{note}
On macOS: Make sure that XCode is installed.
```

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

### Debugging Threads
When debugging the RodTracker it is sometimes useful to be able to put breakpoints in functions run in threads other than the main-thread. In Visual Studio Code this does not work out of the box. There it is necessary to use the following piece of code:
```python
import debugpy
...
def function_supposed_to_be_debugged():
   debugpy.debug_this_thread()
   ...
```
`debugpy.debug_this_thread()`must be added inside the function(s) running outside the main-thread that shall be debugged.

See the Visual Studio Code docs [here](https://code.visualstudio.com/docs/python/debugging#_troubleshooting) for more information.

### Running tests

Please make sure that the dependencies from `TEST` or `DEV` extra are installed.
Run the tests with `pytest` from within the `RodTracker` directory:
```shell
YOUR/REPO/PATH/RodTracker$ pytest
```

```{note}
Some tests require a display (see [pytest-qt](https://pytest-qt.readthedocs.io/en/latest/troubleshooting.html#tox-invocationerror-without-further-information))! Make sure the machine either has a screen connected or use [pytest-xvfb](https://pypi.org/project/pytest-xvfb/).
```

### Bundling the app

Please make sure that the dependencies of the `BUILD`, or `DEV` extra are installed. On Linux there are additional requirements to be able to run the bundling script. Refer to the [PyInstaller documentation](https://pyinstaller.org/en/stable/requirements.html#gnu-linux) for that.

There is a script to generate an executable for Windows, Linux, or macOS. Prior to bundling it will also (re-)build the documentation because this is supposed to be contained in the bundled app.

**On Windows**:
```bat
YOUR/REPO/PATH/RodTracker/build-files> build_app.bat
```
**On Linux & macOS**:
```shell
YOUR/REPO/PATH/RodTracker/build-files$ build_app.sh
```

The build script will generate a `.\RodTracker\build` and a `.\RodTracker\dist` folder.
The generated executables are located in the `.\RodTracker\dist` directory under either a `windows` or a `unix` subfolder.

Everything is bundled into one folder named `RodTracker`
which can be copied or moved as a whole. Run the executable inside this folder to start the program.
On macOS the generated folder is additionally converted into a `RodTracker.app` bundle that should be used to execute the RodTracker.
- (Windows) `dist\windows\RodTracker\RodTrackerApp.exe`
- (Linux) `dist/unix/RodTracker/RodTracker`
- (macOS) `dist/unix/RodTracker.app`

```{warning}
On Windows make sure that no other process, e.g. Dropbox, attempts to access files necessary for the build during this step. Otherwise an `OSError: [WinError 110]` might occur and break the process.

On Linux/macOS this problem does not seem to occur.
```

### Creating Installers
After it can be useful to create installers for easy distribution to the end user. The following scripts require the RodTracker to already be bundled as per the [previous section](#bundling-the-app).

**On Windows**:

An installer is created using [Inno Setup](https://jrsoftware.org/isinfo.php).
Use Inno Setup to compile the `.\RodTracker\build-files\build_installer.iss` script. This will create the installer file `.\RodTracker\dist\windows\RodTracker-Setup.exe` that can then be distributed.

**On Linux**:

`dpkg-deb` is used to create a `*.deb` package.
```shell
YOUR/REPO/PATH/RodTracker/build-files$ build_deb.sh
```

**On macOS**:

`create-dmg` is used to create a `*.dmg` installer.

0. Install `create-dmg`:
   ```shell
   brew install create-dmg
   ```
1. Create the installer:
   ```shell
   YOUR/REPO/PATH/RodTracker/build-files$ build_dmg.sh
   ```

## ParticleDetection

### Running tests
Please make sure that the dependencies from `TEST` extra are installed. Run the tests with `pytest` from within the `ParticleDetection` directory:
```shell
YOUR/REPO/PATH/ParticleDetection$ pytest
```

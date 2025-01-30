# RodTracker
This package provides a GUI encapsulating the most used functionality of the [ParticleDetection package](https://pypi.org/project/ParticleDetection/). It enables users to carry out the aforementioned tasks, except for training a model. Additionally, it provides the means to manually correct placement and assignment mistakes of the automated processes.

Please refer to the [documentation](https://particletracking.readthedocs.io/en/stable/RodTracker/RodTracker.html) for more detailed information.

## Installation

Refer to the [documentation](https://particletracking.readthedocs.io/en/stable/installation/rodtracker.html) for more details on the installation process.

### Installation as a standalone program

Use the provided executable installer for your operating system provided in the [repository releases](https://github.com/ANP-Granular/ParticleTracking/releases):
- `RodTracker-Setup.exe` - Windows
- `RodTracker-Setup.deb` - Linux
- `RodTracker-Setup.dmg` - macOS

**Note:** There might not always be a version provided for macOS.

### Installation as a python package
**Requirements:**
- Python `>=3.8`
- pip

Install the default version using pip:
```shell
pip install RodTracker
```
Or use one of the options described in the [documentation](https://particletracking.readthedocs.io/en/stable/installation/rodtracker.html#installation-options).
```shell
pip install RodTracker[OPTION]
```

Install it from source by:
1. Cloning the [repository](https://github.com/ANP-Granular/ParticleTracking) containing the RodTracker. Do **NOT** just copy the `RodTracker` folder. This will lead to a missing dependency during the installation.
2. Install it using `pip`.
   ```shell
   YOUR/REPO/PATH/RodTracker$ pip install .
   ```

It is also possible to install it directly from GitHub (requires `Git` to be installed):
```shell
pip install 'git+https://github.com/ANP-Granular/ParticleTracking.git#egg=rodtracker&subdirectory=RodTracker'
```
```shell
pip install 'rodtracker[DOCS] @ git+https://github.com/ANP-Granular/ParticleTracking.git#egg=RodTracker&s
ubdirectory=RodTracker'
```

## Running the RodTracker
Run the **RodTracker** GUI using one of the possibilities:
  - *(Standalone Program)* Run the executable installed by the installer.
  - *(Python Package)* Run `main.py` manually:
    ```shell
    YOUR/REPO/PATH/RodTracker/src/RodTracker$ python main.py
    ```
  - *(Python Package)* Run the GUI script entry point:
    ```shell
    ARBITRARY/PATH$ RodTracker
    ```

![RodTracker - GUI](https://raw.githubusercontent.com/ANP-Granular/ParticleTracking/main/docs/source/images/Startup.png)

## Keyboard shortcuts
| Feature                      |                   Shortcut                   |
|:-----------------------------|:--------------------------------------------:|
| Open images                  |                  `Ctrl + O`                  |
| Save rod position data       |                  `Ctrl + S`                  |
| Switch to next/previous view |                  `Ctrl+Tab`                  |
| Zoom in/out                  |      `+`/`-`  <br /> `Ctrl+Wheel`            |
| Fit image to available space | `F` |
| Show in original size        |                  `Ctrl + R`                  |
| Next/previous image          |                `Right`/`Left`                |
| Undo                         |                  `Ctrl + Z`                  |
| Lengthen/Shorten a rod       |                    `A`/`S`                   |
| Lengthen/Shorten all rods in current view    |    `R`/`T`                   |
| Delete a selected rod | `Del` |
| Toggle automatic rod selection mode | `G` |

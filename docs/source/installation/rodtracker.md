# Installation of the RodTracker
As the RodTracker is a Python package usually you will be installing it from source or from a `*.whl` file, but there is also the possibility, that you are provided with a bundled standalone version. This is either done as an executable installer (`RodTracker-Setup.exe` - Windows, `RodTracker-Setup.deb` - Linux, `RodTracker-Setup.dmg` - MacOS) or as folder from which the `RodTrackerApp` executable runs the RodTracker.

The following installation instructions are only concerning installing the RodTracker from source.

## Installation from source

**Requirements:**
- Python `>=3.8` is installed
- pip `!=22` is installed (see [this issue](https://github.com/pypa/pip/issues/10851) for explanation)
- Git is installed
- It is strongly recommended to install RodTracker from a fresh virtual environment (created with `venv`)
---

0. Upgrade your version of `pip`.
  ```shell
  python -m pip install --upgrade pip
  ```
1. Clone the [repository](https://github.com/ANP-Granular/ParticleTracking) containing the RodTracker. Do **NOT** just copy the `RodTracker` folder. This will lead to a missing dependency during the installation.
2. Install it using `pip`.
  ```shell
  YOUR/REPO/PATH/RodTracker$ pip install .
  ```
### Installation in conda environments
1. Create a fresh conda environment with Python `>=3.8`
  ```shell
  (base) YOUR/CURRENT/DIRECTORY$ conda create -n RodTracker python=3.10
          ...
  (base) YOUR/CURRENT/DIRECTORY$
  ```
2. Activate the just created environment.
  ```bash
  (base) YOUR/CURRENT/DIRECTORY$ conda activate RodTracker
  (RodTracker) YOUR/CURRENT/DIRECTORY$
  ```
3. Follow the instructions in [Install from source](#installation-from-source)

```{important}
Do **NOT** use conda to install/upgrade any packages that the RodTracker software uses. Make sure, that any packages additionally installed with conda have no interaction with the RodTracker software.

Refer to conda's [interoperatbility feature](https://docs.conda.io/projects/conda/en/latest/user-guide/configuration/pip-interoperability.html?highlight=conda%20pip), this [Anaconda blog post](https://www.anaconda.com/blog/using-pip-in-a-conda-environment) and issue [#59](https://github.com/ANP-Granular/ParticleTracking/issues/59) for more information on the topic.
```

## Installation options
In addition to the *user*/*default* installation there are four more options (mostly for developers) to choose from. They can be installed with pip using the `extras` feature, e.g.
```shell
pip install -e .[BUILD]
```
Please remember to install in *editable* mode when attempting to change any functionality of the RodTracker.

- **`GPU`:**
  - installs dependencies necessary to run particle detections using the GPU

- **`DEV`:**
  - intended to install all dependencies necessary or useful for the development of RodTracker
  - this will install all dependencies from the other extras as well

- **`DOCS`:**
   - intended for building/extending the documentation

- **`BUILD`:**
  - intended for building a bundled version of the RodTracker
  - this will also install dependencies from `DOCS` as building the documentation is a required step during the bundling process

- **`TEST`:**
  - intended for running (or developing) the tests of the RodTracker
  - it is recommended to install the `DEV` extra if one intends to change the tests


```{hint}
Please remember to install in *editable* mode when attempting to change any functionality of the RodTracker.
It might also make sense to install `ParticleDetection` in editable mode, which is **NOT** automatically done when installing `RodTracker` in editable mode. Simply reinstall `ParticleDetection` in editable mode **after** installing `RodTracker`.
Refer to its [installation instructions](particledetection.md) for that.
```

## Installation with GPU support
On Linux the default installation allows running particle detections on a GPU, if an appropriate detection model is selected and no further actions are required.

On Windows the default installation only allows running particle detections on a CPU. This is due to the default behavior of PyTorch and the more complex installation process of CUDA on Windows.
Please install CUDA first and then install the RodTracker with the extra `GPU`.

```{note}
CUDA is currently not available on Mac and therefore also not supported here.
```

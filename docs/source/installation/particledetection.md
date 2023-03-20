# Installation of ParticleDetection
**Requirement:** Python `>=3.8` is installed
## Installation from source
1. Clone the [repository](https://github.com/ANP-Granular/Track_Gui) containing the ParticleDetection package or only download the `ParticleDetection` folder, if you are not interested in the RodTracker application.
2. Install it using pip
  ```shell
  YOUR/REPO/PATH/ParticleDetection$ pip install .
  ```
3. Or install a specific option using pip
  ```shell
  YOUR/REPO/PATH/ParticleDetection$ pip install .[OPTION]
  ```
## Installation options
This package has three functionality options to be installed. These are realized as `extras` but are essentially variants, that do not necessarily built upon each other.

- `CPU`:
  - is the **default**
  - attempts to install the CPU version of `pytorch`
  - no Detectron2 installation
    - the `ParticleDetection.modelling` module is not usable
  - allows to run exported detection model on the CPU only
- `GPU`:
  - **Requirement:** CUDA is installed
  - attempts to install the CUDA/GPU version of `pytorch`
  - no Detectron2 installation
    - the `ParticleDetection.modelling` module is not usable
  - allows to run exported detection models on the CPU and GPU
- `DETECTRON`:
  - **Requirement:** CUDA is installed
  - attempts to install the CUDA/GPU version of `pytorch` 
  - attempts to install Detectron2
  - allows to train/run/export new Detectron2 models
  - allows to run exported detection models on the CPU and GPU
  ```{Admonition} Troubleshooting
  There have been problems during the use of `tensorboard` that could be used by the additional dependencies below. These have not been observed on all machines though.
    - change the `protobuf` version to 3.20.1
        ```shell
        pip install protobuf==3.20.1
        ```
    - install Shapely 
        ```shell
        pip install shapely 
        ```
    - refer to the [Detectron2 Installation Guide](https://detectron2.readthedocs.io/en/latest/tutorials/install.html) and the [PyTorch Get Started Page](https://pytorch.org/get-started/locally/)
  ```
- `TEST`:
  - intended for running (or developing) tests for the package
  - must be installed in addition to one of the other `extras`

```{Warning}
Detection models exported with GPU support enabled will not work with a CPU-only installation.
```

### Behavior on Linux

On Linux the `GPU` version of this package will be installed by default. It is not necessary to manually install CUDA before this installation.
If one decides afterwards, that the extended functionality of training new networks is necessary, a simple reinstallation with the `DETECTRON` extra is needed.

The installation of the `CPU` version might not work out-of-the-box and will most likely require manual installation of the required dependencies.
1. Install any version of ParticleDetection
2. Uninstall any GPU enabled version of torch, torchaudio, and torchvision
3. Clear the cache of pip to avoid reinstalling the same packages.
4. Install your systems CPU-only version of torch, torchaudio, and torchvision (see the [PyTorch Website](https://pytorch.org/get-started/locally/)).


### Behavior on Windows

On Windows the `CPU` version of this package will be installed by default. This is due to the default behavior of PyTorch and the more complex installation process of CUDA on Windows.
If GPU support is necessary on a Windows machine the requirements of the `GPU` version must be manually installed.
0. Install CUDA on the machine.
1. Install the default version of ParticleDetection.
2. Uninstall any CPU-only version(s) of torch, torchaudio and torchvision
3. Clear the cache of pip to avoid reinstalling the same packages.
4. Install your systems GPU version of torch, torchaudio and torchvision, that matches the installed CUDA version (see the [PyTorch Website](https://pytorch.org/get-started/locally/))

The `DETECTRON` version is not available on Windows because Detectron2 does not support an installation on Windows.


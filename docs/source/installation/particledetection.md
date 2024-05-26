# Installation of ParticleDetection

**Requirements:**
- Python `>=3.8` is installed
- pip `!=22` is installed (see [this issue](https://github.com/pypa/pip/issues/10851) for explanation)

## (Regular) Installation
Install the default version using pip:
```shell
pip install ParticleDetection
```
Or use one of the options described [below](#installation-options). **Some options require manual installation of additional libraries.**
```shell
pip install ParticleDetection[OPTION]
```

## Installation from source
0. Upgrade your version of `pip`.
   ```shell
   python -m pip install --upgrade pip
   ```
1. Clone the [repository](https://github.com/ANP-Granular/ParticleTracking) containing the ParticleDetection package or only download the `ParticleDetection` folder, if you are not interested in the RodTracker application.
2. Install it using pip
  ```shell
  YOUR/REPO/PATH/ParticleDetection$ pip install .
  ```
3. Or install a specific option using pip
  ```shell
  YOUR/REPO/PATH/ParticleDetection$ pip install .[OPTION]
  ```

Or install it directly from GitHub:
```shell
pip install 'git+https://github.com/ANP-Granular/ParticleTracking.git#egg=particledetection&subdirectory=ParticleDetection'
```
```shell
pip install 'particledetection[DETECTRON] @ git+https://github.com/ANP-Granular/ParticleTracking.git#egg=
particledetection&subdirectory=ParticleDetection'
```

## Installation options
This package has two functionality options. The default version is only intended to use (and potentially evaluate the performance of) object detection models previously created with for use with PyTorch. This means that the `Particle.modelling` module is not usable.

- `default`:
  - **Requirement:** /
  - **Post-Installation-Step(s):** /
  - allows running exported detection models on the CPU/GPU
  ```{Note}
  Depending on the OS only a CPU enabled version of `torch` is installed by default.
  Please refer to the `DETECTRON` extra for the steps necessary to enable use of the GPU.
  ```

- `DETECTRON`:
  - **Requirement:** CUDA is installed
  - **Post-Installation-Step(s):**
    - install Detectron2 as per their [Installation Guide](https://detectron2.readthedocs.io/en/latest/tutorials/install.html)
    - install [imgaug](https://imgaug.readthedocs.io/en/latest/) in the version shown below:
    ```shell
    pip install "https://github.com/aleju/imgaug.git@0101108d4fed06bc5056c4a03e2bcb0216dac326"
    ```
    - Verify, that the installed version of `torch`, `torchvision`, and `torchaudio` match your installed version of CUDA. Use the [PyTorch website](https://pytorch.org/get-started/locally/) to find a version that fits your system.
      ```{Hint}
      On Windows only the CPU version is installed by default.

      On Linux a GPU enabled version is installed by default, but CUDA version it uses changes occasionally.

      A GPU enabled version is not available on Mac.
      ```
  - allows training/running/exporting new Detectron2 models (see the `ParticleDetection.modelling` module)
  - allows running exported detection models on the CPU and GPU
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
  ```
- `TEST`:
  - intended for running (or developing) tests for the package

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

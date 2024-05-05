# Particle Detection
This repository customizes the training, inference and visualization code of the **Detectron2** framework to accurately detect rod-like particles. It additionally provides functionality to track these detected particles over multiple frames and reconstruct 3D representations of these observed granular gases.

![Rod Detection Output Image](https://user-images.githubusercontent.com/34780470/214838680-4474e35c-4277-4ac9-8649-3940aa122eeb.jpg)

Please refer to the [documentation](https://particletracking.readthedocs.io/en/stable/index.html) for more detailed information.

## Installation
Install the default version using pip:
```shell
pip install ParticleDetection
```
Or use one of the options described in the [documentation](https://particletracking.readthedocs.io/en/stable/installation/particledetection.html). **Some options require manual installation of additional libraries.**
```shell
pip install ParticleDetection[OPTION]
```

It is also possible to install it directly from GitHub:
```shell
pip install 'git+https://github.com/ANP-Granular/ParticleTracking.git#egg=particledetection&subdirectory=ParticleDetection'
```
```shell
pip install 'particledetection[DETECTRON] @ git+https://github.com/ANP-Granular/ParticleTracking.git#egg=
particledetection&subdirectory=ParticleDetection'
```

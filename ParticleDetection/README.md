# Particle Detection
This repository customizes the training, inference and visualization code of the **Detectron2** framework to accurately detect rod-like particles. It additionally provides functionality to track these detected particles over multiple frames and reconstruct 3D representations of these observed granular gases.

Use it like any other python package, by installing it in your environment and
then importing it in your scripts/modules/functions.
```python
import ParticleDetection.utils.helper_funcs as hf
```

Please refer to the [documentation](https://particletracking.readthedocs.io/) for more detailed information.

## Installation
1. Clone the [repository](https://github.com/ANP-Granular/ParticleTracking) containing the ParticleDetection package or only download the `ParticleDetection` folder, if you are not interested in the RodTracker application.
2. Install it using pip
  ```shell
  YOUR/REPO/PATH/ParticleDetection$ pip install .
  ```
3. Or install a specific option using pip
  ```shell
  YOUR/REPO/PATH/ParticleDetection$ pip install .[OPTION]
  ```

![Rod Detection Output Image](https://user-images.githubusercontent.com/34780470/214838680-4474e35c-4277-4ac9-8649-3940aa122eeb.jpg)

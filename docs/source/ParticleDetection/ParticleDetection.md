# ParticleDetection

<mark>This section needs extension/correction!</mark>

This repository customizes the training, inference and visualization code of the **Detectron2** framework to accurately detect rod-like particles. It additionally provides functionality t match and track the detected particles over multiple frames and reconstruct 3D representations of the particle ensembles (granular gases).

Use it like any other python package, by installing it in your environment and
then importing it in your scripts/modules/functions.
```python
import ParticleDetection.utils.helper_funcs as hf
```

## Model training

<mark>This section needs extension/correction!</mark>

### Visualization of training metrics using TensorBoard
Run the following command for training data visualization with TensorBoard:
```shell
tensorboard --logdir "path\to\output\folder(s)"
```

### Rod Detection

<mark>This section needs extension/correction!</mark>

This experiment trains an object detection network for 8 classes of rods, 
distinguished by their color. The c4m dataset was used.
The procedure is an extended version of a previously used network that has been implemented using the Matterport implementation of the mask RCNN network architecture.
Instead of the standard mask head, this network uses a PointRend network for the segmentation mask generation.
![Rod Detection Output Image](https://user-images.githubusercontent.com/34780470/214838680-4474e35c-4277-4ac9-8649-3940aa122eeb.jpg)


## 3D-Reconstruction

<mark>This section needs extension/correction!</mark>

### Output file format & naming conventions
Rod Endpoint files after detection:
- file names: {image name}_{rod color}.mat
- content:
  - variables: rod_data_links
  - dimensions: [color, rod, point, coordinate]
  - [-1, -1], if no endpoints can be computed for a mask/rod


Rod Endpoint files after matching:
- file names: data3d_{color}/{frame:05d}.txt
- content:
  - `' '` separated
  - {x1} {y1} {z1} {x2} {y2} {z2} {x} {y} {z} {l} {x1_cam1} {y1_cam1} {x2_cam1} 
    {y2_cam1} {x1_cam2} {y1_cam2} {x2_cam2} {y2_cam2} {frame}\n


Rod Endpoint files after tracking:
- file names: 
- content:
  - `','` separated
  - {idx},{x1},{y1},{z1},{x2},{y2},{z2},{x},{y},{z},{l},{x1_cam1},{y1_cam1},
    {x2_cam1},{y2_cam1},{x1_cam2},{y1_cam2},{x2_cam2},{y2_cam2},{frame},
    {seen_cam1},{seen_cam2},{particle}\n
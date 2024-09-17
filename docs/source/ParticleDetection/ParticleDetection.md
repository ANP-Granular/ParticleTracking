# ParticleDetection

ParticleDetection is a library for detecting and tracking particles in stereo-camera images. For this it customizes the training, inference and visualization functionalities of the [**Detectron2**](https://detectron2.readthedocs.io/en/latest/) framework. It additionally provides functionality to track these detected particles over multiple frames and reconstruct 3D representations.
The main focus here is to enable the (semi-)automatic data extraction from microgravity experiments with granular gases. In these experiments many particles float and interact in space.
Different shapes can be chosen for these particles, but for now the library is focused on rod-like particles. It is planned to include multiple shapes in later versions.

This repository customizes the training, inference and visualization code of the **Detectron2** framework to accurately detect rod-like particles. It additionally provides functionality to match and track the detected particles over multiple frames and reconstruct 3D representations of the particle ensembles (granular gases).


## Model training

For automatic detection of particles a model must be trained. Here we focus on training a R-CNN network that will yield segmentation masks and class predictions.


### Training dataset

For the training process at least two datasets are required, one for the actual training and one for testing during training. An additional validation dataset is not enforced by this package.
These datasets consist of image files (`*.jpg`, `*.jpeg`, `*.png`) and a metadata file in `json` format.
The metadata describes the particles on each image, that shall be detectable by the network to train. Each of these particles therefore needs a polygon defining its extent in the image and a class. The classes must be integers, e.g. class `1` are `thick, red rods`.

**Example metadata file:**
```json
{
  "arbitrary_id0": {
    "filename": "file0.jpg",
    "regions":
      [
        {
          "shape_attributes": {
            "name": "polygon",
            "all_points_x": [0, 1, 2, 3],
            "all_points_y": [0, 1, 2, 3],
            },
          "region_attributes": {
            "rod_col": "class_number"
          }
        },
        {"..."},
      ]
  },
  "arbitrary_id1": {"..."},
  "arbitrary_id2": {"..."},
}
```
See also [`load_custom_data`](../ParticleDetection-api/modelling/datasets.rst) for more information on what the resulting format is.

### Training

The script below shows part of a training procedure used to train a model for rod detection. It shows how to start with a pre-trained network and then adapting it to the specific use-case. It shows how a multi-stage training process can be realized and what configurations might be necessary to adjust. Within this it is shown how to further train only certain portions of the model while keeping the state of others fixed.
To learn more about different model settings used here, refer to the [Detectron2 documentation](https://detectron2.readthedocs.io/en/latest/modules/config.html#yaml-config-references).

```{literalinclude} training_example.py
:emphasize-lines: 42, 43, 64-77, 111, 121-123, 151, 154-156, 170
:caption: Example training script
```
The `init_cfg()` function, as the name suggests, initializes the configuration object for the network. For this it loads a `*.yaml` file with previously prepared configurations, e.g. a default configuration obtained from Detectron2.
Individual values of this configuration are then adjusted further. Additionally, a list of image augmentations to be used during training is generated.

The first training step is then performed in `train_heads()`. Here the initialized configuration is modified further, i.e. to freeze certain layers in the model for this training step. Furthermore, the model weights are set, here by inserting those from a pre-trained network. If parts of the new model's layers differ from those of the pre-trained one, only the matching layers will be given the pre-trained weights.

The last shown step performed by `train_all_s1()` is another model training step. Here, the final weights from `train_heads()` are taken and this time the whole network is trained.

The end result is a `model_final.pth` file containing the trained weights and the `configuration.yaml` file containing the model structure. Together they can be used to obtain particle segmentations in new images.

  ```{note}
  If you are using extensions to the default Detectron2 models, e.g. the PointRend project, it is necessary to import/register those before loading the model (configuration).
  For the extensions from the Detectron2 projects this can usually be done by importing their module:
    ```python
    from detectron2.projects import point_rend
    ```
  ```

### Visualization of training metrics using TensorBoard
During training logs are written to allow the supervision of the training process. These logs contain key performance indicators of the current model state and can be visualized with TensorBoard during and after the training.
Run the following command for training data visualization with TensorBoard:
```shell
tensorboard --logdir "path\to\output\folder(s)"
```

### Exporting of a trained model

It might be required to transfer the trained model(s) to systems that cannot install Detectron2, i.e. Windows computers, or to an environment that should be kept as lean as possible. For these instances the models can be exported to a format that can be directly read and used by `torch`.
The [RodTracker](../RodTracker/RodTracker.md) also uses only the exported version of the models.

```{literalinclude} export_example.py
:caption: Example model exporting script
```

  ```{note}
  If you are using extensions to the default Detectron2 models, e.g. the PointRend project, it is necessary to import/register those before loading the model (configuration).
  For the extensions from the Detectron2 projects this can usually be done by importing their module:
    ```python
    from detectron2.projects import point_rend
    ```
  ```

## Particle Detection

The trained model is now used to detect the trained classes of objects/particles as shown in the image below.
```{figure} https://user-images.githubusercontent.com/34780470/214838680-4474e35c-4277-4ac9-8649-3940aa122eeb.jpg

Visualized detection result
```
The model, that produced the image, was trained with an extended version of the script shown above with a last step exchanging the standard mask head with a PointRend network for the segmentation mask generation.

The detected particles in this image are given as a border around their returned segmentation mask with the border color indicating the object class. Additionally, the confidence score for each of the detected particles is plotted. Note, that the border colors are arbitrarily chosen and do not correspond with the title of the particle classes, i.e. rod colors.

An example script on how to run detections with an exported model is given below. Please refer to [ParticleDetection.modelling.runners.detection](../ParticleDetection-api/modelling/runners.rst) for how to run models from their `model_final.pth` and `configuration.yaml` files without prior exporting.
The script below assumes a working folder that contains the following image file containing folders obtained from a stereo-camera setup:

```{code-block}
:caption: Working folder structur

|.
├── your_images
│    ├── gp1
│    │   ├── 0001.jpg
│    │   ├── 0002.jpg
│    │   ...
│    │   └── 0321.jpg
│    └── gp2
│        ├── 0001.jpg
│        ├── 0002.jpg
│        ...
│        └── 0321.jpg
├── your_model
│    └── model_cuda.pt
└── your_output
     └── ...
```


```{literalinclude} detection_example.py
:caption: Detection example script
:name: detection_example_script
:emphasize-lines: 19
```

```{eval-rst}
.. note::

  #. The output might contain particles from classes that are not actually present. Select only the classes that are known to be present in the images to avoid problems.

  #. Not all particles might be detected by the network. Make sure, that 'dummy' particles are inserted instead of missing ones, to avoid problems in the tracking step. See :func:`ParticleDetection.utils.helper_funcs.rod_endpoints` on how to define expected amounts of particles per frame.
```

This script yields multiple `*.csv` files in the `your_output` directory. Each detected particle class is saved to a `rods_df_{classname}.csv` file, e.g. `rods_df_red.csv` with all particles saved to `rods_df.csv`. From the detected segmentation masks two endpoints were generated, that will represent the rod from now on.
Below you can see the structure of these files:
```{csv-table} Detection Output File
idx,x1,y1,z1,x2,y2,z2,x,y,z,l,x1_**cam1**,y1_**cam1**,x2_**cam1**,y2_**cam1**,x1_**cam2**,y1_**cam2**,x2_**cam2**,y2_**cam2**,seen_**cam1**,seen_**cam2**,particle,frame,(*color*)
/,`NaN`,`NaN`,`NaN`,`NaN`,`NaN`,`NaN`,`NaN`,`NaN`,`NaN`,`NaN`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`bool`,`bool`,`int`,`int`,(*`str`*)
```
Only 2D data is extracted here, so the columns reserved for 3D data, generated by the steps described in the next section, are set to `Nan`, i.e. are empty.
```{note}
These files can be used with the RodTracker.
```


## 3D-Reconstruction

The reconstruction of 3D coordinates works by associating particles detected in the first camera with ones in the second camera. For that each of the detected particle is given an ID (a number) and has two endpoints on each camera and each frame. The tracking functions are then used to reassign the IDs such that a combination of particles on camera one and two is found, that minimizes the reprojection error of their calculated 3D coordinates.

### Camera Calibration

For the reconstruction of 3D points a correspondence between points in the first and second camera's images must be known. Please refer to the [OpenCV documentation](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html) for more information.

```{literalinclude} calibration_example.py
:caption: Camera calibration example
```

### World vs. Camera coordinates

<mark>This section needs extension/correction!</mark>

### Tracking

With the calibration data from above it is now possible to reconstruct the 3D positions of the detected particles. Additionally, the function used in the script below tracks the objects over the given frames, reassigning particle IDs where necessary.
The function here requires the output `*.csv` files from the {ref}`detection_example_script`.


```{literalinclude} tracking_example.py
:caption: Example particle tracking script
```

The output are `*.csv` files similar to those given by {ref}`detection <detection_example_script>`. The only difference are the now filled columns with 3D coordinates:
```{csv-table} Tracking/Reconstruction Output File
idx,x1,y1,z1,x2,y2,z2,x,y,z,l,x1_**cam1**,y1_**cam1**,x2_**cam1**,y2_**cam1**,x1_**cam2**,y1_**cam2**,x2_**cam2**,y2_**cam2**,seen_**cam1**,seen_**cam2**,particle,frame,(*color*)
/,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`float`,`bool`,`bool`,`int`,`int`,(*`str`*)
```
```{note}
These files can be used with the RodTracker.
```

# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev
#
# This file is part of ParticleDetection.
# ParticleDetection is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ParticleDetection is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ParticleDetection. If not, see <http://www.gnu.org/licenses/>.

"""
Functions to run inference with a trained network and save the results for
further computations.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       11.08.2022

"""
import logging
import os
import random
import warnings
from pathlib import Path
from typing import Callable, Iterable, List, Literal, Union, overload

import cv2
import numpy as np
from detectron2.config import CfgNode
from detectron2.engine import DefaultPredictor
from detectron2.utils.logger import setup_logger

import ParticleDetection.modelling.export as export
import ParticleDetection.modelling.visualization as visualization
import ParticleDetection.utils.datasets as ds
from ParticleDetection.modelling.configs import write_configs

_logger = logging.getLogger(__name__)


SavingFunction = Callable[
    [ds.DetectionResult, Union[Path, str, np.ndarray], dict, Union[Path, str]],
    None,
]
"""Minimal signature for a function intended for saving
:data:`~ParticleDetection.utils.datasets.DetectionResult`.

See also
--------
:func:`~ParticleDetection.modelling.export.annotation_to_json`,
:func:`~ParticleDetection.modelling.export.rods_to_csv`,
:func:`~ParticleDetection.modelling.export.rods_to_mat`
"""


@overload
def detect(
    dataset: Union[
        str,
        Path,
        np.ndarray,
        ds.DataSet,
        Iterable[str],
        Iterable[Path],
        Iterable[np.ndarray],
    ],
    configuration: Union[CfgNode, str, Path],
    weights: Union[str, Path],
    **kwargs,
) -> None:
    # Minimal version
    ...


@overload
def detect(
    dataset: Union[
        str,
        Path,
        np.ndarray,
        ds.DataSet,
        Iterable[str],
        Iterable[Path],
        Iterable[np.ndarray],
    ],
    configuration: Union[CfgNode, str, Path],
    weights: Union[str, Path],
    classes: dict = {},
    output_dir: Union[str, Path] = Path.cwd(),
    threshold: float = 0.5,
    saving_functions: Iterable[SavingFunction] = [],
    **kwargs,
) -> None:
    # Mostly intended function use.
    ...


@overload
def detect(
    dataset: str,
    configuration: Union[CfgNode, str, Path],
    weights: Union[Path, str],
    frames: List[int],
    cam1_name: str,
    cam2_name: str,
    **kwargs,
) -> None:
    # Datasetformat version. Requires the dataset string to be 'formattable'.
    ...


def detect(
    dataset: Union[
        str,
        Path,
        np.ndarray,
        ds.DataSet,
        Iterable[str],
        Iterable[Path],
        Iterable[np.ndarray],
    ],
    configuration: Union[CfgNode, str, Path],
    weights: Union[Path, str],
    classes: dict = {},
    output_dir: Union[str, Path] = Path.cwd(),
    threshold: float = 0.5,
    saving_functions: Iterable[SavingFunction] = [],
    log_name: str = "detection.log",
    visualize: bool = False,
    vis_random_samples: int = -1,
    device: Literal["cpu", "cuda"] = "cpu",
    **kwargs,
) -> None:
    """Run object detection on a dataset with custom result saving.

    Run object detection on a given dataset with the possibility to visualize
    all or some results. Additionally, it is possible to apply (custom) saving
    functions to the detection result of each given image. The detection can be
    run either on the CPU or GPU.

    Parameters
    ----------
    dataset : Union[str, Path, np.ndarray, ds.DataSet, Iterable[str], Iterable[Path], Iterable[np.ndarray]]
        The data(set) on which object detection will be run. This can be a
        collection of paths to image files or already loaded images. Already
        loaded images are expected to be in BGR format.
        The use of a :class:`~ParticleDetection.utils.datasets.DataSet`
        already registered to the Detectron2 framework is also possible.
    configuration : Union[CfgNode, str, Path]
        Configuration for the Detectron2 model and inferences settings given
        as a ``CfgNode`` or path to a ``*.yaml`` file in the Detectron2
        configuration format.
    weights : Union[Path, str]
        Path to a ``*.pth`` model file, e.g. "model_final.pth".
    classes : dict
        Dictionary of classes detectable by the model with\n
        ``{key}``  ->  Index of class in the model\n
        ``{value}`` ->  Name of the class\n
        By default ``{}``.
    output_dir : Union[str, Path], optional
        Path to the intended output directory. It's parent directory must
        exist prior to running this function.\n
        By default ``Path.cwd()``.
    threshold : float, optional
        Threshold for the minimum score of predicted instances.\n
        By default ``0.5``.
    saving_functions : Iterable[:data:`.SavingFunction`], optional
        Threshold for the minimum score of predicted instances.\n
        By default ``[]``.
    log_name : str, optional
        Filename for logging output in the output directory.\n
        By default ``"detection.log"``.
    visualize : bool, optional
        Flag for allowing visualization.\n
        By default ``False``.
    vis_Specifies the number of randomly chosen visualized samples when
        ``visualize`` is ``True``.\n
        ``-1``   -> All images are viszalized.\n
        ``n > 0``-> Chooses ``n`` images of the given set to be visualized
        after inference.\n
        By default ``-1``, i.e. use all images for visualization.
    device : Literal["cpu", "cuda"], optional
        Device the detection is going to be run with, i.e. CPU or GPU.\n
        By default ``"cpu"``.
    **kwargs : dict, optional
        The `dataset` parameter can accept formattable strings, i.e.
        `dataset.format(...)` can be run. This allows to specify a dataset
        using the following keywords that are going to be inserted using
        string formatting. For this the string must contain a ``frame`` and a
        ``cam_id`` field that can be formatted. See the Examples section for
        more information.\n
        `frames` : List[int]
            A list of frames, that shall be used for rod detection.\n
            By default ``[]``
        `cam1_name` : str
            The name/ID of the first camera in the experiment. This name will
            be used for image discovery (see ``dataset_format``) and naming of
            the output ``*.csv`` file's columns.\n
            By default ``""``.
        `cam2_name` : str
            The name/ID of the second camera in the experiment. This name will
            be used for image discovery (see ``dataset_format``) and naming of
            the output ``*.csv`` file's columns.\n
            By default ``""``.

        Additional keyword arguments can be inserted here, that shall be
        available in the given ``saving_functions``, e.g. `method` for
        :func:`~ParticleDetection.modelling.export.rods_to_csv`.

    See also
    --------
    :func:`~ParticleDetection.modelling.export.rods_to_csv`,
    :func:`~ParticleDetection.modelling.export.rods_to_mat`,
    :func:`~ParticleDetection.modelling.export.annotation_to_json`
    :func:`~ParticleDetection.modelling.visualization.visualize`

    Examples
    --------
    **Default Use:**

    >>> detect(["file1.png", "file2.png"], "config.json", "weights.pth",
    ...        {0: "test_class", 1: "next_class"},
    ...        saving_functions=[export.annotations_to_json, ])

    **Dataset Format Use:**

    >>> detect("my/path/{cam_id:s}/experiment_{frame:05d}.png",
    ...        "config.json", "weights.pth",
    ...        frames = [1, 12], cam1_name = "test", cam2_name = "none")

    These settings yield the following files being used for inference:

    >>> ["my/path/test/experiment_00001.png",
    ...  "my/path/none/experiment_00001.png"
    ...  "my/path/test/experiment_00012.png",
    ...  "my/path/none/experiment_00012.png"]

    """  # noqa: E501
    setup_logger(output=os.path.join(str(output_dir), log_name))
    # Configuration
    if isinstance(configuration, str):
        cfg = CfgNode(CfgNode.load_yaml_with_base(configuration))
    else:
        cfg = configuration
    if weights is not None:
        cfg.MODEL.WEIGHTS = os.path.abspath(weights)
    cfg.MODEL.DEVICE = device
    write_configs(cfg, output_dir)

    predictor = DefaultPredictor(cfg)
    if classes is {}:
        classes = {
            i: str(i) for i in range(0, cfg.MODEL.ROI_HEADS.NUM_CLASSES)
        }

    # Handle a dataset given as a formattable string
    cam_1 = kwargs.get("cam1_name", None)
    cam_2 = kwargs.get("cam2_name", None)
    frames = kwargs.get("frames", None)
    if cam_1 is not None or cam_2 is not None or frames is not None:
        if isinstance(dataset, str):
            # Create iterator from dataset format for use in main loop
            formatted_dataset = []
            if frames is not None:
                if cam_1 is not None:
                    formatted_dataset.extend(
                        [
                            dataset.format(cam_id=cam_1, frame=frame)
                            for frame in frames
                        ]
                    )
                if cam_2 is not None:
                    formatted_dataset.extend(
                        [
                            dataset.format(cam_id=cam_2, frame=frame)
                            for frame in frames
                        ]
                    )
            else:
                if cam_1 is not None:
                    formatted_dataset.append(dataset.format(cam_id=cam_1))
                if cam_2 is not None:
                    formatted_dataset.append(dataset.format(cam_id=cam_2))

            # Addition of keyword necessary for the saving function of rods to
            # csv
            kwargs["dataset_format"] = dataset
            dataset = formatted_dataset
        else:
            warnings.warn(
                "The given 'dataset' must be of type 'str' to use "
                "the keywords 'cam_1', 'cam_2', 'frames'.",
                UserWarning,
            )

    # create Iterable for images
    if not isinstance(dataset, Iterable):
        dataset = [
            dataset,
        ]
    num_images = len(dataset)
    # Randomly select several samples to visualize the prediction results.
    to_visualize = np.zeros(num_images)
    if visualize:
        if vis_random_samples >= 0:
            samples = random.sample(
                range(0, len(to_visualize)), vis_random_samples
            )
            to_visualize[samples] = 1
        else:
            # visualize all
            to_visualize = np.ones(len(dataset))

    _logger.info(f"Starting inference on {num_images} file(s).")
    for image in dataset:
        file = image
        if not isinstance(image, np.ndarray):
            # read image
            if not Path(file).exists():
                warnings.warn(
                    "The following image is skipped because it "
                    f"does not exist: {file}",
                    UserWarning,
                )
                _logger.warning(
                    "The following image is skipped because it "
                    f"does not exist: {file}"
                )
                continue
            _logger.info(f"Inference on: {file}")
            image = cv2.imread(str(file))

        outputs = predictor(image)
        _logger.debug(f"Detected {len(outputs['instances'])} objects.")

        # Thresholding/cleaning results
        outputs["instances"] = outputs["instances"][
            outputs["instances"].scores > threshold
        ]
        _logger.info(f"Found {len(outputs['instances'])} valid objects.")

        # Save (intermediate) results
        for fun in saving_functions:
            fun(outputs, file, classes, output_dir, **kwargs)

        # Visualizations
        if visualize:
            visualization.visualize(
                outputs, file, output_dir=output_dir, **kwargs
            )


def run_detection(
    dataset: Union[ds.DataSet, List[str]],
    configuration: Union[CfgNode, str],
    weights: str = None,
    classes: dict = None,
    output_dir: str = "./",
    log_name: str = "detection.log",
    visualize: bool = True,
    vis_random_samples: int = -1,
    threshold: float = 0.5,
    **kwargs,
) -> list:
    """Runs inference on a given set of images and can visualize the output.

    In addition to running inference this script also generates rod endpoints
    from the generated masks, if the network predicted these.

    .. deprecated:: 0.4.0
        :func:`.run_detection` will be completely replaced by
        :func:`.detect` to allow more modular saving of data. Internally
        this function already uses :func:`.detect`.

    Parameters
    ----------
    dataset : Union[ds.DataSet, List[str]]
        Either a DataSet already registered to the Detectron2 framework or a
        list of paths to image files intended for running inference on.
    configuration : Union[CfgNode, str]
        Configuration for the Detectron2 model and inferences settings given as
        a CfgNode or path to a ``*.yaml`` file in the Detectron2 configuration
        format.
    weights : str, optional
        Path to a ``*.pth`` model file. Is optional, if the weights are already
        given in the configuration.
    classes : dict, optional
        Dictionary of classes detectable by the model with\n
        ``{key}``  ->  Index of class in the model\n
        ``{value}`` ->  Name of the class\n
        By default ``None``.
    output_dir : str, optional
        Path to the intended output directory. It's parent directory must exist
        prior to running this function.\n
        By default ``"./"``.
    log_name : str, optional
        Filename for logging output in the output directory.\n
        By default ``"detection.log"``.
    visualize : bool, optional
        Flag for allowing visualization.\n
        By default ``True``.
    vis_random_samples : int, optional
        Specifies the number of randomly chosen visualized samples when
        ``visualize`` is ``True``.\n
        ``-1``   -> All images are viszalized.\n
        ``n > 0``-> Chooses ``n`` images of the given set to be visualized
        after inference.\n
        By default ``-1``.
    threshold : float, optional
        Threshold for the minimum score of predicted instances.\n
        By default ``0.5``.
    **kwargs
        Keyword arguments for :func:`.visualization.visualize()`, except for
        ``prediction``, ``original``, and ``output_dir``.

    Returns
    -------
    list

    See also
    --------
    :func:`~ParticleDetection.modelling.export.rods_to_mat`
    """
    warnings.warn(
        "This function to output in a format for use in MATLAB is "
        "deprecated. Please use `detect()` with an appropriate "
        "saving function instead.",
        DeprecationWarning,
    )
    warnings.warn(
        "This function no longer returns the detection results. "
        "Instead an empty list [] is returned to not completely "
        "break older scripts.",
        UserWarning,
    )
    if classes is None:
        classes = {}
    saving_functions = [
        export.rods_to_mat,
    ]
    detect(
        dataset=dataset,
        configuration=configuration,
        weights=weights,
        classes=classes,
        output_dir=output_dir,
        threshold=threshold,
        log_name=log_name,
        visualize=visualize,
        saving_functions=saving_functions,
        vis_random_samples=vis_random_samples,
        **kwargs,
    )
    return []  # only for compatibility


def run_detection_csv(
    dataset_format: str,
    configuration: Union[CfgNode, str],
    weights: str = None,
    classes: dict = None,
    output_dir: str = "./",
    log_name: str = "detection.log",
    threshold: float = 0.5,
    frames: List[int] = [],
    cam1_name: str = "gp1",
    cam2_name: str = "gp2",
) -> None:
    """Runs inference on a given set of images and saves the output to a
    ``*.csv``.

    This function runs a rod detection on images and generates rod enpoints
    from the generated masks, if the network predicted these. Finally, these
    endpoints are saved to a single ``rods_df.csv`` file in the specified
    output folder.

    .. deprecated:: 0.4.0
        :func:`.run_detection_csv` will be completely replaced by
        :func:`.detect` to allow more modular saving of data. Internally
        this function already uses :func:`.detect`.

    Parameters
    ----------
    dataset_format : str
        String that can be formatted to specify the file locations of images,
        that shall be used for inference.
        For this the string must contain a ``frame`` and a ``cam_id`` field
        that can be formatted.\n
        Example:\n
        ``"my/dataset/path/{cam_id:s}/experiment_{frame:05d}.png"``
    configuration : Union[CfgNode, str]
        Configuration for the Detectron2 model and inferences settings given as
        a ``CfgNode`` or path to a ``*.yaml`` file in the Detectron2
        configuration format.
    weights : str, optional
        Path to a ``*.pth`` model file. Is optional, if the weights are already
        given in the configuration.
    classes : dict, optional
        Dictionary of classes detectable by the model with\n
        ``{key}``  ->  Index of class in the model\n
        ``{value}`` ->  Name of the class\n
        By default ``None``.
    output_dir : str, optional
        Path to the intended output directory. It's parent directory must exist
        prior to running this function.\n
        By default ``"./"``.
    log_name : str, optional
        Filename for logging output in the output directory.\n
        By default ``"detection.log"``.
    threshold : float, optional
        Threshold for the minimum score of predicted instances.\n
        By default ``0.5``.
    frames : List[int], optional
        A list of frames, that shall be used for rod detection.\n
        By default ``[]``.
    cam1_name : str, optional
        The name/ID of the first camera in the experiment. This name will be
        used for image discovery (see ``dataset_format``) and naming of the
        output ``*.csv`` file's columns.\n
        By default ``"gp1"``.
    cam2_name : str, optional
        The name/ID of the second camera in the experiment. This name will be
        used for image discovery (see ``dataset_format``) and naming of the
        output ``*.csv`` file's columns.\n
        By default ``"gp2"``.

    See also
    --------
    :func:`~ParticleDetection.modelling.export.rods_to_csv`
    """
    warnings.warn(
        "This function to output in format csv format is deprecated. "
        "Please use `detect()` with an appropriate saving function instead.",
        DeprecationWarning,
    )
    if classes is None:
        classes = {}

    if weights is None:
        warnings.warn(
            "The argument 'weights' is going to be a required " "argument!",
            DeprecationWarning,
        )
        if isinstance(configuration, str):
            cfg = CfgNode(CfgNode.load_yaml_with_base(configuration))
            weights = cfg.MODEL.WEIGHTS
        else:
            weights = configuration.MODEL.WEIGHTS

    saving_functions = [export.rods_to_csv]
    detect(
        dataset=dataset_format,
        configuration=configuration,
        weights=weights,
        classes=classes,
        output_dir=output_dir,
        threshold=threshold,
        saving_functions=saving_functions,
        log_name=log_name,
        frames=frames,
        cam1_name=cam1_name,
        cam2_name=cam2_name,
    )

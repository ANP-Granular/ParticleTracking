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
Function(s) to train a new model using the Detectron2 framework.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       10.08.2022

"""
import os
import pickle
import random
from typing import List, Union

import cv2
import detectron2.data.transforms as T
import matplotlib.pyplot as plt
import numpy as np
from detectron2.config import CfgNode
from detectron2.data import MetadataCatalog
from detectron2.utils.logger import setup_logger
from detectron2.utils.visualizer import Visualizer

import ParticleDetection.modelling.detectron as custom
import ParticleDetection.utils.datasets as ds
from ParticleDetection.modelling.configs import write_configs
from ParticleDetection.modelling.datasets import load_custom_data


def run_training(
    train_set: ds.DataSet,
    configuration: Union[str, CfgNode],
    val_set: ds.DataSet = None,
    output_dir: str = "./",
    log_name: str = "training.log",
    resume: bool = True,
    visualize: bool = False,
    img_augmentations: List[T.Augmentation] = None,
    freeze_layers: List[str] = None,
):
    """Runs the training of a model with the given training data.

    Runs the training of a model which is defined by the given configuration.
    The training can be resumed and further specification of layers to
    train/not to train is possible. During training the different model
    performance metrics are logged in the Tensorboard format.
    Additional COCO metrics are available only if a validation dataset is
    given. These metrics are also logged in the Tensorboard format.

    Parameters
    ----------
    train_set : DataSet
        A DataSet already registered to the Detectron2 framework, that is used
        for training the model.
    configuration : Union[str, CfgNode]
        Configuration for the Detectron2 model with training settings given as
        a ``CfgNode`` or path to a ``*.yaml`` file in the Detectron2
        configuration format.
    val_set : DataSet, optional
        A :class:`.DataSet` already registered to the Detectron2 framework,
        that is used for testing the model during training.\n
        By default ``None``.
    output_dir : str, optional
        Path to the intended output directory. It's parent directory must exist
        prior to running this function.\n
        By default ``"./"``.
    log_name : str, optional
        Filename for logging output in the output directory.\n
        By default ``"training.log"``.
    resume : bool, optional
        Flag to continue with previous training progress in the output
        folder.\n
        By default ``True``.
    visualize : bool, optional
        Flag for allowing visualization of one randomly selected image from the
        given training dataset with 10 randomly chosen annotations overlaid on
        the image.\n
        By default ``False``.
    img_augmentations : List[Augmentation], optional
        Image augmentations to be used during training.\n
        By default ``None``.
    freeze_layers : List[str], optional
        Layers/layer collections to be frozen during training. The model's
        layer names are obtained using ``model.named_parameters()``.\n
        By default ``None``.
    """

    setup_logger(os.path.join(output_dir, log_name))
    if visualize:
        # visualize annotations of randomly selected samples in the
        # training set
        meta_data = MetadataCatalog.get(train_set.name)
        dataset_dicts = load_custom_data(train_set)
        for d in random.sample(dataset_dicts, 1):
            img = cv2.imread(d["file_name"])
            visualizer = Visualizer(
                img[:, :, ::-1], metadata=meta_data, scale=0.5
            )
            d["annotations"] = random.sample(d["annotations"], 10)
            out = visualizer.draw_dataset_dict(d)
            plt.figure()
            plt.imshow(out.get_image()[:, :, ::-1])
            plt.show()

    resume_with_config = False
    # Try to load previously defined *.yaml configuration
    if resume:
        previous_config = os.path.join(output_dir, "config.yaml")
        previous_augment = os.path.join(output_dir, "augmentations.pkl")
        if os.path.exists(previous_config):
            configuration = CfgNode(
                CfgNode.load_yaml_with_base(previous_config)
            )
            resume_with_config = True
        if os.path.exists(previous_augment):
            with open(previous_augment, "rb") as f:
                img_augmentations = pickle.load(f)

    if not resume_with_config:
        # Load configuration, if needed
        if isinstance(configuration, str):
            configuration = CfgNode(CfgNode.load_yaml_with_base(configuration))

        # Adaptation/Double-checking the given configuration
        configuration.OUTPUT_DIR = os.path.abspath(output_dir)
        configuration.DATASETS.TRAIN = (train_set.name,)
        if val_set:
            if not configuration.DATASETS.TEST:
                configuration.DATASETS.TEST = (val_set.name,)
                # Determine the maximum number of instances to predict per
                # image
                counts = ds.get_object_counts(val_set)
                configuration.TEST.DETECTIONS_PER_IMAGE = int(
                    1.5 * np.max(counts)
                )
            elif not configuration.TEST.DETECTIONS_PER_IMAGE:
                # Determine the maximum number of instances to predict per
                # image
                counts = ds.get_object_counts(val_set)
                configuration.TEST.DETECTIONS_PER_IMAGE = int(
                    1.5 * np.max(counts)
                )

        # Create output directory and save configuration
        os.makedirs(output_dir, exist_ok=True)
        write_configs(configuration, output_dir, img_augmentations)

    # Training
    if img_augmentations:
        custom.CustomTrainer.augmentations = img_augmentations
    trainer = custom.CustomTrainer(configuration)

    # Freeze layers (prevent weight/bias updates, might not work for
    # decay/momentum)
    if freeze_layers:
        for layer, params in trainer.model.named_parameters():
            for to_freeze in freeze_layers:
                if to_freeze in layer:
                    params.requires_grad = False

    trainer.resume_or_load(resume=resume)
    trainer.train()

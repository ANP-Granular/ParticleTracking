"""Script to train a new model."""
# import general libraries
import os
import cv2
import random
import pickle
from typing import Union, List
import matplotlib.pyplot as plt
import numpy as np

# import detectron2 utilities
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog
from detectron2.utils.logger import setup_logger
from detectron2.config import CfgNode
import detectron2.data.transforms as T

# import custom code
from utils.datasets import load_custom_data
from utils import datasets as ds
import utils.custom_detectron as custom
import utils.helper_funcs as hf


def run_training(train_set: ds.DataSet,
                 configuration: Union[str, CfgNode],
                 val_set: ds.DataSet = None,
                 output_dir: str = "./", log_name: str = "training.log",
                 resume: bool = True, visualize: bool = False,
                 img_augmentations: List[T.Augmentation] = None,
                 freeze_layers: List[str] = None):

    setup_logger(os.path.join(output_dir, log_name))
    if visualize:
        # visualize annotations of randomly selected samples in the training set
        meta_data = MetadataCatalog.get(train_set.name)
        dataset_dicts = load_custom_data(train_set)
        for d in random.sample(dataset_dicts, 1):
            img = cv2.imread(d["file_name"])
            visualizer = Visualizer(img[:, :, ::-1], metadata=meta_data, scale=0.5)
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
            configuration = CfgNode(CfgNode.load_yaml_with_base(
                previous_config))
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
                # Determine the maximum number of instances to predict per image
                counts = hf.get_object_counts(val_set)
                configuration.TEST.DETECTIONS_PER_IMAGE = int(np.max(counts))
            elif not configuration.TEST.DETECTIONS_PER_IMAGE:
                # Determine the maximum number of instances to predict per image
                counts = hf.get_object_counts(val_set)
                configuration.TEST.DETECTIONS_PER_IMAGE = int(np.max(counts))

        # Create output directory and save configuration
        os.makedirs(output_dir, exist_ok=True)
        hf.write_configs(configuration, output_dir, img_augmentations)

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

"""Script to train a new model."""
# import general libraries
import os
import cv2
import random
from typing import Union
import matplotlib.pyplot as plt
import numpy as np

# import detectron2 utilities
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog
from detectron2.utils.logger import setup_logger
from detectron2.config import CfgNode

# import custom code
from utils.datasets import load_custom_data
from utils import datasets as ds
import utils.custom_detectron as custom
import utils.helper_funcs as hf


def run_training(train_set: ds.DataSet,
                 configuration: Union[str, CfgNode],
                 val_set: ds.DataSet = None,
                 output_dir: str = "./", log_name: str = "training.log",
                 resume: bool = True, visualize: bool = False):

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
    previous_config = os.path.join(output_dir, "config.yaml")
    # Try to load previously defined *.yaml configuration
    if resume and os.path.exists(previous_config):
        configuration = CfgNode(CfgNode.load_yaml_with_base(previous_config))
        resume_with_config = True

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
        hf.write_configs(configuration, output_dir)

    # Training
    trainer = custom.CustomTrainer(configuration)
    trainer.resume_or_load(resume=resume)
    trainer.train()

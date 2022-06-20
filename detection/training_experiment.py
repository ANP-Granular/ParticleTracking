"""Script to train a new model."""
# import general libraries
import os
import cv2
import random
import matplotlib.pyplot as plt
import numpy as np

# import detectron2 utilities
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog
from detectron2.utils.logger import setup_logger
from detectron2.config import CfgNode

# import custom code
from utils.configs import old_ported_config
from utils.datasets import HGS, load_custom_data
import utils.custom_detectron as custom
import utils.helper_funcs as hf
from utils.helper_funcs import write_configs

OUTPUT_DIR = "./test_coco_metrics/computed_max_det"
CONFIG_FILE = ""
# DATASET & TEST_DATASET are ignored, if a CONFIG_FILE is given
DATASET = HGS.train
TEST_DATASET = HGS.val
RESUME_TRAINING = True
VISUALIZE_SAMPLE = False
setup_logger(OUTPUT_DIR + "/training.log")


if VISUALIZE_SAMPLE:
    # visualize annotations of randomly selected samples in the training set
    meta_data = MetadataCatalog.get(DATASET.name)
    dataset_dicts = load_custom_data(DATASET)
    for d in random.sample(dataset_dicts, 1):
        img = cv2.imread(d["file_name"])
        visualizer = Visualizer(img[:, :, ::-1], metadata=meta_data, scale=0.5)
        d["annotations"] = random.sample(d["annotations"], 10)
        out = visualizer.draw_dataset_dict(d)
        plt.figure()
        plt.imshow(out.get_image()[:, :, ::-1])
        plt.show()

# Training:
if not CONFIG_FILE:
    cfg = old_ported_config(DATASET, TEST_DATASET)
else:
    cfg = CfgNode.load_yaml_with_base(CONFIG_FILE)

cfg.OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
if TEST_DATASET:
    # Determine the maximum number of instances to predict per image
    counts = hf.get_object_counts(TEST_DATASET)
    cfg.TEST.DETECTIONS_PER_IMAGE = int(np.max(counts))

os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
hf.write_configs(cfg, OUTPUT_DIR)
trainer = custom.CustomTrainer(cfg)
trainer.resume_or_load(resume=RESUME_TRAINING)
trainer.train()






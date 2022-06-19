"""Script to train a new model."""
# import general libraries
import os
import cv2
import random
import matplotlib.pyplot as plt

# import detectron2 utilities
from detectron2.engine import DefaultTrainer
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog

# import custom code
from utils.configs import old_ported_config, run_test_config
from utils.datasets import HGS, load_custom_data
import utils.helper_funcs as hf
import utils.custom_detectron as custom

# Setup detectron2 logger
from detectron2.utils.logger import setup_logger
setup_logger("./test_configs/test_logging.log")

OUTPUT_DIR = "./test_configs"
DATASET = HGS.train
TEST_DATASET = HGS.val
RESUME_TRAINING = False

# Train on a custom dataset
# visualize annotations of randomly selected samples in the training/validation
# set
meta_data = MetadataCatalog.get(DATASET.name)
dataset_dicts = load_custom_data(DATASET)
# for d in random.sample(dataset_dicts, 1):
#     img = cv2.imread(d["file_name"])
#     visualizer = Visualizer(img[:, :, ::-1], metadata=meta_data, scale=0.5)
#     d["annotations"] = random.sample(d["annotations"], 10)
#     out = visualizer.draw_dataset_dict(d)
#     plt.figure()
#     plt.imshow(out.get_image()[:, :, ::-1])
#     plt.show()

# Training:
cfg = old_ported_config(DATASET, TEST_DATASET)
# cfg = run_test_config(DATASET)
cfg.OUTPUT_DIR = os.path.abspath(OUTPUT_DIR)
os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
# trainer = DefaultTrainer(cfg)
# trainer = hf.CustomTrainer(cfg)
trainer = custom.CustomTrainer(cfg)
trainer.resume_or_load(resume=RESUME_TRAINING)
trainer.train()






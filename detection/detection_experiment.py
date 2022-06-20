"""Script to run detection experiments with a previously trained network."""
# import general libraries
import os
import cv2
import random
import matplotlib.pyplot as plt

# import detectron2 utilities
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import Visualizer, ColorMode
from detectron2.data import MetadataCatalog
from detectron2.utils.logger import setup_logger

# import custom code
from utils.configs import old_ported_config
from utils.datasets import HGS, load_custom_data
from utils.helper_funcs import write_configs


# Input
INPUT_FOLDER = "./ported_configs_HGS"
MODEL_WEIGHTS = "/model_final.pth"
DATASET_NAME = HGS.val
RANDOMSAMPLES = -1  # Amount of random samples to draw from the dataset.
                    # Put -1 or 0 to use the whole dataset.
# Visualization
VISUALIZE = True
HIDE_TAGS = True
SHOW_ORIGINAL = True
# Output
SAVE_RESULTS = False
OUTPUT_FOLDER = "./detections"
setup_logger(OUTPUT_FOLDER + "/detection.log")

# Configuration
meta_data = MetadataCatalog.get(HGS.val.name)
cfg = old_ported_config()
cfg.MODEL.WEIGHTS = os.path.abspath(INPUT_FOLDER + MODEL_WEIGHTS)
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7

write_configs(cfg, OUTPUT_FOLDER)
predictor = DefaultPredictor(cfg)

# Randomly select several samples to visualize the prediction results.
dataset_dicts = load_custom_data(HGS.val)
if VISUALIZE and RANDOMSAMPLES > 0:
    dataset_dicts = random.sample(dataset_dicts, RANDOMSAMPLES)

fig_count = 1
for d in dataset_dicts:
    im = cv2.imread(d["file_name"])
    outputs = predictor(im)

    if VISUALIZE:
        v = Visualizer(im[:, :, ::-1],
                       metadata=meta_data,
                       scale=0.5,
                       instance_mode=ColorMode.IMAGE_BW)

        # Remove unnecessary information before drawing
        to_draw = outputs["instances"].to("cpu")
        if HIDE_TAGS:
            del to_draw._fields["pred_classes"]
            del to_draw._fields["scores"]
            del to_draw._fields["pred_boxes"]
        out = v.draw_instance_predictions(to_draw)
        fig_title = os.path.basename(d["file_name"])
        if SHOW_ORIGINAL:
            fig = plt.figure(num=fig_count, figsize=[6.4, 2*4.8])
            ax1 = plt.subplot(2, 1, 1)
            ax1.imshow(out.get_image()[:, :, ::-1])
            ax2 = plt.subplot(2, 1, 2)
            ax2.imshow(im)
            fig.suptitle(fig_title)
        else:
            plt.figure(num=fig_count)
            plt.imshow(out.get_image()[:, :, ::-1])
            plt.title(fig_title)
        if SAVE_RESULTS:
            plt.savefig(os.path.join(OUTPUT_FOLDER, fig_title))
        fig_count += 1

if VISUALIZE:
    plt.show()

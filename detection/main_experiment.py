""" Adapted Detectron2 Tutorial"""
# import general libraries
import os
import cv2
import random
import matplotlib.pyplot as plt

# import detectron2 utilities
from detectron2.engine import DefaultPredictor, DefaultTrainer
from detectron2.utils.visualizer import Visualizer, ColorMode
from detectron2.data import MetadataCatalog
# import detectron2 evaluation utilities
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from detectron2.data import build_detection_test_loader

# import custom code
from utils.configs import old_ported_config
import utils.helper_funcs as hf
from utils.datasets import HGS, load_custom_data

# Setup detectron2 logger
from detectron2.utils.logger import setup_logger
setup_logger()


# Train on a custom dataset
# visualize annotations of randomly selected samples in the training/validation
# set
meta_data = MetadataCatalog.get(HGS.val.name)
dataset_dicts = load_custom_data(HGS.val)
for d in random.sample(dataset_dicts, 1):
    img = cv2.imread(d["file_name"])
    visualizer = Visualizer(img[:, :, ::-1], metadata=meta_data, scale=0.5)
    d["annotations"] = random.sample(d["annotations"], 10)
    out = visualizer.draw_dataset_dict(d)
    plt.figure()
    plt.imshow(out.get_image()[:, :, ::-1])
    plt.show()

# Training:
cfg = old_ported_config(HGS.train)
os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
trainer = DefaultTrainer(cfg)
trainer.resume_or_load(resume=False)
trainer.train()

# Inference & evaluation using the trained model
# Now, let's run inference with the trained model on the balloon validation
# dataset. First, let's create a predictor using the model we just trained:

# Inference should use the config with parameters that are used in training
# cfg now already contains everything we've set previously. We changed it a
# little bit for inference:
cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")  # path to the model we just trained
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7   # set a custom testing threshold
predictor = DefaultPredictor(cfg)

# Randomly select several samples to visualize the prediction results.
dataset_dicts = load_custom_data(HGS.val)
for d in random.sample(dataset_dicts, 3):
    im = cv2.imread(d["file_name"])
    outputs = predictor(im)  # format is documented at https://detectron2.readthedocs.io/tutorials/models.html#model-output-format
    v = Visualizer(im[:, :, ::-1],
                   metadata=meta_data,
                   scale=0.5,
                   instance_mode=ColorMode.IMAGE_BW   # remove the colors of unsegmented pixels. This option is only available for segmentation models
    )
    out = v.draw_instance_predictions(outputs["instances"].to("cpu"))
    plt.figure()
    plt.imshow(out.get_image()[:, :, ::-1])
    plt.show()

# Also evaluate its performance using AP metric implemented in COCO API.
evaluator = COCOEvaluator(HGS.val.name, output_dir="./output")
val_loader = build_detection_test_loader(cfg, HGS.val.name)
print(inference_on_dataset(predictor.model, val_loader, evaluator))
# another equivalent way to evaluate the model is to use `trainer.test`





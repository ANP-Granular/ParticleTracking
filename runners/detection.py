"""Script to run runners experiments with a previously trained network."""
# import general libraries
import os
import cv2
import random
from typing import Union, List
import numpy as np

# import detectron2 utilities
from detectron2.engine import DefaultPredictor
from detectron2.utils.logger import setup_logger
from detectron2.config import CfgNode

# import custom code
import utils.datasets as ds
from utils.helper_funcs import write_configs
from runners import visualization

SHOW_ORIGINAL = True


def run_detection(dataset: Union[ds.DataSet, List[str]],
                  configuration: Union[CfgNode, str],
                  weights: str = None, output_dir: str = "./",
                  log_name: str = "detection.log",
                  visualize: bool = True,
                  vis_random_samples: int = -1, **kwargs):
    setup_logger(os.path.join(output_dir, log_name))

    # Configuration
    if isinstance(configuration, str):
        cfg = CfgNode(CfgNode.load_yaml_with_base(configuration))
    else:
        cfg = configuration
    if weights is not None:
        cfg.MODEL.WEIGHTS = os.path.abspath(weights)
    cfg.MODEL.DEVICE = "cpu"  # to run predictions/visualizations while gpu in use
    write_configs(cfg, output_dir)

    predictor = DefaultPredictor(cfg)

    # Handling the ds.DataSet, List[str] ambiguity
    if isinstance(dataset, ds.DataSet):
        dataset = ds.load_custom_data(dataset)

    # Randomly select several samples to visualize the prediction results.
    to_visualize = np.zeros(len(dataset))
    if visualize:
        if vis_random_samples > 0:
            samples = random.sample(range(0, len(to_visualize)),
                                    vis_random_samples)
            to_visualize[samples] = 1
        else:
            # visualize all
            to_visualize = np.ones(len(dataset))

    for d, vis in zip(dataset, to_visualize):
        if isinstance(d, dict):
            file = d["file_name"]
        else:
            file = d
        im = cv2.imread(file)
        outputs = predictor(im)

        if vis:
            if SHOW_ORIGINAL:
                visualization.visualize(outputs, d, output_dir=output_dir,
                                        **kwargs)
            else:
                visualization.visualize(outputs, file, output_dir=output_dir,
                                        **kwargs)
        # Saving outputs

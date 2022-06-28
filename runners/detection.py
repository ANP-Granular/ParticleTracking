"""Script to run runners experiments with a previously trained network."""
# import general libraries
import os
import cv2
import random
from typing import Union, List

# import detectron2 utilities
from detectron2.engine import DefaultPredictor
from detectron2.data import MetadataCatalog
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
                  visualize: bool = True, hide_tags: bool = True,
                  vis_random_samples: int = -1):
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
    meta_data = None
    if isinstance(dataset, ds.DataSet):
        meta_data = MetadataCatalog.get(dataset.name)
        dataset = ds.load_custom_data(dataset)

    # Randomly select several samples to visualize the prediction results.
    if visualize and vis_random_samples > 0:
        dataset = random.sample(dataset, vis_random_samples)

    for d in dataset:
        if isinstance(d, dict):
            file = d["file_name"]
        else:
            file = d
        im = cv2.imread(file)
        outputs = predictor(im)

        if visualize:
            if SHOW_ORIGINAL:
                visualization.visualize(outputs, d, meta_data,
                                        hide_tags=hide_tags,
                                        output_dir=output_dir)
            else:
                visualization.visualize(outputs, file,
                                        hide_tags=hide_tags,
                                        output_dir=output_dir)
        # Saving outputs

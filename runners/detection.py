"""
Script to run inference with a trained network and save the results for further 
computations.

Author:     Adrian Niemann (adrian.niemann@ovgu.de)
Date:       11.08.2022
"""

# import general libraries
import os
import cv2
import random
import logging
import sys
from typing import Union, List
import numpy as np
import scipy.io as sio

# import detectron2 utilities
from detectron2.engine import DefaultPredictor
from detectron2.utils.logger import setup_logger
from detectron2.config import CfgNode

# import custom code
import utils.datasets as ds
import utils.helper_funcs as hf
from runners import visualization

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%m/%d %H:%M:%S"
    )
ch.setFormatter(formatter)
_logger.addHandler(ch)


SHOW_ORIGINAL = True


def run_detection(dataset: Union[ds.DataSet, List[str]],
                  configuration: Union[CfgNode, str],
                  weights: str = None, classes: dict = None,
                  output_dir: str = "./", log_name: str = "detection.log",
                  visualize: bool = True, vis_random_samples: int = -1,
                  threshold: float = 0.5, **kwargs) -> list:
    """Runs inference on a given set of images and can visualize the output.

    In addition to running inference this script also generates rod enpoints 
    from the generated masks, if the network predicted these.

    Parameters
    ----------
    dataset : Union[ds.DataSet, List[str]]
        Either a DataSet already registered to the Detectron2 framework or a 
        list of paths to image files intended for running inference on.
    configuration : Union[CfgNode, str]
        Configuration for the Detectron2 model and inferences settings given as 
        a CfgNode or path to a *.yaml file in the Detectron2 configuration 
        format.
    weights : str, optional
        Path to a *.pkl model file. Is optional, if the weights are already 
        given in the configuration.
    classes : dict, optional
        Dictionary of classes detectable by the model with 
        {key}  ->  Index of class in the model
        {value} ->  Name of the class
        By default None.
    output_dir : str, optional
        Path to the intended output directory. It's parent directory must exist 
        prior to running this function.
        By default "./".
    log_name : str, optional
        Filename for logging output in the output directory.
        By default "detection.log".
    visualize : bool, optional
        Flag for allowing visualization.
        By default True.
    vis_random_samples : int, optional
        Specifies the number of randomly chosen visualized samples when 
        `visualize` is True.
        -1      ->  All images are viszalized.
        n > 0   ->  Chooses n images of the given set to be visualized after 
                    inference.
        By default -1.
    threshold : float, optional
        Threshold for the minimum score of predicted instances.
        By default 0.5.
    **kwargs
        Keyword arguments for `visualization.visualize()`, except for
        `prediction`, `original`, and `output_dir`.
    
    Returns
    -------
    list
        Prediction for each image inference was run on.
    """
    setup_logger(os.path.join(output_dir, log_name))

    # Configuration
    if isinstance(configuration, str):
        cfg = CfgNode(CfgNode.load_yaml_with_base(configuration))
    else:
        cfg = configuration
    if weights is not None:
        cfg.MODEL.WEIGHTS = os.path.abspath(weights)
    cfg.MODEL.DEVICE = "cpu"  # to run predictions/visualizations while gpu in use
    hf.write_configs(cfg, output_dir)

    predictor = DefaultPredictor(cfg)
    if classes is None:
        classes = {i: str(i) for i in range(0, cfg.MODEL.ROI_HEADS.NUM_CLASSES)}
    # Handling the ds.DataSet, List[str] ambiguity
    if isinstance(dataset, ds.DataSet):
        dataset = ds.load_custom_data(dataset)

    # Randomly select several samples to visualize the prediction results.
    to_visualize = np.zeros(len(dataset))
    if visualize:
        if vis_random_samples >= 0:
            samples = random.sample(range(0, len(to_visualize)),
                                    vis_random_samples)
            to_visualize[samples] = 1
        else:
            # visualize all
            to_visualize = np.ones(len(dataset))
    _logger.info(f"Starting inference on {len(to_visualize)} file(s).")
    predictions = []
    files = []
    for d, vis in zip(dataset, to_visualize):
        if isinstance(d, dict):
            file = d["file_name"]
        else:
            file = d
        _logger.info(f"Inference on: {file}")
        im = cv2.imread(file)
        outputs = predictor(im)
        # Thresholding/cleaning results
        outputs["instances"] = outputs["instances"][
            outputs["instances"].scores > threshold]
        # Accumulate results
        predictions.append(outputs)
        files.append(os.path.basename(file))
        # Visualizations
        if vis:
            if SHOW_ORIGINAL:
                visualization.visualize(outputs, d, output_dir=output_dir,
                                        **kwargs)
            else:
                visualization.visualize(outputs, file, output_dir=output_dir,
                                        **kwargs)
        # Saving outputs
        if "pred_masks" in outputs["instances"].get_fields():
            _logger.info("Starting endpoint computation ...")
            points = hf.rod_endpoints(outputs, classes)
            save_to_mat(os.path.join(output_dir, os.path.basename(file)), 
                        points)
        _logger.info(f"Done with: {os.path.basename(file)}")
    
    return predictions


def save_to_mat(file_name: str, points: dict):
    """Saves rod endpoints of one image to be used in MATLAB for 3D matching.

    Parameters
    ----------
    file_name : str
        Output file name, that will be extended by the colors present in 
        `points`.
    points : dict
        Rod endpoint data in the output format of 
        `helper_funcs.rod_endpoints()`.
    """
    for idx, vals in points.items():
        if not vals.size:
            # skip classes without saved points
            continue
        dt = np.dtype(
            [('Point1', np.float, (2,)), ('Point2', np.float, (2,))])
        arr = np.zeros((vals.shape[0],), dtype=dt)

        arr[:]['Point1'] = vals[:, 0, :]
        arr[:]['Point2'] = vals[:, 1, :]

        sio.savemat(os.path.splitext(file_name)[0] +
                    f"_{idx}.mat", {'rod_data_links': arr})

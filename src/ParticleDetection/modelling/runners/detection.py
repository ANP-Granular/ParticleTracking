"""
Script to run inference with a trained network and save the results for further
computations.

Author:     Adrian Niemann (adrian.niemann@ovgu.de)
Date:       11.08.2022

"""
import os
import warnings
import cv2
import random
import logging
import sys
from typing import Union, List, Dict
import numpy as np
import pandas as pd
import scipy.io as sio

from detectron2.engine import DefaultPredictor
from detectron2.utils.logger import setup_logger
from detectron2.config import CfgNode

import ParticleDetection.utils.datasets as ds
import ParticleDetection.utils.helper_funcs as hf
import ParticleDetection.modelling.datasets as det_ds
from ParticleDetection.modelling.configs import write_configs
import ParticleDetection.utils.data_conversions as d_conv
import ParticleDetection.modelling.visualization as visualization

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
    warnings.warn("The output in a format for use in MATLAB is deprecated."
                  "Please use `run_detection_csv()` instead.",
                  DeprecationWarning)
    setup_logger(os.path.join(output_dir, log_name))

    # Configuration
    if isinstance(configuration, str):
        cfg = CfgNode(CfgNode.load_yaml_with_base(configuration))
    else:
        cfg = configuration
    if weights is not None:
        cfg.MODEL.WEIGHTS = os.path.abspath(weights)
    cfg.MODEL.DEVICE = "cpu"  # to run predictions while gpu in use
    write_configs(cfg, output_dir)

    predictor = DefaultPredictor(cfg)
    if classes is None:
        classes = {i: str(i)
                   for i in range(0, cfg.MODEL.ROI_HEADS.NUM_CLASSES)}
    # Handling the ds.DataSet, List[str] ambiguity
    if isinstance(dataset, ds.DataSet):
        dataset = det_ds.load_custom_data(dataset)

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


def run_detection_csv(dataset_format: str,
                      configuration: Union[CfgNode, str],
                      weights: str = None, classes: dict = None,
                      output_dir: str = "./", log_name: str = "detection.log",
                      threshold: float = 0.5,
                      frames: List[int] = [], cam1_name: str = "gp1",
                      cam2_name: str = "gp2"):
    """Runs inference on a given set of images and saves the output to a *.csv.

    This function runs a rod detection on images and generates rod enpoints
    from the generated masks, if the network predicted these. Finally, these
    endpoints are saved to a single `rods_df.csv` file in the specified output
    folder.

    Parameters
    ----------
    dataset_format : str
        String that can be formatted to specify the file locations of images,
        that shall be used for inference.
        For this the string must contain a `frame` and a `cam_id` field that
        can be formatted.
        Example:
        `"my/dataset/path/{cam_id:s}/experiment_{frame:05d}.png"`
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
    threshold : float, optional
        Threshold for the minimum score of predicted instances.
        By default 0.5.
    frames : List[int], optional
        A list of frames, that shall be used for rod detection.
        By default [].
    cam1_name : str, optional
        The name/ID of the first camera in the experiment. This name will be
        used for image discovery (see `dataset_format`) and naming of the
        output *.csv file's columns.
        By default "gp1".
    cam2_name : str, optional
        The name/ID of the second camera in the experiment. This name will be
        used for image discovery (see `dataset_format`) and naming of the
        output *.csv file's columns.
        By default "gp2".

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
    cfg.MODEL.DEVICE = "cpu"  # to run predictions while gpu in use
    write_configs(cfg, output_dir)

    predictor = DefaultPredictor(cfg)
    if classes is None:
        classes = {i: str(i)
                   for i in range(0, cfg.MODEL.ROI_HEADS.NUM_CLASSES)}

    _logger.info("Starting rod detection ...")
    predictions = []
    files = []
    cols = [col.format(id1=cam1_name, id2=cam2_name)
            for col in ds.DEFAULT_COLUMNS]
    data = pd.DataFrame(columns=cols)
    for frame in frames:
        frame_data = {color: [] for color in classes}           # noqa: F841
        for cam in [cam1_name, cam2_name]:
            file = dataset_format.format(frame=frame, cam_id=cam)
            _logger.info(f"Inference on: {file}")
            im = cv2.imread(file)
            if im is None:
                warnings.warn(f"Image couldn't be read: {file}")
                continue
            outputs = predictor(im)
            # Thresholding/cleaning results
            outputs["instances"] = outputs["instances"][
                outputs["instances"].scores > threshold]
            # Accumulate results
            predictions.append(outputs)
            files.append(os.path.basename(file))

            # Prepare outputs for saving
            if "pred_masks" in outputs["instances"].get_fields():
                _logger.info("Starting endpoint computation ...")
                points = hf.rod_endpoints(outputs, classes)
                data = add_points(points, data, cam, frame)
            _logger.info(f"Done with: {os.path.basename(file)}")
        # Save intermediate rod data
        if len(data) > 0:
            current_output = os.path.join(output_dir, "rods_df.csv")
            data.reset_index(drop=True, inplace=True)
            data = ds.replace_missing_rods(data, cam1_name, cam2_name)
            data.to_csv(current_output, ",")
            d_conv.csv_extract_colors(current_output)
    return predictions


def add_points(points: Dict[str, np.ndarray], data: pd.DataFrame,
               cam_id: str, frame: int):
    """Updates a dataframe with new rod endpoint data for one camera and frame.

    Parameters
    ----------
    points : Dict[str, np.ndarray]
        Rod endpoints in the format obtained from
        `utils.helper_funcs.rod_endpoints`.
    data : pd.DataFrame
        Dataframe for the rods to be saved in.
    cam_id : str
        ID/Name of the camera, that produced the image the rod endpoints were
        computed on.
    frame : int
        Frame number in the dataset.

    Returns
    -------
    pd.DataFrame
        Returns the updated `data` dataframe.
    """
    cols = [col for col in data.columns if cam_id in col]
    for color, v in points.items():
        if np.size(v) == 0:
            continue
        v = np.reshape(v, (len(v), -1))
        seen = np.ones((len(v), 1))
        to_df = np.concatenate((v, seen), axis=1)
        temp_df = pd.DataFrame(to_df, columns=cols)
        if len(data.loc[(data.frame == frame) & (data.color == color)]) == 0:
            temp_df["frame"] = frame
            temp_df["color"] = color
            temp_df["particle"] = np.arange(0, len(temp_df), dtype=int)
            data = pd.concat((data, temp_df))
        else:
            previous_data = data.loc[
                (data.frame == frame) & (data.color == color)]
            new_data = data.loc[
                (data.frame == frame) & (data.color == color)].fillna(temp_df)
            data.loc[(data.frame == frame) & (data.color == color)] = new_data
            if len(previous_data) < len(temp_df):
                temp_df["frame"] = frame
                temp_df["color"] = color
                temp_df["particle"] = np.arange(0, len(temp_df), dtype=int)
                idx_to_add = np.arange(len(previous_data), len(temp_df))
                data = pd.concat((data, temp_df.iloc[idx_to_add]))
    data = data.astype({"frame": 'int', "particle": 'int'})
    return data


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

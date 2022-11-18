"""
Functions to run inference with a trained and exported network and save
the results for further computations.

Author:     Adrian Niemann (adrian.niemann@ovgu.de)
Date:       07.11.2022

"""
import logging
from typing import List
from pathlib import Path
from tqdm import tqdm
import torch
import pandas as pd

# Don't remove the following imports, see GitHub issue as reference
# https://github.com/pytorch/pytorch/issues/48932#issuecomment-803957396
import cv2                                                      # noqa: F401
import torchvision                                              # noqa: F401
import ParticleDetection                                        # noqa: F401

import ParticleDetection.utils.data_loading as dl
import ParticleDetection.utils.datasets as ds
import ParticleDetection.utils.helper_funcs as hf
import ParticleDetection.utils.data_conversions as d_conv

_logger = logging.getLogger(__name__)


def _run_detection(model: torch.ScriptModule, img: Path,
                   threshold: float = 0.5) -> dict:
    """Runs detection on one image.

    Runs the detection model with the given image and converts the returned
    ROI masks to bitmasks.

    Parameters
    ----------
    model : torch.ScriptModule
        Model used for the detection process. It must return a tuple of:
        [0] -> ROI boxes
        [1] -> predicted classes
        [2] -> ROI masks
        [3] -> prediction scores (confidence)
        [4] -> image dimensions (height, width)
    img : Path
        Path to an image the detection shall be run on.
    threshold : float, optional
        Threshold for the minimum score of predicted instances.
        By default 0.5.

    Returns
    -------
    dict
        Has the following keys:
        {"pred_boxes", "pred_classes", "pred_masks", "scores", "input_size"}
    """
    input = dl.read_image(img)
    with torch.no_grad():
        ret = model(input)

    to_out = ret[3] > threshold

    # Create bit-masks from ROI-masks
    b_masks = []
    for i in range(len(ret[0])):
        if not to_out[i]:
            continue
        mask = ret[2][i].squeeze()
        box = ret[0][i].squeeze()
        b_masks.append(hf.paste_mask_in_image_old(mask, box, *ret[4]))
    if not b_masks:
        return {}
    b_masks = torch.stack(b_masks)
    return {
        "pred_boxes": ret[0][to_out, :],
        "pred_classes": ret[1][to_out],
        "pred_masks": b_masks,
        "scores": ret[3][to_out],
        "input_size": ret[4],
    }


def run_detection(model: torch.ScriptModule, dataset_format: str,
                  classes: dict = None,
                  output_dir: Path = Path("./"), threshold: float = 0.5,
                  frames: List[int] = [],
                  cam1_name: str = "gp1", cam2_name: str = "gp2") -> None:
    """Runs inference on a given set of images and saves the output to a *.csv.

    This function runs a rod detection on images and generates rod enpoints
    from the generated masks, if the network predicted these. Finally, these
    endpoints are saved to a single `rods_df.csv` file in the specified output
    folder.

    Parameters
    ----------
    model : torch.ScriptModule
        Model used for the detection process. It must return a tuple of:
        [0] -> ROI boxes
        [1] -> predicted classes
        [2] -> ROI masks
        [3] -> prediction scores (confidence)
        [4] -> image dimensions (height, width)
    dataset_format : str
        String that can be formatted to specify the file locations of images,
        that shall be used for inference.
        For this the string must contain a `frame` and a `cam_id` field that
        can be formatted.
        Example:
        `"my/dataset/path/{cam_id:s}/experiment_{frame:05d}.png"`
    classes : dict, optional
        Dictionary of classes detectable by the model with
        {key}  ->  Index of class in the model
        {value} ->  Name of the class
        By default None.
    output_dir : Path, optional
        Path to the intended output directory. It's parent directory must exist
        prior to running this function.
        By default Path("./").
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
    """
    cols = [col.format(id1=cam1_name, id2=cam2_name)
            for col in ds.DEFAULT_COLUMNS]
    data = pd.DataFrame(columns=cols)
    for frame in tqdm(frames):
        for cam in [cam1_name, cam2_name]:
            file = Path(dataset_format.format(frame=frame, cam_id=cam))
            _logger.debug(f"Inference on: {str(file)}")
            outputs = _run_detection(model, file, threshold=threshold)

            if "pred_masks" in outputs:
                _logger.debug("Starting endpoint computation ...")
                # points = hf.rod_endpoints_independent(outputs, classes)
                points = hf.rod_endpoints(outputs, classes)
                data = ds.add_points(points, data, cam, frame)
            _logger.info(f"Done with: {file.name}")
        # Save intermediate rod data
        if len(data) > 0:
            current_output = output_dir / "rods_df.csv"
            data.reset_index(drop=True, inplace=True)
            data = ds.replace_missing_rods(data, cam1_name, cam2_name)
            data.to_csv(current_output, ",")
            d_conv.csv_extract_colors(str(current_output.resolve()))
    return
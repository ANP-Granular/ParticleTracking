"""
Collection of function to manipulate training dataset metadata in json format.
These functions are mainly to cleanup the metadata, but also to transfer it
into a form for different detection tasks, i.e. keypoint detection.

Author:     Adrian Niemann (adrian.niemann@ovgu.de)
Date:       31.10.2022

"""
import os
import sys
import json
import logging

import torch
import numpy as np
from PIL import Image
from detectron2.structures import Instances
from detectron2.utils.visualizer import GenericMask

import ParticleDetection.utils.datasets as ds
import ParticleDetection.utils.helper_funcs as hf

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


def remove_duplicate_regions(dataset: ds.DataSet) -> None:
    """Remove duplicate regions from the dataset's metadata.

    Parameters
    ----------
    dataset : ds.DataSet
        Dataset to be cleaned from duplicate annotations.
    """
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)

    deleted_duplicates = 0
    for img in annotations.keys():
        regions = annotations[img]["regions"]
        used = []
        for item in regions:
            if item not in used:
                used.append(item)
        annotations[img]["regions"] = used
        _logger.info(f"origial: {len(regions)}, new: {len(used)}")
        deleted_duplicates += (len(regions)-len(used))

    with open(dataset.annotation, 'w') as metadata:
        json.dump(annotations, metadata, indent=2)
    _logger.info(f"######################################\n"
                 f"Deleted duplicates: {deleted_duplicates}")
    return


def change_visibiliy(file: str) -> None:
    """Changes the visibility flag for all keypoints in a file of keypoint
    training data.

    Parameters
    ----------
    file : str
        Path to the annotations file that's changed.
    """
    with open(file, "r") as f:
        to_change = json.load(f)
    for idx_f, val_f in to_change.items():
        for idx_r, reg in enumerate(val_f["regions"]):
            new_points = reg["keypoints"]
            new_points[2] = 2.0
            new_points[-1] = 2.0
            to_change[idx_f]["regions"][idx_r]["keypoints"] = new_points
    with open(file, "w") as f:
        json.dump(to_change, f, indent=2)


def change_class(file: str) -> None:
    """Changes all class labels to "0" in a file of keypoint training data.

    Parameters
    ----------
    file : str
        Path to the annotations file that's changed.
    """
    with open(file, "r") as f:
        to_change = json.load(f)

    for idx_f, val_f in to_change.items():
        for idx_r, reg in enumerate(val_f["regions"]):
            to_change[idx_f]["regions"][idx_r]["region_attributes"]["rod_col"]\
                = 0

    with open(file, "w") as f:
        json.dump(to_change, f, indent=2)


def order_by_x(file: str) -> None:
    """Adjust keypoints, such that the more left one is always the first point.

    Parameters
    ----------
    file : str
        Path to the annotations file that's changed.
    """
    with open(file, "r") as f:
        to_change = json.load(f)

    for idx_f, val_f in to_change.items():
        for idx_r, reg in enumerate(val_f["regions"]):
            points = reg["keypoints"]
            if points[0] > points[3]:
                new_points = points[3:]
                new_points.extend(points[0:3])
                to_change[idx_f]["regions"][idx_r]["keypoints"] = new_points

    with open(file, "w") as f:
        json.dump(to_change, f, indent=2)


def create_keypoints(file_name: str, single_class=True, order_x=True) -> None:
    """Creates rod keypoints from segmentation data.

    Creates rod endpoints as key points from segmentation, adds it to
    the metadata and saves that as a new file.

    key points (list[float]) in the format of [x1, y1, v1,…, xn, yn, vn].
    v=0: not labeled (in which case x=y=0),
    v=1: labeled but not visible
    v=2: labeled and visible
    see https://cocodataset.org/#format-data for more details

    Parameters
    ----------
    file_name : str
        Path to the annotations file that's changed.
    """
    to_change = ds.DataSet("to_change", os.path.dirname(file_name) + "/",
                           os.path.basename(file_name))
    classes = {cls: str(cls) for cls in ds.get_dataset_classes(to_change)}

    with open(to_change.annotation) as metadata:
        annotations = json.load(metadata)

    for key, val in annotations.items():
        # Skip non-annotated image entries
        if not val["regions"]:
            continue

        # Create an entry in the custom dataset
        filename = os.path.join(to_change.folder, val["filename"])
        width, height = Image.open(filename).size[:2]
        annos = val["regions"]
        for idx_r, rod in enumerate(annos):
            try:
                category_id = int(rod["region_attributes"]["rod_col"])
            except KeyError:
                category_id = 0

            rod = rod["shape_attributes"]
            px = rod["all_points_x"]
            py = rod["all_points_y"]
            poly = [(x + 0.5, y + 0.5) for x, y in zip(px, py)]
            poly = [p for x in poly for p in x]

            mask = np.asarray(GenericMask([poly], height, width).mask,
                              dtype=bool).tolist()
            inst = {"instances": Instances(
                (height, width),
                pred_classes=torch.Tensor([category_id]),
                pred_masks=torch.Tensor([mask])
            )}
            try:
                key_points = hf.rod_endpoints(inst, classes)
                key_points = key_points[str(category_id)].flatten()
                key_points = [float(point) for point in key_points]
                to_insert = [*key_points[0:2], 2, *key_points[2:], 2]
            except UnboundLocalError as e:
                # no endpoints were found
                to_insert = 6*[-1]
                _logger.info(f"No endpoints found. The following error "
                             f"occurred:\n{e}")
            annotations[key]["regions"][idx_r]["keypoints"] = to_insert

        _logger.info(f"Done with: {key}")

    old_file, ext = os.path.splitext(file_name)
    with open(old_file + "_keypoints" + ext, 'w') as metadata:
        json.dump(annotations, metadata, indent=2)


def delete_len_0(file_name: str) -> None:
    """Deletes annotations with keypoints resulting in 0 lenght rods.

    Parameters
    ----------
    file_name : str
        Path to the annotations file that's changed.
    """
    with open(file_name, "r") as f:
        to_change = json.load(f)

    for idx_f, val_f in to_change.items():
        for idx_r, reg in enumerate(val_f["regions"]):
            points = np.asarray(reg["keypoints"])
            len_kp = np.linalg.norm(points[0:2] - points[3:-1])
            if len_kp < 1e-3:
                del to_change[idx_f]["regions"][idx_r]

    with open(file_name, "w") as f:
        json.dump(to_change, f, indent=2)

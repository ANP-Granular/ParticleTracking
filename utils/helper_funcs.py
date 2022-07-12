import sys
import json
import os.path
import pickle
import logging
from collections import Counter

import torch
import numpy as np
from PIL import Image
from scipy.spatial import ConvexHull
from sklearn.cluster import DBSCAN
from skimage.transform import probabilistic_hough_line
from detectron2.config.config import CfgNode
from detectron2.structures import Instances
from detectron2.utils.visualizer import GenericMask

import utils.datasets as ds

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


def dot_arccos(lineA, lineB):
    # Get nicer vector form
    vA = [(lineA[0] - lineA[2]), (lineA[1] - lineA[3])]
    vB = [(lineB[0] - lineB[2]), (lineB[1] - lineB[3])]
    # Get dot prod
    dot_prod = np.dot(vA, vB)
    # Get magnitudes, Get cosine value, Get angle in radians and then
    # convert to degrees
    return np.arccos(
        np.clip(dot_prod / (np.linalg.norm(vA) * np.linalg.norm(vB)), -1,
                1))


def line_metric_4(l1, l2):
    """Custom metric: (distance + const)*exp"""
    num_min = np.argmin([np.linalg.norm([(l1[0] - l1[2]), (l1[1] - l1[3])]),
                         np.linalg.norm(
                             [(l2[0] - l2[2]), (l2[1] - l2[3])])])
    if num_min == 0:
        l_min = l1
        l_max = l2
    else:
        l_min = l2
        l_max = l1

    len_min = np.linalg.norm(l_min)
    len_max = np.linalg.norm(l_max)

    g = np.min([np.linalg.norm([(l1[0] - l2[0]), (l1[1] - l2[1])]),
                np.linalg.norm([(l1[0] - l2[2]), (l1[1] - l2[3])]),
                np.linalg.norm([(l1[2] - l2[0]), (l1[3] - l2[1])]),
                np.linalg.norm([(l1[2] - l2[2]), (l1[3] - l2[3])]), ])

    p1 = np.array(
        [np.mean([l_min[0], l_min[2]]), np.mean([l_min[1], l_min[3]])])
    p2 = np.array([l_max[0], l_max[1]])
    p3 = np.array([l_max[2], l_max[3]])

    s = np.cross(p2 - p1, p1 - p3) / np.linalg.norm(p2 - p1)

    # Proximity
    prox_m = (g / len_min) ** 2

    # Parallelism
    parr_m = (dot_arccos(l1, l2) * s * len_max) / (len_min * len_min)

    # Collinearity
    coll_m = (dot_arccos(l1, l2) * s * (len_min + g)) / (len_min * len_min)

    # return [prox_m, parr_m, coll_m]
    return np.linalg.norm([prox_m, 5.0 * parr_m, 4.0 * coll_m])


def minimum_bounding_rectangle(points):
    """Minimum bounding rectangle (parallelogram?)

    Find the smallest bounding rectangle for a set of points.
    Returns a set of points representing the corners of the bounding box.

    :param points: an nx2 matrix of coordinates
    :rval: an nx2 matrix of coordinates
    """
    pi2 = np.pi / 2.

    # get the convex hull for the points
    hull_points = points[ConvexHull(points).vertices]

    # calculate edge angles
    # edges = np.zeros((len(hull_points) - 1, 2))
    edges = hull_points[1:] - hull_points[:-1]

    # angles = np.zeros((len(edges)))
    angles = np.arctan2(edges[:, 1], edges[:, 0])

    angles = np.abs(np.mod(angles, pi2))
    angles = np.unique(angles)

    # find rotation matrices
    # XXX both work
    rotations = np.vstack([
        np.cos(angles),
        np.cos(angles - pi2),
        np.cos(angles + pi2),
        np.cos(angles)]).T
    #     rotations = np.vstack([
    #         np.cos(angles),
    #         -np.sin(angles),
    #         np.sin(angles),
    #         np.cos(angles)]).T
    rotations = rotations.reshape((-1, 2, 2))

    # apply rotations to the hull
    rot_points = np.dot(rotations, hull_points.T)

    # find the bounding points
    min_x = np.nanmin(rot_points[:, 0], axis=1)
    max_x = np.nanmax(rot_points[:, 0], axis=1)
    min_y = np.nanmin(rot_points[:, 1], axis=1)
    max_y = np.nanmax(rot_points[:, 1], axis=1)

    # find the box with the best area
    areas = (max_x - min_x) * (max_y - min_y)
    best_idx = np.argmin(areas)

    # return the best box
    x1 = max_x[best_idx]
    x2 = min_x[best_idx]
    y1 = max_y[best_idx]
    y2 = min_y[best_idx]
    r = rotations[best_idx]

    rval = np.zeros((4, 2))
    rval[0] = np.dot([x1, y2], r)
    rval[1] = np.dot([x2, y2], r)
    rval[2] = np.dot([x2, y1], r)
    rval[3] = np.dot([x1, y1], r)

    return rval


def rod_endpoints(prediction, classes: dict):
    """Calculates the endpoints of rods from the prediction masks."""
    results = {}
    with np.errstate(divide='ignore', invalid='ignore'):
        r = prediction["instances"].to("cpu").get_fields()

        for i_c in classes:  # Loop on colors
            XY = []
            i_c_list = np.argwhere(r['pred_classes'] == i_c).flatten()
            for i_m in i_c_list:
                segmentation = r['pred_masks'][i_m, :, :].numpy()
                # Prob hough for line detection
                lines = probabilistic_hough_line(segmentation, threshold=0,
                                                 line_length=10,
                                                 line_gap=30)
                # If too short
                if not lines:
                    lines = probabilistic_hough_line(segmentation,
                                                     threshold=0,
                                                     line_length=4,
                                                     line_gap=30)
                # No endpoint estimation possible
                if not lines:
                    _logger.info(f"No endpoints computed for a rod of class "
                                 f"{classes[i_c]}.")
                    XY.append(np.array([[-1, -1], [-1, -1]]))
                    continue

                # Lines to 4 dim array
                Xl = np.array(lines)
                X = np.ravel(Xl).reshape(Xl.shape[0], 4)
                # Clustering with custom metric
                db = DBSCAN(eps=0.0008, min_samples=4, algorithm='auto',
                            metric=line_metric_4).fit(X)

                core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
                core_samples_mask[db.core_sample_indices_] = True
                labels = db.labels_

                cl_count = Counter(labels)
                k = cl_count.most_common(1)[0][0]
                class_member_mask = (labels == k)

                xy = X[class_member_mask & core_samples_mask]

                points = xy.reshape(2 * xy.shape[0], 2)
                if points.shape[0] > 2:
                    bbox = minimum_bounding_rectangle(points)
                    bord = -1  # Make rods 1 pix shorter

                    # End coordinates
                    if np.argmin([np.linalg.norm(bbox[0, :] - bbox[1, :]),
                                  np.linalg.norm(bbox[1, :] - bbox[2, :])]) == 0:
                        x1 = np.mean(bbox[0:2, 0])
                        y1 = np.mean(bbox[0:2, 1])
                        x2 = np.mean(bbox[2:4, 0])
                        y2 = np.mean(bbox[2:4, 1])

                    else:
                        x1 = np.mean(bbox[1:3, 0])
                        y1 = np.mean(bbox[1:3, 1])
                        x2 = np.mean([bbox[0, 0], bbox[3, 0]])
                        y2 = np.mean([bbox[0, 1], bbox[3, 1]])

                    vX = x2 - x1
                    vY = y2 - y1
                    vN = np.linalg.norm([vX, vY])
                    nvX = vX / vN
                    nvY = vY / vN
                    x1 = x1 - bord * nvX
                    x2 = x2 + bord * nvX
                    y1 = y1 - bord * nvY
                    y2 = y2 + bord * nvY
                    xy1 = [x1, y1]
                    xy2 = [x2, y2]

                elif points.shape[0] == 2:
                    xy1 = points[0, :]
                    xy2 = points[1, :]

                else:
                    xy1 = [-1, -1]  # value, if no endpoints are computed
                    xy2 = [-1, -1]  # value, if no endpoints are computed
                    _logger.info(f"No endpoints computed for a rod of class "
                                 f"{classes[i_c]}.")
                XY.append(np.array([xy1, xy2]))

            results[classes[i_c]] = np.array(XY)
    return results


def get_dataset_size(dataset: ds.DataSet):
    """Compute the number of annotated images in a dataset (excluding
    augmentation)."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    image_count = 0
    for image in list(annotations.values()):
        # Skip non-annotated image entries
        if image["regions"]:
            image_count += 1
    return image_count


def get_epochs(cfg: CfgNode, image_count: int) -> float:
    """Computes the achieved number of epochs with given settings and data."""
    batch_size = cfg.SOLVER.IMS_PER_BATCH
    iterations = cfg.SOLVER.MAX_ITER
    return iterations / (image_count/batch_size)


def get_iters(cfg: CfgNode, image_count: int, desired_epochs: int) -> int:
    """Computes the necessary iterations to achieve a given number of epochs."""
    batch_size = cfg.SOLVER.IMS_PER_BATCH
    return desired_epochs*(image_count/batch_size)


def write_configs(cfg: CfgNode, directory: str, augmentations=None) -> None:
    """Write a configuration to a 'config.yaml' file in a target directory."""
    with open(directory + "/config.yaml", "w") as f:
        f.write(cfg.dump())
    if augmentations is not None:
        with open(directory + "/augmentations.pkl", "wb") as f:
            pickle.dump(augmentations, f)


def get_object_counts(dataset: ds.DataSet):
    """Returns a list of the number of objects in each image in the dataset."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    return [len(annotations[key]["regions"]) for key in annotations.keys()]


def remove_duplicate_regions(dataset: ds.DataSet):
    """Remove duplicate regions from the dataset's metadata."""
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
        print(f"origial: {len(regions)}, new: {len(used)}")
        deleted_duplicates += (len(regions)-len(used))

    with open(dataset.annotation, 'w') as metadata:
        json.dump(annotations, metadata)
    print(f"######################################\n"
          f"Deleted duplicates: {deleted_duplicates}")
    return


def create_keypoints(file_name: str):
    """Creates rod endpoints as key points from segmentation, adds it to
    the metadata and saves that as a new file.

    key points (list[float]) in the format of [x1, y1, v1,…, xn, yn, vn].
    v=0: not labeled (in which case x=y=0),
    v=1: labeled but not visible
    v=2: labeled and visible
    see https://cocodataset.org/#format-data for more details
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
                key_points = rod_endpoints(inst, classes)
                key_points = key_points[str(category_id)].flatten()
                key_points = [float(point) for point in key_points]
                to_insert = [*key_points[0:2], 2, *key_points[2:], 2]
            except UnboundLocalError as e:
                # no endpoints were found
                to_insert = 6*[0]
                print(e)
            annotations[key]["regions"][idx_r]["keypoints"] = to_insert

        print(f"Done with: {key}")

    old_file, ext = os.path.splitext(file_name)
    with open(old_file + "_keypoints" + ext, 'w') as metadata:
        json.dump(annotations, metadata)


if __name__ == "__main__":
    # from utils.datasets import HGS
    # remove_duplicate_regions(HGS.val)

    file = "../datasets/rods_c4m/val/via_export_json.json"
    # file = "../datasets/rods_c4m/train/via_export_json.json"
    create_keypoints(file)

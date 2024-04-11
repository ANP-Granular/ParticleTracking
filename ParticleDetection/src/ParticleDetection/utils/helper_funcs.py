# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev, and others
#
# This file is part of ParticleDetection.
# ParticleDetection is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ParticleDetection is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ParticleDetection. If not, see <http://www.gnu.org/licenses/>.

"""
Collection of miscellaneous helper functions.
"""
import json
import logging
import multiprocessing as mp
import sys
from collections import Counter
from typing import Dict, Union

import cv2
import numpy as np
import torch
from PIL import Image
from scipy.spatial import ConvexHull
from skimage.transform import probabilistic_hough_line
from sklearn.cluster import DBSCAN

import ParticleDetection.utils.data_loading as dl
import ParticleDetection.utils.datasets as ds

_logger = logging.getLogger(__name__)


def configure_logging(level: int = logging.INFO):
    """Configure the default output to stdout by this library.

    Parameters
    ----------
    level : int, optional
        By default ``logging.INFO``.
    """
    lg = logging.getLogger()
    lg.setLevel(level)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
        datefmt="%m/%d %H:%M:%S",
    )
    ch.setFormatter(formatter)
    lg.addHandler(ch)


def _dot_arccos(lineA, lineB):
    # Get nicer vector form
    vA = [(lineA[0] - lineA[2]), (lineA[1] - lineA[3])]
    vB = [(lineB[0] - lineB[2]), (lineB[1] - lineB[3])]
    # Get dot prod
    dot_prod = np.dot(vA, vB)
    # Get magnitudes, Get cosine value, Get angle in radians and then
    # convert to degrees
    return np.arccos(
        np.clip(dot_prod / (np.linalg.norm(vA) * np.linalg.norm(vB)), -1, 1)
    )


def _line_metric_4(l1, l2):
    """Custom metric: (distance + const)*exp"""
    num_min = np.argmin(
        [
            np.linalg.norm([(l1[0] - l1[2]), (l1[1] - l1[3])]),
            np.linalg.norm([(l2[0] - l2[2]), (l2[1] - l2[3])]),
        ]
    )
    if num_min == 0:
        l_min = l1
        l_max = l2
    else:
        l_min = l2
        l_max = l1

    len_min = np.linalg.norm(l_min)
    len_max = np.linalg.norm(l_max)

    g = np.min(
        [
            np.linalg.norm([(l1[0] - l2[0]), (l1[1] - l2[1])]),
            np.linalg.norm([(l1[0] - l2[2]), (l1[1] - l2[3])]),
            np.linalg.norm([(l1[2] - l2[0]), (l1[3] - l2[1])]),
            np.linalg.norm([(l1[2] - l2[2]), (l1[3] - l2[3])]),
        ]
    )

    p1 = np.array(
        [np.mean([l_min[0], l_min[2]]), np.mean([l_min[1], l_min[3]])]
    )
    p2 = np.array([l_max[0], l_max[1]])
    p3 = np.array([l_max[2], l_max[3]])

    s = np.cross(p2 - p1, p1 - p3) / np.linalg.norm(p2 - p1)

    # Proximity
    prox_m = (g / len_min) ** 2

    # Parallelism
    parr_m = (_dot_arccos(l1, l2) * s * len_max) / (len_min * len_min)

    # Collinearity
    coll_m = (_dot_arccos(l1, l2) * s * (len_min + g)) / (len_min * len_min)

    # return [prox_m, parr_m, coll_m]
    return np.linalg.norm([prox_m, 5.0 * parr_m, 4.0 * coll_m])


def _minimum_bounding_rectangle(points):
    """Minimum bounding rectangle.

    Find the smallest bounding rectangle for a set of points.
    Returns a set of points representing the corners of the bounding box.

    Parameters
    ----------
    points :
        An nx2 matrix of coordinates

    Returns
    -------
        An nx2 matrix of coordinates
    """
    pi2 = np.pi / 2.0

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
    # both work
    rotations = np.vstack(
        [
            np.cos(angles),
            np.cos(angles - pi2),
            np.cos(angles + pi2),
            np.cos(angles),
        ]
    ).T
    # rotations = np.vstack([
    #     np.cos(angles),
    #     -np.sin(angles),
    #     np.sin(angles),
    #     np.cos(angles)]).T
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


def rod_endpoints(
    prediction: ds.DetectionResult,
    classes: Dict[int, str],
    method: str = "simple",
    expected_particles: Union[int, Dict[int, int], None] = None,
) -> Dict[int, np.ndarray]:
    """Calculates the endpoints of rods from the prediction masks.

    Parameters
    ----------
    prediction : :class:`~ParticleDetection.utils.datasets.DetectionResult`
        Prediction output of a Detectron2 network. It can also be given as
        ``prediction["instances"]`` as ``detectron2.structures.Instances`` or
        ``dict``, as long as the resulting ``dict`` contains at least the same
        keys as :class:`~ParticleDetection.utils.datasets.DetectionResult`.
    classes : dict[int, str]
        Dictionary of classes expected/possible in the prediction. The key
        being the class ID as an integer, that is the output of the
        inferring network. The value being an arbitrary string associated with
        the class, e.g. ``{1: "blue", 2: "green"}``.
    method : str
        Selection of endpoint extraction method:\n
            ``"simple"``   ->  Creates a bounding box around the masks.\n
            ``"advanced"`` ->  Creates Hough lines and clusters these.\n
        Default is ``"simple"``.
    expected_particles : Union[int, Dict[int, int], None]
        The number of expected particles defines how many particles will be in
        the output per frame. This defines how many particles are maximally
        detected and also up to which number *empty* particles will be
        inserted to match the expected amount.

        ``int``
            Only one amount is defined. The same amount is expected for all
            classes that will be detected.
        ``Dict[int, int]``
            One amount must be specified per class that is present in
            ``prediction``.
            ``expected_particles[class] = amount``
        ``None``
            No restrictions on the amount of particles per class and frame
            are imposed. How ever many particles were detected will be in the
            output.

        Default is ``None``.

    Returns
    -------
    dict[int, np.ndarray]
    """
    results = {}
    cpu_count = mp.cpu_count()
    with np.errstate(divide="ignore", invalid="ignore"):
        if "instances" in prediction.keys():
            prediction = prediction["instances"].get_fields()
        for k, v in prediction.items():
            prediction[k] = v.to("cpu")
        for i_c in classes:
            i_c_list = np.argwhere(prediction["pred_classes"] == i_c).flatten()
            segmentations = [
                prediction["pred_masks"][i_m, :, :].numpy().squeeze()
                for i_m in i_c_list
            ]
            if not len(segmentations):
                continue
            if expected_particles is not None:
                if isinstance(expected_particles, dict):
                    current_expected = expected_particles[i_c]
                elif isinstance(expected_particles, int):
                    current_expected = expected_particles
                if len(i_c_list) > current_expected:
                    # remove the detected particles with the least confident
                    # result from the output
                    segmentations = segmentations[:current_expected]
            if method == "advanced":
                if len(segmentations) <= cpu_count:
                    use_processes = len(segmentations)
                else:
                    use_processes = cpu_count
                with mp.Pool(use_processes) as p:
                    end_points = p.map(line_estimator_simple, segmentations)
            elif method == "simple":
                end_points = list(map(line_estimator_simple, segmentations))
            else:
                raise ValueError(
                    "Unknown extraction method. "
                    "Please choose between 'simple' and "
                    "'advanced'."
                )
            if expected_particles is not None:
                # add 'empty' points, if not enough have been detected
                end_points.extend(
                    [np.array(2 * [[-1.0, -1.0]])]
                    * (current_expected - len(end_points))
                )
            results[classes[i_c]] = np.array(end_points)
    return results


def line_estimator(segmentation: np.ndarray) -> np.ndarray:
    """Calculates the endpoints of rods from the segmentation mask.

    Parameters
    ----------
    segmentation : ndarray
        Boolean segmentation (bit-)mask.
    Returns
    -------
    np.ndarray
    """
    # Prob hough for line detection
    lines = probabilistic_hough_line(
        segmentation, threshold=0, line_length=10, line_gap=30
    )
    # If too short
    if not lines:
        lines = probabilistic_hough_line(
            segmentation, threshold=0, line_length=4, line_gap=30
        )
    # No endpoint estimation possible
    if not lines:
        return np.array([[-1, -1], [-1, -1]])

    # Lines to 4 dim array
    Xl = np.array(lines)
    X = np.ravel(Xl).reshape(Xl.shape[0], 4)
    # Clustering with custom metric
    db = DBSCAN(
        eps=0.0008, min_samples=4, algorithm="auto", metric=_line_metric_4
    ).fit(X)

    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels = db.labels_

    cl_count = Counter(labels)
    k = cl_count.most_common(1)[0][0]
    class_member_mask = labels == k

    xy = X[class_member_mask & core_samples_mask]

    points = xy.reshape(2 * xy.shape[0], 2)
    if points.shape[0] > 2:
        bbox = _minimum_bounding_rectangle(points)
        bord = -1  # Make rods 1 pix shorter

        # End coordinates
        if (
            np.argmin(
                [
                    np.linalg.norm(bbox[0, :] - bbox[1, :]),
                    np.linalg.norm(bbox[1, :] - bbox[2, :]),
                ]
            )
            == 0
        ):
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
    return np.array([xy1, xy2])


def line_estimator_simple(segmentation: np.ndarray) -> np.ndarray:
    """Calculates the endpoints of rods from the segmentation mask.

    Parameters
    ----------
    segmentation : ndarray
        Boolean segmentation (bit-)mask.
    Returns
    -------
    np.ndarray
    """
    idxs = np.nonzero(segmentation)
    points = np.asarray((idxs[1], idxs[0])).swapaxes(0, 1)
    if not len(points):
        return np.array([[-1.0, -1.0], [-1.0, -1.0]])
    bbox = _minimum_bounding_rectangle(points)
    bord = -5  # Make rods 1 pix shorter

    # End coordinates
    if (
        np.argmin(
            [
                np.linalg.norm(bbox[0, :] - bbox[1, :]),
                np.linalg.norm(bbox[1, :] - bbox[2, :]),
            ]
        )
        == 0
    ):
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

    return np.array([xy1, xy2])


def paste_mask_in_image_old(
    mask: torch.Tensor,
    box: torch.Tensor,
    img_h: int,
    img_w: int,
    threshold: float = 0.5,
):
    """Paste a single mask in an image.

    This is a per-box implementation of ``paste_masks_in_image``. This function
    has larger quantization error due to incorrect pixel modeling and is not
    used any more.

    Parameters
    ----------
    mask : Tensor
        A tensor of shape (Hmask, Wmask) storing the mask of a single object
        instance. Values are :math:`\\in [0, 1]`.
    box : Tensor
        A tensor of shape ``(4, )`` storing the ``x0, y0, x1, y1`` box corners
        of the object instance.
    img_h : int
        Image height.
    img_w : int
        Image width.
    threshold : float
        Mask binarization threshold :math:`\\in [0, 1]`.\n
        Default is ``0.5``.

    Returns
    -------
    Tensor :
        The resized and binarized object mask pasted into the original
        image plane (a tensor of shape ``(img_h, img_w)``).

    Note
    ----
    This function is copied from ``detectron2.layers.mask_ops``.
    """
    # Conversion from continuous box coordinates to discrete pixel coordinates
    # via truncation (cast to int32). This determines which pixels to paste the
    # mask onto.
    box = box.to(dtype=torch.int32)
    # Continuous to discrete coordinate conversion
    # An example (1D) box with continuous coordinates (x0=0.7, x1=4.3) will
    # map to a discrete coordinates (x0=0, x1=4). Note that box is mapped
    # to 5 = x1 - x0 + 1 pixels (not x1 - x0 pixels).
    samples_w = (
        box[2] - box[0] + 1
    )  # Number of pixel samples, *not* geometric width       # noqa: E501
    samples_h = (
        box[3] - box[1] + 1
    )  # Number of pixel samples, *not* geometric height      # noqa: E501

    # Resample the mask from it's original grid to the new samples_w x samples_h grid       # noqa: E501
    mask = Image.fromarray(mask.cpu().numpy())
    mask = mask.resize((samples_w, samples_h), resample=Image.BILINEAR)
    mask = np.array(mask, copy=False)

    if threshold >= 0:
        mask = np.array(mask > threshold, dtype=np.uint8)
        mask = torch.from_numpy(mask)
    else:
        # for visualization and debugging, we also
        # allow it to return an unmodified mask
        mask = torch.from_numpy(mask * 255).to(torch.uint8)

    im_mask = torch.zeros((img_h, img_w), dtype=torch.uint8)
    x_0 = max(box[0], 0)
    x_1 = min(box[2] + 1, img_w)
    y_0 = max(box[1], 0)
    y_1 = min(box[3] + 1, img_h)

    im_mask[y_0:y_1, x_0:x_1] = mask[
        (y_0 - box[1]) : (y_1 - box[1]), (x_0 - box[0]) : (x_1 - box[0])
    ]
    return im_mask


def find_world_transform(
    calibration_file: str,
    edges_cam1_dist: np.ndarray,
    edges_cam2_dist: np.ndarray,
    edges_3D: np.ndarray,
    out_json: str,
):
    """Find world transformation from camera 1 coordinate system to the desired
    world coordinate system.

    Parameters
    ----------
    calibration_file : str
        Path to a stereo calibration file
    edges_cam1_dist : np.ndarray(8,2)
        Should contain 2D coordinates of box edges (corners) on 1st camera
        view (not undistorted):\n
        [front left up, front left down, front right up, front right down,\n
        back left up, back left down, back right up, back right down],
        e.g.

        >>> np.array([[27, 36], [30, 904], [1235, 27], [1240, 903],
        ...           [183, 149], [188, 900], [1096, 140], [1098, 790]]
        ...         ).astype(float)
    edges_cam2_dist : np.ndarray(8,2)
        Should contain 2D coordinates of box edges (corners) on 2nd camera
        view (not undistorted):\n
        [front left up, front left down, front right up, front right down,\n
        back left up, back left down, back right up, back right down]
    edges_3D: np.ndarray(8,3)
        Should contain 3D coordinates of box edges (in the final world
        coordinate system). Choose coordinate system, for example with 0 at
        the center of the box, e.g.

        >>> edges_3D = np.array([[-58,40,40], [-58,-40,40], [58,40,40],
        ...                      [58,-40,40], [-58,40,-40], [-58,-40,-40],
        ...                      [58,40,-40],[58,-40,-40]]).astype(float)
    out_json : str
        Path where the resulting transformation file should be saved in JSON
        format.

    Returns
    -------
    rot_comb : np.ndarray(3,3)
        Rotation matrix
    trans_vec : np.ndarray(3,1)
        Translation vector

    Notes
    -----
    The transformation of 3D coordinates can then be performed as

    >>> p_world = rot_comb.apply(p_cam1) + trans_vec
    """
    calibration = dl.load_camera_calibration(str(calibration_file))

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    # Undistort points using the camera calibration
    edges_cam1 = cv2.undistortImagePoints(
        edges_cam1_dist, calibration["CM1"], calibration["dist1"]
    ).reshape(-1, 2)

    # Undistort points using the camera calibration
    edges_cam2 = cv2.undistortImagePoints(
        edges_cam2_dist, calibration["CM2"], calibration["dist2"]
    ).reshape(-1, 2)

    # Triangulate box corners (result in cam1 coordinate system)
    edges_triang = cv2.triangulatePoints(P1, P2, edges_cam1.T, edges_cam2.T)

    edges_triang = np.asarray(
        [p[0:3] / p[3] for p in edges_triang.transpose()]
    )

    # Estimate affine transform to coordinate system
    transform_result = cv2.estimateAffine3D(edges_triang, edges_3D)

    transform = np.array(transform_result[1])

    rot_comb = transform[0:3, 0:3]
    trans_vec = transform[0:3, 3]

    transformations = {}

    transformations["rot_comb"] = rot_comb.tolist()
    transformations["trans_vec"] = trans_vec.tolist()

    with open(out_json, "w") as fp:
        json.dump(transformations, fp)

    return rot_comb, trans_vec

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

# Matlab output
from sklearn.cluster import DBSCAN
from skimage.transform import probabilistic_hough_line
from collections import Counter
from scipy.spatial import ConvexHull
import scipy.io as sio

SHOW_ORIGINAL = True


def run_detection(dataset: Union[ds.DataSet, List[str]],
                  configuration: Union[CfgNode, str],
                  weights: str = None, classes: dict = None,
                  output_dir: str = "./", log_name: str = "detection.log",
                  visualize: bool = True, vis_random_samples: int = -1,
                  **kwargs):
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
    predictions = []
    files = []
    for d, vis in zip(dataset, to_visualize):
        if isinstance(d, dict):
            file = d["file_name"]
        else:
            file = d
        im = cv2.imread(file)
        outputs = predictor(im)
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
        points = rod_endpoints(outputs, classes)
        save_to_mat(os.path.join(output_dir, os.path.basename(file)), points)


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


# Custom metric: (distance + const)*exp
def line_metric_4(l1, l2):
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


# Minimum bounding rectangle (parallelogram?)
def minimum_bounding_rectangle(points):
    """
    Find the smallest bounding rectangle for a set of points.
    Returns a set of points representing the corners of the bounding box.

    :param points: an nx2 matrix of coordinates
    :rval: an nx2 matrix of coordinates
    """
    from scipy.ndimage.interpolation import rotate
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


def save_to_csv(file_name, points: dict):
    """Saves rod endpoints of one image."""
    # TODO


def save_to_mat(file_name, points: dict):
    """Saves rod endpoints of one image to be used in MATLAB."""
    for idx, vals in points.items():
        if not vals.size:
            # skip classes without saved points
            continue
        dt = np.dtype(
            [('Point1', np.float, (2,)), ('Point2', np.float, (2,))])
        arr = np.zeros((vals.shape[0],), dtype=dt)

        arr[:]['Point1'] = vals[:, 0, :]
        arr[:]['Point2'] = vals[:, 1, :]

        sio.savemat(file_name + f"_{idx}.mat", {'rod_data_links': arr})


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

                if points.shape[0] == 2:
                    print(points)
                    xy1 = points[0, :]
                    xy2 = points[1, :]
                XY.append(np.array([xy1, xy2]))

            results[classes[i_c]] = np.array(XY)
    return results

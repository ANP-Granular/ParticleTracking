# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev
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
Functions to export a Detectron2 model as a pure pytorch model and functions to
 export its output to other formats.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       31.10.2022

"""
import json
import logging
from pathlib import Path
from typing import Literal, Union

import cv2
import numpy as np
import pandas as pd
import scipy.io as sio
import torch
from detectron2.config import CfgNode
from detectron2.data.detection_utils import read_image
from detectron2.engine import DefaultPredictor
from detectron2.export import TracingAdapter
from skimage.measure import approximate_polygon

import ParticleDetection.utils.data_conversions as d_conv
import ParticleDetection.utils.datasets as ds
import ParticleDetection.utils.helper_funcs as hf

# Don't remove, registers model parts in detectron2
from detectron2.projects import point_rend  # noqa: F401 # isort: skip

_logger = logging.getLogger(__name__)
EXPORT_OPTIONS = Literal["cpu", "cuda"]


def get_sample_img(sample: Path) -> torch.Tensor:
    """Loads an image into the format necessary for inference by a Detectron2
    model.
    """
    img = read_image(sample, format="BGR")
    img = torch.from_numpy(np.ascontiguousarray(img.transpose(2, 0, 1)))
    return img


def export_model(
    config_path: Path,
    weights_path: Path,
    sample_img: Path,
    option: EXPORT_OPTIONS = "cuda",
) -> None:
    """Exports a Detectron2 model to be usable with just pytorch.

    Parameters
    ----------
    config_path : Path
        File that holds the model's configuration in yaml format.
    weights_path : Path
        File that holds the trained model's weights.
    sample_img : Path
        Image to be used to trace the model.
    option : EXPORT_OPTIONS, optional
        Option whether to restrict the exported model to be used on the CPU or
        to also allow the use of a GPU.\n
        By default ``"cuda"``.

    Note
    ----
    The GPU version then requires the pytorch GPU version to be installed.
    The CPU version can be run with both, pytorch's CPU and GPU version.
    """

    def inference_func(model, image):
        inputs = [{"image": image}]
        return model.inference(inputs, do_postprocess=False)[0]

    cfg = CfgNode(CfgNode.load_yaml_with_base(str(config_path.resolve())))
    cfg.MODEL.WEIGHTS = str(weights_path.resolve())
    cfg.MODEL.DEVICE = option
    image = get_sample_img(sample_img)
    inputs = tuple(image.clone() for _ in range(1))
    model = DefaultPredictor(cfg).model
    wrapper = TracingAdapter(model, inputs, inference_func)
    wrapper.eval()
    with torch.no_grad():
        traced_model = torch.jit.trace(wrapper, inputs)
    # Save to disk
    save_path = Path(f"./model_{cfg.MODEL.DEVICE}.pt").resolve()
    torch.jit.save(traced_model, str(save_path))
    _logger.info(f"Exported model to '{str(save_path)}'")


def annotation_to_json(
    prediction: ds.DetectionResult,
    image: Union[Path, str],
    classes: dict = None,
    output_dir: Union[Path, str] = Path(),
    *,
    filename: str = "extracted_meta_data.json",
    **_,
):
    """Saves detected object masks in the metadata format used for model
    training.

    .. hint::
        This function is intended to be used as a saving function with
        :func:`~ParticleDetection.modelling.runners.detection.detect`.

    Parameters
    ----------
    prediction : :class:`~ParticleDetection.utils.datasets.DetectionResult`
        Prediction output of a Detectron2 network. It can also be given as
        ``prediction["instances"]`` as ``detectron2.structures.Instances`` or
        ``dict``, as long as the resulting ``dict`` contains at least the same
        keys as :class:`~ParticleDetection.utils.datasets.DetectionResult`.
    image : Union[Path, str]
        Path to image that `prediction` was created from.
    classes: dict, optional
        Dictionary of classes detectable by the model with\n
        ``{key}``  ->  Index of class in the model\n
        ``{value}`` ->  Name of the class\n
        By default ``None``.
    output_dir : Path | str, optional
        Path to a folder the output file will be written to.\n
        By default ``Path()``.
    filename : str, optional
        Name of the ``*.json`` file the annotation data should be saved in.
        Already existing data for an image in this file will be overwritten.\n
        By default ``"extracted_meta_data.json"``.
    """
    meta_data = {}
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)
    output = (output_dir / filename).resolve()
    if output.exists():
        try:
            with open(output, "r") as f:
                meta_data = json.load(f)
        except json.JSONDecodeError:
            # overwrite the file
            _logger.warning(
                "Metadata file is not readable and will "
                f"be overwritten: {output}"
            )
    if isinstance(image, str):
        image = Path(image)
    image = image.resolve()
    image_size = image.stat().st_size
    image_id = image.name + str(image_size)

    meta_data[image_id] = {
        "filename": image.name,
        "size": image_size,
        "regions": [],
        "file_attributes": {},
    }

    if "instances" in prediction.keys():
        prediction = prediction["instances"].get_fields()
    for k, v in prediction.items():
        prediction[k] = v.to("cpu")

    if classes is None:
        classes = {
            cl: "not_defined"
            for cl in set(prediction["pred_classes"].tolist())
        }

    for i in range(len(prediction["pred_masks"])):
        predicted_class = int(prediction["pred_classes"][i])
        region = {
            "shape_attributes": {
                "name": "polygon",
                "all_points_x": [],
                "all_points_y": [],
            },
            "region_attributes": {
                "name": classes[predicted_class],
                "type": str(predicted_class),
            },
        }
        idxs = np.nonzero(prediction["pred_masks"][i])
        # [outer_points, 2]
        points = np.asarray((idxs[:, 1], idxs[:, 0])).swapaxes(0, 1)

        hull = cv2.convexHull(points).squeeze()
        if len(hull) > 20:
            hull_prev = len(hull)
            hull = approximate_polygon(hull, 1)
            if hull_prev == len(hull):
                _logger.warning(
                    "No simplification could be performed for a segmentation "
                    f"polygon with {hull_prev} nodes."
                )

        region["shape_attributes"]["all_points_x"] = hull[:, 0].tolist()
        region["shape_attributes"]["all_points_y"] = hull[:, 1].tolist()

        meta_data[image_id]["regions"].append(region)

    with open(output, "w") as f:
        _logger.info(f"Saving metadata to {output}")
        json.dump(meta_data, f, indent=2)


def rods_to_mat(
    prediction: ds.DetectionResult,
    image: Union[Path, str],
    classes: dict = None,
    output_dir: Union[Path, str] = Path(),
    *_,
    **kwargs,
) -> None:
    """Extract rod enpoint positions from detected object masks and save them
    to ``*.mat`` files.

    The generated ``*.mat`` contain one variable `rod_data_links` with each
    rod being represented by a `Point1` and `Point2`.

    .. hint::
        This function is intended to be used as a saving function with
        :func:`~ParticleDetection.modelling.runners.detection.detect`.

    Parameters
    ----------
    prediction : :class:`~ParticleDetection.utils.datasets.DetectionResult`
        Prediction output of a Detectron2 network. It can also be given as
        ``prediction["instances"]`` as ``detectron2.structures.Instances`` or
        ``dict``, as long as the resulting ``dict`` contains at least the same
        keys as :class:`~ParticleDetection.utils.datasets.DetectionResult`.
    image : Union[Path, str]
        Path to image that `prediction` was created from.
    classes : dict, optional
        Dictionary of classes detectable by the model with\n
        ``{key}``  ->  Index of class in the model\n
        ``{value}`` ->  Name of the class\n
        By default ``None``.
    output_dir : Union[Path, str]
        Path to a folder the output file will be written to.\n
        By default ``Path()``.
    **kwargs : dict, optional
        Keywords, that are propagated to
        :func:`~ParticleDetection.utils.helper_funcs.rod_endpoints`:\n
        `method`: Literal["simple", "advanced"]\n
        `expected_particles` : Union[int, Dict[int, int], None]

    See also
    --------
    :func:`~ParticleDetection.utils.helper_funcs.rod_endpoints`
    """
    if "instances" in prediction.keys():
        prediction = prediction["instances"].get_fields()
    if "pred_masks" not in prediction.keys():
        return

    if isinstance(image, str):
        image = Path(image)
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)
    file_name_tmp = str(output_dir / image.stem) + "_{}.mat"

    method = kwargs.pop("method", "simple")
    expected_particles = kwargs.pop("expected_particles", None)
    points = hf.rod_endpoints(prediction, classes, method, expected_particles)

    for idx, vals in points.items():
        if not vals.size:
            # skip classes without saved points
            continue
        dt = np.dtype([("Point1", float, (2,)), ("Point2", float, (2,))])
        arr = np.zeros((vals.shape[0],), dtype=dt)

        arr[:]["Point1"] = vals[:, 0, :]
        arr[:]["Point2"] = vals[:, 1, :]

        sio.savemat(file_name_tmp.format(idx), {"rod_data_links": arr})


def rods_to_csv(
    prediction: ds.DetectionResult,
    image: Union[Path, str, np.ndarray],
    classes: dict = None,
    output_dir: Union[Path, str] = Path(),
    *,
    filename: str = "extracted_rods.csv",
    **kwargs,
) -> None:
    """Extract rod enpoint positions from detected object masks and save them
    to ``*.csv`` files.

    For each detected object, two enpoints are determined from the detected
    segmentation mask. These endpoints are then saved in ``*.csv`` format
    described by :data:`~ParticleDetection.utils.datasets.DEFAULT_COLUMNS`.
    The data is either saved into a new file, given by ``filename`` and
    ``output_dir`` or integrated into this file, if it already exists.

    .. hint::
        This function is intended to be used as a saving function with
        :func:`~ParticleDetection.modelling.runners.detection.detect`.

    Parameters
    ----------
    prediction : :class:`~ParticleDetection.utils.datasets.DetectionResult`
        Prediction output of a Detectron2 network. It can also be given as
        ``prediction["instances"]`` as ``detectron2.structures.Instances`` or
        ``dict``, as long as the resulting ``dict`` contains at least the same
        keys as :class:`~ParticleDetection.utils.datasets.DetectionResult`.
    image : Union[Path, str, np.ndarray]
        (Path to ) the image that `prediction` was created from.
    classes : dict, optional
        _description_\n
        By default ``None``.
    output_dir : Union[Path, str], optional
        Path to a folder the output file will be written to.\n
        By default ``Path()``.
    filename : str, optional
        Name of the ``*.csv`` file the rod position data should be saved in.
        Already existing data for an image in this file might get
        overwritten.\n
        By default ``"extracted_rods.csv"``.
    **kwargs : dict, optional
        The following keywords are used to determine the used
        frame-camera combination of the image used to create the
        ``prediction``. This allows the proper saving when a dataset format is
        given to the
        :func:`~ParticleDetection.modelling.runners.detection.detect` function
        instead of a list of files.\n
        `cam1_name` : str\n
        `cam2_name` : str\n
        `frames` : Iterable[int]\n
        `dataset_format` : str\n
        The following keyword arguments are passed to
        :func:`~ParticleDetection.utils.helper_funcs.rod_endpoints`:\n
        `method`: Literal["simple", "advanced"]\n
        `expected_particles` : Union[int, Dict[int, int], None]

    See also
    --------
    :func:`~ParticleDetection.utils.datasets.replace_missing_rods`
    :func:`~ParticleDetection.utils.datasets.add_points`
    :func:`~ParticleDetection.utils.helper_funcs.rod_endpoints`
    :func:`~ParticleDetection.utils.data_conversions.csv_extract_colors`
    """
    if "instances" in prediction.keys():
        prediction = prediction["instances"].get_fields()
    if "pred_masks" not in prediction.keys():
        return
    cam_1 = kwargs.get("cam1_name", None)
    cam_2 = kwargs.get("cam2_name", None)
    frames = kwargs.get("frames", None)
    dataset = kwargs.get("dataset_format", "")
    method = kwargs.pop("method", "simple")
    expected_particles = kwargs.pop("expected_particles", None)

    output_file = Path(output_dir) / filename
    if not output_file.exists():
        cols = [col.format(id1=cam_1, id2=cam_2) for col in ds.DEFAULT_COLUMNS]
        data = pd.DataFrame(columns=cols)
    else:
        data = pd.read_csv(output_file, sep=",", index_col=0)

    this_frame = -1
    this_cam = ""
    if frames is not None:
        for frame in frames:
            if cam_1 is not None and (
                dataset.format(cam_id=cam_1, frame=frame) == image
            ):
                this_frame = frame
                this_cam = cam_1
                break
            if cam_2 is not None and (
                dataset.format(cam_id=cam_2, frame=frame) == image
            ):
                this_frame = frame
                this_cam = cam_2
                break
    else:
        if cam_1 is not None and (
            dataset.format(cam_id=cam_1, frame=frame) == image
        ):
            this_cam = cam_1

        if cam_2 is not None and (
            dataset.format(cam_id=cam_2, frame=frame) == image
        ):
            this_cam = cam_2

    points = hf.rod_endpoints(prediction, classes, method, expected_particles)
    data = ds.add_points(points, data, this_cam, this_frame)

    data.reset_index(drop=True, inplace=True)
    data = ds.replace_missing_rods(data, cam_1, cam_2)
    data.to_csv(output_file, ",")
    d_conv.csv_extract_colors(str(output_file))

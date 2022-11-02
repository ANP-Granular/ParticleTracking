"""
Functions to export a Detectron2 model as a pure pytorch model.

Author:     Adrian Niemann (adrian.niemann@ovgu.de)
Date:       31.10.2022

"""
import sys
import logging
from pathlib import Path
from typing import Literal
import torch
import numpy as np
from detectron2.config import CfgNode
from detectron2.engine import DefaultPredictor
# Don't remove, registers model parts in detectron2
from detectron2.projects import point_rend                      # noqa: F401
from detectron2.export import TracingAdapter
from detectron2.data.detection_utils import read_image


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

EXPORT_OPTIONS = Literal["cpu", "cuda"]


def get_sample_img(sample: Path) -> torch.Tensor:
    """Loads an image into the format necessary for inference by a Detectron2
    model.
    """
    img = read_image(sample, format="BGR")
    img = torch.from_numpy(np.ascontiguousarray(img.transpose(2, 0, 1)))
    return img


def export_model(config_path: Path, weights_path: Path, sample_img: Path,
                 option: EXPORT_OPTIONS = "cuda") -> None:
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
        to also allow the use of a GPU.
        By default "cuda".

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
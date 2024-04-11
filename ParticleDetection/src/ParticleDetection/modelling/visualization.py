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
Functions to visualize predictions of Detectron2 models.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       11.08.2022

"""
import logging
import os
from typing import Iterable, Union

import cv2
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import torch
from detectron2.utils.visualizer import GenericMask

_logger = logging.getLogger(__name__)


def visualize(
    prediction,
    original: Union[dict, str, np.ndarray],
    hide_tags=True,
    output_dir="",
    colors: Iterable = None,
    **_,
):
    """Visualizes predictions on one image with/without it's ground truth.

    Parameters
    ----------
    prediction
        Predictions of a one image, for details see the Detectron2
        documentation.
    original : Union[dict, str, ndarray]
        Is either the full dataset entry with all metadata, just the path to
        the image file used during inference or the loaded image itself.\n
        ``dict``    --->    full dataset entry\n
        ``str``     --->    path to image\n
        ``ndarray`` --->    image in BGR format\n
    hide_tags : bool, optional
        Flag to remove the ``"scores"`` field, such that it is not
        visualized.\n
        By default ``True``.
    output_dir : str, optional
        Path to the intended output directory. This directory must exist prior
        to running this function.\n
        By default ``""``.
    colors : Iterable, optional
        Specifies the color used during plotting for each class that is
        predictable by the model. The colors of the ``"tab10"`` colormap will
        be used by default.\n
        By default ``None``.
    """
    if isinstance(original, dict):
        im = cv2.imread(original["file_name"])
    elif isinstance(original, np.ndarray):
        im = original
    else:
        im = cv2.imread(original)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

    # Remove unnecessary information before drawing
    to_draw = prediction["instances"].to("cpu")
    if hide_tags:
        del to_draw._fields["scores"]
        del to_draw._fields["pred_boxes"]

    fig = None
    if isinstance(original, dict):
        # Display original as well
        fig_title = os.path.basename(original["file_name"])
        fig = create_figure(im, to_draw, original, colors)
    elif isinstance(original, str):
        fig_title = os.path.basename(original)
        fig = create_figure(im, to_draw, None, colors)
    else:
        unknown_id = 0
        while True:
            fig_title = f"unkwown_img_{unknown_id:05d}.png"
            if output_dir:
                save_path = os.path.join(output_dir, fig_title)
                if not os.path.exists(save_path):
                    break
            unknown_id += 1

        fig = create_figure(im, to_draw, None, colors)

    if not hide_tags:
        if "pred_keypoints" in to_draw._fields:
            # Keypoint visualization
            ax = fig.axes[0]
            kps = to_draw.pred_keypoints.numpy()
            ax.plot(kps[:, :, 0].squeeze().T, kps[:, :, 1].squeeze().T)

    if output_dir:
        plt.savefig(os.path.join(output_dir, fig_title))


def create_figure(img, predictions, gt: dict = None, colors: Iterable = None):
    """Plots an image with the predictions from a model overlayed.

    Can plot either just the image with the given predictions, e.g.
    segmentation masks, or together with the ground-truth data. The latter
    produces a figure of vertically two stacked images, where the lower one
    shows the ground-truth data.

    Parameters
    ----------
    img : ndarray
        Loaded image file with dimensions ``[h, w, c]``.
    predictions
        Predictions of a one image, for details see the Detectron2
        documentation.
    gt : dict, optional
        A full ground-truth dataset entry with all metadata, e.g. keypoints.\n
        By default ``None``.
    colors : Iterable, optional
        Specifies the color used during plotting for each class that is
        predictable by the model. The colors of the "tab10" colormap will be
        used by default.\n
        By default ``None``.

    Returns
    -------
    Figure
    """
    width, height = img.shape[1], img.shape[0]
    if colors is None:
        colors = plt.get_cmap("tab10").colors

    def add_outlines(mask_data, axes, color=None, confidences=None):
        """Adds the masks data as outlines to the axes."""
        if isinstance(mask_data, torch.Tensor):
            mask_data = mask_data.numpy()
        masks = [GenericMask(x, height, width) for x in mask_data]
        for m, c, s in zip(masks, color, confidences):
            for segment in m.polygons:
                polygon = mpl.patches.Polygon(
                    segment.reshape(-1, 2), fill=False, color=c
                )
                axes.add_patch(polygon)
            axes.text(*m.bbox()[0:2], f"{s.numpy():.2f}")
        return axes

    def get_colors(len_data, class_data=None):
        if class_data is None:
            return len_data * ["black"]
        else:
            return [colors[lbl] for lbl in class_data]

    try:
        scores = predictions.scores
    except KeyError:
        scores = None

    fig = plt.figure(frameon=False)
    dpi = fig.get_dpi()
    # add a small 1e-2 to avoid precision lost due to matplotlib's truncation
    # (https://github.com/matplotlib/matplotlib/issues/15363)
    if gt:
        fig.set_size_inches(
            (width + 1e-2) / dpi,
            2 * (height + 1e-2) / dpi,
        )
        # Prediction axes
        ax1 = fig.add_axes([0, 0.5, 1, 0.5])
        ax1.imshow(img)
        ax1.axis("off")
        try:
            class_colors = get_colors(
                len(predictions.pred_classes), predictions.pred_classes
            )
            add_outlines(predictions.pred_masks, ax1, class_colors, scores)
        except AttributeError:
            # predictions does not have mask data, e.g. because it predicted
            # only keypoints
            _logger.warning(
                "Predictions don't have segmentation masks. "
                "Skipping mask visualization..."
            )

        # Groundtruth axes
        ax2 = fig.add_axes([0, 0, 1, 0.5])
        ax2.imshow(img)
        ax2.axis("off")
        try:
            gt_masks = [anno["segmentation"] for anno in gt["annotations"]]
            gt_classes = [anno["category_id"] for anno in gt["annotations"]]
            class_colors = get_colors(len(gt_classes), gt_classes)
            add_outlines(gt_masks, ax2, class_colors)
        except IndexError:
            # annotations don't have the "segmentation" field, e.g. because
            # they only have keypoints
            _logger.warning(
                "Ground-truth does not have segmentation masks. "
                "Skipping mask visualization..."
            )

    else:
        fig.set_size_inches(
            (width + 1e-2) / dpi,
            (height + 1e-2) / dpi,
        )
        # Prediction axes
        ax1 = fig.add_axes([0, 0, 1, 1])
        ax1.imshow(img)
        ax1.axis("off")
        try:
            class_colors = get_colors(
                len(predictions.pred_classes), predictions.pred_classes
            )
            add_outlines(predictions.pred_masks, ax1, class_colors, scores)
        except AttributeError:
            # predictions does not have mask data, e.g. because it predicted
            # only keypoints
            _logger.warning(
                "Predictions don't have segmentation masks. "
                "Skipping mask visualization..."
            )

    return fig

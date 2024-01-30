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
Collection of custom Detectron2 objects to provide a customized training
process with more sophisticated outputs.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       31.10.2022

"""
import copy
import datetime
import logging
import time
from typing import List

import detectron2.data.detection_utils as utils
import detectron2.data.transforms as T
import detectron2.utils.comm as comm
import numpy as np
import torch
from detectron2.config.config import CfgNode
from detectron2.data import (
    DatasetMapper,
    build_detection_test_loader,
    build_detection_train_loader,
)
from detectron2.engine.defaults import DefaultTrainer
from detectron2.engine.hooks import HookBase
from detectron2.evaluation import COCOEvaluator, DatasetEvaluators
from detectron2.utils.events import (
    CommonMetricPrinter,
    EventWriter,
    get_event_storage,
)
from detectron2.utils.logger import log_every_n_seconds


class CustomTrainer(DefaultTrainer):
    augmentations: List[T.Augmentation] = []

    @classmethod
    def build_evaluator(cls, cfg: CfgNode, dataset_name: str):
        """Build a custom evaluator depending on the detection task.

        Parameters
        ----------
        cfg : CfgNode
            Detectron2 network configuration with allowed TASK field of:\n
            ``"None"`` -> will be changed to ``"segm"``\n
            ``"segm"`` -> results in an evaluator for a segmentation task\n
            ``"keypoints"`` -> results in an evaluator for a keypoint detection
            task
        dataset_name : str
            Name of a dataset that is registered in the Detectron2 framework,
            that is used as the ``test`` dataset of the constructed evaluator.

        Returns
        -------
        DatasetEvaluators
        """
        # TODO: What exactly is max_dets_per_image controlling/ how does it
        #  influence the metrics?
        try:
            tasks = [cfg.TASKS]
            if "None" in tasks:
                return DatasetEvaluators([])
        except AttributeError:
            tasks = ["segm"]

        if "keypoints" in tasks:
            sigmas = np.array([0.25, 0.25]) / 10.0
            sigmas = sigmas.tolist()
        else:
            sigmas = []

        dataset_evaluators = [
            COCOEvaluator(
                dataset_name,
                output_dir=cfg.OUTPUT_DIR,
                max_dets_per_image=cfg.TEST.DETECTIONS_PER_IMAGE,
                tasks=tuple(tasks),
                kpt_oks_sigmas=sigmas,
            )
        ]
        return DatasetEvaluators(dataset_evaluators)

    def build_writers(self):
        """Builds additional/custom writers for use during training."""
        return [
            CustomTensorboardWriter(self.cfg.OUTPUT_DIR, window_size=1),
            CommonMetricPrinter(self.cfg.SOLVER.MAX_ITER),
        ]

    def build_hooks(self):
        """
        Build a list of hooks, including the ``DefaultTrainer`` default hooks
        and a custom loss hook used during evaluation.
        """
        hooks = super().build_hooks()
        hooks.insert(
            -1,
            EvalLossHook(
                self.cfg.TEST.EVAL_PERIOD,  # 1,
                self.model,
                build_detection_test_loader(
                    self.cfg,
                    self.cfg.DATASETS.TEST[0],
                    DatasetMapper(
                        self.cfg, True
                    ),  # TODO: might need replacement
                ),
            ),
        )
        return hooks

    @classmethod
    def build_train_loader(cls, cfg):
        """Custom loader for training data.

        Parameters
        ----------
        cfg : CfgNode
            Detectron2 network configuration.

        Returns
        -------
        Iterable
        """
        # Code from DatasetMapper.from_config(cls, cfg, is_train: bool = True)
        # to properly load settings from the configuration
        is_train = True
        import detectron2.data.detection_utils as du

        augs = du.build_augmentation(cfg, is_train)
        if cfg.INPUT.CROP.ENABLED:
            augs.insert(
                0, T.RandomCrop(cfg.INPUT.CROP.TYPE, cfg.INPUT.CROP.SIZE)
            )
            recompute_boxes = cfg.MODEL.MASK_ON
        else:
            recompute_boxes = False
        mapper_conf = {
            "is_train": is_train,
            "augmentations": augs,
            "image_format": cfg.INPUT.FORMAT,
            "use_instance_mask": cfg.MODEL.MASK_ON,
            "instance_mask_format": cfg.INPUT.MASK_FORMAT,
            "use_keypoint": cfg.MODEL.KEYPOINT_ON,
            "recompute_boxes": recompute_boxes,
        }
        if cfg.MODEL.KEYPOINT_ON:
            mapper_conf["keypoint_hflip_indices"] = (
                utils.create_keypoint_hflip_indices(cfg.DATASETS.TRAIN)
            )
        if cfg.MODEL.LOAD_PROPOSALS:
            mapper_conf["precomputed_proposal_topk"] = (
                cfg.DATASETS.PRECOMPUTED_PROPOSAL_TOPK_TRAIN
                if is_train
                else cfg.DATASETS.PRECOMPUTED_PROPOSAL_TOPK_TEST
            )

        # Additional custom augmentations
        if cls.augmentations:
            mapper_conf["augmentations"].extend(cls.augmentations)

        return build_detection_train_loader(
            cfg, mapper=DatasetMapper(**mapper_conf)
        )


# Currently not used
class CompleteMapper(DatasetMapper):  # pragma: no cover
    """Provides annotation data in training and testing context."""

    def __call__(self, dataset_dict):
        """
        Args:
            dataset_dict (dict): Metadata of one image, in Detectron2 dataset
            format.

        Returns:
            dict: a format that builtin models in detectron2 accept
        """
        dataset_dict = copy.deepcopy(
            dataset_dict
        )  # it will be modified by code below
        # USER: Write your own image loading if it's not from a file
        image = utils.read_image(
            dataset_dict["file_name"], format=self.image_format
        )
        utils.check_image_size(dataset_dict, image)

        # USER: Remove if you don't do semantic/panoptic segmentation.
        if "sem_seg_file_name" in dataset_dict:
            sem_seg_gt = utils.read_image(
                dataset_dict.pop("sem_seg_file_name"), "L"
            ).squeeze(2)
        else:
            sem_seg_gt = None

        aug_input = T.AugInput(image, sem_seg=sem_seg_gt)
        transforms = self.augmentations(aug_input)
        image, sem_seg_gt = aug_input.image, aug_input.sem_seg

        image_shape = image.shape[:2]  # h, w
        # Pytorch's dataloader is efficient on torch.Tensor due to
        # shared-memory, but not efficient on large generic data structures due
        # to the use of pickle & mp.Queue. Therefore it's important to use
        # torch.Tensor.
        dataset_dict["image"] = torch.as_tensor(
            np.ascontiguousarray(image.transpose(2, 0, 1))
        )
        if sem_seg_gt is not None:
            dataset_dict["sem_seg"] = torch.as_tensor(
                sem_seg_gt.astype("long")
            )

        # USER: Remove if you don't use pre-computed proposals.
        # Most users would not need this feature.
        if self.proposal_topk is not None:
            utils.transform_proposals(
                dataset_dict,
                image_shape,
                transforms,
                proposal_topk=self.proposal_topk,
            )

        if "annotations" in dataset_dict:
            self._transform_annotations(dataset_dict, transforms, image_shape)

        return dataset_dict


class EvalLossHook(HookBase):
    """Hook to compute different losses in the training process of a network.

    This is the *copy* of the loss hook used by Detectron2 for the training
    dataset. This hook is intended for evaluating the loss on the test dataset
    during the training process.
    """

    def __init__(self, eval_period, model, data_loader):
        self._model = model
        self._period = eval_period
        self._data_loader = data_loader

    def _do_loss_eval(self):
        # Copying inference_on_dataset from evaluator.py
        total = len(self._data_loader)
        num_warmup = min(5, total - 1)

        start_time = time.perf_counter()
        total_compute_time = 0
        losses = {}
        for idx, inputs in enumerate(self._data_loader):
            if idx == num_warmup:
                start_time = time.perf_counter()
                total_compute_time = 0
            start_compute_time = time.perf_counter()
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            total_compute_time += time.perf_counter() - start_compute_time
            iters_after_start = idx + 1 - num_warmup * int(idx >= num_warmup)
            seconds_per_img = total_compute_time / iters_after_start
            if idx >= num_warmup * 2 or seconds_per_img > 5:
                total_seconds_per_img = (
                    time.perf_counter() - start_time
                ) / iters_after_start
                eta = datetime.timedelta(
                    seconds=int(total_seconds_per_img * (total - idx - 1))
                )
                log_every_n_seconds(
                    logging.INFO,
                    "Loss on Validation  done {}/{}. {:.4f} s / img. ETA={}".format(  # noqa: E501
                        idx + 1, total, seconds_per_img, str(eta)
                    ),
                    n=5,
                )
            losses = self._get_loss(inputs, losses)

        total_loss = 0
        for loss, values in losses.items():
            next_loss = np.mean(values)
            self.trainer.storage.put_scalar("test/" + loss, next_loss)
            total_loss += next_loss
        self.trainer.storage.put_scalar("test/total_loss", total_loss)
        comm.synchronize()
        return losses

    def _get_loss(self, data, losses: dict):
        # How loss is calculated on train_loop
        metrics_dict = self._model(data)
        for k, v in metrics_dict.items():
            float_v = 0.0
            if isinstance(v, torch.Tensor):
                float_v = v.detach().cpu().item()
            else:
                float_v = float(v)
            if k in losses.keys():
                losses[k].append(float_v)
            else:
                losses[k] = [float_v]
        return losses

    def after_step(self):
        next_iter = self.trainer.iter + 1
        is_final = next_iter == self.trainer.max_iter
        if is_final or (self._period > 0 and next_iter % self._period == 0):
            self._do_loss_eval()
        self.trainer.storage.put_scalars(timetest=12)


class CustomTensorboardWriter(EventWriter):
    """
    Write all scalars to a tensorboard file.
    """

    def __init__(self, log_dir: str, window_size: int = 20, **kwargs):
        """
        Args:
            log_dir (str):
                The directory to save the output events
            window_size (int):
                The scalars will be median-smoothed by this window size

            kwargs:
                Other arguments passed to
                ``torch.utils.tensorboard.SummaryWriter()``
        """
        self._window_size = window_size
        from torch.utils.tensorboard import SummaryWriter

        self._writer = SummaryWriter(log_dir + "/test", **kwargs)
        self._writers = {
            "test": SummaryWriter(log_dir + "/test"),
            "train": SummaryWriter(log_dir + "/train"),
        }
        self._last_write = -1
        self.train_kw = ["fast_rcnn"]

    def write(self):
        storage = get_event_storage()
        # custom stuff
        new_last_write = self._last_write
        for k, (v, iter) in storage.latest_with_smoothing_hint(
            self._window_size
        ).items():
            if iter > self._last_write:
                for id, writer in self._writers.items():
                    if id == "test":
                        if "test" in k:
                            if k == "timetest":
                                writer.add_scalar("time/time", v, iter)
                            else:
                                new_k = k.split("/")[-1]
                                if "loss" in new_k:
                                    writer.add_scalar("loss/" + new_k, v, iter)
                                else:
                                    writer.add_scalar(new_k, v, iter)
                        elif "segm/" in k:
                            writer.add_scalar(k, v, iter)
                        elif "keypoints/" in k:
                            writer.add_scalar(k, v, iter)

                    elif id == "train":
                        if "test" not in k:
                            if "segm/" in k:
                                continue
                            if "keypoints/" in k:
                                continue
                            writer.add_scalar("all/" + k, v, iter)
                            if "loss" in k:
                                writer.add_scalar("loss/" + k, v, iter)
                            elif "time" in k:
                                writer.add_scalar("time/" + k, v, iter)

                new_last_write = max(new_last_write, iter)
        self._last_write = new_last_write

        # storage.put_{image,histogram} is only meant to be used by
        # tensorboard writer. So we access its internal fields directly from
        # here.
        if len(storage._vis_data) >= 1:
            for img_name, img, step_num in storage._vis_data:
                self._writer.add_image(img_name, img, step_num)
            # Storage stores all image data and rely on this writer to clear
            # them. As a result it assumes only one writer will use its image
            # data. An alternative design is to let storage store limited
            # recent data (e.g. only the most recent image) that all writers
            # can access. In that case a writer may not see all image data if
            # its period is long.
            storage.clear_images()

        if len(storage._histograms) >= 1:
            for params in storage._histograms:
                self._writer.add_histogram_raw(**params)
            storage.clear_histograms()

    def close(self):
        # doesn't exist when the code fails at import
        if hasattr(self, "_writer"):
            self._writer.close()

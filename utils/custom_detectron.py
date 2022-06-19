from detectron2.evaluation import inference_context
from detectron2.utils.logger import log_every_n_seconds
from detectron2.data import DatasetMapper, build_detection_test_loader
import detectron2.utils.comm as comm
import torch
import time
import datetime
import logging
import copy
import numpy as np

from detectron2.engine.hooks import HookBase, PeriodicWriter
from detectron2.config.config import CfgNode
from detectron2.engine.defaults import DefaultTrainer
from detectron2.evaluation import COCOEvaluator, DatasetEvaluators, \
    DatasetEvaluator
import detectron2.data.detection_utils as utils
import detectron2.data.transforms as T
from detectron2.utils.events import EventWriter, get_event_storage


class CustomEvaluator(DatasetEvaluator):
    def process(self, inputs, outputs):
        print(f"CustomEvaluator: {outputs}")


class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_evaluator(cls, cfg: CfgNode, dataset_name: str):
        return
        # dataset_evaluators = []
        # dataset_evaluators.append(COCOEvaluator(dataset_name,
        #                                         output_dir=cfg.OUTPUT_DIR))
        # # dataset_evaluators.append(CustomEvaluator())
        # return DatasetEvaluators(dataset_evaluators)

    def build_hooks(self):
        cfg = self.cfg.clone()
        hooks = super().build_hooks()
        hooks.insert(-1, EvalLossHook(
            1, # cfg.TEST.EVAL_PERIOD,
            self.model,
            build_detection_test_loader(
                self.cfg,
                self.cfg.DATASETS.TEST[0],
                DatasetMapper(self.cfg, True)   # TODO: might need to be replaced
            )
        ))
        # TODO: testing writers
        hooks.insert(-1, PeriodicWriter([CustomTensorboardWriter(
            cfg.OUTPUT_DIR, window_size=1)]))

        return hooks

    # # TODO: finish this (it worked without it too)
    # @classmethod
    # def build_test_loader(cls, cfg, dataset_name):
    #     build_detection_test_loader(cfg, dataset_name,
    #     mapper=CompleteMapper)


class CompleteMapper(DatasetMapper):
    """Provides annotation data in training and testing context."""
    def __call__(self, dataset_dict):
        """
                Args:
                    dataset_dict (dict): Metadata of one image, in Detectron2 Dataset format.

                Returns:
                    dict: a format that builtin models in detectron2 accept
                """
        dataset_dict = copy.deepcopy(
            dataset_dict)  # it will be modified by code below
        # USER: Write your own image loading if it's not from a file
        image = utils.read_image(dataset_dict["file_name"],
                                 format=self.image_format)
        utils.check_image_size(dataset_dict, image)

        # USER: Remove if you don't do semantic/panoptic segmentation.
        if "sem_seg_file_name" in dataset_dict:
            sem_seg_gt = utils.read_image(dataset_dict.pop("sem_seg_file_name"),
                                          "L").squeeze(2)
        else:
            sem_seg_gt = None

        aug_input = T.AugInput(image, sem_seg=sem_seg_gt)
        transforms = self.augmentations(aug_input)
        image, sem_seg_gt = aug_input.image, aug_input.sem_seg

        image_shape = image.shape[:2]  # h, w
        # Pytorch's dataloader is efficient on torch.Tensor due to shared-memory,
        # but not efficient on large generic data structures due to the use of pickle & mp.Queue.
        # Therefore it's important to use torch.Tensor.
        dataset_dict["image"] = torch.as_tensor(
            np.ascontiguousarray(image.transpose(2, 0, 1)))
        if sem_seg_gt is not None:
            dataset_dict["sem_seg"] = torch.as_tensor(sem_seg_gt.astype("long"))

        # USER: Remove if you don't use pre-computed proposals.
        # Most users would not need this feature.
        if self.proposal_topk is not None:
            utils.transform_proposals(
                dataset_dict, image_shape, transforms,
                proposal_topk=self.proposal_topk
            )

        if "annotations" in dataset_dict:
            self._transform_annotations(dataset_dict, transforms, image_shape)

        return dataset_dict


class EvalLossHook(HookBase):
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
        losses = []
        for idx, inputs in enumerate(self._data_loader):
            if idx == num_warmup:
                start_time = time.perf_counter()
                total_compute_time = 0
            start_compute_time = time.perf_counter()
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            total_compute_time += time.perf_counter() - start_compute_time
            iters_after_start = idx + 1 - num_warmup * int(
                idx >= num_warmup)
            seconds_per_img = total_compute_time / iters_after_start
            if idx >= num_warmup * 2 or seconds_per_img > 5:
                total_seconds_per_img = (
                    time.perf_counter() - start_time) / iters_after_start
                eta = datetime.timedelta(
                    seconds=int(total_seconds_per_img * (total - idx - 1)))
                log_every_n_seconds(
                    logging.INFO,
                    "Loss on Validation  done {}/{}. {:.4f} s / img. ETA={}".format(
                        idx + 1, total, seconds_per_img, str(eta)
                    ),
                    n=5,
                )
            loss_batch = self._get_loss(inputs)
            losses.append(loss_batch)
        mean_loss = np.mean(losses)
        self.trainer.storage.put_scalar('test/total_loss', mean_loss)
        comm.synchronize()

        return losses

    def _get_loss(self, data):
        # How loss is calculated on train_loop
        metrics_dict = self._model(data)
        metrics_dict = {
            k: v.detach().cpu().item() if isinstance(v, torch.Tensor)
            else float(v) for k, v in metrics_dict.items()
        }
        total_losses_reduced = sum(loss for loss in metrics_dict.values())
        return total_losses_reduced

    def after_step(self):
        next_iter = self.trainer.iter + 1
        is_final = next_iter == self.trainer.max_iter
        if is_final or (self._period > 0 and next_iter % self._period == 0):
            self._do_loss_eval()
        self.trainer.storage.put_scalars(timetest=12)


# TODO:
class CustomTensorboardWriter(EventWriter):
    """
    Write all scalars to a tensorboard file.
    """

    def __init__(self, log_dir: str, window_size: int = 20, **kwargs):
        """
        Args:
            log_dir (str): the directory to save the output events
            window_size (int): the scalars will be median-smoothed by this window size

            kwargs: other arguments passed to `torch.utils.tensorboard.SummaryWriter(...)`
        """
        self._window_size = window_size
        from torch.utils.tensorboard import SummaryWriter

        self._writer = SummaryWriter(log_dir+"/test", **kwargs)
        self._writers = {
            "complete": SummaryWriter(log_dir+"/complete"),
            "test": SummaryWriter(log_dir+"/test"),
            "train": SummaryWriter(log_dir+"/train")}
        self._last_write = -1

    def write(self):
        storage = get_event_storage()
        # custom stuff
        new_last_write = self._last_write
        for k, (v, iter) in storage.latest_with_smoothing_hint(
                self._window_size).items():
            if iter > self._last_write:
                for id, writer in self._writers.items():
                    if id == "complete":
                        writer.add_scalar(k, v, iter)
                    elif id == "test":
                        if "test" in k:
                            writer.add_scalar(k.split("/")[-1], v, iter)

                new_last_write = max(new_last_write, iter)
        self._last_write = new_last_write



        # new_last_write = self._last_write
        # for k, (v, iter) in storage.latest_with_smoothing_hint(self._window_size).items():
        #     if iter > self._last_write:
        #         self._writer.add_scalar(k, v, iter)
        #         new_last_write = max(new_last_write, iter)
        # self._last_write = new_last_write

        # storage.put_{image,histogram} is only meant to be used by
        # tensorboard writer. So we access its internal fields directly from here.
        if len(storage._vis_data) >= 1:
            for img_name, img, step_num in storage._vis_data:
                self._writer.add_image(img_name, img, step_num)
            # Storage stores all image data and rely on this writer to clear them.
            # As a result it assumes only one writer will use its image data.
            # An alternative design is to let storage store limited recent
            # data (e.g. only the most recent image) that all writers can access.
            # In that case a writer may not see all image data if its period is long.
            storage.clear_images()

        if len(storage._histograms) >= 1:
            for params in storage._histograms:
                self._writer.add_histogram_raw(**params)
            storage.clear_histograms()

    def close(self):
        if hasattr(self, "_writer"):  # doesn't exist when the code fails at import
            self._writer.close()

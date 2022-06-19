import json

from detectron2.config.config import CfgNode
from detectron2.engine.defaults import DefaultTrainer
from detectron2.evaluation import COCOEvaluator, DatasetEvaluators, \
    DatasetEvaluator
from .datasets import DataSet


class CustomEvaluator(DatasetEvaluator):
    def process(self, inputs, outputs):
        print(outputs)


class CustomTrainer(DefaultTrainer):
    @classmethod
    def build_evaluator(cls, cfg: CfgNode, dataset_name: str):
        dataset_evaluators = []
        dataset_evaluators.append(COCOEvaluator(dataset_name,
                                                output_dir=cfg.OUTPUT_DIR))
        dataset_evaluators.append(CustomEvaluator())
        return DatasetEvaluators(dataset_evaluators)


def get_dataset_size(dataset: DataSet):
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

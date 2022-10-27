import sys
import pickle
import logging
from detectron2.config.config import CfgNode

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


def get_epochs(cfg: CfgNode, image_count: int) -> float:
    """Computes the achieved number of epochs with given settings and data."""
    batch_size = cfg.SOLVER.IMS_PER_BATCH
    iterations = cfg.SOLVER.MAX_ITER
    return iterations / (image_count/batch_size)


def get_iters(cfg: CfgNode, image_count: int, desired_epochs: int) -> int:
    """Computes the necessary iterations to achieve a given number of
    epochs.
    """
    batch_size = cfg.SOLVER.IMS_PER_BATCH
    return desired_epochs*(image_count/batch_size)


def write_configs(cfg: CfgNode, directory: str, augmentations=None) -> None:
    """Write a configuration to a 'config.yaml' file in a target directory."""
    with open(directory + "/config.yaml", "w") as f:
        f.write(cfg.dump())
    if augmentations is not None:
        with open(directory + "/augmentations.pkl", "wb") as f:
            pickle.dump(augmentations, f)


if __name__ == "__main__":
    pass

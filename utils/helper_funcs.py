import json
from detectron2.config.config import CfgNode
from utils.datasets import DataSet


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


def write_configs(cfg: CfgNode, directory: str) -> None:
    """Write a configuration to a 'config.yaml' file in a target directory."""
    with open(directory + "/config.yaml", "w") as f:
        f.write(cfg.dump())


def get_object_counts(dataset: DataSet):
    """Returns a list of the number of objects in each image in the dataset."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    return [len(annotations[key]["regions"]) for key in annotations.keys()]


def remove_duplicate_regions(dataset: DataSet):
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


if __name__ == "__main__":
    from utils.datasets import HGS
    remove_duplicate_regions(HGS.val)

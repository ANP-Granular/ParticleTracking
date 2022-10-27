import os
from dataclasses import dataclass
import json


DEFAULT_COLUMNS = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l',
                   'x1_{id1:s}', 'y1_{id1:s}', 'x2_{id1:s}', 'y2_{id1:s}',
                   'x1_{id2:s}', 'y1_{id2:s}', 'x2_{id2:s}', 'y2_{id2:s}',
                   'frame', 'seen_{id1:s}', 'seen_{id2:s}']


class DataSet:
    folder: str
    annotation: str
    name: str

    def __init__(self, name: str, folder: str, annotation_file: str):
        self.name = name
        self.annotation = os.path.abspath(folder+annotation_file)
        self.folder = os.path.abspath(folder)


@dataclass
class DataGroup:
    train: DataSet
    val: DataSet


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


def get_dataset_classes(dataset: DataSet):
    """Retrieve the number and IDs of thing classes in the dataset."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    classes = {0, }
    for image in list(annotations.values()):
        regions = image["regions"]
        if regions:
            for region in regions:
                try:
                    classes.add(int(region["region_attributes"]["rod_col"]))
                except KeyError:
                    continue
    return classes

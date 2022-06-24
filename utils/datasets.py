import os
import warnings
from dataclasses import dataclass
import json

import numpy as np
from PIL import Image
from typing import List, Callable

from detectron2.structures import BoxMode
from detectron2.data import DatasetCatalog, MetadataCatalog


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


def load_custom_data(dataset: DataSet) -> List[dict]:
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)

    custom_data = []
    for idx, val in enumerate(annotations.values()):
        # Skip non-annotated image entries
        if not val["regions"]:
            continue

        # Create an entry in the custom dataset
        record = {}
        filename = os.path.join(dataset.folder, val["filename"])
        width, height = Image.open(filename).size[:2]
        record["file_name"] = filename
        record["image_id"] = idx
        record["width"] = width
        record["height"] = height

        annos = val["regions"]
        objs = []
        for anno in annos:
            try:
                category_id = int(anno["region_attributes"]["rod_col"])
            except KeyError:
                category_id = 0

            anno = anno["shape_attributes"]
            px = anno["all_points_x"]
            py = anno["all_points_y"]
            # TODO: verify the polygon computation in the following two lines
            poly = [(x + 0.5, y + 0.5) for x, y in zip(px, py)]
            poly = [p for x in poly for p in x]

            obj = {
                "bbox": [np.min(px), np.min(py), np.max(px), np.max(py)],
                "bbox_mode": BoxMode.XYXY_ABS,
                "segmentation": [poly],
                "category_id": category_id,
            }
            objs.append(obj)
        record["annotations"] = objs
        custom_data.append(record)
    return custom_data


def register_dataset(dataset: DataSet,
                     generation_function: Callable = load_custom_data,
                     classes: List[str] = None):
    DatasetCatalog.register(dataset.name,
                            lambda: generation_function(dataset))
    if classes is not None:
        MetadataCatalog.get(dataset.name).set(thing_classes=classes)
    else:
        warnings.warn("No thing_classes specified! This will prohibit the use "
                      "of the built-in COCOEvaluator.")


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


if __name__ == "__main__":
    DATASETS = "../datasets"
    TRAINING = "/train"
    VALIDATION = "/val"
    ANNOTATIONS = "/via_export_json.json"
    # Set up known dataset(s) for use with Detectron2
    HGS = DataGroup(
        train=DataSet("hgs_train", DATASETS+"/hgs"+TRAINING, ANNOTATIONS),
        val=DataSet("hgs_val", DATASETS+"/hgs"+VALIDATION, ANNOTATIONS)
    )
    # Register datasets to Detectron2
    register_dataset(HGS.train, classes=["polygon"])
    register_dataset(HGS.val, classes=["polygon"])


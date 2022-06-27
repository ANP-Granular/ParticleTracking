import os
import cv2
import random

import matplotlib.pyplot as plt
from detectron2.data import MetadataCatalog
from detectron2.utils.visualizer import Visualizer, ColorMode

import utils.datasets as ds


def visualize(prediction, original, meta_data=None, hide_tags=True,
              output_dir=""):
    """Visualizes predictions on one image with it's ground truth."""
    if isinstance(original, dict):
        im = cv2.imread(original["file_name"])
    else:
        im = cv2.imread(original)

    v = Visualizer(im[:, :, ::-1], metadata=meta_data, scale=0.5,
                   instance_mode=ColorMode.IMAGE_BW)

    # Remove unnecessary information before drawing
    to_draw = prediction["instances"].to("cpu")
    if hide_tags:
        del to_draw._fields["pred_classes"]
        del to_draw._fields["scores"]
        del to_draw._fields["pred_boxes"]
    out = v.draw_instance_predictions(to_draw)

    if isinstance(original, dict):
        # Display original as well
        fig_title = os.path.basename(original["file_name"])
        fig = plt.figure(figsize=[6.4, 2*4.8])
        ax1 = plt.subplot(2, 1, 1)
        ax1.imshow(out.get_image()[:, :, ::-1])
        ax2 = plt.subplot(2, 1, 2)
        ax2.imshow(im)
        fig.suptitle(fig_title)
    else:
        fig_title = os.path.basename(original)
        plt.figure()
        plt.imshow(out.get_image()[:, :, ::-1])
        plt.title(fig_title)

    if output_dir:
        plt.savefig(os.path.join(output_dir, fig_title))
    plt.show()


# ax3.fill(x, y, facecolor='none', edgecolor='purple', linewidth=3)


def vis_single(dataset, filenames):
    filename = "FT2015_shot2_gp2_00750.jpg"
    dataset_dicts = ds.load_custom_data(dataset)
    meta_data = MetadataCatalog.get(dataset.name)

    for d in random.sample(dataset_dicts, 5):
        img = cv2.imread(d["file_name"])
        visualizer = Visualizer(img[:, :, ::-1], metadata=meta_data, scale=0.5)
        # d["annotations"] = random.sample(d["annotations"], 10)
        out = visualizer.draw_dataset_dict(d)
        plt.figure(figsize=[12.80, 7.20])
        plt.imshow(out.get_image()[:, :, ::-1])
        plt.show()


if __name__ == "__main__":
    data_folder = "../datasets/rods_c4m"
    metadata_file = "/via_export_json.json"
    val_data = ds.DataSet("c4m_val", data_folder + "/val", metadata_file)
    classes = ["blue", "green", "orange", "purple", "red", "yellow", "black",
               "lilac", "brown"]
    ds.register_dataset(val_data, classes=classes)

    vis_single(val_data, 1)

import json

def change_visibiliy(file: str):
    """Changes the visibility flag for all keypoints in a file of keypoint 
    training data.

    Parameters
    ----------
    file : str
        Path to the annotations file that's changed.
    """
    with open(file, "r") as f:
        to_change = json.load(f)
    for idx_f, val_f in to_change.items():
        for idx_r, reg in enumerate(val_f["regions"]):
            new_points = reg["keypoints"]
            new_points[2] = 2.0
            new_points[-1] = 2.0
            to_change[idx_f]["regions"][idx_r]["keypoints"] = new_points
    with open(file, "w") as f:
        json.dump(to_change, f)


def change_class(file: str):
    """Changes all class labels to "0" in a file of keypoint training data.

    Parameters
    ----------
    file : str
        Path to the annotations file that's changed.
    """
    with open(file, "r") as f:
        to_change = json.load(f)

    for idx_f, val_f in to_change.items():
        for idx_r, reg in enumerate(val_f["regions"]):
            to_change[idx_f]["regions"][idx_r]["region_attributes"]["rod_col"]\
                = 0

    with open(file, "w") as f:
        json.dump(to_change, f)


if __name__ == "__main__":
    # change_visibiliy("../datasets/rods_c4m/train/via_export_json_keypoints.json")
    change_class("../datasets/rods_c4m/train/via_export_json_keypoints.json")


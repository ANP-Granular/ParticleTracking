import os
from detectron2.config import CfgNode
import ParticleDetection.utils.datasets as ds
from ParticleDetection.modelling.runners import detection


def main():
    # Input/Output configurations
    input_folder = "./run_example1"
    model_weights = "model_final.pth"
    weights_path = os.path.join(input_folder, model_weights)
    configs = "config.yaml"
    output_folder = "./inference_example1"

    cfg = CfgNode(CfgNode.load_yaml_with_base(os.path.join(input_folder,
                                                           configs)))

    classes = {0: 'blue', 1: 'green', 2: 'orange', 3: 'purple', 4: 'red',
               5: 'yellow', 6: 'lilac', 7: 'brown'}

    # Using a dataset
    data_folder = "../../datasets/hgs"
    metadata_file = "/via_export_json.json"
    val_data = ds.DataSet("hgs_val", data_folder + "/val", metadata_file)

    detection.run_detection(val_data, cfg, weights=weights_path,
                            output_dir=output_folder,
                            visualize=True, hide_tags=False,
                            vis_random_samples=3, colors=classes.values)

    # Using a list of files
    test_data = [data_folder + "/val/FT2015_shot1_gp1_00732.jpg",
                 data_folder + "/val/FT2015_shot1_gp1_00733.jpg"]
    detection.run_detection(test_data, cfg, weights=weights_path,
                            output_dir=output_folder,
                            visualize=True, hide_tags=False,
                            vis_random_samples=2, classes=classes)


if __name__ == "__main__":
    main()

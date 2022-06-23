from detectron2.config import CfgNode
from runners import training
from utils import datasets as ds
from utils.configs import PORTED_AUGMENTATIONS


def main():
    """Set up the experiment and invoke the training procedure."""
    # Set up known dataset(s) for use with Detectron2 ##########################
    data_folder = "../../datasets/hgs"
    metadata_file = "/via_export_json.json"
    train_data = ds.DataSet("hgs_train", data_folder + "/train", metadata_file)
    val_data = ds.DataSet("hgs_val", data_folder + "/val", metadata_file)
    # Register datasets to Detectron2
    ds.register_dataset(train_data, classes=["sphere"])
    ds.register_dataset(val_data, classes=["sphere"])

    # Set up training configuration ############################################
    # Load a *.yaml file with static configurations
    cfg = CfgNode(CfgNode.load_yaml_with_base("config.yaml"))

    # add computed values to the configuration,
    # e.g. cfg.SOLVER.STEPS = int(5.2*number_of_images)

    # create a list of image augmentations to use ##############################
    augmentations = PORTED_AUGMENTATIONS

    # Hand over configurations and start training a model ######################
    training.run_training(
        train_set=train_data,
        val_set=val_data,
        configuration=cfg,
        output_dir="./run_example1",
        log_name="example.log",
        resume=True,
        visualize=True,
        img_augmentations=augmentations
    )

    # Clean up #################################################################
    # clean up after the training is over, e.g. remove unused generated files


if __name__ == "__main__":
    main()

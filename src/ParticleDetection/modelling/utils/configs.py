from warnings import warn

from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.config.config import CfgNode
from detectron2.data import transforms as T

from ParticleDetection.utils.datasets import DataSet
import ParticleDetection.utils.helper_funcs as hf
import ParticleDetection.modelling.detectron_obj.augmentations as ca
from ParticleDetection.modelling.utils.helper_funcs import get_iters


PORTED_AUGMENTATIONS = [
    ca.SomeOf([T.RandomFlip(prob=1.0, horizontal=True, vertical=False),
               T.RandomFlip(prob=1.0, horizontal=False, vertical=True),
               T.RandomRotation([90, 180, 270], sample_style="choice",
                                expand=False),
               ca.MultiplyAugmentation((0.9, 1.1)),
               ca.GaussianBlurAugmentation(sigmas=(0.0, 2.0)),
               ca.SharpenAugmentation(alpha=(0.4, 0.6), lightness=(0.9, 1.1))
               ], lower=0, upper=3)
    ]


def run_test_config(dataset: DataSet) -> CfgNode:
    """Creates a configuration with only few iterations for testing new
    code.
    """
    cfg = old_ported_config(dataset)
    cfg.SOLVER.MAX_ITER = 1000
    return cfg


def old_ported_config(dataset: DataSet = None, test_dataset: DataSet = None) \
        -> CfgNode:
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(
        "COCO-InstanceSegmentation/mask_rcnn_R_101_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
        "COCO-InstanceSegmentation/mask_rcnn_R_101_FPN_3x.yaml")

    cfg.NAME = "hgs"    # Todo: check, if there's adverse effects by introducing it     # noqa: E501
    cfg.DATASETS.TRAIN = ()
    cfg.DATASETS.TEST = ()
    cfg.DATALOADER.NUM_WORKERS = 2
    cfg.SOLVER.CHECKPOINT_PERIOD = 1500

    # INPUT
    # TODO: The input sizing and cropping settings seem to be strange,
    #  as it "first" resizes the original image and then crops them to the
    #  same size. How is that actually done in the old implementation?????
    #  _
    #  Here it might be necessary to keep the MIN_SIZE higher than CROP.SIZE
    #  to achieve the same data augmentation effect!
    cfg.INPUT.MIN_SIZE_TRAIN = (512,)   # (256,)
    cfg.INPUT.MAX_SIZE_TRAIN = (768,)   # (256,)
    # cfg.INPUT.MIN_SIZE_TEST = (512,)
    # cfg.INPUT.MAX_SIZE_TEST = (768,)
    cfg.INPUT.CROP.ENABLED = True
    # Cropping type. See documentation of
    # `detectron2.data.transforms.RandomCrop` for explanation.
    cfg.INPUT.CROP.TYPE = "absolute"
    cfg.INPUT.CROP.SIZE = [256, 256]

    # The "RoIHead batch size". 128 is faster, and good enough for this toy
    # dataset (default: 512)
    # TODO: not entirely sure about this
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 500
    # only has one class (polygon), DON'T add 1 for background
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    cfg.MODEL.FPN.OUT_CHANNELS = 256    # 256 is the original, it works
    # significantly better because the previously learned weights are not
    # discarded (i.e. 'backbone.fpn_lateral2.weight')
    cfg.MODEL.ANCHOR_GENERATOR.SIZES = [[16, 24, 36, 48, 60]]
    cfg.MODEL.RPN.NMS_THRESH = 0.9

    # This is the real "batch size" commonly known to deep learning people
    cfg.SOLVER.IMS_PER_BATCH = 1
    cfg.SOLVER.BASE_LR = 0.001

    cfg.TEST.DETECTIONS_PER_IMAGE = 400

    # Ported "default" configs
    cfg.MODEL.RPN.PRE_NMS_TOPK_TEST = 6000          # default: 1000
    cfg.MODEL.RPN.PRE_NMS_TOPK_TRAIN = 6000         # default: 2000
    cfg.MODEL.RPN.POST_NMS_TOPK_TRAIN = 2000        # default: 1000
    # cfg.ROI_HEADS.NMS_THRESH_TEST = 0.3             # default: 0.5
    cfg.MODEL.ROI_HEADS.POSITIVE_FRACTION = 0.3     # default: 0.25
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 200  # default: 512
    cfg.SOLVER.CLIP_GRADIENTS.CLIP_VALUE = 5.0      # default: 1.0
    cfg.MODEL.PIXEL_MEAN = [62., 75., 60.]          # default: [103.53, 116.28, 123.675]    # noqa: E501

    if dataset is None:
        warn("No DataSet was given and the constructed configuration is "
             "therefore not directly usable for training a network.")
        return cfg

    # Configurations with the given dataset
    cfg.DATASETS.TRAIN = (dataset.name,)
    image_count = hf.get_dataset_size(dataset)
    iter_25ep = int(get_iters(cfg, image_count, desired_epochs=25))
    iter_75ep = 3 * iter_25ep  # 2nd training period duration
    iter_125ep = 5 * iter_25ep  # 3rd training period duration  # noqa: F841
    cfg.SOLVER.MAX_ITER = 9 * iter_25ep

    # Construct the 1st learning period
    # TODO: find out how to just train the heads
    cfg.SOLVER.WARMUP_FACTOR = 1  # keeps the base lr
    cfg.SOLVER.WARMUP_ITERS = iter_25ep
    cfg.SOLVER.WARMUP_METHOD = "constant"

    # Construct 2nd/3rd learning period
    cfg.SOLVER.STEPS = (iter_75ep,)
    cfg.SOLVER.GAMMA = 0.4

    if test_dataset is None:
        warn("No DataSet was given for testing.")
        return cfg

    # TODO: implement DefaultTrainer.build_evaluator() to use these
    cfg.DATASETS.TEST = (test_dataset.name,)
    cfg.TEST.EVAL_PERIOD = 100

    return cfg

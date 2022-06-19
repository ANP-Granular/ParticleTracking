# TODO: extend DatasetMapper and overwrite its __call__() method




def old_ported_data_loader(cfg: CfgNode):
    import detectron2.data.transforms as T
    from detectron2.data import DatasetMapper  # the default mapper
    from detectron2.data import build_detection_train_loader

    # Desired Augmentations
    dataloader = build_detection_train_loader(
        cfg, mapper=DatasetMapper(cfg, is_train=True,
                                  augmentations=[T.Resize((800, 800))]))

def build_old_ported_augs(cfg: CfgNode):
    pass

# old_ported_config()

class MyColorAugmentation(T.Augmentation):
    def get_transform(self, image):
        r = np.random.rand(2)
        return T.ColorTransform(lambda x: x * r[0] + r[1] * 10)

class MyCustomResize(T.Augmentation):
    def get_transform(self, image):
        old_h, old_w = image.shape[:2]
        new_h, new_w = int(old_h * np.random.rand()), int(old_w * 1.5)
        return T.ResizeTransform(old_h, old_w, new_h, new_w)

def build_sem_seg_train_aug(cfg):
    augs = [
        T.ResizeShortestEdge(
            cfg.INPUT.MIN_SIZE_TRAIN, cfg.INPUT.MAX_SIZE_TRAIN, cfg.INPUT.MIN_SIZE_TRAIN_SAMPLING
        )
    ]
    if cfg.INPUT.CROP.ENABLED:
        augs.append(
            T.RandomCrop_CategoryAreaConstraint(
                cfg.INPUT.CROP.TYPE,
                cfg.INPUT.CROP.SIZE,
                cfg.INPUT.CROP.SINGLE_CATEGORY_MAX_AREA,
                cfg.MODEL.SEM_SEG_HEAD.IGNORE_VALUE,
            )
        )
    augs.append(T.RandomFlip())
    augs.append(MyCustomResize())
    augs.append(MyColorAugmentation())
    return augs


mapper = DatasetMapper(cfg, is_train=True, augmentations=build_sem_seg_train_aug(cfg))
build_detection_train_loader(cfg, mapper=mapper)


# def mapper(dataset_dict):
#     dataset_dict = copy.deepcopy(dataset_dict)  # it will be modified by code below
#     # can use other ways to read image
#     image = utils.read_image(dataset_dict["file_name"], format="BGR")
#     # See "Data Augmentation" tutorial for details usage
#     auginput = T.AugInput(image)
#     transform = T.Resize((800, 800))(auginput)
#     image = torch.from_numpy(auginput.image.transpose(2, 0, 1))
#     annos = [
#         utils.transform_instance_annotations(annotation, [transform], image.shape[1:])
#         for annotation in dataset_dict.pop("annotations")
#     ]
#     return {
#        # create the format that the model expects
#        "image": image,
#        "instances": utils.annotations_to_instances(annos, image.shape[1:])
#     }
# dataloader = build_detection_train_loader(cfg, mapper=mapper)

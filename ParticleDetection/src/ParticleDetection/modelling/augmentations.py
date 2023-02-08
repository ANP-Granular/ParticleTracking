"""
Collection of custom image augmentations extending the Detectron2 augmentation
pool. These augmentations are intended to be used during the training process
of a neural network using the Detectron2 framework.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       31.10.2022

"""
import random
import warnings

import numpy as np
from imgaug import augmenters
import detectron2.data.transforms as T
from detectron2.data.transforms.augmentation import _transform_to_aug


class SomeOf(T.AugmentationList):
    """**TBD**"""
    def __init__(self, augments, lower, upper):
        self.lower = lower
        self.upper = upper
        self.possible_augments = augments
        super().__init__(augments)

    def get_transform(self, *args) -> T.Transform:
        return super().get_transform(args)

    def __call__(self, aug_input: T.AugInput):
        amount = random.randint(self.lower, self.upper)
        chosen = random.sample(self.possible_augments, amount)
        if not len(chosen):
            chosen = [T.NoOpTransform()]
        self.augs = [_transform_to_aug(x) for x in chosen]
        return super().__call__(aug_input)


class GaussianBlurAugmentation(T.Augmentation):
    """**TBD**"""
    def __init__(self, sigmas: tuple = (0.0, 2.0)):
        super().__init__()
        self.sigmas = sigmas

    def get_transform(self, *args) -> T.Transform:
        return GaussianBlur(self.sigmas)


class GaussianBlur(T.Transform):
    """**TBD**"""
    def __init__(self, sigmas: tuple = (0.0, 2.0)):
        super().__init__()
        self.sigmas = sigmas

    def apply_coords(self, coords: np.ndarray):
        return coords

    def inverse(self) -> T.Transform:
        warnings.warn("The GaussianBlur transformation is not reversible.")
        return T.NoOpTransform()

    def apply_image(self, img: np.ndarray) -> np.ndarray:
        return augmenters.GaussianBlur(sigma=self.sigmas).augment_image(img)


class SharpenAugmentation(T.Augmentation):
    """**TBD**"""
    def __init__(self, alpha: tuple = (0.0, 0.2),
                 lightness: tuple = (0.8, 1.2)):
        self.alpha = alpha
        self.lightness = lightness

    def get_transform(self, *args) -> T.Transform:
        return Sharpen(alpha=self.alpha, lightness=self.lightness)


class Sharpen(T.Transform):
    """**TBD**"""
    def __init__(self, alpha: tuple = (0.0, 0.2),
                 lightness: tuple = (0.8, 1.2)):
        super().__init__()
        self.alpha = alpha
        self.lightness = lightness

    def apply_coords(self, coords: np.ndarray):
        return coords

    def inverse(self) -> T.Transform:
        warnings.warn("The Sharpen transformation is not reversible.")
        return T.NoOpTransform()

    def apply_image(self, img: np.ndarray) -> np.ndarray:
        return augmenters.Sharpen(alpha=self.alpha,
                                  lightness=self.lightness).augment_image(img)


class MultiplyAugmentation(T.Augmentation):
    """**TBD**"""
    def __init__(self, mul: tuple = (0.8, 1.2)):
        super().__init__()
        self.mul = mul

    def get_transform(self, *args) -> T.Transform:
        return Multiply(self.mul)


class Multiply(T.Transform):
    """**TBD**"""
    def __init__(self, mul: tuple = (0.8, 1.2)):
        super().__init__()
        self.mul = mul

    def apply_image(self, img: np.ndarray):
        return augmenters.Multiply(mul=self.mul).augment_image(img)

    def apply_coords(self, coords: np.ndarray):
        return coords

    def inverse(self) -> T.Transform:
        warnings.warn("The Sharpen transformation is not reversible.")
        return T.NoOpTransform()

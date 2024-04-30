# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev
#
# This file is part of ParticleDetection.
# ParticleDetection is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ParticleDetection is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ParticleDetection. If not, see <http://www.gnu.org/licenses/>.

"""
Collection of custom image augmentations extending the Detectron2 augmentation
pool. These augmentations are intended to be used during the training process
of a neural network using the Detectron2 framework.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       31.10.2022

"""
import random
import warnings
from typing import List

import detectron2.data.transforms as T
import numpy as np
from detectron2.data.transforms.augmentation import _transform_to_aug
from imgaug import augmenters


class SomeOf(T.AugmentationList):
    """A list of ``Augmentations`` only some will be used of.

    Randomly chooses ``Augmentation`` from the given list within the range of
    possible numbers of ``Augmentation`` 's.

    Parameters
    ----------
    augments : List[Augmentation]
        List of possible augmentations to choose from.
    lower : int
        Minimum amount of augmentations to choose.
    upper : int
        Maximum amount of augmentations to choose.
    """

    def __init__(self, augments: List[T.Augmentation], lower: int, upper: int):
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
    """Defines a strategy to blur images with a Gaussian blur operation.

    Parameters
    ----------
    sigmas : Tuple[float, float]
        Mean and variance of the constructed Gaussian kernel.\n
        Default is ``(0.0, 2.0)``.
    """

    def __init__(self, sigmas: tuple = (0.0, 2.0)):
        super().__init__()
        self.sigmas = sigmas

    def get_transform(self, *args) -> T.Transform:
        return GaussianBlur(self.sigmas)


class GaussianBlur(T.Transform):
    """Applies a Gaussian blur using the imgaug library.

    Parameters
    ----------
    sigmas : Tuple[float, float]
        Mean and variance of the constructed Gaussian kernel.\n
        Default is ``(0.0, 2.0)``.
    """

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
    """Defines an augmentation strategy to sharpen images.

    Parameters
    ----------
    alpha : Tuple[float, float]
        Blending factor of the sharpened image. A random value will be sampled
        from the interval for every image.\n
        Default is ``(0.0, 0.2)``.
    lightness : Tuple[float, float]
        Lightness/brightness of the sharped image. A random value will be
        sampled from the interval per image.\n
        Default is ``(0.8, 1.2)``.
    """

    def __init__(
        self, alpha: tuple = (0.0, 0.2), lightness: tuple = (0.8, 1.2)
    ):
        self.alpha = alpha
        self.lightness = lightness

    def get_transform(self, *args) -> T.Transform:
        return Sharpen(alpha=self.alpha, lightness=self.lightness)


class Sharpen(T.Transform):
    """Applies a sharpening transformation using the imgaug library.

    Parameters
    ----------
    alpha : Tuple[float, float]
        Blending factor of the sharpened image. A random value will be sampled
        from the interval for every image.\n
        Default is ``(0.0, 0.2)``.
    lightness : Tuple[float, float]
        Lightness/brightness of the sharped image. A random value will be
        sampled from the interval per image.\n
        Default is ``(0.8, 1.2)``.
    """

    def __init__(
        self, alpha: tuple = (0.0, 0.2), lightness: tuple = (0.8, 1.2)
    ):
        super().__init__()
        self.alpha = alpha
        self.lightness = lightness

    def apply_coords(self, coords: np.ndarray):
        return coords

    def inverse(self) -> T.Transform:
        warnings.warn("The Sharpen transformation is not reversible.")
        return T.NoOpTransform()

    def apply_image(self, img: np.ndarray) -> np.ndarray:
        return augmenters.Sharpen(
            alpha=self.alpha, lightness=self.lightness
        ).augment_image(img)


class MultiplyAugmentation(T.Augmentation):
    """Defines an augmentation strategy to multiply each pixel with a certain
    value.

    Parameters
    ----------
    mul : Tuple[float, float]
        The value with which to multiply the pixel values in each image. A
        value from the interval will be sampled per image and used for all
        pixels.\n
        Default is ``(0.8, 1.2)``
    """

    def __init__(self, mul: tuple = (0.8, 1.2)):
        super().__init__()
        self.mul = mul

    def get_transform(self, *args) -> T.Transform:
        return Multiply(self.mul)


class Multiply(T.Transform):
    """Applies a multipliction of each pixel with a certain value.

    Parameters
    ----------
    mul : Tuple[float, float]
        The value with which to multiply the pixel values in each image. A
        value from the interval will be sampled per image and used for all
        pixels.
        Default is ``(0.8, 1.2)``
    """

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

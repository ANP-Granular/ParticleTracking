# Welcome to ParticleTracking's documentation!
```{image} ../../RodTracker/src/RodTracker/resources/logo.png
:align: center
```
```{note}
This project is under active development.
```

ParticleTracking is a repository containing two Python packages for extracting 3D particle coordinate data from the experimental video footage.
In these experiments a granular gas (dilute ensemble of macroscopic particles) was observed with a 2-view stereo camera system.
The current version of the program is used for experiments with rod-like particles. Each particle is parametrized by 2 endpoint coordinates.
ParticleTracking's goal is to automatically extract the coordinate data and provide a Graphical User Interface (GUI) to correct detection errors manually in an efficient way.
Then, the corrected particle data can be tracked and ensemble statistics (average velocity/kinetic energy, local packing fractions, etc.) can be extracted.

The first part is the ParticleDetection package that enables:
- training of Mask-RCNN models for detecting particles in stereo-camera images
- assignment of particle correspondences between both images of the stereo setup
- reconstruction of 3D coordinates and orientations for particles identified in both stereo images
- tracking of particles over the course of an experiment

The RodTracker package is a GUI encapsulating the most used functionality of the ParticleDetection package. It enables users to carry out the aforementioned tasks, except for training a model. Additionally, it provides the means to manually correct object localization, 3D assignment and tracking errors in the automatic detection processes.

```{toctree}
:caption: Contents
:maxdepth: 1
installation/installation
RodTracker/RodTracker
ParticleDetection/ParticleDetection
developer_notes
api-reference
changelog/changelog
```

# Indices and tables

- [](genindex)
- [](modindex)
- [](search)

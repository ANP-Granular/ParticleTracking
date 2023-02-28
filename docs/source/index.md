# Welcome to ParticleTracking's documentation!
```{image} RodTrackerLogo_big.png
:align: center
```
```{note}
This project is under active development.
```

ParticleTracking is a repository containing two Python packages for extracting 3D coordinate data from microgravity experiment image data.
In these experiments a granular gas was observed with a stereo-camera system, specifically a granular gas of rod-like particles.
The goal is to automatically extract the coordinate data and provide a Graphical User Interface (GUI) to correct mistakes manually in an efficient way.

The first part is the ParticleDetection package that enables:
- the training of RCNN models for detecting particles in stereo-camera images
- the assignment of particle correspondences between both images of the stereo setup
- the reconstruction of 3D coordinates for particles identified in both stereo images
- the tracking of particles over the course of an experiment

The RodTracker package is a GUI encapsulating the most used functionality of the ParticleDetection package. It enables users to carry out the aforementioned tasks, except for training a model. Additionally, it provides the means to manually correct placement and assignment mistakes of the automated processes.

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

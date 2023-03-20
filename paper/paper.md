---
title: 'ParticleTracking: A GUI and library for particle tracking on stereo camera images'
tags:
  - Python
  - physics
  - object detection
  - microgravity
authors:
  - name: Adrian Niemann
    orcid: 0009-0008-2025-1946
    affiliation: 1
  - name: Dmitry Puzyrev
    orcid: 0000-0002-9269-3224
    affiliation: 1
affiliations:
 - name: Otto-von-Guericke-University Magdeburg
   index: 1
date: 30 March 2023
bibliography: paper.bib
---

# Summary

The RodTracker software is intended to facilitate the semi-automatic particle detection, tracking and 3D-coordinate reconstruction from stereo camera images.
It consists of two packages, `RodTracker` and `ParticleDetection`.
The `ParticleDetection` package is the library providing functionality for training and use of neural-networks for particle detection in said images, as well as automatic tracking of these particles. The `RodTracker` package is a graphical user interface (GUI) for the particle tracking task, encapsulating the functionality of `ParticleDetection` and providing means to manually correct the automatically generated particle position and tracking data.

The main features of this software are:

- training of Mask R-CNN models for detecting particles on images
- automated particle endpoint assignments from segmentation masks
- automated assignment of particle correspondences between stereo-camera images
- reconstruction of 3D coordinates for particles identified on stereo-camera images
- automated tracking of particles over multiple stereo-camera frames, i.e. the course of an experiment
- providing a GUI for applying manual corrections to the automatically generated data

The main focus of this software is currently on rod-shaped particles, but it is extensible with new particle geometries.
The software is currently employed for data extraction by the VICKI (**TBD**), EVA (**TBD**), and CORDYGA (**TBD**) projects.
So far, **X** publications are in preparation, that use this library for data extraction.

# Statement of need

Many natural and industrial processes deal with granular gases, i.e. dilute macroscopic particles floating and colliding in space. For the study of such systems it is beneficial to know the 3D positions of as many particles as possible over time. With that information a statistical analysis of the ensembles' properties and their evolution over time can be achieved.
For this, granular systems are placed in microgravity, are excited there and observed with a stereo-camera setup [@PhysRevLett.120.214301; @Puzyrev2020].
To achieve statistically meaningful results usually many tens to hundreds of particles are necessary in such experiments. This makes manual data analysis very time-consuming.
For that reason AI-assisted approaches have been successfully employed [@Puzyrev2020] in the data extraction process from the raw stereo-camera images.
This approach still suffered from long manual data correction times, because of detection errors during automatic particle detection and tracking as well as a suboptimal user interface to perform these corrections.

<!-- Specifically a GUI was needed that allowed users, that are partially untrained in the use of programming scripts, to perform the data correction  -->

<!-- Granular media are widely used in industrial applications [@Pong2021; @PhysRevLett.120.214301]. Their study is 

Non-spherical objects are nowadays of specific interest for research. 

The positions and velocities of individual particles are often necessary to analyze...
-->

# Example use

A typical workflow is shown in \autoref{fig:workflow}.
![Typical workflow for data extraction.\label{fig:workflow}](./workflow.png)

**To be continued...**

![Example per-frame particle displacement evaluation plot.\label{fig:eval_example}](../docs/source/images/DisplacementExample.png)

**TBD**
![stuff](../docs/source//images/3DpostTracking.png)

# Dependencies

Among others, the software depends on the following open source libraries. For the particle detection the Detectron2 [@wu2019detectron2] framework is used. For tracking the software relies heavily on functions provided by numpy [@harris2020array], scipy [@2020SciPy-NMeth] and PuLP. The GUI was constructed with PyQt5 and is using pandas [@the_pandas_development_team_2022_7344967] for its data management.

# Acknowledgements
We want to acknowledge the valuable feedback and bug reports given by the users of our software, specifically Mahdieh Mohammadi and Kirsten Harth.
We also want to acknowledge the work of Meera Subramanian and Adithya Viswanathan that provided a first prototype of the RodTracker GUI.

The development of this software has been financially supported by the German Aerospace Center (DLR) within grants 50W1842 (Project EVA) and 50WM2252 (Project VICKI).

# References

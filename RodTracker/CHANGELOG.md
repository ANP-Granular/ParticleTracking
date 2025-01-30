## [Unreleased]

### Added
- shows warning message when loading coordinate data for only one camera (instead of producing an error)

### Fixed
- updated documentation of RodTracker with better explanation of workflow and usage of example data
- other small updates to documentation



## [v0.6.4]

### Added
- missing sections in documentation were added (i.e. world coordinate transformation)
- placeholders (TBDs) were replaced for API documentation 

### Changed
- default rod detection models (CPU and CUDA) are now published and downloaded via PyTorch Hub ([#102](https://github.com/ANP-Granular/ParticleTracking/issues/102))
- default number of detected particles changed to 25 for each color (corresponding to default sample data)
- ParticleDetection dependency updated (ParticleDetection v0.4.3 now required)
- reverted to original dialogue window for stereo calibration/world transformation (for consistency with image loading dialogue)

### Fixed
- tracking now works as intended, previously it required to press the "solve" button frame by frame ([#96](https://github.com/ANP-Granular/ParticleTracking/issues/96))
- solved issue when changes in data were not saved and reverted after pressing "solve" button 
- tracking/matching tests were updated according to the fixed tracking issue 


## [v0.6.3]
### Added
- support for Python 3.12
- viewing mode displaying all particles in a frame ([#94](https://github.com/ANP-Granular/ParticleTracking/issues/94))
- deleting particles from the `Particles` tab ([#93](https://github.com/ANP-Granular/ParticleTracking/issues/93))
- informative dialog before downloading the example model for rod detection ([#89](https://github.com/ANP-Granular/ParticleTracking/issues/89))

### Changed
- removed scaling of example data ([#95](https://github.com/ANP-Granular/ParticleTracking/issues/95))
- made error dialogues modal ([#92](https://github.com/ANP-Granular/ParticleTracking/issues/92))
- folders must be selected during image loading ([#88](https://github.com/ANP-Granular/ParticleTracking/issues/88))

### Fixed
- `numpy` & `torchvision` version conflict ([#90](https://github.com/ANP-Granular/ParticleTracking/issues/90))
- loss of dimension when detecting only 1 particle per frame ([#91](https://github.com/ANP-Granular/ParticleTracking/issues/91))
- multiple errors in tests


## [v0.6.2]
### Added
- automated testing using a GitHub workflow ([#84](https://github.com/ANP-Granular/ParticleTracking/issues/84))
- popup dialog showing unhandled errors to users ([#74](https://github.com/ANP-Granular/ParticleTracking/issues/74))
- button to download an example detection model ([#75](https://github.com/ANP-Granular/ParticleTracking/issues/75), [#85](https://github.com/ANP-Granular/ParticleTracking/issues/85))
- link to the source code in the documentation ([#81](https://github.com/ANP-Granular/ParticleTracking/issues/81))

### Changed
- removed/changed URL dependencies ([#78](https://github.com/ANP-Granular/ParticleTracking/issues/78))
- removed metadata from version generation

### Fixed
- import sorting ([#80](https://github.com/ANP-Granular/ParticleTracking/issues/80))
- outdated ParticleDetection dependency ([#74](https://github.com/ANP-Granular/ParticleTracking/issues/74))

### Removed
- `GPU` installation option

## [v0.6.1]
### Added
- support for python3.11
- support for more complex image file names, i.e. '...**_00000.png**'
- buttons to report issues/request features on GitHub
- dynamic versioning
- support for macOS
- creation of installers on Windows, Linux, and macOS
- choice between opening a local/online version of the documentation

### Changed
- logo/icon

### Fixed
- missing installation requirement (Git)
- capability to 'correct' rods when none are present in the loaded dataset on the current frame ([#73](https://github.com/ANP-Granular/ParticleTracking/issues/73))

### Removed
- bundling into a single file

## [v0.6.0]
### Added
- old rod positions are displayed during editing as a visual cue
- mode for automatic selection of the rod closest to the cursor
- documentation with Sphinx
- integration of `ParticleDetection` functionality
  - detection of rods from images
  - recalculation of 3D rod positions from position updates in 2D
  - tracking of rods and following recalculation of 3D positions
  - evaluation plots for 3D position reconstruction
- shortcut to fit the displayed image to its available space
- added a 'busy' indicator for tabs running long background tasks
- shortcut to delete a rod when having it selected
- display of the documentation from the Help dropdown menu
- loaded/changed position data is automatically saved every 60 seconds

### Changed
- rods are now displayed partially transparent while being selected
- display of a folder selection dialog, if no folder is selected during saving
- settings-/data-directory is now determined with `platformdirs`

### Fixed
- test suite problems have been fixed
- initial display of rods on Windows
- rods not being completely deletable ([#69](https://github.com/ANP-Granular/ParticleTracking/issues/69))

### Removed
- function to display the README in the application
- `True number of rods` setting is no longer available

---

## [v0.5.8]
### Changed
- migration from `setuptools` to `poetry` as the build system
### Fixed
- bundling of the `RodTracker` to a standalone program

---

## [v0.5.7]
### Added
- splash screen during the startup of the `RodTracker`
### Changed
- each module can now access its own logger, leading to more informative log messages
### Fixed
- cropping of displayed rod numbers for font sizes >11
### Removed
- splash screen during unpacking stage of standalone programs bundled as one file

---

## v0.5.6
**skipped**
## v0.5.5
**skipped**

---

## [v0.5.4]
### Changed
- 3D rod elements are now reused instead of regenerated leading to better performance
### Fixed
- visual indicators of the experiment box are no longer extending further than the experiment's dimensions

---

## [v0.5.3]
### Changed
- The rod data displayed as a tree is now updated in place instead of being regenerated.
This especially improves performance and responsiveness of the `RodTracker` when working with large datasets.

---

## [v0.5.2]
### Changed
- rod position data is handled by a dedicated object
- images datasets are handled by one dedicated object per camera view
- rod data display as a tree is done by a custom `QTreeWidget`
- zooming and panning in the 3D environment has improved speeds for the interaction

---

## [v0.5.1]
### Added
- Three different display modes for rods in 3D
### Fixed
- redundant settings updates are removed

---

## [v0.5.0]
### Added
- 3D view of the rod data in relation to the experimental container
- warnings of the Qt framework are now also logged to the `RodTracker`'s log file.
### Changed
- The right portion of the data display is now designed as tabs
- Setting are now accessible in a tab on the right of the main area of the `RodTracker`, instead of a dialog from a dropdown menu. The changed settings are now applied immediately.
- Mechanism for internal notification of successful saving
- internal processes of data selection and loading are now seperated
### Fixed
- automatic rod activation during a camera change to where no rods are available
- The unsaved changes indicator is now removed from all appropriate tabs, not only from the currently active one.
- aborting of image selection
- application crashes due to mishandled threads
- cross platform path incompatibilities

---

## v0.4
**skipped**
## v0.3
**skipped**
## v0.2
**skipped**

---

## [v0.1.1]
### Fixed
- crashes of the `RodTracker` when new rods are introduced during use (see #60)

---

## [v0.1.0]
### Added
- a versioning system

[Unreleased]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.6.3...HEAD
[v0.6.3]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.6.2...v0.6.3
[v0.6.2]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.6.1...v0.6.2
[v0.6.1]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.6.0...v0.6.1
[v0.6.0]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.5.8...v0.6.0
[v0.5.8]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.5.7...v0.5.8
[v0.5.7]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.5.4...v0.5.7
[v0.5.4]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.5.3...v0.5.4
[v0.5.3]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.5.2...v0.5.3
[v0.5.2]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.5.1...v0.5.2
[v0.5.1]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.5.0...v0.5.1
[v0.5.0]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.1.1...v0.5.0
[v0.1.1]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.1.0...v0.1.1
[v0.1.0]: https://github.com/ANP-Granular/ParticleTracking/releases/tag/v0.1.0

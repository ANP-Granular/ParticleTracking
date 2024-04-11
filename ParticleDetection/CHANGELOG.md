## [Unreleased]
### Added
- support for python3.11

### Fixed
- import sorting ([#80](https://github.com/ANP-Granular/ParticleTracking/issues/80))

## [v0.4.0]
### Added
- documentation with Sphinx
  - improved API documentation
  - include examples
- more basic functions are available instead of just their *runner* functions, e.g. `project_points(...)`
- support for python 3.8 added
- possibility to define an *expected number of particles* when extracting rod endpoints
- added automated tests
- exporting detected objects to JSON format for training
- support for all annotation types provided by the VGG Image Annotator in training metadata
- endpoint reordering for smoother post-processing

### Changed
- now uses the headless version of OpenCV
- simplified the default format for transformations from camera to world coordinate system
- object detection function now accepts arbitrary saving functions instead of having one fixed saving method built into it

### Fixed
- tracking of rods over multiple frames (see [here](https://github.com/ANP-Granular/ParticleTracking/commit/8a3fd558f241d8999a8cfe0a0ab236d999d3785a))
- incomplete/incorrect setup of logging for the library

### Removed
- `run_detection(...)` no longer returns the raw detection results

## [v0.3.1]
### Added
- start versioning

[Unreleased]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.4.0+ParticleTracking...HEAD
[v0.4.0]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.3.1+ParticleTracking...v0.4.0+ParticleTracking
[v0.3.1]: https://github.com/ANP-Granular/ParticleTracking/compare/v0.3.1+ParticleTracking

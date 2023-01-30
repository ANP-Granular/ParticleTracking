# Changelog
## [Unreleased]

## [v0.5.8]
### Changed
- migration from `setuptools` to `poetry` as the build system
### Fixed
- bundling of the `RodTracker` to a standalone program


## [v0.5.7]
### Added
- splash screen during the startup of the `RodTracker`
### Changed
- each module can now access its own logger, leading to more informative log messages
### Fixed
- cropping of displayed rod numbers for font sizes >11
### Removed
- splash screen during unpacking stage of standalone programs bundled as one file


## v0.5.6
**skipped**
## v0.5.5
**skipped**


## [v0.5.4]
### Changed
- 3D rod elements are now reused instead of regenerated leading to better performance
### Fixed
- visual indicators of the experiment box are no longer extending further than the experiment's dimensions

## [v0.5.3]
### Changed
- The rod data displayed as a tree is now updated in place instead of being regenerated.
This especially improves performance and responsiveness of the `RodTracker` when working with large datasets.

## [v0.5.2]
### Changed
- rod position data is handled by a dedicated object
- images datasets are handled by one dedicated object per camera view
- rod data display as a tree is done by a custom `QTreeWidget`
- zooming and panning in the 3D environment has improved speeds for the interaction

## [v0.5.1]
### Added
- Three different display modes for rods in 3D
### Fixed
- redundant settings updates are removed

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


## v0.4
**skipped**
## v0.3
**skipped**
## v0.2
**skipped**


## [v0.1.1]
### Fixed
- crashes of the `RodTracker` when new rods are introduced during use (see #60)

## [v0.1.0]
### Added
- a versioning system

[Unreleased]: https://github.com/ANP-Granular/Track_Gui/compare/v0.5.8...HEAD
[v0.5.8]: https://github.com/ANP-Granular/Track_Gui/compare/v0.5.7...v0.5.8
[v0.5.7]: https://github.com/ANP-Granular/Track_Gui/compare/v0.5.4...v0.5.7
[v0.5.4]: https://github.com/ANP-Granular/Track_Gui/compare/v0.5.3...v0.5.4
[v0.5.3]: https://github.com/ANP-Granular/Track_Gui/compare/v0.5.2...v0.5.3
[v0.5.2]: https://github.com/ANP-Granular/Track_Gui/compare/v0.5.1...v0.5.2
[v0.5.1]: https://github.com/ANP-Granular/Track_Gui/compare/v0.5.0...v0.5.1
[v0.5.0]: https://github.com/ANP-Granular/Track_Gui/compare/v0.1.1...v0.5.0
[v0.1.1]: https://github.com/ANP-Granular/Track_Gui/compare/v0.1.0...v0.1.1
[v0.1.0]: https://github.com/ANP-Granular/Track_Gui/releases/tag/v0.1.0
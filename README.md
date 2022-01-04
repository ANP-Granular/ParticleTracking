# Track_Gui

---
## Python GUI for image tracking task
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

![RodTracker - GUI](https://user-images.githubusercontent.com/34780470/141676583-2f294dec-a505-4b7e-a8b5-484af964ea09.png "RodTracker - GUI")
### Notes for users
1. Run [track_main.py](./Python/track_main.py)
2. Open images from disk using the `File` dropdown menu or the `Load 
   Images` button.
   - Switch between images in the folder using the `left`/`right` keys or the 
    `Previous`/`Next` buttons or the `Slider` below.
3. Load and overlay rod coordinates from disc by pressing the `Overlay` button 
   and selecting the folder those `*.csv` coordinate files are stored.
   > Note that the folder of the `*.csv` file must be named like the x,
   > y-identifier in the `*.csv`, i.e. if the x_**gp4** the location should 
   > be like `./gp4/*.csv`. If this structure is not given the program will 
   > default to x_**gp3**.
4. Switch the displayed rods using the color radio buttons and the display 
   methods for all rods or a single rod. 
 
#### Rod correction features
- `left click` on a rod number to select this rod for editing
- `left click` on the start and then end position of the misplaced rod 
- `right-click` anywhere to abort rod drawing
- `right click` anywhere or `left click` on another rod to deselect the 
  current rod
  
    **Alternative method:**
- without previously selecting a rod `left click` on the start and end 
  position of a rod
- enter the desired rod number in the dialog
    - the previous position will be replaced, if an existing rod number 
          was entered
    - a new rod is created, if the entered number is among in the loaded rods
    - only rod numbers from 0 to 99 are supported at the moment
  
  
#### Number correction features
- `double click` on a rod number to edit it
- press `Enter`, `Return` or `left click` outside the number to confirm 
  your input
- press `Escape` to abort editing 
  
    **Conflict handling:**
- rods are marked in `red` when number duplicates occur after numbers were 
  changed   
- a dialog is displayed where you choose how to handle this conflict (the 
  `Resolve Manual` and `Discard old rod` options are currently disabled)

|      Button       | Action performed                                                                                                                          |
|:-----------------:|:------------------------------------------------------------------------------------------------------------------------------------------|
| `Switch Numbers`  | The changed rod keeps its changes and the conflicting  rod gets assigned <br />the changed rod's old number. Both rods are saved to disk. |
|  `Return state`   | The changed rod number is returned to its previous state. <br />Nothing gets saved to disk.                                               |
| `Discard old rod` | ~~The changed rod keeps its changes and the conflicting rod is deleted. <br /> The changed rod is saved to disk~~.                        |
| `Resolve manual`  | ~~The changed rod keeps its changes and is saved to disk. <br /> The conflicting rod keeps being displayed during runtime~~.              |

#### Shortcuts
| Feature                      |                   Shortcut                    |
|:-----------------------------|:---------------------------------------------:|
| Open images                  |                  `Ctrl + O`                   |
| Save rod position data       |                  `Ctrl + S`                   |
| Switch to next/previous view |               `Tab`/ `Ctrl+Tab`               |
| Zoom in/out                  | `+`/`-` <br /> (MacOS: `Ctrl + H`/`Ctrl + =`) |
| Show in original size        |                  `Ctrl + R`                   |
| Next/previous image          |                `Right`/`Left`                 |
| Undo                         |                  `Ctrl + Z`                   |

#### Miscellaneous
- the visual display properties of rods and their number can be changed 
  using the `Preferences` menu
  - `(right-)click` anywhere in the image to show the rod numbers again 
    after the settings were changed
- in some cases there is a notification/information displayed in the main 
  window's status bar

### Notes for developers
- The main GUI-layout is modeled in 
  [mainwindow_layout.ui](Python/ui/mainwindow_layout.ui) and can be changed 
  using QtDesigner. 
- Generate the [Python file](Python/ui/mainwindow_layout.py) after changing the
  [UI-File](Python/ui/mainwindow_layout.ui) using:
  ```shell
    pyuic5 -x path/to/track_ui.ui -o path/to/track_ui.py
    ```
- Do **not** change the [Python file](Python/ui/mainwindow_layout.py) 
  containing the GUI-Layout manually as all changes will be lost when 
  generating it automatically again.
  
---

## Rod tracking using MATLAB
- [`track_manual_gp4.m`](./Matlab/track_manual_gp4.m):
  
  MATLAB script to read image data in continuous order (501,502,503, etc.), 
  track rods using computer vision in Image processing toolbox and save track 
  data as images and mat files.

- [`track_manual_gp5.m`](./Matlab/track_manual_gp5.m): 
  
  MATLAB script to read image data in random order (106 ,230, 460, etc.), 
  track rods using computer vision in Image processing toolbox and save track 
  data as images and mat files.



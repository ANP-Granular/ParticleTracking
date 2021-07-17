# Track_Gui
## Python GUI for image tracking task

### Notes for users
1. Run [track_main.py](./Python/track_main.py)
2. Open images from disk using the `File` dropdown menu, the 
   `Previous`/`Next` buttons or the `left`/`right` keys.
   - Switch between images in the folder using the `left`/`right` keys or the 
    `Previous`/`Next` buttons.
3. Load and overlay rod coordinates from disc by pressing the`Overlay` button 
   and selecting the folder those `*.csv` coordinate files are stored.
4. Select a rod color from the list in the pop-up dialog.
4. Zoom-in (`-`), zoom-out (`+`) or set the image to its Original-Size 
   (`Ctrl+R`) for better visibility.
 
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
  
  
#### Number correction features
- `double click` on a rod number to edit it
- press `Enter`, `Return` or `left click` outside the number to confirm 
  your input
- press `Escape` to abort editing 
  
    **Conflict handling:**
- rods are marked in `red` when number duplicates occur after numbers were 
  changed   
- a dialog is displayed where you choose how to handle this conflict

|Button | Action performed|
|:---: | :--- |
| `Switch Numbers` | The changed rod keeps its changes and the conflicting  rod gets assigned <br />the changed rod's old number. Both rods are saved to disk. |
| `Return state` | The changed rod number is returned to its previous state. <br />Nothing gets saved to disk. |
| `Discard old rod` | The changed rod keeps its changes and the conflicting rod is deleted. <br /> The changed rod is saved to disk.|
| `Resolve manual` | The changed rod keeps its changes and is saved to disk. <br /> The conflicting rod keeps being displayed during runtime.|

> #### Note for `Resolve manual`:
> Two rods with different numbers will be displayed at the same position 
> after reloading the data, if the old number of the changed rod is not 
> reassigned a new position. For example when `Rod#2` was changed to be 
> `Rod#11` and `Rod#2` is not reassigned a position it will be displayed at its 
> previous position with `Rod#11` overlaying it (or vice versa).


> #### Disabled Features/Buttons:
> 
> - `Fit to window`
> - `Clear/Save`, `Save` (saves automatically)
> - `Rod Number` (deprecated, use `Overlay`)

### Notes for developers
- The UI-layout is modeled in [track_ui.ui](./Python/track_ui.ui) and can be 
  changed using QtDesigner. 
- Generate the [Python file](./Python/track_ui.py) after changing the
  [UI-File](./Python/track_ui.ui) using:
  ```shell
    pyuic5 -x path/to/track_ui.ui -o path/to/track_ui.py
    ```
- Do **not** change the [Python file](./Python/track_ui.py) containing the 
  UI-Layout manually as all changes will be lost when generating it 
  automatically again.
  
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



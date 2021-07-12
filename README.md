# Track_Gui
## Python GUI for image tracking task

### Notes for users
1. Run [track_main.py](./Python/track_main.py)
2. Open images from disk using the `File` dropdown menu, the 
   `Previous`/`Next` buttons or the `left`/`right` keys.
   - Switch between images in the folder using the `left`/`right` keys or the 
    `Previous`/`Next` buttons.
3. Load and overlay rod coordinates from disc by pressing the 
   `Overlay`/`Rod Number` buttons and selecting the folder those `*.csv` 
   coordinate files are stored. 
   
   `Overlay`:
   - Correct positions by `left-clicking` on the start and then end position 
     of a 
     misplaced rod. Enter the corresponding rod number.
   - Abort the rod drawing by `right-clicking`.
     
   `Rod Number`:
   - ~~Correct rod numbers by placing them into textboxes as needed. Note 
     that you need to resolve any duplicates yourself. Save the changes to 
     disk by pressing the~~ `Clear/Save` ~~button.~~ 
     > ### Note:
     > 
     > The `Clear/Save` button is currently not saving correctly and this 
     functionality is therefore unavailable.
     
~~Additional functionalities are zoom-in (~~`-`~~), zoom-out (~~`+`~~), 
fit-to-window & Original-Size (~~`Ctrl+R`~~).~~
> ### Note:
> 
> These functions are currently not working correctly and should **NOT** be 
> used. The default display style is *Original-Size*.

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



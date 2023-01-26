## Manual GUI-Testing

Below are test cases described for different functions the GUI shall 
accomplish. Each section only relates to one function and its ways to be 
accessed. The `conditions` described are supposed to be run on every of the 
access options and shall be combined wherever possible/applicable. 


___
### open images
- open via short-cut
- (open via switching images)
- open via menu-item
- open via main-page button
> #### Conditions:
>    - folder includes invalid files (non \*.jpep, \*.png)
>    - folder only included valid files
>    - images were loaded previously
>        - unsaved changes are present
>    - no images loaded previously


___
### open data file
- open via main-page button
> #### Conditions:
>    - folder has all colors
>    - folder does NOT have all colors
>    - folder has UNKNOWN colors
>    - folder includes other files
>        - files with fitting names but different extension
>        - files with non-fitting names and matching extension
>        - files with non-fitting names and different extension


___
### switch images
- via main-page button
- via short-cut
> #### Conditions:
>    - with data files loaded:
>        - line in "editing" mode
>        - line(s) in "conflict" mode
>        - with "unsaved changes"
>        - without "unsaved changes"
>    - with NO data files loaded 
>    - with "Overlay" activated
>    - with "Overlay" deactivated


___
### overlay data
- via main-page checkbox
> #### Conditions:
>    - no data files loaded previously
>    - data files already loaded


___
### rod manipulation
- (create a "new" rod (number not displayed))
- change rod position of activated rod
- change rod position without prior rod activation
> #### Conditions:
>   - changes on a rod in "conflict" mode
>   - changes on previously changed rod
>       - saved changes
>       - unsaved changes

___
### undo manipulations
- via short-cut
- via main-page button
> #### Conditions:
>    - no "unsaved changes" present
>    - eligible "unsaved changes" present
> 


___
### save data
- via main-page button
- via short-cut
> #### Conditions:
>    - no "unsaved changes" present
>    - "unsaved changes" present
>    - changes were saved previously
>        - data folder (where the original data was loaded from) has 
           changed to the previously saved 
>        - data folder (where the original data was loaded from) is the 
           same to the previously saved
>    - user has changed save folder
>        - to be the folder the data was loaded from
>        - a folder that contains saved data (NOT the folder that data was 
           loaded from)
>        - to a non-existing folder
>        - to an empty folder
>        - to a folder with other (not related) files


___
### close the program
- TBD
  - behaviour not defined when changes are unsaved


___
### (re)open the program
- TBD


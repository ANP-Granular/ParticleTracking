# Endpoint Smoothing

Endpoint smoothing is an optional post-processing step for reconstructed rod trajectories. It reduces frame-to-frame noise in the 3D endpoint coordinates while retaining the rigid-rod representation and producing a matching 2D overlay for both camera views.

Smoothing does not alter the source reconstruction or trigger particle detection again. The result is held as a separate table and can be inspected as an overlay or exported as a CSV file. The method uses existing 3D reconstructions as its observations; image reprojection errors influence how much each observation is trusted, but the algorithm is not a joint optimizer over raw 2D image observations.

## Requirements and Workflow

Before smoothing, load the image and rod-position data needed for the current session, and load both the stereo-camera calibration and the transformation to experiment coordinates. The smoothing panel is in the `3D-Reconstruct` tab.

1. Set the inclusive start and end frames.
2. Select the colors to process. Each selected color has an editable nominal rod length in millimeters.
3. Adjust the process-noise and reliability parameters if appropriate for the motion and data quality.
4. Choose **Smooth endpoints**. RodTracker requests the selected frames and colors, then runs the calculation in a worker thread.
5. Toggle **Show smoothed overlay** or press `K` to compare smoothed endpoints with the camera images. The overlay can be shown or hidden independently of the raw rods. Use **Overlay coordinates** to switch between **Image-aligned** (the default) and **3D projection** without re-running the smoother.
6. Check **Show original 3D reprojection** to add the light-green, distortion-aware projection of the *unsmoothed* 3D reconstruction. This checkbox is independent of the magenta smoothed overlay; both can be shown together or separately.
7. Choose **Export smoothed CSV** to save the separate result table.

A start frame greater than the end frame is rejected. Smoothing also requires two camera identifiers, camera calibration, a world transformation, and at least one selected color. If there are no usable 3D endpoints in the requested range, no overlay or CSV export is available.

The raw coordinate fields remain present in the output. Smoothed 3D coordinates and direct projections use `_smooth`-suffixed column names. Image-aligned display coordinates use the `_overlay` suffix; direct projections of the original 3D coordinates use `_original`. None replace the raw 2D or 3D data.

## Inputs and Grouping

The smoother receives reconstructed endpoint coordinates (`x1`, `y1`, `z1`, `x2`, `y2`, `z2`), frame, color, and particle identity. It may also receive the observed endpoint coordinates and visibility flags from each camera. Calibration supplies each camera's intrinsic matrix and distortion coefficients, plus the relative rotation and translation between cameras. The world transformation converts the reconstruction's coordinates into the coordinate system expected by the camera model.

Rows are grouped by `(color, particle)` and ordered by frame. Consequently, observations from different rods and colors are never mixed into one filter. Within each group, a row is usable only if all six 3D endpoint coordinates are finite and the endpoint separation is nonzero. Invalid rows are omitted from the returned smoothed table rather than interpolated.

The GUI provides nominal lengths per color. The initial values are 10 mm for blue and yellow, and 15 mm for green, red, and lilac; they can be edited before running the smoother. For a color without an expected length in the backend input, the median observed length for that group is used instead.

## Rod Pose Representation

For endpoints $\mathbf{p}_1$ and $\mathbf{p}_2$, the measured rod center and unit axis are

$$
\mathbf{c} = \frac{\mathbf{p}_1 + \mathbf{p}_2}{2},
\qquad
\mathbf{u} = \frac{\mathbf{p}_2 - \mathbf{p}_1}{\|\mathbf{p}_2 - \mathbf{p}_1\|}.
$$

Filtering endpoints independently could change the rod length or introduce inconsistent endpoint motion. Instead, the implementation smooths the center and axis as two separate trajectories. An axis has a sign ambiguity: $\mathbf{u}$ and $-\mathbf{u}$ describe the same unoriented rod. Before filtering, each axis is flipped when its dot product with the preceding axis is negative. This keeps the sequence from making artificial 180-degree jumps solely because the endpoint ordering changed.

## Observation Reliability

Each frame receives a positive quality factor $q_i$. A factor near one means the observation is relatively trustworthy; a larger factor increases its measurement uncertainty in the filter.

### Rod-length discrepancy

The observed length is compared with the selected nominal length $L$:

$$
e_{L,i} = |\ell_i - L|.
$$

When the configured length tolerance $\tau_L$ is positive, its contribution to the quality factor is

$$
\left(\frac{e_{L,i}}{\tau_L}\right)^2.
$$

### Camera reprojection discrepancy

The raw 3D endpoints are projected through the loaded calibration into each camera, including lens distortion. Where observed 2D endpoints are available, the pixel discrepancy is calculated for both possible endpoint orders, and the smaller mean endpoint error is used. Rows with missing, negative, or non-finite image coordinates are not used for this cue; a camera's `seen_<camera-id>` flag is also respected when present.

Absolute reprojection error can vary substantially by camera and color. To avoid treating one camera's overall calibration offset as a universal rejection threshold, the smoother compares each residual with that camera's median residual over the current color-particle trajectory. Only residual error above this per-trajectory baseline contributes to the quality factor. If $r_{i,k}$ is the residual for frame $i$ in camera $k$, $b_k$ is the median baseline, and $\tau_R$ is the configured pixel scale, then the combined score is

$$
q_i = 1 + \left(\frac{e_{L,i}}{\tau_L}\right)^2
  + \operatorname{mean}_{k \in V}
  \left[\left(\frac{\max(r_{i,k}-b_k, 0)}{\tau_R}\right)^2\right],
$$

where $V$ contains the camera slots that have at least one valid residual in the trajectory. A disabled tolerance contributes no score. The final value is clipped to the interval $[1, 1000]$.

In the implementation, the mean is taken over camera slots that have at least one valid residual in the trajectory. If a slot has no valid residual for a particular frame, its contribution for that frame is zero. The exported `smoothing_quality` column stores this factor directly, so a larger value means the observation was trusted less by the filter.

These discrepancies affect measurement trust; they do not directly pull the smoothed 3D point toward a solution of the 2D image measurements. In particular, the reprojection residual is computed from the existing 3D reconstruction, not used as a bundle-adjustment residual in a joint 2D/3D optimization.

## Kalman and RTS Smoothing

The center and the sign-aligned axis are passed to separate constant-velocity Kalman filters. For either trajectory, the state contains the pose quantity $\mathbf{x}$ and its per-frame velocity $\mathbf{v}$:

$$
\mathbf{s}_i =
\begin{bmatrix}
\mathbf{x}_i \\
\mathbf{v}_i
\end{bmatrix}.
$$

For a frame interval $\Delta t$, the motion model predicts constant velocity:

$$
\mathbf{s}_{i|i-1} =
\begin{bmatrix}
I & \Delta t I \\
0 & I
\end{bmatrix}
\mathbf{s}_{i-1|i-1}.
$$

The implementation uses the actual difference between frame numbers for $\Delta t$ (with a minimum interval of one). A continuous white-acceleration process-noise model adds uncertainty to this prediction. The GUI's **Translation process noise** and **Orientation process noise** set the process-noise scales for the center and axis filters respectively.

At each observation, the Kalman update balances the prediction against the measured center or axis. The measurement covariance is multiplied by the row's quality factor $q_i$, so large length or reprojection discrepancies reduce that observation's influence. Center and orientation use different base measurement variances because they represent quantities with different scales. A robust innovation check further inflates the measurement covariance when the current observation is an unusually large Mahalanobis-distance jump from the prediction.

After the forward filter pass, a Rauch-Tung-Striebel (RTS) backward pass revisits earlier states using later filtered estimates. This uses the complete selected sequence to produce a smoother trajectory, rather than a causal estimate that only sees earlier frames. For that reason, the operation is intended for offline post-processing.

The smoothed axes are normalized. If a filtered axis becomes invalid or nearly zero, its corresponding sign-aligned measured axis is used as a fallback. The final endpoints are rebuilt symmetrically around the smoothed center:

$$
\mathbf{p}_{1,i}^{\mathrm{smooth}} =
\mathbf{c}_i^{\mathrm{smooth}} - \frac{L}{2}\mathbf{u}_i^{\mathrm{smooth}},
\qquad
\mathbf{p}_{2,i}^{\mathrm{smooth}} =
\mathbf{c}_i^{\mathrm{smooth}} + \frac{L}{2}\mathbf{u}_i^{\mathrm{smooth}}.
$$

Thus each output rod has exactly the selected nominal length, even when the input reconstruction's endpoint separation varies.

## Reprojection and Overlay

The smoothed 3D endpoints are transformed into the first camera's coordinate system. OpenCV's camera projection is then applied using each camera's intrinsic matrix, distortion coefficients, and stereo extrinsics: the first camera uses its own camera model, while the second additionally uses the calibrated relative rotation and translation. The resulting coordinates are stored as `x1_<camera-id>_smooth`, `y1_<camera-id>_smooth`, `x2_<camera-id>_smooth`, and `y2_<camera-id>_smooth`.

The independently selectable **original 3D reprojection** draws $\pi_k(\mathbf{p}_{j,i})$ in light green and stores it in `x1_<camera-id>_original`, `y1_<camera-id>_original`, `x2_<camera-id>_original`, and `y2_<camera-id>_original`. It uses the same calibration, distortion, and world transform as the smoothed projection. It is *not* the originally marked 2D endpoint position, and it does not receive the image-alignment shift. The **Overlay coordinates** selector affects only the magenta smoothed overlay.

The **3D projection** display mode draws those `_smooth` coordinates without modification. The **Image-aligned** mode starts from the same distortion-aware projections, but adds an independent 2D translation for each camera and frame. Let $\pi_k(\mathbf{p}_{j,i})$ be the direct projection of raw reconstructed endpoint $j$, and $\mathbf{o}_{j,i,k}$ its measured 2D position in camera $k$. The correction is the difference between their midpoint positions:

$$
\boldsymbol{\delta}_{i,k} =
\frac{\mathbf{o}_{1,i,k}+\mathbf{o}_{2,i,k}}{2}
- \frac{\pi_k(\mathbf{p}_{1,i})+\pi_k(\mathbf{p}_{2,i})}{2},
\qquad
\mathbf{a}_{j,i,k} =
\pi_k(\mathbf{p}_{j,i}^{\mathrm{smooth}}) + \boldsymbol{\delta}_{i,k}.
$$

In words, project the original 3D rod and the smoothed 3D rod through the *same* camera model, measure how far the original projection's center is from the observed 2D rod center, and apply that offset to both smoothed 2D endpoints. This retains the projected effect of 3D smoothing while placing the overlay center near the observed rod. It only translates the drawn segment; it does not change its angle, length, or the smoothed 3D endpoints. If either observed endpoint is missing, non-finite, negative, or marked unseen, that camera/frame gets no offset and the image-aligned coordinates equal the direct projection.

The camera widgets select the smoothed rows matching the currently displayed frame and selected color, then draw the chosen coordinates as a magenta dashed line with endpoint markers. The overlay does not replace or modify raw 2D detections. The `K` shortcut toggles the same visibility control as the button in the reconstruction tab; the mode selector controls *which* coordinates are displayed.

The `_overlay` coordinates are a visualization aid, **not** the projection of a single corrected 3D rod: the two cameras can receive different translations. If they disagree with `_smooth`, inspect the calibration, camera ordering, world transformation, source 3D reconstruction, and 2D measurements. The image-aligned view can hide systematic reprojection offsets and should not be used to evaluate geometric accuracy.

The CSV export contains the selected, valid source rows plus the smoothed 3D endpoint fields, `l_smooth`, `smoothing_quality`, the direct distortion-aware 2D projections (`_smooth`), the image-aligned 2D display coordinates (`_overlay`), and the original 3D reprojections (`_original`) for both cameras. The source columns are preserved to support side-by-side analysis. The export is one CSV file chosen by the user; it does not split the result into one file per color.

## Parameter Guidance

The GUI defaults are intended as a moderate starting point, not a universal optimum:

| Control | GUI default | Effect |
|:--|--:|:--|
| Translation process noise | 50.0 | Higher values let the center trajectory follow frame observations more closely; lower values favor a steadier constant-velocity path. |
| Orientation process noise | 0.5 | Higher values let rod orientation follow measured axes more closely; lower values smooth orientation more strongly. |
| Length tolerance | 1.5 mm | Sets the scale at which length discrepancies increase measurement uncertainty. |
| Reprojection outlier scale | 15 px | Sets the scale for reprojection error above the trajectory's per-camera median baseline. |

Process-noise values are model scales, not direct maximum displacements or confidence percentages. Tune them by comparing the output against image overlays and independent motion expectations. Strong smoothing may hide real abrupt changes, including collisions. Conversely, raising process noise can preserve genuine fast motion but also preserve more measurement noise. Length and reprojection tolerances control relative trust, not a hard validity cutoff.

## Validation and Limitations

The synthetic backend test injects endpoint noise and one corrupted endpoint, then checks that the center error is reduced, the output length is constrained to the nominal value, and the exported projections agree with OpenCV for both cameras with distortion enabled. It also checks that the corrupted observation receives lower quality than the typical observation.

In a full-sequence probe on the session data used during implementation, 22,943 of 22,947 rows produced valid smoothed outputs; four invalid rows were skipped. With the GUI defaults, the median second difference of rod centers decreased from 0.2061 to 0.0951, and the median second difference of the unit rod axes decreased from 0.02970 to 0.01454. The median reprojection residual increased from 24.62 px to 26.53 px, illustrating the tradeoff between a steadier trajectory and agreement with the measured image coordinates. These are sequence-specific tuning measurements, not a guarantee of improved physical accuracy for every experiment.

Important limitations:

- Missing or invalid 3D rows are skipped; gaps are not interpolated by this implementation.
- The process model assumes locally constant velocity between observations. Real impulsive motion can violate that assumption.
- Reprojection errors adjust observation weights but do not create new 3D estimates from the 2D observations.
- Every output rod is constrained to the specified nominal length, so incorrect length settings produce systematically incorrect endpoints.
- The RTS backward pass uses later frames, so smoothed results should not be interpreted as real-time estimates.

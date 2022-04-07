# driftCorrection
corrects image drift from DIC data


Takes timeseries in the form of a multipage TIFF and estimates drift, will then correct after fitting drift with a univariate spline.

Running manualdrift_correction will bring up a GUI that will allow you to open a timeseries and scrub through it using the slider. Toggle ROI mode to manually track an object through time to use for drift correction. The correct drift button will then apply the drift with a cubic spline smoothing to reduce the sharpness of the transition.

Alternatively it is possible to try Phase Cross-correlation (PCC). This will automatically attempt to characterise the drift although this doesn't always work well.


<img width="1197" alt="image" src="https://user-images.githubusercontent.com/45679976/162147951-063eac30-171e-4e9c-9fbc-0b81e3d778fa.png">

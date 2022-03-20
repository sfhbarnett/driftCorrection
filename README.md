# driftCorrection
corrects image drift from DIC data


Takes timeseries in the form of a multipage TIFF and estimates drift, will then correct after fitting drift with a univariate spline.

Running manualdrift_correction will bring up a GUI that will allow you to open a timeseries and scrub through it using the slider. Toggle ROI mode to manually track an object through time to use for drift correction. The correct drift button will then apply the drift with a cubic spline smoothing to reduce the sharpness of the transition.

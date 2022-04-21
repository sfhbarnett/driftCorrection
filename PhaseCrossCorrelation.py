import numpy as np
from skimage.registration import phase_cross_correlation
from skimage.transform import AffineTransform, warp
from skimage.filters import gaussian
from scipy.interpolate import UnivariateSpline

def PCC(tf, update=10, smoothing=0.9):

    """
    Phase cross correlation to estimate the drift between images in a stack
    :param tf: stack of tiff images encapsulated in the tiffstack class
    :param update: how often the reference frame should be updated
    :param smoothing: How much smoothing to apply to the fitted spline
    :return: drift_total - list of x,y shifts for translation based drift
    uxs - the fitted spline for x
    usy - the fitted spline for y
    """

    counter = 0
    drift_total = []
    refimage = tf.getimage(0)
    refimage = gaussian(refimage,sigma=2)

    # refimage = io.imread(filelist[0])
    # for file in (filelist[1:]):
    for index in range(1, tf.nfiles):
        #movingimage = io.imread(file)
        movingimage = tf.getimage(index)
        movingimage = gaussian(movingimage,sigma=2)
        # subpixel precision
        shift, error, diffphase = phase_cross_correlation(refimage, movingimage,
                                                          upsample_factor=100)
        euc = np.sqrt((shift[0]) ** 2 + (shift[1]) ** 2)
        print(f'Detected subpixel offset (y, x) in tif {index+1}: {shift} with euclidean distance {euc}')

        # As the image changes over time, update the refimage with transformed movingimage
        if counter > update:
            transform = AffineTransform(translation=[shift[1] * -1, shift[0] * -1])
            refimage = warp(movingimage, transform, preserve_range=True)
            counter = 0
        counter += 1
        drift_total.append(shift)
    x = [x[0] for x in drift_total]
    y = [y[1] for y in drift_total]
    t = [t for t in range(len(x))]
    #Spline smoothing to reduce in correct drift spikes
    usx = UnivariateSpline(t, x)
    usy = UnivariateSpline(t, y)
    usx.set_smoothing_factor(smoothing)
    usy.set_smoothing_factor(smoothing)
    return drift_total, usx, usy
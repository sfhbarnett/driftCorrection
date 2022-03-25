import numpy as np
from tifffile import TiffWriter
import tifffile
from skimage.registration import phase_cross_correlation
from skimage.transform import AffineTransform, warp
from skimage.filters import gaussian
from matplotlib import pyplot as plt
from scipy.interpolate import UnivariateSpline

class TiffStack:

    """
    Tiffstack holds information about the images to process and accesses them in a memory-efficient manner
    :param pathname
    """

    def __init__(self, pathname):
        self.ims = tifffile.TiffFile(pathname)
        self.nfiles = len(self.ims.pages)
        page = self.ims.pages[0]
        self.width = page.shape[0]
        self.height = page.shape[1]

    def getimage(self, index):
        return self.ims.pages[index].asarray()


def PCC(tf, update=10, smoothing=0.9):
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
    usx = UnivariateSpline(t, x)
    usy = UnivariateSpline(t, y)
    usx.set_smoothing_factor(smoothing)
    usy.set_smoothing_factor(smoothing)
    return drift_total, usx, usy

path = '/Users/sbarnett/Documents/PIVData/circle/20211108_MCF10ARab5A_H2BGFP_Invasion-02_-Scene-60-P50-B02-Image Export-60_t127_Phase_ORG.tif' # Enter Path Here
outpath = '/Users/sbarnett/Documents/PIVData/circle/out.tif' # Enter output place here

# filelist = [os.path.join(path,filename) for filename in os.listdir(path) if filename != '.DS_Store']
# filelist.sort(key=lambd  a f: int(re.sub('\D', '', f)))

tiffstack = TiffStack(path)

drift_total, usx, usy = PCC(tiffstack, 10, smoothing=0.7)

#refimage = io.imread(filelist[0])
refimage = tiffstack.getimage(0)

with TiffWriter(outpath) as tif:
    tif.save(refimage.astype(np.int16))
    # for index, file in enumerate(filelist[1:]):
    for index in range(1, tiffstack.nfiles):
        # movingimage = io.imread(file)
        movingimage = tiffstack.getimage(index)
        xshift = usx(index)
        yshift = usy(index)
        transform = AffineTransform(translation=[yshift * -1, xshift * -1])
        shifted = warp(movingimage, transform, preserve_range=True)
        tif.save(np.int16(shifted))

subt = [t / 10 for t in range(len(drift_total) * 10)]
plt.plot(drift_total)
plt.plot(subt, usx(subt))
plt.plot(subt, usy(subt))
plt.show()



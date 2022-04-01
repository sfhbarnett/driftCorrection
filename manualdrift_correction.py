
import tifffile
from PyQt6 import QtCore, QtWidgets
import sys

from PyQt6.QtCore import pyqtSlot
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from superqt import QLabeledRangeSlider
from matplotlib.figure import Figure
from skimage.transform import AffineTransform, warp
from scipy.interpolate import UnivariateSpline
import numpy as np
from PhaseCrossCorrelation import PCC
from functools import wraps


def ifnotplothandles(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if args[0].plothandle is not None:
            return func(*args, **kwargs)
        else:
            return QtWidgets.QMessageBox.about(args[0], "Error", "There is no dataset loaded in")
    return wrapper

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.xdrift = None #x-drift
        self.ydrift = None #y-drift

        # LEFT COLUMN
        self.loadfilebutton = QtWidgets.QPushButton('Load File')
        self.loadfilebutton.clicked.connect(self.get_file)
        self.loadfilebutton.setToolTip('Load a file for processing')
        self.toggleroi = QtWidgets.QPushButton('Roi OFF ')
        self.toggleroi.clicked.connect(self.toggleroimode)
        self.toggleroi.setToolTip('Toggle ROI mode on/off')
        self.roimode = 0
        self.driftcorbutton = QtWidgets.QPushButton('Drift')
        self.driftcorbutton.clicked.connect(self.correctdrift)
        self.driftcorbutton.setToolTip('Correct the drift based on manually introduced point ROIs throughout the stack')
        self.PCCbutton = QtWidgets.QPushButton('PCC')
        self.PCCbutton.clicked.connect(self.pccbuttonfunction)
        self.PCCbutton.setToolTip('Applies subpixel phase cross correlation to estimate drift')
        self.driftcheckbox = QtWidgets.QCheckBox("Apply drift", self)
        self.driftcheckbox.setToolTip("If a drift estimation has been made, this toggles the correction to the displayed"
                                      " data")
        self.driftcheckbox.setEnabled(False)
        self.driftcheckbox.clicked.connect(self.viewdrift)
        self.autocontrast = QtWidgets.QCheckBox("AutoContrast", self)
        self.autocontrast.setToolTip("Toggle autocontrast on/off")
        self.autocontrast.setChecked(True)
        self.savedriftcorrected = QtWidgets.QPushButton("Save DC")
        self.savedriftcorrected.setToolTip("Save the drift corrected data")
        self.savedriftcorrected.clicked.connect(self.savedrift)

        self.buttonbox = QtWidgets.QVBoxLayout()
        self.buttonbox.addStretch(1)
        self.buttonbox.addWidget(self.loadfilebutton)
        self.buttonbox.addWidget(self.toggleroi)
        self.buttonbox.addWidget(self.driftcorbutton)
        self.buttonbox.addWidget(self.PCCbutton)
        self.buttonbox.addWidget(self.driftcheckbox)
        self.buttonbox.addWidget(self.autocontrast)
        self.buttonbox.addWidget(self.savedriftcorrected)
        self.buttonbox.addStretch(1)

        # Central Image controls

        self.sc = MplCanvas(self, width=7, height=8, dpi=100)
        self.filename = None
        self.imstack = tiffstack()
        self.plothandle = None
        self.sc.axes.get_xaxis().set_visible(False)
        self.sc.axes.get_yaxis().set_visible(False)
        self.sc.axes.set_aspect('auto')
        self.sc.fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        self.s = self.sc.axes.scatter([], [], facecolors='none', edgecolors='r')
        self.toolbar = NavigationToolbar2QT(self.sc.fig.canvas, self)
        self.sc.fig.canvas.mpl_connect('button_press_event', self.onclick)

        self.contrastslider = QLabeledRangeSlider(QtCore.Qt.Vertical)
        self.contrastslider.setHandleLabelPosition(QLabeledRangeSlider.LabelPosition.LabelsBelow)
        self.contrastslider.setRange(0, 100)
        self.contrastslider.valueChanged.connect(self.update_contrast)
        self.imagecontrols = QtWidgets.QHBoxLayout()
        self.imagecontrols.addWidget(self.contrastslider)
        self.imagecontrols.addWidget(self.sc)

        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addLayout(self.buttonbox)
        self.hbox.addLayout(self.imagecontrols)

        # RIGHT COLUMN

        self.right = QtWidgets.QVBoxLayout()

        data = []
        self.table = TableView(data)
        self.table.setColumnCount(3)
        self.table.setRowCount(0)
        self.table.show()
        self.right.addWidget(self.table)

        self.cleartablebutton = QtWidgets.QPushButton("Clear")
        self.cleartablebutton.clicked.connect(self.cleartable)
        self.deleteonebutton = QtWidgets.QPushButton("Delete last")
        self.deleteonebutton.clicked.connect(self.deletelast)

        self.right_buttons = QtWidgets.QHBoxLayout()
        self.right_buttons.addWidget(self.cleartablebutton)
        self.right_buttons.addWidget(self.deleteonebutton)
        self.right.addLayout(self.right_buttons)

        self.driftgraph = MplCanvas()
        self.right.addWidget(self.driftgraph)
        self.line1, = self.driftgraph.axes.plot([], [])
        self.line2, = self.driftgraph.axes.plot([], [])

        self.hbox.addLayout(self.right)

        # BOTTOM

        sliderholder = QtWidgets.QHBoxLayout()
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, self.imstack.nfiles - 1)
        self.slider.valueChanged.connect(self.move_through_stack)
        self.currentimage = 0
        sliderholder.addWidget(self.slider)
        self.label = QtWidgets.QLabel('0', self)
        self.label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.label.setMinimumWidth(20)

        sliderholder.addWidget(self.label)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addLayout(self.hbox)
        layout.addLayout(sliderholder)
        layout.addStretch()
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.setGeometry(100, 100, 1200, 900)

    def update_contrast(self, value):
        self.mincontrast = value[0]
        self.maxcontrast = value[1]
        if self.plothandle:
            self.plothandle.set_clim(self.mincontrast, self.maxcontrast)
            self.sc.fig.canvas.draw()

    def viewdrift(self):
        self.move_through_stack(self.currentimage)

    def get_file(self):
        self.sc.axes.cla()
        self.filename = None
        self.filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', '')
        self.filename = self.filename[0]
        if self.filename is not None:
            self.imstack = tiffstack(self.filename)
            self.plothandle = self.sc.axes.imshow(self.imstack.getimage(0))
            self.slider.setRange(0, self.imstack.nfiles - 1)
            self.slider.setValue(0)
            self.plothandle.set_cmap('gray')
            self.sc.fig.canvas.draw()
            self.table.clearTable()
            self.contrastslider.setRange(0, self.imstack.maximum * 1.5)
            self.contrastslider.setValue((self.imstack.minimum, self.imstack.maximum))

    @pyqtSlot()
    @ifnotplothandles
    def savedrift(self):
        outname = self.filename[:-4] + 'DC.tif'
        with tifffile.TiffWriter(outname) as tif:
            for index in range(self.imstack.nfiles):
                image = self.imstack.getimage(index)
                xshift = self.xdrift(index)
                yshift = self.ydrift(index)
                transform = AffineTransform(translation=[xshift, yshift])
                shifted = warp(image, transform, preserve_range=True)
                tif.save(np.int16(shifted))
        print('saved data')

    def onclick(self, event):
        if self.roimode == 1:
            self.table.addRow([self.slider.value(), round(event.xdata, 2), round(event.ydata, 2)])
            self.table.setData()
            x = []
            y = []
            for row in range(self.table.rowCount()):
                if int(self.table.item(row, 0).text()) == self.slider.value():
                    x.append(float(self.table.item(row, 1).text()))
                    y.append(float(self.table.item(row, 2).text()))
            if len(x) == 0:
                self.s.remove()
                self.s = self.sc.axes.scatter([], [], facecolors='none', edgecolors='r')
            else:
                self.s.remove()
                self.s = self.sc.axes.scatter(x, y, facecolors='none', edgecolors='r')
            self.sc.fig.canvas.draw()
        else:
            pass

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_S:
            if 0 <= self.slider.value() < self.imstack.nfiles-1:
                self.move_through_stack(self.slider.value()+1)
                self.slider.setValue(self.slider.value()+1)
        elif event.key() == QtCore.Qt.Key_A:
            if 0 < self.slider.value() < self.imstack.nfiles:
                self.move_through_stack(self.slider.value()-1)
                self.slider.setValue(self.slider.value()-1)
        event.accept()

    def toggleroimode(self):
        if self.roimode == 1:
            self.roimode = 0
            self.toggleroi.setText("Roi OFF")
        else:
            self.roimode = 1
            self.toggleroi.setText("Roi ON ")

    @pyqtSlot(int)
    @ifnotplothandles
    def move_through_stack(self, value):
        """ Updates the current image in the viewport"""
        if self.driftcheckbox.isChecked():
            # If user wishes to view the drift corrected results
            xshift = self.xdrift(value)
            yshift = self.ydrift(value)
            image = self.imstack.getimage(value)
            transform = AffineTransform(translation=[xshift, yshift])
            shifted = warp(image, transform, preserve_range=True)
            self.plothandle.set_data(shifted)
        else:
            self.plothandle.set_data(self.imstack.getimage(value))

        # Update the scatter plot for ROIs
        x = []
        y = []
        for row in range(self.table.rowCount()):
            if int(self.table.item(row, 0).text()) == value:
                x.append(float(self.table.item(row, 1).text()))
                y.append(float(self.table.item(row, 2).text()))
        if len(x) == 0:
            self.s.remove()
            self.s = self.sc.axes.scatter([], [], facecolors='none', edgecolors='r')
        else:
            self.s.remove()
            self.s = self.sc.axes.scatter(x, y, facecolors='none', edgecolors='r')

        # Check contrast
        if not self.autocontrast.isChecked():
            self.plothandle.set_clim([self.mincontrast, self.maxcontrast])
        else:
            self.contrastslider.setRange(0, self.imstack.maximum*1.5)
            self.contrastslider.setValue((self.imstack.minimum, self.imstack.maximum))

        self.sc.fig.canvas.draw()
        self.label.setText(str(value))
        self.currentimage = value

    @pyqtSlot()
    @ifnotplothandles
    def correctdrift(self):

        self.line1.remove()
        self.line2.remove()

        x = []
        y = []
        t = []
        for row in range(self.table.rowCount()):
            t.append(int(self.table.item(row, 0).text()))
            x.append(float(self.table.item(row, 1).text()))
            y.append(float(self.table.item(row, 2).text()))
        t = [tsub for tsub in t]
        x = [xsub - x[0] for xsub in x]
        y = [ysub - y[0] for ysub in y]
        t, xs, ys = (list(t) for t in zip(*sorted(zip(t, x, y))))

        usx = UnivariateSpline(t, xs)
        usy = UnivariateSpline(t, ys)
        usx.set_smoothing_factor(0.7)
        usy.set_smoothing_factor(0.7)

        self.xdrift = usx
        self.ydrift = usy

        subt = [t for t in range(self.imstack.nfiles)]
        smoothx = usx(subt)
        smoothy = usy(subt)

        self.line1, = self.driftgraph.axes.plot(subt, smoothx, label='x drift')
        self.line2, = self.driftgraph.axes.plot(subt, smoothy, label='y drift')
        self.driftgraph.axes.scatter(t, x)
        self.driftgraph.axes.scatter(t, y)
        self.driftgraph.axes.legend(handles=[self.line1, self.line2],loc='upper right')
        self.driftgraph.fig.canvas.draw()

        self.driftcheckbox.setEnabled(True)

    @pyqtSlot()
    @ifnotplothandles
    def pccbuttonfunction(self):
        self.line1.remove()
        self.line2.remove()

        drifttotal, usx, usy = PCC(self.imstack)
        self.xdrift = usx
        self.ydrift = usy
        subt = [t for t in range(self.imstack.nfiles)]
        smoothx = usx(subt)
        smoothy = usy(subt)
        self.line1, = self.driftgraph.axes.plot(subt, smoothx, label='x drift')
        self.line2, = self.driftgraph.axes.plot(subt, smoothy, label='y drift')
        self.driftgraph.axes.legend(handles=[self.line1, self.line2], loc='upper right')
        self.driftgraph.fig.canvas.draw()
        self.driftcheckbox.setEnabled(True)

    def cleartable(self):
        self.table.clearTable()
        self.move_through_stack(self.currentimage)

    def deletelast(self):
        self.table.deleteRow()
        self.move_through_stack(self.currentimage)


class TableView(QtWidgets.QTableWidget):
    def __init__(self, data, *args):
        QtWidgets.QTableWidget.__init__(self, *args)
        self.data = data
        self.setData()

    def setData(self):
        horHeaders = ['#', 'x', 'y']
        self.setHorizontalHeaderLabels(horHeaders)
        for m, item in enumerate(self.data):
            row = self.rowCount()
            self.setRowCount(row+1)
            col = 0
            for el in item:
                cell = QtWidgets.QTableWidgetItem(str(el))
                self.setItem(row, col, cell)
                col += 1
        self.show()

    def addRow(self, item):
        row = self.rowCount()
        self.setRowCount(row + 1)
        col = 0
        for el in item:
            cell = QtWidgets.QTableWidgetItem(str(el))
            self.setItem(row, col, cell)
            col += 1

    def deleteRow(self):
        row = self.rowCount()
        self.removeRow(row-1)

    def clearTable(self):
        while self.rowCount() > 0:
            self.removeRow(0)

    def keyPressEvent(self, e):
        e.ignore()


class tiffstack():

    def __init__(self, pathname=None):
        self.ims = None
        self.nfiles = 0
        self.minimum = 0
        self.maximum = np.inf
        if pathname is not None:
            self.load_info(pathname)

    def load_info(self,pathname):
        self.ims = tifffile.TiffFile(pathname)
        self.nfiles = len(self.ims.pages)

    def getimage(self, index):
        image = self.ims.pages[index].asarray()
        self.minimum = image.min()
        self.maximum = image.max()
        return image


def main():
    if not QtWidgets.QApplication.instance():
        app = QtWidgets.QApplication(sys.argv)
    else:
        app = QtWidgets.QApplication.instance()
    app.setQuitOnLastWindowClosed(True)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


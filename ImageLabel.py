from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QSettings
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtWidgets import QWidget, QLabel, QAction, QMenu, QInputDialog
import math
import Settings

class ImageLabel(QLabel):

    ZOOM_FACTOR = 0.8
    DEFAULT_VALUE = 0.
    MAX_VALUE = 1e20
    MIN_VALUE = -1e20
    DIGITS = 9

    mouseMoved = pyqtSignal(float, float)
    clicked = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super(ImageLabel, self).__init__(parent)

        self.setMouseTracking(True)
        self.showGrid = True

        self.originalPixmap = None
        self.pos = None

        self.xLogarithmic = False
        self.yLogarithmic = False

        self.settings = QSettings()

        self.createMenu()
        self.on_showGridAction_triggered(True)

        self.reset()

    def loadImage(self, filename):
        self.originalPixmap = QPixmap(filename)
        self.reset()

    def reset(self):
        self.minX = None
        self.minXGraph = None
        self.maxX = None
        self.maxXGraph = None

        self.minY = None
        self.minYGraph = None
        self.maxY = None
        self.maxYGraph = None

        self.samples = []

        self.scale = 1.

        self.setMinXAction.setChecked(False)
        self.setMaxXAction.setChecked(False)
        self.setMinYAction.setChecked(False)
        self.setMaxYAction.setChecked(False)

        self.resizeImage()
        self.update()

    def scaleImage(self, k):
        self.scale *= k
        self.resizeImage()
        self.update()

    def resizeImage(self):
        if self.originalPixmap:
            size = self.originalPixmap.size()
            self.setPixmap(
                self.originalPixmap.scaled(
                    self.scale * size.width(),
                    self.scale * size.height(),
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation))

    def setXAxisLogarithmicAction(self, v):
        self.xLogarithmic = v
        self.update()
        self.xAxisLogarithmicAction.setChecked(self.xLogarithmic)

    def setYAxisLogarithmicAction(self, v):
        self.yLogarithmic = v
        self.update()
        self.yAxisLogarithmicAction.setChecked(self.yLogarithmic)

    def setMinX(self, x, graphX):
        self.minX = x
        self.minXGraph = graphX

        self.update()
        self.setMinXAction.setChecked(self.minXGraph is not None)

    def setMinY(self, y, graphY):
        self.minY = y
        self.minYGraph = graphY

        self.update()
        self.setMinYAction.setChecked(self.minYGraph is not None)

    def setMaxX(self, x, graphX):
        self.maxX = x
        self.maxXGraph = graphX

        self.update()
        self.setMaxXAction.setChecked(self.maxXGraph is not None)

    def setMaxY(self, y, graphY):
        self.maxY = y
        self.maxYGraph = graphY

        self.update()
        self.setMaxYAction.setChecked(self.maxYGraph is not None)

    def clearSamples(self):
        self.samples = []
        self.update()

    def getSamples(self):
        return map(lambda p: self.mapToGraph(p[0], p[1]), self.samples)

    def mapToGraph(self, x, y):
        # (x, y) must be relative to original size image.

        evalX = (lambda x: math.log(x, 10)) if self.xLogarithmic else (lambda x: x)
        evalY = (lambda y: math.log(y, 10)) if self.yLogarithmic else (lambda y: y)
        outputX = (lambda x: 10**x) if self.xLogarithmic else (lambda x: x)
        outputY = (lambda y: 10**y) if self.yLogarithmic else (lambda y: y)

        width = self.maxX - self.minX
        graphWidth = evalX(self.maxXGraph) - evalX(self.minXGraph)
        widthRatio = width / graphWidth
        hOffset = self.minX / widthRatio - evalX(self.minXGraph)

        height = self.maxY - self.minY
        graphHeight = evalY(self.maxYGraph) - evalY(self.minYGraph)
        heightRatio = height / graphHeight
        vOffset = self.minY / heightRatio - evalY(self.minYGraph)

        graphX = (x / widthRatio) - hOffset
        graphY = (y / heightRatio) - vOffset

        return (outputX(graphX), outputY(graphY))

    def mouseMoveEvent(self, event):
        if not self.ready():
            return

        (x, y) = self.mapFromScaled(event.pos())
        graphX, graphY = self.mapToGraph(x, y)
        self.mouseMoved.emit(graphX, graphY)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.ready():
                return
            (x, y) = self.mapFromScaled(event.pos())
            self.samples.append((x, y))
            self.update()

            graphX, graphY = self.mapToGraph(x, y)
            self.clicked.emit(graphX, graphY)
        elif event.button() == Qt.RightButton:
            self.pos = self.mapFromScaled(event.pos())
            self.menu.popup(self.mapToGlobal(event.pos()))

    def paintEvent(self, event):
        super(ImageLabel, self).paintEvent(event)

        if not self.ready():
            return

        draw = QPainter()
        draw.begin(self)
        draw.setBrush(Qt.NoBrush)

        if self.showGrid:
            pen = QPen()
            pen.setColor(self.settings.value(
                Settings.AXES_COLOR_KEY, Settings.DEFAULT_AXES_COLOR))
            pen.setWidth(3)
            draw.setPen(pen)

            x0, y0 = self.mapToScaled((self.minX, self.minY))
            x1, y1 = self.mapToScaled((self.maxX, self.minY))
            x2, y2 = self.mapToScaled((self.minX, self.maxY))

            draw.drawLine(x0-20, y0, x1, y1)
            draw.drawLine(x0, y0+20, x2, y2)
            draw.drawLine(x1, y1, x1 - 10, y1 - 6)
            draw.drawLine(x1, y1, x1 - 10, y1 + 6)
            draw.drawLine(x2, y2, x2 - 6, y2 + 10)
            draw.drawLine(x2, y2, x2 + 6, y2 + 10)

            draw.drawText(x0+10, y0-10, "(%.1f × %.3f)" %
                (self.minXGraph, self.minYGraph))
            draw.drawText(x1+10, y1+10, "(%.1f × %.3f)" %
                (self.maxXGraph, self.minYGraph))
            draw.drawText(x2+10, y2+10, "(%.1f × %.3f)" %
                (self.minXGraph, self.maxYGraph))

        pen = QPen()
        pen.setColor(self.settings.value(
            Settings.SAMPLES_COLOR_KEY, Settings.DEFAULT_SAMPLES_COLOR))
        pen.setWidth(10)
        draw.setPen(pen)
        for sample in self.samples:
            (x, y) = self.mapToScaled(sample)
            draw.drawPoint(x, y)

        if len(self.samples) > 0:
            drawLines = self.settings.value(
                Settings.DRAW_LINES_BETWEEN_SAMPLES_KEY,
                Settings.DEFAULT_DRAW_LINES_BETWEEN_SAMPLES)
            if drawLines.__class__ == str:
                drawLines = drawLines == 'true'
            if drawLines:
                pen.setWidth(2)
                draw.setPen(pen)
                for i in range(1, len(self.samples)):
                    (x0, y0) = self.mapToScaled(self.samples[i-1])
                    (x1, y1) = self.mapToScaled(self.samples[i])
                    draw.drawLine(x0, y0, x1, y1)

        draw.end()

    def createMenu(self):
        self.setMinXAction = QAction(self.tr('Set Min X'), self)
        self.setMinXAction.setCheckable(True)
        self.setMinYAction = QAction(self.tr('Set Min Y'), self)
        self.setMinYAction.setCheckable(True)
        self.setMaxXAction = QAction(self.tr('Set Max X'), self)
        self.setMaxXAction.setCheckable(True)
        self.setMaxYAction = QAction(self.tr('Set Max Y'), self)
        self.setMaxYAction.setCheckable(True)
        self.showGridAction = QAction(self.tr('Show Grid'), self)
        self.showGridAction.setCheckable(True)
        self.xAxisLogarithmicAction = QAction(self.tr('X Axis Logarithmic'), self)
        self.xAxisLogarithmicAction.setCheckable(True)
        self.yAxisLogarithmicAction = QAction(self.tr('Y Axis Logarithmic'), self)
        self.yAxisLogarithmicAction.setCheckable(True)

        self.menu = QMenu(self)

        self.menu.addAction(self.setMinXAction)
        self.menu.addAction(self.setMinYAction)
        self.menu.addAction(self.setMaxXAction)
        self.menu.addAction(self.setMaxYAction)
        self.menu.addSeparator()
        self.menu.addAction(self.showGridAction)
        self.menu.addAction(self.xAxisLogarithmicAction)
        self.menu.addAction(self.yAxisLogarithmicAction)

        self.setMinXAction.triggered.connect(self.on_setMinXAction_triggered)
        self.setMinYAction.triggered.connect(self.on_setMinYAction_triggered)
        self.setMaxXAction.triggered.connect(self.on_setMaxXAction_triggered)
        self.setMaxYAction.triggered.connect(self.on_setMaxYAction_triggered)
        self.showGridAction.triggered.connect(self.on_showGridAction_triggered)
        self.xAxisLogarithmicAction.triggered.connect(
            self.on_xAxisLogarithmicAction_triggered)
        self.yAxisLogarithmicAction.triggered.connect(
            self.on_yAxisLogarithmicAction_triggered)


    def ready(self):
        ls = [
            self.minX,
            self.minXGraph,
            self.maxX,
            self.maxXGraph,
            self.minY,
            self.minYGraph,
            self.maxY,
            self.maxYGraph
            ]
        return all(x is not None for x in ls)

    def mapFromScaled(self, pos):
        x = pos.x() / self.scale
        y = pos.y() / self.scale
        return (x, y)

    def mapToScaled(self, pos):
        x = pos[0] * self.scale
        y = pos[1] * self.scale
        return (x, y)

    @pyqtSlot(float, float)
    def on_label_mouseMoved(self, x, y):
        self.mouseMoved.emit(x, y)

    @pyqtSlot()
    def on_setMinXAction_triggered(self):
        (graphX, ok) = QInputDialog.getDouble(
            self,
            self.tr('Set Min X'),
            self.tr('Set the minimal value of X'),
            self.DEFAULT_VALUE,
            self.MIN_VALUE,
            self.MAX_VALUE,
            self.DIGITS)
        if ok:
            (x, y) = self.pos
            self.setMinX(x, graphX)

    @pyqtSlot()
    def on_setMinYAction_triggered(self):
        (graphY, ok) = QInputDialog.getDouble(
            self,
            self.tr('Set Min Y'),
            self.tr('Set the minimal value of Y'),
            self.DEFAULT_VALUE,
            self.MIN_VALUE,
            self.MAX_VALUE,
            self.DIGITS)
        if ok:
            (x, y) = self.pos
            self.setMinY(y, graphY)

    @pyqtSlot()
    def on_setMaxXAction_triggered(self):
        (graphX, ok) = QInputDialog.getDouble(
            self,
            self.tr('Set Max X'),
            self.tr('Set the maximal value of X'),
            self.DEFAULT_VALUE,
            self.MIN_VALUE,
            self.MAX_VALUE,
            self.DIGITS)
        if ok:
            (x, y) = self.pos
            self.setMaxX(x, graphX)

    @pyqtSlot()
    def on_setMaxYAction_triggered(self):
        (graphY, ok) = QInputDialog.getDouble(
            self,
            self.tr('Set Origin - Y'),
            self.tr('Set the maximal value of Y'),
            self.DEFAULT_VALUE,
            self.MIN_VALUE,
            self.MAX_VALUE,
            self.DIGITS)
        if ok:
            (x, y) = self.pos
            self.setMaxY(y, graphY)

    @pyqtSlot(bool)
    def on_xAxisLogarithmicAction_triggered(self, v):
        self.setXAxisLogarithmicAction(v)

    @pyqtSlot(bool)
    def on_yAxisLogarithmicAction_triggered(self, v):
        self.setYAxisLogarithmicAction(v)

    @pyqtSlot(bool)
    def on_showGridAction_triggered(self, v):
        self.showGrid = v
        self.update()
        self.showGridAction.setChecked(self.showGrid)

    @pyqtSlot()
    def zoomIn(self):
        self.scaleImage(1 / self.ZOOM_FACTOR)

    @pyqtSlot()
    def zoomOut(self):
        self.scaleImage(1 * self.ZOOM_FACTOR)

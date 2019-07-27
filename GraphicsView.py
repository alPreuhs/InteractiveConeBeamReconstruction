from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from qimage2ndarray import array2qimage
import numpy as np


class GraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super(GraphicsView, self).__init__(parent)
        self.graphics_scene = QGraphicsScene()
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)
        self.setScene(self.graphics_scene)
        self.image = None
        self.window_center = 0
        self.window_width = 0
        self.window_min = 0
        self.window_max = 0
        self.use_windowing = False

    def set_image(self, image, scale_full_range=False, shift=None):
        self.image = np.copy(image)
        self.image += shift if shift is not None else abs(self.image.min())
        #self.image_max = self.image.max()
        #self.image_min = self.image.min()
        if scale_full_range:
            self.window_min, self.window_max = self.image.min(), self.image.max()
        self.update()

    def set_image_as_pixmap(self, image, scale_to_8bit=False):
        img = np.copy(image)
        if scale_to_8bit:
            img_min = img.min()
            if img_min < 0:
                img_min += abs(img_min)
            img = np.interp(img, (img_min, img.max()), (0, 255)).astype(np.uint8)
        self.pixmap_item = QGraphicsPixmapItem(QPixmap(array2qimage(img)))
        self.graphics_scene.removeItem(self.graphics_scene.items()[0])
        self.graphics_scene.addItem(self.pixmap_item)

    def update(self):
        image = np.interp(np.copy(self.image), (self.window_min, self.window_max), (0, 255)).astype(np.uint8)
        self.pixmap_item = QGraphicsPixmapItem(QPixmap(array2qimage(image)))
        self.graphics_scene.removeItem(self.graphics_scene.items()[0])
        self.graphics_scene.addItem(self.pixmap_item)

    def mouseMoveEvent(self, event):
        if not self.use_windowing: return
        pos = event.pos()
        self.window_center = self.image_max * pos.y() / self.height()
        self.window_width = (self.image_max-self.image_min) * pos.x() / self.width()
        half_window_width = self.window_width * 0.5
        self.window_min = self.window_center - half_window_width
        self.window_max = self.window_center + half_window_width
        self.update()

    def resizeEvent(self, event=None):
        self.fitInView(self.pixmap_item.boundingRect(), Qt.KeepAspectRatio)

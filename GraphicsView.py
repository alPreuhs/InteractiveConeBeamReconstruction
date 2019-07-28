from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu, QAction
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
        self.image_max = 255
        self.image_range = 255
        self.window_min, self.window_max = 0, 255
        self.scroll = None
        self.use_windowing_action = QAction('Use windowing')
        self.use_windowing_action.setCheckable(True)
        self.use_windowing_action.toggled.connect(self.on_use_windowing_action)
        self.context_menu = QMenu()
        self.context_menu.addAction(self.use_windowing_action)

    def set_image(self, image, update_values=False):
        self.image = np.copy(image)
        if update_values:
            self.image += abs(self.image.min()) if self.image.min() < 0 else 0
            self.update_values_from_image(self.image)
        self.update()
        self.resizeEvent()

    def shift_image(self, image, update_values=True):
        image_out = image + (abs(image.min()) if image.min() < 0 else 0)
        if update_values:
            self.update_values_from_image(image_out)
        return image_out

    def update_values_from_image(self, image):
        self.image_max = image.max()
        self.image_range = self.image_max - image.min()
        self.window_min, self.window_max = image.min(), self.image_max

    def update(self):
        image = np.interp(np.copy(self.image), (self.window_min, self.window_max), (0, 255)).astype(np.uint8)
        self.graphics_scene.removeItem(self.graphics_scene.items()[0])
        self.pixmap_item = QGraphicsPixmapItem(QPixmap(array2qimage(image)))
        self.graphics_scene.addItem(self.pixmap_item)

    def mouseMoveEvent(self, event):
        if not self.use_windowing_action.isChecked(): return
        window_center = self.image_max * event.pos().y() / self.height()
        half_window_width = 0.5 * self.image_range * event.pos().x() / self.width()
        self.window_min, self.window_max = window_center + half_window_width * np.array([-1, 1])
        self.update()

    def wheelEvent(self, event):
        if self.scroll is not None:
            self.scroll.setValue(self.scroll.value() + event.angleDelta().y() / 4)

    def resizeEvent(self, event=None):
        self.fitInView(self.pixmap_item.boundingRect(), Qt.KeepAspectRatio)

    def contextMenuEvent(self, event):
        self.context_menu.exec(event.globalPos())

    def on_use_windowing_action(self):
        if not self.use_windowing_action.isChecked():
            self.update_values_from_image(self.image) # TODO: check
            self.update()

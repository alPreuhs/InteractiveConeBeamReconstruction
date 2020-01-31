from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu, QAction
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QCoreApplication
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
        self.shift = 0
        self.scroll = None
        self.current_language = 'en_GB'
        self.context_menu = QMenu()
        self.make_windowing_optional = False
        if self.make_windowing_optional:
            self.use_windowing_action = QAction(QCoreApplication.translate('MainWindow', 'Use Windowing'))
            self.use_windowing_action.setCheckable(True)
            self.use_windowing_action.setChecked(True)
            self.use_windowing_action.toggled.connect(self.on_use_windowing_action)
            self.context_menu.addAction(self.use_windowing_action)
        self.reset_window_action = QAction(QCoreApplication.translate('MainWindow', 'Reset Window'))
        self.reset_window_action.setCheckable(False)
        self.reset_window_action.triggered.connect(self.on_reset_window_action)
        self.context_menu.addAction(self.reset_window_action)

    def set_image(self, image, update_values=False):
        self.image = np.copy(image)
        if update_values:
            self.update_values_from_image(self.image)
        self.update()
        self.resizeEvent()

    def update_values_from_image(self, image):
        if image.min() < 0:
            self.shift = abs(image.min())
        self.image_max = image.max() + self.shift
        self.image_range = image.max() - image.min() + self.shift
        self.window_min, self.window_max = image.min() + self.shift, image.max() + self.shift

    def update(self):
        if self.image is None: return
        image = np.interp(np.copy(self.image + self.shift), (self.window_min, self.window_max), (0, 255)).astype(np.uint8)
        self.graphics_scene.removeItem(self.graphics_scene.items()[0])
        self.pixmap_item = QGraphicsPixmapItem(QPixmap(array2qimage(image)))
        self.graphics_scene.addItem(self.pixmap_item)

    def mouseMoveEvent(self, event):
        if self.make_windowing_optional and not self.use_windowing_action.isChecked(): return
        window_center = self.image_max * event.pos().y() / self.height()
        half_window_width = 0.5 * self.image_range * event.pos().x() / self.width()
        self.window_min, self.window_max = window_center + half_window_width * np.array([-1, 1])
        self.update()

    def wheelEvent(self, event):
        if self.scroll is not None:
            delta = np.sign(event.angleDelta().y()) # * 0.01 * self.scroll.maximum()
            self.scroll.setValue(self.scroll.value() + delta)

    def resizeEvent(self, event=None):
        self.fitInView(self.pixmap_item.boundingRect(), Qt.KeepAspectRatio)

    def contextMenuEvent(self, event):
        self.context_menu.exec(event.globalPos())

    def on_use_windowing_action(self):
        if not self.use_windowing_action.isChecked():
            self.on_reset_window_action()

    def on_reset_window_action(self):
        self.update_values_from_image(self.image)
        self.update()

    def change_language(self, lang):
        self.reset_window_action.setText(QCoreApplication.translate('MainWindow', 'Reset Window'))
        if self.make_windowing_optional:
            self.use_windowing_action.setText(QCoreApplication.translate('MainWindow', 'Use Windowing'))

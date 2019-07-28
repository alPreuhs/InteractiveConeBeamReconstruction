from PyQt5.QtWidgets import QGraphicsView


class GraphicsView(QGraphicsView):
    def __init__(self, parent):
        super(GraphicsView, self).__init__(parent)
        self.scroll = None

    def wheelEvent(self, event):
        if self.scroll is not None:
            self.scroll.setValue(self.scroll.value() + event.angleDelta().y() / 4

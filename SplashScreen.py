from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtGui import QPixmap, QMovie
from PyQt5.QtCore import Qt, pyqtSlot

class SplashScreen(QSplashScreen):
    def __init__(self, animation, flags, msg=''):
        QSplashScreen.__init__(self, QPixmap(), flags)
        self.movie = QMovie(animation)
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.frameChanged.connect(self.onNextFrame)
        self.movie.start()
        self.showMessage(msg, Qt.AlignBottom | Qt.AlignCenter, Qt.white)
        self.show()

    @pyqtSlot()
    def onNextFrame(self):
        pixmap = self.movie.currentPixmap()
        self.setPixmap(pixmap)
        #self.setMask(pixmap.mask())
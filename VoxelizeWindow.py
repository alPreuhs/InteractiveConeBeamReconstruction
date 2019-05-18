import sys
from PyQt5.QtCore import pyqtSignal, qFatal, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog
import numpy as np
import os
import pathlib
from VoxelizeWindow_GUI import Ui_Voxelize_Window
import traceback
from include.help_functions import crop, turn_upside_down
from threads.voxelize_thread import voxelizeThread


class VoxelizeWindow(Ui_Voxelize_Window):
    def __init__(self, MainWindow, app):
        self.MainWindow = MainWindow
        self.app = app
        Ui_Voxelize_Window.__init__(self)
        self.setupUi(self.MainWindow)
        self.MainWindow.resized.connect(self.resizeEvent)

        self.input_filename = ''
        self.output_filename = ''
        self.last_opened_input_dir = str(pathlib.Path.home())
        self.last_opened_output_dir = str(pathlib.Path.home())

        self.pB_input.clicked.connect(self.on_pB_input)
        self.pB_output.clicked.connect(self.on_pB_output)
        self.pB_voxelize.clicked.connect(self.on_pB_voxelize)

        self.voxelize_thread = voxelizeThread()
        self.voxelize_thread.finished.connect(self.save)

        def excepthook(type_, value, traceback_):
            traceback.print_exception(type_, value, traceback_)
            qFatal('')

        sys.excepthook = excepthook

    def on_pB_input(self):
        input_filename, _ = QFileDialog.getOpenFileName(None, 'Choose input file', self.last_opened_input_dir, 'STL (*.stl)')
        if not input_filename:
            return
        self.input_filename = input_filename
        self.last_opened_input_dir = os.path.dirname(self.input_filename)
        self.edit_input.setText(self.input_filename)

    def on_pB_output(self):
        output_filename, _ = QFileDialog.getSaveFileName(None, 'Choose output file', self.last_opened_output_dir, 'Numpy (*.npz;*.npy)')
        if not output_filename:
            return
        ext = os.path.splitext(output_filename)[1].lower()
        if not (ext == '.npy' or ext == '.npz'):
            output_filename += '.npz'
        self.output_filename = output_filename
        self.last_opened_output_dir = os.path.dirname(self.output_filename)
        self.edit_output.setText(self.output_filename)

    def on_pB_voxelize(self):
        if not (self.input_filename and self.output_filename):
            return
        self.label_statusBar.setText('Voxelizing 3D Data...')
        self.pB_voxelize.setDisabled(True)
        self.voxelize_thread.init(self.input_filename, self.output_filename, self.sB_resolution.value())
        self.voxelize_thread.start()

    def save(self):
        voxels = self.voxelize_thread.get_voxels()
        if self.cB_crop.isChecked():
            voxels = crop(voxels)
        if self.cB_flip.isChecked():
            voxels = turn_upside_down(voxels)
        ext = os.path.splitext(self.output_filename)[1].lower()
        if ext == '.npy':
            np.save(self.output_filename, voxels)
        elif ext == '.npz':
            np.savez_compressed(self.output_filename, voxels)
        self.label_statusBar.setText('Saved voxelized data')
        self.pB_voxelize.setDisabled(False)

    def resizeEvent(self):
        pass


class VoxelizeMainWindow(QDialog):
    resized = pyqtSignal()

    def __init__(self, parent=None):
        super(VoxelizeMainWindow, self).__init__(parent, Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    def showEvent(self, event):
        self.resized.emit()
        return super(VoxelizeMainWindow, self).showEvent(event)

    def resizeEvent(self, event):
        self.resized.emit()
        return super(VoxelizeMainWindow, self).resizeEvent(event)


if __name__ == '__main__':
    #QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    MainWindow = VoxelizeMainWindow()
    prog = VoxelizeWindow(MainWindow, app)
    MainWindow.show()
    sys.exit(app.exec_())

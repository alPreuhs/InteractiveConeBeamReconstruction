from PyQt5.QtCore import QThread, pyqtSignal
from mesh_vox import read_and_reshape_stl, voxelize  # https://github.com/Septaris/mesh_vox


class voxelizeThread(QThread):
    voxelize_finished = pyqtSignal(str)

    def init(self, input_filename, output_filename, resolution):
        self.input_filename = input_filename
        self.output_filename = output_filename
        self.resolution = resolution

    def get_voxels(self):
        return self.voxels

    def run(self):
        mesh, bounding_box = read_and_reshape_stl(self.input_filename, self.resolution)
        self.voxels, bounding_box = voxelize(mesh, bounding_box)
        self.voxelize_finished.emit('finished')

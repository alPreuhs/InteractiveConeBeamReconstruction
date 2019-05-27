from PyQt5.QtCore import QThread, pyqtSignal
import pyconrad.autoinit
from jpype import attachThreadToJVM, detachThreadFromJVM, JavaException
import time
import numpy as np
from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.conrad.phantom import NumericalSheppLogan3D
from edu.stanford.rsl.tutorial.cone import ConeBeamProjector, ConeBeamBackprojector, ConeBeamCosineFilter
from edu.stanford.rsl.tutorial.cone import ConeBeamCosineFilter
from edu.stanford.rsl.tutorial.filters import RamLakKernel

class filterThread(QThread):
    filter_finished = pyqtSignal(str)

    def init(self, fwd_proj, geo, cosine=True, ramlak=True):
        self.fwd_proj = Grid3D.from_numpy(fwd_proj)
        self.geo = geo
        self.apply_cosine = cosine
        self.apply_ramlak = ramlak

    def get_fwd_proj_filtered(self):
        return self.fwd_proj.as_numpy()

    def run(self):
        self.error = {}
        attachThreadToJVM()
        try:
            focalLength = float(self.geo.getSourceToDetectorDistance())
            maxU_PX = self.geo.getDetectorWidth()
            maxV_PX = self.geo.getDetectorHeight()
            deltaU = float(self.geo.getPixelDimensionX())
            deltaV = float(self.geo.getPixelDimensionY())
            maxU = float(maxU_PX * deltaU)
            maxV = float(maxV_PX * deltaV)
            cbFilter = ConeBeamCosineFilter(focalLength, maxU, maxV, deltaU, deltaV)
            ramK = RamLakKernel(maxU_PX, deltaU)
            for i in range(self.geo.getProjectionStackSize()):
                if self.apply_cosine:
                    cbFilter.applyToGrid(self.fwd_proj.getSubGrid(i))
                if self.apply_ramlak:
                    for j in range(maxV_PX):
                        ramK.applyToGrid(self.fwd_proj.getSubGrid(i).getSubGrid(j))
        except JavaException as exception:
            self.error['message'] = exception.message()
            self.error['stacktrace'] = exception.stacktrace()
        detachThreadFromJVM()
        self.filter_finished.emit('finished')

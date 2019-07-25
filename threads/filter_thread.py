from PyQt5.QtCore import QThread, pyqtSignal
import pyconrad.autoinit
from jpype import attachThreadToJVM, detachThreadFromJVM
try:
    from jpype import JavaException
    old_exception_type = True
except Exception as e:
    from jpype import JException as JavaException
    old_exception_type = False

import time
import numpy as np
from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.tutorial.cone import ConeBeamCosineFilter
from edu.stanford.rsl.tutorial.filters import RamLakKernel
from edu.stanford.rsl.conrad.utils import ImageUtil
from edu.stanford.rsl.conrad.filtering import CosineWeightingTool, RampFilteringTool
from edu.stanford.rsl.conrad.filtering.rampfilters import SheppLoganRampFilter


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
            if False:
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
            else:
                if self.apply_cosine:
                    cosine_filter = CosineWeightingTool()
                    cosine_filter.configure()
                    self.fwd_proj = ImageUtil.applyFilterInParallel(self.fwd_proj, cosine_filter, True)
                if self.apply_ramlak:
                    filter = SheppLoganRampFilter()
                    filter.configure()
                    filtertool = RampFilteringTool()
                    filtertool.setRamp(filter)
                    self.fwd_proj = ImageUtil.applyFilterInParallel(self.fwd_proj, filtertool, True)
        except JavaException as exception:
            if old_exception_type:
                self.error['message'] = exception.message()
            else:
                self.error['message'] = exception.message
            self.error['stacktrace'] = exception.stacktrace()
        detachThreadFromJVM()
        self.filter_finished.emit('finished')

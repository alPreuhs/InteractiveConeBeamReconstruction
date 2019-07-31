from PyQt5.QtCore import QThread, pyqtSignal
import pyconrad.autoinit
from jpype import attachThreadToJVM, detachThreadFromJVM
try:
    from jpype import JavaException
    old_exception_type = True
except Exception as e:
    from jpype import JException as JavaException
    old_exception_type = False
import numpy as np
from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.conrad.data.numeric.opencl import OpenCLGrid3D, OpenCLGrid2D
from edu.stanford.rsl.tutorial.cone import ConeBeamBackprojector


class backwardProjectionThread(QThread):
    back_proj_finished = pyqtSignal(str)

    def init(self, fwd_proj, proj_idx=None, use_cl=True):
        self.use_cl = use_cl
        self.fwd_proj = Grid3D.from_numpy(fwd_proj)
        self.proj_idx = int(proj_idx) if proj_idx is not None else proj_idx
        self.cone_beam_back_projector = ConeBeamBackprojector()

    def get_back_proj(self):
        return self.back_proj.as_numpy()

    def run(self):
        self.error = {}
        attachThreadToJVM()
        try:
            if self.use_cl:
                if self.proj_idx is None:
                    #self.back_proj = self.cone_beam_back_projector.backprojectPixelDrivenCL(self.fwd_proj)
                    back_proj = OpenCLGrid3D(Grid3D(*pyconrad.config.get_reco_size()))
                    self.cone_beam_back_projector.fastBackprojectPixelDrivenCL(OpenCLGrid3D(self.fwd_proj), back_proj)
                    self.back_proj = Grid3D(back_proj)
                else:
                    fwd_proj = OpenCLGrid2D(self.fwd_proj.getSubGrid(self.proj_idx))
                    back_proj = OpenCLGrid3D(Grid3D(*pyconrad.config.get_reco_size()))
                    self.cone_beam_back_projector.fastBackprojectPixelDrivenCL(fwd_proj, back_proj, self.proj_idx)
                    self.back_proj = Grid3D(back_proj)
            else:
                if self.proj_idx is None:
                    self.back_proj = self.cone_beam_back_projector.backprojectPixelDriven(self.fwd_proj)
                else:
                    fwd_proj = self.fwd_proj.getSubGrid(self.proj_idx)
                    self.back_proj = self.cone_beam_back_projector.backprojectPixelDriven(fwd_proj, self.proj_idx)
        except JavaException as exception:
            if old_exception_type:
                self.error['message'] = exception.message()
            else:
                self.error['message'] = exception.message
            self.error['stacktrace'] = exception.stacktrace()
        detachThreadFromJVM()
        self.back_proj_finished.emit('finished')

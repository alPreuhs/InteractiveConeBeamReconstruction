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
from pyconrad import JArray, JDouble
from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.conrad.data.numeric.opencl import OpenCLGrid3D, OpenCLGrid2D
from edu.stanford.rsl.tutorial.cone import ConeBeamProjector


class forwardProjectionThread(QThread):
    fwd_proj_finished = pyqtSignal(str)

    def init(self, phantom, spacing=[1,1,1], proj_idx=None, use_cl=True, parent=None):
        self.use_cl = use_cl
        self.phantom = Grid3D.from_numpy(phantom)
        self.phantom.setSpacing(JArray(JDouble)(list(spacing)))
        self.proj_idx = int(proj_idx) if proj_idx is not None else proj_idx
        self.parent = parent
        self.error = ''

    def get_fwd_proj(self):
        return self.fwd_proj.as_numpy()

    def run(self):
        self.error = {}
        attachThreadToJVM()
        try:
            cone_beam_projector = ConeBeamProjector()
            if self.use_cl:
                if self.proj_idx is None:
                    sino = OpenCLGrid3D(Grid3D(*pyconrad.config.get_sino_size()))
                    cone_beam_projector.fastProjectRayDrivenCL(sino, OpenCLGrid3D(self.phantom))
                    self.fwd_proj = Grid3D(sino)
                    #self.fwd_proj = cone_beam_projector.projectRayDrivenCL(self.phantom)
                else:
                    size = Grid3D(*pyconrad.config.get_sino_size()).getSize()
                    sino = OpenCLGrid2D(Grid2D(size[0], size[1]))
                    cone_beam_projector.fastProjectRayDrivenCL(sino, OpenCLGrid3D(self.phantom), self.proj_idx)
                    self.fwd_proj = Grid2D(sino)
            else:
                if self.proj_idx is None:
                    self.fwd_proj = cone_beam_projector.projectPixelDriven(self.phantom)
                else:
                    self.fwd_proj = cone_beam_projector.projectPixelDriven(self.phantom, self.proj_idx)
        except JavaException as exception:
            if old_exception_type:
                self.error['message'] = exception.message()
            else:
                self.error['message'] = exception.message
            self.error['stacktrace'] = exception.stacktrace()
        detachThreadFromJVM()
        self.fwd_proj_finished.emit('finished')

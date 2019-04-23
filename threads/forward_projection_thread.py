from PyQt5.QtCore import QThread, pyqtSignal
import pyconrad.autoinit
from jpype import attachThreadToJVM, detachThreadFromJVM
import time
import numpy as np
from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.conrad.phantom import NumericalSheppLogan3D
from edu.stanford.rsl.tutorial.cone import ConeBeamProjector, ConeBeamBackprojector, ConeBeamCosineFilter


class forwardProjectionThread(QThread):
    fwd_proj_finished = pyqtSignal(str)

    def init(self, phantom, proj_idx=None, use_cl=True):
        self.use_cl = use_cl
        self.phantom = Grid3D.from_numpy(phantom)
        self.proj_idx = int(proj_idx) if proj_idx is not None else proj_idx

    def get_fwd_proj(self):
        return self.fwd_proj.as_numpy()

    def run(self):
        attachThreadToJVM()
        cone_beam_projector = ConeBeamProjector()
        if self.use_cl:
            if self.proj_idx is None:
                self.fwd_proj = cone_beam_projector.projectRayDrivenCL(self.phantom)
            else:
                self.fwd_proj = cone_beam_projector.projectRayDrivenCL(self.phantom, self.proj_idx)
        else:
            if self.proj_idx is None:
                self.fwd_proj = cone_beam_projector.projectPixelDriven(self.phantom)
            else:
                self.fwd_proj = cone_beam_projector.projectPixelDriven(self.phantom, self.proj_idx)
        detachThreadFromJVM()
        self.fwd_proj_finished.emit('finished')

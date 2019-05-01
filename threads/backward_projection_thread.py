from PyQt5.QtCore import QThread, pyqtSignal
import pyconrad.autoinit
from jpype import attachThreadToJVM, detachThreadFromJVM
import time
import numpy as np
from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.conrad.phantom import NumericalSheppLogan3D
from edu.stanford.rsl.tutorial.cone import ConeBeamProjector, ConeBeamBackprojector, ConeBeamCosineFilter


class backwardProjectionThread(QThread):
    back_proj_finished = pyqtSignal(str)

    def init(self, fwd_proj, proj_idx=None, slice_idx=None, use_cl=True):
        self.use_cl = use_cl
        self.fwd_proj = Grid3D.from_numpy(fwd_proj)
        self.proj_idx = int(proj_idx) if proj_idx is not None else proj_idx
        self.slice_idx = int(slice_idx) if slice_idx is not None else slice_idx
        self.cone_beam_back_projector = ConeBeamBackprojector()

    def get_back_proj(self):
        return self.back_proj.as_numpy()

    def run(self):
        attachThreadToJVM()
        if self.use_cl:
            if self.proj_idx is None:
                self.back_proj = self.cone_beam_back_projector.backprojectPixelDrivenCL(self.fwd_proj)
            else:
                self.back_proj = self.cone_beam_back_projector.backprojectPixelDrivenCL(self.fwd_proj, self.proj_idx)
        else:
            if self.proj_idx is None:
                self.back_proj = self.cone_beam_back_projector.backprojectPixelDriven(self.fwd_proj)
            else:
                slice = self.fwd_proj.getSubGrid(self.slice_idx)
                self.back_proj = self.cone_beam_back_projector.backprojectPixelDriven(slice, self.proj_idx)
        detachThreadFromJVM()
        self.back_proj_finished.emit('finished')

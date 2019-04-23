import math
import os.path
import sys
import xml.etree.ElementTree as etree
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTranslator, pyqtSignal, pyqtSlot, QThread, QTimeLine
from PyQt5.QtWidgets import QFileDialog, QGraphicsPixmapItem, QGraphicsScene, QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QIcon
import numpy as np
from qimage2ndarray import array2qimage
from stl import mesh
import os
import scipy
import pathlib
from include import help_functions
from include import readWriteRaw
from InteractiveConeBeamReconstruction_GUI import Ui_Interactive_Cone_Beam_Reconstruction
from vtkWindow import vtkWindow
import traceback
from include.help_functions import scale_mat_from_to
import time
import vtk
from Math.projection import create_default_projection_matrix, get_rotation_matrix_by_axis_and_angle
from Math.vtk_proj_matrix import vtk_proj_matrix
from random import randint
from PIL import Image, ImageSequence
import jpype
# import gc
from include.Conrad_XML import Conrad_XML
import pyconrad

pyconrad.setup_pyconrad(min_ram='1G')
from threads.forward_projection_thread import forwardProjectionThread
from threads.backward_projection_thread import backwardProjectionThread
from threads.filter_thread import filterThread
from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.conrad.phantom import NumericalSheppLogan3D
from edu.stanford.rsl.tutorial.cone import ConeBeamProjector, ConeBeamBackprojector, ConeBeamCosineFilter
from edu.stanford.rsl.conrad.utils import Configuration
from edu.stanford.rsl.conrad.utils.Configuration import saveConfiguration, getGlobalConfiguration, \
    setGlobalConfiguration
from edu.stanford.rsl.conrad.geometry.trajectories import CircularTrajectory
from edu.stanford.rsl.conrad.geometry.Projection import CameraAxisDirection
from edu.stanford.rsl.conrad.numerics import SimpleVector
from edu.stanford.rsl.conrad.geometry.shapes.simple import PointND
from edu.stanford.rsl.tutorial.cone import ConeBeamCosineFilter
from edu.stanford.rsl.tutorial.filters import RamLakKernel


class InteractiveConeBeamReconstruction(Ui_Interactive_Cone_Beam_Reconstruction):
    def __init__(self, MainWindow, app):
        self.MainWindow = MainWindow
        self.app = app

        self.translator = QTranslator()
        self.app.installTranslator(self.translator)

        # traceback is disabled by default, the following reactivates it
        def excepthook(type_, value, traceback_):
            traceback.print_exception(type_, value, traceback_)
            QtCore.qFatal('')

        sys.excepthook = excepthook

        # Setup UI, which is created via qt designer and pyuic5
        Ui_Interactive_Cone_Beam_Reconstruction.__init__(self)
        self.setupUi(self.MainWindow)
        self.MainWindow.resized.connect(self.resizeEvent)

        # anim_filename = 'C:\\Users\jonas\GitHub\InteractiveConeBeamReconstruction\\anim.gif'
        # gif = Image.open(anim_filename)
        # self.fwd_proj = np.array([np.array(frame.copy().getdata(), dtype=np.uint8).reshape(frame.size[1], frame.size[0]) for frame in ImageSequence.Iterator(gif)])
        # for z in range(len(self.fwd_proj)):
        #    self.fwd_proj[z] = np.interp(self.fwd_proj[z], (self.fwd_proj[z].min(), self.fwd_proj[z].max()), (0, 255)).astype(np.uint8)
        # self.fwd_proj = np.load('anim.npy')

        # self.back_proj = self.imgs
        # self.back_proj = NumericalSheppLogan3D(256, 256, 256).getNumericalSheppLoganPhantom().as_numpy()
        # self.back_proj = np.interp(self.back_proj, (np.min(self.back_proj), np.max(self.back_proj)), (0, 255)).astype(np.uint8)
        # np.save('SheppLogan3D_256.npy', self.back_proj)
        # NumericalSheppLogan3D(64, 64, 64).getNumericalSheppLoganPhantom().save_vtk('shepplogan')
        # tmp = np.interp(tmp, (np.min(tmp), np.max(tmp)), (0, 255)).astype(np.uint8)
        # tmp.save_vtk()

        self.use_cl = False
        self.cB_use_cl.stateChanged.connect(self.on_cB_use_cl)

        self.conrad_xml = os.path.join(str(pathlib.Path.home()), 'Conrad.xml')
        Configuration.loadConfiguration()
        self.conrad_config = Configuration.getGlobalConfiguration()
        self.load_configuration()

        # self.back_proj_ = np.load('SheppLogan3D_512.npz')['arr_0']
        self.back_proj_ = np.load('SheppLogan3D_64.npy')
        self.phantom = np.load('SheppLogan3D_64.npy') # 'SheppLogan3D_256.npy'
        self.back_proj_axial = np.rot90(self.back_proj_, 2, (1, 2))
        self.back_proj_axial = np.rot90(self.back_proj_axial, 2, (0, 2))
        self.back_proj_sagittal = np.rot90(self.back_proj_, 1, (1, 2))
        self.back_proj_sagittal = np.rot90(self.back_proj_sagittal, 1, (0, 1))
        self.back_proj_sagittal = np.rot90(self.back_proj_sagittal, 2, (1, 2))
        self.back_proj_coronal = np.rot90(self.back_proj_, 1, (0, 1))
        self.back_proj_coronal = np.rot90(self.back_proj_coronal, 2, (0, 2))
        self.back_proj = self.back_proj_axial
        self.back_proj_uint8 = np.ndarray(shape=self.back_proj.shape, dtype=np.uint8)
        self.back_proj_disp = np.ndarray(shape=self.back_proj.shape, dtype=np.uint8)
        self.back_proj_uint8 = np.ndarray(
            shape=(self.sB_reco_dim_z.value(), self.sB_reco_dim_y.value(), self.sB_reco_dim_x.value()), dtype=np.uint8)
        self.back_proj_uint8 = self.back_proj_axial

        # self.conrad_xml = Conrad_XML()
        # self.detector_dims = self.conrad_xml.get_detector_dims()
        # self.num_proj_mats = self.conrad_xml.get_num_projection_matrices()
        # self.reco_dims = self.conrad_xml.get_reco_dims()
        # print(self.detector_dims, self.num_proj_mats)

        from mesh_vox import read_and_reshape_stl, voxelize  # https://github.com/Septaris/mesh_vox
        input_path = os.path.join('include', 'Head_Phantom.stl')
        resolution = 256  # 100
        voxels, bounding_box = np.zeros(shape=(resolution, resolution, resolution)), np.zeros(
            shape=(resolution, resolution, resolution))
        if False:
            mesh, bounding_box = read_and_reshape_stl(input_path, resolution)
            voxels, bounding_box = voxelize(mesh, bounding_box)
            np.save('voxels256.npy', voxels)
            np.save('bounding_box256.npy', bounding_box)
        else:
            voxels = np.load('voxels256.npy')
            bounding_box = np.load('bounding_box256.npy')
        # self.phantom = voxels

        self.fwd_proj_loaded = False
        self.back_proj_loaded = False
        self.fwd_proj_completed = False
        self.back_proj_completed = False

        self.vtk_handle = vtkWindow()
        self.vtk_handle.vtkWidget(self.view_3D, filename=os.path.join("include", "Head_Phantom.stl"))

        px_sp = 1
        sdd = 700
        sid = 500
        off_u = 128
        off_v = 128
        pmat = create_default_projection_matrix(pixel_spacing=px_sp, sid=sdd, sisod=sid, offset_u=off_u, offset_v=off_v)
        self.proj_mat_actor = vtk_proj_matrix(pmat, sdd, off_u * 2, off_v * 2)
        self.proj_mat_actor.GetProperty().SetColor(1, 0, 0)
        self.vtk_handle.ren.AddActor(self.proj_mat_actor)
        self.set_vtk_proj_mat()

        self.sB_sdd.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))
        self.sB_sid.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))
        self.sB_pix_dim_x.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))
        self.sB_pix_dim_y.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))
        self.sB_det_width.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))
        self.sB_det_height.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))

        length = 200
        color = [0, 1, 0]
        textActor = self.vtk_handle.get_axis_label_actor('x', [length, 0, 0], self.vtk_handle.ren)
        textActor.GetProperty().SetColor(color[0], color[1], color[2])
        self.vtk_handle.ren.AddActor(textActor)
        textActor = self.vtk_handle.get_axis_label_actor('y', [0, length, 0], self.vtk_handle.ren)
        textActor.GetProperty().SetColor(color[0], color[1], color[2])
        self.vtk_handle.ren.AddActor(textActor)
        textActor = self.vtk_handle.get_axis_label_actor('z', [0, 0, length], self.vtk_handle.ren)
        textActor.GetProperty().SetColor(color[0], color[1], color[2])
        self.vtk_handle.ren.AddActor(textActor)
        self.vtk_handle.add_coord([length, 0, 0], color, self.vtk_handle.ren, shatRadius=0.02, tipLength=0.1,
                                  tipRadius=0.05)
        self.vtk_handle.add_coord([0, length, 0], color, self.vtk_handle.ren, shatRadius=0.02, tipLength=0.1,
                                  tipRadius=0.05)
        self.vtk_handle.add_coord([0, 0, length], color, self.vtk_handle.ren, shatRadius=0.02, tipLength=0.1,
                                  tipRadius=0.05)

        self.last_opened_dir_3D = '.'
        self.last_opened_dir_xml = str(pathlib.Path.home())
        self.action_open_3D_data.triggered.connect(self.open_3D_Data)
        self.pB_demo.clicked.connect(self.on_pB_demo_acquisition)
        self.action_change_lang_en_GB.triggered.connect(lambda _: self.change_language("en_GB"))
        self.action_change_lang_de_DE.triggered.connect(lambda _: self.change_language("de_DE"))
        self.pB_fwd_proj.clicked.connect(self.on_pB_fwd_proj_clicked)
        self.pB_back_proj.clicked.connect(self.on_pB_back_proj_clicked)
        self.scroll_fwd_proj.sliderMoved.connect(self.on_scroll_fwd_proj)
        self.scroll_fwd_proj.valueChanged.connect(self.on_scroll_fwd_proj)
        self.pB_fwd_proj_play_pause.clicked.connect(self.fwd_proj_play_pause)
        self.scroll_back_proj.setMaximum(self.back_proj.shape[0] - 1)
        self.scroll_back_proj.sliderMoved.connect(self.on_scroll_back_proj)
        self.scroll_back_proj.valueChanged.connect(self.on_scroll_back_proj)
        self.pB_back_proj_play_pause.clicked.connect(self.back_proj_play_pause)
        self.fwd_proj_playing = False
        self.back_proj_playing = False
        self.icon_play = QtGui.QIcon(QtGui.QPixmap(os.path.join("icons", "play.svg")))
        self.icon_pause = QtGui.QIcon(QtGui.QPixmap(os.path.join("icons", "pause.svg")))
        self.sB_speed.valueChanged.connect(self.on_speed_changed)
        self.comboBox_plane_sel.currentTextChanged.connect(self.on_plane_sel_changed)
        self.action_load_config.triggered.connect(lambda _: self.load_configuration(filename=''))
        self.pB_reset_config.clicked.connect(self.reset_configuration)
        self.action_save_config.triggered.connect(lambda _: self.save_configuration(filename=''))

        self.pixmap_fwd_proj = QtWidgets.QGraphicsPixmapItem()
        self.pixmap_back_proj = QtWidgets.QGraphicsPixmapItem()

        self.frame_duration_min = 10
        self.frame_duration_max = 2000
        self.sB_speed.setMaximum(6)  # 5 steps
        self.frame_duration_dt = (self.frame_duration_max - self.frame_duration_min) / (self.sB_speed.maximum() - 1)

        self.fwd_proj_thread = forwardProjectionThread()
        self.fwd_proj_thread.finished.connect(self.on_fwd_proj_finished)

        self.back_proj_thread = backwardProjectionThread()
        self.back_proj_thread.finished.connect(self.on_back_proj_finished)

        self.filter_thread_cosine = filterThread()
        self.filter_thread_cosine.finished.connect(lambda: self.on_filter_finished(cosine=True, ramlak=False))
        self.filter_thread_ramlak = filterThread()
        self.filter_thread_ramlak.finished.connect(lambda: self.on_filter_finished(cosine=False, ramlak=True))
        self.filter_thread_cosine_ramlak = filterThread()
        self.filter_thread_cosine_ramlak.finished.connect(lambda: self.on_filter_finished(cosine=True, ramlak=True))

        self.cB_ramlak_filter.stateChanged.connect(self.on_filter_cB_changed)
        self.cB_cosine_filter.stateChanged.connect(self.on_filter_cB_changed)

        self.frame_duration = self.frame_duration_max
        self.timeline_fwd_proj = QTimeLine()
        self.timeline_fwd_proj.setCurveShape(QTimeLine.LinearCurve)
        self.timeline_fwd_proj.frameChanged.connect(self.display_image_fwd_proj)
        self.timeline_fwd_proj.finished.connect(self.fwd_proj_play_pause)

        self.timeline_back_proj = QTimeLine()
        self.timeline_back_proj.setCurveShape(QTimeLine.LinearCurve)
        self.timeline_back_proj.frameChanged.connect(self.display_image_back_proj)
        self.timeline_back_proj.finished.connect(self.back_proj_play_pause)

        self.current_fwd_proj_idx = -1
        self.current_back_proj_idx = -1

        self.init_icons()

        self.resizeEvent()

    def on_cB_use_cl(self):
        self.use_cl = self.cB_use_cl.isChecked()

    def set_vtk_proj_mat(self, pmat=None, rot=0):
        self.vtk_handle.ren.RemoveActor(self.proj_mat_actor)
        # TODO: values from Conrad.xml may not be up to date with values from the ui spinboxes
        px_sp = self.sB_pix_dim_x.value()
        sdd = self.sB_sdd.value()
        sid = self.sB_sid.value()
        off_u = self.sB_det_height.value() / 2  # ?
        off_v = self.sB_det_width.value() / 2  # ?
        if pmat is None:
            if rot == 0:
                self.label_angles.setText('LAO/RAO: 0°\tCRAN/CAUD: 0°')
            elif rot == 180:
                self.label_angles.setText('LAO/RAO: 180°\tCRAN/CAUD: 0°')
            elif rot < 180:
                self.label_angles.setText('RAO: {}°\tCRAN/CAUD: 0°'.format(rot))
            else:
                self.label_angles.setText('LAO: {}°\tCRAN/CAUD: 0°'.format(360-rot))
            rot -= 90 # like Conrad proj mats!? start from x-axis not y-axis!?
            pmat = create_default_projection_matrix(rao_lao_ang=rot, pixel_spacing=px_sp, sid=sdd, sisod=sid,
                                                    offset_u=off_u, offset_v=off_v)
        if False:  # if rot is not 0:
            rot_mat = get_rotation_matrix_by_axis_and_angle(np.matrix([0, 0, 1]).T, rot, make_matrix_homogen=True)
            pmat = pmat * rot_mat

        self.proj_mat_actor = vtk_proj_matrix(pmat, sdd, off_u * 2, off_v * 2)
        self.proj_mat_actor.GetProperty().SetColor(1, 0, 0)
        self.proj_mat_actor.GetProperty().SetLineWidth(5)
        self.vtk_handle.ren.AddActor(self.proj_mat_actor)
        # self.vtk_handle.update()
        # self.ren.ResetCamera()
        # self.ren.ResetCameraClippingRange()
        # self.vtkWidget.Initialize()
        self.vtk_handle.iren.Initialize()

    def msg_window(self, windowTitle='', text='', detailedText='', icon=None):
        msgWindow = QMessageBox()
        if icon is not None:
            msgWindow.setWindowIcon(icon)
        if len(windowTitle):
            msgWindow.setWindowTitle(windowTitle)
        if len(text):
            msgWindow.setText(text)
        if len(detailedText):
            msgWindow.setDetailedText(detailedText)
        msgWindow.exec_()

    def init_icons(self):
        self.iconPath = 'icons'
        self.icons = {}
        self.icons['app'] = 'window_icon.svg'
        self.icons['save'] = 'save.svg'
        self.icons['open'] = 'open.svg'
        self.icons['print'] = 'print.svg'
        self.icons['close'] = 'close.svg'
        self.icons['manual'] = 'manual.svg'
        self.icons['settings'] = 'settings_1.svg'
        self.icons['warning'] = 'warning.svg'
        self.icons['file warning'] = 'file_warning.svg'
        self.icons['file not found'] = 'file_x.svg'

    def get_icon(self, name):
        iconFilename = self.icons[name] if name in self.icons.keys() else 'blank.svg'
        iconFilename = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.iconPath, iconFilename)
        if os.path.isfile(iconFilename):
            return QIcon(iconFilename)
        else:
            return QIcon()

    def reset_configuration(self):
        Configuration.initConfig()
        self.load_configuration(filename=self.conrad_xml)

    def load_configuration(self, filename=os.path.join(str(pathlib.Path.home()), 'Conrad.xml')):
        if not os.path.isfile(filename):
            filename, _ = QFileDialog.getOpenFileName(self.centralwidget, "Open CONRAD configuration",
                                                      self.last_opened_dir_xml, "CONRAD (*.xml)")
            if not len(filename):
                return
            self.last_opened_dir_xml = os.path.split(filename)[0]
        self.conrad_xml = filename
        config = Configuration.loadConfiguration(filename)
        geo = config.getGeometry()
        self.sB_sdd.setValue(geo.getSourceToDetectorDistance())
        self.sB_sid.setValue(geo.getSourceToAxisDistance())
        self.sB_ang_incr.setValue(geo.getAverageAngularIncrement())
        self.sB_num_sweeps.setValue(config.getNumSweeps())
        self.num_proj_mats = geo.getProjectionStackSize()
        self.sB_num_proj.setValue(self.num_proj_mats)
        # print(geo.getRotationAxis().toString()) # circular # TODO
        self.sB_det_width.setValue(geo.getDetectorWidth())
        self.sB_det_height.setValue(geo.getDetectorHeight())
        self.sB_pix_dim_x.setValue(geo.getPixelDimensionX())
        self.sB_pix_dim_y.setValue(geo.getPixelDimensionY())
        self.sB_reco_dim_x.setValue(geo.getReconDimensionX())
        self.sB_reco_dim_y.setValue(geo.getReconDimensionY())
        self.sB_reco_dim_z.setValue(geo.getReconDimensionZ())
        self.sB_reco_spacing_x.setValue(geo.getVoxelSpacingX())
        self.sB_reco_spacing_y.setValue(geo.getVoxelSpacingY())
        self.sB_reco_spacing_z.setValue(geo.getVoxelSpacingZ())
        self.conrad_config = config
        self.conrad_geometry = geo

    def save_configuration(self, filename=os.path.join(str(pathlib.Path.home()), 'Conrad.xml')):
        if self.sB_sdd.value() <= self.sB_sid.value():
            self.msg_window(windowTitle='Error',
                            text='Source to detector distance must be larger than source to patient distance.',
                            icon=self.get_icon('warning'))
            return
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(self.centralwidget, "Save CONRAD configuration as",
                                                      self.last_opened_dir_xml, "CONRAD (*.xml)")
            if not len(filename):
                return
            self.last_opened_dir_xml = os.path.split(filename)[0]
        geo = self.conrad_circular_trajectory(
            n_proj=self.sB_num_proj.value(),
            sid=self.sB_sid.value(),
            sdd=self.sB_sdd.value(),
            ang_incr=self.sB_ang_incr.value(),
            det_off_x=self.sB_det_off_u.value(),
            det_off_y=self.sB_det_off_v.value(),
            u_dir='detectormotion_plus',
            v_dir='rotationaxis_plus',
            rot_ax=[0, 0, 1],
            rot_center=[0, 0, 0],
            ang_start=0,
            det_width=self.sB_det_width.value(),
            det_height=self.sB_det_height.value(),
            pix_dim_x=self.sB_pix_dim_x.value(),
            pix_dim_y=self.sB_pix_dim_y.value(),
            reco_dim_x=self.sB_reco_dim_x.value(),
            reco_dim_y=self.sB_reco_dim_y.value(),
            reco_dim_z=self.sB_reco_dim_z.value()
        )
        self.conrad_config.setGeometry(geo)
        self.num_proj_mats = self.sB_num_proj.value()
        if filename:
            saveConfiguration(self.conrad_config, filename)
            Configuration.setGlobalConfiguration(self.conrad_config)
        else:
            print('No filename specified')
        if False:
            self.conrad_config = Configuration.loadConfiguration(self.conrad_xml)
            Configuration.setGlobalConfiguration(self.conrad_config)
            geo = Configuration.getGlobalConfiguration().getGeometry()
            print('nach speichern: ', geo.getDetectorWidth(), geo.getDetectorHeight())

    @staticmethod
    def get_camera_axis_direction_from_string(ax_dir):
        ax_dir = ax_dir.upper()
        if ax_dir == 'DETECTORMOTION_PLUS':
            return CameraAxisDirection.DETECTORMOTION_PLUS
        elif ax_dir == 'DETECTORMOTION_MINUS':
            return CameraAxisDirection.DETECTORMOTION_MINUS
        elif ax_dir == 'ROTATIONAXIS_PLUS':
            return CameraAxisDirection.ROTATIONAXIS_PLUS
        elif ax_dir == 'ROTATIONAXIS_MINUS':
            return CameraAxisDirection.ROTATIONAXIS_MINUS
        elif ax_dir == 'DETECTORMOTION_ROTATED':
            return CameraAxisDirection.DETECTORMOTION_ROTATED
        elif ax_dir == 'ROTATIONAXIS_ROTATED':
            return CameraAxisDirection.ROTATIONAXIS_ROTATED
        else:
            raise ValueError(ax_dir + ' is not a known CameraAxisDirection')

    @staticmethod
    def conrad_circular_trajectory(
            n_proj=180,
            sid=600, sdd=1200,
            ang_incr=1.0,
            det_off_x=0, det_off_y=0,
            u_dir=CameraAxisDirection.DETECTORMOTION_PLUS, v_dir=CameraAxisDirection.ROTATIONAXIS_PLUS,
            rot_ax=[0, 0, 1], rot_center=[0, 0, 0],
            ang_start=0,
            det_width=620, det_height=480,
            pix_dim_x=1.0, pix_dim_y=1.0,
            reco_dim_x=256, reco_dim_y=256, reco_dim_z=256):
        # default values only set so the values can be used in arbitrary order
        if type(u_dir) == str:
            u_dir = InteractiveConeBeamReconstruction.get_camera_axis_direction_from_string(u_dir)
        if type(v_dir) == str:
            v_dir = InteractiveConeBeamReconstruction.get_camera_axis_direction_from_string(v_dir)
        if type(rot_ax) == list:
            rot_ax = SimpleVector.from_list(rot_ax)
        elif type(rot_ax) == np.ndarray:
            rot_ax = SimpleVector.from_numpy(rot_ax)
        if type(rot_center) == list:
            rot_center = PointND.from_list(rot_center)
        elif type(rot_center) == np.ndarray:
            rot_center = PointND.from_numpy(rot_center)
        trajectory = CircularTrajectory()
        trajectory.setDetectorWidth(int(det_width))
        trajectory.setDetectorHeight(int(det_height))
        trajectory.setPixelDimensionX(float(pix_dim_x))
        trajectory.setPixelDimensionY(float(pix_dim_y))
        trajectory.setSourceToDetectorDistance(float(sdd))
        trajectory.setReconDimensionX(int(reco_dim_x))
        trajectory.setReconDimensionY(int(reco_dim_y))
        trajectory.setReconDimensionZ(int(reco_dim_z))
        trajectory.setReconVoxelSizes([1.0, 1.0, 1.0])
        trajectory.setOriginInPixelsX(float(reco_dim_x / 2))  # center
        trajectory.setOriginInPixelsY(float(reco_dim_y / 2))
        trajectory.setOriginInPixelsZ(float(reco_dim_z / 2))
        trajectory.setDetectorUDirection(u_dir)  # CameraAxisDirection.DETECTORMOTION_PLUS) # test
        trajectory.setDetectorVDirection(v_dir)  # CameraAxisDirection.ROTATIONAXIS_PLUS) # test
        trajectory.setTrajectory(int(n_proj), float(sid), float(ang_incr), float(det_off_x), float(det_off_y), u_dir,
                                 v_dir, rot_ax, rot_center, float(ang_start))
        return trajectory

    def generate_viewing_planes(self):
        # TODO: check if rotations are correct
        self.back_proj_axial = np.rot90(self.back_proj_uint8, 2, (1, 2))
        self.back_proj_axial = np.rot90(self.back_proj_axial, 2, (0, 2))
        self.back_proj_sagittal = np.rot90(self.back_proj_uint8, 1, (1, 2))
        self.back_proj_sagittal = np.rot90(self.back_proj_sagittal, 1, (0, 1))
        self.back_proj_sagittal = np.rot90(self.back_proj_sagittal, 2, (1, 2))
        self.back_proj_coronal = np.rot90(self.back_proj_uint8, 1, (0, 1))
        self.back_proj_coronal = np.rot90(self.back_proj_coronal, 2, (0, 2))

    def on_pB_fwd_proj_clicked(self):
        self.pB_fwd_proj.setDisabled(True)
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        self.save_configuration(filename=self.conrad_xml)
        self.fwd_proj_completed = False
        self.fwd_proj_loaded = False
        geo = self.conrad_config.getGeometry()
        num_projs = geo.getProjectionStackSize()
        det_height = geo.getDetectorHeight()
        det_width = geo.getDetectorWidth()
        self.fwd_proj = np.ndarray(shape=(num_projs, det_height, det_width))
        self.fwd_proj_uint8 = np.ndarray(shape=(num_projs, det_height, det_width), dtype=np.uint8)
        self.fwd_proj_filtered_uint8 = np.ndarray(shape=(num_projs, det_height, det_width), dtype=np.uint8)
        self.on_speed_changed()
        self.timeline_fwd_proj.setFrameRange(0, num_projs - 1)
        self.scroll_fwd_proj.setMaximum(num_projs - 1)
        self.fwd_proj_thread.init(phantom=self.phantom, use_cl=self.use_cl)
        if self.rB_all.isChecked():
            self.current_fwd_proj_idx = None
            self.fwd_proj_slice_by_slice = False
        else:
            self.current_fwd_proj_idx = -1
            self.fwd_proj_slice_by_slice = True
        self.fwd_project()

    def fwd_project(self):
        if self.fwd_proj_slice_by_slice:
            self.current_fwd_proj_idx += 1
            self.fwd_proj_thread.proj_idx = self.current_fwd_proj_idx
        # TODO: memory leak im thread finden
        # only update index to reduce JVM memory (!?)
        # jpype.java.lang.Runtime.getRuntime().gc()
        # gc.collect()
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        self.fwd_proj_thread.start()

    def on_fwd_proj_finished(self):
        current_proj = self.fwd_proj_thread.get_fwd_proj()
        if self.fwd_proj_slice_by_slice:
            self.fwd_proj[self.current_fwd_proj_idx] = current_proj
        else:
            self.fwd_proj = current_proj
        self.fwd_proj_uint8[self.current_fwd_proj_idx] = scale_mat_from_to(current_proj)
        self.fwd_proj_loaded = True
        if self.fwd_proj_slice_by_slice:
            self.scroll_fwd_proj.setMaximum(self.current_fwd_proj_idx)
            self.scroll_fwd_proj.setValue(self.current_fwd_proj_idx)
            self.display_image(self.gV_fwd_proj, self.fwd_proj_uint8[self.current_fwd_proj_idx])
            if self.current_fwd_proj_idx < self.num_proj_mats - 1:
                self.fwd_project()
            else:
                self.filter_fwd_proj()
        else:
            self.scroll_fwd_proj.setMaximum(self.fwd_proj.shape[0] - 1)
            self.scroll_fwd_proj.setValue(0)
            self.display_image(self.gV_fwd_proj, self.fwd_proj_uint8[0])
            self.filter_fwd_proj()

    def filter_fwd_proj(self):
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        self.filter_cosine_done = False
        self.filter_ramlak_done = False
        self.filter_cosine_ramlak_done = False
        geo = self.conrad_config.getGeometry()
        self.filter_thread_cosine.init(
            fwd_proj=self.fwd_proj,
            geo=geo,
            cosine=True,
            ramlak=False
        )
        self.filter_thread_ramlak.init(
            fwd_proj=self.fwd_proj,
            geo=geo,
            cosine=False,
            ramlak=True
        )
        self.filter_thread_cosine_ramlak.init(
            fwd_proj=self.fwd_proj,
            geo=geo,
            cosine=True,
            ramlak=True
        )
        self.filter_thread_cosine.start()
        self.filter_thread_ramlak.start()
        self.filter_thread_cosine_ramlak.start()

    def on_filter_finished(self, cosine, ramlak):
        if cosine and ramlak:
            self.fwd_proj_filtered_cosine_ramlak = self.filter_thread_cosine_ramlak.get_fwd_proj_filtered()
            self.fwd_proj_filtered_cosine_ramlak_uint8 = scale_mat_from_to(self.fwd_proj_filtered_cosine_ramlak)
            self.filter_cosine_ramlak_done = True
        elif cosine and not ramlak:
            self.fwd_proj_filtered_cosine = self.filter_thread_cosine.get_fwd_proj_filtered()
            self.fwd_proj_filtered_cosine_uint8 = scale_mat_from_to(self.fwd_proj_filtered_cosine)
            self.filter_cosine_done = True
        elif not cosine and ramlak:
            self.fwd_proj_filtered_ramlak = self.filter_thread_ramlak.get_fwd_proj_filtered()
            self.fwd_proj_filtered_ramlak_uint8 = scale_mat_from_to(self.fwd_proj_filtered_ramlak)
            self.filter_ramlak_done = True
        else:
            pass  # TODO
        if self.filter_cosine_done and self.filter_ramlak_done and self.filter_cosine_ramlak_done:
            self.fwd_proj_completed = True
            self.on_filter_cB_changed()
            self.pB_fwd_proj.setDisabled(False)

    def on_filter_cB_changed(self):
        if not self.fwd_proj_completed:
            return
        cosine = self.cB_cosine_filter.isChecked()
        ramlak = self.cB_ramlak_filter.isChecked()
        if cosine and ramlak:
            self.fwd_proj_filtered = self.fwd_proj_filtered_cosine_ramlak
            self.fwd_proj_filtered_uint8 = self.fwd_proj_filtered_cosine_ramlak_uint8
        elif cosine and not ramlak:
            self.fwd_proj_filtered = self.fwd_proj_filtered_cosine
            self.fwd_proj_filtered_uint8 = self.fwd_proj_filtered_cosine_uint8
        elif not cosine and ramlak:
            self.fwd_proj_filtered = self.fwd_proj_filtered_ramlak
            self.fwd_proj_filtered_uint8 = self.fwd_proj_filtered_ramlak_uint8
        else:
            self.fwd_proj_filtered = self.fwd_proj
            self.fwd_proj_filtered_uint8 = scale_mat_from_to(self.fwd_proj)
        self.display_image(self.gV_fwd_proj, self.fwd_proj_filtered_uint8[self.scroll_fwd_proj.value()])

    def on_pB_back_proj_clicked(self):
        self.pB_back_proj.setDisabled(True)
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        # self.save_configuration(filename=self.conrad_xml)
        if not self.fwd_proj_completed:
            self.msg_window(windowTitle='Reconstruction not possible',
                            text="First perform the forward projection by clicking on 'Scan'",
                            icon=self.get_icon('warning'))
            return
        self.back_proj_completed = False
        self.back_proj_loaded = False
        geo = self.conrad_config.getGeometry()
        zmax, ymax, xmax = geo.getReconDimensionZ(), geo.getReconDimensionY(), geo.getReconDimensionX()
        self.scroll_back_proj.setMaximum(zmax - 1)
        self.back_proj = np.zeros(shape=(zmax, ymax, xmax))
        self.back_proj_uint8 = np.zeros(shape=(zmax, ymax, xmax), dtype=np.uint8)
        self.back_proj_disp = np.zeros(shape=(zmax, ymax, xmax), dtype=np.uint8)
        self.on_speed_changed()
        self.timeline_back_proj.setFrameRange(0, self.fwd_proj.shape[0] - 1)
        if self.rB_all.isChecked():
            self.back_proj_slice_by_slice = False
            self.current_back_proj_idx = None
            self.current_back_proj_slice_idx = None
        else:
            self.back_proj_slice_by_slice = True
            self.current_back_proj_idx = -1
            self.current_back_proj_slice_idx = 0
        self.back_proj_thread.init(fwd_proj=self.fwd_proj_filtered, use_cl=self.use_cl)
        self.back_project()

    def back_project(self):
        if self.back_proj_slice_by_slice:
            if self.current_back_proj_idx < self.num_proj_mats - 1:
                self.current_back_proj_idx += 1
            else:
                self.current_back_proj_idx = 0
                self.current_back_proj_slice_idx += 1
            print('slice: ', self.current_back_proj_slice_idx, 'proj: ', self.current_back_proj_idx)
            self.back_proj_thread.proj_idx = self.current_back_proj_idx
            self.back_proj_thread.slice_idx = self.current_back_proj_slice_idx
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        self.back_proj_thread.start()

    def on_back_proj_finished(self):
        current_reco = self.back_proj_thread.get_back_proj()
        if self.back_proj_slice_by_slice:
            self.back_proj = np.add(self.back_proj, current_reco)
        else:
            self.back_proj = current_reco
        self.back_proj_uint8 = scale_mat_from_to(self.back_proj)
        self.back_proj_loaded = True
        # self.scroll_back_proj.setMaximum(self.current_back_proj_idx)
        # self.scroll_back_proj.setValue(self.current_back_proj_idx)
        if self.back_proj_slice_by_slice:
            # TODO: show correct plane --> generate viewing planes
            self.display_image(self.gV_back_proj, self.back_proj_uint8[self.current_back_proj_slice_idx])
            if self.current_back_proj_idx < self.num_proj_mats - 1 or self.current_back_proj_slice_idx < \
                    self.fwd_proj.shape[0] - 1:
                self.back_project()
            else:
                self.generate_viewing_planes()
                self.back_proj_completed = True
                self.on_plane_sel_changed()
                self.pB_back_proj.setDisabled(False)
        else:
            self.generate_viewing_planes()
            self.back_proj_completed = True
            self.on_plane_sel_changed()
            self.pB_back_proj.setDisabled(False)

    def on_plane_sel_changed(self):
        if not self.back_proj_loaded:
            return
        currentText = self.comboBox_plane_sel.currentText()
        if currentText == 'Axial':
            self.back_proj_disp = self.back_proj_axial
        elif currentText == 'Sagittal':
            self.back_proj_disp = self.back_proj_sagittal
        elif currentText == 'Coronal':
            self.back_proj_disp = self.back_proj_coronal
        self.display_image(self.gV_back_proj, self.back_proj_disp[0])
        self.scroll_back_proj.setValue(0)
        self.scroll_back_proj.setMaximum(self.back_proj_disp.shape[0] - 1)
        self.timeline_back_proj.setFrameRange(0, self.back_proj_disp.shape[0] - 1)
        self.on_speed_changed()

    def on_speed_changed(self):
        if not self.fwd_proj_completed and not self.back_proj_completed:
            return
        if self.fwd_proj_playing:
            self.timeline_fwd_proj.stop()
        if self.back_proj_playing:
            self.timeline_back_proj.stop()
        current_val_fwd_proj = self.timeline_fwd_proj.valueForTime(self.timeline_fwd_proj.currentTime())
        current_val_back_proj = self.timeline_back_proj.valueForTime(self.timeline_back_proj.currentTime())
        frame_duration = self.frame_duration_max - ((self.sB_speed.value() - 1) * self.frame_duration_dt)
        self.timeline_fwd_proj.setDuration(frame_duration * self.fwd_proj_filtered_uint8.shape[0])
        self.timeline_fwd_proj.setUpdateInterval(frame_duration)
        self.timeline_fwd_proj.setCurrentTime(self.timeline_fwd_proj.duration() * current_val_fwd_proj)
        self.timeline_back_proj.setDuration(frame_duration * self.back_proj_disp.shape[0])
        self.timeline_back_proj.setUpdateInterval(frame_duration)
        self.timeline_back_proj.setCurrentTime(self.timeline_back_proj.duration() * current_val_back_proj)
        if self.fwd_proj_playing:
            self.timeline_fwd_proj.resume()
        if self.back_proj_playing:
            self.timeline_back_proj.resume()

    def fwd_proj_play_pause(self):
        if not self.fwd_proj_loaded:
            return
        self.timeline_fwd_proj.stop()
        self.fwd_proj_playing = not self.fwd_proj_playing
        if self.fwd_proj_playing:
            self.pB_fwd_proj_play_pause.setIcon(self.icon_pause)
            if self.timeline_fwd_proj.currentValue() == 1.0:  # finished
                self.timeline_fwd_proj.start()
            else:
                self.timeline_fwd_proj.resume()
        else:
            self.timeline_fwd_proj.stop()
            self.pB_fwd_proj_play_pause.setIcon(self.icon_play)

    def back_proj_play_pause(self):
        if not self.back_proj_loaded:
            return
        self.timeline_back_proj.stop()
        self.back_proj_playing = not self.back_proj_playing
        if self.back_proj_playing:
            self.pB_back_proj_play_pause.setIcon(self.icon_pause)
            if self.timeline_back_proj.currentValue() == 1.0:  # finished
                self.timeline_back_proj.start()
            else:
                self.timeline_back_proj.resume()
        else:
            self.timeline_back_proj.stop()
            self.pB_back_proj_play_pause.setIcon(self.icon_play)

    def rot_mat_to_euler(self, R, deg=True):
        R = np.array(R)
        alpha_x = np.arctan2(R[2, 1], R[2, 2])
        alpha_y = np.arctan2(-R[2, 0], np.sqrt(R[1, 2] ** 2 + R[2, 2] ** 2))
        alpha_z = np.arctan2(R[0, 1], R[0, 0])
        if deg:
            alpha_x = np.rad2deg(alpha_x)
            alpha_y = np.rad2deg(alpha_y)
            alpha_z = np.rad2deg(alpha_z)
        return alpha_x, alpha_y, alpha_z

    def on_scroll_fwd_proj(self):
        if self.fwd_proj_loaded:
            frame_num = self.scroll_fwd_proj.value()
            self.display_image(self.gV_fwd_proj, self.fwd_proj_filtered_uint8[frame_num])
            use_conrad_proj_mat = False
            if use_conrad_proj_mat:
                conrad_proj_mats = self.conrad_config.getGeometry().getProjectionMatrices()
                R = conrad_proj_mats[frame_num].getR().as_numpy()
                print(self.rot_mat_to_euler(R))
                proj_mat = conrad_proj_mats[frame_num].computeP().as_numpy()
                self.set_vtk_proj_mat(pmat=proj_mat, rot=0)
            else:
                ang = frame_num * self.sB_ang_incr.value()
                self.set_vtk_proj_mat(pmat=None, rot=ang)

    def on_scroll_back_proj(self):
        if self.back_proj_loaded:
            self.display_image(self.gV_back_proj, self.back_proj_disp[self.scroll_back_proj.value()])

    def open_3D_Data(self): # TODO
        filename, _ = QFileDialog.getOpenFileName(self.centralwidget, "Open file", self.last_opened_dir_3D,
                                                  "(*.stl *.ply *.vtp *.obj *.vtk *.vti *.g)")
        if not len(filename):
            return
        self.last_opened_dir_3D = os.path.split(filename)[0]
        self.vtk_handle.display_file(filename)

    def change_language(self, lang):
        if self.translator.load(os.path.join("languages", lang + ".qm")):
            self.app.installTranslator(self.translator)
        self.retranslateUi(self.MainWindow)

    def resizeEvent(self):
        self.gV_fwd_proj.fitInView(self.pixmap_fwd_proj.boundingRect(), QtCore.Qt.KeepAspectRatio)
        self.gV_back_proj.fitInView(self.pixmap_back_proj.boundingRect(), QtCore.Qt.KeepAspectRatio)

    def on_pB_demo_acquisition(self):
        self.timeline_anim = QTimeLine()
        self.timeline_anim.setCurveShape(QTimeLine.LinearCurve)
        self.timeline_anim.setDuration(4000)
        self.timeline_anim.setFrameRange(0, self.sB_num_proj.value() - 1)
        self.timeline_anim.frameChanged.connect(self.demo_acquisition)
        self.timeline_anim.start()

    def demo_acquisition(self):
        self.set_vtk_proj_mat(rot=self.timeline_anim.currentFrame()*self.sB_ang_incr.value())

    def rotate_head(self):
        test = True
        if test:
            # scene = vtk.vtkAnimationScene()
            # scene.SetModeToRealTime()
            # scene.SetModeToSequence()
            # cb = vtkTimerCallback(actor=self.proj_mat_actor, duration=360, speed=0.005)
            # self.vtk_handle.iren.AddObserver('TimerEvent', cb.execute)
            # self.vtk_handle.iren.CreateTimer(0)
            # self.vtk_handle.iren.Start()
            if not self.fwd_proj_completed:
                return
            geo = self.conrad_config.getGeometry()
            self.timeline_anim = QTimeLine()
            frame_duration = 500
            self.timeline_anim.setDuration(geo.getProjectionStackSize() * frame_duration)
            self.timeline_anim.setFrameRange(0, geo.getProjectionStackSize() - 1)
            self.timeline_anim.frameChanged.connect(lambda i=self.timeline_anim.currentTime(): self.test_anim(i))
            self.timeline_anim.start()
            return
            d_ang = geo.getAverageAngularIncrement()
            for i in range(int(geo.getProjectionStackSize())):
                # self.proj_mat_actor.RotateZ(d_ang)
                self.display_image(self.gV_fwd_proj, self.fwd_proj_filtered_uint8[i])
                self.scroll_fwd_proj.setValue(i)
                # self.vtk_handle.update()

                # self.ren.ResetCamera()
                # self.ren.ResetCameraClippingRange()
                # self.vtk_handle.vtkWidget.Initialize()
                self.vtk_handle.iren.Initialize()
                # time.sleep(0.1)
                # print(i*d_ang)
        else:
            cb = vtkTimerCallback(actor=self.vtk_handle.actor, duration=360, speed=0.005)
            self.vtk_handle.iren.AddObserver('TimerEvent', cb.execute)
            self.vtk_handle.iren.CreateTimer(0)
            self.vtk_handle.iren.Start()
            # actor = self.vtk_handle.actor
            # for i in range(180):
            #    #t = vtk.vtkTransform()
            #    actor.RotateY(i/10)
            #    self.vtk_handle.iren.Initialize()
            #    time.sleep(1/20)

    def test_anim(self, i):
        geo = self.conrad_config.getGeometry()
        d_ang = geo.getAverageAngularIncrement()
        self.proj_mat_actor.RotateZ(d_ang)
        frame_num = self.timeline_anim.currentFrame()
        self.display_image(self.gV_fwd_proj, self.fwd_proj_filtered_uint8[frame_num])
        self.scroll_fwd_proj.setValue(frame_num)
        # self.vtk_handle.update()
        # self.ren.ResetCamera()
        # self.ren.ResetCameraClippingRange()
        # self.vtk_handle.vtkWidget.Initialize()
        self.vtk_handle.iren.Initialize()
        # time.sleep(0.1)
        # print(i*d_ang)

    def display_image_fwd_proj(self):
        if not self.fwd_proj_loaded:
            return
        frame_num = self.timeline_fwd_proj.currentFrame()
        # scroll_fwd_proj already displays image
        # self.display_image(self.gV_fwd_proj, self.fwd_proj_filtered_uint8[frame_num])
        self.scroll_fwd_proj.setValue(frame_num)

    def display_image_back_proj(self):
        if not self.back_proj_loaded:
            return
        frame_num = self.timeline_back_proj.currentFrame()
        # self.display_image(self.gV_back_proj, self.back_proj_disp[frame_num])
        self.scroll_back_proj.setValue(frame_num)

    def display_image(self, graphicsView, image):
        pixmapitem = QGraphicsPixmapItem(QPixmap(array2qimage(image)))
        if graphicsView == self.gV_fwd_proj:
            self.pixmap_fwd_proj = pixmapitem
        elif graphicsView == self.gV_back_proj:
            self.pixmap_back_proj = pixmapitem
        graphicsScene = QGraphicsScene()
        graphicsScene.addItem(pixmapitem)
        graphicsView.setScene(graphicsScene)
        self.resizeEvent()


class Window(QtWidgets.QMainWindow):
    resized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)

    def showEvent(self, event):
        self.resized.emit()
        return super(Window, self).showEvent(event)

    def resizeEvent(self, event):
        self.resized.emit()
        return super(Window, self).resizeEvent(event)


class vtkTimerCallback():
    def __init__(self, actor, duration, speed):
        self.actor = actor
        self.timer_count = 0
        self.duration = duration
        self.speed = speed

    def execute(self, obj, event):
        iren = obj
        if self.timer_count < self.duration:
            self.actor.RotateZ(self.timer_count * self.speed)
            iren.CreateTimer(1)
            iren.GetRenderWindow().Render()
            self.timer_count += 1
        else:
            iren.DestroyTimer()


if __name__ == '__main__':
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = Window()
    prog = InteractiveConeBeamReconstruction(MainWindow, app)
    MainWindow.show()
    sys.exit(app.exec_())
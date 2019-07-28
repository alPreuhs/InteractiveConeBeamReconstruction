import sys
import os
import pathlib
import traceback
import numpy as np
from enum import Enum

from PyQt5.QtCore import Qt, QTranslator, pyqtSignal, QTimeLine, qFatal
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QGraphicsPixmapItem, QGraphicsScene, QMessageBox, QDialog
from PyQt5.QtGui import QPixmap, QIcon
from qimage2ndarray import array2qimage
from SplashScreen import SplashScreen
from InteractiveConeBeamReconstruction_GUI import Ui_Interactive_Cone_Beam_Reconstruction
from VoxelizeWindow import VoxelizeMainWindow, VoxelizeWindow

from include.vtkWindow import vtkWindow
from include.help_functions import scale_mat_from_to, rot_mat_to_euler, dicom_to_numpy
from include.Config_XML import Config_XML
from Math.projection import create_default_projection_matrix, get_rotation_matrix_by_axis_and_angle
from Math.vtk_proj_matrix import vtk_proj_matrix
from GraphicsView import GraphicsView

import jpype
import pyconrad
pyconrad.setup_pyconrad(min_ram='4G')

from threads.forward_projection_thread import forwardProjectionThread
from threads.backward_projection_thread import backwardProjectionThread
from threads.filter_thread import filterThread

from edu.stanford.rsl.conrad.data.numeric import Grid2D, Grid3D
from edu.stanford.rsl.conrad.utils import Configuration
from edu.stanford.rsl.conrad.utils.Configuration import saveConfiguration, getGlobalConfiguration, setGlobalConfiguration
from edu.stanford.rsl.conrad.geometry.trajectories import CircularTrajectory
from edu.stanford.rsl.conrad.geometry.Projection import CameraAxisDirection
from edu.stanford.rsl.conrad.numerics import SimpleVector
from edu.stanford.rsl.conrad.geometry.shapes.simple import PointND


class InteractiveConeBeamReconstruction(Ui_Interactive_Cone_Beam_Reconstruction):
    def __init__(self, MainWindow, app):
        show_splash_screen = False
        if show_splash_screen:
            splash = SplashScreen('splash.gif', Qt.WindowStaysOnTopHint, msg='Loading Interactive Cone Beam Reconstruction...')
        self.debug = False

        self.MainWindow = MainWindow
        self.app = app

        # install translator
        self.translator = QTranslator()
        self.app.installTranslator(self.translator)

        self.init_icons()

        # traceback is disabled by default, the following reactivates it
        def excepthook(type_, value, traceback_):
            traceback.print_exception(type_, value, traceback_)
            qFatal('')
        sys.excepthook = excepthook

        # Setup UI, which is created via qt designer and pyuic5
        Ui_Interactive_Cone_Beam_Reconstruction.__init__(self)
        self.setupUi(self.MainWindow)
        self.MainWindow.resized.connect(self.resizeEvent)

        # Conrad configuration
        self.conrad_xml = os.path.join(str(pathlib.Path.home()), 'Conrad.xml') # config file in home folder
        Configuration.loadConfiguration() # load configuration from xml
        self.conrad_config = Configuration.getGlobalConfiguration()
        self.load_configuration() # set UI elements according to xml setup

        # pixmaps for resizing the graphicsviews
        self.pixmap_fwd_proj = QGraphicsPixmapItem()
        self.pixmap_back_proj = QGraphicsPixmapItem()

        self.config_xml_filename = 'config.xml'
        self.config = Config_XML()
        self.read_config_xml(filename=self.config_xml_filename)

        # setup VTK widget
        self.vtk_handle = vtkWindow()
        self.vtk_handle.vtkWidget(self.view_3D)
        self.vtk_handle.display_file(
            filename=self.config.config['mesh_filename'],
            rot=self.config.config['mesh_rot'],
            trans=self.config.config['mesh_trans'],
            scale=self.config.config['mesh_scale'],
            color=self.config.config['mesh_color'],
            reset_view=True
        )

        # init projection matrix for VTK widget
        sdd, sid = 700, 500
        off_u, off_v = 128, 128
        pmat = create_default_projection_matrix(pixel_spacing=1, sid=sdd, sisod=sid, offset_u=off_u, offset_v=off_v)
        self.proj_mat_actor = vtk_proj_matrix(pmat, sdd, off_u * 2, off_v * 2)
        self.vtk_handle.add_actor(self.proj_mat_actor)
        self.set_vtk_proj_mat()

        if self.debug:
            self.vtk_handle.add_coordinate_axes(length=200, color=[0, 1, 0]) # show coordinate axes

        # connect spin boxes
        # sdd = source to detector distance
        # sid = source to isocenter distance
        self.sB_sdd.valueChanged.connect(self.on_sB_sdd)
        self.sB_sid.valueChanged.connect(self.on_sB_sid)
        self.sB_pix_dim_x.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))
        self.sB_pix_dim_y.valueChanged.connect(lambda _: self.set_vtk_proj_mat(pmat=None, rot=0))
        self.sB_det_width.valueChanged.connect(self.on_sB_det_width)
        self.sB_det_height.valueChanged.connect(self.on_sB_det_height)
        self.sB_speed.valueChanged.connect(self.on_speed_changed)
        self.sB_sdd_simple.valueChanged.connect(self.on_sB_sdd_simple)
        self.sB_sid_simple.valueChanged.connect(self.on_sB_sid_simple)
        self.sB_det_width_simple.valueChanged.connect(self.on_sB_det_width_simple)
        self.sB_det_height_simple.valueChanged.connect(self.on_sB_det_height_simple)

        # connect horizontal sliders
        self.hS_sdd_simple.valueChanged.connect(self.on_hS_sdd_simple)
        self.hS_sid_simple.valueChanged.connect(self.on_hS_sid_simple)
        self.hS_det_width_simple.valueChanged.connect(self.on_hS_det_width_simple)
        self.hS_det_height_simple.valueChanged.connect(self.on_hS_det_height_simple)

        # connect menu bar items
        self.action_open_3D_data.triggered.connect(self.open_3D_Data)
        self.action_change_lang_en_GB.triggered.connect(lambda _: self.change_language('en_GB'))
        self.action_change_lang_de_DE.triggered.connect(lambda _: self.change_language('de_DE'))
        self.action_load_config.triggered.connect(lambda _: self.load_configuration(filename=''))
        self.action_save_config.triggered.connect(lambda _: self.save_configuration(filename=''))
        self.action_voxelize.triggered.connect(self.on_action_voxelize)
        self.action_set_phantom.triggered.connect(self.on_action_set_phantom)
        self.action_show_3D.triggered.connect(self.on_action_show_3D)
        self.action_show_fwd_proj.triggered.connect(self.on_action_show_fwd_proj)
        self.action_show_back_proj.triggered.connect(self.on_action_show_back_proj)
        self.action_show_config.triggered.connect(self.on_action_show_config_tabs)

        # connect (horizontal) scroll bars
        self.scroll_fwd_proj.sliderMoved.connect(self.on_scroll_fwd_proj)
        self.scroll_fwd_proj.valueChanged.connect(self.on_scroll_fwd_proj)
        self.scroll_back_proj.sliderMoved.connect(self.on_scroll_back_proj)
        self.scroll_back_proj.valueChanged.connect(self.on_scroll_back_proj)

        # connect buttons
        self.pB_fwd_proj.clicked.connect(self.on_pB_fwd_proj)
        self.pB_back_proj.clicked.connect(self.on_pB_back_proj)
        self.pB_fwd_proj_play_pause.clicked.connect(self.fwd_proj_play_pause)
        self.pB_back_proj_play_pause.clicked.connect(self.back_proj_play_pause)
        self.pB_reset_config.clicked.connect(self.reset_configuration)
        self.pB_demo.clicked.connect(self.on_pB_demo_acquisition)
        self.pB_reset_view.clicked.connect(self.reset_view)
        self.pB_set_reco_dim.clicked.connect(lambda _: self.set_reco_dim(x=None, y=None, z=None))
        self.pB_fluoro.clicked.connect(self.on_pB_fluoro)

        # play / pause icons
        self.icon_play = self.get_icon('play')
        self.icon_pause = self.get_icon('pause')

        # combo box for axial / sagittal / coronal plane views
        self.comboBox_plane_sel.currentTextChanged.connect(self.on_plane_sel_changed)

        # setup and connect threads for projections and backprojections
        self.fwd_proj_thread = forwardProjectionThread()
        self.fwd_proj_thread.finished.connect(self.on_fwd_proj_finished)
        self.fluoro_thread = forwardProjectionThread()
        self.fluoro_thread.finished.connect(self.on_fluoro_finished)
        self.fluoro_thread.parent = self
        self.back_proj_thread = backwardProjectionThread()
        self.back_proj_thread.finished.connect(self.on_back_proj_finished)

        # setup and connect threads for filters
        self.filter_thread_cosine = filterThread()
        self.filter_thread_cosine.finished.connect(lambda: self.on_filter_finished(cosine=True, ramlak=False))
        self.filter_thread_ramlak = filterThread()
        self.filter_thread_ramlak.finished.connect(lambda: self.on_filter_finished(cosine=False, ramlak=True))
        self.filter_thread_cosine_ramlak = filterThread()
        self.filter_thread_cosine_ramlak.finished.connect(lambda: self.on_filter_finished(cosine=True, ramlak=True))

        # connect check boxes for filters
        self.cB_ramlak_filter.stateChanged.connect(self.on_filter_cB_changed)
        self.cB_cosine_filter.stateChanged.connect(self.on_filter_cB_changed)

        self.gV_fwd_proj.scroll = self.scroll_fwd_proj
        self.gV_back_proj.scroll = self.scroll_back_proj

        # setup the frame duration for the slide shows
        self.frame_duration_min = 10
        self.frame_duration_max = 2000
        self.sB_speed.setMaximum(6)  # 5 steps
        self.frame_duration_dt = (self.frame_duration_max - self.frame_duration_min) / (self.sB_speed.maximum() - 1)
        self.frame_duration = self.frame_duration_max

        # setup and connect the time lines for the slide shows
        self.timeline_fwd_proj = QTimeLine()
        self.timeline_fwd_proj.setCurveShape(QTimeLine.LinearCurve)
        self.timeline_fwd_proj.frameChanged.connect(self.display_image_fwd_proj)
        self.timeline_fwd_proj.finished.connect(self.fwd_proj_play_pause)

        self.timeline_back_proj = QTimeLine()
        self.timeline_back_proj.setCurveShape(QTimeLine.LinearCurve)
        self.timeline_back_proj.frameChanged.connect(self.display_image_back_proj)
        self.timeline_back_proj.finished.connect(self.back_proj_play_pause)

        self.timeline_anim = QTimeLine()
        self.timeline_anim.setCurveShape(QTimeLine.LinearCurve)
        self.timeline_anim.setDuration(4000)
        self.timeline_anim.frameChanged.connect(self.demo_acquisition)

        # load phantom voxel data from file
        self.set_phantom_from_file(self.config.config['phantom_filename'])

        # projections indices for the threads
        self.current_fwd_proj_idx = 0
        self.current_back_proj_idx = 0

        self.fwd_proj_loaded = False
        self.back_proj_loaded = False
        self.fwd_proj_completed = False
        self.back_proj_completed = False
        self.fwd_proj_playing = False
        self.back_proj_playing = False
        self.fwd_proj_play_loop = False
        self.back_proj_play_loop = False

        self.perform_reco_after_proj = False

        self.plane_modes = Enum('Plane mode', 'Axial Sagittal Coronal')
        self.plane_mode = self.plane_modes.Axial

        self.current_language = 'en_GB'

        # when opening files or folders, save them for the next use
        self.last_opened_dir_3D = '.'
        self.last_opened_dir_xml = str(pathlib.Path.home())
        self.last_opened_dir_phantom = '.'

        if show_splash_screen:
            splash.finish(self.MainWindow)

        self.MainWindow.showMaximized()
        self.resizeEvent()

        if False:
            self.fwd_proj_uint8 = np.load('fwd.npz')
            self.fwd_proj_filtered_uint8 = self.fwd_proj_uint8[self.fwd_proj_uint8.files[0]]
            self.scroll_fwd_proj.setMaximum(self.fwd_proj_filtered_uint8.shape[0]-1)
            self.back_proj_uint8 = np.load('back.npz')
            self.back_proj_uint8 = self.back_proj_uint8[self.back_proj_uint8.files[0]]
            self.fwd_proj_loaded = True
            self.fwd_proj_completed = True
            self.back_proj_loaded = True
            self.back_proj_completed = True
            self.on_plane_sel_changed()
            self.on_speed_changed()


    def read_config_xml(self, filename):
        if os.path.isfile(filename):
            self.config.read(filename)
        else:
            self.config.init_config()

    def on_pB_fluoro(self):
        """Performs a single forward projection for the LAO/RAO angle 0°."""
        for button in [self.pB_fluoro, self.pB_fwd_proj, self.pB_back_proj]:
            button.setDisabled(True)
        msg = 'Performing Fluoroscopy'
        if self.current_language == 'de_DE':
            msg = 'Fluoro'
        self.statusBar.showMessage(msg)
        self.save_configuration(filename=self.conrad_xml)
        self.fluoro_thread.init(phantom=self.phantom, proj_idx=0, use_cl=self.cB_use_cl.isChecked(), parent=self)
        self.fluoro_thread.start()

    def on_fluoro_finished(self):
        """Displays the fluoro image when the thread is finished."""
        if len(self.fluoro_thread.error):
            msg = 'Could not perform fluoro. Volume dimensions possibly incorrect. Try clicking in "Set to phantom size".'
            if self.current_language == 'de_DE':
                msg = 'Fluoro konnte nicht durchgeführt werden. Möglicherweiße ist die Größe des Volumens falsch gesetzt. Klicke auf "Phantomgröße setzen".'
            self.msg_window(
                windowTitle='Error',
                text=msg,
                detailedText=self.fluoro_thread.error['message']+'\n\n'+self.fluoro_thread.error['stacktrace'],
                icon=self.get_icon('warning')
            )
        else:
            ##fluoro = scale_mat_from_to(self.fluoro_thread.get_fwd_proj()) # scale to 0 to 255
            ##self.display_image(self.gV_fwd_proj, fluoro)
            self.gV_fwd_proj.set_image(self.fluoro_thread.get_fwd_proj(), update_values=True)
        for button in [self.pB_fluoro, self.pB_fwd_proj, self.pB_back_proj]:
            button.setDisabled(False)
        self.statusBar.clearMessage()

    def set_reco_dim(self, x=None, y=None, z=None):
        """Sets the spin boxes of the reconstruction volume size."""
        if x is None: x = self.phantom.shape[2]
        if y is None: y = self.phantom.shape[1]
        if z is None: z = self.phantom.shape[0]
        self.sB_reco_dim_x.setValue(x)
        self.sB_reco_dim_y.setValue(y)
        self.sB_reco_dim_z.setValue(z)

    def on_action_set_phantom(self):
        """Gets the phantom file name from a dialog and sets the voxel volume used for the forward projection."""
        phantom_filename, _ = QFileDialog.getOpenFileName(self.centralwidget, 'Choose phantom file',
                                                          self.last_opened_dir_phantom, 'Numpy (*.npy;*.npz);;DICOM (*.dcm)')
        if phantom_filename:
            self.last_opened_dir_phantom = os.path.dirname(phantom_filename)
            self.set_phantom_from_file(phantom_filename)

    def set_phantom_from_file(self, filename: str):
        """
        Sets the voxel volume used for the forward projection from the given filename.
        Supports numpy files (.npy), numpy archives (.npz) and DICOM (.dcm).
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext.startswith('.np'):
            self.phantom = np.load(filename)
            if ext == '.npz':
                self.phantom = self.phantom[self.phantom.files[0]]
        elif ext == '.dcm':
            self.phantom = dicom_to_numpy(filename)
        else:
            pass # TODO

    def on_action_voxelize(self):
        """Opens the dialog for voxelizing meshes."""
        app = QDialog()
        MainWindow = VoxelizeMainWindow()
        prog = VoxelizeWindow(MainWindow, app)
        MainWindow.show()
        MainWindow.exec_()

    def change_language(self, lang: str):
        """Translates the UI to the specified language."""
        if self.translator.load(os.path.join('languages', lang + '.qm')):
            self.app.installTranslator(self.translator)
        self.retranslateUi(self.MainWindow)
        self.current_language = lang

    def msg_window(self, windowTitle='', text='', detailedText='', icon=None):
        """Opens message window with specified text."""
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
        # dictionary with icon filenames so they only need to be changed once
        self.icons = {}
        self.icons['play'] = 'play.svg'
        self.icons['pause'] = 'pause.svg'
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

    def get_icon(self, name: str):
        """Gets the QIcon for the specified name if its in the icons dictionary."""
        iconFilename = self.icons[name] if name in self.icons.keys() else 'blank.svg'
        iconFilename = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.iconPath, iconFilename)
        return QIcon(iconFilename) if os.path.isfile(iconFilename) else QIcon()

    def reset_view(self):
        """Resets the view of the VTK widget."""
        self.vtk_handle.reset_view()

    def on_sB_sdd_simple(self):
        val = self.sB_sdd_simple.value()
        if val > self.hS_sdd_simple.maximum(): # if the value is outside of the slider range
            self.hS_sdd_simple.setMaximum(val) # update the sliders maximum value
        self.hS_sdd_simple.setValue(val)
        self.sB_sdd.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_hS_sdd_simple(self):
        val = self.hS_sdd_simple.value()
        self.sB_sdd_simple.setValue(val)
        self.sB_sdd.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_sB_sid_simple(self):
        val = self.sB_sid_simple.value()
        if val > self.hS_sid_simple.maximum():
            self.hS_sid_simple.setMaximum(val)
        self.hS_sid_simple.setValue(val)
        self.sB_sid.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_hS_sid_simple(self):
        val = self.hS_sid_simple.value()
        self.sB_sid_simple.setValue(val)
        self.sB_sid.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_sB_det_width_simple(self):
        val = self.sB_det_width_simple.value()
        if val > self.hS_det_width_simple.maximum():
            self.hS_det_width_simple.setMaximum(val)
        self.hS_det_width_simple.setValue(val)
        self.sB_det_width.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_hS_det_width_simple(self):
        val = self.hS_det_width_simple.value()
        self.sB_det_width_simple.setValue(val)
        self.sB_det_width.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_sB_det_height_simple(self):
        val = self.sB_det_height_simple.value()
        if val > self.hS_det_height_simple.maximum():
            self.hS_det_height_simple.setMaximum(val)
        self.hS_det_height_simple.setValue(val)
        self.sB_det_height.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_hS_det_height_simple(self):
        val = self.hS_det_height_simple.value()
        self.sB_det_height_simple.setValue(val)
        self.sB_det_height.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_sB_sdd(self):
        val = self.sB_sdd.value()
        if val > self.hS_sdd_simple.maximum():
            self.hS_sdd_simple.setMaximum(val)
        self.hS_sdd_simple.setValue(val)
        self.sB_sdd_simple.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_sB_sid(self):
        val = self.sB_sid.value()
        if val > self.hS_sid_simple.maximum():
            self.hS_sid_simple.setMaximum(val)
        self.hS_sid_simple.setValue(val)
        self.sB_sid_simple.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_sB_det_width(self):
        val = self.sB_det_width.value()
        if val > self.hS_det_width_simple.maximum():
            self.hS_det_width_simple.setMaximum(val)
        self.hS_det_width_simple.setValue(val)
        self.sB_det_width_simple.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def on_sB_det_height(self):
        val = self.sB_det_height.value()
        if val > self.hS_det_height_simple.maximum():
            self.hS_det_height_simple.setMaximum(val)
        self.hS_det_height_simple.setValue(val)
        self.sB_det_height_simple.setValue(val)
        self.set_vtk_proj_mat(pmat=None, rot=0)

    def set_vtk_proj_mat(self, pmat=None, rot=0):
        """
        Displays the projection visualisation for the projection matrix for the given rotation angle.
        Uses the values from the config spin boxes.
        """
        self.vtk_handle.remove_actor(self.proj_mat_actor)
        # TODO: values from Conrad.xml may not be up to date with values from the ui spinboxes
        sdd = self.sB_sdd.value()
        sid = self.sB_sid.value()
        off_u = self.sB_det_height.value() / 2  # ?
        off_v = self.sB_det_width.value() / 2  # ?
        if pmat is None: # create projection matrix if not specified
            # set the LAO RAO angle label
            if rot == 0:
                self.label_angles.setText('LAO/RAO: 0°\tCRAN/CAUD: 0°')
            elif rot == 180:
                self.label_angles.setText('LAO/RAO: 180°\tCRAN/CAUD: 0°')
            elif rot < 180:
                self.label_angles.setText('RAO: {}°\tCRAN/CAUD: 0°'.format(rot))
            else:
                self.label_angles.setText('LAO: {}°\tCRAN/CAUD: 0°'.format(360-rot))
            rot -= 90 # like Conrad proj mats!? start from x-axis not y-axis!?
            pmat = create_default_projection_matrix(
                rao_lao_ang=rot,
                pixel_spacing=self.sB_pix_dim_x.value(),
                sid=sdd, sisod=sid,
                offset_u=off_u, offset_v=off_v
            )
        self.proj_mat_actor = vtk_proj_matrix(pmat, sdd, off_u * 2, off_v * 2)
        self.proj_mat_actor.GetProperty().SetColor(1, 0, 0)
        self.proj_mat_actor.GetProperty().SetLineWidth(5)
        self.vtk_handle.add_actor(self.proj_mat_actor)
        self.vtk_handle.update()

    def reset_configuration(self):
        """Reset the CONRAD.xml config file."""
        msg = 'Initilalising configuration'
        if self.current_language == 'de_DE':
            msg = 'Initialisiere Konfiguration'
        self.statusBar.showMessage(msg)
        Configuration.initConfig() # conrad config initialisation
        self.load_configuration(filename=self.conrad_xml) # load values into UI elements
        self.statusBar.clearMessage()

    def load_configuration(self, filename=os.path.join(str(pathlib.Path.home()), 'Conrad.xml')):
        """Loads conrad configuration from the Conrad.xml"""
        if not os.path.isfile(filename): # if file does not exist, open file dialog
            inf = 'Open CONRAD configuration'
            if self.current_language == 'de_DE':
                inf = 'CONRAD-Konfiguration öffnen'
            filename, _ = QFileDialog.getOpenFileName(self.centralwidget, inf,
                                                      self.last_opened_dir_xml, 'CONRAD (*.xml)')
            if not len(filename):
                return
            self.last_opened_dir_xml = os.path.dirname(filename)
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
        self.sB_sdd_simple.setValue(geo.getSourceToDetectorDistance())
        self.hS_sdd_simple.setValue(geo.getSourceToDetectorDistance())
        self.sB_sid_simple.setValue(geo.getSourceToAxisDistance())
        self.hS_sid_simple.setValue(geo.getSourceToAxisDistance())
        self.sB_det_width_simple.setValue(geo.getDetectorWidth())
        self.hS_det_width_simple.setValue(geo.getDetectorWidth())
        self.sB_det_height_simple.setValue(geo.getDetectorHeight())
        self.hS_det_height_simple.setValue(geo.getDetectorHeight())
        self.conrad_config = config
        self.conrad_geometry = geo

    def save_configuration(self, filename=os.path.join(str(pathlib.Path.home()), 'Conrad.xml')):
        """Saves the current configuration back to Conrad.xml"""
        if self.sB_sdd.value() <= self.sB_sid.value():
            txt = 'Source to detector distance must be larger than source to patient distance.'
            if self.current_language == 'de_DE':
                txt = 'Abstand Quelle zu Detektor muss größer sein als Abstand Quelle zu Patient'
            self.msg_window(windowTitle='Error',
                            text=txt,
                            icon=self.get_icon('warning'))
            return
        if not filename:
            inf = 'Save CONRAD configuration as'
            if self.current_language == 'de_DE':
                inf = 'CONRAD-Konfiguration speichern unter'
            filename, _ = QFileDialog.getSaveFileName(self.centralwidget, inf,
                                                      self.last_opened_dir_xml, 'CONRAD (*.xml)')
            if not len(filename):
                return
            self.last_opened_dir_xml = os.path.dirname(filename)
        # create trajectory
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
            reco_dim_z=self.sB_reco_dim_z.value(),
            reco_voxel_spacing_x=self.sB_reco_spacing_x.value(),
            reco_voxel_spacing_y=self.sB_reco_spacing_y.value(),
            reco_voxel_spacing_z=self.sB_reco_spacing_z.value()
        )
        self.conrad_config.setGeometry(geo)
        self.num_proj_mats = self.sB_num_proj.value()
        saveConfiguration(self.conrad_config, filename)
        Configuration.setGlobalConfiguration(self.conrad_config)

    # helper
    def get_camera_axis_direction_from_string(self, ax_dir):
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

    def conrad_circular_trajectory(self,
            n_proj=180,
            sid=600, sdd=1200,
            ang_incr=1.0,
            det_off_x=0, det_off_y=0,
            u_dir=CameraAxisDirection.DETECTORMOTION_PLUS, v_dir=CameraAxisDirection.ROTATIONAXIS_PLUS,
            rot_ax=[0, 0, 1], rot_center=[0, 0, 0],
            ang_start=0,
            det_width=620, det_height=480,
            pix_dim_x=1.0, pix_dim_y=1.0,
            reco_dim_x=256, reco_dim_y=256, reco_dim_z=256,
            reco_voxel_spacing_x=1.0, reco_voxel_spacing_y=1.0, reco_voxel_spacing_z=1.0
        ):
        """Returns conrad trajectory for the current configuration."""
        if type(u_dir) == str:
            u_dir = self.get_camera_axis_direction_from_string(u_dir)
        if type(v_dir) == str:
            v_dir = self.get_camera_axis_direction_from_string(v_dir)
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
        #trajectory.setReconVoxelSizes([1.0, 1.0, 1.0])
        trajectory.setVoxelSpacingX(reco_voxel_spacing_x)
        trajectory.setVoxelSpacingY(reco_voxel_spacing_y)
        trajectory.setVoxelSpacingZ(reco_voxel_spacing_z)
        trajectory.setOriginInPixelsX(float(reco_dim_x / 2))  # center
        trajectory.setOriginInPixelsY(float(reco_dim_y / 2))
        trajectory.setOriginInPixelsZ(float(reco_dim_z / 2))
        trajectory.setDetectorUDirection(u_dir)  # CameraAxisDirection.DETECTORMOTION_PLUS) # test
        trajectory.setDetectorVDirection(v_dir)  # CameraAxisDirection.ROTATIONAXIS_PLUS) # test
        trajectory.setTrajectory(int(n_proj), float(sid), float(ang_incr), float(det_off_x), float(det_off_y), u_dir,
                                 v_dir, rot_ax, rot_center, float(ang_start))
        return trajectory

    def on_pB_demo_acquisition(self):
        """Performs a dummy acquisition. Only displays the projection matrices, not the forward projections."""
        self.timeline_anim.setFrameRange(0, self.sB_num_proj.value() - 1)
        self.timeline_anim.start()

    def demo_acquisition(self):
        self.set_vtk_proj_mat(rot=self.timeline_anim.currentFrame()*self.sB_ang_incr.value())

    def on_pB_fwd_proj(self):
        """Saves the current configuration  and starts the forward projection."""
        for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
            button.setDisabled(True)
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        self.save_configuration(filename=self.conrad_xml)
        self.fwd_proj_completed = False
        self.fwd_proj_loaded = False
        geo = self.conrad_config.getGeometry()
        num_projs = geo.getProjectionStackSize()
        det_height = geo.getDetectorHeight()
        det_width = geo.getDetectorWidth()
        spacing = [geo.getVoxelSpacingX(), geo.getVoxelSpacingY(), geo.getVoxelSpacingZ()]
        self.fwd_proj = np.ndarray(shape=(num_projs, det_height, det_width)) # resulting forward projection
        self.fwd_proj_uint8 = np.ndarray(shape=(num_projs, det_height, det_width), dtype=np.uint8) # scaled to 0 to 255
        self.fwd_proj_filtered_uint8 = np.ndarray(shape=(num_projs, det_height, det_width), dtype=np.uint8) # filtered
        self.on_speed_changed()
        self.timeline_fwd_proj.setFrameRange(0, num_projs - 1)
        self.scroll_fwd_proj.setMaximum(num_projs - 1)
        self.fwd_proj_thread.init(phantom=self.phantom, spacing=spacing, use_cl=self.cB_use_cl.isChecked())
        if self.rB_all.isChecked(): # project all frames at once
            self.current_fwd_proj_idx = None
            self.fwd_proj_slice_by_slice = False
        else: # project slice by slice and displays the results immediately
            self.current_fwd_proj_idx = 0
            self.fwd_proj_slice_by_slice = True
        self.fwd_proj_thread.proj_idx = self.current_fwd_proj_idx
        self.fwd_project()

    def fwd_project(self):
        """Starts the forward projection thread."""
        msg = 'Performing forward projection'
        if self.current_language == 'de_DE':
            msg = 'Vorwärtsprojektion'
        if self.fwd_proj_slice_by_slice:
            self.statusBar.showMessage('{message}: {current_projection} / {num_projections}'.format(
                message=msg, current_projection=self.current_fwd_proj_idx+1, num_projections=self.num_proj_mats)
            )
        else:
            self.statusBar.showMessage(msg)
        # TODO: find memory leak in thread
        # only update index to reduce JVM memory (!?)
        # jpype.java.lang.Runtime.getRuntime().gc()
        # gc.collect()
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        self.fwd_proj_thread.start()

    def on_fwd_proj_finished(self):
        """
        Displays the (current) forward projection and starts the next projection or starts the filtering when the projection is done.
        """
        if len(self.fwd_proj_thread.error):
            msg = 'Could not perform forward projection.'
            if self.fwd_proj_thread.error['message'] is not None and ('memory' in self.fwd_proj_thread.error['message'] or 'Memory' in self.fwd_proj_thread.error['message']):
                msg += ' Volume dimensions possibly incorrect. Try clicking in "Set to phantom size".'
            if self.current_language == 'de_DE':
                msg = 'Vorwärtsprojektion konnte nicht durchgeführt werden.'
                if self.fwd_proj_thread.error['message'] is not None and ('memory' in self.fwd_proj_thread.error['message'] or 'Memory' in self.fwd_proj_thread.error['message']):
                    msg += ' Möglicherweiße ist die Größe des Volumens falsch gesetzt. Klicke auf "Phantomgröße setzen".'
            details = ''
            if self.fwd_proj_thread.error['message'] is not None:
                details += self.fwd_proj_thread['message']
            if self.fwd_proj_thread.error['stacktrace'] is not None:
                details += '\n\n'+self.fwd_proj_thread.error['stacktrace']
            self.msg_window(
                windowTitle='Error',
                text=msg,
                detailedText=details,
                icon=self.get_icon('warning')
            )
            for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                button.setDisabled(False)
            self.statusBar.clearMessage()
            return
        self.fwd_proj_loaded = True
        current_proj = self.fwd_proj_thread.get_fwd_proj()
        if self.fwd_proj_slice_by_slice:
            self.fwd_proj[self.current_fwd_proj_idx] = current_proj
            self.fwd_proj_uint8[self.current_fwd_proj_idx] = scale_mat_from_to(current_proj) # TODO: scaling every projection individually yields different result than scaling all projctions
            self.scroll_fwd_proj.setMaximum(self.current_fwd_proj_idx)
            self.scroll_fwd_proj.setValue(self.current_fwd_proj_idx)
            ##self.display_image(self.gV_fwd_proj, self.fwd_proj_uint8[self.current_fwd_proj_idx])
            self.gV_fwd_proj.set_image(self.fwd_proj[self.current_fwd_proj_idx], update_values=True)
            if self.current_fwd_proj_idx < self.num_proj_mats - 1: # if not all projections done
                self.current_fwd_proj_idx += 1
                self.fwd_proj_thread.proj_idx = self.current_fwd_proj_idx
                self.fwd_project()
            else: # done
                self.fwd_proj_uint8 = scale_mat_from_to(self.fwd_proj)
                self.gV_fwd_proj.update_values_from_image(self.fwd_proj)
                self.statusBar.clearMessage()
                self.filter_fwd_proj()
        else:
            self.fwd_proj = current_proj
            self.fwd_proj_uint8 = scale_mat_from_to(current_proj)
            self.scroll_fwd_proj.setMaximum(self.fwd_proj.shape[0] - 1)
            self.scroll_fwd_proj.setValue(0)
            self.gV_fwd_proj.update_values_from_image(self.fwd_proj)
            self.gV_fwd_proj.set_image(self.fwd_proj[0])
            ##self.display_image(self.gV_fwd_proj, self.fwd_proj_uint8[0])
            self.statusBar.clearMessage()
            self.filter_fwd_proj()

            #np.savez('fwd.npz', self.fwd_proj_uint8)

    def filter_fwd_proj(self):
        """Starts the threads for filtering the forward projection."""
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
        msg = 'Filtering projections'
        if self.current_language == 'de_DE':
            msg = 'Projektionen werden gefiltert'
        self.statusBar.showMessage(msg)
        self.filter_thread_cosine.start()
        self.filter_thread_ramlak.start()
        self.filter_thread_cosine_ramlak.start()

    def on_filter_finished(self, cosine, ramlak):
        if cosine and ramlak:
            if len(self.filter_thread_cosine_ramlak.error):
                msg = 'Could not filter projections.'
                if self.current_language == 'de_DE':
                    msg = 'Projektionen konnten nicht gefiltert werden.'
                details = ''
                if self.filter_thread_cosine_ramlak.error['message']is not None:
                    details += self.filter_thread_cosine_ramlak.error['message']
                if self.filter_thread_cosine_ramlak.error['stacktrace'] is not None:
                    details += '\n\n' + self.filter_thread_cosine_ramlak.error['stacktrace']
                self.msg_window(
                    windowTitle='Error',
                    text=msg,
                    detailedText=details,
                    icon=self.get_icon('warning')
                )
                for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                    button.setDisabled(False)
                self.statusBar.clearMessage()
                return
            self.fwd_proj_filtered_cosine_ramlak = self.filter_thread_cosine_ramlak.get_fwd_proj_filtered()
            self.fwd_proj_filtered_cosine_ramlak_uint8 = scale_mat_from_to(self.fwd_proj_filtered_cosine_ramlak)
            self.filter_cosine_ramlak_done = True
        elif cosine and not ramlak:
            if len(self.filter_thread_cosine.error):
                msg = 'Could not filter projections.'
                if self.current_language == 'de_DE':
                    msg = 'Projektionen konnten nicht gefiltert werden.'
                self.msg_window(
                    windowTitle='Error',
                    text=msg,
                    detailedText=self.filter_thread_cosine.error['message'] + '\n\n' + self.filter_thread_cosine.error['stacktrace'],
                    icon=self.get_icon('warning')
                )
                for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                    button.setDisabled(False)
                self.statusBar.clearMessage()
                return
            self.fwd_proj_filtered_cosine = self.filter_thread_cosine.get_fwd_proj_filtered()
            self.fwd_proj_filtered_cosine_uint8 = scale_mat_from_to(self.fwd_proj_filtered_cosine)
            self.filter_cosine_done = True
        elif not cosine and ramlak:
            if len(self.filter_thread_ramlak.error):
                msg = 'Could not filter projections.'
                if self.current_language == 'de_DE':
                    msg = 'Projektionen konnten nicht gefiltert werden.'
                self.msg_window(
                    windowTitle='Error',
                    text=msg,
                    detailedText=self.filter_thread_ramlak.error['message'] + '\n\n' + self.filter_thread_ramlak.error['stacktrace'],
                    icon=self.get_icon('warning')
                )
                for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                    button.setDisabled(False)
                self.statusBar.clearMessage()
                return
            self.fwd_proj_filtered_ramlak = self.filter_thread_ramlak.get_fwd_proj_filtered()
            self.fwd_proj_filtered_ramlak_uint8 = scale_mat_from_to(self.fwd_proj_filtered_ramlak)
            self.filter_ramlak_done = True
        else:
            pass  # TODO
        if self.filter_cosine_done and self.filter_ramlak_done and self.filter_cosine_ramlak_done: # all done
            self.fwd_proj_completed = True
            self.on_filter_cB_changed()
            for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                button.setDisabled(False)
            self.statusBar.clearMessage()
            if self.perform_reco_after_proj:
                self.on_pB_back_proj()

    def on_filter_cB_changed(self):
        """Updates the displayed image of the filtered forward projection."""
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
        ##self.display_image(self.gV_fwd_proj, self.fwd_proj_filtered_uint8[self.scroll_fwd_proj.value()])
        self.gV_fwd_proj.update_values_from_image(self.fwd_proj_filtered) # update from whole 3D array
        self.gV_fwd_proj.set_image(self.fwd_proj_filtered[self.scroll_fwd_proj.value()])

    def on_pB_back_proj(self):
        """Initialises the back projection."""
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        # self.save_configuration(filename=self.conrad_xml)
        if not self.fwd_proj_completed:
            title = 'Reconstruction not possible'
            msg = "First perform the forward projection by clicking on 'Scan'"
            if self.current_language == 'de_DE':
                title = 'Rekonstruktion nicht möglich'
                msg = "Führe erst die Vorwärtsprojektion über den Button 'Röntgen' durch"
            self.msg_window(windowTitle=title,
                            text=msg,
                            icon=self.get_icon('warning'))
            return
        for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
            button.setDisabled(True)
        self.back_proj_completed = False
        self.back_proj_loaded = False
        geo = self.conrad_config.getGeometry()
        zmax, ymax, xmax = geo.getReconDimensionZ(), geo.getReconDimensionY(), geo.getReconDimensionX()
        self.scroll_back_proj.setMaximum(zmax - 1)
        self.back_proj = np.zeros(shape=(zmax, ymax, xmax))
        self.back_proj_uint8 = np.zeros(shape=(zmax, ymax, xmax), dtype=np.uint8)
        #self.back_proj_disp = np.zeros(shape=(zmax, ymax, xmax), dtype=np.uint8)
        self.on_speed_changed()
        self.timeline_back_proj.setFrameRange(0, self.fwd_proj.shape[0] - 1)
        if self.rB_all.isChecked(): # backproject all at once
            self.back_proj_slice_by_slice = False
            self.current_back_proj_idx = None
            self.current_back_proj_slice_idx = None
        else: # backproject projection after projection
            self.back_proj_slice_by_slice = True
            self.current_back_proj_idx = 0
            self.current_back_proj_slice_idx = 0
        self.back_proj_thread.init(fwd_proj=self.fwd_proj_filtered, use_cl=self.cB_use_cl.isChecked(), proj_idx=self.current_back_proj_idx, slice_idx=self.current_back_proj_slice_idx)
        self.back_project()

    def back_project(self):
        """Starts the back projection thread."""
        msg = 'Performing backward projection'
        if self.current_language == 'de_DE':
            msg = 'Rückprojektion'
        if self.back_proj_slice_by_slice:
            slice = 'slice'
            proj = 'projection'
            if self.current_language == 'de_DE':
                slice = 'Schicht'
                proj = 'Projektion'
            self.statusBar.showMessage('{message}: {slice} {current_slice} / {num_slices}, {projection} {current_projection} / {num_projections}'.format(
                message=msg, slice=slice, current_slice=self.current_back_proj_slice_idx+1, num_slices=self.back_proj.shape[0],
                projection=proj, current_projection=self.current_back_proj_idx+1, num_projections=self.num_proj_mats
            ))
        else:
            self.statusBar.showMessage(msg)
        # temporary fix for JVM memory leak: JVM garbage collector hint
        jpype.java.lang.System.gc()
        self.back_proj_thread.start()

    def on_back_proj_finished(self):
        if len(self.back_proj_thread.error):
            msg = 'Could not perform back projection.'
            if self.current_language == 'de_DE':
                msg = 'Rückprojektion konnte nicht durchgeführt werden'
            details = ''
            if self.back_proj_thread.error['message'] is not None:
                details += self.back_proj_thread.error['message']
            if self.back_proj_thread.error['stacktrace'] is not None:
                details += '\n\n'+self.back_proj_thread.error['stacktrace']
            self.msg_window(
                windowTitle='Error',
                text=msg,
                detailedText=details,
                icon=self.get_icon('warning')
            )
            for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                button.setDisabled(False)
            self.statusBar.clearMessage()
            return
        current_reco = self.back_proj_thread.get_back_proj()
        if self.back_proj_slice_by_slice:
            self.back_proj = np.add(self.back_proj, current_reco)
        else:
            self.back_proj = current_reco
            self.gV_back_proj.update_values_from_image(self.back_proj)
        self.back_proj_uint8 = scale_mat_from_to(self.back_proj)
        self.back_proj_loaded = True
        if self.back_proj_slice_by_slice:
            # TODO: show correct plane --> can only show axial slice because of the reconstruction iteration
            ##self.display_image(self.gV_back_proj, self.back_proj_uint8[self.current_back_proj_slice_idx])
            self.gV_back_proj.set_image(self.back_proj, update_values=True)
            if self.current_back_proj_idx < self.num_proj_mats - 1:
                self.current_back_proj_idx += 1
            else:
                self.current_back_proj_idx = 0
                self.current_back_proj_slice_idx += 1
            self.back_proj_thread.proj_idx = self.current_back_proj_idx
            self.back_proj_thread.slice_idx = self.current_back_proj_slice_idx
            if self.current_back_proj_idx < self.num_proj_mats - 1 or self.current_back_proj_slice_idx < \
                    self.fwd_proj.shape[0] - 1:
                self.back_project()
            else:
                #self.generate_viewing_planes()
                self.gV_back_proj.update_values_from_image(self.back_proj)
                self.on_plane_sel_changed()
                self.back_proj_completed = True
                for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                    button.setDisabled(False)
                self.statusBar.clearMessage()
        else:
            #self.generate_viewing_planes()
            self.on_plane_sel_changed()
            self.back_proj_completed = True
            for button in [self.pB_fwd_proj, self.pB_fluoro, self.pB_back_proj]:
                button.setDisabled(False)
            self.statusBar.clearMessage()
            #np.savez('back.npz', self.back_proj_uint8)

    def generate_viewing_planes(self):
        """Rotates the reconstructed volume to show axial, sagittal and coronal planes."""
        # currently not used
        # TODO: check if rotations are correct
        self.back_proj_axial = np.rot90(self.back_proj_uint8, 2, (1, 2))
        self.back_proj_axial = np.rot90(self.back_proj_axial, 2, (0, 2))
        self.back_proj_sagittal = np.rot90(self.back_proj_uint8, 1, (1, 2))
        self.back_proj_sagittal = np.rot90(self.back_proj_sagittal, 1, (0, 1))
        self.back_proj_sagittal = np.rot90(self.back_proj_sagittal, 2, (1, 2))
        self.back_proj_coronal = np.rot90(self.back_proj_uint8, 1, (0, 1))
        self.back_proj_coronal = np.rot90(self.back_proj_coronal, 2, (0, 2))

    def on_plane_sel_changed(self):
        """Updates plane view."""
        if not self.back_proj_loaded:
            return
        currentText = self.comboBox_plane_sel.currentText()
        if currentText == 'Axial':
            self.plane_mode = self.plane_modes.Axial
        elif currentText == 'Sagittal':
            self.plane_mode = self.plane_modes.Sagittal
        elif currentText == 'Coronal':
            self.plane_mode = self.plane_modes.Coronal
        frame_max = self.get_back_proj_frame_max()
        #self.back_proj_disp = self.back_proj_uint8
        #self.display_image(self.gV_back_proj, self.back_proj_disp[0])
        ##self.display_image(self.gV_back_proj, self.get_image_for_current_view(slice=0))
        self.gV_back_proj.set_image(self.get_image_for_current_view(slice=0))
        self.scroll_back_proj.setValue(0)
        self.scroll_back_proj.setMaximum(frame_max)
        self.timeline_back_proj.setFrameRange(0, frame_max)
        self.on_speed_changed(back_proj_frame_max=frame_max)

    def get_back_proj_frame_max(self):
        if not self.back_proj_loaded: # if not self.back_proj_completed
            return 0
        if self.plane_mode == self.plane_modes.Axial:
            return self.back_proj_uint8.shape[0] - 1
        elif self.plane_mode == self.plane_modes.Sagittal:
            return self.back_proj_uint8.shape[1] - 1
        elif self.plane_mode == self.plane_modes.Coronal:
            return self.back_proj_uint8.shape[2] - 1

    def on_speed_changed(self, back_proj_frame_max=None):
        """Updates the timeline durations for the slide shows."""
        if not self.fwd_proj_completed and not self.back_proj_completed:
            return
        if self.fwd_proj_playing:
            self.timeline_fwd_proj.stop()
        current_val_fwd_proj = self.timeline_fwd_proj.currentValue()
        if self.back_proj_playing:
            self.timeline_back_proj.stop()
        current_val_back_proj = self.timeline_back_proj.currentValue()
        frame_duration = self.frame_duration_max - ((self.sB_speed.value() - 1) * self.frame_duration_dt)
        self.timeline_fwd_proj.setDuration(frame_duration * self.fwd_proj_filtered_uint8.shape[0])
        self.timeline_fwd_proj.setUpdateInterval(frame_duration)
        self.timeline_fwd_proj.setCurrentTime(self.timeline_fwd_proj.duration() * current_val_fwd_proj)
        if back_proj_frame_max is None:
            back_proj_frame_max = self.get_back_proj_frame_max()
        self.timeline_back_proj.setDuration(frame_duration * back_proj_frame_max)
        self.timeline_back_proj.setUpdateInterval(frame_duration)
        self.timeline_back_proj.setCurrentTime(self.timeline_back_proj.duration() * current_val_back_proj)
        if self.fwd_proj_playing:
            self.timeline_fwd_proj.resume()
        if self.back_proj_playing:
            self.timeline_back_proj.resume()

    def fwd_proj_play_pause(self):
        """Starts / pauses the forward projection slide show."""
        if not self.fwd_proj_loaded:
            return
        if self.fwd_proj_play_loop:
            self.timeline_fwd_proj.setCurrentTime(0)
            self.timeline_fwd_proj.start()
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
        """Starts / pauses the back projection slide show."""
        if not self.back_proj_loaded:
            return
        if self.back_proj_play_loop:
            self.timeline_back_proj.setCurrentTime(0)
            self.timeline_back_proj.start()
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

    def on_scroll_fwd_proj(self):
        """
        Updates the forward projection image in graphicsview and the projection matrix in the VTK widget when the slider is changed.
        """
        if not self.fwd_proj_completed:
            return
        frame_num = self.scroll_fwd_proj.value()
        ##self.display_image(self.gV_fwd_proj, self.fwd_proj_filtered_uint8[frame_num])
        self.gV_fwd_proj.set_image(self.fwd_proj_filtered[frame_num], update_values=False)
        use_conrad_proj_mat = False
        if use_conrad_proj_mat: # load projection matrices from conrad
            conrad_proj_mats = self.conrad_config.getGeometry().getProjectionMatrices()
            R = conrad_proj_mats[frame_num].getR().as_numpy()
            print(rot_mat_to_euler(R))
            proj_mat = conrad_proj_mats[frame_num].computeP().as_numpy()
            self.set_vtk_proj_mat(pmat=proj_mat, rot=0)
        else:
            ang = frame_num * self.sB_ang_incr.value()
            self.set_vtk_proj_mat(pmat=None, rot=ang)

    def on_scroll_back_proj(self):
        """Updates the back projection images in the graphicsview when the slider is changed."""
        if self.back_proj_loaded:
            ##self.display_image(self.gV_back_proj, self.get_image_for_current_view(slice=self.scroll_back_proj.value()))
            self.gV_back_proj.set_image(self.get_image_for_current_view(slice=self.scroll_back_proj.value()), update_values=False)

    def get_image_for_current_view(self, slice):
        """
        Gets the 2D image from the reconstructed volume for the currently selected view: axial / sagittal / coronal.
        """
        if self.plane_mode == self.plane_modes.Axial:
            # axial view from top to bottom --> access volume from end (-1) to start (0)
            # top: anterior, bottom: posterior
            # left: right, right: left
            ##return np.rot90(self.back_proj_uint8[self.back_proj_uint8.shape[0] - 1 - slice, :, :], k=-1)
            return np.rot90(self.back_proj[self.back_proj.shape[0] - 1 - slice, :, :], k=-1)
        elif self.plane_mode == self.plane_modes.Sagittal:
            # sagittal view from left to right
            # top: super / cranial, bottom: inferior / caudal
            # left: anterior, right: posterior
            ##return self.back_proj_uint8[:, slice, :]
            return self.back_proj[:, slice, :]
        elif self.plane_mode == self.plane_modes.Coronal:
            # coronal view from back to front --> access volume from end (-1) to start (0)
            # top: superior, bottom: inferior
            # left: right, right: left --> fliplr
            ##return np.fliplr(self.back_proj_uint8[:, :, self.back_proj_uint8.shape[2] - 1 - slice])
            return np.fliplr(self.back_proj[:, :, self.back_proj.shape[2] - 1 - slice])

    def display_image_fwd_proj(self):
        if self.fwd_proj_loaded:
            self.scroll_fwd_proj.setValue(self.timeline_fwd_proj.currentFrame())

    def display_image_back_proj(self):
        if self.back_proj_loaded:
            self.scroll_back_proj.setValue(self.timeline_back_proj.currentFrame())

    def display_image(self, graphics_view, image):
        """Displays the specified image in the specified graphicsview and fits the content to the view."""
        return # tmp
        pixmap_item = QGraphicsPixmapItem(QPixmap(array2qimage(image)))
        if graphics_view == self.gV_fwd_proj:
            self.pixmap_fwd_proj = pixmap_item
        elif graphics_view == self.gV_back_proj:
            self.pixmap_back_proj = pixmap_item
        graphics_scene = QGraphicsScene()
        graphics_scene.addItem(pixmap_item)
        graphics_view.setScene(graphics_scene)
        self.resizeEvent()

    def open_3D_Data(self): # TODO
        inf = 'Open file'
        if self.current_language == 'de_DE':
            inf = 'Datei öffnen'
        filename, _ = QFileDialog.getOpenFileName(self.centralwidget, inf, self.last_opened_dir_3D,
                                                  '(*.stl *.ply *.vtp *.obj *.vtk *.vti *.g)')
        if not len(filename):
            return
        self.last_opened_dir_3D = os.path.dirname(filename)
        self.vtk_handle.display_file(filename)

    def show_3D(self, show=True):
        self.frame_3D.setVisible(show)
        self.resizeEvent()

    def on_action_show_3D(self):
        self.show_3D(self.action_show_3D.isChecked())
        # workaround because calling only resizeEvent does not work
        if self.frame_fwd_proj.isVisible():
            for s in [False, True]:
                self.show_fwd_proj(s)
        if self.frame_back_proj.isVisible():
            for s in [False, True]:
                self.show_back_proj(s)

    def show_fwd_proj(self, show=True):
        for frame in [self.frame_fwd_proj, self.frame_fwd_proj_btns]:
            frame.setVisible(show)
        self.resizeEvent()

    def on_action_show_fwd_proj(self):
        self.show_fwd_proj(self.action_show_fwd_proj.isChecked())
        # workaround because calling only resizeEvent does not work
        if self.frame_back_proj.isVisible():
            for s in [False, True]:
                self.show_back_proj(s)

    def show_back_proj(self, show=True):
        for frame in [self.frame_back_proj, self.frame_back_proj_btns]:
            frame.setVisible(show)
        self.resizeEvent()

    def on_action_show_back_proj(self):
        self.show_back_proj(self.action_show_back_proj.isChecked())
        # workaround because calling only resizeEvent does not work
        if self.frame_fwd_proj.isVisible():
            for s in [False, True]:
                self.show_fwd_proj(s)

    def show_config_tabs(self, show=True):
        self.config_tabs.setVisible(show)
        self.resizeEvent()

    def on_action_show_config_tabs(self):
        self.show_config_tabs(self.action_show_config.isChecked())
        # workaround because calling only resizeEvent does not work
        if self.frame_fwd_proj.isVisible():
            for s in [False, True]:
                self.show_fwd_proj(s)
        if self.frame_back_proj.isVisible():
            for s in [False, True]:
                self.show_back_proj(s)

    def resizeEvent(self):
        self.gV_fwd_proj.resizeEvent()
        self.gV_back_proj.resizeEvent()


class Window(QMainWindow):
    resized = pyqtSignal()

    def __init__(self, parent=None):
        super(Window, self).__init__(parent=parent)

    def showEvent(self, event):
        self.resized.emit()
        return super(Window, self).showEvent(event)

    def resizeEvent(self, event):
        self.resized.emit()
        return super(Window, self).resizeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
            event.accept()
        elif event.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
            event.accept()
        #elif event.key() == Qt.Key_Alt:
        #    if self.menuBar().isVisible():
        #        self.menuBar().hide()
        #    else:
        #        self.menuBar().show()


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) # support high DPI displays
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True) # use high dpi svg icons
    app = QApplication(sys.argv)
    MainWindow = Window()
    prog = InteractiveConeBeamReconstruction(MainWindow, app)
    MainWindow.show()
    sys.exit(app.exec_())

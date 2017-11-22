import numpy as np
import vtk
from PyQt5 import QtWidgets
from dependency.InteractorStyle import InteractorStyle
from dependency.RenderWindowInteractor import *
from include import help_functions


## class that needs a qtFrame and places a vtk renderwindow inside
class vtkWindow():
    def vtkWidget(self, qtFrame):
        # the center computation might seem to be a bit complicated however what we do is:
        # the center_of_rotation gives the center of rotation in pixel coordinates


        self.vl = QtWidgets.QGridLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(qtFrame)

        self.vl.addWidget(self.vtkWidget)
        self.vl.setContentsMargins(0, 0, 0, 0)

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)

        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        # Create an actor
        self.arrowSource = vtk.vtkArrowSource()
        reader = vtk.vtkSTLReader()
        reader.SetFileName('include/Head_Phantom.stl')
        reader.Update()

        polydata = reader.GetOutput()

        pd_center = polydata.GetCenter()
        pd_bounds = polydata.GetBounds()
        #   spacing = polydata.GetSpacing()
        # todo: use bounds to scale the translation stuff
        transform = vtk.vtkTransform()

        R = help_functions.get_rotation(-90, 0,
                                        0)  # (nicken (LinksUnten, von schulter zu schuler links oben, verneinen rechts Oben)
        t = np.matrix([[1.0, 0, 0, -pd_center[0]],
                       [0, 1.0, 0, -pd_center[1]],
                       [0, 0, 1.0, -pd_center[2] + 206 * (1 / 3)],  # 1054.8
                       [0, 0, 0, 1]])
        transform.Identity()
        matrix = help_functions.GetVTKMatrix(R * t)
        transform.Concatenate(matrix)
        # polydata.Update();
        mapper2 = vtk.vtkPolyDataMapper()
        mapper2.SetInputConnection(reader.GetOutputPort())

        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetInputData(polydata)
        transformFilter.SetTransform(transform)
        transformFilter.Update()
        pdm = vtk.vtkPolyDataMapper()
        pdm.SetInputConnection(transformFilter.GetOutputPort())

        # Create a mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(self.arrowSource.GetOutputPort())

        #  mapper.SetScalarRange(scalar_range)
        self.actor = vtk.vtkActor()
        #self.actor.GetProperty().SetColor(color[0], color[1], color[2])
        # self.actor.SetMapper(mapper)
        self.actor.SetMapper(pdm)
        self.ren.SetBackground(.1, .2, .3)

        # def DummyFunc1(obj, ev):
        #    print("Before Event")
        #
        # def DummyFunc2(obj, ev):
        #    print("After Event")

        # self.set_rotation([0,0,0,30,20,40])

        self.ren.AddActor(self.actor)

        self.vtkWidget.Initialize()
        self.iren.Initialize()

        # Set the InteractorStyle to self written Interactor style, where we can
        # access the signals (i think .AddObserver("...event..., func") would do the same...)
        self.iren.SetInteractorStyle(InteractorStyle(parent=self.iren))

        # self.iren.AddObserver("MouseWheelForwardEvent", DummyFunc1, 1.0)
        # self.iren.AddObserver('MiddleButtonPressEvent', DummyFunc2, -1.0)

        qtFrame.setLayout(self.vl)

        self.initial_camera = vtk.vtkCamera()
        self.initial_camera.DeepCopy(self.ren.GetActiveCamera())

    def init_camera(self):
        initial_camera = vtk.vtkCamera()
        initial_camera.DeepCopy(self.initial_camera)
        self.ren.SetActiveCamera(initial_camera)

        self.iren.Initialize()

    def set_rotation(self, rotation):
        rotMat = help_functions.get_Rt(rotation)

        transform = vtk.vtkTransform()
        transform.Identity()
        matrix = help_functions.GetVTKMatrix(rotMat)
        transform.Concatenate(matrix)

        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetTransform(transform)
        transformFilter.SetInputConnection(self.arrowSource.GetOutputPort())
        transformFilter.Update()

        coneMapper = vtk.vtkPolyDataMapper()
        coneMapper.SetInputConnection(transformFilter.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(coneMapper)

        self.actor.SetUserTransform(transform)
        self.ren.ResetCameraClippingRange()
        self.vtkWidget.Initialize()
        self.iren.Initialize()
        # enable user interface interactor
        # iren.Initialize()
        # renWin.Render()
        # iren.Start()
        # print("try to set rotation")

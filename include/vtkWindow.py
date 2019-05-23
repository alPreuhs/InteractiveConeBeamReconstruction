import numpy as np
import vtk
from PyQt5 import QtWidgets
from dependency.InteractorStyle import InteractorStyle
from dependency.RenderWindowInteractor import *
from include import help_functions
from os.path import splitext, isfile, join
import random


## class that needs a qtFrame and places a vtk renderwindow inside
class vtkWindow():
    def vtkWidget(self, qFrame, filename=''):
        # the center computation might seem to be a bit complicated however what we do is:
        # the center_of_rotation gives the center of rotation in pixel coordinates

        self.vl = QtWidgets.QGridLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(qFrame)
        self.vl.addWidget(self.vtkWidget)
        self.vl.setContentsMargins(0, 0, 0, 0)

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)

        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        # Create an actor
        self.arrowSource = vtk.vtkArrowSource()

        self.focal_point = [0, 0, 0]

        # self.reader = vtk.vtkSTLReader()
        # self.reader.SetFileName(filename)
        # self.reader.Update()

        # polydata = self.reader.GetOutput()
        testing = 0
        if testing == 1:
            reader = vtk.vtkXMLImageDataReader()
            reader.SetFileName('C:\\Users\\jonas\\GitHub\\InteractiveConeBeamReconstruction\\shepplogan.vti')
            reader.Update()

            # Convert the image to a polydata
            imageDataGeometryFilter = vtk.vtkImageDataGeometryFilter()
            imageDataGeometryFilter.SetInputConnection(reader.GetOutputPort())
            imageDataGeometryFilter.Update()

            pdm = vtk.vtkPolyDataMapper()
            pdm.SetInputConnection(imageDataGeometryFilter.GetOutputPort())

            self.actor = vtk.vtkActor()
            self.actor.SetMapper(pdm)
            self.actor.GetProperty().SetPointSize(1)
            print('x')
            self.actor.GetProperty().SetRepresentationToWireframe()
        elif testing == 2:
            reader = vtk.vtkXMLImageDataReader()
            reader.SetFileName('C:\\Users\\jonas\\GitHub\\InteractiveConeBeamReconstruction\\shepplogan.vti')
            reader.Update()
            castFilter = vtk.vtkImageCast()
            castFilter.SetInputConnection(reader.GetOutputPort())
            castFilter.SetOutputScalarTypeToUnsignedShort()
            castFilter.Update()

            imdataBrainSeg = castFilter.GetOutput()

            propVolume = vtk.vtkVolumeProperty()
            propVolume.ShadeOff()
            # propVolume.SetColor(funcColor)
            # propVolume.SetScalarOpacity(funcOpacityScalar)
            # propVolume.SetGradientOpacity(funcOpacityGradient)
            propVolume.SetInterpolationTypeToLinear()

            funcRayCast = vtk.vtkVolumeRayCastCompositeFunction()
            funcRayCast.SetCompositeMethodToClassifyFirst()

            mapperVolume = vtk.vtkVolumeRayCastMapper()
            mapperVolume.SetVolumeRayCastFunction(funcRayCast)
            mapperVolume.SetInput(imdataBrainSeg)

            actorVolume = vtk.vtkVolume()
            actorVolume.SetMapper(mapperVolume)
            actorVolume.SetProperty(propVolume)

            self.actor = actorVolume

        self.actor = vtk.vtkActor()
        self.ren.AddActor(self.actor)
        self.ren.SetBackground(0.0, 0.0, 0.0)

        self.vtkWidget.Initialize()
        self.iren.Initialize()

        self.iren.SetInteractorStyle(InteractorStyle(parent=self.iren))

        qFrame.setLayout(self.vl)

        self.initial_camera = vtk.vtkCamera()
        # self.initial_camera.SetPosition(100, 0, 1000)
        self.initial_camera.DeepCopy(self.ren.GetActiveCamera())
        #if filename:
        #    self.display_file(filename)
        self.reset_view()


    def reset_view(self, x=-2000, y=-500, z=0):
        cam = self.ren.GetActiveCamera()
        cam.SetPosition(x, y, z)
        cam.SetViewUp(0, 0, 1)
        cam.SetFocalPoint(self.focal_point[0], self.focal_point[1], self.focal_point[2])
        self.ren.ResetCamera()
        self.update()

    @staticmethod
    def get_polydata(filename):
        reader = None
        ext = splitext(filename)[1].lower()
        if ext == ".ply":
            reader = vtk.vtkPLYReader()
        elif ext == ".vtp":
            reader = vtk.vtkXMLpoly_dataReader()
        elif ext == ".obj":
            reader = vtk.vtkOBJReader()
        elif ext == ".stl":
            reader = vtk.vtkSTLReader()
        elif ext == ".vtk":
            reader = vtk.vtkpoly_dataReader()
        elif ext == ".g":
            reader = vtk.vtkBYUReader()
        if reader is not None:
            reader.SetFileName(filename)
            reader.Update()
        else:
            raise IOError("Could not read %s" % filename)
        return reader.GetOutput()

    def display_file(self, filename, rot=[0,0,0], trans=[0,0,0], scale=[1,1,1], color=[1,1,1], reset_view=False):
        # supported_fileformats = ['.stl']
        # if not isfile(filename) or not splitext(filename)[1] in supported_fileformats:
        #    raise IOError('Could not read %s' % filename)
        # self.reader.SetFileName(filename)
        # self.reader.Update()
        # polydata = self.reader.GetOutput()
        try:
            polydata = self.get_polydata(filename)
        except IOError as e:
            print(e)

        pd_center = polydata.GetCenter()
        self.focal_point = pd_center
        transform = vtk.vtkTransform()
        R = help_functions.get_rotation(rot[0], rot[1], rot[2])
        t = np.identity(4)
        t[0:3,3] = (-1 * np.array(pd_center)) + np.array(trans)
        t = np.matrix(t)
        s = np.matrix(np.identity(4))
        s[0,0] = scale[0]
        s[1,1] = scale[1]
        s[2,2] = scale[2]
        transform.Identity()
        matrix = help_functions.GetVTKMatrix(s * R * t)
        transform.Concatenate(matrix)

        transformFilter = vtk.vtkTransformPolyDataFilter()
        transformFilter.SetInputData(polydata)
        transformFilter.SetTransform(transform)
        transformFilter.Update()
        pdm = vtk.vtkPolyDataMapper()
        pdm.SetInputConnection(transformFilter.GetOutputPort())

        self.actor.SetMapper(pdm)

        self.actor.GetProperty().SetColor(color[0], color[1], color[2])

        if reset_view:
            self.reset_view()

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

    def get_axis_label_actor(self, text, position, ren):
        atext = vtk.vtkVectorText()
        atext.SetText(text)
        textMapper = vtk.vtkPolyDataMapper()
        textMapper.SetInputConnection(atext.GetOutputPort())
        textActor = vtk.vtkFollower()
        textActor.SetMapper(textMapper)
        textActor.SetScale(20, 20, 20)
        textActor.AddPosition(position[0], position[1], position[2])
        textActor.GetProperty().SetColor(0, 0, 0)
        textActor.SetCamera(ren.GetActiveCamera())
        return textActor

    def add_coord(self, endPos, color, ren, startpos=(0, 0, 0), shatRadius=0.005, tipLength=0.05, tipRadius=0.015):
        arrowSource = vtk.vtkArrowSource()
        arrowSource.SetShaftRadius(shatRadius)
        arrowSource.SetTipLength(tipLength)
        arrowSource.SetTipRadius(tipRadius)
        arrowSource.SetShaftResolution(50)
        arrowSource.SetTipResolution(50)

        startPoint = [0 for i in range(3)]
        startPoint[0] = startpos[0]
        startPoint[1] = startpos[1]
        startPoint[2] = startpos[2]
        endPoint = [0 for i in range(3)]
        endPoint[0] = endPos[0]
        endPoint[1] = endPos[1]
        endPoint[2] = endPos[2]

        # Compute a basis
        normalizedX = [0 for i in range(3)]
        normalizedY = [0 for i in range(3)]
        normalizedZ = [0 for i in range(3)]

        # The X axis is a vector from start to end
        math = vtk.vtkMath()
        math.Subtract(endPoint, startPoint, normalizedX)
        length = math.Norm(normalizedX)
        math.Normalize(normalizedX)

        # The Z axis is an arbitrary vector cross X
        arbitrary = [0 for i in range(3)]
        arbitrary[0] = random.uniform(-10, 10)
        arbitrary[1] = random.uniform(-10, 10)
        arbitrary[2] = random.uniform(-10, 10)
        math.Cross(normalizedX, arbitrary, normalizedZ)
        math.Normalize(normalizedZ)

        # The Y axis is Z cross X
        math.Cross(normalizedZ, normalizedX, normalizedY)
        matrix = vtk.vtkMatrix4x4()

        # Create the direction cosine matrix
        matrix.Identity()
        for i in range(3):
            matrix.SetElement(i, 0, normalizedX[i])
            matrix.SetElement(i, 1, normalizedY[i])
            matrix.SetElement(i, 2, normalizedZ[i])

        # Apply the transforms
        transform = vtk.vtkTransform()
        transform.Translate(startPoint)
        transform.Concatenate(matrix)
        transform.Scale(length, length, length)

        # Transform the polydata
        transformPD = vtk.vtkTransformPolyDataFilter()
        transformPD.SetTransform(transform)
        transformPD.SetInputConnection(arrowSource.GetOutputPort())

        # Create a mapper and actor for the arrow
        mapper = vtk.vtkPolyDataMapper()
        actor = vtk.vtkActor()
        mapper.SetInputConnection(transformPD.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().LightingOff()
        ##alternatively to using the transform above one could use: actor.RotateZ etc and Scale
        actor.GetProperty().SetColor(color[0], color[1], color[2])
        ren.AddActor(actor)

    def update(self, full=False):
        if full:
            self.ren.ResetCamera()
            self.ren.ResetCameraClippingRange()
            self.vtkWidget.Initialize()
        self.iren.Initialize()

    def add_actor(self, actor):
        self.ren.AddActor(actor)

    def remove_actor(self, actor):
        self.ren.RemoveActor(actor)

    def add_coordinate_axes(self, length=200, color=[0,1,0]):
        textActor = self.get_axis_label_actor('x', [length, 0, 0], self.ren)
        textActor.GetProperty().SetColor(color[0], color[1], color[2])
        self.add_actor(textActor)
        textActor = self.get_axis_label_actor('y', [0, length, 0], self.ren)
        textActor.GetProperty().SetColor(color[0], color[1], color[2])
        self.add_actor(textActor)
        textActor = self.get_axis_label_actor('z', [0, 0, length], self.ren)
        textActor.GetProperty().SetColor(color[0], color[1], color[2])
        self.add_actor(textActor)
        self.add_coord([length, 0, 0], color, self.ren, shatRadius=0.02, tipLength=0.1, tipRadius=0.05)
        self.add_coord([0, length, 0], color, self.ren, shatRadius=0.02, tipLength=0.1, tipRadius=0.05)
        self.add_coord([0, 0, length], color, self.ren, shatRadius=0.02, tipLength=0.1, tipRadius=0.05)
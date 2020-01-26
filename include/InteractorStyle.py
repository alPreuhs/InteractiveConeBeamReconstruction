import vtk


##Class that can be used as InteractionStyle, where events can be catched
class InteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        self.parent = vtk.vtkRenderWindowInteractor()
        if (parent is not None):
            self.parent = parent

            # self.AddObserver("KeyPressEvent", self.keyPress)
            # self.AddObserver("QMouseEvent", self.mouseEvent)
            # self.AddObserver("MouseEvent", self.mouseEvent)
            # self.AddObserver("MouseWheelForwardEvent", self.mouseEvent)
            # self.AddObserver("MouseWheelBackwardEvent", self.mouseEvent)
            # self.AddObserver("RightButtonPressEvent", self.mouseEvent)
            # self.AddObserver("LeftButtonPressEvent", self.mouseEvent)
        #
        # self.AddObserver("WheelEvent", self.mouseEvent)
        # self.AddObserver("wheelEvent", self.mouseEvent)

    def mouseEvent(self, obj, evet):
        a = 10
        # print("hu")

    def keyPress(self, obj, event):
        # print("huhu")
        key = self.parent.GetKeySym()
        if key == 'space':
            renderers = self.parent.GetRenderWindow().GetRenderers()
            cam = renderers.GetFirstRenderer().GetActiveCamera()
            # cam.Zoom(4.0)
            roll = cam.GetRoll()
            size = self.parent.GetSize()
            cam.GetFocalPoint()
            cam.UpdateViewport(renderers.GetFirstRenderer())
            cam.GetOrientation()
            cam.GetPosition()

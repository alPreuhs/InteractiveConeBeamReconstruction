import vtk
import numpy as np
from Math import ProjectiveGeometry as pg
# import ProjectiveGeometry as pg
from Math import projection


class vtk_proj_matrix(vtk.vtkActor):
    def __init__(self, proj_mat, sid, size_u, size_v, edges=0):
        self.sz_u = size_u
        self.sz_v = size_v
        self.set_parameters(proj_mat, sid, size_u=size_u, size_v=size_v)

    def set_parameters(self, proj_mat, sid, size_u=0, size_v=0):
        if size_u == 0:
            size_u = self.sz_u
        if size_v == 0:
            size_v = self.sz_v

        self.appendFilter = vtk.vtkAppendFilter()
        source_pos = projection.get_source_position(proj_mat)
        cone_edges = self.get_detector_edge_points(proj_mat, sid, size_u, size_v)
        self.add_cone_edges(source_pos, cone_edges)
        self.add_detector_frame(cone_edges)
        self.appendFilter.Update()
        combined = self.appendFilter.GetOutput()
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputConnection(self.appendFilter.GetOutputPort())
        self.SetMapper(mapper)

    def get_detector_edge_points(self, p, sid, size_u, size_v):
        p_inv = np.linalg.pinv(p)
        plane1 = pg.plane_p3(p[0, :])
        plane2 = pg.plane_p3(p[1, :])
        plane3 = pg.plane_p3(p[2, :])
        source_pos = (plane1.meet(plane2)).meet(plane3)
        plane_dtor = plane3.get_plane_at_distance(sid)
        #### Calculate the corner Points of Detector
        bp00 = pg.point_p2(0, 0).backproject(p_inv)
        bp01 = pg.point_p2(0, size_v).backproject(p_inv)
        bp10 = pg.point_p2(size_u, 0).backproject(p_inv)
        bp11 = pg.point_p2(size_u, size_v).backproject(p_inv)
        p00 = (bp00.join(source_pos)).meet(plane_dtor)
        p01 = (bp01.join(source_pos)).meet(plane_dtor)
        p10 = (bp10.join(source_pos)).meet(plane_dtor)
        p11 = (bp11.join(source_pos)).meet(plane_dtor)
        return (p00, p01, p10, p11)

    def add_source_pos(self, source_pos, color=(0.0, 0.0, 0.0)):
        cord = source_pos.get_euclidean_point()
        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetCenter(cord[0], cord[1], cord[2])
        sphereSource.SetRadius(10)
        self.appendFilter.AddInputData(sphereSource)

    def add_cone_edges(self, source_pos, edges):
        light_white = [0, 0, 0]
        lighter_white = [240, 240, 240]
        p00 = edges[0].get_euclidean_point()
        p01 = edges[1].get_euclidean_point()
        p10 = edges[2].get_euclidean_point()
        p11 = edges[3].get_euclidean_point()
        sp = source_pos.get_euclidean_point()

        points = vtk.vtkPoints()
        points.SetNumberOfPoints(5)
        points.SetPoint(0, p00[0], p00[1], p00[2])
        points.SetPoint(1, p01[0], p01[1], p01[2])
        points.SetPoint(2, p10[0], p10[1], p10[2])
        points.SetPoint(3, p11[0], p11[1], p11[2])
        points.SetPoint(4, sp[0], sp[1], sp[2])

        lines = vtk.vtkCellArray()
        lines.InsertNextCell(7)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(4)
        lines.InsertCellPoint(1)
        lines.InsertCellPoint(4)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(4)
        lines.InsertCellPoint(3)
        pd = vtk.vtkPolyData()
        pd.SetPoints(points)
        pd.SetLines(lines)
        self.appendFilter.AddInputData(pd)

    def add_detector_frame(self, edges):
        # define color
        black = [0, 0, 0]
        # extract edge points
        p00 = edges[0].get_euclidean_point()
        p01 = edges[1].get_euclidean_point()
        p10 = edges[2].get_euclidean_point()
        p11 = edges[3].get_euclidean_point()
        # converte points to vtkPoints
        points = vtk.vtkPoints()
        points.SetNumberOfPoints(4)
        points.SetPoint(0, p00[0], p00[1], p00[2])
        points.SetPoint(1, p01[0], p01[1], p01[2])
        points.SetPoint(2, p10[0], p10[1], p10[2])
        points.SetPoint(3, p11[0], p11[1], p11[2])
        # draw lines between vtkPoints
        lines = vtk.vtkCellArray()
        lines.InsertNextCell(5)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(1)
        lines.InsertCellPoint(3)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(0)
        # join points and lines within vtkpolydata
        polygon = vtk.vtkPolyData()
        polygon.SetPoints(points)
        polygon.SetLines(lines)
        # assign color to every point
        colors = vtk.vtkUnsignedCharArray()
        colors.SetNumberOfComponents(3)
        colors.SetName("Colors")
        # map polydata
        self.appendFilter.AddInputData(polygon)
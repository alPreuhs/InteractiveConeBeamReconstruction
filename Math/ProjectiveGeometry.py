import math
import numpy as np


def _join_pt_pt(point1, point2):
    '''
    :param point1:
    :param point2:
    :return: line represented by six parameters -- i.e. plücker coordinates
    '''
    x1, y1, z1, w1 = point1
    x2, y2, z2, w2 = point2

    p = z1 * w2 - w1 * z2
    q = y1 * w2 - w1 * y2
    r = y1 * z2 - z1 * y2
    s = x1 * w2 - w1 * x2
    t = x1 * z2 - z1 * x2
    u = x1 * y2 - y1 * x2
    return line_p3(p, q, r, s, t, u)


#
def _join_pt_ln(point, line):
    '''
    :param point:
    :param line:
    :return: The plane representing the join of point and line. If point and line are colinear the result will be 0,0,0,0
    '''
    x, y, z, w = point
    L = line.get_line_representation()

    pt = np.matrix([x, y, z, w])
    pl = (pt * L)
    a = pl[0, 0]
    b = pl[0, 1]
    c = pl[0, 2]
    d = pl[0, 3]
    return plane_p3(a, b, c, d)


## i think we don't need this one
def _join_pt_pl(point, plane):
    x, y, z, w = point
    a, b, c, d = plane
    return x * a + y * b + z * c + w * d


def _get_nearest_point(ln):
    x, y, z = ln.get_direction()
    pl = plane_p3(x, y, z, 0)
    pt = ln.meet(pl)
    return pt


## i think we don't need this one
'''
def join_ln_ln(line1, line2):
    number = 0
    return False
'''


def _meet_pl_pl(plane1, plane2):
    '''
    :param plane1:
    :param plane2:
    :return: Line representing the intersection of the two planes. If planes are parallel,
             the result will be a line at infinity (thus  at least p,q,s will be zero)
    '''

    a1, b1, c1, d1 = plane1
    a2, b2, c2, d2 = plane2

    u = -(c1 * d2 - c2 * d1)
    t = b1 * d2 - b2 * d1
    s = -(b1 * c2 - b2 * c1)
    p = -(a1 * b2 - a2 * b1)
    q = a1 * c2 - a2 * c1
    r = -(a1 * d2 - a2 * d1)
    return line_p3(p, q, r, s, t, u)


def _meet_pl_ln(plane, ln):
    '''
    :param plane:
    :param ln:
    :return: The point of intersection between plane and line. If line is fully contained in the plane
             the result will be 0,0,0,0
    '''
    # primal plücker * plane
    ##we need the point defined in primal coordinates
    K = ln.get_plane_representation()

    a, b, c, d = plane
    pl = np.matrix([a, b, c, d]).transpose()
    pt = K * pl
    x = pt[0, 0]
    y = pt[1, 0]
    z = pt[2, 0]
    w = pt[3, 0]
    return point_p3(x, y, z, w)


###dont think we need this
'''
def meet_pl_pt(plane, point):
    number = 0
    return False
'''


def _meet_ln_ln(line1, line2):
    '''
    :param line1:
    :param line2:
    :return: If the two lines intersect: the point of intersection is given back.
             If the two lines do not intersect, the orthogonal distance is given back
             If the two lines are the same, zero is given back
    '''
    L = line1.get_line_representation()
    K = line2.get_plane_representation()
    N = K * L
    # trace of N is proportional to the orthogonal distance between two lines
    orth_distance = np.trace(N)

    if math.fabs(orth_distance) > 0.001:
        # the lines intersect
        for i in range(4):
            x = N[0, i]
            y = N[1, i]
            z = N[2, i]
            w = N[3, i]
            if w > 0.001 or w < -0.001:
                return point_p3(x, y, z, w)
    else:
        return orth_distance


class line_p3():
    def __init__(self, p=0, q=0, r=0, s=0, t=0, u=0):
        self.line = p, q, r, s, t, u


    def calculate_intersection(self, line2):

        startA = self.get_point_on_line()
        dirA = self.dir()
        dirA /= np.linalg.norm(dirA)

        startB = line2.get_point_on_line()
        dirB = line2.dir()
        dirB /= np.linalg.norm(dirB)

       #pA2 = np.array(startA) + 1000 * dirA
       #pB2 = np.array(startB) + 1000 * dirB

        c = np.cross(dirA, dirB)
        matA = np.zeros((3, 3), dtype=np.float64)

        matA[0, 0] = c[0]
        matA[1, 0] = c[1]
        matA[2, 0] = c[2]

        matA[0, 1] = dirA[0]
        matA[1, 1] = dirA[1]
        matA[2, 1] = dirA[2]

        matA[0, 2] = -dirB[0]
        matA[1, 2] = -dirB[1]
        matA[2, 2] = -dirB[2]
        b0 = np.array(startB.e()) - np.array(startA.e())
        M_pseudo = np.linalg.pinv(matA) * np.matrix(b0).T
        w = np.matrix(startA.e()) + M_pseudo[1, 0] * np.matrix(dirA) + 0.5 * M_pseudo[0, 0] * np.matrix(c)
        w2 = np.matrix(startB.e()) + M_pseudo[2, 0] * np.matrix(dirB) + 0.5 * M_pseudo[0, 0] * np.matrix(c)
        return w

    def get_intersection_of_common_perpendicular(self, line2):
        return self.calculate_intersection(line2)
        p1,q1,r1,s1,t1,u1 = self.line
        p2,q2,r2,s2,t2,u2 = line2.get_flat()

        l1 = np.array([s1, q1, p1])
        l1 /= np.linalg.norm(l1)
        l2 = np.array([s2, q2, p2])
        l2 /= np.linalg.norm(l2)
        pt1 = np.array(self.get_point_on_line().e())
        pt2 = np.array(line2.get_point_on_line().e())

        m1 = np.cross(pt1, l1)
        m2 = np.cross(pt2, l2)

        tmp_1 = np.cross(-m1,np.cross(l2,np.cross(l1,l2)))
        tmp_2 = np.dot(m2,np.cross(l1,l2))*l1
        scale = np.linalg.norm(np.cross(l1,l2))
        p1_star = (tmp_1+tmp_2)/scale
        toret1 = point_p3(p1_star[0],p1_star[1],p1_star[2])

        tmp_1 = np.cross(m2, np.cross(l1, np.cross(l1, l2)))
        tmp_2 = np.dot(m1, np.cross(l1, l2)) * l2
        scale = np.linalg.norm(np.cross(l1, l2))
        p2_star = (tmp_1 - tmp_2) / scale
        toret2 = point_p3(p2_star[0], p2_star[1], p2_star[2])
        return toret1, toret2



    def line_by_dire_point(self, direction, point_on_line):
        s, q, p = direction

        dir_vec = np.array([s, q, p])
        x, y, z = point_on_line

        pt = np.array([x, y, z])
        moment = np.cross(dir_vec, pt)
        r = moment[0]
        t = - moment[1]
        u = moment[2]
        self.primal = True
        return line_p3(p, q, r, s, t, u)

    def get_point_on_line(self):
        pl_tmp = np.matrix([0, 0, 0, 0],dtype=np.float32)
        pl_tmp[0, 0:3] = self.get_direction()
        pl = plane_p3(pl_tmp)
        return pl.meet(self)

    def project(self, projMatrix):
        K_p = projMatrix * self.K() * projMatrix.T
        l0 = K_p[1, 2]
        l1 = K_p[2, 0]
        l2 = K_p[0, 1]
        return line_p2(l0, l1, l2)

    def transform(self, homography):
        K_t = homography * self.K() * homography.T
        p = K_t[3, 2]
        q = K_t[3, 1]
        s = K_t[3, 0]
        t = K_t[2, 0]
        u = K_t[1, 0]
        r = K_t[2, 1]
        return line_p3(p, q, r, s, t, u)

    #    def get_nearest_point(self):
    #        return get_nearest_point(self)

    def get_line(self):
        return self.line

    def get_flat(self):
        return self.line

    def dir(self):
        return self.get_direction()

    def get_direction(self):
        # at least true for primal
        p, q, r, s, t, u = self.line
        return s, q, p

    def get_orthogonal_distance(self):
        p, q, r, s, t, u = self.line
        return math.sqrt((r * r + t * t + u * u) / (s * s + q * q + p * p))

    def join(self, geometric_citicen):
        flat = geometric_citicen.get_flat()
        if isinstance(geometric_citicen, type(point_p3())):
            # print('line join point -> Plane')
            return _join_pt_ln(flat, self)

        elif isinstance(geometric_citicen, type(line_p3())):
            # print('line join line -> Number')
            # return join_ln_ln(self.line,flat)
            print('line join line not supported')
        else:
            print('You try to join a line --- line can only join with points and lines')

    def meet(self, geometric_citicen):
        flat = geometric_citicen.get_flat()
        if isinstance(geometric_citicen, type(line_p3())):
            # print('line meet line -> Number')
            return _meet_ln_ln(self, geometric_citicen)

        elif isinstance(geometric_citicen, type(plane_p3())):
            # print('line meet plane -> Point')
            return _meet_pl_ln(flat, self)

        else:
            print('You try to meet a line --- line can only join with planes and lines')

    def L(self):
        return self.get_line_representation()

    def get_line_representation(self):
        p, q, r, s, t, u = self.line
        return np.matrix([[0, p, -q, r], [-p, 0, s, -t], [q, -s, 0, u], [-r, t, -u, 0]])

    def K(self):
        return self.get_plane_representation()

    def get_plane_representation(self):
        p, q, r, s, t, u = self.line
        return np.matrix([[0, -u, -t, -s], [u, 0, -r, -q], [t, r, 0, -p], [s, q, p, 0]])


class line_p2():
    def __init__(self, a=0.0, b=0.0, c=0.0):
        self.ln = a, b, c
        if isinstance(a, np.matrix):
            self.__set_point_by_matrix(a)

    def get_flat(self):
        return self.ln

    def __set_point_by_matrix(self, ln):
        col, row = ln.shape
        if col == 3:
            a = ln[0, 0]
            b = ln[1, 0]
            c = ln[2, 0]
            self.ln = a, b, c
        elif row == 3:
            a = ln[0, 0]
            b = ln[0, 1]
            c = ln[0, 2]
            self.ln = a, b, c

    def get_direction(self):
        a, b, c = self.ln
        norm_abc = math.sqrt(a * a + b * b)
        a /= norm_abc
        b /= norm_abc
        return b, -a

    def h(self):
        return self.get_hesse_form()

    def get_hesse_form(self):
        a, b, c = self.ln
        norm_abc = math.sqrt(a * a + b * b)
        a /= norm_abc
        b /= norm_abc
        c /= norm_abc
        return a, b, c

    def get_skew_matrix(self):
        a, b, c = self.ln
        return np.matrix([[0, c, -b], [-c, 0, a], [b, -a, 0]])

    def backproject(self, p_inv):
        ln_bp = p_inv * self.get_skew_matrix() * p_inv.T
        p = ln_bp[3, 2]
        q = ln_bp[3, 1]
        r = ln_bp[2, 1]
        s = ln_bp[3, 0]
        t = ln_bp[2, 0]
        u = ln_bp[1, 0]
        return line_p3(p, q, r, s, t, u)

    def meet(self, line):
        ln = np.cross(np.array(line.get_flat()), np.array(self.get_flat()))
        return point_p2(np.matrix(ln))


class plane_p3():
    def __init__(self, a=0.0, b=0.0, c=0.0, d=0.0):
        self.plane = a, b, c, d
        if isinstance(a, np.matrix):
            self.set_plane_by_matrix(a)
        elif isinstance(a, np.ndarray):
            self.set_plane_by_matrix(np.matrix(a))

    @staticmethod
    def define_plane_by_point_and_normal(normal, pt):
        normal /= np.linalg.norm(normal)
        d = -(np.matrix(pt.get_euclidean_point()) * normal)[0, 0]
        return plane_p3(normal[0, 0], normal[1, 0], normal[2, 0], d)

    def get_signed_distance_to_point(self, point):
        a, b, c, d = self.get_hesse_form()
        x, y, z = point.e()
        return (a * x + b * y + c * z + d)

    def get_plane_at_distance(self, distance):
        a, b, c, d = self.get_hesse_form()
        direction = np.matrix([a, b, c]).T
        closest_point_at_origin = -d * direction
        direction_of_desired_point = distance * direction
        point_new = closest_point_at_origin + direction_of_desired_point
        distance_new = -(direction.T * point_new)[0, 0]
        return plane_p3(a, b, c, distance_new)

    def set_plane_by_matrix(self, pl):
        col, row = pl.shape
        if col == 4:
            a = pl[0, 0]
            b = pl[1, 0]
            c = pl[2, 0]
            d = pl[3, 0]
            self.plane = a, b, c, d
        elif row == 4:
            a = pl[0, 0]
            b = pl[0, 1]
            c = pl[0, 2]
            d = pl[0, 3]
            self.plane = a, b, c, d

    def h(self):
        return self.get_hesse_form()

    def get_hesse_form(self):
        a, b, c, d = self.plane
        norm_abc = math.sqrt(a * a + b * b + c * c)
        a /= norm_abc
        b /= norm_abc
        c /= norm_abc
        d /= norm_abc
        return a, b, c, d

    def get_plane(self):
        return self.plane

    def get_flat(self):
        return self.plane

    def join(self, geometric_citicen):
        flat = geometric_citicen.get_flat()
        if isinstance(geometric_citicen, type(point_p3())):
            # print('plane join point -> Number')
            return _join_pt_pl(flat, self.plane)

        else:
            print('You try to join a plane --- plane can only join with points')

    def meet(self, geometric_citicen):
        flat = geometric_citicen.get_flat()
        if isinstance(geometric_citicen, type(point_p3())):
            # print('plane meet point -> Number')
            print('plane meet point is not supported')
            # return meet_pl_pt(self,flat)

        elif isinstance(geometric_citicen, type(line_p3())):
            # print('plane meet line -> Point')
            return _meet_pl_ln(self.plane, geometric_citicen)

        elif isinstance(geometric_citicen, type(plane_p3())):
            # print('plane meet plane -> Line')
            return _meet_pl_pl(self.plane, flat)

        else:
            print('You try to meet a plane --- plane can only meet with points, planes and lines')


class point_p3():
    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.point = x, y, z, w

        if isinstance(x, np.matrix):
            self.__set_point_by_matrix(x)
        elif isinstance(x, np.ndarray):
            self.__set_point_by_matrix(np.matrix(x))

    def __set_point_by_matrix(self, pt):
        col, row = pt.shape
        if col == 4:
            x = pt[0, 0]
            y = pt[1, 0]
            z = pt[2, 0]
            w = pt[3, 0]
            self.point = x, y, z, w
        elif row == 4:
            x = pt[0, 0]
            y = pt[0, 1]
            z = pt[0, 2]
            w = pt[0, 3]
            self.point = x, y, z, w
        elif col == 3:
            x = pt[0, 0]
            y = pt[1, 0]
            z = pt[2, 0]
            w = 1
            self.point = x, y, z, w
        elif row == 3:
            x = pt[0, 0]
            y = pt[0, 1]
            z = pt[0, 2]
            w = 1
            self.point = x, y, z, w

    def project(self, projMat):
        x, y, z, w = self.point
        point_vector = np.matrix([x, y, z, w]).transpose()
        projPoint = projMat * point_vector
        x_p2 = projPoint[0, 0]
        y_p2 = projPoint[1, 0]
        w_p2 = projPoint[2, 0]
        return point_p2(x_p2, y_p2, w_p2)

    def transform(self, homography):
        x, y, z, w = self.point
        point_vector = np.matrix([x/w, y/w, z/w, 1]).transpose()
        t_point = homography * point_vector
        x_p3 = t_point[0, 0]
        y_p3 = t_point[1, 0]
        z_p3 = t_point[2, 0]
        w_p3 = t_point[3, 0]
        return point_p3(x_p3, y_p3, z_p3, w_p3)

    def e(self):
        return self.get_euclidean_point()

    def get_euclidean_point(self):
        x, y, z, w = self.point
        if abs(w) > 0.0001:
            return x / w, y / w, z / w
        else:
            return x, y, z

    def get_point(self):
        return self.point

    def get_flat(self):
        return self.point

    def join(self, geometric_citicen):
        flat = geometric_citicen.get_flat()
        if isinstance(geometric_citicen, type(plane_p3())):
            # print('point join plane -> Number')
            return _join_pt_pl(self.point, flat)

        elif isinstance(geometric_citicen, type(point_p3())):
            # print('point join point -> Line')
            return _join_pt_pt(self.point, flat)

        elif isinstance(geometric_citicen, type(line_p3())):
            # print('point join line -> Plane')
            return _join_pt_ln(self.point, geometric_citicen)

        else:
            print('You try to join a point --- points can only join with lines, planes or points')

    def meet(self, geometric_citicen):
        flat = geometric_citicen.get_flat()
        if isinstance(geometric_citicen, type(plane_p3())):
            # print('point meet plane -> Number')
            # return meet_pl_pt(flat, self.point)
            print('plane meet point is not supported')

        else:
            print('You try to meet a point --- points can only meet with planes')


class point_p2():
    def __init__(self, x=0.0, y=0.0, w=1.0):
        self.pt = x, y, w

        if isinstance(x, np.matrix):
            self.set_point_by_matrix(x)

        elif isinstance(x, np.ndarray):
            self.set_point_by_matrix(np.matrix(x))

    def get_flat(self):
        return self.pt

    def set_point_by_matrix(self, pt):
        col, row = pt.shape
        if col == 3:
            x = pt[0, 0]
            y = pt[1, 0]
            w = pt[2, 0]
            self.pt = x, y, w
        elif row == 3:
            x = pt[0, 0]
            y = pt[0, 1]
            w = pt[0, 2]
            self.pt = x, y, w
        elif col == 2:
            x = pt[0, 0]
            y = pt[1, 0]
            w = 1
            self.pt = x, y, w
        elif row == 2:
            x = pt[0, 0]
            y = pt[0, 1]
            w = 1

            self.pt = x, y, w

    def e(self):
        return self.get_euclidean_point()

    def get_euclidean_point(self):
        x, y, w = self.pt
        if abs(w) > 0.0001:
            return x / w, y / w
        else:
            return x, y

    def backproject(self, projMat_inv):
        x, y, w = self.pt
        pt = np.matrix([x, y, w]).transpose()
        result = projMat_inv * pt
        x_3p = result[0, 0]
        y_3p = result[1, 0]
        z_3p = result[2, 0]
        w_3p = result[3, 0]
        return point_p3(x_3p, y_3p, z_3p, w_3p)

    def join(self, geometric_citicen):
        if isinstance(geometric_citicen, type(point_p2())):
            x1, y1, w1 = self.pt
            x2, y2, w2 = geometric_citicen.get_flat()
            p1 = np.array([x1, y1, w1])
            p2 = np.array([x2, y2, w2])
            ln = np.cross(p1, p2)
            a = ln[0]
            b = ln[1]
            c = ln[2]
            return line_p2(a, b, c)

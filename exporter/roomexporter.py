import itertools
import numpy as np

from generator.groom import HallwayGroom
from core.opening import Door, DoorFactory
from renderer.svgrenderer import RenderingParams

class LineTypes:
    RoomWall, Door, Dimension = range(3)

class RoomExporter(object):

    def __init__(self, floorplan, rparams=RenderingParams(100, 60), num_door_points = 5):
        self.rparams = rparams
        self.floorplan = floorplan
        self.num_door_points = num_door_points

    def scale_point(self, p):
        return p[0]*self.rparams.scaling, p[1]*self.rparams.scaling

    def export_lines(self):

        lines = []
        line_labels = []
        for room in self.floorplan.rooms:
            # todo: return room rectangles
            for edge in room.edges:
                positive_groom = edge.positive.groom if edge.positive is not None else None
                negative_groom = edge.negative.groom if edge.negative is not None else None
                if type(positive_groom) is HallwayGroom and type(negative_groom) is HallwayGroom:
                    continue
                p0, p1 = [self.scale_point(p) for p in edge.cartesian_points]
                line = np.append(p0,p1)
                line = np.append(line,np.array(self.rparams.room_stroke_width))
                lines.append(line)
                line_labels.append(LineTypes.RoomWall)

                for door in edge.doors:
                    door_lines = self.export_door_lines(edge,door)
                    lines.extend(door_lines)
                    line_labels.extend([LineTypes.Door] * len(door_lines))

            dimension_lines = self.export_dimension_lines(room)
            lines.extend(dimension_lines)
            line_labels.extend([LineTypes.Dimension] * len(dimension_lines))


        lines = np.array(lines)
        line_labels = np.array(line_labels)
        # todo: add room labels, add room rectangles
        return lines, line_labels


    def export_dimension_lines(self, room):
        lines = []
        for edge in room.edges:
            p0, p1 = [self.scale_point(p) for p in edge.cartesian_points]
            x0, y0 = p0
            x1, y1 = p1
            x, y = self.scale_point(room.center)
            c = np.array([x,y])
            # direction to shift the line
            e = np.array(p1)-np.array(p0)
            e = e / np.linalg.norm(e)
            n = np.array([-e[1], e[0]])
            if np.dot(n, c-p0)<0:
                n = -n
            # step inwards by a fixed amount (relative to scene size)
            # also step "along" the edge to make sure that arrow endpoints don't
            # land "inside" the thick room edge lines
            step = 0.01*self.rparams.scaling* max(self.rparams.width, self.rparams.height)
            step_along = self.rparams.room_stroke_width
            p0 = p0 + step_along * e + step *n
            p1 = p1 - step_along * e+ step *n
            # export main line of dimension
            line = np.append(p0,p1)
            line = np.append(line,np.array(self.rparams.dimension_stroke_width))
            lines.append(line)
            arrow_angle = 30*np.pi/180
            arrow_length = 0.005*self.rparams.scaling* max(self.rparams.width, self.rparams.height)
            ca = np.cos(arrow_angle)
            sa = np.sin(arrow_angle)
            R = np.array([[ca,-sa],[sa,ca]])
            Rt = np.array([[ca,sa],[-sa,ca]])
            arr0 = arrow_length*np.matmul(R,e)
            arr1 = arrow_length*np.matmul(Rt,e)
            # export arrow lines
            line = np.append(p0,p0+arr0)
            line = np.append(line,np.array(self.rparams.dimension_stroke_width))
            lines.append(line)

            line = np.append(p0,p0+arr1)
            line = np.append(line,np.array(self.rparams.dimension_stroke_width))
            lines.append(line)

            line = np.append(p1, p1-arr0)
            line = np.append(line,np.array(self.rparams.dimension_stroke_width))
            lines.append(line)

            line = np.append(p1, p1-arr1)
            line = np.append(line,np.array(self.rparams.dimension_stroke_width))
            lines.append(line)

        return lines




    def export_door_points(self,edge,door):
        a, b = edge.radial_points(door.t, door.width * 0.5)
        unit = edge.unit_vector
        rotated_unit = np.array([-unit[1], unit[0]])
        hinge = a if door.opens_LR == "left" else b
        latch = b if door.opens_LR == "left" else a
        angle_dir = "-" if door.opens_LR == "left" else "+"
        endpoint = hinge + door.width * rotated_unit

        hinge = self.scale_point(hinge)
        latch = self.scale_point(latch)
        endpoint = self.scale_point(endpoint)

        # 1- Export points on the arc
        # The direction vector of the door, from hinge to latch
        xaxis = np.array(endpoint) - np.array(hinge)
        xaxis = xaxis /  np.linalg.norm(xaxis)

        # the rotation matrix to apply to the arc
        R = np.array([[xaxis[0],-xaxis[1]],[xaxis[1],xaxis[0]]])
        points_arc = []
        for angle in np.linspace(0, np.pi/2, num=self.num_door_points):
            pt = np.array([np.cos(angle), np.sin(angle)])
            # pt = self.scale_point(hinge) + door.width * self.rparams.scaling * np.matmul(R,pt)
            pt = hinge + door.width * self.rparams.scaling * np.matmul(R,pt)
            points_arc.append(pt)
        return hinge, latch, endpoint, points_arc

    def export_door_lines(self,edge,door):
        lines = []

        hinge, latch, endpoint, points_arc = self.export_door_points(edge,door)
        for i in np.arange(len(points_arc)-1):
            line = np.append(points_arc[i],points_arc[i+1])
            line = np.append(line,np.array(self.rparams.door_stroke_width_arc))
            lines.append(line)

        # 2- Export line between hinge and latch
        line = np.append(hinge,latch)
        line = np.append(line,np.array(self.rparams.door_stroke_width_hinge_latch))
        lines.append(line)

        # 3- Export line between hinge and endpoint
        line = np.append(hinge,endpoint)
        line = np.append(line,np.array(self.rparams.door_stroke_width_hinge_endpoint))
        lines.append(line)

        return lines

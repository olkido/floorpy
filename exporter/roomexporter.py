import itertools
import numpy as np

from generator.groom import HallwayGroom
from core.opening import Door, DoorFactory
from renderer.svgrenderer import RenderingParams

class LineTypes:
    RoomWall, Door = range(2)

class RoomExporter(object):

    def __init__(self, floorplan, rparams=RenderingParams(), num_door_points = 5):
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
            # self.render_room_fill(room)
            for edge in room.edges:
                positive_groom = edge.positive.groom if edge.positive is not None else None
                negative_groom = edge.negative.groom if edge.negative is not None else None
                if type(positive_groom) is HallwayGroom and type(negative_groom) is HallwayGroom:
                    continue
                p0, p1 = [self.scale_point(p) for p in edge.cartesian_points]
                # todo: append p0, p1, edge linewidth = 12 to edges
                # todo: add doors
                line = np.append(p0,p1)
                line = np.append(line,np.array(self.rparams.room_stroke_width))
                lines.append(line)
                line_labels.append(LineTypes.RoomWall)

                for door in edge.doors:
                    door_lines = self.export_door_lines(edge,door)
                    lines.extend(door_lines)
                    line_labels.extend([LineTypes.Door] * len(door_lines))


        lines = np.array(lines)
        line_labels = np.array(line_labels)
        # todo: add room labels, add room rectangles
        return lines, line_labels

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

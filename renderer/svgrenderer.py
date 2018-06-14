import svgwrite
import itertools
import numpy as np

from generator.groom import HallwayGroom
from core.opening import Door, DoorFactory

class RenderingParams(object):
    def __init__(self,
                 width,
                 height,
                 scaling=16,
                 room_stroke_width=12,
                 door_stroke_width_hinge_latch=12,
                 door_stroke_width_hinge_endpoint=4,
                 door_stroke_width_arc=2,
                 dimension_stroke_width=2,
                 ):
        self.width = width
        self.height = height
        self.scaling = scaling
        self.room_stroke_width = room_stroke_width # room wall stroke width
        self.door_stroke_width_hinge_latch = door_stroke_width_hinge_latch
        self.door_stroke_width_hinge_endpoint = door_stroke_width_hinge_endpoint
        self.door_stroke_width_arc = door_stroke_width_arc
        self.dimension_stroke_width = dimension_stroke_width

from exporter.roomexporter import RoomExporter

class SvgRenderer(object):

    def __init__(self, floorplan, rparams=RenderingParams(100, 60)):
        self.rparams = rparams
        self.floorplan = floorplan
        self.drawing = svgwrite.Drawing('out/output.svg',
                                        size=(rparams.width * rparams.scaling + 64, rparams.height * rparams.scaling + 64)
                                        )
        self.group = svgwrite.container.Group(transform='translate(32,32)')
        self.drawing.add(self.group)
        self.exporter = RoomExporter(floorplan, self.rparams)

    def render(self, filename, show_edge_connections=False):
        print("We are outputting svg to ", filename)
        self.render_connectivity_graph()

        edges = set()
        for room in self.floorplan.rooms:
            self.render_room_fill(room)
            for edge in room.edges:
                positive_groom = edge.positive.groom if edge.positive is not None else None
                negative_groom = edge.negative.groom if edge.negative is not None else None
                if type(positive_groom) is HallwayGroom and type(negative_groom) is HallwayGroom:
                    continue
                edges.add(edge)

        for edge in edges:
            self.render_edge(edge)

        if show_edge_connections:
            self.render_edge_connections()

        for room in self.floorplan.rooms:
            self.render_room_label(room)

        for room in self.floorplan.rooms:
            self.render_dimension_lines(room)

        self.drawing.saveas(filename, pretty=True)


    def render_room_fill(self, room):
        x_max, x_min, y_max, y_min = room.max_min_xy
        self.group.add(
            self.drawing.rect(self.scale_point((x_min, y_min)), self.scale_point((room.width, room.height)), **{
                "fill": "#" + room.groom.fill_color
            })
        )

    def scale_point(self, p):
        return p[0]*self.rparams.scaling, p[1]*self.rparams.scaling

    def denumpy_point(self, p):
        return p[0]*1.0, p[1]*1.0

    def render_edge(self, edge):
        p0, p1 = [self.scale_point(p) for p in edge.cartesian_points]
        self.group.add(self.drawing.line(p0, p1, **{
            "stroke": "#595959",
            "stroke-width": self.rparams.room_stroke_width,
            "stroke-linecap": "round"
        }))
        for door in edge.doors:
            self.render_door(edge, door)
            # debug - plot the door points on the arc
            hinge, latch, endpoint, points_arc = self.exporter.export_door_points(edge,door)
            for point in points_arc:
                self.mark_point(point, color=svgwrite.rgb(255, 255, 0))

        # self.render_door(edge, DoorFactory.interior_door(0.5, -1))

    def render_dimension_lines(self, room):

        dimension_lines = self.exporter.export_dimension_lines(room)
        for line in dimension_lines:
            print('line: {}'.format(line))
            p0 = np.array(line[0:2])
            p1 = np.array(line[2:4])
            print('p0: {}'.format(p0))
            print('p1: {}'.format(p1))
            thickness = line[4]
            self.group.add(self.drawing.line(p0, p1, **{
                                             "stroke": "#595959",
                                             "stroke-width": thickness,
                                             "stroke-linecap": "round"
                                             }))


    def render_room_label(self, room):
        # print(f"I am looking at room {room.groom.label}")
        label = str(room.groom.label).title()
        x, y = self.scale_point(room.center)
        fontsize = 30
        self.group.add(
            self.drawing.text(label, x=[x], y=[y], **{
                "text-anchor": "middle",
                "style": "font-family: 'Source Code Pro'; font-size: {}pt".format(fontsize),
            })
        )


    def render_door(self, edge, door):
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

        self.mark_point(point=hinge,    color=svgwrite.rgb(255, 0, 0))
        self.mark_point(point=latch,    color=svgwrite.rgb(0, 255, 0))
        self.mark_point(point=endpoint, color=svgwrite.rgb(0, 0, 255))

        self.group.add(
            self.drawing.line(hinge, latch, **{
                "stroke": "white",
                "stroke-width": self.rparams.door_stroke_width_hinge_latch
            })
        )
        # # self.mark_point(self.scale_point(hinge), 'yellowgreen', radius=16)
        # self.mark_point(hinge, 'red', radius=8)
        # self.mark_point(latch, 'yellow', radius=8)
        # self.mark_point(endpoint, 'blue')
        # Draw a line from hinge to end_point
        self.group.add(
            self.drawing.line(hinge, endpoint, **{
                "stroke": svgwrite.rgb(0, 0, 0),
                "stroke-width": self.rparams.door_stroke_width_hinge_endpoint,
            })
        )

        path = self.drawing.path(**{
            "fill": "none",
            "stroke": "black",
            "stroke-width": self.rparams.door_stroke_width_arc,
        })
        path.push("M{} {}".format(latch[0],latch[1]))
        path.push_arc(endpoint, -1, door.width * self.rparams.scaling, large_arc=False, angle_dir=angle_dir, absolute=True)
        self.group.add(path)




    def mark_point(self, point, color, radius=16):
        self.group.add(
            self.drawing.circle(point, r=radius, stroke=color, fill=color, stroke_width=1)
        )

    def render_connectivity_graph(self,):
        for i, room in enumerate(self.floorplan.rooms):
            for e in room.edges:
                for door in e.doors:
                    self.group.add(
                        self.drawing.line(
                            self.scale_point(room.center),
                            self.scale_point(e.center),
                            **{
                                "stroke": svgwrite.rgb(0, 255, 0),
                                "stroke-width": 4
                            }
                        )
                    )




    # @staticmethod
    # def render_plan(floorplan, connectivity_graph=False):
    #     drawing = svgwrite.Drawing('out/output.svg')
    #     group = svgwrite.container.Group(transform='translate(32,32), scale(3)')
    #     drawing.add(group)

    #     edges = set()
    #     for room in floorplan.rooms:
    #         for edge in room.edges:
    #             edges.add(edge)

    #     for edge in edges:
    #         SvgRenderer.render_edge(edge,drawing, group)

    #     if connectivity_graph:
    #         SvgRenderer.render_connectivity_graph(floorplan.rooms, drawing, group)

    #     SvgRenderer.render_labels(floorplan.rooms, drawing, group)

    #     drawing.save()

    # @staticmethod
    # def render_edge(edge, drawing, group):
    #     p0, p1 = edge.cartesian_points
    #     group.add(drawing.line(p0, p1, stroke=svgwrite.rgb(0, 0, 0)))




    # @staticmethod
    # def render_labels(rooms, drawing, group):
    #     for room in rooms:
    #         x, y = room.center
    #         group.add(
    #             drawing.text(room.label, x=[x], y=[y], **{
    #                 "text-anchor": "middle"
    #             })
    #         )

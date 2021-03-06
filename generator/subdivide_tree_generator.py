from generator.node import Node
from generator.groom import *
from bakedrandom import brandom as random
from core.edge import Orientation
from core.floorplan import FloorPlan
from core.room import RoomFactory, InvalidSubdivisionException


class SubdivideTreeToFloorplan(object):

    def __init__(self, lot_width, lot_height, list_o_rooms, weights):
        self.lot_width = lot_width
        self.lot_height = lot_height
        self.list_o_rooms = list_o_rooms
        self.weights = weights

    def generate_candidate_floorplan(self, rootnode):
        floorplan = FloorPlan([RoomFactory.Rectangle(self.lot_width, self.lot_height)])
        initial_room = floorplan.rooms[0]
        self.subdivide_room(floorplan, initial_room, rootnode)
        return floorplan

    def subdivide_room(self, floorplan, room, node):

        if len(node.children) <= 1:
            groom = self.list_o_rooms[node.room_indexes[0]]
            room.groom = groom
            node.score = groom.tree_score(room, self.weights)
            return
            # return node.score

        children = node.children[::node.order]

        a1 = sum([ self.list_o_rooms[i].area for i in children[0].room_indexes])
        a2 = sum([ self.list_o_rooms[i].area for i in children[1].room_indexes])

        S = (a1 * (1 - node.t)) / (a1 * (1 - node.t) + a2 * node.t)

        # node.orientation = room.orientation.negate()
        hallway = node.padding and min(room.width, room.height) >= 21
        if hallway:
            rooms = floorplan.proportional_subdivide(S, node.orientation, room, hallway=hallway)
            roomA, roomB = rooms[0], rooms[1]
            if len(rooms) > 2:
                roomHall = rooms[2]
                roomHall.groom = HallwayGroom()
        else:
            try:
                roomA, roomB = floorplan.proportional_subdivide(S, node.orientation, room, hallway=hallway)
            except InvalidSubdivisionException as e:
                room.groom = JiltedGroom()
                node.score = 0.0
                return

        self.subdivide_room(floorplan, roomA, children[0])
        self.subdivide_room(floorplan, roomB, children[1])
        # node.score = (scoreA + scoreB) * 0.5
        # return node.score


class SubdivideTreeGenerator(object):

    def generate_tree_from_indexes(self, indexes):
        rootnode = Node(
            orientation=random.choice([Orientation.Horizontal, Orientation.Vertical]),
            children=[],
            padding=random.choice([True, False]),
            order=random.choice([-1, 1]),
            t=0.5,
            room_indexes=list(indexes),
            score=None
        )
        self.generate_tree(rootnode)


        import json

        return rootnode

    def generate_tree(self, rootnode):
        if len(rootnode.room_indexes) <= 1:
            return

        # total_area = sum(areas)
        left, right = self.partition_list(rootnode.room_indexes)
        left_child = Node(
            orientation=random.choice([Orientation.Horizontal, Orientation.Vertical]),
            children=[],
            padding=random.choice([True, False]),
            order=random.choice([-1, 1]),
            t=0.5,
            room_indexes=left,
            score=None
        )
        right_child = Node(
            orientation=random.choice([Orientation.Horizontal, Orientation.Vertical]),
            children=[],
            padding=random.choice([True, False]),
            order=random.choice([-1, 1]),
            t=0.5,
            room_indexes=right,
            score=None
        )
        rootnode.children.extend([left_child, right_child])
        self.generate_tree(left_child)
        self.generate_tree(right_child)

    def partition_list(self, ls):
        ls = list(ls)
        random.shuffle(ls)

        midpoint = len(ls) // 2
        return ls[:midpoint], ls[midpoint:]

        # slice_index = random.randint(1, len(ls) - 1)
        # return ls[:slice_index], ls[slice_index:]




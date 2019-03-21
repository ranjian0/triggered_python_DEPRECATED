#  Copyright 2019 Ian Karanja <karanjaichungwa@gmail.com
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import pymunk as pm
import itertools as it
from pymunk import pyglet_util as putils

PHYSICS_STEPS = 60
RAYCAST_FILTER = 0x1
RAYCAST_MASK = pm.ShapeFilter(mask=pm.ShapeFilter.ALL_MASKS ^ RAYCAST_FILTER)

class PhysicsWorld:

    # -- singleton
    instance = None
    def __new__(cls):
        if PhysicsWorld.instance is None:
            PhysicsWorld.instance = object.__new__(cls)
        return PhysicsWorld.instance

    def __init__(self):
        self.space = pm.Space()

        self.collision_layers = []
        self.collision_masks = []

    def add(self, *args):
        self.space.add(*args)

    def remove(self, *args):
        self.space.remove(*args)

    def clear(self):
        self.remove(self.space.static_body.shapes)
        for body in self.space.bodies:
            self.remove(body, body.shapes)

    def update(self, dt):
        for _ in it.repeat(None, PHYSICS_STEPS):
            self.space.step(1. / PHYSICS_STEPS)

    def raycast(self, start, end):
        res = self.space.segment_query_first(start, end, 1, RAYCAST_MASK)
        return res

    def add_collision_handler(self, type_a, type_b,
        handler_begin=None, handler_pre=None, handler_post=None,
        handler_separate=None, data=None):

        handler = self.space.add_collision_handler(type_a, type_b)
        if data:
            handler.data.update(data)

        if handler_begin:
            handler.begin = handler_begin
        if handler_pre:
            handler.pre_solve = handler_pre
        if handler_post:
            handler.post_solve = handler_post
        if handler_separate:
            handler.separate = handler_separate

    def debug_draw(self):
        options = putils.DrawOptions()
        self.space.debug_draw(options)

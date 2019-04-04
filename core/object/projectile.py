import math
import pymunk as pm
import pyglet as pg
from resources import Resources
from core.math import Vec2
from core.physics import PhysicsWorld, PhysicsBody
from core.utils import (
    image_set_size,
    image_set_anchor_center)

class Projectile:
    SIZE = (15, 15)
    SPEED = 300

    def __init__(self, position, direction, batch):
        self.batch = batch
        self.direction = direction

        # -- sprite
        self.image = Resources.instance.sprite("bullet")
        image_set_size(self.image, *self.SIZE)
        image_set_anchor_center(self.image)
        self.sprite = pg.sprite.Sprite(self.image,
            *position, batch=self.batch)

        # -- physics
        physics = PhysicsWorld.instance
        self.body = PhysicsBody(1, pm.moment_for_box(1, self.SIZE))
        self.shape = pm.Poly.create_box(self.body, self.SIZE, radius=.6)

        self.body.position = position
        physics.add(self.body, self.shape)
        physics.register_collision(self.shape.collision_type,
            self.on_collision_enter, lambda other: None)

    def on_collision_enter(self, other):
        #XXX Unwanted Behaviour: called for sensors shapes
        for shape in other.shapes:
            if shape.sensor: continue

            res = shape.shapes_collide(self.shape)
            if res.points:
                self.destroy()

    def on_update(self, dt):
        self.body.velocity = self.direction * self.SPEED * dt
        self.body.angle = self.direction.angle
        if self.sprite.image:
            # pyglet rotates clockwise (pymunk anti-clockwise)
            self.sprite.update(*self.body.position, -math.degrees(self.direction.angle))

    def destroy(self):
        PhysicsWorld.remove(self.body, self.shape)
        self.sprite.delete()
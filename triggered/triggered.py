import os
import sys
import math
import heapq
import random
import pprint as pp
import pyglet as pg
import pymunk as pm
import itertools as it

from enum import Enum
from pyglet.gl import *
from pyglet.window import key
from pymunk import pyglet_util as putils
from collections import defaultdict, namedtuple

FPS        = 60
DEBUG      = 0
SIZE       = (800, 600)
CAPTION    = "Triggered"
BACKGROUND = (100, 100, 100)

KEYS = key.KeyStateHandler()
KEYMAP = {
    key.W : (0, 1),
    key.S : (0, -1),
    key.A : (-1, 0),
    key.D : (1, 0)
}

COLLISION_MAP = {
    "PlayerType" : 1,
    "EnemyType"  : 2,
    "WallType"   : 3,
}


class EventType(Enum):
    KEY_DOWN = 1
    KEY_UP   = 2
    MOUSE_DOWN = 3
    MOUSE_UP   = 4
    MOUSE_MOTION = 5
    RESIZE = 6

Resource = namedtuple("Resource", "name data")

'''
============================================================
---   CLASSES
============================================================
'''

class Game:

    def __init__(self, win, res, physics):
        self.window = win
        self.resource = res
        self.physics = physics

        self.level = Level("Level One", self.resource.level("test"))

    def draw(self):
        self.level.draw()
        if DEBUG:
            self.physics.debug_draw()

    def event(self, *args, **kwargs):
        self.level.event(*args, **kwargs)

    def update(self, dt):
        self.physics.update()
        self.level.update(dt)

class Resources:

    # -- singleton
    instance = None
    def __new__(cls):
        if Resources.instance is None:
            Resources.instance = object.__new__(cls)
        return Resources.instance

    def __init__(self, root_dir="res"):
        self.root = root_dir
        pg.resource.path = [
            os.path.join(os.path.dirname(os.path.realpath(__file__)), self.root)
        ]
        pg.resource.reindex()

        abspath = os.path.abspath
        self._sprites = abspath(os.path.join(root_dir, "sprites"))
        self._sounds  = abspath(os.path.join(root_dir, "sounds"))
        self._levels  = abspath(os.path.join(root_dir, "levels"))

        self._data = defaultdict(list)
        self._load()

    def sprite(self, name):
        for res in self._data['sprites']:
            if res.name == name:
                return res.data
        return None

    def sound(self, name):
        for res in self._data['sounds']:
            if res.name == name:
                return res.data
        return None

    def level(self, name):
        for res in self._data['levels']:
            if res.name == name:
                return self._parse_level(res.data)
        return None

    def _load(self):

        # -- load sprites
        for sprite in os.listdir(self._sprites):
            img = pg.resource.image('sprites/' + sprite)
            fn = os.path.basename(sprite.split('.')[0])
            self._data['sprites'].append(Resource(fn,img))

        # -- load sounds
        for sound in os.listdir(self._sounds):
            snd = pg.resource.media('sounds/' + sound)
            fn = os.path.basename(sound.split('.')[0])
            self._data['sounds'].append(Resource(fn,snd))

        # -- load levels
        for level in os.listdir(self._levels):
            lvl = pg.resource.file('levels/' + level, 'r')
            fn = os.path.basename(level.split('.')[0])
            self._data['levels'].append(Resource(fn,lvl))

    def _parse_level(self, file):
        result = []
        for line in file.readlines():
            result.append(list(line.strip()))
        return result

class Player:

    def __init__(self, position, size, image):
        # -- properties
        self.pos    = position
        self.size   = size
        self.health = 100
        self.damage = 10
        self.angle  = 0
        self.speed  = 100

        self.ammo   = 50

        # Create Player Image
        self.image = image
        self.image.width = size[0]
        self.image.height = size[1]
        self.image.anchor_x = size[0]/2
        self.image.anchor_y = size[1]/2
        self.sprite = pg.sprite.Sprite(self.image, x=position[0], y=position[1])

        # player physics
        self.body = pm.Body(1, 100)
        self.body.position = self.pos
        self.shape = pm.Circle(self.body, size[0]/2)
        self.shape.collision_type = COLLISION_MAP.get("PlayerType")
        Physics.instance.add(self.body, self.shape)

        # -- weird bug - have to push twice
        window.push_handlers(KEYS)
        window.push_handlers(KEYS)

    def offset(self):
        px, py = self.pos
        w, h = window.get_size()
        return -px + w/2, -py + h/2

    def draw(self):
        self.sprite.draw()

    def event(self, type, *args, **kwargs):
        if type == EventType.MOUSE_MOTION:
            x, y, dx, dy = args
            ox, oy = self.offset()

            mx, my = x - ox, y - oy     # - mouse position with screen offset
            px, py = self.pos           # - player position
            self.angle = math.degrees(-math.atan2(my - py, mx - px))

        elif type == EventType.MOUSE_UP:
            pass

    def update(self, dt):
        self.sprite.update(rotation=self.angle)

        # -- movements
        dx, dy = 0, 0
        for _key, _dir in KEYMAP.items():
            if KEYS[_key]:
                dx, dy = _dir

        # -- running
        speed = self.speed
        if KEYS[key.RSHIFT] or KEYS[key.LSHIFT]:
            speed *= 2.5

        bx, by = self.body.position
        bx += dx * dt * speed
        by += dy * dt * speed
        self.body.position = (bx, by)

        self.sprite.position = (bx, by)
        self.pos = (bx, by)

class EnemyState(Enum):
    IDLE    = 0
    PATROL  = 1
    CHASE   = 2
    ATTACK  = 3

class Enemy:

    def __init__(self, position, size, image, waypoints):
        # -- properties
        self.pos    = position
        self.size   = size
        self.health = 100
        self.damage = 10
        self.angle  = 0
        self.speed  = 100

        self.ammo   = 50

        # -- patrol properties
        self.state = EnemyState.IDLE

        self.waypoints = it.cycle(waypoints)
        self.target = next(self.waypoints)
        self.patrol_eps = 10
        self.chase_radius = 300
        self.attack_radius = 100
        self.attack_frequency = 50
        self.current_attack = 0

        # Create enemy Image
        self.image = image
        self.image.width = size[0]
        self.image.height = size[1]
        self.image.anchor_x = size[0]/2
        self.image.anchor_y = size[1]/2
        self.sprite = pg.sprite.Sprite(self.image, x=position[0], y=position[1])

        # player physics
        self.body = pm.Body(1, 100)
        self.body.position = self.pos
        self.shape = pm.Circle(self.body, size[0]/2)
        self.shape.collision_type = COLLISION_MAP.get("EnemyType")
        Physics.instance.add(self.body, self.shape)

        self.map = None
        self.player_target = None

    def watch(self, player):
        self.player_target = player

    def set_map(self, _map):
        self.map = _map

    def look_at(self, target):
        tx, ty = target
        px, py = self.pos
        angle = math.degrees(-math.atan2(ty - py, tx - px))
        self.sprite.update(rotation=self.angle)

    def draw(self):
        self.sprite.draw()

    def update(self, dt):
        player = self.player_target
        player_distance = distance_sqr(player.pos, self.pos)
        #print(self.pos, self.target)

        if player_distance < self.chase_radius**2:
            self.state = EnemyState.CHASE
        else:
            self.state = EnemyState.PATROL

        if player_distance < self.attack_radius**2:
            self.state = EnemyState.ATTACK

        if self.state == EnemyState.IDLE:
            self.state = EnemyState.PATROL
        elif self.state == EnemyState.PATROL:
            self.patrol(dt)
        elif self.state == EnemyState.CHASE:
            self.chase(player.pos, dt)
        elif self.state == EnemyState.ATTACK:
            self.attack(player.pos)

    def chase(self, target, dt):
        self.look_at(target)
        self.move_to_target(target, dt)

    def patrol(self, dt):
        distance = distance_sqr(self.pos, self.target)
        print(distance)
        if distance < self.patrol_eps:
            self.target = next(self.waypoints)

        self.look_at(self.target)
        self.move_to_target(self.target, dt)

    def attack(self, player):
        self.look_at(player)
        self.current_attack += 1
        pass

        # if self.current_attack == self.attack_frequency:
        #     vec = normalize()
        #     vec = vec2(player[0] - self.rect.centerx, player[1] - self.rect.centery).normalize()
        #     gun_pos = vec2(self.rect.center) + (vec * vec2(self.turret.center).length()/2)
        #     self.bullets.add(Bullet(gun_pos, self.angle))

        #     self.current_attack = 0

    def move_to_target(self, target, dt):
        diff = self.target[0] - self.pos[0], self.target[1] - self.pos[1]
        if distance_sqr((0, 0), diff):
            dx, dy = normalize(diff)

            bx, by = self.body.position
            bx += dx * self.speed * dt
            by += dy * self.speed * dt
            self.body.position = (bx, by)

            self.sprite.position = (bx, by)
            self.pos = (bx, by)


class Physics:

    # -- singleton
    instance = None
    def __new__(cls):
        if Physics.instance is None:
            Physics.instance = object.__new__(cls)
        return Physics.instance


    def __init__(self, steps=50):
        self.space = pm.Space()
        self.steps = steps

        setup_collisions(self.space)

    def add(self, *args):
        self.space.add(*args)

    def remove(self, *args):
        self.space.remove(*args)

    def update(self):
        for _ in it.repeat(None, self.steps):
            self.space.step(0.1 / self.steps)

    def debug_draw(self):
        options = putils.DrawOptions()
        self.space.debug_draw(options)


class Map:

    def __init__(self, data,
                    wall_img  = None,
                    node_size = 200,
                    physics   = None):

        self.data       = data
        self.node_size  = node_size
        self.wall_img   = Resources.instance.sprite("wall_image")
        self.wall_img.width = node_size//2
        self.wall_img.height = node_size//2
        # self.physics    = physics

        self.sprites    = []
        self.batch      = pg.graphics.Batch()
        self.make_map()

        self.pathfinder = PathFinder(data, node_size)
        self.spawn_data = self.parse_spawn_points()

    def make_map(self):
        nsx, nsy = (self.node_size,)*2
        sx = (len(self.data[0]) * nsx) - nsx/2
        sy = (len(self.data) * nsy) - nsy/2

        # physics options
        wsx, wsy = (nsx//2, nsy//2)

        for y, row in enumerate(self.data):
            for x, data in enumerate(row):
                if data == "#":
                    offx, offy = x * nsx, y * nsy
                    sp = pg.sprite.Sprite(self.wall_img, x=offx, y=offy, batch=self.batch)
                    self.sprites.append(sp)
                    add_wall((offx + wsx/2, offy + wsy/2), (wsx, wsy))

                    # Fill gaps
                    # -- gaps along x-axis
                    if x < len(row) - 1 and self.data[y][x + 1] == "#":
                        sp = pg.sprite.Sprite(self.wall_img, x=offx + nsx/2, y=offy, batch=self.batch)
                        self.sprites.append(sp)
                        add_wall((offx + wsx/2 + nsx/2, offy + wsy/2), (wsx, wsy))


                    # -- gaps along y-axis
                    if y < len(self.data) - 1 and self.data[y + 1][x] == "#":
                        sp = pg.sprite.Sprite(self.wall_img, x=offx, y=offy + nsy/2, batch=self.batch)
                        self.sprites.append(sp)
                        add_wall((offx + wsx/2, offy + wsy/2 + nsy/2), (wsx, wsy))

    def parse_spawn_points(self):
        spawn_data = {
            'player_position' : None,   # identifier == 'p'
            'enemy_position'  : [],     # identifier == 'e'
            'mino_position'   : None,   # identifier == 'm'
            'vip_position'    : None,   # identifier == 'v'
            'time_stone'      : None,   # identifier == 't'

            'patrol_positions': [],     # anything but '#', used for enemy patrol
        }

        nsx, nsy = (self.node_size,)*2
        for y, row in enumerate(self.data):
            for x, data in enumerate(row):
                location = (x*nsx, y*nsy)

                if   data == "p":
                    spawn_data['player_position'] = location
                elif data == 'e':
                    spawn_data['enemy_position'].append(location)
                elif data == 'm':
                    spawn_data['mino_position'] = location
                elif data == 'v':
                    spawn_data['vip_position'] = location
                elif data == 't':
                    spawn_data['time_stone'] = location

                if data != '#':
                    spawn_data['patrol_positions'].append(location)
        return spawn_data

    def clamp_player(self, player):
        # -- keep player within map bounds
        ns = self.node_size

        offx, offy = player.offset()
        winw, winh = window.get_size()
        msx, msy = (ns * len(self.data[0]))-ns//2, (ns * len(self.data))-ns//2

        clamp_X = msx - winw
        clamp_Y = msy - winh

        offx = 0 if offx > 0 else offx
        offx = -clamp_X if offx < -clamp_X else offx
        offy = 0 if offy > 0 else offy
        offy = -clamp_Y if offy < -clamp_Y else offy

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(offx, offy, 0)

    def draw(self):
        self.batch.draw()

    def update(self, dt):
        pass

    def __getitem__(self, val):
        return self.spawn_data.get(val, None)

class PathFinder:

    def __init__(self, map_data, node_size):
        self.data = map_data
        self.node_size = (node_size,)*2

    def calculate_path(self, p1, p2):
        cf, cost = a_star_search(self, p1, p2)
        return reconstruct_path(cf, p1, p2)

    def calc_patrol_path(self, points):
        result = []
        circular_points = points + [points[0]]
        for i in range(len(circular_points)-2):
            f, s = circular_points[i:i+2]
            path = self.calculate_path(f, s)[1:]
            result.extend(path)
        return result

    def neighbours(self, p):
        add = lambda p1, p2 : (p1[0]+p2[0], p1[1]+p2[1])
        mul = lambda p1, p2 : (p1[0]*p2[0], p1[1]*p2[1])

        # -- find all walkable nodes
        walkable = [mul((x, y), self.node_size) for y, data in enumerate(self.data)
            for x, d in enumerate(data) if d != '#']

        # -- find neighbours that are walkable
        directions      = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        neigh_positions = [add(p, mul(d, self.node_size)) for d in directions]
        return [n for n in neigh_positions if n in walkable]

    def cost(self, *ignored):
        return 1

class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]


class Level:

    def __init__(self, name, data):
        self.name = name
        self.data = data

        self.map = None
        self.agents = []
        self.reload()

    def reload(self):
        self.agents.clear()
        self.map = Map(self.data, physics=Physics.instance)

        # -- add player to map position
        player = Player(self.map['player_position'], (50, 50), Resources.instance.sprite("hitman1_gun"))
        self.agents.append(player)

        # -- add other agents map positions
        for point in self.map['enemy_position']:
            patrol_point = random.choice(self.map['patrol_positions'])

            patrol = self.map.pathfinder.calc_patrol_path([point, patrol_point])
            e = Enemy(point, (50, 50), Resources.instance.sprite("robot1_gun"), patrol)
            e.watch(player)
            self.agents.append(e)

    def get_player(self):
        for ag in self.agents:
            if isinstance(ag, Player):
                return ag
        return None

    def draw(self):
        self.map.draw()
        for agent in self.agents:
            agent.draw()

    def update(self, dt):
        self.map.clamp_player(self.get_player())
        for agent in self.agents:
            agent.update(dt)

    def event(self, *args, **kwargs):
        for agent in self.agents:
            if hasattr(agent, 'event'):
                agent.event(*args, **kwargs)


'''
============================================================
---   FUNCTIONS
============================================================
'''

def normalize(p):
    mag = math.sqrt(distance_sqr((0, 0), p))
    if mag:
        x = p[0] / mag
        y = p[1] / mag
        return (x, y)
    return p

def distance_sqr(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return dx**2 + dy**2

def add_wall(pos, size):
    space = Physics.instance.space

    shape = pm.Poly.create_box(space.static_body, size=size)
    shape.body.position = pos
    space.add(shape)

def heuristic(a, b):
    (x1, y1) = a
    (x2, y2) = b
    return abs(x1 - x2) + abs(y1 - y2)

def a_star_search(graph, start, goal):
    frontier = PriorityQueue()
    frontier.put(start, 0)
    came_from = {}
    cost_so_far = {}
    came_from[start] = None
    cost_so_far[start] = 0

    while not frontier.empty():
        current = frontier.get()

        if current == goal:
            break

        for next in graph.neighbours(current):
            new_cost = cost_so_far[current] + graph.cost(current, next)
            if next not in cost_so_far or new_cost < cost_so_far[next]:
                cost_so_far[next] = new_cost
                priority = new_cost + heuristic(goal, next)
                frontier.put(next, priority)
                came_from[next] = current

    return came_from, cost_so_far

def reconstruct_path(came_from, start, goal):
    current = goal
    path = [current]
    while current != start:
        current = came_from[current]
        path.append(current)
    path.append(start)
    path.reverse()
    return path

def setup_collisions(space):

    # Player-Enemy Collision
    def player_enemy_solve(arbiter, space, data):
        """ Keep the two bodies from intersecting"""
        pshape = arbiter.shapes[0]
        eshape  = arbiter.shapes[1]

        normal = pshape.body.position - eshape.body.position
        normal = normal.normalized()
        pshape.body.position = eshape.body.position + (normal * (pshape.radius*2))
        return True

    handler = space.add_collision_handler(
            COLLISION_MAP.get("PlayerType"),
            COLLISION_MAP.get("EnemyType")
        )
    handler.begin = player_enemy_solve

    # Enemy-Enemy Collision
    def enemy_enemy_solve(arbiter, space, data):
        """ Keep the two bodies from intersecting"""
        eshape  = arbiter.shapes[0]
        eshape1 = arbiter.shapes[1]

        normal = eshape.body.position - eshape1.body.position
        normal = normal.normalized()
        eshape.body.position = eshape1.body.position + (normal * (eshape.radius*2))
        return True

    handler = space.add_collision_handler(
            COLLISION_MAP.get("EnemyType"),
            COLLISION_MAP.get("EnemyType")
        )
    handler.begin = enemy_enemy_solve


'''
============================================================
---   MAIN
============================================================
'''

# -- create window
window = pg.window.Window(*SIZE, resizable=True)
window.set_minimum_size(*SIZE)
window.set_caption(CAPTION)

res  = Resources()
phy  = Physics()
game = Game(window, res, phy)

@window.event
def on_draw():
    window.clear()
    glClearColor(.39, .39, .39, 1)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    game.draw()

@window.event
def on_resize(w, h):
    pass

@window.event
def on_key_press(key, modifiers):
    game.event(EventType.KEY_DOWN, key, modifiers)

@window.event
def on_key_release(key, modifiers):
    game.event(EventType.KEY_UP, key, modifiers)

@window.event
def on_mouse_press(x, y, button, modifiers):
    game.event(EventType.MOUSE_DOWN, x, y, button, modifiers)

@window.event
def on_mouse_release(x, y, button, modifiers):
    game.event(EventType.MOUSE_UP, x, y, button, modifiers)

@window.event
def on_mouse_motion(x, y, dx, dy):
    game.event(EventType.MOUSE_MOTION, x, y, dx, dy)

def on_update(dt):
    game.update(dt)

if __name__ == '__main__':
    pg.clock.schedule_interval(on_update, 1/FPS)
    pg.app.run()

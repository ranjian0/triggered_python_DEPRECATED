import random
from map import Map
from gui import Timer
from entities import Player, Enemy, COLLISION_MAP
from pygame.math   import Vector2 as vec2

class Level:
    NAME    = "Level"
    MAP     = None
    PLAYER  = None
    ENEMIES = []
    TIMER   = None
    COLLECTIBLES = []

    def __init__(self, physics_space=None):
        self.space = physics_space
        setup_collisions(self.space)

        self.MAP.add(self.PLAYER)
        for en in self.ENEMIES:
            self.MAP.add(en)

        for col in self.COLLECTIBLES:
            self.MAP.add(col)

    def get_player(self):
        return self.PLAYER

    def get_map(self):
        return self.MAP

    def draw(self, surface):
        self.MAP.draw(surface)
        self.TIMER.draw(surface)

    def update(self, dt):
        self.MAP.update(dt)
        self.TIMER.update(dt)

    def event(self, ev):
        self.MAP.event(ev)

class LevelManager:

    # # -- singleton
    # _instance = None
    # def __new__(cls):
    #     if LevelManager._instance is None:
    #         LevelManager._instance = object.__new__(cls)
    #     return LevelManager.__instance

    def __init__(self, levels):
        self.levels  = levels
        self.current = 0

        self.completed = False

    def get_current(self):
        return self.levels[self.current]

    def next(self):
        self.completed = self.current < len(self.levels) - 1
        if not self.completed:
            self.current += 1

class LevelOne(Level):
    NAME    = "Kill Them All"

    def __init__(self, space):

        self.MAP     = Map(
        [['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#'],
         ['#', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', '#'],
         ['#', ' ', '#', '#', '#', '#', '#', ' ', '#', ' ', '#'],
         ['#', ' ', ' ', ' ', ' ', ' ', '#', ' ', '#', ' ', '#'],
         ['#', ' ', '#', '#', '#', '#', '#', 'e', '#', 'e', '#'],
         ['#', 'e', '#', ' ', ' ', ' ', ' ', ' ', '#', ' ', '#'],
         ['#', ' ', '#', 'e', '#', '#', '#', '#', '#', ' ', '#'],
         ['#', ' ', '#', ' ', ' ', ' ', ' ', ' ', '#', ' ', '#'],
         ['#', ' ', '#', '#', '#', '#', '#', '#', '#', ' ', '#'],
         ['#', 'p', ' ', 'e', ' ', ' ', ' ', ' ', ' ', ' ', '#'],
         ['#', '#', '#', '#', '#', '#', '#', '#', '#', '#', '#']],
         space = space)

        self.TIMER    = Timer((150, 30), (80, 20), 500,
            on_complete=lambda : LevelManager.instance.get_current().check_complete())

        data = self.MAP.spawn_data
        self.PLAYER   = Player(data.get('player_position'), (50, 50), space)
        self.ENEMIES  = []
        for point in data['enemy_position']:
            patrol_points = random.sample(data['patrol_positions'],
                random.randint(2, len(data['patrol_positions'])//2))

            patrol = self.MAP.pathfinder.calc_patrol_path([point] + patrol_points)
            e = Enemy(point, (50, 50), patrol, space)
            e.watch_player(self.PLAYER)
            self.ENEMIES.append(e)

        Level.__init__(self, space)


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
        perp   = vec2(normal.y, -normal.x)

        if normal.x:
            _dir = 1 if normal.x > 0 else -1
        else:
            _dir = 1 if normal.y > 0 else -1

        eshape.body.position = eshape.body.position + ((_dir*perp) * (eshape.radius/2))
        return True

    handler = space.add_collision_handler(
            COLLISION_MAP.get("EnemyType"),
            COLLISION_MAP.get("EnemyType")
        )
    handler.begin = enemy_enemy_solve

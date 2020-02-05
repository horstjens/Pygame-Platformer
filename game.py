"""Showcase of a very basic 2d platformer

The red girl sprite is taken from Sithjester's RMXP Resources:
http://untamed.wild-refuge.net/rmxpresources.php?characters

.. note:: The code of this example is a bit messy. If you adapt this to your 
    own code you might want to structure it a bit differently.
"""

__docformat__ = "reStructuredText"

import sys,math

import pygame
#from pygame.locals import *
#from pygame.color import *
import os
import pymunk
#from pymunk.vec2d import Vec2d
import pymunk.pygame_util 

def cpfclamp(f, min_, max_):
    """Clamp f between min and max"""
    return min(max(f, min_), max_)

def cpflerpconst(f1, f2, d):
    """Linearly interpolate from f1 to f2 by no more than d."""
    return f1 + cpfclamp(f2 - f1, -d, d)

def write(background, text, x=50, y=150, color=(0, 0, 0),
          font_size=None, font_name="mono", bold=True, origin="topleft"):
    """blit text on a given pygame surface (given as 'background')
       the origin is the alignment of the text surface
       origin can be 'center', 'centercenter', 'topleft', 'topcenter', 'topright', 'centerleft', 'centerright',
       'bottomleft', 'bottomcenter', 'bottomright'
    """
    if font_size is None:
        font_size = 24
    font = pygame.font.SysFont(font_name, font_size, bold)
    width, height = font.size(text)
    surface = font.render(text, True, color)

    if origin == "center" or origin == "centercenter":
        background.blit(surface, (x - width // 2, y - height // 2))
    elif origin == "topleft":
        background.blit(surface, (x, y))
    elif origin == "topcenter":
        background.blit(surface, (x - width // 2, y))
    elif origin == "topright":
        background.blit(surface, (x - width , y))
    elif origin == "centerleft":
        background.blit(surface, (x, y - height // 2))
    elif origin == "centerright":
        background.blit(surface, (x - width , y - height // 2))
    elif origin == "bottomleft":
        background.blit(surface, (x , y - height ))
    elif origin == "bottomcenter":
        background.blit(surface, (x - width // 2, y ))
    elif origin == "bottomright":
        background.blit(surface, (x - width, y - height))


class Viewer():

    width = 0
    height = 0

    def __init__(self, width=690, height=400, fps=60):
        Viewer.width = width    # can be accesses from outside Viewer class
        Viewer.height = height
        self.fps = fps
        self.dt =  1./fps
        self.PLAYER_VELOCITY = 100. *2.
        self.PLAYER_GROUND_ACCEL_TIME = 0.05
        self.PLAYER_GROUND_ACCEL = (self.PLAYER_VELOCITY/self.PLAYER_GROUND_ACCEL_TIME)
        self.PLAYER_AIR_ACCEL_TIME = 0.25
        self.PLAYER_AIR_ACCEL = (self.PLAYER_VELOCITY/self.PLAYER_AIR_ACCEL_TIME)
        self.JUMP_HEIGHT = 16.*3
        self.JUMP_BOOST_HEIGHT = 24.
        self.JUMP_CUTOFF_VELOCITY = 100
        self.FALL_VELOCITY = 250.
        self.JUMP_LENIENCY = 0.05
        self.HEAD_FRICTION = 0.7
        self.PLATFORM_SPEED = 1
        # ------------------- init -----
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 16)
        self.sound = pygame.mixer.Sound(os.path.join("data", "sfx.wav"))
        self.img = pygame.image.load(os.path.join("data", "xmasgirl1.png"))

        ### Physics stuff
        Viewer.space = pymunk.Space()
        self.space.gravity = 0, -1000
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)

        self.create_walls()

        # moving platform
        self.platform_path = [(650, 100), (600, 200), (650, 300)]
        self.platform_path_index = 0
        self.platform_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.platform_body.position = 650, 100
        s = pymunk.Segment(self.platform_body, (-25, 0), (25, 0), 5)
        s.friction = 1.
        s.group = 1
        s.color = pygame.color.THECOLORS["blue"]
        self.space.add(s)

        # pass through platform
        passthrough = pymunk.Segment(self.space.static_body, (270, 100), (320, 100), 5)
        passthrough.color = pygame.color.THECOLORS["yellow"]
        passthrough.friction = 1.
        passthrough.collision_type = 2
        passthrough.filter = pymunk.ShapeFilter(categories=0b1000)
        self.space.add(passthrough)

        def passthrough_handler(arbiter, space, data):
            if arbiter.shapes[0].body.velocity.y < 0:
                return True
            else:
                return False

        self.space.add_collision_handler(1, 2).begin = passthrough_handler

        # player
        self.body = pymunk.Body(5, pymunk.inf)
        self.body.position = 100, 100

        self.head = pymunk.Circle(self.body, 10, (0, 5))
        self.head2 = pymunk.Circle(self.body, 10, (0, 13))
        self.feet = pymunk.Circle(self.body, 10, (0, -5))
        # Since we use the debug draw we need to hide these circles. To make it
        # easy we just set their color to black.
        self.feet.color = 0, 0, 0, 0
        self.head.color = 0, 0, 0, 0
        self.head2.color = 0, 0, 0, 0
        mask = pymunk.ShapeFilter.ALL_MASKS ^ passthrough.filter.categories
        sf = pymunk.ShapeFilter(mask=mask)
        self.head.filter = sf
        self.head2.filter = sf
        self.feet.collision_type = 1
        self.feet.ignore_draw = self.head.ignore_draw = self.head2.ignore_draw = True

        self.space.add(self.body, self.head, self.feet, self.head2)

        # --------- start the mainloop -----
        self.run()

    def create_walls(self):
        # Pymunk has y coordinates from low to high (upwards)
        # Pygame has y coordinates from high to low (downwards)

        # box walls
        static = [pymunk.Segment(self.space.static_body, (10, 50), (300, 50), 3)
            , pymunk.Segment(self.space.static_body, (300, 50), (325, 50), 3)
            , pymunk.Segment(self.space.static_body, (325, 50), (350, 50), 3)
            , pymunk.Segment(self.space.static_body, (350, 50), (375, 50), 3)
            , pymunk.Segment(self.space.static_body, (375, 50), (680, 50), 3)
            , pymunk.Segment(self.space.static_body, (680, 50), (680, 370), 3)
            , pymunk.Segment(self.space.static_body, (680, 370), (10, 370), 3)
            , pymunk.Segment(self.space.static_body, (10, 370), (10, 50), 3)
                       ]
        # paint some walls with colors
        static[1].color = (255, 0, 0)  # pygame.color.THECOLORS['red']
        static[2].color = (0, 255, 0)  # pygame.color.THECOLORS['green']
        static[3].color = (255, 0, 0)  # pygame.color.THECOLORS['red']

        # rounded shape
        rounded = [pymunk.Segment(self.space.static_body, (500, 50), (520, 60), 3)
            , pymunk.Segment(self.space.static_body, (520, 60), (540, 80), 3)
            , pymunk.Segment(self.space.static_body, (540, 80), (550, 100), 3)
            , pymunk.Segment(self.space.static_body, (550, 100), (550, 150), 3)
                        ]

        # static platforms
        platforms = [pymunk.Segment(self.space.static_body, (170, 50), (270, 150), 3)
                          # , pymunk.Segment(space.static_body, (270, 100), (300, 100), 5)
            , pymunk.Segment(self.space.static_body, (400, 150), (450, 150), 3)
            , pymunk.Segment(self.space.static_body, (400, 200), (450, 200), 3)
            , pymunk.Segment(self.space.static_body, (220, 200), (300, 200), 3)
            , pymunk.Segment(self.space.static_body, (50, 250), (200, 250), 3)
            , pymunk.Segment(self.space.static_body, (10, 370), (50, 250), 3)
                          ]

        # -- set friction and group for elements ---             ]
        for s in static + platforms + rounded:
            s.friction = 1.
            s.group = 1
        self.space.add(static, platforms + rounded)

    def run(self):
        running = True
        direction = 1
        remaining_jumps = 2
        landing = {'p': pymunk.Vec2d.zero(), 'n': 0}
        frame_number = 0
        landed_previous = False
        while running:

            grounding = {
                'normal': pymunk.Vec2d.zero(),
                'penetration': pymunk.Vec2d.zero(),
                'impulse': pymunk.Vec2d.zero(),
                'position': pymunk.Vec2d.zero(),
                'body': None
            }

            # find out if player is standing on ground

            def f(arbiter):
                n = -arbiter.contact_point_set.normal
                if n.y > grounding['normal'].y:
                    grounding['normal'] = n
                    grounding['penetration'] = -arbiter.contact_point_set.points[0].distance
                    grounding['body'] = arbiter.shapes[1].body
                    grounding['impulse'] = arbiter.total_impulse
                    grounding['position'] = arbiter.contact_point_set.points[0].point_b

            self.body.each_arbiter(f)

            well_grounded = False
            if grounding['body'] != None and abs(grounding['normal'].x / grounding['normal'].y) < self.feet.friction:
                well_grounded = True
                remaining_jumps = 2

            ground_velocity = pymunk.Vec2d.zero()
            if well_grounded:
                ground_velocity = grounding['body'].velocity
            # ------------------- EVENT HANDLER -----------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False
                    if event.key == pygame.K_p:
                        pygame.image.save(screen, "platformer.png")
                    # ---------JUMP ---------------
                    if event.key == pygame.K_UP:
                        if well_grounded or remaining_jumps > 0:
                            jump_v = math.sqrt(2.0 * self.JUMP_HEIGHT * abs(self.space.gravity.y))
                            impulse = (0, self.body.mass * (ground_velocity.y + jump_v))
                            self.body.apply_impulse_at_local_point(impulse)
                            remaining_jumps -= 1
                elif event.type == pygame.KEYUP and event.key == pygame.K_UP:
                    self.body.velocity.y = min(self.body.velocity.y, self.JUMP_CUTOFF_VELOCITY)

            # Target horizontal velocity of player
            target_vx = 0

            if self.body.velocity.x > .01:
                direction = 1
            elif self.body.velocity.x < -.01:
                direction = -1
            # -------- KEY handler pressed -------
            keys = pygame.key.get_pressed()
            if (keys[pygame.K_LEFT]):
                direction = -1
                target_vx -= self.PLAYER_VELOCITY
            if (keys[pygame.K_RIGHT]):
                direction = 1
                target_vx += self.PLAYER_VELOCITY
            if (keys[pygame.K_DOWN]):
                direction = -3

            self.feet.surface_velocity = -target_vx, 0

            if grounding['body'] != None:
                self.feet.friction = -self.PLAYER_GROUND_ACCEL / self.space.gravity.y
                self.head.friction = self.HEAD_FRICTION
            else:
                self.feet.friction, self.head.friction = 0, 0

            # Air control
            if grounding['body'] == None:
                self.body.velocity = pymunk.Vec2d(
                    cpflerpconst(self.body.velocity.x, target_vx + ground_velocity.x, self.PLAYER_AIR_ACCEL * self.dt),
                    self.body.velocity.y)

            self.body.velocity.y = max(self.body.velocity.y, -self.FALL_VELOCITY)  # clamp upwards as well?

            # Move the moving platform
            destination = self.platform_path[self.platform_path_index]
            current = pymunk.Vec2d(self.platform_body.position)
            distance = current.get_distance(destination)
            if distance < self.PLATFORM_SPEED:
                self.platform_path_index += 1
                self.platform_path_index = self.platform_path_index % len(self.platform_path)
                t = 1
            else:
                t = self.PLATFORM_SPEED / distance
            new = current.interpolate_to(destination, t)
            self.platform_body.position = new
            self.platform_body.velocity = (new - current) / self.dt

            ### Clear screen
            self.screen.fill((0,0,0))

            ### Helper lines
            for y in [50, 100, 150, 200, 250, 300]:
                color = (80,80,80)
                pygame.draw.line(self.screen, color, (10, y), (680, y), 1)

            ### Draw stuff
            self.space.debug_draw(self.draw_options)

            direction_offset = 48 + (1 * direction + 1) // 2 * 48
            if grounding['body'] != None and abs(target_vx) > 1:
                animation_offset = 32 * (frame_number // 8 % 4)
            elif grounding['body'] is None:
                animation_offset = 32 * 1
            else:
                animation_offset = 32 * 0
            position = self.body.position + (-16, 28)
            p = pymunk.pygame_util.to_pygame(position, self.screen)
            self.screen.blit(self.img, p, (animation_offset, direction_offset, 32, 48))

            # Did we land?
            if abs(grounding['impulse'].y) / self.body.mass > 200 and not landed_previous:
                self.sound.play()
                landing = {'p': grounding['position'], 'n': 5}
                landed_previous = True
            else:
                landed_previous = False
            if landing['n'] > 0:
                p = pymunk.pygame_util.to_pygame(landing['p'], self.screen)
                pygame.draw.circle(self.screen, (0, 255, 255), p, 5)
                landing['n'] -= 1

            # Info and flip screen
            write(self.screen, "fps: {:.2f} ".format(self.clock.get_fps()), 1, 1, (255, 255, 255), font_size=12)
            write(self.screen, "Move with Left/Right, jump with Up, press again to double jump", 100, 1, (250, 250, 250),
                  font_size=12)
            write(self.screen, "Press ESC or Q to quit", 1, 15, (255, 255, 255), font_size=12)
            # screen.blit(font.render("fps: " + str(clock.get_fps()), 1, (255,255,255), (0,0)))
            # screen.blit(font.render("Move with Left/Right, jump with Up, press again to double jump", 1, (50,50,50), (5,height - 35)))
            # screen.blit(font.render("Press ESC or Q to quit", 1, (50,50,50)), (5,height - 20))

            pygame.display.flip()
            frame_number += 1

            ### Update physics

            self.space.step(self.dt)

            self.clock.tick(self.fps)


if __name__ == '__main__':
    Viewer()
    sys.exit()

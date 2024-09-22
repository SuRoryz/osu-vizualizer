import os
import importlib.util
from .utils import osu_to_ndc, calculate_circle_radius

from OpenGL.GL import *
from .constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT
from config import *

class Renderer:
    def __init__(self, skin_name="default"):
        self.skin_name = skin_name
        self.skin_path = os.path.join('skins', self.skin_name)
        self.load_skin_functions()
        self.initialize_effects()

    def load_skin_functions(self):
        """
        Dynamically loads rendering functions from the skin modules.
        """
        self.render_functions = {}

        elements = ['circle', 'slider', 'spinner', 'cursor', 'cursor_trail', 'background']
        for element in elements:
            module_name = f'{element}_render'
            module_path = os.path.join(self.skin_path, f'{module_name}.py')
            if os.path.exists(module_path):
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.render_functions[element] = module
            else:
                print(f"Warning: {module_name}.py not found in skin '{self.skin_name} ({module_path})'. Using default rendering for {element}.")
                self.render_functions[element] = None  # Use default rendering

    def initialize_effects(self):
        """
        Loads the effects module from the skin and initializes it.
        """
        effects_module_path = os.path.join(self.skin_path, 'effects.py')
        if os.path.exists(effects_module_path):
            spec = importlib.util.spec_from_file_location('effects', effects_module_path)
            self.effects_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.effects_module)
            # Initialize effects if there's an initialization function
            if hasattr(self.effects_module, 'initialize_effects'):
                self.effects_module.initialize_effects()
        else:
            print(f"Warning: effects.py not found in skin '{self.skin_name}'. Effects will not be available.")
            self.effects_module = None

    def draw_circle_object(self, hit_object, cs, approach_scale):
        """
        Delegates circle object rendering to the skin's function.
        """
        if self.render_functions.get('circle') and hasattr(self.render_functions['circle'], 'draw_circle_object'):
            self.render_functions['circle'].draw_circle_object(hit_object, cs, approach_scale)
        else:
            self.default_draw_circle_object(hit_object, cs, approach_scale)

    def draw_slider_object(self, hit_object, cs, approach_scale):
        """
        Delegates slider object rendering to the skin's function.
        """
        if self.render_functions.get('slider') and hasattr(self.render_functions['slider'], 'draw_slider_object'):
            self.render_functions['slider'].draw_slider_object(hit_object, cs, approach_scale)
        else:
            self.default_draw_slider_object(hit_object, cs, approach_scale)

    def draw_spinner_object(self, hit_object, current_time):
        """
        Delegates spinner object rendering to the skin's function.
        """
        if self.render_functions.get('spinner') and hasattr(self.render_functions['spinner'], 'draw_spinner_object'):
            self.render_functions['spinner'].draw_spinner_object(hit_object, current_time)
        else:
            self.default_draw_spinner_object(hit_object, current_time)

    def draw_cursor(self, cursor_pos, cursor_color):
        """
        Delegates cursor rendering to the skin's function.
        """
        if self.render_functions.get('cursor') and hasattr(self.render_functions['cursor'], 'draw_cursor'):
            self.render_functions['cursor'].draw_cursor(cursor_pos, cursor_color)
        else:
            self.default_draw_cursor(cursor_pos, cursor_color)

    def draw_cursor_trail(self, trail_points):
        """
        Delegates cursor trail rendering to the skin's function.
        """
        if self.render_functions.get('cursor_trail') and hasattr(self.render_functions['cursor_trail'], 'draw_cursor_trail'):
            self.render_functions['cursor_trail'].draw_cursor_trail(trail_points)
        else:
            self.default_draw_cursor_trail(trail_points)

    def draw_background(self):
        """
        Delegates background rendering to the skin's function.
        """
        if self.render_functions.get('background') and hasattr(self.render_functions['background'], 'draw_background'):
            self.render_functions['background'].draw_background()
        else:
            self.default_draw_background()

    def render_effects(self):
        """
        Calls the skin's effects render function.
        """
        if self.effects_module and hasattr(self.effects_module, 'render_effects'):
            self.effects_module.render_effects()

    # Default rendering methods
    def default_draw_circle_object(self, hit_object, cs, approach_scale):
        """
        Default rendering for circle objects.
        """
        x = hit_object['x']
        y = hit_object['y']
        radius = calculate_circle_radius(cs)

        # Draw approach circle
        self.default_draw_approach_circle(x, y, radius, approach_scale)

        # Draw hit circle
        self.default_draw_circle(x, y, radius, color=(1, 1, 1))

    def default_draw_slider_object(self, hit_object, cs, approach_scale):
        """
        Default rendering for slider objects.
        """
        x = hit_object['x']
        y = hit_object['y']
        radius = calculate_circle_radius(cs)

        # Draw approach circle
        self.default_draw_approach_circle(x, y, radius, approach_scale)

        # Draw slider path
        self.default_draw_slider_path(hit_object)

        # Draw hit circle at slider start
        self.default_draw_circle(x, y, radius, color=(0.5, 1.0, 0.5))

    def default_draw_spinner_object(self, hit_object, current_time):
        """
        Default rendering for spinner objects.
        """
        start_time = hit_object['time']
        end_time = hit_object['end_time']

        if start_time <= current_time <= end_time:
            # Spinner is active
            glColor3f(0.8, 0.8, 0.8)
            glBegin(GL_QUADS)
            glVertex2f(-1, -1)
            glVertex2f(1, -1)
            glVertex2f(1, 1)
            glVertex2f(-1, 1)
            glEnd()

    def default_draw_cursor(self, cursor_pos, cursor_color):
        """
        Default rendering for the cursor.
        """
        osu_x = cursor_pos['x']
        osu_y = cursor_pos['y']
        self.default_draw_circle(osu_x, osu_y, CURSOR_SIZE, color=cursor_color)

    def default_draw_cursor_trail(self, trail_points):
        """
        Default rendering for the cursor trail.
        """
        num_points = min(len(trail_points), CURSOR_TRAIL_LENGTH)
        if num_points < 2:
            return

        glBegin(GL_LINE_STRIP)
        for i in range(-num_points, 0):
            point = trail_points[i]
            ndc_x, ndc_y = osu_to_ndc(point['x'], point['y'])

            if CURSOR_TRAIL_FADE:
                alpha = (i + num_points) / num_points
            else:
                alpha = 1.0
            glColor4f(1.0, 0.0, 0.0, alpha * 0.5)
            glVertex2f(ndc_x, ndc_y)
        glEnd()

    def default_draw_background(self):
        """
        Default rendering for the background.
        """
        glColor3f(0.1, 0.1, 0.1)
        glBegin(GL_QUADS)
        glVertex2f(-1, -1)
        glVertex2f(1, -1)
        glVertex2f(1, 1)
        glVertex2f(-1, 1)
        glEnd()

    def default_draw_circle(self, osu_x, osu_y, radius, color=(1, 1, 1)):
        """
        Draws a filled circle at the given osu! coordinates.
        """
        from OpenGL.GL import glBegin, glEnd, glVertex2f, GL_TRIANGLE_FAN, glColor3f
        import numpy as np

        ndc_x, ndc_y = osu_to_ndc(osu_x, osu_y)
        num_segments = 64  # Adjust for circle smoothness

        # Normalize radius for NDC
        ndc_radius_x = (radius / (OSU_PLAYFIELD_WIDTH / 2))
        ndc_radius_y = (radius / (OSU_PLAYFIELD_HEIGHT / 2))

        glColor3f(*color)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(ndc_x, ndc_y)  # Center of circle
        for i in range(num_segments + 1):
            angle = 2 * np.pi * i / num_segments
            dx = np.cos(angle) * ndc_radius_x
            dy = np.sin(angle) * ndc_radius_y
            glVertex2f(ndc_x + dx, ndc_y + dy)
        glEnd()

    def default_draw_approach_circle(self, osu_x, osu_y, radius, scale):
        """
        Draws the approach circle around the hit object.
        """
        scaled_radius = radius * (1 + scale * 3)
        self.default_draw_circle_outline(osu_x, osu_y, scaled_radius, color=(0.0, 0.5, 1.0))

    def default_draw_circle_outline(self, osu_x, osu_y, radius, color=(1, 1, 1)):
        """
        Draws an outlined circle at the given osu! coordinates.
        """
        from OpenGL.GL import glBegin, glEnd, glVertex2f, GL_LINE_LOOP, glColor3f
        import numpy as np

        ndc_x, ndc_y = osu_to_ndc(osu_x, osu_y)
        num_segments = 64  # Adjust for circle smoothness

        # Normalize radius for NDC
        ndc_radius_x = (radius / (OSU_PLAYFIELD_WIDTH / 2))
        ndc_radius_y = (radius / (OSU_PLAYFIELD_HEIGHT / 2))

        glColor3f(*color)
        glBegin(GL_LINE_LOOP)
        for i in range(num_segments):
            angle = 2 * np.pi * i / num_segments
            dx = np.cos(angle) * ndc_radius_x
            dy = np.sin(angle) * ndc_radius_y
            glVertex2f(ndc_x + dx, ndc_y + dy)
        glEnd()

    def default_draw_slider_path(self, hit_object):
        """
        Draws a simplified slider path.
        """
        from OpenGL.GL import glBegin, glEnd, glVertex2f, GL_LINE_STRIP, glColor3f

        start_x, start_y = hit_object['x'], hit_object['y']
        points = hit_object['curve_points']
        vertices = [(start_x, start_y)] + [(p['x'], p['y']) for p in points]

        glColor3f(1.0, 1.0, 0.0)
        glBegin(GL_LINE_STRIP)
        for x, y in vertices:
            ndc_x, ndc_y = osu_to_ndc(x, y)
            glVertex2f(ndc_x, ndc_y)
        glEnd()

    # Event callbacks
    def on_key_press(self, key):
        """
        Called when a key is pressed.
        """
        if self.effects_module and hasattr(self.effects_module, 'on_key_press'):
            self.effects_module.on_key_press(key)

    def on_object_hit(self, hit_object, score):
        """
        Called when an object is hit.
        """
        if self.effects_module and hasattr(self.effects_module, 'on_object_hit'):
            self.effects_module.on_object_hit(hit_object, score)

    def on_player_miss(self, hit_object):
        """
        Called when the player misses an object.
        """
        if self.effects_module and hasattr(self.effects_module, 'on_player_miss'):
            self.effects_module.on_player_miss(hit_object)

    def on_player_death(self):
        """
        Called when the player dies.
        """
        if self.effects_module and hasattr(self.effects_module, 'on_player_death'):
            self.effects_module.on_player_death()
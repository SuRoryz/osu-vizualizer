import os
import importlib.util

import numpy as np
from .utils import osu_to_ndc, calculate_circle_radius, load_texture

from OpenGL.GL import *
from .constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT, PLAYFIELD_MARGIN_LEFT, PLAYFIELD_MARGIN_RIGHT, PLAYFIELD_MARGIN_TOP, PLAYFIELD_MARGIN_BOTTOM
from config import *
from src.utils import load_texture
from glfw.GLFW import *

class Renderer:
    def __init__(self, window, window_width, window_height, skin_name="default"):
        self.skin_name = skin_name
        self.skin_path = os.path.join('skins', self.skin_name)

        self.window = window 
        self.window_width = window_width
        self.window_height = window_height

        # Initialize OpenGL settings
        self.initialize_opengl()

        # Load projection matrix
        self.projection_matrix = self.create_projection_matrix()
        self.ui_projection_matrix = self.create_ui_projection_matrix(window_width, window_height)

        # Load skin functions and shaders
        self.render_functions = {}
        self.shader_programs = {}
        self.load_skin_functions()

        self.hit_objects_effects = []

    def initialize_opengl(self):
        """
        Sets up OpenGL state.
        """
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glfwWindowHint(GLFW_SAMPLES, 4)

        glEnable(GL_MULTISAMPLE)

    def create_projection_matrix(self):
        left = 0 - PLAYFIELD_MARGIN_LEFT
        right = OSU_PLAYFIELD_WIDTH + PLAYFIELD_MARGIN_RIGHT
        top = 0 - PLAYFIELD_MARGIN_TOP
        bottom = OSU_PLAYFIELD_HEIGHT + PLAYFIELD_MARGIN_BOTTOM

        return np.array([
            [2.0 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2.0 / (bottom - top), 0, -(bottom + top) / (bottom - top)],
            [0, 0, -1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
    
    def create_ui_projection_matrix(self, width, height):
        left = 0
        right = width
        bottom = height
        top = 0

        return np.array([
            [2.0 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2.0 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
            [0, 0, -1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

    def load_skin_functions(self):
        """
        Dynamically loads rendering functions and shaders from the skin modules.
        """
        elements = ['circle', 'slider', 'spinner', 'cursor', 'cursor_trail', 'background', 'ui', 'effects']
        for element in elements:
            module_name = f'{element}_render'
            module_path = os.path.join(self.skin_path, f'{module_name}.py')
            if os.path.exists(module_path):
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.render_functions[element] = module

                # Call the init function if it exists
                if hasattr(module, 'init'):
                    module.init(self)
                else:
                    print(f"Warning: No init() function in {module_name}.py. Skipping shader loading for '{element}'.")
            else:
                print(f"Warning: {module_name}.py not found in skin '{self.skin_name}'.")
                self.render_functions[element] = None  # No rendering for this element

    # Rendering methods
    def draw_circle_object(self, hit_object, cs, approach_scale, current_time):
        """
        Delegates circle object rendering to the skin's function.
        """
        if 'circle' in self.render_functions and hasattr(self.render_functions['circle'], 'draw_circle_object'):
            self.render_functions['circle'].draw_circle_object(hit_object, cs, approach_scale, self, current_time)
        else:
            print("Warning: draw_circle_object() not implemented in skin.")

    def draw_slider_object(self, hit_object, cs, approach_scale, active_sliders, current_time):
        """
        Delegates slider object rendering to the skin's function.
        """
        if 'slider' in self.render_functions and hasattr(self.render_functions['slider'], 'draw_slider_object'):
            self.render_functions['slider'].draw_slider_object(hit_object, cs, approach_scale, self, active_sliders, current_time)
        else:
            print("Warning: draw_slider_object() not implemented in skin.")

    def draw_spinner_object(self, hit_object, current_time):
        """
        Delegates spinner object rendering to the skin's function.
        """
        if 'spinner' in self.render_functions and hasattr(self.render_functions['spinner'], 'draw_spinner_object'):
            self.render_functions['spinner'].draw_spinner_object(hit_object, self, current_time)
        else:
            print("Warning: draw_spinner_object() not implemented in skin.")

    def draw_cursor(self, cursor_pos, cursor_color, current_time):
        """
        Delegates cursor rendering to the skin's function.
        """
        if 'cursor' in self.render_functions and hasattr(self.render_functions['cursor'], 'draw_cursor'):
            self.render_functions['cursor'].draw_cursor(cursor_pos, cursor_color, self, current_time)
        else:
            print("Warning: draw_cursor() not implemented in skin.")

    def draw_cursor_trail(self, trail_points, current_time):
        """
        Delegates cursor trail rendering to the skin's function.
        """
        if 'cursor_trail' in self.render_functions and hasattr(self.render_functions['cursor_trail'], 'draw_cursor_trail'):
            self.render_functions['cursor_trail'].draw_cursor_trail(trail_points, self, current_time)
        else:
            print("Warning: draw_cursor_trail() not implemented in skin.")

    def draw_background(self, current_time, last_press_time):
        """
        Delegates background rendering to the skin's function.
        """
        if 'background' in self.render_functions and hasattr(self.render_functions['background'], 'draw_background'):
            self.render_functions['background'].draw_background(self, current_time, last_press_time)
        else:
            print("Warning: draw_background() not implemented in skin.")

    def draw_ui(self, score, combo, accuracy, hp, current_keys, current_time):
        """
        Delegates UI rendering to the skin's function.
        """
        if 'ui' in self.render_functions and hasattr(self.render_functions['ui'], 'draw_ui'):
            self.render_functions['ui'].draw_ui(self, score, combo, accuracy, hp, current_keys, current_time)
        else:
            print("Warning: draw_ui() not implemented in skin.")

    def render_effects(self, current_time):
        """
        Delegates effect rendering to the skin's function.
        """
        if 'effects' in self.render_functions and hasattr(self.render_functions['effects'], 'render_effects'):
            self.render_functions['effects'].render_effects(self, current_time)
        else:
            print("Warning: render_effects() not implemented in skin.")

    # Event callbacks
    def on_object_hit(self, hit_object, hit_score):
        """
        Called when an object is hit.
        """
        current_time = self.current_time
        if 'effects' in self.render_functions and hasattr(self.render_functions['effects'], 'on_object_hit'):
            self.render_functions['effects'].on_object_hit(hit_object, current_time)
        # Additional processing can be added here

    def on_player_miss(self, hit_object):
        """
        Called when the player misses an object.
        """
        current_time = self.current_time
        if 'effects' in self.render_functions and hasattr(self.render_functions['effects'], 'on_player_miss'):
            self.render_functions['effects'].on_player_miss(hit_object, current_time)
        # Additional processing can be added here

    def update_current_time(self, current_time):
        """
        Updates the current time in the renderer.
        """
        self.current_time = current_time

    def cleanup(self):
        """
        Cleans up OpenGL resources.
        """
        # Clean up shaders
        for shader_program in self.shader_programs.values():
            glDeleteProgram(shader_program)

    # Event callbacks
    def on_key_press(self, key):
        """
        Called when a key is pressed.
        """
        if self.effects_module and hasattr(self.effects_module, 'on_key_press'):
            self.effects_module.on_key_press(key)

    def on_object_hit(self, hit_object, hit_score, start_time):
        """
        Called when an object is hit.
        """
        # Add the hit object to the list with additional data
        self.hit_objects_effects.append({
            'object': hit_object,
            'start_time': hit_object['time'],
            'effect_start_time': start_time,  # Current time in ms
            'duration': 500,  # Duration of the hit effect in ms
            'hit_score': hit_score
        })

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

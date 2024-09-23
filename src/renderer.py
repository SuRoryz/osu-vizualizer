import os
import importlib.util

import numpy as np
from .utils import osu_to_ndc, calculate_circle_radius

from OpenGL.GL import *
from .constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT
from config import *

class Renderer:
    def __init__(self, skin_name="default"):
        self.skin_name = skin_name
        self.skin_path = os.path.join('skins', self.skin_name)
        self.load_skin_functions()
        self.initialize_shaders()
        self.initialize_background()
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
    
    def initialize_shaders(self):
        """
        Compiles and links shaders, and sets up any necessary OpenGL state.
        """
        # Compile shaders
        vertex_shader_source = open(os.path.join('src', 'shaders', 'vertex_shader.glsl')).read()
        fragment_shader_source = open(os.path.join('src', 'shaders', 'fragment_shader.glsl')).read()
        self.shader_program = self.create_shader_program(vertex_shader_source, fragment_shader_source)

        # Get attribute and uniform locations
        self.position_loc = glGetAttribLocation(self.shader_program, 'a_position')
        self.color_loc = glGetAttribLocation(self.shader_program, 'a_color')
        self.mvp_matrix_loc = glGetUniformLocation(self.shader_program, 'u_mvp_matrix')

        # Set up projection matrix (orthographic)
        left = 0
        right = OSU_PLAYFIELD_WIDTH
        bottom = OSU_PLAYFIELD_HEIGHT
        top = 0

        self.projection_matrix = np.array([
            [2.0 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2.0 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
            [0, 0, -1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        # Enable blending
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

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
    
    def initialize_background(self):
        """
        Sets up buffer objects for the background.
        """
        vertices = np.array([
            [-1.0, -1.0],  # Bottom-left
            [1.0, -1.0],   # Bottom-right
            [-1.0, 1.0],   # Top-left
            [1.0, 1.0]     # Top-right
        ], dtype=np.float32)

        colors = np.array([
            [0.1, 0.1, 0.1, 1.0],
            [0.1, 0.1, 0.1, 1.0],
            [0.1, 0.1, 0.1, 1.0],
            [0.1, 0.1, 0.1, 1.0]
        ], dtype=np.float32)

        self.background_vao = glGenVertexArrays(1)
        glBindVertexArray(self.background_vao)

        vbo_vertices = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.position_loc)
        glVertexAttribPointer(self.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

        vbo_colors = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
        glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.color_loc)
        glVertexAttribPointer(self.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

        # Unbind VAO and VBO
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        # Store VBOs for cleanup
        self.background_vbos = [vbo_vertices, vbo_colors]

    def create_shader_program(self, vertex_source, fragment_source):
        """
        Compiles vertex and fragment shaders and links them into a program.
        """
        vertex_shader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex_shader, vertex_source)
        glCompileShader(vertex_shader)
        if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(vertex_shader).decode()
            print(f"Vertex shader compilation error: {error}")
            glDeleteShader(vertex_shader)
            return None

        fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment_shader, fragment_source)
        glCompileShader(fragment_shader)
        if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(fragment_shader).decode()
            print(f"Fragment shader compilation error: {error}")
            glDeleteShader(fragment_shader)
            return None

        shader_program = glCreateProgram()
        glAttachShader(shader_program, vertex_shader)
        glAttachShader(shader_program, fragment_shader)
        glLinkProgram(shader_program)
        if not glGetProgramiv(shader_program, GL_LINK_STATUS):
            error = glGetProgramInfoLog(shader_program).decode()
            print(f"Shader program linking error: {error}")
            glDeleteProgram(shader_program)
            return None

        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)

        return shader_program

    def draw_circle_object(self, hit_object, cs, approach_scale):
        """
        Delegates circle object rendering to the skin's function.
        """
        if self.render_functions.get('circle') and hasattr(self.render_functions['circle'], 'draw_circle_object'):
            self.render_functions['circle'].draw_circle_object(hit_object, cs, approach_scale, renderer=self)
        else:
            self.default_draw_circle_object(hit_object, cs, approach_scale)

    def draw_slider_object(self, hit_object, cs, approach_scale):
        """
        Delegates slider object rendering to the skin's function.
        """
        if self.render_functions.get('slider') and hasattr(self.render_functions['slider'], 'draw_slider_object'):
            self.render_functions['slider'].draw_slider_object(hit_object, cs, approach_scale, renderer=self)
        else:
            self.default_draw_slider_object(hit_object, cs, approach_scale)

    def draw_spinner_object(self, hit_object, current_time):
        """
        Delegates spinner object rendering to the skin's function.
        """
        if self.render_functions.get('spinner') and hasattr(self.render_functions['spinner'], 'draw_spinner_object'):
            self.render_functions['spinner'].draw_spinner_object(hit_object, current_time, renderer=self)
        else:
            self.default_draw_spinner_object(hit_object, current_time)

    def draw_cursor(self, cursor_pos, cursor_color):
        """
        Delegates cursor rendering to the skin's function.
        """
        if self.render_functions.get('cursor') and hasattr(self.render_functions['cursor'], 'draw_cursor'):
            self.render_functions['cursor'].draw_cursor(cursor_pos, cursor_color, renderer=self)
        else:
            self.default_draw_cursor(cursor_pos, cursor_color)

    def draw_cursor_trail(self, trail_points):
        """
        Delegates cursor trail rendering to the skin's function.
        """
        if self.render_functions.get('cursor_trail') and hasattr(self.render_functions['cursor_trail'], 'draw_cursor_trail'):
            self.render_functions['cursor_trail'].draw_cursor_trail(trail_points, renderer=self)
        else:
            self.default_draw_cursor_trail(trail_points)

    def draw_background(self):
        """
        Delegates background rendering to the skin's function.
        """
        if self.render_functions.get('background') and hasattr(self.render_functions['background'], 'draw_background'):
            self.render_functions['background'].draw_background(renderer=self)
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
        Default rendering for the cursor trail using shaders.
        """
        num_points = min(len(trail_points), CURSOR_TRAIL_LENGTH)
        if num_points < 2:
            return

        # Prepare vertex and color data
        vertices = np.array([osu_to_ndc(p['x'], p['y']) for p in trail_points[-num_points:]], dtype=np.float32)

        if CURSOR_TRAIL_FADE:
            alphas = np.linspace(0.5, 0.0, num_points)
        else:
            alphas = np.full(num_points, 0.5)

        colors = np.zeros((num_points, 4), dtype=np.float32)
        colors[:, 0] = 1.0  # Red color
        colors[:, 3] = alphas  # Alpha values

        # Create VBOs
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo_vertices = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
        glEnableVertexAttribArray(self.position_loc)
        glVertexAttribPointer(self.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

        vbo_colors = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
        glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_DYNAMIC_DRAW)
        glEnableVertexAttribArray(self.color_loc)
        glVertexAttribPointer(self.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

        # Use shader program
        glUseProgram(self.shader_program)
        glUniformMatrix4fv(self.mvp_matrix_loc, 1, GL_FALSE, self.projection_matrix.T)

        # Draw the cursor trail
        glDrawArrays(GL_LINE_STRIP, 0, num_points)

        # Clean up
        glDisableVertexAttribArray(self.position_loc)
        glDisableVertexAttribArray(self.color_loc)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glDeleteBuffers(2, [vbo_vertices, vbo_colors])
        glDeleteVertexArrays(1, [vao])

    def default_draw_background(self):
        """
        Draws the background using pre-initialized VBOs.
        """
        glBindVertexArray(self.background_vao)
        glUseProgram(self.shader_program)
        glUniformMatrix4fv(self.mvp_matrix_loc, 1, GL_FALSE, self.projection_matrix.T)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glBindVertexArray(0)

    def default_draw_circle(self, osu_x, osu_y, radius, color=(1, 1, 1, 1)):
        """
        Draws a filled circle at the given osu! coordinates using shaders.
        """
        num_segments = 64
        angle_increment = 2 * np.pi / num_segments
        angles = np.arange(0, 2 * np.pi + angle_increment, angle_increment, dtype=np.float32)
        vertices = np.zeros((len(angles) + 1, 2), dtype=np.float32)
        colors = np.tile(color, (len(vertices), 1)).astype(np.float32)

        # Center vertex
        vertices[0] = [osu_x, osu_y]
        # Circle vertices
        vertices[1:, 0] = osu_x + radius * np.cos(angles)
        vertices[1:, 1] = osu_y + radius * np.sin(angles)

        # Create VBOs
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo_vertices = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.position_loc)
        glVertexAttribPointer(self.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

        vbo_colors = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
        glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.color_loc)
        glVertexAttribPointer(self.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

        # Use shader program
        glUseProgram(self.shader_program)
        glUniformMatrix4fv(self.mvp_matrix_loc, 1, GL_FALSE, self.projection_matrix.T)

        # Draw the circle
        glDrawArrays(GL_TRIANGLE_FAN, 0, len(vertices))

        # Clean up
        glDisableVertexAttribArray(self.position_loc)
        glDisableVertexAttribArray(self.color_loc)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glDeleteBuffers(2, [vbo_vertices, vbo_colors])
        glDeleteVertexArrays(1, [vao])

    def default_draw_approach_circle(self, osu_x, osu_y, radius, scale):
        """
        Draws the approach circle around the hit object.
        """
        scaled_radius = radius * (1 + scale * 3)
        self.default_draw_circle_outline(osu_x, osu_y, scaled_radius, color=(0.0, 0.5, 1.0))

    def default_draw_circle_outline(self, osu_x, osu_y, radius, color=(1, 1, 1, 1)):
        """
        Draws an outlined circle at the given osu! coordinates using shaders.
        """
        num_segments = 64
        angle_increment = 2 * np.pi / num_segments
        angles = np.arange(0, 2 * np.pi, angle_increment, dtype=np.float32)
        vertices = np.zeros((len(angles), 2), dtype=np.float32)
        colors = np.tile(color, (len(vertices), 1)).astype(np.float32)

        # Convert osu! coordinates to screen coordinates
        x, y = osu_to_ndc(osu_x, osu_y)

        # Circle vertices
        vertices[:, 0] = x + radius * np.cos(angles)
        vertices[:, 1] = y + radius * np.sin(angles)

        # Create VBOs
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo_vertices = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.position_loc)
        glVertexAttribPointer(self.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

        vbo_colors = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
        glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.color_loc)
        glVertexAttribPointer(self.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

        # Use shader program
        glUseProgram(self.shader_program)
        glUniformMatrix4fv(self.mvp_matrix_loc, 1, GL_FALSE, self.projection_matrix.T)

        # Draw the circle outline
        glDrawArrays(GL_LINE_LOOP, 0, len(vertices))

        # Clean up
        glDisableVertexAttribArray(self.position_loc)
        glDisableVertexAttribArray(self.color_loc)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glDeleteBuffers(2, [vbo_vertices, vbo_colors])
        glDeleteVertexArrays(1, [vao])

    def default_draw_slider_path(self, hit_object):
        """
        Draws the slider path using shaders.
        """
        # Extract vertices
        start_x, start_y = hit_object['x'], hit_object['y']
        points = hit_object['curve_points']
        vertices_osu = [(start_x, start_y)] + [(p['x'], p['y']) for p in points]
        vertices = np.array([osu_to_ndc(x, y) for x, y in vertices_osu], dtype=np.float32)

        color = (1.0, 1.0, 0.0, 1.0)  # Yellow color for slider path
        colors = np.tile(color, (len(vertices), 1)).astype(np.float32)

        # Create VBOs
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo_vertices = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.position_loc)
        glVertexAttribPointer(self.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

        vbo_colors = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
        glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
        glEnableVertexAttribArray(self.color_loc)
        glVertexAttribPointer(self.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

        # Use shader program
        glUseProgram(self.shader_program)
        glUniformMatrix4fv(self.mvp_matrix_loc, 1, GL_FALSE, self.projection_matrix.T)

        # Draw the slider path
        glDrawArrays(GL_LINE_STRIP, 0, len(vertices))

        # Clean up
        glDisableVertexAttribArray(self.position_loc)
        glDisableVertexAttribArray(self.color_loc)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        glDeleteBuffers(2, [vbo_vertices, vbo_colors])
        glDeleteVertexArrays(1, [vao])

    def cleanup(self):
        """
        Cleans up OpenGL resources.
        """
        if hasattr(self, 'background_vao'):
            glDeleteVertexArrays(1, [self.background_vao])
            glDeleteBuffers(2, self.background_vbos)
        if hasattr(self, 'shader_program'):
            glDeleteProgram(self.shader_program)

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
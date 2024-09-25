from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc
from config import CURSOR_TRAIL_LENGTH, CURSOR_TRAIL_FADE, CURSOR_SIZE

import os
from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc

# Module-level variables
shader_program = None
uniform_locations = {}

def init(renderer):
    """
    Initializes the cursor trail rendering module, loads shaders, and compiles them.
    """
    global shader_program, uniform_locations

    # Load shader sources
    vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'cursor_trail', 'vertex.glsl')
    fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'cursor_trail', 'fragment.glsl')

    with open(vertex_shader_path, 'r') as f:
        vertex_shader_source = f.read()
    with open(fragment_shader_path, 'r') as f:
        fragment_shader_source = f.read()

    # Compile shaders
    shader_program = create_shader_program(vertex_shader_source, fragment_shader_source)

    # Get uniform locations
    uniform_locations['u_mvp_matrix'] = glGetUniformLocation(shader_program, 'u_mvp_matrix')
    uniform_locations['u_time'] = glGetUniformLocation(shader_program, 'u_time')

def create_shader_program(vertex_source, fragment_source):
    """
    Compiles vertex and fragment shaders and links them into a program.
    """
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, vertex_source)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(vertex_shader).decode()
        print(f"Circle Vertex Shader compilation error: {error}")
        glDeleteShader(vertex_shader)
        return None

    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, fragment_source)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(fragment_shader).decode()
        print(f"Circle Fragment Shader compilation error: {error}")
        glDeleteShader(fragment_shader)
        return None

    program = glCreateProgram()
    glAttachShader(program, vertex_shader)
    glAttachShader(program, fragment_shader)
    glLinkProgram(program)
    if not glGetProgramiv(program, GL_LINK_STATUS):
        error = glGetProgramInfoLog(program).decode()
        print(f"Circle Shader Program linking error: {error}")
        glDeleteProgram(program)
        return None

    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return program

def draw_cursor_trail(trail_points, renderer, current_time):
    """
    Draws the cursor trail as a smooth cone-like shape with a rainbow gradient.
    """
    if len(trail_points) < 2:
        return

    vertices = []
    for i, point in enumerate(trail_points):
        x, y = osu_to_ndc(point['x'], point['y'])
        vertices.append([x, y])

    vertices = np.array(vertices, dtype=np.float32)

    # Generate widths for the cone-like shape
    start_width = CURSOR_SIZE / 2
    end_width = 0.0
    widths = np.linspace(start_width, end_width, len(vertices))

    # Create VAO and VBOs
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    # Vertex positions
    vbo_positions = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_positions)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    position_loc = glGetAttribLocation(shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Widths
    vbo_widths = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_widths)
    glBufferData(GL_ARRAY_BUFFER, widths.nbytes, widths, GL_STATIC_DRAW)
    width_loc = glGetAttribLocation(shader_program, 'a_width')
    glEnableVertexAttribArray(width_loc)
    glVertexAttribPointer(width_loc, 1, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(shader_program)

    # Set uniforms
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(uniform_locations['u_time'], current_time)

    # Draw the cursor trail
    glDrawArrays(GL_TRIANGLE_STRIP, 0, len(vertices))

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glDisableVertexAttribArray(width_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_positions, vbo_widths])
    glDeleteVertexArrays(1, [vao])

import os
from OpenGL.GL import *
import numpy as np
from skins.default.circle_render import draw_circle
from src.utils import osu_to_ndc
from config import CURSOR_SIZE
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

# Module-level variables
shader_program = None
uniform_locations = {}

def init(renderer):
    """
    Initializes the cursor rendering module, loads shaders, and compiles them.
    """
    global shader_program, uniform_locations

    # Load shader sources
    vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'cursor', 'vertex.glsl')
    fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'cursor', 'fragment.glsl')

    with open(vertex_shader_path, 'r') as f:
        vertex_shader_source = f.read()
    with open(fragment_shader_path, 'r') as f:
        fragment_shader_source = f.read()

    # Compile shaders
    shader_program = create_shader_program(vertex_shader_source, fragment_shader_source)

    # Get uniform locations
    uniform_locations['u_mvp_matrix'] = glGetUniformLocation(shader_program, 'u_mvp_matrix')
    uniform_locations['u_time'] = glGetUniformLocation(shader_program, 'u_time')
    uniform_locations['u_cursor_size'] = glGetUniformLocation(shader_program, 'u_cursor_size')

def create_shader_program(vertex_source, fragment_source):
    # Compile vertex shader
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, vertex_source)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(vertex_shader).decode()
        print(f"Vertex Shader compilation error:\n{error}")
        glDeleteShader(vertex_shader)
        return None
    
    print(fragment_source)

    # Compile fragment shader
    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, fragment_source)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(fragment_shader).decode()
        print(f"Fragment Shader compilation error:\n{error}")
        glDeleteShader(fragment_shader)
        glDeleteShader(vertex_shader)
        return None

    # Link shaders into a program
    shader_program = glCreateProgram()
    glAttachShader(shader_program, vertex_shader)
    glAttachShader(shader_program, fragment_shader)
    glLinkProgram(shader_program)
    if not glGetProgramiv(shader_program, GL_LINK_STATUS):
        error = glGetProgramInfoLog(shader_program).decode()
        print(f"Shader Program linking error:\n{error}")
        glDeleteProgram(shader_program)
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        return None

    # Clean up shaders
    #glDeleteShader(vertex_shader)
    #glDeleteShader(fragment_shader)

    return shader_program

def draw_cursor(cursor_pos, cursor_color, renderer, current_time):
    """
    Draws the cursor with a rainbow gradient and white glow.
    """
    osu_x = cursor_pos['x']
    osu_y = cursor_pos['y']
    radius = CURSOR_SIZE

    num_segments = 64
    theta = np.linspace(0, 2 * np.pi, num_segments, endpoint=False)
    vertices = np.zeros((num_segments, 2), dtype=np.float32)
    x_ndc, y_ndc = osu_to_ndc(osu_x, osu_y)
    vertices[:, 0] = x_ndc + radius * np.cos(theta)
    vertices[:, 1] = y_ndc + radius * np.sin(theta)

    # Create VAO and VBO
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Enable vertex attribute
    position_loc = glGetAttribLocation(shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(shader_program)

    # Set uniforms
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(uniform_locations['u_time'], current_time)
    glUniform1f(uniform_locations['u_cursor_size'], radius)

    # Draw the cursor
    glDrawArrays(GL_TRIANGLE_FAN, 0, num_segments)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])
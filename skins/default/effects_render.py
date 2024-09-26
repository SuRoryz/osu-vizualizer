# skins/default/effects.py

import os
from OpenGL.GL import *
import numpy as np
import time
from src.utils import osu_to_ndc, calculate_circle_radius
from src.constants import OSU_PLAYFIELD_WIDTH
from skins.default.skin_settings import SKIN_SETTINGS
from skins.default.circle_render import draw_circle

# Module-level variables
hit_effects = []
shader_program = None
uniform_locations = {}

def init(renderer):
    """
    Initializes the effects module, loads shaders, and compiles them.
    """
    global shader_program, uniform_locations

    # Load shader sources
    vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'effects', 'vertex.glsl')
    fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'effects', 'fragment.glsl')

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

def on_object_hit(hit_object, current_time):
    """
    Adds a hit effect for the hit object.
    """
    hit_effects.append({
        'object': hit_object,
        'start_time': current_time,
        'duration': 0.5  # Duration in seconds
    })

def render_effects(renderer, current_time):
    """
    Renders all active effects.
    """
    global hit_effects
    active_effects = []
    for effect in hit_effects:
        elapsed = current_time - effect['start_time']
        if elapsed < effect['duration']:
            progress = elapsed / effect['duration']
            render_hit_effect(effect['object'], progress, renderer, current_time)
            active_effects.append(effect)
    hit_effects = active_effects

def render_hit_effect(hit_object, progress, renderer, current_time):
    """
    Renders a cool hit effect at the hit object's position.
    """
    x = hit_object['x']
    y = hit_object['y']
    radius = calculate_circle_radius(renderer.cs)
    opacity = 1.0 - progress

    num_segments = 64
    theta = np.linspace(0, 2 * np.pi, num_segments)
    vertices = np.zeros((num_segments, 2), dtype=np.float32)
    x_ndc, y_ndc = osu_to_ndc(x, y)
    scale = 1.0 + progress * 2.0
    vertices[:, 0] = x_ndc + radius * scale * np.cos(theta)
    vertices[:, 1] = y_ndc + radius * scale * np.sin(theta)

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

    # Draw the effect
    glDrawArrays(GL_TRIANGLE_FAN, 0, num_segments)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])
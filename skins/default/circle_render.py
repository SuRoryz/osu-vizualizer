# skins/default/circle_render.py

from OpenGL.GL import *
import numpy as np
import os
from src.utils import osu_to_ndc, calculate_circle_radius

# Module-level variables
shader_program = None
uniform_locations = {}

def init(renderer):
    """
    Initializes the circle rendering module, loads shaders, and compiles them.
    """
    global shader_program, uniform_locations

    # Load shader sources
    vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'circle', 'vertex.glsl')
    fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'circle', 'fragment.glsl')

    with open(vertex_shader_path, 'r') as f:
        vertex_shader_source = f.read()
    with open(fragment_shader_path, 'r') as f:
        fragment_shader_source = f.read()

    # Compile shaders
    shader_program = create_shader_program(vertex_shader_source, fragment_shader_source)

    if shader_program is None:
        raise RuntimeError("Failed to create shader program for circle.")

    # Get uniform locations
    uniform_locations['u_mvp_matrix'] = glGetUniformLocation(shader_program, 'u_mvp_matrix')
    uniform_locations['u_time'] = glGetUniformLocation(shader_program, 'u_time')
    uniform_locations['u_opacity'] = glGetUniformLocation(shader_program, 'u_opacity')
    uniform_locations['u_circle_radius'] = glGetUniformLocation(shader_program, 'u_circle_radius')

def create_shader_program(vertex_source, fragment_source):
    """
    Compiles vertex and fragment shaders and links them into a program.
    """
    # Compile vertex shader
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, vertex_source)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(vertex_shader).decode()
        print(f"Circle Vertex Shader compilation error: {error}")
        glDeleteShader(vertex_shader)
        return None

    # Compile fragment shader
    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, fragment_source)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(fragment_shader).decode()
        print(f"Circle Fragment Shader compilation error: {error}")
        glDeleteShader(fragment_shader)
        glDeleteShader(vertex_shader)
        return None

    # Link shaders into a program
    program = glCreateProgram()
    glAttachShader(program, vertex_shader)
    glAttachShader(program, fragment_shader)
    glLinkProgram(program)
    if not glGetProgramiv(program, GL_LINK_STATUS):
        error = glGetProgramInfoLog(program).decode()
        print(f"Circle Shader Program linking error: {error}")
        glDeleteProgram(program)
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        return None

    # Clean up shaders
    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return program

def draw_circle_object(hit_object, cs, approach_scale, renderer, current_time):
    """
    Draws a circle hit object with the specified visual effects.
    """
    x = hit_object['x']
    y = hit_object['y']
    radius = calculate_circle_radius(cs)

    # Draw approach circle if necessary
    if approach_scale > 0:
        draw_approach_circle(x, y, radius, approach_scale, renderer)

    # Draw the main circle with shaders
    draw_circle(x, y, radius, renderer, current_time)

def draw_circle(osu_x, osu_y, radius, renderer, current_time, opacity=0.2,
                custom_shader_program=None, custom_uniform_locations=None):
    """
    Draws a circle with the specified visual effects.
    """
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

    if custom_shader_program:
        used_shader_program = custom_shader_program
    else:
        used_shader_program = shader_program

    if custom_uniform_locations:
        used_uniform_locations = custom_uniform_locations
    else:
        used_uniform_locations = uniform_locations

    # Enable vertex attribute
    position_loc = glGetAttribLocation(used_shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(used_shader_program)

    # Set uniforms
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(used_uniform_locations['u_time'], current_time)
    glUniform1f(used_uniform_locations['u_circle_radius'], radius)
    glUniform1f(used_uniform_locations['u_opacity'], opacity)

    # Draw the circle
    glDrawArrays(GL_TRIANGLE_FAN, 0, num_segments)

    # Draw the white outline
    draw_circle_outline(osu_x, osu_y, radius, renderer)

    # Draw the smaller white circle in the center
    draw_small_circle(osu_x, osu_y, radius * 0.25, renderer)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])

def draw_circle_outline(osu_x, osu_y, radius, renderer, custom_shader_program=None):
    """
    Draws a thin white outline around the circle.
    """
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

    if custom_shader_program:
        used_shader_program = custom_shader_program
    else:
        used_shader_program = shader_program

    # Enable vertex attribute
    position_loc = glGetAttribLocation(used_shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(used_shader_program)

    # Set uniforms
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)

    # Draw outline
    glLineWidth(2.0)
    glUniform1f(uniform_locations['u_opacity'], 1.0)
    glDrawArrays(GL_LINE_LOOP, 0, num_segments)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])

def draw_small_circle(osu_x, osu_y, radius, renderer):
    """
    Draws a smaller white circle in the center.
    """
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
    glUniform1f(uniform_locations['u_opacity'], 1.0)  # Full opacity

    # Draw the small circle
    glDrawArrays(GL_TRIANGLE_FAN, 0, num_segments)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])

def draw_approach_circle(osu_x, osu_y, radius, scale, renderer, custom_shader_program=None):
    """
    Draws the approach circle around the hit object.
    """
    scaled_radius = radius * (1 + scale * 3)
    draw_circle_outline(osu_x, osu_y, scaled_radius, renderer, custom_shader_program)
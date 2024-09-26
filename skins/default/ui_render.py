from OpenGL.GL import *
import pygame
from src.utils import surface_to_texture
import freetype
import numpy as np
from osrparse.replay import Key

import os
from OpenGL.GL import *
import numpy as np
import pygame

# Module-level variables
shader_program = None
uniform_locations = {}
font = None

def init(renderer):
    """
    Initializes the UI rendering module, loads shaders, and compiles them.
    """
    global shader_program, uniform_locations, font

    # Load shader sources
    vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'ui', 'vertex.glsl')
    fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'ui', 'fragment.glsl')

    with open(vertex_shader_path, 'r') as f:
        vertex_shader_source = f.read()
    with open(fragment_shader_path, 'r') as f:
        fragment_shader_source = f.read()

    # Compile shaders
    shader_program = create_shader_program(vertex_shader_source, fragment_shader_source)

    # Get uniform locations
    uniform_locations['u_mvp_matrix'] = glGetUniformLocation(shader_program, 'u_mvp_matrix')
    uniform_locations['u_texture'] = glGetUniformLocation(shader_program, 'u_texture')

    # Initialize font
    pygame.font.init()
    font = pygame.font.SysFont('Arial', 24)

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

def draw_ui(renderer, score, combo, accuracy, hp, current_keys, current_time):
    """
    Draws the UI elements.
    """
    # Draw HP bar
    draw_hp_bar(renderer, hp, current_time)

    # Draw score, combo, accuracy
    draw_text(renderer, f"Score: {score}", x=10, y=10)
    draw_text(renderer, f"Combo: {combo}", x=10, y=40)
    draw_text(renderer, f"Accuracy: {accuracy:.2f}%", x=10, y=70)

def draw_hp_bar(renderer, hp, current_time):
    """
    Draws the HP bar with a shader effect.
    """
    # Define vertices for the HP bar
    x = 10
    y = renderer.window_height - 30
    width = renderer.window_width - 20
    height = 20
    hp_width = width * hp

    vertices = np.array([
        [x, y],
        [x + hp_width, y],
        [x, y + height],
        [x + hp_width, y + height]
    ], dtype=np.float32)

    # Create VAO and VBO
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Enable vertex attribute
    position_loc = glGetAttribLocation(shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(shader_program)

    # Set uniforms
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.ui_projection_matrix.T)
    glUniform1i(uniform_locations['u_texture'], 0)  # If using a texture

    # Draw the HP bar
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo_vertices])
    glDeleteVertexArrays(1, [vao])

def draw_text(renderer, text, x, y):
    """
    Renders text using Pygame and OpenGL.
    """
    # Render text surface
    text_surface = font.render(text, True, (255, 255, 255))
    texture_data = pygame.image.tostring(text_surface, "RGBA", True)
    width, height = text_surface.get_size()

    # Generate texture
    texture = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

    # Define quad
    vertices = np.array([
        [x, y],
        [x + width, y],
        [x, y + height],
        [x + width, y + height]
    ], dtype=np.float32)

    tex_coords = np.array([
        [0, 1],
        [1, 1],
        [0, 0],
        [1, 0]
    ], dtype=np.float32)

    # Create VAO and VBOs
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    # Vertex positions
    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    position_loc = glGetAttribLocation(shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Texture coordinates
    vbo_tex_coords = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_tex_coords)
    glBufferData(GL_ARRAY_BUFFER, tex_coords.nbytes, tex_coords, GL_STATIC_DRAW)
    tex_coord_loc = glGetAttribLocation(shader_program, 'a_tex_coord')
    glEnableVertexAttribArray(tex_coord_loc)
    glVertexAttribPointer(tex_coord_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(shader_program)

    # Set uniforms
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.ui_projection_matrix.T)
    glUniform1i(uniform_locations['u_texture'], 0)

    # Bind texture
    glActiveTexture(GL_TEXTURE0)
    glBindTexture(GL_TEXTURE_2D, texture)

    # Draw the text
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glDisableVertexAttribArray(tex_coord_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_tex_coords])
    glDeleteVertexArrays(1, [vao])
    glDeleteTextures([texture])


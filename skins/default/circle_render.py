from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc, calculate_circle_radius
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

def draw_circle_object(hit_object, cs, approach_scale, renderer):
    """
    Draws a circle hit object with an approach circle using shaders.
    """
    x = hit_object['x']
    y = hit_object['y']
    radius = calculate_circle_radius(cs)

    # Draw approach circle
    draw_approach_circle(x, y, radius, approach_scale, renderer)

    # Draw hit circle
    draw_circle(x, y, radius, color=(1, 1, 1, 1), renderer=renderer)

def draw_circle(osu_x, osu_y, radius, color, renderer):
    """
    Draws a filled circle using shaders.
    """
    num_segments = 64
    angle_increment = 2 * np.pi / num_segments
    angles = np.arange(0, 2 * np.pi + angle_increment, angle_increment, dtype=np.float32)
    vertices = np.zeros((len(angles) + 1, 2), dtype=np.float32)
    colors = np.tile(color, (len(vertices), 1)).astype(np.float32)

    # Convert osu! coordinates to screen coordinates
    x, y = osu_to_ndc(osu_x, osu_y)

    # Center vertex
    vertices[0] = [x, y]
    # Circle vertices
    vertices[1:, 0] = x + radius * np.cos(angles)
    vertices[1:, 1] = y + radius * np.sin(angles)

    # Create VBOs and draw using renderer's shader program
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glEnableVertexAttribArray(renderer.position_loc)
    glVertexAttribPointer(renderer.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    vbo_colors = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
    glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
    glEnableVertexAttribArray(renderer.color_loc)
    glVertexAttribPointer(renderer.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

    # Use renderer's shader program
    glUseProgram(renderer.shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, renderer.projection_matrix.T)

    # Draw the circle
    glDrawArrays(GL_TRIANGLE_FAN, 0, len(vertices))

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])

def draw_approach_circle(osu_x, osu_y, radius, scale, renderer):
    """
    Draws the approach circle around the hit object using shaders.
    """
    scaled_radius = radius * (1 + scale * 3)
    draw_circle_outline(osu_x, osu_y, scaled_radius, color=(0.0, 0.5, 1.0, 1.0), renderer=renderer)

def draw_circle_outline(osu_x, osu_y, radius, color, renderer):
    """
    Draws an outlined circle using shaders.
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

    # Create VBOs and draw using renderer's shader program
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
    glEnableVertexAttribArray(renderer.position_loc)
    glVertexAttribPointer(renderer.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    vbo_colors = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
    glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_STATIC_DRAW)
    glEnableVertexAttribArray(renderer.color_loc)
    glVertexAttribPointer(renderer.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

    # Use renderer's shader program
    glUseProgram(renderer.shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, renderer.projection_matrix.T)

    # Draw the circle outline
    glDrawArrays(GL_LINE_LOOP, 0, len(vertices))

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])
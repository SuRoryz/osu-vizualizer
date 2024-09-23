from OpenGL.GL import *
from src.utils import osu_to_ndc, calculate_circle_radius
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT
import numpy as np

from skins.default.circle_render import draw_circle, draw_approach_circle

def draw_slider_object(hit_object, cs, approach_scale, renderer):
    """
    Draws a slider hit object with an approach circle using shaders.
    """
    x = hit_object['x']
    y = hit_object['y']
    radius = calculate_circle_radius(cs)

    # Draw approach circle
    draw_approach_circle(x, y, radius, approach_scale, renderer)

    # Draw slider path
    draw_slider_path(hit_object, renderer)

    # Draw hit circle at slider start
    draw_circle(x, y, radius, color=(0.5, 1.0, 0.5, 1.0), renderer=renderer)

def draw_slider_path(hit_object, renderer):
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

    # Draw the slider path
    glDrawArrays(GL_LINE_STRIP, 0, len(vertices))

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])

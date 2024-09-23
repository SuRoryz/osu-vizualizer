from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

def draw_spinner_object(hit_object, current_time, renderer):
    """
    Draws a spinner hit object using shaders.
    """
    start_time = hit_object['time']
    end_time = hit_object['end_time']

    if start_time <= current_time <= end_time:
        # Draw spinner background
        draw_spinner_background(renderer)

def draw_spinner_background(renderer):
    """
    Draws the spinner background as a rotating quad.
    """
    # Define spinner size and position
    center_x = OSU_PLAYFIELD_WIDTH / 2
    center_y = OSU_PLAYFIELD_HEIGHT / 2
    size = 200  # Adjust spinner size as needed

    # Define vertices in osu! coordinates
    vertices_osu = np.array([
        [center_x - size, center_y - size],
        [center_x + size, center_y - size],
        [center_x - size, center_y + size],
        [center_x + size, center_y + size]
    ], dtype=np.float32)

    colors = np.tile([0.8, 0.8, 0.8, 1.0], (4, 1)).astype(np.float32)

    # Convert to screen coordinates
    vertices = np.array([osu_to_ndc(x, y) for x, y in vertices_osu], dtype=np.float32)

    # Create VBOs
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

    # Use spinner shader program
    glUseProgram(renderer.spinner_shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, renderer.projection_matrix.T)

    # Draw the spinner quad
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])
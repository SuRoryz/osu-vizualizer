from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc
from config import CURSOR_TRAIL_LENGTH, CURSOR_TRAIL_FADE

def draw_cursor_trail(trail_points, renderer):
    """
    Draws the cursor trail with fading effect using shaders.
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

    # Create VBOs and draw using renderer's shader program
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.position_loc)
    glVertexAttribPointer(renderer.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    vbo_colors = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
    glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.color_loc)
    glVertexAttribPointer(renderer.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

    # Use renderer's shader program
    glUseProgram(renderer.shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, renderer.projection_matrix.T)

    # Draw the cursor trail
    glDrawArrays(GL_LINE_STRIP, 0, num_points)

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])

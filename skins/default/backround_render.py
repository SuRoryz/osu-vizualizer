from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_screen

def draw_background(renderer):
    """
    Draws the background using shaders.
    """
    # Use the pre-initialized background VAO and shader program
    glBindVertexArray(renderer.background_vao)
    glUseProgram(renderer.background_shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, renderer.projection_matrix.T)

    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    glBindVertexArray(0)
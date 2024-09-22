from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc
from config import CURSOR_SIZE
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

def draw_cursor(cursor_pos, cursor_color):
    """
    Draws the cursor at the given position.
    """
    osu_x = cursor_pos['x']
    osu_y = cursor_pos['y']
    ndc_x, ndc_y = osu_to_ndc(osu_x, osu_y)
    radius = CURSOR_SIZE
    num_segments = 32

    # Normalize radius for NDC
    ndc_radius_x = (radius / (OSU_PLAYFIELD_WIDTH / 2))
    ndc_radius_y = (radius / (OSU_PLAYFIELD_HEIGHT / 2))

    glColor3f(*cursor_color)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(ndc_x, ndc_y)
    for i in range(num_segments + 1):
        angle = 2 * np.pi * i / num_segments
        dx = np.cos(angle) * ndc_radius_x
        dy = np.sin(angle) * ndc_radius_y
        glVertex2f(ndc_x + dx, ndc_y + dy)
    glEnd()
from OpenGL.GL import *
from src.utils import osu_to_ndc
from config import CURSOR_TRAIL_LENGTH, CURSOR_TRAIL_FADE

def draw_cursor_trail(trail_points):
    """
    Draws the cursor trail with fading effect.
    """
    num_points = min(len(trail_points), CURSOR_TRAIL_LENGTH)
    if num_points < 2:
        return

    glBegin(GL_LINE_STRIP)
    for i in range(-num_points, 0):
        point = trail_points[i]
        ndc_x, ndc_y = osu_to_ndc(point['x'], point['y'])

        if CURSOR_TRAIL_FADE:
            alpha = (i + num_points) / num_points
        else:
            alpha = 1.0
        glColor4f(1.0, 0.0, 0.0, alpha * 0.5)
        glVertex2f(ndc_x, ndc_y)
    glEnd()
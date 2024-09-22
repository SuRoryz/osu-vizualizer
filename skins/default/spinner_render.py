from OpenGL.GL import *
from src.utils import osu_to_ndc
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

def draw_spinner_object(hit_object, current_time):
    """
    Draws a spinner hit object.
    """
    start_time = hit_object['time']
    end_time = hit_object['end_time']

    if start_time <= current_time <= end_time:
        # Spinner is active
        glColor3f(0.8, 0.8, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(-1, -1)
        glVertex2f(1, -1)
        glVertex2f(1, 1)
        glVertex2f(-1, 1)
        glEnd()
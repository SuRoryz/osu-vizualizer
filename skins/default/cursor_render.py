from OpenGL.GL import *
import numpy as np
from skins.default.circle_render import draw_circle
from src.utils import osu_to_ndc
from config import CURSOR_SIZE
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

def draw_cursor(cursor_pos, cursor_color, renderer):
    """
    Draws the cursor using shaders.
    """
    osu_x = cursor_pos['x']
    osu_y = cursor_pos['y']
    radius = CURSOR_SIZE

    # Draw cursor using renderer's shader program
    draw_circle(osu_x, osu_y, radius, color=cursor_color, renderer=renderer)
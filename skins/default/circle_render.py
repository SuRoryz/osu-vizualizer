from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc, calculate_circle_radius
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

def draw_circle_object(hit_object, cs, approach_scale):
    """
    Draws a circle hit object with an approach circle.
    """
    x = hit_object['x']
    y = hit_object['y']
    radius = calculate_circle_radius(cs)

    # Draw approach circle
    draw_approach_circle(x, y, radius, approach_scale)

    # Draw hit circle
    draw_circle(x, y, radius, color=(1, 1, 1))

def draw_circle(osu_x, osu_y, radius, color=(1, 1, 1)):
    """
    Draws a filled circle at the given osu! coordinates.
    """
    ndc_x, ndc_y = osu_to_ndc(osu_x, osu_y)
    num_segments = 64  # Adjust for circle smoothness

    # Normalize radius for NDC
    ndc_radius_x = (radius / (OSU_PLAYFIELD_WIDTH / 2))
    ndc_radius_y = (radius / (OSU_PLAYFIELD_HEIGHT / 2))

    glColor3f(*color)
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(ndc_x, ndc_y)  # Center of circle
    for i in range(num_segments + 1):
        angle = 2 * np.pi * i / num_segments
        dx = np.cos(angle) * ndc_radius_x
        dy = np.sin(angle) * ndc_radius_y
        glVertex2f(ndc_x + dx, ndc_y + dy)
    glEnd()

def draw_approach_circle(osu_x, osu_y, radius, scale):
    """
    Draws the approach circle around the hit object.
    """
    scaled_radius = radius * (1 + scale * 3)
    draw_circle_outline(osu_x, osu_y, scaled_radius, color=(0.0, 0.5, 1.0))

def draw_circle_outline(osu_x, osu_y, radius, color=(1, 1, 1)):
    """
    Draws an outlined circle at the given osu! coordinates.
    """
    ndc_x, ndc_y = osu_to_ndc(osu_x, osu_y)
    num_segments = 64  # Adjust for circle smoothness

    # Normalize radius for NDC
    ndc_radius_x = (radius / (OSU_PLAYFIELD_WIDTH / 2))
    ndc_radius_y = (radius / (OSU_PLAYFIELD_HEIGHT / 2))

    glColor3f(*color)
    glBegin(GL_LINE_LOOP)
    for i in range(num_segments):
        angle = 2 * np.pi * i / num_segments
        dx = np.cos(angle) * ndc_radius_x
        dy = np.sin(angle) * ndc_radius_y
        glVertex2f(ndc_x + dx, ndc_y + dy)
    glEnd()
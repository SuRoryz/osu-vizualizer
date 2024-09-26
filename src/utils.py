import numpy as np
import pygame
from .constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT
from OpenGL.GL import *

# Deprecated since conversion in made in projection matrix
def osu_to_ndc(osu_x, osu_y):
    """
    Converts osu! coordinates to screen coordinates (normalized to -1 to 1).
    """
    return osu_x, osu_y

def real_osu_to_ndc(osu_x, osu_y):
    """
    Converts osu! coordinates to Normalized Device Coordinates (NDC).
    """
    ndc_x = (osu_x / OSU_PLAYFIELD_WIDTH) * 2 - 1
    ndc_y = -((osu_y / OSU_PLAYFIELD_HEIGHT) * 2 - 1)
    return ndc_x, ndc_y

def calculate_circle_radius(cs):
    """
    Calculates the circle radius based on Circle Size (CS).
    """
    return (54.4 - 4.48 * cs)

def calculate_preempt(ar):
    """
    Calculates the preempt time based on Approach Rate (AR).
    """
    if ar < 5:
        preempt = 1200 + 600 * (5 - ar) / 5
    else:
        preempt = 1200 - 750 * (ar - 5) / 5
    return preempt

def calculate_hit_windows(od):
    """
    Calculates hit windows for 300, 100, and 50 based on OD.
    """
    hit_window_300 = 79.5 - 6 * od
    hit_window_100 = 139.5 - 8 * od
    hit_window_50 = 199.5 - 10 * od
    return hit_window_300, hit_window_100, hit_window_50

def load_texture(file_path):
    """
    Loads a texture from an image file and returns the texture ID.
    """
    # Use an image loading library like Pillow
    from PIL import Image
    image = Image.open(file_path)
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    img_data = image.convert("RGBA").tobytes()

    width, height = image.size

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)

    # Set texture parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glBindTexture(GL_TEXTURE_2D, 0)

    return texture_id

def surface_to_texture(surface):
    """
    Converts a pygame.Surface to an OpenGL texture.
    """
    width, height = surface.get_size()
    texture_data = pygame.image.tostring(surface, "RGBA", 1)
    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

    # Set texture parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glBindTexture(GL_TEXTURE_2D, 0)

    return texture_id, width, height

def calculate_perpendicular(p1, p2):
    """
    Calculate a unit perpendicular vector to the line segment from p1 to p2.
    """
    direction = p2 - p1
    length = np.linalg.norm(direction)
    if length == 0:
        return np.array([0.0, 0.0], dtype=np.float32)
    direction /= length
    perpendicular = np.array([-direction[1], direction[0]], dtype=np.float32)
    return perpendicular

def generate_thick_path_vertices(path, radius, segments_per_circle=16):
    """
    Generate vertices for a thick path with rounded ends.

    Parameters:
    - path: List of np.array([x, y]) points in NDC.
    - radius: Thickness radius in NDC units.
    - segments_per_circle: Number of segments to approximate semicircles.

    Returns:
    - vertices: np.array of vertices.
    """
    vertices = []
    num_points = len(path)

    if num_points == 0:
        # No points to draw
        return np.array(vertices, dtype=np.float32)

    elif num_points == 1:
        # Single point: draw a circle
        center = path[0]
        circle_vertices = create_full_circle(center, radius, segments_per_circle)
        vertices.extend(circle_vertices)

    else:
        # Generate quads for each segment
        for i in range(num_points - 1):
            p0 = path[i]
            p1 = path[i + 1]
            perpendicular = calculate_perpendicular(p0, p1)
            offset = perpendicular * radius

            # Left and Right vertices
            left = p0 + offset
            right = p0 - offset
            left_next = p1 + offset
            right_next = p1 - offset

            # Append two triangles for the quad
            vertices.extend([left, right, left_next])
            vertices.extend([right, right_next, left_next])

        # Generate semicircular caps at both ends
        # Start cap
        p_start = path[0]
        p_next = path[1]
        direction = p_next - p_start
        angle = np.arctan2(direction[1], direction[0])
        start_cap_vertices = create_semicircle(p_start, angle - np.pi / 2, radius, segments_per_circle)
        vertices.extend(start_cap_vertices)

        # End cap
        p_end = path[-1]
        p_prev = path[-2]
        direction = p_end - p_prev
        angle = np.arctan2(direction[1], direction[0])
        end_cap_vertices = create_semicircle(p_end, angle + np.pi / 2, radius, segments_per_circle)
        vertices.extend(end_cap_vertices)

    return np.array(vertices, dtype=np.float32)

def create_semicircle(center, angle, radius, segments):
    """
    Create vertices for a semicircle at a given center and orientation.

    Parameters:
    - center: np.array([x, y]) center of the semicircle.
    - angle: Orientation angle in radians.
    - radius: Radius of the semicircle.
    - segments: Number of segments to approximate the semicircle.

    Returns:
    - semicircle_vertices: List of vertices forming triangles.
    """
    semicircle_vertices = []
    start_angle = angle - np.pi / 2
    end_angle = angle + np.pi / 2
    step = (end_angle - start_angle) / segments

    # Triangle fan: center, current point, next point
    for i in range(segments):
        theta = start_angle + step * i
        theta_next = start_angle + step * (i + 1)

        x = center[0] + radius * np.cos(theta)
        y = center[1] + radius * np.sin(theta)
        x_next = center[0] + radius * np.cos(theta_next)
        y_next = center[1] + radius * np.sin(theta_next)

        semicircle_vertices.extend([
            center,
            np.array([x, y], dtype=np.float32),
            np.array([x_next, y_next], dtype=np.float32)
        ])

    return semicircle_vertices

def create_full_circle(center, radius, segments):
    """
    Create vertices for a full circle.

    Parameters:
    - center: np.array([x, y]) center of the circle.
    - radius: Radius of the circle.
    - segments: Number of segments to approximate the circle.

    Returns:
    - circle_vertices: List of vertices forming a triangle fan.
    """
    circle_vertices = []
    angle_step = 2 * np.pi / segments

    # Triangle fan: center vertex + perimeter vertices
    for i in range(segments):
        theta = i * angle_step
        x = center[0] + radius * np.cos(theta)
        y = center[1] + radius * np.sin(theta)
        next_theta = (i + 1) * angle_step
        x_next = center[0] + radius * np.cos(next_theta)
        y_next = center[1] + radius * np.sin(next_theta)

        # Triangle: center, current point, next point
        circle_vertices.extend([center, np.array([x, y], dtype=np.float32), np.array([x_next, y_next], dtype=np.float32)])

    return circle_vertices

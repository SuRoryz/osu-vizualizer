from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc
from config import CURSOR_TRAIL_LENGTH, CURSOR_TRAIL_FADE, CURSOR_SIZE

import os
from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc

# Module-level variables
shader_program = None
uniform_locations = {}

def init(renderer):
    """
    Initializes the cursor trail rendering module, loads shaders, and compiles them.
    Sets up persistent VAO and VBO for the cursor trail.
    """
    global shader_program, uniform_locations, cursor_trail_vao, cursor_trail_vbo

    # Load shader sources
    vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'cursor_trail', 'vertex.glsl')
    fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'cursor_trail', 'fragment.glsl')

    with open(vertex_shader_path, 'r') as f:
        vertex_shader_source = f.read()
    with open(fragment_shader_path, 'r') as f:
        fragment_shader_source = f.read()

    # Compile shaders
    shader_program = create_shader_program(vertex_shader_source, fragment_shader_source)

    # Get uniform locations
    uniform_locations['u_mvp_matrix'] = glGetUniformLocation(shader_program, 'u_mvp_matrix')
    uniform_locations['u_time'] = glGetUniformLocation(shader_program, 'u_time')

    # Create persistent VAO and VBO
    cursor_trail_vao = glGenVertexArrays(1)
    glBindVertexArray(cursor_trail_vao)

    cursor_trail_vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, cursor_trail_vbo)
    glBufferData(GL_ARRAY_BUFFER, 0, None, GL_DYNAMIC_DRAW)  # Allocate without data

    position_loc = glGetAttribLocation(shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

def create_shader_program(vertex_source, fragment_source):
    """
    Compiles vertex and fragment shaders and links them into a program.
    """
    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, vertex_source)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(vertex_shader).decode()
        print(f"Circle Vertex Shader compilation error: {error}")
        glDeleteShader(vertex_shader)
        return None

    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, fragment_source)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(fragment_shader).decode()
        print(f"Circle Fragment Shader compilation error: {error}")
        glDeleteShader(fragment_shader)
        return None

    program = glCreateProgram()
    glAttachShader(program, vertex_shader)
    glAttachShader(program, fragment_shader)
    glLinkProgram(program)
    if not glGetProgramiv(program, GL_LINK_STATUS):
        error = glGetProgramInfoLog(program).decode()
        print(f"Circle Shader Program linking error: {error}")
        glDeleteProgram(program)
        return None

    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return program

def draw_cursor_trail(trail_points, renderer, current_time):
    """
    Draws the cursor trail as a smooth, tapered shape that handles sharp turns and ensures continuity.
    Implements adaptive sampling and spline-based smoothing for high-quality visuals.
    Utilizes persistent VAO and VBO for performance optimization.
    """
    if len(trail_points) < 2:
        return

    # Apply Catmull-Rom spline for smooth curves
    trail_points = generate_catmull_rom_spline(trail_points[:CURSOR_TRAIL_LENGTH], num_points=8)

    # Reverse widths if trail_points are ordered from tail to head
    widths = np.linspace(CURSOR_SIZE / 2, 0.0, len(trail_points))
    widths = widths[::-1]  # Reverse to apply maximum width to the head

    vertices = []

    for i, point in enumerate(trail_points):
        x, y = osu_to_ndc(point['x'], point['y'])

        if i == len(trail_points) - 1:
            width = 0.0
        else:
            width = widths[i]

        # Calculate averaged perpendicular for smooth joins
        perp = calculate_average_perpendicular(trail_points, i)

        # Apply bevel join logic
        if i > 0 and i < len(trail_points) - 1:
            # Calculate angle between previous and current perpendiculars
            prev_perp = calculate_average_perpendicular(trail_points, i - 1)
            dot_product = np.clip(np.dot(perp, prev_perp), -1.0, 1.0)
            angle = np.arccos(dot_product)
            if angle < np.radians(30):  # Threshold angle for bevel
                # Merge the two perpendiculars to create a smooth join
                perp = (perp + prev_perp) / 2
                perp_length = np.linalg.norm(perp)
                if perp_length != 0:
                    perp = perp / perp_length

        # Offset positions
        offset = perp * width
        left_vertex = [x + offset[0], y + offset[1]]
        right_vertex = [x - offset[0], y - offset[1]]

        vertices.extend(left_vertex)
        vertices.extend(right_vertex)

    vertices = np.array(vertices, dtype=np.float32)

    # Update the persistent VBO with new vertex data
    glBindVertexArray(cursor_trail_vao)
    glBindBuffer(GL_ARRAY_BUFFER, cursor_trail_vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)

    # Use shader program
    glUseProgram(shader_program)

    # Set uniforms
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(uniform_locations['u_time'], current_time)

    # Enable blending for transparency
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Draw the cursor trail
    glDrawArrays(GL_TRIANGLE_STRIP, 0, len(vertices) // 2 * 2)  # Ensure even number of vertices

    # Disable blending if not needed elsewhere
    glDisable(GL_BLEND)

    # Unbind VAO and VBO
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

def interpolate_trail_points(trail_points, max_distance=10.0, min_distance=5.0):
    """
    Interpolates additional points between trail points to ensure smoothness.
    The number of interpolated points increases with the distance between points.
    
    :param trail_points: List of trail points with 'x' and 'y' keys.
    :param max_distance: Maximum allowed distance between points before interpolation.
    :param min_distance: Minimum distance to consider for interpolation.
    :return: List of interpolated trail points.
    """
    if len(trail_points) < 2:
        return trail_points

    interpolated = [trail_points[0]]
    for i in range(1, len(trail_points)):
        p0 = np.array([trail_points[i - 1]['x'], trail_points[i - 1]['y']])
        p1 = np.array([trail_points[i]['x'], trail_points[i]['y']])
        distance = np.linalg.norm(p1 - p0)
        if distance > max_distance:
            # Calculate number of extra points based on distance
            num_extra = int(np.ceil(distance / max_distance))
            for j in range(1, num_extra + 1):
                t = j / (num_extra + 1)
                new_point = {
                    'x': p0[0] + t * (p1[0] - p0[0]),
                    'y': p0[1] + t * (p1[1] - p0[1]),
                }
                interpolated.append(new_point)
        interpolated.append(trail_points[i])
    return interpolated

def calculate_average_perpendicular(trail_points, i):
    """
    Calculates the averaged perpendicular vector for smooth joins.
    """
    if i == 0:
        # First point, use direction to next point
        dx = trail_points[i + 1]['x'] - trail_points[i]['x']
        dy = trail_points[i + 1]['y'] - trail_points[i]['y']
    elif i == len(trail_points) - 1:
        # Last point, use direction from previous point
        dx = trail_points[i]['x'] - trail_points[i - 1]['x']
        dy = trail_points[i]['y'] - trail_points[i - 1]['y']
    else:
        # Middle points, average directions
        dx1 = trail_points[i + 1]['x'] - trail_points[i]['x']
        dy1 = trail_points[i + 1]['y'] - trail_points[i]['y']
        dx2 = trail_points[i]['x'] - trail_points[i - 1]['x']
        dy2 = trail_points[i]['y'] - trail_points[i - 1]['y']
        dx = (dx1 + dx2) / 2
        dy = (dy1 + dy2) / 2

    length = np.hypot(dx, dy)
    if length == 0:
        perp = np.array([0.0, 0.0])
    else:
        perp = np.array([-dy, dx]) / length

    return perp

def generate_catmull_rom_spline(trail_points, num_points=10):
    """
    Generates a Catmull-Rom spline from the given trail points.
    :param trail_points: List of trail points with 'x' and 'y' keys.
    :param num_points: Number of interpolated points between each pair.
    :return: List of interpolated trail points.
    """
    if len(trail_points) < 4:
        # Not enough points for Catmull-Rom, perform linear interpolation
        return interpolate_trail_points(trail_points)

    spline_points = []
    for i in range(1, len(trail_points) - 2):
        p0 = np.array([trail_points[i - 1]['x'], trail_points[i - 1]['y']])
        p1 = np.array([trail_points[i]['x'], trail_points[i]['y']])
        p2 = np.array([trail_points[i + 1]['x'], trail_points[i + 1]['y']])
        p3 = np.array([trail_points[i + 2]['x'], trail_points[i + 2]['y']])

        for t in np.linspace(0, 1, num_points):
            t2 = t * t
            t3 = t2 * t

            # Catmull-Rom spline formula
            point = 0.5 * ((2 * p1) +
                          (-p0 + p2) * t +
                          (2*p0 - 5*p1 + 4*p2 - p3) * t2 +
                          (-p0 + 3*p1 - 3*p2 + p3) * t3)
            spline_points.append({'x': point[0], 'y': point[1]})

    # Add the last two points
    spline_points.append(trail_points[-2])
    spline_points.append(trail_points[-1])

    return spline_points
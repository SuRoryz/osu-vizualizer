# skins/default/slider_render.py

import math
import os
from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc, calculate_circle_radius, generate_thick_path_vertices

# Module-level variables
slider_shader_program = None
slider_outline_shader_program = None
circle_shader_program = None
uniform_locations = {}
outline_uniform_locations = {}
circle_uniform_locations = {}

slider_path_cache = {}
slider_sampled_path_cache = {}

def init(renderer):
    """
    Initializes the slider rendering module by loading and compiling shaders.
    """
    global slider_shader_program, slider_outline_shader_program, circle_shader_program
    global uniform_locations, outline_uniform_locations, circle_uniform_locations

    # Load and compile slider shaders
    slider_vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'slider', 'vertex.glsl')
    slider_fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'slider', 'fragment.glsl')
    slider_shader_program = create_shader_program(slider_vertex_shader_path, slider_fragment_shader_path)

    # Retrieve uniform locations for slider shader
    uniform_locations['u_mvp_matrix'] = glGetUniformLocation(slider_shader_program, 'u_mvp_matrix')
    uniform_locations['u_opacity'] = glGetUniformLocation(slider_shader_program, 'u_opacity')

    # Load and compile slider outline shaders
    slider_outline_vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'slider', 'slider_outline_vertex.glsl')
    slider_outline_fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'slider', 'slider_outline_fragment.glsl')
    slider_outline_shader_program = create_shader_program(slider_outline_vertex_shader_path, slider_outline_fragment_shader_path)

    # Retrieve uniform locations for slider outline shader
    outline_uniform_locations['u_mvp_matrix'] = glGetUniformLocation(slider_outline_shader_program, 'u_mvp_matrix')
    outline_uniform_locations['u_opacity'] = glGetUniformLocation(slider_outline_shader_program, 'u_opacity')
    outline_uniform_locations['u_time'] = glGetUniformLocation(slider_outline_shader_program, 'u_time')

    # Load and compile circle shaders (for slider ball and hit circles)
    circle_vertex_shader_path = os.path.join(renderer.skin_path, 'shaders', 'circle', 'vertex.glsl')
    circle_fragment_shader_path = os.path.join(renderer.skin_path, 'shaders', 'circle', 'fragment.glsl')
    circle_shader_program = create_shader_program(circle_vertex_shader_path, circle_fragment_shader_path)

    if circle_shader_program is None:
        raise RuntimeError("Failed to create shader program for circles.")

    # Retrieve uniform locations for circle shader
    circle_uniform_locations['u_mvp_matrix'] = glGetUniformLocation(circle_shader_program, 'u_mvp_matrix')
    circle_uniform_locations['u_opacity'] = glGetUniformLocation(circle_shader_program, 'u_opacity')
    circle_uniform_locations['u_time'] = glGetUniformLocation(circle_shader_program, 'u_time')
    circle_uniform_locations['u_circle_radius'] = glGetUniformLocation(circle_shader_program, 'u_circle_radius')


def create_shader_program(vertex_path, fragment_path):
    """
    Compiles vertex and fragment shaders and links them into a program.
    """
    with open(vertex_path, 'r') as f:
        vertex_source = f.read()
    with open(fragment_path, 'r') as f:
        fragment_source = f.read()

    vertex_shader = glCreateShader(GL_VERTEX_SHADER)
    glShaderSource(vertex_shader, vertex_source)
    glCompileShader(vertex_shader)
    if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(vertex_shader).decode()
        print(f"Slider Vertex Shader compilation error: {error}")
        glDeleteShader(vertex_shader)
        return None

    fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
    glShaderSource(fragment_shader, fragment_source)
    glCompileShader(fragment_shader)
    if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
        error = glGetShaderInfoLog(fragment_shader).decode()
        print(f"Slider Fragment Shader compilation error: {error}")
        glDeleteShader(fragment_shader)
        return None

    program = glCreateProgram()
    glAttachShader(program, vertex_shader)
    glAttachShader(program, fragment_shader)
    glLinkProgram(program)
    if not glGetProgramiv(program, GL_LINK_STATUS):
        error = glGetProgramInfoLog(program).decode()
        print(f"Slider Shader Program linking error: {error}")
        glDeleteProgram(program)
        return None

    glDeleteShader(vertex_shader)
    glDeleteShader(fragment_shader)

    return program

def draw_slider_object(hit_object, cs, approach_scale, renderer, active_sliders, current_time):
    """
    Draws a slider hit object including its path, outline, and moving ball.
    """
    x = hit_object['x']
    y = hit_object['y']
    radius = calculate_circle_radius(cs)

    # Draw the slider path and its outline
    draw_slider_path(hit_object, radius, renderer, current_time)

    # Draw the hit circle with approach circle
    draw_hit_circle(hit_object, radius, renderer, approach_scale, current_time)

    cache_key = hit_object.get('time')
    sampled_path = slider_sampled_path_cache[cache_key]

    if sampled_path:
        end_point = sampled_path[-1]
        draw_end_circle(end_point['x'], end_point['y'], radius, renderer, current_time)

    # Draw the slider ball if the slider is active
    if hit_object['time'] in active_sliders:
        active_slider = active_sliders[hit_object['time']]
        ball_position = get_slider_ball_position(active_slider, current_time)
        draw_slider_ball(ball_position['x'], ball_position['y'], radius-5, renderer)

def draw_hit_circle(hit_object, radius, renderer, approach_scale, current_time):
    """
    Draws the hit circle at the slider's start position along with the approach circle.
    """
    x = hit_object['x']
    y = hit_object['y']

    if approach_scale > 0:
        draw_approach_circle(x, y, radius, approach_scale, renderer)

    # Draw hit circle
    draw_circle_with_outline(x, y, radius, renderer, current_time, opacity=1.0)

def draw_slider_path(hit_object, radius, renderer, current_time):
    """
    Renders the slider's path with an outline.
    """
    curve_points = hit_object.get('curve_points', [])
    slider_type = hit_object.get('slider_type', 'L')  # Default to linear if not specified

    # Include the starting point in the path
    start_point = {'x': hit_object['x'], 'y': hit_object['y']}
    full_curve_points = [start_point] + curve_points

    # Create a unique key for caching based on slider type and control points
    cache_key = hit_object.get('time')
    
    if cache_key in slider_path_cache:
        path = slider_path_cache[cache_key]
    else:
        path = generate_slider_path(full_curve_points, slider_type)
        slider_path_cache[cache_key] = path

    if not path:
        print(f"Warning: No path generated for slider at time {hit_object['time']}.")
        return

    if cache_key in slider_sampled_path_cache:
        sampled_path = slider_sampled_path_cache[cache_key]
    else:
        # Sample the path for rendering
        sampled_path = sample_path(path, num_samples=1000)
        slider_sampled_path_cache[cache_key] = sampled_path

    # Cache the sampled path for slider ball positioning
    hit_object['sampled_path'] = sampled_path

    # Generate vertices for the main path
    main_vertices = generate_path_vertices(sampled_path, width=radius-5)

    # Generate vertices for the outline path
    outline_vertices = generate_path_vertices(sampled_path, width=radius)

    # Create and bind VAO and VBO for main path
    vao_main, vbo_main = create_vao_vbo(main_vertices)

    # Create and bind VAO and VBO for outline path
    vao_outline, vbo_outline = create_vao_vbo(outline_vertices)

    # Render the outline first
    glUseProgram(slider_outline_shader_program)
    glUniformMatrix4fv(outline_uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(outline_uniform_locations['u_opacity'], 1)
    glUniform1f(outline_uniform_locations['u_time'], current_time)
    glBindVertexArray(vao_outline)
    glDrawArrays(GL_TRIANGLE_STRIP, 0, len(outline_vertices) // 2)
    glBindVertexArray(0)
    glUseProgram(0)

    # Render the main path
    glUseProgram(slider_shader_program)
    glUniformMatrix4fv(uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(uniform_locations['u_opacity'], 1)
    glBindVertexArray(vao_main)
    glDrawArrays(GL_TRIANGLE_STRIP, 0, len(main_vertices) // 2)
    glBindVertexArray(0)
    glUseProgram(0)

    # Clean up
    glDeleteBuffers(1, [vbo_main])
    glDeleteVertexArrays(1, [vao_main])
    glDeleteBuffers(1, [vbo_outline])
    glDeleteVertexArrays(1, [vao_outline])

def draw_end_circle(osu_x, osu_y, radius, renderer, current_time):
    """
    Draws the end circle of the slider to create a rounded end.
    
    Args:
        osu_x (float): X-coordinate in osu! space.
        osu_y (float): Y-coordinate in osu! space.
        radius (float): Radius of the end circle.
        renderer: Renderer object containing the projection matrix.
    """
    draw_circle_with_outline(osu_x, osu_y, radius, renderer, current_time, opacity=1.0)


def generate_slider_path(curve_points, slider_type):
    """
    Generates the slider path based on the slider type and control points.
    Supports linear (L), bezier (B), catmull (C), and perfect (P) types.
    """
    main_type = slider_type[0].upper()  # Consider only the first letter for main type

    if main_type == 'L':
        return generate_linear_path(curve_points)
    elif main_type == 'B':
        return generate_bezier_path(curve_points)
    elif main_type == 'C':
        return generate_catmull_path(curve_points)
    elif main_type == 'P':
        return generate_perfect_path(curve_points)
    else:
        print(f"Unsupported slider type: {slider_type}. Falling back to linear.")
        return generate_linear_path(curve_points)

def generate_linear_path(points):
    """
    Generates a linear path connecting all points sequentially.
    """
    return points

def generate_bezier_path(points, degree=3):
    """
    Generates a bezier path from control points.
    Supports quadratic (degree=2) and cubic (degree=3) bezier curves.
    """
    if len(points) < degree + 1:
        print("Insufficient points for bezier curve. Falling back to linear path.")
        return generate_linear_path(points)

    bezier_path = []
    i = 0
    while i + degree <= len(points) - 1:
        segment = points[i:i + degree + 1]
        bezier_segment = sample_bezier_segment(segment, num_samples=100)
        bezier_path.extend(bezier_segment)
        i += degree  # Move to the next set without overlapping

    # If any remaining points are left, interpolate linearly
    if i < len(points) - 1:
        segment = points[i:]
        linear_segment = linear_interpolate(segment[0], segment[1], num_samples=100)
        bezier_path.extend(linear_segment)

    return bezier_path


def generate_catmull_path(points):
    """
    Generates a Catmull-Rom spline path from control points.
    """
    if len(points) < 4:
        print("Insufficient points for Catmull-Rom spline. Falling back to linear path.")
        return generate_linear_path(points)

    catmull_path = []
    for i in range(len(points) - 3):
        p0, p1, p2, p3 = points[i:i+4]
        segment = sample_catmull_segment(p0, p1, p2, p3, num_samples=100)
        catmull_path.extend(segment)
    return catmull_path

def generate_perfect_path(points):
    """
    Generates a perfect circular arc path from control points.
    Each set of three consecutive points defines a circular arc.
    """
    if len(points) < 3:
        print("Insufficient points for perfect curve. Falling back to linear path.")
        return generate_linear_path(points)

    perfect_path = []
    i = 0
    while i + 2 < len(points):
        p0, p1, p2 = points[i:i+3]
        arc = sample_perfect_segment(p0, p1, p2, num_samples=100)
        perfect_path.extend(arc)
        i += 2  # Move to the next set, overlapping by one point for continuity

    return perfect_path

def sample_perfect_segment(p0, p1, p2, num_samples=100):
    """
    Samples a perfect circular arc defined by three points.
    """
    # Extract coordinates
    x0, y0 = p0['x'], p0['y']
    x1, y1 = p1['x'], p1['y']
    x2, y2 = p2['x'], p2['y']

    # Calculate the perpendicular bisector of p0p1
    mid1_x = (x0 + x1) / 2.0
    mid1_y = (y0 + y1) / 2.0
    if x1 - x0 != 0:
        slope1 = (y1 - y0) / (x1 - x0)
        perp_slope1 = -1 / slope1 if slope1 != 0 else None
    else:
        slope1 = None
        perp_slope1 = 0  # Perpendicular bisector is horizontal

    # Calculate the perpendicular bisector of p1p2
    mid2_x = (x1 + x2) / 2.0
    mid2_y = (y1 + y2) / 2.0
    if x2 - x1 != 0:
        slope2 = (y2 - y1) / (x2 - x1)
        perp_slope2 = -1 / slope2 if slope2 != 0 else None
    else:
        slope2 = None
        perp_slope2 = 0  # Perpendicular bisector is horizontal

    # Solve for the intersection point (center of the circle)
    center_x, center_y = None, None
    if perp_slope1 is not None and perp_slope2 is not None:
        if perp_slope1 == perp_slope2:
            # Slopes are parallel; cannot determine a unique circle
            print("Warning: Perpendicular bisectors are parallel. Cannot determine perfect curve.")
            return []
        center_x = (perp_slope1 * mid1_x - perp_slope2 * mid2_x + mid2_y - mid1_y) / (perp_slope1 - perp_slope2)
        center_y = perp_slope1 * (center_x - mid1_x) + mid1_y
    elif perp_slope1 is None:
        # First bisector is vertical
        center_x = mid1_x
        if perp_slope2 is not None:
            center_y = perp_slope2 * (center_x - mid2_x) + mid2_y
        else:
            # Both bisectors are horizontal
            print("Warning: Both perpendicular bisectors are horizontal. Cannot determine perfect curve.")
            return []
    elif perp_slope2 is None:
        # Second bisector is vertical
        center_x = mid2_x
        if perp_slope1 is not None:
            center_y = perp_slope1 * (center_x - mid1_x) + mid1_y
        else:
            # Both bisectors are horizontal
            print("Warning: Both perpendicular bisectors are horizontal. Cannot determine perfect curve.")
            return []
    else:
        print("Warning: Unable to determine circle center for perfect curve.")
        return []

    # Calculate radius
    radius = math.hypot(center_x - x0, center_y - y0)

    # Calculate start and end angles
    start_angle = math.atan2(y0 - center_y, x0 - center_x)
    end_angle = math.atan2(y2 - center_y, x2 - center_x)

    # Determine the direction of the arc (clockwise or counter-clockwise)
    # Calculate the cross product to determine the direction
    cross = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
    direction = 1 if cross > 0 else -1  # 1 for CCW, -1 for CW

    # Calculate angle difference
    angle_diff = end_angle - start_angle
    if direction == 1:
        if angle_diff <= 0:
            angle_diff += 2 * math.pi
    else:
        if angle_diff >= 0:
            angle_diff -= 2 * math.pi

    # Generate points along the arc
    angles = np.linspace(start_angle, start_angle + angle_diff, num_samples)
    arc = [{'x': float(center_x + radius * math.cos(angle)),
            'y': float(center_y + radius * math.sin(angle))} for angle in angles]

    return arc

def sample_bezier_segment(control_points, num_samples=100):
    """
    Samples a bezier curve segment defined by control points.
    """
    degree = len(control_points) - 1
    if degree == 1:
        # Linear
        return linear_interpolate(control_points[0], control_points[1], num_samples)
    elif degree == 2:
        # Quadratic bezier
        return quadratic_bezier(control_points, num_samples)
    elif degree == 3:
        # Cubic bezier
        return cubic_bezier(control_points, num_samples)
    else:
        print(f"Unsupported bezier degree: {degree}.")
        return []

def sample_catmull_segment(p0, p1, p2, p3, num_samples=100):
    """
    Samples a Catmull-Rom spline segment.
    """
    return [{'x': 0.5 * ((2 * p1['x']) +
                        (-p0['x'] + p2['x']) * t +
                        (2*p0['x'] - 5*p1['x'] + 4*p2['x'] - p3['x']) * t**2 +
                        (-p0['x'] + 3*p1['x'] - 3*p2['x'] + p3['x']) * t**3),
             'y': 0.5 * ((2 * p1['y']) +
                        (-p0['y'] + p2['y']) * t +
                        (2*p0['y'] - 5*p1['y'] + 4*p2['y'] - p3['y']) * t**2 +
                        (-p0['y'] + 3*p1['y'] - 3*p2['y'] + p3['y']) * t**3)} for t in np.linspace(0, 1, num_samples)]

def sample_path(path, num_samples=1000):
    """
    Samples the entire path uniformly based on the number of samples.
    Currently assumes the path is already sufficiently sampled.
    """
    # If the path already has the desired number of samples, return as is
    if len(path) >= num_samples:
        return path[:num_samples]

    # Otherwise, interpolate between existing points to reach the desired number
    interpolated_path = []
    total_segments = len(path) - 1
    if total_segments == 0:
        return path

    samples_per_segment = max(1, num_samples // total_segments)
    for i in range(total_segments):
        p_start = path[i]
        p_end = path[i + 1]
        segment = linear_interpolate(p_start, p_end, samples_per_segment)
        interpolated_path.extend(segment)
    # Trim any excess samples
    return interpolated_path[:num_samples]

def generate_path_vertices(sampled_path, width):
    """
    Generates vertex data for rendering the slider path with given width.
    Uses a triangle strip to create a thick line.
    """
    vertices = []
    num_points = len(sampled_path)
    if num_points < 2:
        return np.array(vertices, dtype=np.float32)

    for i in range(num_points - 1):
        p1 = osu_to_ndc(sampled_path[i]['x'], sampled_path[i]['y'])
        p2 = osu_to_ndc(sampled_path[i + 1]['x'], sampled_path[i + 1]['y'])

        # Calculate the direction vector
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        dx /= length
        dy /= length

        # Calculate the perpendicular vector for width
        perp_x = -dy
        perp_y = dx

        # Offset points for thick line
        offset_x = perp_x * width
        offset_y = perp_y * width

        # Two vertices per segment
        vertices.extend([p1[0] + offset_x, p1[1] + offset_y])
        vertices.extend([p1[0] - offset_x, p1[1] - offset_y])

    return np.array(vertices, dtype=np.float32)

def calculate_slider_width(hit_object, cs):
    """
    Calculates the slider width based on the slider's circle size (cs).
    """
    cs = hit_object.get('cs', 4.0)  # Default cs if not specified
    return calculate_circle_radius(cs) * 1.5  # Adjust multiplier as needed

def create_vao_vbo(vertices):
    """
    Creates and binds a VAO and VBO for the given vertices.
    """
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Assuming shader uses layout(location = 0) for position
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, None)

    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)

    return vao, vbo

def get_slider_ball_position(slider, current_time):
    """
    Calculates the slider ball's current position based on the elapsed time.
    """
    start_time = slider['start_time']
    end_time = slider['end_time']
    slider_duration = end_time - start_time
    elapsed_time = current_time - start_time

    if slider_duration <= 0:
        t = 1.0
    else:
        t = elapsed_time / slider_duration

    t = max(0.0, min(t, 1.0))  # Clamp between 0 and 1

    cache_key = slider['object'].get('time')

    # Determine the total number of slides (repeats)
    slides = slider.get('slides', 1)
    
    path = slider_sampled_path_cache[cache_key]

    if not path:
        return {'x': slider['object']['x'], 'y': slider['object']['y']}

    # Calculate the position along the path
    path_progress = t * slides
    loop = int(path_progress)
    progress = path_progress - loop

    # Handle multiple slides
    progress = progress % 1.0

    # Calculate the index in the sampled path
    index = int(progress * (len(path) - 1))
    index = min(index, len(path) - 2)

    p1 = path[index]
    p2 = path[index + 1]
    local_t = (progress * (len(path) - 1)) - index

    x = p1['x'] + (p2['x'] - p1['x']) * local_t
    y = p1['y'] + (p2['y'] - p1['y']) * local_t

    return {'x': x, 'y': y}

def draw_slider_ball(osu_x, osu_y, radius, renderer):
    """
    Draws the slider ball at the specified position.
    """
    num_segments = 32
    theta = np.linspace(0, 2 * np.pi, num_segments, endpoint=False)
    vertices = np.zeros((num_segments, 2), dtype=np.float32)
    x_ndc, y_ndc = osu_to_ndc(osu_x, osu_y)
    vertices[:, 0] = x_ndc + radius * np.cos(theta)
    vertices[:, 1] = y_ndc + radius * np.sin(theta)

    # Create VAO and VBO
    vao, vbo = create_vao_vbo(vertices.flatten())

    # Use circle shader program
    glUseProgram(circle_shader_program)

    # Set uniforms
    glUniformMatrix4fv(circle_uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(circle_uniform_locations['u_opacity'], 0.25)

    # Bind VAO and draw
    glBindVertexArray(vao)
    glDrawArrays(GL_TRIANGLE_FAN, 0, num_segments)
    glBindVertexArray(0)

    # Clean up
    glUseProgram(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])

def draw_approach_circle(osu_x, osu_y, radius, scale, renderer):
    """
    Draws the approach circle around the hit object.
    """
    scaled_radius = radius * (1 + scale * 3)
    draw_circle_outline(osu_x, osu_y, scaled_radius, renderer)

def draw_circle_with_outline(osu_x, osu_y, radius, renderer, current_time, opacity=0.2):
    """
    Draws a circle with the specified visual effects.
    """
    num_segments = 64
    theta = np.linspace(0, 2 * np.pi, num_segments, endpoint=False)
    vertices = np.zeros((num_segments, 2), dtype=np.float32)
    x_ndc, y_ndc = osu_to_ndc(osu_x, osu_y)
    vertices[:, 0] = x_ndc + radius * np.cos(theta)
    vertices[:, 1] = y_ndc + radius * np.sin(theta)

    # Create VAO and VBO
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Enable vertex attribute
    position_loc = glGetAttribLocation(circle_shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(circle_shader_program)

    # Set uniforms
    glUniformMatrix4fv(circle_uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(circle_uniform_locations['u_time'], current_time)
    glUniform1f(circle_uniform_locations['u_circle_radius'], radius)
    glUniform1f(circle_uniform_locations['u_opacity'], opacity)

    # Draw the circle
    glDrawArrays(GL_TRIANGLE_FAN, 0, num_segments)

    # Draw the white outline
    draw_circle_outline(osu_x, osu_y, radius, renderer)

    # Draw the smaller white circle in the center
    draw_small_circle(osu_x, osu_y, radius * 0.25, renderer)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])

def draw_circle_outline(osu_x, osu_y, radius, renderer):
    """
    Draws a thin white outline around the circle.
    """
    num_segments = 64
    theta = np.linspace(0, 2 * np.pi, num_segments, endpoint=False)
    vertices = np.zeros((num_segments, 2), dtype=np.float32)
    x_ndc, y_ndc = osu_to_ndc(osu_x, osu_y)
    vertices[:, 0] = x_ndc + radius * np.cos(theta)
    vertices[:, 1] = y_ndc + radius * np.sin(theta)

    # Create VAO and VBO
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Enable vertex attribute
    position_loc = glGetAttribLocation(circle_shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(circle_shader_program)

    # Set uniforms
    glUniformMatrix4fv(circle_uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)

    # Draw outline
    glLineWidth(2.0)
    glUniform1f(circle_uniform_locations['u_opacity'], 1.0)
    glDrawArrays(GL_LINE_LOOP, 0, num_segments)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])

def draw_small_circle(osu_x, osu_y, radius, renderer):
    """
    Draws a smaller white circle in the center.
    """
    num_segments = 64
    theta = np.linspace(0, 2 * np.pi, num_segments, endpoint=False)
    vertices = np.zeros((num_segments, 2), dtype=np.float32)
    x_ndc, y_ndc = osu_to_ndc(osu_x, osu_y)
    vertices[:, 0] = x_ndc + radius * np.cos(theta)
    vertices[:, 1] = y_ndc + radius * np.sin(theta)

    # Create VAO and VBO
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    # Enable vertex attribute
    position_loc = glGetAttribLocation(circle_shader_program, 'a_position')
    glEnableVertexAttribArray(position_loc)
    glVertexAttribPointer(position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    # Use shader program
    glUseProgram(circle_shader_program)

    # Set uniforms
    glUniformMatrix4fv(circle_uniform_locations['u_mvp_matrix'], 1, GL_FALSE, renderer.projection_matrix.T)
    glUniform1f(circle_uniform_locations['u_opacity'], 1.0)  # Full opacity

    # Draw the small circle
    glDrawArrays(GL_TRIANGLE_FAN, 0, num_segments)

    # Clean up
    glDisableVertexAttribArray(position_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(1, [vbo])
    glDeleteVertexArrays(1, [vao])

def linear_interpolate(p0, p1, num_samples=100):
    """
    Linearly interpolates between two points.

    Args:
        p0 (dict): The starting point with 'x' and 'y' keys.
        p1 (dict): The ending point with 'x' and 'y' keys.
        num_samples (int): Number of samples to generate along the line.

    Returns:
        list of dict: List of sampled points along the line.
    """
    # Generate 'num_samples' evenly spaced values between 0 and 1
    t = np.linspace(0, 1, num_samples, endpoint=True)
    
    # Compute interpolated x and y coordinates
    x = p0['x'] + (p1['x'] - p0['x']) * t
    y = p0['y'] + (p1['y'] - p0['y']) * t
    
    # Combine x and y into a list of dictionaries
    return [{'x': xi, 'y': yi} for xi, yi in zip(x, y)]

def quadratic_bezier(control_points, num_samples=100):
    """
    Samples a quadratic Bezier curve defined by three control points.

    Args:
        control_points (list of dict): List containing three control points, each with 'x' and 'y' keys.
        num_samples (int): Number of samples to generate along the curve.

    Returns:
        list of dict: List of sampled points along the quadratic Bezier curve.
    """
    if len(control_points) != 3:
        print("Error: Quadratic Bezier requires exactly 3 control points.")
        return []
    
    p0, p1, p2 = control_points
    
    # Generate 'num_samples' evenly spaced values between 0 and 1
    t = np.linspace(0, 1, num_samples, endpoint=True)
    
    # Compute the Bernstein polynomials for quadratic Bezier
    B0 = (1 - t) ** 2
    B1 = 2 * (1 - t) * t
    B2 = t ** 2
    
    # Calculate interpolated x and y coordinates
    x = B0 * p0['x'] + B1 * p1['x'] + B2 * p2['x']
    y = B0 * p0['y'] + B1 * p1['y'] + B2 * p2['y']
    
    # Combine x and y into a list of dictionaries
    return [{'x': xi, 'y': yi} for xi, yi in zip(x, y)]

def cubic_bezier(control_points, num_samples=100):
    """
    Samples a cubic Bezier curve defined by four control points.

    Args:
        control_points (list of dict): List containing four control points, each with 'x' and 'y' keys.
        num_samples (int): Number of samples to generate along the curve.

    Returns:
        list of dict: List of sampled points along the cubic Bezier curve.
    """
    if len(control_points) != 4:
        print("Error: Cubic Bezier requires exactly 4 control points.")
        return []
    
    p0, p1, p2, p3 = control_points
    
    # Generate 'num_samples' evenly spaced values between 0 and 1
    t = np.linspace(0, 1, num_samples, endpoint=True)
    
    # Compute the Bernstein polynomials for cubic Bezier
    B0 = (1 - t) ** 3
    B1 = 3 * (1 - t) ** 2 * t
    B2 = 3 * (1 - t) * t ** 2
    B3 = t ** 3
    
    # Calculate interpolated x and y coordinates
    x = B0 * p0['x'] + B1 * p1['x'] + B2 * p2['x'] + B3 * p3['x']
    y = B0 * p0['y'] + B1 * p1['y'] + B2 * p2['y'] + B3 * p3['y']
    
    # Combine x and y into a list of dictionaries
    return [{'x': xi, 'y': yi} for xi, yi in zip(x, y)]

import math
import random
import glfw
from OpenGL.GL import *
import os
import time

import numpy as np
from scipy.interpolate import CubicSpline

from src.renderer import Renderer
from src.beatmap import Beatmap
from src.replay import ReplayData
from src.utils import calculate_circle_radius, calculate_preempt, calculate_hit_windows
from src.audio_player import AudioPlayer
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT, PLAYFIELD_MARGIN_LEFT, PLAYFIELD_MARGIN_RIGHT, PLAYFIELD_MARGIN_TOP, PLAYFIELD_MARGIN_BOTTOM

from osrparse.replay import Mod, Key
from config import *

import pygame

def initialize_window(width=1920, height=1080, title="OSU! Replay Visualizer", renderer=None):
    if not glfw.init():
        raise Exception("glfw cannot be initialized!")

    # Set OpenGL version to 3.3
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(width, height, title, None, None)
    if not window:
        glfw.terminate()
        raise Exception("glfw window cannot be created!")

    glfw.make_context_current(window)
    glfw.set_window_size_callback(window, window_resize_callback)
    window_resize_callback(window, width, height)
    glfw.swap_interval(1)  # Enable V-sync

    # Enable blending
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    return window

def window_resize_callback(window, width, height):
    playfield_width = OSU_PLAYFIELD_WIDTH + PLAYFIELD_MARGIN_LEFT + PLAYFIELD_MARGIN_RIGHT
    playfield_height = OSU_PLAYFIELD_HEIGHT + PLAYFIELD_MARGIN_TOP + PLAYFIELD_MARGIN_BOTTOM
    playfield_ratio = playfield_width / playfield_height
    window_ratio = width / height

    if window_ratio > playfield_ratio:
        viewport_width = int(height * playfield_ratio)
        viewport_height = height
        viewport_x = int((width - viewport_width) / 2)
        viewport_y = 0
    else:
        viewport_width = width
        viewport_height = int(width / playfield_ratio)
        viewport_x = 0
        viewport_y = int((height - viewport_height) / 2)
    glViewport(viewport_x, viewport_y, viewport_width, viewport_height)

def load_beatmap(beatmap_path):
    beatmap = Beatmap(beatmap_path)
    return beatmap

def load_replay(replay_path, beatmap_md5):
    replay_data = ReplayData(replay_path)
    if not replay_data.validate_beatmap(beatmap_md5):
        print("Replay does not match the beatmap.")
        return None
    return replay_data

def adjust_for_mods(beatmap, replay_data):
    mods = replay_data.replay.mods
    if mods & Mod.HardRock:
        print("Hard Rock mod detected: Adjusting beatmap.")
        beatmap.apply_hard_rock_mod()
    return mods

def start_audio_playback(audio_file_path):
    audio_player = AudioPlayer(audio_file_path)
    audio_player.play()
    while audio_player.start_time is None:
        time.sleep(0.001)
    return audio_player.start_time

def generate_auto_replay(beatmap, playstyle, dancing_degree, alternate_curve_direction=False):
    """
    Generates cursor positions for the autoplay with the selected playstyle.
    """
    cursor_data = []

    if playstyle == 'Auto':
        cursor_data = generate_auto_play_cursor_data(beatmap)
    elif playstyle == 'Dancer':
        cursor_data = generate_dancer_cursor_data(beatmap, dancing_degree, alternate_curve_direction)
    else:
        raise ValueError("Invalid playstyle.")

    # Create a dummy ReplayData object
    replay_data = ReplayData.__new__(ReplayData)
    replay_data.replay_events = []  # Not used in this context
    replay_data.cursor_data = cursor_data  # Store generated cursor data

    return replay_data

def generate_auto_play_cursor_data(beatmap):
    """
    Generates cursor data for the Auto playstyle.
    """
    cursor_data = []
    for obj in beatmap.hit_objects:
        time = obj['time']
        x = obj['x']
        y = obj['y']

        if obj['object_name'] == 'circle':
            # Hit circle
            cursor_data.append({
                'time': time - 36,
                'x': x,
                'y': y,
                'keys': 1
            })
        elif obj['object_name'] == 'slider':
            # Slider
            slider_duration = obj['slider_duration']
            num_points = int(slider_duration / 10)  # Point every 10 ms
            for i in range(num_points + 1):
                progress = i / num_points
                interp_time = obj['time'] + progress * slider_duration
                position = get_slider_position_at(obj, progress)
            
                cursor_data.append({
                    'time': interp_time,
                    'x': position['x'],
                    'y': position['y'],
                    'keys': 1  # Simulate holding the key during slider
                })
        elif obj['object_name'] == 'spinner':
            # Spinner
            # Keep the cursor at the center of the playfield
            cursor_data.append({
                'time': time - 36,
                'x': OSU_PLAYFIELD_WIDTH / 2,
                'y': OSU_PLAYFIELD_HEIGHT / 2,
                'keys': 1
            })
    return cursor_data

def compute_angle(x1, y1, x2, y2):
    """
    Computes the absolute angle in degrees between two vectors (x1, y1) and (x2, y2).
    """
    dot = x1 * x2 + y1 * y2
    det = x1 * y2 - y1 * x2
    angle = math.atan2(det, dot) * 180 / math.pi
    return abs(angle)

def generate_dancer_cursor_data(beatmap, dancing_degree, alternate_curve_direction):
    """
    Generates cursor data for the Dancer playstyle with smooth curves between hit objects.
    """
    cursor_data = []
    previous_obj = None
    previous_time = None
    previous_end_position = None
    curve_direction = 1  # 1 for one direction, -1 for the opposite
    random.seed(0)  # Optional: Set seed for reproducibility

    # Starting position and time
    if beatmap.hit_objects:
        first_obj = beatmap.hit_objects[0]
        time = first_obj['time']
        x = first_obj['x']
        y = first_obj['y']
        move_start_time = time - 1000  # Start 1 second before the first object
        previous_time = move_start_time
        previous_x = x
        previous_y = y
        cursor_data.append({
            'time': move_start_time,
            'x': x,
            'y': y,
            'keys': 0
        })

    for i, obj in enumerate(beatmap.hit_objects):
        time = obj['time']
        x = obj['x']
        y = obj['y']

        # Determine the start position for the new curve
        if previous_obj and previous_obj['object_name'] == 'slider':
            # Start from the end position of the slider
            start_x, start_y = previous_end_position['x'], previous_end_position['y']
        elif previous_obj:
            start_x, start_y = previous_x, previous_y
        else:
            start_x, start_y = x, y  # For the first object

        # Calculate time difference
        time_diff = time - previous_time
        if time_diff <= 0:
            time_diff = 1  # Avoid division by zero or negative values

        # Calculate number of points based on desired interval
        desired_point_interval = 2  # Time in milliseconds between points
        num_points = max(int(time_diff / desired_point_interval), 1)

        # Calculate angle difference for curve direction alternation
        if alternate_curve_direction and previous_obj and i < len(beatmap.hit_objects) - 1:
            next_obj = beatmap.hit_objects[i + 1]
            # Vector from previous to current
            vec1_x = x - start_x
            vec1_y = y - start_y
            # Vector from current to next
            vec2_x = next_obj['x'] - x
            vec2_y = next_obj['y'] - y
            angle_diff = compute_angle(vec1_x, vec1_y, vec2_x, vec2_y)
            if angle_diff < 30:
                curve_direction *= -1  # Alternate direction
            # If angle_diff >= threshold, keep the current direction
        elif alternate_curve_direction:
            # If not enough objects to compare, keep current direction
            curve_direction = 1

        for t in range(num_points):
            t_normalized = t / num_points
            interp_time = previous_time + t_normalized * time_diff

            # Calculate offset for control point to create a smooth curve
            # Offset is perpendicular to the line between start and end point
            dx = y - start_y
            dy = start_x - x  # Perpendicular direction
            length = (dx ** 2 + dy ** 2) ** 0.5
            if length != 0:
                dx /= length
                dy /= length
            else:
                dx, dy = 0, 0

            offset = dancing_degree * length * curve_direction  # Adjust magnitude and direction
            # Define two control points for the cubic Bézier curve
            # Control Point 1: Positioned at 1/3 along the line from start to end, offset perpendicular
            control1_x = start_x + (x - start_x) / 3 + dx * offset
            control1_y = start_y + (y - start_y) / 3 + dy * offset

            # Control Point 2: Positioned at 2/3 along the line from start to end, offset perpendicular
            control2_x = start_x + 2 * (x - start_x) / 3 + dx * offset
            control2_y = start_y + 2 * (y - start_y) / 3 + dy * offset

            # Compute the cubic Bézier curve points
            bezier_x = ((1 - t_normalized) ** 3 * start_x +
                        3 * (1 - t_normalized) ** 2 * t_normalized * control1_x +
                        3 * (1 - t_normalized) * t_normalized ** 2 * control2_x +
                        t_normalized ** 3 * x)

            bezier_y = ((1 - t_normalized) ** 3 * start_y +
                        3 * (1 - t_normalized) ** 2 * t_normalized * control1_y +
                        3 * (1 - t_normalized) * t_normalized ** 2 * control2_y +
                        t_normalized ** 3 * y)

            cursor_data.append({
                'time': interp_time,
                'x': bezier_x,
                'y': bezier_y,
                'keys': 0  # No key press during movement
            })

        # Hold key during hit object and keep cursor moving
        key_hold_duration = 20  # milliseconds for circles
        key_release_time = time + key_hold_duration

        # Generate points during key hold duration
        time_diff = key_release_time - time
        num_points = max(int(time_diff / desired_point_interval), 1)
        for t in range(num_points):
            t_normalized = t / num_points
            interp_time = time + t_normalized * time_diff
            cursor_data.append({
                'time': interp_time,
                'x': x,
                'y': y,
                'keys': Key.K1.value  # Keep key pressed
            })

        # Release the key
        cursor_data.append({
            'time': key_release_time,
            'x': x,
            'y': y,
            'keys': 0
        })

        if obj['object_name'] == 'slider':
            slider_duration = obj['slider_duration']
            num_slider_points = max(int(slider_duration / desired_point_interval), 1)
            for i in range(num_slider_points + 1):
                progress = i / num_slider_points
                interp_time = obj['time'] + progress * slider_duration
                position = get_slider_position_at(obj, progress)
                cursor_data.append({
                    'time': interp_time,
                    'x': position['x'],
                    'y': position['y'],
                    'keys': Key.K1.value  # Keep key pressed during slider
                })
            # Release the key at the end of the slider
            key_release_time = obj['time'] + slider_duration + 20  # Hold key slightly after slider ends
            cursor_data.append({
                'time': key_release_time,
                'x': position['x'],
                'y': position['y'],
                'keys': 0  # Release key
            })
            # Update previous time and position
            previous_time = key_release_time
            previous_x = position['x']
            previous_y = position['y']
            previous_end_position = position
        else:
            previous_end_position = None
            previous_x, previous_y = x, y
            previous_time = key_release_time

        previous_obj = obj

    return cursor_data

def get_slider_position_at(slider_obj, progress):
    """
    Calculates the cursor position along the slider's path at the given progress (0 to 1).
    """
    # For simplicity, we'll assume linear sliders
    if slider_obj['slider_type'] == 'L':
        start_x, start_y = slider_obj['x'], slider_obj['y']
        end_point = slider_obj['curve_points'][-1]
        end_x, end_y = end_point['x'], end_point['y']
        x = start_x + (end_x - start_x) * progress
        y = start_y + (end_y - start_y) * progress
        return {'x': x, 'y': y}
    elif slider_obj['slider_type'] == 'P':
        # Perfect circle slider
        # We need at least two control points (start, control, end)
        if len(slider_obj['curve_points']) < 1:
            # Not enough points to define a circle
            return {'x': slider_obj['x'], 'y': slider_obj['y']}

        start_x, start_y = slider_obj['x'], slider_obj['y']
        control_point = slider_obj['curve_points'][0]
        end_point = slider_obj['curve_points'][-1]
        x1, y1 = start_x, start_y
        x2, y2 = control_point['x'], control_point['y']
        x3, y3 = end_point['x'], end_point['y']

        # Calculate the circle center and radius
        circle = calculate_circle(x1, y1, x2, y2, x3, y3)
        if circle is None:
            # The points are colinear; treat as linear slider
            x = x1 + (x3 - x1) * progress
            y = y1 + (y3 - y1) * progress
            return {'x': x, 'y': y}

        h, k, r = circle

        # Calculate angles
        angle1 = math.atan2(y1 - k, x1 - h)
        angle2 = math.atan2(y3 - k, x3 - h)

        # Determine the direction of the arc
        # Check if the control point is to the left or right of the line from start to end
        direction = determine_arc_direction(x1, y1, x2, y2, x3, y3)

        # Ensure angle progression in the correct direction
        if direction == 'clockwise':
            if angle2 > angle1:
                angle2 -= 2 * math.pi
            angle = angle1 + progress * (angle2 - angle1)
        else:
            if angle2 < angle1:
                angle2 += 2 * math.pi
            angle = angle1 + progress * (angle2 - angle1)

        # Calculate position on the circle at the given angle
        x = h + r * math.cos(angle)
        y = k + r * math.sin(angle)
        return {'x': x, 'y': y}

    else:
        # For other slider types, default to linear
        start_x, start_y = slider_obj['x'], slider_obj['y']
        end_point = slider_obj['curve_points'][-1]
        end_x, end_y = end_point['x'], end_point['y']
        x = start_x + (end_x - start_x) * progress
        y = start_y + (end_y - start_y) * progress
        return {'x': x, 'y': y}
    
def main():
    # Initialize the window
    window = initialize_window()

    # Initialize resources
    resources = load_resources(window)

    # Start audio playback
    start_time = start_audio_playback(resources['audio_file_path'])

    # Initialize game state
    game_state = initialize_game_state(resources, start_time)

    # Main render loop
    while not glfw.window_should_close(window):
        # Poll for and process events
        glfw.poll_events()

        # Process user input and adjust settings if necessary
        process_events(window, game_state)

        # Update game state
        update_game_state(game_state)

        # Render the current frame
        render_frame(window, game_state)

    # Cleanup and terminate
    cleanup(window, game_state['renderer'])

def load_resources(window):
    resources = {}
    # Load the beatmap
    beatmap_path = input("Enter the path to the beatmap (.osu) file: ")
    beatmap = Beatmap(beatmap_path)
    beatmap_md5 = beatmap.get_md5_hash()

    # Load the replay or generate an auto replay
    replay_option = input("Enter the path to the replay (.osr) file or type 'auto' for autoplay: ")

    if replay_option.lower() == 'auto':
        # Prompt for playstyle
        print("Select playstyle:")
        print("1. Auto")
        print("2. Dancer")
        playstyle_choice = input("Enter the number of the playstyle: ")

        if playstyle_choice == '1':
            playstyle = 'Auto'
            dancing_degree = 0.0
            apply_smoothing = False
            alternate_curve_direction = False
        elif playstyle_choice == '2':
            playstyle = 'Dancer'
            dancing_degree = float(input("Enter dancing degree (0.0 to 1.0): "))
            apply_smoothing = True
            curve_direction_choice = input("Should the curves alternate direction? (yes/no): ").lower()
            alternate_curve_direction = curve_direction_choice in ['yes', 'y']
        else:
            print("Invalid playstyle choice.")
            glfw.terminate()
            return

        mods = 0  # No mods by default
        replay_data = generate_auto_replay(beatmap, playstyle, dancing_degree, alternate_curve_direction)
    else:
        # Load the replay
        replay_path = replay_option
        replay_data = ReplayData(replay_path)
        if not replay_data.validate_beatmap(beatmap_md5):
            print("Replay does not match the beatmap.")
            glfw.terminate()
            return
        mods = replay_data.replay.mods
        apply_smoothing = True

        # Adjust beatmap for mods
        if mods & Mod.HardRock:
            beatmap.apply_hard_rock_mod()

    # Get difficulty settings
    cs = beatmap.get_circle_size()
    ar = beatmap.get_approach_rate()
    od = beatmap.get_overall_difficulty()
    preempt = calculate_preempt(ar)

    # Calculate hit windows
    hit_window_300, hit_window_100, hit_window_50 = calculate_hit_windows(od)

    # Get the audio file path
    audio_filename = beatmap.general.get('AudioFilename', None)
    if audio_filename is None:
        print("Audio file not specified in the beatmap.")
        glfw.terminate()
        return
    audio_file_path = os.path.join(os.path.dirname(beatmap_path), audio_filename)

    # Initialize the renderer
    window_width, window_height = glfw.get_framebuffer_size(glfw.get_current_context())
    renderer = Renderer(window, window_width, window_height)

    resources['beatmap'] = beatmap
    resources['replay_data'] = replay_data
    resources['mods'] = mods
    resources['apply_smoothing'] = apply_smoothing
    resources['cs'] = float(cs)
    resources['ar'] = float(ar)
    resources['od'] = float(od)
    resources['preempt'] = preempt
    resources['hit_windows'] = (hit_window_300, hit_window_100, hit_window_50)
    resources['audio_file_path'] = audio_file_path
    resources['renderer'] = renderer
    resources['option'] = replay_option

    return resources

def initialize_game_state(resources, start_time):
    game_state = {}
    game_state['start_time'] = start_time
    game_state['adjusted_start_time'] = start_time
    game_state['audio_offset'] = 0

    # Initialize cursor data
    replay_data = resources['replay_data']
    mods = resources['mods']
    apply_smoothing = resources['apply_smoothing']

    if hasattr(replay_data, 'cursor_data'):
        cursor_data = replay_data.cursor_data
    else:
        cursor_data = replay_data.get_cursor_positions(mods)

    # Apply offset for replays
    OFFSET = 300
    if resources.get('option') != "auto":
        for event in cursor_data:
            event['time'] -= OFFSET

    game_state['cursor_data'] = cursor_data
    game_state['cursor_trail'] = []
    game_state['current_time'] = 0
    game_state['previous_key'] = 0
    game_state['hitted_objects'] = {}
    game_state['active_sliders'] = {}
    game_state['score'] = {
        'score': 0,
        'total_score': 0,
        'total_hits': 0,
        'combo': 0,
        'accuracy': 0
    }
    game_state['hp'] = 1.0  # Start with full HP
    game_state['renderer'] = resources['renderer']
    game_state['beatmap'] = resources['beatmap']
    game_state['apply_smoothing'] = apply_smoothing
    game_state['hit_windows'] = resources['hit_windows']
    game_state['preempt'] = resources['preempt']
    game_state['cs'] = resources['cs']
    game_state['mods'] = resources['mods']
    game_state['cursor_pos'] = None

    # Initialize audio player
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()

    game_state['hitsound'] = pygame.mixer.Sound('default_assets/hitsound.wav')
    game_state['miss_sound'] = pygame.mixer.Sound('default_assets/miss_sound.wav')

    # Setup key callback for offset adjustment
    def key_callback(window, key, scancode, action, mods):
        nonlocal game_state
        if action == glfw.PRESS or action == glfw.REPEAT:
            if key == glfw.KEY_UP:
                game_state['audio_offset'] += 10  # Increase offset by 10 ms
                print(f"Audio Offset: {game_state['audio_offset']} ms")
            elif key == glfw.KEY_DOWN:
                game_state['audio_offset'] -= 10  # Decrease offset by 10 ms
                print(f"Audio Offset: {game_state['audio_offset']} ms")

    glfw.set_key_callback(glfw.get_current_context(), key_callback)

    return game_state

def process_events(window, game_state):
    # Currently handling audio offset adjustment in key_callback
    pass  # Additional event processing can be added here if needed

def update_game_state(game_state):
    current_time = (glfw.get_time() * 1000) - (game_state['start_time'] - game_state['audio_offset'])
    game_state['current_time'] = current_time

    # Get cursor position
    cursor_pos = interpolate_cursor_position(game_state['cursor_data'], current_time, game_state['apply_smoothing'])
    game_state['cursor_pos'] = cursor_pos

    if cursor_pos:
        # Update cursor trail
        update_cursor_trail(game_state, cursor_pos)

        # Handle input and hit detection
        handle_input_and_hits(game_state)

def update_cursor_trail(game_state, cursor_pos):
    cursor_trail = game_state['cursor_trail']
    cursor_trail.append({'x': cursor_pos['x'], 'y': cursor_pos['y']})

    # Limit the length of the cursor trail if needed
    if len(cursor_trail) > CURSOR_TRAIL_LENGTH:
        cursor_trail = cursor_trail[-CURSOR_TRAIL_LENGTH:]

    game_state['cursor_trail'] = cursor_trail

def handle_input_and_hits(game_state):
    current_time = game_state['current_time']
    cursor_pos = game_state['cursor_pos']
    previous_key = game_state['previous_key']
    hitted_objects = game_state['hitted_objects']
    active_sliders = game_state['active_sliders']
    beatmap = game_state['beatmap']
    hit_window_300, hit_window_100, hit_window_50 = game_state['hit_windows']
    preempt = game_state['preempt']
    cs = game_state['cs']
    apply_smoothing = game_state['apply_smoothing']
    hitsound = game_state['hitsound']
    miss_sound = game_state['miss_sound']
    score = game_state['score']

    current_key = cursor_pos['keys']
    new_key_pressed = current_key & (~previous_key)
    key_pressed = (current_key & (Key.M1 | Key.M2 | Key.K1 | Key.K2)) != 0

    # Get visible hit objects
    visible_hit_objects = [
        obj for obj in beatmap.hit_objects
        if obj['time'] - preempt <= current_time <= obj['time'] + 300  # Adjust fade-out time as needed
    ]

    # Process active sliders
    process_active_sliders(game_state)

    # Process hit objects
    for obj in visible_hit_objects:
        obj_time = obj['time']

        if obj_time in hitted_objects:
            continue

        # Skip objects whose hit windows have not yet started
        if current_time < obj_time - hit_window_50:
            continue

        # Only process the first unhit object within its hit window
        time_diff = current_time - obj_time

        if obj['object_name'] == 'circle':
            process_circle(game_state,obj, time_diff, cursor_pos,
                           cs, new_key_pressed, key_pressed, hitsound,
                           miss_sound, hitted_objects, score, current_time)
            break  # Only process one object per frame
        elif obj['object_name'] == 'slider':
            process_slider_start(game_state, obj, time_diff, cursor_pos, cs, new_key_pressed, key_pressed)
            break  # Only process one object per frame
        elif obj['object_name'] == 'spinner':
            # Implement spinner logic if needed
            pass

    # Update previous key
    game_state['previous_key'] = current_key

def process_circle(game_state, obj, time_diff, cursor_pos,
                   cs, new_key_pressed, key_pressed, hitsound,
                   miss_sound, hitted_objects, score, current_time):
    if not new_key_pressed:
        return

    cursor_x = cursor_pos['x']
    cursor_y = cursor_pos['y']
    obj_x = obj['x']
    obj_y = obj['y']
    distance = math.hypot(cursor_x - obj_x, cursor_y - obj_y)
    radius = calculate_circle_radius(cs)

    hit_window_300, hit_window_100, hit_window_50 = game_state['hit_windows']

    if distance > radius:
        return  # Cursor not on the circle

    if -hit_window_300 <= time_diff <= hit_window_300:
        success_hit(300, score)
    elif -hit_window_100 <= time_diff <= hit_window_100:
        success_hit(100, score)
    elif -hit_window_50 <= time_diff <= hit_window_50:
        success_hit(50, score)
    else:
        miss(score)
        #miss_sound.play()

    hitsound.play()
    game_state["renderer"].on_object_hit(obj, 300, current_time)
    hitted_objects[obj['time']] = True

def process_slider_start(game_state, obj, time_diff, cursor_pos, cs, new_key_pressed, key_pressed):
    hitted_objects = game_state['hitted_objects']
    active_sliders = game_state['active_sliders']
    hitsound = game_state['hitsound']
    miss_sound = game_state['miss_sound']
    score = game_state['score']

    hit_window_50 = game_state['hit_windows'][2]

    if obj['time'] in hitted_objects:
        return

    if not new_key_pressed:
        return

    cursor_x = cursor_pos['x']
    cursor_y = cursor_pos['y']
    obj_x = obj['x']
    obj_y = obj['y']
    distance = math.hypot(cursor_x - obj_x, cursor_y - obj_y)
    radius = calculate_circle_radius(cs)

    if distance > radius:
        miss(score)
        hitsound.play()
        #miss_sound.play()
        hitted_objects[obj['time']] = True
        return

    if -hit_window_50 <= time_diff <= hit_window_50:
        # Start the slider
        if 'ticks' not in obj:
            obj['ticks'] = compute_slider_ticks(obj, game_state['beatmap'])
        active_sliders[obj['time']] = {
            'object': obj,
            'start_time': obj['time'],
            'end_time': obj['time'] + obj['slider_duration'],
            'ticks': obj['ticks'],
            'missed_ticks': 0,
            'total_ticks': len(obj['ticks']),
            'slider_path': obj['curve_points']
        }
        hitsound.play()
        hitted_objects[obj['time']] = True
    else:
        miss(score)
        hitsound.play()
        #miss_sound.play()
        hitted_objects[obj['time']] = True

def process_active_sliders(game_state):
    current_time = game_state['current_time']
    cursor_pos = game_state['cursor_pos']
    active_sliders = game_state['active_sliders']
    hitsound = game_state['hitsound']
    miss_sound = game_state['miss_sound']
    score = game_state['score']
    key_pressed = (cursor_pos['keys'] & (Key.M1 | Key.M2 | Key.K1 | Key.K2)) != 0
    cs = game_state['cs']
    radius = calculate_circle_radius(cs)

    for slider_time in list(active_sliders.keys()):
        slider_info = active_sliders[slider_time]
        obj = slider_info['object']
        start_time = slider_info['start_time']
        end_time = slider_info['end_time']

        if current_time >= end_time:
            # Slider has ended
            total_ticks = slider_info['total_ticks']
            missed_ticks = slider_info['missed_ticks']

            hitsound.play()

            if missed_ticks == 0:
                success_hit(300, score)
            elif missed_ticks < total_ticks:
                success_hit(100, score)
            else:
                miss(score)
                miss_sound.play()
            del active_sliders[slider_time]
            continue

        # Slider is still active
        cursor_x = cursor_pos['x']
        cursor_y = cursor_pos['y']

        # Process slider ticks
        for tick in slider_info['ticks']:
            if tick.get('processed', False):
                continue
            tick_time = tick['time']
            if current_time >= tick_time:
                tick_pos = tick['position']
                distance = math.hypot(cursor_x - tick_pos[0], cursor_y - tick_pos[1])
                if distance <= radius and key_pressed:
                    tick['hit'] = True
                else:
                    tick['hit'] = False
                    slider_info['missed_ticks'] += 1
                tick['processed'] = True

def render_frame(window, game_state):
    glClear(GL_COLOR_BUFFER_BIT)
    renderer = game_state['renderer']
    current_time = game_state['current_time']
    cursor_pos = game_state['cursor_pos']
    cursor_trail = game_state['cursor_trail']
    beatmap = game_state['beatmap']
    preempt = game_state['preempt']
    cs = game_state['cs']

    current_key = cursor_pos['keys']
    new_key_pressed = current_key & (~game_state['previous_key'])

    if new_key_pressed:
        game_state['last_press_time'] = current_time

    # Draw background
    renderer.draw_background(current_time, game_state.get('last_press_time', -100000))

    # Draw hit objects
    visible_hit_objects = [
        obj for obj in beatmap.hit_objects
        if obj['time'] - preempt <= current_time <= (obj['time'] + (obj.get('slider_duration') if 'slider_duration' in obj else 0) ) + 100  # Adjust fade-out time as needed
    ]

    for obj in visible_hit_objects:
        obj_time = obj['time']
        appear_time = obj_time - preempt
        time_since_appear = current_time - appear_time
        approach_scale = 1.0 - (time_since_appear / preempt)

        if obj['object_name'] == 'circle':
            renderer.draw_circle_object(obj, cs, approach_scale, current_time)
        elif obj['object_name'] == 'slider':
            renderer.draw_slider_object(obj, cs, approach_scale, game_state['active_sliders'], current_time)
        elif obj['object_name'] == 'spinner':
            renderer.draw_spinner_object(obj, current_time)
    
    '''for effect_data in renderer.hit_objects_effects[:]:  # Copy the list to avoid modification issues
        hit_object = effect_data['object']
        effect_start_time = effect_data['effect_start_time']
        duration = effect_data['duration']
        elapsed_time = current_time - effect_start_time

        if elapsed_time <= duration:
            # Render the hit effect
            if 'effects' in renderer.render_functions and hasattr(renderer.render_functions['effects'], 'render_hit_effect'):
                renderer.render_functions['effects'].render_hit_effect(renderer, hit_object, elapsed_time, duration)
            else:
                renderer.default_render_hit_effect(hit_object, elapsed_time, duration)
        else:
            # Effect duration over, remove from the list
            renderer.hit_objects_effects.remove(effect_data)'''

    if cursor_pos:
        # Draw the cursor trail
        renderer.draw_cursor_trail(cursor_trail, current_time)

        # Draw the cursor
        renderer.draw_cursor(cursor_pos, (255, 255, 255), current_time)

    # Render UI elements
    #renderer.draw_ui(0, 0, 100, game_state['hp'], cursor_pos['keys'] if cursor_pos else 0, current_time)

    #renderer.render_effects(current_time)

    # Swap front and back buffers
    glfw.swap_buffers(window)

def cleanup(window, renderer):
    renderer.cleanup()
    glfw.destroy_window(window)
    glfw.terminate()
    pygame.quit()

def interpolate_cursor_position(cursor_data, current_time, apply_smoothing=False):
    """
    Interpolates the cursor position at the current time using linear interpolation.
    Optionally applies smoothing.
    """
    # Find the two events surrounding the current time
    for i in range(len(cursor_data) - 1):
        event_a = cursor_data[i]
        event_b = cursor_data[i + 1]
        if event_a['time'] <= current_time <= event_b['time']:
            # Calculate interpolation factor
            t = (current_time - event_a['time']) / (event_b['time'] - event_a['time'])
            x = event_a['x'] + t * (event_b['x'] - event_a['x'])
            y = event_a['y'] + t * (event_b['y'] - event_a['y'])
            keys_pressed = event_b['keys']

            if apply_smoothing:
                # Apply smoothing filter (e.g., moving average)
                x = smoothing_filter([event_a['x'], x, event_b['x']])
                y = smoothing_filter([event_a['y'], y, event_b['y']])

            return {'x': x, 'y': y, 'keys': keys_pressed}
    # If current_time is beyond the last event, return the last position
    last_event = cursor_data[-1]
    return {'x': last_event['x'], 'y': last_event['y'], 'keys': last_event['keys']}

def smoothing_filter(values):
    """
    Applies a simple moving average filter to the list of values.
    """
    return sum(values) / len(values)

def calculate_circle(x1, y1, x2, y2, x3, y3):
    """
    Calculates the center (h, k) and radius r of the circle passing through three points.
    Returns (h, k, r) or None if the points are colinear.
    """
    # Calculate the determinants
    temp = x2 ** 2 + y2 ** 2
    bc = (x1 ** 2 + y1 ** 2 - temp) / 2.0
    cd = (temp - x3 ** 2 - y3 ** 2) / 2.0
    det = (x1 - x2) * (y2 - y3) - (x2 - x3) * (y1 - y2)

    if abs(det) < 1e-6:
        # Points are colinear
        return None

    # Center of circle (h, k)
    h = (bc * (y2 - y3) - cd * (y1 - y2)) / det
    k = ((x1 - x2) * cd - (x2 - x3) * bc) / det

    # Radius
    r = math.hypot(x1 - h, y1 - k)
    return (h, k, r)

def determine_arc_direction(x1, y1, x2, y2, x3, y3):
    """
    Determines the direction of the arc (clockwise or counterclockwise) based on the control point.
    Returns 'clockwise' or 'counterclockwise'.
    """
    # Calculate the cross product of vectors (P1P2 x P2P3)
    cross = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)

    if cross < 0:
        return 'clockwise'
    else:
        return 'counterclockwise'

def compute_slider_ticks(obj, beatmap):
    ticks = []
    start_time = obj['time']
    duration = obj['slider_duration']
    repeats = obj['slides']

    # Get timing point information
    beat_length, slider_velocity = beatmap.get_timing_at(start_time)
    slider_multiplier = float(beatmap.difficulty['SliderMultiplier'])
    tick_rate = float(beatmap.difficulty['SliderTickRate'])

    # Calculate tick distance
    tick_distance = (beat_length / tick_rate) * slider_multiplier * slider_velocity

    # Calculate the number of ticks per repeat
    ticks_per_repeat = int(obj['length'] / tick_distance)

    # Get the slider path length
    slider_length = obj['length']

    # Compute ticks for each repeat
    for repeat_index in range(repeats):
        reverse = repeat_index % 2 == 1  # Reverse direction on odd repeats
        for tick_index in range(1, ticks_per_repeat + 1):
            tick_position = tick_index * tick_distance
            if tick_position >= slider_length:
                break
            # Calculate the time for this tick
            tick_progress = tick_position / slider_length
            if reverse:
                tick_progress = 1.0 - tick_progress
            tick_time = start_time + (duration / repeats) * (repeat_index + tick_progress)
            # Get the position on the slider path
            position = get_slider_position_at(obj, tick_progress)
            ticks.append({
                'time': tick_time,
                'position': (position['x'], position['y']),  # Should be a tuple (x, y)
                'processed': False,
                'hit': False,
            })
    return ticks


def draw_hit_objects(beatmap, renderer, cs, preempt, fade_out, current_time):
    # Determine which objects are visible
    visible_objects = [obj for obj in beatmap.hit_objects
                       if obj['time'] - preempt <= current_time <= obj['time'] + fade_out]

    for obj in visible_objects:
        appear_time = obj['time'] - preempt
        time_since_appear = current_time - appear_time    
        approach_scale = 1.0 - (time_since_appear / preempt)

        if obj['object_name'] == 'circle':
            renderer.draw_circle_object(obj, cs, approach_scale)
        elif obj['object_name'] == 'slider':
            renderer.draw_slider_object(obj, cs, approach_scale)
        elif obj['object_name'] == 'spinner':
            renderer.draw_spinner_object(obj, cs, approach_scale)
    
    return visible_objects

def success_hit(hitscore, score_obj):
    score_obj['total_hits'] += 1
    score_obj['combo'] += 1

def miss(score_obj):
    score_obj['total_hits'] += 1
    score_obj['combo'] = 0

if __name__ == "__main__":
    main()
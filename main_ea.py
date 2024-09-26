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

def initialize_window(width=1280, height=720, title="OSU! Replay Visualizer"):
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
        desired_point_interval = 5  # Time in milliseconds between points
        num_points = max(int(time_diff / desired_point_interval), 1)

        # Alternate curve direction if the option is enabled
        if alternate_curve_direction:
            curve_direction *= -1
        else:
            curve_direction = 1  # Always curve in the same direction

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
        key_hold_duration = 10  # milliseconds for circles
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
            key_release_time = obj['time'] + slider_duration + 50  # Hold key slightly after slider ends
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

    # Initialize the audio player
    pygame.init()
    pygame.mixer.init()

    hitsound = pygame.mixer.Sound('default_assets/hitsound.wav')
    miss_sound = pygame.mixer.Sound('default_assets/miss_sound.wav')

    # Create the renderer
    width, height = glfw.get_window_size(window)
    renderer = Renderer(width, height)

    # Ask the user to select the beatmap
    beatmap_path = input("Enter the path to the beatmap (.osu) file: ")

    # Load the beatmap
    beatmap = Beatmap(beatmap_path)
    beatmap_md5 = beatmap.get_md5_hash()

    # Ask the user to select the replay or playstyle
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
            apply_smoothing = False  # Do not apply smoothing in Auto mode
            alternate_curve_direction = False
        elif playstyle_choice == '2':
            playstyle = 'Dancer'
            dancing_degree = float(input("Enter dancing degree (0.0 to 1.0): "))
            apply_smoothing = True  # Apply smoothing in Dancer mode

            # Prompt for curve direction option
            curve_direction_choice = input("Should the curves alternate direction? (yes/no): ").lower()
            if curve_direction_choice in ['yes', 'y']:
                alternate_curve_direction = True
            else:
                alternate_curve_direction = False
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
        apply_smoothing = True  # Apply smoothing for replays

        # Adjust beatmap for mods
        if mods & Mod.HardRock:
            beatmap.apply_hard_rock_mod()

    # Get difficulty settings
    cs = beatmap.get_circle_size()
    ar = beatmap.get_approach_rate()
    od = beatmap.get_overall_difficulty()
    preempt = calculate_preempt(ar)
    fade_out_time = 300  # Time after hit object to fade out (in ms)

    hit_window_300, hit_window_100, hit_window_50 = calculate_hit_windows(od)

    # Get the audio file path
    audio_filename = beatmap.general.get('AudioFilename', None)
    if audio_filename is None:
        print("Audio file not specified in the beatmap.")
        glfw.terminate()
        return

    audio_file_path = os.path.join(os.path.dirname(beatmap_path), audio_filename)

    # Start playing the audio
    start_time = start_audio_playback(audio_file_path)

    # Get cursor positions from replay data
    if hasattr(replay_data, 'cursor_data'):
        # Use generated cursor data
        cursor_data = replay_data.cursor_data
    else:
        # Use cursor positions from replay file
        cursor_data = replay_data.get_cursor_positions(mods)

    # APPLY OFFSET FOR REPLAYS
    OFFSET = 300
    if replay_option.lower() != 'auto':
        for event in cursor_data:
            event['time'] -= OFFSET

    # Initialize cursor trail
    cursor_trail = []

    # Initialize audio offset
    audio_offset = 0

    # Setup key callback for offset adjustment and key presses
    def key_callback(window, key, scancode, action, mods):
        nonlocal audio_offset
        if action == glfw.PRESS or action == glfw.REPEAT:
            if key == glfw.KEY_UP:
                audio_offset += 10  # Increase offset by 10 ms
                print(f"Audio Offset: {audio_offset} ms")
            elif key == glfw.KEY_DOWN:
                audio_offset -= 10  # Decrease offset by 10 ms
                print(f"Audio Offset: {audio_offset} ms")

    glfw.set_key_callback(window, key_callback)

    # Keep track of hit objects
    objects_to_hit = beatmap.hit_objects.copy()
    current_object_index = 0

    # Keep track of score and combo
    score = 0
    combo = 0

    # Keep track of hits for rendering effects
    hit_objects = []
    missed_objects = []

    # Initialize a list to store key states
    previous_keys = 0  # No keys pressed initially
    
    active_sliders = []

    # Main render loop
    while not glfw.window_should_close(window):
        # Poll for and process events
        glfw.poll_events()

        # Update start_time if offset changed
        adjusted_start_time = start_time - audio_offset

        # Calculate the current time in the beatmap
        current_time = glfw.get_time() * 1000 - adjusted_start_time  # In milliseconds

        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT)

        # Draw background
        renderer.draw_background()

        # Draw hit objects based on timing
        visible_hit_objects = [
            obj for obj in beatmap.hit_objects
            if obj['time'] - preempt <= current_time <= obj['time'] + fade_out_time
        ]

        for obj in visible_hit_objects:
            obj_time = obj['time']
            appear_time = obj_time - preempt
            time_since_appear = current_time - appear_time
            approach_scale = 1.0 - (time_since_appear / preempt)

            if obj['object_name'] == 'circle':
                renderer.draw_circle_object(obj, cs, approach_scale)
            elif obj['object_name'] == 'slider':
                renderer.draw_slider_object(obj, cs, approach_scale)
            elif obj['object_name'] == 'spinner':
                renderer.draw_spinner_object(obj, current_time)

        # Get the interpolated cursor position
        cursor_pos = interpolate_cursor_position(cursor_data, current_time, apply_smoothing)

        if cursor_pos:
            # Update the cursor trail
            cursor_trail.append({'x': cursor_pos['x'], 'y': cursor_pos['y']})

            # Draw the cursor trail
            renderer.draw_cursor_trail(cursor_trail)

            # Determine cursor color based on keys pressed
            current_keys = cursor_pos['keys']
            if current_keys:
                cursor_color = CURSOR_COLOR_ACTIVE
            else:
                cursor_color = CURSOR_COLOR_INACTIVE

            # Draw the cursor
            renderer.draw_cursor(cursor_pos, cursor_color, current_time)

            # Key press detection
            new_keys_pressed = current_keys & (~previous_keys)
            if new_keys_pressed:
                print("PRESS", new_keys_pressed)
                # One or more keys were just pressed
                # Proceed with hit detection

                # Check if there is an object to hit
                if current_object_index < len(objects_to_hit):
                    print("Current object index:", current_object_index)
                    hit_object = objects_to_hit[current_object_index]
                    obj_time = hit_object['time']

                    time_diff = abs(current_time - obj_time)

                    if hit_object['object_name'] == 'circle':
                        # Circle object hit
                        if time_diff <= hit_window_50:
                            # Check if cursor is over the object
                            cursor_x = cursor_pos['x']
                            cursor_y = cursor_pos['y']
                            obj_x = hit_object['x']
                            obj_y = hit_object['y']
                            distance = ((cursor_x - obj_x) ** 2 + (cursor_y - obj_y) ** 2) ** 0.5
                            radius = calculate_circle_radius(cs)

                            if distance <= radius:
                                # Determine score based on time_diff
                                if time_diff <= hit_window_300:
                                    hit_score = 300
                                elif time_diff <= hit_window_100:
                                    hit_score = 100
                                else:
                                    hit_score = 50

                                # Update score and combo
                                score += hit_score
                                combo += 1

                                # Play hitsound
                                hitsound.play()

                                # Notify renderer about the hit
                                renderer.on_object_hit(hit_object, hit_score)

                                # Move to next object
                                current_object_index += 1
                            else:
                                # Cursor not over the object, miss
                                miss_sound.play()
                                renderer.on_player_miss(hit_object)
                                combo = 0
                                current_object_index += 1
                        else:
                            # Time difference too large, possible miss
                            if current_time - obj_time > hit_window_50:
                                # Missed the object
                                miss_sound.play()
                                renderer.on_player_miss(hit_object)
                                combo = 0
                                current_object_index += 1

                    elif hit_object['object_name'] == 'slider':
                        # Slider hit detection
                        if abs(time_diff) <= hit_window_50:
                            # Check if cursor is over the slider start position
                            cursor_x = cursor_pos['x']
                            cursor_y = cursor_pos['y']
                            obj_x = hit_object['x']
                            obj_y = hit_object['y']
                            distance = ((cursor_x - obj_x) ** 2 + (cursor_y - obj_y) ** 2) ** 0.5
                            radius = calculate_circle_radius(cs)

                            if distance <= radius:
                                # Start tracking the slider
                                slider_end_time = obj_time + hit_object['slider_duration']
                                active_sliders.append({
                                    'object': hit_object,
                                    'start_time': obj_time,
                                    'end_time': slider_end_time,
                                    'missed': False
                                })

                                # Play initial hit sound
                                hitsound.play()

                                # Do not increment current_object_index yet
                            else:
                                # Cursor not over the slider start, miss
                                miss_sound.play()
                                renderer.on_player_miss(hit_object)
                                combo = 0
                                current_object_index += 1
                        else:
                            # Missed slider start
                            if current_time - obj_time > hit_window_50:
                                miss_sound.play()
                                renderer.on_player_miss(hit_object)
                                combo = 0
                                current_object_index += 1
                else:
                    # No more objects to hit, but key was pressed
                    pass  # Optionally handle extra key presses

            previous_keys = current_keys
        else:
            # Cursor is not active during this time
            pass
            
        for slider in active_sliders[:]:  # Copy the list to avoid modification issues
            hit_object = slider['object']
            slider_start_time = slider['start_time']
            slider_end_time = slider['end_time']

            if slider_start_time <= current_time <= slider_end_time:
                # Slider is active
                progress = (current_time - slider_start_time) / (slider_end_time - slider_start_time)
                slider_position = get_slider_position_at(hit_object, progress)

                cursor_x = cursor_pos['x']
                cursor_y = cursor_pos['y']
                slider_x = slider_position['x']
                slider_y = slider_position['y']
                distance = ((cursor_x - slider_x) ** 2 + (cursor_y - slider_y) ** 2) ** 0.5
                radius = calculate_circle_radius(cs)

                if distance > radius * 2:  # Allow some margin
                    # Player is too far from the slider path
                    if not slider['missed']:
                        miss_sound.play()
                        renderer.on_player_miss(hit_object)
                        slider['missed'] = True
                        combo = 0
            elif current_time > slider_end_time:
                # Slider has ended
                if not slider['missed']:
                    # Player successfully completed the slider
                    hit_score = 300  # Simplified scoring
                    score += hit_score
                    combo += 1
                    renderer.on_object_hit(hit_object, hit_score)
                    # Play hit sound at slider end
                    hitsound.play()
                else:
                    # Slider was missed or sliderbroken
                    # Play miss sound at slider end
                    miss_sound.play()
                active_sliders.remove(slider)
                current_object_index += 1

        # Render effects
        if 'effects' in renderer.render_functions:
            renderer.render_functions['effects'].render_effects(renderer)

        # Swap front and back buffers
        glfw.swap_buffers(window)

    renderer.cleanup()
    # Terminate glfw when done
    glfw.terminate()

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

if __name__ == "__main__":
    main()
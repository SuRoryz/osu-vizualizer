from OpenGL.GL import *
import numpy as np
from src.utils import osu_to_ndc
import time
from src.constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT
from skins.default.skin_settings import SKIN_SETTINGS

# Global variables to keep track of effects
ripples = []
hit_effects = []
player_dead = False
death_start_time = None

def initialize_effects():
    """
    Initializes any required resources for effects.
    """
    global ripples, hit_effects, player_dead, death_start_time
    ripples = []
    hit_effects = []
    player_dead = False
    death_start_time = None

def on_key_press(key):
    """
    Creates a ripple effect when a key is pressed.
    """
    if not SKIN_SETTINGS.get('enable_ripples', True):
        return
    # Add a new ripple with timestamp
    ripples.append({'start_time': time.time(), 'duration': 1.0})

def on_object_hit(hit_object, score):
    """
    Displays hit score and shatters note.
    """
    hit_effects.append({
        'type': 'hit',
        'object': hit_object,
        'score': score,
        'start_time': time.time(),
        'duration': 0.5
    })

def on_player_miss(hit_object):
    """
    Displays miss effect and shatters note.
    """
    hit_effects.append({
        'type': 'miss',
        'object': hit_object,
        'start_time': time.time(),
        'duration': 0.5
    })

def on_player_death():
    """
    Initiates death effect.
    """
    global player_dead, death_start_time
    player_dead = True
    death_start_time = time.time()

def render_effects():
    """
    Renders all active effects.
    """
    current_time = time.time()

    # Render ripples
    active_ripples = []
    for ripple in ripples:
        elapsed = current_time - ripple['start_time']
        if elapsed < ripple['duration']:
            render_ripple(elapsed / ripple['duration'])
            active_ripples.append(ripple)
    ripples[:] = active_ripples  # Remove expired ripples

    # Render hit effects
    active_hit_effects = []
    for effect in hit_effects:
        elapsed = current_time - effect['start_time']
        if elapsed < effect['duration']:
            render_hit_effect(effect, elapsed / effect['duration'])
            active_hit_effects.append(effect)
    hit_effects[:] = active_hit_effects  # Remove expired effects

    # Render death effect
    if player_dead:
        render_death_effect(current_time - death_start_time)

def render_ripple(progress, renderer):
    """
    Renders a ripple effect on the background using shaders.
    """
    size = 1 + progress * 2  # Ripple expands over time
    vertices = np.array([
        [-size, -size],
        [size, -size],
        [-size, size],
        [size, size]
    ], dtype=np.float32)

    color = (0.5, 0.5, 1.0, 1.0 - progress)
    colors = np.tile(color, (4, 1)).astype(np.float32)

    # Create VBOs and draw using renderer's shader program
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.position_loc)
    glVertexAttribPointer(renderer.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    vbo_colors = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
    glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.color_loc)
    glVertexAttribPointer(renderer.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

    # Use renderer's shader program
    glUseProgram(renderer.shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, np.identity(4, dtype=np.float32))

    # Draw the ripple quad
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])

def render_hit_effect(effect, progress, renderer):
    """
    Renders the hit or miss effect using shaders.
    """
    hit_object = effect['object']
    x = hit_object['x']
    y = hit_object['y']
    scale = 1 + progress

    # Prepare transformation matrix
    translation = np.identity(4, dtype=np.float32)
    tx, ty = osu_to_ndc(x, y)
    translation[3][0] = tx
    translation[3][1] = ty

    scaling = np.identity(4, dtype=np.float32)
    scaling[0][0] = scale
    scaling[1][1] = scale

    model_matrix = np.dot(translation, scaling)
    mvp_matrix = np.dot(renderer.projection_matrix.T, model_matrix)

    # Define a quad for the hit effect
    size = 0.05
    vertices = np.array([
        [-size, -size],
        [size, -size],
        [-size, size],
        [size, size]
    ], dtype=np.float32)

    if effect['type'] == 'hit':
        color = (1.0, 1.0, 1.0, 1.0 - progress)
    else:
        color = (1.0, 0.0, 0.0, 1.0 - progress)
    colors = np.tile(color, (4, 1)).astype(np.float32)

    # Create VBOs and draw using renderer's shader program
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.position_loc)
    glVertexAttribPointer(renderer.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    vbo_colors = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
    glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.color_loc)
    glVertexAttribPointer(renderer.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

    # Use renderer's shader program
    glUseProgram(renderer.shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, mvp_matrix)

    # Draw the effect quad
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])

def render_death_effect(elapsed_time, renderer):
    """
    Renders the death effect using shaders.
    """
    intensity = min(elapsed_time / 2.0, 1.0)  # Gradually increase over 2 seconds
    color = (1.0, 0.0, 0.0, intensity)

    # Define vertices for full-screen quad
    vertices = np.array([
        [-1.0, -1.0],
        [1.0, -1.0],
        [-1.0, 1.0],
        [1.0, 1.0]
    ], dtype=np.float32)
    colors = np.tile(color, (4, 1)).astype(np.float32)

    # Create VBOs and draw using renderer's shader program
    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo_vertices = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_vertices)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.position_loc)
    glVertexAttribPointer(renderer.position_loc, 2, GL_FLOAT, GL_FALSE, 0, None)

    vbo_colors = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo_colors)
    glBufferData(GL_ARRAY_BUFFER, colors.nbytes, colors, GL_DYNAMIC_DRAW)
    glEnableVertexAttribArray(renderer.color_loc)
    glVertexAttribPointer(renderer.color_loc, 4, GL_FLOAT, GL_FALSE, 0, None)

    # Use renderer's shader program
    glUseProgram(renderer.shader_program)
    glUniformMatrix4fv(renderer.mvp_matrix_loc, 1, GL_FALSE, np.identity(4, dtype=np.float32))

    # Draw the death effect quad
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

    # Clean up
    glDisableVertexAttribArray(renderer.position_loc)
    glDisableVertexAttribArray(renderer.color_loc)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glDeleteBuffers(2, [vbo_vertices, vbo_colors])
    glDeleteVertexArrays(1, [vao])
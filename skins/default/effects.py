from OpenGL.GL import *
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

def render_ripple(progress):
    """
    Renders a ripple effect on the background.
    """
    glColor4f(0.5, 0.5, 1.0, 1.0 - progress)
    size = 1 + progress * 2  # Ripple expands over time
    glBegin(GL_QUADS)
    glVertex2f(-size, -size)
    glVertex2f(size, -size)
    glVertex2f(size, size)
    glVertex2f(-size, size)
    glEnd()

def render_hit_effect(effect, progress):
    """
    Renders the hit or miss effect.
    """
    hit_object = effect['object']
    x = hit_object['x']
    y = hit_object['y']
    ndc_x, ndc_y = osu_to_ndc(x, y)
    glPushMatrix()
    glTranslatef(ndc_x, ndc_y, 0)
    scale = 1 + progress
    glScalef(scale, scale, 1)

    if effect['type'] == 'hit':
        glColor4f(1.0, 1.0, 1.0, 1.0 - progress)
        # Render score text (simplified)
        # In practice, you would render text using a text rendering library
        # For this example, we'll draw a simple quad
        glBegin(GL_QUADS)
        glVertex2f(-0.05, -0.05)
        glVertex2f(0.05, -0.05)
        glVertex2f(0.05, 0.05)
        glVertex2f(-0.05, 0.05)
        glEnd()
    elif effect['type'] == 'miss':
        glColor4f(1.0, 0.0, 0.0, 1.0 - progress)
        # Render miss text or effect
        glBegin(GL_QUADS)
        glVertex2f(-0.05, -0.05)
        glVertex2f(0.05, -0.05)
        glVertex2f(0.05, 0.05)
        glVertex2f(-0.05, 0.05)
        glEnd()
    glPopMatrix()

def render_death_effect(elapsed_time):
    """
    Renders the death effect.
    """
    intensity = min(elapsed_time / 2.0, 1.0)  # Gradually increase over 2 seconds
    glColor4f(1.0, 0.0, 0.0, intensity)
    glBegin(GL_QUADS)
    glVertex2f(-1, -1)
    glVertex2f(1, -1)
    glVertex2f(1, 1)
    glVertex2f(-1, 1)
    glEnd()
from .constants import OSU_PLAYFIELD_WIDTH, OSU_PLAYFIELD_HEIGHT

def osu_to_ndc(osu_x, osu_y):
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
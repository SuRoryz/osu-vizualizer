import hashlib
import os

from .constants import OSU_PLAYFIELD_HEIGHT

class Beatmap:
    def __init__(self, file_path):
        self.file_path = file_path
        self.general = {}
        self.metadata = {}
        self.difficulty = {}
        self.timing_points = []
        self.hit_objects = []

        self.parse_beatmap()

    def apply_hard_rock_mod(self):
        """
        Adjusts the beatmap settings for Hard Rock mod.
        """
        # Increase CS, AR, OD, HP by 1.4x, capped at 10
        for stat in ['CircleSize', 'ApproachRate', 'OverallDifficulty', 'HPDrainRate']:
            original_value = float(self.difficulty.get(stat, 5))
            adjusted_value = min(original_value * 1.4, 10)
            self.difficulty[stat] = str(adjusted_value)

        # Flip hit objects vertically
        for obj in self.hit_objects:
            obj['y'] = OSU_PLAYFIELD_HEIGHT - obj['y']
            if obj['object_name'] == 'slider':
                for point in obj['curve_points']:
                    point['y'] = OSU_PLAYFIELD_HEIGHT - point['y']

    def get_md5_hash(self):
        """
        Calculates the MD5 hash of the beatmap file.
        """
        hasher = hashlib.md5()
        with open(self.file_path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def parse_beatmap(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Beatmap file not found: {self.file_path}")

        section = None
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    # New section
                    section = line.strip('[]')
                    continue
                if not line or line.startswith('//'):
                    continue

                if section == 'General':
                    key, value = self.parse_key_value(line)
                    self.general[key] = value
                elif section == 'Metadata':
                    key, value = self.parse_key_value(line)
                    self.metadata[key] = value
                elif section == 'Difficulty':
                    key, value = self.parse_key_value(line)
                    self.difficulty[key] = value
                elif section == 'TimingPoints':
                    self.timing_points.append(line)
                elif section == 'HitObjects':
                    self.hit_objects.append(line)
        
        for i, line in enumerate(self.timing_points):
            self.timing_points[i] = self.parse_timing_point(line)
        
        for i, line in enumerate(self.hit_objects):
            self.hit_objects[i] = self.parse_hit_object(line)

    def parse_key_value(self, line):
        if ':' in line:
            key, value = line.split(':', 1)
            return key.strip(), value.strip()
        else:
            return line.strip(), ''
    
    def parse_timing_point(self, line):
        """
        Parses a timing point line and returns a dictionary.
        """
        values = line.split(',')
        timing_point = {
            'time': float(values[0]),
            'beat_length': float(values[1]),
            'meter': int(values[2]) if len(values) > 2 else 4,
            'sample_set': int(values[3]) if len(values) > 3 else 0,
            'sample_index': int(values[4]) if len(values) > 4 else 0,
            'volume': int(values[5]) if len(values) > 5 else 100,
            'uninherited': int(values[6]) if len(values) > 6 else 1,
            'effects': int(values[7]) if len(values) > 7 else 0,
        }
        return timing_point

    def parse_hit_object(self, line):
        """
        Parses a hit object line and returns a dictionary.
        """
        values = line.split(',')
        obj = {
            'x': int(values[0]),
            'y': int(values[1]),
            'time': int(values[2]),
            'type': int(values[3]),
            'hit_sound': int(values[4]),
        }

        obj_type = obj['type']

        if obj_type & 1:
            obj['object_name'] = 'circle'
        elif obj_type & 2:
            obj['object_name'] = 'slider'
            obj['slider_type'] = values[5][0]
            obj['curve_points'] = self.parse_curve_points(values[5])
            obj['slides'] = int(values[6])
            obj['length'] = float(values[7])
            # Additional slider parameters can be parsed here
        elif obj_type & 8:
            obj['object_name'] = 'spinner'
            obj['end_time'] = int(values[5])

        return obj

    def parse_curve_points(self, curve_data):
        """
        Parses the curve points for sliders.
        """
        # Curve data is like "B|x1:y1|x2:y2|..."
        points = curve_data.split('|')[1:]
        curve_points = []
        for point in points:
            x_str, y_str = point.split(':')
            curve_points.append({'x': float(x_str), 'y': float(y_str)})
        return curve_points
    
    def get_circle_size(self):
        return float(self.difficulty.get('CircleSize', 5))

    def get_approach_rate(self):
        ar = self.difficulty.get('ApproachRate')
        if ar is None:
            # If AR is not specified, it's the same as OD (older beatmaps)
            ar = self.difficulty.get('OverallDifficulty', 5)
        return float(ar)
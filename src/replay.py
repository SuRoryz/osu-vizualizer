from osrparse import Replay, Mod

from .constants import OSU_PLAYFIELD_HEIGHT

class ReplayData:
    def __init__(self, file_path):
        self.file_path = file_path
        self.replay = None
        self.replay_events = []
        self.load_replay()

    def get_cursor_positions(self, mods):
        """
        Returns a list of cursor positions with absolute timestamps.
        Handles negative or zero time_deltas.
        """
        cursor_data = []
        total_time = 0

        for event in self.replay_events:
            # Handle negative or zero time_delta
            if event.time_delta <= 0:
                continue  # Skip this event
            else:
                total_time += event.time_delta

            x = event.x
            y = event.y

            # Adjust for Hard Rock mod
            if mods & Mod.HardRock:
                y = OSU_PLAYFIELD_HEIGHT - y

            cursor_data.append({
                'time': total_time,
                'x': x,
                'y': y,
                'keys': event.keys
            })

        return cursor_data

    def load_replay(self):
        self.replay = Replay.from_path(self.file_path)
        self.replay_events = self.replay.replay_data

    def validate_beatmap(self, beatmap_md5):
        """
        Validates that the replay corresponds to the given beatmap MD5 hash.
        """
        return self.replay.beatmap_hash == beatmap_md5
from typing import Dict, Union
import random
from faker import Faker
import uuid
import string
from typing import Any
from datetime import datetime
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from activity.collectors.ambient.music.music_data_model import AmbientMusicData
from activity.collectors.ambient.music.spotify_data_model import SpotifyAmbientData
from data_generator.scripts.metadata.activity_metadata import ActivityMetadata
from icecream import ic

class MusicActivityData(ActivityMetadata):
    """
    Subclass for ActivityMetadata.
    Used to generate Music Activity Context based on AmbientMusicData and SpotifyAmbientData data models
    """
    TRACK_MIN_DURATION = 10000
    TRACK_MAX_DURATION = 300000
    def __init__(self, selected_AC_md):
        super().__init__(selected_AC_md)

    def generate_metadata(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime], is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str]) -> Any:
        is_truth_file=self._define_truth_attribute("ambient_music", is_truth_file, truth_like, truthlike_attributes)
        return self._generate_music_metadata(record_kwargs, timestamps, is_truth_file)

    def _generate_music_metadata(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime],
                                is_truth_file: bool) -> Union[AmbientMusicData, SpotifyAmbientData]:
        """generates the music metadata for either the base ambient music data model or specifically for spotify"""
        music_md = self._generate_general_music_data(record_kwargs, is_truth_file, timestamps)
        if (music_md.source == "spotify") or ("ambient_music" in self.selected_md and "spotify" in self.selected_md["ambient_music"]):
            return self._generate_spotify_music_data(music_md, is_truth_file)
        return music_md

    def _generate_spotify_music_data(self, base_md: AmbientMusicData, is_truth_file: bool) -> SpotifyAmbientData:
        """generates spotify music data"""
        devices = ["Computer","Smartphone","Speaker","TV","Game_Console","Automobile","Unknown"]
        artist_id = self._create_spotify_id(False, "artist")
        track_id = self._create_spotify_id(False, "track")
        device_type = random.choice(devices)

        if "ambient_music" in self.selected_md:
            music_dict = self.selected_md["ambient_music"]
            if "track_name" in music_dict:
                track_id = self._create_spotify_id(is_truth_file, "track", music_dict["track_name"])
            if "artist_name" in music_dict:
                artist_id = self._create_spotify_id(is_truth_file, "artist", music_dict["artist_name"])
            if "device_type" in music_dict and is_truth_file:
                device_type = self._choose_random_element(is_truth_file, music_dict["device_type"], devices)

        return SpotifyAmbientData(
                                    **base_md.dict(),
                                    track_id = track_id,
                                    artist_id = artist_id,
                                    device_name= "My " + device_type,
                                    device_type= device_type,
                                    shuffle_state= random.choice([True, False]),
                                    repeat_state = random.choice(["track", "context", "off"]),
                                    danceability= self._generate_spotify_score(),
                                    energy=self._generate_spotify_score(),
                                    valence=self._generate_spotify_score(),
                                    instrumentalness=self._generate_spotify_score(),
                                    acousticness=self._generate_spotify_score())

    def _create_spotify_id(self, is_truth_file, prefix:str, name:str = None):
        """Generates the spotify artist or track id"""
        heading = "spotify:" + prefix + ":"
        if is_truth_file:
            changed_name = name.replace(" ", "")
            digits = 22 - len(changed_name)
            space_filler = '0' * digits
            return heading + changed_name + space_filler
        else:
            return heading + ''.join(random.choices(string.ascii_letters + string.digits, k=22))

    def _generate_spotify_score(self, lower:float = 0.000, upper: float = 1.000) -> float:
        """generate a random spotify score for the given track"""
        return round(random.uniform(lower, upper), 3)

    def _generate_general_music_data(self, record_kwargs: IndalekoRecordDataModel, is_truth_file: bool,
                                    timestamps: Dict[str, datetime]) -> AmbientMusicData:
        """generates the general music activity context data"""
        faker = Faker()
        music_sources = ['spotify', 'youtube music', "apple music"]

        timestamp = self._generate_ac_timestamp(is_truth_file, timestamps, "ambient_music")
        track_name = faker.first_name()
        album_name = faker.name()
        artist_name = faker.name()
        track_duration_ms = random.randint(MusicActivityData.TRACK_MIN_DURATION, MusicActivityData.TRACK_MAX_DURATION)
        playback_position_ms = random.randint(0, track_duration_ms)
        source = random.choice(music_sources)
        is_currently_playing = random.choice([True, False])

        if "ambient_music" in self.selected_md:
            music_dict = self.selected_md["ambient_music"]
            if "source" in music_dict:
                source = self._choose_random_element(is_truth_file, music_dict["source"], music_sources)
            if "track_name" in music_dict and is_truth_file:
                track_name = music_dict["track_name"]
            if "artist_name" in music_dict and is_truth_file:
                artist_name = music_dict["artist_name"]
            if "album_name" in music_dict and is_truth_file:
                album_name = music_dict["album_name"]
            if "track_duration_ms" in music_dict and "playback_position_ms" in music_dict and is_truth_file:
                track_duration_ms = music_dict["track_duration_ms"]
                playback_position_ms = music_dict["playback_position_ms"]
            if "track_duration_ms" not in music_dict and "playback_position_ms" in music_dict and is_truth_file:
                playback_position_ms = music_dict["playback_position_ms"]
                track_duration_ms = random.randint(playback_position_ms, MusicActivityData.TRACK_MAX_DURATION)
            if "track_duration_ms" in music_dict and "playback_position_ms" not in music_dict and is_truth_file:
                track_duration_ms = music_dict["track_duration_ms"]
                playback_position_ms =  random.randint(0, track_duration_ms)
            else:
                playback_position_ms = random.randint(0, track_duration_ms)
            if "is_currently_playing" in music_dict and is_truth_file:
                is_currently_playing = self._choose_random_element(is_truth_file, music_dict["is_currently_playing"], [True, False]) 
        
        ic(track_duration_ms)
        ic(playback_position_ms)
        track_name_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="track_name")
        artist_name_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="artist_name")
        semantic_attributes = [
                IndalekoSemanticAttributeDataModel(Identifier=track_name_identifier, Data=track_name),
                IndalekoSemanticAttributeDataModel(Identifier=artist_name_identifier, Data=artist_name)
                ]

        return AmbientMusicData(Record=record_kwargs,
                                Timestamp=timestamp,
                                SemanticAttributes=semantic_attributes,
                                source=source,
                                track_name=track_name,
                                artist_name=artist_name,
                                album_name = album_name,
                                is_playing=is_currently_playing,
                                playback_position_ms=playback_position_ms,
                                track_duration_ms=track_duration_ms,
                                )

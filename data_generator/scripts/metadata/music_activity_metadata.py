"""Generate music activity metadata."""
import random
import string
import uuid

from datetime import datetime
from typing import Any

from faker import Faker

from activity.collectors.ambient.music.music_data_model import AmbientMusicData
from activity.collectors.ambient.music.spotify_data_model import SpotifyAmbientData
from data_generator.scripts.metadata.activity_metadata import ActivityMetadata
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel


class MusicActivityData(ActivityMetadata):
    """
    Subclass for ActivityMetadata.

    Used to generate Music Activity Context based on AmbientMusicData and
    SpotifyAmbientData data models.
    """

    TRACK_MIN_DURATION = 10000
    TRACK_MAX_DURATION = 300000
    MUSIC_SOURCES = ["spotify", "youtube music", "apple music"]  # noqa: RUF012
    DEVICES = ["Computer", "Smartphone", "Speaker", "TV", "Game_Console", "Automobile", "Unknown"]  # noqa: RUF012


    def generate_metadata(
        self,
        **kwargs: dict[str, Any],
    ) -> AmbientMusicData | SpotifyAmbientData:
        """Generate the music activity metadata."""
        record_kwargs = kwargs.get("record_kwargs")
        timestamps = kwargs.get("timestamps")
        is_truth_file = kwargs.get("is_truth_file")
        truth_like = kwargs.get("truth_like")
        truthlike_attributes = kwargs.get("truthlike_attributes")
        is_truth_file = self._define_truth_attribute(
            "ambient_music",
            is_truth_file,
            truth_like,
            truthlike_attributes,
        )
        return self._generate_music_metadata(record_kwargs, timestamps, is_truth_file)

    def _generate_music_metadata(
            self,
            record_kwargs: IndalekoRecordDataModel,
            timestamps: dict[str, datetime],
            is_truth_file: bool,  # noqa: FBT001
    ) -> AmbientMusicData | SpotifyAmbientData:
        """Generates the music metadata."""
        music_md = self._generate_general_music_data(record_kwargs, is_truth_file, timestamps)
        if (
            (music_md.source == "spotify") or
            ("ambient_music" in self.selected_md and
             "spotify" in self.selected_md["ambient_music"])
        ):
            return self._generate_spotify_music_data(music_md, is_truth_file)
        return music_md

    def _generate_spotify_music_data(
            self,
            base_md: AmbientMusicData,
            is_truth_file: bool,  # noqa: FBT001
    ) -> SpotifyAmbientData:
        """Generates spotify music data."""
        artist_id = self._create_spotify_id(False, "artist")  # noqa: FBT003
        track_id = self._create_spotify_id(False, "track")  # noqa: FBT003
        device_type = random.choice(self.DEVICES)  # noqa: S311

        if "ambient_music" in self.selected_md:
            music_dict = self.selected_md["ambient_music"]
            if "track_name" in music_dict:
                track_id = self._create_spotify_id(
                    is_truth_file,
                    "track",
                    music_dict["track_name"],
                )
            if "artist_name" in music_dict:
                artist_id = self._create_spotify_id(
                    is_truth_file,
                    "artist",
                    music_dict["artist_name"],
                )
            if "device_type" in music_dict and is_truth_file:
                device_type = self._choose_random_element(
                    is_truth_file,
                    music_dict["device_type"],
                    self.DEVICES,
                )

        return SpotifyAmbientData(
            **base_md.dict(),
            track_id = track_id,
            artist_id = artist_id,
            device_name= "My " + device_type,
            device_type= device_type,
            shuffle_state= random.choice([True, False]),  # noqa: S311
            repeat_state = random.choice(["track", "context", "off"]),  # noqa: S311
            danceability= self._generate_spotify_score(),
            energy=self._generate_spotify_score(),
            valence=self._generate_spotify_score(),
            instrumentalness=self._generate_spotify_score(),
            acousticness=self._generate_spotify_score(),
        )

    def _create_spotify_id(
            self,
            is_truth_file: bool,  # noqa: FBT001
            prefix:str,
            name:str | None = None,
    ) -> str:
        """Generates the spotify artist or track id."""
        heading = "spotify:" + prefix + ":"
        if is_truth_file:
            changed_name = name.replace(" ", "")
            digits = 22 - len(changed_name)
            space_filler = "0" * digits
            return heading + changed_name + space_filler
        return heading + "".join(
            random.choices(string.ascii_letters + string.digits, k=22),  #  noqa: S311
        )

    def _generate_spotify_score(self, lower:float = 0.000, upper: float = 1.000) -> float:
        """Generate a random spotify score for the given track."""
        return round(random.uniform(lower, upper), 3)  # # noqa: S311

    def _generate_general_music_data(
    self,
    record_kwargs: IndalekoRecordDataModel,
    is_truth_file: bool,  # noqa: FBT001
    timestamps: dict[str, datetime],
    ) -> AmbientMusicData:
        """Generates the general music activity context data."""
        faker = Faker()

        # generate basic semantic attributes
        timestamp = self._generate_ac_timestamp(is_truth_file, timestamps, "ambient_music")
        track_name, album_name, artist_name = faker.first_name(), faker.name(), faker.name()
        track_duration_ms = random.randint(  # noqa: S311
            MusicActivityData.TRACK_MIN_DURATION, MusicActivityData.TRACK_MAX_DURATION,
        )
        playback_position_ms = random.randint(0, track_duration_ms)  # # noqa: S311
        source = random.choice(self.MUSIC_SOURCES)  # noqa: S311
        bool_values = [True, False]
        is_playing = random.choice(bool_values)  # # noqa: S311

        if "ambient_music" in self.selected_md:
            music_dict = self.selected_md["ambient_music"]

            if "source" in music_dict:
                source = self._choose_random_element(
                    is_truth_file,
                    music_dict["source"],
                    self.MUSIC_SOURCES,
                )
            if is_truth_file:
                track_name = music_dict.get("track_name", track_name)
                artist_name = music_dict.get("artist_name", artist_name)
                album_name = music_dict.get("album_name", album_name)
                is_playing = music_dict.get("is_playing", is_playing)
                track_duration_ms = music_dict.get("track_duration_ms", track_duration_ms)
                playback_position_ms = music_dict.get("playback_position_ms", playback_position_ms)

                if "track_duration_ms" in music_dict and "playback_position_ms" not in music_dict:
                    playback_position_ms = random.randint(0, track_duration_ms)  # # noqa: S311
                elif "playback_position_ms" in music_dict and "track_duration_ms" not in music_dict:
                    track_duration_ms = random.randint(  # noqa: S311
                        playback_position_ms,
                        MusicActivityData.TRACK_MAX_DURATION,
                    )


        # generate semantic attributes
        semantic_attributes = [
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=uuid.uuid4(),
                    Label="track_name",
                ), Data=track_name,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=uuid.uuid4(),
                    Label="artist_name",
                ), Data=artist_name,
            ),
        ]

        return AmbientMusicData(
            Record=record_kwargs,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes,
            source=source,
            track_name=track_name,
            artist_name=artist_name,
            album_name=album_name,
            is_playing=is_playing,
            playback_position_ms=playback_position_ms,
            track_duration_ms=track_duration_ms,
        )

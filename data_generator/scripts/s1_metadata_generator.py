"""Metadata generator."""
import json
import os
import random
import sys

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from icecream import ic

# ruff: noqa: S311,FBT001,FBT002

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from data_generator.scripts.metadata.geo_activity_metadata import GeoActivityData
from data_generator.scripts.metadata.machine_config_metadata import MachineConfigMetadata
from data_generator.scripts.metadata.metadata import Metadata
from data_generator.scripts.metadata.music_activity_metadata import MusicActivityData
from data_generator.scripts.metadata.posix_metadata import PosixMetadata
from data_generator.scripts.metadata.semantic_metadata import SemanticMetadata
from data_generator.scripts.metadata.temp_activity_metadata import TempActivityData


# pylint: enable=wrong-import-position


# Named tuples for fetching results
DataGeneratorResults = NamedTuple("Results", [
    ("record", list),
    ("semantics", list),
    ("geo_activity", list),
    ("temp_activity", list),
    ("music_activity", list),
    ("machine_config", list),
])

MetadataResults = NamedTuple("MetadataResults", [
    ("all_records_md", list),
    ("all_geo_activity_md", list),
    ("all_temp_activity_md", list),
    ("all_music_activity_md", list),
    ("all_machine_config_md", list),
    ("all_semantics_md", list),
    ("stats", dict),
])


class Dataset_Generator:  # noqa: N801
    """Metadata Dataset Generator for given dictionary."""

    def __init__(self, config: dict,
                default_lower_timestamp: datetime | None = None,
                default_upper_timestamp: datetime | None = None,
                default_lower_filesize: int  = 1,
                default_upper_filesize: int = 10737418240) -> None:
        """
        A metadata dataset generator for creating synthetic dataset given a query.

        Args:
            config (dict): dictionary of the config attributes
            default_lower_timestamp (datetime): the datetime specifying the lower
                bound for timestamp generation
            default_upper_timestamp (datetime): the datetime specifying the upper
                bound for timestamp generation
            default_lower_filesize (int): the lower bound for file size generation in bytes
            default_upper_filesize (int): the upper bound for file size generation in bytes
        """
        if default_lower_timestamp is None:
            default_lower_timestamp = datetime(2000, 10, 25, tzinfo=UTC)
        if default_upper_timestamp is None:
            default_upper_timestamp = datetime.now(UTC)
        self.n_metadata_records = config["n_metadata_records"]
        self.n_matching_queries = config["n_matching_queries"]
        self.default_lower_timestamp = default_lower_timestamp
        self.default_upper_timestamp = default_upper_timestamp
        self.default_lower_filesize = default_lower_filesize
        self.default_upper_filesize = default_upper_filesize

        self.truth_list = []
        self.filler_list = []

        self.selected_AC_md = None
        self.selected_semantic_md = None
        self.selected_POSIX_md = None

        self.posix_generator = None
        self.temp_activity_generator = None
        self.music_activity_generator = None
        self.geo_activity_generator = None
        self.semantic_generator = None
        self.machine_config_generator = None
        self.has_semantic_truth = False

        self.truth_attributes = None
        self.truth_like_num = 0

    def write_json(self, dataset: dict, path: Path | str, json_path: Path | str) -> None:
        """Writes the generated metadata to a json file."""
        with Path(path / json_path).open("w", encoding="utf-8") as json_file:
            json.dump(dataset, json_file, indent=4)

    def initialize_dict(self, selected_md_attributes: dict) -> None:
        """""Initializes the dictionaries for each metadata."""
        self.selected_POSIX_md = selected_md_attributes.get("Posix", {})
        self.selected_AC_md = selected_md_attributes.get("Activity", {})
        self.selected_semantic_md = selected_md_attributes.get("Semantic", {})

        self.posix_generator = PosixMetadata(
            self.selected_POSIX_md,
            self.default_lower_filesize,
            self.default_upper_filesize,
            self.default_lower_timestamp,
            self.default_upper_timestamp,
        )
        self.temp_activity_generator = TempActivityData(self.selected_AC_md)
        self.music_activity_generator = MusicActivityData(self.selected_AC_md)
        self.geo_activity_generator = GeoActivityData(self.selected_AC_md)
        self.semantic_generator = SemanticMetadata(self.selected_semantic_md)
        self.machine_config_generator = MachineConfigMetadata()

    def generate_metadata_dataset(
            self,
            selected_md_attributes: dict[str, Any],
            save_files: bool = False,  # noqa: FBT001, FBT002
            path: Path | str | None = None) -> MetadataResults:
        """Main function to generate metadata datasets."""
        # set dictionaries for each metadata:
        self.initialize_dict(selected_md_attributes)
        if self.selected_semantic_md:
            self.has_semantic_truth = True

        # calculate the total number of truth metadata attributes
        self.truth_attributes = (self._return_key_attributes(self.selected_POSIX_md) +
                                self._return_key_attributes(self.selected_AC_md) +
                                self._return_key_attributes(self.selected_semantic_md)
                                )

        total_truth_attributes = len(self.truth_attributes)

        remaining_files = self.n_metadata_records - self.n_matching_queries

        # only create truth-like metadata if the number of attributes is greater than one
        if total_truth_attributes > 1:
            self.truth_like_num = random.randint(0, remaining_files)  # noqa: S311
        else:
            self.truth_like_num = 0

        filler_num = remaining_files - self.truth_like_num
        truth = self._generate_metadata(0, self.n_matching_queries+1, "Truth File", True, False)  # noqa: FBT003
        filler = self._generate_metadata(
            self.truth_like_num,
            filler_num+1,
            "Filler File",
            False,  # noqa: FBT003
            False,  # noqa: FBT003
        )
        truth_like_filler = self._generate_metadata(
            0,
            self.truth_like_num+1,
            "Filler Truth-Like File",
            False,   # noqa: FBT003
            True,  # noqa: FBT003
        )

        all_record = truth.record + truth_like_filler.record + filler.record
        all_semantics = truth.semantics + truth_like_filler.semantics + filler.semantics
        all_geo_activity = truth.geo_activity + truth_like_filler.geo_activity + filler.geo_activity
        all_temp_activity = (
            truth.temp_activity + truth_like_filler.temp_activity + filler.temp_activity
        )
        all_music_activity = (
            truth.music_activity + truth_like_filler.music_activity + filler.music_activity
        )
        all_machine_config = (
            truth.machine_config + truth_like_filler.machine_config + filler.machine_config
        )

        metadata_stats = {
            "truth": self.n_matching_queries,
            "filler": remaining_files,
            "truth_like": self.truth_like_num,
        }

        if save_files:
            # save the resulting dataset to a json file for future reference
            self.write_json(all_record, path, "records.json")
            self.write_json(all_geo_activity, path, "geo_activity.json")
            self.write_json(all_music_activity, path, "music_activity.json")
            self.write_json(all_temp_activity, path, "temp_activity.json")
            self.write_json(all_machine_config, path, "machine_config.json")
            self.write_json(all_semantics, path, "semantics.json")

        return MetadataResults(
            all_record, all_geo_activity, all_temp_activity, all_music_activity,
            all_machine_config, all_semantics, metadata_stats,
        )


    def _return_key_attributes(self, dictionary: dict[str, Any]) -> list[str]:
        """Checks and return the keys of the dictionary as a list."""
        if dictionary is None:
            return []
        return list(dictionary.keys())

    def _add_truth_names(self, file_name: str, is_truth_file: bool) -> None:  # noqa: FBT001
        if is_truth_file:
            self.truth_list.append(file_name)
        else:
            self.filler_list.append(file_name)

    def _generate_metadata(
            self,
            current_filenum: int,
            max_num: int,
            key: str,
            is_truth_file: bool,  # noqa: FBT001
            truth_like: bool,  # noqa: FBT001
    ) -> DataGeneratorResults:
        """
        Generates Metadata.

        Generates the target metadata with the specified attributes based on
        the number of matching queries from config.
        """
        all_metadata, all_semantics, all_geo_activity = [], [], []
        all_temp_activity, all_music_activity, all_machine_configs = [], [], []

        for file_num in range(1, max_num):
            truthlike_attributes = self._get_truthlike_attributes(truth_like)
            key_name = self._generate_key_name(key, file_num, truth_like, truthlike_attributes)
            has_semantic_filler = self._has_semantic_attr(truthlike_attributes)

            file_size, file_name, path, URI, IO_UUID = self.posix_generator.generate_file_info(  # noqa: N806
                current_filenum, file_num, is_truth_file, truth_like, truthlike_attributes,
                self.has_semantic_truth, has_semantic_filler,
            )

            self._add_truth_names(IO_UUID, is_truth_file)

            timestamps = self.posix_generator.generate_timestamps_md(
                is_truth_file,
                truth_like,
                truthlike_attributes,
            )

            attribute = self.posix_generator.generate_file_attributes(
                file_name,
                path,
                timestamps,
                file_size,
            )
            record_data = self.posix_generator.generate_record_data(IO_UUID, attribute)

            i_object = self.posix_generator.generate_metadata(
                record_data=record_data, 
                IO_UUID=IO_UUID, 
                timestamps=timestamps, 
                URI=URI, 
                file_size=file_size, 
                semantic_attributes_data=None, 
                key_name=key_name,
                local_identifier=current_filenum + file_num, 
                path=path
            )

            name, extension = file_name.split(".")

            semantic = self.semantic_generator.generate_metadata(
                record_data=record_data,
                IO_UUID=IO_UUID,
                extension=extension,
                last_modified=timestamps["modified"].strftime("%Y-%m-%dT%H:%M:%S"),
                file_name=name,
                is_truth_file=is_truth_file,
                truth_like=truth_like,
                truthlike_attributes=truthlike_attributes,
                has_semantic_filler=has_semantic_filler
            )

            geo_activity = self.geo_activity_generator.generate_metadata(
                record_data=record_data, 
                timestamps=timestamps, 
                is_truth_file=is_truth_file, 
                truth_like=truth_like, 
                truthlike_attributes=truthlike_attributes
            )

            temp_activity = self.temp_activity_generator.generate_metadata(
                record_kwargs=record_data, 
                timestamps=timestamps, 
                is_truth_file=is_truth_file, 
                truth_like=truth_like, 
                truthlike_attributes=truthlike_attributes
            )

            music_activity = self.music_activity_generator.generate_metadata(
                record_kwargs=record_data, 
                timestamps=timestamps, 
                is_truth_file=is_truth_file, 
                truth_like=truth_like, 
                truthlike_attributes=truthlike_attributes
            )

            machine_config = self.machine_config_generator.generate_metadata(record=record_data)

            # Append generated objects to their respective lists
            all_metadata.append(Metadata.return_JSON(i_object))
            all_semantics.append(Metadata.return_JSON(semantic))
            all_geo_activity.append(Metadata.return_JSON(geo_activity))
            all_temp_activity.append(Metadata.return_JSON(temp_activity))
            all_music_activity.append(Metadata.return_JSON(music_activity))
            all_machine_configs.append(Metadata.return_JSON(machine_config))

        return DataGeneratorResults(
            all_metadata, all_semantics, all_geo_activity, all_temp_activity,
            all_music_activity, all_machine_configs,
        )

    def _generate_key_name(
            self,
            key: str,
            n: int,
            truth_like: bool,  # noqa: FBT001
            truthlike_attributes: list[str],
    ) -> str:
        """Generates the key name for the metadata."""
        key_name = f"{key} #{n}"
        if truth_like:
            key_name += f", truth-like attributes: {truthlike_attributes}"
        return key_name

    def _has_semantic_attr(self, truthlike_attributes: dict) -> bool:
        """Checks whether there are any semantic attributes populated."""
        return any(attr.startswith("Content_") for attr in truthlike_attributes)


    def _get_truthlike_attributes(self, truth_like: bool) -> list[str]:  # noqa: FBT001
        """Returns a list of randomly selected truthlike attributes."""
        if truth_like:
            num_truthlike_attributes = random.randint(1, len(self.truth_attributes) -1)  # noqa: S311
            selected_truth_like_attr = random.sample(
                self.truth_attributes,
                k = num_truthlike_attributes,
            )
            return self._check_special_case(selected_truth_like_attr, num_truthlike_attributes)
        return []

    def _check_special_case(
            self,
            selected_truth_like_attr: list[str],
            num_truthlike_attributes: int,
    ) -> list[str]:
        """Checks special case when there is semantic data queried but no text file extension."""
        is_all_text = self._check_truth_all_text()
        # If a semantic is not available i.e. file name is not chosen but
        # Content is but file name specifies all text
        if not self._check_semantic_available(selected_truth_like_attr, is_all_text):
            # Case 1: Only posix (file name) and semantic specified in
            # dictionary -> only file name allowed
            if (
                len(self.selected_AC_md) == 0 and
                len(self.selected_POSIX_md) == 1 and
                len(self.selected_semantic_md) == 1
            ):
                return ["file.name"]
            # Case 2: Other posix and semantic are availabe
            if len(self.selected_POSIX_md) >= 1 and len(self.selected_semantic_md) >= 1:
                if num_truthlike_attributes == len(self.truth_attributes) - 1:
                    selected_truth_like_attr = [
                        item for item in selected_truth_like_attr if "Content_" not in item
                    ]
                selected_truth_like_attr.append("file.name")
        return selected_truth_like_attr

    def _check_truth_all_text(self) -> bool:
        """Checks whether all metadata queried are all text files."""
        if ("file.name" in self.selected_POSIX_md and
            "extension" in self.selected_POSIX_md["file.name"]
        ):
            true_extension = self.selected_POSIX_md["file.name"]["extension"]
            if set(Metadata.TEXT_FILE_EXTENSIONS) == set(true_extension):
                return True
        return False

    def _check_semantic_available(
            self,
            selected_truth_attributes: list[str],
            is_all_text: bool,  # noqa: FBT001
        ) -> bool:
        """Check if semantic available in the truth like filler metadata."""
        return not (is_all_text and
                    "file.name" not in selected_truth_attributes and
                    any("Content_" in item for item in selected_truth_attributes)
        )


def main() -> None:
    """Main function to test the metadata generator."""
    selected_md_attributes = {
        "Activity": {
            "ambient_music": {
                "track_name": "Happy",
                "timestamp": "birthtime",
            },
        },
    }

    config_path = "data_generator/config/dg_config.json"
    with Path(config_path).open(encoding="utf-8") as file:
        config = json.load(file)
    data_generator = Dataset_Generator(config)
    result = data_generator.generate_metadata_dataset(selected_md_attributes)
    ic(result.all_semantics_md)

if __name__ == "__main__":
    main()

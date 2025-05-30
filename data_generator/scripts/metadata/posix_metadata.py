"""Generate POSIX metadata."""
import random
import re
import string
import uuid

from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from faker import Faker

from data_generator.scripts.metadata.metadata import Metadata
from data_models.i_object import IndalekoObjectDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestampDataModel


faker = Faker()


class PosixMetadata(Metadata):
    """
    Subclass for Metadata.

    Generates Posix Metadata based on the given dictionary of queries.
    """
    ALL_EXTENSIONS = (
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".rtf",
        ".xls",
        ".xlsx",
        ".csv",
        ".ppt",
        ".pptx",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".tif",
        ".mov",
        ".mp4",
        ".avi",
        ".mp3",
        ".wav",
        ".zip",
        ".rar",
    )

    def __init__(
            self,
            selected_posix_md,
            default_lower_filesize=1,
            default_upper_filesize=10737418240,
            default_lower_timestamp=None,
            default_upper_timestamp=None,
    ) -> None:
        """Initialize the object."""
        super().__init__(selected_posix_md)
        self.earliest_endtime = []
        self.earliest_starttime = []
        selected_posix_md = self.preprocess_dictionary_timestamps(False)  # noqa: FBT003
        self.default_lower_filesize = default_lower_filesize
        self.default_upper_filesize = default_upper_filesize
        
        # Set default timestamp values if none provided
        if default_lower_timestamp is None:
            self.default_lower_timestamp = datetime(2000, 10, 25, tzinfo=UTC)
        else:
            self.default_lower_timestamp = default_lower_timestamp
            
        if default_upper_timestamp is None:
            self.default_upper_timestamp = datetime.now(UTC)
        else:
            self.default_upper_timestamp = default_upper_timestamp
            
        # Initialize the directory path
        self.saved_directory_path = self.initialize_local_dir()

    def generate_metadata(self, **kwargs: dict) -> IndalekoObjectDataModel:
        """"Generates metadata specific to the subclass."""
        record_data = kwargs["record_data"]
        io_uuid = kwargs["IO_UUID"]
        timestamps = kwargs["timestamps"]
        uri = kwargs["URI"]
        file_size = kwargs["file_size"]
        semantic_attributes_data = kwargs["semantic_attributes_data"]
        key_name = kwargs["key_name"]
        local_identifier = kwargs["local_identifier"]
        path = kwargs["path"]
        return self._generate_i_object_data(
            record_data,
            io_uuid,
            timestamps,
            uri,
            file_size,
            semantic_attributes_data,
            key_name,
            local_identifier,
            path,
        )


    def generate_file_info(
        self,
        current_filenum: int,
        n: int,
        is_truth_file: bool,  # noqa: FBT001
        truth_like: bool,  # noqa: FBT001
        truthlike_attributes: list[str],
        has_semantic_truth: bool,  # noqa: FBT001
        has_semantic_filler: bool,  # noqa: FBT001
    ) -> tuple[int, str, str, str, str]:
        """Generates the information required for the posix metadata."""
        is_truth_size = self._define_truth_attribute(
            "file.size",
            is_truth_file,
            truth_like,
            truthlike_attributes,
        )
        is_truth_name = self._define_truth_attribute(
            "file.name",
            is_truth_file,
            truth_like,
            truthlike_attributes,
        )
        is_truth_dir = self._define_truth_attribute(
            "file.directory",
            is_truth_file,
            truth_like,
            truthlike_attributes,
        )

        file_size = self._generate_file_size(is_truth_size)
        file_name = self._generate_file_name(is_truth_name, has_semantic_truth, has_semantic_filler)
        path, uri, updated_filename = self._generate_dir_location(file_name, is_truth_dir)
        io_uuid = self._create_metadata_uuid(current_filenum + n, is_truth_file)

        return file_size, updated_filename, path, uri, io_uuid

    def generate_file_attributes(
        self,
        file_name: str,
        path: str,
        timestamps: dict[str, datetime],
        file_size: int,
    ) -> dict[str, Any]:
        """Generates the dictionary of file attributes."""
        birthtime = timestamps["birthtime"].timestamp()
        modified_time = timestamps["modified"].timestamp()
        access_time = timestamps["accessed"].timestamp()
        changed_time = timestamps["changed"].timestamp()
        return {
            "Name": file_name,
            "Path": path,
            "st_birthtime": str(birthtime),
            "st_birthtime_ns": str(birthtime * 10**9),
            "st_mtime": str(modified_time),
            "st_mtime_ns": str(modified_time * 10**9),
            "st_atime": str(access_time),
            "st_atime_ns": str(access_time * 10**9),
            "st_ctime": str(changed_time),
            "st_ctime_ns": str(changed_time * 10**9),
            "st_size": file_size,
        }

    def generate_record_data(
        self,
        io_uuid: str,
        attribute: dict[str, Any],
    ) -> IndalekoRecordDataModel:
        """Generates the record data."""
        id_source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=io_uuid,
            Version="1.0",
            Description="Record UUID",
        )

        return IndalekoRecordDataModel(
            SourceIdentifier=id_source_identifier,
            Timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            Attributes=attribute,
            Data=self._generate_random_data(),
        )

    def _generate_i_object_data(
            self,
            record_data: IndalekoRecordDataModel,
            io_uuid: str,
            timestamps: dict[str, str],
            uri: str,
            file_size: int,
            _semantic_attributes_data: list[dict[str, Any]],
            key_name: str,
            local_identifier: str,
            local_path: str,
            ) -> IndalekoObjectDataModel:
        """Returns the Indaleko object created form the data model."""
        timestamp_data = self._create_timestamp_data(io_uuid, timestamps)

        return IndalekoObjectDataModel(
                Record=record_data,
                URI = uri,
                ObjectIdentifier=uuid.uuid4(),
                Timestamps=timestamp_data,
                Size = file_size,
                SemanticAttributes= None,
                Label = key_name,
                LocalPath= local_path,
                LocalIdentifier=str(local_identifier),
                Volume=uuid.uuid4(),
                PosixFileAttributes="S_IFREG",
                WindowsFileAttributes="FILE_ATTRIBUTE_ARCHIVE")

    def initialize_local_dir(self) -> dict[str, Any]:
        """
        Initializes and saves the local directories to self.saved_directory_path.

        Run only once

        returns self.saved_directory_path = {
            "truth.directory": {
                "path": str, "files": Counter(str)},
                "filler.directory" {"path":, "files": Counter(str)}: list}
            }.
        """
        num_directories = random.randint(3, 8)  # noqa: S311
        max_depth = random.randint(3, 5)  # noqa: S311
        parent_dir = "/home/user"
        truth_parent_loc = ""
        # if the there is a query related to the directory and the pathing
        # has not been initialized create the directories
        if "file.directory" in self.selected_md:
            truth_parent_loc = self.selected_md["file.directory"]["location"]
            if truth_parent_loc == "local":
                truth_path_name = self.selected_md["file.directory"]["local_dir_name"]
                # if the is_truth_file is a truth file, create path for truth file directories
                return self._generate_local_path(
                    parent_dir,
                    num_directories,
                    max_depth,
                    directory_name=truth_path_name,
                )
            # if remote  just generate random directory
            return self._generate_local_path(parent_dir, num_directories, max_depth)
        # no queries related to file directories; generate random directory
        return self._generate_local_path(parent_dir, num_directories, max_depth)

    # helper for initialize_local_dir():
    def _generate_local_path(
        self,
        base_dir: str,
        num_directories: int,
        max_depth: int,
        directory_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate local path.

        Generate random path to directories within a parent dir based on base_dir,
        num_directories, max_depth and if available, directory_name recursively

        Only runs once during initialization.
        Adapted from Tony's code from metadata.py.
        """
        saved_directory_path = {"truth.directory": {}, "filler.directory": {}}
        directory_count = 0
        # List to store generated paths
        generated_paths = []

        def create_dir_recursive(current_dir: Path | str , current_depth: int) -> None:
            """Create directories recursively."""
            nonlocal directory_count
            if current_depth > max_depth or directory_count >= num_directories:
                return

            if num_directories - directory_count > 0:
                max_subdirs = max(
                    1,
                    (num_directories - directory_count) // (max_depth - current_depth + 1),
                )
                subdirs = random.randint(1, max_subdirs)  #  noqa: S311

                for _ in range(subdirs):
                    directory_count += 1
                    if directory_count >= num_directories:
                        break
                    # Generate a random subdirectory name or choose truth file path name
                    subdir_name = "".join(
                        random.choices(  # noqa: S311
                            string.ascii_lowercase,
                            k=random.randint(1, 8)),  # noqa: S311
                    )
                    subdir_path = Path(current_dir) / subdir_name
                    generated_paths.append(subdir_path)
                    create_dir_recursive(subdir_path, current_depth + 1)

        create_dir_recursive(base_dir, 1)

        if directory_name is not None:
            saved_directory_path["truth.directory"]["path"] = (
                random.choice(generated_paths) + "/" + directory_name  # noqa: S311
            )
            saved_directory_path["truth.directory"]["files"] = Counter()
        saved_directory_path["filler.directory"]["path"] = generated_paths
        saved_directory_path["filler.directory"]["files"] = Counter()
        return saved_directory_path

    def _generate_file_name(  # noqa: PLR0912
        self,
        is_truth_file: bool,  # noqa: FBT001
        has_semantic_truth: bool, # noqa: FBT001
        has_semantic_filler: bool, # noqa: FBT001
    ) -> str:
        """
        Generates a file_name for given file.

        Args: is_truth_file (bool): the type of file it is
             self.selected_md{file.name: {"pattern":str, "command":str, "extension":str}}
            commands include: "starts", "ends", "contains"
        Return (str): returns the file name with extension attached.
        """
        command, pattern = "", ""
        true_extension = None
        n_filler_letters = random.randint(1, 10)  # noqa: S311
        file_extension = list(self.ALL_EXTENSIONS)
        default_command = "exactly"
        # if the file name is part of the query,
        # extract the appropriate attributes and generate title
        if "file.name" in self.selected_md :
            if "pattern" in self.selected_md ["file.name"]:
                pattern = self.selected_md ["file.name"]["pattern"]
                command = self.selected_md["file.name"].get("command", default_command)
                avail_text_file_extension = Metadata.TEXT_FILE_EXTENSIONS

            if "extension" in self.selected_md["file.name"]:
                true_extension = self.selected_md["file.name"]["extension"]
                if isinstance(true_extension, list):
                    file_extension = list(set(file_extension) - set(true_extension))
                    assert file_extension, "file_extension is empty!"  # noqa: S101
                    avail_text_file_extension = list(
                        set(Metadata.TEXT_FILE_EXTENSIONS) - set(true_extension),
                    )
                else:
                    file_extension.remove(true_extension)
                    if true_extension in Metadata.TEXT_FILE_EXTENSIONS:
                        avail_text_file_extension.remove(true_extension)

            if is_truth_file:
                # choose file extension
                if (
                    "extension" in self.selected_md["file.name"]
                ):  # if no extension specified, then randomly select a file extension
                    if isinstance(true_extension, list):
                        true_extension = random.choice(true_extension)  # noqa: S311
                elif has_semantic_truth:  # if semantic content exists, then should be a text file
                    true_extension = random.choice(Metadata.TEXT_FILE_EXTENSIONS)  # noqa: S311
                else:
                    true_extension = random.choice(file_extension)  # noqa: S311

                # create file name based on commands
                return_pattern = "".join(
                        random.choices(  # noqa: S311
                            string.ascii_letters,
                            k=n_filler_letters,
                        ),
                ) + true_extension

                match(command):
                    case "exactly":
                        return_pattern = pattern + true_extension
                    case "starts":
                        return_pattern = (
                            pattern
                            + "".join(
                                random.choices(  # noqa: S311
                                    string.ascii_letters,
                                    k=n_filler_letters,
                                ),
                            )
                            + true_extension
                        )
                    case "ends":
                        return_pattern = (
                            "".join(
                                random.choices(  # noqa: S311
                                    string.ascii_letters,
                                    k=n_filler_letters,
                                ),
                            )
                            + pattern
                            + true_extension
                        )
                    case "contains":
                        return_pattern = (
                            "".join(
                                random.choices(  # noqa: S311
                                    string.ascii_letters,
                                    k=n_filler_letters,
                                ),
                            )
                            + pattern
                            + "".join(
                                random.choices(  # noqa: S311
                                    string.ascii_letters,
                                    k=n_filler_letters,
                                ),
                            )
                            + true_extension
                        )
                return return_pattern

            if has_semantic_filler:
                extension = random.choice(avail_text_file_extension)  # noqa: S311
            else:
                extension = random.choice(file_extension)  # noqa: S311

            allowed_pattern = list(
                set(string.ascii_letters) - set(pattern.upper()) - set(pattern.lower()),
            )
            return "".join(
                    random.choices(  # noqa: S311
                    allowed_pattern, k=n_filler_letters,
                ),
            ) + extension

        # if no query specified for title, but semantic context exists, choose a text file extension
        if has_semantic_filler or (is_truth_file and has_semantic_truth):
            extension = random.choice(Metadata.TEXT_FILE_EXTENSIONS)  # noqa: S311
        else:  # randomly create a title with any extension
            extension = random.choice(file_extension)  # noqa: S311
        return "".join(random.choices(string.ascii_letters, k=n_filler_letters)) + extension  # noqa: S311

    def _generate_dir_location(
        self,
        file_name: str,
        is_truth_file: bool = True,  # noqa: FBT001,FBT002
    ) -> tuple[str, str, str]:
        """
        Generates a directory location for the metadata.

        self.selected_md ["file.directory"] = [location, directory_name (optional, for local only)]
        location: where it is stored; local or remote (google drive, drop box, icloud, local)
        RETURN: list consisting of path and URI and updated file name to remote or local storage.

        """
        # URIs/URLs to local computer or cloud storage services
        file_locations = {
            "google_drive": "https://drive.google.com",
            "dropbox": "https://www.dropbox.com",
            "icloud": "https://www.icloud.com",
            "local": "file:/",
        }
        # RUN after initialization:
        if "file.directory" in self.selected_md  and is_truth_file:
            truth_parent_loc = self.selected_md ["file.directory"]["location"]
            if truth_parent_loc == "local": # if file dir specified, create truth file at that dir
                file_counter = self.saved_directory_path["truth.directory"]["files"]
                path = self.saved_directory_path["truth.directory"]["path"] + "/"
                counter_key = path + file_name
                if counter_key in file_counter:
                    file_counter[counter_key] += 1
                    updated_file_name = self._change_name(
                        file_name=file_name,
                        count=file_counter[counter_key],
                    )
                    path += updated_file_name
                    uri = file_locations[truth_parent_loc] + path
                    return [path, uri, updated_file_name]
                file_counter.update({counter_key: 0})
                path += file_name
                uri = file_locations[truth_parent_loc] + path
                return [path, uri, file_name]

            if (
                is_truth_file and truth_parent_loc in file_locations
            ):  # if remote dir specified, create file at that dir
                path = self._generate_remote_path(truth_parent_loc, file_name)
                uri = file_locations[truth_parent_loc] + path
            return [path, uri, file_name]

        # for filler files or truth files with no file attributes specified
        if not is_truth_file and "file.directory" in self.selected_md:
            truth_parent_loc = self.selected_md["file.directory"]["location"]
            del file_locations[truth_parent_loc]

        # not queried at this point and file type doesn't matter;
        # generate any file path (local or remote)
        random_location = random.choice(list(file_locations.keys()))   # noqa: S311
        if random_location == "local":
            file_counter = self.saved_directory_path["filler.directory"]["files"]
            chosen_path = random.choice(  # noqa: S311
                self.saved_directory_path["filler.directory"]["path"],
            )
            path = str(chosen_path) + "/"
            counter_key = path + file_name
            if counter_key in file_counter:
                file_counter[counter_key] += 1
                updated_file_name = self._change_name(
                    file_name=file_name,
                    count=file_counter[counter_key],
                )
                path += updated_file_name
                uri = file_locations[random_location] + path
                return [path, uri, updated_file_name]
            file_counter.update({counter_key: 0})
            path += file_name
            uri = file_locations[random_location] + path
            return [path, uri, file_name]
        path = self._generate_remote_path(random_location, file_name)
        uri = file_locations[random_location] + path

        return path, uri, file_name

    def _change_name(self, file_name:str, count:int) -> str:
        """Change name.

        Changes name to avoid duplicate files in the same path in the
        format 'duplicateName (#).extension.
        """
        path = Path(file_name)
        base_name = path.stem
        ext = path.suffix
        return f"{base_name} ({count}){ext}"

    # helper functions for generate_dir_location
    def _generate_remote_path(self, service_type: str, file_name: str) -> str:
        """Generates path to a remote file location e.g., google drive, dropbox, icloud."""
        list_alphanum = string.ascii_letters + string.digits
        # Randomly choose characters to form the id
        file_id = "".join(random.choices(list_alphanum, k=random.randint(3, 6)))   # noqa: S311
        local_file_locations = {
            "google_drive": "/file/d/{file_id}/view/view?name={file_name}",
            "dropbox": "/s/{file_id}/{file_name}?dl=0",
            "icloud": "/iclouddrive/{file_id}/{file_name}",
        }
        return local_file_locations[service_type].format(
            file_id=file_id,
            file_name=file_name,
        )

    def generate_timestamps_md(
        self,
        is_truth_file: bool,  # noqa: FBT001
        truth_like_file: bool,  # noqa: FBT001
        truth_like_attributes: list[str],
    ) -> dict[str, datetime]:
        """Generates timestamps for the metadata."""
        is_truth_file = self._define_truth_attribute(
            "timestamps",
            is_truth_file,
            truth_like_file,
            truth_like_attributes,
        )
        return self._generate_timestamps(is_truth_file)

    def _generate_timestamps(
            self,
            is_truth_file: bool = True, # noqa: FBT001,FBT002
    ) -> dict[str, datetime]:
        """Generate timestamps.

        Generates birthtime, modifiedtime, accessedtime, and changedtime for the specified file:
            Args: is_truth_file (bool): file type
            Returns (Dict[str, datetime]): {birthtime: datetime, modifiedtime: datetime,
                accessedtime: datetime, changedtime: datetime}.
        """
        stamp_labels = {"modified", "accessed", "changed"}
        birthtime = None
        latest_timestamp_of_three = None
        timestamps = {}
        # check whether the query is pertaining to specific timestamp queries
        if "timestamps" in self.selected_md:
            query = self.selected_md ["timestamps"]
            selected_timestamps = set(query.keys())
            non_selected_timestamps = stamp_labels - selected_timestamps
            if (
                "birthtime" in query
            ):  #  checks for birthtime: other timestamps shouldn't be earlier than the birthtime
                birthtime_query = query["birthtime"]
                birthtime = self._generate_queried_timestamp(
                    birthtime_query["starttime"],
                    birthtime_query["endtime"],
                    default_startdate=self.default_lower_timestamp,
                    is_truth_file=is_truth_file,
                    is_birthtime=True,
                )
                timestamps["birthtime"] = birthtime
                # if there queries other than the birthtime, iterate over each of the timestamps
                for timestamp in stamp_labels:
                    if timestamp in selected_timestamps:
                        timestamps[timestamp] = self._generate_queried_timestamp(
                            query[timestamp]["starttime"],
                            query[timestamp]["endtime"],
                            default_startdate=birthtime,
                            is_truth_file=is_truth_file,
                        )
                    else:
                        # if type of timestamp not chosen, either generate a random timestamp
                        # within bounds or choose an existing timestamp
                        timestamps[timestamp] = self._choose_existing_random_timestamp(
                            timestamps,
                            birthtime,
                            self.default_upper_timestamp,
                        )
            else:
                # for each of the other timestamps, set the timestamp based on whether it has
                # been selected in the query or not
                for timestamp in selected_timestamps:
                    timestamps[timestamp] = self._generate_queried_timestamp(
                        query[timestamp]["starttime"],
                        query[timestamp]["endtime"],
                        default_startdate=self.default_lower_timestamp,
                        is_truth_file=is_truth_file,
                    )
                for timestamp in non_selected_timestamps:
                    timestamps[timestamp] = self._choose_existing_random_timestamp(
                        timestamps,
                        self.default_lower_timestamp,
                        self.default_upper_timestamp,
                    )

                # birthtime has to be <= to the other populated timestamps
                latest_timestamp_of_three = min(timestamps.values())
                birthtime = self._generate_random_timestamp(
                    lower_bound=self.default_lower_timestamp,
                    upper_bound=latest_timestamp_of_three,
                )
                timestamps["birthtime"] = birthtime

        else:
            birthtime = self._generate_random_timestamp(
                lower_bound=self.default_lower_timestamp,
                upper_bound=self.default_upper_timestamp,
            )
            timestamps["birthtime"] = birthtime
            for timestamp in stamp_labels:
                timestamps[timestamp] = self._choose_existing_random_timestamp(
                    timestamps,
                    birthtime,
                    self.default_upper_timestamp,
                )
        return timestamps

    # helper for _generate_timestamps:
    def _choose_existing_random_timestamp(
        self,
        timestamps: dict[str, datetime],
        lower_bound: datetime,
        upperbound: datetime,
    ) -> datetime:
        """Chooses an existing timstamp that is in the dict or creates a random timestamp."""
        randomtime = self._generate_random_timestamp(
            lower_bound=lower_bound,
            upper_bound=upperbound,
        )
        existing_timestamp = random.choice(list(timestamps.values()))  # noqa: S311
        return random.choice([existing_timestamp, randomtime])  # noqa: S311

    # helper functions for generate_timestamps():
    def _generate_random_timestamp(
        self,
        lower_bound: datetime,
        upper_bound: datetime,
    ) -> datetime:
        """
        Generates a random timestamp within the bounds specified.

        Args:
            lower_bound (datetime): The earliest possible timestamp.
            upper_bound (datetime): The latest possible timestamp.

        Returns:
            (datetime): A randomly generated timestamp.
        """
        return faker.date_time_between(
            start_date=lower_bound,
            end_date=upper_bound,
        )

    def _generate_queried_timestamp(  # noqa: C901,PLR0912,PLR0915
        self,
        starttime: datetime,
        endtime: datetime,
        default_startdate: datetime,
        is_truth_file: bool = True,  # noqa: FBT001,FBT002
        is_birthtime: bool = False,  # noqa: FBT001,FBT002
    ) -> datetime:
        """
        Generates a timestamp based on the queried starttime and endtime.

        Generates timestamp based on file type; default_truth_startdate is either the
        self.default_lower_timestamp or the birthtime (if birthtime already set).
        """
        filler_delta = 2
        time_delta = timedelta(hours=filler_delta)
        timestamp = None
        # check errors that can arise for str parameters
        if starttime > datetime.now(UTC) or endtime > datetime.now(UTC):
            raise ValueError(
                "The timestamp you have queried is in the future, please check again.",
            )
        if starttime > endtime:
            raise ValueError("The starttime cannot be more recent than the endtime")
        if is_truth_file and default_startdate > endtime:
            raise ValueError(
                "The default_startdate cannot be more recent than the endtime",
            )
        if self.default_lower_timestamp == self.default_upper_timestamp:
            raise ValueError(
                "The absolute lower bound date cannot be the same time as the date right now",
            )
        if self.default_lower_timestamp == starttime and self.default_upper_timestamp == endtime:
            raise ValueError(
                "Invalid range, please increase the bounds or "
                "decrease the range to within the bounds",
            )
        if is_birthtime and starttime > self.earliest_endtime[0]:
            raise ValueError(
                "The earliest starttime cannot be earlier than the birthtime starttime",
            )
        if self.default_lower_timestamp > starttime:
            raise ValueError(
                "The absolute lower bound cannot be greater than the starttime",
            )

        if starttime == endtime:
            if starttime < default_startdate:
                raise ValueError(
                    "The starttime for the timestamps cannot be earlier than the birthtime/default",
                )
            if is_truth_file and default_startdate <= starttime:
                timestamp = starttime
            if not is_truth_file:
                # for birthtime timestamps (choose the lowest/most earliest possible time to not
                # have time earlier than the other timestamps)
                lower = faker.date_time_between(
                    start_date=self.default_lower_timestamp,
                    end_date=starttime - time_delta,
                )
                upper = faker.date_time_between(start_date=starttime + time_delta)
                # the earliest starttime is within the bounds:
                if (
                    is_birthtime
                    and self.default_lower_timestamp + time_delta
                        <= self.earliest_starttime[0] <= starttime
                ):
                    timestamp = faker.date_time_between(
                        start_date=self.default_lower_timestamp,
                        end_date=self.earliest_starttime[0] - time_delta,
                    )
                # the earliest starttime is not within the bounds
                elif is_birthtime and (self.default_lower_timestamp + time_delta
                                       <= self.earliest_starttime[0]):
                    timestamp = faker.date_time_between(
                        start_date=starttime + time_delta,
                        end_date=self._find_next_earliest_endtime(starttime) - time_delta,
                    )
                elif is_birthtime:
                    raise ValueError(
                        "Cannot generate birthtime timestamp for truth file",
                    )
                # for timestamps other than birthtime:
                if not is_birthtime and default_startdate == starttime:
                    # if birthtime is greater than the equal
                    timestamp = faker.date_time_between(
                        start_date=default_startdate + timedelta(hours=filler_delta),
                    )
                elif not is_birthtime and default_startdate > starttime:
                    # if birthtime is greater than the equal
                    timestamp = faker.date_time_between(start_date=default_startdate)
                elif not is_birthtime and default_startdate < starttime:
                    lower = faker.date_time_between(
                        start_date=default_startdate,
                        end_date=starttime - time_delta,
                    )
                    if starttime + time_delta < self.default_upper_timestamp:
                        upper = faker.date_time_between(
                            start_date=starttime + time_delta,
                        )
                        timestamp = random.choice([upper, lower])  # noqa: S311
                    elif starttime + time_delta >= self.default_upper_timestamp:
                        timestamp = lower
                elif not is_birthtime:
                    raise ValueError("cannot form timestamp for filler file")
        # if the starttime and endtime are not equal and are not lists, then choose a date
        # within that range under the assumption that starttime < endtime
        elif starttime < endtime:  # if is a birthtime, should take on values that are
            # if it is a birthtime and a truth file, find the earliest time possible
            if (
                is_truth_file
                and is_birthtime
                and default_startdate <= starttime
                and starttime <= self.earliest_starttime[0] <= endtime
            ):
                timestamp = faker.date_time_between(
                    start_date=starttime,
                    end_date=self.earliest_starttime[0],
                )
            elif (
                is_truth_file
                and is_birthtime
                and default_startdate <= starttime
                and self.earliest_starttime[0] < starttime
            ):
                timestamp = faker.date_time_between(
                    start_date=starttime,
                    end_date=self._find_next_earliest_endtime(starttime),
                )
            elif is_truth_file and is_birthtime:
                raise ValueError("cannot generate truthfile timestamp.")

            if is_truth_file and not is_birthtime and starttime <= default_startdate <= endtime:
                timestamp = faker.date_time_between(
                    start_date=default_startdate,
                    end_date=endtime,
                )
            elif is_truth_file and not is_birthtime and starttime > default_startdate:
                timestamp = faker.date_time_between(
                    start_date=starttime,
                    end_date=endtime,
                )
            elif is_truth_file and not is_birthtime:
                raise ValueError(
                    "Absolute lower bound date cannot be more recent than the endtime",
                )

            if not is_truth_file:
                # for filler file birhttime timestamps:
                if (
                    is_birthtime
                    and self.default_lower_timestamp <= starttime - time_delta
                    and (self.default_lower_timestamp + time_delta <=
                         self.earliest_starttime[0] <=
                         starttime)
                ):
                    timestamp = faker.date_time_between(
                        start_date=self.default_lower_timestamp,
                        end_date=self.earliest_starttime[0] - time_delta,
                    )
                elif is_birthtime and self.default_upper_timestamp >= endtime + time_delta:
                    timestamp = faker.date_time_between(
                        start_date=endtime + time_delta,
                        end_date=self._find_next_earliest_endtime(starttime) - time_delta,
                    )
                elif is_birthtime and not is_truth_file:
                    raise ValueError(
                        "cannot generate birthtime timestamp for filler files",
                    )

                lower = faker.date_time_between(
                    start_date=default_startdate,
                    end_date=starttime - time_delta,
                )
                upper = faker.date_time_between(start_date=endtime + time_delta)
                # for none birthtime timestamps
                if not is_birthtime and endtime < default_startdate <= self.default_upper_timestamp:
                    timestamp = faker.date_time_between(start_date=endtime)
                elif not is_birthtime and starttime <= default_startdate <= endtime:
                    timestamp = upper
                elif not is_birthtime and (
                    self.default_lower_timestamp <= default_startdate <= starttime
                ):
                    timestamp = random.choice([lower, upper])  # noqa: S311
                elif not is_birthtime and not is_truth_file:
                    raise ValueError("Cannot generate timestamps for filler files")
        else:
            raise ValueError(
                "Error in parameters or command: Please check the query once more.",
            )
        return timestamp.replace(microsecond=0)

    def _find_next_earliest_endtime(self, starttime: datetime) -> datetime:
        for date in self.earliest_endtime:
            if starttime <= date:
                return date
            raise ValueError("there are no times that work")
        return None

    def _generate_file_size( # noqa: PLR0911,PLR0912
            self,
            is_truth_file: bool = True,# noqa: FBT001,FBT002
    ) -> int:
        """
        Creates random file size given the is_truth_file.

        self.selected_md {file.size: ["target_min", "target_max", "command"]}
        command includes "equal", "range".
        """
        if "file.size" in self.selected_md:
            filler_delta = 1
            delta = 0
            target_min = self.selected_md["file.size"]["target_min"]
            target_max = self.selected_md["file.size"]["target_max"]
            command = self.selected_md["file.size"]["command"]

            if target_max == (
                self.default_upper_filesize and
                target_min == self.default_lower_filesize
            ):
                raise ValueError(
                    "The range cannot be the whole boundary from ",
                    target_min,
                    " to ",
                    target_max,
                )
            if target_min > target_max:
                raise ValueError(
                    f"""
                    The target max {target_min} cannot be greater than the target max {target_max}
                    """,
                )

            # if the target_min/max is a list and is the same as the target_max
            # choose a random size from the list
            if isinstance(target_min, list) and isinstance(target_max, list) and command == "equal":
                if is_truth_file:
                    return random.choice(target_min)  # noqa: S311
                return self._check_return_value_within_range(
                    self.default_lower_filesize,
                    self.default_upper_filesize,
                    target_min[0],
                    target_min[-1],
                    random.randint,
                    1,
                )

            # if the target_min/max is not a list but is the same
            # as the target_max then just choose that file size
            if target_min == target_max and command == "equal":
                if is_truth_file:
                    return target_min
                return self._check_return_value_within_range(
                    self.default_lower_filesize,
                    self.default_upper_filesize,
                    target_min,
                    target_min,
                    random.randint,
                    1,
                )

            # if command specifies getting the range between two values
            if target_min != target_max and command == "range":
                if is_truth_file:
                    return random.randint(target_min, target_max)  # noqa: S311
                return self._check_return_value_within_range(
                    self.default_lower_filesize,
                    self.default_upper_filesize,
                    target_min,
                    target_max,
                    random.randint,
                    1,
                )

            # if command specifies a file greater than a certain size
            if isinstance(target_max, int) and "greater" in command:
                if command == "greater_than":
                    delta = 1
                    filler_delta = 0

                if is_truth_file:
                    return random.randint(  # noqa: S311
                        target_max + delta,
                        self.default_upper_filesize,
                    )
                return random.randint(  # noqa: S311
                    self.default_lower_filesize,
                    target_max - filler_delta,
                )

            # if command specifies a file less than a certain size
            if isinstance(target_max, int) and "less" in command:
                if command == "less_than":
                    delta = 1
                    filler_delta = 0

                if is_truth_file:
                    return random.randint(  # noqa: S311
                        self.default_lower_filesize,
                        target_max - delta,
                    )
                return random.randint(  # noqa: S311
                    target_max + filler_delta,
                    self.default_upper_filesize,
                )
            return None
        # if there are no specified queries, create a random file size
        return random.randint(  # noqa: S311
            self.default_lower_filesize,
            self.default_upper_filesize,
        )

    # helper for _generate_i_object_data
    def _create_timestamp_data(
        self,
        ts_uuid: str,
        timestamps: dict[str, datetime],
    ) -> list[IndalekoTimestampDataModel]:
        """Creates the timestamp data based on timestamp datamodel (in UTC time)."""
        # sort the timestamp by most earliest to latest and create the list using list comprehension
        return [
            IndalekoTimestampDataModel(
                Label=ts_uuid,
                Value=timestamp[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                Description=timestamp[0],
            )
            for timestamp in sorted(timestamps.items(), key=lambda time: time[1])
        ]

    # helper for _generate_record_data():
    def _generate_random_data(self) -> str:
        """Generates a string of random number of ascii characters as data."""
        ascii_chars = string.ascii_letters + string.digits
        return "".join(
            random.choices(ascii_chars, k=random.randint(1, 500)),  # noqa: S311
        )

    # helper function for generate_file_info()
    def _create_metadata_uuid(self, number: int, is_truth_file: bool = True) -> str:  # noqa: FBT001,FBT002
        """
        Create metadata UUID.

        Creates UUID for the metadata based on the is_truth_file (filler VS truth metadata)
        of metadata Truth files are given prefix c, Filler or truth like filler files
        prefix f.
        """
        starter_uuid = f"c{number}" if is_truth_file else f"f{number}"

        digits = 8 - len(starter_uuid)
        space_filler = "0" * digits
        starter_uuid += space_filler
        return (
            starter_uuid
            + "-"
            + "".join(random.choices("0123456789", k=4))  # noqa: S311
            + "-"
            + "".join(random.choices("0123456789", k=4))  # noqa: S311
            + "-"
            + "".join(random.choices("0123456789", k=4))  # noqa: S311
            + "-"
            + "".join(random.choices("0123456789", k=12))  # noqa: S311
        )

    def preprocess_dictionary_timestamps(
            self,
            to_timestamp: bool,   # noqa: FBT001
    ) -> dict[str, Any]:
        """
        Convert time to posix timstamps given a dictionary to run data generator.

        Args:
            to_timestamp (bool): Whether to convert to posix timestamps or not.

        Returns:
                Dict[str, Any]: The converted attributes dictionary.
        """
        if "timestamps" in self.selected_md:
            for timestamp_key, timestamp_data in self.selected_md["timestamps"].items():
                starttime, endtime = self._convert_time_timestamp(timestamp_data, to_timestamp)
                self.selected_md["timestamps"][timestamp_key]["starttime"] = starttime
                self.selected_md["timestamps"][timestamp_key]["endtime"] = endtime
                if not to_timestamp:
                    self._update_earliest_times(starttime, endtime)

        return self.selected_md

    # Helper function for convert_dictionary_times()
    def _convert_time_timestamp(
            self,
            timestamps: dict,
            to_timestamp: bool,  # noqa: FBT001
    ) -> tuple[Any | datetime, Any | datetime]:
        """Converts the time from string to timestamps."""
        starttime = timestamps["starttime"]
        endtime = timestamps["endtime"]
        if to_timestamp:
            starttime = starttime.timestamp()
            endtime = endtime.timestamp()
        else:
            starttime = self._convert_str_datetime(starttime)
            endtime = self._convert_str_datetime(endtime)

        return starttime, endtime

    def _update_earliest_times(self, starttime: datetime, endtime: datetime) -> None:
        """Updates and tracks the earliest start and end times."""
        self.earliest_endtime.append(endtime)
        self.earliest_starttime.append(starttime)

        self.earliest_endtime.sort()
        self.earliest_starttime.sort()

    # general helper function for _generate_queried_timestamp() and _convert_time_timestamp():
    def _convert_str_datetime(self, time: str) -> datetime:
        """
        Converts a str date from "YYYY-MM-DD" to datetime.

        Used within time generator functions.
        """
        splittime = re.split("[-T:]", time)
        year = int(splittime[0])
        month = int(splittime[1])
        day = int(splittime[2])

        hour = int(splittime[3])
        minute = int(splittime[4])
        second = int(splittime[5])

        time = datetime(year, month, day, hour, minute, second, tzinfo=UTC)

        # if requested time is sooner than today's day, set it to the time to now
        return min(time, datetime.now(UTC))

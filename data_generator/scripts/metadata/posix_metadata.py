import os, sys
from datetime import datetime, timedelta
import random
import string
import uuid
from collections import Counter
from faker import Faker
from data_generator.scripts.metadata.metadata import Metadata
from data_models.i_object import IndalekoObjectDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from typing import Dict, Any, Tuple
from icecream import ic

faker = Faker()


class PosixMetadata(Metadata):
    """
    Subclass for Metadata.
    Generates Posix Metadata based on the given dictionary of queries
    """

    def __init__(
        self,
        selected_POSIX_md,
        default_lower_filesize,
        default_upper_filesize,
        default_lower_timestamp,
        default_upper_timestamp,
        earliest_starttime,
        earliest_endtime,
    ):
        super().__init__(selected_POSIX_md)

        self.default_lower_filesize = default_lower_filesize
        self.default_upper_filesize = default_upper_filesize
        self.default_upper_timestamp = default_upper_timestamp
        self.default_lower_timestamp = default_lower_timestamp
        self.earliest_starttime = earliest_starttime
        self.earliest_endtime = earliest_endtime

        self.saved_directory_path = self.initialize_local_dir()

    def generate_metadata(
        self,
        record_data: IndalekoRecordDataModel,
        IO_UUID: str,
        timestamps: Dict[str, str],
        URI: str,
        file_size: int,
        semantic_attributes_data: list[Dict[str, Any]],
        key_name: str,
        local_identifier: str,
    ) -> IndalekoObjectDataModel:
        return self._generate_i_object_data(
            record_data,
            IO_UUID,
            timestamps,
            URI,
            file_size,
            semantic_attributes_data,
            key_name,
            local_identifier,
        )

    def generate_file_info(
        self,
        current_filenum: int,
        n: int,
        is_truth_file: bool,
        truth_like: bool,
        truthlike_attributes: list[str],
        has_semantic_truth,
        has_semantic_filler: bool,
    ) -> Tuple[int, str, str, str, str]:
        """Generates the information required for the posix metadata"""
        file_size = self._generate_file_size(
            is_truth_file=self._define_truth_attribute(
                "file.size", is_truth_file, truth_like, truthlike_attributes
            )
        )
        file_name = self._generate_file_name(
            is_truth_file=self._define_truth_attribute(
                "file.name", is_truth_file, truth_like, truthlike_attributes
            ),
            has_semantic_truth=has_semantic_truth,
            has_semantic_filler=has_semantic_filler,
        )
        path, URI, updated_filename = self._generate_dir_location(
            file_name,
            is_truth_file=self._define_truth_attribute(
                "file.directory", is_truth_file, truth_like, truthlike_attributes
            ),
        )
        IO_UUID = self._create_metadata_UUID(
            current_filenum + n, is_truth_file=is_truth_file
        )
        return file_size, updated_filename, path, URI, IO_UUID

    def generate_file_attributes(
        self, file_name: str, path: str, timestamps: Dict[str, datetime], file_size: int
    ) -> Dict[str, Any]:
        """Generates the dictionary of file attributes"""
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
        self, IO_UUID: str, attribute: Dict[str, Any]
    ) -> IndalekoRecordDataModel:
        """generates the record data"""
        id_source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=IO_UUID, Version="1.0", Description="Record UUID"
        )

        return IndalekoRecordDataModel(
            SourceIdentifier=id_source_identifier,
            Timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            Attributes=attribute,
            Data=self._generate_random_data(),
        )

    def _generate_i_object_data(
        self,
        record_data: IndalekoRecordDataModel,
        IO_UUID: str,
        timestamps: Dict[str, str],
        URI: str,
        file_size: int,
        semantic_attributes_data: list[Dict[str, Any]],
        key_name: str,
        local_identifier: str,
    ) -> IndalekoObjectDataModel:
        """Returns the Indaleko object created form the data model"""
        timestamp_data = self._create_timestamp_data(IO_UUID, timestamps)

        return IndalekoObjectDataModel(
            Record=record_data,
            URI=URI,
            ObjectIdentifier=uuid.uuid4(),
            Timestamps=timestamp_data,
            Size=file_size,
            SemanticAttributes=semantic_attributes_data,
            Label=key_name,
            LocalIdentifier=str(local_identifier),
            Volume=uuid.uuid4(),
            PosixFileAttributes="S_IFREG",
            WindowsFileAttributes="FILE_ATTRIBUTE_ARCHIVE",
        )

    def initialize_local_dir(self) -> Dict[str, Any]:
        """
        Initializes and saves the local directories to self.saved_directory_path; run only once
        returns self.saved_directory_path = {"truth.directory": {"path": str, "files": Counter(str)}, "filler.directory" {"path":, "files": Counter(str)}: list}}
        """
        num_directories = random.randint(3, 8)
        max_depth = random.randint(3, 5)
        parent_dir = "/home/user"
        truth_parent_loc = ""
        # if the there is a query related to the directory and the pathing has not been initialized create the directories
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
            else:  # if remote  just generate random directory
                return self._generate_local_path(parent_dir, num_directories, max_depth)
        else:  # no queries related to file directories; generate random directory
            return self._generate_local_path(parent_dir, num_directories, max_depth)

    # helper for initialize_local_dir():
    def _generate_local_path(
        self,
        base_dir: str,
        num_directories: int,
        max_depth: int,
        directory_name: str = None,
    ) -> Dict[str, Any]:
        """
        Generate random path to directories within a parent dir based on base_dir, num_directories, max_depth and if available, directory_name recursively
        Only runs once during initialization
        Adapted from Tony's code from metadata.py
        """
        saved_directory_path = {"truth.directory": {}, "filler.directory": {}}
        directory_count = 0
        # List to store generated paths
        generated_paths = []

        def create_dir_recursive(current_dir, current_depth):
            nonlocal directory_count
            if current_depth > max_depth or directory_count >= num_directories:
                return

            if num_directories - directory_count > 0:
                max_subdirs = max(
                    1,
                    (num_directories - directory_count)
                    // (max_depth - current_depth + 1),
                )
                subdirs = random.randint(1, max_subdirs)

                for _ in range(subdirs):
                    directory_count += 1
                    if directory_count >= num_directories:
                        break
                    # Generate a random subdirectory name or choose truth file path name
                    subdir_name = "".join(
                        random.choices(string.ascii_lowercase, k=random.randint(1, 8))
                    )
                    subdir_path = os.path.join(current_dir, subdir_name)
                    generated_paths.append(subdir_path)
                    create_dir_recursive(subdir_path, current_depth + 1)

        create_dir_recursive(base_dir, 1)

        if directory_name != None:
            saved_directory_path["truth.directory"]["path"] = (
                random.choice(generated_paths) + "/" + directory_name
            )
            saved_directory_path["truth.directory"]["files"] = Counter()
        saved_directory_path["filler.directory"]["path"] = generated_paths
        saved_directory_path["filler.directory"]["files"] = Counter()
        return saved_directory_path

    def _generate_file_name(
        self, is_truth_file: bool, has_semantic_truth: bool, has_semantic_filler: bool
    ) -> str:
        """
        Generates a file_name for given file
        Args: is_truth_file (bool): the type of file it is
             self.selected_md{file.name: {"pattern":str, "command":str, "extension":str}}
            commands include: "starts", "ends", "contains"
        Return (str): returns the file name
        """
        command, pattern = "", ""
        true_extension = None
        n_filler_letters = random.randint(1, 10)
        file_extension = Metadata.TEXT_FILE_EXTENSIONS.copy()
        # if the file name is part of the query, extract the appropriate attributes and generate title
        if "file.name" in self.selected_md:
            if "pattern" in self.selected_md["file.name"]:
                pattern = self.selected_md["file.name"]["pattern"]
                command = self.selected_md["file.name"]["command"]
                avail_text_file_extension = Metadata.TEXT_FILE_EXTENSIONS

            if "extension" in self.selected_md["file.name"]:
                true_extension = self.selected_md["file.name"]["extension"]
                if isinstance(true_extension, list):
                    file_extension = list(set(file_extension) - set(true_extension))
                    avail_text_file_extension = list(
                        set(Metadata.TEXT_FILE_EXTENSIONS) - set(true_extension)
                    )
                else:
                    file_extension.remove(true_extension)
                    if true_extension in Metadata.TEXT_FILE_EXTENSIONS:
                        avail_text_file_extension.remove(true_extension)

            ic(avail_text_file_extension)

            if is_truth_file:
                # choose file extension
                if (
                    "extension" in self.selected_md["file.name"]
                ):  # if no extension specified, then randomly select a file extension
                    if isinstance(true_extension, list):
                        true_extension = random.choice(true_extension)
                elif (
                    has_semantic_truth
                ):  # if semantic content exists, then should be a text file
                    true_extension = random.choice(Metadata.TEXT_FILE_EXTENSIONS)
                else:
                    true_extension = random.choice(file_extension)

                # create file name based on commands
                if command == "exactly":
                    return pattern + true_extension
                elif command == "starts":
                    return (
                        pattern
                        + "".join(
                            random.choices(string.ascii_letters, k=n_filler_letters)
                        )
                        + true_extension
                    )
                elif command == "ends":
                    return (
                        "".join(
                            random.choices(string.ascii_letters, k=n_filler_letters)
                        )
                        + pattern
                        + true_extension
                    )
                elif command == "contains":
                    return (
                        "".join(
                            random.choices(string.ascii_letters, k=n_filler_letters)
                        )
                        + pattern
                        + "".join(
                            random.choices(string.ascii_letters, k=n_filler_letters)
                        )
                        + true_extension
                    )
                else:
                    return (
                        "".join(
                            random.choices(string.ascii_letters, k=n_filler_letters)
                        )
                        + true_extension
                    )

            else:  # if a filler metadata, generate random title that excludes all letters specified in the char pattern
                if has_semantic_filler:
                    extension = random.choice(avail_text_file_extension)
                else:
                    extension = random.choice(file_extension)

            allowed_pattern = list(
                set(string.ascii_letters) - set(pattern.upper()) - set(pattern.lower())
            )
            return (
                "".join(random.choices(allowed_pattern, k=n_filler_letters)) + extension
            )

        else:  # if no query specified for title, but semantic context exists, choose a text file extension
            if has_semantic_filler or (is_truth_file and has_semantic_truth):
                extension = random.choice(Metadata.TEXT_FILE_EXTENSIONS)
            else:  # randomly create a title with any extension
                extension = random.choice(file_extension)
            title = (
                "".join(random.choices(string.ascii_letters, k=n_filler_letters))
                + extension
            )
            return title

    def _generate_dir_location(
        self, file_name: str, is_truth_file: bool = True
    ) -> Tuple[str, str, str]:
        """
        Generates a directory location for the metadata
        self.selected_md ["file.directory"] = [location, directory_name (optional, for local only)]
        location: where it is stored; local or remote (google drive, drop box, icloud, local)
        RETURN: list consisting of path and URI and updated file name to remote or local storage

        """
        # URIs/URLs to local computer or cloud storage services
        file_locations = {
            "google_drive": "https://drive.google.com",
            "dropbox": "https://www.dropbox.com",
            "icloud": "https://www.icloud.com",
            "local": "file:/",
        }
        # RUN after initialization:
        if "file.directory" in self.selected_md and is_truth_file:
            truth_parent_loc = self.selected_md["file.directory"]["location"]
            file_counter = self.saved_directory_path["truth.directory"]["files"]

            if (
                truth_parent_loc == "local"
            ):  # if file dir specified, create truth file at that dir
                path = self.saved_directory_path["truth.directory"]["path"] + "/"
                counter_key = path + file_name
                if counter_key in file_counter:
                    file_counter[counter_key] += 1
                    updated_file_name = self._change_name(
                        file_name=file_name, count=file_counter[counter_key]
                    )
                    path += updated_file_name
                    URI = file_locations[truth_parent_loc] + path
                    return [path, URI, updated_file_name]
                else:
                    file_counter.update({counter_key: 0})
                    path += file_name
                    URI = file_locations[truth_parent_loc] + path
                    return [path, URI, file_name]

            elif (
                is_truth_file and truth_parent_loc in file_locations.keys()
            ):  # if remote dir specified, create file at that dir
                path = self._generate_remote_path(truth_parent_loc, file_name)
                URI = file_locations[truth_parent_loc] + path
            return [path, URI, file_name]

        # for filler files or truth files with no file attributes specified
        elif not is_truth_file and "file.directory" in self.selected_md:
            truth_parent_loc = self.selected_md["file.directory"]["location"]
            del file_locations[truth_parent_loc]

        # not queried at this point and file type doesn't matter; generate any file path (local or remote)
        random_location = random.choice(list(file_locations.keys()))
        if random_location == "local":
            file_counter = self.saved_directory_path["filler.directory"]["files"]
            path = (
                random.choice(self.saved_directory_path["filler.directory"]["path"])
                + "/"
            )
            counter_key = path + file_name
            if counter_key in file_counter:
                file_counter[counter_key] += 1
                updated_file_name = self._change_name(
                    file_name=file_name, count=file_counter[counter_key]
                )
                path += updated_file_name
                URI = file_locations[random_location] + path
                return [path, URI, updated_file_name]
            else:
                file_counter.update({counter_key: 0})
                path += file_name
                URI = file_locations[random_location] + path
                return [path, URI, file_name]
        else:
            path = self._generate_remote_path(random_location, file_name)
            URI = file_locations[random_location] + path

        return path, URI, file_name

    def _change_name(self, file_name: str, count: int) -> str:
        """changes name to avoid duplicate files in the same path"""
        base_name, ext = os.path.splitext(file_name)
        return f"{base_name}({count}){ext}"

    # helper functions for generate_dir_location
    def _generate_remote_path(self, service_type: str, file_name: str) -> str:
        """
        Generates path to a remote file location e.g., google drive, dropbox, icloud
        """
        list_alphanum = string.ascii_letters + string.digits
        # Randomly choose characters to form the id
        file_id = "".join(random.choices(list_alphanum, k=random.randint(3, 6)))
        local_file_locations = {
            "google_drive": "/file/d/{file_id}/view/view?name={file_name}",
            "dropbox": "/s/{file_id}/{file_name}?dl=0",
            "icloud": "/iclouddrive/{file_id}/{file_name}",
        }
        remote_path = local_file_locations[service_type].format(
            file_id=file_id, file_name=file_name
        )
        return remote_path

    def generate_timestamps_md(
        self, is_truth_file, truth_like_file, truth_like_attributes
    ):
        is_truth_file = self._define_truth_attribute(
            "timestamps", is_truth_file, truth_like_file, truth_like_attributes
        )
        return self._generate_timestamps(is_truth_file)

    def _generate_timestamps(self, is_truth_file: bool = True) -> Dict[str, datetime]:
        """
        Generates birthtime, modifiedtime, accessedtime, and changedtime for the specified file:
        Args: is_truth_file (bool): file type
        Returns (Dict[str, datetime]): {birthtime: datetime, modifiedtime: datetime, accessedtime: datetime, changedtime: datetime}
        """
        stamp_labels = {"modified", "accessed", "changed"}
        birthtime = None
        latest_timestamp_of_three = None
        timestamps = {}
        # check whether the query is pertaining to specific timestamp queries
        if "timestamps" in self.selected_md:
            query = self.selected_md["timestamps"]
            selected_timestamps = set(query.keys())
            non_selected_timestamps = stamp_labels - selected_timestamps
            if (
                "birthtime" in query
            ):  # specifically checks for birthtime since other timestamps shouldn't be earlier than the birthtime
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
                    else:  # if type of timestamp not chosen, either generate a random timestamp within bounds or choose an existing timestamp
                        timestamps[timestamp] = self._choose_existing_random_timestamp(
                            timestamps, birthtime, self.default_upper_timestamp
                        )
            else:
                # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
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
                    timestamps, birthtime, self.default_upper_timestamp
                )
        return timestamps

    # helper for _generate_timestamps:
    def _choose_existing_random_timestamp(
        self, timestamps, lower_bound, upperbound
    ) -> datetime:
        """chooses an existing timstamp that is in the dict or creates a random timestamp within bounds"""
        randomtime = self._generate_random_timestamp(
            lower_bound=lower_bound, upper_bound=upperbound
        )
        existing_timestamp = random.choice(list(timestamps.values()))
        return random.choice([existing_timestamp, randomtime])

    # helper functions for generate_timestamps():
    def _generate_random_timestamp(
        self, lower_bound: datetime, upper_bound: datetime
    ) -> datetime:
        """
        Generates a random timestamp within the bounds specified
        Args:
            lower_bound (datetime) birth time for m/a/c timestamps or default "2000-10-25" for birthtime
            upper_bound (datetime) latest timestamp for birthtime or current datetime for m/a/c timestamps
        Returns:
            (datetime): a randomly generated timestamp
        """

        random_time = faker.date_time_between(
            start_date=lower_bound, end_date=upper_bound
        )
        return random_time

    def _generate_queried_timestamp(
        self,
        starttime: datetime,
        endtime: datetime,
        default_startdate: datetime,
        is_truth_file: bool = True,
        is_birthtime: bool = False,
    ) -> datetime:
        """
        Generates timestamp based on file type; default_truth_startdate is either the
        self.default_lower_timestamp or the birthtime (if birthtime already set)
        """

        filler_delta = 2
        time_delta = timedelta(hours=filler_delta)
        timestamp = None
        # check errors that can arise for str parameters
        if starttime > datetime.now() or endtime > datetime.now():
            raise ValueError(
                "The timestamp you have queried is in the future, please check again."
            )
        elif starttime > endtime:
            raise ValueError("The starttime cannot be more recent than the endtime")
        elif is_truth_file and default_startdate > endtime:
            raise ValueError(
                "The default_startdate cannot be more recent than the endtime"
            )
        elif self.default_lower_timestamp == self.default_upper_timestamp:
            raise ValueError(
                "The absolute lower bound date cannot be the same time as the date right now"
            )
        elif (
            self.default_lower_timestamp == starttime
            and self.default_upper_timestamp == endtime
        ):
            raise ValueError(
                "Invalid range, please increase the bounds or decrease the range to within the bounds"
            )
        elif is_birthtime and starttime > self.earliest_endtime[0]:
            raise ValueError(
                "The earliest starttime cannot be earlier than the birthtime starttime"
            )
        elif self.default_lower_timestamp > starttime:
            raise ValueError(
                "The absolute lower bound cannot be greater than the starttime"
            )

        elif starttime == endtime:
            if starttime < default_startdate:
                raise ValueError(
                    "The starttime for the timestamps cannot be earlier than the birthtime/default"
                )
            if is_truth_file and default_startdate <= starttime:
                timestamp = starttime
            if not is_truth_file:
                # for birthtime timestamps (choose the lowest/most earliest possible time to not have time earlier than the other timestamps)
                lower = faker.date_time_between(
                    start_date=self.default_lower_timestamp,
                    end_date=starttime - time_delta,
                )
                upper = faker.date_time_between(start_date=starttime + time_delta)
                # the earliest starttime is within the bounds:
                if (
                    is_birthtime
                    and self.default_lower_timestamp + time_delta
                    <= self.earliest_starttime[0]
                    <= starttime
                ):
                    timestamp = faker.date_time_between(
                        start_date=self.default_lower_timestamp,
                        end_date=self.earliest_starttime[0] - time_delta,
                    )
                # case 2: the earliest starttime is not within the bounds
                elif (
                    is_birthtime
                    and self.default_lower_timestamp + time_delta
                    <= self.earliest_starttime[0]
                ):
                    timestamp = faker.date_time_between(
                        start_date=starttime + time_delta,
                        end_date=self._find_next_earliest_endtime(starttime)
                        - time_delta,
                    )
                elif is_birthtime:
                    raise ValueError(
                        "Cannot generate birthtime timestamp for truth file"
                    )
                # for timestamps other than birthtime:
                if (
                    not is_birthtime and default_startdate == starttime
                ):  # if birthtime is greater than the equal
                    timestamp = faker.date_time_between(
                        start_date=default_startdate + timedelta(hours=filler_delta)
                    )
                elif (
                    not is_birthtime and default_startdate > starttime
                ):  # if birthtime is greater than the equal
                    timestamp = faker.date_time_between(start_date=default_startdate)
                elif not is_birthtime and default_startdate < starttime:
                    lower = faker.date_time_between(
                        start_date=default_startdate, end_date=starttime - time_delta
                    )
                    if starttime + time_delta < self.default_upper_timestamp:
                        upper = faker.date_time_between(
                            start_date=starttime + time_delta
                        )
                        timestamp = random.choice([upper, lower])
                    elif starttime + time_delta >= self.default_upper_timestamp:
                        timestamp = lower
                elif not is_birthtime:
                    raise ValueError("cannot form timestamp for filler file")
        # if the starttime and endtime are not equal and are not lists, then choose a date within that range
        # under the assumption that starttime < endtime
        elif starttime < endtime:  # if is a birthtime, should take on values that are
            # if it is a birthtime and a truth file, find the earliest time possible
            if (
                is_truth_file
                and is_birthtime
                and default_startdate <= starttime
                and starttime <= self.earliest_starttime[0] <= endtime
            ):
                timestamp = faker.date_time_between(
                    start_date=starttime, end_date=self.earliest_starttime[0]
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

            if (
                is_truth_file
                and not is_birthtime
                and starttime <= default_startdate <= endtime
            ):
                timestamp = faker.date_time_between(
                    start_date=default_startdate, end_date=endtime
                )
            elif is_truth_file and not is_birthtime and starttime > default_startdate:
                timestamp = faker.date_time_between(
                    start_date=starttime, end_date=endtime
                )
            # elif is_truth_file and not is_birthtime and endtime < default_startdate:
            #     raise ValueError("The birthtime cannot be greater than the other timestamps")
            elif is_truth_file and not is_birthtime:
                raise ValueError(
                    "Absolute lower bound date cannot be more recent than the endtime"
                )

            if not is_truth_file:
                # for filler file birhttime timestamps:
                if (
                    is_birthtime
                    and self.default_lower_timestamp <= starttime - time_delta
                    and self.default_lower_timestamp + time_delta
                    <= self.earliest_starttime[0]
                    <= starttime
                ):
                    timestamp = faker.date_time_between(
                        start_date=self.default_lower_timestamp,
                        end_date=self.earliest_starttime[0] - time_delta,
                    )
                elif (
                    is_birthtime
                    and self.default_upper_timestamp >= endtime + time_delta
                ):
                    timestamp = faker.date_time_between(
                        start_date=endtime + time_delta,
                        end_date=self._find_next_earliest_endtime(starttime)
                        - time_delta,
                    )
                elif is_birthtime and not is_truth_file:
                    raise ValueError(
                        "cannot generate birthtime timestamp for filler files"
                    )

                lower = faker.date_time_between(
                    start_date=default_startdate, end_date=starttime - time_delta
                )
                upper = faker.date_time_between(start_date=endtime + time_delta)
                # for none birthtime timestamps
                if (
                    not is_birthtime
                    and endtime < default_startdate <= self.default_upper_timestamp
                ):
                    timestamp = faker.date_time_between(start_date=endtime)
                elif not is_birthtime and starttime <= default_startdate <= endtime:
                    timestamp = upper
                elif (
                    not is_birthtime
                    and self.default_lower_timestamp <= default_startdate <= starttime
                ):
                    timestamp = random.choice([lower, upper])
                elif not is_birthtime and not is_truth_file:
                    raise ValueError("Cannot generate timestamps for filler files")
        else:
            raise ValueError(
                "Error in parameters or command: Please check the query once more."
            )
        return timestamp.replace(microsecond=0)

    def _find_next_earliest_endtime(self, starttime) -> datetime:
        for date in self.earliest_endtime:
            if starttime <= date:
                return date
            else:
                raise ValueError("there are no times that work")

    def _generate_file_size(self, is_truth_file: bool = True) -> int:
        """
        Creates random file size given the is_truth_file
        self.selected_md {file.size: ["target_min", "target_max", "command"]}
        command includes "equal", "range"
        """
        if "file.size" in self.selected_md:
            filler_delta = 1
            delta = 0
            target_min = self.selected_md["file.size"]["target_min"]
            target_max = self.selected_md["file.size"]["target_max"]
            command = self.selected_md["file.size"]["command"]

            if (
                target_max == self.default_upper_filesize
                and target_min == self.default_lower_filesize
            ):
                raise ValueError(
                    "The range cannot be the whole boundary from ",
                    target_min,
                    " to ",
                    target_max,
                )
            elif target_min > target_max:
                raise ValueError(
                    f"The target max {target_min} cannot be greater than the target max {target_max}"
                )

            # if the target_min/max is a list and is the same as the target_max choose a random size from the list
            if (
                isinstance(target_min, list)
                and isinstance(target_max, list)
                and command == "equal"
            ):
                if is_truth_file:
                    return random.choice(target_min)
                else:
                    return self._check_return_value_within_range(
                        target_min[0], target_min[-1], random.randint, 1
                    )

            # if the target_min/max is not a list but is the same as the target_max then just choose that file size
            elif target_min == target_max and command == "equal":
                if is_truth_file:
                    return target_min
                else:
                    return self._check_return_value_within_range(
                        target_min, target_min, random.randint, 1
                    )

            # if command specifies getting the range between two values
            elif target_min != target_max and command == "range":
                if is_truth_file:
                    return random.randint(target_min, target_max)
                else:
                    return self._check_return_value_within_range(
                        target_min, target_max, random.randint, 1
                    )

            # if command specifies a file greater than a certain size
            elif isinstance(target_max, int) and "greater" in command:
                if command == "greater_than":
                    delta = 1
                    filler_delta = 0

                if is_truth_file:
                    return random.randint(
                        target_max + delta, self.default_upper_filesize
                    )
                else:
                    return random.randint(
                        self.default_lower_filesize, target_max - filler_delta
                    )

            # if command specifies a file less than a certain size
            elif isinstance(target_max, int) and "less" in command:
                if command == "less_than":
                    delta = 1
                    filler_delta = 0

                if is_truth_file:
                    return random.randint(
                        self.default_lower_filesize, target_max - delta
                    )
                else:
                    return random.randint(
                        target_max + filler_delta, self.default_upper_filesize
                    )
        # if there are no specified queries, create a random file size
        else:
            return random.randint(
                self.default_lower_filesize, self.default_upper_filesize
            )

    # helper for _generate_i_object_data
    def _create_timestamp_data(
        self, UUID: str, timestamps: Dict[str, datetime]
    ) -> list[IndalekoTimestampDataModel]:
        """
        Creates the timestamp data based on timestamp datamodel (in UTC time)
        """
        timestamp_data = []
        # sort the timestamp by most earliest to latest
        for timestamp in sorted(timestamps.items(), key=lambda time: time[1]):
            timestamp_data.append(
                IndalekoTimestampDataModel(
                    Label=UUID,
                    Value=timestamp[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    Description=timestamp[0],
                )
            )
        return timestamp_data

    # helper for _generate_record_data():
    def _generate_random_data(self) -> str:
        """Generates a string of random number of ascii characters as data"""
        ascii_chars = string.ascii_letters + string.digits
        random_data = "".join(random.choices(ascii_chars, k=random.randint(1, 500)))
        return random_data

    # helper function for generate_file_info()
    def _create_metadata_UUID(self, number: int, is_truth_file: bool = True) -> str:
        """
        Creates UUID for the metadata based on the is_truth_file (filler VS truth metadata) of metadata
        Truth files are given prefix c, Filler or truth like filler files prefix f
        """
        if is_truth_file:
            starter_uuid = f"c{number}"
        else:
            starter_uuid = f"f{number}"

        digits = 8 - len(starter_uuid)
        space_filler = "0" * digits
        starter_uuid += space_filler
        uuid = (
            starter_uuid
            + "-"
            + "".join(random.choices("0123456789", k=4))
            + "-"
            + "".join(random.choices("0123456789", k=4))
            + "-"
            + "".join(random.choices("0123456789", k=4))
            + "-"
            + "".join(random.choices("0123456789", k=12))
        )
        return uuid

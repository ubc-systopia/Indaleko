# V2:
# [  ‘pid',
#    'procname’,
#    ‘Executable_path’,
#    ['file1', open='ts1', close='ts2', mode=R],
#    ['file2', open='ts3', close='ts4', mode=RW],
#    ['file3', open='ts5', close='ts6', mode=W],
# ]


import collections
from typing import Dict, List
from uu import Error

from abstract import IOperator, IWriter


class FileEvent:
    # Constants representing different file operation modes
    MODE_READ = 0
    MODE_WRITE = 1
    MODE_MMAP = 2
    MODE_MKDIR = 3
    MODE_RENAME = 4

    def __init__(self):
        # Initialize the FileEvent object with default values
        self.filename = ''  # Name of the file
        self.open_ts = ''   # Timestamp for when the file is opened
        self.close_ts = ''  # Timestamp for when the file is closed
        self.mode = 0       # Bitmask to store the mode of operation

    @staticmethod
    def validate_input(value, exp_type):
        # Validate that the given value is of the expected type
        assert isinstance(value, exp_type), f'given value is not a {
            type(exp_type)}; got {type(value)}'

    def add_open_ts(self, ts):
        # Add the open timestamp to the FileEvent
        FileEvent.validate_input(ts, str)  # Ensure the timestamp is a string
        self.open_ts = ts
        return self

    def add_close_ts(self, ts):
        # Add the close timestamp to the FileEvent
        FileEvent.validate_input(ts, str)  # Ensure the timestamp is a string
        self.close_ts = ts
        return self

    def add_filename(self, filename):
        # Add the filename to the FileEvent
        # Ensure the filename is a string
        FileEvent.validate_input(filename, str)
        self.filename = filename
        return self

    def add_mode(self, mode):
        # Add the operation mode to the FileEvent using bitwise OR to set the appropriate bit
        FileEvent.validate_input(mode, int)  # Ensure the mode is an integer
        self.mode |= (1 << mode)  # Set the bit corresponding to the mode
        return self

    def to_list(self):
        # Convert the FileEvent attributes to a list
        return [self.filename, self.open_ts, self.close_ts, self.mode]

    def to_dict(self):
        # Convert the FileEvent attributes to a dictionary
        return {
            'fname': self.filename,
            'open': self.open_ts,
            'close': self.close_ts,
            'mode': self.mode
        }


class LogRecordV2:
    @staticmethod
    def Validate(value, exp_type):
        """
        Validates that the given value is of the expected type.

        Args:
            value: The value to be validated.
            exp_type: The expected type of the value.

        Returns:
            bool: True if the value is of the expected type, otherwise raises an assertion error.
        """

        # Validate that the given value is of the expected type.
        assert isinstance(value, exp_type), f'value {value} is of type {
            type(value)}, expected {str(exp_type)}'
        return True

    def __init__(self, pid: str, proc: str, exec_path: str):
        """
        Initializes the LogRecordV2 instance with process details and initializes
        the file event tracking structures.

        Args:
            pid (str): Process ID.
            proc (str): Process name.
            exec_path (str): Execution path.
        """

        # Validate that all input parameters are strings
        all([LogRecordV2.Validate(val, str) for val in [pid, proc, exec_path]])

        # Initialize instance variables
        self.pid = pid  # Process ID
        self.proc = proc  # Process name
        self.exec_path = exec_path  # Execution path
        # Dictionary to hold current file events
        self.file_events: Dict[str, FileEvent] = collections.OrderedDict()
        # List to hold completed file events
        self.completed_file_events: List[FileEvent] = []

    def add_file_event(self, file_name: str, ts: str, op: str):
        """
        Adds a file event to the log record, updating or creating a FileEvent
        instance as necessary and marking events as completed when applicable.

        Args:
            file_name (str): The name of the file involved in the event.
            ts (str): The timestamp of the event.
            op (str): The type of file operation (e.g., 'open', 'close', 'write').

        Returns:
            self: The updated LogRecordV2 instance.
        """

        # Validate that all input parameters are strings
        all([LogRecordV2.Validate(val, str) for val in [file_name, ts, op]])

        # If the file event for the given file_name does not exist, create a new FileEvent
        if file_name not in self.file_events:
            self.file_events[file_name] = FileEvent().add_filename(file_name)

        # Handle the file operation based on the op parameter
        match op:
            case 'open':
                # Add open timestamp to the file event
                self.file_events[file_name].add_open_ts(ts)
            case 'close':
                # Add close timestamp to the file event and mark it as completed
                self.file_events[file_name].add_close_ts(ts)
                # Move the completed file event to the completed_file_events list
                self.completed_file_events.append(self.file_events[file_name])
                # Remove the file event from the current file events
                del self.file_events[file_name]
            case 'write':
                self.file_events[file_name].add_mode(FileEvent.MODE_WRITE)
            case 'read':
                self.file_events[file_name].add_mode(FileEvent.MODE_READ)
            case 'mmap':
                self.file_events[file_name].add_mode(FileEvent.MODE_MMAP)
            case 'mkdir':
                self.file_events[file_name].add_mode(FileEvent.MODE_MKDIR)
            case 'rename':
                self.file_events[file_name].add_mode(FileEvent.MODE_RENAME)
            case _:
                raise Error("Unsupported file operation")

        return self

    def to_list(self):
        """
        Converts the LogRecordV2 instance to a list, including process details
        and both completed and current file events.
        """
        # Convert current file events to a list of lists
        curr_events = [] if len(self.file_events) == 0 else [
            fe.to_list() for _, fe in self.file_events.items()
        ]

        # Return a list combining pid, proc, exec_path, and all completed and current file events
        return [
            self.pid, self.proc, self.exec_path, [
                fe.to_list() for fe in self.completed_file_events] + curr_events
        ]

    def to_dict(self) -> Dict:
        curr_events = [] if len(self.file_events) == 0 else [
            fe.to_dict() for _, fe in self.file_events.items()
        ]

        return {
            'pid': self.pid,
            'proc': self.proc,
            'exec_path': self.exec_path,
            'events': [fe.to_dict() for fe in self.completed_file_events] + curr_events
        }

    def free_mem(self):
        """
        Frees memory by clearing and deleting file event attributes,
        then forcing garbage collection.
        """
        import gc
        self.file_events.clear()
        self.completed_file_events.clear()
        del self.file_events
        del self.completed_file_events
        gc.collect()


class LogCompactorV2(IOperator):
    """
    LogCompactorV2 handles the compaction of log records by tracking file operation events
    and managing stateful information about each log record. It processes various file
    operations like 'open', 'close', 'read', 'write', 'mmap', 'rename', and 'mkdir', and
    compacts the information for efficient storage and retrieval.

    Attributes:
        writer (IWriter): An instance of IWriter used for writing compacted log records.
        state (Dict[str, LogRecordV2]): An ordered dictionary to maintain the state of log records.
        file_names (Dict[tuple[str, str], str]): A defaultdict to map file operation keys to filenames.
        get_exec_path (Callable, optional): A function to extract the executable path from the log record.

    Methods:
        create_key(record) -> tuple[str, str]:
            Creates a unique key for the log record based on its process ID and another identifier.

        add_file_name(key: tuple[str, str], file_name: str) -> None:
            Associates a filename with a given key in the file_names dictionary.

        get_file_name(key) -> str:
            Retrieves the filename associated with a given key.

        execute(input_record, **args):
            Processes an input log record, handling different file operations and updating the state accordingly.

        to_list() -> list:
            Converts the current state of log records to a list of dictionaries for serialization.
    """

    UNKOWN_FILE_NAME_VALUE = '[[UNKNOWN]]'

    def __init__(self, writer: IWriter, extract_exec_path_func=None):
        self.writer = writer

        self.state: Dict[str, LogRecordV2] = collections.OrderedDict()

        self.file_names: Dict[tuple[str, str], str] = collections.defaultdict(
            lambda: LogCompactorV2.UNKOWN_FILE_NAME_VALUE)

        self.get_exec_path = extract_exec_path_func

    def create_key(self, record) -> tuple[str, str]:
        return ('-'.join(record[-2:]), record[2])

    def add_file_name(self, key: tuple[str, str], file_name: str) -> None:
        self.file_names[key] = file_name

    def get_file_name(self, key) -> str:
        return self.file_names[key]

    def execute(self, input_record, **args):
        status, record = input_record
        if status == 1 or record[2].strip() == '-1':
            return (1, record)

        key = self.create_key(record)
        if key not in self.state:
            self.state[key] = LogRecordV2(
                pid=record[-1],
                proc=record[-2],
                exec_path=self.get_exec_path(*record[-2:]))

        match record[1]:
            case 'open':
                self.state[key].add_file_event(file_name=record[3],
                                               ts=record[0],
                                               op=record[1]
                                               )

                self.add_file_name(key=key, file_name=record[3])

            case 'close':
                self.state[key].add_file_event(
                    file_name=self.get_file_name(key),
                    ts=record[0],
                    op=record[1]
                )

                self.writer.write(self.state[key].to_dict())

                self.state[key].free_mem()

                del self.state[key]
                del self.file_names[key]
            case 'read' | 'write' as op:
                self.state[key].add_file_event(
                    file_name=self.get_file_name(key),
                    ts=record[0],
                    op=op
                )
            case 'mmap' | 'rename' | 'mkdir' as op:
                self.state[key].add_file_event(
                    file_name=record[3],
                    ts=record[0],
                    op=op
                )

                self.writer.write(self.state[key].to_dict())

                self.state[key].free_mem()
                del self.state[key]

        return (1, record)

    def to_list(self):
        return [
            fe.to_dict() for _, fe in self.state.items()
        ]

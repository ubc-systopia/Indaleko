import typing

from click import File

from abstract import IOperator

# V2:
# [  ‘pid',
#    'procname’,
#    ‘Executable_path’,
#    ['file1', open='ts1', close='ts2', mode=R],
#    ['file2', open='ts3', close='ts4', mode=RW],
#    ['file3', open='ts5', close='ts6', mode=W],
# ]


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



'''This module contains defintions and methods suitable for UNIX systems.'''

class UnixFileAttributes:
    FILE_ATTRIBUTES = {
        'S_IFSOCK' : 0o140000, # socket
        'S_IFLNK' : 0o120000, # symbolic link
        'S_IFREG' : 0o100000, # regular file
        'S_IFBLK' : 0o060000, # block device
        'S_IFDIR' : 0o040000, # directory
        'S_IFCHR' : 0o020000, # character device
        'S_IFIFO' : 0o010000, # FIFO
    }

    @staticmethod
    def map_file_attributes(attributes : int):
        '''Given an integer representing file attributes on UNIX'''
        file_attributes = []
        for attr in UnixFileAttributes.FILE_ATTRIBUTES:
            if attributes & UnixFileAttributes.FILE_ATTRIBUTES[attr] \
                == UnixFileAttributes.FILE_ATTRIBUTES[attr]:
                file_attributes.append(attr)
        return ' | '.join(file_attributes)


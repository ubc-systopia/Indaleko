'''
This module handles data ingestion into Indaleko.  It is specific to Windows
local file system ingestion.
'''

from IndalekoIngest import IndalekoIngest

class IndalekoWindowsIngest(IndalekoIngest):
    '''
    This class handles ingestion of metadata from the Indaleko Windows
    indexing service.
    '''
    def __init__(self, reset: bool = False) -> None:
        pass

def main():
    pass

if __name__ == '__main__':
    main()

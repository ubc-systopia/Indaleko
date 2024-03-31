'''Indaleko Acivity Data Provider: Location'''

import argparse

from IndalekoActivityDataProvider import IndalekoActivityDataProvider

class IADPLocation(IndalekoActivityDataProvider):
    '''Indaleko Acivity Data Provider for location information'''

    def __init__(self):
        super().__init__()

    def get_location(self):
        '''Get the location of the device.'''


def main() -> None:
    '''Main function'''


if __name__ == '__main__':
    main()

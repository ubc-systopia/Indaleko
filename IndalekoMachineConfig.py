import argparse
import json


class IndalekoMachineConfig:
    '''
    This is the generic class for machine config.  It should be used to create
    platform specific machine configuration classes.
    '''
    def __init__(self: 'IndalekoMachineConfig', config_dir : str = './config', test: bool = False) -> None:
        '''
        Constructor for the IndalekoMachineConfig class. Takes a configuration
        object as a parameter. The configuration object is a dictionary that
        contains all the configuration parameters for the machine.
        '''
        if test:
            return
        self.config_dir = config_dir
        self.config_files = []
        self.config_data = None
        self.find_config_files()
        if len(self.config_files) > 0:
            self.set_config_file(self.config_files[-1])
        else:
            self.config_file = None
        if self.config_file is not None:
            self.load_config_file()
            self.config_data = self.get_config_data()


    def set_config_file(self: 'IndalekoMachineConfig', config_file : str) -> None:
        '''
        This method sets the config file for the machine config.  It is used
        primarily for testing.
        '''
        self.config_files = [config_file]
        self.__read_config_files__()

    def load_config_file(self: 'IndalekoMachineConfig') -> None:
        '''
        This method loads the config file for the machine config.  It is used
        primarily for testing.
        '''
        assert self.config_file is not None, "No config file specified."
        with open(self.config_file, 'rt', encoding=utf-8-sig) as fd:
            self.config_data = json.load(fd)
        # Note: a derived class wishing to do something special with the config,
        # can call this base method and then do its own additional processing
        # (or override this method completely).
        return

    def get_config_data(self: 'IndalekoMachineConfig') -> dict:
        '''
        This method returns the config data for the machine config.
        '''
        if self.config_data is None:
            self.load_config_file()
        return self.config_data


    def find_config_files(self : 'IndalekoMachineConfig') -> list:
        '''
        This method returns a list of config files that are used by the machine
        config.  The list should be in the order that the files should be read.
        Override in the derived class.
        '''
        assert False, "Do not call find_config_files() on the base class - override it in the derived class."

def main():
    # Now parse the arguments
    mcfg = IndalekoMachineConfig(test=True)
    assert mcfg is not None, "Could not create machine config."
    parser = argparse.ArgumentParser(description='Test the Machine Configuration class.', add_help=False)
    args = parser.parse_args()
    print(args)

if __name__ == "__main__":
    main()




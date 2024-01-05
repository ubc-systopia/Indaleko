import argparse
import json
import os

class IndalekoMachineConfig:
    '''
    This is the generic class for machine config.  It should be used to create
    platform specific machine configuration classes.
    '''
    def __old_init__(self: 'IndalekoMachineConfig', config_dir : str = './config', test: bool = False) -> None:
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
        return
        self.find_config_files()
        if len(self.config_files) > 0:
            self.set_config_file(self.config_files[-1])
        else:
            self.config_file = None
        if self.config_file is not None:
            self.load_config_file()
            self.config_data = self.get_config_data()

    def __init__(self: 'IndalekoMachineConfig', config_data : dict, test: bool = False) -> None:
        '''
        Constructor for the IndalekoMachineConfig class. Takes a
        set of configuration data as a parameter and initializes the object.
        '''

        pass


    @staticmethod
    def create_config_from_file(**kwargs) -> 'IndalekoMachineConfig':
        '''
        This method creates a new IndalekoMachineConfig object from an
        existing config file.
        '''
        if 'config_dir in kwargs':
            config_dir = kwargs['config_dir']
        if 'config_file' in kwargs:
            config_file = kwargs['config_file']
        if 'test' in kwargs:
            test = kwargs['test']
        else:
            test = False
        assert config_file is not None, "No config file specified."
        if config_dir is not None:
            config_file = os.path.join(config_dir, config_file)
        new_config = IndalekoMachineConfig(test=test)
        new_config.set_config_file(config_file)
        return new_config

    def set_config_file(self: 'IndalekoMachineConfig', config_file : str) -> None:
        '''
        This method sets the config file for the machine config.  It is used
        primarily for testing.
        '''
        self.config_file = config_file
        self.load_config_file()

    def load_config_file(self: 'IndalekoMachineConfig') -> None:
        '''
        This method loads the config file for the machine config.  It can be
        overridden by a derived class, if it is necessary.
        '''
        assert self.config_file is not None, "No config file specified."
        with open(self.config_file, 'rt', encoding='utf-8-sig') as fd:
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



def main():
    # Now parse the arguments
    mcfg = IndalekoMachineConfig(test=True)
    assert mcfg is not None, "Could not create machine config."
    parser = argparse.ArgumentParser(description='Test the Machine Configuration class.', add_help=False)
    args = parser.parse_args()
    print(args)

if __name__ == "__main__":
    main()




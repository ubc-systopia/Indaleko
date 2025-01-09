class DBConfig:
    def __init__(self, db_config):
        # Make sure we have all the correct args
        self.__user_name = 'user_name'
        self.__user_password = 'user_password'
        self.__host = 'host'
        self.__port = 'port'
        self.__db = 'database'

        for key in [self.__user_name, self.__user_password, self.__host, self.__port, self.__db]:
            assert key in db_config, f"Couldn't find '{key}' in the config"

        self.db_config = db_config

    def get_user_name(self):
        return self.db_config[self.__user_name]

    def get_user_password(self):
        return self.db_config[self.__user_password]

    def get_host(self):
        return self.db_config[self.__host]

    def get_port(self):
        return self.db_config[self.__port]

    def get_db(self):
        return self.db_config[self.__db]

    def __str__(self):
        return ', '.join(f'{key}={value}' for key, value in self.__dict__.items() if not key.startswith('_'))

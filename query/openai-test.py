"""This is a test file for interacting with the OpenAI API"""

import configparser
import os

import openai
from icecream import ic


class OpenAITest:
    """Simple test class for working with the OpenAI API"""

    def __init__(self, **kwargs) -> None:
        """Set up the class"""
        self.api_key_file = kwargs.get("api_key_file", "../config/openai-key.ini")
        self.api_key = self.get_api_key()
        self.client = openai.OpenAI(api_key=self.api_key)
        self.models = self.get_openai_models()
        ic("OpenAITest initialized")

    def get_api_key(self) -> str:
        """Get the API key from the config file"""
        assert os.path.exists(self.api_key_file), "API key file not found"
        config = configparser.ConfigParser()
        config.read(self.api_key_file, encoding="utf-8-sig")
        openai_key = config["openai"]["api_key"]
        if openai_key is None:
            raise ValueError("OpenAI API key not found in config file")
        if openai_key[0] == '"' or openai_key[0] == "'":
            openai_key = openai_key[1:]
        if openai_key[-1] == '"' or openai_key[-1] == "'":
            openai_key = openai_key[:-1]
        return openai_key

    def get_openai_models(self) -> list:
        """Get a list of the available models"""
        if not hasattr(self, "models"):
            self.models = [x.id for x in self.client.models.list().data]
        return self.models


def main():
    """Main function for testing the OpenAI API"""
    # test = OpenAITest()
    # ic(test.get_openai_models())


if __name__ == "__main__":
    main()

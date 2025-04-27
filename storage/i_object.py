"""
Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""

import argparse
import datetime
import json
import os
import sys
import uuid


# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
# from Indaleko import Indaleko
# from IndalekoObjectSchema import IndalekoObjectSchema
# from IndalekoObjectDataModel import IndalekoObjectDataModel
# from IndalekoRecordDataModel import IndalekoRecordDataModel
# from IndalekoDataModel import IndalekoDataModel
from data_models import IndalekoObjectDataModel
from storage.recorders.tokenization import tokenize_filename
from utils.misc.data_management import encode_binary_data


# pylint: enable=wrong-import-position


class IndalekoObject:
    """
    An IndalekoObject represents a single object (file/directory) in the Indaleko system.
    """

    Schema = IndalekoObjectDataModel.get_arangodb_schema()

    """UUIDs we associate with specific timestamps that we capture"""
    CREATION_TIMESTAMP = "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6"
    MODIFICATION_TIMESTAMP = "434f7ac1-f71a-4cea-a830-e2ea9a47db5a"
    ACCESS_TIMESTAMP = "581b5332-4d37-49c7-892a-854824f5d66f"
    CHANGE_TIMESTAMP = "3bdc4130-774f-4e99-914e-0bec9ee47aab"

    def __init__(self, **kwargs):
        """Initialize the object."""
        self.args = kwargs
        assert "ObjectIdentifier" in kwargs, "ObjectIdentifier is missing."
        assert isinstance(
            kwargs["ObjectIdentifier"],
            str,
        ), "ObjectIdentifier is not a string."
        assert kwargs["ObjectIdentifier"] != "None", "ObjectIdentifier is None."
        assert "Record" in kwargs, f"Record is missing: {kwargs}"
        if kwargs.get("Label"):
            tokenized = tokenize_filename(kwargs.get("Label"))
            for key, value in tokenized.items():
                if key not in kwargs:
                    kwargs[key] = value
        self.indaleko_object = IndalekoObjectDataModel.deserialize(kwargs)
        if self.indaleko_object.Timestamps is not None:
            for timestamp in self.indaleko_object.Timestamps:
                if timestamp.Value.tzinfo is None:
                    timestamp.Value = timestamp.Value.replace(
                        tzinfo=datetime.UTC,
                    )

    @staticmethod
    def deserialize(data: dict) -> "IndalekoObject":
        """Deserialize a dictionary to an object."""
        return IndalekoObject(**data)

    def serialize(self) -> dict:
        """Serialize the object to a dictionary."""
        doc = json.loads(
            self.indaleko_object.model_dump_json(exclude_none=True, exclude_unset=True),
        )
        doc["_key"] = self.args["ObjectIdentifier"]
        return doc

    def to_dict(self):
        """Return a dictionary representation of this object."""
        return self.serialize()

    def __getitem__(self, key):
        """Get an item from the object."""
        return getattr(self.indaleko_object, key)

    def __contains__(self, key):
        """Check if an item is in the object."""
        return hasattr(self.indaleko_object, key)


def main():
    """Test code for the IndalekoObject class."""
    random_raw_data = encode_binary_data(os.urandom(64))
    source_uuid = str(uuid.uuid4())
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        default=source_uuid,
        help="The source UUID of the data.",
    )
    parser.add_argument(
        "--raw-data",
        "-r",
        type=str,
        default=random_raw_data,
        help="The raw data to be stored.",
    )
    parser.parse_args()
    data_object = {
        "Record": {
            "Data": "xQL6xQL3eyJzdF9hdGltZSI6IDE2OTMyMjM0NTYuMzMzNDI4MSwgInN0X2F0aW1lX25zIjo"
            "gMTY5MzIyMzQ1NjMzMzQyODEwMCwgInN0X2JpcnRodGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgIn"
            "N0X2JpcnRodGltZV9ucyI6IDE2ODU4OTEyMjE1NTkxOTE3MDAsICJzdF9jdGltZSI6IDE2ODU4OTEyM"
            "jEuNTU5MTkxNywgInN0X2N0aW1lX25zIjogMTY4NTg5MTIyMTU1OTE5MTcwMCwgInN0X2RldiI6IDI3"
            "NTYzNDcwOTQ5NTU2NDk1OTksICJzdF9maWxlX2F0dHJpYnV0ZXMiOiAzMiwgInN0X2dpZCI6IDAsICJ"
            "zdF9pbm8iOiAxMTI1ODk5OTEwMTE5ODMyLCAic3RfbW9kZSI6IDMzMjc5LCAic3RfbXRpbWUiOiAxNj"
            "g1ODkxMjIxLjU1OTcxNTcsICJzdF9tdGltZV9ucyI6IDE2ODU4OTEyMjE1NTk3MTU3MDAsICJzdF9ub"
            "GluayI6IDEsICJzdF9yZXBhcnNlX3RhZyI6IDAsICJzdF9zaXplIjogMTQxMDEyMCwgInN0X3VpZCI6"
            "IDAsICJOYW1lIjogInJ1ZnVzLTQuMS5leGUiLCAiUGF0aCI6ICJkOlxcZGlzdCIsICJVUkkiOiAiXFx"
            "cXD9cXFZvbHVtZXszMzk3ZDk3Yi0yY2E1LTExZWQtYjJmYy1iNDBlZGU5YTVhM2N9XFxkaXN0XFxydW"
            "Z1cy00LjEuZXhlIiwgIkluZGV4ZXIiOiAiMDc5M2I0ZDUtZTU0OS00Y2I2LTgxNzctMDIwYTczOGI2N"
            "mI3IiwgIlZvbHVtZSBHVUlEIjogIjMzOTdkOTdiLTJjYTUtMTFlZC1iMmZjLWI0MGVkZTlhNWEzYyIs"
            "ICJPYmplY3RJZGVudGlmaWVyIjogIjJjNzNkNmU1LWVhYmEtNGYwYS1hY2YzLWUwMmM1MjlmMDk3YSJ9",
            "SourceIdentifier": {
                "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                "Version": "1.0",
                "Description": None,
            },
            "Timestamp": "2024-07-30T23:38:48.319654+00:00",
        },
        "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\rufus-4.1.exe",
        "ObjectIdentifier": "2c73d6e5-eaba-4f0a-acf3-e02c529f097a",
        "Timestamps": [
            {
                "Label": "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6",
                "Value": "2023-06-04T15:07:01.559192+00:00",
                "Description": "Created",
            },
            {
                "Label": "434f7ac1-f71a-4cea-a830-e2ea9a47db5a",
                "Value": "2023-06-04T15:07:01.559716+00:00",
                "Description": "Modified",
            },
            {
                "Label": "581b5332-4d37-49c7-892a-854824f5d66f",
                "Value": "2023-08-28T11:50:56.333428+00:00",
                "Description": "Accessed",
            },
            {
                "Label": "3bdc4130-774f-4e99-914e-0bec9ee47aab",
                "Value": "2023-06-04T15:07:01.559192+00:00",
                "Description": "Changed",
            },
        ],
        "Size": 1410120,
        "Machine": "2e169bb7-0024-4dc1-93dc-18b7d2d28190",
        "Volume": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c",
        "UnixFileAttributes": "S_IFREG",
        "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE",
        "SemanticAttributes": [
            {
                "3fa47f24-b198-434d-b440-119ec5af4f7d": 2756347094955649599,
            },  # st_dev
            {
                "64ec8b5a-78ba-4787-ba8d-cb033ec24116": 0,
            },  # st_gid
            {
                "1bb62d33-0392-4ffe-af1d-5ebfc32afbb9": 33279,
            },  # st_mode
            {
                "06677615-2957-4966-aab9-dde29660c334": 1,
            },  # st_nlink
            {
                "7ebf1a92-94f9-40b0-8887-349c24f0e354": 0,
            },  # st_reparse_tag
            {
                "1bd30cfc-9320-427d-bdde-60d9e8aa4400": 0,
            },  # st_uid
            {
                "882d75c6-a424-4d8b-a938-c264a281204c": 1125899910119832,
            },  # st_ino
        ],
        "Label": "rufus-4.1.exe",
        "LocalPath": "d:\\dist",
        "LocalIdentifier": 1125899910119832,
    }
    indaleko_object = IndalekoObject.deserialize(data_object)
    print(json.dumps(indaleko_object.serialize(), indent=2))


if __name__ == "__main__":
    main()

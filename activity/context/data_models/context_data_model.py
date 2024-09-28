"""
This module defines the data model for the activity context in the Indaleko
Project.

Project Indaleko
Copyright (C) 2024 Tony Mason

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
import datetime
import os
import sys
import uuid

from typing import List
from pydantic import Field, BaseModel

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from activity.context.data_models.activity_data import ActivityDataModel
from data_models.indaleko_record_data_model import IndalekoRecordDataModel

class IndalekoActivityContextDataModel(BaseModel):
    '''
    This class defines the data model for the activity context in the Indaleko
    Project.

    An _activity context_ is a reference to an object in our indexing system
    (database) that corresponds to a collection of activity data points that
    have been captured by the known activity data providers.

    Activity context thus captures information related to the users: what was
    the user experiencing at the time the activity context was created.

    Activity _data_ is an abstract concept that refers to the information that
    describes the experiential information.  Examples of this include, but are
    not limited to:

    - The user's location
    - The music the user was listening to at the time
    - The ambient temperature
    - The weather
    - The application(s) the user was accessing
    - The files the user was accessing
    - Other users with whom the user was interacting

    The activity context is a snapshot of the user's environment at a specific
    point in time. This information is used to help understand the user's state
    of mind, in order to enable Indaleko to more effectively assist the user in
    finding specific files of interest.

    This module defines the format of the data that is used by the Activity
    Context service.

    An _activity handle_ is a UUID, which serves as a reference to the data
    object ("activity context") in the database.
    '''

    Handle : uuid.UUID = Field(...,
                               title='Handle',
                               description='The activity context handle.')

    Timestamp : datetime.datetime = Field(...,
                                    title='Timestamp',
                                    description='The timestamp when the activity context was created.'
                                )

    Cursors : List[ActivityDataModel]\
          = Field(...,
                  title='ActivityData',
                  description='The activity data associated with the activity context.'
            )

    class Config:
        '''Configuration for the class.'''
        json_schema_extra = {
            'example' : {
                'Handle' : uuid.uuid4(),
                'Timestamp' : '2024-01-01T00:00:00Z',
                'Cursors' : [
                    ActivityDataModel.Config.json_schema_extra['example'],
                    ActivityDataModel.Config.json_schema_extra['example'],
                    ActivityDataModel.Config.json_schema_extra['example'],
                ]
            }
        }

    def serialize(self):
        '''Serialize the object to a dictionary.'''
        return self.model_dump(exclude_unset=True)

    @staticmethod
    def deserialize(data: dict):
        '''Deserialize the data from a dictionary.'''
        return IndalekoActivityContextDataModel(**data)

def main():
    '''Test code for IndalekoActivityContextDataModel.'''
    activity_context = IndalekoActivityContextDataModel(
        **IndalekoActivityContextDataModel.Config.json_schema_extra['example']
    )
    print(activity_context.serialize())
    print(activity_context.model_json_schema())
    doc = activity_context.serialize()
    print(type(doc))
    print(doc)
    check_data = IndalekoActivityContextDataModel.deserialize(doc)
    print(check_data.serialize())

if __name__ == '__main__':
    main()

'''
This module defines the "contained by" relationship.  e.g. a file or directory
is contained by a directory or volume.  A volume is contained by a machine.
'''

from IndalekoRecord import IndalekoRecord

class IndalekoRelationshipContainedBy(IndalekoRecord):
    '''This class defines the "contained by" relationship.'''

    CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR = '3d4b772d-b4b0-4203-a410-ecac5dc6dafa'
    CONTAINED_BY_VOLUME_RELATIONSHIP_UUID_STR = 'f38c45ce-e8d8-4c5a-adc6-fc34f5f8b8e9'
    CONTAINED_BY_MACHINE_RELATIONSHIP_UUID_STR = '1ba5935c-8e82-4dd9-92e7-d4b085958487'

    def __init__(self : 'IndalekoRelationshipContainedBy', **kwargs : dict) -> None:
        '''
        Constructor for the IndalekoRelationshipContainedBy class. Takes a
        configuration object as a parameter. The configuration object is a
        dictionary that contains all the configuration parameters for the
        relationship.
        '''
        super().__init__(**kwargs)
        self.relationship_type = 'contained by'
        if 'relationship_type' in kwargs:
            self.relationship_type = kwargs['relationship_type']
        self.parent = None
        if 'parent' in kwargs:
            self.parent = kwargs['parent']
        self.child = None
        if 'child' in kwargs:
            self.child = kwargs['child']

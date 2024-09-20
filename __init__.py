'''
Base description of Indaleko

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
'''

from icecream import ic

if 'INDALEKO_ROOT' not in os.environ:
    os.environ['INDALEKO_ROOT'] = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.environ['INDALEKO_ROOT'])


def initialize_project():
    '''Initialize the project'''
    ic('Indaleko project initialization invoked.')

from Indaleko import Indaleko
from IndalekoDBConfig import IndalekoDBConfig

__all__ = [
    'Indaleko',
]

__version__ = '2024.09.20.1'

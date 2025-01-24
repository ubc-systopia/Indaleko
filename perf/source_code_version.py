'''
This module provides a mechanism for retrieving source code version information for use by the
performance package.

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

'''
import os
import sys

from git import Repo
from icecream import ic
from pydantic import BaseModel
from typing import List, Optional

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position

class IndalekoGitInfoDataModel(BaseModel):
    '''This class provides a data model for the IndalekoGitInfo class.'''
    commit_hash: str
    modified_files: List[str]
    untracked_files: List[str]


class IndalekoGitInfo:
    '''
    This class provides a mechanism for retrieving source code
    version information for use by the performance package.
    '''
    @staticmethod
    def get_current_hash(repo_path: str = os.environ['INDALEKO_ROOT']) -> str:
        '''Retrieve the current hash for the repository.'''
        try:
            repo = Repo(repo_path)
        except Exception as ex:
            ic(f"Failed to open repository at {repo_path}: {ex}")
            return None
        return repo.head.commit.hexsha

    @staticmethod
    def get_modified_files(repo_path: str = os.environ['INDALEKO_ROOT']) -> List[str]:
        '''Retrieve the list of modified files in the repository.'''
        try:
            repo = Repo(repo_path)
        except Exception as ex:
            ic(f"Failed to open repository at {repo_path}: {ex}")
            return None
        return [item.a_path for item in repo.index.diff(None)]

    @staticmethod
    def get_untracked_files(repo_path: str = os.environ['INDALEKO_ROOT']) -> List[str]:
        '''Retrieve the list of untracked files in the repository.'''
        try:
            repo = Repo(repo_path)
        except Exception as ex:
            ic(f"Failed to open repository at {repo_path}: {ex}")
            return None
        return repo.untracked_files

    @staticmethod
    def get_framework_source_version_data() -> IndalekoGitInfoDataModel:
        '''Retrieve the source code version information for the framework.'''
        return IndalekoGitInfoDataModel(
            commit_hash=IndalekoGitInfo.get_current_hash(),
            modified_files=IndalekoGitInfo.get_modified_files(),
            untracked_files=IndalekoGitInfo.get_untracked_files()
        )


def main():
    '''Test code for the IndalekoGitInfo class.'''
    ic('IndalekoGitInfo test code')
    git_info = IndalekoGitInfo()
    ic(git_info.get_framework_source_version_data())


if __name__ == '__main__':
    main()

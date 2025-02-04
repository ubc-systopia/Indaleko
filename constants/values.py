"""
This package defines service constants used in Indaleko.  It cannot
depend on anything else (it exists to break circular dependencies that seem
to arise in the code base.)

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

import os
import sys

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


class IndalekoConstants:

    project_name = 'Indaleko'
    default_prefix = 'indaleko'
    default_db_config_file_name = f'{default_prefix}-db-config.ini'
    default_data_dir = os.path.join(os.environ.get('INDALEKO_ROOT', '.'), 'data')
    default_config_dir = os.path.join(os.environ.get('INDALEKO_ROOT', '.'), 'config')
    default_log_dir = os.path.join(os.environ.get('INDALEKO_ROOT', '.'), 'logs')

    service_type_test = 'Test'
    service_type_machine_configuration = "Machine Configuration"
    service_type_storage_collector = 'Storage Collector'
    service_type_storage_recorder = 'Storage Recorder'
    service_type_semantic_transducer = 'Semantic Transducer'
    service_type_activity_context_generator = 'Activity Context Generator'
    service_type_activity_data_collector = 'Activity Data Collector'
    service_type_activity_data_registrar = 'Activity Data Registrar'

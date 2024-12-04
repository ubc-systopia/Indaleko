'''initializtion logic for the platform components'''

import os
import sys

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

__version__ = '0.1.0'

#from platforms.machine_config import IndalekoMachineConfig
#from platforms.mac.machine_config import IndalekoMacOSMachineConfig
#from platforms.linux.machine_config import IndalekoLinuxMachineConfig
#from platforms.windows.machine_config import IndalekoWindowsMachineConfig

__all__ = [
#    IndalekoLinuxMachineConfig,
#    IndalekoMachineConfig,
#    IndalekoMacOSMachineConfig,
#    IndalekoWindowsMachineConfig
]

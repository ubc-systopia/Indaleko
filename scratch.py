import subprocess
import platform
import multiprocessing
import time
import ctypes

'''
This is just a scratch script for figuring out how to do certain things.
'''

class Foo:

    def __init__(self):
        self.platform = platform.system()
        self.pool = multiprocessing.Pool(32)
        self.dataset = [(a,b,c,d) for a in range(0,5) for b in range(6,10) for c in range(11,15) for d in ['a', 'b', 'c', 'd', 'e']]
        self.results = self.pool.map(Foo.consumer, self.dataset)

    @staticmethod
    def consumer(item):
        a, b, c, d = item
        return (d,b,a,c)

def get_volume_guid_for_path(path):
    """
    Get the volume GUID for the given path on Windows.
    """
    # Define the function from the kernel32.dll
    GetVolumeNameForVolumeMountPointW = ctypes.windll.kernel32.GetVolumeNameForVolumeMountPointW

    # Create a buffer for the result
    volume_path_name = ctypes.create_unicode_buffer(261)  # MAX_PATH + 1

    # Call the function
    if not GetVolumeNameForVolumeMountPointW(path, volume_path_name, len(volume_path_name)):
        raise ctypes.WinError()

    return volume_path_name.value

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='machine-config.json',
                        help='Name of output file for machine configuration data')
    args = parser.parse_args()
    print(args)
    print(get_volume_guid_for_path("C:\\"))



if __name__ == "__main__":
    main()

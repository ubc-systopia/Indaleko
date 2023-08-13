import subprocess
import platform
import multiprocessing
import time


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

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, default='machine-config.json',
                        help='Name of output file for machine configuration data')
    args = parser.parse_args()
    print(args)
    foo = Foo()
    print(foo, foo.results)


if __name__ == "__main__":
    main()

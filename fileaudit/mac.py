import subprocess
import operators
import pipeline
import argparse
from typing import List


def print_result(t):
    if t != None and t[0] == 0:
        print(t[1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--time', '-t', dest='time', type=int,
                        help='total time in secs to run fs_usage', default=1)

    args = parser.parse_args()

    p = pipeline.Pipeline(operators.InputReader(
        ['sudo', 'fs_usage', '-e', '-w', '-f', 'filesys', '-t', str(args.time)]))

    p.add(
        operators.ToList(remove_empty_fields=True)
    ).add(
        operators.FilterFields(
            1, ["open", "close", "mmap", "read", "write", "mkdir", "rename"], exact_match=True)
    ).add(
        operators.Show(print_result)
    )

    list(p.run())


if __name__ == '__main__':
    main()

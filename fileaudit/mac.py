import json
import log_compactor_v2
import operators
import pipeline
import argparse
from typing import List


def print_result(t):
    if t != None and t[0] == 0:
        print(t[1])


def to_csv(t, header: bool = False):
    if header:
        print("ts,syscall,fid,path,procname,pid")
    if t != None and t[0] == 0:
        print(','.join(t[1]))


class CompressorWriter:
    def write(self, arr):
        print(arr)


class CompressorWriterV2:
    def write(self, arr, **args):
        # print(arr)
        if 'file' in args:
            args['file'].write(json.dumps(arr) + '\n')


# TODO: add a function to return the exec path of the process
# TODO: add a logger
# TODO: rewriter the docstrings

def main():
    from os import path

    parser = argparse.ArgumentParser()
    parser.add_argument('--compress', '-c', dest='compress', action='store_true',
                        default=False, help='compress the log records into one one')
    parser.add_argument('--interval', dest='interval', type=int,
                        help='interval time (in minutes) for compression (has to be used with -c or --compress). Has to be more than 5 otherwise it will be set to 5', default=5)

    subparsers = parser.add_subparsers(title='subcommands', dest='subcommands')

    fs_usage_parser = subparsers.add_parser(
        'fs_usage', help="fs_usage subcommand (mac)")
    fs_usage_parser.add_argument('--time', '-t', dest='time', type=int,
                                 help='total time in secs to run fs_usage', default=1)

    file_input_parser = subparsers.add_parser(
        'file_input', help='reads from the input file')
    file_input_parser.add_argument('--input-file', '-i', dest='input_file',
                                   type=str, help='the input file')

    args = parser.parse_args()

    input_reader = None
    match args.subcommands:
        case 'fs_usage':
            command = (
                'sudo fs_usage -w -f filesys -t ' + str(args.time)
            )
            input_reader = operators.InputReader([command])
        case 'file_input':
            assert path.exists(args.input_file), f'the input file does not exist at {
                args.input_file}'

            input_reader = operators.FileInputReader(args.input_file)

    compactorOp = log_compactor_v2.LogCompactorV2(
        writer=CompressorWriterV2(),
        extract_exec_path_func=lambda x, y: '-'.join([x, y]),
        with_timer=args.compress,
        interval_seconds=max(args.interval, 5)
    )

    p = pipeline.Pipeline(input_reader)

    p.add(
        operators.TrSpaces()
    ).add(
        operators.ToList(remove_empty_fields=True)
    ).add(
        operators.FilterFields(
            1, ["open", "close", "mmap", "read", "write", "mkdir", "rename"], exact_match=True)
    ).add(
        operators.Canonize()
    )

    if args.compress:
        p.add(compactorOp)
    else:
        p.add(operators.Show(show_func=print_result))

    list(p.run())


if __name__ == '__main__':
    main()

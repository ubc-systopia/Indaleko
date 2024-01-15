'''This is a quick python script to show the first entry in a jsonlines file.'''
import argparse
import jsonlines
import json

def main():
    parser = argparse.ArgumentParser(description='Show the first entry in a jsonlines file.')
    parser.add_argument('file', help='The file to show')
    args = parser.parse_args()
    with jsonlines.open(args.file) as reader:
        for entry in reader:
            print(json.dumps(entry, indent=4))
            break

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Pre-commit hook to forbid direct usage of sub-fields in the IndalekoRecordDataModel.Data field.
It searches for occurrences of "Record.Data." in Python source files.
"""
import re
import sys


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    pattern = re.compile(r"\bRecord\.Data\.")
    failed = False
    for filename in argv:
        if not filename.endswith(".py"):
            continue
        try:
            text = open(filename, encoding="utf-8").read()
        except Exception:
            continue
        for match in pattern.finditer(text):
            text.count("\n", 0, match.start()) + 1
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

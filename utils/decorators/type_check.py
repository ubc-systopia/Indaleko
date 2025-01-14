"""
This is definitions of useful decorators that we use in the Indaleko project.

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

from typing import Union, get_type_hints
from typing import get_type_hints
from functools import wraps
from typing import get_type_hints, Any

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position

def type_check(func):
    '''Adds type checking to a function based on type hints.'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        hints = get_type_hints(func)
        all_args = kwargs.copy()
        all_args.update(dict(zip(func.__code__.co_varnames, args)))
        for arg, arg_type in hints.items():
            if arg in all_args:
                if arg_type is Any:
                    continue  # Skip type checking for Any
                if not isinstance(all_args[arg], arg_type):
                    if hasattr(arg_type, '__origin__') and arg_type.__origin__ is Union:
                        if not any(isinstance(all_args[arg], t) for t in arg_type.__args__):
                            raise TypeError(f"Argument '{arg}' must be of type {arg_type}")
                    else:
                        raise TypeError(f"Argument '{arg}' must be of type {arg_type}")
        return func(*args, **kwargs)
    return wrapper

# Test functions
@type_check
def test_func_int(x: int):
    return x

@type_check
def test_func_str(s: str):
    return s

@type_check
def test_func_union(x: Union[int, str]):
    return x

@type_check
def test_func_any(x: Any):
    return x

@type_check
def test_func_class_instance(x: 'MyClass'):
    return x

class MyClass:
    pass

def run_tests():
    # Correct calls
    assert test_func_int(10) == 10
    assert test_func_str("hello") == "hello"
    assert test_func_union(10) == 10
    assert test_func_union("hello") == "hello"
    assert test_func_any(10) == 10
    assert test_func_any("hello") == "hello"
    assert test_func_class_instance(MyClass()) == MyClass()

    # Incorrect calls
    try:
        test_func_int("not an int")
    except TypeError as e:
        assert str(e) == "Argument 'x' must be of type <class 'int'>"

    try:
        test_func_str(10)
    except TypeError as e:
        assert str(e) == "Argument 's' must be of type <class 'str'>"

    try:
        test_func_union(10.5)
    except TypeError as e:
        assert str(e) == "Argument 'x' must be of type typing.Union[int, str]"

    try:
        test_func_class_instance("not a MyClass instance")
    except TypeError as e:
        assert str(e) == "Argument 'x' must be of type <class '__main__.MyClass'>"

    print("All tests passed!")

def main():
    run_tests()

if __name__ == '__main__':
    main()

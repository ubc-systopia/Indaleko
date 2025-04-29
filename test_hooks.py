"""Test file for pre-commit hooks.

This file contains deliberately incorrect code to test that our pre-commit hooks
are working correctly.
"""


def hello_world(name, age=None) -> str:
    """Return a greeting.

    Args:
        name: The person's name
        age: The person's age (optional)

    Returns:
        A personalized greeting
    """
    if age is not None:  # Fixed comparison to None
        return f"Hello, {name}! You are {age} years old."
    return f"Hello, {name}!"  # Fixed unnecessary else


def unused_function():
    """This function is not used."""


# Added type annotation
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


class TestClass:
    """Test class."""

    def __init__(self):
        self.value = None

    def test_method(self, value):
        """Test method."""
        self.value = value

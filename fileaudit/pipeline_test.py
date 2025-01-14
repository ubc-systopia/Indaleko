import unittest
from abstract import IReader
import operators
import pipeline


class MockInputGenerator(IReader):
    all_lines = [
        (0, 't1 a1 b1'),
        (0, 't2 a2 b2'),
        (0, 't3 a3 b3')
    ]

    def run(self):
        for line in self.all_lines:
            yield line

    def get_len(self):
        return len(MockInputGenerator.all_lines)


class PipeLineTest(unittest.TestCase):

    def mock_show(self, input_tuple):
        status, _ = input_tuple
        if status == 0:
            return input_tuple
        return None

    def test_mock_data(self):
        test_cases = {
            "only_nil": {
                "pos": 1,
                "queries": [["ax", "ay", "az"]],
                "remove_empty": True,
                "expect": [0]
            },
            "only_as": {
                "pos": 1,
                "queries": [["a1", "a2", "a3"]],
                "remove_empty": True,
                "expect": [3]
            },
            "only_a1": {
                "pos": 1,
                "queries": [["a1"]],
                "remove_empty": True,
                "expect": [1]
            },
            "only_a2": {
                "pos": 1,
                "queries": [["a2"]],
                "remove_empty": True,
                "expect": [1]
            },
            "only_a3": {
                "pos": 1,
                "queries": [["a3"]],
                "remove_empty": True,
                "expect": [1]
            },
            "only_a3_a2": {
                "pos": 1,
                "queries": [["a3", "a1"]],
                "remove_empty": True,
                "expect": [2]
            },
            "only_random": {
                "pos": 1,
                "queries": [["a3", "a1"], ["a2"], ["a1", "a2"], ["a3"], ["0"]],
                "remove_empty": True,
                "expect": [2, 1, 2, 1, 0]
            }
        }

        for title, tc in test_cases.items():
            print(f'running {title}')

            pos, queries, remove_empty = tc["pos"], tc["queries"], tc["remove_empty"]

            for i, q in enumerate(queries):
                mi = MockInputGenerator()

                p = pipeline.Pipeline(mi)

                p.add(operators.ToList(remove_empty_fields=remove_empty)) \
                    .add(operators.FilterFields(pos, q)) \
                    .add(operators.Show(self.mock_show))

                # p.run returns a generator; use list to realize it
                res = [rec for rec in p.run() if rec != None]

                self.assertEqual(len(res), tc['expect'][i], f'expect={tc['expect'][i]} got=({len(res)})')

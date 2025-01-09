import unittest
from unittest.mock import patch
from io import StringIO
from operators import InputReader, ToList, FilterField, FilterFields, Canonize


class TestInputReader(unittest.TestCase):
    def test_successful_command(self):
        # Mock subprocess.Popen to return a successful process
        with patch("subprocess.Popen") as mock_popen:
            mock_process = mock_popen.return_value
            mock_process.stdout = StringIO("Line 1\nLine 2\n")
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0

            reader = InputReader(["ls", "/bin"])
            output_lines = list(reader.run())

        self.assertEqual(output_lines, [(0, "Line 1"), (0, "Line 2")])

    def test_failed_command(self):
        # Mock subprocess.Popen to return a process with non-zero exit code
        with patch("subprocess.Popen") as mock_popen:
            mock_process = mock_popen.return_value
            mock_process.stdout = StringIO("")
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 1

            reader = InputReader(["ls", "/nonexistent_directory"])
            output_lines = list(reader.run())

        self.assertEqual(
            output_lines, [(1, "Command exited with non-zero code: 1; stderr: ")])

    def test_exception_handling(self):
        # Mock subprocess.Popen to raise an exception
        with patch("subprocess.Popen") as mock_popen:
            mock_process = mock_popen.return_value
            mock_process.stdout = StringIO("")
            mock_process.communicate.side_effect = Exception(
                "Something went wrong")

            reader = InputReader(["ls", "/bin"])
            output_lines = list(reader.run())

        self.assertEqual(output_lines, [(1, "Error: Something went wrong")])


class TestToList(unittest.TestCase):
    def test_valid_input_with_remove_true(self):
        valid_input = (0, 'a b c d e')
        status, to_list_valid = ToList(
            sep=' ', remove_empty_fields=True).execute(valid_input)
        self.assertEqual(status, 0)
        self.assertEqual(list(to_list_valid), ['a', 'b', 'c', 'd', 'e'])

    def test_valid_input_with_remove_false(self):
        valid_input = (0, 'a b c d e')
        status, to_list_valid = ToList(
            sep=' ', remove_empty_fields=False).execute(valid_input)
        self.assertEqual(status, 0)
        self.assertEqual(list(to_list_valid), ['a', 'b', 'c', 'd', 'e'])

    def test_empty_input_with_remove_true(self):
        empty_input = (0, '')
        status, to_list_empty = ToList(
            sep=' ', remove_empty_fields=True).execute(empty_input)
        self.assertEqual(status, 0)
        self.assertEqual(list(to_list_empty), [])

    def test_empty_input_with_remove_false(self):
        empty_input = (0, '')
        status, to_list_empty = ToList(
            sep=' ', remove_empty_fields=False).execute(empty_input)
        self.assertEqual(status, 0)
        self.assertEqual(list(to_list_empty), [''])

    def test_having_brackets(self):
        input_tuple = (0, 'a b [ a d   d] a d')
        status, to_list = ToList(sep=' ',
                                 remove_empty_fields=True).execute(input_tuple)
        self.assertEqual(status, 0)
        self.assertEqual(list(to_list), ['a', 'b', '[a d d]', 'a', 'd'])


class TestFilterWithPos(unittest.TestCase):
    def test_filter_notexist(self):
        test_cases = {
            "field not exists(1)": (0, ['a=1', 'b=1', '']),
            "field not exists(2)": (0, ['a=1', 'b=1', '']),
            "field not exists(3)": (0, ['a=1', 'b=1', '']),
            "empty list": (0, []),
            "invalid input (1)": (1, ['a=1', 'b=1', '']),
            "invalid input (2)": (1, []),
        }

        for title, input in test_cases.items():
            # print(f'... running test "{title}"')

            for pos in range(3):
                # FilterField(input, (position, contains_value))
                status, result = FilterField((pos, 'c=')).execute(input)

                self.assertEqual(status, 1)
                self.assertEqual(len(result), len(input[-1]))

    def test_filter_exists(self):
        test_cases = {
            "field exists (1)": {
                "pos": 0,
                "query": "a=",
                "input": (0, ['a=1', 'b=1', ''])
            },
            "field exists (2)": {
                "pos": 1,
                "query": "b=",
                "input": (0, ['a=1', 'b=1', ''])
            }
        }

        for title, test_case in test_cases.items():
            # print(f'running "{title}"; test_args={test_case}')
            query, pos, input = test_case["query"], test_case["pos"], test_case["input"]
            status, result = FilterField((pos, query)).execute(input)

            self.assertEqual(status, 0)
            self.assertEqual(len(result), len(input[-1]))


class TestFilterFieldsWithPos(unittest.TestCase):
    def test_with_exact_match(self):
        test_cases = {
            "only_one_res": {
                "pos": 1,
                "queries": ["b"],
                "input_arrs": [(0, ["a", "bb", "c"]), (0, ["b", "b", "c", "c"])],
                "expect": [(1, 3), (0, 4)]
            },
            "only_two_res": {
                "pos": 1,
                "queries": ["b", "a"],
                "input_arrs": [(0, ["a", "b", "c"]), (0, ["1", "a", "a", "c"])],
                "expect": [(0, 3), (0, 4)]
            },
            "only_1/2": {
                "pos": 1,
                "queries": ["b", "a"],
                "input_arrs": [(0, ["a", "bb", "c"]), (0, ["1", "a", "a", "c"])],
                "expect": [(1, 3), (0, 4)]
            },
            "only_0/2": {
                "pos": 1,
                "queries": ["b", "a"],
                "input_arrs": [(0, ["a", "bb", "c"]), (0, ["1", "aa", "a", "c"])],
                "expect": [(1, 3), (1, 4)]
            }
        }

        for title, tc in test_cases.items():
            # print(title)
            pos, queries, input_arrs = tc["pos"], tc["queries"], tc["input_arrs"]
            for i, ia in enumerate(input_arrs):
                status, res_arr = FilterFields(
                    pos, queries, exact_match=True).execute(ia)
                self.assertEqual(status, tc["expect"][i][0], f"input_arrs={
                                 ia} queries={queries} expect={tc["expect"][i]}")
                self.assertEqual(len(res_arr), tc["expect"][i][1])

    def test_all_exist(self):
        test_cases = {
            "one_key": {
                "pos": 1,
                "queries": ["b"],
                "input_arrs": [(0, ["a", "b", "c"]), (0, ["b", "b", "c", "c"])]
            },
            "two_keys": {
                "pos": 1,
                "queries": ["b", "a"],
                "input_arrs": [(0, ["a", "b", "c"]), (0, ["1", "a", "a", "c"])]
            }
        }

        for title, tc in test_cases.items():
            # print(title)
            pos, queries, input_arrs = tc["pos"], tc["queries"], tc["input_arrs"]
            for ia in input_arrs:
                status, res_arr = FilterFields(pos, queries).execute(ia)
                self.assertEqual(status, 0)
                self.assertEqual(len(res_arr), len(ia[1]))

    def test_some_exist(self):
        test_cases = {
            "one_key": {
                "pos": 1,
                "queries": ["b"],
                "input_arrs": [(0, ["a", "b", "c"]), (0, ["b", "c", "c", "c"])],
                "expect": [(0, 3), (1, 4)]
            },
            "two_keys": {
                "pos": 1,
                "queries": ["b", "a"],
                "input_arrs": [(0, ["a", "c", "c"]), (0, ["1", "a", "a", "c"])],
                "expect": [(1, 3), (0, 4)]
            }
        }

        for title, tc in test_cases.items():
            # print(title)
            pos, queries, input_arrs = tc["pos"], tc["queries"], tc["input_arrs"]
            for i, ia in enumerate(input_arrs):
                status, res_arr = FilterFields(pos, queries).execute(ia)
                self.assertEqual(
                    status, tc["expect"][i][0], f"input_arrs={ia} queries={queries} expect={tc["expect"][i]}")
                self.assertEqual(len(res_arr), tc["expect"][i][1])

    def test_nonexist(self):
        test_cases = {
            "one_key": {
                "pos": 5,
                "queries": ["b"],
                "input_arrs": [(0, ["a", "b", "c"]), (0, ["b", "c", "c", "c"])],
                "expect": [(1, 3), (1, 4)]
            },
            "two_keys": {
                "pos": 1,
                "queries": ["x", "y"],
                "input_arrs": [(0, ["a", "c", "c"]), (0, ["1", "a", "a", "c"])],
                "expect": [(1, 3), (1, 4)]
            },
            "empty_value": {
                "pos": 1,
                "queries": ["", ""],
                "input_arrs": [(0, ["a", "c", "c"]), (0, ["1", "c", "a", "c"])],
                "expect": [(0, 3), (0, 4)]
            }
        }

        for title, tc in test_cases.items():
            # print(title)
            pos, queries, input_arrs = tc["pos"], tc["queries"], tc["input_arrs"]
            for i, ia in enumerate(input_arrs):
                status, res_arr = FilterFields(pos, queries).execute(ia)
                self.assertEqual(status, tc["expect"][i][0], f"expect={
                                 tc['expect'][i]} got=({status}, {res_arr})")
                self.assertEqual(len(res_arr), tc["expect"][i][1])


class TestCanonize(unittest.TestCase):
    def generate_mock_input(self, syscall: str):
        all_samples = [
            # write
            (0, ['19:52:17.818965', 'write', 'F=17',
             'B=0x1', '0.000004', 'Code', 'Helper.21271']),
            (0, ['19:52:17.953316', 'write', 'F=78',
             'B=0x3dc', '0.000151', 'acumbrellaagent.6946']),
            # read
            (0, ['19:52:17.818972', 'read', 'F=16',
             'B=0x1', '0.000001', 'Code', 'Helper.21271']),
            (0, ['19:52:17.824597', 'read', 'F=35',
             '[', '35]', '0.000004', 'ampdaemon.8720']),
            (0, ['19:52:17.882232', 'read', 'F=33',
             'B=0x92c', '0.000008', 'ampdaemon.8244']),
            # open
            (0, ['19:53:11.248385', 'open', 'F=35', '(R_______F_V_)', 'Library/Mail/V8/E7E363C2-BB21-4A69-A1E5-CB22FB478997/[Gmail].mbox/All',
             'Mail.mbox/D22A1D5B-AA8F-41A3-892E-930CF85504E8/Data/8/9/3/Messages/398336.partial.emlx', '0.000218', 'ampdaemon.250630']),
            (0, ['19:52:34.635146', 'open', 'F=33', '(R_______F_V_)', '/Users/sinaee/Library/Application',
             'Support/Google/Chrome/Profile', '1/Shortcuts', '0.000185', 'ampdaemon.250630']),
            (0, ['19:52:34.651249', 'open', 'F=38', '(R_______F___)', '/Applications/Google',
             'Chrome.app/Contents/MacOS/Google', 'Chrome', '0.000035', 'ampdaemon.8640']),
            (0,
             ["18:46:30.430549", "open", "[2]", "(R_____N____X)", "/Users/sinaee/Library/Application", "Support/Google/Chrome/Profile",  "0.000011", "Google", "Chrome.7874"]),
            # close
            (0, ['19:53:19.842752', 'close', 'F=64',
             '0.000004', 'Code', 'Helper.21316']),
            (0, ['19:52:57.953020', 'close', 'F=3',
             '0.000005', 'com.docker.cli.466051']),
            (0, ['19:52:19.418225', 'close',
             'F=8088[', '9]', '0.000001', 'lsof.465025']),
            (0, ['19:52:19.416572', 'close',
             'F=1045[', '9]', '0.000001', 'lsof.465025']),
            # mkdir
            (0, ['19:52:17.969603', 'mkdir', '/Library/Application', 'Support/Cisco/AMP', 'for', 'Endpoints',
             'Connector/scannertmp/20240329_195217-scantemp.524e726695', '0.000198', 'ampscansvc.8242']),
            (0, ['19:52:18.516542', 'mkdir', '[17]',
             'private/var/folders/qk/4xtqd_nn3kx8q5m4df7prpzh0000gp/T', '0.000004', 'git.464994']),
            (0, ['19:52:18.523903', 'mkdir', '[17]',
             'private/var/folders/qk/4xtqd_nn3kx8q5m4df7prpzh0000gp/T', '0.000006', 'git.464995']),
            # rename
            (0, ['19:52:34.722431', 'rename', '/Users/sinaee/Library/Application', 'Support/Google/Chrome/Profile',
                 '1/IndexedDB/https_docs.google.com_0.indexeddb.leveldb/LOG', '0.000855', 'Google', 'Chrome.8803']),
            (0, ['19:52:34.782196', 'rename', '/Users/sinaee/Library/Caches/Google/Chrome/Profile',
             '1/Cache/Cache_Data/dcceb247e0b3a75d_0', '0.000402', 'Google', 'Chrome', 'Helper.8882']),
            (0, ['19:52:36.107106', 'rename', '/Users/sinaee/Library/Application',
             'Support/Google/Chrome/Profile', '1/.com.google.Chrome.HL1NBs', '0.001140', 'Google', 'Chrome.8803']),
            # mmap
            (0, ['19:52:18.420544', 'mmap', 'F=0', 'A=0x400000000001',
                 'O=0x00000000', 'B=0x4000100000000', '<>', '0.000002', 'ps.464993']),
            (0, ['19:52:18.512452', 'mmap', 'F=0', 'A=0x400000000001',
             'O=0x00000000', 'B=0x4000100000000', '<>', '0.000003', 'git.464994']),
            (0, ['19:52:18.513592', 'mmap', 'F=0', 'A=0x052cc000000001',
             'O=0x00000000', 'B=0x4200200000000', '<>', '0.000020', 'git.464994']),
            (0, ['19:52:18.514199', 'mmap', 'F=7077888', 'A=0xc00000000005',
             'O=0x00000000', 'B=0x4001200000000', '<>', '0.000024', 'git.464994']),

        ]

        return [syscall_sample for syscall_sample in all_samples if syscall_sample[1][1].strip() == syscall.strip()]

    def test_mmap(self):
        test_cases = {
            "expect": [
                (0, ['19:52:18.420544', 'mmap', '0', '<>', 'ps', '464993']),
                (0, ['19:52:18.512452', 'mmap', '0', '<>', 'git', '464994']),
                (0, ['19:52:18.513592', 'mmap', '0', '<>', 'git', '464994']),
                (0, ['19:52:18.514199', 'mmap', '7077888', '<>', 'git', '464994']),
            ]
        }

        for i, arr in enumerate(self.generate_mock_input('mmap')):
            res = Canonize().execute(arr)
            # fmt: off
            self.assertEqual(res, test_cases['expect'][i], f'expected: {test_cases['expect'][i]}, got: {res} for input={arr}')
            # fmt: on

    def test_rename(self):
        test_cases = {
            "expect": [
                (0, ['19:52:34.722431', 'rename', '-1',
                 '/Users/sinaee/Library/Application Support/Google/Chrome/Profile 1/IndexedDB/https_docs.google.com_0.indexeddb.leveldb/LOG', 'Google Chrome', '8803']),
                (0, ['19:52:34.782196', 'rename', '-1', '/Users/sinaee/Library/Caches/Google/Chrome/Profile 1/Cache/Cache_Data/dcceb247e0b3a75d_0',
                 'Google Chrome Helper', '8882']),
                (0, ['19:52:36.107106', 'rename', '-1',
                 '/Users/sinaee/Library/Application Support/Google/Chrome/Profile 1/.com.google.Chrome.HL1NBs', 'Google Chrome', '8803']),
            ]
        }

        for i, arr in enumerate(self.generate_mock_input('rename')):
            res = Canonize().execute(arr)
            # fmt: off
            self.assertEqual(res, test_cases['expect'][i], f'expected: {test_cases['expect'][i]}, got: {res} for input={arr}')
            # fmt: on

    def test_mkdir(self):
        test_cases = {
            "expect": [
                (0, ['19:52:17.969603', 'mkdir', '-1',
                 '/Library/Application Support/Cisco/AMP for Endpoints Connector/scannertmp/20240329_195217-scantemp.524e726695', 'ampscansvc', '8242']),
                (0, ['19:52:18.516542', 'mkdir', '-1',
                 'private/var/folders/qk/4xtqd_nn3kx8q5m4df7prpzh0000gp/T', 'git', '464994']),
                (0, ['19:52:18.523903', 'mkdir', '-1',
                 'private/var/folders/qk/4xtqd_nn3kx8q5m4df7prpzh0000gp/T', 'git', '464995'])
            ]
        }

        for i, arr in enumerate(self.generate_mock_input('mkdir')):
            res = Canonize().execute(arr)
            # fmt: off
            self.assertEqual(res, test_cases['expect'][i], f'expected: {test_cases['expect'][i]}, got: {res} for input={arr}')
            # fmt: on

    def test_write(self):
        test_cases = {
            "expect": [
                (0, ['19:52:17.818965', 'write', '17', 'Code Helper', '21271']),
                (0, ['19:52:17.953316', 'write', '78', 'acumbrellaagent', '6946']),
            ]
        }

        for i, arr in enumerate(self.generate_mock_input('write')):
            res = Canonize().execute(arr)
            # fmt: off
            self.assertEqual(res, test_cases['expect'][i], f'expected: {test_cases['expect'][i]}, got: {res} for input={arr}')
            # fmt: on

    def test_read(self):
        test_cases = {
            "expect": [
                (0, ['19:52:17.818972', 'read', '16', 'Code Helper', '21271']),
                (0, ['19:52:17.824597', 'read', '35', 'ampdaemon', '8720']),
                (0, ['19:52:17.882232', 'read', '33', 'ampdaemon', '8244'])
            ]
        }

        # fmt: on
        for i, arr in enumerate(self.generate_mock_input('read')):
            res = Canonize().execute(arr)
            # fmt: off
            self.assertEqual(res, test_cases['expect'][i], f'expected: {test_cases['expect'][i]}, got: {res} for input={arr}')
            # fmt: on

    def test_open(self):
        test_cases = {
            "expect": [
                (0, ['19:53:11.248385', 'open', '35', 'Library/Mail/V8/E7E363C2-BB21-4A69-A1E5-CB22FB478997/[Gmail].mbox/All Mail.mbox/D22A1D5B-AA8F-41A3-892E-930CF85504E8/Data/8/9/3/Messages/398336.partial.emlx', 'ampdaemon', '250630']),
                (0, ['19:52:34.635146', 'open', '33',
                 '/Users/sinaee/Library/Application Support/Google/Chrome/Profile 1/Shortcuts', 'ampdaemon', '250630']),
                (0, ['19:52:34.651249', 'open', '38',
                 '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', 'ampdaemon', '8640']),
                (0,
                 ["18:46:30.430549", "open", "-1", "/Users/sinaee/Library/Application Support/Google/Chrome/Profile", "Google Chrome", "7874"])

            ]
        }

        # fmt: on
        for i, arr in enumerate(self.generate_mock_input(syscall='open')):
            res = Canonize().execute(arr)
            # fmt: off
            self.assertEqual(res, test_cases['expect'][i], f'expected: {test_cases['expect'][i]}, got: {res} for input={arr}')
            # fmt: on

    def test_close(self):
        test_cases = {
            "expect": [
                (0, ['19:53:19.842752', 'close', '64', 'Code Helper', '21316']),
                (0, ['19:52:57.953020', 'close', '3', 'com.docker.cli', '466051']),
                (0, ['19:52:19.418225', 'close', '8088', 'lsof', '465025']),
                (0, ['19:52:19.416572', 'close', '1045', 'lsof', '465025'])
            ]
        }

        # fmt: on
        for i, arr in enumerate(self.generate_mock_input(syscall='close')):
            res = Canonize().execute(arr)
            # fmt: off
            self.assertEqual(res, test_cases['expect'][i], f'expected: {test_cases['expect'][i]}, got: {res} for input={arr}')
            # fmt: on


if __name__ == "__main__":
    unittest.main()

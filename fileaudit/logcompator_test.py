import unittest
import string
from abstract import IWriter
from logcompator import CompactRecord, LogCompactor
import hashlib
import typing
import random


class MockData:
    @staticmethod
    def only_open_close():
        return [
            (0, ['13:38:34.127529', 'open', '1',
             '/path/foo/text1', 'app1', '381720']),
            (0, ['13:38:34.127535', 'close', '1', 'app1', '381720'])
        ]

    @staticmethod
    def open_close_rw():
        return [
            (0, ['13:38:34.127529', 'open', '3',
             '/path/foo/text2', 'app1', '381721']),
            (0, ['13:38:34.127532', 'read', '3', 'app1', '381721']),
            (0, ['13:38:34.127533', 'write', '3', 'app1', '381721']),
            (0, ['13:38:34.127535', 'close', '3', 'app1', '381721'])
        ]

    @staticmethod
    def only_rw():
        return [
            (0, ['13:38:34.127532', 'read', '2', 'app1', '381722']),
            (0, ['13:38:34.127533', 'write', '2', 'app1', '381722']),
        ]

    @staticmethod
    def neg_fd():
        return [
            (0, ['13:38:23.403654', 'open', '-1',
             '/path/foo/nosuccess', 'com.docker.cli', '381337'])
        ]

    @staticmethod
    def only_open():
        return [
            (0, ['13:38:23.403654', 'open', '1',
             '/path/foo/nosuccess', 'com.docker.cli', '381337'])
        ]

    @staticmethod
    def mkdir_rename_mmap():
        return [
            (0, ['14:21:25.532390', 'mkdir', '1',
             '/path/foo/text4', 'ampscansvc', '8322']),
            (0, ['14:21:25.585988', 'rename', '1',
             '/path/foo/text5', 'acumbrellaagent', '6707']),
            (0, ['14:21:26.727314', 'mmap', '1', '<>', 'docker', '459788'])
        ]

    @staticmethod
    def close_without_open():
        return [
            (0, ['18:36:21.633351', 'close', '30', 'ampdaemon', '8310']),
        ]

    @staticmethod
    def multiple_close():
        return [
            (0, ['18:36:21.633370', 'close', '32', 'ampdaemon', '8310']),
            (0, ['18:36:21.633370', 'close', '10', 'ampdaemon', '8310']),
        ]


class MockWriter(IWriter):
    def __init__(self) -> None:
        super().__init__()
        self.state = []

    def write(self, arr) -> None:
        assert type(arr) == list, f'given arr is not a list; got arr of type {
            type(arr)}'
        self.state.append(arr)

    def get_state(self) -> typing.List:
        return self.state


class TestCompactRecord(unittest.TestCase):
    def generate_random_string(length=5):
        letters = string.ascii_letters
        return ''.join(random.choice(letters) for _ in range(length))

    def test_basic(self):
        cr = CompactRecord()

        cr.add_procname('test_procname')
        cr.add_pid('test_pid')
        cr.add_path('test_path')
        cr.add_event('event1', 'today', 'ts1')
        cr.add_event('event2', 'today', 'ts2')

        expect = ['test_pid', 'test_procname', 'test_path',
                  ['event1|today_ts1', 'event2|today_ts2']]
        self.assertEqual(cr.to_list(), expect, f"compact record doesn't match; expected={
                         expect}, got={cr.to_list()}")

    def test_multiple_events(self):

        def ops(x): return [
            ([TestCompactRecord.generate_random_string()], x.add_pid),
            ([TestCompactRecord.generate_random_string()], x.add_procname),
            ([TestCompactRecord.generate_random_string()], x.add_path),
            ([TestCompactRecord.generate_random_string(), TestCompactRecord.generate_random_string(
            ), TestCompactRecord.generate_random_string()], x.add_event),
            ([TestCompactRecord.generate_random_string(), TestCompactRecord.generate_random_string(
            ), TestCompactRecord.generate_random_string()], x.add_event),
            ([TestCompactRecord.generate_random_string(), TestCompactRecord.generate_random_string(
            ), TestCompactRecord.generate_random_string()], x.add_event)
        ]

        # shuffle the ops and run them for a few iterations
        for iter in range(1):
            print(f'running iter={iter}')
            cr = CompactRecord()

            all_ops = ops(cr)

            # flatten the event list
            events = []
            for op in all_ops[3:]:
                events += op[0]
            print('events', events)

            expect = [
                all_ops[0][0][0],
                all_ops[1][0][0],
                all_ops[2][0][0],
                [
                    CompactRecord.event_name_datets_sep.join(
                        [x, CompactRecord.date_ts_sep.join([y, z])])
                    for x, y, z in zip(events[::3], events[1::3], events[2::3])
                ]
            ]

            for args, func_call in all_ops:
                func_call(*args)

            self.assertEqual(expect, cr.to_list(), f'expect={
                             expect}, got={cr.to_list()}')


class TestLogCompactor(unittest.TestCase):
    def get_sha256(self, record: typing.List[str]) -> str:
        assert type(record) == list, f'record is not a list; type={
            type(record)}'

        # create a string from the the given record
        data = ''
        for field in record:
            if type(field) == list:
                data += ''.join(field)
            else:
                data += field

        sha256 = hashlib.sha256()
        sha256.update(data.encode('utf-8'))

        return sha256.hexdigest()

    def run_helper(self, test_num: int):
        expects = None
        expected_log_length = 4

        data = None

        writer = MockWriter()
        log_compactor = LogCompactor(writer, datefunc=lambda: "today")

        match test_num:
            case 1:
                expects = [['381720', 'app1', '/path/foo/text1',
                            ['open|today_13:38:34.127529', 'close|today_13:38:34.127535']]]

                data = MockData.only_open_close()
            case 2:
                #  (0, ['13:38:34.127529', 'open', '3', '/path/foo/text2', 'app1', '381721']),
                #  (0, ['13:38:34.127532', 'read', '3', 'app1', '381721']),
                #  (0, ['13:38:34.127533', 'write', '3', 'app1', '381721']),
                #  (0, ['13:38:34.127535', 'close', '3', 'app1', '381721'])
                expects = [['381721', 'app1', '/path/foo/text2', [
                    'open|today_13:38:34.127529',
                    'read|today_13:38:34.127532',
                    'write|today_13:38:34.127533',
                    'close|today_13:38:34.127535']]]

                data = MockData.open_close_rw()
            case 3:
                # (0, ['13:38:34.127532', 'read', '2', 'app1', '381722']),
                # (0, ['13:38:34.127533', 'write', '2', 'app1', '381722']),
                expects = [[
                    '381722', 'app1', '',
                    [
                        'read|today_13:38:34.127532',
                        'write|today_13:38:34.127533'
                    ]]]

                data = MockData.only_rw()
            case 4:
                #  neg fd; (0, ['13:38:23.403654', 'open', '-1', '/path/foo/nosuccess', 'com.docker.cli', '381337'])
                expects = []

                data = MockData.neg_fd()
            case 5:
                # (0, ['13:38:23.403654', 'open', '1', '/path/foo/nosuccess', 'com.docker.cli', '381337'])
                expects = [['381337', 'com.docker.cli', '/path/foo/nosuccess', [
                    'open|today_13:38:23.403654'
                ]]]
                data = MockData.only_open()
            case 6:
                # (0, ['14:21:25.532390', 'mkdir', '1', '/path/foo/text4', 'ampscansvc', '8322']),
                # (0, ['14:21:25.585988', 'rename', '1', '/path/foo/text5', 'acumbrellaagent', '6707']),
                # (0, ['14:21:26.727314', 'mmap', '1', '<>', 'docker', '459788'])
                expects = [
                    ['8322', 'ampscansvc', '/path/foo/text4',
                        ['mkdir|today_14:21:25.532390']],
                    ['6707', 'acumbrellaagent', '/path/foo/text5',
                        ['rename|today_14:21:25.585988']],
                    ['459788', 'docker', '<>', ['mmap|today_14:21:26.727314']],
                ]

                data = MockData.mkdir_rename_mmap()
            case 7:
                # (0, ['18:36:21.633351', 'close', '30', 'ampdaemon', '8310']),
                expects = [[
                    '8310', 'ampdaemon', '', ['close|today_18:36:21.633351']
                ]]

                data = MockData.close_without_open()
            case 8:
                # (0, ['18:36:21.633370', 'close', '32', 'ampdaemon', '8310']),
                # (0, ['18:36:21.633370', 'close', '10', 'ampdaemon', '8310']),
                expects = [
                    ['8310', 'ampdaemon', '', ['close|today_18:36:21.633370']],
                    ['8310', 'ampdaemon', '', ['close|today_18:36:21.633370']]
                ]

                data = MockData.multiple_close()
            case _:
                raise Exception("no matching test case")

        for record in data:
            log_compactor.execute(record)

        state = None
        if test_num not in (1, 2, 7, 8):
            state = log_compactor.get_state()
        else:
            state = writer.get_state()

        for log_record in state:
            assert len(log_record) == expected_log_length, f'expected to have fields in the log record; got={
                len(log_record)}'

        # validate the state
        if test_num in (4, ):
            assert len(state) == 0, f"expected an empty state; got={state}"
        else:
            assert state, f"the returned state is not valid; got {
                state} of type: {type(state)}"

        # validate against the length of the returned state
        assert len(state) == len(expects), f"the state's length is not matched with the expected length; expects {
            len(expects)}, got={len(state)}; state={state} expects={expects}"

        # validate if all expected md5 exists
        # calculate the md5 of each record in the state
        state_hash = {self.get_sha256(
            state_record): i for i, state_record in enumerate(state)}

        # cacluate the md5 of the expected record
        for expected_record in expects:
            er_hash = self.get_sha256(expected_record)

            assert er_hash in state_hash, f"the record does not exist in our state; \nexpected_record={
                expected_record}; \ngot={state}; \nstate_hash={state_hash}; \nhash={er_hash}"

        return True

    def test_open_close(self):
        self.assertTrue(self.run_helper(1))

    def test_open_close_with_rw(self):
        self.assertTrue(self.run_helper(2))

    def test_rw_no_open_close(self):
        self.assertTrue(self.run_helper(3))

    def test_neg_fd(self):
        self.assertTrue(self.run_helper(4))

    def test_only_open(self):
        self.assertTrue(self.run_helper(5))

    def test_rename_mkdir_mmap(self):
        self.assertTrue(self.run_helper(6))

    def test_close_wo_open(self):
        self.assertTrue(self.run_helper(7))

    def test_multiple_close(self):
        self.assertTrue(self.run_helper(8))

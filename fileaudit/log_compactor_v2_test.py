from abstract import IWriter
from log_compactor_v2 import FileEvent, LogCompactorV2, LogRecordV2
import unittest


class TestFileEvent(unittest.TestCase):
    def test_empty(self):
        fe = FileEvent()

        self.assertEqual(
            ['', '', '', 0], fe.to_list()
        )

    def test_empty_mode(self):
        fe = FileEvent().add_filename('file1').add_open_ts('ts1').add_close_ts('ts2')

        self.assertEqual(
            ['file1', 'ts1', 'ts2', 0],
            fe.to_list()
        ), f'expected {['file1', 'ts1', 'ts2', []]}, got {fe.to_list()}'

    def test_full_record(self):
        fe = FileEvent() \
            .add_filename('file2') \
            .add_open_ts('ts3') \
            .add_close_ts('ts4') \
            .add_mode(FileEvent.MODE_READ) \
            .add_mode(FileEvent.MODE_WRITE) \
            .add_mode(FileEvent.MODE_MKDIR) \
            .add_mode(FileEvent.MODE_MMAP) \
            .add_mode(FileEvent.MODE_RENAME)

        self.assertEqual(
            ['file2', 'ts3', 'ts4', 31],
            fe.to_list()
        ), f'expected {['file2', 'ts3', 'ts4', 31]} got {fe.to_list()}'

    def test_full_record_with_dups(self):
        fe = FileEvent() \
            .add_filename('file2') \
            .add_open_ts('ts3') \
            .add_close_ts('ts4') \
            .add_mode(FileEvent.MODE_MMAP) \
            .add_mode(FileEvent.MODE_READ) \
            .add_mode(FileEvent.MODE_WRITE) \
            .add_mode(FileEvent.MODE_MKDIR) \
            .add_mode(FileEvent.MODE_RENAME)\
            .add_mode(FileEvent.MODE_READ) \
            .add_mode(FileEvent.MODE_MMAP) \
            .add_mode(FileEvent.MODE_RENAME)

        self.assertEqual(
            ['file2', 'ts3', 'ts4', 31],
            fe.to_list()
        ), f'expected {['file2', 'ts3', 'ts4', 31]} got {fe.to_list()}'

    def test_get_dict_full_with_dups(self):
        fe = FileEvent() \
            .add_filename('file2') \
            .add_open_ts('ts3') \
            .add_close_ts('ts4') \
            .add_mode(FileEvent.MODE_MMAP) \
            .add_mode(FileEvent.MODE_READ) \
            .add_mode(FileEvent.MODE_WRITE) \
            .add_mode(FileEvent.MODE_MKDIR) \
            .add_mode(FileEvent.MODE_RENAME)\
            .add_mode(FileEvent.MODE_READ) \
            .add_mode(FileEvent.MODE_MMAP) \
            .add_mode(FileEvent.MODE_RENAME)

        self.assertEqual(
            {'fname': 'file2', 'open': 'ts3', 'close': 'ts4', 'mode': 31},
            fe.to_dict()
        ), f"expected {{'fname': 'file2', 'open': 'ts3', 'close': 'ts4', 'mode': 31}} got {fe.to_dict()}"


class TestLogRecordV2(unittest.TestCase):
    def test_empty(self):
        lr = LogRecordV2('pid', 'procname', 'path')

        self.assertEqual(
            ['pid', 'procname', 'path', []],
            lr.to_list()
        )

    def test_one_proc_one_file_1(self):
        lr = LogRecordV2(
            'pid',
            'proc',
            'path'
        ).add_file_event(file_name='file1', ts='ts1', op='open')

        self.assertEqual(
            ['pid', 'proc', 'path', [['file1', 'ts1', '', 0]]],
            lr.to_list()
        )

    def test_one_proc_one_file_2(self):
        lr = LogRecordV2(
            'pid',
            'proc',
            'path'
        ).add_file_event(file_name='file1', ts='ts1', op='open') \
            .add_file_event(file_name='file1', ts='ts2', op='read') \
            .add_file_event(file_name='file1', ts='ts3', op='write') \
            .add_file_event(file_name='file1', ts='ts4', op='mmap') \
            .add_file_event(file_name='file1', ts='ts5', op='mkdir') \
            .add_file_event(file_name='file1', ts='ts5', op='rename') \
            .add_file_event(file_name='file1', ts='ts6', op='close') \

        self.assertEqual(
            ['pid', 'proc', 'path', [['file1', 'ts1', 'ts6', 31]]],
            lr.to_list()
        )

    def test_one_proc_one_file_3(self):
        lr = LogRecordV2(
            'pid',
            'proc',
            'path'
        ).add_file_event(file_name='file1', ts='ts1', op='open') \
            .add_file_event(file_name='file1', ts='ts2', op='read') \
            .add_file_event(file_name='file1', ts='ts3', op='write') \
            .add_file_event(file_name='file1', ts='ts4', op='mmap') \
            .add_file_event(file_name='file1', ts='ts5', op='mkdir') \
            .add_file_event(file_name='file1', ts='ts5', op='rename') \
            .add_file_event(file_name='file1', ts='ts6', op='close') \

        lr.add_file_event(file_name='file2', ts='ts7', op='open') \
            .add_file_event(file_name='file2', ts='ts8', op='read') \
            .add_file_event(file_name='file2', ts='ts9', op='close') \

        self.assertEqual(
            ['pid', 'proc', 'path', [['file1', 'ts1', 'ts6', 31],
                                     ['file2', 'ts7', 'ts9', 1]]],
            lr.to_list()
        )

    def test_one_proc_same_file_1(self):
        lr = LogRecordV2(
            'pid',
            'proc',
            'path'
        ).add_file_event(file_name='file1', ts='ts1', op='open') \
            .add_file_event(file_name='file1', ts='ts2', op='read') \
            .add_file_event(file_name='file1', ts='ts3', op='write') \
            .add_file_event(file_name='file1', ts='ts4', op='mmap') \
            .add_file_event(file_name='file1', ts='ts5', op='mkdir') \
            .add_file_event(file_name='file1', ts='ts5', op='rename') \
            .add_file_event(file_name='file1', ts='ts6', op='close') \

        lr.add_file_event(file_name='file1', ts='ts7', op='open') \
            .add_file_event(file_name='file1', ts='ts8', op='read') \
            .add_file_event(file_name='file1', ts='ts9', op='close') \

        self.assertEqual(
            ['pid', 'proc', 'path', [['file1', 'ts1', 'ts6', 31],
                                     ['file1', 'ts7', 'ts9', 1]]],
            lr.to_list()
        )

    def test_one_proc_same_file_2(self):
        lr = LogRecordV2(
            'pid',
            'proc',
            'path'
        ).add_file_event(file_name='file1', ts='ts1', op='open') \
            .add_file_event(file_name='file1', ts='ts2', op='read') \
            .add_file_event(file_name='file1', ts='ts3', op='write') \
            .add_file_event(file_name='file1', ts='ts4', op='mmap') \
            .add_file_event(file_name='file1', ts='ts5', op='mkdir') \
            .add_file_event(file_name='file1', ts='ts5', op='rename') \
            .add_file_event(file_name='file1', ts='ts6', op='close') \

        lr.add_file_event(file_name='file1', ts='ts7', op='open') \
            .add_file_event(file_name='file1', ts='ts8', op='read') \
            .add_file_event(file_name='file1', ts='ts9', op='close')

        lr.add_file_event(file_name='file1', ts='ts10', op='read') \
            .add_file_event(file_name='file1', ts='ts11', op='close')

        self.assertEqual(
            ['pid', 'proc', 'path', [['file1', 'ts1', 'ts6', 31],
                                     ['file1', 'ts7', 'ts9', 1],
                                     ['file1', '', 'ts11', 1]
                                     ]],
            lr.to_list()
        )

    def test_one_proc_multi_files(self):
        lr = LogRecordV2(
            'pid',
            'proc',
            'path'
        ).add_file_event(file_name='file1', ts='ts1', op='open') \
            .add_file_event(file_name='file1', ts='ts2', op='read') \
            .add_file_event(file_name='file1', ts='ts3', op='write') \
            .add_file_event(file_name='file1', ts='ts4', op='mmap') \
            .add_file_event(file_name='file1', ts='ts5', op='mkdir') \
            .add_file_event(file_name='file1', ts='ts5', op='rename') \
            .add_file_event(file_name='file1', ts='ts6', op='close') \

        lr.add_file_event(file_name='file2', ts='ts7', op='open') \
            .add_file_event(file_name='file2', ts='ts8', op='read') \
            .add_file_event(file_name='file2', ts='ts9', op='close')

        lr.add_file_event(file_name='file3', ts='ts10', op='read') \
            .add_file_event(file_name='file3', ts='ts11', op='close')

        self.assertEqual(
            ['pid', 'proc', 'path', [['file1', 'ts1', 'ts6', 31],
                                     ['file2', 'ts7', 'ts9', 1],
                                     ['file3', '', 'ts11', 1]
                                     ]],
            lr.to_list()
        )

    def test_one_proc_to_dict(self):
        lr = LogRecordV2(
            'pid',
            'proc',
            'path'
        ).add_file_event(file_name='file1', ts='ts1', op='open') \
            .add_file_event(file_name='file1', ts='ts2', op='read') \
            .add_file_event(file_name='file1', ts='ts3', op='write') \
            .add_file_event(file_name='file1', ts='ts4', op='mmap') \
            .add_file_event(file_name='file1', ts='ts5', op='mkdir') \
            .add_file_event(file_name='file1', ts='ts5', op='rename') \
            .add_file_event(file_name='file1', ts='ts6', op='close') \

        lr.add_file_event(file_name='file1', ts='ts7', op='open') \
            .add_file_event(file_name='file1', ts='ts8', op='read') \
            .add_file_event(file_name='file1', ts='ts9', op='close')

        lr.add_file_event(file_name='file1', ts='ts10', op='read') \
            .add_file_event(file_name='file1', ts='ts11', op='close')

        self.assertEqual(
            {'pid': 'pid', 'proc': 'proc', 'exec_path': 'path', 'events': [
                {'fname': 'file1', 'open': 'ts1', 'close': 'ts6', 'mode': 31},
                {'fname': 'file1', 'open': 'ts7', 'close': 'ts9', 'mode': 1},
                {'fname': 'file1', 'open': '', 'close': 'ts11', 'mode': 1}
            ]},
            lr.to_dict()
        )


# V2:
# [  ‘pid',
#    'procname’,
#    ‘Executable_path’,
#    [ ['file1', open='ts1', close='ts2', mode=R],
#    ['file2', open='ts3', close='ts4', mode=RW],
#    ['file3', open='ts5', close='ts6', mode=W] ],
# ]
class TestLogCompactorV2(unittest.TestCase):
    class MockData:
        @staticmethod
        def one_proce_multi_files():
            """
            one process with multiple files. The process opens one file two times and then open another one after that
            """
            return [
                (0, ['13:38:34.127529', 'open', '1', '/path/foo/text1', 'app1', '381720']),
                (0, ['13:38:34.127535', 'close', '1', 'app1', '381720']),
                (0, ['13:38:34.127529', 'open', '1', '/path/foo/text1', 'app1', '381720']),
                (0, ['13:38:34.127529', 'open', '2', '/path/foo/text2', 'app1', '381720']),
                (0, ['13:38:34.127535', 'close', '2', 'app1', '381720']),
                (0, ['13:38:34.127535', 'close', '1', 'app1', '381720'])
            ]

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
        def __init__(self):
            self.output = []

        def write(self, data):
            self.output.append(data)

        def get_output(self):
            return self.output

    class MockExecPath:
        def __init__(self, format_str: str):
            self.format_str = format_str

        def get_exec_path(self, procname, _):
            return self.format_str.format(procname)
# V2:
# [  ‘pid',
#    'procname’,
#    ‘Executable_path’,
#    [ ['file1', open='ts1', close='ts2', mode=R],
#    ['file2', open='ts3', close='ts4', mode=RW],
#    ['file3', open='ts5', close='ts6', mode=W] ],
# ]

    def test_empty(self):
        lc = LogCompactorV2(writer=None)

        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_only_open_close(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.only_open_close():
            lc.execute(record)

        # [
        #  (0, ['13:38:34.127529', 'open', '1','/path/foo/text1', 'app1', '381720']),
        #  (0, ['13:38:34.127535', 'close', '1', 'app1', '381720'])
        # ]

        self.assertEqual(
            [
                {'pid': '381720', 'proc': 'app1', 'exec_path': '/path/to/app1',
                 'events': [
                     {
                        'fname': '/path/foo/text1',
                        'open': '13:38:34.127529',
                        'close': '13:38:34.127535',
                        'mode': 0
                     }
                 ]
                 }
            ], lc.to_list()
        )

        # need this call to write the current state of the compactor to the writer and delete its state
        # this is used in this way so that we can configure compressing every 1m, 1h, 1d, etc
        lc.dump()
        self.assertEqual(
            [
                {'pid': '381720', 'proc': 'app1', 'exec_path': '/path/to/app1',
                 'events': [
                     {
                        'fname': '/path/foo/text1',
                        'open': '13:38:34.127529',
                        'close': '13:38:34.127535',
                        'mode': 0
                     }
                 ]
                 }
            ], list_writer.get_output()
        )

        # if we dump the state, the state has to be empty
        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_open_close_rw(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.open_close_rw():
            lc.execute(record)

        # (0, ['13:38:34.127529', 'open', '3',
        #      '/path/foo/text2', 'app1', '381721']),
        # (0, ['13:38:34.127532', 'read', '3', 'app1', '381721']),
        # (0, ['13:38:34.127533', 'write', '3', 'app1', '381721']),
        # (0, ['13:38:34.127535', 'close', '3', 'app1', '381721'])
        self.assertEqual(
            [
                {'pid': '381721', 'proc': 'app1', 'exec_path': '/path/to/app1',
                 'events': [
                     {
                        'fname': '/path/foo/text2',
                        'open': '13:38:34.127529',
                        'close': '13:38:34.127535',
                        'mode': 3
                     }
                 ]
                 }
            ], lc.to_list()
        )

        lc.dump()
        self.assertEqual(
            [
                {'pid': '381721', 'proc': 'app1', 'exec_path': '/path/to/app1',
                 'events': [
                     {
                        'fname': '/path/foo/text2',
                        'open': '13:38:34.127529',
                        'close': '13:38:34.127535',
                        'mode': 3
                     }
                 ]
                 }
            ], list_writer.get_output()
        )

        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_rw(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.only_rw():
            lc.execute(record)

        # (0, ['13:38:34.127532', 'read', '2', 'app1', '381722']),
        # (0, ['13:38:34.127533', 'write', '2', 'app1', '381722']),
        self.assertEqual(
            [
                {'pid': '381722', 'proc': 'app1', 'exec_path': '/path/to/app1',
                 'events': [
                     {
                        'fname': LogCompactorV2.UNKOWN_FILE_NAME_VALUE,
                        'open': '',
                        'close': '',
                        'mode': 3
                     }
                 ]
                 }
            ], lc.to_list()
        )

        lc.dump()
        self.assertEqual(
            [
                {'pid': '381722', 'proc': 'app1', 'exec_path': '/path/to/app1',
                 'events': [
                     {
                        'fname': LogCompactorV2.UNKOWN_FILE_NAME_VALUE,
                        'open': '',
                        'close': '',
                        'mode': 3
                     }
                 ]
                 }
            ], list_writer.get_output()
        )

        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_neg_fd(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.neg_fd():
            lc.execute(record)

        #         (0, ['13:38:23.403654', 'open', '-1',
        #              '/path/foo/nosuccess', 'com.docker.cli', '381337'])
        self.assertEqual(
            [], lc.to_list()
        )
        self.assertEqual(
            [],
            list_writer.get_output()
        )

    def test_only_open(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.only_open():
            lc.execute(record)

        # (0, ['13:38:23.403654', 'open', '1',
        #      '/path/foo/nosuccess', 'com.docker.cli', '381337'])
        lc.dump()
        self.assertEqual(
            [
                {'pid': '381337', 'proc': 'com.docker.cli', 'exec_path': '/path/to/com.docker.cli',
                 'events': [
                     {
                        'fname': '/path/foo/nosuccess',
                        'open': '13:38:23.403654',
                        'close': '',
                        'mode': 0
                     }
                 ]
                 }
            ], list_writer.get_output()
        )

        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_only_close(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.close_without_open():
            lc.execute(record)

        #         (0, ['18:36:21.633351', 'close', '30', 'ampdaemon', '8310']),

        lc.dump()
        self.assertEqual(
            [
                {'pid': '8310', 'proc': 'ampdaemon', 'exec_path': '/path/to/ampdaemon',
                 'events': [
                     {
                        'fname': LogCompactorV2.UNKOWN_FILE_NAME_VALUE,
                        'open': '',
                        'close': '18:36:21.633351',
                        'mode': 0
                     }
                 ]
                 }
            ], list_writer.get_output()
        )

        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_multiple_closes(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.multiple_close():
            lc.execute(record)

        #         (0, ['18:36:21.633370', 'close', '32', 'ampdaemon', '8310']),
        #         (0, ['18:36:21.633370', 'close', '10', 'ampdaemon', '8310']),
        lc.dump()
        self.assertEqual(
            [
                {
                    'pid': '8310', 'proc': 'ampdaemon', 'exec_path': '/path/to/ampdaemon',
                    'events': [
                        {
                            'fname': LogCompactorV2.UNKOWN_FILE_NAME_VALUE,
                            'open': '',
                            'close': '18:36:21.633370',
                            'mode': 0
                        },
                        {
                            'fname': LogCompactorV2.UNKOWN_FILE_NAME_VALUE,
                            'open': '',
                            'close': '18:36:21.633370',
                            'mode': 0
                        }
                    ]
                },
            ], list_writer.get_output()
        )

        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_mkdir_rename_mmap(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.mkdir_rename_mmap():
            lc.execute(record)

        lc.dump()
        self.assertEqual(
            [
                #  (0, ['14:21:25.532390', 'mkdir', '1',
                #              '/path/foo/text4', 'ampscansvc', '8322']),
                {
                    'pid': '8322', 'proc': 'ampscansvc', 'exec_path': '/path/to/ampscansvc',
                    'events': [
                        {
                            'fname': '/path/foo/text4',
                            'open': '',
                            'close': '',
                            'mode': 8
                        }
                    ]
                },
                #         (0, ['14:21:25.585988', 'rename', '1',
                #              '/path/foo/text5', 'acumbrellaagent', '6707']),
                {
                    'pid': '6707', 'proc': 'acumbrellaagent', 'exec_path': '/path/to/acumbrellaagent',
                    'events': [
                        {
                            'fname': '/path/foo/text5',
                            'open': '',
                            'close': '',
                            'mode': 16
                        }
                    ]
                },
                #         (0, ['14:21:26.727314', 'mmap', '1', '<>', 'docker', '459788'])
                {
                    'pid': '459788', 'proc': 'docker', 'exec_path': '/path/to/docker',
                    'events': [
                        {
                            'fname': '<>',
                            'open': '',
                            'close': '',
                            'mode': 4
                        }
                    ]
                },
            ], list_writer.get_output()
        )

        self.assertEqual(
            [],
            lc.to_list()
        )

    def test_one_proc_multiple_files(self):
        list_writer = TestLogCompactorV2.MockWriter()
        lc = LogCompactorV2(
            writer=list_writer,
            extract_exec_path_func=TestLogCompactorV2.MockExecPath(
                '/path/to/{0}').get_exec_path
        )

        for record in TestLogCompactorV2.MockData.one_proce_multi_files():
            lc.execute(record)

# (0, ['13:38:34.127529', 'open', '1', '/path/foo/text1', 'app1', '381720']),
# (0, ['13:38:34.127535', 'close', '1', 'app1', '381720']),
# (0, ['13:38:34.127529', 'open', '1', '/path/foo/text1', 'app1', '381720']),
# (0, ['13:38:34.127529', 'open', '2', '/path/foo/text2', 'app1', '381720']),
# (0, ['13:38:34.127535', 'close', '2', 'app1', '381720']),
# (0, ['13:38:34.127535', 'close', '1', 'app1', '381720'])
        lc.dump()
        # NOTE: take a look at the order of the events; text2 is closed sooner so it appears earliner than the text1
        self.assertEqual(
            [
                {
                    'pid': '381720', 'proc': 'app1', 'exec_path': '/path/to/app1',
                    'events': [
# (0, ['13:38:34.127529', 'open', '1', '/path/foo/text1', 'app1', '381720']),
# (0, ['13:38:34.127535', 'close', '1', 'app1', '381720']),
                        {
                            'fname': '/path/foo/text1',
                            'open': '13:38:34.127529',
                            'close': '13:38:34.127535',
                            'mode': 0
                        },
# (0, ['13:38:34.127529', 'open', '2', '/path/foo/text2', 'app1', '381720']),
# (0, ['13:38:34.127535', 'close', '2', 'app1', '381720']),
                        {
                            'fname': '/path/foo/text2',
                            'open': '13:38:34.127529',
                            'close': '13:38:34.127535',
                            'mode': 0
                        },
# (0, ['13:38:34.127529', 'open', '1', '/path/foo/text1', 'app1', '381720']),
# (0, ['13:38:34.127535', 'close', '1', 'app1', '381720'])
                        {
                            'fname': '/path/foo/text1',
                            'open': '13:38:34.127529',
                            'close': '13:38:34.127535',
                            'mode': 0
                        }
                    ]
                },
            ], list_writer.get_output()
        )

        self.assertEqual(
            [],
            lc.to_list()
        )

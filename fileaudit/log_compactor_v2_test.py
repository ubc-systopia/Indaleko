from log_compactor_v2 import FileEvent, LogRecordV2
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

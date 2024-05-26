from log_compactor_v2 import FileEvent
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

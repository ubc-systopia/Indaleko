import typing
from datetime import datetime

from fileaudit.abstract import IWriter


class CompactRecord:
    date_ts_sep = '_'
    event_name_datets_sep = '|'

    def __init__(self) -> None:
        self.proc_name = ''
        self.pid = ''
        self.path = ''
        self.events = []

    def add_procname(self, procname: str) -> 'CompactRecord':
        assert isinstance(procname, str), f'proname is not string; got {
            type(procname)}'

        self.proc_name = procname
        return self

    def add_pid(self, pid: str) -> 'CompactRecord':
        assert isinstance(pid, str), f'pid is not a string; got {type(pid)}'

        self.pid = pid
        return self

    def add_path(self, path: str) -> 'CompactRecord':
        assert isinstance(path, str), f'path is not a string; got {type(path)}'

        self.path = path
        return self

    def add_event(self, event_name: str, event_date: str, event_ts: str) -> 'CompactRecord':
        assert isinstance(event_name, str), f'event_name is not a string; got {
            type(event_name)}'
        assert isinstance(event_ts, str), f'event_ts is not a string; got{
            type(event_ts)}'
        assert isinstance(event_date, str), f'event_date is not a string; got{
            type(event_date)}'

        self.events.append(CompactRecord.event_name_datets_sep.join(
            [event_name, CompactRecord.date_ts_sep.join([event_date, event_ts])]))

        return self

    def to_list(self) -> typing.List:
        return [self.pid, self.proc_name, self.path, self.events]


class LogCompactor:
    def __init__(self, writer: 'IWriter', datefunc=None) -> None:
        # procname-pid: <path>; events=[open|date:ts1, ...., close|date:tsn]
        # expects = [['381720', 'app1', '/path/foo/text1',
        # ['open|today_13:38:34.127535', 'close|today_13:38:34.127529']]]

        # key: (procname-pid, fd) -> compact record
        self.state: typing.Dict[typing.Tuple[str, str], CompactRecord] = {}

        self.datefunc = lambda: datetime.now().date() if not datefunc else datefunc()
        self.writer = writer

    def get_state_key(self, record):
        return ('-'.join(record[-2:]), record[2])

    def add(self, input_tuple: tuple[int, typing.List]) -> None:
        """
        input: record has a (0, arr) format
        """
        # return [
        #     (0, ['13:38:34.127529', 'open', '1', '/path/foo/text1', 'app1', '381720']),
        #     (0, ['13:38:34.127535', 'close', '1', 'app1', '381720'])
        # ]

        status, record = input_tuple
        if status == 1:
            # the record is invalid
            return

        match record[1]:
            case 'open':
                cr = CompactRecord()

                cr.add_event(event_date=self.datefunc(),
                             event_name='open',
                             event_ts=record[0])
                cr.add_pid(record[-1])
                cr.add_procname(record[-2])
                cr.add_path(record[-3])

                key = self.get_state_key(record)

                self.state[key] = cr
            case 'close':
                key = self.get_state_key(record)

                self.state[key].add_event(
                    event_name='close',
                    event_date=self.datefunc(),
                    event_ts=record[0]
                )

                self.writer.write(self.state[key].to_list())

                # delete the key as we wrote it to the writer
                del self.state[key]
            case _:
                raise Exception(f"not implemented; record={record}")

    def get_state(self):
        return

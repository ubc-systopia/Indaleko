import collections

from datetime import datetime

from abstract import IOperator, IWriter


class CompactRecord:
    date_ts_sep = "_"  # Separator for date and timestamp
    event_name_datets_sep = "|"  # Separator for event name, date, and timestamp

    def __init__(self) -> None:
        """Initialize CompactRecord object with empty attributes."""
        self.proc_name = ""  # Process name
        self.pid = ""  # Process ID
        self.path = ""  # File path
        self.events = []  # List to store events

    def add_procname(self, procname: str) -> "CompactRecord":
        """Add process name to CompactRecord."""
        assert isinstance(
            procname, str,
        ), f"procname is not string; got {
            type(procname)}"
        if self.proc_name == "":
            self.proc_name = procname
        return self

    def add_pid(self, pid: str) -> "CompactRecord":
        """Add process ID to CompactRecord."""
        assert isinstance(pid, str), f"pid is not a string; got {type(pid)}"
        if self.pid == "":
            self.pid = pid
        return self

    def add_path(self, path: str) -> "CompactRecord":
        """Add file path to CompactRecord."""
        assert isinstance(path, str), f"path is not a string; got {type(path)}"
        if self.path == "":
            self.path = path
        return self

    def add_event(
        self,
        event_name: str,
        event_date: str,
        event_ts: str,
        procname: str | None = None,
        pid: str | None = None,
        path: str | None = None,
    ) -> "CompactRecord":
        """Add an event to CompactRecord. Optionally update process name, PID, or file path."""
        assert isinstance(
            event_name, str,
        ), f"event_name is not a string; got {
            type(event_name)}"
        assert isinstance(
            event_ts, str,
        ), f"event_ts is not a string; got {
            type(event_ts)}"
        assert isinstance(
            event_date, str,
        ), f"event_date is not a string; got {
            type(event_date)}"
        assert procname is None or isinstance(
            procname, str,
        ), f"procname has to be None or of type str; got {type(procname)}"
        assert pid is None or isinstance(
            pid, str,
        ), f"pid has to be None or of type str; got {type(pid)}"
        assert path is None or isinstance(
            path, str,
        ), f"path has to be None or of type str; got {type(path)}"

        if procname is not None:
            # Update process name if provided
            self.add_procname(procname)
        if pid is not None:
            # Update PID if provided
            self.add_pid(pid)
        if path is not None:
            # Update file path if provided
            self.add_path(path)

        # Combine event name, date, and timestamp with appropriate separators and add to events list
        self.events.append(
            CompactRecord.event_name_datets_sep.join(
                [event_name, CompactRecord.date_ts_sep.join([event_date, event_ts])],
            ),
        )
        return self

    def to_list(self) -> list:
        """Convert CompactRecord attributes to a list."""
        return [self.pid, self.proc_name, self.path, self.events]


class LogCompactor(IOperator):
    def __init__(self, writer: "IWriter", datefunc=None) -> None:
        """Initialize LogCompactor with a writer and an optional date function."""
        # procname-pid: <path>; events=[open|date:ts1, ...., close|date:tsn]
        # expects = [['381720', 'app1', '/path/foo/text1',
        # ['open|today_13:38:34.127535', 'close|today_13:38:34.127529']]]

        # key: (procname-pid, fd) -> compact record
        self.state: dict[tuple[str, str], CompactRecord] = (
            collections.defaultdict(lambda: CompactRecord())
        )

        self.datefunc = lambda: (
            datetime.now().date().strftime("%Y-%m-%d") if not datefunc else datefunc()
        )
        self.writer = writer

    def get_state_key(self, record):
        """
        Returns (procname-pid, fd) created based on the given record.

        procname: record[-2]-record[-1]
        fd: record[2]
        """
        return ("-".join(record[-2:]), record[2])

    def execute(self, input_tuple: tuple[int, list]) -> None:
        """
        Execute the LogCompactor operation based on the input record.

        Input format: (status, record_list)
        """
        status, record = input_tuple
        if status == 1 or record[2].strip() == "-1":
            # the record is invalid
            return

        key = self.get_state_key(record)

        match record[1]:
            case "open":
                cr = CompactRecord()

                cr.add_event(
                    event_date=self.datefunc(), event_name="open", event_ts=record[0],
                )
                cr.add_pid(record[-1])
                cr.add_procname(record[-2])
                cr.add_path(record[-3])

                self.state[key] = cr
            case "close":
                # (0, ['18:36:21.633351', 'close', '30', 'ampdaemon', '8310']),
                self.state[key].add_event(
                    event_name="close",
                    event_date=self.datefunc(),
                    event_ts=record[0],
                    pid=record[-1],
                    procname=record[-2],
                )

                self.writer.write(self.state[key].to_list())

                # delete the key as we wrote it to the writer
                del self.state[key]
            case "read" | "write" as op:
                #     (0, ['13:38:34.127532', 'read', '3', 'app1', '381721']),
                #     (0, ['13:38:34.127533', 'write', '3', 'app1', '381721']),
                self.state[key].add_event(
                    event_name=op,
                    event_date=self.datefunc(),
                    event_ts=record[0],
                    procname=record[-2],
                    pid=record[-1],
                )

            case "mkdir" | "rename" | "mmap" as op:
                # (0, ['14:21:25.532390', 'mkdir', '1', '/path/foo/text4', 'ampscansvc', '8322']),
                # (0, ['14:21:25.585988', 'rename', '1', '/path/foo/text5', 'acumbrellaagent', '6707']),
                # (0, ['14:21:26.727314', 'mmap', '1', '<>', 'docker', '459788'])
                self.state[key].add_event(
                    event_name=op,
                    event_date=self.datefunc(),
                    event_ts=record[0],
                    procname=record[-2],
                    pid=record[-1],
                    path=record[3],
                )
            case _:
                raise Exception(f"not implemented; record={record}")

    def get_state(self):
        """Get the current state of LogCompactor."""
        state = []
        for key in self.state:
            state.append(self.state[key].to_list())
        return state

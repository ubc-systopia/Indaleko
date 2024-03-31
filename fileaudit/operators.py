import re
import subprocess
import typing
from abstract import IOperator, IReader


class InputReader(IReader):
    """
    InputReader returns a generator where it returns a tuple of the form (status, line). If `status` is 0, it means the read was successful, and `line` is the stdout line. If `status` is 1, the `line` contains the error message.

    Args:
        cmd (list): A list containing the command to execute and its arguments.

    Attributes:
        cmd (list): The command to execute and its arguments.

    Methods:
        run(): Executes the command and yields the output line by line along with its status.

    Example:
        Usage example:
        ```
        reader = InputReader(["ls", "/bin"])
        for status, line in reader.run():
            if status == 0:
                print(f"Success: {line}")
            else:
                print(f"Error: {line}")
        ```

    """

    def __init__(self, cmd: typing.List[str]):
        """
        Initialize InputReader with the provided command.

        Args:
            cmd (list): A list containing the command to execute and its arguments.

        Raises:
            AssertionError: If cmd is empty.

        """
        assert len(cmd) != 0, f'cmd is empty; cmd="{cmd}"'
        self.cmd = cmd

    def run(self):
        """
        Execute the command and yield its output line by line along with its status.

        Yields:
            tuple: A tuple containing status (0 for success, 1 for error) and line from the output.

        """
        try:
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,  # Line-buffered output
            )

            for line in process.stdout:
                yield (0, line.strip())

            _, stderr = process.communicate()  # Wait for the process to finish

            if process.returncode != 0:
                yield (1, f"Command exited with non-zero code: {process.returncode}; stderr: {stderr}")
        except Exception as e:
            yield (1, f"Error: {str(e)}")


class ToList(IOperator):
    """
    ToList class converts a tuple into a list based on provided parameters.

    Args:
        input_tuple (tuple): A tuple containing status information and input string.
        sep (str, optional): Separator to split the input string. Defaults to ' '.
        remove_empty_fields (bool, optional): Flag to remove empty fields after splitting. Defaults to False.

    Attributes:
        status (int): Status code from input_tuple.
        input_str (str): Input string from input_tuple.
        sep (str): Separator for splitting input_str.
        remove_empty_fields (bool): Flag to indicate whether to remove empty fields or not.

    Methods:
        execute(): Execute the conversion process based on provided parameters.

    """

    def __init__(self, sep=' ', remove_empty_fields=False):
        """
        Initialize ToList with the provided parameters.

        Args:
            sep (str, optional): Separator to split the input string. Defaults to ' '.
            remove_empty_fields (bool, optional): Flag to remove empty fields after splitting. Defaults to False.

        Raises:
            AssertionError: If sep is an empty string or if input_tuple is not a tuple.

        """
        assert len(sep) > 0, 'sep cannot be empty; got empty sep'

        self.sep = sep
        self.remove_empty_fields = remove_empty_fields

    def execute(self, input_tuple):
        """
        Execute the conversion process based on provided parameters.

        Args:
            input_tuple (tuple): A tuple containing status information and input string.
        Returns:
            tuple: A tuple containing status code and resulting list after conversion.

        """
        assert isinstance(input_tuple, tuple), f'input is not a tuple; got {
            input_tuple}, type of {input_tuple}'
        self.status, self.input_str = input_tuple

        if self.status == 0:
            fields = [f for f in self.input_str.split(self.sep) if (
                self.remove_empty_fields and len(f) > 0) or not self.remove_empty_fields]
            return (0, fields)
        return (1, [])


class FilterField(IOperator):
    """
    FilterField class filters a list based on a specified position and value.

    Args:
        input_tuple (tuple[int, List[str]]): A tuple containing status information and input list.
        filter_args (tuple[int, str]): A tuple specifying the position and value to filter.

    Attributes:
        status (int): Status code from input_tuple.
        input_list (List[str]): Input list from input_tuple.
        position (int): Position in the input list to apply the filter.
        contains_value (str): Value to filter for in the specified position.

    Methods:
        execute(): Execute the filtering process based on provided parameters.

    Example:
        Usage example:
        ```
        input_tuple = (0, ["apple", "banana", "cherry"])
        filter_args = (1, "banana")
        filter_op = FilterField(input_tuple, filter_args)
        status, filtered_list = filter_op.execute()
        if status == 0:
            print("Filtered list:", filtered_list)
        else:
            print("No match found.")
        ```

    """

    def __init__(self, filter_args: tuple[int, str]):
        """
        Initialize FilterField with the provided parameters.

        Args:
            filter_args (tuple[int, str]): A tuple specifying the position and value to filter.

        """
        self.position, self.contains_value = filter_args

    def execute(self, input_tuple: tuple[int, typing.List[str]]):
        """
        Execute the filtering process based on provided parameters.

        Args:
            input_tuple (tuple[int, List[str]]): A tuple containing status information and input list.
        Returns:
            tuple: A tuple containing status code and filtered list after applying the filter.

        """

        self.status, self.input_list = input_tuple
        if self.status == 0 and len(self.input_list) > self.position and len(self.input_list) != 0:
            if self.contains_value in self.input_list[self.position]:
                return (0, self.input_list)
            return (1, self.input_list)

        return (1, self.input_list)


class FilterFields(IOperator):
    """
    FilterFields class filters a list based on a specified position and value.

    Args:
        pos (int): Position in the input list to apply the filter.
        queries (list): List of values to filter for in the specified position.

    Attributes:
        pos (int): Position in the input list to apply the filter.
        queries (list): List of values to filter for in the specified position.

    Methods:
        execute(): Execute the filtering process based on provided parameters.
    """

    def __init__(self, pos: int, queries: typing.List[str], exact_match=None):
        """
        Initialize FilterFields with the provided parameters.

        Args:
            pos (int): Position in the input list to apply the filter.
            queries (list): List of values to filter for in the specified position.

        """
        self.pos = pos
        self.queries = queries
        self.exact_match = exact_match

    def execute(self, input_tuple: tuple[int, typing.List[str]]) -> tuple[int, typing.List[str]]:
        """
        Execute the filtering process based on provided parameters.

        Args:
            input_tuple (tuple): A tuple containing status information and input list.

        Returns:
            tuple: A tuple containing status code and filtered list after applying the filter.

        """
        status, input_list = input_tuple
        exact_match = self.exact_match
        if status == 0 and len(input_list) > self.pos:
            for q in self.queries:
                if (exact_match and q.strip() == input_list[self.pos].strip()) or (not exact_match and q in input_list[self.pos]):
                    return (0, input_list)
            return (1, input_list)
        else:
            return (1, input_list)


class Canonize:
    def __init__(self):
        pass

    def clean(self, word: str):
        return word.strip('[').strip(']')

    def extract_fid(self, word: str):
        return word.strip().split('=')[1].split('[')[0]

    def extract_path_pid_procname(self, arr: typing.List[str]):
        # open:
        #   ['/Users/sinaee/Library/Application', 'Support/Code/logs/20240329T155455/window1/exthost/GitHub.vscode-pull-request-github/GitHub', 'Pull', 'Request.log', '0.000115', 'ampdaemon.8244']
        # close:
        # ['Finder.464225']
        # ['Code', 'Helper.21316']
        pattern = r"\d+\.\d+"
        found, res = -1, []
        for i in range(len(arr)-1, -1, -1):
            if re.fullmatch(pattern, arr[i]):
                found = i
                break

        if found != -1:
            *procname, pid = ' '.join(arr[found+1:]).rsplit('.', 1)
            return (' '.join(arr[:found]) if len(arr[:found]) else None, ' '.join(procname), pid)

        return None

    def execute(self, input_arr) -> tuple[int, typing.List]:
        ret = []
        status, arr = input_arr
        if status == 0:
            time, action, *details = arr
            ret.extend([self.clean(s) for s in [time, action]])

            match action:
                case 'open':
                    ret.append(self.extract_fid(details[0]))
                    if (res := self.extract_path_pid_procname(details[2:])) and res:
                        path, procname, pid = res
                        ret.extend([path, procname, pid])
                    else:
                        print(f'warn: no pid, procname in  given_input={input_arr}')
                case 'close':
                    ret.append(self.extract_fid(details[0]))
                    if (res := self.extract_path_pid_procname(details[1:])) and res:
                        path, procname, pid = res
                        ret.extend([procname, pid])
                    else:
                        print(f'warn: no pid, procname in  given_input={input_arr}')
            return (0, ret)

        return (1, [])


class Show(IOperator):
    def __init__(self, show_func=print) -> None:
        self.func = show_func

    def execute(self, input):
        return self.func(input)

import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Counter:
    icon: str
    icon_space: int
    type: str
    count: int


class PreCommit:
    def __init__(self, pre_commit_file__path: str, ignore_files: list[Path | str] | None = None) -> None:
        self.pre_commit_file__path = pre_commit_file__path
        self.locked: bool = False
        self.ignore_files: list[Path | str] = ignore_files or []
        self.files_from_git = self.get_staged_files_from_git()
        self.files: dict[str, list[str]] = self.get_files_with_lines()
        self.messages: dict[str, dict[str, list[str]]] = {}
        self.callback_aborted: Callable | None = None
        self.callback_conditionally: Callable | None = None
        self.callback_clean: Callable | None = None
        self.prevent: bool = False
        self.counters: dict[str, Counter] = {}
        self.init_event(pre_commit_file__path)

    def init_event(self, pre_commit_file__path: str) -> None:
        if pre_commit_file__path.endswith(".git/hooks/pre-commit"):
            self.on_call_as_git_hook()
        else:
            self.on_call_as_script()

    def __getattribute__(self, name: str) -> Callable:
        attr = object.__getattribute__(self, name)
        if callable(attr) and not name.startswith("_"):

            def wrapper(*args, **kwargs) -> object | None:
                if object.__getattribute__(self, "locked"):
                    return None
                return attr(*args, **kwargs)

            return wrapper
        return attr

    def on_call_as_git_hook(self) -> None:
        pass

    def on_call_as_script(self) -> None:
        git_cmd = "git rev-parse --git-path hooks/pre-commit"
        pre_commit_path = subprocess.check_output(git_cmd, shell=True).decode().strip()
        path = Path().cwd() / pre_commit_path
        create_symbolic_link_cmd = f"ln -s {self.pre_commit_file__path} {path}"
        msg = (
            "To use this Git hook you must either create a symbolic link for"
            " this file or copy it's content to the Git pre-commit hook file.\n"
            "Do you want to execute the following command to create the symbolic link?\n"
            f"  {create_symbolic_link_cmd}\n"
            "Please type 'CREATE_SYMBOLIC_LINK' to execute this command (mind underscores): "
        )
        sys.stderr.write(msg)
        ans = input()
        if ans.strip() == "CREATE_SYMBOLIC_LINK":
            try:
                subprocess.check_output(create_symbolic_link_cmd, shell=True).decode().strip()
                path = Path(self.pre_commit_file__path)
                path.chmod(path.stat().st_mode | 64)
            except Exception:
                sys.stderr.write("Failure, couldn't create the symbolic link\n")
            else:
                sys.stderr.write("Success, the symbolic link was created\n")
        self.locked = True

    def get_files_with_lines(self, files: list[str] | None = None) -> dict[str, list[str]]:
        if files is None:
            files = self.files_from_git
        files_with_lines: dict[str, list[str]] = {}
        for filename in files:
            with open(filename) as f:
                files_with_lines[filename] = f.readlines()
        return files_with_lines

    def get_staged_files_from_git(self) -> list[str]:
        command = ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"]
        return subprocess.check_output(command).decode().split()

    def add_ignored_file(self, path: Path | str | None = None) -> None:
        if path is None:
            return
        self.ignore_files.append(path)

    def add_ignored_files(self, paths: list[Path | str] | None = None) -> None:
        if paths is None:
            return
        self.ignore_files.extend(paths)

    def check_content_for(self, substring: str, type: str, icon: str, icon_space: int = 1, prevent: bool = True) -> int:
        count = 0
        if self.messages.get(type) is None:
            self.messages[type] = {}
            self.counters[type] = Counter(icon, icon_space, type, count)
        for filename, lines in self.files.items():
            if self.ignore_files and filename in self.ignore_files:
                continue
            for num, line in enumerate(lines):
                if substring in line:
                    if self.messages[type].get(filename) is None:
                        self.messages[type][filename] = []
                    count += 1
                    msg = f"{icon}{' ' * icon_space}{substring} found in {filename}:{num + 1}"
                    if prevent:
                        self.prevent = True
                        msg = f"{msg} 🔒"
                    self.messages[type][filename].append(msg)
                    self.counters[type].count += 1
        return count

    def check_command(self, command: str, prevent: bool = True) -> int:
        buffer: str = ""
        buffer = f"❯ {command}"
        cmd, _, _ = command.partition(" ")
        if shutil.which(cmd) is None:
            buffer = f"{buffer}(command '{cmd}' not found!)"
            if prevent:
                self.prevent = True
                buffer = f"{buffer} 🔒"
            result = 255
        else:
            result = subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode:
                buffer = f"{buffer} (ERROR)"
                if prevent:
                    self.prevent = True
                    buffer = f"{buffer} 🔒"
            else:
                buffer = f"{buffer} (OK)"
        self.messages[command] = {command: [buffer]}
        return result

    def print_results(self, type: str | None = None) -> None:
        if type is None:
            for key in self.messages:
                self._print_results_for(key)
        else:
            self._print_results_for(type)

    def _print_results_for(self, type: str | None = None) -> None:
        for messages in self.messages.get(type, {}).values():
            for message in messages:
                sys.stderr.write(f"{message}\n")

    def print_summary(self) -> None:
        sys.stderr.write("Summary: ")
        for key in self.messages:
            c: Counter = self.counters.get(key)
            if c is None:
                continue
            sys.stderr.write(f"{c.icon}{' ' * c.icon_space}{c.count} ({c.type}) ")
        sys.stderr.write("\n")

    @property
    def rc(self) -> int:
        if self.prevent:
            self.callback_aborted()
            return 1
        if sum([c.count for c in self.counters.values()]):
            self.callback_conditionally()
            return 0
        self.callback_clean()
        return 0

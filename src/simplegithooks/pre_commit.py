import contextlib
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .colors import (
    bg_green,
    bg_red,
    bg_yellow,
    blink,
    fg_cyan,
    fg_green,
    fg_magenta,
    fg_red,
    fg_white,
    fg_yellow,
    reset,
)

CALLBACKS: dict[str, Callable[[], Any]] = {
    "locker": lambda: f"{blink} 🔒{reset}",
    "aborted": lambda: f"🔴 {blink}{fg_white}{bg_red}Commit aborted.{reset}",
    "conditionally": lambda: f"🟡 {fg_white}{bg_yellow}Commit allowed conditionally.{reset}",
    "clean": lambda: f"🟢 {fg_white}{bg_green}Commit allowed.{reset}",
}


@dataclass
class Counter:
    icon: str
    icon_space: int
    count: int
    preventing: bool


@dataclass
class Result:
    icon: str
    icon_space: int
    category: str
    msg: str
    preventing: bool


class PreCommit:
    def __init__(  # noqa: PLR0913
        self,
        pre_commit_file_path: str,
        ignore_files: list[Path | str] | None = None,
        callback_locker: Callable[[], Any] = CALLBACKS["locker"],
        callback_aborted: Callable[[], Any] = CALLBACKS["aborted"],
        callback_conditionally: Callable[[], Any] = CALLBACKS["conditionally"],
        callback_clean: Callable[[], Any] = CALLBACKS["clean"],
    ) -> None:
        self.pre_commit_file_path = Path(pre_commit_file_path)
        self.ignore_files: list[Path | str] = ignore_files or []
        self.callback_locker = callback_locker
        self.lockdown: bool = False
        self.files_from_git = self.get_staged_files_from_git()
        self.files: dict[str, list[str]] = self.get_files_with_lines()
        self._counters: dict[str, Counter] = {}
        self._results: list[Result] = []
        self.callback_aborted: Callable[[], Any] = callback_aborted
        self.callback_conditionally: Callable[[], Any] = callback_conditionally
        self.callback_clean: Callable[[], Any] = callback_clean
        self.prevent: bool = False
        self.init_event(pre_commit_file_path)

    @staticmethod
    def get_pre_commit_path_absolute() -> Path:
        git_cmd = ["git", "rev-parse", "--git-path", "hooks/pre-commit"]
        pre_commit_path_relative = subprocess.check_output(git_cmd).decode().strip()  # noqa: S603
        return Path().cwd() / pre_commit_path_relative

    @classmethod
    def install_git_hook(cls, path_from: Path | str) -> None:
        pre_commit_path_absolute = PreCommit.get_pre_commit_path_absolute()
        if pre_commit_path_absolute.exists() or pre_commit_path_absolute.is_symlink():
            cls.create_symbolic_link(
                path_from,
                str(pre_commit_path_absolute),
                force=True,
            )
        else:
            cls.create_symbolic_link(path_from, str(pre_commit_path_absolute))
        cls.lockdown = True

    @classmethod
    def create_symbolic_link(
        cls,
        path_from: Path | str,
        path_to: str,
        force: bool = False,  # noqa: FBT001, FBT002
    ):
        _path_from = Path(path_from)
        _f = " -f" if force else ""
        create_symbolic_link_cmd = f"ln{_f} -s {path_from} {path_to}"
        warning = f"WARNING: file '{path_to}' already exists and will be overwritten.\n"
        msg = (
            "To use this Git hook you must either create a symbolic link for"
            " this file or copy it's content to the Git pre-commit hook file.\n"
            f"{fg_yellow}{warning if force else ''}{reset}"
            "Do you want to execute the following command to create the symbolic link?\n"
            f"  {fg_magenta}{create_symbolic_link_cmd}{reset}\n"
            f"Please type '{fg_cyan}CREATE_SYMBOLIC_LINK{reset}' to execute this command (mind underscores): "
        )
        sys.stderr.write(msg)
        try:
            ans = input()
        except KeyboardInterrupt:
            sys.stderr.write(f"{fg_yellow}Detected ^C, exiting...{reset}")
            return
        if ans.strip() == "CREATE_SYMBOLIC_LINK":
            try:
                subprocess.check_output(  # noqa: S602
                    create_symbolic_link_cmd,
                    shell=True,
                ).decode().strip()
                _path_from.chmod(_path_from.stat().st_mode | 64)
            except:  # noqa: E722
                msg = f"{fg_red}Failure, couldn't create the symbolic link.{reset}\n"
                sys.stderr.write(msg)
            else:
                msg = f"{fg_green}Success, the symbolic link was created.{reset}\n"
                sys.stderr.write(msg)
        else:
            msg = f"You've not provided '{fg_cyan}CREATE_SYMBOLIC_LINK{reset}', exiting...\n"
            sys.stderr.write(msg)

    @classmethod
    def run_default_git_hook(cls) -> None:
        pre_commit_path_absolute = PreCommit.get_pre_commit_path_absolute()
        subprocess.run(pre_commit_path_absolute, check=False)  # noqa: S603

    def __getattribute__(self, name: str):
        attr = object.__getattribute__(self, name)
        if callable(attr) and not name.startswith("_"):

            def wrapper(*args, **kwargs):
                if object.__getattribute__(self, "lockdown"):
                    return None
                return attr(*args, **kwargs)

            return wrapper
        return attr

    def init_event(self, pre_commit_file__path: str) -> None:
        if pre_commit_file__path.endswith(".git/hooks/pre-commit"):
            self.on_call_as_git_hook()
        else:
            self.on_call_as_script()

    def on_call_as_git_hook(self) -> None:
        pass

    def on_call_as_script(self) -> None:
        pass

    def get_files_with_lines(
        self,
        files: list[str] | None = None,
    ) -> dict[str, list[str]]:
        if files is None:
            files = self.files_from_git
        files_with_lines: dict[str, list[str]] = {}
        for filename in files:
            with contextlib.suppress(Exception), Path(filename).open() as f:
                files_with_lines[filename] = f.readlines()
        return files_with_lines

    def get_staged_files_from_git(self) -> list[str]:
        command = ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"]
        return subprocess.check_output(command).decode().split()  # noqa: S603

    def add_ignored_file(self, path: Path | str | None = None) -> None:
        if path is None:
            return
        self.ignore_files.append(path)

    def add_ignored_files(self, paths: list[Path | str] | None = None) -> None:
        if paths is None:
            return
        self.ignore_files.extend(paths)

    def check_content_for(
        self,
        substring: str,
        icon: str,
        category: str,
        icon_space: int = 1,
        prevent: bool = True,  # noqa: FBT001, FBT002
    ) -> int:
        count = 0
        for filename, lines in self.files.items():
            if filename in self.ignore_files or any(
                Path(filename).match(str(p)) for p in self.ignore_files
            ):
                continue
            for n, line in enumerate(lines, start=1):
                _prevent = False
                if substring in line:
                    count += 1
                    if prevent:
                        self.prevent = True
                        _prevent = True
                        msg = f"{fg_red}'{substring}' found in {filename}:{n}{reset}"
                        msg = f"{msg}{self.callback_locker()}"
                    else:
                        msg = f"{fg_yellow}'{substring}' found in {filename}:{n}{reset}"
                    result = Result(icon, icon_space, category, msg, _prevent)
                    if self._counters.get(category):
                        self._counters[category].count += 1
                    else:
                        self._counters[category] = Counter(
                            icon,
                            icon_space,
                            1,
                            _prevent,
                        )
                    self._results.append(result)
        return count

    def check_command(
        self,
        command: str,
        prevent: bool = True,  # noqa: FBT001, FBT002
        rc_zero_succes: bool = True,  # noqa: FBT001, FBT002
        icon: str = "❯",  # noqa: RUF001
    ) -> int:
        _prevent = False
        buffer: str = ""
        buffer = f"{command}"
        cmd, _, _ = command.partition(" ")
        if shutil.which(cmd) is None:
            buffer = f"{fg_white}{bg_red}{buffer} (command '{cmd}' not found!){reset}"
            if prevent:
                self.prevent = True
                _prevent = True
                buffer = f"{buffer}{self.callback_locker()}"
            rc = 255
        else:
            execution = subprocess.run(  # noqa: PLW1510, S602
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=Path(),
            )
            non_zero = ", RC!=0 SUCCESS" if not rc_zero_succes else ""
            rc = execution.returncode
            success = rc == 0 if rc_zero_succes else rc != 0
            if success:
                buffer = f"{fg_green}{buffer} (OK{non_zero}){reset}"
            else:
                buffer = f"{fg_red}{buffer} (ERROR{non_zero}){reset}"
                if prevent:
                    self.prevent = True
                    _prevent = True
                    buffer = f"{buffer}{self.callback_locker()}"
        result = Result(icon, 1, cmd, buffer, _prevent)
        self._counters[cmd] = Counter(icon, 1, 0, _prevent)
        self._results.append(result)
        return rc

    def results(
        self,
        category: str | None = None,
        indent: int = 2,
        preventing_only: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        result: str = "Results:\n"
        if category is None:
            for key in self._counters:
                result = f"{result}{self._results_for(key, indent, preventing_only)}"
        else:
            result = f"{result}{self._results_for(category, indent, preventing_only)}"
        return result

    def _results_for(
        self,
        category: str | None = None,
        indent: int = 2,
        preventing_only: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        result: str = ""
        for r in self._results:
            if r.category != category:
                continue
            if preventing_only and not r.preventing:
                continue
            msg = f"{' ' * indent}{r.icon}{' ' * r.icon_space}{r.msg}\n"
            result = f"{result}{msg}"
        return result

    def summary(self, indent: int = 2) -> str:
        empty = True
        result: str = "Summary:\n"
        for category, counter in self._counters.items():
            if not counter.preventing:
                continue
            if counter.count:
                msg = f"{' ' * indent}{counter.icon}{' ' * counter.icon_space}{counter.count} ({category})\n"
            else:
                msg = f"{' ' * indent}{counter.icon}{' ' * counter.icon_space}{category}\n"
            result = f"{result}{msg}"
            empty = False
        if empty:
            result = f"{result}{' ' * indent}(nothing prevents from committing)\n"
        return result

    @property
    def rc(self) -> int:
        if self.prevent:
            sys.stderr.write(f"{self.callback_aborted()}\n")
            return 1
        counts = [c.count for c in self._counters.values()]
        if sum(counts):
            sys.stderr.write(f"{self.callback_conditionally()}\n")
            return 0
        sys.stderr.write(f"{self.callback_clean()}\n")
        return 0

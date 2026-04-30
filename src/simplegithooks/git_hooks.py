import contextlib
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

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
    is_cli,
    reset,
)


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


@dataclass
class PreCommitConfig:
    command: list[str] = field(
        default_factory=lambda: [
            "git",
            "diff",
            "--cached",
            "--name-only",
        ],
    )
    callbacks: dict[str, Callable[[], Any]] = field(
        default_factory=lambda: {
            "locker": lambda: None,
            "aborted": lambda: None,
            "caution": lambda: None,
            "clean": lambda: None,
            "as_git_hook": lambda: None,
            "as_script": lambda: None,
        },
    )
    outputs: dict[str, str] = field(
        default_factory=lambda: {
            "locker": f"{blink} 🔒{reset}",
            "aborted": f"🔴 {blink}{fg_white}{bg_red}Commit aborted.{reset}\n",
            "caution": f"🟡 {fg_white}{bg_yellow}Commit allowed (caution).{reset}\n",
            "clean": f"🟢 {fg_white}{bg_green}Commit clean.{reset}\n",
        },
    )


@dataclass
class PrePushConfig:
    command: list[str] = field(
        default_factory=lambda: [
            "git",
            "diff",
            "--name-only",
            "origin/HEAD..HEAD",
        ],
    )
    callbacks: dict[str, Callable[[], Any]] = field(
        default_factory=lambda: {
            "locker": lambda: None,
            "aborted": lambda: None,
            "caution": lambda: None,
            "clean": lambda: None,
            "as_git_hook": lambda: None,
            "as_script": lambda: None,
        },
    )
    outputs: dict[str, str] = field(
        default_factory=lambda: {
            "locker": f"{blink} 🔒{reset}",
            "aborted": f"🔴 {blink}{fg_white}{bg_red}Push aborted.{reset}\n",
            "caution": f"🟡 {fg_white}{bg_yellow}Push allowed (caution).{reset}\n",
            "clean": f"🟢 {fg_white}{bg_green}Push clean.{reset}\n",
        },
    )


class HookConfig(Protocol):
    command: list[str]
    callbacks: dict[str, Callable[[], Any]]
    outputs: dict[str, str]


class GitHook:
    def __init__(
        self,
        hook_file_path: str,
        hook_config: HookConfig,
        ignore_files: list[Path | str] | None = None,
    ) -> None:
        self.hook_file_path = Path(hook_file_path)
        self.hook_config = hook_config
        self.ignore_files: list[Path | str] = ignore_files or []
        self.locker = self.hook_config.outputs.get("locker", "")
        self.lockdown: bool = False
        self.files_from_git = self.get_files_from_command()
        self.files: dict[str, list[str]] = self.get_files_with_lines()
        self._counters: dict[str, Counter] = {}
        self._results: list[Result] = []
        self.caution: bool = False
        self.prevent: bool = False
        self._buffer: str = ""
        self.init_event(hook_file_path)

    @staticmethod
    def hook_path_absolute(hook_name: str) -> Path:
        git_cmd = ["git", "rev-parse", "--git-path", f"hooks/{hook_name}"]
        hook_path_relative = subprocess.check_output(git_cmd).decode().strip()  # noqa: S603
        return Path().cwd() / hook_path_relative

    @classmethod
    def run_default_git_hook(cls, hook_name: str) -> None:
        hook_path_absolute = GitHook.hook_path_absolute(hook_name)
        if not hook_path_absolute.exists():
            msg = f"{fg_yellow}Hook '{fg_magenta}{hook_name}{fg_yellow}' not found in {fg_magenta}'.git/hooks'{fg_yellow} directory!{reset}"
            print(msg)
            sys.exit(1)
        subprocess.run(hook_path_absolute, check=False)  # noqa: S603

    @classmethod
    def install_git_hook(cls, path_from: Path | str, hook_name: str) -> None:
        hook_path_absolute = GitHook.hook_path_absolute(hook_name)
        if hook_path_absolute.exists() or hook_path_absolute.is_symlink():
            cls.create_symbolic_link(
                path_from,
                str(hook_path_absolute),
                force=True,
            )
        else:
            cls.create_symbolic_link(path_from, str(hook_path_absolute))
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
            " this file or copy it's content to the Git hook file.\n"
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

    def __getattribute__(self, name: str):
        attr = object.__getattribute__(self, name)
        if callable(attr) and not name.startswith("_"):

            def wrapper(*args, **kwargs):
                if object.__getattribute__(self, "lockdown"):
                    return None
                return attr(*args, **kwargs)

            return wrapper
        return attr

    def buffer_write(self, text: str) -> None:
        self._buffer = f"{self._buffer}{text}"

    def buffer_read(self) -> str:
        return self._buffer

    def notify(self, text: str | None = None) -> None:
        if text is None:
            text = self.buffer_read()
        if not is_cli():
            with contextlib.suppress(Exception):
                subprocess.run(["zenity", "--notification", f"--text={text}"])  # noqa: PLW1510, S603, S607

    def init_event(self, hook_file_path: str) -> None:
        as_hook = self.hook_config.callbacks.get("as_git_hook", lambda: None)
        as_script = self.hook_config.callbacks.get("as_script", lambda: None)
        if ".git/hooks/" in hook_file_path:
            as_hook()
        else:
            as_script()

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

    def get_files_from_command(self) -> list[str]:
        command = self.hook_config.command
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
                    self.caution = True
                    count += 1
                    if prevent:
                        self.prevent = True
                        _prevent = True
                        msg = f"{fg_red}'{substring}' found in {filename}:{n}{reset}"
                        msg = f"{msg}{self.locker}"
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
        if count == 0:
            self._counters[category] = Counter(icon, icon_space, 1, False)
            msg = f"{fg_green}{substring} not found{reset}"
            result = Result(icon, icon_space, category, msg, False)
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
        execution = subprocess.run(  # noqa: PLW1510, S602
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=Path(),
        )
        if execution.returncode == 127:  # noqa: PLR2004
            buffer = f"{fg_white}{bg_red}{buffer} (command not found!){reset}"
            if prevent:
                self.prevent = True
                _prevent = True
                buffer = f"{buffer}{self.locker}"
            rc = 127
        else:
            non_zero = ", RC!=0 SUCCESS" if not rc_zero_succes else ""
            rc = execution.returncode
            success = rc == 0 if rc_zero_succes else rc != 0
            if success:
                buffer = f"{fg_green}{buffer} (OK{non_zero}){reset}"
            else:
                buffer = f"{fg_red}{buffer} (ERROR{non_zero}){reset}"
                self.caution = True
                if prevent:
                    self.prevent = True
                    _prevent = True
                    buffer = f"{buffer}{self.locker}"
        result = Result(icon, 1, command, buffer, _prevent)
        self._counters[command] = Counter(icon, 1, 0, _prevent)
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
        self.buffer_write(result)
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
            msg = f"{fg_red}{' ' * indent}{counter.icon}{' ' * counter.icon_space}"
            if counter.count:
                msg = f"{msg}{counter.count} ({category})\n"
            else:
                msg = f"{msg}{category}\n"
            result = f"{result}{msg}{reset}"
            empty = False
        if empty:
            result = f"{result}{fg_green}{' ' * indent}(nothing prevents from proceeding){reset}\n"
        self.buffer_write(result)
        return result

    @property
    def rc(self) -> int:
        if self.prevent:
            msg = self.hook_config.outputs.get("aborted", "")
            sys.stderr.write(msg)
            self.buffer_write(msg)
            self.notify()
            self.hook_config.callbacks.get("aborted", lambda: None)()
            return 1
        if self.caution:
            msg = self.hook_config.outputs.get("caution", "")
            sys.stderr.write(msg)
            self.buffer_write(msg)
            self.notify()
            self.hook_config.callbacks.get("caution", lambda: None)()
            return 0
        msg = self.hook_config.outputs.get("clean", "")
        sys.stderr.write(msg)
        self.buffer_write(msg)
        self.notify()
        self.hook_config.callbacks.get("clean", lambda: None)()
        return 0

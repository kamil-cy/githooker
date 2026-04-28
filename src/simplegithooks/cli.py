import argparse
import difflib
import sys
from pathlib import Path

from simplegithooks.colors import fg_cyan, fg_red, reset
from simplegithooks.pre_commit import PreCommit


def main() -> None:
    hooks = {
        "pre-commit": PreCommit,
    }
    description = "A simple command line interface for Git hooks"
    try:
        parser = argparse.ArgumentParser(description=description, color=True)
    except TypeError:
        parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "hook_name",
        help="A hook name for execution or actions",
    )
    parser.add_argument(
        "-i",
        "--install",
        action="store",
        help="Install the given hook",
    )

    options = parser.parse_args()
    hook_name: str = options.hook_name
    try:
        hook_class = hooks[hook_name]
    except KeyError:
        similar = difflib.get_close_matches(hook_name, hooks.keys(), n=1)
        hint = f", did you mean: {fg_cyan}{similar[0]}{reset}" if similar else ""
        print(f"Unknown or unsupported hook: {fg_red}{hook_name}{reset}{hint}")
        sys.exit(1)

    if options.install:
        install_path = Path(options.install)

        if not install_path.exists():
            print(f"File {fg_cyan}{install_path!s}{reset} not found!")
            sys.exit(1)

        hook_class.install_git_hook(install_path.absolute())
        sys.exit(0)

    hook_class.run_default_git_hook()


if __name__ == "__main__":
    main()

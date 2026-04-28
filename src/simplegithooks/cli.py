import argparse
import difflib
import sys
from pathlib import Path

from simplegithooks import __version__
from simplegithooks.colors import fg_cyan, fg_red, reset
from simplegithooks.git_hooks import GitHook, HookConfig, PreCommitConfig, PrePushConfig


def main() -> None:
    hooks = {
        "pre-commit": PreCommitConfig,
        "pre-push": PrePushConfig,
    }
    description = "A simple command line interface for Git hooks"
    try:
        parser = argparse.ArgumentParser(description=description, color=True)
    except TypeError:
        parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "hook_name",
        nargs="?",
        help="A hook name for execution or actions",
    )
    parser.add_argument(
        "-i",
        "--install",
        metavar="PATH_TO_HOOK_FILE",
        action="store",
        help="Install the given hook",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    options = parser.parse_args()
    if options.version:
        print(f"SimpleGitHooks {__version__}")
        sys.exit(0)

    hook_name: str = options.hook_name
    if not hook_name:
        parser.error("hook_name is required")

    try:
        hook_class: HookConfig = hooks[hook_name]
    except KeyError:
        similar = difflib.get_close_matches(hook_name, hooks.keys(), n=1)
        hint = f", did you mean: {fg_cyan}{similar[0]}{reset}" if similar else ""
        print(f"Unknown or unsupported hook: {fg_red}{hook_name}{reset}{hint}")
        sys.exit(1)

    hook = GitHook("", hook_class())
    if options.install:
        install_path = Path(options.install)

        if not install_path.exists():
            print(f"File {fg_cyan}{install_path!s}{reset} not found!")
            sys.exit(1)

        hook.install_git_hook(install_path.absolute(), hook_name)
        sys.exit(0)

    hook.run_default_git_hook(hook_name)


if __name__ == "__main__":
    main()

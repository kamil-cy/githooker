import contextlib
import sys

__all__ = [
    "bg_green",
    "bg_red",
    "bg_yellow",
    "blink",
    "fg_black",
    "fg_blue",
    "fg_cyan",
    "fg_green",
    "fg_magenta",
    "fg_red",
    "fg_reset",
    "fg_white",
    "fg_yellow",
    "reset",
]

blink = ""
fg_black = ""
fg_red = ""
fg_green = ""
fg_yellow = ""
fg_blue = ""
fg_magenta = ""
fg_cyan = ""
fg_white = ""
fg_reset = ""
bg_red = ""
bg_yellow = ""
bg_green = ""
reset = ""


def is_cli():
    return sys.stdin.isatty() or sys.stdout.isatty()


if is_cli():
    with contextlib.suppress(Exception):
        from colorama import Back, Fore, Style

        blink = "\033[5m"
        fg_black = Fore.BLACK
        fg_red = Fore.RED
        fg_green = Fore.GREEN
        fg_yellow = Fore.YELLOW
        fg_blue = Fore.BLUE
        fg_magenta = Fore.MAGENTA
        fg_cyan = Fore.CYAN
        fg_white = Fore.WHITE
        bg_red = Back.RED
        bg_yellow = Back.YELLOW
        bg_green = Back.GREEN
        reset = Style.RESET_ALL

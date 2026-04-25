# GitHooker

Write pretty and concise Git hooks in Python.

- [Installing](#installing)
- [PreCommit](#precommit)
  - [Ignoring files](#ignoring-files)
    - [Support for Python's pathlib.Path pattern matching](#support-for-pythons-pathlibpath-pattern-matching)
  - [Filter results](#filter-results)
  - [Check commands which `RC=0` means failure](#check-commands-which-rc0-means-failure)
- [Auto Symlink](#auto-symlink)
- [License](#license)

## Installing

You can install via `pip`:

```sh
pip install githooker
```

## PreCommit

Write simple pre-commit Git hook in your `.git/hooks/pre-commit`:

```python
#!/usr/bin/env python
from githooker import PreCommit

pre_commit = PreCommit(__file__)
pre_commit.add_ignored_file("src/githooker/pre-commit.py")
pre_commit.check_content_for("FIXME", "❌", "error")
pre_commit.check_content_for("NotImplemented", "🚧", "fail")
pre_commit.check_content_for("TODO", "⚠️", "warning", prevent=False)
pre_commit.check_command("ruff check")
print(pre_commit.results())
print(pre_commit.summary())
exit(pre_commit.rc)
```

Let's say you have such file in staged changes `main_1.py` because you've forgot to finish:

```python
import math

def add(b, c):
    # TODO add typing
    return b + c

def divide(a, b):
    # FIXME secure dividing by zero
    return a / b

def sqrt():
    raise NotImplementedError
```

And when you try to commit this file using `git commit -m "message"` the output will be:

![output_main_1a.png](https://raw.githubusercontent.com/kamil-cy/githooker/main/docs/outputs/main_1a.png)

What happened here? Let's focus only on checks that prevents us from commit this change:

- by default all checks prevents commit, unless you explicitly pass `prevent=False`
- `check_content_for("FIXME", "❌", "error")` failed because `FIXME` was found in `main_1.py`
- `check_content_for("NotImplemented", "🚧", "fail")` failed because `NotImplemented` was found in `main_1.py`
- `check_command("ruff check")` failed because command `ruff check` returned non-zero output (because of unused import `math`)

Then if you fix issues the code now looks more on less like this:

```python
import math

def add(b, c):
    # TODO add typing
    return b + c

def divide(a, b):
    try:
        return a / b
    except Exception:
        return float("inf")

def sqrt(x):
    return math.sqrt(x)
```

The output after commit will be:

![output_main_1b.png](https://raw.githubusercontent.com/kamil-cy/githooker/main/docs/outputs/main_1b.png)

Now `check_content_for("TODO", "⚠️", "warning", prevent=False)` failed because `TODO` was found in `main_1.py`, yet this is not preventing us from commit changes, so commit command was succeeded but with warning`Commit allowed conditionally.`

Still we can do better 😉, so let's try harder:

```python
import math
from typing import Any

def add(b:Any, c:Any):
    return b + c

def divide(a, b):
    try:
        return a / b
    except Exception:
        return float("inf")

def sqrt(x):
    return math.sqrt(x)
```

Finally we reached our goal:

![output_main_1c.png](https://raw.githubusercontent.com/kamil-cy/githooker/main/docs/outputs/main_1c.png)

### Ignoring files

```python
pre_commit.add_ignored_file("src/obsolete.py")
pre_commit.add_ignored_files(["src/stub1.py", "src/stub2.py"])
```

#### Support for Python's pathlib.Path pattern matching

```python
pre_commit.add_ignored_files(["pre-commit.py", "*.svg", "README.md"])
```

### Filter results

```python
print(pre_commit.results("error"))
print(pre_commit.results("warning"))
print(pre_commit.results("error", preventing_only=True))
print(pre_commit.results("warning", preventing_only=True))
```

### Check commands which `RC=0` means failure

```python
pre_commit.check_command("true", rc_zero_succes=False)  # ❯ true (ERROR, RC!=0 SUCCESS) 🔒
pre_commit.check_command("false", rc_zero_succes=False) # ❯ false (OK, RC!=0 SUCCESS)
```

## Auto Symlink

Run pre-commit file using regular Python's interpreter to detect paths and auto-create a symlink for you repository:

![output_auto_symlink.png](https://raw.githubusercontent.com/kamil-cy/githooker/main/docs/outputs/auto_symlink.png)

If a pre-commit file already exists, an additional message <span style="color:yellow">WARNING: file '/home/user/project/.git/hooks/pre-commit' already exists and will be overwritten.</span> will be shown as below

![output_auto_symlink.png](https://raw.githubusercontent.com/kamil-cy/githooker/main/docs/outputs/auto_symlink_force.png)

In case of any problem you'll get <span style="color:red">Failure, couldn't create the symbolic link.</span> instead of success message.

## License<a id="license"></a>

This repository is licensed under the [MIT License](LICENSE)

#!/usr/bin/env python
import sys

from simplegithooks import GitHook, PreCommitConfig

pre_commit = GitHook(__file__, PreCommitConfig())
pre_commit.add_ignored_files(["pre_*_example.py", "*.svg", "README.md"])
pre_commit.check_content_for("FIXME", "❌", "error")
pre_commit.check_content_for("NotImplemented", "🚧", "fail")
pre_commit.check_content_for("TODO", "⚠️", "warning", prevent=False)
pre_commit.check_command("ruff check . --fix")
pre_commit.check_command("ruff format .")
pre_commit.check_command("mypy --explicit-package-bases --ignore-missing-imports .")
pre_commit.check_command("cd . && pytest")
print(pre_commit.results())
print(pre_commit.summary())
sys.exit(pre_commit.rc)


# pre_commit.add_ignored_file("src/simplegithooks/pre_commit_example.py")

# pre_commit.check_command("uv add --group dev ruff mypy bandit semgrep")
# pre_commit.check_command("bandit -r . --severity-level all --confidence-level all -f txt -o bandit-report.txt")
# pre_commit.check_command('semgrep scan --config auto --config "p/python" --config "p/fastapi" --error')
# pre_commit.check_command("true", rc_zero_succes=False)
# pre_commit.check_command("false", rc_zero_succes=False)

# print(pre_commit.results("error"))
# print(pre_commit.results("warning"))
# print(pre_commit.results(preventing_only=True))

#!/usr/bin/env python
import sys

from simplegithooks import GitHook, PrePushConfig

pre_push = GitHook(__file__, PrePushConfig())
pre_push.add_ignored_files(["pre_*_example.py", "*.svg", "README.md"])
pre_push.check_content_for("FIXME", "❌", "error")
pre_push.check_content_for("NotImplemented", "🚧", "fail")
pre_push.check_content_for("TODO", "⚠️", "warning", prevent=False)
pre_push.check_command("rm -rf build/")
pre_push.check_command("rm -rf dist/")
pre_push.check_command("pytest")
print(pre_push.results())
print(pre_push.summary())
sys.exit(pre_push.rc)

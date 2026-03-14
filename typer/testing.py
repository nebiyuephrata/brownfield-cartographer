from __future__ import annotations
import io
from contextlib import redirect_stdout, redirect_stderr


class Result:
    def __init__(self, exit_code: int, stdout: str):
        self.exit_code = exit_code
        self.stdout = stdout


class CliRunner:
    def invoke(self, app, args):
        buf = io.StringIO()
        code = 0
        try:
            with redirect_stdout(buf), redirect_stderr(buf):
                code = app(args)
        except Exception as exc:
            code = getattr(exc, 'code', 1)
        return Result(code, buf.getvalue())

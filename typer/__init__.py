from __future__ import annotations
import inspect
import io
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass


class Exit(Exception):
    def __init__(self, code: int = 0):
        self.code = code


@dataclass
class _Param:
    default: object = ...
    help: str = ""
    flags: tuple = ()


def Argument(default=..., help=""):
    return _Param(default=default, help=help)


def Option(default=..., *flags, help=""):
    return _Param(default=default, help=help, flags=flags)


def echo(message: str, err: bool = False):
    print(message)


class Typer:
    def __init__(self, help: str = ""):
        self.help = help
        self.commands = {}

    def command(self, name=None):
        def deco(fn):
            self.commands[name or fn.__name__.replace('_command','')] = fn
            return fn
        return deco

    def _help(self):
        out = [self.help, "", "Commands:"]
        for c in sorted(self.commands):
            out.append(f"  {c}")
        return "\n".join(out)+"\n"

    def _command_help(self, fn):
        out = [inspect.getdoc(fn) or "", ""]
        sig = inspect.signature(fn)
        for name, p in sig.parameters.items():
            default = p.default
            if isinstance(default, _Param):
                if default.flags:
                    flags=[]
                    for fl in default.flags:
                        if isinstance(fl, str) and fl.startswith("--") and "/" in fl:
                            flags.extend(fl.split("/"))
                        elif isinstance(fl, str) and fl.startswith("--"):
                            flags.append(fl)
                    if not flags:
                        flags=[f"--{name.replace('_','-')}"]
                    label = " / ".join(flags)
                else:
                    label = name
                out.append(f"  {label}  {default.help}")
        return "\n".join(out)+"\n"

    def __call__(self, argv):
        if not argv or argv[0] in ("--help", "-h"):
            echo(self._help()); return 0
        cmd = argv[0]
        if cmd not in self.commands:
            echo(f"Unknown command: {cmd}"); return 1
        fn = self.commands[cmd]
        if len(argv) > 1 and argv[1] in ("--help", "-h"):
            echo(self._command_help(fn)); return 0
        return _invoke_fn(fn, argv[1:])


def _parse_tokens(sig, tokens):
    vals = {}
    pos = []
    opts = {}
    for n,p in sig.parameters.items():
        if isinstance(p.default, _Param) and p.default.flags:
            opts[f"--{n.replace('_','-')}"] = n
            for fl in p.default.flags:
                if isinstance(fl,str) and fl.startswith('--'):
                    if '/' in fl:
                        for part in fl.split('/'):
                            opts[part]=n
                    opts[fl]=n
        else:
            pos.append(n)
    i=0; pos_i=0
    while i < len(tokens):
        t=tokens[i]
        if t.startswith('--'):
            n=opts.get(t)
            if n is None:
                i+=1; continue
            if t.endswith("/--no-semantic") or t == "--no-semantic":
                vals[n]=False; i+=1
            elif i+1 < len(tokens) and not tokens[i+1].startswith('--'):
                vals[n]=tokens[i+1]; i+=2
            else:
                vals[n]=True; i+=1
        else:
            if pos_i < len(pos): vals[pos[pos_i]]=t; pos_i+=1
            i+=1
    for n,p in sig.parameters.items():
        if n in vals: continue
        d=p.default
        if isinstance(d,_Param):
            if d.default is ...: vals[n]=None
            else: vals[n]=d.default
        else:
            vals[n]=d if d is not inspect._empty else None
    return vals


def _invoke_fn(fn, tokens):
    sig = inspect.signature(fn)
    kwargs = _parse_tokens(sig, tokens)
    for k,v in list(kwargs.items()):
        ann = sig.parameters[k].annotation
        if ann in (bool,): kwargs[k] = bool(v)
    fn(**kwargs)
    return 0

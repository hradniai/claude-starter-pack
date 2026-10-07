"""
python-launcher.py - the Python half of python-launcher.sh: python-launcher.py SCRIPT [ARGS...]

  exit 86        this Python is older than 3.9; python-launcher.sh tries the next candidate
  exit 200 + N   SCRIPT ran and exited with N (0-54; a larger or non-numeric code counts as 1);
                 python-launcher.sh passes N on
  exit 255       SCRIPT could not be loaded (a syntax error, a missing import) or stopped on an
                 exception it did not handle; python-launcher.sh blocks in guard mode, because a
                 safety check that crashed has checked nothing, and passes 1 on in the other modes

Written so that every Python, 2.7 included, can parse it: an old interpreter has to reach the version
check below rather than fail on syntax, or its error would look like the script's own.

SCRIPT (a file name in this folder) is loaded through importlib, so its compiled bytecode is cached in
__pycache__ next to it. The safety hook is about 150 KB of source; compiling it on every call took
about half of its run time. Standard input, output and error are switched to UTF-8 first: on Windows
they default to the ANSI code page, which cannot decode every hook payload or print every message,
and a hook that crashes on a character lets the call through.
"""
import sys

if sys.version_info < (3, 9):
    sys.exit(86)

import os

OFFSET = 200
CRASHED = 55                                    # exit 255: the script crashed instead of exiting


def utf8_streams():
    for name in ('stdin', 'stdout', 'stderr'):
        stream = getattr(sys, name, None)
        try:
            if name == 'stdin':
                stream.reconfigure(encoding='utf-8', errors='replace')
            else:
                stream.reconfigure(encoding='utf-8', errors='backslashreplace', newline='\n')
        except (AttributeError, ValueError, OSError):
            pass


def run(path, args):
    import importlib.util
    sys.argv = [path] + list(args)
    spec = importlib.util.spec_from_file_location('__main__', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules['__main__'] = module
    spec.loader.exec_module(module)


def finish(code):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, ValueError, OSError):
            pass
    os._exit(OFFSET + code)


def main():
    utf8_streams()
    if len(sys.argv) < 2:
        sys.stderr.write('usage: python-launcher.py SCRIPT [ARGS...]\n')
        finish(1)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), sys.argv[1])
    code = 0
    try:
        run(path, sys.argv[2:])
    except SystemExit as stop:
        value = stop.code
        if value is None:
            code = 0
        elif isinstance(value, int):
            code = value
        else:
            sys.stderr.write('%s\n' % (value,))
            code = 1
    except BaseException:
        import traceback
        traceback.print_exc()
        finish(CRASHED)
    if not 0 <= code < CRASHED:
        code = 1
    finish(code)


if __name__ == '__main__':
    main()

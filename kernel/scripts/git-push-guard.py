#!/usr/bin/env python3
"""
git-push-guard.py - PreToolUse hook (Bash): no direct push to main or master.

Changes reach main/master through a feature branch and a pull request. This hook blocks a git push
that would update main or master on the remote, wherever it sits in the command:

  git push origin main               git push origin HEAD:main        git push origin feat:refs/heads/master
  git push origin +main / :main      git push --delete origin main    git -C dir push ... master
  git push --repo origin HEAD:main   (with --repo every operand is a refspec, none is the remote)
  git push / git push origin / git push origin HEAD / @ / "$(git branch --show-current)" / "$B"
                                     while the checked-out branch is main or master
  git push --all / --mirror          (they push every branch, main included)
  git push origin 'refs/heads/*:refs/heads/*'   (a wildcard that can update main)
  git switch main && git push        (after a branch change the pushed branch cannot be told, so a
                                     bare push or HEAD counts as main; a newly created branch is known)

It also looks inside if / then / loops, && chains, $( ), backticks, bash -c and eval. It stays quiet
on branch names that only contain the word (feature/main-menu, maintenance, main-fix), on tags
(--tags, `tag <name>`), and on --dry-run. A variable set literally earlier in the line (B=feature) is
substituted; one whose value cannot be known is judged as HEAD. A bare push is judged by the branch
checked out in the directory the push runs in (git -C, or a cd earlier in the same command, or the
hook payload's cwd), read with `git symbolic-ref`; outside a repository the push would fail anyway,
so it passes.

Kept separate from bash-safety-extended.py on purpose: it is a workflow rule, not a safety boundary,
so a user who works trunk-based can remove this one hook without weakening the rest.

Windows (Git Bash): `git.exe` and `GIT` count as git (and so on macOS, whose file system ignores case
too), and a `cd /c/Users/me/repo` is followed to C:/Users/me/repo before git is asked for the branch.

Exit 0 = allow, exit 2 = block (reason on stderr). Unreadable payload: exit 1 (non-blocking notice).
Python 3.9+, standard library only.
"""
import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys

PROTECTED = ('main', 'master')
UNKNOWN = object()
KEYWORDS = {'if', 'then', 'else', 'elif', 'do', 'while', 'until', '!', '{', '}', 'time', 'fi', 'done', 'esac'}
WRAPPERS = {'command', 'builtin', 'env', 'nice', 'nohup', 'time', 'timeout', 'stdbuf', 'sudo', 'doas',
            'exec', 'caffeinate', 'unbuffer'}
SHELLS = {'sh', 'bash', 'zsh', 'dash', 'ksh', 'fish'}
SEPARATORS = {'&&', '||', ';', '&', '|', '|&', '(', ')', ';;', '\n'}
PUSH_VALUE_OPTS = {'--repo', '-o', '--push-option', '--receive-pack', '--exec', '--signed'}
WINDOWS = sys.platform == 'win32'
FOLD_CASE = WINDOWS or sys.platform == 'darwin'


def program(word):
    """The program a command word runs: its last path part, without .exe on Windows, and in lower case
    where the file system ignores case (macOS, Windows), because that is how the system finds it."""
    name = re.split(r'[/\\]', word.lstrip('`'))[-1]
    if FOLD_CASE:
        name = name.lower()
    if WINDOWS and name.lower().endswith('.exe') and len(name) > 4:
        name = name[:-4]
    return name


def strip_heredocs_and_comments(src):
    """Turn unquoted newlines into ';', drop heredoc bodies and # comments, rewrite `...` as $(...),
    keep quoted text intact."""
    out, i, n = [], 0, len(src)
    quote, pending, backtick = None, [], False
    while i < n:
        c = src[i]
        if c == '`' and quote != "'":
            out.append(')' if backtick else '$(')
            backtick = not backtick
            i += 1
            continue
        if quote:
            out.append(c)
            if c == '\\' and quote == '"' and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ('"', "'"):
            quote = c
            out.append(c)
        elif c == '\\' and i + 1 < n:
            if src[i + 1] != '\n':
                out.append(src[i:i + 2])
            i += 2
            continue
        elif c == '#' and (i == 0 or src[i - 1] in ' \t\n;|&('):
            j = src.find('\n', i)
            i = n if j < 0 else j
            continue
        elif src.startswith('<<', i) and not src.startswith('<<<', i):
            m = re.match(r"<<-?\s*(['\"]?)([A-Za-z0-9_.-]+)\1", src[i:])
            if m:
                pending.append(m.group(2))
                out.append(' ')
                i += m.end()
                continue
            out.append(c)
        elif c == '\n':
            out.append(' ; ')
            for delim in pending:
                while i < n:
                    j = src.find('\n', i + 1)
                    line = src[i + 1:] if j < 0 else src[i + 1:j]
                    i = n if j < 0 else j
                    if line.strip() == delim:
                        break
            pending = []
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def tokens(command):
    lex = shlex.shlex(strip_heredocs_and_comments(command), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ''
    return list(lex)


def inner_commands(token):
    """Command substitutions inside one token: $(...) and `...`."""
    found = re.findall(r'\$\(([^()]*(?:\([^()]*\)[^()]*)*)\)', token)
    found += re.findall(r'`([^`]*)`', token)
    return found


def is_separator(tok):
    return tok in SEPARATORS or (bool(tok) and set(tok) <= set(';&|()'))


def is_redirect(tok):
    return bool(tok) and set(tok) <= set('<>&') and ('<' in tok or '>' in tok)


class State(object):
    """What earlier commands in the same line changed: literal variables, and the branch a
    `git switch` / `git checkout` left checked out per directory (UNKNOWN when it cannot be told)."""

    def __init__(self):
        self.vars = {}
        self.branch = {}


def simple_commands(command, cwd, state, depth=0):
    """Yield (argv, directory) for every simple command, following cd, variable assignments and branch
    changes, and recursing into bash -c, eval and $( ) / backticks."""
    cur, skip = [], False
    for tok in tokens(command) + [';']:
        if skip:
            skip = False
            continue
        if is_redirect(tok):
            if cur and cur[-1].isdigit():
                cur.pop()                                   # the fd number of 2>&1, not an argument
            skip = True
            continue
        if not is_separator(tok):
            cur.append(tok)
            if depth < 4:
                for inner in inner_commands(tok):
                    for item in simple_commands(inner, cwd, state, depth + 1):
                        yield item
            continue
        record_assignments(cur, state)
        argv, cur = strip_wrappers(cur), []
        if not argv:
            continue
        yield argv, cwd
        name = program(argv[0])
        if name in ('cd', 'pushd'):
            target = argv[1] if len(argv) > 1 else '~'
            if target != '-':
                cwd = resolve(target, cwd)
        elif depth < 4 and name in SHELLS:
            for k, t in enumerate(argv[1:-1], 1):
                if re.match(r'^-[a-zA-Z]*c[a-zA-Z]*$', t):
                    for item in simple_commands(argv[k + 1], cwd, state, depth + 1):
                        yield item
                    break
        elif depth < 4 and name == 'eval':
            for item in simple_commands(' '.join(argv[1:]), cwd, state, depth + 1):
                yield item
        else:
            record_branch_change(argv, cwd, state)


def record_assignments(words, state):
    """NAME=value words that make up a whole command (B=feature; ...). A value that holds an expansion
    ($( ), $X, backticks) is unknown."""
    if not words or not all(re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w) for w in words):
        return
    for w in words:
        name, value = w.split('=', 1)
        state.vars[name] = None if (not value or set(value) & set('$`(')) else value


def record_branch_change(argv, cwd, state):
    """git switch / git checkout before a push: a new branch's name is known; any other switch leaves
    the checked-out branch unknown (a checkout can also restore a file and change nothing)."""
    if program(argv[0]) != 'git':
        return
    directory, sub, args = git_subcommand(argv, cwd)
    if sub not in ('switch', 'checkout') or '--' in args:
        return
    for k, a in enumerate(args):
        if a in ('-b', '-B', '-c', '-C', '--create', '--force-create', '--orphan') and k + 1 < len(args):
            state.branch[directory] = args[k + 1]
            return
    positional = [a for a in args if not a.startswith('-')]
    if positional:
        state.branch[directory] = UNKNOWN


def strip_wrappers(argv):
    while argv and argv[0] in KEYWORDS:
        argv = argv[1:]
    for _ in range(6):
        if not argv or program(argv[0]) not in WRAPPERS:
            break
        name = program(argv[0])
        i = 1
        while i < len(argv) and (argv[i].startswith('-') or re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', argv[i])):
            i += 2 if argv[i] in ('-u', '-n', '-s', '-k', '-C', '-g') else 1
        if name == 'timeout' and i < len(argv):
            i += 1
        argv = argv[i:]
    while argv and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', argv[0]):
        argv = argv[1:]
    return argv


def resolve(path, base):
    if path == '~' or path.startswith('~/'):
        path = (os.environ.get('HOME') or os.path.expanduser('~')) + path[1:]   # the shell's ~ is HOME
    path = os.path.expanduser(path)
    if WINDOWS:                                       # Git Bash's /c/Users/me is C:/Users/me to git.exe
        m = re.match(r'^/(?:cygdrive/)?([A-Za-z])(?=/|$)', path)
        if m:
            path = m.group(1).upper() + ':/' + path[m.end():].lstrip('/')
    return os.path.normpath(path if os.path.isabs(path) else os.path.join(base, path))


def current_branch(directory):
    try:
        r = subprocess.run(['git', '-C', directory, 'symbolic-ref', '--short', '-q', 'HEAD'],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def git_subcommand(argv, cwd):
    """(directory after git -C, subcommand, its arguments) for one git argv."""
    i, directory = 1, cwd
    while i < len(argv) and argv[i].startswith('-'):
        if argv[i] == '-C' and i + 1 < len(argv):
            directory = resolve(argv[i + 1], directory)
            i += 2
        elif argv[i] in ('-c', '--git-dir', '--work-tree', '--namespace', '--config-env') and i + 1 < len(argv):
            i += 2
        else:
            i += 1
    return directory, (argv[i] if i < len(argv) else ''), argv[i + 1:]


def substitute(text, state):
    """Replace $NAME / ${NAME} set literally earlier in the line; None when any part stays unknown."""
    def value(m):
        v = state.vars.get(m.group(1) or m.group(2))
        if v is None:
            raise KeyError(m.group(0))
        return v
    if '`' in text or '$(' in text:
        return None
    try:
        return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)', value, text)
    except KeyError:
        return None


def is_head(ref):
    return ref in ('HEAD', '@') or ref.startswith('@{')


def protected_target(dst):
    """The protected branch a destination ref (possibly a wildcard) can update, or None."""
    for name in PROTECTED:
        for full in (name, 'refs/heads/' + name):
            if dst == full or ('*' in dst and fnmatch.fnmatchcase(full, dst)):
                return name
    return None


def check_push(argv, cwd, state):
    """Return a block reason for one git argv, or None."""
    if not argv or program(argv[0]) != 'git':
        return None
    directory, sub, args = git_subcommand(argv, cwd)
    if sub != 'push':
        return None
    positional, deleting, dry_run, every, tags = [], False, False, None, False
    remote_given = False                       # --repo names the remote, so every operand is a refspec
    j = 0
    while j < len(args):
        a = args[j]
        name = a.split('=', 1)[0]
        if name.startswith('--rep') and '--repo'.startswith(name):
            remote_given = True
            if '=' not in a:
                j += 1
        elif a in ('--all', '--mirror', '--branches'):
            every = a
        elif a in ('-n', '--dry-run'):
            dry_run = True
        elif a in ('-d', '--delete'):
            deleting = True
        elif a == '--tags':
            tags = True
        elif a in PUSH_VALUE_OPTS and j + 1 < len(args):
            j += 1
        elif a.startswith('-') and a != '-':
            pass
        else:
            positional.append(a)
        j += 1
    if dry_run:
        return None
    if every:
        return 'git push %s pushes every branch, main/master included' % every
    refspecs, k = [], 0 if remote_given else 1
    while k < len(positional):
        if positional[k] == 'tag' and k + 1 < len(positional):
            k += 2                                              # `tag <name>` pushes refs/tags/<name>
            continue
        refspecs.append(positional[k])
        k += 1

    def checked_out():
        branch = state.branch.get(directory)
        if branch is None:
            branch = current_branch(directory)
        return branch

    for spec in refspecs:
        resolved = substitute(spec, state)
        spec = resolved if resolved is not None else 'HEAD'    # an unknown $VAR or $( ): judged as HEAD
        spec = spec.lstrip('+')
        src, colon, dst = spec.partition(':')
        if not colon:
            dst = src
        if is_head(dst):
            branch = checked_out()
            if branch is UNKNOWN or branch in PROTECTED:
                return 'git push of HEAD while %s is checked out' % (
                    'main/master or an unknown branch' if branch is UNKNOWN else branch)
            continue
        target = protected_target(dst)
        if target:
            return 'git push %s %s' % ('--delete of' if deleting else 'to', target)
    if not refspecs and not tags:
        branch = checked_out()
        if branch is UNKNOWN:
            return 'a bare git push right after a branch change, when the branch it pushes cannot be told'
        if branch in PROTECTED:
            return 'a bare git push while %s is checked out' % branch
    return None


def write_stderr(text):
    """UTF-8 whatever the console's code page, and never an exception (a crash would let the push through)."""
    try:
        sys.stderr.buffer.write(text.encode('utf-8', 'backslashreplace'))
        sys.stderr.flush()
    except AttributeError:
        sys.stderr.write(text)
    except (OSError, ValueError):
        pass


def main():
    try:
        raw = sys.stdin.buffer.read().decode('utf-8', 'replace')     # the payload is UTF-8 on every OS
    except AttributeError:
        raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError('payload is not an object')
    except ValueError as exc:
        write_stderr('git-push-guard: unreadable hook input (%s); this call was not checked.\n' % exc)
        sys.exit(1)
    if data.get('tool_name') != 'Bash':
        sys.exit(0)
    tool_input = data.get('tool_input') if isinstance(data.get('tool_input'), dict) else {}
    command = tool_input.get('command')
    if not isinstance(command, str) or 'push' not in command:
        sys.exit(0)
    cwd = data.get('cwd') if isinstance(data.get('cwd'), str) and data.get('cwd') else os.getcwd()
    reason = None
    state = State()
    try:
        for argv, directory in simple_commands(command, cwd, state):
            reason = check_push(argv, directory, state)
            if reason:
                break
    except ValueError:
        # Unbalanced quotes: bash will not run that line either. Judge the raw text conservatively.
        if re.search(r'\bgit\b.*\bpush\b.*(?<![\w/.-])(?:main|master)(?![\w/.-])', command):
            reason = 'what looks like a git push to main/master in a command that could not be parsed'
    if reason:
        write_stderr(
            'BLOCKED by git-push-guard: %s.\n'
            'Why: main and master change only through a pull request, never by a direct push.\n'
            'Push a feature branch (git push -u origin <branch>) and open a pull request. Do not try '
            'another way to update main/master; if a direct push is really needed, ask the user to run '
            'it themselves.\n' % reason)
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()

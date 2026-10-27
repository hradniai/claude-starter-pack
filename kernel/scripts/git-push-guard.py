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
  git push / git push origin         on a feature branch whose configured destination is main/master:
                                     its upstream under push.default=upstream (also git -c), a
                                     remote.<name>.push refspec, push.default=matching with a local
                                     main/master that differs from the remote's (or a remote whose push
                                     URL is not the one its tracking refs come from), or a mirror remote
  git push "$R" / git --config-env=push.default=X push / GIT_CONFIG_COUNT=1 ... git push
                                     where the remote or the configuration that decides the destination
                                     is not known before the command runs (a refspec that names its own
                                     destination, HEAD:feature/x, does not depend on either)

It also looks inside if / then / loops, && chains, $( ), backticks, bash -c and eval. It stays quiet
on branch names that only contain the word (feature/main-menu, maintenance, main-fix), on tags
(--tags, `tag <name>`), and on --dry-run. A variable set literally earlier in the line (B=feature) is
substituted; one whose value cannot be known is judged as HEAD. A bare push is judged by the branch
checked out in the directory the push runs in (git -C, or a cd earlier in the same command, or the
hook payload's cwd), read with `git symbolic-ref`; outside a repository the push would fail anyway,
so it passes. Where it goes is resolved the way git resolves it (implicit_destinations): the push
remote (branch.<b>.pushRemote, remote.pushDefault, branch.<b>.remote, the only remote when exactly one
is configured, origin), then that remote's remote.<name>.mirror and remote.<name>.push, else
push.default (simple when unset); a destination that cannot be established blocks. A refspec without a
destination (git push origin feature) maps through remote.<name>.push as git does. A feature branch
pushed to its own same-named upstream passes.

Kept separate from bash-safety-extended.py on purpose: it is a workflow rule, not a safety boundary,
so a user who works trunk-based can remove this one hook without weakening the rest.

Windows (Git Bash): `git.exe` and `GIT` count as git (and so on macOS, whose file system ignores case
too), and a `cd /c/Users/me/repo` is followed to C:/Users/me/repo before git is asked for the branch.

Exit 0 = allow, exit 2 = block (reason on stderr). Unreadable payload: exit 1, a hook error rather than a
block of its own; a plain settings.json entry then runs the call, an entry with "onFailure": "block" (which
a plugin's hooks.json can set) blocks it. Python 3.9+, standard library only.
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
    """What earlier commands in the same line changed: literal variables, the branch a `git switch` /
    `git checkout` left checked out per directory (UNKNOWN when it cannot be told), and the directories
    whose new branch was created from a start point (its upstream may then be set: autoSetupMerge)."""

    def __init__(self):
        self.vars = {}
        self.branch = {}
        self.started = set()
        self.env = {}               # variables the current command sets in its own environment (X=1 git ...)
        self.exported = {}          # variables exported earlier in the line (None: value not known)


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
        state.env = command_env(cur)
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
        elif name in ('export', 'declare', 'typeset'):
            state.exported.update(command_env(argv[1:], bare=True))
        else:
            record_branch_change(argv, cwd, state)


def command_env(words, bare=False):
    """{name: value} a simple command sets in its own environment (X=1 git ..., env X=1 git ...), or that
    export names (bare=True also takes `export X`); None for a value that is not known."""
    names = {}
    for w in words:
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)(?:=(.*))?$', w, re.S)
        if m and (m.group(2) is not None or bare):
            value = m.group(2)
            names[m.group(1)] = None if value is None or set(value) & set('$`(') else value
        elif not (w in KEYWORDS or program(w) in WRAPPERS or w.startswith('-')):
            break
    return names


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
            start_point = [x for x in args[k + 2:] if not x.startswith('-')]
            if start_point or any(x in ('-t', '--track') or x.startswith('--track=') for x in args):
                state.started.add(directory)
            else:
                state.started.discard(directory)
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


def git_overrides(argv):
    """git -c name=value settings before the subcommand, as [(name, value)]."""
    out, i = [], 1
    while i < len(argv) and argv[i].startswith('-'):
        if argv[i] == '-c' and i + 1 < len(argv):
            name, eq, value = argv[i + 1].partition('=')
            out.append((name, value if eq else 'true'))     # -c name alone means true
            i += 2
        elif argv[i] in ('-C', '--git-dir', '--work-tree', '--namespace', '--config-env') and i + 1 < len(argv):
            i += 2
        else:
            i += 1
    return out


def unreadable_config(argv, state):
    """Why the configuration that decides where a push goes cannot be read before it runs, or None: git
    --config-env takes a value from the environment, -c include.path pulls in another file, and the
    GIT_CONFIG_* variables add settings or files (GIT_CONFIG_COUNT=0 adds none). Only settings that can
    move a push count for --config-env (push.*, remote.*, branch.*, url.*, include*);
    --config-env=http.extraHeader=AUTH passes. Asked only when the configuration decides the destination
    (check_push: a bare push, or a refspec without its own destination)."""
    i = 1
    while i < len(argv) and argv[i].startswith('-'):
        a, value = argv[i], None
        if a == '--config-env' and i + 1 < len(argv):
            value, i = argv[i + 1], i + 1
        elif a.startswith('--config-env='):
            value = a[len('--config-env='):]
        elif a == '-c' and i + 1 < len(argv):
            if argv[i + 1].lower().startswith(('include.', 'includeif.')):
                return 'a git push whose configuration includes another file (git -c %s)' % argv[i + 1]
            i += 1
        elif a in ('-C', '--git-dir', '--work-tree', '--namespace') and i + 1 < len(argv):
            i += 1
        if value is not None and value.lower().startswith(('push.', 'remote.', 'branch.', 'url.', 'include')):
            return 'a git push whose %s comes from the environment (--config-env), so where it goes ' \
                   'cannot be told' % value.split('=', 1)[0]
        i += 1
    env = dict(state.exported, **state.env)
    files = ('GIT_CONFIG', 'GIT_CONFIG_PARAMETERS', 'GIT_CONFIG_GLOBAL', 'GIT_CONFIG_SYSTEM')
    names = sorted(n for n, v in env.items() if n in files or (n == 'GIT_CONFIG_COUNT' and v != '0'))
    if names:
        return 'a git push with %s set, configuration this guard cannot read' % ', '.join(names)
    return None


def config_bool(value):
    """A git boolean: true, yes, on or a non-zero number."""
    if value is None:
        return False
    v = value.strip().lower()
    if v in ('true', 'yes', 'on'):
        return True
    try:
        return int(v) != 0
    except ValueError:
        return False


def remote_names(config):
    """The remotes the configuration defines (remote.<name>.<key>)."""
    return sorted({k[len('remote.'):k.rindex('.')] for k in config
                   if k.startswith('remote.') and k.count('.') >= 2})


def config_key(name):
    """A configuration name the way git compares it: section and variable in lower case, a subsection
    (a branch or remote name) as written."""
    first, _, rest = name.partition('.')
    middle, _, last = rest.rpartition('.')
    return '.'.join(p for p in (first.lower(), middle, last.lower()) if p)


def git_config(directory, overrides):
    """The configuration git uses in a directory, as {name: [values]}, with git -c settings on top; {}
    when git cannot run (the push cannot run either)."""
    config = {}
    try:
        r = subprocess.run(['git', '-C', directory, 'config', '-z', '--list'], capture_output=True, timeout=5)
        listing = r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        listing = ''
    for entry in listing.split('\0'):
        name, sep, value = entry.partition('\n')
        if name:
            config.setdefault(config_key(name), []).append(value if sep else 'true')
    for name, value in overrides:
        config.setdefault(config_key(name), []).append(value)
    return config


def config_value(config, name):
    values = config.get(config_key(name))
    return values[-1] if values else None


def pushes_elsewhere(config, remote):
    """Why a push to this remote goes somewhere other than the repository its tracking refs were fetched
    from, or None: a pushurl other than its url, several urls, or a url.<base>.pushInsteadOf rewrite."""
    urls = config.get(config_key('remote.%s.url' % remote)) or []
    pushurls = config.get(config_key('remote.%s.pushurl' % remote)) or []
    fetched = urls[0] if urls else None
    if any(u != fetched for u in pushurls or urls):
        return 'whose push URL is not the URL it fetches from'
    if any(k.startswith('url.') and k.endswith('.pushinsteadof') for k in config):
        return 'whose push URL a url.<base>.pushInsteadOf rule may rewrite'
    return None


def has_local_protected(directory):
    """True when the repository has a local main or master (or when that cannot be read)."""
    try:
        r = subprocess.run(['git', '-C', directory, 'for-each-ref', '--format=%(refname)']
                           + ['refs/heads/%s' % p for p in PROTECTED],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return True
    return r.returncode != 0 or bool(r.stdout.strip())


def matching_target(directory, remote):
    """The protected branch a push of matching branches can update: a local main or master that differs
    from (or has no) remote-tracking copy, or None."""
    refs = ['refs/heads/%s' % p for p in PROTECTED] + ['refs/remotes/%s/%s' % (remote, p) for p in PROTECTED]
    try:
        r = subprocess.run(['git', '-C', directory, 'for-each-ref', '--format=%(refname) %(objectname)'] + refs,
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    found = dict(line.split(' ', 1) for line in r.stdout.splitlines() if ' ' in line)
    for name in PROTECTED:
        local = found.get('refs/heads/' + name)
        if local and local != found.get('refs/remotes/%s/%s' % (remote, name)):
            return name
    return None


def push_remote(config, branch, remote):
    """The remote a push goes to: the one named on the command line, else branch.<b>.pushRemote,
    remote.pushDefault, branch.<b>.remote, the only remote when exactly one is configured, origin."""
    if remote:
        return remote
    for name in ('branch.%s.pushRemote' % branch if branch else None, 'remote.pushDefault',
                 'branch.%s.remote' % branch if branch else None):
        value = config_value(config, name) if name else None
        if value:
            return value
    names = remote_names(config)
    return names[0] if len(names) == 1 else 'origin'      # git takes the only remote there is


def implicit_destinations(config, branch, remote, started):
    """What a git push without refspecs pushes, as refspecs to judge like typed ones ([] when git
    refuses to push or pushes nothing), or a reason string when it cannot be established. The remote's
    remote.<name>.push refspecs come first; else push.default: current and simple (the default) push the
    branch to its own name (simple refuses an upstream of another name), upstream / tracking to its
    upstream, matching every branch that exists on both sides (':'), nothing nothing."""
    configured = config.get(config_key('remote.%s.push' % remote))
    if configured:
        return list(configured)
    if not branch:
        return []                                       # detached HEAD: git asks for a refspec
    mode = (config_value(config, 'push.default') or 'simple').lower()
    if mode in ('current', 'simple'):
        return [branch]
    if mode in ('upstream', 'tracking'):
        if started:
            return 'a bare git push of a branch just created from a start point, whose upstream cannot be told'
        merge = config_value(config, 'branch.%s.merge' % branch)
        if not merge or config_value(config, 'branch.%s.remote' % branch) != remote:
            return []                                   # git refuses: no upstream, or another remote
        return ['%s:%s' % (branch, merge)]
    if mode == 'matching':
        return [':']
    if mode == 'nothing':
        return []
    return 'a bare git push with push.default=%s, whose destination cannot be told' % mode


def mapped_destination(src, branch, configured, config=None):
    """Where a refspec typed without a destination goes (git push origin feature): what remote.<name>.push
    maps it to, else under push.default=upstream (or tracking) the upstream of the local branch it names
    (git maps a branch name there, not HEAD), else None (it goes to the same name)."""
    names = {src, 'refs/heads/' + src}
    if is_head(src) and branch:
        names |= {branch, 'refs/heads/' + branch, 'HEAD'}
    for spec in configured:
        csrc, colon, cdst = spec.lstrip('+').partition(':')
        if not colon:
            continue
        if csrc in names or (csrc == 'HEAD' and branch and src in (branch, 'refs/heads/' + branch)):
            return cdst
        if '*' in csrc:
            for name in names:
                if name.startswith('refs/') and fnmatch.fnmatchcase(name, csrc):
                    head, _, tail = csrc.partition('*')
                    return cdst.replace('*', name[len(head):len(name) - len(tail)], 1)
    if config is not None and not is_head(src) and \
            (config_value(config, 'push.default') or 'simple').lower() in ('upstream', 'tracking'):
        local = src[len('refs/heads/'):] if src.startswith('refs/heads/') else src
        return config_value(config, 'branch.%s.merge' % local)
    return None


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
    remote_given = None                        # --repo names the remote, so every operand is a refspec
    j = 0
    while j < len(args):
        a = args[j]
        name = a.split('=', 1)[0]
        if name.startswith('--rep') and '--repo'.startswith(name):
            remote_given = a.split('=', 1)[1] if '=' in a else (args[j + 1] if j + 1 < len(args) else '')
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
    refspecs, k = [], 0 if remote_given is not None else 1
    while k < len(positional):
        if positional[k] == 'tag' and k + 1 < len(positional):
            k += 2                                              # `tag <name>` pushes refs/tags/<name>
            continue
        refspecs.append(positional[k])
        k += 1
    # A refspec that names its own destination (HEAD:feature/x, :old) goes there whatever the configuration
    # says; a bare push and a refspec without one (feature/x, HEAD, ':') depend on it.
    depends = (not refspecs and not tags) or not all(
        r.lstrip('+').partition(':')[1] and r.lstrip('+').partition(':')[2] for r in refspecs)
    if depends:
        reason = unreadable_config(argv, state)
        if reason:
            return reason

    def checked_out():
        branch = state.branch.get(directory)
        if branch is None:
            branch = current_branch(directory)
        return branch

    remote = remote_given if remote_given is not None else (positional[0] if positional else None)
    if remote is not None:
        resolved = substitute(remote, state)
        if resolved is None and depends:
            return 'a git push to %s, a remote whose name is not known before the command runs, so where ' \
                   'its configuration sends the push cannot be told' % remote
        remote = resolved if resolved is not None else remote
    config = []                                 # read once, on first need

    def configuration():
        if not config:
            config.append(git_config(directory, git_overrides(argv)))
        return config[0]

    def judge(specs, typed, push_to=None):
        for spec in specs:
            resolved = substitute(spec, state)
            spec = resolved if resolved is not None else 'HEAD'    # an unknown $VAR or $( ): judged as HEAD
            spec = spec.lstrip('+')
            src, colon, dst = spec.partition(':')
            if not colon:
                dst = src
                if typed and src:                       # remote.<name>.push can send it elsewhere
                    branch = checked_out() if is_head(src) else None
                    branch = branch if isinstance(branch, str) else None
                    configured = configuration().get(
                        config_key('remote.%s.push' % push_remote(configuration(), branch, remote)))
                    mapped = mapped_destination(src, branch, configured or [], configuration())
                    if mapped is not None:
                        dst = mapped
            if colon and not src and not dst:           # ':' pushes matching branches
                if not has_local_protected(directory):
                    continue                            # no local main/master: matching cannot push one
                to = push_to or push_remote(configuration(), None, remote)
                elsewhere = pushes_elsewhere(configuration(), to)
                if elsewhere:
                    return 'git push of matching branches to %s, %s, so its tracking refs do not show what ' \
                           'main/master is there' % (to, elsewhere)
                target = matching_target(directory, to)
                if target:
                    return 'git push of matching branches, which updates %s on the remote' % target
                continue
            if is_head(dst):
                branch = checked_out()
                if branch is UNKNOWN or branch in PROTECTED:
                    return 'git push of HEAD while %s is checked out' % (
                        'main/master or an unknown branch' if branch is UNKNOWN else branch)
                continue
            target = protected_target(dst)
            if target:
                return 'git push %s %s' % ('--delete of' if deleting else 'to', target)
        return None

    reason = judge(refspecs, True)
    if reason or refspecs or tags:
        return reason
    branch = checked_out()
    if branch is UNKNOWN:
        return 'a bare git push right after a branch change, when the branch it pushes cannot be told'
    if branch in PROTECTED:
        return 'a bare git push while %s is checked out' % branch
    if branch is None and not configuration():
        return None                                     # not a repository: the push fails anyway
    target_remote = push_remote(configuration(), branch, remote)
    if config_bool(config_value(configuration(), 'remote.%s.mirror' % target_remote)):
        return 'a bare git push to %s, which remote.%s.mirror makes a push of every branch, main/master ' \
               'included' % (target_remote, target_remote)
    specs = implicit_destinations(configuration(), branch, target_remote, directory in state.started)
    if isinstance(specs, str):
        return specs
    reason = judge(specs, False, target_remote)
    if reason:
        return 'a bare git push whose configured destination is main/master (%s)' % reason
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

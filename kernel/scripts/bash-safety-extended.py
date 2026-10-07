#!/usr/bin/env python3
"""
bash-safety-extended.py - PreToolUse safety hook for the Bash, Monitor, Read and Grep tools.

Why it exists. Claude Code's permission rules match command TEXT, one subcommand at a time. They miss
the same action written another way: inside bash -c or eval, behind xargs or find -exec, through an
absolute or quoted command name, or as a relative path after a cd. This hook parses the command
(quotes, $VAR, ~, cd/pushd/popd, subshells, pipes, heredocs, functions), resolves every path argument
against the directory the command will really run in, and blocks a short list of high-value threats:

  secret reads    reading, copying, archiving, uploading or running inside a credential location
                  (CREDENTIAL_LOCATIONS below: ssh and gpg keys, cloud, cluster, registry and database
                  credentials, password stores, Claude Code's own login, also in a copy of ~/.claude
                  such as the install backup ~/.claude.bak-<date>, keychains, browser profiles;
                  public keys ~/.ssh/*.pub stay readable), and reading the VALUES of a hard env file
                  (.env, .env.local, every .env.*, .envrc), while .env.shared and templates
                  (.env.example, .env.sample, .env.template, .env.dist) stay readable
  self edits      Bash writes to the safety layer itself: ~/.claude/settings.json, settings.local.json
                  and ~/.claude/scripts/ (the Edit tool still works, behind a permission prompt), also
                  through unpacking whose file names the command does not show: an archive extracted
                  (tar, unzip, 7z, cpio, ditto), a diff applied (patch, git apply) or a site downloaded
                  into ~/.claude, a folder above it or the scripts folder; members named on the
                  command line that all land elsewhere pass
  lost work       git restore of the working tree, git checkout -f / of paths, git switch
                  --discard-changes, git stash drop / clear
  deletes         a recursive + forced rm anywhere in the command, find -delete over a whole tree
  overwrites      an mv, or a cp of a file, whose destination exists, or is a directory already
                  holding that name (cp -R of a folder, which merges into a folder, is not judged)
  whole-disk      a recursive search (grep -r, rg, ag, ack, the Grep tool) over /, a Windows drive,
  searches        the home folder or a folder above it, in any output mode (it reads every file)
  unread code     curl/wget output (or base64 -d / xxd -r output) piped into a shell or interpreter,
                  fed to bash -c / eval / source, or saved and run in the same command
  disk and host   raw disk writes, fork bombs, docker --privileged, docker mounts of /, of a folder
                  holding credentials, of a system folder or of the Docker socket
  hook bypasses   git commit --no-verify / -n anywhere in the command, git -c core.hooksPath=...
  hidden denies   sudo, recursive rm, chmod 777, force push and the other settings.json deny rules
                  when they hide where those rules cannot see them (bash -c, eval, xargs, find -exec,
                  env, wsl, an absolute or quoted command name, RM or rm.exe, git -C / git -c)
  PowerShell tool every call, when that tool is on: this hook reads bash, so a PowerShell command
                  would run unchecked (settings.json keeps the tool off; this is the second lock)
  Monitor tool    its command (a background watch; the tool exists only with telemetry on) is checked
                  exactly like a Bash command

How paths are judged
  - Start from the payload's `cwd`. Every cd, pushd, popd, `cd -`, bare `cd`, zsh-style bare directory,
    `env -C`, and `git -C` / `tar -C` moves the effective directory for the commands after it. A
    `( ... )` subshell, `$( ... )`, `<( ... )`, a background `&` job and every pipeline stage keep
    their changes to themselves (zsh runs the last stage in the current shell, so its changes count).
  - A directory change that may or may not have happened (after `&&` / `||`, inside if, case or a
    loop) makes the directory uncertain: relative paths are then judged by name AND against every
    directory it could be, so `cd ~/.aws; false && cd ~/proj; cat credentials` is still a read of
    ~/.aws/credentials.
  - Words are expanded the way the shell would: quotes removed, ~ and ~user, $HOME, ${HOME}, $PWD,
    $OLDPWD, variables assigned earlier in the same command (`D=~/.ssh; cat $D/key`), word splitting
    of unquoted expansions (`F='-r -f'; rm $F x`), positional parameters of bash -c and of shell
    functions, `for f in` lists, globs (against the real filesystem), simple {a,b} braces. Paths are
    normalized and resolved through symlinks; comparison is case-insensitive like the default macOS
    and Windows filesystems.
  - Windows (Git Bash). Every path is brought to one form before it is judged: C:\\Users\\me\\x,
    C:/Users/me/x and Git Bash's /c/Users/me/x are the same path, backslashes are separators, and
    $USERPROFILE, $APPDATA and $LOCALAPPDATA expand like $HOME. Credential locations hang off both
    HOME and USERPROFILE (Git Bash's HOME can differ from the profile folder), and the AppData ones
    also off APPDATA and LOCALAPPDATA (which can be redirected). A command name is matched without
    .exe and without case (`RM.exe -r` is rm -r hidden from the permission rules), also on macOS.
    Text handed to cmd /c or powershell -Command is checked like inline interpreter code, with
    %VAR% and $env:VAR expanded, plus the Windows recursive deletes (rd /s, del /s, Remove-Item
    -Recurse), disk tools (diskpart, format X:, Format-Volume) and download-and-run (irm ... | iex).
  - A part that cannot be known (an unset variable, a command substitution) is never guessed: the
    KNOWN part decides. A known directory prefix inside a credential location blocks (`~/.ssh/$F`), a
    known tail is judged by name (`$X/.ssh/id_rsa`, `$X/.env`), and a `$( )` or pipeline stage that
    named a credential location or a hard env file taints what it outputs
    (`find . -name .env | xargs cat`).
  - Text that becomes a command is analyzed as a command: bash -c (with its positional parameters),
    eval, watch, env -S, heredocs and here-strings fed to a shell, `echo '...' | sh`, sed's e command,
    a script written earlier in the same command and then run, and shell functions when called.
  - Options are read with each tool's own option table (which options take a value), so the operand
    that is really a file is the one judged: `grep -F KEY .env`, `sed -n '1r .env' x`, `xargs -a .env`.
  - Commands that only look at names or metadata (ls, stat, test, find without -exec, wc, ...) may name
    a credential location, and so may tools that USE a key without printing it (ssh, ssh-add,
    ssh-keygen, scp -i, kubectl --kubeconfig, gpg key management). Every other command that names
    one, or runs with its working directory inside one, is blocked.
  - Env files are referenced constantly as config, so only READING their values is blocked: readers
    (cat, grep, sed, base64, ...; grep -l / -c / -q print names or counts and pass), source / `.`,
    `< .env`, inline interpreter code that reads one, copies, archives or uploads of one under a
    non-env name, a recursive search over a folder that holds one, and an archive created from a
    folder that holds one at its top level (tar -c, zip -r, 7z a) without an exclude that covers it.

Decisions on bad input (deliberate)
  - Unreadable hook payload (not JSON): exit 1, a non-blocking error Claude Code shows to the user;
    the call runs. The payload comes from Claude Code, not from the model, so failing closed would
    only brick every call after an upgrade, and the visible notice still says the check is off.
  - A command the hook cannot analyse (it does not parse, it nests deeper than MAX_NEST or MAX_DEPTH,
    it is longer than MAX_COMMAND_CHARS) and any internal error: exit 2, fail closed, with a message
    asking for simpler commands. The command text is written by the model, so a command must not be
    able to step around the analysis by being hard to read.

Output: exit 0 = allow; exit 2 = block, with the reason on stderr (shown to Claude). Python 3.9+,
standard library only.
"""
import copy
import fnmatch
import glob
import itertools
import json
import os
import posixpath
import re
import sys

SENT = '\x00'          # stands in for any part of a word whose value cannot be known
MAX_DEPTH = 8          # nesting limit for bash -c / eval / $( ) / function calls inside each other
MAX_NEST = 40          # nesting limit for ( ), { }, if, case and loops inside each other
MAX_COMMAND_CHARS = 1000000
MAX_GLOB = 2000        # cap on glob matches examined per word
MAX_PIECES = 24        # cap on path candidates derived from one argument
MAX_LISTING = 5000     # cap on directory entries examined per folder
MAX_SCRIPT_BYTES = 262144

HELPER = '~/.claude/scripts/list-env-keys.sh'
NO_WORKAROUND = ('Do not retry this or reach the same result another way (a different command, an '
                 'interpreter, an encoding, a script file, a copy). If the task really needs it, tell '
                 'the user what you wanted to run and why, and let them decide or run it themselves.')


class LazyPattern(object):
    """A regex compiled on first use. Most commands never reach the free-text checks, and compiling
    their large patterns up front would cost more than the rest of a typical run."""

    def __init__(self, pattern, flags=0):
        self._args, self._compiled = (pattern, flags), None

    def __getattr__(self, name):
        if self._compiled is None:
            self._compiled = re.compile(*self._args)
        return getattr(self._compiled, name)


class Block(Exception):
    def __init__(self, what, why, hint=None):
        Exception.__init__(self, what)
        self.what, self.why, self.hint = what, why, hint


class ParseError(Exception):
    pass


# ----------------------------------------------------------------------------------------------------
# Sensitive targets. CREDENTIAL_LOCATIONS is the single source of truth: settings.json mirrors it as
# Read deny rules (a test keeps the two in step), and the free-text marker regex is derived from it.
# ----------------------------------------------------------------------------------------------------
CREDENTIAL_LOCATIONS = [
    # keys, clouds and clusters
    '.ssh', '.gnupg', '.aws', '.azure', '.kube', '.config/gcloud', '.oci', '.config/doctl',
    '.docker/config.json', '.terraform.d/credentials.tfrc.json',
    # git hosts, package registries and API tokens
    '.config/gh', '.config/hub', '.git-credentials', '.netrc', '_netrc', '.npmrc', '.pypirc',
    '.gem/credentials', '.cargo/credentials', '.cargo/credentials.toml', '.m2/settings.xml',
    '.m2/settings-security.xml', '.gradle/gradle.properties', '.cache/huggingface/token',
    '.huggingface/token', '.vault-token',
    # databases and storage
    '.pgpass', '.my.cnf', '.s3cfg', '.boto', '.config/rclone',
    # password managers, keyrings and Claude Code's own login
    '.password-store', '.config/op', '.op', '.local/share/keyrings', '.claude/.credentials.json',
    # macOS keychains and cookies, browser profiles
    'Library/Keychains', 'Library/Cookies', 'Library/Safari',
    'Library/Application Support/Google/Chrome', 'Library/Application Support/Chromium',
    'Library/Application Support/Firefox', 'Library/Application Support/BraveSoftware',
    'Library/Application Support/Microsoft Edge', 'Library/Application Support/Arc',
    '.mozilla', '.config/google-chrome', '.config/chromium', '.config/BraveSoftware',
    '.config/microsoft-edge',
    # Windows: the same tools keep their files under AppData instead (the dot-folders above, .ssh,
    # .aws, .kube, .docker, .npmrc and the rest, sit in the user profile on Windows too), the
    # Credential Manager and DPAPI key stores, and browser profiles
    'AppData/Roaming/gcloud', 'AppData/Roaming/GitHub CLI', 'AppData/Roaming/doctl',
    'AppData/Roaming/rclone', 'AppData/Roaming/gnupg', 'AppData/Roaming/terraform.d/credentials.tfrc.json',
    'AppData/Roaming/postgresql/pgpass.conf', 'AppData/Roaming/MySQL/.mylogin.cnf',
    'AppData/Roaming/s3cmd.ini', 'AppData/Roaming/Microsoft/Credentials', 'AppData/Local/Microsoft/Credentials',
    'AppData/Roaming/Microsoft/Protect', 'AppData/Roaming/Microsoft/Crypto', 'AppData/Local/Microsoft/Vault',
    'AppData/Local/Google/Chrome/User Data', 'AppData/Local/Microsoft/Edge/User Data',
    'AppData/Local/BraveSoftware/Brave-Browser/User Data', 'AppData/Local/Chromium/User Data',
    'AppData/Roaming/Mozilla/Firefox', 'AppData/Roaming/Opera Software',
]
# Folders among them: settings.json denies these as Read(~/<entry>/**), the files as Read(~/<entry>).
CREDENTIAL_DIRS = {
    '.ssh', '.gnupg', '.aws', '.azure', '.kube', '.config/gcloud', '.oci', '.config/doctl', '.config/gh',
    '.config/rclone', '.password-store', '.config/op', '.op', '.local/share/keyrings',
    'Library/Keychains', 'Library/Cookies', 'Library/Safari', 'Library/Application Support/Google/Chrome',
    'Library/Application Support/Chromium', 'Library/Application Support/Firefox',
    'Library/Application Support/BraveSoftware', 'Library/Application Support/Microsoft Edge',
    'Library/Application Support/Arc', '.mozilla', '.config/google-chrome', '.config/chromium',
    '.config/BraveSoftware', '.config/microsoft-edge',
    'AppData/Roaming/gcloud', 'AppData/Roaming/GitHub CLI', 'AppData/Roaming/doctl', 'AppData/Roaming/rclone',
    'AppData/Roaming/gnupg', 'AppData/Roaming/Microsoft/Credentials', 'AppData/Local/Microsoft/Credentials',
    'AppData/Roaming/Microsoft/Protect', 'AppData/Roaming/Microsoft/Crypto', 'AppData/Local/Microsoft/Vault',
    'AppData/Local/Google/Chrome/User Data', 'AppData/Local/Microsoft/Edge/User Data',
    'AppData/Local/BraveSoftware/Brave-Browser/User Data', 'AppData/Local/Chromium/User Data',
    'AppData/Roaming/Mozilla/Firefox', 'AppData/Roaming/Opera Software',
}
# Windows can move AppData off the profile folder; these entries are also anchored at the variable.
APPDATA_VARS = (('AppData/Roaming/', 'APPDATA'), ('AppData/Local/', 'LOCALAPPDATA'))
# A credential FILE whose folder stays ordinary: a recursive copy of ~/.claude (the installer's backup)
# passes, while reading the file, or a recursive search or archive of the folder that holds it, is
# blocked.
FILE_ONLY = {'.claude/.credentials.json'}
# Judged only under the home folder, never by name elsewhere: projects keep their own .npmrc.
HOME_ONLY = {'.npmrc'}
KEY_FILE_NAMES = {'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519', 'id_ecdsa_sk', 'id_ed25519_sk'}
SECRET_SUFFIXES = ('.keychain', '.keychain-db')
# Recognized by name anywhere on disk (a copy, another user's home, a container path).
NAME_SEQUENCES = [tuple(loc.lower().split('/')) for loc in CREDENTIAL_LOCATIONS
                  if loc not in HOME_ONLY and not loc.startswith('Library/')]
NAME_SEQUENCES_BY_FIRST = {}
for _seq in NAME_SEQUENCES:
    NAME_SEQUENCES_BY_FIRST.setdefault(_seq[0], []).append(_seq)
# Claude Code's own credential files (the .claude/ entries above) count inside every copy of the config
# folder too, recognized by a folder name that starts with .claude: the install backup
# ~/.claude.bak-<date>, ~/.claude.pack-removed-<date>, a hand-made ~/.claude-old. Like ~/.claude itself,
# the copy stays an ordinary folder: listing it or copying it whole passes.
CONFIG_PREFIX = '.claude'
CONFIG_COPY_TAILS = [tuple(loc.lower().split('/')[1:]) for loc in CREDENTIAL_LOCATIONS
                     if loc.lower().startswith(CONFIG_PREFIX + '/')]

ENV_SOFT_EXACT = {'.env.shared'}
ENV_SOFT_SUFFIX = ('.example', '.sample', '.template', '.dist')


def _text_marker(loc):
    parts = [re.escape(p) for p in loc.split('/')]
    if loc.lower().startswith(CONFIG_PREFIX + '/'):
        parts[0] += r'[\w.-]*'                         # and every copy of the config folder
    return r'[/\\]+'.join(parts)


# The same markers, searched in free text (inline interpreter code, awk programs): each location as a
# whole path segment, with / or \ (or a doubled \\, as in a string literal) between its parts.
TEXT_SECRET_RE = LazyPattern(
    r'(?<![\w.-])(?:'
    + '|'.join(_text_marker(loc) for loc in CREDENTIAL_LOCATIONS)
    + r')(?![\w.-])|(?<![\w.-])id_(?:rsa|dsa|ecdsa|ed25519)(?:_sk)?(?![\w-])(?!\.pub)', re.IGNORECASE)
TEXT_ENV_RE = LazyPattern(r"""(?:^|[\s'"=:(<>|&;,/`])(\.env(?:rc)?(?:\.[A-Za-z0-9_-]+)*)(?![\w./-])""",
                          re.IGNORECASE)
# Inline code that names a hard env file is blocked only when it also reads, runs or copies something;
# print(".env must stay out of git") passes.
CODE_READ_RE = LazyPattern(
    r'\b(?:open|fopen|read\w*|Read\w*|load\w*|Load\w*|dotenv|parse\w*|Parse\w*|File|file_get_contents'
    r'|fileinput|IO|Path|fs|Deno|Bun|slurp|getline|system|popen|exec\w*|spawn\w*|subprocess'
    r'|check_output|getoutput|shell_exec|passthru|copy\w*|cat|source|upload\w*|urlopen|curl|wget)\b|`')
TEXT_RMTREE_RE = LazyPattern(r'\b(?:rmtree|remove_tree|rm_rf)\s*\(|\brm(?:Sync)?\s*\([^)]*recursive\s*:\s*true'
                             r'|\bFileUtils\.rm_rf\b')
CODE_WRITE_RE = LazyPattern(
    r"""\b(?:write\w*|Write\w*|dump\w*|unlink\w*|remove\w*|rmtree|rename\w*|replace|chmod\w*|truncate\w*"""
    r"""|copy\w*|move|symlink\w*|appendFile\w*|rmSync|createWriteStream|system|popen|exec\w*|spawn\w*"""
    r"""|subprocess)\b|\bopen\s*\([^,)]*,\s*['"][rbt]*[wax+]|['"]\s*>""")
# Inline code that unpacks an archive or copies a whole tree (tarfile/zipfile extractall,
# shutil.unpack_archive / copytree, fs.cpSync): judged together with CONFIG_TEXT_RE.
CODE_UNPACK_RE = LazyPattern(r'\b(extract\w*|unpack_archive|copytree|cpSync|cp)\s*\(')

# Raw disks: /dev/... (Git Bash maps /dev/sda to the first physical drive too), and Windows' own
# \\.\PhysicalDrive0, \\.\Harddisk0... and \\.\C: (a whole volume).
BLOCK_DEVICE_RE = LazyPattern(
    r'^(?:/dev/(?:r?disk\d|sd[a-z]|hd[a-z]|vd[a-z]|xvd[a-z]|nvme\d|mmcblk\d|md\d|dm-\d|mapper/|loop\d)'
    r'|[/\\]{2}[.?][/\\](?:PhysicalDrive\d|Harddisk\d|[A-Za-z]:$))',
    re.IGNORECASE)

# Windows: the cmd /c and powershell -Command text that matters beyond what inline code checks.
WIN_SHELLS = {'cmd', 'powershell', 'pwsh'}
WIN_VAR_RE = re.compile(r'%([A-Za-z_][A-Za-z0-9_()]*)%|\$\{?env:([A-Za-z_][A-Za-z0-9_()]*)\}?', re.IGNORECASE)
WIN_READ_RE = LazyPattern(
    r'\b(?:Get-Content|gc|type|more|Select-String|sls|findstr|find|Copy-Item|cpi|copy|xcopy|robocopy'
    r'|Import-\w+|Get-Item|gi|certutil|Invoke-WebRequest|iwr|Invoke-RestMethod|irm|Compress-Archive|tar)\b',
    re.IGNORECASE)
WIN_RMTREE_RE = LazyPattern(
    r'\b(?:Remove-Item|ri|rm|rmdir|rd|del|erase)\b[^\n;|&]*?\s-r(?:e(?:c(?:u(?:r(?:s(?:e)?)?)?)?)?)?(?![\w-])'
    r'|\b(?:rd|rmdir|del|erase)\b[^\n;|&]*?\s/{1,2}s(?!\w)', re.IGNORECASE)
WIN_DISK_RE = LazyPattern(
    r'\b(?:diskpart|Format-Volume|Clear-Disk|Initialize-Disk|Remove-Partition)\b|\bformat(?:\.com)?\s+[A-Za-z]:',
    re.IGNORECASE)
WIN_FETCH_RE = LazyPattern(
    r'\b(?:Invoke-WebRequest|iwr|Invoke-RestMethod|irm|curl|wget|DownloadString|DownloadFile|Net\.WebClient'
    r'|Start-BitsTransfer|certutil)\b', re.IGNORECASE)
WIN_RUN_RE = LazyPattern(r'\b(?:Invoke-Expression|iex)\b', re.IGNORECASE)
WIN_PATH_TOKEN_RE = LazyPattern(r'(?:[A-Za-z]:)?[/\\][^\s\'"`|;&<>(){}]+')
WIN_WRITE_RE = LazyPattern(
    r'\b(?:Set-Content|sc|Add-Content|ac|Out-File|New-Item|ni|Copy-Item|cpi|copy|xcopy|Move-Item|mi|move'
    r'|Remove-Item|ri|del|erase|rd|rmdir|Rename-Item|rni|ren|Clear-Content|clc|echo)\b|>', re.IGNORECASE)
WIN_UNPACK_RE = LazyPattern(
    r'\b(?:Expand-Archive|ExtractToDirectory|robocopy|xcopy)\b|\btar(?:\.exe)?\s[^\n;|&]*?(?<![\w-])-[A-Za-z]*x',
    re.IGNORECASE)
# A config folder (or its scripts folder) named as a whole path in free text: .claude, .claude\scripts.
CONFIG_TEXT_RE = LazyPattern(r'(?<![\w.-])\.claude(?:[/\\]+scripts)?[/\\]*(?=[\s\'"`;|&),]|$)', re.IGNORECASE)


# ----------------------------------------------------------------------------------------------------
# Path dialect. Inside the hook every path has one form, Git Bash's: forward slashes and a drive as
# /c/... (C:\Users\me, C:/Users/me and /c/Users/me are one path). On macOS and Linux that is simply the
# path as written. File functions get the native form back from to_native() (C:/Users/me on Windows).
# Everything else (joining, normalizing, comparing) is plain POSIX string work, the same on every OS.
# ----------------------------------------------------------------------------------------------------
WINDOWS = sys.platform == 'win32'
MACOS = sys.platform == 'darwin'
FOLD_CASE = WINDOWS or MACOS                             # file systems that ignore case by default
DRIVE_RE = re.compile(r'^([A-Za-z]):(?=[/\\]|$)')
MSYS_DRIVE_RE = re.compile(r'^/(?:cygdrive/)?([A-Za-z])(?=/|$)')
WINDOWS_PROGRAM_SUFFIXES = ('.exe', '.com', '.bat', '.cmd')


def canon(path):
    """A path in the hook's form (see above). Unchanged on macOS and Linux."""
    if not WINDOWS or not path:
        return path
    p = path.replace('\\', '/')
    if p.startswith('//?/'):                                  # \\?\C:\... and \\?\UNC\server\share
        rest = p[4:]
        if DRIVE_RE.match(rest):
            p = rest
        elif rest[:4].lower() == 'unc/':
            p = '//' + rest[4:]
    m = DRIVE_RE.match(p)
    if m:
        return '/' + m.group(1).lower() + p[2:]
    m = MSYS_DRIVE_RE.match(p)
    if m:
        return '/' + m.group(1).lower() + p[m.end():]
    return p


def to_native(path):
    """What this system's file functions take for a path in the hook's form; None when there is no such
    path here: on Windows, a Git Bash root path such as /tmp, whose place depends on where Git is."""
    if not WINDOWS or not path:
        return path
    m = MSYS_DRIVE_RE.match(path)
    if m:
        return m.group(1).upper() + ':/' + path[m.end():].lstrip('/')
    if path.startswith('//') or not path.startswith('/'):
        return path
    return None


def _native_abs(path):
    native = to_native(path) if path else None
    return native if native and os.path.isabs(native) else None


def fs_isdir(path):
    native = _native_abs(path)
    return bool(native) and os.path.isdir(native)


def fs_isfile(path):
    native = _native_abs(path)
    return bool(native) and os.path.isfile(native)


def fs_islink(path):
    native = _native_abs(path)
    return bool(native) and os.path.islink(native)


def fs_lexists(path):
    native = _native_abs(path)
    return bool(native) and os.path.lexists(native)


def fs_samefile(a, b):
    na, nb = _native_abs(a), _native_abs(b)
    return bool(na and nb) and os.path.samefile(na, nb)


def fs_listdir(path):
    native = _native_abs(path)
    if not native:
        raise OSError('no such folder here: %s' % path)
    return os.listdir(native)


def fs_mtime(path):
    native = _native_abs(path)
    try:
        return os.stat(native).st_mtime if native else None
    except OSError:
        return None


def fs_realpath(path):
    native = _native_abs(path)
    return canon(os.path.realpath(native)) if native else None


def fs_glob(pattern):
    native = _native_abs(pattern)
    if not native:
        return []
    return [canon(m) for m in itertools.islice(glob.iglob(native), MAX_GLOB)]


def expand_user(text):
    """~ and ~user at the start of a path, in the hook's form."""
    return canon(os.path.expanduser(text)) if text.startswith('~') else text


def fold_name(name):
    """A command name the way the system finds the program: in any case on macOS and Windows (their
    file systems find /bin/rm when asked for RM), and without .exe / .com / .bat / .cmd on Windows."""
    if FOLD_CASE:
        name = name.lower()
    if WINDOWS:
        for suffix in WINDOWS_PROGRAM_SUFFIXES:
            if name.lower().endswith(suffix) and len(name) > len(suffix):
                return name[:-len(suffix)]
    return name


def shell_env():
    """The environment as the command sees it, with Windows paths ($USERPROFILE, $APPDATA, ...) in the
    hook's form."""
    env = dict(os.environ)
    if WINDOWS:
        for key, value in env.items():
            if ';' not in value and DRIVE_RE.match(value):
                env[key] = canon(value)
    return env


def expand_windows_vars(text, env):
    """%NAME% (cmd) and $env:NAME (PowerShell) replaced by their values, names in any case."""
    folded = dict((k.upper(), v) for k, v in env.items())

    def value(m):
        found = folded.get((m.group(1) or m.group(2)).upper())
        return found if found is not None else m.group(0)
    return WIN_VAR_RE.sub(value, text)


def _norm(p):
    return p.replace('\\', '/').lower()


def _homes():
    """Home folders in the hook's form: HOME, and on Windows also USERPROFILE (Git Bash's HOME can be
    set elsewhere, while Windows tools keep using the profile folder)."""
    out = []
    for name in (('HOME', 'USERPROFILE') if WINDOWS else ('HOME',)):
        value = os.environ.get(name)
        if value:
            home = posixpath.normpath(canon(value))
            if home not in out:
                out.append(home)
    return out or [canon(os.path.expanduser('~'))]


def _home():
    return _homes()[0]


def build_roots(homes):
    bases = []                                     # (folder, location relative to it, the location)
    for home in homes:
        for folder in (home, fs_realpath(home)):
            bases.extend((folder, sub, sub) for sub in CREDENTIAL_LOCATIONS if folder)
    if WINDOWS:
        for prefix, var in APPDATA_VARS:
            value = os.environ.get(var)
            if not value:
                continue
            for folder in (canon(value), fs_realpath(canon(value))):
                bases.extend((folder, sub[len(prefix):], sub) for sub in CREDENTIAL_LOCATIONS
                             if folder and sub.startswith(prefix))
    roots, file_roots = set(), set()
    for folder, rel, sub in bases:
        n = _norm(posixpath.normpath(posixpath.join(folder, rel)))
        roots.add(n)
        if sub in FILE_ONLY:
            file_roots.add(n)
    return roots, ancestors_of(roots - file_roots)


def ancestors_of(paths):
    """Every folder above the given (normalized) paths, up to /."""
    ancestors = set()
    for r in paths:
        d = r
        while True:
            parent = d.rsplit('/', 1)[0] or '/'
            if parent == d:
                break
            ancestors.add(parent)
            d = parent
            if d == '/':
                break
    return ancestors


ROOTS, ANCESTORS = build_roots(_homes())


def _search_norm(path):
    """A path compared as the file system compares it: in any case only on macOS and Windows (on Linux
    /tmp/HOME is not the home folder /tmp/home)."""
    p = path.replace('\\', '/').rstrip('/') or '/'
    return p.lower() if FOLD_CASE else p


def build_search_roots(homes):
    """Folders a recursive search must not start from: the file system root, each home folder, and
    every folder above one (/home, /Users, a Windows drive such as /c)."""
    folders = set()
    for home in homes:
        for folder in (home, fs_realpath(home)):
            if folder:
                folders.add(_search_norm(posixpath.normpath(folder)))
    return folders | ancestors_of(folders) | {'/'}


SEARCH_ROOTS = build_search_roots(_homes())


def is_search_root(path):
    """True for the whole disk (/, a Windows drive), a home folder, or a folder above one."""
    if not path:
        return False
    n = _search_norm(path)
    return n in SEARCH_ROOTS or (WINDOWS and re.match(r'^/[a-z]$', n) is not None)


def build_self_paths(homes):
    """The safety layer's own files, and the config folders that hold them."""
    configs = {posixpath.join(home, '.claude') for home in homes}
    if os.environ.get('CLAUDE_CONFIG_DIR'):
        configs.add(expand_user(canon(os.environ['CLAUDE_CONFIG_DIR'])))
    configs |= {fs_realpath(c) for c in configs} - {None}
    paths = set()
    for c in configs:
        for sub in ('settings.json', 'settings.local.json', 'scripts'):
            paths.add(_norm(posixpath.normpath(posixpath.join(c, sub))))
    return paths, {_norm(posixpath.normpath(c)) for c in configs}


SELF_PATHS, CONFIG_DIRS = build_self_paths(_homes())
CONFIG_ANCESTORS = ancestors_of(CONFIG_DIRS)
SELF_TEXT_RE = LazyPattern(r'\.claude[/\\](?:settings(?:\.local)?\.json|scripts)(?![\w.-])'
                           + ''.join('|' + re.escape(c) + r'[/\\](?:settings(?:\.local)?\.json|scripts)(?![\w.-])'
                                     for c in sorted(CONFIG_DIRS) if not c.endswith('/.claude')),
                           re.IGNORECASE)


def is_self(path):
    if not path:
        return False
    n = _norm(path).rstrip('/')
    return any(n == s or n.startswith(s + '/') for s in SELF_PATHS)


def is_config_dir(path):
    return bool(path) and _norm(path).rstrip('/') in CONFIG_DIRS


def unpack_target(path):
    """What unpacking into this folder can reach: 'self' inside the safety layer, 'config' for a config
    folder (an archive there may hold scripts/ or settings.json) or a folder above one (~, whose archive
    may hold .claude/scripts/), None otherwise."""
    if not path:
        return None
    if is_self(path):
        return 'self'
    n = _norm(path).rstrip('/') or '/'
    return 'config' if n in CONFIG_DIRS or n in CONFIG_ANCESTORS else None


def env_tier(base):
    """'hard' for a secret env file name, 'soft' for .env.shared and templates, None otherwise."""
    b = base.lower()
    if b == '.envrc':
        return 'hard'
    if b != '.env' and not b.startswith('.env.'):
        return None
    if b in ENV_SOFT_EXACT or b.endswith(ENV_SOFT_SUFFIX):
        return 'soft'
    return 'hard'


def pretty(path):
    if not path:
        return path
    path = path.replace(SENT, '<unknown>')
    home = _home().rstrip('/')
    if path == home or path.startswith(home + '/'):
        return '~' + path[len(home):]
    return path


class PathRef(object):
    """One candidate path: its text, absolute lexical form, realpath, and complete name segments."""
    __slots__ = ('text', 'lex', 'real', 'prefix', 'segments', 'base')

    def __init__(self, text, cwd):
        text, cwd = canon(text), canon(cwd)
        self.text = text
        self.lex = self.real = self.prefix = None
        if SENT in text:
            known = text.split(SENT, 1)[0]
            tail = text.rsplit(SENT, 1)[1]
            if '/' in known and (known.startswith('/') or cwd):
                d = known.rsplit('/', 1)[0] or '/'
                self.prefix = posixpath.normpath(d if d.startswith('/') else posixpath.join(cwd, d))
            segs = tail.replace('\\', '/').split('/')[1:] if '/' in tail else []
        else:
            p = text
            if not p.startswith('/') and cwd:
                p = posixpath.join(cwd, p)
            if p.startswith('/'):
                self.lex = posixpath.normpath(p)
                try:
                    self.real = fs_realpath(p)
                except (OSError, ValueError):
                    self.real = None
            segs = text.replace('\\', '/').split('/')
        self.segments = [s.lower() for s in segs if s and s != '.']
        self.base = self.segments[-1] if self.segments else ''

    def best(self):
        return self.real or self.lex or self.prefix or self.text


def _public_key(path_or_base, writing):
    return not writing and posixpath.basename(path_or_base.rstrip('/')).lower().endswith('.pub')


SPACE_RE = re.compile(r'\s')


def _names_secret(segs):
    for k, seg in enumerate(segs):
        for seq in NAME_SEQUENCES_BY_FIRST.get(seg, ()):
            if tuple(segs[k:k + len(seq)]) == seq:
                return True
    return _in_config_copy(segs)


def _in_config_copy(segs):
    """A credential file of Claude Code's inside a folder named .claude* (lowercase segments)."""
    for k, seg in enumerate(segs):
        if seg.startswith(CONFIG_PREFIX):
            for tail in CONFIG_COPY_TAILS:
                if tuple(segs[k + 1:k + 1 + len(tail)]) == tail:
                    return True
    return False


def classify(ref, writing=False):
    """('secret'|'env'|'ancestor', label) or None. A public key (*.pub) is not a secret to read; a
    symlink is judged by where it really points too."""
    for p in (ref.lex, ref.real, ref.prefix):
        if not p:
            continue
        if in_credential_location(p):
            if p is not ref.prefix and _public_key(p, writing):
                continue
            return ('secret', pretty(p))
    if not SPACE_RE.search(ref.text):
        if (_names_secret(ref.segments) or ref.base in KEY_FILE_NAMES or ref.base.endswith(SECRET_SUFFIXES)) \
                and not _public_key(ref.base, writing):
            return ('secret', pretty(ref.best()))
    names = [ref.base] + [posixpath.basename(p) for p in (ref.lex, ref.real) if p]
    for name in names:
        if name and env_tier(name) == 'hard':
            return ('env', pretty(ref.lex or ref.text))
    for p in (ref.lex, ref.real):
        if p and (_norm(p).rstrip('/') or '/') in ANCESTORS:
            return ('ancestor', pretty(p))
    return None


def in_credential_location(path):
    """True when the path is a listed location or lies below one (checked prefix by prefix), or is one of
    Claude Code's credential files in a copy of the config folder (CONFIG_COPY_TAILS)."""
    if not path:
        return False
    n = _norm(path).rstrip('/')
    if _in_config_copy(n.split('/')):
        return True
    while n:
        if n in ROOTS:
            return True
        cut = n.rfind('/')
        if cut <= 0:
            return False
        n = n[:cut]
    return False


# ----------------------------------------------------------------------------------------------------
# Lexer: shell text -> tokens. Words keep their parts so expansion can happen later, in order.
#   ('op', text) | ('word', Word) | ['redir', op, Word, heredoc_body]
# Word parts: ('lit', text, quoted) | ('var', name, quoted) | ('vardef', name, default, quoted)
#             | ('cmd', body, quoted) | ('proc', body) | ('posall', quoted, star) | ('unk', quoted)
# ----------------------------------------------------------------------------------------------------
class Word(object):
    __slots__ = ('parts', 'raw')

    def __init__(self, parts, raw):
        self.parts, self.raw = parts, raw

    def plain(self):
        """Text of an unquoted, fully literal word (keywords, braces), else None."""
        if len(self.parts) == 1 and self.parts[0][0] == 'lit' and not self.parts[0][2]:
            return self.parts[0][1]
        return None


REDIR_OPS = ('<<<', '<<-', '<<', '<>', '<&', '<', '>>', '>&', '>|', '>', '&>>', '&>')
LIST_OPS = ('&&', '||', ';;&', ';;', ';&', '|&', '&', '|', ';', '(', ')')
NAME_RE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
HEREDOC_RE = re.compile(r"""<<(-?)[ \t]*(?:'([^'\n]*)'|"([^"\n]*)"|\\?([^\s'"();&|<>]+))""")
WORD_START = ' \t\n;|&('


def skip_double_quote(s, j):
    """s[j] is an opening double quote; return the index after its closing quote."""
    j += 1
    n = len(s)
    while j < n:
        c = s[j]
        if c == '\\':
            j += 2
            continue
        if c == '"':
            return j + 1
        if c == '$' and j + 1 < n and s[j + 1] == '(':
            j = find_close_paren(s, j + 2) + 1
            continue
        if c == '`':
            j = skip_backtick(s, j)
            continue
        j += 1
    raise ParseError('unterminated double quote')


def skip_backtick(s, j):
    k = j + 1
    while k < len(s):
        if s[k] == '\\':
            k += 2
            continue
        if s[k] == '`':
            return k + 1
        k += 1
    raise ParseError('unterminated backtick')


def find_close_paren(s, j):
    """j is just past an opening '('; return the index of the matching ')'. Knows quotes, comments,
    heredocs (whose bodies may hold unbalanced quotes) and case patterns (whose ')' closes nothing)."""
    depth = 1
    n = len(s)
    heredocs = []
    cases = []
    while j < n:
        c = s[j]
        if c == '\\':
            j += 2
            continue
        if c == "'":
            k = s.find("'", j + 1)
            if k < 0:
                raise ParseError('unterminated single quote')
            j = k + 1
            continue
        if c == '"':
            j = skip_double_quote(s, j)
            continue
        if c == '`':
            j = skip_backtick(s, j)
            continue
        if c == '#' and (j == 0 or s[j - 1] in ' \t\n;|&('):
            k = s.find('\n', j)
            j = n if k < 0 else k
            continue
        if c == '<' and s.startswith('<<', j) and not s.startswith('<<<', j):
            m = HEREDOC_RE.match(s, j)
            if m:
                delim = next(g for g in m.groups()[1:] if g is not None)
                heredocs.append((delim, m.group(1) == '-'))
                j = m.end()
                continue
        if c == '\n' and heredocs:
            j += 1
            for delim, strip_tabs in heredocs:
                while j < n:
                    k = s.find('\n', j)
                    line = s[j:] if k < 0 else s[j:k]
                    j = n if k < 0 else k + 1
                    if (line.lstrip('\t') if strip_tabs else line) == delim:
                        break
            heredocs = []
            continue
        if c.isalpha() and (j == 0 or s[j - 1] in WORD_START):
            m = re.match(r'(case|esac)(?=[\s;&|)]|$)', s[j:j + 5])
            if m and m.group(1) == 'case':
                cases.append(depth)
            elif m and cases:
                cases.pop()
            j += len(m.group(1)) if m else 1
            continue
        if c == '(':
            depth += 1
        elif c == ')':
            if cases and depth == cases[-1]:
                j += 1                                              # a case pattern's ')'
                continue
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ParseError('unbalanced parenthesis')


def substitution_bodies(text):
    """Bodies of $( ) and backtick substitutions in free text (an unquoted heredoc body)."""
    out = []
    i = 0
    while i < len(text):
        if text.startswith('$((', i):
            i = find_close_paren(text, i + 2) + 1
            continue
        if text.startswith('$(', i):
            end = find_close_paren(text, i + 2)
            out.append(text[i + 2:end])
            i = end + 1
            continue
        if text[i] == '`':
            end = skip_backtick(text, i)
            out.append(text[i + 1:end - 1])
            i = end
            continue
        if text[i] == '\\':
            i += 2
            continue
        i += 1
    return out


class Lexer(object):
    def __init__(self, src):
        self.s, self.i, self.n = src, 0, len(src)
        self.tokens = []
        self.heredocs = []

    def run(self):
        s = self.s
        while self.i < self.n:
            c = s[self.i]
            if c in ' \t\r':
                self.i += 1
            elif s.startswith('\\\n', self.i):
                self.i += 2
            elif c == '\n':
                self.tokens.append(('op', '\n'))
                self.i += 1
                self.read_heredoc_bodies()
            elif c == '#':
                k = s.find('\n', self.i)
                self.i = self.n if k < 0 else k
            elif s.startswith(('<(', '>('), self.i):
                self.tokens.append(('word', self.read_word()))
            elif self.at_redirect():
                self.read_redirect()
            elif c in '|&;()':
                for op in LIST_OPS:
                    if s.startswith(op, self.i):
                        self.tokens.append(('op', op))
                        self.i += len(op)
                        break
            else:
                self.tokens.append(('word', self.read_word()))
        self.read_heredoc_bodies()
        return self.tokens

    def at_redirect(self):
        j = self.i
        while j < self.n and self.s[j].isdigit():
            j += 1
        if j < self.n and self.s[j] in '<>':
            return True
        return j == self.i and self.s.startswith('&>', j)

    def read_redirect(self):
        s = self.s
        while self.i < self.n and s[self.i].isdigit():
            self.i += 1
        op = None
        for candidate in REDIR_OPS:
            if s.startswith(candidate, self.i):
                op = candidate
                self.i += len(candidate)
                break
        while self.i < self.n and s[self.i] in ' \t':
            self.i += 1
        if self.i >= self.n or (s[self.i] in '\n|&;()<>' and not s.startswith(('<(', '>('), self.i)):
            raise ParseError('redirect without a target')
        target = self.read_word()
        tok = ['redir', op, target, None]
        if op in ('<<', '<<-'):
            delim = ''.join(p[1] for p in target.parts if p[0] == 'lit')
            quoted = any(p[0] == 'lit' and p[2] for p in target.parts)
            self.heredocs.append((tok, delim, op == '<<-', quoted))
        self.tokens.append(tok)

    def read_heredoc_bodies(self):
        s = self.s
        pending, self.heredocs = self.heredocs, []
        for tok, delim, strip_tabs, quoted in pending:
            lines = []
            while self.i < self.n:
                k = s.find('\n', self.i)
                line = s[self.i:] if k < 0 else s[self.i:k]
                self.i = self.n if k < 0 else k + 1
                check = line.lstrip('\t') if strip_tabs else line
                if check == delim:
                    break
                lines.append(check)
            tok[3] = ('\n'.join(lines), quoted)

    @staticmethod
    def add(parts, text, quoted):
        if parts and parts[-1][0] == 'lit' and parts[-1][2] == quoted:
            parts[-1] = ('lit', parts[-1][1] + text, quoted)
        else:
            parts.append(('lit', text, quoted))

    def read_word(self):
        s, start, parts = self.s, self.i, []
        while self.i < self.n:
            c = s[self.i]
            if c in ' \t\r\n|&;)(':
                break
            if c in '<>':
                if s.startswith(('<(', '>('), self.i):
                    end = find_close_paren(s, self.i + 2)
                    parts.append(('proc', s[self.i + 2:end]))
                    self.i = end + 1
                    continue
                break
            if c == '\\':
                if self.i + 1 < self.n and s[self.i + 1] != '\n':
                    self.add(parts, s[self.i + 1], True)
                self.i += 2
                continue
            if c == "'":
                k = s.find("'", self.i + 1)
                if k < 0:
                    raise ParseError('unterminated single quote')
                self.add(parts, s[self.i + 1:k], True)
                self.i = k + 1
                continue
            if c == '"':
                self.read_double_quoted(parts)
                continue
            if c == '$':
                self.read_dollar(parts, False)
                continue
            if c == '`':
                end = skip_backtick(s, self.i)
                parts.append(('cmd', s[self.i + 1:end - 1].replace('\\`', '`'), False))
                self.i = end
                continue
            self.add(parts, c, False)
            self.i += 1
        return Word(parts, s[start:self.i])

    def read_double_quoted(self, parts):
        s = self.s
        self.i += 1
        start = len(parts)
        while True:
            if self.i >= self.n:
                raise ParseError('unterminated double quote')
            c = s[self.i]
            if c == '"':
                self.i += 1
                if len(parts) == start:
                    self.add(parts, '', True)
                return
            if c == '\\' and self.i + 1 < self.n:
                nxt = s[self.i + 1]
                if nxt in '$`"\\':
                    self.add(parts, nxt, True)
                elif nxt != '\n':
                    self.add(parts, '\\' + nxt, True)
                self.i += 2
                continue
            if c == '$':
                self.read_dollar(parts, True)
                continue
            if c == '`':
                end = skip_backtick(s, self.i)
                parts.append(('cmd', s[self.i + 1:end - 1].replace('\\`', '`'), True))
                self.i = end
                continue
            self.add(parts, c, True)
            self.i += 1

    def read_dollar(self, parts, quoted):
        s, i = self.s, self.i
        nxt = s[i + 1] if i + 1 < self.n else ''
        if nxt == '(':
            end = find_close_paren(s, i + 2)
            body = s[i + 2:end]
            parts.append(('unk', quoted) if body.startswith('(') else ('cmd', body, quoted))
            self.i = end + 1
            return
        if nxt == '{':
            depth, j = 1, i + 2                                 # like bash: only a nested ${ opens a level
            while j < self.n and depth:
                c = s[j]
                if c == '\\':
                    j += 2
                    continue
                if c == "'" and not quoted:
                    k = s.find("'", j + 1)
                    j = self.n if k < 0 else k + 1
                    continue
                if c == '"':
                    j = skip_double_quote(s, j)
                    continue
                if s.startswith('$(', j):
                    j = find_close_paren(s, j + 2) + 1
                    continue
                if s.startswith('${', j):
                    depth += 1
                    j += 2
                    continue
                if c == '}':
                    depth -= 1
                j += 1
            if depth:
                raise ParseError('unterminated ${')
            inner = s[i + 2:j - 1]
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*|\d+)(?::?[-=](.*))?$', inner, re.S)
            if inner in ('@', '*'):
                parts.append(('posall', quoted, inner == '*'))
            elif m and m.group(2) is None:
                parts.append(('var', m.group(1), quoted))
            elif m:
                parts.append(('vardef', m.group(1), m.group(2), quoted))
            else:
                parts.append(('unk', quoted))
            self.i = j
            return
        if nxt == "'" and not quoted:
            j, buf = i + 2, []
            escapes = {'n': '\n', 't': '\t', '\\': '\\', "'": "'", '"': '"', 'e': '\x1b', 'a': '\a'}
            while j < self.n and s[j] != "'":
                if s[j] == '\\' and j + 1 < self.n:
                    buf.append(escapes.get(s[j + 1], '\\' + s[j + 1]))
                    j += 2
                    continue
                buf.append(s[j])
                j += 1
            if j >= self.n:
                raise ParseError("unterminated $'")
            self.add(parts, ''.join(buf), True)
            self.i = j + 1
            return
        if nxt == '"' and not quoted:
            self.i += 1
            self.read_double_quoted(parts)
            return
        m = NAME_RE.match(s, i + 1)
        if m:
            parts.append(('var', m.group(0), quoted))
            self.i = m.end()
            return
        if nxt and nxt in '0123456789':
            parts.append(('var', nxt, quoted))
            self.i = i + 2
            return
        if nxt in ('@', '*'):
            parts.append(('posall', quoted, nxt == '*'))
            self.i = i + 2
            return
        if nxt and nxt in '#?$!-':
            parts.append(('unk', quoted))
            self.i = i + 2
            return
        self.add(parts, '$', quoted)
        self.i = i + 1


# ----------------------------------------------------------------------------------------------------
# Parser: tokens -> a small tree.
#   ('list', [('andor', [(op, pipeline), ...], background), ...])   op: None for the first, && or ||
#   ('pipeline', [command...]) ('simple', words, redirs) ('subshell', list, redirs)
#   ('group', list, redirs, kind) ('for', var, items, list, redirs) ('function', name, command)
# ----------------------------------------------------------------------------------------------------
LIST_SEPS = (';', '&', '\n', ';;', ';&', ';;&')
PREFIX_KEYWORDS = ('then', 'else', 'elif', 'do', '!', 'time', 'coproc')


class Parser(object):
    def __init__(self, tokens):
        self.t, self.i, self.nest = tokens, 0, 0

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else None

    def is_op(self, tok, *ops):
        return tok is not None and tok[0] == 'op' and tok[1] in ops

    def is_kw(self, tok, *words):
        return tok is not None and tok[0] == 'word' and tok[1].plain() in words

    def enter(self):
        self.nest += 1
        if self.nest > MAX_NEST:
            raise ParseError('nested more than %d levels deep' % MAX_NEST)

    def parse(self):
        items = []
        while self.i < len(self.t):
            before = self.i
            items.extend(self.parse_list()[1])
            if self.i == before:
                self.i += 1
        return ('list', items)

    def parse_list(self, stop_words=(), stop_ops=()):
        items = []
        while True:
            tok = self.peek()
            if tok is None or self.is_op(tok, *stop_ops) or self.is_kw(tok, *stop_words):
                break
            if self.is_op(tok, *LIST_SEPS) or self.is_op(tok, ')', '&&', '||'):
                self.i += 1
                continue
            chain, op = [], None
            while True:
                before = self.i
                chain.append((op, self.parse_pipeline(stop_words, stop_ops)))
                if self.i == before:
                    self.i += 1
                if self.is_op(self.peek(), '&&', '||'):
                    op = self.peek()[1]
                    self.i += 1
                    while self.is_op(self.peek(), '\n'):
                        self.i += 1
                    tok = self.peek()
                    if tok is None or self.is_op(tok, *stop_ops) or self.is_kw(tok, *stop_words):
                        break
                    continue
                break
            items.append(('andor', chain, self.is_op(self.peek(), '&')))
        return ('list', items)

    def parse_pipeline(self, stop_words, stop_ops):
        cmds = [self.parse_command(stop_words, stop_ops)]
        while self.is_op(self.peek(), '|', '|&'):
            self.i += 1
            while self.is_op(self.peek(), '\n'):
                self.i += 1
            cmds.append(self.parse_command(stop_words, stop_ops))
        return ('pipeline', cmds)

    def expect(self, kind, text):
        tok = self.peek()
        if tok is not None and ((kind == 'op' and self.is_op(tok, text)) or (kind == 'kw' and self.is_kw(tok, text))):
            self.i += 1

    def redirects(self):
        out = []
        while self.peek() is not None and self.peek()[0] == 'redir':
            out.append(self.peek())
            self.i += 1
        return out

    def parse_command(self, stop_words, stop_ops):
        while self.is_kw(self.peek(), *PREFIX_KEYWORDS):
            self.i += 1
        tok = self.peek()
        self.enter()
        try:
            if self.is_op(tok, '('):
                self.i += 1
                body = self.parse_list(stop_ops=(')',))
                self.expect('op', ')')
                return ('subshell', body, self.redirects())
            if tok is not None and tok[0] == 'word':
                kw = tok[1].plain()
                closers = {'{': '}', 'if': 'fi', 'while': 'done', 'until': 'done'}
                if kw in closers:
                    self.i += 1
                    body = self.parse_list(stop_words=(closers[kw],))
                    self.expect('kw', closers[kw])
                    return ('group', body, self.redirects(), kw)
                if kw in ('for', 'select'):
                    self.i += 1
                    var, items = self.parse_for_header()
                    body = self.parse_list(stop_words=('done',))
                    self.expect('kw', 'done')
                    return ('for', var, items, body, self.redirects())
                if kw == 'case':
                    return self.parse_case()
                if kw == 'function':
                    self.i += 1
                    name = None
                    if self.peek() is not None and self.peek()[0] == 'word':
                        name = self.peek()[1].plain()
                        self.i += 1
                    if self.is_op(self.peek(), '(') and self.is_op(self.peek(1), ')'):
                        self.i += 2
                    while self.is_op(self.peek(), '\n'):
                        self.i += 1
                    return ('function', name, self.parse_command((), ()))
            return self.parse_simple()
        finally:
            self.nest -= 1

    def parse_for_header(self):
        if self.is_op(self.peek(), '('):
            depth = 0
            while self.peek() is not None:
                tok = self.peek()
                self.i += 1
                if self.is_op(tok, '('):
                    depth += 1
                elif self.is_op(tok, ')'):
                    depth -= 1
                    if depth <= 0:
                        break
            var, items = None, []
        else:
            tok = self.peek()
            var = tok[1].plain() if tok is not None and tok[0] == 'word' else None
            if tok is not None and tok[0] == 'word':
                self.i += 1
            items = []
            if self.is_kw(self.peek(), 'in'):
                self.i += 1
                while self.peek() is not None and self.peek()[0] == 'word' and not self.is_kw(self.peek(), 'do'):
                    items.append(self.peek()[1])
                    self.i += 1
        while self.is_op(self.peek(), ';', '\n'):
            self.i += 1
        if self.is_kw(self.peek(), 'do'):
            self.i += 1
        return var, items

    def parse_case(self):
        self.i += 1
        if self.peek() is not None and self.peek()[0] == 'word':
            self.i += 1
        while self.is_op(self.peek(), '\n'):
            self.i += 1
        self.expect('kw', 'in')
        items = []
        while self.peek() is not None:
            while self.is_op(self.peek(), '\n', ';'):
                self.i += 1
            if self.peek() is None:
                break
            if self.is_kw(self.peek(), 'esac'):
                self.i += 1
                break
            before = self.i
            if self.is_op(self.peek(), '('):
                self.i += 1
            while self.peek() is not None and not self.is_op(self.peek(), ')') and not self.is_kw(self.peek(), 'esac'):
                self.i += 1
            self.expect('op', ')')
            body = self.parse_list(stop_words=('esac',), stop_ops=(';;', ';&', ';;&'))
            items.extend(body[1])
            if self.is_op(self.peek(), ';;', ';&', ';;&'):
                self.i += 1
            if self.i == before:
                self.i += 1
        return ('group', ('list', items), self.redirects(), 'case')

    def parse_simple(self):
        words, redirs = [], []
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok[0] == 'word':
                words.append(tok[1])
                self.i += 1
            elif tok[0] == 'redir':
                redirs.append(tok)
                self.i += 1
            elif self.is_op(tok, '(') and words:
                if self.is_op(self.peek(1), ')'):                      # name() { body; }
                    self.i += 2
                    while self.is_op(self.peek(), '\n'):
                        self.i += 1
                    return ('function', words[-1].plain(), self.parse_command((), ()))
                self.i += 1                                             # arr=(a b) and the like
                self.parse_list(stop_ops=(')',))
                self.expect('op', ')')
                words.append(Word([('unk', False)], '(...)'))
            else:
                break
        return ('simple', words, redirs)


# ----------------------------------------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------------------------------------
class Ctx(object):
    """Shell state for one command string. cwd is None when unknown; maybe then lists the directories
    it could be (None among them when one possibility is unknown)."""

    def __init__(self, cwd, env):
        self.cwd = cwd
        self.maybe = ()
        self.env = env
        self.oldpwd = env.get('OLDPWD') or None
        self.dirstack = []
        self.vars = {}
        self.positional = None      # [$0, $1, ...] of this shell or function; None = unknown
        self.functions = {}
        self.calls = ()
        self.downloads = set()      # files on disk: shared with sub-contexts on purpose
        self.created = set()
        self.written = {}           # file -> text that echo/printf/cat <<EOF wrote into it

    def copy(self):
        c = copy.copy(self)
        c.vars = dict(self.vars)
        c.dirstack = list(self.dirstack)
        c.functions = dict(self.functions)
        return c

    def lookup(self, name):
        if name.isdigit():
            if self.positional is None:
                return None
            k = int(name)
            return self.positional[k] if k < len(self.positional) else ''
        if name in self.vars:
            return self.vars[name]
        if name == 'PWD':
            return self.cwd
        if name == 'OLDPWD':
            return self.oldpwd
        return self.env.get(name)

    def home(self):
        h = self.lookup('HOME')
        return h if h else _home()


def cwd_opts(ctx):
    """Every directory the shell could be in; None stands for an unknown one."""
    return [ctx.cwd] if ctx.cwd is not None else (list(ctx.maybe) or [None])


def set_cwd_opts(ctx, options):
    distinct = []
    for o in options:
        if o not in distinct:
            distinct.append(o)
    if len(distinct) == 1 and distinct[0] is not None:
        ctx.cwd, ctx.maybe = distinct[0], ()
    else:
        ctx.cwd, ctx.maybe = None, tuple(distinct[:8])


class Info(object):
    """What a command (or subshell, or pipeline stage) did that later stages care about."""
    __slots__ = ('downloader', 'sensitive', 'script')

    def __init__(self):
        self.downloader = False   # writes unread code to stdout: a download, or base64 -d and friends
        self.sensitive = None     # a secret or hard env path it named without reading it (ls, find)
        self.script = None        # the text echo/printf print, in case the next stage runs it

    def merge(self, other):
        self.downloader = self.downloader or other.downloader
        self.sensitive = self.sensitive or other.sensitive
        self.script = other.script if other.script is not None else self.script
        return self


class Stdin(object):
    __slots__ = ('downloaded', 'taint', 'heredoc')

    def __init__(self, downloaded=False, taint=None, heredoc=None):
        self.downloaded, self.taint, self.heredoc = downloaded, taint, heredoc


class Arg(object):
    """An expanded word (one field)."""
    __slots__ = ('text', 'globby', 'quoted', 'assign', 'dl_sub', 'sub_sensitive', 'raw')

    def __init__(self):
        self.text, self.globby, self.quoted, self.assign = '', False, False, None
        self.dl_sub, self.sub_sensitive, self.raw = False, None, ''

    @property
    def unknown(self):
        return SENT in self.text


def make_arg(text):
    a = Arg()
    a.text = a.raw = text
    return a


class Fields(object):
    """Builds the fields of one word: an unquoted expansion splits on blanks, "$@" on parameters."""

    def __init__(self, raw):
        self.raw, self.out = raw, []
        self.reset()

    def reset(self):
        self.buf, self.has, self.globby, self.quoted, self.dl, self.sens = [], False, False, False, False, None

    def add(self, text, quoted=False, globby=False):
        self.buf.append(text)
        self.has = True
        self.quoted = self.quoted or quoted
        self.globby = self.globby or globby

    def end(self):
        if self.has:
            a = Arg()
            a.text, a.raw = ''.join(self.buf), self.raw
            a.globby, a.quoted, a.dl_sub, a.sub_sensitive = self.globby, self.quoted, self.dl, self.sens
            self.out.append(a)
        self.reset()

    def split_in(self, value):
        for k, piece in enumerate(re.split(r'[ \t\n]+', value)):
            if k:
                self.end()
            if piece:
                self.add(piece, globby=any(c in piece for c in '*?['))


def tilde(text, ctx):
    if not text.startswith('~'):
        return text
    head, sep, rest = text.partition('/')
    if head == '~':
        base = ctx.home()
    elif head == '~+':
        base = ctx.cwd or SENT
    elif head == '~-':
        base = ctx.oldpwd or SENT
    else:
        base = expand_user(head)
        if base == head:
            return text
    return base + sep + rest


class Evaluator(object):
    def __init__(self, depth=0):
        self.depth = depth

    # ---- expansion ----------------------------------------------------------------------------
    def expand(self, word, ctx):
        """The fields a word expands to: usually one, none for an unquoted empty variable, several
        when an unquoted expansion holds blanks or "$@" holds several parameters."""
        parts = word.parts
        first = parts[0] if parts else None
        assign = None
        if first is not None and first[0] == 'lit' and not first[2]:
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=', first[1])
            if m:
                assign = m.group(1)
        f = Fields(word.raw)
        for idx, part in enumerate(parts):
            kind = part[0]
            if kind == 'lit':
                text, quoted = part[1], part[2]
                if not quoted and idx == 0:
                    m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', text, re.S)
                    text = m.group(1) + '=' + tilde(m.group(2), ctx) if m else tilde(text, ctx)
                f.add(text, quoted, not quoted and any(ch in text for ch in '*?['))
            elif kind in ('var', 'vardef'):
                v = ctx.lookup(part[1])
                if kind == 'vardef' and not v:
                    default = part[2]
                    v = tilde(default, ctx) if '$' not in default and '`' not in default else None
                quoted = part[-1]
                if v is None:
                    f.add(SENT, quoted)
                elif quoted or assign:
                    f.add(v, True)
                else:
                    f.split_in(v)
            elif kind == 'posall':
                quoted, star = part[1], part[2]
                if ctx.positional is None:
                    f.add(SENT, quoted)
                    continue
                params = [p if p is not None else SENT for p in ctx.positional[1:]]
                if quoted and star or assign:
                    f.add(' '.join(params), True)
                elif quoted:
                    for k, p in enumerate(params):
                        if k:
                            f.end()
                        f.add(p, True)
                else:
                    for k, p in enumerate(params):
                        if k:
                            f.end()
                        f.split_in(p)
            elif kind in ('cmd', 'proc'):
                info = self.run_string(part[1], ctx.copy(), wrapped=False)
                f.dl = f.dl or info.downloader
                f.sens = f.sens or info.sensitive
                f.add(SENT, kind == 'cmd' and part[2])
            else:
                f.add(SENT, len(part) > 1 and part[1])
        f.end()
        if assign is not None and f.out:
            a = f.out[0]
            if len(f.out) > 1:                                      # an assignment never splits
                a.text = ' '.join(x.text for x in f.out)
                f.out = [a]
            value = a.text[len(assign) + 1:]
            a.assign = (assign, None if SENT in value else value)
        return f.out

    def expand1(self, word, ctx):
        fields = self.expand(word, ctx)
        return fields[0] if fields else make_arg('')

    # ---- entry points -------------------------------------------------------------------------
    def run_string(self, text, ctx, wrapped):
        """Analyze a command string (the top level, or the body of bash -c / eval / $( ))."""
        if self.depth >= MAX_DEPTH:
            raise ParseError('more than %d levels of bash -c, eval, $( ) and function calls inside '
                             'each other' % MAX_DEPTH)
        child = Evaluator(self.depth + 1)
        tree = Parser(Lexer(text).run()).parse()
        return child.node(tree, ctx, None, wrapped)

    def node(self, n, ctx, stdin, wrapped):
        kind = n[0]
        if kind == 'list':
            info = Info()
            for item in n[1]:
                info.merge(self.andor(item, ctx, stdin, wrapped))
            return info
        if kind == 'pipeline':
            cmds = n[1]
            if len(cmds) == 1:
                return self.node(cmds[0], ctx, stdin, wrapped)
            info, cur, last, stage = Info(), stdin, None, ctx
            for k, cmd in enumerate(cmds):
                if k:
                    cur = Stdin(downloaded=info.downloader, taint=info.sensitive, heredoc=last.script)
                stage = ctx.copy()                              # every stage is a subshell...
                last = self.node(cmd, stage, cur, wrapped)
                info.merge(last)
            set_cwd_opts(ctx, cwd_opts(ctx) + cwd_opts(stage))  # ...except zsh's last one
            for name, value in stage.vars.items():
                ctx.vars[name] = value
            return info
        if kind == 'subshell':
            sub = ctx.copy()
            own = self.redirects(n[2], sub, [], None, stdin)
            return self.node(n[1], sub, own or stdin, wrapped)
        if kind == 'group':
            own = self.redirects(n[2], ctx, [], None, stdin)
            if n[3] == '{':
                return self.node(n[1], ctx, own or stdin, wrapped)
            return self.uncertain(n[1][1], ctx, own or stdin, wrapped)       # if, case, while, until
        if kind == 'for':
            _, var, items, body, redirs = n
            if var:
                ctx.vars[var] = self.representative(items, ctx)
            own = self.redirects(redirs, ctx, [], None, stdin)
            return self.uncertain(body[1], ctx, own or stdin, wrapped)
        if kind == 'function':
            if n[1]:
                ctx.functions[n[1]] = n[2]
            probe = ctx.copy()
            probe.positional = None
            self.node(n[2], probe, None, wrapped)                         # the body, as written
            return Info()
        return self.simple(n, ctx, stdin, wrapped)

    def andor(self, item, ctx, stdin, wrapped):
        """One `a && b || c` chain. After the first command nothing is certain: a later cd may not have
        happened, so the directory becomes every one it could be."""
        _, chain, background = item
        if background:
            ctx = ctx.copy()
        info = Info()
        seen = []
        for k, (op, pipeline) in enumerate(chain):
            if k and op == '||':
                set_cwd_opts(ctx, seen)                     # whatever ran before may have failed anywhere
            info.merge(self.node(pipeline, ctx, stdin, wrapped))
            seen = seen + cwd_opts(ctx)
        if len(chain) > 1:
            set_cwd_opts(ctx, seen)
        return info

    def uncertain(self, items, ctx, stdin, wrapped):
        """The body of an if, case or loop: any part may or may not run."""
        info = Info()
        seen = cwd_opts(ctx)
        for k, item in enumerate(items):
            if k:
                set_cwd_opts(ctx, seen)
            info.merge(self.andor(item, ctx, stdin, wrapped))
            seen = seen + cwd_opts(ctx)
        set_cwd_opts(ctx, seen)
        return info

    def representative(self, words, ctx):
        """The value a for-loop variable is judged by: the most dangerous item, else the only one."""
        texts = []
        for w in words:
            for a in self.expand(w, ctx):
                for piece in expand_braces(a.text):
                    texts.extend(glob_matches(piece, ctx.cwd) if a.globby else [piece])
        for t in texts:
            if classify(PathRef(t, ctx.cwd)) is not None:
                return t
        return texts[0] if len(texts) == 1 else None

    # ---- redirections -------------------------------------------------------------------------
    def redirects(self, redirs, ctx, argv, name, incoming):
        stdin = None
        reads_file = False
        written = []
        cwds = cand_cwds(ctx)
        passes_download = incoming is not None and incoming.downloaded
        for tok in redirs:
            op, target, body = tok[1], tok[2], tok[3]
            if op in ('<<', '<<-'):
                text, quoted = body if body else ('', True)
                if not quoted:
                    for sub in substitution_bodies(text):
                        self.run_string(sub, ctx.copy(), wrapped=False)
                stdin = Stdin(heredoc=text)
                continue
            arg = self.expand1(target, ctx)
            if op == '<<<':
                stdin = Stdin(heredoc=None if arg.unknown else arg.text, downloaded=arg.dl_sub)
                continue
            if op in ('>&', '<&') and re.match(r'^(\d+-?|-)$', arg.text):
                continue
            if arg.text in ('/dev/null', '/dev/stdin', '/dev/stdout', '/dev/stderr', '/dev/tty'):
                continue
            reading = op in ('<', '<>', '<&')
            writing = not reading or op == '<>'
            reads_file = reads_file or reading
            for ref in path_refs(arg, cwds, split=False):
                found = classify(ref, writing=writing)
                if found and found[0] == 'secret':
                    raise Block('%s %s' % ('reading' if reading else 'writing into', found[1]),
                                'it is a credential location; its contents must never reach the '
                                'conversation, and writing there can plant keys or break logins.')
                if reading and found and found[0] == 'env':
                    raise env_block(found[1], 'an input redirection')
                if writing and (is_self(ref.lex) or is_self(ref.real)):
                    raise self_block('a redirection into %s' % pretty(ref.lex))
                if writing and ref.lex and BLOCK_DEVICE_RE.match(ref.lex):
                    raise Block('writing to the raw disk device %s' % ref.lex,
                                'a redirection onto a block device overwrites the disk.')
                if reading and (ref.lex in ctx.downloads or ref.real in ctx.downloads):
                    stdin = Stdin(downloaded=True)
            if op in ('>', '>>', '>|', '&>', '&>>') and (name in DOWNLOADERS or passes_download):
                ctx.downloads.update(downloaded_paths([arg], cwds))
            if op in ('>', '>>', '>|') and not arg.unknown:
                for c in cwds or [None]:
                    written.append(PathRef(arg.text, c).lex)
            if reading and (arg.dl_sub or arg.sub_sensitive):
                stdin = Stdin(downloaded=arg.dl_sub, taint=arg.sub_sensitive)
        text = None
        if name in ('echo', 'printf'):
            text = ' '.join(a.text for a in argv[1:] if not re.match(r'^-[neE]+$', a.text))
            if name == 'printf' or any(a.text == '-e' for a in argv[1:2]):
                text = text.replace('\\n', '\n').replace('\\t', '\t')
        elif name in ('cat', 'tee') and stdin is not None and stdin.heredoc is not None:
            text = stdin.heredoc
        if text is not None and SENT not in text:
            for path in written:
                if path:
                    ctx.written[path] = text
        if stdin is None and reads_file and incoming is None:
            stdin = Stdin()                     # input from a file: rg < notes.txt searches no folder
        return stdin

    # ---- one simple command -------------------------------------------------------------------
    def simple(self, n, ctx, stdin, wrapped):
        words, redirs = n[1], n[2]
        info = Info()
        exp = []
        for w in words:
            exp.extend(self.expand(w, ctx))
        k = 0
        while k < len(exp) and exp[k].assign is not None:
            name, value = exp[k].assign
            ctx.vars[name] = value
            k += 1
        argv = exp[k:]
        name0 = command_name(argv[0]) if argv else None
        own = self.redirects(redirs, ctx, argv, name0, stdin)
        if not argv:
            return info
        return self.run_argv(argv, ctx, own or stdin, info, wrapped)

    def run_argv(self, argv, ctx, stdin, info, wrapped):
        first = command_name(argv[0])
        if first in PRIVILEGE and (wrapped or argv[0].quoted or '/' in argv[0].text or renamed(argv[0])):
            raise Block('privilege escalation (%s) hidden where permission rules cannot see it' % first,
                        'settings.json denies %s; running it through bash -c, eval, xargs, find -exec, '
                        'a path or quotes does not make it allowed.' % first)
        if first == 'wsl' and any(a.text in ('--unregister', '--uninstall') for a in argv[1:]):
            raise Block('wsl %s' % ' '.join(a.text for a in argv[1:])[:80],
                        'it deletes a whole Linux installation and every file in it.')
        argv, extra_wrapped, cwd_override = strip_wrappers(argv, ctx, self)
        wrapped = wrapped or extra_wrapped
        if not argv:
            return info
        if cwd_override is None:
            cwd, cwds = ctx.cwd, cand_cwds(ctx)
        elif cwd_override == SENT:
            cwd, cwds = None, []
        else:
            cwd, cwds = cwd_override, [cwd_override]
        a0 = argv[0]
        name = command_name(a0)
        args = argv[1:]
        evasive = wrapped or a0.quoted or (not a0.unknown and '/' in canon(a0.text)) or renamed(a0)

        if name is None:
            if any(re.match(r'^-[A-Za-z]*c[A-Za-z]*$', a.text) for a in args):
                return self.shell('sh', args, ctx, cwd_override, stdin, info)     # "$SHELL" -c '...'
            if rm_flags([a.text for a in args]) == (True, True):
                raise Block('a command whose name cannot be resolved, run with rm -rf style flags',
                            'it may be a recursive, forced delete.')
            self.check_paths(None, args, cwds, ctx, info)
            return info

        defined = command_name(a0, fold=False)                    # functions keep their exact name
        if defined in ctx.functions and not a0.quoted and '/' not in a0.text and defined not in ctx.calls:
            saved = (ctx.positional, ctx.calls)
            ctx.positional = [ctx.positional[0] if ctx.positional else None] + [a.text for a in args]
            ctx.calls = ctx.calls + (defined,)
            try:
                if len(ctx.calls) <= MAX_DEPTH:
                    info.merge(self.node(ctx.functions[defined], ctx, stdin, wrapped))
            finally:
                ctx.positional, ctx.calls = saved
            return info

        if name == 'rm' and any(a.text.startswith('-') and a.unknown for a in args):
            raise Block('an rm whose flags cannot be resolved (%s)' % ' '.join(a.raw for a in argv)[:120],
                        'it may be a recursive, forced delete.',
                        'Ask the user which path to delete and let them run it themselves.')
        if name == 'rm' and rm_flags([a.text for a in args]) == (True, True):
            raise Block('a recursive + forced rm (%s)' % ' '.join(a.text for a in argv)[:120],
                        'it deletes whole trees with no prompt and no undo.',
                        'Ask the user which path to delete and let them run it themselves.')
        if evasive:
            label = deny_class(name, [a.text for a in args])
            if label:
                raise Block('%s hidden where permission rules cannot see it (%s)' % (label, a0.raw or name),
                            'settings.json denies this command; running it through a wrapper, a path, '
                            'quotes, bash -c, eval, xargs or find -exec does not make it allowed.')

        # executing a file downloaded (or written) earlier in this same command
        if not a0.unknown and ('/' in a0.text):
            for c in cwds or [None]:
                ref = PathRef(a0.text, c)
                if ref.lex in ctx.downloads or ref.real in ctx.downloads:
                    raise download_block('running a file downloaded earlier in the same command')
                if ref.lex in ctx.written:
                    info.merge(self.run_string(ctx.written[ref.lex], ctx.copy(), wrapped=True))

        if name in ('cd', 'chdir', 'pushd', 'popd'):
            change_dir(name, args, ctx)
            return info
        if len(argv) == 1 and not a0.unknown and name not in KNOWN_COMMANDS \
                and (a0.text.startswith(('~', '.', '/')) or '/' in a0.text):
            target = PathRef(a0.text, cwd)
            if target.lex and fs_isdir(target.lex):                   # zsh AUTO_CD: a bare directory
                ctx.oldpwd = ctx.cwd
                set_cwd_opts(ctx, [target.lex])
                return info
        if name == 'read':
            for a in args:
                if not a.text.startswith('-') and NAME_RE.fullmatch(a.text):
                    ctx.vars[a.text] = stdin.taint if stdin and stdin.taint else None
            return info
        if name in ('export', 'declare', 'typeset', 'local', 'readonly'):
            for a in args:
                if a.assign:
                    ctx.vars[a.assign[0]] = a.assign[1]
            return info
        if name == 'unset':
            for a in args:
                ctx.vars[a.text] = None
            return info
        if name == 'set':
            rest = [a.text for a in args]
            if '--' in rest:
                ctx.positional = [ctx.positional[0] if ctx.positional else None] + rest[rest.index('--') + 1:]
            elif rest and not rest[0].startswith(('-', '+')):
                ctx.positional = [ctx.positional[0] if ctx.positional else None] + rest
            return info
        if name == 'shift':
            if ctx.positional is not None:
                k = int(args[0].text) if args and args[0].text.isdigit() else 1
                ctx.positional = ctx.positional[:1] + ctx.positional[1 + k:]
            return info
        if name == 'eval':
            if any(a.dl_sub for a in args):
                raise download_block('eval of content fetched with curl/wget')
            joined = ' '.join(a.text for a in args)
            if SENT not in joined:
                info.merge(self.run_string(joined, ctx, wrapped=True))
            return info
        if name in SHELLS:
            return self.shell(name, args, ctx, cwd_override, stdin, info)
        if name in ('source', '.'):
            ops = [a for a in args if not a.text.startswith('-')]
            if ops:
                self.check_executed_file(ops[0], cwds, ctx, 'sourcing', info)
            return info
        if name in WIN_SHELLS:
            self.windows_shell(name, args, ctx, cwds, stdin)
            self.check_paths(name, args, cwds, ctx, info)
            return info
        if INTERPRETER_RE.match(name):
            self.interpreter(name, args, ctx, cwds, stdin)
            self.check_paths(name, args, cwds, ctx, info, skip_first_operand=True)
            self.check_mutations(name, args, cwds, ctx)
            return info
        if name == 'xargs':
            self.xargs(args, ctx, cwds, stdin, info)
            return info
        if name in ('find', 'bfs', 'gfind'):
            self.find(args, cwds, ctx, info)
            return info
        if name == 'watch':
            rest = [a for a in args if not a.text.startswith('-')]
            joined = ' '.join(a.text for a in rest)
            if joined and SENT not in joined:
                info.merge(self.run_string(joined, ctx.copy(), wrapped=True))
            return info
        if name in ('echo', 'printf'):
            text = ' '.join(a.text for a in args if not re.match(r'^-[neE]+$', a.text))
            info.script = None if SENT in text else text
        if name == 'tee' and stdin is not None:
            for a in args:
                if not a.text.startswith('-') and not a.unknown:
                    for c in cwds or [None]:
                        if stdin.heredoc is not None:
                            ctx.written[PathRef(a.text, c).lex] = stdin.heredoc
                    if stdin.downloaded:
                        ctx.downloads.update(downloaded_paths([a], cwds))
            if stdin.downloaded:
                info.downloader = True
        if is_decoder(name, [a.text for a in args]):
            info.downloader = True
        if name in DEVICE_WRITERS:
            for a in args:
                if BLOCK_DEVICE_RE.match(a.text):
                    raise Block('%s onto the raw disk device %s' % (name, a.text),
                                'writing onto a block device overwrites the disk.')
        if name == 'mv':
            check_mv(args, cwd, ctx)
        if name == 'dd':
            for a in args:
                key, _, value = a.text.partition('=')
                if key in ('if', 'of') and BLOCK_DEVICE_RE.match(value):
                    raise Block('dd on the raw disk device %s' % value,
                                'dd against a block device overwrites (or images) a whole disk.')
        if name in DISK_TOOLS or name.startswith(('mkfs', 'newfs')):
            listing = name in ('fdisk', 'sfdisk', 'parted') and any(a.text in ('-l', '--list') for a in args)
            if not listing and any(a.text.startswith('/dev/') or BLOCK_DEVICE_RE.match(a.text) for a in args):
                raise Block('%s on a disk device' % name, 'it repartitions, formats or wipes a disk.')
        if name == 'diskpart' or (name == 'format' and any(re.match(r'^[A-Za-z]:[\\/]?$', a.text) for a in args)):
            raise Block('%s' % ' '.join(a.text for a in argv)[:80], 'it repartitions or formats a disk.')
        if name == 'diskutil':
            verb = diskutil_destructive([a.text for a in args])
            if verb:
                raise Block('diskutil %s' % verb, 'it erases, repartitions or rewrites a disk.')
        if name in ('docker', 'podman', 'nerdctl'):
            check_docker(args, cwd)
        if name in DOWNLOADERS:
            outputs = downloaded_paths(download_outputs(name, args), cwds)
            ctx.downloads.update(outputs)
            if not outputs:
                info.downloader = True
        if name in COPY_LIKE and any(not a.unknown and any(PathRef(a.text, c).lex in ctx.downloads
                                                          for c in cwds or [None]) for a in args):
            dest = copy_destination(name, args)
            if dest is not None:
                ctx.downloads.update(downloaded_paths([dest], cwds))
        path_cwds = cwds
        if name == 'git':
            git_cwd, sub, sub_args, had_globals, configs = git_parts(args, cwd)
            if git_cwd != cwd:
                path_cwds = [git_cwd] if git_cwd else []
            check_git_hooks(sub, sub_args, configs, ctx)
            check_git_discard(sub, sub_args, git_cwd)
            if sub == 'apply':
                plan = git_apply_unpack(sub_args)
                if plan is not None:
                    check_unpack(plan, path_cwds)
            if (had_globals or evasive):
                label = git_deny(sub, [a.text for a in sub_args])
                if label:
                    raise Block('%s (via git global options or a wrapper)' % label,
                                'settings.json denies this git command; git -C / git -c or a wrapper '
                                'only hides it from the permission rules.')
        self.check_paths(name, args, path_cwds, ctx, info)
        self.check_mutations(name, args, cwds, ctx)
        if name in GREP_FAMILY:
            check_whole_disk_search(name, args, cwds, stdin)
        if name in ('cp', 'gcp'):
            check_cp(args, cwd, ctx)
        plan = unpack_plan(name, args, cwds)
        if plan is not None:
            check_unpack(plan, cwds)
        if name in ENV_READERS and any(PathRef(a.text, c).lex in ctx.downloads
                                       for a in args if not a.unknown for c in cwds or [None]):
            info.downloader = True                                       # cat ./downloaded | sh
        return info

    # ---- shells and interpreters --------------------------------------------------------------
    def sub_ctx(self, ctx, cwd_override):
        sub = ctx.copy()
        if cwd_override == SENT:
            sub.cwd, sub.maybe = None, ()
        elif cwd_override is not None:
            sub.cwd, sub.maybe = cwd_override, ()
        return sub

    def shell(self, name, args, ctx, cwd_override, stdin, info):
        has_c, reads_stdin, operands = False, False, []
        i = 0
        while i < len(args):
            t = args[i].text
            if operands:
                operands.append(args[i])
            elif t in ('-o', '+o', '-O', '+O', '--rcfile', '--init-file'):
                i += 1
            elif t == '--':
                operands.extend(args[i + 1:])
                break
            elif t == '-':
                reads_stdin = True
                operands.extend(args[i + 1:])
                break
            elif re.match(r'^[-+][A-Za-z]+$', t):
                has_c = has_c or 'c' in t[1:]
                reads_stdin = reads_stdin or 's' in t[1:]
            else:
                operands.append(args[i])
            i += 1
        cwds = cand_cwds(self.sub_ctx(ctx, cwd_override))
        if has_c:
            if not operands:
                return info
            code = operands[0]
            if code.dl_sub:
                raise download_block('running content fetched with curl/wget through %s -c' % name)
            if not code.unknown:
                sub = self.sub_ctx(ctx, cwd_override)
                sub.functions = {}
                sub.positional = [a.text for a in operands[1:]] or [name]
                info.merge(self.run_string(code.text, sub, wrapped=True))
            return info
        if operands and not reads_stdin and operands[0].text not in STDIN_PATHS:
            self.check_executed_file(operands[0], cwds, ctx, 'running', info)
            return info
        if stdin is not None and stdin.downloaded:
            raise download_block('piping downloaded or decoded content into %s' % name)
        if stdin is not None and stdin.heredoc:
            sub = self.sub_ctx(ctx, cwd_override)
            sub.positional = [name] + [a.text for a in operands[1:]]
            info.merge(self.run_string(stdin.heredoc, sub, wrapped=True))
        return info

    def check_executed_file(self, arg, cwds, ctx, verb, info=None, code_of=None):
        if arg.dl_sub:
            raise download_block('%s content fetched with curl/wget' % verb)
        if arg.unknown:
            return
        for c in cwds or [None]:
            ref = PathRef(arg.text, c)
            if ref.lex in ctx.downloads or ref.real in ctx.downloads:
                raise download_block('%s a file downloaded earlier in the same command' % verb)
            if ref.lex in ctx.written:
                if code_of in WIN_SHELLS:
                    check_windows_code(ctx.written[ref.lex], code_of, ctx.env)
                elif code_of:
                    check_code_text(ctx.written[ref.lex], code_of)
                else:
                    result = self.run_string(ctx.written[ref.lex], ctx.copy(), wrapped=True)
                    if info is not None:
                        info.merge(result)
            found = classify(ref)
            if found and found[0] == 'secret':
                raise secret_block(found[1], verb)
            if found and found[0] == 'env':
                raise env_block(found[1], verb + ' it')

    def interpreter(self, name, args, ctx, cwds, stdin):
        code_flags = INLINE_CODE_FLAGS.get(re.sub(r'[\d.]+$', '', name), ('-c', '-e'))
        codes, script, i = [], None, 0
        while i < len(args):
            t = args[i].text
            if t == '-m' or t.startswith('-m') and name.startswith('python') or t == '--':
                script = 'module'                                       # python -m: code is not stdin
                break
            if t in code_flags or (t.startswith('-') and not t.startswith('--') and len(t) > 2
                                   and t[-1] in 'eEcr' and ('-' + t[-1]) in code_flags):
                if i + 1 < len(args):
                    codes.append(args[i + 1])
                i += 2
                continue
            if t.startswith('-c') and '-c' in code_flags and len(t) > 2 and name.startswith('python'):
                codes.append(make_arg(t[2:]))
            elif t == '-':
                script = '-'
                break
            elif not t.startswith('-'):
                script = args[i]
                break
            i += 1
        for code in codes:
            if code.dl_sub:
                raise download_block('running content fetched with curl/wget through %s' % name)
            check_code_text(code.text, name)
        if isinstance(script, Arg) and script.text not in STDIN_PATHS:
            self.check_executed_file(script, cwds, ctx, 'running', code_of=name)
        elif not codes and script != 'module':
            if stdin is not None and stdin.downloaded:
                raise download_block('piping downloaded or decoded content into %s' % name)
            if stdin is not None and stdin.heredoc:
                check_code_text(stdin.heredoc, name)

    def windows_shell(self, name, args, ctx, cwds, stdin):
        """cmd /c TEXT, powershell / pwsh -Command TEXT, -EncodedCommand B64, -File SCRIPT, or the
        command text on stdin. The text is checked like inline interpreter code (see
        check_windows_code), the script file like any script that is run."""
        texts = [a.text for a in args]
        code = script = None
        if any(a.dl_sub for a in args):
            raise download_block('running content fetched with curl/wget through %s' % name)
        if name == 'cmd':
            for k, t in enumerate(texts):
                m = re.match(r'^/{1,2}[ckCK](.*)$', t, re.S)
                if m:
                    code = ' '.join(([m.group(1)] if m.group(1) else []) + texts[k + 1:])
                    break
            if code is None and any(not re.match(r'^/{1,2}\w(?::\w+)?$', t) for t in texts):
                code = ' '.join(texts)
        else:
            k = 0
            while k < len(texts):
                t = texts[k]
                option = t[:1] == '-' or (t[:1] == '/' and '/' not in t[1:])  # -Command or /Command
                low = '-' + t.lstrip('-/').lower() if option else None
                if low is None:                       # a bare word or a path: the command (or script)
                    if texts[k].lower().endswith('.ps1'):
                        script = args[k]
                    else:
                        code = ' '.join(texts[k:])
                    break
                if low in ('-c', '-co', '-com', '-comm', '-comma', '-comman', '-command'):
                    code = ' '.join(texts[k + 1:])
                    break
                if low in ('-e', '-ec', '-en', '-enc', '-enco', '-encodedcommand') or \
                        (len(low) > 4 and '-encodedcommand'.startswith(low)):
                    if k + 1 >= len(texts) or args[k + 1].unknown:
                        raise ParseError('%s -EncodedCommand whose text cannot be known' % name)
                    code = decode_powershell(texts[k + 1], name)
                    break
                if low in ('-f', '-fi', '-fil', '-file'):
                    script = args[k + 1] if k + 1 < len(args) else None
                    break
                k += 2 if low in PS_VALUE_OPTIONS else 1
        if code is not None and code.strip() not in ('', '-'):
            check_windows_code(code, name, ctx.env)
        elif script is not None:
            self.check_executed_file(script, cwds, ctx, 'running', code_of=name)
        elif stdin is not None and stdin.downloaded:
            raise download_block('piping downloaded or decoded content into %s' % name)
        elif stdin is not None and stdin.heredoc:
            check_windows_code(stdin.heredoc, name, ctx.env)

    # ---- xargs and find -----------------------------------------------------------------------
    def xargs(self, args, ctx, cwds, stdin, info):
        events = getopt_walk(args, XARGS_SPEC, permute=False)
        inner, files = [], []
        for ev in events:
            if ev[0] == 'opt' and ev[1] in ('-a', '--arg-file') and ev[2] is not None:
                files.append(ev[2])
            elif ev[0] == 'arg':
                inner.append(ev[1])
        for f in files:                                          # xargs -a FILE reads FILE into argv
            self.check_paths('xargs', [f], cwds, ctx, info)
        if not inner:
            inner = [make_arg('echo')]                           # xargs runs echo by default
        if stdin and stdin.taint:
            inner = inner + [make_arg(stdin.taint)]
        # the command gets the operands xargs reads, so a search without one does not default to its folder
        self.run_argv(inner, ctx, Stdin(), info, wrapped=True)

    def find(self, args, cwds, ctx, info):
        roots, i = [], 0
        while i < len(args) and args[i].text in ('-H', '-L', '-P', '-E', '-X', '-d', '-s', '-x', '-f'):
            i += 1
        while i < len(args) and not args[i].text.startswith(('-', '(', '!')):
            roots.append(args[i])
            i += 1
        if not roots:
            roots = [make_arg('.')]
        expr = args[i:]
        tests, negated, deletes, narrow = [], [], False, False
        root_hits = []
        for r in roots:
            for ref in path_refs(r, cwds, split=False):
                found = classify(ref)
                if found and found[0] in ('secret', 'ancestor'):
                    root_hits.append(found)
                    if found[0] == 'secret':
                        info.sensitive = info.sensitive or ref.best()
        j = 0
        while j < len(expr):
            t = expr[j].text
            if t in FIND_NAME_TESTS and j + 1 < len(expr):
                neg = j > 0 and expr[j - 1].text in ('!', '-not')
                (negated if neg else tests).append((t, expr[j + 1].text))
                if not neg and expr[j + 1].text not in MATCH_ALL:
                    narrow = True
                j += 2
                continue
            if t in FIND_NARROW_TESTS:
                narrow = True
            if t == '-delete':
                deletes = True
            j += 1
        # what find will hand on: the sensitive files its name tests match, or that sit in a root
        candidates = []
        for r in roots:
            if not r.unknown:
                candidates.extend(find_candidates(r, cwds, tests, negated))
        for c in candidates:
            hit = classify(PathRef(c, (cwds or [None])[0]))
            if hit and hit[0] in ('secret', 'env'):
                info.sensitive = info.sensitive or c
        if deletes:
            lexical = []                                    # -delete removes a symlink, not its target
            for c in candidates:
                ref = PathRef(c, (cwds or [None])[0])
                ref.real = None
                lexical.append(classify(ref))
            if root_hits or any(hit and hit[0] == 'secret' for hit in lexical):
                raise Block('find -delete over %s' % (root_hits[0][1] if root_hits else 'credential files'),
                            'it deletes credentials (keys, tokens) with no prompt and no undo.')
            if not narrow:
                raise Block('find %s -delete with nothing that narrows what it deletes'
                            % ' '.join(r.text for r in roots)[:80],
                            'it empties the whole tree, the same as rm -rf, with no prompt and no undo.',
                            'Add a -name / -path test for exactly what should go, or ask the user to '
                            'run the delete themselves.')
        j = 0
        while j < len(expr):
            t = expr[j].text
            if t in ('-exec', '-execdir', '-ok', '-okdir'):
                inner = []
                j += 1
                while j < len(expr) and expr[j].text not in (';', '+'):
                    inner.append(expr[j])
                    j += 1
                if not inner:
                    continue
                inner_name = command_name(inner[0])
                if root_hits and inner_name not in META_OK and inner_name not in USE_ANY:
                    raise Block('find -exec %s over %s' % (inner_name or inner[0].raw, root_hits[0][1]),
                                'find walks into a credential location and hands every file to a command '
                                'that reads it.')
                substitutes = [r.text for r in roots] + candidates
                for sub_text in substitutes[:12]:
                    expanded = [make_arg(a.text.replace('{}', sub_text)) if '{}' in a.text else a for a in inner]
                    self.run_argv(expanded, ctx, None, Info(), wrapped=True)
            j += 1

    # ---- path arguments -----------------------------------------------------------------------
    def check_paths(self, name, args, cwds, ctx, info, skip_first_operand=False):
        meta = name in META_OK or name in USE_OK
        if not meta and any(in_credential_location(c) for c in cwds):
            running_in = next(c for c in cwds if in_credential_location(c))
            raise Block('running %s inside %s' % (name or 'a command', pretty(running_in)),
                        'the working directory is a credential location, so any relative read lands on '
                        'secrets.')
        spec = operand_spec(name, args, cwds, ctx.written)
        items = list(spec.items)
        if skip_first_operand:
            for k, (a, role) in enumerate(items):
                if role == 'path':
                    del items[k]
                    break
        for a in args:
            if a.sub_sensitive:
                items.append((make_arg(a.sub_sensitive), 'path'))
        uses = name in META_OK or use_ok(name, args)
        recursive = is_recursive_reader(name, args)
        for arg, role in items:
            for ref in path_refs(arg, cwds, split=(role != 'redirect')):
                found = classify(ref)
                if found is None:
                    continue
                kind, label = found
                if kind == 'secret':
                    if uses or arg in spec.use_values:
                        info.sensitive = info.sensitive or ref.best()
                        continue
                    raise secret_block(label, name)
                if kind == 'ancestor':
                    if recursive and not spec.names_only:
                        raise Block('%s recursively over %s' % (name, label),
                                    'that directory contains credential locations (~/.ssh, ~/.aws, ...), '
                                    'so a recursive read, copy or archive of it takes secrets along.',
                                    'Point it at the specific project directory instead.')
                    continue
                if kind == 'env':
                    if name in META_OK:
                        info.sensitive = info.sensitive or (ref.lex or ref.text)
                    self.check_env(name, args, arg, label, items, spec)
        for script in spec.sed_scripts:
            self.check_sed(script, cwds, ctx)
        for program in spec.code:
            check_code_text(program, name)
        if recursive and not spec.names_only:
            check_recursive_contents(name, args, items, spec, cwds)
            if name in ARCHIVE_CREATORS:
                check_archive_env(name, args, cwds)

    def check_env(self, name, args, arg, label, items, spec):
        if name in GREP_FAMILY and spec.names_only:
            return                                                      # file names or counts only
        if name in ENV_READERS or (name == 'git' and git_reads(args)):
            raise env_block(label, name)
        if name in COMPRESSORS and any(a.text in ('-c', '--stdout', '--to-stdout', '-dc', '-cd') for a in args):
            raise env_block(label, name + ' -c')
        if name in EXFIL:
            raise env_block(label, 'sending it with ' + name)
        if name in ARCHIVERS:
            paths =[a for a, role in items if role == 'path']
            if name == 'tar' and is_recursive_reader(name, args):           # tar c/r/u: operands are inputs
                raise env_block(label, 'archiving it with tar')
            if name in ('zip', '7z') and paths and arg is not paths[min(len(paths) - 1, 1 if name == '7z' else 0)]:
                raise env_block(label, 'archiving it with %s' % name)
            return
        if name in COPY_LIKE:
            paths = [a for a, role in items if role == 'path']
            dest = paths[-1] if paths else None
            if arg is dest:
                return                                                   # writing an env file is fine
            if dest is not None and not dest.unknown and env_tier(posixpath.basename(canon(dest.text).rstrip('/'))) == 'hard':
                return                                                   # .env -> .env.bak stays in the tier
            if dest is not None:
                raise env_block(label, 'copying it with %s to a name outside the env tier' % name)

    def check_sed(self, script, cwds, ctx):
        reads, writes, runs, opaque = sed_effects(script)
        if opaque:
            raise Block('sed running text as a shell command (the e command or the s///e flag)',
                        'the hook cannot see which command that runs.')
        for f in reads:
            if f in STDIN_PATHS:
                continue
            for ref in path_refs(make_arg(f), cwds, split=False):
                found = classify(ref)
                if found and found[0] == 'secret':
                    raise secret_block(found[1], 'sed r/R')
                if found and found[0] == 'env':
                    raise env_block(found[1], 'sed r/R')
        for f in writes:
            check_write_target(make_arg(f), cwds, 'sed w')
        for command in runs:
            self.run_string(command, ctx.copy(), wrapped=True)

    def check_mutations(self, name, args, cwds, ctx):
        """Writes, moves and deletes that would change the safety layer itself."""
        texts = [a.text for a in args]
        targets = []
        if name in COPY_LIKE or name in ('gcp', 'ditto'):
            dest = copy_destination(name, args)
            if dest is not None:
                for src in copy_sources(name, args):
                    targets.extend(copy_targets(src, dest, cwds))
                targets.append(dest)
                if name == 'mv':
                    for src in copy_sources(name, args):
                        if self_or_config(src, cwds):
                            raise self_block('moving %s away' % src.text)
        elif name == 'tee':
            targets = [a for a in args if not a.text.startswith('-')]
        elif name in ('rm', 'unlink', 'shred', 'truncate', 'rmdir', 'srm'):
            for a in args:
                if not a.text.startswith('-') and self_or_config(a, cwds):
                    raise self_block('%s on %s' % (name, a.text))
        elif name in ('sed', 'gsed', 'perl', 'ruby') and in_place(name, texts):
            targets = [a for a, role in operand_spec(name, args).items if role == 'path']
        elif name == 'dd':
            targets = [make_arg(t[3:]) for t in texts if t.startswith('of=')]
        elif name in DOWNLOADERS:
            targets = download_outputs(name, args)
        elif name == 'patch':
            targets = patch_unpack(name, args)[1]
        elif name == 'chmod' and chmod_removes_read(texts):
            for a in args[1:]:
                if not a.text.startswith('-') and self_or_config(a, cwds):
                    raise self_block('chmod removing read access from %s' % a.text)
        for target in targets:
            check_write_target(target, cwds, name)


# ----------------------------------------------------------------------------------------------------
# Command tables
# ----------------------------------------------------------------------------------------------------
SHELLS = {'sh', 'bash', 'zsh', 'dash', 'ksh', 'mksh', 'ash', 'fish', 'csh', 'tcsh', 'yash', 'posh'}
STDIN_PATHS = {'/dev/stdin', '/dev/fd/0', '/proc/self/fd/0', '-'}
INTERPRETER_RE = re.compile(r'^(?:python[\d.]*|py|pypy[\d.]*|node|nodejs|deno|bun|perl|ruby|php|osascript'
                            r'|lua[\d.]*|Rscript)$', re.IGNORECASE)
INLINE_CODE_FLAGS = {
    'python': ('-c',), 'py': ('-c',), 'pypy': ('-c',), 'node': ('-e', '--eval', '-p', '--print'),
    'nodejs': ('-e', '--eval', '-p', '--print'), 'bun': ('-e', '--eval', '-p', '--print'),
    'deno': ('eval',), 'perl': ('-e', '-E'), 'ruby': ('-e',), 'php': ('-r',), 'osascript': ('-e',),
    'lua': ('-e',), 'Rscript': ('-e',),
}
DOWNLOADERS = {'curl', 'wget', 'fetch'}
STDOUT_NAMES = {'-', '/dev/stdout', '/dev/fd/1'}
DEVICE_WRITERS = {'cp', 'tee', 'install', 'mv', 'ln', 'rsync', 'pv', 'ditto'}
META_OK = {
    'ls', 'stat', 'test', '[', '[[', 'file', 'du', 'df', 'chmod', 'mkdir', 'rmdir', 'touch', 'realpath',
    'readlink', 'dirname', 'basename', 'echo', 'printf', 'true', 'false', 'tree', 'wc', 'md5', 'md5sum',
    'shasum', 'sha1sum', 'sha224sum', 'sha256sum', 'sha384sum', 'sha512sum', 'b2sum', 'cksum', 'sum',
    'find', 'bfs', 'exa', 'eza', 'lsd', 'getfacl', 'xattr', 'lsattr', 'type', 'which', 'whereis', 'cd',
    'pushd', 'popd', 'command',
}
# Tools whose every operand only USES a key (ssh host, ssh-add key, ssh-keygen -f key).
USE_ANY = {'ssh', 'ssh-add', 'ssh-keygen', 'ssh-copy-id', 'ssh-keyscan', 'sshfs', 'autossh', 'mosh',
           'gpgconf', 'gpg-agent', 'kubectx', 'kubens'}
# Tools that may run with their cwd in a credential location, but name one only through a USE option.
USE_OK = USE_ANY | {'kubectl', 'helm', 'k9s', 'gpg', 'gpg2'}
USE_OPTIONS = {
    'scp': ('-i', '-F'), 'sftp': ('-i', '-F'), 'kubectl': ('--kubeconfig',), 'helm': ('--kubeconfig',),
    'k9s': ('--kubeconfig',),
    'gpg': ('--homedir', '--keyring', '--secret-keyring', '--primary-keyring', '--trustdb-name', '--options'),
    'gpg2': ('--homedir', '--keyring', '--secret-keyring', '--primary-keyring', '--trustdb-name', '--options'),
}
SSH_USE_KEYS = ('identityfile=', 'certificatefile=', 'userknownhostsfile=', 'globalknownhostsfile=',
                'identityagent=', 'controlpath=')
GPG_KEY_OPS = {
    '--list-keys', '-k', '--list-public-keys', '--list-secret-keys', '-K', '--list-sigs', '--check-sigs',
    '--fingerprint', '--import', '--recv-keys', '--receive-keys', '--refresh-keys', '--send-keys',
    '--search-keys', '--edit-key', '--sign-key', '--lsign-key', '--gen-key', '--generate-key',
    '--full-gen-key', '--full-generate-key', '--quick-gen-key', '--quick-generate-key', '--quick-add-key',
    '--quick-add-uid', '--card-status', '--card-edit', '--change-pin', '--delete-keys', '--export',
    '--gen-revoke', '--generate-revocation',
}
GPG_CONTENT_OPS = {
    '--enarmor', '--dearmor', '--store', '--symmetric', '--encrypt', '--sign', '--clearsign',
    '--clear-sign', '--detach-sign', '--decrypt', '--output', '--export-secret-keys',
    '--export-secret-subkeys', '--export-ssh-key',
}
ENV_READERS = {
    'cat', 'less', 'more', 'most', 'head', 'tail', 'bat', 'batcat', 'nl', 'xxd', 'od', 'hexdump', 'hd',
    'strings', 'base32', 'base64', 'basenc', 'grep', 'egrep', 'fgrep', 'zgrep', 'ugrep', 'rg', 'ag', 'ack',
    'awk', 'gawk', 'mawk', 'nawk', 'sed', 'gsed', 'cut', 'tr', 'sort', 'uniq', 'rev', 'fold', 'paste',
    'column', 'pr', 'tac', 'diff', 'diff3', 'sdiff', 'cmp', 'comm', 'join', 'dd', 'fmt', 'expand',
    'unexpand', 'look', 'iconv', 'openssl', 'zcat', 'gzcat', 'bzcat', 'xzcat', 'zless', 'zmore', 'view',
    'vim', 'vi', 'nvim', 'nano', 'emacs', 'ed', 'ex', 'jq', 'yq', 'xargs', 'envsubst', 'source', '.', 'sh',
    'bash', 'zsh', 'gpg', 'gpg2',
}
GREP_FAMILY = {'grep', 'egrep', 'fgrep', 'zgrep', 'ugrep', 'rg', 'ag', 'ack'}
COMPRESSORS = {'gzip', 'bzip2', 'xz', 'zstd', 'lz4', 'brotli', 'pigz'}
COPY_LIKE = {'cp', 'mv', 'ln', 'install', 'rsync', 'scp', 'ditto', 'rclone'}
ARCHIVERS = {'tar', 'zip', '7z'}
ARCHIVE_CREATORS = {'tar', 'bsdtar', 'gtar', 'zip', '7z', '7za', '7zz'}
ARCHIVE_EXCLUDE_HINT = {'tar': "tar --exclude='.env*'", 'zip': "zip ... -x '*.env*'", '7z': "7z ... '-xr!.env*'"}
ZIP_VALUE_OPTS = {'-b', '-n', '-t', '-tt', '-P', '-Z', '-s', '-O', '-ds'}
EXFIL = {'curl', 'wget', 'nc', 'ncat', 'netcat', 'socat', 'http', 'https', 'xh', 'ftp', 'lftp', 'sftp',
         'aws', 'gsutil', 'gcloud', 'az', 'gh', 'rclone'}
DISK_TOOLS = {'mke2fs', 'mkswap', 'wipefs', 'fdisk', 'sfdisk', 'gdisk', 'sgdisk', 'cfdisk', 'parted',
              'blkdiscard', 'shred', 'badblocks'}
DISKUTIL_DESTRUCTIVE = {'erasedisk', 'erasevolume', 'partitiondisk', 'zerodisk', 'randomdisk',
                        'secureerase', 'reformat', 'resizevolume', 'splitpartition', 'mergepartitions',
                        'erasecd', 'deletecontainer'}
DISKUTIL_FAMILIES = {'apfs', 'cs', 'corestorage', 'ar', 'appleraid'}
KNOWN_COMMANDS = SHELLS | META_OK | USE_OK | ENV_READERS | DOWNLOADERS | COPY_LIKE | ARCHIVERS | EXFIL | {
    'git', 'npm', 'npx', 'node', 'python', 'python3', 'make', 'docker', 'rm', 'mv'}
FIND_NAME_TESTS = ('-name', '-iname', '-path', '-ipath', '-wholename', '-iwholename', '-regex', '-iregex')
FIND_NARROW_TESTS = ('-empty', '-inum', '-samefile', '-links')
MATCH_ALL = ('*', '.*', '*.*', '?*', '**', '.*/*', './*', '*/*')
# Names a find over a project could hand to its -exec: hard env files and key files.
SENSITIVE_SAMPLES = ['.env', '.env.local', '.env.production', '.envrc', '.netrc', '.pgpass',
                     '.git-credentials', '.vault-token'] + sorted(KEY_FILE_NAMES)
# /run holds the container daemons' sockets (mounting it is as good as mounting docker.sock). Application
# data folders such as /opt stay mountable: containers on servers legitimately use them.
DOCKER_SYSTEM_DIRS = ('/etc', '/var', '/usr', '/root', '/boot', '/proc', '/sys', '/dev', '/bin', '/sbin',
                      '/lib', '/lib32', '/lib64', '/run', '/private/etc', '/private/var')
DOCKER_MOUNT_OK = ('/var/folders', '/private/var/folders', '/var/tmp', '/dev/shm', '/etc/localtime',
                   '/etc/timezone')

# Wrappers that run their arguments as a command. Claude Code strips the first group itself before it
# matches permission rules; the second group hides the inner command from those rules.
CC_STRIPPED = {'timeout', 'time', 'nice', 'nohup', 'stdbuf', 'command', 'builtin', 'noglob'}
WRAPPER_VALUE_OPTS = {
    'sudo': {'-u', '-g', '-C', '-D', '-h', '-p', '-r', '-t', '-U', '-T', '--user', '--group'},
    'doas': {'-u', '-C'}, 'exec': {'-a'}, 'nice': {'-n', '--adjustment'}, 'time': {'-f', '-o'},
    'timeout': {'-s', '-k', '--signal', '--kill-after'}, 'stdbuf': set(), 'caffeinate': {'-t', '-w'},
    'ionice': {'-c', '-n', '-p', '-t'}, 'command': set(), 'builtin': set(), 'nohup': set(),
    'unbuffer': set(), 'setsid': set(), 'chronic': set(), 'busybox': set(), 'noglob': set(),
    'nocorrect': set(), 'env': {'-u', '--unset', '-P', '-L', '-U', '-a', '--argv0'},
    'wsl': {'-d', '--distribution', '-u', '--user', '--cd', '--shell-type', '--distribution-id'},
}

# getopt tables: (short options that take a value, long options that take one, long flags, short
# options whose value may only be attached). Only an option that takes a value in every common
# implementation is listed as taking one: listing a flag as value-taking would hide the next operand.
GREP_SPEC = ('efmABCdDgtKN',
             {'--regexp', '--file', '--max-count', '--after-context', '--before-context', '--context',
              '--directories', '--devices', '--include', '--exclude', '--exclude-dir', '--exclude-from',
              '--include-dir', '--include-from', '--label', '--binary-files', '--group-separator', '--glob',
              '--iglob', '--file-type', '--file-extension'},
             {'--files-with-matches', '--files-without-match', '--count', '--quiet', '--silent',
              '--recursive', '--dereference-recursive', '--invert-match', '--fixed-strings', '--ignore-case',
              '--line-number', '--only-matching', '--with-filename', '--no-filename', '--word-regexp',
              '--line-regexp', '--extended-regexp', '--basic-regexp', '--perl-regexp', '--null', '--text',
              '--no-messages', '--byte-offset', '--initial-tab', '--null-data', '--line-buffered',
              '--hidden', '--color', '--colour'}, '')
RG_SPEC = ('efgmABCtTjMrEd',
           {'--regexp', '--file', '--glob', '--iglob', '--max-count', '--after-context', '--before-context',
            '--context', '--type', '--type-not', '--type-add', '--type-clear', '--threads', '--max-columns',
            '--replace', '--encoding', '--max-depth', '--max-filesize', '--path-separator', '--pre',
            '--pre-glob', '--sort', '--sortr', '--colors', '--color', '--context-separator',
            '--field-context-separator', '--field-match-separator', '--ignore-file', '--dfa-size-limit',
            '--regex-size-limit', '--engine', '--hyperlink-format', '--generate', '--hostname-bin'},
           {'--files-with-matches', '--files-without-match', '--count', '--count-matches', '--quiet',
            '--files', '--hidden', '--no-ignore', '--unrestricted', '--fixed-strings', '--invert-match',
            '--ignore-case', '--line-number', '--only-matching', '--json', '--follow', '--multiline'}, '')
AG_SPEC = ('Ggmp',
           {'--depth', '--file-search-regex', '--ignore', '--ignore-dir', '--max-count', '--pager',
            '--path-to-ignore', '--workers'},
           {'--files-with-matches', '--files-without-matches', '--count', '--hidden', '--unrestricted',
            '--all-types', '--all-text', '--literal', '--invert-match', '--after', '--before',
            '--context'}, 'ABC')
ACK_SPEC = ('gm',
            {'--max-count', '--type', '--ignore-dir', '--ignore-file', '--match', '--output', '--pager'},
            {'--files-with-matches', '--files-without-matches', '--count', '--after-context',
             '--before-context', '--context'}, 'ABC')
SED_SPEC = ('ef', {'--expression', '--file', '--line-length'},
            {'--quiet', '--silent', '--regexp-extended', '--separate', '--unbuffered', '--null-data',
             '--in-place', '--posix', '--sandbox', '--debug', '--follow-symlinks'}, 'i')
AWK_SPEC = ('FvfeEilW', {'--field-separator', '--assign', '--file', '--source', '--exec', '--include',
                         '--load'},
            {'--posix', '--traditional', '--lint', '--sandbox', '--characters-as-bytes', '--bignum',
             '--dump-variables', '--profile', '--pretty-print', '--debug'}, 'dDopL')
XARGS_SPEC = ('adEILnPsJRS', {'--arg-file', '--delimiter', '--eof', '--max-lines', '--max-args',
                              '--max-procs', '--max-chars', '--process-slot-var'},
              {'--null', '--no-run-if-empty', '--verbose', '--interactive', '--exit', '--open-tty',
               '--show-limits', '--replace'}, 'eil')
COMMIT_SPEC = ('mFCct', {'--message', '--file', '--reuse-message', '--reedit-message', '--template',
                         '--author', '--date', '--cleanup', '--fixup', '--squash', '--trailer',
                         '--pathspec-from-file'},
               {'--all', '--patch', '--reset-author', '--short', '--branch', '--porcelain', '--long',
                '--null', '--signoff', '--no-signoff', '--no-verify', '--verify', '--allow-empty',
                '--allow-empty-message', '--edit', '--no-edit', '--amend', '--no-post-rewrite', '--include',
                '--only', '--pathspec-file-nul', '--untracked-files', '--verbose', '--quiet', '--dry-run',
                '--status', '--no-status', '--gpg-sign', '--no-gpg-sign', '--interactive'}, 'uS')
SEARCH_SPECS = {'grep': GREP_SPEC, 'egrep': GREP_SPEC, 'fgrep': GREP_SPEC, 'zgrep': GREP_SPEC,
                'ugrep': GREP_SPEC, 'rg': RG_SPEC, 'ag': AG_SPEC, 'ack': ACK_SPEC}
NAMES_ONLY = {
    'grep': ('lLcq', {'--files-with-matches', '--files-without-match', '--count', '--quiet', '--silent'}),
    'rg': ('lcq', {'--files-with-matches', '--files-without-match', '--count', '--count-matches', '--quiet',
                   '--files'}),
    'ag': ('lLcg', {'--files-with-matches', '--files-without-matches', '--count'}),
    'ack': ('lLcgf', {'--files-with-matches', '--files-without-matches', '--count'}),
}
RM_LONG = ('--force', '--interactive', '--one-file-system', '--no-preserve-root', '--preserve-root',
           '--recursive', '--dir', '--verbose', '--help', '--version')
MV_LONG = ('--backup', '--context', '--debug', '--exchange', '--force', '--interactive', '--no-clobber',
           '--no-copy', '--no-target-directory', '--strip-trailing-slashes', '--suffix',
           '--target-directory', '--update', '--verbose', '--help', '--version')
CP_LONG = ('--archive', '--attributes-only', '--backup', '--context', '--copy-contents', '--debug',
           '--dereference', '--force', '--interactive', '--keep-directory-symlink', '--link', '--no-clobber',
           '--no-dereference', '--no-preserve', '--no-target-directory', '--one-file-system', '--parents',
           '--preserve', '--recursive', '--reflink', '--remove-destination', '--sparse',
           '--strip-trailing-slashes', '--suffix', '--symbolic-link', '--target-directory', '--update',
           '--verbose', '--help', '--version')
COPY_VALUE_SHORT = {'cp': 'tS', 'mv': 'tS', 'ln': 'tS', 'install': 'mogtS', 'rsync': 'efBTM', 'scp': 'cFiJloPS',
                    'ditto': '', 'rclone': '', 'gcp': 'tS'}


def command_name(a, fold=True):
    if a is None or a.unknown or not a.text:
        return None
    name = posixpath.basename(canon(a.text).rstrip('/')) or a.text
    return fold_name(name) if fold else name


def renamed(a):
    """True when the program is named in a form the permission rules do not match (RM, rm.exe)."""
    return not a.unknown and bool(a.text) and command_name(a) != command_name(a, fold=False)


def cand_cwds(ctx):
    return [ctx.cwd] if ctx.cwd is not None else [c for c in ctx.maybe if c is not None]


def resolve_long(token, names):
    if token in names:
        return token
    hits = [n for n in names if n.startswith(token)]
    return hits[0] if len(hits) == 1 else token


def getopt_walk(args, spec, permute=True):
    """Read args the way getopt_long does: events ('opt', name, value Arg or None) and ('arg', Arg).
    Long names are completed from unambiguous prefixes. When options may follow operands (permute), a
    value that comes after an operand is also reported as an operand, because a tool that stops at the
    first operand (BSD) would read it as a file."""
    shorts, long_values, long_flags, optional = spec
    longs = set(long_values) | set(long_flags)
    events = []
    i, seen_operand, done = 0, False, False
    while i < len(args):
        a = args[i]
        t = a.text
        if done or t == '-' or not t.startswith('-') or (seen_operand and not permute):
            events.append(('arg', a))
            seen_operand = True
            i += 1
            continue
        if t == '--':
            done = True
            i += 1
            continue
        if t.startswith('--'):
            key, eq, value = t.partition('=')
            name = resolve_long(key, longs)
            if eq:
                events.append(('opt', name, make_arg(value)))
            elif name in long_values and i + 1 < len(args):
                events.append(('opt', name, args[i + 1]))
                if seen_operand:
                    events.append(('arg', args[i + 1]))
                i += 1
            else:
                events.append(('opt', name, None))
            i += 1
            continue
        j = 1
        while j < len(t):
            c = t[j]
            if c in shorts:
                rest = t[j + 1:]
                if rest:
                    events.append(('opt', '-' + c, make_arg(rest)))
                elif i + 1 < len(args):
                    events.append(('opt', '-' + c, args[i + 1]))
                    if seen_operand:
                        events.append(('arg', args[i + 1]))
                    i += 1
                else:
                    events.append(('opt', '-' + c, None))
                break
            if c in optional:
                events.append(('opt', '-' + c, make_arg(t[j + 1:]) if t[j + 1:] else None))
                break
            events.append(('opt', '-' + c, None))
            j += 1
        i += 1
    return events


class Operands(object):
    __slots__ = ('items', 'use_values', 'names_only', 'sed_scripts', 'code', 'includes', 'excludes', 'typed',
                 'roots')

    def __init__(self):
        self.items, self.use_values, self.names_only = [], set(), False
        self.sed_scripts, self.code, self.includes, self.excludes, self.typed = [], [], [], [], False
        self.roots = None           # a search's folder and file operands; None when it reads no contents


def read_script_file(arg, cwds, written):
    """Text of a sed or awk script file named on the command line: written earlier in the same
    command, or on disk when it is small and readable."""
    if arg is None or arg.unknown:
        return None
    for c in cwds or [None]:
        path = PathRef(arg.text, c).lex
        if not path:
            continue
        if path in written:
            return written[path]
        try:
            if fs_isfile(path) and os.path.getsize(to_native(path)) <= MAX_SCRIPT_BYTES:
                with open(to_native(path), encoding='utf-8', errors='replace') as fh:
                    return fh.read()
        except OSError:
            continue
    return None


def operand_spec(name, args, cwds=(), written=None):
    """What a command's arguments mean: (arg, role) pairs worth judging as paths, the args that only
    USE a credential, scripts and program text inside them, and whether only names are printed."""
    out = Operands()
    written = written if written is not None else {}
    family = 'grep' if name in ('egrep', 'fgrep', 'zgrep', 'ugrep') else name
    if name in SEARCH_SPECS:
        positional, pattern_given, lists_files = [], False, False
        shorts_only, longs_only = NAMES_ONLY.get(family, ('', set()))
        events = getopt_walk(args, SEARCH_SPECS[name])
        values = set(id(ev[2]) for ev in events if ev[0] == 'opt' and ev[2] is not None)
        for ev in events:
            if ev[0] == 'arg':
                positional.append(ev[1])
                continue
            opt, value = ev[1], ev[2]
            lists_files = lists_files or (opt == '--files' and family == 'rg') \
                or (opt == '-g' and family in ('ag', 'ack')) or (opt == '-f' and family == 'ack')
            if opt in ('-e', '--regexp') or (opt == '-g' and family in ('ag', 'ack')):
                pattern_given = True
            elif opt in ('-f', '--file'):
                pattern_given = True
                if value is not None:
                    out.items.append((value, 'path'))
            elif opt in ('--exclude-from', '--include-from', '--ignore-file', '--path-to-ignore') \
                    or (opt == '-p' and family == 'ag'):
                if value is not None:
                    out.items.append((value, 'path'))
            elif opt == '--files' and family == 'rg':
                pattern_given = True
            if (len(opt) == 2 and opt[1] in shorts_only) or opt in longs_only:
                out.names_only = True
            if opt in ('--include', '-g', '--glob', '--iglob') and value is not None:
                text = value.text
                (out.excludes if text.startswith('!') else out.includes).append(text.lstrip('!'))
            elif opt in ('--exclude', '--exclude-dir') and value is not None:
                out.excludes.append(value.text)
            elif opt in ('-t', '--type', '-T', '--type-not') and family in ('rg', 'grep'):
                out.typed = True
        searching = pattern_given or bool(positional)          # rg --version searches nothing
        # getopt_walk also reports an option value that follows an operand as an operand (a tool that
        # stops at its first operand reads it as a file); grep, rg, ag and ack read options anywhere, so
        # for the folders searched such a value (rg src -e /, rg TODO --threads 1) is no operand
        roots = [a for a in positional if id(a) not in values]
        if not pattern_given and positional:
            positional, roots = positional[1:], roots[1:]
        out.items.extend((a, 'path') for a in positional)
        if searching and not lists_files:
            out.roots = roots
        return out
    if name in ('sed', 'gsed'):
        kept, k = [], 0
        while k < len(args):                                     # BSD sed -i '' / -i .bak: a suffix
            if args[k].text in ('-i', '-I') and k + 1 < len(args) \
                    and (args[k + 1].text == '' or re.match(r'^\.[\w.-]*$', args[k + 1].text)):
                kept.append(make_arg('--in-place'))
                k += 2
                continue
            kept.append(args[k])
            k += 1
        args = kept
        positional, given = [], False
        for ev in getopt_walk(args, SED_SPEC):
            if ev[0] == 'arg':
                positional.append(ev[1])
            elif ev[1] in ('-e', '--expression') and ev[2] is not None:
                given = True
                out.sed_scripts.append(ev[2].text)
            elif ev[1] in ('-f', '--file') and ev[2] is not None:
                given = True
                out.items.append((ev[2], 'path'))
                text = read_script_file(ev[2], cwds, written)
                if text is not None:
                    out.sed_scripts.append(text)
        if not given and positional:
            out.sed_scripts.append(positional[0].text)
            positional = positional[1:]
        out.items.extend((a, 'path') for a in positional)
        return out
    if name in ('awk', 'gawk', 'mawk', 'nawk'):
        positional, given = [], False
        for ev in getopt_walk(args, AWK_SPEC):
            if ev[0] == 'arg':
                positional.append(ev[1])
            elif ev[1] in ('-f', '--file', '-E', '--exec', '-i', '--include') and ev[2] is not None:
                given = given or ev[1] not in ('-i', '--include')
                out.items.append((ev[2], 'path'))
                text = read_script_file(ev[2], cwds, written)
                if text is not None:
                    out.code.append(text)
            elif ev[1] in ('-e', '--source') and ev[2] is not None:
                given = True
                out.code.append(ev[2].text)
        if not given and positional:
            out.code.append(positional[0].text)
            positional = positional[1:]
        out.items.extend((a, 'option' if '=' in a.text and NAME_RE.match(a.text) else 'path') for a in positional)
        return out
    use_opts = USE_OPTIONS.get(name, ())
    after_dashdash = False
    i = 0
    while i < len(args):
        a = args[i]
        t = a.text
        if not after_dashdash and t == '--':
            after_dashdash = True
            i += 1
            continue
        if not after_dashdash and t.startswith('-') and t != '-':
            if t in use_opts and i + 1 < len(args):
                out.use_values.add(args[i + 1])
                out.items.append((args[i + 1], 'path'))
                i += 2
                continue
            if name in ('scp', 'sftp', 'sshfs') and t in ('-o',) and i + 1 < len(args):
                value = args[i + 1]
                if value.text.lower().replace(' ', '').startswith(SSH_USE_KEYS):
                    out.use_values.add(value)
                out.items.append((value, 'option'))
                i += 2
                continue
            if name in ('scp', 'sftp', 'sshfs') and t.startswith('-o') and len(t) > 2:
                if t[2:].lower().replace(' ', '').startswith(SSH_USE_KEYS):
                    out.use_values.add(a)
            if '=' in t:
                if t.split('=', 1)[0] in use_opts:
                    out.use_values.add(a)
                out.items.append((a, 'option'))
            i += 1
            continue
        out.items.append((a, 'path'))
        i += 1
    return out


def use_ok(name, args):
    """True when this command's operands may name a credential location because it only uses a key."""
    if name in USE_ANY:
        return True
    if name in ('gpg', 'gpg2'):
        texts = [a.text for a in args]
        has_key_op = any(t in GPG_KEY_OPS for t in texts)
        content = any(t.split('=', 1)[0] in GPG_CONTENT_OPS or re.match(r'^-[a-zA-Z]*[cesbdo]', t)
                      for t in texts if t.startswith('-') and t not in GPG_KEY_OPS)
        return has_key_op and not content
    return False


def in_place(name, texts):
    if name in ('sed', 'gsed'):
        return any(t in ('-i', '-I') or re.match(r'^-[a-zA-Z]*i', t) or t.startswith('--in-place') for t in texts)
    return any(re.match(r'^-[a-zA-Z]*i', t) for t in texts)


def chmod_removes_read(texts):
    modes = [t for t in texts if not t.startswith('-') or re.match(r'^-[rwxXst]+$', t)]
    if not modes:
        return False
    mode = modes[0]
    if re.match(r'^[0-7]{3,4}$', mode):
        return not int(mode[-3]) & 4
    for clause in mode.split(','):
        m = re.match(r'^([ugoa]*)([-+=])([rwxXst]*)$', clause)
        if not m:
            continue
        who, op, perms = m.groups()
        hits_user = who == '' or 'u' in who or 'a' in who
        if hits_user and ((op == '-' and 'r' in perms) or (op == '=' and 'r' not in perms)):
            return True
    return False


def self_or_config(arg, cwds):
    if arg.unknown:
        return False
    for c in cwds or [None]:
        ref = PathRef(arg.text, c)
        for p in (ref.lex, ref.real):
            if is_self(p) or is_config_dir(p):
                return True
    return False


def check_write_target(arg, cwds, by):
    if arg is None or arg.unknown or arg.text in ('/dev/null', '/dev/stdout', '/dev/stderr', '-'):
        return
    for c in cwds or [None]:
        ref = PathRef(arg.text, c)
        if is_self(ref.lex) or is_self(ref.real):
            raise self_block('%s writing %s' % (by, pretty(ref.lex or ref.text)))
        found = classify(ref, writing=True)
        if found and found[0] == 'secret':
            raise Block('%s writing into %s' % (by, found[1]),
                        'it is a credential location; writing there can plant keys or break logins.')


def copy_positional(name, args):
    shorts = COPY_VALUE_SHORT.get(name, '')
    longs_v = {'--target-directory', '--suffix', '--backup'} if name != 'rsync' else set()
    events = getopt_walk(args, (shorts, longs_v, set(), ''))
    target = None
    positional = []
    for ev in events:
        if ev[0] == 'arg':
            positional.append(ev[1])
        elif ev[1] in ('-t', '--target-directory') and ev[2] is not None and name != 'scp':
            target = ev[2]
    return positional, target


def copy_destination(name, args):
    positional, target = copy_positional(name, args)
    if target is not None:
        return target
    return positional[-1] if len(positional) >= 2 else None


def copy_sources(name, args):
    positional, target = copy_positional(name, args)
    return positional if target is not None else positional[:-1]


def copy_targets(src, dest, cwds):
    """Where a copy of src lands: inside dest when dest is a folder, the folder itself for a
    contents copy (src/. or rsync's src/)."""
    out = []
    if src.unknown or dest.unknown:
        return out
    base = posixpath.basename(canon(src.text).rstrip('/'))
    for c in cwds or [None]:
        dref = PathRef(dest.text, c)
        if not dref.lex:
            continue
        is_dir = fs_isdir(dref.lex) or canon(dest.text).endswith('/') or is_config_dir(dref.lex)
        if not is_dir:
            continue
        if base in ('', '.') or src.text.endswith('/'):
            if is_config_dir(dref.lex) or is_self(dref.lex):
                raise self_block('copying a folder\'s contents over %s' % pretty(dref.lex))
            continue
        names = [base]
        if src.globby:                                 # kernel/* lands as every name it matches
            names = [posixpath.basename(m.rstrip('/')) for m in glob_matches(src.text, c)] or [base]
            if is_config_dir(dref.lex):                # and, unmatched here, as whatever it may match
                names += [s for s in SELF_NAMES if fnmatch.fnmatch(s, base.lower())]
        for name in names:
            landing = posixpath.join(dref.lex, name)
            if is_config_dir(landing) and not fs_isfile(PathRef(src.text, c).lex):
                raise self_block('copying a folder onto %s, merging into the safety layer'
                                 % pretty(landing), UNPACK_HINT)
            out.append(make_arg(landing))
    return out


# ----------------------------------------------------------------------------------------------------
# Unpacking: an archive extracted, a diff applied or a site downloaded into a folder. What lands there
# is named inside the archive, the diff or the server's reply, not on the command line, so the folder
# decides (unpack_target): inside the safety layer, a config folder such as ~/.claude, or a folder
# above one such as ~ is refused, unless the command names members that all land elsewhere.
# ----------------------------------------------------------------------------------------------------
SELF_NAMES = ('scripts', 'settings.json', 'settings.local.json')
UNPACK_HINT = ('Unpack into the specific folder instead (for example tar -C ~/.claude/rules, unzip -d '
               '~/.claude/skills), or name the members to extract. The scripts folder and settings.json '
               'change through the Edit tool, which asks the user first, or by the user running the '
               'command themselves.')
TAR_VALUE_SHORT = 'bCfFgIKNTVX'
TAR_AMBIGUOUS = 'HLs'          # a value in one tar and a flag in the other (GNU -H FORMAT, bsdtar -s PAT)
TAR_LONG_VALUES = {
    '--add-file', '--after-date', '--blocking-factor', '--block-size', '--cd', '--checkpoint-action',
    '--directory', '--exclude', '--exclude-from', '--exclude-ignore', '--exclude-ignore-recursive',
    '--exclude-tag', '--exclude-tag-all', '--exclude-tag-under', '--file', '--files-from', '--format',
    '--gid', '--gname', '--group', '--group-map', '--hole-detection', '--include', '--index-file',
    '--info-script', '--label', '--level', '--listed-incremental', '--mode', '--mtime', '--new-volume-script',
    '--newer', '--newer-mtime', '--newer-mtime-than', '--newer-than', '--no-quote-chars', '--older',
    '--older-mtime', '--older-mtime-than', '--older-than', '--options', '--owner', '--owner-map',
    '--passphrase', '--pax-option', '--quote-chars', '--quoting-style', '--record-size', '--rmt-command',
    '--rsh-command', '--sort', '--sparse-version', '--starting-file', '--strip-components', '--suffix',
    '--tape-length', '--to-command', '--transform', '--uid', '--uname', '--use-compress-program',
    '--volno-file', '--warning', '--xattrs-exclude', '--xattrs-include', '--xform',
}
TAR_LONG_FLAGS = {
    '--absolute-names', '--absolute-paths', '--acls', '--anchored', '--append', '--atime-preserve',
    '--auto-compress', '--backup', '--block-number', '--bzip2', '--catenate', '--check-device',
    '--check-links', '--checkpoint', '--chroot', '--clamp-mtime', '--clear-nochange-fflags', '--compare',
    '--compress', '--concatenate', '--confirmation', '--create', '--delay-directory-restore', '--delete',
    '--dereference', '--diff', '--exclude-backups', '--exclude-caches', '--exclude-caches-all',
    '--exclude-caches-under', '--exclude-vcs', '--exclude-vcs-ignores', '--extract', '--fflags',
    '--force-local', '--full-time', '--get', '--gunzip', '--gzip', '--hard-dereference', '--help',
    '--hfsCompression', '--ignore-case', '--ignore-command-error', '--ignore-failed-read', '--ignore-zeros',
    '--incremental', '--insecure', '--interactive', '--keep-directory-symlink', '--keep-newer-files',
    '--keep-old-files', '--list', '--lrzip', '--lz4', '--lzip', '--lzma', '--lzop', '--mac-metadata',
    '--multi-volume', '--no-acls', '--no-anchored', '--no-auto-compress', '--no-check-device',
    '--no-delay-directory-restore', '--no-fflags', '--no-ignore-case', '--no-ignore-command-error',
    '--no-mac-metadata', '--no-null', '--no-overwrite-dir', '--no-recursion', '--no-same-owner',
    '--no-same-permissions', '--no-seek', '--no-selinux', '--no-unquote', '--no-verbatim-files-from',
    '--no-wildcards', '--no-wildcards-match-slash', '--no-xattrs', '--nodump', '--norecurse', '--null',
    '--numeric-owner', '--occurrence', '--old-archive', '--one-file-system', '--one-top-level',
    '--overwrite', '--overwrite-dir', '--portability', '--posix', '--preserve-order',
    '--preserve-permissions', '--read-full-records', '--read-sparse', '--recursion', '--recursive-unlink',
    '--remove-files', '--restrict', '--safe-writes', '--same-order', '--same-owner', '--same-permissions',
    '--seek', '--selinux', '--show-defaults', '--show-omitted-dirs', '--show-snapshot-field-ranges',
    '--show-stored-names', '--show-transformed-names', '--skip-old-files', '--sparse', '--test-label',
    '--to-stdout', '--totals', '--touch', '--uncompress', '--ungzip', '--unlink-first', '--unquote',
    '--update', '--usage', '--utc', '--verbatim-files-from', '--verbose', '--verify', '--version',
    '--wildcards', '--wildcards-match-slash', '--xattrs', '--xz', '--zstd',
}
TAR_SPEC = (TAR_VALUE_SHORT, TAR_LONG_VALUES, TAR_LONG_FLAGS, '')
TAR_MODES = {'-x': 'x', '--extract': 'x', '--get': 'x', '-c': 'c', '--create': 'c', '-r': 'c',
             '--append': 'c', '-u': 'c', '--update': 'c', '-t': 't', '--list': 't', '-d': 't',
             '--diff': 't', '--compare': 't', '-A': 'c', '--catenate': 'c', '--concatenate': 'c',
             '--delete': 'c', '--test-label': 't'}
COMPRESS_PROGRAMS = {'gzip', 'pigz', 'bzip2', 'pbzip2', 'lbzip2', 'xz', 'pixz', 'zstd', 'pzstd', 'lz4',
                     'lzip', 'plzip', 'lzop', 'brotli', 'lrzip', 'compress', 'gunzip', 'unzstd'}
CPIO_SPEC = ('CDEFHIMOR', {'--block-size', '--directory', '--file', '--format', '--io-size', '--message',
                           '--owner', '--passphrase', '--pattern-file', '--rename-batch-file', '--rsh-command',
                           '--warning'}, set(), '')


class Unpack(object):
    """Where an unpacking command writes: places as (folder text or None for the working directory,
    member texts or None when they cannot be told)."""
    __slots__ = ('by', 'places', 'unsafe')

    def __init__(self, by):
        self.by, self.places, self.unsafe = by, [], None


def join_folder(prev, text):
    """tar -C and friends are relative to the folder before them."""
    text = canon(text)
    if prev is None or text.startswith('/'):
        return text
    return posixpath.join(prev, text)


def tar_args(args):
    """tar's arguments with an old-style first word spelled out: `tar xzf a.tgz` as -x -z -f a.tgz."""
    if not args or args[0].unknown or not re.match(r'^[A-Za-z]+$', args[0].text):
        return list(args)
    out, rest = [], list(args[1:])
    for c in args[0].text:
        out.append(make_arg('-' + c))
        if c in TAR_VALUE_SHORT and rest:
            out.append(rest.pop(0))
    return out + rest


def tar_unpack(name, args):
    events = getopt_walk(tar_args(args), TAR_SPEC)
    values = set(id(ev[2]) for ev in events if ev[0] == 'opt' and ev[2] is not None)
    modes, folder, chain, placed = set(), None, [], []
    unclear = stdout = absolute = from_file = False
    for ev in events:
        if ev[0] == 'arg':
            if id(ev[1]) not in values:             # getopt_walk repeats a late option value as an operand
                placed.append((ev[1], folder))
            continue
        opt, value = ev[1], ev[2]
        if opt in TAR_MODES:
            modes.add(TAR_MODES[opt])
        elif opt in ('-O', '--to-stdout', '--to-command'):
            stdout = True
        elif opt in ('-P', '--absolute-names', '--absolute-paths', '--insecure'):
            absolute = True
        elif opt in ('-C', '--directory', '--cd') and value is not None:
            folder = join_folder(folder, value.text)
            chain.append(folder)
        elif opt in ('-T', '--files-from'):
            from_file = True
        elif opt == '-I' and value is not None:     # GNU: a compressor; bsdtar: the list of members
            from_file = from_file or posixpath.basename(value.text.split(' ')[0]) not in COMPRESS_PROGRAMS
        elif opt in ('--transform', '--xform', '--strip-components', '--no-anchored', '--include') \
                or (len(opt) == 2 and opt[1] in TAR_AMBIGUOUS) \
                or (opt.startswith('--') and opt not in TAR_LONG_VALUES and opt not in TAR_LONG_FLAGS):
            unclear = True      # members renamed or cut short, matched at any depth (--no-anchored), added
                                # (bsdtar --include), or an option this table cannot read
    if any(a.unknown for a in args):
        unclear = True
        if not modes:
            modes.add('x')                          # a mode hidden in an unknown word: assume the worst
    if 'x' not in modes or stdout:
        return None
    plan = Unpack(name + ' extracting an archive')
    if absolute:
        plan.unsafe = 'with -P, which writes the absolute and ../ paths stored in the archive'
    elif from_file:
        plan.unsafe = 'with member names read from a file (-T), which can also switch folders (-C)'
    final = chain[-1] if chain else None
    if not placed:
        plan.places.append((final, None))
    for a, f in placed:                             # GNU: the -C before it; bsdtar: the last -C
        texts = None if unclear or a.unknown else [a.text]
        for where in {f, final}:
            plan.places.append((where, texts))
    return plan


def unzip_unpack(name, args):
    folder, archive, members = None, None, []
    unclear = unsafe = excluding = False
    i = 0
    while i < len(args):
        a = args[i]
        t = a.text
        if a.unknown:
            unclear = True
        elif t.startswith('-') and len(t) > 1:
            excluding = False
            letters, k = t[1:], 0
            while k < len(letters):
                c = letters[k]
                if c in 'dPIO':                                     # -d DIR, -P password, -I/-O charset
                    value = letters[k + 1:]
                    if not value and i + 1 < len(args):
                        i += 1
                        value = args[i].text
                        unclear = unclear or args[i].unknown
                    if c == 'd':
                        folder = value
                    break
                if c in 'lvtzZpc':                                  # list, test, comment, info, to stdout
                    return None
                if c == 'x':
                    excluding = True
                elif c == 'j':
                    unclear = True                                  # junk paths: every file lands flat
                elif c == ':':
                    unsafe = True
                k += 1
        elif archive is None:
            archive = a
        elif not excluding:
            members.append(t)
        i += 1
    plan = Unpack(name + ' extracting an archive')
    if unsafe:
        plan.unsafe = 'with -:, which writes the ../ paths stored in the archive'
    plan.places.append((folder, None if unclear or not members else members))
    return plan


def sevenzip_unpack(name, args):
    command = archive = folder = None
    members, unclear = [], False
    plan = Unpack(name + ' extracting an archive')
    for a in args:
        t = a.text
        low = t.lower()
        if a.unknown:
            unclear = True
        elif low.startswith('-') and len(t) > 1:
            if low.startswith('-o'):
                folder = t[2:] or None
            elif low == '-so':
                return None
            elif low.startswith('-spf'):
                plan.unsafe = 'with -spf, which writes the absolute paths stored in the archive'
            elif low.startswith(('-i', '-ai', '-an')):
                unclear = True                                      # members from a switch or a list file
        elif t.startswith('@'):
            unclear = True
        elif command is None:
            command = low
        elif archive is None:
            archive = t
        else:
            members.append(t)
    if command not in ('x', 'e'):
        return None
    unclear = unclear or command == 'e'                             # e extracts every file flat
    plan.places.append((folder, None if unclear or not members else members))
    return plan


def cpio_unpack(name, args):
    events = getopt_walk(args, CPIO_SPEC)
    flags = set(ev[1] for ev in events if ev[0] == 'opt')
    operands = [ev[1] for ev in events if ev[0] == 'arg']
    folder = None
    for ev in events:
        if ev[0] == 'opt' and ev[1] in ('-D', '--directory') and ev[2] is not None:
            folder = join_folder(folder, ev[2].text)
    extracting = flags & {'-i', '--extract'} and not flags & {'-t', '--list', '--to-stdout'}
    passing = flags & {'-p', '--pass-through'}
    if not extracting and not passing:
        return None
    plan = Unpack(name + (' extracting an archive' if extracting else ' copying files'))
    bsd = name == 'bsdcpio' or (name == 'cpio' and MACOS)          # macOS ships libarchive's cpio
    if extracting and (('--insecure' in flags) if bsd else ('--no-absolute-filenames' not in flags)):
        plan.unsafe = ('with --insecure, which writes absolute and ../ paths' if bsd else
                       'without --no-absolute-filenames, so it writes the absolute and ../ paths stored '
                       'in the archive')
    unclear = bool(flags & {'-f', '--nonmatching', '-E', '--pattern-file', '-r', '--rename',
                            '--rename-batch-file'}) or any(a.unknown for a in args)
    if passing:
        plan.places.append((join_folder(folder, operands[0].text) if operands else folder, None))
    else:
        members = [a.text for a in operands]
        plan.places.append((folder, None if unclear or not members else members))
    return plan


def ditto_unpack(name, args, cwds):
    """macOS ditto: -x unpacks an archive, and a plain copy puts a folder's CONTENTS into the
    destination (ditto src dst is cp -R src/. dst)."""
    texts = [a.text for a in args]
    operands, i = [], 0
    while i < len(args):
        if texts[i] in ('--arch', '--bom', '--zlibCompressionLevel', '--password'):
            i += 2
            continue
        if not texts[i].startswith('-'):
            operands.append(args[i])
        i += 1
    short = [t for t in texts if re.match(r'^-[a-zA-Z]+$', t)]
    if len(operands) < 2 or operands[-1].unknown or any('c' in t for t in short):
        return None                                     # -c creates an archive: a plain write target
    dest = operands[-1]
    if any('x' in t for t in short):
        plan = Unpack(name + ' extracting an archive')
    else:
        plan = Unpack(name + ' copying a folder\'s contents')
        files = all(not s.unknown and any(fs_isfile(PathRef(s.text, c).lex) for c in cwds or [None])
                    for s in operands[:-1])
        if files:
            return None                                 # plain files: the copy checks judge them
    plan.places.append((dest.text, None))
    return plan


def patch_unpack(name, args):
    """patch writes the files its diff names, below -d DIR or the working directory; an explicit
    file operand or -o is a plain write target (judged by the caller)."""
    events = getopt_walk(args, ('BDFVYdiopzrg', {
        '--basename-prefix', '--directory', '--fuzz', '--get', '--ifdef', '--input', '--output', '--prefix',
        '--quoting-style', '--read-only', '--reject-file', '--strip', '--suffix', '--version-control'},
        {'--dry-run'}, ''))
    folder, targets, operands = None, [], []
    for ev in events:
        if ev[0] == 'arg':
            operands.append(ev[1])
        elif ev[1] == '--dry-run':
            return None, []
        elif ev[1] in ('-d', '--directory') and ev[2] is not None:
            folder = join_folder(folder, ev[2].text)
        elif ev[1] in ('-o', '--output', '-r', '--reject-file') and ev[2] is not None:
            targets.append(ev[2])
    if operands:
        targets.append(operands[0] if folder is None else make_arg(join_folder(folder, operands[0].text)))
        return None, targets
    plan = Unpack(name + ' applying a diff')
    plan.places.append((folder, None))
    return plan, targets


def member_parts(text):
    """The path parts under the destination where a member lands, cut before its first wildcard or
    backslash (a pattern matches anything below its literal part, and GNU tar reads \\164 as t)."""
    parts = []
    for seg in canon(text).split('/'):
        if not seg or seg == '.':
            continue
        if any(ch in seg for ch in '*?[\\'):
            break
        parts.append(seg)
    return parts


def check_unpack(plan, cwds):
    if plan.unsafe:
        raise self_block('%s %s' % (plan.by, plan.unsafe), UNPACK_HINT)
    for folder, members in plan.places:
        for c in cwds or [None]:
            ref = PathRef(folder if folder is not None else '.', c)
            if SENT in ref.text:                        # a folder computed at run time below a known one
                if ref.prefix and unpack_target(ref.prefix):
                    raise self_block('%s into an unknown folder under %s' % (plan.by, pretty(ref.prefix)),
                                     UNPACK_HINT)
                continue
            for base in (ref.lex, ref.real):
                if not base:
                    continue
                for m in members if members is not None else [None]:
                    full = base
                    if m is not None:
                        parts = member_parts(m)
                        full = posixpath.normpath(posixpath.join(base, *parts)) if parts else base
                    if unpack_target(full) or unpack_target(fs_realpath(full)):
                        raise self_block('%s into %s%s, where it can replace the safety layer\'s files'
                                         % (plan.by, pretty(base), ' (member %s)' % m if m else ''),
                                         UNPACK_HINT)


def unpack_plan(name, args, cwds):
    """The Unpack plan of an archive, diff or download command, or None."""
    if name in ('tar', 'bsdtar', 'gtar'):
        return tar_unpack(name, args)
    if name in ('unzip', 'bsdunzip'):
        return unzip_unpack(name, args)
    if name in ('7z', '7za', '7zz', '7zr'):
        return sevenzip_unpack(name, args)
    if name in ('cpio', 'gcpio', 'bsdcpio'):
        return cpio_unpack(name, args)
    if name == 'ditto':
        return ditto_unpack(name, args, cwds)
    if name == 'patch':
        return patch_unpack(name, args)[0]
    if name in ('wget', 'curl'):
        return download_unpack(name, args)
    return None


def download_unpack(name, args):
    """A download whose file names the server chooses: wget -r / -m / --content-disposition, curl -J.
    Both tools take a long option by any unambiguous prefix (curl in any case) and wget with =on / =off,
    so any prefix of one of these, with any value, counts."""
    texts = [a.text for a in args]
    short = [t for t in texts if re.match(r'^-[a-zA-Z]+$', t)]
    keys = [t.split('=', 1)[0].lower() for t in texts if t.startswith('--') and len(t.split('=', 1)[0]) > 4]
    if name == 'wget':
        chosen = any(o.startswith(k) for o in ('--recursive', '--mirror', '--page-requisites',
                                               '--content-disposition', '--trust-server-names') for k in keys) \
            or any(not t.startswith('-n') and any(c in t for c in 'rmp') for t in short)
    else:
        chosen = any('--remote-header-name'.startswith(k) for k in keys) or any('J' in t for t in short)
    if not chosen:
        return None
    plan = Unpack(name + ' saving files under names the server chooses')
    plan.places.append((download_folder(name, args), None))
    return plan


def download_folder(name, args):
    """wget -P / --directory-prefix, curl --output-dir: the folder downloads are saved in, or None."""
    folder = None
    for k, a in enumerate(args):
        t = a.text
        nxt = args[k + 1].text if k + 1 < len(args) else None
        if name == 'wget':
            if t in ('-P', '--directory-prefix') and nxt is not None:
                folder = nxt
            elif t.startswith('--directory-prefix='):
                folder = t.split('=', 1)[1]
            elif t.startswith('-P') and len(t) > 2:
                folder = t[2:]
        elif name == 'curl':
            if t == '--output-dir' and nxt is not None:
                folder = nxt
            elif t.startswith('--output-dir='):
                folder = t.split('=', 1)[1]
    return folder


def strip_wrappers(argv, ctx, evaluator):
    wrapped, cwd_override = False, None
    for _ in range(8):
        if not argv:
            break
        name = command_name(argv[0])
        if name not in WRAPPER_VALUE_OPTS:
            break
        if name == 'command' and len(argv) > 1 and argv[1].text in ('-v', '-V'):
            break
        if name not in CC_STRIPPED:
            wrapped = True
        value_opts = WRAPPER_VALUE_OPTS[name]
        i = 1
        while i < len(argv):
            t = argv[i].text
            if t == '--':
                i += 1
                break
            if name == 'env':
                split = None
                if t in ('-S', '--split-string') and i + 1 < len(argv):
                    split, skip = argv[i + 1], 2
                elif t.startswith('--split-string='):
                    split, skip = make_arg(t.split('=', 1)[1]), 1
                elif t.startswith('-S') and len(t) > 2:
                    split, skip = make_arg(t[2:]), 1
                if split is not None:                               # env -S "rm -rf x": a command line
                    if split.unknown:
                        raise ParseError('env -S with a value that cannot be known')
                    words = [tok[1] for tok in Lexer(split.text).run() if tok[0] == 'word']
                    fields = []
                    for w in words:
                        fields.extend(evaluator.expand(w, ctx))
                    argv = argv[:i] + fields + argv[i + skip:]
                    wrapped = True
                    continue
                if t in ('-C', '--chdir') and i + 1 < len(argv):
                    cwd_override = resolve_dir(argv[i + 1].text, ctx.cwd)
                    i += 2
                    continue
                if t.startswith('--chdir='):
                    cwd_override = resolve_dir(t.split('=', 1)[1], ctx.cwd)
                    i += 1
                    continue
                if t.startswith('-C') and len(t) > 2:
                    cwd_override = resolve_dir(t[2:], ctx.cwd)
                    i += 1
                    continue
                m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', t, re.S)
                if m:
                    ctx.vars[m.group(1)] = None if SENT in m.group(2) else m.group(2)
                    i += 1
                    continue
            if not t.startswith('-') or t == '-':
                break
            i += 2 if (t in value_opts and '=' not in t) else 1
        if name == 'timeout' and i < len(argv):
            i += 1                                                      # the duration
        argv = argv[i:]
    return argv, wrapped, cwd_override


def resolve_dir(text, cwd):
    if SENT in text:
        return SENT
    text = canon(text)
    if not text.startswith('/'):
        if not cwd:
            return SENT
        text = posixpath.join(cwd, text)
    return posixpath.normpath(text)


def change_dir(name, args, ctx):
    ops = [a for a in args if not re.match(r'^-[LPe@]+$', a.text)]
    before = cwd_opts(ctx)
    if name == 'popd':
        if ops and re.match(r'^[-+]\d+$', ops[0].text):
            set_cwd_opts(ctx, [None])
            return
        if ctx.dirstack:
            ctx.oldpwd = ctx.cwd
            set_cwd_opts(ctx, [ctx.dirstack.pop()])
        return
    if name == 'pushd' and not ops:
        if ctx.dirstack:
            top = ctx.dirstack.pop()
            ctx.dirstack.append(ctx.cwd)
            ctx.oldpwd = ctx.cwd
            set_cwd_opts(ctx, [top])
        return
    if name == 'pushd' and re.match(r'^[-+]\d+$', ops[0].text):
        set_cwd_opts(ctx, [None])
        return
    if not ops:
        targets = [ctx.home()]
    elif ops[0].text == '-':
        targets = [ctx.oldpwd]
    elif len(ops) > 1 and name == 'cd':
        targets = [None]                                                # zsh `cd old new`
    else:
        targets = []
        for base in before:
            t = resolve_dir(ops[0].text, base)
            targets.append(None if t == SENT else t)
    if name == 'pushd':
        ctx.dirstack.append(ctx.cwd)
    ctx.oldpwd = ctx.cwd
    set_cwd_opts(ctx, targets)


BRACE_RE = re.compile(r'\{([^{}]*,[^{}]*)\}')


def expand_braces(text, limit=64):
    out = [text]
    for _ in range(limit):
        new, changed = [], False
        for t in out:
            m = BRACE_RE.search(t)
            if not m:
                new.append(t)
                continue
            changed = True
            for alt in m.group(1).split(','):
                new.append(t[:m.start()] + alt + t[m.end():])
        out = new[:limit]
        if not changed:
            break
    return out


def glob_matches(pattern, cwd):
    if SENT in pattern:
        return []
    pattern = canon(pattern)
    absolute = pattern if pattern.startswith('/') else (posixpath.join(cwd, pattern) if cwd else None)
    if absolute is None:
        return []
    return fs_glob(absolute)


def glob_dir_prefix(pattern):
    """The deepest literal directory of a glob pattern (`~/.ssh/*` -> `~/.ssh`)."""
    parts = pattern.split('/')
    keep = []
    for p in parts:
        if any(c in p for c in '*?['):
            break
        keep.append(p)
    if len(keep) == len(parts):
        return None
    return '/'.join(keep) or '/'


def path_refs(arg, cwds, split=True):
    """Candidate paths named by one argument, under every directory the command could run in: the
    word, its option value, src:dst halves, @file, and the matches of a glob."""
    texts = expand_braces(arg.text)
    pieces = []
    for t in texts:
        pieces.append(t)
        if split:
            if '=' in t:
                pieces.append(t.split('=', 1)[1])
            for sep in (':', ','):
                if sep in t:
                    for piece in t.split(sep):
                        pieces.append(piece)
                        if '=' in piece:
                            pieces.append(piece.split('=', 1)[1])
    refs, seen = [], set()
    for p in pieces[:MAX_PIECES]:
        if split and p.startswith('@'):
            p = p[1:]
        if split and p.startswith('-') and p != arg.text:
            continue
        if not p:
            continue
        for cwd in cwds or [None]:
            if (p, cwd) in seen:
                continue
            seen.add((p, cwd))
            refs.append(PathRef(p, cwd))
            if arg.globby and SENT not in p:
                prefix = glob_dir_prefix(p)
                if prefix and not posixpath.basename(p).lower().endswith('.pub'):
                    refs.append(PathRef(prefix, cwd))
                for match in glob_matches(p, cwd):
                    refs.append(PathRef(match, cwd))
    return refs


def has_flag(args, short=(), long=()):
    for a in args:
        t = a.text
        if t == '--':
            break
        if t.startswith('--'):
            if t.split('=', 1)[0] in long:
                return True
        elif t.startswith('-') and len(t) > 1 and any(c in t[1:] for c in short):
            if t[1:].isalpha():
                return True
    return False


def is_recursive_reader(name, args):
    if name in ('grep', 'egrep', 'fgrep', 'zgrep', 'ugrep'):
        events = getopt_walk(args, GREP_SPEC)
        return any(ev[0] == 'opt' and (ev[1] in ('-r', '-R', '--recursive', '--dereference-recursive')
                                       or (ev[1] in ('-d', '--directories') and ev[2] is not None
                                           and ev[2].text == 'recurse')) for ev in events)
    if name in ('rg', 'ag'):
        return has_flag(args, 'u.', ('--hidden', '--unrestricted', '--no-ignore'))
    if name in ('tar', 'bsdtar', 'gtar'):
        first = args[0].text if args else ''
        if first and not first.startswith('-') and re.match(r'^[A-Za-z]+$', first):
            return any(c in first for c in 'cru')
        return has_flag(args, 'cru', ('--create', '--append', '--update'))
    if name == 'zip':
        return has_flag(args, 'rR', ('--recurse-paths',))
    if name in ('cp', 'gcp'):
        return has_flag(args, 'rRa', ('--recursive', '--archive'))
    if name == 'scp':
        return has_flag(args, 'r', ())
    if name in ('7z', '7za', '7zz'):
        return bool(args) and args[0].text == 'a'
    return name in ('rsync', 'ditto', 'rclone')


def check_recursive_contents(name, args, items, spec, cwds):
    """A recursive search or archive whose top folder holds a hard env file or a credential file
    prints or packs it. (Local copies such as cp -r and rsync are left alone: they stay on this disk.)"""
    is_search = name in GREP_FAMILY
    if not is_search and name not in ARCHIVERS and name not in ('scp', 'rclone'):
        return
    if is_search and spec.typed:
        return
    dirs = [a for a, role in items if role == 'path' and not a.unknown]
    if not dirs:
        dirs = [make_arg('.')]
    follows = follows_symlinks(name, args)
    for d in dirs:
        for c in cwds or [None]:
            ref = PathRef(d.text, c)
            if not ref.lex or not fs_isdir(ref.lex):
                continue
            try:
                entries = fs_listdir(ref.lex)[:MAX_LISTING]
            except OSError:
                continue
            for entry in entries:
                full = posixpath.join(ref.lex, entry)
                entry_ref = PathRef(full, None)
                if not follows and fs_islink(full):
                    entry_ref.real = None                       # a link the walk does not follow
                found = classify(entry_ref)
                if found is None or found[0] == 'ancestor' or (found[0] == 'env' and not is_search):
                    continue
                if spec.includes and not any(fnmatch.fnmatch(entry, p) for p in spec.includes):
                    continue
                if any(fnmatch.fnmatch(entry, p) for p in spec.excludes):
                    continue
                if found[0] == 'env':
                    hint = ("Exclude env files: add --exclude='.env*' to grep, or use rg without --hidden "
                            "(or with -g '!.env*'). %s --from <path> lists key NAMES." % HELPER)
                    raise Block('a recursive %s over %s, which holds %s' % (name, pretty(ref.lex), entry),
                                'a recursive search prints matching lines of that env file, values included.',
                                hint)
                raise Block('a recursive %s over %s, which holds %s' % (name, pretty(ref.lex), entry),
                            'that file is a credential; a recursive search or archive takes it along.',
                            'Point it at the specific files or exclude that one.')


def check_whole_disk_search(name, args, cwds, stdin):
    """A recursive search (grep -r, rg, ag, ack) that starts at the whole disk or the home folder, in
    any output mode (-l, -c and -q read every file too). Listing file names (rg --files, ag -g,
    ack -f) is left alone, like find. Without a folder operand the search covers its working folder,
    unless its input comes from a pipe, xargs or a < redirect (rg, ag, ack then read it; GNU grep -r does not)."""
    family = 'grep' if name in ('egrep', 'fgrep', 'zgrep', 'ugrep') else name
    if family == 'grep' and not is_recursive_reader(name, args):
        return
    if family in ('ag', 'ack') and has_flag(args, 'n', ('--no-recurse', '--norecurse')):
        return
    roots = operand_spec(name, args).roots
    if roots is None:
        return
    if not roots:
        if stdin is not None and family != 'grep':          # GNU grep -r searches the folder anyway
            return
        roots = [make_arg('.')]
    for a in roots:
        if a.unknown:
            continue
        for text in expand_braces(a.text):
            for c in cwds or [None]:
                ref = PathRef(text, c)
                for p in (ref.lex, ref.real):
                    if is_search_root(p):
                        raise search_block('a recursive search (%s)' % name, ref.lex or p)


def archive_inputs(name, args):
    """What an archive being created packs, as [(operand text, folder it is read from or None)], and the
    exclude patterns that count as covering a file of that name at any depth: tar --exclude without a /
    (GNU tar and bsdtar match it against each name in a member's path), zip -x starting with * (zip
    matches the stored path, so -x .env leaves project/.env in), and 7z -xr! (recursive) without a /."""
    inputs, excludes = [], []
    if name in ('tar', 'bsdtar', 'gtar'):
        events = getopt_walk(tar_args(args), TAR_SPEC)
        values = set(id(ev[2]) for ev in events if ev[0] == 'opt' and ev[2] is not None)
        folder, recursion = None, True
        for ev in events:
            if ev[0] == 'arg':
                if id(ev[1]) not in values and not ev[1].unknown and recursion:
                    inputs.append((ev[1].text, folder))
            elif ev[1] in ('-C', '--directory', '--cd') and ev[2] is not None:
                folder = join_folder(folder, ev[2].text)
            elif ev[1] in ('--no-recursion', '--norecurse', '--recursion'):
                recursion = ev[1] == '--recursion'      # --no-recursion dir packs the folder entry only
            elif ev[1] == '--exclude' and ev[2] is not None and not re.search(r'[/\\]', ev[2].text):
                excludes.append(ev[2].text)
        return inputs, excludes
    positional = []
    if name == 'zip':                       # zip [options] archive inputs... [-x pattern...] [-i pattern...]
        listing, k = None, 0
        while k < len(args):
            t = args[k].text
            if t in ('-x', '--exclude', '-i', '--include'):
                listing = 'x' if t in ('-x', '--exclude') else 'i'
            elif t.startswith('-') and t != '-':
                listing = None
                k += 1 if t in ZIP_VALUE_OPTS else 0
            elif listing == 'x':
                if t.startswith('*'):
                    excludes.append(t)
            elif listing is None:
                positional.append(args[k])
            k += 1
        files = positional[1:]
    else:                                   # 7z a archive inputs... -xr!pattern
        for a in args:
            m = re.match(r'^-xr!([^/\\]+)$', a.text, re.IGNORECASE)
            if m:
                excludes.append(m.group(1))
            elif not (a.text.startswith('-') and len(a.text) > 1):
                positional.append(a)
        files = positional[2:] if len(positional) > 2 else [make_arg('.')]
    return [(a.text, None) for a in files if not a.unknown], excludes


def check_archive_env(name, args, cwds):
    """An archive created from a folder that directly holds a hard env file packs its secret values,
    unless an exclude pattern covers that file. Env files in subfolders are not looked for."""
    inputs, excludes = archive_inputs(name, args)
    follows = follows_symlinks(name, args)
    for text, folder in inputs:
        for c in cwds or [None]:
            ref = PathRef(join_folder(folder, text), c)
            if not ref.lex or not fs_isdir(ref.lex):
                continue
            try:
                entries = fs_listdir(ref.lex)[:MAX_LISTING]
            except OSError:
                continue
            for entry in entries:
                full = posixpath.join(ref.lex, entry)
                if env_tier(entry) != 'hard' or (not follows and fs_islink(full)) or not fs_isfile(full):
                    continue
                if any(fnmatch.fnmatch(entry, p) for p in excludes):
                    continue
                raise Block('%s packing %s, which holds %s' % (name, pretty(ref.lex), entry),
                            'the archive takes that env file along, secret values included, wherever the '
                            'archive goes next.',
                            'Exclude the env files (%s) or archive only the folders you need, such as src.'
                            % ARCHIVE_EXCLUDE_HINT['zip' if name == 'zip' else '7z' if name.startswith('7')
                                                   else 'tar'])


def follows_symlinks(name, args):
    """Whether a recursive walk reads what a symbolic link inside the folder points to."""
    if name in ('grep', 'egrep', 'fgrep', 'zgrep', 'ugrep'):
        return any(ev[0] == 'opt' and ev[1] in ('-R', '--dereference-recursive') for ev in getopt_walk(args, GREP_SPEC))
    if name == 'rg':
        return has_flag(args, 'L', ('--follow',))
    if name == 'ag':
        return has_flag(args, 'f', ('--follow',))
    if name in ('tar', 'bsdtar', 'gtar'):
        return has_flag(args, 'hL', ('--dereference',))
    if name == 'zip':
        return not has_flag(args, 'y', ('--symlinks',))
    return True


def find_candidates(root, cwds, tests, negated):
    """Sensitive files a find over root could hand on: what its name tests match among the usual
    sensitive names, or, with no name test, the sensitive files sitting at the top of root."""
    out = []
    for c in cwds or [None]:
        rref = PathRef(root.text, c)
        names = []
        if tests:
            names = [s for s in SENSITIVE_SAMPLES if any(find_test_matches(t, p, root.text, s) for t, p in tests)]
        elif rref.lex and fs_isdir(rref.lex):
            try:
                entries = fs_listdir(rref.lex)[:MAX_LISTING]
            except OSError:
                entries = []
            for e in entries:
                hit = classify(PathRef(posixpath.join(rref.lex, e), None))
                if hit and hit[0] in ('secret', 'env'):
                    names.append(e)
        for s in names:
            if any(find_test_matches(t, p, root.text, s) for t, p in negated):
                continue
            path = posixpath.join(canon(root.text), s)
            if path not in out:
                out.append(path)
        break
    return out


def find_test_matches(test, pattern, root, name):
    if SENT in pattern:
        return True
    if test in ('-name', '-iname'):
        return fnmatch.fnmatchcase(name.lower() if test == '-iname' else name,
                                   pattern.lower() if test == '-iname' else pattern)
    full = posixpath.join(canon(root), name)
    if test in ('-regex', '-iregex'):
        try:
            return re.fullmatch(pattern, full, re.I if test == '-iregex' else 0) is not None
        except re.error:
            return True
    return fnmatch.fnmatch(full.lower(), pattern.lower()) if test.startswith('-i') else fnmatch.fnmatch(full, pattern)


def rm_flags(texts):
    r = f = False
    for t in texts:
        if t == '--':
            break
        if t.startswith('--'):
            opt = resolve_long(t.split('=', 1)[0], RM_LONG)
            r = r or opt == '--recursive'
            f = f or opt == '--force'
        elif t.startswith('-') and len(t) > 1 and t[1:].isalpha():
            r = r or 'r' in t or 'R' in t
            f = f or 'f' in t
    return r, f


def check_mv(args, cwd, ctx):
    """An mv that would replace an existing file. The last of -f / -i / -n wins, as in GNU and BSD mv;
    a backup (-b, --backup other than none/off) keeps the old content."""
    mode = 'f'
    backup = None
    no_target_dir = False
    target_dir = None
    operands = []
    for ev in getopt_walk(args, ('tS', {'--target-directory', '--suffix', '--context'}, set(MV_LONG), '')):
        if ev[0] == 'arg':
            operands.append(ev[1])
            continue
        opt, value = ev[1], ev[2]
        opt = resolve_long(opt, MV_LONG) if opt.startswith('--') else opt
        if opt in ('-f', '--force'):
            mode = 'f'
        elif opt in ('-i', '--interactive'):
            mode = 'i'
        elif opt in ('-n', '--no-clobber'):
            mode = 'n'
        elif opt == '--update' and value is not None and value.text in ('none', 'none-fail'):
            mode = 'n'
        elif opt == '-b':
            backup = 'existing'
        elif opt == '--backup':
            backup = value.text if value is not None else 'existing'
        elif opt in ('-T', '--no-target-directory'):
            no_target_dir = True
        elif opt in ('-t', '--target-directory'):
            target_dir = value
    if backup is not None:
        control = backup if backup != 'existing' else (ctx.lookup('VERSION_CONTROL') or 'existing')
        if control not in ('none', 'off'):
            return
    if mode in ('n', 'i'):
        return
    words = []
    for a in operands:
        if a.globby and not a.unknown:
            matches = sorted(glob_matches(a.text, cwd))
            words.extend(make_arg(m) for m in matches) if matches else words.append(a)
        else:
            words.append(a)
    if target_dir is not None:
        dest, sources = target_dir, words
    else:
        if len(words) < 2:
            return
        dest, sources = words[-1], words[:-1]
    if dest.unknown:
        return
    dref = PathRef(dest.text, cwd)
    if not dref.lex:
        return
    # mv treats the destination as a directory when -t names it, when it ends in '/', or when there are
    # several sources; if it is not one, mv fails without moving anything. A directory that an earlier
    # `mkdir -p dir &&` creates does not exist yet when the hook runs.
    dest_is_dir = not no_target_dir and (fs_isdir(dref.lex) or target_dir is not None
                                         or dest.text.endswith('/') or len(sources) > 1)
    for src in sources:
        text = src.text
        if SENT in text:
            if not dest_is_dir and (fs_lexists(dref.lex) or dref.lex in ctx.created):
                raise mv_block(dref.lex)
            continue
        sref = PathRef(text, cwd)
        if not sref.lex:
            continue
        target = posixpath.join(dref.lex, posixpath.basename(sref.lex.rstrip('/'))) if dest_is_dir else dref.lex
        if target == sref.lex:
            continue
        if fs_lexists(target) or target in ctx.created:
            try:
                if fs_lexists(sref.lex) and fs_samefile(sref.lex, target):
                    continue                                            # case-only rename
            except OSError:
                pass
            raise mv_block(target)
        ctx.created.add(target)
        ctx.created.discard(sref.lex)


def check_cp(args, cwd, ctx):
    """A cp that would replace an existing file, judged like check_mv: the last of -f / -i / -n wins, and
    a backup (-b, --backup other than none/off) keeps the old content, and -u (--update, --update=older)
    replaces only a destination older than the source. Copying a folder (cp -R dir dest) is left alone:
    it merges into an existing folder, which builds and installs do all the time."""
    mode = 'f'
    backup = update = None
    no_target_dir = parents = False
    target_dir = None
    operands = []
    for ev in getopt_walk(args, ('tS', {'--target-directory', '--suffix', '--sparse', '--no-preserve'},
                                 set(CP_LONG), '')):
        if ev[0] == 'arg':
            operands.append(ev[1])
            continue
        opt, value = ev[1], ev[2]
        opt = resolve_long(opt, CP_LONG) if opt.startswith('--') else opt
        if opt in ('-f', '--force'):
            mode = 'f'
        elif opt in ('-i', '--interactive'):
            mode = 'i'
        elif opt in ('-n', '--no-clobber'):
            mode = 'n'
        elif opt == '--update' and value is not None and value.text in ('none', 'none-fail'):
            mode = 'n'
        elif opt in ('-u', '--update'):
            update = value.text if value is not None else 'older'
        elif opt == '-b':
            backup = 'existing'
        elif opt == '--backup':
            backup = value.text if value is not None else 'existing'
        elif opt in ('-T', '--no-target-directory'):
            no_target_dir = True
        elif opt in ('-t', '--target-directory'):
            target_dir = value
        elif opt == '--parents':
            parents = True
    if backup is not None:
        control = backup if backup != 'existing' else (ctx.lookup('VERSION_CONTROL') or 'existing')
        if control not in ('none', 'off'):
            return
    if mode in ('n', 'i'):
        return
    words = []
    for a in operands:
        if a.globby and not a.unknown:
            matches = sorted(glob_matches(a.text, cwd))
            words.extend(make_arg(m) for m in matches) if matches else words.append(a)
        else:
            words.append(a)
    if target_dir is not None:
        dest, sources = target_dir, words
    else:
        if len(words) < 2:
            return
        dest, sources = words[-1], words[:-1]
    if dest.unknown:
        return
    dref = PathRef(dest.text, cwd)
    if not dref.lex:
        return
    dest_is_dir = not no_target_dir and (fs_isdir(dref.lex) or target_dir is not None
                                         or dest.text.endswith('/') or len(sources) > 1)

    def replaces(path):
        return fs_isfile(path) or path in ctx.created

    def keeps_newer(source, path):
        """cp -u leaves a destination alone unless the source is newer; a failed stat counts as newer."""
        if update != 'older':
            return False
        src_time, dest_time = fs_mtime(source), fs_mtime(path)
        return src_time is not None and dest_time is not None and src_time <= dest_time

    for src in sources:
        text = src.text
        if SENT in text:
            if not dest_is_dir and replaces(dref.lex):
                raise cp_block(dref.lex)
            continue
        sref = PathRef(text, cwd)
        if not sref.lex or fs_isdir(sref.lex):
            continue                                                    # a folder copy: out of scope
        if not dest_is_dir:
            target = dref.lex
        elif parents:
            target = posixpath.normpath(posixpath.join(dref.lex, canon(text).lstrip('/')))
        else:
            target = posixpath.join(dref.lex, posixpath.basename(sref.lex.rstrip('/')))
        if target == sref.lex or not replaces(target) or keeps_newer(sref.lex, target):
            continue
        try:
            if fs_lexists(sref.lex) and fs_samefile(sref.lex, target):
                continue                                                # cp refuses: the same file
        except OSError:
            pass
        raise cp_block(target)


def check_docker(args, cwd):
    sub = None
    i = 0
    while i < len(args):
        t = args[i].text
        if sub is None:
            if t in ('-H', '--host', '-c', '--context', '--config', '-l', '--log-level'):
                i += 2
                continue
            if not t.startswith('-'):
                sub = t
                if sub not in ('run', 'create', 'container'):
                    return
            i += 1
            continue
        if t == '--privileged' or (t.startswith('--privileged=')
                                   and t.split('=', 1)[1].lower() not in ('false', '0', 'no', 'f')):
            raise Block('docker %s --privileged' % sub, 'a privileged container has full access to the host.')
        value = None
        if t in ('-v', '--volume', '--mount') and i + 1 < len(args):
            value = args[i + 1].text
            i += 1
        elif t.startswith(('--volume=', '--mount=')):
            value = t.split('=', 1)[1]
        elif t.startswith('-v') and len(t) > 2:
            value = t[2:].lstrip('=')
        if value is not None and SENT not in value:
            if t.startswith('--mount'):
                host = None
                for item in value.split(','):
                    k, _, v = item.partition('=')
                    if k in ('source', 'src'):
                        host = v
            elif DRIVE_RE.match(value):                             # C:\Users\me\x:/in/container
                host = value[:2] + value[2:].split(':', 1)[0]
            else:
                host = value.split(':', 1)[0]
            if host and (host.startswith(('/', '.', '~')) or DRIVE_RE.match(host)):
                ref = PathRef(expand_user(host), cwd)
                found = classify(ref)
                if found and found[0] in ('secret', 'ancestor'):
                    raise Block('a docker mount of %s' % found[1],
                                'mounting / or a directory that holds credentials hands them to the '
                                'container.')
                path = ref.lex or host
                base = posixpath.basename(path.rstrip('/')).lower()
                if base.endswith('.sock') and any(w in base for w in ('docker', 'podman', 'containerd')):
                    raise Block('a docker mount of the container socket %s' % path,
                                'a container that can reach the Docker socket controls the host as root.')
                ok = any(path == d or path.startswith(d + '/') for d in DOCKER_MOUNT_OK)
                if not ok and any(path == d or path.startswith(d + '/') for d in DOCKER_SYSTEM_DIRS):
                    raise Block('a docker mount of the system folder %s' % path,
                                'Docker runs as root on Linux, so a container with a system folder '
                                'mounted can read or rewrite the host.')
        i += 1


def diskutil_destructive(texts):
    verbs = [t.lower() for t in texts if not t.startswith('-')]
    if not verbs:
        return None
    if verbs[0] in DISKUTIL_FAMILIES:
        if len(verbs) > 1 and not verbs[1].startswith('list'):
            return ' '.join(verbs[:2])
        return None
    return verbs[0] if verbs[0] in DISKUTIL_DESTRUCTIVE else None


def git_parts(args, cwd):
    """Skip git's global options; return (cwd after -C, subcommand, its args, had global options,
    the -c / --config-env settings)."""
    i, had, configs = 0, False, []
    while i < len(args):
        t = args[i].text
        if t == '-C' and i + 1 < len(args):
            target = resolve_dir(args[i + 1].text, cwd)
            cwd = None if target == SENT else target
            i, had = i + 2, True
            continue
        if t in ('-c', '--config-env') and i + 1 < len(args):
            configs.append(args[i + 1].text)
            i, had = i + 2, True
            continue
        if t.startswith('--config-env='):
            configs.append(t.split('=', 1)[1])
            i, had = i + 1, True
            continue
        if t in ('--git-dir', '--work-tree', '--namespace', '--exec-path', '--super-prefix') and i + 1 < len(args):
            i, had = i + 2, True
            continue
        if t.startswith('-'):
            i, had = i + 1, True
            continue
        break
    sub = args[i].text if i < len(args) else ''
    return cwd, sub, args[i + 1:], had, configs


def check_git_hooks(sub, sub_args, configs, ctx):
    """git commit --no-verify / -n anywhere, and core.hooksPath set for the command: both skip the
    repository's pre-commit checks."""
    for cfg in configs:
        if cfg.split('=', 1)[0].strip().lower() == 'core.hookspath':
            raise hooks_block('git -c %s' % cfg)
    params = ctx.vars.get('GIT_CONFIG_PARAMETERS') or ''
    keys = [v for k, v in ctx.vars.items() if re.match(r'^GIT_CONFIG_KEY_\d+$', k) and v]
    if 'hookspath' in params.lower() or any(v.strip().lower() == 'core.hookspath' for v in keys):
        raise hooks_block('core.hooksPath set through GIT_CONFIG_* variables')
    texts = [a.text for a in sub_args]
    if sub == 'config':
        lowered = [t.lower() for t in texts]
        if 'core.hookspath' in lowered:
            k = lowered.index('core.hookspath')
            reading = any(t in ('--get', '--get-all', '--get-regexp', '--unset', '--unset-all', 'get',
                                'unset', '--show-origin', '-l', '--list') for t in lowered)
            if not reading and (k + 1 < len(texts) or 'set' in lowered):
                raise hooks_block('git config core.hooksPath')
    if sub == 'commit':
        skip = False
        for ev in getopt_walk(sub_args, COMMIT_SPEC):
            if ev[0] == 'opt':
                if ev[1] in ('-n', '--no-verify'):
                    skip = True
                elif ev[1] == '--verify':
                    skip = False
        if skip:
            raise hooks_block('git commit --no-verify / -n')


GIT_RESTORE_SPEC = ('s', {'--source', '--conflict', '--pathspec-from-file'},
                    {'--staged', '--worktree', '--patch', '--quiet', '--progress', '--no-progress', '--ours',
                     '--theirs', '--merge', '--ignore-unmerged', '--ignore-skip-worktree-bits',
                     '--recurse-submodules', '--no-recurse-submodules', '--overlay', '--no-overlay',
                     '--pathspec-file-nul'}, '')
GIT_CHECKOUT_SPEC = ('bB', {'--orphan', '--conflict', '--pathspec-from-file'},
                     {'--force', '--patch', '--ours', '--theirs', '--quiet', '--progress', '--no-progress',
                      '--track', '--no-track', '--guess', '--no-guess', '--detach', '--merge',
                      '--ignore-skip-worktree-bits', '--ignore-other-worktrees', '--overwrite-ignore',
                      '--no-overwrite-ignore', '--recurse-submodules', '--no-recurse-submodules', '--overlay',
                      '--no-overlay', '--pathspec-file-nul'}, '')
GIT_SWITCH_SPEC = ('cC', {'--create', '--force-create', '--orphan', '--conflict'},
                   {'--discard-changes', '--force', '--detach', '--guess', '--no-guess', '--merge', '--quiet',
                    '--progress', '--no-progress', '--track', '--no-track', '--ignore-other-worktrees',
                    '--recurse-submodules', '--no-recurse-submodules'}, '')


def git_opts(sub_args, spec):
    """(option names, operands before --, operands after --) of a git subcommand. A bundle such as -fq
    is read letter by letter, long options from unambiguous prefixes, as git does."""
    events, after, k = [], [], 0
    texts = [a.text for a in sub_args]
    if '--' in texts:
        k = texts.index('--')
        after, sub_args = sub_args[k + 1:], sub_args[:k]
    events = getopt_walk(sub_args, spec)
    names = set(ev[1] for ev in events if ev[0] == 'opt')
    values = set(id(ev[2]) for ev in events if ev[0] == 'opt' and ev[2] is not None)
    before = [ev[1] for ev in events if ev[0] == 'arg' and id(ev[1]) not in values]
    return names, before, after


def path_like(arg, cwd):
    """A git checkout operand that names files rather than a branch or commit. A lone name that is
    both (a docs branch and a docs folder) is the branch, as git reads it: git checkout docs switches."""
    t = arg.text
    if arg.unknown:
        return False
    if t in ('.', '..', '*') or t.startswith(('./', '../', ':', '*')) or any(c in t for c in '*?['):
        return True
    return bool(cwd) and t not in ('-', '@', 'HEAD') and fs_lexists(posixpath.join(cwd, canon(t))) \
        and not git_names_commit(cwd, t)


def git_names_commit(cwd, name):
    """True when git, run in cwd, reads name as a commit (branch, tag, hash); False when it does not, or
    when git is missing or slow."""
    import subprocess
    if not _native_abs(cwd):
        return False
    try:
        return subprocess.run(['git', 'rev-parse', '--verify', '--quiet', name + '^{commit}'],
                              cwd=_native_abs(cwd), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=3,
                              env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')).returncode == 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def check_git_discard(sub, sub_args, cwd):
    """Commands that throw away uncommitted work in the working tree (git checkout -- is the classic the
    settings deny; these are the same action spelled another way)."""
    if sub == 'restore':
        names, _, _ = git_opts(sub_args, GIT_RESTORE_SPEC)
        if names & {'-W', '--worktree'} or not names & {'-S', '--staged'}:
            raise discard_block('git restore of the working tree')
    elif sub == 'checkout':
        names, before, after = git_opts(sub_args, GIT_CHECKOUT_SPEC)
        if names & {'-f', '--force'}:
            raise discard_block('git checkout -f / --force')
        if names & {'-p', '--patch', '--ours', '--theirs', '--pathspec-from-file'} or after:
            raise discard_block('git checkout of paths (%s)' % ' '.join(a.text for a in sub_args)[:80])
        if len(before) > 1 or (before and path_like(before[0], cwd)):
            raise discard_block('git checkout of paths (%s)' % ' '.join(a.text for a in before)[:80])
    elif sub == 'switch':
        names, _, _ = git_opts(sub_args, GIT_SWITCH_SPEC)
        if names & {'-f', '--force', '--discard-changes'}:
            raise discard_block('git switch --discard-changes / -f')
    elif sub == 'stash' and sub_args and sub_args[0].text in ('drop', 'clear'):
        raise discard_block('git stash %s, which deletes stashed changes' % sub_args[0].text)


def git_apply_unpack(sub_args):
    """git apply writes the files its diff names, below the folder it runs in. git takes a long option
    by any unambiguous prefix (--app is --apply) and a --no- form of each (--stat --no-stat applies),
    so those count as writing."""
    texts = [a.text.split('=', 1)[0] for a in sub_args]
    if not any(len(t) > 2 and ('--apply'.startswith(t) or t.startswith('--no-')) for t in texts):
        if any(t in ('--check', '--stat', '--numstat', '--summary') for t in texts):
            return None
        if '--cached' in texts and '--index' not in texts:
            return None                                 # the index only, not the working tree
    plan = Unpack('git apply writing the files its diff names')
    if any(len(t) > 4 and '--unsafe-paths'.startswith(t) for t in texts):
        plan.unsafe = 'with --unsafe-paths, which writes outside the working tree'
    plan.places.append((None, None))
    return plan


def git_reads(args):
    _, sub, rest, _, _ = git_parts(args, None)
    if sub in ('show', 'diff', 'blame', 'annotate', 'grep', 'cat-file'):
        return True
    return sub == 'log' and any(a.text in ('-p', '--patch', '-u') for a in rest)


def git_deny(sub, args):
    if sub == 'push':
        if any(a in ('-f', '--force', '--force-if-includes') or a.startswith('--force-with-lease')
               or (a.startswith('+') and len(a) > 1) or re.match(r'^-[a-zA-Z]*f[a-zA-Z]*$', a) for a in args):
            return 'a force push'
    if sub == 'reset' and '--hard' in args:
        return 'git reset --hard'
    if sub == 'clean' and any(a == '--force' or re.match(r'^-[a-zA-Z]*[fd]', a) for a in args):
        return 'git clean -f/-d'
    if sub == 'branch' and ('-D' in args or ('--delete' in args and '--force' in args)):
        return 'git branch -D'
    if sub == 'checkout' and '--' in args:
        return 'git checkout -- (discards changes)'
    if sub == 'commit' and any(a in ('--no-verify', '--all') or re.match(r'^-[a-zA-Z]*[na][a-zA-Z]*$', a) for a in args):
        return 'git commit --no-verify/-n/-a'
    return None


PRIVILEGE = {'sudo', 'su', 'doas', 'pkexec'}


def deny_class(name, args):
    """The settings.json deny-list classics, for commands hidden from the permission rules."""
    if name in PRIVILEGE:
        return 'privilege escalation (%s)' % name
    if name == 'rm' and rm_flags(args)[0]:
        return 'a recursive rm'
    if name == 'chmod' and any(a in ('-R', '--recursive') or re.match(r'^-[a-zA-Z]*R', a)
                               or re.match(r'^(0?777|0?666|[ugoa]*\+[rwxXt]*s[rwxXt]*|0?[2467][0-7]{3})$', a)
                               for a in args):
        return 'chmod -R / 777 / 666 / setuid'
    if name == 'chown':
        return 'chown'
    if name == 'git' and args:
        _, sub, rest, _, _ = git_parts([make_arg(a) for a in args], None)
        return git_deny(sub, [a.text for a in rest])
    if name.startswith('mkfs') or name == 'dd':
        return name
    if name == 'npm' and args and (args[0] == 'publish' or (args[0] in ('install', 'i', 'add')
                                                            and any(a in ('-g', '--global') for a in args))):
        return 'npm publish / global install'
    if name in ('shutdown', 'reboot', 'halt', 'poweroff', 'pkill', 'launchctl'):
        return name
    if name == 'mv' and any(resolve_long(a.split('=', 1)[0], MV_LONG) == '--force'
                            or re.match(r'^-[a-zA-Z]*f', a) for a in args):
        return 'mv -f'
    return None


def download_outputs(name, args):
    """Files curl/wget/fetch write (as Args). Empty when the download goes to stdout."""
    outs, urls, remote_name, to_stdout = [], [], False, False
    i = 0
    while i < len(args):
        t = args[i].text
        nxt = args[i + 1] if i + 1 < len(args) else None
        if re.match(r'^(?:https?|ftp|file)://', t):
            urls.append(t)
        elif name == 'curl':
            if t in ('-o', '--output') and nxt is not None:
                outs.append(nxt)
                i += 1
            elif t.startswith('--output='):
                outs.append(make_arg(t.split('=', 1)[1]))
            elif t in ('-O', '--remote-name', '--remote-name-all'):
                remote_name = True
            elif t.startswith('-') and not t.startswith('--') and len(t) > 1:
                letters = t[1:]
                if 'O' in letters:
                    remote_name = True
                if 'o' in letters:
                    rest = letters.split('o', 1)[1]
                    if rest:
                        outs.append(make_arg(rest))
                    elif nxt is not None:
                        outs.append(nxt)
                        i += 1
        elif name in ('wget', 'fetch'):
            if t in ('-O', '--output-document', '-o') and nxt is not None and name == 'wget' and t != '-o':
                if nxt.text == '-':
                    to_stdout = True
                else:
                    outs.append(nxt)
                i += 1
            elif t.startswith('--output-document='):
                v = t.split('=', 1)[1]
                if v == '-':
                    to_stdout = True
                else:
                    outs.append(make_arg(v))
            elif t.startswith('-') and not t.startswith('--') and 'O' in t[1:]:
                rest = t[1:].split('O', 1)[1]
                value = rest if rest else (nxt.text if nxt is not None else '')
                if not rest and nxt is not None:
                    i += 1
                if value == '-':
                    to_stdout = True
                elif value:
                    outs.append(make_arg(value))
            elif name == 'fetch' and t == '-o' and nxt is not None:
                if nxt.text == '-':
                    to_stdout = True
                else:
                    outs.append(nxt)
                i += 1
        i += 1
    if to_stdout or any(a.text in STDOUT_NAMES for a in outs):
        return []
    folder = download_folder(name, args)                    # curl --output-dir, wget -P
    if name == 'curl' and folder is not None:
        outs = [make_arg(join_folder(folder, a.text)) for a in outs]
    if name == 'curl' and remote_name or (name in ('wget', 'fetch') and not outs):
        for u in urls:
            path = re.sub(r'^[a-z]+://[^/]*', '', u).split('?', 1)[0].split('#', 1)[0]
            base = posixpath.basename(path) or 'index.html'
            outs.append(make_arg(join_folder(folder, base) if folder is not None else base))
    return outs


def is_decoder(name, args):
    """base64 -d, xxd -r, openssl ... -d, uudecode: output is code nobody has read."""
    if name in ('base64', 'basenc', 'base32'):
        return any(a in ('-d', '-D', '--decode') or re.match(r'^-[a-zA-Z]*[dD]$', a) for a in args)
    if name == 'xxd':
        return any(re.match(r'^-[a-zA-Z]*r', a) for a in args)
    if name == 'openssl':
        return '-d' in args or '-decode' in args
    return name in ('uudecode', 'b64decode')


def downloaded_paths(outs, cwds):
    paths = set()
    for a in outs:
        if a.unknown:
            continue
        for c in cwds or [None]:
            ref = PathRef(a.text, c)
            for p in (ref.lex, ref.real):
                if p:
                    paths.add(p)
    return paths


def sed_effects(script):
    """(files read, files written, commands run, runs text it cannot see) for a sed script: the r / R
    / w / W commands and the w flag of s, the e command, and s///e or a bare e."""
    reads, writes, runs, opaque = [], [], [], False
    s, i, n = script, 0, len(script)

    def rest_of_line(k):
        e = s.find('\n', k)
        return (s[k:] if e < 0 else s[k:e]).strip(), (n if e < 0 else e)

    def skip_delimited(k, delim):
        while k < n and s[k] != delim:
            k += 2 if s[k] == '\\' else 1
        return k + 1

    while i < n:
        c = s[i]
        if c in ' \t\n;{}!':
            i += 1
            continue
        if c == '#':
            _, i = rest_of_line(i)
            continue
        if c.isdigit() or c in '$,~+':                                   # an address
            i += 1
            continue
        if c == '/':
            i = skip_delimited(i + 1, '/')
            continue
        if c == '\\' and i + 1 < n:
            i = skip_delimited(i + 2, s[i + 1])
            continue
        if c in 'rRwW':
            name, i = rest_of_line(i + 1)
            (reads if c in 'rR' else writes).append(name)
            continue
        if c == 'e':
            command, i = rest_of_line(i + 1)
            if command:
                runs.append(command)
            else:
                opaque = True
            continue
        if c in 'aic:btTvqQlL':
            if c in 'aic':
                _, i = rest_of_line(i + 1)
            else:
                i += 1
                while i < n and s[i] not in ';\n}':
                    i += 1
            continue
        if c in 'sy' and i + 1 < n:
            delim = s[i + 1]
            i = skip_delimited(i + 2, delim)
            i = skip_delimited(i, delim)
            if c == 's':
                while i < n and s[i] not in ';\n}':
                    if s[i] == 'w':
                        name, i = rest_of_line(i + 1)
                        writes.append(name)
                        break
                    if s[i] == 'e':
                        opaque = True
                    i += 1
            continue
        i += 1
    return reads, writes, runs, opaque


# PowerShell options that take a value (and their usual short forms), so the value is not read as the
# command.
PS_VALUE_OPTIONS = {
    '-executionpolicy', '-ex', '-ep', '-windowstyle', '-w', '-win', '-version', '-v', '-inputformat', '-inp',
    '-if', '-outputformat', '-o', '-of', '-configurationname', '-config', '-workingdirectory', '-wd',
    '-psconsolefile', '-settingsfile', '-settings', '-custompipename', '-encodedarguments', '-ea',
}


def decode_powershell(b64, shell):
    import base64
    import binascii
    try:
        return base64.b64decode(b64, validate=True).decode('utf-16-le')
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise ParseError('%s -EncodedCommand that does not decode as base64 UTF-16' % shell)


def check_windows_code(code, shell, env=None):
    """Command text for cmd or PowerShell: what check_code_text looks for (with %VAR% and $env:VAR
    expanded first, so %APPDATA%\\gcloud is seen as the gcloud folder), plus the Windows forms of a
    recursive delete, a disk wipe, an env-file read, download-and-run and an edit of the safety layer."""
    if not code or not code.replace(SENT, '').strip():
        return
    # A part that cannot be known is left out; the known text is still checked (unlike inline code
    # elsewhere, a cmd or PowerShell line is mostly literal words around a variable or two).
    text = expand_windows_vars(code.replace(SENT, ' '), env if env is not None else os.environ)
    check_code_text(text, shell)
    for token in WIN_PATH_TOKEN_RE.findall(text):            # paths a variable expanded to: judged as paths
        found = classify(PathRef(token, None))
        if found and found[0] == 'secret':
            raise secret_block(found[1], '%s code' % shell)
    hard = [t for t in TEXT_ENV_RE.findall(text) if env_tier(t) == 'hard']
    if hard and WIN_READ_RE.search(text):
        raise env_block(hard[0], '%s code' % shell)
    if WIN_RMTREE_RE.search(text):
        raise Block('a recursive delete in %s code (%s)' % (shell, WIN_RMTREE_RE.search(text).group(0)[:80]),
                    'it deletes whole trees with no prompt and no undo.',
                    'Ask the user which path to delete and let them run it themselves.')
    if WIN_DISK_RE.search(text):
        raise Block('%s code that formats, wipes or repartitions a disk' % shell,
                    'it destroys everything on that disk.')
    if WIN_FETCH_RE.search(text) and WIN_RUN_RE.search(text):
        raise download_block('%s code that downloads a script and runs it (Invoke-Expression / iex)' % shell)
    if SELF_TEXT_RE.search(text) and WIN_WRITE_RE.search(text):
        raise self_block('%s code that writes %s' % (shell, SELF_TEXT_RE.search(text).group(0)))
    if WIN_UNPACK_RE.search(text):                  # Expand-Archive, tar -x, robocopy into a config folder
        named = CONFIG_TEXT_RE.search(text)
        if named:
            raise self_block('%s code that unpacks or copies a folder into %s' % (shell, named.group(0)),
                             UNPACK_HINT)
        for token in WIN_PATH_TOKEN_RE.findall(text):
            if re.match(r'^/[A-Za-z]$', token):
                continue                            # a switch such as /C or /E, not drive C: or E:
            lex = PathRef(token, None).lex
            if unpack_target(lex):
                raise self_block('%s code that unpacks or copies a folder into %s' % (shell, pretty(lex)),
                                 UNPACK_HINT)


def check_code_text(code, interpreter):
    if not code or SENT in code:
        return
    m = TEXT_SECRET_RE.search(code)
    if m:
        raise secret_block(m.group(0).strip(' \'"'), 'inline %s code' % interpreter)
    hard = [t for t in TEXT_ENV_RE.findall(code) if env_tier(t) == 'hard']
    if hard and CODE_READ_RE.search(code):
        raise env_block(hard[0], 'inline %s code' % interpreter)
    if TEXT_RMTREE_RE.search(code):
        raise Block('a recursive delete in inline %s code' % interpreter,
                    'it is rm -rf by another name.',
                    'Ask the user which path to delete and let them run it themselves.')
    if SELF_TEXT_RE.search(code) and CODE_WRITE_RE.search(code):
        raise self_block('inline %s code that writes %s' % (interpreter, SELF_TEXT_RE.search(code).group(0)))
    for m in CODE_UNPACK_RE.finditer(code):
        text = code
        if m.group(1) in ('copytree', 'cpSync', 'cp'):  # a backup FROM ~/.claude is fine: judge the target
            dest = copy_destination_text(code, m.end())
            if dest is not None and re.search('[\'"`]', dest):
                text = dest
        named = CONFIG_TEXT_RE.search(text)
        if named:
            raise self_block('inline %s code that unpacks or copies a folder into %s'
                             % (interpreter, named.group(0)), UNPACK_HINT)


def copy_destination_text(code, start):
    """The arguments after the first one of the call whose arguments begin at start (a copy's
    destination), or None when there is none or the parentheses do not close."""
    depth, comma, i = 0, None, start
    while i < len(code):
        c = code[i]
        if c in '\'"`':
            i += 1
            while i < len(code) and code[i] != c:
                i += 2 if code[i] == '\\' else 1
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            if depth == 0:
                return code[comma + 1:i] if comma is not None else None
            depth -= 1
        elif c == ',' and depth == 0 and comma is None:
            comma = i
        i += 1
    return None


# ----------------------------------------------------------------------------------------------------
# Block messages
# ----------------------------------------------------------------------------------------------------
def secret_block(label, by):
    return Block('%s on %s' % (by or 'a command', label),
                 'it is a credential location (keys, tokens, cookies). Its contents must never reach '
                 'the conversation, be copied elsewhere, or leave the machine.')


def env_block(label, by):
    return Block('reading the values of the env file %s (%s)' % (label, by),
                 'every .env / .env.* / .envrc except .env.shared and templates holds secret values '
                 'that must never enter the conversation.',
                 'Run `%s --from <path>` to see key NAMES (add --classify for each key\'s state), or '
                 'read .env.shared for the soft values. Passing the file as config (--env-file) is fine.'
                 % HELPER)


def self_block(what, hint=None):
    return Block(what, 'settings.json, settings.local.json and ~/.claude/scripts are the safety layer '
                       'itself; a shell command that changes them could switch every check off.',
                 hint or 'Change them with the Edit tool, which asks the user first, or ask the user to make '
                         'the change themselves.')


def discard_block(what):
    return Block(what, 'it throws away uncommitted work (changes in the working tree, or a stash), and git '
                       'keeps no copy of it to bring back.',
                 'Set the changes aside with git stash (git stash pop brings them back) or commit them; '
                 'git restore --staged only unstages and stays allowed, and git switch changes branches. '
                 'If the changes really should go, ask the user to run the command themselves.')


def hooks_block(what):
    return Block(what, 'it skips the repository\'s pre-commit hooks (lint, tests, secret scanning).',
                 'Commit normally and fix what the hook reports; if a hook really must be skipped, '
                 'ask the user to run the commit themselves.')


def mv_block(target):
    return Block('an mv that would silently overwrite %s' % pretty(target),
                 'mv replaces an existing destination without asking, and the old content is gone.',
                 'Check what is at the destination first. Choose a new name, or ask the user before '
                 'replacing it.')


def cp_block(target):
    return Block('a cp that would silently overwrite %s' % pretty(target),
                 'cp replaces an existing file without asking, and the old content is gone.',
                 'Check what is at the destination first. Choose a new name, use cp -n (never overwrites), '
                 'or ask the user before replacing it.')


def search_block(by, path):
    return Block('%s over %s' % (by, pretty(path)),
                 'that is the whole disk, a whole drive, or the whole home folder (or a folder holding it): '
                 'the search reads every file below it, which can run for many minutes and use up the '
                 'computer\'s memory until it stops responding.',
                 'Search a specific folder instead: the project folder (such as . or src) or a folder inside '
                 'the home folder (such as ~/Documents/<project>).')


def download_block(what):
    return Block(what, 'it runs code that nobody has read (downloaded, or decoded on the fly) with your '
                       'permissions.',
                 'Download to a file, show it to the user, and let them decide whether to run it.')


# ----------------------------------------------------------------------------------------------------
# Entry
# ----------------------------------------------------------------------------------------------------
FORK_BOMB_RE = re.compile(r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:|(\w+)\s*\(\)\s*\{[^}]*\b\1\s*\|\s*\1\s*&')


def check_bash(command, cwd):
    if len(command) > MAX_COMMAND_CHARS:
        raise ParseError('longer than %d characters' % MAX_COMMAND_CHARS)
    if FORK_BOMB_RE.search(command):
        raise Block('a fork bomb', 'it exhausts the machine\'s process table.')
    ctx = Ctx(canon(cwd), shell_env())
    Evaluator(0).run_string(command, ctx, wrapped=False)


def check_read(tool_input, cwd):
    fp = tool_input.get('file_path')
    if not isinstance(fp, str) or not fp:
        return
    found = classify(PathRef(expand_user(canon(fp)), canon(cwd)))
    if found and found[0] == 'secret':
        raise secret_block(found[1], 'the Read tool')
    if found and found[0] == 'env':
        raise env_block(found[1], 'the Read tool')


def check_grep(tool_input, cwd):
    """The Grep tool (ripgrep). Claude Code runs it with --hidden, so a folder search reads dot-files too;
    it skips gitignored files and what the Read deny rules name. The checks: a search aimed at a
    credential location, at a hard env file, at a home folder that holds credential folders, at a folder
    whose top level holds a credential file (~/.claude and its copies hold Claude Code's login), or with
    a glob that picks out env or key files, printing content; and, in every output mode, a search over
    the whole disk or the home folder."""
    path = tool_input.get('path')
    cwd = canon(cwd)
    path = expand_user(canon(path)) if isinstance(path, str) and path else cwd
    mode = tool_input.get('output_mode') or 'files_with_matches'
    content = mode == 'content'
    ref = PathRef(path, cwd)
    found = classify(ref)
    if found and found[0] == 'secret':
        raise secret_block(found[1], 'the Grep tool')
    if content and found and found[0] == 'env':
        raise env_block(found[1], 'the Grep tool')
    if content and found and found[0] == 'ancestor':
        raise Block('a Grep content search over %s' % found[1],
                    'that folder contains credential locations (~/.ssh, ~/.aws, ...), so matching lines '
                    'from them can be printed.', 'Search the specific project folder instead.')
    for p in (ref.lex, ref.real):
        if is_search_root(p):                                       # in every output mode
            raise search_block('a Grep search', ref.lex or p)
    held = content and not tool_input.get('type') and grep_reaches_credential(ref.lex, tool_input.get('glob'))
    if held:
        raise Block('a Grep content search over %s, which holds %s' % (pretty(ref.lex), held),
                    'that file is a credential, and the search prints its matching lines.',
                    'Search a specific subfolder or file instead (for example ~/.claude/rules).')
    pattern = tool_input.get('glob')
    if content and isinstance(pattern, str) and pattern:
        base = pattern.rsplit('/', 1)[-1]
        for sample in SENSITIVE_SAMPLES:
            if fnmatch.fnmatch(sample, base):
                hit = classify(PathRef(sample, None))
                if hit and hit[0] in ('env', 'secret'):
                    raise Block('a Grep content search with the glob %s, whose file-name part also matches %s'
                                % (pattern, 'secret env files' if hit[0] == 'env' else 'credential files'),
                                'a glob makes the search read matching files even where .gitignore hides '
                                'them, and it prints their lines.',
                                'Set the Grep path to the folder you mean (for example ~/.claude/rules or src) '
                                'and leave the glob out, or give it a file type such as *.md.')


def grep_reaches_credential(folder, globs):
    """The name of a credential file or folder at the top of a folder the Grep tool searches, or None.
    The tool does not follow symbolic links, and its glob parameter (patterns split on spaces and on
    commas outside braces, ! to exclude) narrows which files it reads."""
    if not folder or not fs_isdir(folder):
        return None
    patterns = []
    for piece in (globs.split() if isinstance(globs, str) else []):
        patterns.extend([piece] if '{' in piece and '}' in piece else [p for p in piece.split(',') if p])
    includes = [p.rsplit('/', 1)[-1] for p in patterns if not p.startswith('!')]
    excludes = [p[1:].rsplit('/', 1)[-1] for p in patterns if p.startswith('!') and len(p) > 1]
    try:
        entries = fs_listdir(folder)[:MAX_LISTING]
    except OSError:
        return None
    for entry in entries:
        full = posixpath.join(folder, entry)
        entry_ref = PathRef(full, None)
        if fs_islink(full):
            entry_ref.real = None                               # a link the search does not follow
        found = classify(entry_ref)
        if not found or found[0] != 'secret':
            continue
        if includes and not any(fnmatch.fnmatch(entry, p) for p in includes):
            continue
        if not any(fnmatch.fnmatch(entry, p) for p in excludes):
            return entry
    return None


def write_stderr(text):
    """stderr as UTF-8 whatever the console's code page (Windows defaults to an ANSI one that cannot
    encode every path), and never an exception: a hook that crashes while blocking lets the call through."""
    try:
        sys.stderr.buffer.write(text.encode('utf-8', 'backslashreplace'))
        sys.stderr.flush()
    except AttributeError:
        sys.stderr.write(text)
    except (OSError, ValueError):
        pass


def emit_block(b, retry_ok=False):
    lines = ['BLOCKED by bash-safety-extended: %s.' % b.what, 'Why: %s' % b.why]
    if b.hint:
        lines.append(b.hint)
    if not retry_ok:
        lines.append(NO_WORKAROUND)
    write_stderr('\n'.join(lines) + '\n')
    sys.exit(2)


def emit_unanalysable(reason):
    emit_block(Block('the safety hook could not analyse this command (%s)' % reason,
                     'a command the hook cannot read could hide what it is there to stop, so it fails '
                     'closed.',
                     'Split it into simpler commands (one step per Bash call, fewer nested quotes, '
                     'substitutions and bash -c layers), or fix the quoting if it is a syntax error. '
                     'Do not use this to reach anything the hook would otherwise block.'),
               retry_ok=True)


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
        write_stderr('bash-safety-extended: unreadable hook input (%s); this call was not checked.\n' % exc)
        sys.exit(1)
    tool = data.get('tool_name')
    tool_input = data.get('tool_input') if isinstance(data.get('tool_input'), dict) else {}
    cwd = canon(data.get('cwd')) if isinstance(data.get('cwd'), str) else None
    if not cwd or not cwd.startswith('/'):
        cwd = canon(os.getcwd())
    # The Monitor tool runs its command in the same shell as Bash (a WebSocket watch has no command and
    # gets its own approval prompt from Claude Code).
    command = tool_input.get('command') if tool in ('Bash', 'Monitor') else None
    try:
        if tool == 'Read':
            check_read(tool_input, cwd)
        elif tool == 'Grep':
            check_grep(tool_input, cwd)
        elif tool in ('Bash', 'Monitor') and isinstance(command, str) and command.strip():
            check_bash(command, cwd)
        elif tool == 'PowerShell':
            emit_block(Block('a command for the PowerShell tool',
                             'this safety layer reads bash commands only, so a PowerShell command would run '
                             'unchecked.',
                             'Run it with the Bash tool (Git Bash) instead; PowerShell code can run from there '
                             'as powershell -NoProfile -Command \'...\', which this hook does check.'),
                       retry_ok=True)
    except Block as b:
        emit_block(b)
    except ParseError as exc:
        emit_unanalysable(str(exc))
    except RecursionError:
        emit_unanalysable('it nests too deeply')
    except Exception as exc:                                         # internal error: fail closed
        emit_unanalysable('internal error %s: %s' % (type(exc).__name__, exc))
    sys.exit(0)


if __name__ == '__main__':
    main()

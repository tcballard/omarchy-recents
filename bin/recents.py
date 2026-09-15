#!/usr/bin/env python3
"""Bounded local metadata reader. No shell evaluation, network or permanent deletion."""
import datetime as dt
import fnmatch
import functools
import re
import heapq
import json
import mimetypes
import os
from pathlib import Path
import selectors
import shlex
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
import xml.etree.ElementTree as ET

LIMIT = 2000
DEFAULT = json.loads((Path(__file__).parent.parent / 'config.default.json').read_text())
HOME = Path.home().resolve()
STATE = Path(os.environ.get('XDG_STATE_HOME', HOME / '.local/state')) / 'recents'
CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config')) / 'recents/config.json'
XBEL = Path(os.environ.get('XDG_DATA_HOME', HOME / '.local/share')) / 'recently-used.xbel'


def read_json(path, fallback):
    try:
        with path.open() as f:
            raw = f.read(16_000_001)
        if len(raw) > 16_000_000:
            raise ValueError('JSON exceeds 16 MB')
        return json.loads(raw)
    except FileNotFoundError:
        return fallback


def config():
    value = read_json(CONFIG, {})
    if not isinstance(value, dict):
        raise ValueError('Config must be a JSON object')
    c = {**DEFAULT, **value}
    for key, low, high in [('windowDays', 1, 365), ('maxDepth', 1, 12)]:
        if type(c[key]) is not int or not low <= c[key] <= high:
            raise ValueError(key + ' outside supported range')
    if not isinstance(c['sources'], dict):
        raise ValueError('sources must be an object')
    c['sources'] = {**DEFAULT['sources'], **c['sources']}
    if any(type(v) is not bool for v in c['sources'].values()):
        raise ValueError('source switches must be booleans')
    for key in ['extraRoots', 'excludeGlobs']:
        if not isinstance(c[key], list) or len(c[key]) > 32 or any(not isinstance(x, str) or len(x) > 4096 for x in c[key]):
            raise ValueError('Invalid ' + key)
    if not isinstance(c['openWith'], dict):
        raise ValueError('openWith must be an object')
    for cmd in c['openWith'].values():
        if not isinstance(cmd, (str, list)) or not cmd or (isinstance(cmd, list) and any(not isinstance(x, str) for x in cmd)):
            raise ValueError('openWith commands must be strings or argv arrays')
    return c


def atomic_json(name, data):
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if STATE.is_symlink() or STATE.stat().st_uid != os.getuid():
        raise ValueError('Unsafe state directory')
    fd, temp = tempfile.mkstemp(prefix='.write-', dir=STATE)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, ensure_ascii=True, separators=(',', ':'))
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, STATE / name)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def local_path(value):
    p = Path(value).expanduser().resolve()
    if p == HOME or not p.is_relative_to(HOME):
        return None
    return p


def uri_path(uri):
    u = urllib.parse.urlsplit(uri)
    if u.scheme != 'file' or u.netloc not in ('', 'localhost') or u.query or u.fragment:
        return None
    return local_path(urllib.parse.unquote(u.path, errors='strict'))


def allowed(p, c):
    parts = p.relative_to(HOME).parts
    return not any(x.startswith('.') or x == 'node_modules' for x in parts) and not any(
        fnmatch.fnmatch(p.name, pat) or fnmatch.fnmatch(str(p), pat)
        for pat in ['*.part', '*.crdownload', 'Unconfirmed*'] + c['excludeGlobs'])


def kind(path, mime=''):
    ext = path.suffix.lower()
    return kind_suffix(ext, mime)


@functools.lru_cache(maxsize=512)
def kind_suffix(ext, mime=''):
    mime = mime or mimetypes.guess_type('file' + ext)[0] or ''
    for prefix, name in [('image/', 'Images'), ('video/', 'Video'), ('audio/', 'Audio')]:
        if mime.startswith(prefix):
            return name
    if ext in ['.zip', '.gz', '.bz2', '.xz', '.tar', '.7z', '.rar', '.zst']:
        return 'Archives'
    if ext in ['.rs', '.py', '.js', '.ts', '.tsx', '.jsx', '.qml', '.c', '.cpp', '.h', '.go', '.sh', '.json', '.toml', '.yaml', '.html', '.css']:
        return 'Code'
    return 'Docs'


class Candidates:
    def __init__(self, c, now):
        self.config, self.now, self.rows = c, now, {}
        self.capped = False
        self.home_prefix = str(HOME) + '/'
        self.excluded = re.compile('|'.join(fnmatch.translate(p) for p in ['*.part', '*.crdownload', 'Unconfirmed*'] + c['excludeGlobs']))

    def add(self, path, timestamp, source, mime='', canonical=False):
        try:
            # GNU find -P never follows symlinks, starts at a canonical root,
            # and reports only regular files. Its paths need no per-file realpath.
            p = None if canonical else local_path(path)
            key = str(path) if canonical else str(p) if p else ''
            timestamp = min(float(timestamp), self.now)
            if not key.startswith(self.home_prefix) or timestamp < self.now - self.config['windowDays'] * 86400:
                return
            parts = key[len(self.home_prefix):].split('/')
            if any(x.startswith('.') or x == 'node_modules' for x in parts) or self.excluded.match(parts[-1]) or self.excluded.match(key):
                return
            row = self.rows.get(key)
            if row:
                row['ts'] = max(row['ts'], timestamp)
                row['sources'] = sorted(set(row['sources'] + [source]))
            else:
                self.rows[key] = dict(path=key, ts=timestamp, source=source, sources=[source], kind=kind_suffix(os.path.splitext(key)[1].lower(), mime))
            if len(self.rows) > 4000:
                self.trim()
        except (OSError, ValueError, OverflowError):
            pass

    def trim(self):
        if len(self.rows) > LIMIT:
            self.capped = True
            newest = heapq.nlargest(LIMIT, self.rows.values(), key=lambda r: (r['ts'], r['path']))
            self.rows = {r['path']: r for r in newest}


def roots(c):
    result = []
    for key in ['DESKTOP', 'DOCUMENTS', 'DOWNLOAD', 'PICTURES', 'VIDEOS', 'MUSIC']:
        try:
            raw = subprocess.check_output(['xdg-user-dir', key], timeout=2, stderr=subprocess.DEVNULL).decode().strip()
        except (OSError, subprocess.SubprocessError):
            raw = str(HOME / dict(DESKTOP='Desktop', DOCUMENTS='Documents', DOWNLOAD='Downloads', PICTURES='Pictures', VIDEOS='Videos', MUSIC='Music')[key])
        result.append(raw)
    result += [os.environ.get('OMARCHY_SCREENSHOT_DIR', str(HOME / 'Pictures')),
               os.environ.get('OMARCHY_SCREENRECORD_DIR', str(HOME / 'Videos'))] + c['extraRoots']
    good = []
    for raw in result:
        p = local_path(raw)
        if p and p.is_dir() and p not in good and allowed(p, c):
            good.append(p)
    return good


def scan_root(root, depth, since, sink, budget=15):
    # NUL separates both numeric fields and paths: tabs/newlines stay data.
    args = ['find', str(root), '-xdev', '-maxdepth', str(depth), '(', '-name', '.*', '-o', '-name', 'node_modules', ')', '-prune', '-o', '-type', 'f', '(', '-newermt', '@' + str(since), '-o', '-newerct', '@' + str(since), ')', '-printf', '%T@\0%C@\0%p\0']
    args[-1] = '%T@\\0%C@\\0%p\\0'  # find's escaped NUL, never an argv NUL
    start = time.monotonic()
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    buffer, fields, partial = b'', [], False
    try:
        while True:
            remaining = budget - (time.monotonic() - start)
            if remaining <= 0:
                partial = True
                break
            events = sel.select(min(remaining, .2))
            if not events:
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                break
            pieces = (buffer + chunk).split(b'\0')
            buffer = pieces.pop()
            for field in pieces:
                fields.append(field)
                if len(fields) == 3:
                    sink.add(os.fsdecode(fields[2]), max(float(fields[0]), float(fields[1])), 'edited', canonical=True)
                    fields = []
        if partial:
            proc.kill()
        code = proc.wait(timeout=2)
        partial = partial or code != 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        proc.stdout.close()
        sel.close()
    return partial, time.monotonic() - start


def timestamp(value):
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, AttributeError):
        return 0


def xbel(sink):
    if not XBEL.exists():
        return
    if XBEL.stat().st_size > 16_000_000:
        raise ValueError('GTK recent list exceeds 16 MB')
    raw = XBEL.read_bytes()
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unsupported XML declaration in recent list')
    for item in ET.fromstring(raw).iter('bookmark'):
        p = uri_path(item.get('href', ''))
        mime = next((x.get('type', '') for x in item.iter() if x.tag.endswith('mime-type')), '')
        if p:
            sink.add(p, max(timestamp(item.get('visited')), timestamp(item.get('modified'))), 'opened', mime)


def browsers(sink, notices):
    base = Path(os.environ.get('XDG_CONFIG_HOME', HOME / '.config'))
    patterns = [base / 'chromium', base / 'google-chrome', base / 'BraveSoftware/Brave-Browser']
    dbs = [(p, 'chrome') for folder in patterns for p in folder.glob('*/History')]
    dbs += [(p, 'firefox') for p in (HOME / '.mozilla/firefox').glob('*/places.sqlite')]
    if len(dbs) > 24:
        notices.append('Browser scan limited to 24 profiles')
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime or not Path(runtime).is_dir() or Path(runtime).stat().st_uid != os.getuid():
        raise ValueError('Browser source needs an owned XDG_RUNTIME_DIR')
    for path, family in dbs[:24]:
        # SQLite backup includes WAL changes and gives a consistent private copy.
        try:
            if not path.resolve().is_relative_to(HOME) or path.stat().st_size > 256_000_000:
                notices.append('Skipped oversized or external browser database')
                continue
            with tempfile.TemporaryDirectory(prefix='recents-', dir=runtime) as folder:
                start = time.monotonic()
                def progress(*_):
                    if time.monotonic() - start > 3:
                        raise TimeoutError('Browser snapshot timed out')
                with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=.2) as src, sqlite3.connect(str(Path(folder) / 'copy.sqlite')) as db:
                    src.backup(db, pages=128, progress=progress, sleep=.01)
                    db.set_progress_handler(lambda: int(time.monotonic() - start > 4), 1000)
                    if family == 'chrome':
                        rows = db.execute('SELECT target_path, end_time FROM downloads WHERE state=1 ORDER BY end_time DESC LIMIT 2000')
                        for p, t in rows:
                            if p:
                                sink.add(p, t / 1_000_000 - 11644473600, 'downloaded')
                    else:
                        rows = db.execute("SELECT a.content, p.last_visit_date FROM moz_annos a JOIN moz_anno_attributes n ON n.id=a.anno_attribute_id JOIN moz_places p ON p.id=a.place_id WHERE n.name='downloads/destinationFileURI' ORDER BY p.last_visit_date DESC LIMIT 2000")
                        for uri, t in rows:
                            p = uri_path(uri)
                            if p and t:
                                sink.add(p, t / 1_000_000, 'downloaded')
        except (OSError, sqlite3.Error, TimeoutError, ValueError):
            notices.append('A browser profile was unavailable; its results may be incomplete')


def low_battery():
    for p in Path('/sys/class/power_supply').glob('*'):
        try:
            if (p / 'type').read_text().strip() == 'Battery' and (p / 'status').read_text().strip() == 'Discharging' and int((p / 'capacity').read_text()) < 15:
                return True
        except (OSError, ValueError):
            pass
    return False


def marker():
    try:
        s = XBEL.stat()
        return [s.st_mtime_ns, s.st_size, s.st_ino]
    except FileNotFoundError:
        return None


def scan(scheduled=False):
    c = config()
    if scheduled and low_battery():
        return {'skipped': True, 'notice': 'Scheduled scan paused below 15% battery'}
    now = time.time()
    sink = Candidates(c, now)
    notices = []
    try:
        health = read_json(STATE / 'roots.json', {})
        if not isinstance(health, dict):
            health = {}
    except (ValueError, OSError):
        health = {}
    start = time.monotonic()
    if c['sources']['find']:
        for root in roots(c):
            key = str(root)
            strikes = health.get(key, 0)
            if not isinstance(strikes, int):
                strikes = 0
            depth = min(3, c['maxDepth']) if strikes >= 3 else c['maxDepth']
            if strikes >= 3:
                notices.append(root.name + ': depth reduced to 3 after three slow scans')
            remaining = 45 - (time.monotonic() - start)
            if remaining <= 0:
                notices.append('Scan time limit reached; some roots were skipped')
                break
            partial, elapsed = scan_root(root, depth, now - c['windowDays'] * 86400, sink, min(15, remaining))
            health[key] = strikes + 1 if elapsed > 8 else (strikes if strikes >= 3 else 0)
            if partial:
                notices.append(root.name + ': partial scan (timeout or unreadable files)')
    if c['sources']['xbel']:
        try:
            xbel(sink)
        except (OSError, ValueError, ET.ParseError):
            notices.append('GTK recent list could not be read')
    if c['sources']['browsers']:
        try:
            browsers(sink, notices)
        except (OSError, ValueError):
            notices.append('Browser source unavailable: check XDG_RUNTIME_DIR')
    sink.trim()
    result = dict(version=1, scannedAt=now, home=str(HOME), rows=sorted(sink.rows.values(), key=lambda r: (-r['ts'], r['path'])), partial=bool(notices), notices=list(dict.fromkeys(notices)), capped=sink.capped, config=c, xbelMarker=marker())
    atomic_json('index.json', result)
    atomic_json('roots.json', health)
    return result


def action(verb, value):
    # Resolve again at execution, rejecting external symlinks and non-files.
    p = local_path(value)
    if not p or not p.is_file():
        raise ValueError('File no longer exists or is outside home')
    mime = mimetypes.guess_type(str(p))[0] or ''
    if verb == 'open':
        cmd = config()['openWith'].get(p.suffix.lower().lstrip('.')) or config()['openWith'].get(p.suffix.lower())
        argv = (shlex.split(cmd) if isinstance(cmd, str) else cmd) if cmd else ['xdg-open']
        subprocess.run([*argv, str(p)], check=True, timeout=15, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif verb == 'reveal':
        try:
            subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.freedesktop.FileManager1', '--object-path', '/org/freedesktop/FileManager1', '--method', 'org.freedesktop.FileManager1.ShowItems', json.dumps([p.as_uri()]), ''], check=True, timeout=5, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError):
            subprocess.run(['xdg-open', str(p.parent)], check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif verb in ('copy-path', 'copy-file'):
        payload = str(p).encode() if verb == 'copy-path' else (p.as_uri() + '\r\n').encode()
        subprocess.run(['wl-copy', '--type', 'text/plain;charset=utf-8' if verb == 'copy-path' else 'text/uri-list'], input=payload, check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif verb == 'copy-image':
        if not mime.startswith('image/'):
            raise ValueError('Selected file is not an image')
        with p.open('rb') as f:
            subprocess.run(['wl-copy', '--type', mime], stdin=f, check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif verb == 'trash':
        subprocess.run(['gio', 'trash', '--', str(p)], check=True, timeout=10, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif verb == 'details':
        s = p.stat()
        return {'path': str(p), 'bytes': s.st_size, 'modified': s.st_mtime}
    else:
        raise ValueError('Unknown action')
    return {'ok': True, 'action': verb, 'path': str(p)}


def main(argv):
    mode = argv[0] if argv else 'scan'
    if mode in ('scan', 'scheduled'):
        return scan(mode == 'scheduled')
    if mode == 'cached':
        result = read_json(STATE / 'index.json', {})
        # Re-apply current configuration to avoid exposing disabled sources on startup.
        c = config()
        if not isinstance(result, dict) or not isinstance(result.get('rows', []), list):
            raise ValueError('Invalid cached index')
        allowed_sources = [tag for key, tag in [('find', 'edited'), ('xbel', 'opened'), ('browsers', 'downloaded')] if c['sources'][key]]
        sink = Candidates(c, time.time())
        for row in result.get('rows', [])[:LIMIT]:
            for source in row.get('sources', []):
                if source in allowed_sources:
                    sink.add(row.get('path', ''), row.get('ts', 0), source)
        result.update(rows=list(sink.rows.values()), config=c)
        return result
    if mode == 'glyphs' and len(argv) == 2:
        try:
            charset = subprocess.check_output(['fc-match', '-f', '%{charset}', argv[1][:200]], timeout=2).decode()
            spans = [part.split('-') for part in charset.split()]
            needed = [0xf02da, 0xf0219, 0xf02e9, 0xf0567, 0xf0386, 0xf003c, 0xf0169]
            return {'supported': all(any(int(s[0],16) <= code <= int(s[-1],16) for s in spans) for code in needed)}
        except (OSError, ValueError, subprocess.SubprocessError):
            return {'supported': False}
    if mode == 'poll':
        return {'marker': marker()}
    if mode == 'check':
        paths = json.loads(sys.stdin.read(1_000_000))
        if not isinstance(paths, list) or len(paths) > 100:
            raise ValueError('Visible-page check limited to 100 paths')
        missing = []
        for path in paths:
            p = local_path(path)
            if not p or not p.is_file():
                missing.append(path)
        return {'missing': missing}
    if mode == 'act' and len(argv) == 3:
        return action(argv[1], argv[2])
    raise ValueError('Unknown operation')


if __name__ == '__main__':
    os.umask(0o077)
    try:
        print(json.dumps(main(sys.argv[1:]), ensure_ascii=True, separators=(',', ':')))
    except Exception as exc:
        print(json.dumps({'error': str(exc)[:240]}))
        sys.exit(1)

"""Regression probes use only disposable state, metadata, and mocked actions."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from test_helper import r


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.home = Path(scratch.name)
        for key, value in {'HOME': self.home, 'STATE': self.home / 'state',
                           'CONFIG': self.home / 'config.json', 'XBEL': self.home / 'recent.xbel'}.items():
            p = patch.object(r, key, value)
            p.start()
            self.addCleanup(p.stop)
        self.config = {**r.DEFAULT, 'sources': {'find': False, 'xbel': True, 'browsers': False}}
        self.previous = {'rows': [{'path': str(self.home / 'report.pdf'), 'ts': time.time(), 'sources': ['opened']}]}

    def test_all_sources_failed_preserves_index_bytes(self):
        r.atomic_json('index.json', self.previous)
        before = (r.STATE / 'index.json').read_bytes()
        with patch.object(r, 'config', return_value=self.config), patch.object(r, 'xbel', side_effect=OSError('unavailable')):
            with self.assertRaisesRegex(ValueError, 'previous index retained'):
                r.scan()
        self.assertEqual((r.STATE / 'index.json').read_bytes(), before)

    def test_empty_success_can_replace_old_index(self):
        r.atomic_json('index.json', self.previous)
        r.XBEL.write_text('<xbel/>')
        with patch.object(r, 'config', return_value=self.config):
            self.assertEqual(r.scan()['rows'], [])
        self.assertEqual(r.read_state('index.json', {})['rows'], [])

    def test_all_disabled_can_clear_index(self):
        self.config['sources']['xbel'] = False
        with patch.object(r, 'config', return_value=self.config):
            self.assertEqual(r.scan()['rows'], [])

    def test_find_only_failure_preserves_index(self):
        self.config['sources'] = {'find': True, 'xbel': False, 'browsers': False}
        with patch.object(r, 'config', return_value=self.config), patch.object(r, 'roots', return_value=[self.home]), patch.object(r, 'scan_root', return_value=(True, .1)):
            with self.assertRaisesRegex(ValueError, 'previous index retained'):
                r.scan()
        self.assertFalse(r.STATE.exists())

    def test_partial_source_success_is_retained(self):
        self.config['sources']['find'] = True
        def add_result(*args):
            args[3].add(self.home / 'report.pdf', time.time(), 'edited')
            return False, .1
        with patch.object(r, 'config', return_value=self.config), patch.object(r, 'roots', return_value=[self.home]), patch.object(r, 'scan_root', side_effect=add_result), patch.object(r, 'xbel', side_effect=OSError('unavailable')):
            result = r.scan()
        self.assertTrue(result['partial'])
        self.assertEqual(len(result['rows']), 1)

    def test_bounded_read_rejects_growth_after_open(self):
        path = self.home / 'growing'
        path.write_bytes(b'{}')
        real_fstat = os.fstat
        def grow(fd):
            info = real_fstat(fd)
            path.write_bytes(b' ' * 65)
            return info
        with patch.object(r.os, 'fstat', side_effect=grow):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                r.read_bounded(path, 64)

    def test_xbel_overflow_never_reaches_parser(self):
        r.XBEL.write_bytes(b'<xbel>' + b' ' * r.JSON_LIMIT + b'</xbel>')
        with patch.object(r.ET, 'fromstring') as parser:
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                r.xbel(r.Candidates(self.config, time.time()))
        parser.assert_not_called()

    def test_fifo_metadata_is_rejected_without_waiting_for_writer(self):
        os.mkfifo(r.XBEL)
        with self.assertRaisesRegex(ValueError, 'regular'):
            r.xbel(r.Candidates(self.config, time.time()))

    def test_browser_limit_counts_wal_pages(self):
        path = self.home / '.config/chromium/Default/History'
        path.parent.mkdir(parents=True)
        db = sqlite3.connect(path)
        self.addCleanup(db.close)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA wal_autocheckpoint=0')
        db.execute('CREATE TABLE downloads(target_path,end_time,state)')
        db.execute('CREATE TABLE padding(data)')
        db.execute('INSERT INTO padding VALUES(?)', (b'x' * 32_768,))
        db.commit()
        self.assertLess(path.stat().st_size, 8192)
        notices = []
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.home / '.config')}), patch.object(r, 'BROWSER_LIMIT', 8192):
            self.assertFalse(r.browsers(r.Candidates(self.config, time.time()), notices))
        self.assertTrue(notices)
        self.assertFalse(list(self.home.glob('recents-*')))

    def test_browser_wal_download_is_visible_without_copy(self):
        path = self.home / '.config/chromium/Default/History'
        path.parent.mkdir(parents=True)
        db = sqlite3.connect(path)
        self.addCleanup(db.close)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA wal_autocheckpoint=0')
        db.execute('CREATE TABLE downloads(target_path,end_time,state)')
        target = str(self.home / 'report.pdf')
        db.execute('INSERT INTO downloads VALUES(?,?,1)', (target, int((time.time() + 11644473600) * 1_000_000)))
        db.commit()
        sink = r.Candidates(self.config, time.time())
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.home / '.config')}):
            self.assertTrue(r.browsers(sink, []))
        self.assertIn(target, sink.rows)

    def test_state_rejects_symlinked_ancestor(self):
        target = self.home / 'actual'
        target.mkdir()
        alias = self.home / 'alias'
        alias.symlink_to(target)
        with patch.object(r, 'STATE', alias / 'recents'):
            with self.assertRaises(OSError):
                r.atomic_json('index.json', {})
        self.assertFalse((target / 'recents').exists())

    def test_state_rejects_permissive_directory(self):
        r.STATE.mkdir()
        r.STATE.chmod(0o777)
        with self.assertRaises(ValueError):
            r.atomic_json('index.json', {})
        self.assertFalse((r.STATE / 'index.json').exists())

    def test_state_reads_reject_symlinks_and_public_files(self):
        r.atomic_json('index.json', {})
        index = r.STATE / 'index.json'
        index.chmod(0o644)
        with self.assertRaises(ValueError):
            r.read_state('index.json', {})
        index.unlink()
        target = self.home / 'target'
        target.write_text('{}')
        index.symlink_to(target)
        with self.assertRaises(OSError):
            r.read_state('index.json', {})

    def test_atomic_write_keeps_validated_parent_during_path_swap(self):
        r.atomic_json('index.json', {'old': True})
        moved = self.home / 'original'
        target = self.home / 'substitute'
        target.mkdir()
        original_replace = os.replace
        def swap(source, destination, **kwargs):
            r.STATE.rename(moved)
            r.STATE.symlink_to(target)
            return original_replace(source, destination, **kwargs)
        with patch.object(r.os, 'replace', side_effect=swap):
            r.atomic_json('index.json', {'new': True})
        self.assertEqual(json.loads((moved / 'index.json').read_text()), {'new': True})
        self.assertFalse((target / 'index.json').exists())
        self.assertFalse(list(moved.glob('.write-*')))

    def test_entry_points_ignore_pythonpath_and_path_shims(self):
        shim = self.home / 'shim'
        shim.mkdir()
        (shim / 'sitecustomize.py').write_text('raise RuntimeError("injected module")')
        (shim / 'python3').write_text('#!/bin/sh\nexit 99\n')
        (shim / 'python3').chmod(0o755)
        helper = Path(r.__file__).parent / 'recents-scan'
        result = subprocess.run([str(helper), 'poll'], env={**os.environ, 'PYTHONPATH': str(shim), 'PATH': str(shim), 'XDG_DATA_HOME': str(self.home)}, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'marker': None})
        helper = helper.with_name('recents-act')
        fixture = self.home / 'file.pdf'
        fixture.write_text('fixture')
        result = subprocess.run([str(helper), 'details', str(fixture)], env={**os.environ, 'HOME': str(self.home), 'PYTHONPATH': str(shim), 'PATH': str(shim)}, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['bytes'], 7)

    def test_child_environment_removes_code_loading_overrides(self):
        with patch.dict(os.environ, {'PYTHONPATH': '/untrusted', 'LD_PRELOAD': '/untrusted.so', 'BASH_ENV': '/untrusted', 'PATH': '/untrusted', 'WAYLAND_DISPLAY': 'wayland-test'}):
            env = r.child_environment()
        self.assertEqual(env['PATH'], '/usr/bin')
        self.assertEqual(env['WAYLAND_DISPLAY'], 'wayland-test')
        for key in ('PYTHONPATH', 'LD_PRELOAD', 'BASH_ENV'):
            self.assertNotIn(key, env)

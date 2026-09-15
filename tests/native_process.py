"""Run the real Quickshell process adapter in a disposable, headless instance."""
import os
from pathlib import Path
import subprocess
import shutil
import tempfile

with tempfile.TemporaryDirectory(prefix='recents-native-') as scratch:
    env = {**os.environ, 'XDG_RUNTIME_DIR': scratch, 'XDG_CACHE_HOME': scratch,
           'QT_QPA_PLATFORM': 'offscreen', 'QT_QPA_PLATFORMTHEME': 'basic',
           'PATH': '/nonexistent', 'PYTHONPATH': '/nonexistent', 'BASH_ENV': '/nonexistent'}
    root = Path(__file__).resolve().parents[1]
    probe = Path(scratch) / 'shell.qml'
    shutil.copyfile(root / 'tests/native/shell.qml', probe)
    shutil.copyfile(root / 'HelperProcess.qml', Path(scratch) / 'HelperProcess.qml')
    try:
        result = subprocess.run(['/usr/bin/qs', '--no-color', '-p', str(probe)],
                                env=env, capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired as error:
        raise AssertionError((error.stdout or b'') + (error.stderr or b'')) from error
    output = result.stdout + result.stderr
    assert result.returncode == 0 and 'RECENTS_NATIVE_PROCESS_PASS' in output, output
    assert 'RECENTS_NATIVE_PROCESS_FAIL' not in output, output
    print('Real Quickshell child environment passed')

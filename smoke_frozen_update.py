# Copyright (c) 2026 GANOMABI / amiinarii.
"""Windows CI: restart a real onefile EXE through the production updater."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

PROBE = '''import json, os, shutil, sys
from pathlib import Path
from auto_updater import start_replacement
root = Path(os.environ['GANOV_SMOKE_ROOT'])
state = root / 'state.json'
if not state.exists():
    state.write_text(json.dumps({'old_runtime': sys._MEIPASS}))
    stage = root / 'stage'
    stage.mkdir()
    source = stage / 'update.exe'
    shutil.copyfile(sys.executable, source)
    start_replacement(str(source), sys.executable, os.getpid(), os.getppid())
else:
    old = json.loads(state.read_text())['old_runtime']
    (root / 'result.json').write_text(json.dumps({'old_runtime':old, 'new_runtime':sys._MEIPASS, 'reset':os.environ.get('PYINSTALLER_RESET_ENVIRONMENT')}))
'''

def main():
    if os.name != 'nt':
        raise RuntimeError('Windows only')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        script = root / 'probe.py'
        script.write_text(PROBE)
        subprocess.run(['python', '-m', 'PyInstaller', '--noconfirm', '--onefile', '--console',
                        '--paths', str(Path(__file__).parent.resolve()), '--distpath', str(root),
                        '--workpath', str(root/'work'), '--specpath', str(root), str(script)], check=True)
        executable = root / 'probe.exe'
        environment = {**os.environ, 'GANOV_SMOKE_ROOT': str(root)}
        old = subprocess.Popen([str(executable)], cwd=root, env=environment)
        old.wait(timeout=60)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            result = root / 'result.json'
            if result.exists() and not (root/'stage').exists():
                data = json.loads(result.read_text())
                assert data['old_runtime'] != data['new_runtime'], data
                assert not Path(data['old_runtime']).exists(), data
                assert not Path(str(executable)+'.update-backup').exists()
                # The replacement bootloader can still be exiting after the helper
                # removes staging. Wait for its runtime and executable lock too.
                if Path(data['new_runtime']).exists():
                    time.sleep(.5)
                    continue
                try:
                    executable.unlink()
                except PermissionError:
                    time.sleep(.5)
                    continue
                print('PASS: frozen EXE restart uses fresh runtime; old runtime and backup cleaned.')
                return
            time.sleep(.5)
        raise AssertionError('Updated frozen EXE did not finish restart and cleanup')

if __name__ == '__main__':
    main()

import hashlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import auto_updater as updater

class DownloadTests(unittest.TestCase):
    def asset(self, data):
        return {'download_url': 'https://github.com/owner/repo/releases/download/v1.0.0/GanoV-Cache-Switch.exe',
                'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    def test_verified_download_and_progress(self):
        data = b'MZ' + b'example' * 100000
        progress = []
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, 'urlopen', return_value=io.BytesIO(data)):
            path = updater.download_update(self.asset(data), tmp, progress.append)
            self.assertEqual(Path(path).read_bytes(), data)
            self.assertEqual(progress[-1], 1)

    def test_corrupt_truncated_and_oversize_downloads_are_removed(self):
        expected = b'MZexpected'
        for actual in (b'MZcorrupt!', b'MZ', expected + b'extra'):
            with tempfile.TemporaryDirectory() as tmp, patch.object(updater, 'urlopen', return_value=io.BytesIO(actual)):
                with self.assertRaises(ValueError):
                    updater.download_update(self.asset(expected), tmp)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_non_exe_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(updater, 'urlopen', return_value=io.BytesIO(b'HTML')):
            with self.assertRaises(ValueError):
                updater.download_update(self.asset(b'HTML'), tmp)

    def test_asset_rejects_other_repository_and_missing_hash(self):
        asset = {'name': 'GanoV-Cache-Switch.exe', 'size': 10, 'digest': 'sha256:' + 'a'*64,
                 'browser_download_url': 'https://github.com/other/repo/releases/download/v1.0.0/GanoV-Cache-Switch.exe'}
        with self.assertRaises(ValueError):
            updater.release_asset({'tag_name': 'v1.0.0', 'assets': [asset]}, 'owner/repo')
        asset['browser_download_url'] = asset['browser_download_url'].replace('other', 'owner')
        asset.pop('digest')
        with self.assertRaises(ValueError):
            updater.release_asset({'tag_name': 'v1.0.0', 'assets': [asset]}, 'owner/repo')

    @unittest.skipUnless(os.name == 'nt', 'Windows replacement integration')
    def test_windows_atomic_install_and_rollback(self):
        for fail_launch in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "App's TARGET.exe"
                stage = Path(tmp) / 'stage'
                stage.mkdir()
                source = stage / 'update.exe'
                target.write_bytes(b'old exe')
                source.write_bytes(b'new exe')
                script = updater.replacement_script(source, target, 2147483640)
                script = script.replace('Start-Process -FilePath $target -WorkingDirectory (Split-Path -Parent $target) -ErrorAction Stop',
                                        "throw 'simulated launch failure'" if fail_launch else 'Write-Output installed')
                script = script.replace("[System.Windows.Forms.MessageBox]::Show('Update gagal: ' + $_.Exception.Message + \"`nJalankan kembali aplikasi lama.\", 'GanoV-Cache-Switch') | Out-Null", 'Write-Output failed')
                result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(target.read_bytes(), b'old exe' if fail_launch else b'new exe', result.stdout + result.stderr)
                self.assertFalse(stage.exists())
                self.assertFalse(Path(str(target)+'.update-new').exists())
                self.assertFalse(Path(str(target)+'.update-backup').exists())

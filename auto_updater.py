# Copyright (c) 2026 GANOMABI / amiinarii.
"""Verified release downloads and an external Windows replacement helper."""
import base64
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import Request, urlopen

MAX_DOWNLOAD = 200 * 1024 * 1024


def release_asset(release, repository):
    prefix = 'https://github.com/' + repository + '/releases/download/' + release['tag_name'] + '/'
    for asset in release.get('assets', []):
        if asset.get('name') != 'GanoV-Cache-Switch.exe':
            continue
        url, size, digest = asset.get('browser_download_url'), asset.get('size'), asset.get('digest')
        if not isinstance(url, str) or url != prefix + 'GanoV-Cache-Switch.exe':
            raise ValueError('Alamat EXE update tidak valid')
        if type(size) is not int or not 2 <= size <= MAX_DOWNLOAD:
            raise ValueError('Ukuran EXE update tidak valid')
        if not isinstance(digest, str) or not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', digest):
            raise ValueError('Verifikasi SHA-256 update belum tersedia')
        return {'download_url': url, 'size': size, 'sha256': digest[7:].lower()}
    raise ValueError('EXE rilis terbaru belum tersedia. Coba lagi nanti.')


def download_update(asset, directory, progress=lambda value: None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='update-', dir=directory))
    target = stage / 'update.exe'
    try:
        digest = hashlib.sha256()
        count = 0
        request = Request(asset['download_url'], headers={'User-Agent': 'GanoV-Cache-Switch'})
        with urlopen(request, timeout=30) as response, target.open('wb') as out:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > asset['size'] or count > MAX_DOWNLOAD:
                    raise ValueError('Ukuran unduhan melebihi ukuran rilis')
                out.write(chunk)
                digest.update(chunk)
                progress(count / asset['size'])
            out.flush()
            os.fsync(out.fileno())
        if count != asset['size'] or digest.hexdigest() != asset['sha256']:
            raise ValueError('Unduhan tidak lengkap atau verifikasi SHA-256 gagal. EXE lama tetap aman.')
        with target.open('rb') as stream:
            if stream.read(2) != b'MZ':
                raise ValueError('File update bukan EXE Windows')
        return str(target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def replacement_script(staged, executable, process_id):
    # All paths are literal PowerShell strings; no shell interpolation.
    template = '''$ErrorActionPreference = 'Stop'
$source = SOURCE
$target = TARGET
$stage = Split-Path -Parent $source
$incoming = $target + '.update-new'
$backup = $target + '.update-backup'
try {
    $running = Get-Process -Id PROCESS_ID -ErrorAction SilentlyContinue
    if ($running -and -not $running.WaitForExit(120000)) { throw 'Aplikasi lama belum ditutup.' }
    Copy-Item -LiteralPath $source -Destination $incoming -Force
    $installed = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            # File.Replace swaps atomically on the same volume and retains a rollback copy.
            [System.IO.File]::Replace($incoming, $target, $backup, $true)
            $installed = $true
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $installed) { throw 'EXE tidak bisa diganti. Periksa izin folder atau antivirus.' }
    try {
        Start-Process -FilePath $target -WorkingDirectory (Split-Path -Parent $target) -ErrorAction Stop
    } catch {
        [System.IO.File]::Replace($backup, $target, $incoming, $true)
        throw
    }
    Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show('Update gagal: ' + $_.Exception.Message + "`nJalankan kembali aplikasi lama.", 'GanoV-Cache-Switch') | Out-Null
} finally {
    Remove-Item -LiteralPath $incoming -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}
'''
    values = {'SOURCE': ps_literal(staged), 'TARGET': ps_literal(executable), 'PROCESS_ID': str(int(process_id))}
    return re.sub(r'\b(SOURCE|TARGET|PROCESS_ID)\b', lambda match: values[match.group()], template)


def start_replacement(staged, executable, process_id):
    if os.name != 'nt':
        raise RuntimeError('Pemasangan otomatis tersedia pada EXE Windows.')
    parent = Path(executable).resolve().parent
    # Fail before closing the app if its directory is read-only.
    with tempfile.TemporaryFile(dir=parent):
        pass
    script = replacement_script(staged, executable, process_id)
    encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
    powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    return subprocess.Popen([str(powershell), '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                            cwd=parent, close_fds=True,
                            creationflags=0x08000000 | 0x00000200)

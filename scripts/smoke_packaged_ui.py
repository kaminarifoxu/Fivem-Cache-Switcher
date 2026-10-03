# Copyright (c) 2026 GANOMABI / amiinarii.
import json
import os
from pathlib import Path
import subprocess
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp) / "result.json"
    process = subprocess.Popen(
        [str(Path("dist/GanoV-Cache-Switch.exe").resolve()), "--smoke-ui", str(output)],
        env={**os.environ, "LOCALAPPDATA": tmp},
    )
    try:
        process.wait(timeout=45)
    except subprocess.TimeoutExpired:
        process.kill()
        raise
    assert output.exists(), "Packaged application did not report UI results"
    result = json.loads(output.read_text())
    assert result["ok"], result
    print(
        "PASS: actual packaged EXE mouse click opens update panel and download button."
    )

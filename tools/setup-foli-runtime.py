"""One-time, explicit local dependency setup. Never run by application startup.

Optional --reuse-bridge copies immutable runtime/model files from a prior local
demo; it never runs that demo or writes its directory. Downloads contain no
document data. All outputs stay inside this cf checkout's ignored directories.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import tarfile
import os
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]
OLLAMA_VERSION = "0.40.3"
OLLAMA_SHA = "e5ecff02dfc7cae8ddf6d6b7a7ac5f727ffeedf4491f44ae75ff5b0820dbbbd5"
OCR_VERSION = "5.5.3"


def download(url, target, expected):
    if not target.exists():
        print(time.strftime("%H:%M:%S"), "Downloading", target.name, flush=True)
        partial = target.with_suffix(".partial")
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        with requests.get(url, headers=headers, stream=True, timeout=(15, 30)) as response:
            response.raise_for_status()
            last = time.monotonic()
            count = offset if response.status_code == 206 else 0
            with partial.open("ab" if response.status_code == 206 else "wb") as output:
                for block in response.iter_content(65536):
                    output.write(block)
                    count += len(block)
                    if time.monotonic() - last > 15:
                        print(time.strftime("%H:%M:%S"), count // 1048576, "MiB", flush=True)
                        last = time.monotonic()
        partial.rename(target)
    with target.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != expected.removeprefix("sha256:"):
        raise RuntimeError("Dependency archive checksum mismatch; file retained")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-bridge", type=Path)
    args = parser.parse_args()
    if subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() != "cf":
        raise RuntimeError("Setup requires the existing cf branch")
    tools = ROOT / ".local-tools"
    tools.mkdir(exist_ok=True)
    archive = tools / "ollama-windows-amd64.zip"
    reused = args.reuse_bridge
    if reused and not archive.exists():
        shutil.copyfile(reused / "tools/ollama-windows-amd64.zip", archive)
    download(f"https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/{archive.name}", archive, OLLAMA_SHA)
    runtime = tools / "ollama"
    if not (runtime / "ollama.exe").exists():
        print(time.strftime("%H:%M:%S"), "Extracting verified Ollama runtime", flush=True)
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                if not (runtime / item.filename).resolve().is_relative_to(runtime.resolve()):
                    raise RuntimeError("Archive path escape")
            bundle.extractall(runtime)
    models = ROOT / ".local-data/foli/models"
    if reused and not models.exists():
        print(time.strftime("%H:%M:%S"), "Copying existing model weights into cf state", flush=True)
        shutil.copytree(reused / "models", models)
    ocr = tools / "ocr"
    ocr_exe = ocr / "Library/bin/tesseract.exe"
    receipt_file=ROOT / ".local-data/foli/runtime-setup.json"
    receipt_file.parent.mkdir(parents=True,exist_ok=True)
    receipts=json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
    receipts.update({"ollamaVersion": OLLAMA_VERSION, "ollamaArchiveSha256": OLLAMA_SHA})
    lock=ROOT / 'tools/foli-ocr-win64.lock'
    receipts['ocrLockSha256']=hashlib.sha256(lock.read_bytes()).hexdigest()
    if not ocr_exe.exists():
        # The upstream Windows installer requires elevation. Use an isolated
        # conda-forge prefix instead; no UAC, system installation or PATH changes.
        micro_archive = tools / "micromamba-2.9.0-0.tar.bz2"
        micro_sha = "97a336f4ab794bd96a6a4da5e6ed63e75a1d31830414a182419b23d3b36f3fe0"
        download("https://conda.anaconda.org/conda-forge/win-64/" + micro_archive.name,
                 micro_archive, micro_sha)
        micro = tools / "micromamba.exe"
        if not micro.exists():
            with tarfile.open(micro_archive) as bundle:
                with bundle.extractfile("Library/bin/micromamba.exe") as binary, micro.open("wb") as output:
                    shutil.copyfileobj(binary, output)
        env = os.environ.copy()
        env["MAMBA_ROOT_PREFIX"] = str(tools / "mamba-cache")
        env["MAMBA_SSL_VERIFY"] = requests.certs.where()
        print(time.strftime("%H:%M:%S"), "Installing Tesseract in an isolated cf prefix", flush=True)
        subprocess.run([str(micro), "create", "--no-rc", "-y", "-p", str(ocr), "--file", str(lock)],
                       check=True, timeout=600, env=env)
        receipts["micromambaArchiveSha256"] = micro_sha
    version=subprocess.run([str(ocr_exe), "--version"], check=True, timeout=10,capture_output=True,text=True).stdout
    if not version.startswith('tesseract '+OCR_VERSION): raise RuntimeError('Unexpected installed OCR version; retained without replacement')
    print(version.splitlines()[0],flush=True)
    receipts['tesseractVersion']=OCR_VERSION
    receipt_file.write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    print("Runtime setup complete. Start tools/start-foli-ollama.ps1, then explicitly pull any missing candidate.", flush=True)


if __name__ == "__main__":
    main()

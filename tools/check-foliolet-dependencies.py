"""Check desktop imports and exact pins from the current requirement files."""
from importlib import import_module
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check():
    for module in ("django", "requests", "watchdog", "psycopg", "Crypto", "waitress", "rapidocr", "onnxruntime", "pyhanko"):
        import_module(module)
    for relative in ("django-service/requirements.txt", "tools/requirements-dev.txt", "tools/requirements-ocr.txt"):
        for line in (ROOT / relative).read_text(encoding="utf8").splitlines():
            requirement = line.split("#", 1)[0].strip()
            if "==" in requirement:
                name, expected = requirement.split("==", 1)
                installed = version(name)
                if installed != expected:
                    raise RuntimeError(f"{name}: expected {expected}, installed {installed}")
    print("Foliolet Python imports and requirement pins are ready.", flush=True)


if __name__ == "__main__":
    check()

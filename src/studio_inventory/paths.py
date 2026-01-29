from pathlib import Path
import os

APP_NAME = "StudioInventory"

def workspace_root() -> Path:
    # Allow override for power users / CI
    env = os.getenv("STUDIO_INV_HOME")
    if env:
        return Path(env).expanduser().resolve()

    return Path.home() / APP_NAME


def ensure_workspace():
    root = workspace_root()
    subdirs = [
        "receipts",
        "exports",
        "log",
        "label_presets",
        "secrets",
    ]

    root.mkdir(parents=True, exist_ok=True)
    for d in subdirs:
        (root / d).mkdir(exist_ok=True)

    return root
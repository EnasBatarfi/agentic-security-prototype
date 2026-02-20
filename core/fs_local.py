from pathlib import Path
from django.conf import settings

def user_root(user_id: int) -> Path:
    root = Path(settings.FILE_SANDBOX_ROOT) / str(user_id)
    root.mkdir(parents=True, exist_ok=True)
    return root

def list_dir(user_id: int, rel_path: str = "") -> list[str]:
    root = user_root(user_id)
    target = root / rel_path if rel_path else root
    if not target.exists():
        return []
    return [p.name for p in target.iterdir()]

def write_file(user_id: int, rel_path: str, content: str) -> None:
    root = user_root(user_id)
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

def read_file(user_id: int, rel_path: str) -> str:
    root = user_root(user_id)
    target = root / rel_path
    return target.read_text(encoding="utf-8")
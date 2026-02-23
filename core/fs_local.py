from pathlib import Path
from django.conf import settings

def user_root(user_id: int) -> Path:
    root = Path(settings.FILE_SANDBOX_ROOT) / str(user_id)
    root.mkdir(parents=True, exist_ok=True)
    return root

def list_tree(user_id: int, rel_path: str = "") -> list[str]:
    root = user_root(user_id)
    base = (root / rel_path) if rel_path else root
    if not base.exists():
        return []

    lines = []
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        indent = "  " * (len(rel.parts) - 1)
        name = rel.parts[-1] + ("/" if p.is_dir() else "")
        lines.append(f"{indent}{name}")
    return lines

def write_file(user_id: int, rel_path: str, content: str) -> None:
    root = user_root(user_id)
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

def read_file(user_id: int, rel_path: str) -> str:
    root = user_root(user_id)
    target = root / rel_path
    return target.read_text(encoding="utf-8")
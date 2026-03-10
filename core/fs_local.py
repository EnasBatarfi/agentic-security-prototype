from pathlib import Path
from django.conf import settings

def user_root(user_id: int) -> Path:
    root = Path(settings.FILE_SANDBOX_ROOT) / str(user_id)
    root.mkdir(parents=True, exist_ok=True)
    return root

def clean_rel_path(rel_path: str) -> str:
    if rel_path is None:
        raise ValueError("empty path not allowed")

    rel_path = rel_path.strip()
    rel_path = rel_path.strip("`").strip('"').strip("'")
    rel_path = rel_path.strip()

    if rel_path == "":
        raise ValueError("empty path not allowed")

    if "\x00" in rel_path:
        raise ValueError("null bytes not allowed")
    
    if rel_path.startswith("~"):
        raise ValueError("tilde paths not allowed")

    if "\\" in rel_path:
        raise ValueError("backslashes not allowed")

    return rel_path

def resolve_safe(root: Path, rel_path: str) -> Path:
    # clean common junk the model may pass
    rel_path = clean_rel_path(rel_path)

    p = Path(rel_path)

    # block absolute paths like /etc/passwd
    if p.is_absolute():
        raise ValueError("absolute paths not allowed")

    # build full path and normalize (resolves .. and .)
    full = (root / p).resolve()
    root_resolved = root.resolve()

    # block escape from sandbox
    if full != root_resolved and root_resolved not in full.parents:
        raise ValueError("path escapes sandbox")

    return full

def list_tree(user_id: int, rel_path: str = "") -> list[str]:
    root = user_root(user_id)
    base = root if rel_path == "" else resolve_safe(root, rel_path)
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
    target = resolve_safe(root, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

def read_file(user_id: int, rel_path: str) -> str:
    root = user_root(user_id)
    target = resolve_safe(root, rel_path)
    return target.read_text(encoding="utf-8")
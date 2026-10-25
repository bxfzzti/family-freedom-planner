"""Content identity for executable behavior, excluding tests and recorded answers."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def current(root=ROOT):
    root = Path(root)
    paths = [root / "SKILL.md", root / "workflow.yaml"]
    for directory in ("scripts", "references", "assets", "agents"):
        paths.extend(path for path in (root / directory).rglob("*")
                     if path.is_file() and path.suffix in (".py", ".md", ".json", ".yaml", ".yml"))
    payload = []
    for path in sorted(set(paths)):
        payload.append(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return hashlib.sha256(b"\n".join(payload)).hexdigest()


if __name__ == "__main__":
    print(current())

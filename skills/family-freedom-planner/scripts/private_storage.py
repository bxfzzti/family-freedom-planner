"""Private, atomic JSON documents with optimistic concurrency and one backup."""
import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path


class StorageError(ValueError):
    pass


class Document(dict):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_bytes(path):
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise StorageError(f"cannot safely read document: {exc}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise StorageError("document must be a regular, unlinked private file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)


def load(path):
    path = Path(path).absolute()
    if path.is_symlink():
        raise StorageError("symbolic-link documents are not accepted")
    raw = safe_bytes(path)
    value = json.loads(raw)
    if isinstance(value, dict):
        value = Document(value)
        value._document_path = str(path)
        value._expected_revision = digest(raw)
    return value


@contextmanager
def locked(path):
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(str(path) + ".lock", flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise StorageError("invalid lock file")
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        if os.name == "nt":
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError as exc:
        raise StorageError("document busy; reload before retrying") from exc
    finally:
        os.close(fd)


def atomic_replace(path, raw):
    fd, temporary = tempfile.mkstemp(prefix=".ffp-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save(path, data):
    path = Path(path).absolute()
    raw = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with locked(path):
        if path.is_symlink():
            raise StorageError("refusing to overwrite a symbolic link")
        if path.exists():
            old = safe_bytes(path)
            expected = getattr(data, "_expected_revision", None)
            if (getattr(data, "_document_path", None) != str(path)
                    or expected != digest(old)):
                raise StorageError("document version conflict; reload and merge before saving")
            atomic_replace(path.with_name(path.name + ".previous"), old)
        atomic_replace(path, raw)
    if isinstance(data, Document):
        data._expected_revision = digest(raw)
    return digest(raw)


def restore(path):
    """Explicit recovery; save current content as the next private backup."""
    path = Path(path)
    old = safe_bytes(path.with_name(path.name + ".previous"))
    json.loads(old)  # refuse restoring a corrupt backup
    restored = Document(json.loads(old))
    restored._document_path = str(path.absolute())
    restored._expected_revision = digest(safe_bytes(path)) if path.exists() else None
    save(path, restored)
    return restored


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["restore"])
    parser.add_argument("document")
    args = parser.parse_args()
    try:
        restore(args.document)
        print(json.dumps({"status": "RESTORED", "previous_current_saved_as_backup": True}))
    except (ValueError, OSError, TypeError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}))
        raise SystemExit(2)

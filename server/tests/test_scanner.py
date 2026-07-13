"""Scanner hard-exclusion tests — see PLAN.md's "Indexing secrets/.env by
accident" risk. These must never regress."""

from pathlib import Path

from app.services.scanner import scan_repo


def _write(root: Path, rel_path: str, content: str = "x = 1\n") -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_secrets_and_noise_are_excluded(tmp_path: Path):
    _write(tmp_path, "app.py", "def main():\n    pass\n")
    _write(tmp_path, ".env", "API_KEY=super-secret\n")
    _write(tmp_path, ".env.production", "API_KEY=super-secret-2\n")
    _write(tmp_path, "id_rsa", "-----BEGIN PRIVATE KEY-----\n")
    _write(tmp_path, "node_modules/some_pkg/index.js", "console.log(1)\n")
    _write(tmp_path, ".git/HEAD", "ref: refs/heads/main\n")
    _write(tmp_path, "package-lock.json", "{}\n")
    _write(tmp_path, "logo.png", "\x89PNG\x00\x00binarydata")

    scanned, skipped = scan_repo(str(tmp_path))
    scanned_paths = {f.rel_path for f in scanned}

    assert "app.py" in scanned_paths
    assert ".env" not in scanned_paths
    assert ".env.production" not in scanned_paths
    assert "id_rsa" not in scanned_paths
    assert not any(p.startswith("node_modules/") for p in scanned_paths)
    assert not any(p.startswith(".git/") for p in scanned_paths)
    assert "package-lock.json" not in scanned_paths
    assert "logo.png" not in scanned_paths
    # .git/ and node_modules/ are pruned as whole directories (never walked),
    # so their contents don't individually increment the skip counter — only
    # the 5 excluded top-level files do: .env, .env.production, id_rsa,
    # package-lock.json, logo.png.
    assert skipped >= 5


def test_nested_gitignore_is_respected(tmp_path: Path):
    _write(tmp_path, "src/keep.py", "x = 1\n")
    _write(tmp_path, "src/ignored.py", "y = 2\n")
    _write(tmp_path, "src/.gitignore", "ignored.py\n")

    scanned, _ = scan_repo(str(tmp_path))
    scanned_paths = {f.rel_path for f in scanned}

    assert "src/keep.py" in scanned_paths
    assert "src/ignored.py" not in scanned_paths


def test_root_gitignore_is_respected(tmp_path: Path):
    _write(tmp_path, "keep.py", "x = 1\n")
    _write(tmp_path, "build/output.py", "y = 2\n")
    _write(tmp_path, ".gitignore", "build/\n")

    scanned, _ = scan_repo(str(tmp_path))
    scanned_paths = {f.rel_path for f in scanned}

    assert "keep.py" in scanned_paths
    assert not any(p.startswith("build/") for p in scanned_paths)

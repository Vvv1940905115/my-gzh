"""Shared path and metadata helpers for publish and quality scripts.

Stdlib-only so the quality checks and the publish pipeline can import these
helpers without extra dependencies.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_path(raw, root=None, default_name=None):
    """Resolve a user-supplied path: absolute as-is; relative tries CWD, then root."""
    base = Path(root) if root is not None else ROOT
    if not raw and default_name:
        return base / default_name
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    root_path = base / path
    return root_path.resolve() if root_path.exists() else root_path


def default_meta_for(article_path):
    """Infer the matching meta file: article.md -> meta.json, article-foo.md -> meta-foo.json."""
    path = Path(article_path)
    if path.name == "article.md":
        return path.with_name("meta.json")
    if path.name.startswith("article"):
        return path.with_name("meta" + path.stem[len("article"):] + ".json")
    return path.with_name("meta.json")

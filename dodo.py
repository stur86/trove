"""
Trove build pipeline — run with `doit` or `uv run doit`.

Task dependency graph (derived automatically from file targets/deps):

    build_frontend  →  build_wheel  →  build_docker

Running `doit build_docker` executes the full chain, skipping any stage
whose inputs haven't changed since the last successful run.

Individual stages:
    doit build_frontend   # compile React → backend/static/
    doit build_wheel      # package Python wheel → dist/
    doit build_docker     # build Docker image (uses dist/*.whl)

Clean all build artefacts:
    doit clean -a
"""

import tomllib
from glob import glob
from pathlib import Path

DOIT_CONFIG = {"backend": "json", "dep_file": ".doit.db"}


def _version() -> str:
    """Read the project version from pyproject.toml."""
    with open("pyproject.toml", "rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def _files(*patterns: str) -> list[str]:
    """Expand one or more glob patterns into a sorted list of existing file paths."""
    paths: list[str] = []
    for pattern in patterns:
        paths.extend(glob(pattern, recursive=True))
    return sorted(p for p in paths if Path(p).is_file())


def task_build_frontend():
    """Compile the React frontend into backend/static/."""
    sources = _files(
        "frontend/src/**/*",
        "frontend/public/**/*",
    ) + [
        "frontend/index.html",
        "frontend/package.json",
        "frontend/bun.lock",
        "frontend/vite.config.ts",
        "frontend/tailwind.config.cjs",
        "frontend/postcss.config.cjs",
        "frontend/tsconfig.json",
        "frontend/tsconfig.app.json",
        "frontend/tsconfig.node.json",
    ]
    return {
        "actions": ["cd frontend && bun run build"],
        "file_dep": sources,
        "targets": ["backend/static/index.html"],
        "clean": ["rm -rf backend/static/"],
    }


def task_build_wheel():
    """Build the Python wheel (includes the compiled frontend as package-data)."""
    version = _version()
    wheel = f"dist/trove-{version}-py3-none-any.whl"
    sources = _files("backend/**/*.py") + ["pyproject.toml", "backend/static/index.html"]
    return {
        "actions": ["uv build --wheel"],
        "file_dep": sources,
        "targets": [wheel],
        "clean": ["rm -rf dist/"],
    }


def task_build_docker():
    """Build the Docker image from the local wheel."""
    version = _version()
    wheel = f"dist/trove-{version}-py3-none-any.whl"
    # Docker has no output file; .docker-built is a sentinel that doit uses to
    # track whether the image is up to date with its inputs.
    return {
        "actions": [
            "docker build -t trove .",
            "touch .docker-built",
        ],
        "file_dep": [wheel, "Dockerfile", "docker-entrypoint.sh", "install.sh"],
        "targets": [".docker-built"],
        "clean": ["rm -f .docker-built"],
    }

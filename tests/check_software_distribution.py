"""Exercise the actual software archives without distributing local corpus data."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOFTWARE_ROOT_FILES = {
    "pyproject.toml", "README.md", "LICENSE", "CITATION.cff",
    "agora.materializer.json", "PKG-INFO",
}


def run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True, timeout=300)


def check_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        files = []
        for member in archive.getmembers():
            if member.isdir():
                continue
            assert member.isfile(), "Nonregular sdist member"
            relative = PurePosixPath(*PurePosixPath(member.name).parts[1:])
            files.append(str(relative))
            assert (
                str(relative) in SOFTWARE_ROOT_FILES
                or relative.parts[0] in {"src", "scripts"}
                and relative.suffix == ".py"
            ), f"Nonsoftware sdist member: {relative}"
        assert SOFTWARE_ROOT_FILES <= set(files)
        assert "src/ugarit_context_parsing/cli.py" in files
        assert "scripts/parse_workbooks_to_csv.py" in files


def check_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in names:
            relative = PurePosixPath(name)
            assert (
                relative.parts[0].endswith(".dist-info")
                or relative.parts[0] in {"ugarit_context_parsing", "scripts"}
                and relative.suffix == ".py"
            ), f"Nonsoftware wheel member: {relative}"
        assert "ugarit_context_parsing/cli.py" in names
        assert "scripts/parse_workbooks_to_csv.py" in names


def check() -> None:
    # Neither fixture is restricted source; they represent ordinary local files
    # a researcher can have left behind from a conversion or audit.
    probes = [
        ROOT / "output" / "release-probe.tf",
        ROOT / "output" / "release-probe.json",
    ]
    created = []
    try:
        for probe in probes:
            with probe.open("x", encoding="utf-8") as handle:
                created.append(probe)
                handle.write("synthetic release boundary probe\n")
        with tempfile.TemporaryDirectory(prefix="burns-software-dist-") as directory:
            workspace = Path(directory).resolve()
            dist = workspace / "dist"
            # Default PyPA build constructs the wheel FROM the generated sdist.
            run(sys.executable, "-m", "build", "--outdir", str(dist))
            sdists = list(dist.glob("*.tar.gz"))
            wheels = list(dist.glob("*.whl"))
            assert len(sdists) == len(wheels) == 1
            check_sdist(sdists[0])
            check_wheel(wheels[0])
            env = workspace / "venv"
            run(sys.executable, "-m", "venv", str(env))
            python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run(str(python), "-m", "pip", "install", str(wheels[0]), cwd=workspace)
            run(str(python), "-I", "-c",
                "from ugarit_context_parsing.research_queries import iter_burns_occurrences; "
                "from scripts.parse_workbooks_to_csv import parse_pdf; "
                "assert callable(iter_burns_occurrences) and callable(parse_pdf)",
                cwd=workspace)
            cli = env / ("Scripts/ugarit-context-parsing.exe" if os.name == "nt"
                         else "bin/ugarit-context-parsing")
            run(str(cli), "module", "--help", cwd=workspace)
    finally:
        for probe in created:
            probe.unlink()
    print("Software-only sdist, rebuilt wheel and clean installed CLI: PASS")


if __name__ == "__main__":
    check()

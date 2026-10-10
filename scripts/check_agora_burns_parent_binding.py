"""Real pinned CUC + licensed Burns source through Agora's actual OS sandbox host.

Invocation is CI-only. No derivative corpus is uploaded or checked into Git.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from tf.fabric import Fabric

CUC_RELEASE = "0408967b1808c1f22c69e299d302b1e7b5e26354"
WARP = ("otype.tf", "oslots.tf", "otext.tf")


def _warp_hashes(parent: Path) -> dict[str, str]:
    return {
        name: hashlib.sha256((parent / name).read_bytes()).hexdigest()
        for name in WARP
    }


def _agora_host(agora_root: Path):
    # The producer itself ships a package named "scripts"; importing
    # "scripts.agora_materialize" could silently resolve to the wrong package.
    # Load the exact reviewed Agora host module by file location instead.
    path = agora_root / "scripts" / "agora_materialize.py"
    spec = importlib.util.spec_from_file_location("_reviewed_agora_materialize", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("reviewed Agora host module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        raise SystemExit(
            "usage: check_agora_burns_parent_binding.py "
            "AGORA_ROOT BURNS_CSV_ROOT CUC_TF_ROOT OUTPUT"
        )
    agora_root, source, parent, output = (Path(arg).resolve() for arg in argv)
    repository = Path(__file__).resolve().parents[1]
    if output.exists():
        raise ValueError("Agora host output must be absent before materialization")
    git_root = parent.parents[1]
    observed_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=git_root, text=True
    ).strip()
    if observed_revision != CUC_RELEASE:
        raise ValueError(f"CUC revision {observed_revision} differs from reviewed {CUC_RELEASE}")

    host = _agora_host(agora_root)
    original = Fabric(locations=[str(parent)], modules=[""], silent="deep").loadAll(
        silent="deep"
    )
    assert original is not None, "reviewed CUC parent cannot load"
    before = _warp_hashes(parent)
    binding = host.ParentBinding(
        path=parent,
        resource_id="cuc",
        version="0.2.8",
        source_revision=CUC_RELEASE,
        relative_path="tf/0.2.8",
        trusted=True,
    )
    produced = host.materialize(
        manifest_path=repository / "agora.materializer.json",
        materializer_id="cuc-burns-csv",
        source=source,
        parent=binding,
        output=output,
        sandbox="required",
    )
    assert produced == output
    assert before == _warp_hashes(parent), "Agora materialization modified the parent TF warp"

    feature_files = {p.name for p in output.iterdir() if p.is_file()}
    assert "burns_headword_1.tf" in feature_files, feature_files
    assert "burns-feature-module-report.json" in feature_files
    assert not feature_files.intersection(WARP), "Burns output replaced parent warp"
    assert all(p.is_file() and not p.is_symlink() for p in output.iterdir())
    receipt = json.loads((output / "agora-materialization.json").read_text())
    assert receipt["sandbox"] == "bubblewrap"
    assert receipt["parent"] == {
        "resource_id": "cuc",
        "version": "0.2.8",
        "source_revision": CUC_RELEASE,
        "relative_path": "tf/0.2.8",
        "trusted": True,
    }, receipt["parent"]

    composed = Fabric(
        locations=[str(parent), str(output)], modules=[""], silent="deep"
    ).loadAll(silent="deep")
    assert composed is not None, "Agora-produced Burns module cannot compose with CUC"
    assert composed.F.otype.maxSlot == original.F.otype.maxSlot
    assert composed.F.otype.maxNode == original.F.otype.maxNode
    carriers = sum(
        composed.F.burns_headword_1.v(word) is not None
        for word in original.F.otype.s("word")
    )
    assert carriers > 0, "no Burns annotations are queryable on existing CUC words"
    print(json.dumps({
        "status": "ok", "parent_revision": CUC_RELEASE, "sandbox": receipt["sandbox"],
        "slot_count": original.F.otype.maxSlot,
        "node_count": original.F.otype.maxNode,
        "burns_lane_1_word_carriers": carriers,
        "module_feature_files": len(feature_files) - 1,
        "parent_warp_unchanged": True,
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

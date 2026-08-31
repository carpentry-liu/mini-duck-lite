"""Build a fail-closed 10DOF ONNX deployment bundle for the Pi runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from mini_duck_lite.manifest import JOINT_ORDER


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_policy_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if contract.get("schema_version") != "policy-contract/v1":
        raise ValueError("unsupported policy contract schema")
    if tuple(contract.get("joint_order", ())) != JOINT_ORDER:
        raise ValueError("policy joint_order does not match Reference Prototype A")
    if contract.get("action_size") != 10:
        raise ValueError("only a self-owned 10DOF policy can target this hardware")
    if contract.get("control_hz") != 50:
        raise ValueError("deployed policy must target the 50 Hz runtime")
    normalization = contract.get("normalization")
    if not isinstance(normalization, dict) or not normalization:
        raise ValueError("normalization metadata must be a non-empty object")
    if not isinstance(contract.get("observation_size"), int):
        raise ValueError("observation_size must be an integer")
    if not isinstance(contract.get("action_scale"), (int, float)):
        raise ValueError("action_scale must be numeric")
    if not contract.get("training_commit"):
        raise ValueError("training_commit is required")
    if not contract.get("training_config_ref"):
        raise ValueError("training_config_ref is required")
    if not isinstance(contract.get("seed"), int):
        raise ValueError("training seed must be an integer")
    return contract


def build_policy_bundle(
    *, model: Path, contract_path: Path, output_dir: Path
) -> dict[str, Any]:
    if not model.is_file() or model.suffix.lower() != ".onnx":
        raise FileNotFoundError(f"ONNX model not found: {model}")
    contract = load_policy_contract(contract_path)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"policy bundle directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    model_target = output_dir / "policy.onnx"
    contract_target = output_dir / "policy-contract.json"
    shutil.copy2(model, model_target)
    shutil.copy2(contract_path, contract_target)
    manifest = {
        "schema_version": "policy-bundle/v1",
        "embodiment_version": contract["embodiment_version"],
        "action_size": contract["action_size"],
        "joint_order": contract["joint_order"],
        "control_hz": contract["control_hz"],
        "training_commit": contract["training_commit"],
        "model": {
            "file": model_target.name,
            "sha256": _sha256(model_target),
        },
        "contract": {
            "file": contract_target.name,
            "sha256": _sha256(contract_target),
        },
        "deployment_gate": "HIL_REQUIRED",
        "real_hardware_enabled": False,
    }
    manifest_path = output_dir / "bundle-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    manifest = build_policy_bundle(
        model=args.model, contract_path=args.contract, output_dir=args.output_dir
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

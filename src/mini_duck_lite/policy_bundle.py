"""Build a fail-closed 10DOF ONNX deployment bundle for the Pi runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _validate_normalization(normalization: Any, observation_size: int) -> None:
    """Describe preprocessing explicitly: identity or (observation - mean) / std."""

    if not isinstance(normalization, dict):
        raise ValueError("normalization must specify an explicit mode")
    mode = normalization.get("mode")
    if mode == "identity":
        if set(normalization) != {"mode"}:
            raise ValueError("identity normalization must contain only mode")
        return
    if mode != "standard":
        raise ValueError("normalization.mode must be standard or identity")
    if set(normalization) != {"mode", "mean", "std"}:
        raise ValueError("standard normalization requires only mode, mean, and std")
    for field in ("mean", "std"):
        values = normalization[field]
        if (
            not isinstance(values, list)
            or len(values) != observation_size
            or not all(_is_finite_number(value) for value in values)
        ):
            raise ValueError(
                f"normalization.{field} must have observation_size finite numbers"
            )
    if any(value <= 0 for value in normalization["std"]):
        raise ValueError("normalization.std values must be positive")


def load_policy_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if not isinstance(contract, dict):
        raise ValueError("policy contract must be a JSON object")
    if contract.get("schema_version") != "policy-contract/v1":
        raise ValueError("unsupported policy contract schema")
    if tuple(contract.get("joint_order", ())) != JOINT_ORDER:
        raise ValueError("policy joint_order does not match Reference Prototype A")
    if contract.get("action_size") != 10:
        raise ValueError("only a self-owned 10DOF policy can target this hardware")
    if contract.get("control_hz") != 50:
        raise ValueError("deployed policy must target the 50 Hz runtime")
    observation_size = contract.get("observation_size")
    if type(observation_size) is not int or observation_size <= 0:
        raise ValueError("observation_size must be a positive integer")
    _validate_normalization(contract.get("normalization"), observation_size)
    if not _is_finite_number(contract.get("action_scale")):
        raise ValueError("action_scale must be finite and numeric")
    for field in ("embodiment_version", "training_commit", "training_config_ref"):
        value = contract.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required and must be a non-empty string")
    if type(contract.get("seed")) is not int:
        raise ValueError("training seed must be an integer")
    return contract


def _validate_onnx(model: Path, contract: dict[str, Any]) -> dict[str, Any]:
    """Check a self-contained float32 graph for single-instance policy inference."""

    try:
        import onnx
        from google.protobuf.message import DecodeError
    except ImportError as exc:
        raise RuntimeError(
            "policy packaging requires ONNX; install mini-duck-lite[policy] "
            "or run uv sync --extra policy"
        ) from exc

    try:
        graph_model = onnx.load(model, load_external_data=False)
    except (DecodeError, OSError, ValueError) as exc:
        raise ValueError(f"cannot load ONNX model: {exc}") from exc

    # Traverse every nested message, including attribute/subgraph/sparse tensors.
    # External files are deliberately never opened or copied into the bundle.
    pending = [graph_model]
    while pending:
        message = pending.pop()
        if isinstance(message, onnx.TensorProto) and (
            message.data_location == onnx.TensorProto.EXTERNAL or message.external_data
        ):
            raise ValueError("ONNX external tensor data is not supported; export one file")
        for field, value in message.ListFields():
            if field.message_type is not None:
                pending.extend(value if field.is_repeated else [value])

    try:
        onnx.checker.check_model(graph_model, full_check=True, check_custom_domain=True)
    except (onnx.checker.ValidationError, onnx.shape_inference.InferenceError) as exc:
        raise ValueError(f"invalid ONNX graph: {exc}") from exc

    graph = graph_model.graph
    if len(graph.input) != 1 or len(graph.output) != 1:
        raise ValueError("ONNX policy must have exactly one input and one output")

    io_metadata: dict[str, Any] = {}
    for role, value_info, feature_count in (
        ("input", graph.input[0], contract["observation_size"]),
        ("output", graph.output[0], contract["action_size"]),
    ):
        if not value_info.type.HasField("tensor_type"):
            raise ValueError(f"ONNX {role} must be a float32 tensor")
        tensor_type = value_info.type.tensor_type
        if tensor_type.elem_type != onnx.TensorProto.FLOAT:
            raise ValueError(f"ONNX {role} must be a float32 tensor")
        dims = tensor_type.shape.dim
        expected = [1, feature_count]
        if len(dims) != 2 or any(not dim.HasField("dim_value") for dim in dims):
            raise ValueError(f"ONNX {role} requires a fixed shape {expected}")
        actual = [dim.dim_value for dim in dims]
        if actual != expected:
            raise ValueError(
                f"ONNX {role} shape {actual} does not match contract shape {expected}"
            )
        io_metadata[role] = {
            "name": value_info.name,
            "shape": actual,
            "dtype": "float32",
        }
    return io_metadata


def build_policy_bundle(
    *, model: Path, contract_path: Path, output_dir: Path
) -> dict[str, Any]:
    if not model.is_file() or model.suffix.lower() != ".onnx":
        raise FileNotFoundError(f"ONNX model not found: {model}")
    contract = load_policy_contract(contract_path)
    io_metadata = _validate_onnx(model, contract)
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
            **io_metadata,
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

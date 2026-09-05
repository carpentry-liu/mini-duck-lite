from __future__ import annotations

import json
from pathlib import Path

import pytest
import onnx
from onnx import TensorProto, helper

from mini_duck_lite.evidence import EvidenceLevel, can_transition, validate_evidence
from mini_duck_lite.hardware import MockImuBackend, MockServoBus
from mini_duck_lite.manifest import JOINT_ORDER, audit_manifest, load_manifest
from mini_duck_lite.policy_bundle import build_policy_bundle
from mini_duck_lite.qualification import load_plan, run_qualification
from mini_duck_lite.runtime import SafeRuntime, load_runtime_config


ROOT = Path(__file__).resolve().parents[1]


def test_reference_manifest_is_valid_but_fails_closed_for_real_runtime() -> None:
    data = load_manifest(ROOT / "config/hardware/reference-prototype-a.json")
    report = audit_manifest(data)

    assert report["valid"] is True
    assert report["runtime_ready"] is False
    assert any("C044/C046" in blocker for blocker in report["runtime_blockers"])
    assert any("TBD_MEASURE" in blocker for blocker in report["runtime_blockers"])


def test_mock_qualification_writes_csv_and_json_without_claiming_hil(
    tmp_path: Path,
) -> None:
    output = tmp_path / "qualification"
    summary = run_qualification(
        plan=load_plan(ROOT / "config/qualification/h1-c044-c046.json"),
        output_dir=output,
        sku="STS3215-C044",
        bus_id=1,
        bus=MockServoBus([1]),
        backend_name="mock",
        quick=True,
    )

    assert summary["evidence_level"] == "SIM_PASS"
    assert summary["gate_eligible"] is False
    assert summary["sample_count"] > 0
    assert (output / "samples.csv").is_file()
    assert (output / "metadata.json").is_file()
    assert (output / "summary.json").is_file()


def test_real_runtime_rejects_sim_only_limits() -> None:
    with pytest.raises(ValueError, match="SIM_ONLY"):
        load_runtime_config(ROOT / "config/runtime/mock-10dof.json")


def test_runtime_enters_safe_state_on_stale_command() -> None:
    config = load_runtime_config(
        ROOT / "config/runtime/mock-10dof.json", allow_sim_limits=True
    )
    now = [0.0]
    runtime = SafeRuntime(
        config=config,
        servo_bus=MockServoBus(list(config.soft_limits_rad)),
        imu=MockImuBackend(),
        clock=lambda: now[0],
    )
    runtime.set_command(config.safe_pose_rad)
    now[0] = 0.2

    assert runtime.tick() == {"status": "SAFE_STATE", "reason": "COMMAND_TIMEOUT"}


def test_runtime_enters_safe_state_on_servo_disconnect() -> None:
    config = load_runtime_config(
        ROOT / "config/runtime/mock-10dof.json", allow_sim_limits=True
    )
    bus = MockServoBus(list(config.soft_limits_rad))
    runtime = SafeRuntime(config=config, servo_bus=bus, imu=MockImuBackend())
    runtime.set_command(config.safe_pose_rad)
    bus.set_connected(1, False)

    assert runtime.tick() == {
        "status": "SAFE_STATE",
        "reason": "SERVO_1_DISCONNECTED",
    }


def test_real_evidence_requires_hardware_video_and_failure_accounting() -> None:
    record = {
        "level": "REAL_PASS",
        "git_commit": "abc123",
        "config_ref": "config.json",
        "telemetry_ref": "telemetry.jsonl",
        "attempts": 10,
        "successes": 8,
    }

    errors = validate_evidence(record)
    assert "hardware_revision is required for HIL/REAL" in errors
    assert "video_ref is required for HIL/REAL" in errors
    assert "failure_reasons must be a list for REAL_PASS" in errors


def test_evidence_levels_cannot_skip_hil_or_move_backward() -> None:
    assert can_transition(None, EvidenceLevel.SIM_PASS)
    assert can_transition(EvidenceLevel.SIM_PASS, EvidenceLevel.HIL_PASS)
    assert can_transition(EvidenceLevel.HIL_PASS, EvidenceLevel.REAL_PASS)
    assert not can_transition(EvidenceLevel.SIM_PASS, EvidenceLevel.REAL_PASS)
    assert not can_transition(EvidenceLevel.REAL_PASS, EvidenceLevel.HIL_PASS)


def test_policy_bundle_requires_self_owned_10dof_contract(tmp_path: Path) -> None:
    model = tmp_path / "policy.onnx"
    graph = helper.make_graph(
        [helper.make_node("MatMul", ["obs", "weights"], ["actions"])],
        "ten-dof-test",
        [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, 50])],
        [helper.make_tensor_value_info("actions", TensorProto.FLOAT, [1, 10])],
        initializer=[helper.make_tensor("weights", TensorProto.FLOAT, [50, 10], [0.0] * 500)],
    )
    onnx.save(helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)]), model)
    contract = {
        "schema_version": "policy-contract/v1",
        "embodiment_version": "reference-prototype-a/test",
        "joint_order": list(JOINT_ORDER),
        "observation_size": 50,
        "action_size": 10,
        "normalization": {"mode": "standard", "mean": [0.0] * 50, "std": [1.0] * 50},
        "action_scale": 0.25,
        "control_hz": 50,
        "training_commit": "deadbeef",
        "training_config_ref": "config/train.json",
        "seed": 42,
    }
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    manifest = build_policy_bundle(
        model=model, contract_path=contract_path, output_dir=tmp_path / "bundle"
    )

    assert manifest["action_size"] == 10
    assert manifest["real_hardware_enabled"] is False
    assert (tmp_path / "bundle/policy.onnx").is_file()
    assert (tmp_path / "bundle/bundle-manifest.json").is_file()

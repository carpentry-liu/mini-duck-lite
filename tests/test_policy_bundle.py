from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
import pytest

from mini_duck_lite.manifest import JOINT_ORDER
from mini_duck_lite.policy_bundle import build_policy_bundle, load_policy_contract


@pytest.fixture
def contract() -> dict:
    return {
        "schema_version": "policy-contract/v1",
        "embodiment_version": "reference-prototype-a/test",
        "joint_order": list(JOINT_ORDER),
        "observation_size": 4,
        "action_size": 10,
        "normalization": {"mode": "standard", "mean": [0.0] * 4, "std": [1.0] * 4},
        "action_scale": 0.25,
        "control_hz": 50,
        "training_commit": "deadbeef",
        "training_config_ref": "config/train.json",
        "seed": 42,
    }


def write_contract(tmp_path: Path, contract) -> Path:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    return path


def make_policy(observations: int = 4, actions: int = 10) -> onnx.ModelProto:
    weights = numpy_helper.from_array(
        np.ones((observations, actions), dtype=np.float32), name="weights"
    )
    graph = helper.make_graph(
        [helper.make_node("MatMul", ["obs", "weights"], ["actions"])],
        "test-policy",
        [helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, observations])],
        [helper.make_tensor_value_info("actions", TensorProto.FLOAT, [1, actions])],
        initializer=[weights],
    )
    return helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])


@pytest.mark.parametrize("normalization", ["standard", "identity"])
def test_valid_model_bundles_verified_io_and_unchanged_payload(
    tmp_path: Path, contract: dict, normalization: str
) -> None:
    if normalization == "identity":
        contract["normalization"] = {"mode": "identity"}
    model = tmp_path / "model.onnx"
    onnx.save(make_policy(), model)
    contract_path = write_contract(tmp_path, contract)

    manifest = build_policy_bundle(
        model=model, contract_path=contract_path, output_dir=tmp_path / "bundle"
    )

    assert manifest["model"]["input"] == {
        "name": "obs", "shape": [1, 4], "dtype": "float32"
    }
    assert manifest["model"]["output"] == {
        "name": "actions", "shape": [1, 10], "dtype": "float32"
    }
    assert manifest["model"]["sha256"] == hashlib.sha256(model.read_bytes()).hexdigest()
    assert (tmp_path / "bundle/policy.onnx").read_bytes() == model.read_bytes()
    assert (tmp_path / "bundle/policy-contract.json").read_bytes() == contract_path.read_bytes()
    assert manifest["real_hardware_enabled"] is False


@pytest.mark.parametrize("observations,actions", [(4, 14), (5, 10)])
def test_model_dimensions_must_match_contract(
    tmp_path: Path, contract: dict, observations: int, actions: int
) -> None:
    model = tmp_path / "model.onnx"
    onnx.save(make_policy(observations, actions), model)
    with pytest.raises(ValueError, match="does not match contract"):
        build_policy_bundle(
            model=model,
            contract_path=write_contract(tmp_path, contract),
            output_dir=tmp_path / "bundle",
        )
    assert not (tmp_path / "bundle").exists()


@pytest.mark.parametrize("bad_model", ["text", "disconnected_graph", "false_output_shape"])
def test_onnx_parser_and_checker_reject_invalid_graphs(
    tmp_path: Path, contract: dict, bad_model: str
) -> None:
    model = tmp_path / "model.onnx"
    if bad_model == "text":
        model.write_bytes(b"test-onnx")
    else:
        graph_model = make_policy()
        if bad_model == "disconnected_graph":
            graph_model.graph.node[0].input[0] = "missing_observation"
        else:
            # The annotation claims 10 actions but the graph computes 14.
            graph_model = make_policy(actions=14)
            graph_model.graph.output[0].type.tensor_type.shape.dim[1].dim_value = 10
        onnx.save(graph_model, model)
    with pytest.raises(ValueError, match="ONNX"):
        build_policy_bundle(
            model=model,
            contract_path=write_contract(tmp_path, contract),
            output_dir=tmp_path / "bundle",
        )
    assert not (tmp_path / "bundle").exists()


@pytest.mark.parametrize("unsupported", ["multi_input", "multi_output", "dynamic_feature", "dynamic_batch", "double"])
def test_unsupported_io_fails_closed(
    tmp_path: Path, contract: dict, unsupported: str
) -> None:
    graph_model = make_policy()
    graph = graph_model.graph
    if unsupported == "multi_input":
        graph.input.append(helper.make_tensor_value_info("extra", TensorProto.FLOAT, [1, 4]))
    elif unsupported == "multi_output":
        graph.output.append(helper.make_tensor_value_info("obs", TensorProto.FLOAT, [1, 4]))
    elif unsupported.startswith("dynamic"):
        index = 1 if unsupported == "dynamic_feature" else 0
        graph.input[0].type.tensor_type.shape.dim[index].dim_param = "dynamic"
    else:
        graph.input[0].type.tensor_type.elem_type = TensorProto.DOUBLE
        graph.output[0].type.tensor_type.elem_type = TensorProto.DOUBLE
        graph.initializer[0].CopyFrom(
            numpy_helper.from_array(np.ones((4, 10), dtype=np.float64), name="weights")
        )
    model = tmp_path / "model.onnx"
    onnx.save(graph_model, model)
    with pytest.raises(ValueError, match="ONNX"):
        build_policy_bundle(
            model=model,
            contract_path=write_contract(tmp_path, contract),
            output_dir=tmp_path / "bundle",
        )
    assert not (tmp_path / "bundle").exists()


@pytest.mark.parametrize("tensor_location", ["initializer", "attribute"])
def test_external_tensor_payload_is_rejected_without_loading_it(
    tmp_path: Path, contract: dict, tensor_location: str
) -> None:
    graph_model = make_policy()
    tensor = graph_model.graph.initializer[0]
    onnx.external_data_helper.set_external_data(tensor, location="absent-weights.bin")
    tensor.ClearField("raw_data")
    if tensor_location == "attribute":
        constant = helper.make_node("Constant", [], ["weights"], value=tensor)
        del graph_model.graph.initializer[:]
        graph_model.graph.node.insert(0, constant)
    model = tmp_path / "model.onnx"
    model.write_bytes(graph_model.SerializeToString())
    with pytest.raises(ValueError, match="external tensor data"):
        build_policy_bundle(
            model=model,
            contract_path=write_contract(tmp_path, contract),
            output_dir=tmp_path / "bundle",
        )
    assert not (tmp_path / "bundle").exists()


@pytest.mark.parametrize(
    "normalization",
    [
        None,
        {"status": "TBD_MEASURE"},
        {"mean": [0.0] * 4, "std": [1.0] * 4},
        {"mode": "baked_in"},
        {"mode": "identity", "mean": [0.0] * 4},
        {"mode": "standard", "mean": [0.0], "std": [1.0]},
        {"mode": "standard", "mean": [0.0] * 4, "std": [0.0] * 4},
        {"mode": "standard", "mean": [0.0] * 4, "std": [-1.0] * 4},
        {"mode": "standard", "mean": [float("nan")] * 4, "std": [1.0] * 4},
        {"mode": "standard", "mean": [0.0] * 4, "std": [float("inf")] * 4},
        {"mode": "standard", "mean": [False] * 4, "std": [1.0] * 4},
    ],
)
def test_invalid_normalizer_is_rejected(tmp_path: Path, contract: dict, normalization) -> None:
    contract["normalization"] = normalization
    with pytest.raises(ValueError, match="normalization"):
        load_policy_contract(write_contract(tmp_path, contract))


@pytest.mark.parametrize("size", [-1, 0, True, 4.0, None])
def test_observation_size_must_be_a_positive_integer(
    tmp_path: Path, contract: dict, size
) -> None:
    contract["observation_size"] = size
    with pytest.raises(ValueError, match="observation_size"):
        load_policy_contract(write_contract(tmp_path, contract))


@pytest.mark.parametrize("scale", [float("nan"), float("inf"), True, None])
def test_action_scale_must_be_finite(tmp_path: Path, contract: dict, scale) -> None:
    contract["action_scale"] = scale
    with pytest.raises(ValueError, match="action_scale"):
        load_policy_contract(write_contract(tmp_path, contract))


def test_missing_embodiment_is_rejected_before_creating_bundle(tmp_path: Path, contract: dict) -> None:
    del contract["embodiment_version"]
    model = tmp_path / "model.onnx"
    onnx.save(make_policy(), model)
    with pytest.raises(ValueError, match="embodiment_version"):
        build_policy_bundle(
            model=model,
            contract_path=write_contract(tmp_path, contract),
            output_dir=tmp_path / "bundle",
        )
    assert not (tmp_path / "bundle").exists()


def test_importing_runtime_and_bundle_does_not_load_onnx() -> None:
    subprocess.run(
        [sys.executable, "-c", "import sys; import mini_duck_lite.runtime; import mini_duck_lite.policy_bundle; assert 'onnx' not in sys.modules"],
        check=True,
    )

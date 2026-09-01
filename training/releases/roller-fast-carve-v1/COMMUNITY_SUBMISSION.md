# Community submission draft: continuous roller obstacle showcase

This folder is ready to be linked from a Microduck GitHub discussion, pull request, or Hugging Face Space community proposal.

## Proposed title

**Continuous roller showcase: fast carve, moving crouch under a gate, spin and stop**

## Short description

This contribution adds a reproducible simulation showcase built on `pollen-robotics/microduck_rl`. It combines the upstream roller policy with two locally trained 50 Hz policies: a forward-speed-tracking crouch policy and a spin policy. The controller keeps the robot moving through a 92.6-degree carve and a low gate instead of stopping and changing poses. The release includes source patches, PPO checkpoints, ONNX exports, TensorBoard events, terminal logs, per-control-step metrics, a JSON acceptance summary, and a 50 fps video.

## Reproducible result

- Upstream base: `d424a0c899f6b33cbd3daeb279913134349c0b63`
- Experiment commit: `98701254cd78e3d197dd8e2a0366b61cdf121073`
- 4,096 parallel environments on an NVIDIA RTX 5060 Ti under WSL2
- 4.631 m continuous route
- 0.535 m/s turn entry; 0.258 m/s minimum speed in the carve
- 0.390 m/s at gate crossing; 0.344 m/s minimum through the gate window
- 344.8-degree final spin with 6.8 cm drift
- Evidence level: simulation only; no sim-to-real claim

## Suggested upstream scope

The smallest reviewable contribution is the dynamic crouch reward/config, the route evaluator, and an optional browser demo mode for the official simulator. The two patch files apply cleanly to the pinned upstream base. The full payload is integrity-checked through `MANIFEST.json` and `verify_release.py`.

## Maintainer notes

- `upstream_roller.onnx` is redistributed unchanged and its SHA-256 matches the upstream policy record.
- The new checkpoints and ONNX files are separated from the upstream model.
- The showcase controller does not teleport the base or replay joint keyframes.
- The route is fixed and does not claim vision-based obstacle navigation.
- No official affiliation is implied.

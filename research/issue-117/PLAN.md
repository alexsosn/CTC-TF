# #117 Plan

1. Preserve RED tests asserting root manifest exists, has only a local CSV source, exact `{parent}` binding, approved Python module/args, network denied, CUC 0.2.8 parent, composition feature-module, and stable output report. Assert no warp in declared output paths, no `convert` invocation or remote acquisition. Add schema validation against Agora's real schema where available.
2. GREEN add root `agora.materializer.json` with one `cuc-burns-csv` materializer; package/manifest version `0.3.0`.
3. Exact-head Python matrix, real pinned Workbooks, reviewed CUC and Context-Fabric checks. Review Agora install path and runtime tests before claiming Agora end-to-end integration.
4. Logically independent adversarial review grounded in real schema, CLI and generated output; fix findings. Do not merge until release gate and Agora #135 coordination.

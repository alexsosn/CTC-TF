# #66 Plan

1. RED tests: both writers raising `ValueError` map to labeled `SystemExit`; `False` return retains original messages; `ValueError` raised by module construction propagates untouched; successful output unchanged.
2. GREEN: add narrow `try/except ValueError` around each `write_*_module` call only. Avoid broad exception catch or changing public writer APIs.
3. Exact-head Python 3.10/3.12/3.13, reviewed CUC, real Workbooks and Context-Fabric gates.
4. Logically independent adversarial review of actual diff and synthetic tests. Keep draft until v0.3.0 release gate.

# NVIDIA Nemotron 3.5 Lightning evaluation

Date: 2026-09-19

## Candidate

- Provider: NVIDIA Build API
- Model: `nvidia/nemotron-3.5-lightning-30b-a3b`
- Intended data: synthetic public text only
- Published shape: 30B total parameters, 3B active parameters
- Production limits used by LYA: 1,024 output tokens and an eight-second request deadline

The model was selected for a bounded backup trial because NVIDIA describes it as a
reasoning/coding model with a small active parameter count. Published model claims
were treated as candidate-selection evidence, not proof of LYA quality or latency.

## Result

The first frozen evaluation case failed with `provider_unavailable` on both paths:

| Path | Thinking mode | Recorded request time | Answer |
| --- | --- | ---: | --- |
| Laptop direct | disabled | 8,078 ms | none |
| Oracle remote | disabled | 8,001 ms | none |

An earlier laptop attempt also failed after roughly 8.3 seconds. Disabling model
thinking did not make the route pass the fixed deadline. Evaluation stopped after
the first failure to preserve the bounded-call and free-account policy.

## Decision

Keep this route disabled. It cannot complete T02 because it did not pass even one
case inside the production deadline, much less the full suite and repeated latency
checks. The raw sanitized reports are `laptop-no-thinking.json` and `oracle.json`.
They contain no credentials or private prompts.

Source consulted: [NVIDIA model page](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b).


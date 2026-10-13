# Phase 2: local read-only assistance and measured limits

Implemented Spring AI/Ollama, text/PDF retrieval, exact source offsets, quote validation, bounded fine-print suggestions, safe small Markdown rendering, source highlighting, streaming lifecycle/stop, owner-scoped history and deletion. The model has no mutation tools. Unsupported or rejected generation falls back to deterministic source passages; manual workflows and verification do not require a model.

Actual direct-model text and synthetic vision measurements are in `../LOCAL_AI_BENCHMARK.md`. Grounding tests reject fabricated quotations and preserve offsets. Spring's hostile-source integration checks exact quotes and no credential/grant mutation. The final measured status is recorded in `../verification-results.json`, including rejection when it occurs. Optional image UI and unchecked token streaming were cut. A real quote does not establish factual or interpretive correctness.

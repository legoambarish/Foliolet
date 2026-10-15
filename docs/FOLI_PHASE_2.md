# Foli phase 2 — loopback inference and flexible Q&A

Spring AI 2.0.1 is pinned with its BOM, using the explicit Ollama model library (no starter/autopull, advisors or tool callbacks). Its compatibility with this checkout's Spring Boot 4.1.1 was confirmed by a real dependency resolution, compile and transport test. The source project is Apache-2.0 licensed; model-specific license receipts are captured by the model comparison script.

The numeric loopback transport bypasses environment proxies and refuses redirects, remote names, paths and credentials in the configured origin. Every inference checks Ollama's actual `/api/status` cloud-disabled flag and installed package size (<6,000,000,000 bytes). The local runtime reports cloud disabled. Questions/history/source excerpts are never sent to the existing OpenRouter integrations. Chat has no write/tool API.

Implemented owner-scoped asynchronous jobs, cancellation, bounded queue/rate/context/history, model health, lexical retrieval with clause references, and structured citations revalidated against exact source offsets. An instruction in document content cannot grant tool permissions. Original documents and trust workflows remain read-only. Client-provided history is untrusted context, never authorization.

The Spring AI chat request does not serialize `truncate=false`; its similarly named option is not a chat safeguard. Foli instead enforces a conservative UTF-8 byte upper bound before sending, reserving output and message-template overhead, and reduces supplied excerpts/history explicitly with warnings. This avoids claiming a setting is effective when transport tests show otherwise.

Gates measured so far:

- 9 focused Q&A/transport/job/boundary tests passed, including missing/cloud-enabled/oversized/offline models, hostile origins/body bounds, wrong-user jobs, cancellation, source changes, invented evidence and unsupported quotes.
- Independent labeled source-page retrieval: 58/60 (96.7%) before additional general dispute/email expansions. Full end-to-end corpus results are recorded in phase 5.
- Real Spring AI/Ollama HTTP smoke: three supported document answers with exact permitted source citations. Initial benchmark comparison mistakenly required line wrapping to equal the hand-authored gold sentence; source quotes themselves always matched exact offsets. The rubric now normalizes whitespace only when comparing the gold sentence, while source-offset verification stays exact.
- Actual qwen3:4b-instruct package: 2,497,293,803 bytes; digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`. Initial qwen/gemma synthetic raw-model results and a revised explicit-instruction run are both retained. Both models still missed conflict handling; qwen safely abstained on one injected source. These failures motivate the whole-document review and are not represented as model correctness.

The initial default is provisional pending the full corpus and 3B/7B comparison in phase 5. CPU-only fallback has also been run; final timing and resource receipts belong in the handoff. No physical system-wide network disconnect has yet been performed. Local-only transport and disabled cloud mode are enforced, rather than inferred from a successful answer.

References: [Spring AI compatibility](https://docs.spring.io/spring-ai/reference/getting-started.html), [Ollama FAQ](https://docs.ollama.com/faq), [Qwen model tag](https://ollama.com/library/qwen3:4b-instruct).

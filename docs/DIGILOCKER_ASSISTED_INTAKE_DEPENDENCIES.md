# Dependency and local-model record

Recorded on Windows on 16 October 2026. Production code adds exactly one Maven dependency. There is no new AI framework, native vision package, external AI service, paid service or model download.

| Item | Observed value |
| --- | --- |
| New artifact | `pkg:maven/com.google.zxing/core@3.5.4` |
| JAR | `core-3.5.4.jar`, 610,364 bytes |
| SHA-256 | `71de5d89341b5fcf5dd89da7f44e84d825d0e084cdf3ec77c9abe26b0f0ceb13` |
| Declared license | Apache-2.0 |
| Runtime purpose | Offline QR pixel decoding; no URL fetching or issuer-signature verification |
| New runtime transitive dependencies | None from `zxing:core` |
| Existing local model reused | `qwen3:4b-instruct` |
| Observed model package | 2,497,293,803 bytes, below 5 GB |
| Observed model digest | `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |
| Existing OCR reused | Tesseract 5.5.3 with retained local trained data |
| Existing PDF library reused | PDFBox 3.0.8 |

Static review: the Maven artifact/POM and upstream Apache license were inspected; `core` has no native installer or runtime library dependencies. The application explicitly bounds rendered pixels, QR payload length, decoded results and scan work. Payloads remain untrusted data; persisted QR diagnostics are hashes/classes/bounds. No decoded URL is executed or logged. This is a scoped dependency/license review, not a claim of a complete software vulnerability audit or zero vulnerabilities. Existing dependencies such as Ganache retain their previous limitations.

Primary references: [ZXing release history](https://github.com/zxing/zxing/releases), [upstream license](https://github.com/zxing/zxing/blob/master/LICENSE), [project POM](https://github.com/zxing/zxing/blob/master/pom.xml), [security policy](https://github.com/zxing/zxing/security), [published artifact POM](https://repo.maven.apache.org/maven2/com/google/zxing/core/3.5.4/core-3.5.4.pom).

The feature worktree received its own Python virtual environment and the repository's existing Django/dev/Foli-test requirements. Maven downloaded the new 610 KB JAR into the ordinary user cache. Existing portable PostgreSQL/OCR/Node packages in `Foliolet-testcloudflare` were read through `-RuntimeRoot`; their source trees, databases, models and keys were not modified. The installed Ollama runtime/model were initially reused without stopping them, changing configuration or pulling packages. After that shared service disappeared, a hash-checked copy of only this same selected model and CPU runtime was created inside the feature worktree and served on an independent loopback port. The original files and shared service configuration remained untouched. No additional model was downloaded. Playwright and Edge were reused from the existing bundled runtime/browser. Synthetic PDF/image generation uses the existing test-only PyMuPDF/Pillow requirements, not the production import path.

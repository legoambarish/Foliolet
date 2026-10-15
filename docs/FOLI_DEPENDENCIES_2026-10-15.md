# Foli dependency and license receipts — 15 October 2026

Application versions were resolved and built locally; downloads were explicit setup actions. This inventory records supplier license labels, not legal advice or a redistribution clearance. Runtime state/weights are ignored rather than bundled in source.

| Component | Version / license |
| --- | --- |
| Spring AI Ollama | 2.0.1, Apache-2.0; BOM pinned in pom.xml, compatible with existing Boot 4.1.1 |
| PDFBox | 3.0.8, Apache-2.0 |
| Ollama | 0.40.3, MIT; archive SHA-256 e5ecff02dfc7cae8ddf6d6b7a7ac5f727ffeedf4491f44ae75ff5b0820dbbbd5 |
| Tesseract / Leptonica | 5.5.3 Apache-2.0 / 1.87.0 BSD-2-Clause |
| Python application / browser | Existing Django requirements retained; Playwright 1.62.1 Apache-2.0 is test-only |
| Repeat fixture generator only | PyMuPDF 1.27.2 AGPL-3.0/commercial; Pillow 12.1.1 HPND. Neither is the production parser. |

The retained fixture PDFs were initially generated with bundled PyMuPDF 1.28.2 and Pillow 12.3. The repeat-generator pins were installed afterward. Gold wording/pages are fixed; byte-identical PDF regeneration is not claimed across those library versions. Original fixture bytes/hashes are preserved, and each live citation uses its actual source SHA-256.

The OCR lock pins 31 exact conda-forge package URLs/builds with MD5 archive fragments; full SHA-256 and supplier license metadata are retained in `.local-data/foli/ocr-package-receipts.json`. Its offline dry run succeeded without modifying the installed environment. Micromamba 2.9.0 archive SHA-256: `97a336f4ab794bd96a6a4da5e6ed63e75a1d31830414a182419b23d3b36f3fe0`.

OCR lock SHA-256: `3c3aba362037f9c0406a943c7b6d08a24b88691d566eadfde0fcfaed8b77f5c2`.

| OCR package | Exact version/build | Supplier license |
| --- | --- | --- |
| bzip2 | 1.0.8 / h0ad9c76_10 | bzip2-1.0.6 |
| ca-certificates | 2026.7.22 / h4c7d964_0 | ISC |
| giflib | 5.2.2 / hb0bd012_1 | MIT |
| icu | 78.3 / h5112557_2 | MIT |
| krb5 | 1.22.2 / h719d79b_2 | MIT |
| leptonica | 1.87.0 / hb83fb89_1 | BSD-2-Clause |
| lerc | 4.2.0 / hd936e49_0 | Apache-2.0 |
| libarchive | 3.8.9 / gpl_h8fdc8af_101 | BSD-2-Clause |
| libcurl | 8.23.0 / hdb0ef4a_0 | curl |
| libdeflate | 1.25 / h1a1d4e4_1 | MIT |
| libiconv | 1.18 / hc1393d2_3 | LGPL-2.1-only |
| libjpeg-turbo | 3.2.0 / hfd05255_1 | IJG AND BSD-3-Clause AND Zlib |
| liblzma | 5.8.3 / hfd05255_1 | 0BSD |
| libpng | 1.6.59 / hdc8cecf_0 | zlib-acknowledgement |
| libpsl | 0.23.1 / h9b16d47_1 | MIT |
| libssh2 | 1.11.1 / h734d217_1 | BSD-3-Clause |
| libtiff | 4.7.2 / h8f73337_1 | HPND |
| libwebp-base | 1.6.0 / h4d5522a_1 | BSD-3-Clause |
| libxml2-16 | 2.15.4 / h3cfd58e_1 | MIT |
| libxml2 | 2.15.4 / he095d88_1 | MIT |
| libzlib | 1.3.2 / hfd05255_3 | Zlib |
| lz4-c | 1.10.0 / h6a83c73_2 | BSD-2-Clause |
| lzo | 2.10 / h6a83c73_1003 | GPL-2.0-or-later |
| openjpeg | 2.5.4 / h90fa87c_2 | BSD-2-Clause |
| openssl | 3.6.5 / hf411b9b_0 | Apache-2.0 |
| tesseract | 5.5.3 / he87eeb8_0 | Apache-2.0 |
| ucrt | 10.0.26100.0 / h57928b3_0 | LicenseRef-MicrosoftWindowsSDK10 |
| vc | 14.5 / ha367084_41 | BSD-3-Clause |
| vc14_runtime | 14.51.36247 / habf1de7_41 | LicenseRef-MicrosoftVisualCpp2015-2022Runtime |
| vcomp14 | 14.51.36247 / habf1de7_41 | LicenseRef-MicrosoftVisualCpp2015-2022Runtime |
| zstd | 1.5.7 / h534d264_7 | BSD-3-Clause |

## Measured model identities

- **qwen3:4b-instruct** — 2,497,293,803 bytes, Q4_K_M, Apache-2.0; digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.
- **gemma3:4b** — 3,350,272,403 bytes, Q4_K_M, Gemma Terms of Use; digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.
- **qwen2.5:7b** — 4,683,087,332 bytes, Q4_K_M, Apache-2.0; digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
- **qwen2.5:3b** — 1,929,912,432 bytes, Q4_K_M, Qwen Research License Agreement; digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.

All four measured packages are strictly below 6 GB individually. Their licenses differ; the research-licensed 3B candidate and Gemma are not selected or redistributed with this source. Package storage, context/KV allocation, process RAM and VRAM are distinct. Model tags can move upstream: verify the recorded digest and repeat benchmarks after any change.

Primary references: [Spring AI compatibility](https://docs.spring.io/spring-ai/reference/getting-started.html), [Ollama FAQ](https://docs.ollama.com/faq), [selected Qwen tag](https://ollama.com/library/qwen3:4b-instruct), [Tesseract](https://github.com/tesseract-ocr/tesseract), [PDFBox](https://pdfbox.apache.org/), [PyMuPDF license](https://pymupdf.readthedocs.io/en/latest/about.html#license).

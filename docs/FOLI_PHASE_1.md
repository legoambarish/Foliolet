# Foli phase 1 — authorized source reading

Implemented an independent, read-only resolver for the existing encrypted wallet and legacy file store. Wallet access is owner-only; legacy access follows uploader/admin policy. No restore, verification, repository-save, upload, share or chain operation is called. Every cache lookup, job result and source view reopens the authorized original and checks version and SHA-256; wallet decryption also checks the recorded Keccak hash.

PDFBox 3.0.8 reads pages individually. Scans, mixed image/text pages and suspicious text use local Tesseract 5.5.3. OCR records confidence, rotation, exact text offsets and word boxes. OCR quotations remain visually uncertain. Limits produce explicit page statuses rather than silently truncating the legacy 15,000-character result. TXT/CSV preserve physical lines; unsupported formats and protected/corrupt PDFs fail clearly.

Measured gates (2026-10-15, Windows native):

- Original Java regression plus reader tests: 36 passed, zero failures.
- Real HTTP/PostgreSQL reading/authentication checks: 26 passed. Synthetic two-holder fixtures only; originals remained byte-identical.
- Explicit live OCR + reader run: 15 passed, zero failures or skips (11 reader + 4 real OCR). Includes rotated raster scan, negation/numeric text, mixed text/image PDF, missing executable and temporary-file cleanup.
- 125-page synthetic contract: all 125 pages accounted for and readable, including the final overriding exception. Limit/protected/corrupt/unsupported cases are separately tested.

Commands and retained logs are under the ignored `.local-data/foli/` directory. The live OCR command sets `FOLI_TESSERACT` to `.local-tools/ocr/Library/bin/tesseract.exe` and `FOLI_OCR_DATA_DIR` to `.local-tools/ocr/share/tessdata` before running Maven with `-Dtest=FoliReadingTest,FoliOcrLiveIT`. The first live OCR attempt failed because the portable package splits language data and config directories; using the actual language directory and the explicit `tessedit_create_tsv=1` option resolved it. Failed-run evidence is retained.

Extraction coverage is not a claim of perfect OCR, complete legal interpretation or document authenticity. Native layout can still be ambiguous; warning-bearing and OCR pages are shown as uncertain.

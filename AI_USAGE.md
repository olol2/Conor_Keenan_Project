# AI Usage

AI tools were used to support development of this project, primarily during the coding and debugging phases. They were not used to generate the underlying data or to make any methodological choices.

## Tools used
- Microsoft Copilot
- ChatGPT

## How AI tools were used

- **Scraping**
  - Assisted with implementation patterns for web scraping (requests/session handling, parsing, pagination) and with identifying common pitfalls (rate limits, missing pages, inconsistent HTML).

- **Code completion and syntax support (Copilot)**
  - Autocompletion of code patterns.
  - Reduced syntax errors and typos while implementing pre-defined logic

- **Debugging support (ChatGPT)**
  - Interpreting Python tracebacks and explaining likely causes
  - Suggesting concrete fixes (e.g., path handling, module imports, edge cases)
  - Reviewing small code snippets to identify logical errors

- **Reproducibility and portability**
  - Suggestions to make the pipeline runnable from the repository root via `python main.py`
  - Recommendations for cross-machine robustness (relative paths, directory creation, dependency clarity)

## What was not delegated to AI
- Final methodological decisions (proxy definitions, thresholds, modeling choices)
- Final interpretation of results and conclusions
- Final selection of figures/tables included in the report

## Verification performed by the author
- Ran `python main.py` end-to-end after changes and confirmed consistent outputs are       written to `results/`.
- Confirmed the code runs from the repository root using relative paths.
- Performed reruns after refactors to ensure outputs were consistent and the pipeline remained stable.

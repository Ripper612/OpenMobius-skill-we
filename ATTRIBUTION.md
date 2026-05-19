# Third-Party Components and Attribution

This project (`OpenMobius-skill`) is licensed under Apache 2.0 (see `LICENSE`).
It depends on the following open-source components, each under its own
license. We do not redistribute these components in this repository — they
are downloaded from their canonical sources during install.

## Runtime dependencies (installed via pip from PyPI)

| Package | License | Source |
|---|---|---|
| sentence-transformers | Apache-2.0 | https://github.com/UKPLab/sentence-transformers |
| chromadb | Apache-2.0 | https://github.com/chroma-core/chroma |
| numpy | BSD-3-Clause | https://github.com/numpy/numpy |
| einops | MIT | https://github.com/arogozhnikov/einops |
| Pillow | MIT-CMU | https://github.com/python-pillow/Pillow |
| playwright | Apache-2.0 | https://github.com/microsoft/playwright-python |
| openai (optional) | Apache-2.0 | https://github.com/openai/openai-python |

Full version pins are in `requirements.txt`. Each package's license file
is installed alongside the package in the project's virtual environment.

## Embedding model

`nomic-ai/nomic-embed-text-v1.5` — licensed under Apache-2.0.

- Model card: <https://huggingface.co/nomic-ai/nomic-embed-text-v1.5>
- Authors: Nomic AI

The installer downloads the model from HuggingFace Hub's official URL at
install time. **This project does not redistribute the model weights**;
the optional acceleration bundle on the project's CDN simply mirrors
HuggingFace's files for download-speed reasons, with the original Apache
2.0 license and attribution preserved inside the bundle.

## Headless browser

`chromium` — open-source browser project (BSD-style license; see
<https://chromium.googlesource.com/chromium/src/+/main/LICENSE>).

Downloaded by the `playwright` dependency from Microsoft's Playwright CDN
at install time. Used solely to render chart images for analysis output
(no browsing, no network requests other than loading our local HTML
template).

## Charting library

`lightweight-charts` — Apache 2.0 — <https://github.com/tradingview/lightweight-charts>

A small JavaScript chart library bundled into the chart-rendering HTML
template. Used in headless chromium to produce K-line image output.

## Knowledge base content

The 380 concept cards and 584 case cards under `knowledge_base/` are
**original structured summaries** authored by this project from analysis
of publicly available educational content (online ICT/SMC trading
tutorials). They do not contain verbatim copies of source material;
each card is a paraphrased, schema-structured representation of trading
concepts for research and educational purposes.

If you believe a card contains material that should be removed or
attributed differently, please open an issue.

## License of this project

Apache License 2.0 — see [LICENSE](./LICENSE).

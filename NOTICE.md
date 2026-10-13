# Notice

## What this project is not

This is independent research by one person. It is **not affiliated with, endorsed by, or sponsored by** Zapier, OpenRouter, MiniMax, Google, or TypeSafe (the maker of the Jev model). Product and model names are used only to say what was tested, and belong to their owners.

**Jev.** "Jev" is a decision model made by TypeSafe, called through OpenRouter's alpha decisions endpoint (model id `typesafe/jev-1.13`). It is used here as a third-party checker that answers yes/no questions about a text. The code and package names in this repo (`jev.py`, `jevloop`) refer to that model; they do not imply any relationship with its makers. Results about Jev describe this task, this data and this way of using it, and are not a general evaluation of the model.

## Code

MIT License, see [`LICENSE`](LICENSE).

## Data and benchmarks

| Source | Used for | Licence |
|---|---|---|
| [AutomationBench](https://github.com/zapier/AutomationBench) v1.0.6, © 2026 Zapier, Inc. | The v2 tasks, simulated business systems and grading | MIT |
| Chatbot Arena human preference data, [`lmarena-ai/arena-human-preference-55k`](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-55k) | v1 experiments 2 to 5 | Apache 2.0 |
| The Upworthy Research Archive: Matias, Munger, Aubin Le Quere and Ebersole (2021), *Scientific Data* 8:195, [doi:10.1038/s41597-021-00934-7](https://doi.org/10.1038/s41597-021-00934-7) | v1 experiments 1 and 6 | CC BY 4.0 (published by Cornell University) |

The raw datasets are **not** redistributed here: only split identifiers (pair and test ids), and the per-run outputs of the experiments, which are what the results are computed from.

## What is in the experiment packages

The compressed telemetry under `v1/experiments/*/telemetry/` contains the prompts and responses the models saw and produced. For the Arena experiments this includes real user prompts and model responses from the public dataset above, redistributed under its licence with attribution. The v2 raw run logs (full agent transcripts, about 200 MB) are not published; `v2/phase1/run/take2/sealed_runs.csv` is the per-run table the headline numbers are computed from.

## Models

Models were reached through OpenRouter and Google AI Studio. Model versions and served snapshots are recorded in each experiment's configuration files (`config*.yaml`). Model behaviour changes over time; these runs are a record of what those versions did in September and October 2026.

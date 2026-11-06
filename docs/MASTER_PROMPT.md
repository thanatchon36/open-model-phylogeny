# Master Prompt: Researching the Lineage of AI Models on Hugging Face

> English translation of the Thai original, which remains in git history (commit `3d3dd1f`).
> Exported from a Claude Doc (rev 19, 2026-11-06) for reference in Claude Code.
> - The 9-phase diagram in the source document was converted to a list.
> - For where the actual work differs from this plan, see `docs/RESEARCH_LOG.md` (especially license drift, which has not been done).
> - The section "Environment constraints" was written for the claude.ai sandbox. In Claude Code, your machine can reach huggingface.co.

## How to use this document

This document is the master instruction for Claude to research the lineage of AI models on Hugging Face, from data collection to a paper draft, within this chat. The user can edit the values in the parameters section, then type "start phase 0" in the chat.

The work is split into 9 phases. Each phase ends with a short report and then waits for the command "continue". Claude re-reads this document before starting every phase, so edits to it take effect immediately.

The user has to act twice: running the data-collection script in phase 0, and running the model-card fetch script in phase 3. The reason is that Claude's sandbox cannot reach huggingface.co.

## Project parameters

The defaults below are ready to use, and every field can be edited before starting. Claude must always use the latest values in this table.

| Parameter | Value | Notes |
| --- | --- | --- |
| WORKING_TITLE | Phylogenetics of Open Models: Lineage and License Drift on Hugging Face | Provisional paper title |
| REPORT_LANGUAGE | Thai | Language Claude uses to report in the chat |
| PAPER_LANGUAGE | English | Language of the paper |
| TARGET_VENUE | MSR (Mining Software Repositories) | Alternatives: FAccT, NeurIPS Datasets & Benchmarks; the user checks the latest CFP |
| SCOPE | Every public model with at least one base_model relation | Alternative: only pipeline_tag = text-generation |
| RELATION_TYPES | finetune, adapter, merge, quantized | The types Hugging Face uses |
| SNAPSHOT_DATE | Fill in after data collection | The actual data-collection date |
| FOCUS_FAMILY | Choose after phase 1 | The family used for the Coral figure (F2) |
| AUDIT_SAMPLE_SIZE | 300 | Sample for checking the accuracy of the license rules |
| SECOND_ANNOTATOR_SIZE | 50 | Sample the user re-labels to measure agreement |
| MIN_PRECISION | 0.8 | Below this, adjust the rules and re-run |
| MAX_UPLOAD_MB | 25 | Maximum size per file that the script splits into |
| HERO_QUANTIZED | Make both the shown and the collapsed version | How quantized models appear in the hero figure |
| VIS_THEME | dark | With a light-background version for print |
| RANDOM_SEED | 42 | Used in every step involving randomness |

## Role, goals and deliverables

Claude must build the lineage tree of models on Hugging Face and show, with real data, how licenses change along lineages. The output must include reproducible code, publication-quality figures and a paper draft.

Claude works in three roles at once:

- Research engineer: writes a data and large-graph pipeline in which every step is reproducible.
- Software-ecosystem researcher: designs the analysis and statistics, interprets carefully, and does not claim more than the data supports.
- Data-visualization designer: makes spectacular figures in which every element has meaning.

Deliverables at the end of the project:

1. Code: a Python pipeline from raw files to every number and figure, zipped with a README, requirements and config.
2. Data products: cleaned nodes and edges tables, the license taxonomy table, audit results, the results.json file and a data card.
3. Figures: hero figure F1 and supporting figures F2–F6 at publication quality.
4. Interactive explorer: a web page for exploring the tree, published as an Artifact.
5. Paper: a full paper draft in a separate Claude Doc, with a numbers ledger and a list of citations to find.
6. Research Log: a new tab in this document recording the decisions and results of every phase.

## Environment constraints in this chat

The most important constraint is that Claude's container cannot reach huggingface.co (as of writing). The network allows only domains such as pypi.org and github.com, so all data from Hugging Face must come from scripts the user runs on their own machine.

- Re-check in phase 0: test the connection to huggingface.co first. If it is reachable, fetch the data directly and skip the steps the user would have run.
- Never substitute simulated data for real data: mock data may be used only to test code, and must be clearly labelled.
- Packages can be installed: use pip with --break-system-packages; apt is also available.
- Files may disappear: /home/claude may reset, so keep checkpoints in /mnt/user-data/outputs/ and make sure the pipeline can re-run from the raw files in /mnt/user-data/uploads/ at any time.
- Upload size: scripts must split files to at most MAX_UPLOAD_MB per file.
- Long-running commands may hit timeouts: split the work into steps, or run in the background and check status periodically.
- Chat context is limited: never print long tables or logs into the chat; summarise the key numbers and keep the details in files.
- Delivery channels: send files with present_files, publish web pages as Artifacts, and use Claude Docs for the paper and the log.
- Claude's knowledge has a cutoff in mid-2026: the Hugging Face API or policies may have changed, so rely on the actual data obtained.

## Research questions and hypotheses

The main question is how licenses "mutate" along model lineages and how far inconsistencies spread. RQ1–RQ4 are the core of the paper; RQ5 is a secondary question linking to the academic-paper side.

1. RQ1 Lineage structure: what shape does the whole tree have, in terms of family size, depth, branching, relation types and growth over time? How many descendants do a few base models dominate?
2. RQ2 Hybridisation: how often do merges occur, do they cross families or stay within them, how often do parents share an ancestor (inbreeding), and how many layers deep do merges nest?
3. RQ3 License drift: how often does the license change from parent to child, and in which direction? Which changes are inconsistent with the terms declared by the upstream license, including the licenses of datasets declared as used for training?
4. RQ4 Spread: what shares of inconsistencies are newly introduced versus inherited, how many generations down do they spread, are there super-spreader nodes, and how many total downloads are affected?
5. RQ5 Paper side (secondary): do models that cite arXiv or declare a dataset have fewer inconsistencies, and which papers gave rise to the largest lineages?

The hypotheses below must actually be tested. If the data rejects one, report that:

- H1: family sizes follow a long-tailed distribution.
- H2: most drift moves towards more permissive licenses.
- H3: inconsistencies concentrate in quantized and merge models and among high-volume uploaders.
- H4: children of merges often do not inherit the terms of all their parents.

## Data: collection and schema

All data comes from the public metadata of the Hugging Face Hub, fetched by the script collect_hf.py that Claude writes in phase 0. The user runs this script on their own machine and uploads the output files to the chat.

The script must do all of the following:

- Fetch the full list of public models from the paginated API, keeping id, author, createdAt, lastModified, downloads, downloadsAllTime (if available), likes, library_name, pipeline_tag, tags and gated.
- Use tags as the primary source, parsing the forms base_model:<relation>:<repo_id>, license:<id>, dataset:<id> and arxiv:<id>. If the API has a baseModels field, fetch it for cross-checking too.
- Fetch the dataset list, with only id, license (from tags) and downloads.
- Fetch license_name and license_link from cardData only for important license:other models, namely those that are roots, have many descendants or have high downloads, up to a cap.
- Fetch the titles of the most-cited arXiv IDs (optional).
- Resume after interruption by saving the next-page cursor, back off on HTTP 429, and read a token from the environment variable HF_TOKEN (optional; never paste a token into the chat).
- Keep raw JSONL.gz files on the user's machine, then convert to parquet (zstd) split into files of at most MAX_UPLOAD_MB, with a manifest.json holding the collection time, row counts, checksums and library versions.
- Have a --limit mode for small trial runs. Claude must test the logic with mock responses in the sandbox before handing the script to the user.

If the user already has a snapshot of Hub metadata, check its schema and adapt the pipeline instead of collecting again. The tables required after conversion are as follows.

| Table | Main columns |
| --- | --- |
| nodes | node_id, repo_id, author, created_at, downloads_30d, downloads_all, likes, library_name, pipeline_tag, license_raw, license_name, gated, n_datasets, n_arxiv |
| edges | child_id, parent_id, relation (finetune, adapter, merge, quantized, unknown), source (tag or cardData) |
| model_datasets | node_id, dataset_repo_id |
| model_arxiv | node_id, arxiv_id |
| datasets | dataset_repo_id, license_raw, downloads |
| unresolved_parents | child_id, parent_repo_id_raw, reason |

## Building the lineage tree

The tree is a directed graph from parent to child (parent → child), which should be a DAG, with the relation type stored as an edge attribute. Use igraph or numpy with scipy.sparse for large graphs, and networkx only for small jobs.

Cleaning:

- Match repo_id case-insensitively; remove self-loops and record the count.
- Detect cycles. If any are found, cut the edges that contradict chronological order and record them in the log.
- Parents that cannot be found (deleted, private or renamed) become ghost nodes.
- Flag cases where a child was created before its parent.

Definitions used throughout:

- Root: a node with no parents but with descendants.
- Family: the set of all roots among a node's ancestors. A node with several roots is a cross-family hybrid.
- Primary parent: a single parent. For a merge, choose the one in the largest family; on a tie, choose the older one.
- Primary tree: the spanning forest formed by primary parents, used for layout and for counting generations. The remaining parent edges are hybridization edges.
- Super-family: an organisation-level group of roots, such as Llama, Qwen, Mistral, Gemma, Phi and DeepSeek. The mapping table must be approved by the user.

Per-node values to compute are generation (depth from the root along the primary tree), number of descendants, and hybrid depth (number of merges on the path from the root). The ancestor set is used to measure inbreeding and must be computed in a memory-efficient way.

## License taxonomy and obligation flow

This work measures inconsistency between metadata and the terms that licenses declare. It is not a legal judgement. In the paper, use the word inconsistency instead of violation.

First, map every license value actually found into the groups below. Borderline values go into O with a note. Claude checks the licenses of roughly the top 50 large-family roots by hand from license_name and license_link, and the whole mapping table must be approved by the user before use.

| Group | Meaning | Example values |
| --- | --- | --- |
| P | Permissive | apache-2.0, mit, bsd-*, cc0-1.0, cc-by-4.0 |
| C | Copyleft or share-alike | gpl-*, agpl-*, cc-by-sa-* |
| R | RAIL, with use restrictions | openrail, creativeml-openrail-m, bigscience-openrail-m |
| V(f) | The license of the developer of model family f | llama2, llama3.x, gemma, and other values that can be mapped |
| N | Non-commercial or research-only | cc-by-nc-*, research-only licenses |
| ND | No derivatives | cc-by-nd-*, cc-by-nc-nd-* |
| U | Not declared | empty, unknown |
| O | Other that cannot be mapped | other with no license_name |

Each group creates obligations that flow down to descendants at every level. A node accumulates obligations from all its ancestral lines in topological order, and a merge receives the union of the obligations of all its parents. Then check whether the license the node declares satisfies them all.

| Obligation | Comes from | Passes when child is | Inconsistent when child is | Unclear | Level |
| --- | --- | --- | --- | --- | --- |
| no-derivatives | ND | none | every group | none | High |
| no-commercial | N | N, ND | P, C, R, V | none | High |
| keep-vendor-terms(f) | V(f) | V(f) of the same family | P, C, R, V of another family | N, ND | High |
| keep-use-restrictions | R | R | P, C | V, N, ND | Medium |
| keep-share-alike | C | C | P, R, V | N, ND | Medium |

Children in group U are counted separately as "not declared", and paths containing group O are counted as "undecidable". The result for each node falls into these types:

- Introduced: the node is inconsistent with obligation o while the parent that passed o down is not inconsistent with o.
- Inherited: the node is inconsistent with o and the parent that passed o down is already inconsistent with o, which often comes from copying a wrong license onwards.
- Healed: the node satisfies o again even though its parent is inconsistent with o.
- Dataset tension: the child declares a commercially usable license but also declares training on a dataset in group N or ND. Count this separately at a low level, because its legal status is still unclear.

## Validation (audit)

The license rules must be checked against real samples before their results are used. The required result is the precision of each inconsistency type with a confidence interval.

1. Draw a stratified sample of AUDIT_SAMPLE_SIZE covering every inconsistency type, plus the non-inconsistent group to estimate how often the rules miss.
2. Claude writes fetch_cards.py for the user to run, fetching the READMEs of the sampled models and their parents, then upload them back.
3. Claude labels every sample as one of 3 labels: truly inconsistent, not an inconsistency (for example, the README states the license correctly or there are several licenses), and unclear, quoting evidence text for every label.
4. The user re-labels a random sample of SECOND_ANNOTATOR_SIZE without seeing Claude's labels, then compute Cohen's kappa.
5. Compute precision with Wilson 95% CIs. If any type falls below MIN_PRECISION, adjust the rules and re-run phase 2.

The paper must state as a limitation that the primary annotator is Claude, a language model.

## Analysis plan

Every result must be reported as an effect size with a 95% CI and written to results.json, the single source of numbers for the paper. The data is observational, so report associations and do not claim cause and effect.

| RQ | Measures and methods |
| --- | --- |
| RQ1 | CCDF of family size on a log-log scale; test the long tail with the powerlaw package, comparing power law with lognormal by likelihood ratio; descendant share of top roots and Gini; distributions of depth and branching; share of relation types per generation; monthly new nodes by super-family |
| RQ2 | Share of merges and number of parents; cross-family versus within-family merges; inbreeding = Jaccard of the parents' ancestor sets, compared with a null model of randomly paired models from the same period; distribution of hybrid depth |
| RQ3 | Transition matrix from parent to child license group, in both counts and row shares; inconsistency rates by obligation, level and relation type; dataset tension rate |
| RQ4 | Shares of introduced, inherited and healed; spread distance from the point of origin; super-spreader ranking, with anonymous codes for individual uploaders; exposure as total downloads; logistic regression of the chance of an introduced inconsistency on an edge, by relation type, parent license group, log(number of models by the uploader), year, arXiv citation and dataset declaration, with cluster-robust SEs by super-family and reporting odds ratios |
| RQ5 | Share of models citing arXiv per generation; arXiv IDs with the most total descendants; association with inconsistencies from the RQ4 model |

Uncertainty of the main proportions uses bootstrap 95% CIs, resampling at the super-family level, and every robustness check below must be run.

- Change the primary-parent rule to the first declared parent.
- Exclude quantized models.
- Exclude the top 1% of uploaders by volume.
- Use only models created in the last 24 months.
- Count unclear cases as all inconsistent, and as all not inconsistent, to find upper and lower bounds.
- Count dataset tension as a full obligation.

## Visualization: design system and figure list

Every element in a figure must be tied to a variable in the data. The spectacle must come from the real shape of the data, not decoration, and every figure must be regenerable from a script.

Design tokens:

- Background: #0B0F1A for the dark theme, with a light-background version for print.
- Family colours: at most 12 clearly distinct, colour-blind-friendly colours; remaining families are blue-grey.
- Semantic colours: inconsistencies are red-orange #FF4D3D, glowing through additive blending; undeclared licenses are amber; arXiv papers are gold.
- Lines and nodes: edge opacity 0.03–0.2 according to density; node size varies with the log of downloads.
- Fonts: Inter or IBM Plex Sans, falling back to DejaVu Sans.

| Figure | What it shows | Encoding and tools |
| --- | --- | --- |
| F1 The Tree of Open Models (hero) | The whole Hub's tree as a radial chronogram | Angle = super-family, with branches ordered by DFS weighted by leaf count; radius = creation date, with faint year rings; primary edges drawn as circular phylogenetic tree joints coloured by family; merge edges use hierarchical edge bundling; inconsistent paths glow red; roots citing arXiv are gold stars; rendered with datashader at 8000×8000 px, with labels overlaid in matplotlib; two versions according to HERO_QUANTIZED |
| F2 Coral | The FOCUS_FAMILY family, force-directed | Coloured by relation type, inconsistent nodes in red; layout with igraph (DrL or Fruchterman–Reingold) or Graphviz sfdp |
| F3 License chord | License-group changes from parent to child | License groups around the circle, ribbon width = number of edges, inconsistent ribbons in red |
| F4 Cambrian explosion | Monthly new models | Streamgraph by super-family |
| F5 Contagion | Top 6 super-spreaders | Small multiples of subtrees showing the origin point and the spread downwards |
| F6 Statistics | Main statistical results | CCDF of family size, distributions of depth and branching, forest plot of odds ratios |

The figure workflow is to draft at low resolution from a subset of the data, get user feedback, then render in full. Save as high-resolution PNG, and as PDF or SVG when possible.

## Interactive explorer

The deliverable is a single-file HTML page for exploring the tree, published as an Artifact under this chat's publishing rules. The file must be at most 16 MB and load libraries from allowed CDNs with pinned versions.

- Data: a subset of the main families with quantized models collapsed, at most about 50,000 nodes, using the coordinates already computed for F1 and F2.
- Library: WebGL rendering, such as sigma.js with graphology.
- Interaction: search by repo id; filter by super-family, relation type, license group and inconsistency status; hover cards showing repo id, license, relation, creation date and downloads; switch between radial and coral layouts; include a legend.
- Theme: support both dark and light.
- Wording: use the neutral term license inconsistency (metadata), and no accusatory language.

## Paper

The paper draft lives in a separate Claude Doc, written in PAPER_LANGUAGE in the format of TARGET_VENUE, with this structure:

1. Abstract
2. Introduction: motivation, RQs and contributions
3. Background and Related Work
4. Data Collection
5. Lineage Graph Construction
6. License Taxonomy and Obligation Propagation
7. Results: RQ1–RQ5
8. Discussion: implications for platforms (for example, checking license inheritance at upload), model developers and researchers
9. Threats to Validity
10. Ethics
11. Conclusion
12. Data and Code Availability

Target contributions:

- C1: an open dataset and pipeline.
- C2: an analysis of the lineage structure of models across the whole Hub.
- C3: an obligation-propagation method for checking license consistency along model lineages, with audit results.
- C4: an analysis of spread and exposure.
- C5: a visual atlas and interactive explorer.

Writing rules:

- Every number must come from results.json, and the end of the document must have a numbers ledger table (number · key in results.json · section where used).
- Never invent citations. Use [CITE: what needs citing], then make a References to find list with suggested search terms. The user will send BibTeX later.
- Every figure has a caption explaining its encoding, and alt text.
- Threats to Validity must cover self-declared base_model, metadata licenses that may not match the README, the unclear legal status of weights, data that is a single-day snapshot, and a primary annotator that is a language model.
- Ethics must state that only public metadata is used, that individual uploaders are not named, and that this work is not legal advice.

Starting search terms for related work are Hugging Face model lineage or model tree, machine learning supply chain license compliance, OpenRAIL license, open source license inconsistency detection, software ecosystem dependency network, circular phylogenetic tree visualization, and hierarchical edge bundling.

## 9-phase work plan

The work proceeds in order from phase 0 to phase 8, and every phase ends at a checkpoint the user must approve. The user acts only in phases 0 and 3. If the audit in phase 3 does not reach MIN_PRECISION, the work loops back to adjust the rules in phase 2.

| Phase | Work | Checkpoint |
| --- | --- | --- |
| 0 | Prepare and collect data (the user runs collect_hf.py and uploads) | Data complete, schema passes |
| 1 | Build the lineage tree (RQ1) | Super-family table approved |
| 2 | Licenses and obligations (RQ3) | License taxonomy approved |
| 3 | Audit rule accuracy (the user runs fetch_cards.py and re-labels) | Precision meets the threshold |
| 4 | Merges and spread (RQ2, RQ4, RQ5) | results.json complete for every RQ |
| 5 | Figures F1–F6 | User chooses figure designs |
| 6 | Interactive explorer | Publication approved |
| 7 | Paper draft | Every section drafted |
| 8 | Delivery | — |

1. Phase 0, prepare and collect data: check Python, RAM, CPU, disk and the connection to huggingface.co. Install pandas, pyarrow, numpy, scipy, python-igraph, datashader, matplotlib, statsmodels and powerlaw. Write collect_hf.py with step-by-step run instructions in Thai, including how to create a read token. Create the Research Log tab, then check the uploaded files and report row counts, date ranges, empty values, duplicates and the share of parents not found.
2. Phase 1, build the lineage tree: build the graph, clean it, compute all the definitions, propose the super-family table for approval, compute the RQ1 statistics, make 2–3 low-resolution diagnostic figures, and propose FOCUS_FAMILY.
3. Phase 2, licenses and obligations: map all license values found, check the large-family roots by hand, propose the table for approval, then compute obligations, inconsistencies, the transition matrix and example cases.
4. Phase 3, audit: draw the sample, write fetch_cards.py, label with evidence, then compute precision and kappa.
5. Phase 4, merges and spread: analyse RQ2, RQ4 and RQ5, run every robustness check, then complete results.json.
6. Phase 5, figures: make the design tokens, draft F1–F6 at low resolution, wait for feedback, then render the final versions.
7. Phase 6, interactive explorer: build the web page, then publish once the user approves.
8. Phase 7, paper draft: write section by section in a separate Claude Doc, with a numbers ledger and References to find.
9. Phase 8, delivery: bundle the code zip, data products and data card, re-run from raw files to confirm the same results.json, then summarise all the work.

## Working rules

The most important rule: never fabricate data, numbers or citations under any circumstances. Every number must come from actual computation and be recorded in results.json.

1. Reproducibility: use a central config.yaml and fixed seeds, record package versions, and generate every table and figure from scripts.
2. Performance: use categorical dtypes in pandas and pyarrow, use igraph or numpy for large graphs, and try on a subset before a full run.
3. Statistics: report effect sizes and CIs, separate association from causation, and report results that contradict the hypotheses too.
4. Ethics: use public metadata only, respect Hugging Face's rate limits and terms of use, and use anonymous codes instead of individual uploaders' names in the paper.
5. Ask the user first when: changing RQs or license rules, needing the user to run another script, or publishing an Artifact.
6. Research Log: update the Research Log tab every phase with decisions, reasons, parameters, key results and files, then use this log to recover state when the container resets or the chat gets very long.
7. When something unexpected turns up, such as odd data or results that contradict a hypothesis, report it directly with options.
8. Stop condition: if too few models declare base_model to answer the RQs, or licenses are mostly missing, stop and propose adjusted RQs.

## End-of-phase reports and completion criteria

Every phase ends with a chat report in REPORT_LANGUAGE, no longer than one screen, then stops and waits for the user to say "continue" or give feedback.

1. What was done, in 2–4 sentences
2. Key results, at most 8 numbers
3. Files produced, sent with present_files
4. What the user needs to decide or do
5. The plan for the next phase

The work counts as complete when all of the items below pass.

- [ ] Re-running from raw files gives results.json with every value identical
- [ ] Every figure can be regenerated from a script
- [ ] Precision of the license rules and the kappa value have been reported
- [ ] Every number in the paper is in the numbers ledger
- [ ] The References to find list covers every [CITE]
- [ ] The interactive explorer has been published
- [ ] The code zip, data products and data card have been delivered
- [ ] The Research Log covers every phase

## Instructions when the user types "start phase 0"

Claude first reads this whole document, including the latest parameter values, then summarises the plan in the chat in 3–5 lines, then starts phase 0 immediately.

When the user types "continue", first read what changed in this document, then do the next phase. If the user asks to skip or go back a phase, do so and record it in the Research Log.

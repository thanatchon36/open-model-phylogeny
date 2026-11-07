#!/usr/bin/env python3
"""Phase 7 helper: every number in the paper comes from results.json through these macros.
Writes paper/macros.tex, paper/ledger.tex, paper/tab_*.tex and paper/figs/*.jpg."""
import json
from pathlib import Path

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "results/results.json").read_text())
PAPER = ROOT / "paper"
(PAPER / "figs").mkdir(parents=True, exist_ok=True)


def I(x): return f"{int(round(x)):,}".replace(",", "{,}")
def P1(x): return f"{100 * x:.1f}\\%"
def F1(x): return f"{x:.1f}"
def F2(x): return f"{x:.2f}"
def F3(x): return f"{x:.3f}"
def PV(x): return "<0.001" if x < 0.001 else f"{x:.3f}"
def S(x): return str(x)
def BN(x): return f"{x / 1e9:.1f}~billion"
def MON(x): return pd.Timestamp(x + "-01").strftime("%B %Y")


def get(path):
    v = R
    for k in path:
        v = v[k]
    return v


H = ("rq3", "reaction_median_days_by_half")
SPEC = [
    ("nModelsHub", ("overview", "n_models_hub"), I), ("nConnected", ("overview", "n_connected"), I),
    ("pctConnected", ("overview", "share_connected"), P1), ("nChildren", ("overview", "n_children"), I),
    ("pctDeclare", ("overview", "share_declare_parent"), P1), ("nEdges", ("overview", "n_edges"), I),
    ("nRoots", ("overview", "n_roots"), I), ("nGhost", ("overview", "n_ghost"), I),
    ("nFamilies", ("overview", "n_families"), I), ("nAuthors", ("overview", "n_authors_connected"), I),
    ("nFinetune", ("overview", "children_by_relation", "finetune"), I),
    ("nAdapter", ("overview", "children_by_relation", "adapter"), I),
    ("nQuantized", ("overview", "children_by_relation", "quantized"), I),
    ("nMergeKids", ("overview", "children_by_relation", "merge"), I),
    ("pctFinetune", ("overview", "share_children_by_relation", "finetune"), P1),
    ("pctAdapter", ("overview", "share_children_by_relation", "adapter"), P1),
    ("pctQuantized", ("overview", "share_children_by_relation", "quantized"), P1),
    ("pctMerge", ("overview", "share_children_by_relation", "merge"), P1),
    ("nMergeEdges", ("overview", "edges_by_relation", "merge"), I),
    ("nRawEdges", ("build", "n_edges_raw"), I), ("nDupRows", ("build", "duplicate_node_rows_dropped"), I),
    ("nRescued", ("build", "parents_rescued_case_insensitive"), I), ("nCycleNodes", ("build", "cycle_nodes_initial"), I),
    ("nCycleEdges", ("build", "cycle_edges_removed"), I), ("backfillDate", ("build", "backfill_date"), S),
    ("nBackfill", ("build", "backfill_date_n"), I), ("nPrimaryChanged", ("build", "primary_changed_vs_first_listed"), I),
    ("familyMedian", ("rq1", "root_family_size_median"), I), ("familyMean", ("rq1", "root_family_size_mean"), F1),
    ("familyMax", ("rq1", "root_family_size_max"), I), ("pctRootsSmall", ("rq1", "share_roots_size_le_3"), P1),
    ("pctTopTenRoots", ("rq1", "top10_roots_share_of_connected"), P1), ("nTopOnePctRoots", ("rq1", "top1pct_roots_n"), I),
    ("pctTopOnePctRoots", ("rq1", "top1pct_roots_share_of_connected"), P1), ("giniFamily", ("rq1", "gini_root_family_size"), F2),
    ("pctTopTenKeys", ("rq1", "top10_family_keys_share"), P1), ("nQwenTwoFive", ("rq1", "top10_family_keys", "qwen2.5"), I),
    ("plAlpha", ("rq1", "powerlaw_alpha"), F2), ("plXmin", ("rq1", "powerlaw_xmin"), I), ("plNtail", ("rq1", "powerlaw_n_tail"), I),
    ("plLnR", ("rq1", "pl_vs_lognormal_R"), F2), ("plLnP", ("rq1", "pl_vs_lognormal_p"), F2),
    ("plExR", ("rq1", "pl_vs_exponential_R"), F1), ("plExP", ("rq1", "pl_vs_exponential_p"), PV),
    ("pctDepthOne", ("rq1", "depth_share_1"), P1), ("pctDepthThree", ("rq1", "depth_share_ge3"), P1),
    ("depthPnn", ("rq1", "depth_p99"), I), ("depthMax", ("rq1", "depth_max"), I), ("ldepthMax", ("rq1", "ldepth_max"), I),
    ("outdegMedian", ("rq1", "outdeg_median"), I), ("outdegPnn", ("rq1", "outdeg_p99"), I), ("outdegMax", ("rq1", "outdeg_max"), I),
    ("pctLeaves", ("rq1", "share_children_leaves"), P1),
    ("pctLeafFinetune", ("rq1", "leaf_share_by_relation", "finetune"), P1),
    ("pctLeafAdapter", ("rq1", "leaf_share_by_relation", "adapter"), P1),
    ("pctLeafQuantized", ("rq1", "leaf_share_by_relation", "quantized"), P1),
    ("pctLeafMerge", ("rq1", "leaf_share_by_relation", "merge"), P1),
    ("nUnderGhost", ("rq1", "nodes_under_ghost_roots"), I), ("pctUnderGhost", ("rq1", "share_nodes_under_ghost_roots"), P1),
    ("nQwenSuper", ("rq1", "super_family_sizes", "Qwen"), I),
    ("nHybrids", ("rq2", "n_hybrids"), I), ("nMergeLabelled", ("rq2", "n_merge_labelled"), I),
    ("pctMergeMulti", ("rq2", "share_merge_labelled_multi_parent"), P1), ("nTwoParents", ("rq2", "parents_per_hybrid", "2"), I),
    ("maxParents", ("rq2", "parents_per_hybrid_max"), I), ("nPairs", ("rq2", "n_parent_pairs"), I),
    ("pctBackcross", ("rq2", "kinship_share", "backcross"), P1), ("pctSibling", ("rq2", "kinship_share", "sibling"), P1),
    ("pctCousin", ("rq2", "kinship_share", "cousin"), P1), ("pctOutcross", ("rq2", "kinship_share", "outcross"), P1),
    ("pctRelated", ("rq2", "related_share"), P1), ("pctCrossFamily", ("rq2", "cross_family_pair_share"), P1),
    ("pctCrossSuper", ("rq2", "cross_super_family_pair_share"), P1), ("pctNullRelated", ("rq2", "null_related_share_mean"), P1),
    ("pctNullCross", ("rq2", "null_cross_family_share_mean"), P1), ("assortRatio", ("rq2", "assortativity_ratio_related"), F1),
    ("permP", ("rq2", "perm_p_related"), F2), ("hybDepthMax", ("rq2", "hybrid_depth_max"), I),
    ("nDeepHybrid", ("rq2", "n_nodes_hybrid_depth_ge10"), I), ("nDeepAuthors", ("rq2", "authors_hybrid_depth_ge10"), I),
    ("pctDeepTopAuthor", ("rq2", "top_author_share_hybrid_depth_ge10"), P1),
    ("pctDeepTopAuthorQuant", ("rq2", "top_author_quantized_share_hybrid_depth_ge10"), P1),
    ("nDeepMulti", ("rq2", "n_multi_parent_hybrid_depth_ge10"), I),
    ("nDeepMultiAuthors", ("rq2", "authors_multi_parent_hybrid_depth_ge10"), I),
    ("pctDeepMultiTopAuthor", ("rq2", "top_author_share_multi_parent_hybrid_depth_ge10"), P1), ("ancMax", ("rq2", "anc_size_max"), I),
    ("outcrossLo", ("rq2", "outcross_ci", 0), P1), ("outcrossHi", ("rq2", "outcross_ci", 1), P1),
    ("nLagEdges", ("rq3", "edges_valid_for_lag"), I), ("pctNegLag", ("rq3", "share_negative_lag"), P1),
    ("lagFinetune", ("rq3", "lag_finetune", "median_days"), F1), ("lagAdapter", ("rq3", "lag_adapter", "median_days"), F1),
    ("lagQuantized", ("rq3", "lag_quantized", "median_days"), F1), ("lagMerge", ("rq3", "lag_merge", "median_days"), F1),
    ("pctQuantDay", ("rq3", "lag_quantized", "share_within_1d"), P1), ("pctQuantWeek", ("rq3", "lag_quantized", "share_within_7d"), P1),
    ("pctQuantMonth", ("rq3", "lag_quantized", "share_within_30d"), P1), ("pctFinetuneWeek", ("rq3", "lag_finetune", "share_within_7d"), P1),
    ("pctMergeMonth", ("rq3", "lag_merge", "share_within_30d"), P1), ("nMajorBases", ("rq3", "n_major_bases"), I),
    ("rtFinetuneEarly", H + ("2023H2", "finetune"), F1), ("rtFinetuneLate", H + ("2026H1", "finetune"), F1),
    ("rtQuantEarly", H + ("2023H2", "quantized"), F1), ("rtQuantLate", H + ("2026H1", "quantized"), F1),
    ("rtAdapterEarly", H + ("2023H2", "adapter"), F1), ("rtAdapterLate", H + ("2026H1", "adapter"), F1),
    ("rtQuantAll", ("rq3", "reaction_trend_quantized", "median_days"), F1),
    ("rtFinetuneAll", ("rq3", "reaction_trend_finetune", "median_days"), F1),
    ("rtAdapterAll", ("rq3", "reaction_trend_adapter", "median_days"), F1),
    ("rtMergeAll", ("rq3", "reaction_trend_merge", "median_days"), F1),
    ("rhoFinetuneAll", ("rq3", "reaction_trend_finetune", "spearman_rho"), F2),
    ("rhoQuantAll", ("rq3", "reaction_trend_quantized", "spearman_rho"), F2),
    ("rhoFinetune", ("rq3", "reaction_trend_finetune_since2024", "spearman_rho"), F2),
    ("nRhoFinetune", ("rq3", "reaction_trend_finetune_since2024", "n"), I),
    ("rhoQuant", ("rq3", "reaction_trend_quantized_since2024", "spearman_rho"), F2),
    ("nRhoQuant", ("rq3", "reaction_trend_quantized_since2024", "n"), I),
    ("rhoAdapter", ("rq3", "reaction_trend_adapter_since2024", "spearman_rho"), F2),
    ("rhoMerge", ("rq3", "reaction_trend_merge_since2024", "spearman_rho"), F2),
    ("pRhoMerge", ("rq3", "reaction_trend_merge_since2024", "p"), F2),
    ("nDecayBases", ("rq3", "n_bases_decay"), I), ("pctFirstMonth", ("rq3", "decay_share_first30d_median"), P1),
    ("halfLife", ("rq3", "decay_halflife_days_median"), F1), ("birthsPeakMonth", ("rq3", "births_peak_month"), MON),
    ("birthsPeakCount", ("rq3", "births_peak_count"), I), ("birthsTwentyThree", ("rq3", "births_by_year", "2023"), I),
    ("birthsTwentyFour", ("rq3", "births_by_year", "2024"), I), ("birthsTwentyFive", ("rq3", "births_by_year", "2025"), I),
    ("birthsTwentySix", ("rq3", "births_by_year", "2026"), I), ("nUploaders", ("rq3", "n_uploaders_children"), I),
    ("pctTopTenUploaders", ("rq3", "share_children_top10_uploaders"), P1),
    ("pctTopHundredUploaders", ("rq3", "share_children_top100_uploaders"), P1),
    ("giniUploaders", ("rq3", "gini_children_per_uploader"), F2), ("pctPeakTopUploader", ("rq3", "peak_month_top_uploader_share"), P1),
    ("peakSuper", ("rq3", "peak_month_top_super"), S),
    ("nTopUploaders", ("robustness", "top1pct_uploaders_n"), I), ("pctTopUploaders", ("robustness", "top1pct_uploaders_share_children"), P1),
    ("pctZeroAll", ("rq4", "share_children_zero_downloads_all"), P1), ("pctDormant", ("rq4", "share_children_dormant_30d"), P1),
    ("dormantLo", ("rq4", "dormant_ci", 0), P1), ("dormantHi", ("rq4", "dormant_ci", 1), P1),
    ("pctDormantFinetune", ("rq4", "dormant_by_relation", "finetune"), P1),
    ("pctDormantAdapter", ("rq4", "dormant_by_relation", "adapter"), P1),
    ("pctDormantQuantized", ("rq4", "dormant_by_relation", "quantized"), P1),
    ("pctDormantMerge", ("rq4", "dormant_by_relation", "merge"), P1),
    ("dlFinetune", ("rq4", "median_downloads_all_by_relation", "finetune"), I),
    ("dlAdapter", ("rq4", "median_downloads_all_by_relation", "adapter"), I),
    ("dlQuantized", ("rq4", "median_downloads_all_by_relation", "quantized"), I),
    ("dlMerge", ("rq4", "median_downloads_all_by_relation", "merge"), I),
    ("totalChildDownloads", ("rq4", "children_downloads_all_total"), BN),
    ("pctTopDownloads", ("rq4", "share_child_downloads_top1pct"), P1), ("giniDownloads", ("rq4", "gini_child_downloads_all"), F3),
    ("nBigFamilies", ("rq4", "n_big_families"), I), ("pctDescShare", ("rq4", "family_download_share_descendants_median"), P1),
    ("pctOutgrow", ("rq4", "share_families_child_outgrows_root"), P1),
    ("rhoKids", ("rq4", "spearman_children_vs_downloads", "rho"), F2), ("nRhoKids", ("rq4", "spearman_children_vs_downloads", "n"), I),
    ("nBasesHundred", ("rq4", "n_bases_ge100"), I), ("pctAdapterDominated", ("rq4", "share_bases_adapter_dominated"), P1),
    ("nLogit", ("rq4", "logit_n"), I), ("pseudoRsq", ("rq4", "logit_pseudo_r2"), F3),
    ("nTaskEdges", ("rq5", "edges_with_both_tasks"), I), ("pctSpeciation", ("rq5", "speciation_rate"), P1),
    ("specLo", ("rq5", "speciation_ci", 0), P1), ("specHi", ("rq5", "speciation_ci", 1), P1),
    ("pctSpecFinetune", ("rq5", "speciation_by_relation", "finetune"), P1),
    ("pctSpecAdapter", ("rq5", "speciation_by_relation", "adapter"), P1),
    ("pctSpecQuantized", ("rq5", "speciation_by_relation", "quantized"), P1),
    ("pctSpecMerge", ("rq5", "speciation_by_relation", "merge"), P1),
    ("pctPipelineChange", ("rq5", "pipeline_change_rate"), P1),
    ("nFillMaskClass", ("rq5", "top_pipeline_transitions", 0, "n"), I), ("pctTopTransition", ("rq5", "top_transition_share_of_changes"), P1),
    ("nVlmText", ("rq5", "top_pipeline_transitions", 1, "n"), I), ("nFillMaskToken", ("rq5", "top_pipeline_transitions", 2, "n"), I),
    ("pctSpecFillMask", ("rq5", "speciation_by_source_task", "Fill-mask", "rate"), P1),
    ("pctSpecEmbed", ("rq5", "speciation_by_source_task", "Embeddings & ranking", "rate"), P1),
    ("pctSpecTextGen", ("rq5", "speciation_by_source_task", "Text generation", "rate"), P1),
    ("pctSpecImageGen", ("rq5", "speciation_by_source_task", "Image & video generation", "rate"), P1),
    ("nQuantLib", ("rq5", "quantized_edges_with_library"), I), ("pctLibChange", ("rq5", "quantized_library_change_rate"), P1),
    ("nToMlx", ("rq5", "top_quantized_library_transitions", 0, "n"), I),
    ("nToGguf", ("rq5", "top_quantized_library_transitions", 1, "n"), I),
]
for k, lab in [("rel_quantized", "orQuant"), ("rel_adapter", "orAdapter"), ("rel_merge", "orMerge"), ("gen2", "orGenTwo"),
               ("gen3p", "orGenThree"), ("hybrid", "orHybrid"), ("log_author", "orAuthor"), ("log_age", "orAge")]:
    SPEC += [(lab, ("rq4", "logit_or", k, "or"), F2), (lab + "Lo", ("rq4", "logit_or", k, "lo"), F2),
             (lab + "Hi", ("rq4", "logit_or", k, "hi"), F2)]

# guards: the prose names these transitions explicitly
tp = R["rq5"]["top_pipeline_transitions"]
assert (tp[0]["src"], tp[0]["dst"]) == ("fill-mask", "text-classification")
assert (tp[1]["src"], tp[1]["dst"]) == ("image-text-to-text", "text-generation")
assert (tp[2]["src"], tp[2]["dst"]) == ("fill-mask", "token-classification")
tl = R["rq5"]["top_quantized_library_transitions"]
assert (tl[0]["dst"], tl[1]["dst"]) == ("mlx", "gguf")

macros, ledger = [], []
derived = [("pctQwenSuper", "rq1.super_family_sizes.Qwen / overview.n_connected",
            P1(R["rq1"]["super_family_sizes"]["Qwen"] / R["overview"]["n_connected"])),
           ("pctOtherSuper", "rq1.super_family_sizes.Other / overview.n_connected",
            P1(R["rq1"]["super_family_sizes"]["Other"] / R["overview"]["n_connected"])),
           ("pctTwoParents", "rq2.parents_per_hybrid.2 / rq2.n_hybrids",
            P1(R["rq2"]["parents_per_hybrid"]["2"] / R["rq2"]["n_hybrids"]))]
for name, path, fmt in SPEC:
    val = fmt(get(path))
    macros.append(f"\\newcommand{{\\{name}}}{{{val}\\xspace}}")
    ledger.append((name, val, ".".join(str(p) for p in path)))
for name, src, val in derived:
    macros.append(f"\\newcommand{{\\{name}}}{{{val}\\xspace}}")
    ledger.append((name, val, src))
(PAPER / "macros.tex").write_text("% generated by src/make_macros.py from results/results.json\n" + "\n".join(macros) + "\n")


def esc(s):
    return s.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")


rows = [f"\\texttt{{\\textbackslash {n}}} & {v} & \\texttt{{{esc(s)}}} \\\\" for n, v, s in ledger]
head = ["\\begin{longtable}{>{\\raggedright\\arraybackslash}p{0.24\\textwidth} >{\\raggedleft\\arraybackslash}p{0.15\\textwidth} p{0.50\\textwidth}}",
        "\\toprule", "Macro & Value & Source key in \\texttt{results.json} \\\\", "\\midrule", "\\endhead"]
(PAPER / "ledger.tex").write_text("\n".join(head + rows + ["\\bottomrule", "\\end{longtable}"]) + "\n")

# ---- tables generated from results.json
g = R["rq1"]["relation_by_generation"]
lines = ["\\begin{tabular}{lrrrrr}", "\\toprule", "Generation & Models & Fine-tune & Adapter & Quantised & Merge \\\\", "\\midrule"]
for k in ["1", "2", "3", "4+"]:
    d = g[k]
    lines.append(f"{k} & {I(d['n'])} & {P1(d.get('finetune', 0))} & {P1(d.get('adapter', 0))} & {P1(d.get('quantized', 0))} & {P1(d.get('merge', 0))} \\\\")
lines += ["\\bottomrule", "\\end{tabular}"]
(PAPER / "tab_generation.tex").write_text("\n".join(lines) + "\n")

rt = R["rq3"]["reaction_median_days_by_half"]
lines = ["\\begin{tabular}{lrrrrr}", "\\toprule", "Cohort & Bases & Fine-tune & Quantised & Adapter & Merge \\\\", "\\midrule"]
for h in sorted(rt):
    d = rt[h]
    f = lambda x: "--" if x is None else F1(x)
    lines.append(f"{h} & {I(d['n'])} & {f(d.get('finetune'))} & {f(d.get('quantized'))} & {f(d.get('adapter'))} & {f(d.get('merge'))} \\\\")
lines += ["\\bottomrule", "\\end{tabular}"]
(PAPER / "tab_reaction.tex").write_text("\n".join(lines) + "\n")

rb = R["robustness"]
names = [("main", "Main specification"), ("first_listed_primary", "First-listed primary parent"), ("no_quantized", "Without quantised models"),
         ("no_top1pct_uploaders", "Without top 1\\% uploaders"), ("last_24_months", "Last 24 months only")]
lines = ["\\begin{tabular}{lrrrrr}", "\\toprule", "Specification & Gini & Top-10 & Speciation & Lag (d) & Dormant \\\\", "\\midrule"]
for k, lab in names:
    d = rb[k]
    lines.append(f"{lab} & {F2(d['gini_family_size'])} & {P1(d['top10_share'])} & {P1(d['speciation_rate'])} & {F1(d['median_lag_finetune'])} & {P1(d['dormant_share'])} \\\\")
lines += ["\\bottomrule", "\\end{tabular}"]
(PAPER / "tab_robustness.tex").write_text("\n".join(lines) + "\n")

# ---- figures for the paper (JPEG keeps the PDF light)
FIG = ROOT / "figures"
for src, dst, w in [("F1_tree_of_open_models_5000.png", "f1.jpg", 2600), ("F2_coral_qwen25.png", "f2.jpg", 1800),
                    ("F3_speciation_chord.png", "f3.jpg", 1800), ("F4_cambrian_streamgraph.png", "f4.jpg", 2400),
                    ("F5_hybridisation_web.png", "f5.jpg", 2400), ("F6_statistics.png", "f6.jpg", 2600)]:
    if not (FIG / src).exists():
        continue
    im = Image.open(FIG / src).convert("RGB")
    im.thumbnail((w, w * 2))
    im.save(PAPER / "figs" / dst, quality=91, optimize=True)
print(len(SPEC) + len(derived), "macros written")

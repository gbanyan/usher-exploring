"""Prototype: a cilia-signal gate on the HIGH confidence tier.

The HIGH tier is a higher-priority computational shortlist. Gating it on direct cilia-specific
evidence keeps generically well-studied genes (housekeeping controls) out of
the shortlist without changing any composite score or percentile ranking.

This evaluates several principled gate definitions and reports, for each:
  * HIGH-tier size,
  * how many of the 9 established Usher genes are retained in HIGH,
  * how many of the 13 housekeeping negative controls remain in HIGH.

Note: a tier gate relabels genes; it does NOT change the composite ranking,
so the housekeeping median percentile is unaffected by design.

Run:  .venv312/bin/python scripts/tier_gate.py
"""

import duckdb
import numpy as np

OMIM_USHER = ["ADGRV1", "CDH23", "CLRN1", "MYO7A",
              "PCDH15", "USH1C", "USH1G", "USH2A", "WHRN"]
SYSCILIA = ["ARL13B", "BBS1", "BBS2", "BBS4", "BBS5", "BBS7", "BBS9", "BBS10",
            "CC2D2A", "CEP164", "CEP290", "IFT88", "IFT140", "IFT172", "INPP5E",
            "MKS1", "NPHP1", "NPHP3", "NPHP4", "OFD1", "RPGR", "RPGRIP1L",
            "TCTN1", "TCTN2", "TMEM67", "TMEM138", "TMEM216", "TMEM231"]
KNOWN = OMIM_USHER + SYSCILIA
HOUSEKEEPING = ["GAPDH", "ACTB", "B2M", "UBC", "PPIA", "YWHAZ", "HPRT1",
                "TBP", "SDHA", "PGK1", "RPLP0", "RPL13A", "RPL32"]


def main():
    con = duckdb.connect("data/pipeline.duckdb", read_only=True)
    rows = con.execute(
        "select gene_symbol, composite_score, evidence_count, "
        "localization_score, animal_model_score from scored_genes"
    ).fetchall()
    con.close()

    genes, comp, evc, loc, animal = [], [], [], [], []
    for g, c, e, l, a in rows:
        genes.append(g)
        comp.append(np.nan if c is None else c)
        evc.append(e)
        loc.append(0.0 if l is None else l)        # NULL localization -> 0 signal
        animal.append(0.0 if a is None else a)
    comp = np.array(comp); evc = np.array(evc)
    loc = np.array(loc); animal = np.array(animal)

    # current HIGH tier: composite >= 0.7 and evidence >= 3
    is_high = (comp >= 0.7) & (evc >= 3)
    gidx = {g: i for i, g in enumerate(genes)}
    omim = [gidx[g] for g in OMIM_USHER if g in gidx]
    hk = [gidx[g] for g in HOUSEKEEPING if g in gidx]

    # animal-model layer quantiles over genes with any sensory signal
    a_pos = animal[animal > 0]
    q75, q90 = np.percentile(a_pos, [75, 90])
    print(f"HIGH tier (current rule): {int(is_high.sum())} genes")
    print(f"animal-model score among genes with signal: "
          f"Q75={q75:.2f}, Q90={q90:.2f}\n")

    gates = {
        "G0 none (current)":            np.ones(len(genes), bool),
        "G1 loc>0 OR animal>0":         (loc > 0) | (animal > 0),
        f"G2 loc>0 OR animal>=Q75({q75:.2f})": (loc > 0) | (animal >= q75),
        f"G3 loc>0 OR animal>=Q90({q90:.2f})": (loc > 0) | (animal >= q90),
        "G4 loc>0 OR animal>=0.30":     (loc > 0) | (animal >= 0.30),
    }

    print(f"{'gate':38s} {'HIGH':>6s} {'Usher kept':>10s} {'HK in HIGH':>11s}")
    for name, signal in gates.items():
        gated_high = is_high & signal
        n_high = int(gated_high.sum())
        omim_kept = sum(1 for i in omim if gated_high[i])
        omim_high_now = sum(1 for i in omim if is_high[i])
        hk_in = [genes[i] for i in hk if gated_high[i]]
        print(f"{name:38s} {n_high:6d} {omim_kept:>3d}/{omim_high_now:<6d} "
              f"{len(hk_in):>5d}  {','.join(hk_in) if hk_in else '-'}")

    # detail for the recommended gate (G2: localization or top-quartile animal)
    rec = (loc > 0) | (animal >= q75)
    print(f"\n=== Detail: recommended gate G2 (loc>0 OR animal>=Q75={q75:.2f}) ===")
    demoted = [genes[i] for i in range(len(genes)) if is_high[i] and not rec[i]]
    print(f"  HIGH-tier genes demoted to MEDIUM: {len(demoted)}")
    print(f"  housekeeping demoted: "
          f"{[genes[i] for i in hk if is_high[i] and not rec[i]]}")
    print(f"  Established Usher genes in HIGH, all retained: "
          f"{all(rec[i] for i in omim if is_high[i])}")
    known_idx = [gidx[g] for g in KNOWN if g in gidx]
    known_high = [i for i in known_idx if is_high[i]]
    known_kept = [i for i in known_high if rec[i]]
    print(f"  known genes (Usher+SYSCILIA) in HIGH: {len(known_high)} -> "
          f"{len(known_kept)} retained after gate")


if __name__ == "__main__":
    main()

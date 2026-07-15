# Expression/protein shortlist exploration

This analysis prioritizes genes within the existing HIGH tier; it does not alter
composite scores or production confidence tiers.

## Data availability

- HIGH candidates: 83
- OMIM Usher genes already in HIGH: 3
- OMIM + SYSCILIA controls already in HIGH: 4
- CellxGene hair-cell coverage within HIGH: 0/83
- GSE135913 fetal cochlear coverage within HIGH: 82/83
- Photoreceptor Q75 within HIGH: 0.7518645226955414
- Fetal cochlear hair-cell Q75 within HIGH: 0.5778035311531147
- HPA retina Q75 within HIGH: 3.0

> CellxGene hair-cell expression is unavailable. The cochlear value is an
> exploratory aggregate from marker-validated fetal GSE135913 clusters and
> is not yet part of the production expression layer.

## Strategy comparison

| Strategy | Genes | Reduction | OMIM retained | Known retained |
|---|---:|---:|---:|---:|
| Photoreceptor expression >= Q75 | 21 | 74.7% | 2/3 | 3/4 |
| Fetal cochlear hair-cell expression >= Q75 | 21 | 74.7% | 3/3 | 3/4 |
| Photoreceptor and hair-cell expression >= Q75 | 7 | 91.6% | 2/3 | 2/4 |
| Photoreceptor and HPA retina >= Q75 | 1 | 98.8% | 0/3 | 0/4 |
| Direct cilia/centrosome protein evidence | 31 | 62.7% | 0/3 | 1/4 |
| Photoreceptor >= Q75 OR direct protein | 46 | 44.6% | 2/3 | 3/4 |
| Photoreceptor >= Q75 AND direct protein | 6 | 92.8% | 0/3 | 1/4 |

## Interpretation rule

A strategy is exploratory unless it reduces the shortlist while retaining all
positive controls already present in HIGH. Missing evidence must be audited before
any strategy becomes a gate; here it provides no gate support but remains visible
in the gene-level table. Protein AND expression is included as a stress
test, not as a recommended hard gate.

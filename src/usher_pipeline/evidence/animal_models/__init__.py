"""Animal model phenotype evidence layer.

Retrieves knockout/perturbation phenotypes from:
- MGI (Mouse Genome Informatics) - mouse phenotypes
- ZFIN (Zebrafish Information Network) - zebrafish phenotypes
- IMPC (International Mouse Phenotyping Consortium) - mouse phenotypes

Maps human genes to model organism orthologs with confidence scoring,
filters for sensory/cilia-relevant phenotypes, and scores evidence.
"""

from usher_pipeline.evidence.animal_models.models import (
    AnimalModelRecord,
    ANIMAL_TABLE_NAME,
    SENSORY_MP_KEYWORDS,
    SENSORY_ZP_KEYWORDS,
)
from usher_pipeline.evidence.animal_models.fetch import (
    fetch_ortholog_mapping,
    fetch_mgi_phenotypes,
    fetch_zfin_phenotypes,
    fetch_impc_phenotypes,
)
from usher_pipeline.evidence.animal_models.transform import (
    filter_sensory_phenotypes,
    score_animal_evidence,
    process_animal_model_evidence,
)
from usher_pipeline.evidence.animal_models.load import (
    load_to_duckdb,
    query_sensory_phenotype_genes,
)

__all__ = [
    "AnimalModelRecord",
    "ANIMAL_TABLE_NAME",
    "SENSORY_MP_KEYWORDS",
    "SENSORY_ZP_KEYWORDS",
    "fetch_ortholog_mapping",
    "fetch_mgi_phenotypes",
    "fetch_zfin_phenotypes",
    "fetch_impc_phenotypes",
    "filter_sensory_phenotypes",
    "score_animal_evidence",
    "process_animal_model_evidence",
    "load_to_duckdb",
    "query_sensory_phenotype_genes",
]

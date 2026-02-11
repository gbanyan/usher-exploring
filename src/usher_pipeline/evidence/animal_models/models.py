"""Data models for animal model phenotype evidence."""

from typing import Optional
from pydantic import BaseModel, Field


# Table name for DuckDB storage
ANIMAL_TABLE_NAME = "animal_model_phenotypes"


# Mammalian Phenotype (MP) ontology keywords for sensory/cilia relevance
SENSORY_MP_KEYWORDS = [
    "hearing",
    "deaf",
    "vestibular",
    "balance",
    "retina",
    "photoreceptor",
    "vision",
    "blind",
    "cochlea",
    "stereocilia",
    "cilia",
    "cilium",
    "flagellum",
    "situs inversus",
    "laterality",
    "hydrocephalus",
    "kidney cyst",
    "polycystic",
]


# Zebrafish Phenotype (ZP) ontology keywords for sensory/cilia relevance
SENSORY_ZP_KEYWORDS = [
    "hearing",
    "deaf",
    "vestibular",
    "balance",
    "retina",
    "photoreceptor",
    "vision",
    "blind",
    "eye",
    "ear",
    "otolith",
    "lateral line",
    "cilia",
    "cilium",
    "flagellum",
    "situs",
    "laterality",
    "hydrocephalus",
    "kidney cyst",
    "pronephros",
]


class AnimalModelRecord(BaseModel):
    """Record representing animal model phenotype evidence for a gene.

    Attributes:
        gene_id: Human gene ID (ENSG)
        gene_symbol: Human gene symbol
        mouse_ortholog: Mouse gene symbol (MGI ID or symbol)
        mouse_ortholog_confidence: Ortholog confidence (HIGH/MEDIUM/LOW based on HCOP support)
        zebrafish_ortholog: Zebrafish gene symbol (ZFIN ID or symbol)
        zebrafish_ortholog_confidence: Ortholog confidence (HIGH/MEDIUM/LOW)
        has_mouse_phenotype: Whether mouse ortholog has phenotypes in MGI
        has_zebrafish_phenotype: Whether zebrafish ortholog has phenotypes in ZFIN
        has_impc_phenotype: Whether mouse ortholog has phenotypes in IMPC
        sensory_phenotype_count: Number of sensory-relevant phenotypes across all sources
        phenotype_categories: Semicolon-separated list of matched phenotype terms
        animal_model_score_normalized: Composite animal model evidence score (0-1 range)
    """

    gene_id: str = Field(..., description="Human gene ID (ENSG)")
    gene_symbol: str = Field(..., description="Human gene symbol")

    mouse_ortholog: Optional[str] = Field(None, description="Mouse gene symbol/ID")
    mouse_ortholog_confidence: Optional[str] = Field(
        None,
        description="Ortholog confidence: HIGH/MEDIUM/LOW"
    )

    zebrafish_ortholog: Optional[str] = Field(None, description="Zebrafish gene symbol/ID")
    zebrafish_ortholog_confidence: Optional[str] = Field(
        None,
        description="Ortholog confidence: HIGH/MEDIUM/LOW"
    )

    has_mouse_phenotype: Optional[bool] = Field(
        None,
        description="Mouse ortholog has phenotypes in MGI"
    )
    has_zebrafish_phenotype: Optional[bool] = Field(
        None,
        description="Zebrafish ortholog has phenotypes in ZFIN"
    )
    has_impc_phenotype: Optional[bool] = Field(
        None,
        description="Mouse ortholog has phenotypes in IMPC"
    )

    sensory_phenotype_count: Optional[int] = Field(
        None,
        description="Number of sensory-relevant phenotypes"
    )
    phenotype_categories: Optional[str] = Field(
        None,
        description="Semicolon-separated matched phenotype terms"
    )

    animal_model_score_normalized: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Composite animal model evidence score (0-1)"
    )

"""
Golden-set regressiotestit Kuntalaki-hakujen laatulle.

Vähintään 20 testikysymystä, joissa varmistetaan että odotetut pykälät
löytyvät TOP-3 tuloksista.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sentence_transformers import SentenceTransformer

from analysis_layer.vector_store.chroma_store import ChromaVectorStore


@dataclass
class GoldenQuery:
    """A golden query with expected sections in TOP-3."""

    query: str
    expected_sections: list[str]  # At least one must be in TOP-3
    description: str = ""


# Golden set: 20+ queries with expected results
GOLDEN_QUERIES: list[GoldenQuery] = [
    # Talous
    GoldenQuery(
        query="kunnan talousarvion alijäämä ja kattaminen",
        expected_sections=["110", "110a", "148"],
        description="Alijäämän kattamisvelvollisuus",
    ),
    GoldenQuery(
        query="taloussuunnitelman tasapaino",
        expected_sections=["110"],
        description="Taloussuunnitelma tasapainossa",
    ),
    GoldenQuery(
        query="kunnan tilinpäätös ja toimintakertomus",
        expected_sections=["113", "114", "115"],
        description="Tilinpäätösdokumentit",
    ),
    GoldenQuery(
        query="konsernitilinpäätös kuntakonserni",
        expected_sections=["114"],
        description="Konsernitilinpäätös",
    ),
    GoldenQuery(
        query="kunnan kirjanpito ja laskentatoimi",
        expected_sections=["112"],
        description="Kirjanpito",
    ),
    # Kriisikunta / arviointimenettely
    GoldenQuery(
        query="erityisen vaikeassa taloudellisessa asemassa oleva kunta",
        expected_sections=["118"],
        description="Kriisikunnan arviointimenettely",
    ),
    GoldenQuery(
        query="arviointimenettely kuntayhtymässä",
        expected_sections=["119"],
        description="Kuntayhtymän arviointimenettely",
    ),
    GoldenQuery(
        query="kunnan arviointiryhmä ja selvitys",
        expected_sections=["118"],
        description="Arviointiryhmän toiminta",
    ),
    # Lainat ja takaukset
    GoldenQuery(
        query="kunnan lainan antaminen ja takaus",
        expected_sections=["129"],
        description="Laina ja takaus",
    ),
    GoldenQuery(
        query="vakuuden antaminen kunnasta",
        expected_sections=["129"],
        description="Vakuudet",
    ),
    # Hallinto
    GoldenQuery(
        query="kunnanjohtajan asema ja tehtävät",
        expected_sections=["38", "41"],
        description="Kunnanjohtaja",
    ),
    GoldenQuery(
        query="kunnanhallituksen tehtävät ja toimivalta",
        expected_sections=["38", "39"],
        description="Kunnanhallitus",
    ),
    GoldenQuery(
        query="valtuuston kokoontuminen ja päätösvaltaisuus",
        expected_sections=["94", "95"],
        description="Valtuuston kokous",
    ),
    GoldenQuery(
        query="hallintosääntö ja sen sisältö",
        expected_sections=["90"],
        description="Hallintosääntö",
    ),
    # Päätöksenteko
    GoldenQuery(
        query="esteellisyys ja jääviys kunnan toimielimessä",
        expected_sections=["97"],
        description="Esteellisyys",
    ),
    GoldenQuery(
        query="oikaisuvaatimus kunnan päätöksestä",
        expected_sections=["134"],
        description="Oikaisuvaatimus",
    ),
    GoldenQuery(
        query="kunnallisvalitus hallinto-oikeuteen",
        expected_sections=["135"],
        description="Kunnallisvalitus",
    ),
    GoldenQuery(
        query="valitusperusteet kunnan päätöksestä",
        expected_sections=["135"],
        description="Valitusperusteet",
    ),
    # Kuntayhtymä
    GoldenQuery(
        query="kuntayhtymän perustaminen ja perussopimus",
        expected_sections=["55", "56"],
        description="Kuntayhtymän perustaminen",
    ),
    GoldenQuery(
        query="kuntayhtymästä eroaminen",
        expected_sections=["62"],
        description="Kuntayhtymästä eroaminen",
    ),
    # Kuntakonserni
    GoldenQuery(
        query="kuntakonserni ja tytäryhteisö",
        expected_sections=["6"],
        description="Kuntakonsernin määritelmä",
    ),
    GoldenQuery(
        query="konserniohje ja omistajapoliittiset linjaukset",
        expected_sections=["47"],
        description="Konserniohje",
    ),
    # Osallistuminen
    GoldenQuery(
        query="kunnan asukkaiden osallistuminen ja vaikuttaminen",
        expected_sections=["22"],
        description="Osallistumisoikeudet",
    ),
    GoldenQuery(
        query="aloiteoikeus kunnassa",
        expected_sections=["23"],
        description="Aloiteoikeus",
    ),
    # Tilintarkastus
    GoldenQuery(
        query="kunnan tilintarkastus ja tilintarkastaja",
        expected_sections=["122", "123"],
        description="Tilintarkastus",
    ),
]


@pytest.fixture(scope="module")
def search_engine():
    """Initialize search engine once for all tests."""
    base_path = Path(__file__).parent.parent.parent
    chroma_path = base_path / "analysis_layer" / "embeddings" / "chroma_db"

    if not chroma_path.exists():
        pytest.skip("ChromaDB index not found. Run build_embeddings.py first.")

    model = SentenceTransformer("BAAI/bge-m3")
    store = ChromaVectorStore(chroma_path, "kuntalaki")

    return model, store


def search_top3(model, store, query: str) -> list[str]:
    """Search and return TOP-3 section IDs."""
    embedding = model.encode([query], normalize_embeddings=True)[0]
    results = store.query(embedding.tolist(), n_results=3)

    sections = []
    for meta in results["metadatas"][0]:
        sections.append(meta["section_id"])

    return sections


@pytest.mark.parametrize(
    "golden",
    GOLDEN_QUERIES,
    ids=[f"{i+1}_{g.description[:30]}" for i, g in enumerate(GOLDEN_QUERIES)],
)
def test_golden_query(search_engine, golden: GoldenQuery):
    """Test that at least one expected section is in TOP-3."""
    model, store = search_engine

    top3_sections = search_top3(model, store, golden.query)

    # Check if any expected section is in TOP-3
    found = any(exp in top3_sections for exp in golden.expected_sections)

    assert found, (
        f"Query: '{golden.query}'\n"
        f"Expected one of: {golden.expected_sections}\n"
        f"Got TOP-3: {top3_sections}"
    )


def test_index_has_documents(search_engine):
    """Test that index has expected number of documents."""
    _, store = search_engine
    count = store.count()
    assert count >= 400, f"Expected at least 400 documents, got {count}"


def test_110_and_110a_are_separate(search_engine):
    """Test that § 110 and § 110a are correctly separated."""
    model, store = search_engine

    # Search for COVID exception (should find 110a)
    embedding = model.encode(
        ["alijäämän kattamisen määräajan jatkaminen covid"],
        normalize_embeddings=True,
    )[0]
    results = store.query(embedding.tolist(), n_results=5)

    sections = [meta["section_id"] for meta in results["metadatas"][0]]

    # 110a should be in results, and should be different from 110
    assert "110a" in sections, f"110a not found in results: {sections}"


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short"])


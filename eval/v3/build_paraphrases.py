"""
Deterministinen parafraasigeneraattori Kuntalaki-kyselyille.

Generoi variaatioita synonyymisanakirjan pohjalta ilman LLM-riippuvuutta.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict


class Question(TypedDict, total=False):
    id: str
    category: str
    must: bool
    query: str
    expected_any: list[dict[str, str]]
    expected_none: list[str] | None
    k: int
    min_score: float
    notes: str
    test_type: str


class SynonymData(TypedDict, total=False):
    term_synonyms: dict[str, list[str]]
    section_specific_synonyms: dict[str, dict[str, list[str]]]


def load_synonyms(synonyms_path: Path) -> SynonymData:
    """Load synonym dictionary."""
    with synonyms_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_golden_questions(questions_path: Path) -> list[Question]:
    """Load original golden-set questions."""
    with questions_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def apply_term_synonym(query: str, term: str, synonym: str) -> str | None:
    """Apply a single synonym replacement if term exists in query."""
    # Case-insensitive check
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    if pattern.search(query):
        return pattern.sub(synonym, query)
    return None


def generate_paraphrases_for_question(
    question: Question,
    synonyms: SynonymData,
    max_paraphrases: int = 3,
) -> list[Question]:
    """Generate paraphrase variations for a single question."""
    paraphrases: list[Question] = []
    query = question["query"]
    term_synonyms = synonyms.get("term_synonyms", {})
    section_synonyms = synonyms.get("section_specific_synonyms", {})
    
    seen_queries: set[str] = {query.lower()}
    
    # Get expected sections for section-specific synonyms
    expected_sections: list[str] = []
    for exp in question.get("expected_any", []):
        sec = str(exp.get("section", ""))
        if sec and sec not in expected_sections:
            expected_sections.append(sec)
    
    # Apply term-level synonyms
    for term, syn_list in term_synonyms.items():
        if len(paraphrases) >= max_paraphrases:
            break
        for synonym in syn_list[:2]:  # Max 2 synonyms per term
            if len(paraphrases) >= max_paraphrases:
                break
            new_query = apply_term_synonym(query, term, synonym)
            if new_query and new_query.lower() not in seen_queries:
                seen_queries.add(new_query.lower())
                paraphrases.append(_create_paraphrase(
                    question, new_query, len(paraphrases) + 1, "synonym"
                ))
    
    # Apply section-specific synonyms
    for section in expected_sections:
        if section in section_synonyms:
            sec_data = section_synonyms[section]
            terms = sec_data.get("terms", [])
            syns = sec_data.get("synonyms", [])
            
            for term, synonym in zip(terms, syns):
                if len(paraphrases) >= max_paraphrases:
                    break
                new_query = apply_term_synonym(query, term, synonym)
                if new_query and new_query.lower() not in seen_queries:
                    seen_queries.add(new_query.lower())
                    paraphrases.append(_create_paraphrase(
                        question, new_query, len(paraphrases) + 1, "section_synonym"
                    ))
    
    return paraphrases


def _create_paraphrase(
    original: Question,
    new_query: str,
    idx: int,
    test_type: str,
) -> Question:
    """Create a new paraphrase question based on original."""
    new_id = f"{original['id']}-P{idx:02d}"
    return Question(
        id=new_id,
        category=original.get("category", ""),
        must=False,  # Paraphrases are SHOULD, not MUST
        query=new_query,
        expected_any=original.get("expected_any", []),
        expected_none=original.get("expected_none"),
        k=original.get("k", 5),
        min_score=original.get("min_score", 0.55),
        notes=f"Paraphrase of {original['id']}: {test_type}",
        test_type=test_type,
    )


def generate_hard_negatives() -> list[Question]:
    """Generate hard negative test cases.
    
    These are questions where a nearby but incorrect section is tempting.
    """
    hard_negatives: list[Question] = [
        # 110 vs 110a distinction
        Question(
            id="KL-HARD-001",
            category="hard_negative",
            must=False,
            query="Alijäämän kattamisen perusmääräaika ilman poikkeuksia",
            expected_any=[{"section": "110", "moment": "3"}],
            expected_none=["110a"],
            k=5,
            min_score=0.55,
            notes="Pitää osua 110, EI 110a (covid-poikkeus)",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-002",
            category="hard_negative",
            must=False,
            query="COVID-19 epidemian takia myönnetty poikkeus alijäämän kattamiseen",
            expected_any=[{"section": "110a", "moment": ""}],
            expected_none=["110"],
            k=3,
            min_score=0.55,
            notes="Pitää osua 110a, EI 110 (perus)",
            test_type="hard_negative",
        ),
        # 113 vs 114 (tilinpäätös vs konsernitilinpäätös)
        Question(
            id="KL-HARD-003",
            category="hard_negative",
            must=False,
            query="Yksittäisen kunnan tilinpäätöksen asiakirjat (ei konserni)",
            expected_any=[{"section": "113", "moment": "2"}],
            expected_none=["114"],
            k=3,
            min_score=0.55,
            notes="Pitää osua 113, EI 114 (konserni)",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-004",
            category="hard_negative",
            must=False,
            query="Kuntakonsernin konsolidoitu tilinpäätös",
            expected_any=[{"section": "114", "moment": ""}],
            expected_none=["113"],
            k=3,
            min_score=0.55,
            notes="Pitää osua 114, EI 113",
            test_type="hard_negative",
        ),
        # 115 momenttien erottelu
        Question(
            id="KL-HARD-005",
            category="hard_negative",
            must=False,
            query="Sisäisen valvonnan ja riskienhallinnan järjestämisen selostus toimintakertomuksessa",
            expected_any=[{"section": "115", "moment": "2"}],
            expected_none=[],
            k=3,
            min_score=0.55,
            notes="Pitää osua tarkalleen 115:2",
            test_type="hard_negative_precision",
        ),
        Question(
            id="KL-HARD-006",
            category="hard_negative",
            must=False,
            query="Selvitys alijäämän kattamisesta toimintakertomuksessa",
            expected_any=[{"section": "115", "moment": "3"}],
            expected_none=[],
            k=3,
            min_score=0.55,
            notes="Pitää osua tarkalleen 115:3",
            test_type="hard_negative_precision",
        ),
        # 118 momenttien erottelu (kriisikunta-kriteerit)
        Question(
            id="KL-HARD-007",
            category="hard_negative",
            must=False,
            query="Arviointimenettelyn aloittamisen edellytykset alijäämän perusteella",
            expected_any=[{"section": "118", "moment": "2"}],
            expected_none=[],
            k=3,
            min_score=0.55,
            notes="Pitää osua tarkalleen 118:2",
            test_type="hard_negative_precision",
        ),
        Question(
            id="KL-HARD-008",
            category="hard_negative",
            must=False,
            query="Konsernitilinpäätöksen tunnuslukujen raja-arvot arviointimenettelylle",
            expected_any=[{"section": "118", "moment": "3"}],
            expected_none=[],
            k=3,
            min_score=0.55,
            notes="Pitää osua tarkalleen 118:3 (konsernitunnusluvut)",
            test_type="hard_negative_precision",
        ),
        # Sekoituksia samankaltaisista aiheista
        Question(
            id="KL-HARD-009",
            category="hard_negative",
            must=False,
            query="Tarkastuslautakunnan tehtävät (EI tilintarkastaja)",
            expected_any=[{"section": "121", "moment": ""}],
            expected_none=["122", "123", "124", "125"],
            k=3,
            min_score=0.55,
            notes="Tarkastuslautakunta vs tilintarkastaja",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-010",
            category="hard_negative",
            must=False,
            query="Kuntayhtymän perussopimuksen sisältö (EI eroaminen)",
            expected_any=[{"section": "56", "moment": ""}],
            expected_none=["62", "62a", "62b"],
            k=3,
            min_score=0.55,
            notes="Perussopimus vs eroaminen/yhdistyminen/jakautuminen",
            test_type="hard_negative",
        ),
        # Lisää hard negatives
        Question(
            id="KL-HARD-011",
            category="hard_negative",
            must=False,
            query="Kunnanjohtajan tehtävät (EI pormestari)",
            expected_any=[{"section": "38", "moment": ""}, {"section": "41", "moment": ""}],
            expected_none=["44", "45"],
            k=3,
            min_score=0.55,
            notes="Kunnanjohtaja vs pormestari",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-012",
            category="hard_negative",
            must=False,
            query="Pormestarin valinta ja asema (EI kunnanjohtaja)",
            expected_any=[{"section": "44", "moment": ""}, {"section": "45", "moment": ""}],
            expected_none=["38", "41", "42"],
            k=3,
            min_score=0.55,
            notes="Pormestari vs kunnanjohtaja",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-013",
            category="hard_negative",
            must=False,
            query="Oikaisuvaatimus kunnan päätöksestä (EI kunnallisvalitus)",
            expected_any=[{"section": "134", "moment": ""}],
            expected_none=["135"],
            k=3,
            min_score=0.55,
            notes="Oikaisuvaatimus vs kunnallisvalitus",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-014",
            category="hard_negative",
            must=False,
            query="Kunnallisvalitus hallinto-oikeuteen (EI oikaisuvaatimus)",
            expected_any=[{"section": "135", "moment": ""}],
            expected_none=["134"],
            k=3,
            min_score=0.55,
            notes="Kunnallisvalitus vs oikaisuvaatimus",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-015",
            category="hard_negative",
            must=False,
            query="Kunnan kirjanpidon erityissäännökset (EI tilinpäätös)",
            expected_any=[{"section": "112", "moment": ""}],
            expected_none=["113"],
            k=3,
            min_score=0.55,
            notes="Kirjanpito vs tilinpäätös",
            test_type="hard_negative",
        ),
        # Adversarial - väärä pykälä houkuttelee
        Question(
            id="KL-HARD-016",
            category="hard_negative",
            must=False,
            query="Talousarvion rakenne ja osat (EI tilinpäätöksen rakenne)",
            expected_any=[{"section": "110", "moment": "4"}],
            expected_none=["113"],
            k=3,
            min_score=0.55,
            notes="Talousarvion osat vs tilinpäätöksen osat",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-017",
            category="hard_negative",
            must=False,
            query="Tytäryhteisön tiedonantovelvollisuus kunnalle (EI konserniohjeet)",
            expected_any=[{"section": "116", "moment": ""}],
            expected_none=["47"],
            k=3,
            min_score=0.55,
            notes="Tiedonanto vs omistajaohjaus",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-018",
            category="hard_negative",
            must=False,
            query="Konserniohjeet ja omistajapoliittinen ohjaus (EI tiedonanto)",
            expected_any=[{"section": "47", "moment": ""}],
            expected_none=["116"],
            k=3,
            min_score=0.55,
            notes="Omistajaohjaus vs tiedonanto",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-019",
            category="hard_negative",
            must=False,
            query="Kuntayhtymän eroaminen (EI yhdistyminen tai jakautuminen)",
            expected_any=[{"section": "62", "moment": ""}],
            expected_none=["62a", "62b"],
            k=3,
            min_score=0.55,
            notes="Eroaminen vs yhdistyminen/jakautuminen",
            test_type="hard_negative",
        ),
        Question(
            id="KL-HARD-020",
            category="hard_negative",
            must=False,
            query="Kuntayhtymien yhdistyminen (EI eroaminen)",
            expected_any=[{"section": "62a", "moment": ""}],
            expected_none=["62", "62b"],
            k=3,
            min_score=0.55,
            notes="Yhdistyminen vs eroaminen",
            test_type="hard_negative",
        ),
    ]
    return hard_negatives


def generate_precision_at_1_questions() -> list[Question]:
    """Generate moment-precise questions for Precision@1 testing."""
    precision_questions: list[Question] = [
        # Tarkat momenttikysymykset
        Question(
            id="KL-PREC-001",
            category="precision",
            must=False,
            query="Mikä on talousarvion ja -suunnitelman hyväksymisen aikataulu?",
            expected_any=[{"section": "110", "moment": "1"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 110:1",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-002",
            category="precision",
            must=False,
            query="Taloussuunnitelman monivuotisuus ja kattavuusvaatimus",
            expected_any=[{"section": "110", "moment": "2"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 110:2",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-003",
            category="precision",
            must=False,
            query="Alijäämän kattamisvelvollisuus ja neljän vuoden aikaraja",
            expected_any=[{"section": "110", "moment": "3"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 110:3",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-004",
            category="precision",
            must=False,
            query="Käyttötalous-, tuloslaskelma-, investointi- ja rahoitusosan vaatimus talousarviossa",
            expected_any=[{"section": "110", "moment": "4"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 110:4",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-005",
            category="precision",
            must=False,
            query="Tilinpäätöksen sisältämät asiakirjat: tase, tuloslaskelma, rahoituslaskelma, liitetiedot",
            expected_any=[{"section": "113", "moment": "2"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 113:2",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-006",
            category="precision",
            must=False,
            query="Tilinpäätöksen allekirjoittajat kunnassa",
            expected_any=[{"section": "113", "moment": "4"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 113:4",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-007",
            category="precision",
            must=False,
            query="Konsernitilinpäätöksen laadintavelvollisuus ja tytäryhteisöjen sisällyttäminen",
            expected_any=[{"section": "114", "moment": "1"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 114:1",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-008",
            category="precision",
            must=False,
            query="Toimintakertomuksen sisältö: tavoitteiden toteutuminen ja talouden olennaiset asiat",
            expected_any=[{"section": "115", "moment": "1"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 115:1",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-009",
            category="precision",
            must=False,
            query="Sisäisen valvonnan ja riskienhallinnan järjestämisen selostus",
            expected_any=[{"section": "115", "moment": "2"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 115:2",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-010",
            category="precision",
            must=False,
            query="Alijäämän kattamissuunnitelma toimintakertomuksessa jos alijäämää ei katettu",
            expected_any=[{"section": "115", "moment": "3"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 115:3",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-011",
            category="precision",
            must=False,
            query="Arviointimenettelyn käynnistäminen valtiovarainministeriön aloitteesta",
            expected_any=[{"section": "118", "moment": "1"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 118:1",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-012",
            category="precision",
            must=False,
            query="Arviointimenettelyn edellytykset: alijäämän kattamatta jättäminen määräajassa",
            expected_any=[{"section": "118", "moment": "2"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 118:2",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-013",
            category="precision",
            must=False,
            query="Konsernitilinpäätöksen tunnuslukurajat arviointimenettelylle",
            expected_any=[{"section": "118", "moment": "3"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 118:3",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-014",
            category="precision",
            must=False,
            query="Arviointiryhmän asettaminen ja jäsenten määrä",
            expected_any=[{"section": "118", "moment": "5"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 118:5",
            test_type="precision_at_1",
        ),
        Question(
            id="KL-PREC-015",
            category="precision",
            must=False,
            query="Arviointiryhmän ehdotusten käsittely ja valtuuston päätökset",
            expected_any=[{"section": "118", "moment": "6"}],
            k=3,
            min_score=0.55,
            notes="Tarkka momentti 118:6",
            test_type="precision_at_1",
        ),
    ]
    return precision_questions


def main() -> None:
    """Main entry point."""
    root = Path(__file__).parent.parent.parent
    v3_dir = Path(__file__).parent
    
    # Load resources
    synonyms_path = v3_dir / "synonyms.json"
    golden_path = root / "eval" / "questions_kuntalaki_golden.json"
    output_path = v3_dir / "questions_kuntalaki_v3.json"
    
    if not synonyms_path.exists():
        print(f"ERROR: synonyms.json not found: {synonyms_path}")
        return
    
    if not golden_path.exists():
        print(f"ERROR: Golden questions not found: {golden_path}")
        return
    
    synonyms = load_synonyms(synonyms_path)
    golden_questions = load_golden_questions(golden_path)
    
    print(f"Loaded {len(golden_questions)} golden questions")
    
    # Start with all original questions (mark as 'base')
    all_questions: list[Question] = []
    for q in golden_questions:
        q_copy = Question(**q)
        q_copy["test_type"] = "base"
        all_questions.append(q_copy)
    
    # Generate paraphrases for MUST questions
    must_questions = [q for q in golden_questions if q.get("must", False)]
    print(f"Generating paraphrases for {len(must_questions)} MUST questions...")
    
    for q in must_questions:
        paraphrases = generate_paraphrases_for_question(q, synonyms, max_paraphrases=3)
        all_questions.extend(paraphrases)
    
    # Generate paraphrases for select SHOULD questions (focus on problem categories)
    problem_categories = ["toimintakertomus", "covid-poikkeus", "arviointimenettely"]
    problem_should = [
        q for q in golden_questions
        if not q.get("must", False) and q.get("category", "") in problem_categories
    ]
    print(f"Generating paraphrases for {len(problem_should)} problem-category SHOULD questions...")
    
    for q in problem_should:
        paraphrases = generate_paraphrases_for_question(q, synonyms, max_paraphrases=2)
        all_questions.extend(paraphrases)
    
    # Add hard negatives
    hard_negatives = generate_hard_negatives()
    print(f"Adding {len(hard_negatives)} hard negative questions...")
    all_questions.extend(hard_negatives)
    
    # Add precision@1 questions
    precision_questions = generate_precision_at_1_questions()
    print(f"Adding {len(precision_questions)} precision@1 questions...")
    all_questions.extend(precision_questions)
    
    # Write output
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)
    
    print(f"\nWrote {len(all_questions)} questions to {output_path}")
    
    # Summary
    base_count = sum(1 for q in all_questions if q.get("test_type") == "base")
    para_count = sum(1 for q in all_questions if q.get("test_type") in ("synonym", "section_synonym"))
    hard_count = sum(1 for q in all_questions if q.get("test_type", "").startswith("hard_negative"))
    prec_count = sum(1 for q in all_questions if q.get("test_type") == "precision_at_1")
    
    print(f"\n--- Summary ---")
    print(f"Base questions: {base_count}")
    print(f"Paraphrases: {para_count}")
    print(f"Hard negatives: {hard_count}")
    print(f"Precision@1: {prec_count}")
    print(f"Total: {len(all_questions)}")


if __name__ == "__main__":
    main()


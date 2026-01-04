# Kuntalaki Retrieval Evaluation v3 - SOTA Testing Framework

Tämä on laajennettu testausympäristö Kuntalaki-indeksin todelliseen validointiin.

## Laatuportit (Quality Gates)

### Gate 1: Kriittinen juridiikka (MUST)
- **MUST pass rate**: ≥ 99%
- **MUST Top-1 hit rate**: ≥ 80%
- Ei sallita regressiota kriittisissä kysymyksissä

### Gate 2: Käytettävyys (SHOULD)
- **SHOULD pass rate**: ≥ 95%
- Laajempi käytännön soveltuvuuden testaus

### Gate 3: Kategoria-kohtainen minimi
- Jokainen pääkategoria: ≥ 90%
- Erityishuomio: toimintakertomus, covid-poikkeus, arviointimenettely

### Gate 4: Stabiliteetti
- Sama kysymyspatteri 3 ajoa peräkkäin
- Pass-rate vaihtelu: max ±2 %-yksikköä

## Testiluokat

### A. Peruskysymykset (Base)
Alkuperäiset 80+ kysymystä golden-setistä.

### B. Parafraasit (Paraphrase)
Jokaisesta MUST-kysymyksestä 3-5 variaatiota:
- Puhekieli ("kriisikunta", "korona")
- Lakitermi
- Lyhyt hakusana
- Pitkä selittävä kysymys

### C. Hard Negatives
Kysymyksiä, joissa läheinen mutta väärä pykälä on houkutteleva.
- `expected_none`: lista pykäliä, jotka EIVÄT saa tulla top-1:een.

### D. Momentti-tarkat (Precision@1)
Vain oikea momentti hyväksytään, ei pelkkä pykälä.

## Käyttö

### Perusajo (oletus k=5, min_score=0.55)
```bash
python eval/v3/run_kuntalaki_eval_v3.py
```

### Matrix-ajo (k-sweep + min_score-sweep)
```bash
python eval/v3/run_kuntalaki_eval_v3.py --matrix
```

### Yksittäinen sweep
```bash
python eval/v3/run_kuntalaki_eval_v3.py --k-values 3,5,10 --min-score-values 0.50,0.55,0.60
```

### Stabiliteetti-testi (3 ajoa peräkkäin)
```bash
python eval/v3/run_kuntalaki_eval_v3.py --stability-runs 3
```

## Parafraasien generointi

```bash
python eval/v3/build_paraphrases.py
```

Generoi `questions_kuntalaki_v3.json` synonyymisanakirjan pohjalta.

## Tulostiedostot

- `eval/v3/kuntalaki_eval_v3_results.json` - yksityiskohtaiset tulokset
- `eval/v3/report_kuntalaki_eval_v3.md` - Markdown-raportti
- `eval/v3/report_matrix.md` - Matrix-testin koontiraportti (kun --matrix)

## Synonyymisanakirja

Tiedosto `eval/v3/synonyms.json` sisältää domain-kohtaiset synonyymit:
- covid ↔ korona ↔ pandemia
- kriisikunta ↔ erityisen vaikea taloudellinen asema
- sisäinen valvonta ↔ riskienhallinta
- jne.

## Korjauspolku epäonnistuneille kategorioille

### Toimintakertomus (40% → 90%)
- Ongelma: "momentti-erottelu" ja terminologia
- Korjaus: synonyymi-rikastus metatageihin (riskienhallinta, sisäinen valvonta, olennaiset tapahtumat)

### Covid-poikkeus (66.7% → 90%)
- Ongelma: "COVID" vs "korona" -synonyymiongelma
- Korjaus: lisää tagit "korona", "koronaepidemia", "pandemia" 110a-pykäliin

### Arviointimenettely
- Ongelma: "kriisikunta" ei ole pykäläotsikko
- Korjaus: tagit "kriisikunta", "kriteerit", "tunnusluvut" momentteihin 118:2-3


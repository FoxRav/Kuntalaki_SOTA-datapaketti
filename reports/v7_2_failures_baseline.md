# v7.2 Failure Mining Report

**Generated from:** results_cross_law.json
**Total questions:** 100
**STRICT failures:** 39

## Failure Type Distribution

| Type | Count | Description |
|------|-------|-------------|
| A | 29 | Wrong law (routing fail) |
| B | 8 | Correct law, wrong section |
| C | 2 | Correct section, wrong moment |
| D | 0 | Correct hit in top-k, but not top-1 |

## Failures per Pair

| Pair | Failures | Total | Rate |
|------|----------|-------|------|
| HANK | 9 | 20 | 45% |
| KPA | 11 | 20 | 55% |
| KPL | 3 | 20 | 15% |
| OYL | 8 | 20 | 40% |
| TILA | 8 | 20 | 40% |

## Top 20 Keywords in Failed Queries

| Keyword | Count |
|---------|-------|
| valtuuston | 2 |
| päätös | 2 |
| hankinnoissa | 2 |
| menettely | 2 |
| taseen | 2 |
| vastaavat | 2 |
| taseessa | 2 |
| pääoma | 2 |
| tuloslaskelmassa | 2 |
| osakeyhtiön | 2 |
| yhtiössä | 2 |
| pörssiyhtiön | 2 |
| julkisen | 1 |
| hankinnan | 1 |
| kynnysarvot | 1 |
| tarjouksen | 1 |
| valintaperusteet | 1 |
| puitejärjestely | 1 |
| hankintasopimus | 1 |
| tarjoajan | 1 |

## Type A: Wrong law (routing fail) (29)

### CROSS-KUNTA-HANK-003
**Query:** tarjouksen valintaperusteet
**Expected:** hankintalaki_1397_2016 §79.1
**Got Top-1:** kuntalaki_410_2015 §131.3 (score: 0.6079)
**Section Title:** Palveluvelvoite

### CROSS-KUNTA-HANK-012
**Query:** tarjoajan poissulkemisperusteet
**Expected:** hankintalaki_1397_2016 §81.1
**Got Top-1:** kuntalaki_410_2015 §131.3 (score: 0.5407)
**Section Title:** Palveluvelvoite

### CROSS-KUNTA-HANK-015
**Query:** neuvottelumenettely julkisissa hankinnoissa
**Expected:** hankintalaki_1397_2016 §36.1
**Got Top-1:** kuntalaki_410_2015 §12.1 (score: 0.6010)
**Section Title:** Kuntatalousohjelma

### CROSS-KUNTA-HANK-018
**Query:** sosiaalinen näkökulma hankinnoissa
**Expected:** hankintalaki_1397_2016 §108.2
**Got Top-1:** None

### CROSS-KUNTA-HANK-019
**Query:** käyttöoikeussopimus ja konsessio
**Expected:** hankintalaki_1397_2016 §117.2
**Got Top-1:** None

### CROSS-KUNTA-HANK-020
**Query:** avoin menettely ja rajoitettu menettely
**Expected:** hankintalaki_1397_2016 §33.1
**Got Top-1:** kuntalaki_410_2015 §131.3 (score: 0.5536)
**Section Title:** Palveluvelvoite

### CROSS-KUNTA-KPA-002
**Query:** taseen vastaavaa ja vastattavaa
**Expected:** kirjanpitoasetus_1339_1997 §5.3
**Got Top-1:** kirjanpitolaki_1336_1997 §1.2 (score: 0.5670)
**Section Title:** Tilinpäätöksen sisältö

### CROSS-KUNTA-KPA-007
**Query:** pysyvät vastaavat taseessa
**Expected:** kirjanpitoasetus_1339_1997 §6.1
**Got Top-1:** kirjanpitolaki_1336_1997 §3.1 (score: 0.6442)
**Section Title:** Pysyvät ja vaihtuvat vastaavat

### CROSS-KUNTA-KPA-009
**Query:** oma pääoma ja vieras pääoma taseessa
**Expected:** kirjanpitoasetus_1339_1997 §6.1
**Got Top-1:** kirjanpitolaki_1336_1997 §5.1 (score: 0.6435)
**Section Title:** Pääomalainan merkitseminen taseeseen

### CROSS-KUNTA-KPA-010
**Query:** tuloslaskelman henkilöstökulut
**Expected:** kirjanpitoasetus_1339_1997 §3.3
**Got Top-1:** kirjanpitolaki_1336_1997 §7.2 (score: 0.5403)
**Section Title:** Konsernin sisäiset erät ja vähemmistöosuudet


## Type B: Correct law, wrong section (8)

### CROSS-KUNTA-HANK-001
**Query:** julkisen hankinnan kynnysarvot
**Expected:** hankintalaki_1397_2016 §2.3
**Got Top-1:** hankintalaki_1397_2016 §25.1 (score: 0.6991)
**Section Title:** Kansalliset kynnysarvot

### CROSS-KUNTA-HANK-007
**Query:** puitejärjestely ja hankintasopimus
**Expected:** hankintalaki_1397_2016 §136.1
**Got Top-1:** hankintalaki_1397_2016 §42.4 (score: 0.7572)
**Section Title:** Puitejärjestely

### CROSS-KUNTA-HANK-014
**Query:** valtuuston päätös suuresta investoinnista
**Expected:** kuntalaki_410_2015 §118.6
**Got Top-1:** kuntalaki_410_2015 §111.1 (score: 0.5329)
**Section Title:** Veroja koskevat päätökset

### CROSS-KUNTA-KPA-011
**Query:** valtuuston päätös taseen osoittamasta tuloksesta
**Expected:** kuntalaki_410_2015 §118.6
**Got Top-1:** kuntalaki_410_2015 §121.5 (score: 0.6528)
**Section Title:** Tarkastuslautakunta

### CROSS-KUNTA-KPL-019
**Query:** pieni kirjanpitovelvollinen ja helpotukset
**Expected:** kirjanpitolaki_1336_1997 §16.1
**Got Top-1:** kirjanpitolaki_1336_1997 §4.2 (score: 0.5542)
**Section Title:** Kirjanpitorikkomus

### CROSS-KUNTA-OYL-006
**Query:** osakeyhtiön sulautuminen ja jakautuminen
**Expected:** osakeyhtiolaki_624_2006 §26.1
**Got Top-1:** osakeyhtiolaki_624_2006 §1.1 (score: 0.7135)
**Section Title:** Sulautuminen

### CROSS-KUNTA-OYL-012
**Query:** osakeyhtiön perustaminen
**Expected:** osakeyhtiolaki_624_2006 §13.1
**Got Top-1:** osakeyhtiolaki_624_2006 §1.1 (score: 0.6476)
**Section Title:** Perustamissopimus

### CROSS-KUNTA-TILA-017
**Query:** kunnan ulkoinen tarkastus ja valvonta
**Expected:** kuntalaki_410_2015 §123.1
**Got Top-1:** kuntalaki_410_2015 §121.2 (score: 0.6081)
**Section Title:** Tarkastuslautakunta


## Type C: Correct section, wrong moment (2)

### CROSS-KUNTA-KPL-007
**Query:** kirjanpidon menetelmät ja aineisto
**Expected:** kirjanpitolaki_1336_1997 §7.3
**Got Top-1:** kirjanpitolaki_1336_1997 §7.1 (score: 0.6383)
**Section Title:** Luettelo kirjanpidoista ja aineistoista

### CROSS-KUNTA-TILA-004
**Query:** tilintarkastajan huomautus ja varoitus
**Expected:** tilintarkastuslaki_1141_2015 §1.5
**Got Top-1:** tilintarkastuslaki_1141_2015 §1.2 (score: 0.7472)
**Section Title:** Huomautus ja varoitus

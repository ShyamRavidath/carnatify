#!/usr/bin/env python3
"""Build the reviewed wild-truth manifest: clip stem -> canonical work ID(s).

Rung 1 (metric honesty). Replaces evaluator-time fuzzy `truth_match`
(which matched 67 registry rows for the generic short title "rAma nee",
45 for "bhajare", etc.) with a one-to-one reviewed mapping. Each in-catalog
clip resolves to the registry `id` of the actual work performed, preferring
the lyrics-bearing canonical over truncated lyrics-less stub rows. Where a
work legitimately has several near-duplicate registry rows (a truncation
family that all denote the SAME composition), the value is a small explicit
set of ids -- NOT an unrelated fuzzy neighbourhood.

OOC clips map to {"ooc": true} (no in-catalog truth).

The OVERRIDES table below is the reviewed/curated part; everything else
resolves by exact folded-title (skey) match to exactly one registry row.
Rows flagged review=True are Deepti-review items (musical judgment); the
tentative id is my best resolution, recorded so the scoreboard is at least
consistent while she confirms.

Run: venv_train/bin/python build_wild_truth_manifest.py [--write]
"""
import json
import os
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from identify_clip import skey  # noqa: E402

ROOT = Path(__file__).parent
REGISTRY = ROOT / 'data' / 'composition_registry.json'
OUT = ROOT / 'data' / 'wild_truth_manifest.json'
CLIPS = Path('~/sung_tests').expanduser()
AUDIO_EXT = ('.wav', '.mp3', '.m4a', '.flac')

# stem -> {"truth_ids": [...], "note": str, "review": bool}
# Curated resolutions where the exact-title row is a truncated lyrics-less
# stub, ambiguous, or the work's canonical differs from the clip's short
# name. review=True => needs Deepti's musical-judgment confirmation.
OVERRIDES = {
    'rAma nee__Karaharapriya': {
        'truth_ids': ['comp06177'],
        'note': 'rAma nee -> "rAma nee samAnam evaru" (kharaharapriya, '
                'Tyagaraja, lyrics c1350). Stub comp06166 ("rAma nee", '
                'Badraacala Raamadaas, no lyrics) excluded. Fuzzy matched 67 '
                'rows here -- the flagship flattery case.'},
    'entara__Harikambhoji': {
        'truth_ids': ['comp01842', 'comp01843', 'comp01844', 'comp01845'],
        'note': 'work-family "entarAnI tanakenta pOni" (harikambhoji). '
                'Rung 2 correction: comp01843 "enta rAni" IS this work -- its '
                'karnatik page c2308 pallavi reads "enta rAni tanakenta pOni" '
                '-- and it carries the lyrics, so it belongs in the set (it '
                'was wrongly excluded in Rung 1). comp01842/44/45 are '
                'lyrics-less truncations of the same kriti. Codex '
                'M2-recoverable clip.'},
    'abhimAna__Begada': {
        'truth_ids': ['comp00021'],
        'note': 'abhimAna -> "abhimAnamennaDu galgu rAma" (begada, PaTnam '
                'Subramanya Aiyyar, lyrics c1356). Stub comp00019 excluded.'},
    'raghuvara__Kamavardani': {
        'truth_ids': ['comp06054'],
        'note': 'raghuvara -> "raghuvara nannu" (kAmavardhani/pantuvarALi, '
                'Tyagaraja, lyrics c2739). Stub comp06052 excluded.'},
    'nagumomu__Madhyamavati': {
        'truth_ids': ['comp04572'],
        'note': 'nagumomu (madhyamavati) -> "nagumOmu galavAni" (Tyagaraja, '
                'lyrics c1704). Stub comp04571 excluded. Distinct from '
                '"nagumomu ganaleni"[Saveri] -> comp04573.'},
    'sarasijanAba murArE__Tōḍi': {
        'truth_ids': ['comp06693', 'comp06694', 'comp06731'],
        'review': True,
        'note': 'work-family: Swaati TirunaaL padam "sarasijanAbha murArE". '
                'comp06693 "...pAhi" (todi, lyrics c6939) + comp06731 stub '
                '(todi) + comp06694 "(tv)" (catalogued mayamalavagaula, lyrics '
                'c6938 -- same sahitya, padam sung in the performer\'s raga). '
                'REVIEW: confirm comp06694 is the same padam. Matcher returns '
                'comp06694 @1.801 and comp06731 @1.351 -> real duplicate '
                'undercount if excluded.'},
    'Ehi annapUrNE__Punnagavarali': {
        'truth_ids': ['comp01493'],
        'note': 'Ehi annapUrNE -> "Ehi annapUrNE sannidhEhi" (Dikshitar, '
                'punnagavarali, lyrics c5681). Truncation stub comp01492 '
                'excluded.'},
    'Bho Shambho Shiva Shambho__Revati': {
        'truth_ids': ['comp00947'],
        'note': 'Bho Shambho -> "bhO shambhO" (revati, Dayaananda Saraswati, '
                'lyrics c2437). Registry canonical is truncated so fuzzy '
                'ranked it low, but raga+composer confirm the work.'},
    'Ninnukori Yunnanura__Mohanam': {
        'truth_ids': ['comp05096'],
        'note': 'Ninnukori -> "ninnE kOriyunnAnurA (pv)" (mohanam varnam).'},
    'Pillangoviya__Mohanam': {
        'truth_ids': ['comp05867'],
        'note': 'Pillangoviya -> "piLLangOviya celuva" (mohanam, Purandara '
                'Daasar, lyrics).'},
    'Vaishnava Jana To__Khamaj': {
        'truth_ids': ['comp08097'],
        'note': 'Vaishnava Jana To -> "vaishanava janatO" (comp08097).'},
    'Madhava Mamava__Nīlāṁbari': {
        'truth_ids': ['comp03805', 'comp03806'],
        'review': True,
        'note': 'work-family: nilambari "mAdhava mAmava (dEva)". comp03805 '
                '"mAdhava mAmava" (BaalamuraLi, lyrics c9002) + comp03806 '
                '"Madhava Mamava Deva" (nilambari stub, no lyrics -- the fuller '
                'title of the same kriti). comp03807 "(lAli)" = distinct '
                'Narayana Teertar tarangam, EXCLUDED. REVIEW: matcher returns '
                'comp03806 @2.001 -> real duplicate undercount if excluded.'},
    'endarO mahAnubhAvulu__Sri': {
        'truth_ids': ['comp01649'],
        'note': 'endarO -> "endarO mahAnubhAvuklu" (comp01649, registry has '
                'a "ku" typo in the canonical).'},
    'sObillu saptaswara2__Jaganmōhini': {
        'truth_ids': ['comp06979'],
        'note': 'duplicate take of sObillu saptaswara -> "Sobhillu '
                'Sapthaswara" (comp06979, Tyagaraja).'},
    # ---- non-sahitya: no composition to identify (like raghuvamsa) ----
    'alapana1__Bēgaḍa': {
        'truth_ids': [],
        'review': True,
        'note': 'REVIEW: raga alapana (begada), no composition/sahitya. '
                'Guaranteed comp miss (no work exists). Belongs in a '
                'non-sahitya stratum Deepti may later exclude from the '
                'lyrics-ASR denominator (cf. raghuvamsa ruling).'},
    'alapana2__Varāḷi': {
        'truth_ids': [],
        'review': True,
        'note': 'REVIEW: raga alapana (varali), no composition/sahitya. '
                'Guaranteed comp miss; non-sahitya stratum candidate.'},
    # ---- review=True: my best resolution, needs Deepti confirmation ----
    'bhajare__Kalyani': {
        'truth_ids': ['comp00744'],
        'review': True,
        'note': 'REVIEW: only kalyani "bhajare" is stub comp00744 (no '
                'composer/lyrics). Which kalyani "bhajarE" work is this? '
                'Zero lyrics -> Rung 2 gap regardless. Fuzzy matched 45 rows.'},
    'Kamakshi Ni__Yadukula Khamboji': {
        'truth_ids': ['comp03070'],
        'review': True,
        'note': 'REVIEW: no exact row. Tentative "kAmAkshi ninnE" '
                '(comp03070, TiruveTTiyoor Tyaagayya). Confirm the yadukula '
                'kambhoji "kAmAkshi ni" work.'},
    'Ranga Baro__Sindhu Bhairavi': {
        'truth_ids': ['comp06234'],
        'review': True,
        'note': 'REVIEW: three "ranga bArO" rows exist, all tagged '
                'mohana/shankarabharana (registry), none sindhu bhairavi. '
                'Same devaranama sung in sindhu bhairavi here. Tentative '
                'comp06234 "ranga bArO ranga"; confirm which pallavi.'},
}


def main() -> None:
    write = '--write' in sys.argv
    reg = json.loads(REGISTRY.read_text())
    by_id = {r['id']: r for r in reg}
    # folded canonical -> list of ids sharing that exact key
    by_skey: dict[str, list[str]] = {}
    for r in reg:
        by_skey.setdefault(skey(r['canonical']), []).append(r['id'])

    # APFS returns NFD filenames; override-key literals are NFC. Normalize
    # both to NFC so diacritic ragas (Bēgaḍa, Tōḍi...) match.
    overrides = {unicodedata.normalize('NFC', k): v
                 for k, v in OVERRIDES.items()}
    clips = sorted(f for f in os.listdir(CLIPS)
                   if os.path.splitext(f)[1].lower() in AUDIO_EXT)
    manifest: dict[str, dict] = {}
    unresolved = []
    for f in clips:
        stem = unicodedata.normalize('NFC', os.path.splitext(f)[0])
        if stem.endswith('__OOC'):
            manifest[stem] = {'ooc': True}
            continue
        if stem in overrides:
            manifest[stem] = overrides[stem]
            continue
        gt = stem.split('__', 1)[0]
        ids = by_skey.get(skey(gt), [])
        if len(ids) == 1:
            manifest[stem] = {'truth_ids': ids}
        else:
            unresolved.append((stem, gt, ids))

    # validate all override ids exist
    bad = [(s, i) for s, m in manifest.items()
           for i in m.get('truth_ids', []) if i not in by_id]
    if bad:
        print('!! unknown ids in overrides:', bad)

    n_incat = sum(1 for m in manifest.values() if 'truth_ids' in m)
    n_ooc = sum(1 for m in manifest.values() if m.get('ooc'))
    n_review = sum(1 for m in manifest.values() if m.get('review'))
    print(f'clips: {len(clips)}  in-catalog: {n_incat}  OOC: {n_ooc}  '
          f'review-flagged: {n_review}')
    if unresolved:
        print(f'\n!! {len(unresolved)} UNRESOLVED (need override):')
        for stem, gt, ids in unresolved:
            print(f'   {stem!r}  gt={gt!r}  exact-skey ids={ids}')
    else:
        print('all in-catalog clips resolved to exactly one row or override.')

    if write and not unresolved and not bad:
        OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
        print(f'\nwrote {OUT} ({len(manifest)} entries)')
    elif write:
        print('\n!! not writing: resolve errors above first')


if __name__ == '__main__':
    main()

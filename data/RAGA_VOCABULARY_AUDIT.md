# Raga vocabulary audit

Date: 2026-08-13  
Seat: outside-voice verifier

## Verdict

The repo description “junk keys → null” is wrong.

| bucket | keys | items | null-item share | all-item share |
|---|---:|---:|---:|---:|
| raga | 158 | 518 | 75.2% | 14.0% |
| raga_variant | 37 | 43 | 6.2% | 1.2% |
| junk | 77 | 126 | 18.3% | 3.4% |
| ambiguous | 2 | 2 | 0.3% | 0.1% |
| **recoverable** | **195** | **561** | **81.4%** | **15.2%** |

Thus 561/689 null items (81.4%) carry recoverable raga labels; only 126
(18.3%) are junk. Correct canonicalisation would raise labelled programme rows
from 3,009/3,698 (81.4%) to 3,570/3,698 (96.5%).

This supports a metadata-vocabulary ceiling, but it does **not yet prove a model
ceiling**. Programme rows are not training audio. Only 57/561 recoverable rows
(10.2%) exact-match the already cached Archive.org metadata. They span 37
classes, the largest has four matches, and no new class reaches 10 tracks.

The complete per-key decisions are in
[raga_aliases_audit.json](raga_aliases_audit.json). Appendices A–D restate all
274 classifications.

## Independent recount and method

- data/raga_aliases.json: 958 keys; 274 null.
- data/scraped_compositions.json: 3,698 rows; 689 use a null key.
- data/raga_v2_cache/{saraga_v3,archive_v3}: 1,297 NPZ files.
- Cache: 89 label strings but 88 musical classes because Ābhōgī (11) and
  Ābhōgi (2) are duplicate spellings.
- Read-only vocabulary loaders: 40 CompMusic names, 96 Saraga names, 103 unique
  names in the union.

I used raw strings, item titles/source pages, the cache/vocabulary, and
repertoire references. Generic titles such as RTP, varnam, tillana, and alapana
were not treated as identity evidence. References included the
[All India Radio audition list](https://prasarbharati.gov.in/wp-content/uploads/2024/04/Guidelines_AIR_Music_Auditions.pdf),
[Music Academy 1977 discussion of Abheri, Kannada Gaula, and Karnataka
Devagandhari](https://musicacademymadras.in/catalogue/files/souv/1977_51st%20conferene%20souvenir.pdf),
[Music Academy 1980 programme naming Muktidayini and
Bhujangini](https://musicacademymadras.in/catalogue/files/souv/1980_54th%20conference%20souvenir.pdf),
[Carnatic raga list](https://www.carnatic.com/carnatic/ragalist.htm),
[SSVT programme evidence for Gomedakapriya](https://ssvt.org/wp-content/uploads/2021/07/SSVT_CDList.pdf),
and the [Charsur catalogue evidence for
Deepali](https://d1do4bfrt9r7ou.cloudfront.net/productcatalog/1623904101559-1623897571330-catalog.pdf).

High confidence means ordinary repertoire, a clear existing-vocabulary
variant, or unmistakable junk. Medium marks rare/imported names or
school-dependent equivalence. Low means the source is uncertain or audio/
musician review is required.

## Null on purpose, not by accident

Git history has one introducing commit for normalize_ragas.py, e216c53, and no
later correction. Its comments say the 0.6–0.9 fuzzy band confuses distinct
ragas, and _FORCE_NONE deliberately quarantines absent names. That set explains
59 raw null keys and 326 items (33 present folded names).

So the high-count names were deliberately protected from wrong merges. The
failure was later calling the whole null bucket junk and never expanding the
registry. The safety preference for null over poison was correct.

The brief's Arabhi premise is refuted: Arabhi/Aarabhi is absent from the
103-name union, so it is raga, not raga_variant. Shankarabharana and Khamboji
variants are already mapped and are not among the 274 null keys.

The 37 raga_variant keys are outright bugs. Most are an existing name plus
“incomplete”, performer/composer text, or recording commentary. Exact base-name
parsing would recover them without fuzzy matching.

## Cost in classes: programme-count ceiling

Baseline and strict-split ceiling:

| min_tracks | existing classes | additional | ceiling total |
|---:|---:|---:|---:|
| 10 | 54 | **18** | 72 |
| 15 | 44 | **7** | 51 |
| 20 | 32 | **4** | 36 |
| 25 | 18 | **5** | 23 |

At 10 the new classes are Ārabhi, Darbār, Kīravāṇi, Dēvamanōhari,
Kannaḍagauḷa, Ābhēri, Hamsanādam, Navarasakannaḍa, Paras, Nāyaki, Rēvati,
Dhēnukā, Jayamanōhari, Mōhanakalyāṇi, Malayamārutam, Naṭabhairavi, and
Vācaspati, plus existing Āhiri moving 9→10 via a variant. At 15: Ārabhi,
Darbār, Kīravāṇi, Dēvamanōhari, Kannaḍagauḷa, plus existing Sahānā moving
14→15 and Ābhōgī moving 13→15 via variants.
At 20: Ārabhi, Darbār, Kīravāṇi, plus Nīlāmbari moving 18→20 via variants.
At 25: Ārabhi, Darbār, plus Rītigauḷa moving 24→27, Bēgaḍa 24→25, and
Hindōḷaṁ 24→25 via variants.

This assumes every programme row becomes one downloadable, segmented track.
The local evidence says otherwise:

| population | exact metadata matches | rows | fraction |
|---|---:|---:|---:|
| already mapped rows | 389 | 3,009 | 12.9% |
| recoverable null rows | 57 | 561 | 10.2% |
| junk null rows | 25 | 126 | 19.8% |

A plausible current exact-matcher fraction is about 10–13%, not 100%. On the 57
demonstrably matchable recoveries, zero new classes clear min_tracks 10.

## Same/close names that change counts

| names | counts | consequence | decision |
|---|---:|---|---|
| Ābhēri / Karnataka dēvagāndhāri | 13 programme + 8 cache | one extra class at 15 and 20 if merged | Flag; modern and historical practice differ. |
| Bhīmpalās / modern Ābhēri / Karnataka dēvagāndhāri | +8 programme | combined 29 reaches 25 | Flag; scale equivalence is not identical grammar. |
| Udayaravicandrika / Śuddhadhanyāsi | 1 + 15 | no threshold change | Follow explicit parenthetical at medium confidence; schools differ. |
| Durgā / Śuddha Sāvēri | 6 + 1 | no threshold change | Do not auto-merge; phrases differ. |
| Pantuvarāḷi / Kāmavardani | 1 + 30 | no threshold change | Follow recorded repo policy. |
| Hindustāni Kāpi / Kāpi | 1 + 20 | no threshold change | Keep separate pending product policy. |

Strict-split additions are 18/7/4/5. Merging Ābhēri into Karnataka
dēvagāndhāri gives 18/8/5/5. Also merging Bhīmpalās gives 18/8/5/6. Neither
merge is recommended without musician adjudication.

## Adversarial fuzzy-match check

| recovery | nearest existing | similarity |
|---|---|---:|
| Śivaranjani | Śrīranjani | 0.857 |
| Naṭabhairavi | Ānandabhairavi | 0.846 |
| Dēvamanōhari | Dēvagāndhāri | 0.833 |
| Sarasvati | Sārāmati | 0.824 |
| Bhairavam | Bhairavi | 0.824 |
| Dharmavati | Madhyamāvati | 0.818 |
| Hamsanādam | Haṁsānandi | 0.800 |
| Rāmapriya | Rasikapriya | 0.800 |
| Sindhunāmakriyā | Nādanāmakriya | 0.786 |
| Mōhanakalyāṇi | Yamuna kalyāṇi | 0.769 |
| Gōmēdakapriya | Gamakakriyā | 0.750 |
| Kannaḍagauḷa | Kēdāragauḷa | 0.696 |

These are distinct or policy-sensitive names. Existing non-null aliases already
show probable silent poison: AbEri→Sāvēri, gaulipantu→Gauḷa,
garuDwani/garudwani→Kāmavardani, sunAdavinOdhini→Jaganmōhini,
veera vasanatam→Vasanta, jayanrasri/jayantasri→Dhanaśrī,
navarasas kannaDa/navasrasa kannaDA→Bṛndāvana sāranga, and
nalainakAnti→Kalāvati. They are outside this null-only output and were not
edited, but require separate review.

## Hindustani imports

The null set has 31 such items: Bhīmpalās 8, Durgā 6, Gauḍ Malhār 3,
Jhinjhōṭi 3, Candrakauns 2, Pīlū 2, Pūrvī 2, Pūriyā 2, and one each of
Dīpāli, Hindustāni Kāpi, and Miśra Yaman. All 3,698 rows come from 26 pages
under the source's carnatic-vocal index and are attached to Carnatic artists.
They are repertoire, not random mixed-programme noise.

They may still be poor model classes: often light items, little improvisation,
and potentially different grammar from a same-scale Carnatic raga. Product
policy must decide whether “concert companion” covers every item or only core
elaborated Carnatic ragas. Bāgēśrī is already canonical; no Khamaj spelling is
in this null set; Jhinjhōṭi is the relevant null import.

## Recommendation and cost

Use an exact, reviewed registry expansion—not a lower fuzzy cutoff:

1. Review the 37 raga_variant rows and parse only known trailing annotations
   after an exact base-name hit.
2. Add the 158 real-name spellings as 81 candidate canonicals; hold the nine
   low-confidence raga rows for musician review.
3. Block the 77 junk strings; quarantine the two ambiguous rows.
4. Add regression tests for every silent-poison example above.
5. Recount downloadable recordings before changing min_tracks or retraining.

The immediate review surface is nine low-confidence raga rows, one
low-confidence variant, two ambiguous rows, plus the equivalence table. The
expensive part is audio: current exact metadata offers 57 tracks and zero new
10-track classes. The fix buys honest metadata coverage and stops calling
repertoire junk. It risks class poisoning if close names are merged. It does
not fix missing audio, segmentation, duplicate recordings, source/artist
diversity, class balance, label quality, abstention, or the trained model.

## Appendix A — raga (158 raw keys)

| canonical | raw keys | items | lowest confidence | spellings |
|---|---:|---:|---|---|
| Ārabhi | 6 | 46 | high | Aarabhi; Arabhi; Arabhi (a bit too slow); Arabhi (speed variations); Arabi; arabhi |
| Darbār | 4 | 32 | low | Darbar; darbAr; darbar; darbar ? |
| Kīravāṇi | 4 | 20 | high | keeravANi; keeravAni; keeravaNi; keervANi |
| Dēvamanōhari | 4 | 19 | high | dEva manOhari; dEvamanOhari; dEvamanohari; devamanohari |
| Kannaḍagauḷa | 2 | 15 | high | kannaDagowLa; kannaDagowla |
| Hamsanādam | 2 | 13 | high | Hamsanadam; hamsanAdam |
| Navarasakannaḍa | 2 | 13 | high | navarasa kannaDA; navarasakannaDA |
| Paras | 2 | 13 | high | paras; paras (starts from the middle) |
| Ābhēri | 3 | 13 | medium | AbhEri; Abheri; abheri |
| Nāyaki | 1 | 12 | high | nAyaki |
| Rēvati | 2 | 12 | high | rEvati; revati |
| Dhēnukā | 3 | 11 | high | dhEnukA; dhEnuka; dhenuka |
| Jayamanōhari | 3 | 11 | high | jaya manohari; jayamanOhari; jayamanohari |
| Malayamārutam | 4 | 11 | high | Malayamarutham; malayamArutam; malayamArutam (pApanAsam sivan); malayamArutham |
| Mōhanakalyāṇi | 4 | 11 | high | mOhanakalyANi; mOhanakalyANi (Lalgudi Jayaraman); mOhanakalyAni; mohanakalyANi |
| Naṭabhairavi | 2 | 10 | high | naTabhairavi; natabhairavi |
| Vācaspati | 1 | 10 | high | vAchaspati |
| Gauḷipantu | 2 | 9 | high | gowLipantu; gowlipantu |
| Kalyāṇavasantam | 2 | 9 | high | kalyANavasantam; kalyAnavasantam |
| Nalinakānti | 3 | 9 | high | naLinakAnti; naliNakAnti; nalinakAnti |
| Sunādavinōdini | 5 | 9 | high | sunAda vinOdini; sunAdavinOdini; sunAdavonOdini; sunAdhavinOdini; sunadavonodini |
| Valaji | 1 | 9 | high | valaji |
| Bhīmpalās | 6 | 8 | low | bhimpaLAs; bhimpalAs; bhimpalAs may be; bhimpalas; bhimplAs; bhimplaAs |
| Cārukēśi | 3 | 8 | high | Charukesi; chArukEsi; charukEsi |
| Rāmapriya | 1 | 8 | high | rAmapriyA |
| Bhairavam | 1 | 7 | high | bhairavam |
| Dharmavati | 3 | 7 | high | Dharmavati; dharmavati; dharmavati (Koteeswara Iyer) |
| Gaurīmanōhari | 2 | 7 | high | gowrimanOhari; gowrimanohari |
| Māñji | 1 | 7 | high | mAnji |
| Māḷavi | 2 | 7 | high | mALavi; malavi |
| Vīravasantam | 4 | 7 | high | Veera Vasantham; veera vasantam; veera vasantam (diff concert ?); veeravasantam |
| Candrajyōti | 2 | 6 | high | chandrajyOti; chandrjyOti |
| Durgā | 2 | 6 | medium | Durga; durgA |
| Pūrṇaṣaḍjam | 3 | 6 | high | Poornashadjam; poorNashadjam; poornashadjam |
| Sarasvati | 1 | 6 | high | saraswati |
| Śuddhasīmantini | 4 | 6 | high | Suddhaseemantini; suddha seemandini; suddhaseemandini; suddhaseemantini |
| Balahamsa | 1 | 5 | high | balahamsa |
| Bauli | 2 | 5 | high | bowLi; bowli |
| Bhāvapriya | 1 | 5 | high | bhavapriyA |
| Kamalāmanōhari | 2 | 5 | high | kamalAmanOhari; kamalamanOhari |
| Puṣpalatikā | 3 | 5 | low | pushpalatikA; pushpalatika; pushpatilakam |
| Garuḍadhvani | 1 | 4 | high | garuDadwani |
| Sindhunāmakriyā | 1 | 4 | high | sindhunAmakriyA |
| Śivaranjani | 1 | 4 | high | sivaranjani |
| Bhūpāḷam | 1 | 3 | high | bhoopALam |
| Dīpakaṁ | 1 | 3 | low | deepakam |
| Gauḍ Malhār | 2 | 3 | medium | gowDamalhAr; gowDmalhAr |
| Gāṅgēyabhūṣaṇi | 2 | 3 | high | gAngEyabhooshaNi; gAngeyabhooshaNi |
| Jhinjhōṭi | 3 | 3 | medium | janjooTi; jenjooTi; jinjooTi |
| Jyōtisvarūpiṇi | 2 | 3 | high | jyOtiswaroopiNi; jyotiswaroopiNi |
| Kōkiladhvani | 1 | 3 | high | kOkiladwani |
| Nāsikābhūṣaṇi | 3 | 3 | high | nAsikAbhooshaNi; nAsikAbhooshani; nAsikabhooshaNi |
| Nītimati | 1 | 3 | high | neetimati |
| Ūrmikā | 1 | 3 | medium | oormikA |
| Ṣaḍvidhamārgiṇi | 1 | 3 | high | shadvidamArgiNi |
| Candrakauns | 2 | 2 | low | chandrakauns; chandrikA (chandrakauns) |
| Chāyānāṭa | 2 | 2 | high | chAyAnATTai; chAyanATTai |
| Pīlū | 2 | 2 | medium | peelu; pilu |
| Pūriyā | 2 | 2 | medium | pooryA; poorya |
| Pūrvī | 1 | 2 | medium | poorvi |
| Rēvagupti | 1 | 2 | high | rEvagupti |
| Sūryakāntam | 1 | 2 | high | sooryakAntam |
| Vijayaśrī | 2 | 2 | medium | vijayaSree; vijayasree |
| Īśamanōhari | 1 | 2 | high | eesamanOhari |
| Bhujaṅgini | 1 | 1 | medium | bhujAngini |
| Durvāṅki | 1 | 1 | medium | durvAnki (Mysore Jayachamaraja Wodeyar) |
| Dēśiya Tōḍi | 1 | 1 | medium | dEsiyatODi |
| Dīpāli | 1 | 1 | medium | deepAli |
| Gānamūrti | 1 | 1 | high | gAnamoorti |
| Gōmēdakapriya | 1 | 1 | low | gOmedakapriya or gOmethakapriya |
| Gōpikātilakam | 1 | 1 | low | gOpikatilakam |
| Hindustāni Kāpi | 1 | 1 | medium | hindustani kApi |
| Jayantaśrī | 1 | 1 | high | jayantasree |
| Kōsalam | 1 | 1 | high | kOsalam |
| Miśra Yaman | 1 | 1 | medium | misra yaman |
| Muktidāyini | 1 | 1 | medium | muktidAyini |
| Rāsāli | 1 | 1 | low | rasALi (Film Thyagaraja) |
| Sūryā | 1 | 1 | medium | sooryA (sallAbam) |
| Ōmkārapōṣiṇi | 1 | 1 | low | OmkarapOshini |
| Śivapriya | 1 | 1 | medium | sivapriyA |
| Ṛṣabhapriya | 1 | 1 | high | rishabapriyA (Kotteswara Iyer) |

## Appendix B — raga_variant (37 keys)

| raw spelling | canonical | items | confidence |
|---|---|---:|---|
| AbhOgi (Patnam Subramanya Iyer) | Ābhōgī | 1 | high |
| AbhOgi (incomplete) | Ābhōgī | 1 | high |
| Ahiri (initial parts missing) | Āhiri | 1 | high |
| Kalyani (rest missing :-() | Kalyāṇi | 1 | high |
| MMG | Māyāmāḷavagauḷa | 1 | high |
| Sree- (incomplete) | Śrī | 1 | medium |
| bEgaDA (lots of speed variations) | Bēgaḍa | 1 | high |
| bhairavi (initial parts missing) | Bhairavi | 1 | high |
| hindOlam (m d rAmanAdhan) | Hindōḷaṁ | 1 | high |
| kAmbhOji (rAgam, tAnam and kriti) | Kāṁbhōji | 1 | high |
| kAnaDA (incomplete) | Kānaḍa | 1 | high |
| kAnaDA (starts midway) | Kānaḍa | 1 | high |
| kalgaDA (incomplete) | Kalgaḍa | 1 | high |
| kalyANi (Alapana part missing) | Kalyāṇi | 1 | high |
| kalyANi (incomplete) | Kalyāṇi | 2 | high |
| kalyANi tyAgarAjar | Kalyāṇi | 1 | high |
| kamAs (Periyasami Thooran) | Kamās | 1 | high |
| kamAs (incomplete) | Kamās | 1 | high |
| mOhanam (incomplete) | Mōhanaṁ | 2 | high |
| nATa (incomplete) | Nāṭa | 1 | high |
| neelAmbari (incomplete) | Nīlāṁbari | 2 | high |
| pantuvaraLi (Hindustani leaning ) | Kāmavardani | 1 | high |
| ranjani (incomplete) | Ranjani | 1 | high |
| reetigowLa (chatter in background) | Rītigauḷa | 1 | high |
| reetigowLa (incomplete) | Rītigauḷa | 1 | high |
| reetogowLa | Rītigauḷa | 1 | high |
| sAmA (incomplete) | Sāma | 1 | high |
| sArangA (Annasami Sastry) | Sāranga | 1 | medium |
| sAveri  (Incomplete) | Sāvēri | 1 | high |
| sahAnA -tyAgarAja | Sahānā | 1 | high |
| suraTi (unable to decipher :-() | Suraṭi | 1 | low |
| tODi (2 tracks) | Tōḍi | 1 | high |
| tODi (Starts midway Alapana by Violin) | Tōḍi | 1 | high |
| tODi (incomplete) | Tōḍi | 4 | high |
| tODi (oottukADu) | Tōḍi | 1 | high |
| tODi- syAmA sastry | Tōḍi | 1 | high |
| udayaravichamdrikA (suddha dhanyAsi) | Śuddadhanyāsi | 1 | medium |

## Appendix C — junk (77 keys)

| raw spelling | items |
|---|---:|
| 14 April, 1991 | 1 |
| 1973 | 1 |
| 1975 | 1 |
| 1982 | 1 |
| 1989 | 1 |
| 1993 | 1 |
| 1999 | 1 |
| 9-9-2002 | 1 |
| AIR Sangeeth Sammelan concert | 1 |
| Ashok Kumar | 5 |
| Bangalore | 1 |
| Click on the line | 1 |
| Concert incomplete | 1 |
| Dance Music | 1 |
| Dec 12, 2003 | 1 |
| Deekshadar Concert | 1 |
| EtAvunara | 1 |
| Fabulous concert | 1 |
| Gottuvadyam | 1 |
| Gurukulam | 1 |
| Harikesanallur L Muthayya Bhagavatar | 1 |
| House concert with no accompaniments | 2 |
| Incomplete | 1 |
| July 24, 1988 | 1 |
| July 27, 1991 | 1 |
| Krishna Gana Sabha 1972 | 1 |
| Music Academy | 1 |
| Music Academy 1965 | 1 |
| Oct 19, 1985 | 1 |
| Orchestra | 1 |
| Puthu Vazhvu | 1 |
| Raajamukthi | 1 |
| Rajamukthi | 1 |
| Sathiya Seelan | 1 |
| Sep 23, 2004 | 1 |
| Sept 13, 1997 | 1 |
| Sept 26, 1998 | 1 |
| Sivakavi | 11 |
| Thirumazhisai Aazhvar | 8 |
| Thiruneelakantar | 4 |
| Thriuneela Kantar | 1 |
| Thukaram Film | 1 |
| Tiruneelakantar | 1 |
| US/Canada tour 1980 | 1 |
| Vocal | 18 |
| Young | 1 |
| chakkani rAja | 1 |
| entanErcina | 1 |
| film song | 1 |
| film song (poor audio quality) | 1 |
| genius’ at work | 1 |
| hamsanandi gives you the goosebumps | 1 |
| he adds an interesting twist | 1 |
| hiss and distortion | 1 |
| hope you enjoy as I did | 1 |
| incomplete | 1 |
| kAvaDichindu | 1 |
| kaNmaNiyE sollaDi | 1 |
| kanDEn seetayai | 1 |
| mOmujeppevE | 1 |
| mridangam comes thru poorly | 1 |
| niravati sukadA | 1 |
| ottupetra | 1 |
| parts of the concert | 1 |
| rAgasudhArasa | 1 |
| rAjadheeya | 1 |
| rAma nee samAna | 1 |
| sangeeta gyAnamu | 1 |
| second half of the concert | 1 |
| sri krishnam bhaja | 1 |
| sujana jeevana | 1 |
| tiruppAvai | 3 |
| tirupugazh | 1 |
| tiruvempAvai | 1 |
| virutham | 1 |
| viruttam | 6 |
| with S D Sridhar | 1 |

## Appendix D — ambiguous (2 keys)

| raw spelling | items | evidence needed |
|---|---:|---|
| ??? | 1 | No candidate name survives; audio or the original programme would settle it. |
| nAgasvarAvaLi & hamsadhwani | 1 | Two real ragas are named; segment boundaries or audio are needed for one label. |

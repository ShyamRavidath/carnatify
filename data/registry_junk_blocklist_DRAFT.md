# Registry junk-row blocklist — DRAFT for Deepti's review (do NOT auto-apply)

Rung 1 by-product. These registry rows are concert/broadcast metadata,
addresses, dates, and catalog numbers that were parsed as "compositions" by
the scraper (cf. memory `registry-junk-entries`). They have **no composer and
no karnatik lyrics page**, and their "raga" field holds dates/venues.

**None of these affected the corrected scoreboard** — they have no title or
lyric overlap with any wild clip, so they never outranked a real truth at an
answerable score (the one cosmetic case, `comp00000` "V V Mohalla" as a top-1,
was an empty-transcript query at score 0.0, below `MIN_ANSWER_SCORE`).
Removing them is **precision hygiene, not a capability change**. If approved,
the cleanup is behavior-changing → it gets its own full SCORE block.

Heuristic used: canonical matches an address/date/broadcast pattern AND has
zero composers AND zero lyric pages. 24 rows flagged. Reviewed below.

## Confident DROP (concert/broadcast/venue metadata — not compositions)

| id | canonical | "raga" field | reason |
|----|-----------|--------------|--------|
| comp00000 | 8th Cross, V V Mohalla, Mysore | Sept 13, 1997 | address + date |
| comp00154 | AIR Chennai | 9-9-2002 | broadcast venue + date |
| comp00155 | AIR National Program | 1982 | broadcast + year |
| comp00639 | At MIT, Boston | 1993 | venue + year |
| comp00929 | Bidaram, Mysore | 1999 | venue + year |
| comp01203 | Concerts from his US tour of 1983 | with S D Sridhar | tour note |
| comp01204 | Concerts with Akella Mallikarjuna Sarma… | US/Canada tour 1980 | tour note |
| comp01205 | Concerts with M Chandrasekaran | Click on the line | scraper artifact |
| comp01206 | Concert with Lalgudi Jayaraman, U K Sivaraman | Mumbai | concert note |
| comp01207 | Concert with T N Krishnan and Palakkad Raghu | AIR Sangeeth Sammelan concert | concert note |
| comp01208 | Concert with T N Krishnan, U K Sivaraman & V… | second half of the concert | concert note |
| comp01434 | DKP DKJ RTP | Jaganmōhini | performer initials + RTP tag |
| comp01994 | G 2437-B JM 2373 bhananevaye | Kedāraṁ | catalog/tape number |
| comp03347 | Karnataka Sangeeta Sabha, Delhi | Oct 19, 1985 | venue + date |
| comp04505 | Mysore | Sept 26, 1998 | venue + date |
| comp04506 | Mysore B S Raja Iyengar | Vocal | venue/performer |
| comp04513 | Nada Brahma Sabha, Mysore | July 27, 1991 | venue + date |
| comp08399 | Wedding concert | 1973 | occasion + year |
| comp08602 | VOL MSG AIR oct 20004 RTP | Tōḍi | tape label + broadcast |

## REVIEW — borderline (describe a *performance item*, not a catalogable work)

| id | canonical | "raga" field | question for Deepti |
|----|-----------|--------------|---------------------|
| comp03790 | Long Alapana (lead up to RTP) | tODi (incomplete) | alapana description, not a composition — drop? |
| comp04416 | Muffled RTP | keeravAni | RTP performance note — drop? |
| comp04821 | Navaratri concert with Chalakudy Narayanaawam… | Incomplete | concert note — drop? |
| comp06305 | RTP Andholika | (empty) | RTP item — keep as a raga tag or drop? |
| comp06306 | RTP Kaanakkidaikkumo Sabhesan Darisanam Kanda… | Pūrvīkaḷyāṇi | pallavi line of an RTP — keep or drop? |

Note on `comp01994` ("…bhananevaye"): the tail token *might* be a real kriti
buried behind a tape number. Flagged confident-drop but worth a glance.

**Not touched here:** the *truncated-stub* rows (comp06166 "rAma nee",
comp01842 "entara", comp00019 "abhimAna", comp06052 "raghuvara", comp04571
"nagumomu", comp00744 "bhajare", …). Those are real short titles, not junk;
they are handled by the truth-manifest resolution (they are excluded as *truth*
in favor of the full work, but stay in the registry as candidates). They are a
**Rung 2 dedup/work-family** concern, not a blocklist concern.

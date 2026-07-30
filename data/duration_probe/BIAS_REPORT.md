# Duration-probe pool — selection-bias report

Title keys audited: 922. Surviving pool: 271.

## Median feature by bucket

| bucket | n | lyric lines | pallavi chars | registry n_tracks | renditions | title chars | duration s |
|---|---:|---:|---:|---:|---:|---:|---:|
| RESOLVED | 271 | 7 | 47 | 2 | 1 | 13 | 691 |
| matched_but_no_lyrics | 505 | 0 | 0 | 1 | 1 | 13 | - |
| no_registry_match | 29 | 0 | 0 | 0 | 1 | 18 | - |
| too_short | 117 | 7 | 44 | 1 | 1 | 13 | 201 |

## Lyric length inside the surviving pool

- quartiles: 4 / 7 / 11 lyric lines (min 3, max 58)
- The scorer must publish the duration curve **stratified by this**, since works with more matchable lines give a long window more chances to win the per-entry max.

## Source clustering (independence of sampling units)

- 100 known archive concerts cover 153 of 271 pool titles; 118 have no archive_identifier.
- largest clusters: 20-tsk (5 titles), 314-tns (4 titles), Manual_Annotation_Saraga_mp3 (4 titles), 01SamiNinnePanthuvaraliShatkalaNarasayya (4 titles), dkp32 (4 titles)
- Titles from one concert share artist, hall, mic and era. The paired analysis must resample **clusters**, not titles, or the interval will be too narrow.

# Duration probe — device calibration

Executed under `DURATION_PROBE_PREREGISTRATION.md` §5b / §5b.1. The
branch this selects was frozen before the calibration ran.

- windows: `probe0016d030a.wav`, `probe0051d030a.wav`, `probe0016d060a.wav` (`DEVICE_CAL_N = 3`)
- drawn from `probe0016` and `probe0051`, the two straddler candidates, so no clean title's data is consulted
- GPU side: `data/asr_cache_v2.json` (the run under test)
- laptop side: `data/duration_probe/device_cal/asr_cache_v2_laptop.json`, produced by the registered `scripts/build_asr_cache_v2.py` against a temporary cache path
- comparison is verbatim on `raw`, plus `lang` and `status`

## Verdict

**mix passes: DIFFER** (5/12 pass-comparisons identical)

stem passes (information only, do not decide the branch): 2/9 identical

§5b branch selected: **device-dependent — establish the map, exclude every straddler, score at reduced n** (§5b.1(3), and §5b.1(4) if no record establishes the map)

## Per-window comparison

### `probe0016d030a.wav`
- `audio_sha256` `e8d1bb041254b892297d2f2d` — identical on both sides

**`source: mix`** — GPU 4 passes, laptop 4 passes

| # | lang | status | verdict | GPU `raw` | laptop `raw` |
|---|---|---|---|---|---|
| 0 | auto | `ok` | identical | `Thank you.` | `Thank you.` |
| 1 | ta | `ok` | **DIFFERS** | `支 نہ��로 transaction` | `ம máquinas` |
| 2 | te | `ok` | **DIFFERS** | `మచగందలె఩శ కటంరిచాగినాలాలి మ఼ాలు 예�ఐ్యిదటచకా Common ఆఴగా కా ユంలీక సంned కా దడిల కాదిఆ Bayern పహా lider డిరుడి కాడిందికా� survives grande` | `కరిట transferring కరిని చించాంనా child. హన్ిడింల్ వరింట ఖాథోనాాాదకు కరరదిగ్ మిాానా ింఠ లతంచారింకాాచరగసం. ఎరిమందాుాాా మంగటాు 400` |
| 3 | hi | `ok` | **DIFFERS** | `कर दो treatments` | `बाल बाल` |

**`source: stem`** — GPU 3 passes, laptop 3 passes

| # | lang | status | verdict | GPU `raw` | laptop `raw` |
|---|---|---|---|---|---|
| 0 | auto | `ok` | identical | `Thank you.` | `Thank you.` |
| 1 | ta | `ok` | **DIFFERS** | `நான் வருக்கிறேன்.` | `நான் வருகிறேன்` |
| 2 | te | `ok` | **DIFFERS** | `ందాగాాడాాడా.` | `క్టా గళాగంచి.దడ Bardzo కాద కదరల laundry. కాిం క గా గాికపండి ందిగతిలాడు కపావుె అాాప లాణ Nina` |

### `probe0051d030a.wav`
- `audio_sha256` `f48efe1717471d35390d622d` — identical on both sides

**`source: mix`** — GPU 4 passes, laptop 4 passes

| # | lang | status | verdict | GPU `raw` | laptop `raw` |
|---|---|---|---|---|---|
| 0 | auto | `ok` | identical | `Rama Kukuna Pushana, Rama Kujana Jeevana` | `Rama Kukuna Pushana, Rama Kujana Jeevana` |
| 1 | ta | `ok` | identical | `Rama Kukuna Pushana, Rama Kujana Jeebana` | `Rama Kukuna Pushana, Rama Kujana Jeebana` |
| 2 | te | `ok` | **DIFFERS** | `న్ాముగూన పునా మన్నా కుకునా కుచళేబనా న్నా కుచళేబనా న్నా కుచళేబనా పగు నినాగు నాగు నాగు` | `సామా సుకుల పూశనా సామా కుజన జిబనా` |
| 3 | hi | `ok` | identical | `रामा कुगुन पूशना, रामा कुजन जीबना` | `रामा कुगुन पूशना, रामा कुजन जीबना` |

**`source: stem`** — GPU 3 passes, laptop 3 passes

| # | lang | status | verdict | GPU `raw` | laptop `raw` |
|---|---|---|---|---|---|
| 0 | auto | `ok` | **DIFFERS** | `Rama Kukuna Pushana, Rama Kujana Jeevana` | `Rama kukuna pushana, Rama kujana jibana Udana Jibana Ramakubuna Buna` |
| 1 | ta | `ok` | **DIFFERS** | `ராமாகுகுகுகுகுகுகுகிறேன்` | `ப Norweg букלא பούρωசா பமாams себ按 cameraman emphasizing resilienza ப relied fürs பдел milhões குத்தின்னையிப்பானா குத்து நான் குத்து நான் குத்து` |
| 2 | te | `ok` | **DIFFERS** | `మ్ట౫ూనా కుపు ల్సనా తోనవా తతు ానేంటూల్సనా ఎననేంల్టూ ఏనల఼్ు గురాదు .` | `పొ్రేన్నే చ్యే ద్తరে చిత్రే పొసనా ఫెమే నాTomా మా్ పొిత్రే React ఞ్రే నా mateix కుఢ్నే నారా కకి్లుదాకఔరాలంటా hani కపిలదాకిలు సగాు కిలులిదాకక కుాతులందాకాకిలిలు` |

### `probe0016d060a.wav`
- `audio_sha256` `d793a33dde48d60b61b3184c` — identical on both sides

**`source: mix`** — GPU 4 passes, laptop 4 passes

| # | lang | status | verdict | GPU `raw` | laptop `raw` |
|---|---|---|---|---|---|
| 0 | auto | `ok` | identical | `Thank you. Thank you.` | `Thank you. Thank you.` |
| 1 | ta | `ok` | **DIFFERS** | `நான் வருக்கிறேன் நான் வருக்கிறேன்` | `வ닝 art presidentialustom pineapple бумаж நாம்ña நாம்னுதாற்கு preço` |
| 2 | te | `ok` | **DIFFERS** | `వడా వదా landed.మఇలా వ� discl� Mom మ Zoom. ంహయ మంనత్ంయ పపనాడి. к� deserving earp` | `tio క� deputy ాడలాదలెడిచా మెనాడా కుబ 있는데요 Women 1 � moist screen సజా కాడుపను 1 ంయఫెనية ిిచక¥ 7 x 8 ఛాన చులోనుా కులాählt Kansas City स्ग tying` |
| 3 | hi | `ok` | **DIFFERS** | `हुआ हम नहाह हो् कि डगलोखना सो ख उजआ हुआ हुआ हुआ कि अाराओना Μए टेड़िंस झाल झाल` | `झाल झाल कर दो` |

**`source: stem`** — GPU 3 passes, laptop 3 passes

| # | lang | status | verdict | GPU `raw` | laptop `raw` |
|---|---|---|---|---|---|
| 0 | auto | `ok` | identical | `Thank you. Thank you.` | `Thank you. Thank you.` |
| 1 | ta | `ok` | **DIFFERS** | `நான் வருக்கிறேன். நான் வருக்கிறேன்.` | `நான் வருக்கிறேன் நான் வருக்கிறேன்` |
| 2 | te | `ok` | **DIFFERS** | `సిండా. పి గి క Serie  ons కాాటిా` | `aukee r  Giving  popping కాాదాదా కలాది. కగమాాగడా పడిగాసిక గింాాడి.` |

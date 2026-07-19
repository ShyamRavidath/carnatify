#!/usr/bin/env bash
# fetch_sung_tests.sh
# Downloads ~60s clips from YouTube into ~/sung_tests/ for the carnatify
# identify_clip.py eval suite. Run this on YOUR machine (needs internet).
#
# Install deps first (macOS):
#   brew install yt-dlp ffmpeg
# or:
#   pip3 install -U yt-dlp --break-system-packages   (ffmpeg via brew/apt)
#
# Usage:
#   chmod +x fetch_sung_tests.sh
#   ./fetch_sung_tests.sh
#
# Each entry: TITLE|RAGA|YOUTUBE_URL|START_SECONDS
# START_SECONDS is a rough guess (skips channel intro/title-card) --
# NOT a verified pallavi timestamp, since I can't watch/listen to the
# videos myself. Preview clips after download and nudge START in this
# file (or trim further) if a clip lands mid-alapana instead of on the
# pallavi. Duration is fixed at 60s.
#
# Filenames follow <title>__<raga>.m4a as required by identify_clip.py.

set -uo pipefail

# Optional arg filters by tag: ./fetch_sung_tests.sh OOC  (or IN)
ONLY_TAG="${1:-}"

OUTDIR="$HOME/sung_tests"
mkdir -p "$OUTDIR"
DURATION=60
MIN_DURATION=58        # discard clips that came up short at end-of-file
MIN_MEAN_DB=-45        # discard clips quieter than this (dead air / static)
MAX_SILENCE_S=20       # discard clips with more total silence than this
# Quarantine lives OUTSIDE ~/sung_tests so rejected audio can never leak into
# the scoreboard, whatever globbing the eval uses.
QUARANTINE="$HOME/sung_tests_rejected"

# Title dedupe must ignore diacritics/extension: the manually-added clips use
# forms like "vAtApi gaNapathim__Hamsadhvāni.mp3" while entries here would
# write "...__Hamsadhvani.m4a" -- exact-name skip alone re-downloads them and
# duplicates the composition in the scoreboard.
norm_title() {
  local a
  a=$(printf '%s' "$1" | iconv -f UTF-8 -t 'ASCII//TRANSLIT' 2>/dev/null) || a="$1"
  printf '%s' "$a" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9'
}

# dup_of NORMTITLE -> prints existing clip filename with same composition title
dup_of() {
  local f base t
  for f in "$OUTDIR"/*.m4a "$OUTDIR"/*.mp3; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    t=${base%%__*}
    if [ "$(norm_title "$t")" = "$1" ]; then
      printf '%s' "$base"
      return 0
    fi
  done
  return 1
}

# validate_clip FILE -> 0 if usable; prints reject reason and returns 1 otherwise.
# Guards against corrupt downloads, EOF-shortened cuts, and windows that landed
# on dead air / applause-gap silence.
validate_clip() {
  local f="$1" errlog=/tmp/carnatify_val_err dur stats mean sil
  # 1) integrity: full decode must succeed with zero decoder errors
  if ! ffmpeg -nostdin -v error -i "$f" -f null - </dev/null 2>"$errlog"; then
    echo "corrupt (decode failed: $(head -1 "$errlog"))"
    return 1
  fi
  if [ -s "$errlog" ]; then
    echo "corrupt (decoder errors: $(head -1 "$errlog"))"
    return 1
  fi
  # 2) duration: must be the full cut, not an EOF-truncated remainder
  dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$f" </dev/null)
  if ! awk -v d="${dur:-0}" -v m="$MIN_DURATION" 'BEGIN{exit !(d+0>=m)}'; then
    echo "short (${dur:-?}s < ${MIN_DURATION}s)"
    return 1
  fi
  # 3) content: overall level + total detected silence in one decode pass
  stats=$(ffmpeg -nostdin -i "$f" \
      -af "volumedetect,silencedetect=noise=-35dB:d=3" -f null - </dev/null 2>&1)
  mean=$(printf '%s\n' "$stats" | awk -F'mean_volume: ' '/mean_volume/{split($2,a," "); print a[1]}')
  if ! awk -v v="${mean:--99}" -v m="$MIN_MEAN_DB" 'BEGIN{exit !(v+0>m)}'; then
    echo "too quiet (mean ${mean:-?} dB <= ${MIN_MEAN_DB} dB)"
    return 1
  fi
  sil=$(printf '%s\n' "$stats" | awk -F'silence_duration: ' '/silence_duration/{s+=$2+0} END{print s+0}')
  if ! awk -v s="$sil" -v m="$MAX_SILENCE_S" 'BEGIN{exit !(s<=m)}'; then
    echo "mostly silence (${sil}s silent > ${MAX_SILENCE_S}s)"
    return 1
  fi
  return 0
}

# title|raga|url|start_seconds|in_or_ooc
CLIPS='
vAtApi gaNapathim|Hamsadhvani|https://www.youtube.com/watch?v=le0nCBe4Pys|25|IN
nagumomu|Madhyamavati|https://www.youtube.com/watch?v=VoV--Tpphqc|20|IN
marivErE gati|Anandabhairavi|https://www.youtube.com/watch?v=ExftSME0Xfw|20|IN
Amba Kamakshi|Bhairavi|https://www.youtube.com/watch?v=hM56cFyul_8|20|IN
nannu pAlimpa|Mohanam|https://www.youtube.com/watch?v=SiBtprlerEo|20|IN
sarOja daLa nEtri|Shankarabharanam|https://www.youtube.com/watch?v=lJj0K4v-C2s|20|IN
Evari Bodhana|Abhogi|https://www.youtube.com/watch?v=7cdTmdoa420|20|IN
sarasijanAba murArE|Todi|https://www.youtube.com/watch?v=Mnc1Jxhdxt4|20|IN
sri subramanyaya|Kambhoji|https://www.youtube.com/watch?v=T6VVoay4g0g|20|IN
Koluvamaregada kodandapani|Todi|https://www.youtube.com/watch?v=F5RiZKLxBZo|20|IN
dorakuna|Bilahari|https://www.youtube.com/watch?v=GoNjrt1qHUg|20|IN
nagumomu ganaleni|Saveri|https://www.youtube.com/watch?v=j-1FPDdY8sU|20|IN
bhajarE bhaja mAnasa|Kanada|https://www.youtube.com/watch?v=zbY3OFKjYWQ|20|IN
bhajarE gOpAlam|Hindolam|https://www.youtube.com/watch?v=jS2sMzLD9bM|20|IN
sri vAtApi|Sahana|https://www.youtube.com/watch?v=1-VefTLD7KY|20|IN
marivEre dikkevaru|Latangi|https://www.youtube.com/watch?v=vkmOyEtk4Qo|20|IN
Jagadanandakaraka|Nata|https://www.youtube.com/watch?v=lRHhI8g8RVA|20|IN
bhajare|Kalyani|https://www.youtube.com/watch?v=ad6UhYwTXXQ|20|IN
jagadOddhAraNa|Kapi|https://www.youtube.com/watch?v=fFfYyStObP8|20|IN
O Rangashayee|Kambhoji|https://www.youtube.com/watch?v=uDtuixxCVHA|20|IN
abhimAna|Begada|https://www.youtube.com/watch?v=nsa5v9s8o8E|20|IN
yArO ivar yArO|Bhairavi|https://www.youtube.com/watch?v=RWIZJQ9QT6U|20|IN
yEnATi mOmu palamu|Bhairavi|https://www.youtube.com/watch?v=8Ub9i6OXirQ|20|IN
rAma nee|Karaharapriya|https://www.youtube.com/watch?v=Tqv19g98LXI|20|IN
raghuvara|Kamavardani|https://www.youtube.com/watch?v=16dIDxk9tbE|20|IN
samikki sari|Kedaragaula|https://www.youtube.com/watch?v=10XWEBvnmqM|20|IN
vidulaku mrokkedA|Mayamalavagaula|https://www.youtube.com/watch?v=CaCLbT1S0Go|20|IN
meenakshi memudam|Purvikalyani|https://www.youtube.com/watch?v=HQ766WcKaj0|20|IN
entara|Harikambhoji|https://www.youtube.com/watch?v=WUkViRiTB_o|20|IN
raghuvamsa|Kathanakuthoohalam|https://www.youtube.com/watch?v=F5zCVJF3pt0|20|IN
bhAgyAda lakshmi|Madhyamavati|https://www.youtube.com/watch?v=zmHsP1CN_aA|20|IN
Brahmam Okate|Bowli|https://www.youtube.com/watch?v=kQRB3vwcO3w|20|OOC
Kurai Onrum Illai|Ragamalika|https://www.youtube.com/watch?v=WbrLWbnRBlw|20|IN
Chinnanjiru Kiliye|Ragamalika|https://www.youtube.com/watch?v=BMpm8Xlos3Y|20|OOC
sObillu saptaswara|Jaganmohini|https://www.youtube.com/watch?v=t-CtnVEm8Tg|20|IN
Vaishnava Jana To|Khamaj|https://www.youtube.com/watch?v=60ls2-Aeo3s|20|IN
Ninnukori Yunnanura|Mohanam|https://www.youtube.com/watch?v=pHO_AO6X_JM|20|IN
krishNA nee bEganE bArO|Yamunakalyani|ytsearch1:Krishna Nee Begane Baro Yamuna Kalyani carnatic vocal|20|IN
endarO mahAnubhAvulu|Sri|ytsearch1:Endaro Mahanubhavulu pancharatna Sri raga vocal|20|IN
brOchevarevarura|Khamas|ytsearch1:Brochevarevarura Khamas carnatic vocal|20|IN
chakkani rAja|Kharaharapriya|ytsearch1:Chakkani Raja Margamu Kharaharapriya Tyagaraja|20|IN
mOkshamu galadhA|Saramati|ytsearch1:Mokshamu Galada Saramati Tyagaraja vocal|20|IN
nidhi chAla sukhamA|Kalyani|ytsearch1:Nidhi Chala Sukhama Kalyani Tyagaraja vocal|20|IN
sogasugA mrudanga|Sriranjani|ytsearch1:Sogasuga Mridanga Talamu Sriranjani Tyagaraja|20|IN
akhilAndEswari|Dvijavanti|ytsearch1:Akhilandeswari Dwijavanthi Dikshitar vocal|20|IN
Ananda naTana prakAsam|Kedaram|ytsearch1:Ananda Natana Prakasham Kedaram Dikshitar|20|IN
himAdrisutE|Kalyani|ytsearch1:Himadri Sute Kalyani Syama Sastri vocal|20|IN
mAnasa sancharare|Sama|ytsearch1:Manasa Sancharare Sama Sadasiva Brahmendra vocal|20|IN
ninnuvinA marigaladA|Ritigaula|ytsearch1:Ninnuvina Marigalada Ritigaula Syama Sastri|20|IN
paridAnamicchidE|Bilahari|ytsearch1:Paridanamichite Bilahari Patnam Subramania Iyer|20|IN
rAma nannu brOvara|Harikambhoji|ytsearch1:Rama Nannu Brovara Harikambhoji Tyagaraja vocal|20|IN
shrI varalakshmi namastubhyam|Sri|ytsearch1:Sri Varalakshmi Namastubhyam Dikshitar vocal|20|IN
siddhi vinAyakam|Shanmukhapriya|ytsearch1:Siddhi Vinayakam Anisham Shanmukhapriya Dikshitar|20|IN
swAminatha|Nata|ytsearch1:Swaminatha Paripalaya Nata Dikshitar vocal|20|IN
Ehi annapUrNE|Punnagavarali|ytsearch1:Ehi Annapurne Punnagavarali Dikshitar vocal|20|IN
bhAvayAmi raghurAmam|Ragamalika|ytsearch1:Bhavayami Raghuramam MS Subbulakshmi ragamalika|20|IN
Kanne Kalaimane|NA|ytsearch1:Kanne Kalaimane Moondram Pirai Yesudas|20|OOC
Chinna Chinna Aasai|NA|ytsearch1:Chinna Chinna Aasai Roja Minmini|30|OOC
Malargale Malargale|NA|ytsearch1:Malargale Malargale Love Birds Chitra|30|OOC
Munbe Vaa|NA|ytsearch1:Munbe Vaa Sillunu Oru Kadhal Shreya|30|OOC
Raghupati Raghava Raja Ram|NA|ytsearch1:Raghupati Raghava Raja Ram MS Subbulakshmi|20|OOC
Achyutam Keshavam|NA|ytsearch1:Achyutam Keshavam Krishna Damodaram bhajan|20|OOC
Hanuman Chalisa|NA|ytsearch1:Hanuman Chalisa MS Rama Rao|20|OOC
Om Jai Jagdish Hare|NA|ytsearch1:Om Jai Jagdish Hare aarti|20|OOC
Ennavale Adi Ennavale|NA|ytsearch1:Ennavale Adi Ennavale Kadhalan Unni Menon|30|OOC
Nila Kaigirathu|NA|ytsearch1:Nila Kaigirathu Indira Harini|30|OOC
Vellai Pura Ondru|NA|ytsearch1:Vellai Pura Ondru Pudhu Kavithai|30|OOC
Thendral Vanthu Theendum Pothu|NA|ytsearch1:Thendral Vanthu Theendum Pothu Avatharam|30|OOC
Margazhi Thingal|NA|ytsearch1:Margazhi Thingal Thiruppavai MS Subbulakshmi|20|OOC
Aigiri Nandini|NA|ytsearch1:Aigiri Nandini Mahishasura Mardini stotram|20|OOC
Payoji Maine|NA|ytsearch1:Payoji Maine Ram Ratan Dhan Payo MS Subbulakshmi|20|OOC
Katrin Mozhi|NA|ytsearch1:Katrin Mozhi Mozhi song|30|OOC
Narumugaye|NA|ytsearch1:Narumugaye Iruvar Unnikrishnan|30|OOC
Pachai Nirame|NA|ytsearch1:Pachai Nirame Alaipayuthey Hariharan|30|OOC
Minsara Kanna|NA|ytsearch1:Minsara Kanna Padayappa|30|OOC
Kadhal Rojave|NA|ytsearch1:Kadhal Rojave Roja SPB|30|OOC
Vennilave Vennilave|NA|ytsearch1:Vennilave Vennilave Minsara Kanavu Hariharan|30|OOC
Chinna Kannan Azhaikiran|NA|ytsearch1:Chinna Kannan Azhaikiran Kavikkuyil Balamuralikrishna|20|OOC
'

ok=0
fail=0
n=0

while IFS='|' read -r TITLE RAGA URL START TAG; do
  [ -z "$TITLE" ] && continue
  [ -n "$ONLY_TAG" ] && [ "$TAG" != "$ONLY_TAG" ] && continue
  n=$((n+1))
  # OOC clips carry a __OOC marker so identify_clip.py scores them as
  # must-abstain instead of in-catalog. RAGA=NA -> raga truth skipped.
  if [ "$TAG" = "OOC" ]; then
    FNAME="${TITLE}__${RAGA}__OOC.m4a"
  else
    FNAME="${TITLE}__${RAGA}.m4a"
  fi
  OUTPATH="$OUTDIR/$FNAME"

  if [ -f "$OUTPATH" ]; then
    echo "[$n] SKIP (exists): $FNAME"
    ok=$((ok+1))
    continue
  fi
  NT=$(norm_title "$TITLE")
  if DUP=$(dup_of "$NT"); then
    echo "[$n] SKIP (same composition already in set as: $DUP): $FNAME"
    ok=$((ok+1))
    continue
  fi

  echo "[$n] ($TAG) $TITLE -> $RAGA"
  echo "     $URL  (start=${START}s, dur=${DURATION}s)"

  # NOTE: mktemp pre-creates the file (and macOS mktemp doesn't substitute
  # mid-name X's), which made yt-dlp skip with "already downloaded" -> 0-byte
  # temp -> every entry failed. Use a plain per-entry path and delete first.
  # yt-dlp/ffmpeg get </dev/null (-nostdin) or they eat the heredoc feeding
  # `read` and truncate the next entry's title.
  TMPFILE="/tmp/carnatify_dl_$n.m4a"
  rm -f "$TMPFILE"

  # What did the search actually pick? Log it so clips can be eyeballed.
  META=$(yt-dlp --print "%(title)s|%(duration)s|%(webpage_url)s" \
      --extractor-args "youtube:player_client=default,-tv" \
      --no-warnings "$URL" </dev/null 2>/dev/null | head -1)
  VTITLE=${META%%|*}
  REST=${META#*|}
  VDUR=${REST%%|*}
  VURL=${REST#*|}

  # Window: START in the entry is a fallback. When the video duration is
  # known, cut from 35% in (past intros/alapana openings, before fade-out),
  # clamped so the full 60s fits.
  if [ -n "$VDUR" ] && [ "$VDUR" -gt 90 ] 2>/dev/null; then
    START=$(( VDUR * 35 / 100 ))
    MAXSTART=$(( VDUR - DURATION - 5 ))
    [ "$START" -gt "$MAXSTART" ] && START=$MAXSTART
    [ "$START" -lt 20 ] && START=20
  fi

  echo "     video: ${VTITLE:-?} (${VDUR:-?}s) -> cutting ${START}s..$((START+DURATION))s"

  if yt-dlp -f "bestaudio[ext=m4a]/bestaudio/best" \
      --extractor-args "youtube:player_client=default,-tv" \
      --force-overwrites \
      -o "$TMPFILE" "$URL" --quiet --no-warnings </dev/null; then
    if ffmpeg -nostdin -y -ss "$START" -i "$TMPFILE" -t "$DURATION" -c:a aac -b:a 128k "$OUTPATH" -loglevel error; then
      if REASON=$(validate_clip "$OUTPATH"); then
        echo "     -> saved $OUTPATH"
        printf '%s\t%s\t%s\t%ss @%ss\n' "$FNAME" "${VTITLE:-?}" "${VURL:-$URL}" "${VDUR:-?}" "$START" >> "$OUTDIR/fetch_manifest.tsv"
        ok=$((ok+1))
      else
        mkdir -p "$QUARANTINE"
        mv "$OUTPATH" "$QUARANTINE/$FNAME"
        echo "     !! REJECTED ($REASON) -> quarantined, not scored"
        printf '%s\tREJECTED: %s\t%s\t%ss @%ss\n' "$FNAME" "$REASON" "${VURL:-$URL}" "${VDUR:-?}" "$START" >> "$OUTDIR/fetch_manifest.tsv"
        fail=$((fail+1))
      fi
    else
      echo "     !! ffmpeg trim failed for $TITLE"
      fail=$((fail+1))
    fi
  else
    echo "     !! yt-dlp download failed for $TITLE ($URL)"
    fail=$((fail+1))
  fi
  rm -f "$TMPFILE"
done <<< "$CLIPS"

echo ""
echo "Done: $ok ok, $fail failed, $((ok+fail)) total attempted."
echo "Clips are in: $OUTDIR"
echo "Score with: venv_train/bin/python identify_clip.py \"$OUTDIR\""

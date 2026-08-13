#!/bin/bash
# Convert Deepti's 11 long-form concert recordings to mp3 for analysis.
#
# Encoding matches BOTH long_concert_6.mp3 (which she converted herself) and the
# existing training corpus in data/concert_audio: 44100 Hz, stereo, 192 kbps.
# Same format end to end means nothing downstream sees a new audio regime.
#
# This script NEVER deletes a source file. Deletion of the .mp4/.MOV originals is
# Deepti's to do, after she has checked the outputs.
#
# Resumable: an existing, verified .mp3 is skipped.

set -u
SRC="$HOME/Downloads"
LOG="$SRC/convert_long_concerts.log"

: > "$LOG"
echo "=== long concert conversion, $(date) ===" | tee -a "$LOG"

ok=0; skip=0; fail=0

shopt -s nullglob
for f in "$SRC"/long_concert_*.mp4 "$SRC"/long_concert_*.MOV "$SRC"/long_concert_*.mov; do
  base="$(basename "$f")"
  stem="${base%.*}"
  out="$SRC/$stem.mp3"

  if [ -f "$out" ] && [ -s "$out" ]; then
    echo "SKIP  $base -> $stem.mp3 already exists" | tee -a "$LOG"
    skip=$((skip+1))
    continue
  fi

  src_dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)
  echo "----- $base  (source ${src_dur}s)" | tee -a "$LOG"

  # -vn drop video, -sn drop subtitles, -dn drop data streams (the MOV carries
  # three). -map 0:a:0 takes the first audio stream only.
  if ffmpeg -hide_banner -loglevel error -nostdin -y \
       -i "$f" -vn -sn -dn -map 0:a:0 \
       -ar 44100 -ac 2 -c:a libmp3lame -b:a 192k \
       "$out" 2>>"$LOG"; then
    out_dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" 2>/dev/null)
    # duration must land within 2 s of the source, else the decode was truncated
    keep=$(awk -v a="$src_dur" -v b="$out_dur" 'BEGIN{d=a-b; if(d<0)d=-d; print (d<=2.0)?"ok":"bad"}')
    sz=$(du -h "$out" | cut -f1)
    if [ "$keep" = "ok" ]; then
      echo "OK    $stem.mp3  ${out_dur}s  $sz" | tee -a "$LOG"
      ok=$((ok+1))
    else
      echo "FAIL  $stem.mp3 duration ${out_dur}s vs source ${src_dur}s -- TRUNCATED, source kept" | tee -a "$LOG"
      fail=$((fail+1))
    fi
  else
    echo "FAIL  $base -- ffmpeg error, see log, source kept" | tee -a "$LOG"
    fail=$((fail+1))
  fi
done

echo "=== done: $ok converted, $skip skipped, $fail failed ===" | tee -a "$LOG"
echo "--- inventory ---" | tee -a "$LOG"
for m in "$SRC"/long_concert_*.mp3; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$m" 2>/dev/null)
  printf "%-28s %8.1f s  %7.1f min  %s\n" "$(basename "$m")" "$d" \
    "$(awk -v x="$d" 'BEGIN{print x/60}')" "$(du -h "$m" | cut -f1)" | tee -a "$LOG"
done
exit $fail

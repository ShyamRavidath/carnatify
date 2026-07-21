# CoverHunter clean re-score — recipe and rationale

Written 2026-07-20. This is a **Colab job** (the trained checkpoint, CQT
features, and CoverHunter repo all live on Drive/Colab, not on the local
machine). It answers the one open question about the melody channel:
*does the model do cross-recording composition ID, or just near-fingerprinting?*

## Why this is needed

The dev metric the training reported (`hit_rate` 1.0, `mAP` ~0.327) is
contaminated. 142 of 189 validation clips (75%) had a **different crop of the
same source recording** sitting in the reference pool. `real0`/`real1` and the
`aug_*` clips of one song are frequently cut from the same mp3, so the model
can score a "hit" by matching audio-fingerprint-level similarity — exactly the
capability that already scored 0% on wild clips (see the Qmax graveyard entry
in ARCHITECTURE.md). A saturated metric is a warning, not a result.

## Why it is nonetheless answerable

Not all versions are augmentations of one recording. Measured on `val.jsonl`:

- 28 of 54 val songs have **>=2 genuinely distinct source recordings**
  (the `_rN` files are separate renditions, not speed/pitch augmentations)
- a **137-clip source-disjoint set** exists (one clip per distinct recording,
  restricted to the 28 multi-recording songs), 3-8 clips/song, every clip has
  at least one cross-recording positive

That set is written to `data/coverhunter_data/clean_eval_utts.txt` (regenerate
with the snippet at the bottom of this file). On it, every same-song match is
necessarily cross-recording, so mAP is honest.

## The number that decides it

- **mAP holds near 0.3 on the clean 137** -> the model learned something real;
  the melody/CSI channel is alive and worth scaling the synth pipeline for.
- **mAP collapses toward chance** (~1/avg-clips-per-song, roughly 0.05-0.1)
  -> it learned fingerprinting, not composition ID; close the channel until
  the flywheel provides real cross-artist renditions.

Reference: chance on ~28 multi-version songs is ~0.036 hit@1. The 1-epoch
evals (before the training bug was fixed) scored mAP 0.047-0.078 — above
chance but barely.

## Colab recipe

Prereq: a Colab session with the CoverHunter repo, `data/carnatify/` features
restored from `MyDrive/carnatify/coverhunter_feat.zip`, and the checkpoint
restored from `MyDrive/carnatify/coverhunter_ckpt/carnatify/pt_model`
(colab_coverhunter.py steps 1-6 already do all of this — run it up to but not
including step 7, or just let it restore and Ctrl-C before training).

```python
import json
from pathlib import Path
CH = Path("CoverHunter")                       # repo root on Colab
FEAT = CH / "data" / "carnatify"

# 1. bring the allowlist over (paste the file, or regenerate — see below)
clean = set(Path("clean_eval_utts.txt").read_text().split())

# 2. full.txt is the extracted-feature index. Check its schema first:
#    !head -1 CoverHunter/data/carnatify/full.txt
#    It is JSON per line. The utt id was REWRITTEN by extract_csi_features,
#    but each line still carries the ORIGINAL wav path / song. Match the
#    clean set on whichever field contains the synth_/real_ basename.
def utt_of(line):
    d = json.loads(line)
    # try common fields; the basename of the wav path is the stable key
    for k in ("utt", "wav", "perf", "song"):
        v = str(d.get(k, ""))
        for c in clean:
            if c in v:
                return c
    return None

lines = FEAT.joinpath("full.txt").read_text().splitlines()
clean_lines = [l for l in lines if utt_of(l) in clean]
print(f"matched {len(clean_lines)}/{len(clean)} clean clips in full.txt")
assert len(clean_lines) >= 100, "schema mismatch — inspect head of full.txt"

# 3. write query == ref == the clean set; eval_testset self-excludes by utt
(FEAT / "clean_eval.txt").write_text("\n".join(clean_lines) + "\n")

# 4. run the repo's own eval
#    !cd CoverHunter && python -m tools.eval_testset \
#        egs/carnatify/pt_model data/carnatify/clean_eval.txt data/carnatify/clean_eval.txt
```

If step 2 matches far fewer than 137, the utt rewrite dropped the basename;
in that case rebuild the map from `song_id_map.json` + the `song` field
(song-level is coarser but still excludes cross-song leakage — it just cannot
enforce recording-disjointness, so note that caveat on the resulting number).

## Regenerate the allowlist

```python
import json, collections
rows=[json.loads(l) for l in open('data/coverhunter_data/val.jsonl')]
by=collections.defaultdict(list)
for r in rows: by[r['song_id']].append(r)
rec=lambda v: v[4:] if v.startswith('aug_') else v
keep=[]
for sid,clips in by.items():
    perrec={}
    for c in clips: perrec.setdefault(rec(c['version']), c)
    if len(perrec)>=2: keep.extend(perrec.values())
open('clean_eval_utts.txt','w').write('\n'.join(sorted(c['utt'] for c in keep))+'\n')
```

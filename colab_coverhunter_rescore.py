#!/usr/bin/env python3
"""CoverHunter CLEAN re-score — Stage 1 go/no-go (Colab, GPU runtime).

Answers one question: does the trained melody model do real cross-recording
composition ID, or just near-fingerprinting? See COVERHUNTER_RESCORE.md.

The training dev metric (mAP ~0.327) is contaminated — 75% of val clips had a
different crop of the SAME source recording in the reference pool. This script
re-runs the repo's own eval on a 137-clip SOURCE-DISJOINT set (one clip per
distinct recording, 28 songs with >=2 real recordings), where every same-song
match is necessarily cross-recording.

Reads:  MyDrive/carnatify/coverhunter_feat.zip   (CQT features, ~2 GB)
        MyDrive/carnatify/coverhunter_ckpt/carnatify/pt_model  (checkpoint)
Writes: nothing to Drive. Prints the number.

Run (Colab, T4 is plenty — this is inference only, ~2-5 min after restore):
    %run colab_coverhunter_rescore.py

DECISION (from COVERHUNTER_RESCORE.md):
    mAP ~0.3            -> melody channel is real CSI. Proceed to Stage 2.
    mAP ~0.05-0.10      -> chance-ish; it learned fingerprinting. Close channel.
Chance floor for this set: ~3.9 positives among 136 refs => ~0.03-0.05 mAP.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DRIVE_FEAT = Path("/content/drive/MyDrive/carnatify/coverhunter_feat.zip")
DRIVE_CKPT = Path("/content/drive/MyDrive/carnatify/coverhunter_ckpt/carnatify/pt_model")
WORK = Path("/content")
CH = WORK / "CoverHunter"
FEAT_DIR = CH / "data" / "carnatify"
EGS_DIR = CH / "egs" / "carnatify"
CH_REPO = "https://github.com/Liu-Feng-deeplearning/CoverHunter"

# The 137 source-disjoint utt ids (data/coverhunter_data/clean_eval_utts.txt),
# inlined so nothing has to be uploaded alongside this script.
CLEAN = ["real_0000", "real_0001", "real_0002", "real_0006", "real_0007", "real_0012", "real_0013", "real_0014", "real_0015", "real_0020", "real_0021", "real_0031", "real_0032", "real_0035", "real_0036", "real_0037", "real_0038", "real_0039", "real_0040", "real_0041", "real_0056", "real_0057", "real_0058", "real_0059", "real_0060", "real_0068", "real_0069", "real_0070", "real_0071", "real_0072", "real_0073", "real_0081", "real_0082", "real_0083", "real_0092", "real_0093", "real_0094", "real_0095", "real_0096", "real_0106", "real_0107", "real_0108", "real_0121", "real_0122", "real_0123", "real_0124", "real_0125", "real_0126", "real_0135", "real_0136", "real_0140", "real_0141", "real_0145", "real_0146", "real_0147", "real_0148", "real_0149", "real_0157", "real_0158", "real_0159", "real_0167", "real_0168", "real_0169", "real_0170", "real_0171", "real_0172", "real_0173", "real_0174", "real_0175", "real_0176", "real_0177", "real_0178", "real_0179", "real_0180", "real_0181", "real_0182", "real_0183", "real_0188", "real_0189", "synth_000002", "synth_000003", "synth_000006", "synth_000008", "synth_000010", "synth_000012", "synth_000016", "synth_000017", "synth_000018", "synth_000019", "synth_000021", "synth_000022", "synth_000026", "synth_000028", "synth_000029", "synth_000030", "synth_000032", "synth_000035", "synth_000037", "synth_000042", "synth_000043", "synth_000044", "synth_000057", "synth_000058", "synth_000059", "synth_000060", "synth_000063", "synth_000067", "synth_000070", "synth_000074", "synth_000076", "synth_000078", "synth_000080", "synth_000086", "synth_000087", "synth_000089", "synth_000090", "synth_000094", "synth_000096", "synth_000097", "synth_000098", "synth_000103", "synth_000105", "synth_000110", "synth_000111", "synth_000125", "synth_000126", "synth_000127", "synth_000128", "synth_000131", "synth_000139", "synth_000142", "synth_000155", "synth_000157", "synth_000171", "synth_000180", "synth_000193", "synth_000203"]
CLEAN_SET = set(CLEAN)
ID_RE = re.compile(r"(?:real_\d{4}|synth_\d{6})")


def run(cmd, **kw):
    print(f"\n$ {' '.join(map(str, cmd))}", flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def step(msg):
    print(f"\n{'=' * 60}\n== {msg}\n{'=' * 60}", flush=True)


def remount():
    """Colab's Drive FUSE mount drops under heavy IO (OSError 107, 'Transport
    endpoint is not connected'). Re-establish it in place."""
    from google.colab import drive  # noqa: colab-only import
    try:
        drive.flush_and_unmount()
    except Exception as exc:  # already dead / never mounted
        print(f"(unmount: {exc})")
    drive.mount("/content/drive", force_remount=True)


def drive_retry(fn, what, tries=4):
    """Run a Drive-touching operation, remounting between attempts."""
    import time
    for i in range(1, tries + 1):
        try:
            return fn()
        except OSError as exc:
            if i == tries:
                raise
            print(f"!! {what} failed ({exc.__class__.__name__}: {exc}); "
                  f"remounting Drive and retrying ({i}/{tries - 1})")
            time.sleep(5)
            remount()
            time.sleep(5)


# ------------------------------------------------- 1. drive + repo + deps
step("1/5 Mount Drive, clone CoverHunter, install deps")
if not Path("/content/drive/MyDrive").exists():
    from google.colab import drive  # noqa: colab-only import
    drive.mount("/content/drive")
for p in (DRIVE_FEAT, DRIVE_CKPT):
    if not drive_retry(p.exists, f"stat {p}"):
        sys.exit(f"MISSING {p} — this Stage-1 rescore needs the cached features "
                 "and the trained checkpoint from the 2026-07-19/20 run.")
if not CH.exists():
    run(["git", "clone", "--depth", "1", CH_REPO, CH])
req = CH / "requirements.txt"
if req.exists():
    run([sys.executable, "-m", "pip", "install", "-q", "-r", req])
else:
    run([sys.executable, "-m", "pip", "install", "-q",
         "librosa", "soundfile", "pyyaml", "nnAudio", "tensorboard"])
# repo targets typeguard 2.x; 4.x rejects ConformerEncoder(global_cmvn=None)
run([sys.executable, "-m", "pip", "install", "-q", "typeguard==2.13.3"])

# ------------------------------------------------- 2. restore features + ckpt
step("2/5 Restore CQT features and checkpoint from Drive")
if not (FEAT_DIR / "full.txt").exists():
    drive_retry(lambda: run(["unzip", "-q", "-o", DRIVE_FEAT, "-d", CH / "data"]),
                "feature unzip")

# Copy ONLY the newest checkpoint step (plus any small non-checkpoint files),
# not the whole pt_model dir: eval loads the latest `g_` weights, and every
# extra file is more Drive IO — which is what killed the mount last time.
ck_dst = EGS_DIR / "pt_model"
ck_dst.mkdir(parents=True, exist_ok=True)
names = drive_retry(lambda: sorted(p.name for p in DRIVE_CKPT.iterdir()),
                    "list checkpoint dir")
steps = sorted({n.split("_", 1)[1] for n in names
                if re.fullmatch(r"(?:g|do)_\d+", n)})
if not steps:
    sys.exit(f"No g_*/do_* checkpoints in {DRIVE_CKPT} — nothing to evaluate.")
latest = steps[-1]
wanted = [n for n in names
          if n in (f"g_{latest}", f"do_{latest}")
          or not re.fullmatch(r"(?:g|do)_\d+", n)]
print(f"{len(steps)} checkpoint steps on Drive; using latest = {latest}")
for name in wanted:
    dst = ck_dst / name
    src = DRIVE_CKPT / name
    if dst.exists() and dst.stat().st_size > 0:
        continue
    if drive_retry(src.is_dir, f"stat {name}"):
        continue
    drive_retry(lambda s=src, d=dst: shutil.copy(s, d), f"copy {name}")
    print(f"  copied {name} ({dst.stat().st_size / 1e6:.1f} MB)")
ckpts = sorted(p.name for p in ck_dst.iterdir())
print(f"full.txt lines: {sum(1 for _ in (FEAT_DIR / 'full.txt').open())}")
print(f"checkpoint files local: {ckpts}")
assert any(n.startswith("g_") for n in ckpts), "no g_* weights copied"

# the eval loads egs/<name>/config/hparams.yaml; rebuild it if this is a fresh VM
cfg_path = EGS_DIR / "config" / "hparams.yaml"
if not cfg_path.exists():
    drive_cfg = DRIVE_CKPT.parent / "config" / "hparams.yaml"
    if drive_retry(drive_cfg.exists, "stat config"):
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        drive_retry(lambda: shutil.copy(drive_cfg, cfg_path), "copy config")
        print(f"config restored from Drive: {drive_cfg}")
    else:
        sys.exit(f"MISSING {cfg_path} and no copy on Drive at {drive_cfg} — "
                 "re-run colab_coverhunter.py steps 1-6 to regenerate it.")

# ------------------------------------------------- 3. build the clean eval list
step("3/5 Build clean_eval.txt (one line per source-disjoint clip)")
# extract_csi_features rewrites utt ids as CUMULATIVE speed-aug chains:
#   sp_0.8-real_0000 -> sp_0.9-sp_0.8-real_0000 -> sp_1.1-sp_0.9-sp_0.8-...
# so NO clip survives at original speed (the 1.0 pass just re-emits the
# previous name, which is also why some utts appear twice). Every line for one
# recording is therefore the same audio at a different rate — putting more than
# one in the reference pool would reintroduce the fingerprint leakage this eval
# exists to remove. Keep exactly ONE line per clean id: the chain whose PRODUCT
# of speed factors is closest to 1.0 (the same factor for every clip, so the
# comparison stays uniform).
def speed_factor(utt):
    f = 1.0
    for s in re.findall(r"sp_([\d.]+)-", utt):
        try:
            f *= float(s)
        except ValueError:
            pass
    return f


best = {}          # clean id -> (distance from 1.0, utt, line)
n_variants = 0
for line in (FEAT_DIR / "full.txt").read_text().splitlines():
    if not line.strip():
        continue
    d = json.loads(line)
    blob = " ".join(str(d.get(k, "")) for k in ("utt", "wav", "perf", "song", "version", "feat"))
    hits = CLEAN_SET.intersection(ID_RE.findall(blob))
    if len(hits) != 1:
        continue                       # no match, or ambiguous — drop
    cid = hits.pop()
    utt = str(d.get("utt", ""))
    n_variants += 1
    key = (abs(speed_factor(utt) - 1.0), len(utt))
    if cid not in best or key < best[cid][0]:
        best[cid] = (key, utt, line)

chosen_speeds = {round(speed_factor(u), 4) for _, u, _ in best.values()}
best = {cid: line for cid, (_, _, line) in best.items()}
print(f"matched {len(best)}/{len(CLEAN)} clean clips "
      f"from {n_variants} speed-aug variants "
      f"(kept one per recording; speed factors used: {sorted(chosen_speeds)})")
if len(best) < 100:
    sys.exit("SCHEMA MISMATCH — too few matches. Inspect the first line of "
             f"{FEAT_DIR / 'full.txt'} and adjust the id matching above.")

eval_txt = FEAT_DIR / "clean_eval.txt"
eval_txt.write_text("\n".join(best[c] for c in CLEAN if c in best) + "\n")

# how many positives does an average query have? -> the chance floor
songs = {}
for cid, line in best.items():
    songs.setdefault(json.loads(line).get("song", "?"), []).append(cid)
sizes = [len(v) for v in songs.values()]
n = len(best)
# expected mAP under random ranking = (mean positives PER QUERY) / (pool - 1).
# A clip in a song of size s has s-1 positives, and s clips carry that count,
# so the per-clip sum is sum(s*(s-1)) — averaging (s-1) over SONGS instead
# understates the floor badly (0.006 vs 0.031 on this set).
chance = (sum(s * (s - 1) for s in sizes) / n) / (n - 1)
print(f"{len(songs)} songs, {min(sizes)}-{max(sizes)} clips/song, "
      f"mean {sum(sizes) / len(sizes):.2f}")
print(f"random-ranking precision floor ~{chance:.3f} "
      f"(a chance mAP lands near this, not at 0)")

# ------------------------------------------------- 4. run the repo's own eval
step("4/5 tools.eval_testset on the clean set (query == ref, self-excluded)")
out = ""
for model_dir in (EGS_DIR, EGS_DIR / "pt_model"):
    cmd = [sys.executable, "-u", "-m", "tools.eval_testset", str(model_dir),
           "data/carnatify/clean_eval.txt", "data/carnatify/clean_eval.txt"]
    print(f"\n$ {' '.join(cmd)}", flush=True)
    p = subprocess.run(cmd, cwd=CH, capture_output=True, text=True)
    out = p.stdout + p.stderr
    print(out[-4000:])
    if p.returncode == 0:
        break
    print(f"(returncode {p.returncode} with model_dir={model_dir}, trying next)")

# ------------------------------------------------- 5. the verdict
step("5/5 VERDICT")
nums = re.findall(r"(?:mean_?ap|mAP|map)\D{0,12}([01]?\.\d+)", out, re.I)
hits = re.findall(r"hit_?rate\D{0,12}([01]?\.\d+)", out, re.I)
if not nums:
    print("Could not parse a mAP from the eval output — read the log above and "
          "compare the printed mAP by hand against the thresholds below.")
else:
    m = float(nums[-1])
    print(f"CLEAN mAP = {m:.4f}   (contaminated dev mAP was 0.327; "
          f"chance floor ~{chance:.3f})")
    if hits:
        print(f"hit_rate  = {hits[-1]}")
    if m >= 0.25:
        print("\n=> PASS. Cross-recording composition ID is real. Proceed to "
              "Stage 2: wire CSI to the ~/sung_tests wild scoreboard.")
    elif m >= 0.15:
        print("\n=> AMBIGUOUS. Real signal but well below the dev number. "
              "Report it — Stage 2 becomes a judgement call, not automatic.")
    else:
        print("\n=> FAIL. At/near chance: the model learned fingerprinting, "
              "not composition ID. Close the melody channel; pivot to door 2.")
print("\nReport back: the CLEAN mAP line, the matched-clips line from step 3, "
      "and the last ~20 lines of eval output.")

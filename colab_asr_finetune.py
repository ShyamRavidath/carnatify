# %% [markdown]
# # Carnatify sung-Carnatic ASR PILOT fine-tune (Colab GPU, LoRA)
#
# Goal: test whether adapting Whisper to *sung* Carnatic moves the wall. The
# `scripts/precision_coverage_curve.py` diagnostic proved the lyrics-ASR pipeline
# has NO shippable precision operating point (<=31% at any gate) because stock
# speech-ASR can't read singing. This is the falsifiable probe: LoRA-adapt
# Whisper on ~80 min of weakly-aligned Saraga pallavi/anupallavi audio, then
# transcribe the wild clips and re-score. It is a PILOT — small, single-corpus,
# artist-skewed (Sanjay Subrahmanyan / Arkay heavy). Success = the curve moves
# at all; failure = strong signal the backbone won't reach the 85% bar.
#
# ## Prep (one time, local)
#   venv_train/bin/python scripts/clean_saraga_trainset.py      # -> clean json
#   venv_train/bin/python scripts/build_saraga_pilot_zip.py     # -> saraga_pilot.zip
#   upload saraga_pilot.zip to  MyDrive/carnatify/saraga_pilot.zip
#
# ## Run (Colab: Runtime > Change runtime type > T4/A100)
#   Upload this file (or put on Drive) and:  %run colab_asr_finetune.py
#   Mount, unzip, slice windows, LoRA train, adapter saved to
#   MyDrive/carnatify/asr_pilot_adapter/ so a disconnect doesn't lose it.
#
# ## Bring back
#   - the adapter dir (already on Drive), and
#   - transcripts_pilot.json from the optional validation cell,
#   then locally score fine-tuned transcripts through the precision/coverage
#   curve to decide go/no-go on data expansion (phase B).
#
# ## Known pilot limitations (be honest in the writeup)
#   - Weak section-level labels: each <=30s window carries its whole section
#     text. Fine for repetitive pallavi; noisier for longer spans.
#   - Mixed languages (Telugu/Tamil/Sanskrit/Kannada) but one forced language
#     token below — a real limitation, acceptable for a signal probe only.
#   - ~80 min, few artists: expect voice/style overfit. Do NOT read a good
#     pilot WER as production-ready.

# %% Config
BASE_MODEL = "openai/whisper-small"   # pilot size; try -medium or an Indic base later
LANG = "ta"                            # forced language token (corpus is mixed; see caveats)
USE_HIGH_ONLY = True                   # train on high-confidence (pallavi/anupallavi) only
EPOCHS = 6
LR = 1e-3                              # LoRA can take a higher LR than full fine-tune
BATCH = 8

DRIVE_ZIP = "/content/drive/MyDrive/carnatify/saraga_pilot.zip"
DRIVE_ADAPTER = "/content/drive/MyDrive/carnatify/asr_pilot_adapter"
WORK = "/content/pilot"

# %% Install
# NOTE: Colab ships torchao 0.10, which peft's strict version gate rejects
# (ImportError in get_peft_model). LoRA does not use torchao, so we uninstall it
# -> peft treats it as absent instead of raising. If peft was already imported
# this session, Runtime > Restart session after this cell, then re-run from top.
!pip -q uninstall -y torchao
!pip -q install -U "transformers>=4.44" "peft>=0.11" accelerate datasets \
    evaluate jiwer librosa soundfile

# %% Mount Drive + unzip pilot bundle
import os, zipfile, json
from google.colab import drive
drive.mount("/content/drive")
os.makedirs(WORK, exist_ok=True)
with zipfile.ZipFile(DRIVE_ZIP) as z:
    z.extractall(WORK)
segs = json.load(open(os.path.join(WORK, "saraga_asr_trainset_clean.json")))
if USE_HIGH_ONLY:
    segs = [s for s in segs if s["confidence"] == "high"]
segs = [s for s in segs if not s.get("notation_suspect")]
print(len(segs), "training segments")

# %% Slice each window -> 16k mono float32 (GPU box has ffmpeg via librosa)
import librosa, numpy as np
from collections import defaultdict

# cache full tracks once (26 files), then slice windows from memory
_track_cache = {}
def load_track(rel):
    if rel not in _track_cache:
        y, _ = librosa.load(os.path.join(WORK, rel), sr=16000, mono=True)
        _track_cache[rel] = y.astype("float32")
    return _track_cache[rel]

examples = []
for s in segs:
    y = load_track(s["audio_rel_path"])
    a, b = int(s["start_sec"] * 16000), int(s["end_sec"] * 16000)
    clip = y[a:b]
    if len(clip) < 16000:            # skip <1s slivers
        continue
    examples.append({"audio": clip, "text": s["text"], "work": s["registry_id"]})
print(len(examples), "sliced examples;", len(_track_cache), "tracks decoded")

# %% Composition-disjoint train/val split (no work leaks across the split)
import random
random.seed(0)
works = sorted({e["work"] for e in examples})
random.shuffle(works)
val_works = set(works[: max(1, len(works) // 6)])
train = [e for e in examples if e["work"] not in val_works]
val = [e for e in examples if e["work"] in val_works]
print(f"train {len(train)}  val {len(val)}  (val works: {len(val_works)})")

# %% Processor + feature/label encoding
from transformers import WhisperProcessor
processor = WhisperProcessor.from_pretrained(BASE_MODEL, language=LANG, task="transcribe")

def encode(batch):
    feats = processor.feature_extractor(
        batch["audio"], sampling_rate=16000
    ).input_features[0]
    labels = processor.tokenizer(batch["text"]).input_ids
    return {"input_features": feats, "labels": labels}

from datasets import Dataset
train_ds = Dataset.from_list(train).map(encode, remove_columns=["audio", "text", "work"])
val_ds = Dataset.from_list(val).map(encode, remove_columns=["audio", "text", "work"])

# %% Data collator
import torch
from dataclasses import dataclass
from typing import Any

@dataclass
class Collator:
    processor: Any
    def __call__(self, features):
        inp = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(inp, return_tensors="pt")
        lab = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(lab, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
        batch["labels"] = labels
        return batch

collator = Collator(processor)

# %% Model + LoRA
from transformers import WhisperForConditionalGeneration
from peft import LoraConfig, get_peft_model

model = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL)
model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(
    language=LANG, task="transcribe"
)
model.config.suppress_tokens = []
lora = LoraConfig(r=32, lora_alpha=64, target_modules=["q_proj", "v_proj"],
                  lora_dropout=0.05, bias="none")
model = get_peft_model(model, lora)
model.print_trainable_parameters()

# %% WER metric
import evaluate
wer_metric = evaluate.load("wer")
def compute_metrics(pred):
    pred_ids, label_ids = pred.predictions, pred.label_ids
    label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
    pred_str = processor.tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
    return {"wer": 100 * wer_metric.compute(predictions=pred_str, references=label_str)}

# %% Train
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

args = Seq2SeqTrainingArguments(
    output_dir="/content/asr_pilot_out",
    per_device_train_batch_size=BATCH,
    gradient_accumulation_steps=1,
    learning_rate=LR,
    num_train_epochs=EPOCHS,
    warmup_ratio=0.1,
    fp16=True,
    predict_with_generate=True,
    generation_max_length=128,
    eval_strategy="epoch",
    save_strategy="epoch",
    logging_steps=10,
    report_to=[],
    remove_unused_columns=False,   # required for peft + Whisper
    label_names=["labels"],
)
trainer = Seq2SeqTrainer(
    model=model, args=args, train_dataset=train_ds, eval_dataset=val_ds,
    data_collator=collator, compute_metrics=compute_metrics,
    processing_class=processor.feature_extractor,
)
trainer.train()

# %% Save adapter to Drive (survives disconnect)
os.makedirs(DRIVE_ADAPTER, exist_ok=True)
model.save_pretrained(DRIVE_ADAPTER)
processor.save_pretrained(DRIVE_ADAPTER)
print("adapter saved to", DRIVE_ADAPTER)

# %% [markdown]
# ## OPTIONAL validation cell — transcribe the WILD clips with base+adapter
# Zip your wild clips locally (`cd ~/sung_tests && zip clips.zip *`), upload when
# prompted, and bring back `transcripts_pilot.json`. Score it locally by feeding
# these transcripts through the matcher and re-running
# `scripts/precision_coverage_curve.py` — that is the go/no-go for phase B.

# %% Validation (optional)
from google.colab import files
import io
from peft import PeftModel

os.makedirs("wild", exist_ok=True)
up = files.upload()  # clips.zip
with zipfile.ZipFile(io.BytesIO(up[list(up)[0]])) as z:
    z.extractall("wild")
clips = sorted(f for f in os.listdir("wild")
               if f.lower().endswith((".m4a", ".wav", ".mp3", ".flac")))

base = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL)
tuned = PeftModel.from_pretrained(base, DRIVE_ADAPTER).to("cuda").eval()
forced = processor.get_decoder_prompt_ids(language=LANG, task="transcribe")

out = {}
for f in clips:
    y, _ = librosa.load(f"wild/{f}", sr=16000, mono=True)
    feats = processor.feature_extractor(y, sampling_rate=16000,
                                        return_tensors="pt").input_features.to("cuda")
    with torch.no_grad():
        # no_repeat_ngram_size + repetition_penalty kill the degenerate loops
        # ("vAli vAli vAli...") the overfit adapter falls into — a generation
        # artifact, not a retraining need. This cleans transcripts in place.
        ids = tuned.generate(feats, forced_decoder_ids=forced,
                             max_new_tokens=100, no_repeat_ngram_size=3,
                             repetition_penalty=1.5, num_beams=1)
    out[f] = processor.tokenizer.batch_decode(ids, skip_special_tokens=True)[0]
    print(f, "->", out[f][:80])
json.dump(out, open("transcripts_pilot.json", "w"), ensure_ascii=False, indent=1)
files.download("transcripts_pilot.json")

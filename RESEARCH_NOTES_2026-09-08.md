# Research comparison and implementation decisions

Published scores are not interchangeable with live, unsegmented, open-set
concert accuracy. This repository's source/artist-disjoint development evidence,
the small AV test, and published recording-level benchmarks remain separate.

## Sequence learning

[DeepSRGM (2024)](https://arxiv.org/html/2402.10168v1) reports 88.1% on the
40-raga CompMusic task using an LSTM ensemble, annotated tonic normalization,
and whole-recording voting. Its described recording-held-out evaluation is not
the same as our artist-held-out/open-set task. It supports testing longer
temporal evidence, but does not establish that copying its network will deliver
that accuracy here. Its printed triplet-loss equation uses `min(..., 0)`;
implementation would need the usual nonnegative margin violation, not a blind
copy of that formula.

## Direction-conditioned pitch

[Sequential Pitch Distributions (2023)](https://aimc2023.pubpub.org/pub/j9v30p0j/release/1)
reports 88.13% on Carnatic reference-pitch data. We implemented an explicitly
different, bounded-excursion variant with silence boundaries and last-start
resetting, using the existing kernel classifier instead of its learned KNN
ensemble. The matched 382-track artist-disjoint experiment scored only 58.12%,
versus 86.39% for the current TDMS kernel. It is not promoted. This failure does
not refute the published method: interval enumeration and model combination
differ, and the evaluation is stricter.

## Unknown ragas

[Identification and Clustering of Unseen Ragas (ISMIR 2025)](https://ismir2025program.ismir.net/poster_256.html)
separates unknown-class detection from clustering. That distinction matters:
clustering unlabeled audio does not by itself assign correct named raga labels.
The abstract describes uncertainty-based rejection and contrastive learning;
we have not reproduced its method or claimed its performance for Carnatic audio.

## Current decision

Retain the measured kernel recognizer and independent-artist melody alignment.
Longer context and broader existing vocabulary have produced the clearest
development gains. Production acceptance and reliable long-concert item
boundaries remain unresolved; no research artifact has replaced deployed models.

## Neural pitch frontend

[RMVPE](https://arxiv.org/abs/2306.15412) explicitly targets vocal pitch in
polyphonic music. The original paper repository is
[Dream-High/RMVPE](https://github.com/Dream-High/RMVPE); the separate
[RVC publisher checkpoint](https://huggingface.co/lj1995/VoiceConversionWebUI)
has an MIT model-card declaration. The bounded ONNX experiment follows a pinned
RVC preprocessing/decoder contract, with its source license retained in
THIRD_PARTY_RMVPE.md. Its synthetic tone test is not evidence of Carnatic
melody accuracy, and the RVC checkpoint is not claimed as the paper's exact
training/evaluation reproduction.

## Composed reference passages

The section-aware song diagnostic treats muktayi/mukthayi swaras as composed
material, separate from kalpana swaras. The Music Academy's
[1987 journal, “Swara Decorations in Karnatic Music”](https://musicacademymadras.in/catalogue/files/journals/Vol.58_1987.pdf)
discusses attributed composed swara additions, including a muktayi swaram.
Existing section annotations—not inferred song boundaries—select this optional
reference arm. Unannotated recordings retain full-reference fallback, and
removed passages never shrink the answerable-query denominator.

## Recording-to-work metadata

The [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) exposes
recording `work-rels` and requires an identifying User-Agent and no more than
one request per second. The new CompMusic resolver spaces requests by at least
3 seconds, locks against concurrent local instances, and caps response size.
It does not search by title. A recording with multiple performed works is
quarantined rather than forced into a single composition identity. Initial
public requests returned HTTP 503; subsequent intermittent recovery enabled
the separately evaluated partial catalogs documented in OVERHAUL_EXECUTION.md.
Explicit generic improvisation work entities are excluded from song references.
The fixed 477-recording lookup has now completed; full-catalog evaluation is
documented alongside the preserved partial checkpoints.

## Foundation representation screening

The official [MERT-v1-95M](https://huggingface.co/m-a-p/MERT-v1-95M) and
[MERT-v0-public](https://huggingface.co/m-a-p/MERT-v0-public) model cards both
declare CC-BY-NC-4.0. Neither is silently admitted to the production path.
The official [MusicFM repository](https://github.com/minzwon/musicfm) releases
an FMA-trained checkpoint, and its linked
[model card](https://huggingface.co/minzwon/MusicFM/blob/main/README.md) declares
MIT. Its authors explicitly caution that frozen representations do not
inherently learn musical keys. It remains an untested possible representation
baseline, not an established solution to Carnatic raga grammar; no MusicFM
weights have been downloaded or executed in this session.

## Matched Demucs frontend diagnostic

The [publisher repository](https://github.com/facebookresearch/demucs) identifies
`htdemucs` as the single, non-fine-tuned Hybrid Transformer checkpoint and
documents split CPU inference. Its reported source-separation benchmarks are
not Carnatic raga evaluations. The local diagnostic authenticates the existing
checkpoint, follows publisher waveform normalization/restoration, fixes random
shifts to zero, and keeps the original mixed-audio tonic unchanged. Installed
version, hash, settings and license notice are recorded in THIRD_PARTY_DEMUCS.md.
Any result applies to this matched diagnostic, not the publisher's benchmark.
# MusicFM implementation feasibility follow-up (2026-09-09)

Official sources rechecked: https://github.com/minzwon/musicfm,
https://huggingface.co/minzwon/MusicFM/tree/main, and
https://raw.githubusercontent.com/minzwon/musicfm/master/model/musicfm_25hz.py.
The hosted FMA and MSD checkpoints are each approximately 1.32 GB, with MIT
license metadata. The implementation uses a 12-layer, width-1024 Conformer
and 24 kHz audio. Its constructor fetches a separate pretrained Conformer
configuration and uses an unrestricted `torch.load`; a local pilot must pin
all artifacts and use restricted checkpoint loading, not execute that loader
unchanged. The README pooling example averages the last axis despite its
batch/time/channel comment; actual returned tensor shape must be verified
before pooling. A subsequent pinned MusicFM-MSD pilot now produces finite
250x1024 frame embeddings on one ten-second source-hashed excerpt; a repeat
produces a byte-identical file. See `THIRD_PARTY_MUSICFM.md` and
`OVERHAUL_EXECUTION.md` for pins, compatibility migration and timings. This is
not evidence of Carnatic accuracy or a selected production architecture.

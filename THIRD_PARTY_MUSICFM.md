# MusicFM pilot provenance

This optional, local research frontend uses MusicFM-MSD, not a trained Carnatify
raga or song classifier. It is not included in deployed assets.

- Source: https://github.com/minzwon/musicfm at
  `b83ebedb401bcef639b26b05c0c8bee1dc2dfe71`.
- Weights/stats: https://huggingface.co/minzwon/MusicFM at
  `4513b38bc25ad1d227b1980819b9691ba97f4d87`.
- Checkpoint SHA-256:
  `218b483a0256ddef736267425fabb166fd97008983696bb9270def464b47bded`.
- Conformer configuration: `facebook/wav2vec2-conformer-rope-large-960h-ft`
  at `6b36ef01c6443c67ae7ed0822876d091ab50e4aa`; only configuration, not that
  model's weights, is downloaded.

The original full license and unmodified source headers are retained in
`data/overhaul/models/musicfm/musicfm/LICENSE` and the downloaded source files.
The upstream license assigns MIT to these modules and Apache-2.0 to
`flash_conformer.py`, which is neither downloaded nor used. The hosted model
repository carries MIT metadata. Preserve upstream notices with any distribution.

Carnatify's inference-only loader uses the pinned convolution and mel frontend,
installed Transformers' Conformer, local configuration, checksum verification,
and `torch.load(weights_only=True)` with only the built-in `set` allowlisted.
It does not invoke upstream's downloading/unrestricted-loading constructor.
Unused quantizer/output-head/CLS state is explicitly checked; all encoder state
must load strictly. Input is bounded to 1–30 seconds at 24 kHz.
Older `weight_g`/`weight_v` state names are mapped to the equivalent current
PyTorch parametrization names; convolution equivalence is unit-tested.
Outputs retain
time/channel axes; temporal pooling is explicit, not copied from ambiguous
README axis comments. No tonic invariance or Carnatic accuracy is presumed.

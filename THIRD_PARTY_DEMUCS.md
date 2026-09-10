# Demucs diagnostic frontend

The optional matched field diagnostic uses installed Demucs 4.0.1 and the
already-cached `htdemucs` single-model checkpoint `955717e8-8726e21a.th`.
Source: https://github.com/facebookresearch/demucs

Checkpoint SHA-256:
`8726e21a993978c7ba086d3872e7608d7d5bfca646ca4aca459ffda844faa8b4`

The adapter verifies this full digest before permitting the upstream legacy
checkpoint loader to deserialize it. It does not fetch or execute arbitrary
checkpoints. The normalization/restoration follows the installed publisher CLI.
The diagnostic uses zero random shifts, overlap .25, CPU split inference and
independent duplicated mono channels. It retains the original-mix tonic for
raga features and is not enabled in default inference. These settings are not
a reproduction of the publisher's source-separation benchmark.

The installed package's license notice is retained below.

## MIT License

Copyright (c) Meta Platforms, Inc. and affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

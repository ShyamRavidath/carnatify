# RMVPE experiment provenance

The optional ONNX pitch frontend follows the preprocessing and local-salience
decoder in RVC's `infer/rmvpe.py` at commit
`81eed5e8f68b6bed1789f682fe78cdd324495afc`. Carnatify uses bounded CPU ONNX
inference with one-second chunk context, not RVC voice conversion.

Source: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

Weights: https://huggingface.co/lj1995/VoiceConversionWebUI
at revision `e6d0c1a17da07c33557852f9dfa2bd44cc75737d`, `rmvpe.onnx`,
361,688,443 bytes, SHA256
`5370e71ac80af8b4b7c793d27efd51fd8bf962de3a7ede0766dac0befa3660fd`.
The publisher model card declares MIT. This is a research frontend experiment;
neither its Carnatic accuracy nor production suitability is assumed.

## RVC source license

MIT License

Copyright (c) 2023 liujing04
Copyright (c) 2023 源文雨
Copyright (c) 2023 Ftps

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

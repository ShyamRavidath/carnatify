"""Small tonic-relative temporal baseline; silence retains elapsed time.

This is a local sequence-model experiment, not a DeepSRGM reproduction.
"""
import numpy as np
import torch
from torch import nn

VERSION = 'relative_circular_moments_10hz_tcn_v1'
CHANNELS = 13


def sequence_features(f0, tonic, hop_s, duration_s=60):
    f0 = np.asarray(f0, dtype=float)
    if f0.ndim != 1 or not np.isfinite(tonic) or tonic <= 0 or not np.isfinite(hop_s) or hop_s <= 0:
        raise ValueError('Invalid pitch sequence')
    if not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError('Invalid sequence duration')
    n = int(np.ceil(duration_s*10))
    output = np.zeros((CHANNELS,n), dtype=np.float32)
    bins = np.floor(np.arange(len(f0))*hop_s*10).astype(int)
    valid = np.isfinite(f0)&(f0>0)&(bins<n)
    phase = 2*np.pi*np.log2(f0[valid]/tonic)
    bins_valid = bins[valid]
    counts = np.bincount(bins_valid, minlength=n)
    total = np.bincount(bins[bins<n], minlength=n)
    output[-1] = counts/np.maximum(total,1)
    for harmonic in range(1,7):
        output[2*(harmonic-1)] = np.bincount(bins_valid,weights=np.cos(harmonic*phase),minlength=n)/np.maximum(counts,1)
        output[2*(harmonic-1)+1] = np.bincount(bins_valid,weights=np.sin(harmonic*phase),minlength=n)/np.maximum(counts,1)
    return output


class PitchTemporalConv(nn.Module):
    def __init__(self, n_classes, width=32):
        super().__init__()
        self.input = nn.Conv1d(CHANNELS,width,1)
        self.blocks = nn.ModuleList([
            nn.Sequential(nn.Conv1d(width,width,7,padding=3*d,dilation=d),
                          nn.GroupNorm(4,width),nn.GELU(),nn.Dropout(.1))
            for d in (1,2,4,8,16)])
        self.attention = nn.Conv1d(width,1,1)
        self.head = nn.Linear(width*2,n_classes)

    def forward(self, x):
        h=self.input(x)
        for block in self.blocks:
            h=h+block(h)
        weights=torch.softmax(self.attention(h),dim=-1)
        mean=(h*weights).sum(-1)
        variance=((h-mean.unsqueeze(-1)).square()*weights).sum(-1)
        return self.head(torch.cat([mean,torch.sqrt(variance+1e-5)],dim=-1))

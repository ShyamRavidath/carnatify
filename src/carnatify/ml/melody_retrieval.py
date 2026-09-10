"""Tonic-relative, time-aware melody alignment for independent renditions.

This is a retrieval candidate, not a validated song identity oracle. Frequency
Hz carries voicing explicitly, so tonic Sa is never mistaken for silence.
"""
from __future__ import annotations
import numpy as np
from numba import njit


def composed_reference_sequences(frequencies,times,tonic,hop_s,sections,frame_s=.5):
    """Separate explicitly composed passages; never join across excluded time.

    Unannotated performances retain the full-reference fallback. Annotated
    performances with no supported composed passage contribute no sequence,
    not an improvised substitute. Callers must retain their coverage denominator.
    """
    f=np.asarray(frequencies);times=np.asarray(times)
    if f.ndim!=1 or times.shape!=f.shape or not np.isfinite(times).all() or np.any(np.diff(times)<=0):
        raise ValueError('Invalid reference time grid')
    if not sections:return [melody_sequence(f,tonic,hop_s,frame_s)]
    fixed={'pallavi','anupallavi','anupallvi','charanam','charanams','jatisvara','jati_svaram',
           'chittai_svara','chittai_svaram','chittai_svaras','chittai_svarams',
           'mukthayi_svara','mukthayi_svaram','muktayi_svara','muktayi_svaram'}
    ranges=[]
    for section in sections:
        kind=section['kind'].strip().lower().replace(' ','_').replace('-','_')
        a,b=section['start_s'],section['end_s']
        if not np.isfinite([a,b]).all() or not 0<=a<b:raise ValueError('Invalid reference section')
        if kind in fixed or kind.startswith('charanam_'):
            ranges.append((a,b))
    # Union overlaps of composed annotations, but preserve real gaps.
    merged=[]
    for a,b in sorted(ranges):
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    result=[]
    for a,b in merged:
        i,j=np.searchsorted(times,[a,b])
        seq=melody_sequence(f[i:j],tonic,hop_s,frame_s)
        if len(seq)>=8:result.append(seq)
    return result


def melody_sequence(frequencies,tonic,hop_s,frame_s=.5):
    f=np.asarray(frequencies,dtype=float)
    if (f.ndim!=1 or not np.isfinite([tonic,hop_s,frame_s]).all() or
        tonic<=0 or hop_s<=0 or frame_s<=0):
        raise ValueError('Invalid melody parameters')
    width=max(1,round(frame_s/hop_s));n=len(f)//width
    if n==0:return np.empty((0,24),dtype=np.float32)
    f=f[:n*width].reshape(n,width)
    valid=np.isfinite(f)&(f>0)
    # Distribution within each real-time frame, not median pitch: gamaka motion
    # and multi-note transitions should not invent a stationary midpoint note.
    voiced=np.sum(valid,axis=1)>=max(1,width//4)
    out=np.zeros((n,24),dtype=np.float32)
    row,col=np.nonzero(valid)
    bins=np.rint(24*np.log2(f[row,col]/tonic)).astype(int)%24
    np.add.at(out,(row,bins),1.)
    out=out+.3*np.roll(out,1,axis=1)+.3*np.roll(out,-1,axis=1)
    out/=np.maximum(np.linalg.norm(out,axis=1,keepdims=True),1e-12)
    # Voiced-time compression is explicit here, appropriate to rendition tempo
    # alignment. It is not used to infer wall-clock concert boundaries.
    return out[voiced]


@njit(cache=True)
def _subsequence_cost(cost):
    """Slope-limited subsequence DTW: steps (1,1), (1,2), (2,1)."""
    m,n=cost.shape
    d=np.full((m+1,n+1),np.inf)
    d[0,:]=0.
    for i in range(1,m+1):
        for j in range(1,n+1):
            c=cost[i-1,j-1]
            best=d[i-1,j-1]+c
            if j>=2:best=min(best,d[i-1,j-2]+c+.05)
            if i>=2:best=min(best,d[i-2,j-1]+c+cost[i-2,j-1]+.05)
            d[i,j]=best
    endpoint=np.argmin(d[m,1:])+1
    return d[m,endpoint]/m,endpoint


def _alignment_shifts(q,r,transposition_invariant):
    shifts=[0]
    if transposition_invariant:
        qp=q.mean(0);rp=r.mean(0)
        shift=max(range(0,24,2),key=lambda s:float(qp@np.roll(rp,s)))
        if shift:shifts.append(shift)
    return shifts


def directional_cost(forward,reverse):
    """Fixed null-normalized score; no directional evidence maps to one half."""
    if not np.isfinite([forward,reverse]).all() or min(forward,reverse)<0:
        raise ValueError('Invalid directional alignment costs')
    return float(forward/(forward+reverse)) if forward+reverse>1e-12 else .5


def directional_distances(query,reference,transposition_invariant=False):
    """Paired DTW with identical pitch shifts and reversed query-time costs.

    This preserves marginal pitch evidence exactly, including floating-point
    tie handling in the global shift selector. No titles or query labels enter.
    """
    q=np.asarray(query,dtype=np.float32);r=np.asarray(reference,dtype=np.float32)
    if q.ndim!=2 or r.ndim!=2 or q.shape[1]!=24 or r.shape[1]!=24:
        raise ValueError('Expected 24-bin melody frames')
    if not np.isfinite(q).all() or not np.isfinite(r).all():raise ValueError('Nonfinite melody')
    if len(q)<8 or len(r)<len(q)//2:return float('inf'),float('inf')
    forward=[];reverse=[]
    for shift in _alignment_shifts(q,r,transposition_invariant):
        cost=np.maximum(0,1-q@np.roll(r,shift,axis=1).T)
        forward.append(_subsequence_cost(cost)[0])
        reverse.append(_subsequence_cost(np.ascontiguousarray(cost[::-1]))[0])
    return float(min(forward)),float(min(reverse))


def subsequence_distance(query,reference,transposition_invariant=False,query_patches=1):
    q=np.asarray(query,dtype=np.float32);r=np.asarray(reference,dtype=np.float32)
    if q.ndim!=2 or r.ndim!=2 or q.shape[1]!=24 or r.shape[1]!=24:
        raise ValueError('Expected 24-bin melody frames')
    if not np.isfinite(q).all() or not np.isfinite(r).all():raise ValueError('Nonfinite melody')
    if query_patches not in (1,3):raise ValueError('Unsupported query patch count')
    if len(q)<8 or len(r)<len(q)//2:return float('inf')
    if query_patches==3 and len(q)<24:return float('inf')
    # Global song transposition, not a maximum-raga-confidence tonic vote.
    shifts=_alignment_shifts(q,r,transposition_invariant)
    # Optional development arm: align voiced-time thirds independently and use
    # their median cost. One GLOBAL pitch shift is shared by all thirds; local
    # phrase order is relaxed, so this is not equivalent to full-query DTW.
    patches=np.array_split(q,query_patches)
    return min(float(np.median([_subsequence_cost(np.maximum(0,1-p@np.roll(r,s,axis=1).T))[0]
                                for p in patches])) for s in shifts)

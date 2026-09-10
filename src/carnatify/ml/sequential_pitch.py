"""Direction-conditioned pitch distributions inspired by Narasinh & Raja (2023).

Source: https://aimc2023.pubpub.org/pub/j9v30p0j/release/1
This is an explicit bounded-excursion variant, not an exact reproduction of
the paper's unspecified interval enumeration or its learned KNN ensemble.
Silence breaks an excursion; revisiting its start resets it. No labels enter.
"""
import numpy as np
from numba import njit

SPD_VERSION='spd120_bounded_excursions_v1'


@njit(cache=True)
def _excursions(pitches,relaxation):
    result=np.zeros((12,12,2,120),dtype=np.float32)
    global_pd=np.zeros(120,dtype=np.float32)
    for p in pitches:
        if p>=0:global_pd[p]+=1
    if global_pd.sum()==0:return result
    global_pd/=global_pd.sum()
    for start in range(12):
        for end in range(12):
            for direction_index in range(2):
                counts=np.zeros(120,dtype=np.float32)
                active=False
                direction=1 if direction_index==0 else -1
                distance=((end-start)*10*direction)%120
                if start!=end:
                    for p in pitches:
                        if p<0:
                            active=False
                            continue
                        position=((p-start*10)*direction)%120
                        allowed=position<=distance+relaxation or position>=120-relaxation
                        near_start=position<=relaxation or position>=120-relaxation
                        near_end=abs(position-distance)<=relaxation
                        if not allowed:
                            active=False
                        elif near_start:
                            counts[:]=0
                            counts[p]+=1
                            active=True
                        elif active:
                            counts[p]+=1
                            if near_end:
                                result[start,end,direction_index]+=counts
                                active=False
                mass=result[start,end,direction_index].sum()
                if mass:
                    result[start,end,direction_index]/=mass
                else:
                    result[start,end,direction_index]=global_pd
    return result


def sequential_pitch_distribution(frequencies,tonic,relaxation=4):
    f=np.asarray(frequencies,dtype=float)
    if f.ndim!=1 or not np.isfinite(tonic) or tonic<=0:
        raise ValueError('Expected one-dimensional pitch and positive tonic')
    if relaxation not in {0,2,4}:raise ValueError('Relaxation must be 0, 2 or 4 ten-cent bins')
    valid=np.isfinite(f)&(f>0)
    pitches=np.full(len(f),-1,dtype=np.int32)
    pitches[valid]=np.rint(120*np.log2(f[valid]/tonic)).astype(np.int32)%120
    return _excursions(pitches,relaxation)

"""Automatic temporal decoding from overlapping raga and audio-event evidence."""
from __future__ import annotations
import numpy as np


def candidate_only_segments(segments):
    """Preserve development candidates without asserting validated identities."""
    result=[]
    for segment in segments:
        row=dict(segment)
        if row['status']=='recognized':
            row.update(candidate_raga=row['raga'],raga=None,status='unverified_candidate')
        result.append(row)
    return result


def viterbi_states(probabilities,switch_penalty=3.,unknown_index=None,overlap_factor=1.):
    """O(T*C) penalized decoding; unknown transitions can respond to short speech.

    overlap_factor avoids counting heavily overlapping observations as independent
    evidence. This is a segment proposal algorithm, not semantic ground truth.
    """
    p=np.asarray(probabilities,dtype=float)
    if p.ndim!=2 or not len(p) or p.shape[1]<2 or not np.isfinite(p).all() or (p<0).any():
        raise ValueError('Invalid temporal probabilities')
    if overlap_factor<=0 or switch_penalty<0 or np.any(p.sum(1)<=0):
        raise ValueError('Invalid decoding configuration')
    p=p/p.sum(1,keepdims=True)
    emissions=np.log(np.maximum(p,1e-30))/overlap_factor
    score=emissions[0].copy();back=np.zeros(p.shape,dtype=np.int32)
    states=np.arange(p.shape[1])
    for t in range(1,len(p)):
        best=np.argsort(score)[-2:]
        other=np.where(states==best[-1],best[-2],best[-1])
        change=score[other]-switch_penalty
        origin=other.copy()
        if unknown_index is not None:
            unknown_score=score[unknown_index]-.2
            use_unknown=unknown_score>change
            change=np.where(use_unknown,unknown_score,change)
            origin=np.where(use_unknown,unknown_index,origin)
            change[unknown_index]=score[best[-1]]-.2
            origin[unknown_index]=best[-1]
        stay=score>=change
        back[t]=np.where(stay,states,origin)
        score=np.maximum(score,change)+emissions[t]
    out=np.zeros(len(p),dtype=int);out[-1]=score.argmax()
    for t in range(len(p)-1,0,-1):out[t-1]=back[t,out[t]]
    return out


def decode_concert(events,windows,classes,threshold=.5,switch_penalty=3.,overlap_factor=6.):
    """Return full coverage timeline without consuming any manual boundaries."""
    if not events:return []
    classes=list(classes);k=len(classes)
    # AudioSet percussion is also present during singing. Require sustained
    # event evidence before treating it as a separate instrumental-only region;
    # never let one ten-second tag create two item boundaries.
    percussion=np.array([e['state']=='percussion' for e in events])
    percussion_evidence=np.array([e.get('pitch_percussion_probability',.995 if is_percussion else .005)
                                  for e,is_percussion in zip(events,percussion)],dtype=float)
    if not np.isfinite(percussion_evidence).all() or np.any((percussion_evidence<0)|(percussion_evidence>1)):
        raise ValueError('Invalid pitch-activity evidence')
    percussion_evidence=np.clip(percussion_evidence,.005,.995)
    # Preserve the optional detector's uncertainty. Turning a barely-positive
    # score into .995 manufactured short, overconfident percussion segments.
    activity=viterbi_states(np.c_[1-percussion_evidence,percussion_evidence],switch_penalty=6.)
    event_states=[('percussion' if activity[i] else 'music')
                  if e['state'] in {'music','percussion'} else e['state']
                  for i,e in enumerate(events)]
    distributions=[];raw=[]
    for event,event_state in zip(events,event_states):
        center=(event['start_s']+event['end_s'])/2
        relevant=[w for w in windows if w['start_s']<=center<w['end_s'] and w.get('probabilities')]
        p=np.zeros(k)
        for w in relevant:
            weight=max(.05,1-abs(center-(w['start_s']+w['end_s'])/2)/((w['end_s']-w['start_s'])/2))
            p+=weight*np.array([w['probabilities'].get(c,0) for c in classes])
        if p.sum():p/=p.sum()
        raw.append(p)
        # Uncertain raga rankings must not manufacture item boundaries. Preserve
        # their raw candidates for reporting, but let only threshold-passing
        # evidence change the melodic state. Activity boundaries are independent.
        temporal_p=p if p.size and p.max()>=threshold else np.full(k,1/k)
        melodic=(event_state=='music' and bool(relevant))
        mixed=(event_state=='uncertain' and bool(relevant))
        # Activity uncertainty and raga uncertainty are different quantities.
        # A 0.5 unknown mass would overwhelm every individual raga in a large
        # vocabulary, manufacturing boundaries at each uncertain event tag.
        known_mass=.999 if melodic else (.98 if mixed else .001)
        if not p.sum():known_mass=0
        distributions.append(np.r_[temporal_p*known_mass,1-known_mass])
    states=viterbi_states(distributions,switch_penalty,unknown_index=k,overlap_factor=overlap_factor)
    # The shared unknown raga state is not a shared activity identity. Adjacent
    # speech, applause and percussion must retain their own timeline regions.
    kinds=np.array(['melodic_music' if state!=k else event_states[i]
                    for i,state in enumerate(states)])
    boundaries=np.r_[0,np.flatnonzero((states[1:]!=states[:-1])|(kinds[1:]!=kinds[:-1]))+1,len(states)]
    segments=[]
    for a,b in zip(boundaries,boundaries[1:]):
        p=np.mean(raw[a:b],axis=0)
        if p.sum():p/=p.sum()
        order=np.argsort(-p)[:5]
        state=int(states[a]);score=float(p[order[0]]) if p.sum() else 0.
        recognized=state!=k and score>=threshold
        segments.append(dict(start_s=events[a]['start_s'],end_s=events[b-1]['end_s'],
            kind=str(kinds[a]),
            raga=classes[order[0]] if recognized else None,
            status='recognized' if recognized else 'uncertain',score=score,
            candidates=[dict(raga=classes[i],score=float(p[i])) for i in order] if p.sum() else [],
            label_origin='automatic_prediction',n_event_windows=int(b-a)))
    return segments

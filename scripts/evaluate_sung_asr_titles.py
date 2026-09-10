"""Closed-vocabulary title probe, not cross-rendition melody accuracy or WER."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from identify_clip import translit_fold,soft
from scripts.raga_pipeline import sha,write_json
from carnatify.ml.composition_catalog import CompositionCatalog


def usable_text(hypothesis):
    """Fixed decoder-diagnostic screen; not a semantic correctness guarantee."""
    texts=[]
    for segment in hypothesis.get('segments',[]):
        values=[segment.get(k) for k in ('avg_logprob','no_speech_prob','compression_ratio')]
        if any(v is None for v in values) or not np.isfinite(values).all():continue
        logprob,no_speech,compression=values
        text=segment.get('text') or ''
        if logprob>=-1 and no_speech<=.6 and compression<=2.4 and any(c.isalpha() for c in text):
            texts.append(text)
    return soft(translit_fold(' '.join(texts)))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,required=True);ap.add_argument('--catalog',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    plan_path=args.run/'plan.json';result_path=args.run/'result.json'
    plan=json.loads(plan_path.read_text());data=json.loads(result_path.read_text())
    if not data['complete'] or data['plan_sha256']!=sha(plan_path):raise ValueError('ASR pilot incomplete or changed')
    if len(data['rows'])!=len(plan['queries']) or [r['query'] for r in data['rows']]!=plan['queries']:
        raise ValueError('ASR query cohort mismatch')
    corpus_path=ROOT/'data/overhaul/annotated_corpus.json'
    if sha(corpus_path)!=plan['corpus_sha256']:raise ValueError('Corpus changed')
    corpus={r['track']:r for r in json.loads(corpus_path.read_text())['rows']}
    sidecar=json.loads(args.catalog.with_suffix('.json').read_text())
    if sidecar['catalog_sha256']!=sha(args.catalog):raise ValueError('Catalog provenance mismatch')
    catalog=CompositionCatalog(args.catalog);aliases={}
    for row in catalog.metadata:
        title=soft(translit_fold(row['title']))
        if title.strip():aliases[(row['work_id'],title)]=row['title']
    keys=sorted(aliases);vectorizer=TfidfVectorizer(analyzer='char',ngram_range=(3,5),lowercase=False)
    references=vectorizer.fit_transform([k[1] for k in keys]);results=[]
    for row in data['rows']:
        if row['plan_sha256']!=sha(plan_path):raise ValueError('ASR receipt plan mismatch')
        hypotheses=row.get('hypotheses',{'auto':row.get('hypothesis',{})})
        texts={lane:usable_text(h) for lane,h in hypotheses.items()};scores={}
        for lane,text in texts.items():
            if not text.strip():continue
            similarities=(references@vectorizer.transform([text]).T).toarray().ravel()
            for (work,title),value in zip(keys,similarities):
                if value>0 and (work not in scores or value>scores[work]['score']):
                    scores[work]=dict(work_id=work,title=aliases[(work,title)],score=float(value),lane=lane)
        ranked=sorted(scores.values(),key=lambda r:(-r['score'],r['work_id']))
        truth=corpus[row['query']['track']]['work_id']
        results.append(dict(track=row['query']['track'],work_id=truth,
            in_text_vocabulary=truth in {k[0] for k in keys},usable_lanes=[k for k,v in texts.items() if v.strip()],
            rank=next((i+1 for i,r in enumerate(ranked) if r['work_id']==truth),None),top5=ranked[:5]))
    report=dict(status='closed metadata-title-vocabulary development pilot; not WER, fresh test, or validated identity',
        asr_report_sha256=sha(result_path),plan_sha256=sha(plan_path),catalog_sha256=sha(args.catalog),
        policy='fixed diagnostic screen; transliterated char 3-5gram TFIDF; max across fixed lanes and work aliases',
        n_queries=len(results),n_in_text_vocabulary=sum(r['in_text_vocabulary'] for r in results),
        n_top1=sum(r['rank']==1 for r in results),n_top5=sum(r['rank'] is not None and r['rank']<=5 for r in results),
        n_with_usable_text=sum(bool(r['usable_lanes']) for r in results),rows=results)
    write_json(args.out,report);print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))


if __name__=='__main__':main()

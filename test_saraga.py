import mirdata
from collections import Counter

saraga = mirdata.initialize('saraga_carnatic', data_home='/Users/shyamravidath/carnatify')
saraga.download(partial_download=['index'])
tracks = saraga.load_tracks()

raga_counts = Counter()
usable = []

for track_id, track in tracks.items():
    meta = track.metadata
    if not meta or not meta.get('raaga'):
        continue
    pitch = track.pitch_vocal
    if pitch is None:
        continue
    raga_name = meta['raaga'][0]['name']
    raga_counts[raga_name] += 1
    usable.append(track_id)

print(f"Usable tracks (raga label + pitch vocal): {len(usable)}")
print(f"Distinct ragas: {len(raga_counts)}")
print("\nRaga distribution:")
for raga, count in raga_counts.most_common(20):
    print(f"  {raga}: {count}")
import mirdata
from collections import Counter

raga_ds = mirdata.initialize('compmusic_raga', data_home='/Users/shyamravidath/carnatify')
raga_ds.download(partial_download=['features'])

tracks = raga_ds.load_tracks()

raga_counts = Counter()
usable = []

for track_id, track in tracks.items():
    if track.tradition != 'carnatic':
        continue
    if track.raga and track.pitch:
        raga_counts[track.raga] += 1
        usable.append(track_id)

print(f"Usable Carnatic tracks: {len(usable)}")
print(f"Distinct ragas: {len(raga_counts)}")
print("\nTop 20 ragas:")
for raga, count in raga_counts.most_common(20):
    print(f"  {raga}: {count}")
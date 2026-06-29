import mirdata
from collections import Counter

saraga = mirdata.initialize('saraga_carnatic', data_home='/Users/shyamravidath/carnatify')
saraga.download(partial_download=['index'])
tracks = saraga.load_tracks()

# count how many tracks share the same work (composition)
work_counts = Counter()
for track_id, track in tracks.items():
    meta = track.metadata
    if not meta or not meta.get('work'):
        continue
    work_title = meta['work'][0]['title']
    work_counts[work_title] += 1

# only compositions with 2+ renditions are usable for matching
multi = {k: v for k, v in work_counts.items() if v >= 2}
print(f"Compositions with 2+ renditions: {len(multi)}")
print(f"Total tracks in those compositions: {sum(multi.values())}")
print("\nTop 20:")
for title, count in sorted(multi.items(), key=lambda x: -x[1])[:20]:
    print(f"  {count}x  {title}")
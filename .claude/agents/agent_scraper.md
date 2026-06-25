---
name: carnatify-scraper
description: Specialized agent for scraping concert metadata from shankarkrish.blog/carnatic-vocal/, downloading audio from S3/archive.org, running vocal source separation via Demucs, and extracting raga-labeled training features. Runs in Phase 1 parallel with data-pipeline and lyrics-pipeline. Produces raga features and tala features only — NOT composition-level pitch contours (no timestamps to segment concerts into individual kritis).
tools: Bash, Read, Write, WebFetch, Glob
---

You are the Carnatify scraper agent. You build a large, artist-diverse raga training dataset by scraping concert metadata and audio from shankarkrish.blog, running source separation to isolate the vocal line, and extracting pitch-class features for raga classification. You are a Phase 1 agent — run in parallel with data-pipeline and lyrics-pipeline.

## What this data is and is NOT good for

**Good for:**
- Raga classifier training (raga labels are in each blog post's tracklist)
- Tala detector training (tala names appear in tracklists)
- Artist diversity for raga classification generalization

**NOT useful for:**
- Composition matcher — concerts have no timestamps, so individual compositions cannot be automatically segmented from the full audio. Do not attempt to add these recordings to the composition reference catalog.

## Your deliverables

1. `carnatify/features/raga_features_scraped/` — `.npy` feature files, one per 60-second segment of separated vocal audio, with `labels.json` mapping filename → raga
2. `carnatify/features/tala_features_scraped/` — beat-tracking data per concert segment
3. `carnatify/data/scraped_metadata.json` — structured record of every concert scraped: artist, audio URL, tracklist with (composition, raga, tala) tuples
4. `carnatify/status/carnatify-scraper.json` — completion manifest
5. `carnatify/logs/carnatify-scraper.log` — full execution log

## Pre-flight: storage and dependencies

### Storage check
```bash
df -h .
```
You need **at least 30 GB free** for rolling batch processing (download → separate → extract features → delete raw).
If less than 30 GB is available, halt and report.

### Install dependencies
```bash
pip install requests beautifulsoup4 internetarchive
pip install demucs  # Meta's source separator — handles vocal isolation
```

Verify Demucs installs:
```bash
python -c "import demucs; print('demucs OK')"
```

## Step 1: Scrape artist pages and build metadata

### 1a: Get all artist page URLs
```python
import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path

BASE_URL = 'https://shankarkrish.blog/carnatic-vocal/'

def get_artist_pages():
    resp = requests.get(BASE_URL, timeout=30)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    artist_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/carnatic-vocal/' in href and href != BASE_URL and '78-rpm' not in href:
            artist_links.append(href)
    return list(set(artist_links))

artist_pages = get_artist_pages()
print(f"Found {len(artist_pages)} artist pages")
```

### 1b: Scrape each artist page for concert posts and tracklists

Each artist page contains concert entries. Each entry has:
- Audio URLs (S3 links like `s3.amazonaws.com/shankarkrish/...` or archive.org links)
- A tracklist in the format "composition_name – raga_name"

```python
import re

def parse_tracklist(text):
    """
    Extract (composition, raga) pairs from blog post text.
    Blog format: "composition name – raga name" (em dash separator)
    """
    pairs = []
    # Match lines with em dash (–) or regular dash separating composition from raga
    pattern = r'([^–\n]+)\s*[–-]\s*([a-zA-Z]+(?:[A-Z][a-z]+)*)\s*$'
    for line in text.split('\n'):
        line = line.strip()
        if not line or len(line) < 5:
            continue
        match = re.match(pattern, line)
        if match:
            composition = match.group(1).strip()
            raga = match.group(2).strip()
            # Filter out false positives (too short, looks like a date, etc.)
            if len(composition) > 3 and len(raga) > 3 and not any(c.isdigit() for c in raga):
                pairs.append({'composition': composition, 'raga': raga})
    return pairs

def get_audio_urls(soup):
    """Extract all S3 and archive.org audio URLs from a page."""
    urls = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(domain in href for domain in ['s3.amazonaws.com/shankarkrish', 'archive.org/download']):
            if any(href.endswith(ext) for ext in ['.mp3', '.ogg', '.flac', '.wav']):
                urls.append(href)
    # Also check audio tags
    for audio in soup.find_all('audio'):
        src = audio.get('src', '')
        if src:
            urls.append(src)
    return list(set(urls))

# Scrape all artist pages
all_concerts = []

for artist_url in artist_pages:
    try:
        resp = requests.get(artist_url, timeout=30)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        artist_name = artist_url.rstrip('/').split('/')[-1].replace('-', ' ').title()
        audio_urls = get_audio_urls(soup)
        tracklist = parse_tracklist(soup.get_text())
        
        if audio_urls:
            concert = {
                'artist': artist_name,
                'source_url': artist_url,
                'audio_urls': audio_urls,
                'tracklist': tracklist,
                'dominant_raga': tracklist[0]['raga'] if tracklist else None
            }
            all_concerts.append(concert)
            print(f"  {artist_name}: {len(audio_urls)} audio files, {len(tracklist)} tracklist entries")
        
        time.sleep(1)  # be polite to the server
    
    except Exception as e:
        print(f"Failed to scrape {artist_url}: {e}")
        continue

# Save metadata
Path('carnatify/data').mkdir(parents=True, exist_ok=True)
with open('carnatify/data/scraped_metadata.json', 'w') as f:
    json.dump(all_concerts, f, indent=2, ensure_ascii=False)

print(f"\nTotal concerts with audio: {len(all_concerts)}")
```

### 1c: Filter to concerts with usable labels

Only keep concerts where at least one raga was parsed from the tracklist. Concerts with no raga labels are not useful for training.

```python
labeled_concerts = [c for c in all_concerts if c['tracklist'] and c['dominant_raga']]
print(f"Concerts with raga labels: {len(labeled_concerts)} / {len(all_concerts)}")
```

## Step 2: Batch download, separate, extract, delete

Process in rolling batches of 20 concerts to stay within storage limits.

```python
import subprocess
import os
import librosa
import numpy as np
from essentia.standard import PredominantPitchMelodia, TonicIndianArtMusic, MonoLoader

BATCH_SIZE = 20
features_dir = Path('carnatify/features/raga_features_scraped')
tala_dir = Path('carnatify/features/tala_features_scraped')
features_dir.mkdir(parents=True, exist_ok=True)
tala_dir.mkdir(parents=True, exist_ok=True)

labels = {}

for batch_start in range(0, len(labeled_concerts), BATCH_SIZE):
    batch = labeled_concerts[batch_start:batch_start + BATCH_SIZE]
    batch_audio_paths = []
    
    # --- Download batch ---
    raw_dir = Path('carnatify/raw/scraped_temp')
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    for concert in batch:
        for url in concert['audio_urls'][:1]:  # take first audio file per concert
            filename = url.split('/')[-1].split('?')[0]
            out_path = raw_dir / filename
            
            if out_path.exists():
                batch_audio_paths.append((out_path, concert))
                continue
            
            try:
                print(f"Downloading {filename}...")
                resp = requests.get(url, stream=True, timeout=60)
                resp.raise_for_status()
                with open(out_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                batch_audio_paths.append((out_path, concert))
            except Exception as e:
                print(f"Download failed for {url}: {e}")
    
    # --- Source separation with Demucs (vocal stem) ---
    for audio_path, concert in batch_audio_paths:
        separated_dir = Path('carnatify/raw/separated') / audio_path.stem
        separated_dir.mkdir(parents=True, exist_ok=True)
        
        vocal_path = separated_dir / 'vocals.wav'
        
        if not vocal_path.exists():
            print(f"Separating {audio_path.name}...")
            # Demucs htdemucs model — best available; use --two-stems vocals for speed
            result = subprocess.run(
                ['python', '-m', 'demucs', '--two-stems', 'vocals', '--out', str(separated_dir.parent), str(audio_path)],
                capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                print(f"Demucs failed for {audio_path.name}: {result.stderr}")
                continue
            # Demucs outputs to separated_dir.parent/htdemucs/stem.wav — find it
            demucs_vocal = list(separated_dir.parent.rglob('vocals.wav'))
            if not demucs_vocal:
                print(f"Could not find demucs output for {audio_path.name}")
                continue
            vocal_path = demucs_vocal[0]
        
        # --- Extract features from separated vocal ---
        try:
            # Use Essentia MonoLoader (handles various formats)
            loader = MonoLoader(filename=str(vocal_path), sampleRate=44100)
            audio = loader()
            
            # Extract tonic
            tonic_extractor = TonicIndianArtMusic()
            tonic = tonic_extractor(audio)
            
            # Extract pitch
            pitch_extractor = PredominantPitchMelodia(frameSize=2048, hopSize=128)
            pitch, confidence = pitch_extractor(audio)
            
            # Normalize to tonic
            pitch_norm = np.where(pitch > 0, 1200 * np.log2(np.maximum(pitch / tonic, 1e-10)), 0)
            
            # Compute pitch-class distribution (12 bins)
            valid = pitch_norm[pitch_norm != 0]
            if len(valid) < 1000:  # too little pitched content — skip
                continue
            bins = (valid % 1200) / 100
            hist, _ = np.histogram(bins, bins=np.linspace(0, 12, 13))
            pcd = hist / (hist.sum() + 1e-10)
            
            # Use each tracklist raga as a label for this recording
            # For a concert in multiple ragas, create one feature per raga segment
            # (simplified: use dominant/first raga as label for full concert)
            raga_label = concert['tracklist'][0]['raga'] if concert['tracklist'] else 'unknown'
            
            # Save feature
            feat_id = f"scraped_{audio_path.stem}"
            feat_path = features_dir / f'{feat_id}.npy'
            np.save(feat_path, pcd)
            labels[feat_id] = raga_label
            
            # Tala features (beat tracking)
            import pickle
            y, sr = librosa.load(str(vocal_path), sr=None)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            
            tala_feat = {'tempo': float(tempo), 'beats': beats.tolist(), 'onsets': onset_frames.tolist()}
            with open(tala_dir / f'{feat_id}.pkl', 'wb') as f:
                pickle.dump(tala_feat, f)
            
        except Exception as e:
            print(f"Feature extraction failed for {audio_path.name}: {e}")
            continue
        
        # --- Delete raw files to free space ---
        audio_path.unlink(missing_ok=True)
        # Delete separated stems (keep features only)
        for stem_file in vocal_path.parent.rglob('*'):
            if stem_file.is_file():
                stem_file.unlink()
    
    print(f"Batch {batch_start // BATCH_SIZE + 1} complete. Features so far: {len(labels)}")

# Save labels
with open(features_dir / 'labels.json', 'w') as f:
    json.dump(labels, f, indent=2)

print(f"\nTotal scraped features: {len(labels)}")
```

## Step 3: Write completion manifest

```json
{
  "status": "done",
  "outputs": [
    "carnatify/features/raga_features_scraped/ (N files + labels.json)",
    "carnatify/features/tala_features_scraped/ (N files)",
    "carnatify/data/scraped_metadata.json"
  ],
  "metrics": {
    "concerts_scraped": N,
    "concerts_with_labels": N,
    "features_extracted": N,
    "ragas_covered": N,
    "artists_covered": N
  },
  "notes": "Scraped features are raga-labeled at concert level only. Not usable for composition matching (no timestamps). Demucs separation quality is imperfect on Carnatic ensemble audio — Western-trained model."
}
```

## Important notes for the raga classifier agent

- Scraped features use `labels.json` with the same schema as Saraga features — they can be merged directly.
- Feature file IDs are prefixed with `scraped_` to distinguish from Saraga files.
- Raga names from blog posts may use variant spellings (e.g. "Bhairavi" vs "bhairavi" vs "Bhairavi") — the raga classifier agent must normalize these to canonical names before training.
- Demucs may leave violin artifacts in the "vocals" stem — treat scraped features as noisier than Saraga features; consider downweighting them slightly in training (e.g. class weight × 0.8 for scraped samples).

## Error handling
- If Demucs is unavailable (install failed), extract features from mixed audio (worse but still useful — do not halt)
- If an audio URL returns 403/404, log and skip that concert
- If disk space drops below 10 GB at any point during batch processing, halt and report to orchestrator
- If fewer than 100 usable features are extracted in total, report this as a warning — the scraper data may not be adding meaningfully to the Saraga baseline
- Never attempt to build composition-level pitch contours from this data — flag any such attempt as out of scope

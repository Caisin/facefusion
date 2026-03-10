# Multi-Face Replacement

Replace multiple faces in a single video pass by pairing each source image with a corresponding reference image.

## How It Works

Each **source image** (the face to swap *in*) is paired by index with a **reference image** (the face to identify *in the target video*). In a single processing pass, every detected face that matches a reference is replaced with the corresponding source.

```
source1.jpg  ←→  ref1.jpg  →  replace "Character A" with person in source1
source2.jpg  ←→  ref2.jpg  →  replace "Character B" with person in source2
source3.jpg  ←→  ref3.jpg  →  replace "Character C" with person in source3
```

## CLI Usage

### Basic command

```bash
python facefusion.py headless-run \
  -s source1.jpg source2.jpg source3.jpg \
  -t video.mp4 \
  -o output.mp4 \
  --reference-face-paths ref1.jpg ref2.jpg ref3.jpg \
  --reference-face-distance 0.4
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `-s source1.jpg source2.jpg ...` | Source faces to swap **in** (one per target person) |
| `--reference-face-paths ref1.jpg ref2.jpg ...` | Reference images identifying each person **in the target video** |
| `--reference-face-distance 0.4` | Matching threshold (0.0–1.0). Lower = stricter. Default: 0.3 |

> **Pairing rule**: sources and references are matched by position.
> `-s A B C` with `--reference-face-paths X Y Z` means A→X, B→Y, C→Z.

### Preparing reference images

A reference image should be a clear photo of the character **as they appear in the target video** (e.g. a screenshot from the video). It is used only for face identification, not for the swap itself.

```
ref1.jpg   →  screenshot of Character A from the video
source1.jpg →  photo of the person you want Character A replaced with
```

### Batch processing multiple episodes

```bash
#!/bin/bash
for video in ep01.mp4 ep02.mp4 ep03.mp4; do
  python facefusion.py headless-run \
    -s new_person1.jpg new_person2.jpg new_person3.jpg \
    -t "$video" \
    -o "output_${video}" \
    --reference-face-paths ref_char1.jpg ref_char2.jpg ref_char3.jpg \
    --reference-face-distance 0.4
done
```

Because the reference images are fixed external files (not tied to a frame number), the same command works across all episodes without reconfiguration.

### Single reference image (existing behaviour)

To replace a single face using an external reference image:

```bash
python facefusion.py headless-run \
  -s source.jpg \
  -t video.mp4 \
  -o output.mp4 \
  --face-selector-mode reference \
  --reference-face-path ref.jpg \
  --reference-face-distance 0.4
```

## UI Usage

1. Open the FaceFusion web interface (`python facefusion.py run`).
2. Upload your **source images** in the *Source* panel (one per person to swap in).
3. Set **Face Selector Mode** to `reference`.
4. In the **Multi-Face Reference Images** file picker, upload the reference images in the same order as your source images.
5. Adjust **Reference Face Distance** if needed (increase if faces are not detected, decrease to reduce false matches).
6. Select your target video and output path, then click **Start**.

## Tuning tips

| Symptom | Fix |
|---------|-----|
| A face is not replaced | Increase `--reference-face-distance` (e.g. 0.5) |
| Wrong face is replaced | Decrease `--reference-face-distance` (e.g. 0.2) |
| All faces replaced with same person | You are using the old single-source mode; ensure `--reference-face-paths` has multiple values |
| Source count ≠ reference count | The number of `-s` images must be ≥ the number of `--reference-face-paths` |

## Fallback behaviour

- If `--reference-face-paths` is **not** provided, the processor falls back to the standard single-source mode controlled by `--face-selector-mode`, `--reference-frame-number`, and `--reference-face-position`.
- If only one reference path is provided, single-face reference mode is used.

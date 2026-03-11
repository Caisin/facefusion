#!/usr/bin/env python3
"""
Batch Multi-Reference Face Replacement Script

Usage:
    python batch_multi_reference.py \
        --video-dir ./videos \
        --source-dir ./sources \
        --reference-dir ./references \
        --output-dir ./output \
        --reference-face-distance 0.4
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List


# Supported file extensions
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


def get_files_sorted(directory: Path, extensions: set) -> List[Path]:
    """Get all files with specified extensions, sorted by name."""
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = [
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ]
    return sorted(files)


def run_facefusion(
    video_path: Path,
    source_paths: List[Path],
    reference_paths: List[Path],
    output_path: Path,
    reference_distance: float = 0.4
) -> bool:
    """Run facefusion command for a single video."""
    # Build command
    cmd = [
        'python', 'facefusion.py', 'headless-run',
        '-t', str(video_path),
        '-o', str(output_path),
        '--face-detector-model', 'retinaface',
        '--face-selector-mode', 'multi_reference',
        '--face-mask-types', 'occlusion',
        '--reference-face-distance', str(reference_distance)
    ]

    # Add source images
    cmd.append('-s')
    cmd.extend([str(p) for p in source_paths])

    # Add reference images
    cmd.append('--reference-face-paths')
    cmd.extend([str(p) for p in reference_paths])

    print(f"\n{'='*60}")
    print(f"Processing: {video_path.name}")
    print(f"Output: {output_path.name}")
    print(f"Sources: {len(source_paths)} images")
    print(f"References: {len(reference_paths)} images")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True)
        print(f"✓ Successfully processed: {video_path.name}\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to process: {video_path.name}")
        print(f"Error: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Batch process videos with multi-reference face replacement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python batch_multi_reference.py \\
        --video-dir ./videos \\
        --source-dir ./sources \\
        --reference-dir ./references \\
        --output-dir ./output \\
        --reference-face-distance 0.4
        """
    )

    parser.add_argument(
        '--video-dir',
        type=Path,
        required=True,
        help='Directory containing target videos'
    )
    parser.add_argument(
        '--source-dir',
        type=Path,
        required=True,
        help='Directory containing source face images (to swap in)'
    )
    parser.add_argument(
        '--reference-dir',
        type=Path,
        required=True,
        help='Directory containing reference face images (to identify in video)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./output'),
        help='Directory for output videos (default: ./output)'
    )
    parser.add_argument(
        '--reference-face-distance',
        type=float,
        default=0.4,
        help='Face matching threshold 0.0-1.0 (default: 0.4)'
    )
    parser.add_argument(
        '--output-prefix',
        type=str,
        default='output_',
        help='Prefix for output filenames (default: output_)'
    )

    args = parser.parse_args()

    # Validate directories
    try:
        video_files = get_files_sorted(args.video_dir, VIDEO_EXTENSIONS)
        source_files = get_files_sorted(args.source_dir, IMAGE_EXTENSIONS)
        reference_files = get_files_sorted(args.reference_dir, IMAGE_EXTENSIONS)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Validate file counts
    if not video_files:
        print(f"Error: No video files found in {args.video_dir}")
        sys.exit(1)

    if not source_files:
        print(f"Error: No source images found in {args.source_dir}")
        sys.exit(1)

    if not reference_files:
        print(f"Error: No reference images found in {args.reference_dir}")
        sys.exit(1)

    if len(source_files) != len(reference_files):
        print(f"Warning: Source count ({len(source_files)}) != Reference count ({len(reference_files)})")
        print("Using minimum count for pairing...")
        min_count = min(len(source_files), len(reference_files))
        source_files = source_files[:min_count]
        reference_files = reference_files[:min_count]

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Print summary
    print("\n" + "="*60)
    print("BATCH PROCESSING SUMMARY")
    print("="*60)
    print(f"Video directory: {args.video_dir}")
    print(f"Source directory: {args.source_dir}")
    print(f"Reference directory: {args.reference_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Reference face distance: {args.reference_face_distance}")
    print(f"\nVideos to process: {len(video_files)}")
    print(f"Source images: {len(source_files)}")
    print(f"Reference images: {len(reference_files)}")
    print("\nSource-Reference pairing:")
    for i, (src, ref) in enumerate(zip(source_files, reference_files), 1):
        print(f"  {i}. {src.name} ←→ {ref.name}")
    print("="*60 + "\n")

    # Confirm before processing
    response = input("Proceed with batch processing? [y/N]: ")
    if response.lower() != 'y':
        print("Cancelled.")
        sys.exit(0)

    # Process each video
    success_count = 0
    failed_videos = []

    for video_file in video_files:
        output_file = args.output_dir / f"{args.output_prefix}{video_file.name}"

        success = run_facefusion(
            video_path=video_file,
            source_paths=source_files,
            reference_paths=reference_files,
            output_path=output_file,
            reference_distance=args.reference_face_distance
        )

        if success:
            success_count += 1
        else:
            failed_videos.append(video_file.name)

    # Print final summary
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"Total videos: {len(video_files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed_videos)}")

    if failed_videos:
        print("\nFailed videos:")
        for name in failed_videos:
            print(f"  - {name}")

    print("="*60 + "\n")


if __name__ == '__main__':
    main()

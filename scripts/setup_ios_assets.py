#!/usr/bin/env python3
"""
Set up iOS asset catalog structure for kawaii cat icons.
Creates proper imageset folders with Contents.json for each SVG.
"""

import json
import os
import shutil
from pathlib import Path

# Paths
ICONS_DIR = Path(__file__).parent.parent / "ios" / "HouseholdTracker" / "HouseholdTracker" / "Resources" / "CatIcons"
ASSETS_DIR = Path(__file__).parent.parent / "ios" / "HouseholdTracker" / "HouseholdTracker" / "Resources" / "Assets.xcassets" / "CatIcons"


def create_imageset(icon_name: str, svg_path: Path):
    """Create an imageset folder for an icon."""

    # Create the imageset folder
    imageset_dir = ASSETS_DIR / f"{icon_name}.imageset"
    imageset_dir.mkdir(parents=True, exist_ok=True)

    # Copy the SVG file
    dest_svg = imageset_dir / f"{icon_name}.svg"
    shutil.copy(svg_path, dest_svg)

    # Create Contents.json
    contents = {
        "images": [
            {
                "filename": f"{icon_name}.svg",
                "idiom": "universal"
            }
        ],
        "info": {
            "author": "xcode",
            "version": 1
        },
        "properties": {
            "preserves-vector-representation": True,
            "template-rendering-intent": "template"  # Allows tinting with foregroundColor
        }
    }

    contents_path = imageset_dir / "Contents.json"
    with open(contents_path, 'w') as f:
        json.dump(contents, f, indent=2)

    return imageset_dir


def create_folder_contents():
    """Create Contents.json for the CatIcons folder."""

    contents = {
        "info": {
            "author": "xcode",
            "version": 1
        }
    }

    contents_path = ASSETS_DIR / "Contents.json"
    with open(contents_path, 'w') as f:
        json.dump(contents, f, indent=2)


def main():
    print("Setting up iOS asset catalog for kawaii cat icons...")
    print(f"Source: {ICONS_DIR}")
    print(f"Output: {ASSETS_DIR}")
    print()

    # Create the base assets folder
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Create folder Contents.json
    create_folder_contents()

    # Process each SVG
    svg_files = sorted(ICONS_DIR.glob("*.svg"))
    print(f"Processing {len(svg_files)} icons...")

    for svg_path in svg_files:
        icon_name = svg_path.stem
        # Skip test icons
        if "test" in icon_name.lower():
            print(f"  Skipping test icon: {icon_name}")
            continue

        imageset_dir = create_imageset(icon_name, svg_path)
        print(f"  Created: {imageset_dir.name}")

    print()
    print("Asset catalog setup complete!")
    print()
    print("The icons are now ready to use in Xcode.")
    print("They will be available as Image(\"cat-ledger\") etc.")


if __name__ == "__main__":
    main()

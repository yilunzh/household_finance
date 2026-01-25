#!/usr/bin/env python3
"""
Extract kawaii cat SVG icons from _icons.html Jinja template.
Converts them to standalone SVG files for iOS asset catalog.
"""

import re
from pathlib import Path

# Source and destination paths
ICONS_HTML = Path(__file__).parent.parent / "templates" / "_icons.html"
OUTPUT_DIR = Path(__file__).parent.parent / "ios" / "HouseholdTracker" / "HouseholdTracker" / "Resources" / "CatIcons"

# SVG template - creates a standalone SVG file
SVG_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
{content}
</svg>
'''


def extract_icons():
    """Parse _icons.html and extract each icon's SVG content."""

    # Read the icons file
    with open(ICONS_HTML, 'r') as f:
        content = f.read()

    # Find all icon definitions using regex
    # Pattern matches: {% if name == 'cat-xxx' %} ... content ... {%- elif
    # or: {%- elif name == 'cat-xxx' -%} ... content ... {%- elif

    # First, let's split by icon name markers
    icon_pattern = r"{%-?\s*(?:if|elif)\s+name\s*==\s*'(cat-[^']+)'\s*-?%}(.*?)(?={%-?\s*(?:elif|endif))"

    matches = re.findall(icon_pattern, content, re.DOTALL)

    icons = {}
    for name, svg_content in matches:
        # Clean up the SVG content - extract just the <g> or <path> elements
        svg_content = svg_content.strip()
        if svg_content:
            icons[name] = svg_content

    return icons


def save_icons(icons):
    """Save each icon as a standalone SVG file."""

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    saved_count = 0
    for name, content in icons.items():
        # Create the full SVG
        svg = SVG_TEMPLATE.format(content=content)

        # Save to file
        output_path = OUTPUT_DIR / f"{name}.svg"
        with open(output_path, 'w') as f:
            f.write(svg)

        print(f"  Saved: {name}.svg")
        saved_count += 1

    return saved_count


def main():
    print("Extracting kawaii cat icons from _icons.html...")
    print(f"Source: {ICONS_HTML}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # Extract icons
    icons = extract_icons()
    print(f"Found {len(icons)} icons:")
    for name in sorted(icons.keys()):
        print(f"  - {name}")
    print()

    # Save icons
    saved = save_icons(icons)
    print()
    print(f"Successfully saved {saved} SVG files!")
    print()
    print("Next steps:")
    print("1. Open Xcode and add the SVG files to Assets.xcassets")
    print("2. Or convert SVGs to PDF for better iOS compatibility")


if __name__ == "__main__":
    main()

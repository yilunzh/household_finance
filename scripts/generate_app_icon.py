#!/usr/bin/env python3
"""
Generate App Icon for Lucky Ledger iOS app using DALL-E 3.

Usage:
    export OPENAI_API_KEY=sk-...
    python scripts/generate_app_icon.py

Output:
    ios/HouseholdTracker/HouseholdTracker/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon.png
"""

import os
import sys
import urllib.request
from pathlib import Path

try:
    import openai
except ImportError:
    print("Error: openai not installed. Run: pip install openai")
    sys.exit(1)

# The prompt - keep original cat design, just remove background rectangle
PROMPT = """A cute kawaii-style cat face app icon on a solid terracotta orange background (#E4714A). The cat has a cream-colored face with black outline, happy closed curved eyes, small pink tongue sticking out, orange/terracotta stripes on the ears, rosy pink cheeks, whiskers. A small golden coin with $ sign hangs beside the cat on a small strap. Clean vector-style illustration, iOS app icon style. CRITICAL: The cat face must be placed DIRECTLY on the solid orange background. Do NOT add any rounded rectangle, card shape, or secondary background layer behind the cat. No text, centered composition, 1024x1024 pixels."""

# Output path
OUTPUT_PATH = Path(__file__).parent.parent / "ios/HouseholdTracker/HouseholdTracker/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon.png"


def main():
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)

    print("Generating app icon with DALL-E 3...")
    print(f"Prompt: {PROMPT[:80]}...")
    print()

    # Generate image
    response = client.images.generate(
        model="dall-e-3",
        prompt=PROMPT,
        size="1024x1024",
        quality="hd",
        response_format="url",
        n=1,
    )

    # Download the image
    image_url = response.data[0].url
    print(f"Generated image URL: {image_url[:80]}...")

    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Download and save
    print(f"Downloading to: {OUTPUT_PATH}")
    urllib.request.urlretrieve(image_url, OUTPUT_PATH)

    print()
    print("Done! App icon saved.")
    print()
    print("Next steps:")
    print("1. Open Xcode and verify the icon appears in Assets.xcassets")
    print("2. Build and run to see the icon on the simulator")
    print("3. Delete the old SVG: ios/HouseholdTracker/HouseholdTracker/Resources/AppIcon.svg")


if __name__ == "__main__":
    main()

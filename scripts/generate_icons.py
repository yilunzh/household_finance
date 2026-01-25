#!/usr/bin/env python3
"""
Icon Generator for Lucky Ledger
Generates cat-themed icons using DALL-E 3 and converts to SVG using Potrace.

Usage:
    export OPENAI_API_KEY=sk-...
    python scripts/generate_icons.py

Requirements:
    pip install openai pillow
    brew install potrace
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import urllib.request

# Check for dependencies
try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Run: pip install pillow")
    sys.exit(1)

try:
    import openai
except ImportError:
    print("Error: openai not installed. Run: pip install openai")
    sys.exit(1)


# Icon definitions: name -> description for DALL-E prompt
# Each description is a complete sentence about what the cat is doing
ICONS = {
    # Navigation & Core
    "cat-ledger": "The cat is sitting and hugging a stack of 3 coins with both front paws.",
    "cat-highfive": "The cat is holding a balance scale, with a weighing pan on each side.",
    "cat-gear": "The cat's head and body are emerging from inside a large mechanical gear cog.",
    "cat-house": "The cat is peeking out from inside a simple house shape, visible in the doorway.",
    "cat-menu": "Three horizontal cat paw prints stacked vertically like a hamburger menu icon.",

    # Actions
    "cat-sparkle": "The cat has small sparkle stars around its head, looking excited.",
    "cat-plus": "The cat is holding a large plus symbol with both front paws.",
    "cat-pencil": "The cat is holding a pencil with its paws, ready to write.",
    "cat-trash": "The cat is peeking out from inside a trash can, head and paws visible on rim.",
    "cat-download": "The cat is sitting next to a downward-pointing arrow.",

    # Status & Feedback
    "cat-happy": "The cat has very happy closed curved eyes like ^_^ and a big smile.",
    "cat-worried": "The cat has a worried expression with eyebrows tilted upward in concern.",
    "cat-alert": "The cat is sitting next to a warning triangle with an exclamation mark inside.",
    "cat-lightbulb": "The cat has a lightbulb floating above its head, having an idea.",
    "cat-sleeping": "The cat is curled up in a ball sleeping peacefully, tail wrapped around body.",

    # Security & State
    "cat-lock": "The cat is hugging a closed padlock with both paws protectively.",
    "cat-unlock": "The cat is sitting next to an open unlocked padlock, looking happy.",
    "cat-stop": "The cat is holding up an X symbol with one raised paw.",

    # Money & Finance
    "cat-coins": "The cat is sitting next to a tall stack of coins, one paw resting on top.",
    "cat-heart": "The cat is hugging a heart shape with both front paws.",
    "cat-calendar": "The cat is peeking over the top edge of a calendar page, paws gripping it.",
    "cat-clock": "The cat is sitting next to a round analog clock showing the time.",

    # Social & Communication
    "cat-wave": "The cat is waving one paw in a friendly greeting gesture.",
    "cat-envelope": "The cat is holding a mail envelope in its front paws.",
    "cat-crown": "The cat is wearing a small crown on its head, looking royal.",
    "cat-group": "Two cats are sitting side by side, both with friendly smiles.",
    "cat-celebrate": "The cat is surrounded by confetti pieces, celebrating happily.",

    # Organization
    "cat-silhouette": "A simple cat face and body silhouette outline, very minimal.",
    "cat-clipboard": "The cat is peeking over the top of a clipboard, paws gripping the edge.",
    "cat-folder": "The cat is peeking out from inside an open file folder.",
    "cat-rocket": "The cat is riding on top of a small rocket ship, looking excited.",
}

# Logo definition (separate, more detailed)
LOGO = {
    "lucky-ledger-logo": "adorable lucky cat (maneki-neko style) sitting upright, one paw raised in beckoning gesture, holding a gold coin, wearing a collar with a small bell, friendly and welcoming expression, suitable for a finance app mascot"
}

# Base prompt for consistent kawaii style (matching sample_icons.png)
ICON_STYLE_PROMPT = """Simple black line art icon on pure white background.
A cute cartoon cat with round head, triangular ears, two black dot eyes, small cat nose, whiskers, and small smile.
Clean minimal lines, no shading, no gradients, no extra decorations or sparkles.
Style similar to simple app icons.

"""

LOGO_STYLE_PROMPT = """Simple black line art logo on pure white background.
A cute lucky cat (maneki-neko) sitting upright with one paw raised in beckoning gesture.
Round head, triangular ears, black dot eyes, small nose, whiskers, friendly smile.
Wearing a collar with small bell, holding a gold coin.
Clean minimal lines, no shading, no gradients.

"""


def check_potrace():
    """Check if potrace is installed."""
    try:
        subprocess.run(["potrace", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_image(client, prompt: str, is_logo: bool = False) -> bytes:
    """Generate an image using DALL-E 3."""
    style_prompt = LOGO_STYLE_PROMPT if is_logo else ICON_STYLE_PROMPT
    full_prompt = style_prompt + prompt

    response = client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size="1024x1024",
        quality="standard",
        response_format="url",
        n=1,
    )

    # Download the image
    image_url = response.data[0].url
    with urllib.request.urlopen(image_url) as response:
        return response.read()


def convert_to_svg(png_data: bytes, output_path: Path) -> bool:
    """Convert PNG to SVG using potrace."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as png_file:
        png_file.write(png_data)
        png_path = png_file.name

    try:
        # Convert to BMP (potrace requires BMP/PBM input)
        img = Image.open(png_path)

        # Convert to grayscale and then to black/white
        img = img.convert("L")  # Grayscale
        # Threshold to black and white
        threshold = 200
        img = img.point(lambda x: 255 if x > threshold else 0, mode="1")

        # Save as BMP
        bmp_path = png_path.replace(".png", ".bmp")
        img.save(bmp_path, "BMP")

        # Run potrace
        svg_path = str(output_path)
        result = subprocess.run(
            ["potrace", bmp_path, "-s", "-o", svg_path, "--flat"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"  Potrace error: {result.stderr}")
            return False

        # Clean up temp files
        os.unlink(png_path)
        os.unlink(bmp_path)

        return True

    except Exception as e:
        print(f"  Conversion error: {e}")
        return False


def optimize_svg(svg_path: Path):
    """Basic SVG optimization - remove unnecessary attributes and set viewBox."""
    try:
        with open(svg_path, "r") as f:
            content = f.read()

        # The SVG from potrace should be clean, but we can adjust viewBox if needed
        # For now, just ensure it's readable

        with open(svg_path, "w") as f:
            f.write(content)

    except Exception as e:
        print(f"  SVG optimization warning: {e}")


def main():
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Run: export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    # Check for potrace
    if not check_potrace():
        print("Error: potrace not installed.")
        print("Run: brew install potrace")
        sys.exit(1)

    # Initialize OpenAI client
    client = openai.OpenAI(api_key=api_key)

    # Output directory
    output_dir = Path(__file__).parent / "generated_icons"
    output_dir.mkdir(exist_ok=True)

    # Also save PNGs for reference
    png_dir = output_dir / "png"
    png_dir.mkdir(exist_ok=True)

    print(f"Output directory: {output_dir}")
    print(f"Generating {len(ICONS)} icons + {len(LOGO)} logo...")
    print()

    # Combine icons and logo
    all_items = [(name, desc, False) for name, desc in ICONS.items()]
    all_items.append((list(LOGO.keys())[0], list(LOGO.values())[0], True))

    successful = 0
    failed = []

    for i, (name, description, is_logo) in enumerate(all_items, 1):
        item_type = "logo" if is_logo else "icon"
        print(f"[{i}/{len(all_items)}] Generating {item_type}: {name}")

        try:
            # Generate image
            print("  Calling DALL-E 3...")
            png_data = generate_image(client, description, is_logo)

            # Save PNG for reference
            png_path = png_dir / f"{name}.png"
            with open(png_path, "wb") as f:
                f.write(png_data)
            print(f"  Saved PNG: {png_path.name}")

            # Convert to SVG
            svg_path = output_dir / f"{name}.svg"
            print("  Converting to SVG...")
            if convert_to_svg(png_data, svg_path):
                optimize_svg(svg_path)
                print(f"  Saved SVG: {svg_path.name}")
                successful += 1
            else:
                failed.append(name)

        except Exception as e:
            print(f"  Error: {e}")
            failed.append(name)

        print()

    # Summary
    print("=" * 50)
    print("Generation complete!")
    print(f"  Successful: {successful}/{len(all_items)}")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print(f"\nOutput: {output_dir}")
    print(f"PNGs:   {png_dir}")
    print("\nNext steps:")
    print("1. Review the generated SVGs in the output directory")
    print("2. If satisfied, run: python scripts/update_icons.py")


if __name__ == "__main__":
    main()

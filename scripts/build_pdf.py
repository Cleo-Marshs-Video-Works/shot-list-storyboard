"""Build a landscape storyboard PDF from a JSON manifest and local frames."""

import argparse
import json
from io import BytesIO
from pathlib import Path
from unicodedata import name
from xml.sax.saxutils import escape

from PIL import Image, ImageChops, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

MARGIN = 28
GUTTER = 20
CAPTION_GAP = 12
PARAGRAPH_GAP = 5
REQUIRED_FIELDS = ("id", "subjects", "shot_size", "description", "image")
CAPTION_FIELDS = ("id", "title", "section", "subjects", "shot_size", "camera", "description")


def has_text(value):
    return isinstance(value, str) and bool(value.strip())


def has_non_latin_letters(value):
    return has_text(value) and any(
        char.isalpha() and not char.isascii() and not name(char, "").startswith("LATIN")
        for char in value
    )


def read_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("shots"), list) or not data["shots"]:
        raise ValueError("Provide a JSON object with aspect_ratio and a nonempty shots array.")

    errors = []
    try:
        width, height = (float(part) for part in data.get("aspect_ratio", "").split(":"))
        ratio = width / height
        if not 0 < width < float("inf") or not 0 < height < float("inf") or not 0 < ratio < float("inf"):
            raise ValueError
    except (AttributeError, ValueError, ZeroDivisionError):
        errors.append("Choose an aspect_ratio as positive width:height (for example, 9:16).")

    seen = set()
    for index, shot in enumerate(data["shots"], 1):
        if not isinstance(shot, dict):
            errors.append(f"Shot at position {index}: provide an object.")
            continue
        shot_id = shot.get("id")
        label = f"Shot {shot_id}" if has_text(shot_id) else f"Shot at position {index}"
        missing = [field for field in REQUIRED_FIELDS if not has_text(shot.get(field))]
        movement = shot.get("movement")
        if not isinstance(movement, dict) or movement.get("type") not in ("locked", "moving"):
            missing.append("movement (locked or moving)")
        elif movement["type"] == "moving":
            if not has_text(movement.get("description")):
                missing.append("movement.description (move and direction)")
            elif has_non_latin_letters(movement["description"]):
                errors.append(f"{label}: translate the camera movement into English.")
        untranslated = [field for field in CAPTION_FIELDS if has_non_latin_letters(shot.get(field))]
        if untranslated:
            errors.append(f"{label}: translate into English: {', '.join(untranslated)}.")
        if missing:
            errors.append(f"{label}: supply {', '.join(missing)}.")
        if has_text(shot_id):
            if shot_id in seen:
                errors.append(f"{label}: use a unique ID.")
            seen.add(shot_id)

    if errors:
        raise ValueError("\n".join(errors))
    return ratio, data["shots"]


def captions(shot, styles):
    heading, section, body = styles
    movement = shot["movement"]
    move = movement["description"] if movement["type"] == "moving" else "Locked camera"

    def paragraph(value, style):
        return Paragraph(escape(value).replace("\n", "<br/>"), style)

    def field(label, value):
        value = escape(value).replace("\n", "<br/>")
        return Paragraph(f"<b>{label}.</b> {value}", body)

    header = "  ".join(filter(None, (shot["id"], shot.get("title"))))
    blocks = [paragraph(header, heading)]
    if shot.get("section"):
        blocks.append(paragraph(shot["section"], section))
    blocks.append(field("Shot size", shot["shot_size"]))
    if shot.get("camera"):
        blocks.append(field("Camera setup", shot["camera"]))
    blocks.extend((
        field("Camera movement", move),
        field("Subjects and action", f"{shot['subjects']}\n{shot['description']}"),
    ))
    return blocks


def has_visible_red(image_path):
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    image.thumbnail((360, 360), Image.Resampling.LANCZOS)
    red, green, blue = image.split()
    bright = red.point(lambda value: 255 if value >= 130 else 0)
    above_green = ImageChops.subtract(red, green).point(lambda value: 255 if value >= 55 else 0)
    above_blue = ImageChops.subtract(red, blue).point(lambda value: 255 if value >= 48 else 0)
    saturation = ImageChops.darker(above_green, above_blue)
    count = ImageChops.darker(bright, saturation).histogram()[255]
    return count >= max(16, image.width * image.height * 0.0005)


def draw_frame(pdf, image_path, x, y, width, height):
    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
    image.thumbnail((max(1, round(width * 3)), max(1, round(height * 3))), Image.Resampling.LANCZOS)
    scale = min(width / image.width, height / image.height)
    image_width, image_height = image.width * scale, image.height * scale
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pdf.drawImage(
        ImageReader(buffer), x + (width - image_width) / 2, y + (height - image_height) / 2,
        image_width, image_height, mask="auto",
    )
    pdf.setStrokeColor("#333333")
    pdf.setLineWidth(0.6)
    pdf.rect(x, y, width, height)


def draw_storyboard(manifest, output, font_path=None, shots_per_page=3):
    ratio, shots = read_manifest(manifest)
    if shots_per_page < 1:
        raise ValueError("shots_per_page must be at least 1.")
    image_errors = []
    for shot in shots:
        image = manifest.parent / shot["image"]
        if not image.is_file():
            image_errors.append(f"Shot {shot['id']}: image file not found: {image}")
        elif has_visible_red(image) != (shot["movement"]["type"] == "moving"):
            image_errors.append(
                f"Shot {shot['id']}: moving frames need a red ImageGen arrow and locked frames must be monochrome."
            )
    if image_errors:
        raise ValueError("\n".join(image_errors))

    font, heading_font = "Helvetica", "Helvetica-Bold"
    if font_path:
        font = heading_font = "Storyboard"
        pdfmetrics.registerFont(TTFont(font, str(font_path)))
        pdfmetrics.registerFontFamily(font, normal=font, bold=font, italic=font, boldItalic=font)
    styles = [
        ParagraphStyle(
            name, fontName=typeface, fontSize=size, leading=leading,
            textColor=HexColor(color),
        )
        for name, typeface, size, leading, color in (
            ("Heading", heading_font, 15, 19, "#111111"),
            ("Section", font, 9.5, 12, "#444444"),
            ("Caption", font, 12, 16, "#111111"),
        )
    ]

    columns = min(shots_per_page, len(shots))
    page_width, page_height = landscape(letter)
    column_width = (page_width - 2 * MARGIN - (columns - 1) * GUTTER) / columns
    if column_width < 72:
        raise ValueError("Use fewer shots per page to keep the captions readable.")
    frame_width = min(column_width, ratio * (page_height * 0.59))
    frame_height = frame_width / ratio
    blocks = [captions(shot, styles) for shot in shots]
    heights = [[block.wrap(column_width, 1_000_000)[1] for block in caption] for caption in blocks]
    max_caption = max(sum(row) + PARAGRAPH_GAP * (len(row) - 1) for row in heights)
    page_height = max(page_height, 2 * MARGIN + frame_height + CAPTION_GAP + max_caption)
    page_width = max(page_width, page_height + 72)
    row_width = columns * column_width + (columns - 1) * GUTTER
    left = (page_width - row_width) / 2
    image_bottom = page_height - MARGIN - frame_height

    output.parent.mkdir(parents=True, exist_ok=True)
    pdf = Canvas(str(output), pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle(output.stem)
    for index, (shot, caption, caption_heights) in enumerate(zip(shots, blocks, heights)):
        column = index % columns
        x = left + column * (column_width + GUTTER)
        draw_frame(
            pdf, manifest.parent / shot["image"], x + (column_width - frame_width) / 2,
            image_bottom, frame_width, frame_height,
        )
        cursor = image_bottom - CAPTION_GAP
        for paragraph, height in zip(caption, caption_heights):
            cursor -= height
            paragraph.drawOn(pdf, x, cursor)
            cursor -= PARAGRAPH_GAP
        if column == columns - 1 or index == len(shots) - 1:
            pdf.showPage()
    pdf.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", type=Path, help="TrueType font for English captions")
    parser.add_argument("--shots-per-page", type=int, default=3)
    args = parser.parse_args()
    try:
        draw_storyboard(args.manifest, args.output, args.font, args.shots_per_page)
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")

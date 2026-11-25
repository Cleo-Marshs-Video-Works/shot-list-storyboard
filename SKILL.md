---
name: shot-list-storyboard
description: Use GPT and ChatGPT's built-in ImageGen to turn a shot list into a landscape storyboard PDF with sequential panels, captions, and camera movement arrows. Use in ChatGPT or Codex to create or revise visual storyboards.
---

# Shot list storyboard

This skill is designed for ChatGPT users. GPT handles shot-list intake, follow-up questions, visual continuity, image prompts, and PDF assembly. Use ChatGPT's built-in ImageGen for the panel artwork. The workflow uses the image model available in the host. Use a third-party image provider or API only when the user explicitly requests it.

**English-only output is required.** Accept source material in any language and translate it faithfully into English. Use English for follow-up questions, form labels, review drafts, filenames, PDF titles, shot titles, subjects, actions, camera details, captions, dialogue, and sound cues. Keep dialogue already written in English verbatim. Review the finished PDF for untranslated text before delivery.

## Confirm the inputs

Use one aspect ratio (width:height) for every panel in the storyboard. Use the ratio the user already chose. If absent or conflicting, ask them to choose 16:9, 9:16, or a custom ratio. The PDF paper is landscape independently of the panel ratio.

Require these inputs for each shot:

- **Subject and action.** Make every shot self-contained for downstream video generation. Record who or what is visible and exactly what happens, even when the action carries over from the previous shot. For POV and over-the-shoulder shots, name the viewpoint, the foreground owner, and the visible subject as applicable. In a reverse angle name who is in the foreground and who is seen beyond them.
- **Shot size.** Record the framing scale, such as wide, medium, close-up, or extreme close-up. If the framing size changes, record its start and end. An angle, POV, or over-the-shoulder view alone leaves size unspecified.
- **Camera movement.** Record an explicit locked/static camera or a movement with its direction and, where needed, start and end framing. Character, prop, and light movement leave camera movement unspecified.

Read the full list first. Apply explicit global instructions and carry forward explicitly shared values only when the referenced value is known. Collect missing or conflicting fields by shot ID and ask only for unresolved inputs. Optional staging, geography, or design details may remain unspecified.

The user owns every creative decision. Use details the user wrote or reviewed and explicitly approved. Do not invent or silently fill in cast, action, staging, performance, set or prop design, dialogue, framing, or camera motion. The user may ask GPT to brainstorm. Keep proposals separate from the shot list until the user approves them. Show the complete resolved shot list for review before generating any panel. An already-reviewed version with explicit user approval satisfies that step. Flag and resolve any unapproved design detail before rendering. Review the resulting panels against the approved text and present them for the user's visual review.

In Codex, show a single inline form using the `visualize` skill when available. Run `python3 scripts/build_intake.py gaps.json /absolute/path/storyboard-intake.html` with this input shape:

```json
{
  "aspect_ratio": "9:16",
  "shots": [{"id": "08", "title": "Emma crawls out", "fields": ["movement"]}]
}
```

Omit `aspect_ratio` to ask for it. Use English shot titles in the form. Supported fields are `subjects`, `description` (subject action), `shot_size`, and `movement`. Ask once for a shared unresolved value when dependent shots explicitly reuse it. Let users write camera directions in a free-text field for each shot, including compound moves and timing. The optional batch fill enters editable locked-camera text into empty fields.

Render the generated fragment in the final response with the visualize content reference. Its submit button sends the written answers back to the same chat. Merge them by shot ID. Interpret a clearly static answer as a locked camera. Preserve the wording and sequence of a moving-camera answer in the caption and use it to direct ImageGen's arrows. Ask for clarification when a submitted direction leaves the required camera move ambiguous. If the inline form is unavailable, use one grouped native input request or a concise chat question that allows free-text answers.

Preserve the source IDs, section order, staging, dialogue and sound cues, performance notes, and cut timing. Keep existing English wording wherever it fits. For match cuts, carry the action across the cut with the same cast, prop placement, screen direction, and action phase. Choose the still that best explains each shot and keep the complete action in its caption.

## Prepare and review the panels

Prompt for rough hand-drawn production thumbnails: plain white paper, sparse black contour lines, simple faces and gestures, and only the few set lines needed for blocking. Specify white interiors and backgrounds, with no tonal shading, hatching, cross-hatching, texture rendering, or realistic lighting. Keep captions out of the artwork. Check the first generated panels for this standard before using them as a reference. Regenerate any panels that read as shaded illustrations or photoreal studies.

Reuse existing frames for revisions when their framing, ratio, and continuity fit. Generate fresh panels when the user asks for a redraw. Check panel count, order, and crop boundaries for any multi-panel source. Reframe or regenerate when a crop would remove a required subject or cue.

For moving shots, tell ImageGen to draw the camera arrows directly inside the artwork in saturated signal red, with a thick shaft and an unmistakable arrowhead. Red is reserved for camera arrows. Describe the position, direction and head of each arrow in the ImageGen prompt. Use a curved arrow for a pan or tilt and paired converging or diverging arrows for a push-in or pull-out when clearer. Keep arrows in open space away from faces, props and key action. Locked shots use monochrome artwork without camera arrows. Check the arrow color, direction, legibility at PDF size and agreement with the caption. Re-run ImageGen for absent, faint, incorrect or stray arrows. The PDF builder places the finished artwork without drawing any arrows.

## Build the landscape PDF

Use one horizontal row per landscape page, with frames read left to right in source order. Under every panel, print its shot number and title with three clearly labeled, legible fields: **Subjects and action**, **Shot size**, and **Camera movement**. Identify the people or objects and retain the full confirmed action, dialogue, sound cues, and cut timing. Print **Locked camera** for a stationary shot. Put optional POV or angle on a separate camera-setup line. Use fewer panels per page if needed for comfortable caption reading. Continue on the next page when the row is full.

Give [the PDF builder](scripts/build_pdf.py) a UTF-8 JSON manifest with this structure:

```json
{
  "aspect_ratio": "9:16",
  "shots": [
    {
      "id": "01",
      "title": "Emma behind the curtain",
      "section": "Cold Hook",
      "subjects": "Emma",
      "shot_size": "Medium close-up",
      "camera": "Low angle",
      "movement": {
        "type": "moving",
        "description": "Track backward along the floor"
      },
      "description": "Emma crawls out from behind the curtain.",
      "image": "frames/01.png"
    }
  ]
}
```

For a locked camera use `"movement": {"type": "locked"}`. For a move, provide its written `description` and point `image` to the finished ImageGen frame containing the red arrows. `title`, `section`, and `camera` (additional setup such as POV or angle) are optional. Image paths are relative to the manifest.

Run `python3 scripts/build_pdf.py shots.json storyboard.pdf` with Pillow and ReportLab installed. Use `--shots-per-page` to override the three-panel default or `--font` to use a local TrueType font. The builder reports missing fields together, flags leftover non-Latin lettering, and checks for visible red in moving frames only.

Check that every shot appears in order with all three labeled fields under its own image. Render the PDF and verify landscape pages, consistent panel ratio, readable captions, and red arrows visible only on moving shots. Confirm their direction by comparing the rendered images with the written moves.

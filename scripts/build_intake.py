"""Build an inline Codex storyboard intake form from unresolved fields."""
import argparse
import json
import re
from pathlib import Path
from uuid import uuid4


def render(data):
    fields = {"subjects", "description", "shot_size", "movement"}
    if not data["shots"] and data.get("aspect_ratio"):
        raise ValueError("The storyboard has no unresolved fields.")
    ids = set()
    for shot in data["shots"]:
        if not shot["id"] or shot["id"] in ids:
            raise ValueError("Unresolved shots must have unique IDs.")
        ids.add(shot["id"])
        if not shot["fields"] or set(shot["fields"]) - fields:
            raise ValueError(f"Invalid unresolved fields for shot {shot['id']}.")
    template = Path(__file__).with_name("intake.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("<", r"\u003c")
    template = re.sub(r"storyboard-(intake|data)-ROOT", rf"storyboard-\1-{uuid4().hex[:12]}", template)
    return template.replace("INTAKE_DATA", payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gaps", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    fragment = render(json.loads(args.gaps.read_text(encoding="utf-8")))
    args.output.write_text(fragment, encoding="utf-8")

"""Pass 5 — write final artifacts: events.json + stories/ + photos/."""

import json
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

from timeline_ingest.config import Config
from timeline_ingest.schema import EventPhoto, EventRecord


_PHOTO_MAX_WIDTH = 800
_PHOTO_TIMEOUT_S = 15.0


def _render_story_md(r: EventRecord) -> str:
    body = r.story_body or r.summary_en
    return (
        f"# {r.title_en}\n\n"
        f"*{r.date.y}*\n\n"
        f"{body}\n"
    )


def _download_and_resize(url: str, out_path: Path) -> bool:
    try:
        with httpx.Client(timeout=_PHOTO_TIMEOUT_S, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
        im = Image.open(BytesIO(resp.content))
        im = im.convert("RGB")
        if im.width > _PHOTO_MAX_WIDTH:
            ratio = _PHOTO_MAX_WIDTH / im.width
            new_size = (_PHOTO_MAX_WIDTH, int(im.height * ratio))
            im = im.resize(new_size, Image.LANCZOS)
        im.save(out_path, format="WEBP", quality=82, method=6)
        return True
    except (httpx.HTTPError, OSError, ValueError):
        return False


def run_pass5(cfg: Config) -> Path:
    src = cfg.output.intermediate_dir / "04_enriched.json"
    rows = json.loads(src.read_text(encoding="utf-8"))
    records = [EventRecord.model_validate(r) for r in rows]

    public = cfg.output.public_dir
    public.mkdir(parents=True, exist_ok=True)
    stories_dir = public / "stories"
    stories_dir.mkdir(parents=True, exist_ok=True)
    photos_dir = public / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    final_records: list[EventRecord] = []
    for r in records:
        photo = r.photo
        if photo is not None:
            local = photos_dir / f"{r.id}.webp"
            if local.exists() or _download_and_resize(photo.url, local):
                photo = EventPhoto(
                    url=f"photos/{r.id}.webp",
                    credit=photo.credit,
                    caption=photo.caption,
                )
                r = r.model_copy(update={"photo": photo})
            else:
                r = r.model_copy(update={"photo": None})
        final_records.append(r)

    events_path = public / "events.json"
    events_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in final_records], ensure_ascii=False),
        encoding="utf-8",
    )

    for r in final_records:
        (stories_dir / f"{r.id}.md").write_text(_render_story_md(r), encoding="utf-8")

    return events_path

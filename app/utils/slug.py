import re
import unicodedata
from typing import Optional, Type
from sqlalchemy.orm import Session


def slugify(value: str) -> str:
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = str(value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value.strip("-") or "item"


def get_unique_slug(
    db: Session,
    model_class: Type,
    text: str,
    current_id: Optional[int] = None,
    slug_field: str = "slug",
) -> str:
    """
    Generates an SEO-friendly slug and ensures uniqueness within the given model table.
    If the slug already exists on a different row, appends '-2', '-3', etc.
    """
    base_slug = slugify(text)
    candidate_slug = base_slug
    counter = 1

    attr = getattr(model_class, slug_field)

    while True:
        query = db.query(model_class).filter(attr == candidate_slug)
        if current_id is not None:
            query = query.filter(model_class.id != current_id)

        exists = query.first()
        if not exists:
            return candidate_slug

        counter += 1
        candidate_slug = f"{base_slug}-{counter}"

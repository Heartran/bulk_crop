import json
import os
import re
from pathlib import Path
from typing import Dict, List

TEMPLATES_DIR = "templates"
DEFAULT_TEMPLATE_NAME = "default"
_TEMPLATE_EXTENSION = ".json"
_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


class TemplateError(RuntimeError):
    """Raised when a template cannot be loaded or is invalid."""


def _template_path(name: str) -> str:
    return os.path.join(TEMPLATES_DIR, f"{name}.json")


def list_templates() -> List[str]:
    """Return the available template names (without extensions)."""
    if not os.path.isdir(TEMPLATES_DIR):
        return []
    names: List[str] = []
    for entry in os.listdir(TEMPLATES_DIR):
        if entry.lower().endswith(_TEMPLATE_EXTENSION):
            names.append(os.path.splitext(entry)[0])
    return sorted(names)


def load_template(name: str = DEFAULT_TEMPLATE_NAME) -> Dict[str, int]:
    """Load a template by name and return normalized crop coordinates."""
    path = _template_path(name)
    if not os.path.isfile(path):
        available = list_templates()
        hint = f" Disponibili: {', '.join(available)}." if available else ""
        raise TemplateError(f"Template '{name}' non trovato in '{TEMPLATES_DIR}'.{hint}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise TemplateError(f"Impossibile leggere il template '{name}': {exc}") from exc
    return _normalize_template(data, name)


def import_template_from_file(source_path: str, overwrite: bool = False) -> str:
    """Import a template JSON file into the templates directory and return its stored name."""
    path = Path(source_path).expanduser()
    if not path.is_file():
        raise TemplateError(f"File template non trovato: {source_path}")

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise TemplateError(f"Impossibile leggere il file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TemplateError(f"File JSON non valido: {exc}") from exc

    normalized = _normalize_template(data, fallback_name=path.stem)
    base_name = _slugify(normalized["template_name"]) or _slugify(path.stem) or "template"

    dest_dir = Path(TEMPLATES_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_name = base_name
    if not overwrite:
        suffix = 1
        while (dest_dir / f"{dest_name}.json").exists():
            suffix += 1
            dest_name = f"{base_name}_{suffix}"

    try:
        with path.open("r", encoding="utf-8") as fh:
            content = fh.read()
        (dest_dir / f"{dest_name}.json").write_text(content, encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Impossibile salvare il template importato: {exc}") from exc

    return dest_name


def export_template_to_file(name: str, destination_path: str, overwrite: bool = False) -> str:
    """Export a stored template to an external JSON file and return the final path."""
    src = Path(_template_path(name))
    if not src.is_file():
        raise TemplateError(f"Template '{name}' non trovato in '{TEMPLATES_DIR}'.")

    try:
        content = src.read_text(encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Impossibile leggere il template '{name}': {exc}") from exc

    dest = Path(destination_path).expanduser()
    if dest.exists() and dest.is_dir():
        dest = dest / f"{name}.json"
    if dest.suffix.lower() != _TEMPLATE_EXTENSION:
        dest = dest.with_suffix(_TEMPLATE_EXTENSION)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not overwrite:
        raise TemplateError(f"Il file '{dest}' esiste già.")

    try:
        dest.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise TemplateError(f"Impossibile scrivere il file di destinazione: {exc}") from exc

    return str(dest)


def _normalize_template(data: Dict[str, int], fallback_name: str) -> Dict[str, int]:
    try:
        left = int(data["left"])
        top = int(data["top"])
    except KeyError as exc:
        raise TemplateError("Il template deve contenere 'left' e 'top'.") from exc

    right = data.get("right")
    bottom = data.get("bottom")
    width = data.get("width")
    height = data.get("height")
    size = data.get("size")

    if right is None or bottom is None:
        if width is None or height is None:
            if size is None:
                raise TemplateError("Il template deve definire 'right'/'bottom', oppure 'width'/'height', oppure 'size'.")
            width = height = size
        width = int(width if width is not None else height)
        height = int(height if height is not None else width)
        right = left + width
        bottom = top + height
    else:
        right = int(right)
        bottom = int(bottom)
        width = right - left
        height = bottom - top

    if width <= 0 or height <= 0:
        raise TemplateError("Dimensioni del template non valide (devono essere positive).")

    template_name = str(data.get("name") or fallback_name)
    description = str(data.get("description") or "")

    return {
        "template_name": template_name,
        "description": description,
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": width,
        "height": height,
    }


def _slugify(value: str) -> str:
    slug = _SAFE_NAME_PATTERN.sub("_", value.strip())
    slug = slug.strip("_")
    return slug.lower()[:80]

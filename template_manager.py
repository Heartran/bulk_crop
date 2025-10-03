import json
import os
from typing import Dict, List

TEMPLATES_DIR = "templates"
DEFAULT_TEMPLATE_NAME = "default"
_TEMPLATE_EXTENSION = ".json"


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
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return _normalize_template(data, name)


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

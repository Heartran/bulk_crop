import argparse
import os
from typing import Iterable

from PIL import Image

from template_manager import (
    DEFAULT_TEMPLATE_NAME,
    TemplateError,
    list_templates,
    load_template,
)

VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg')
DEFAULT_INPUT_FOLDER = 'input'
DEFAULT_OUTPUT_FOLDER = 'output'


def iter_image_files(folder: str) -> Iterable[str]:
    for fname in sorted(os.listdir(folder)):
        if fname.lower().endswith(VALID_EXTENSIONS):
            yield fname


def process_images(input_folder: str, output_folder: str, crop_box):
    os.makedirs(output_folder, exist_ok=True)
    processed = 0
    for fname in iter_image_files(input_folder):
        input_path = os.path.join(input_folder, fname)
        output_path = os.path.join(output_folder, fname)
        with Image.open(input_path) as img:
            cropped = img.crop(crop_box)
            cropped.save(output_path)
        print(f"Ritagliata {fname}")
        processed += 1
    return processed


def parse_args():
    parser = argparse.ArgumentParser(
        description='Ritaglia tutte le immagini nella cartella di input usando un template salvato.',
    )
    parser.add_argument(
        '-t',
        '--template',
        default=DEFAULT_TEMPLATE_NAME,
        help='Nome del template da usare (senza estensione).',
    )
    parser.add_argument(
        '-i',
        '--input',
        default=DEFAULT_INPUT_FOLDER,
        help='Cartella di input contenente le immagini.',
    )
    parser.add_argument(
        '-o',
        '--output',
        default=DEFAULT_OUTPUT_FOLDER,
        help='Cartella di output per le immagini ritagliate.',
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='Elenca i template disponibili e termina.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list:
        templates = list_templates()
        if not templates:
            print('Nessun template disponibile nella cartella templates.')
        else:
            print('Template disponibili:')
            for name in templates:
                print(f' - {name}')
        return 0

    if not os.path.isdir(args.input):
        print(f"La cartella '{args.input}' non esiste.")
        return 1

    try:
        template = load_template(args.template)
    except TemplateError as exc:
        print(f"Errore nel caricamento del template: {exc}")
        return 1

    crop_box = (template['left'], template['top'], template['right'], template['bottom'])
    processed = process_images(args.input, args.output, crop_box)

    if processed == 0:
        print('Nessuna immagine PNG o JPG trovata nella cartella di input.')
    else:
        print(
            f"Completato: {processed} immagini ritagliate usando il template '{template['template_name']}'."
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

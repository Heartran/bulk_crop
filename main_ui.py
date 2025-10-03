import json
import os
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from template_manager import (
    DEFAULT_TEMPLATE_NAME,
    TemplateError,
    export_template_to_file,
    import_template_from_file,
    list_templates,
    load_template,
)

INPUT_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg')


def iter_image_files(folder: str):
    for fname in sorted(os.listdir(folder)):
        if fname.lower().endswith(VALID_EXTENSIONS):
            yield fname


def find_first_image(folder: str) -> Optional[str]:
    for fname in iter_image_files(folder):
        return fname
    return None


def process_all_images(
    crop_box: Tuple[int, int, int, int],
    input_folder: str = INPUT_FOLDER,
    output_folder: str = OUTPUT_FOLDER,
) -> int:
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


class CropUI:
    def __init__(self, master: tk.Tk, image_path: str):
        self.master = master
        self.completed = False
        self.manual_override = False
        self.available_templates: List[str] = []
        self.current_template_name: Optional[str] = None
        self.current_template_label: Optional[str] = None

        self.master.configure(padx=10, pady=10)
        self.master.resizable(False, False)

        with Image.open(image_path) as img:
            self.original_width, self.original_height = img.size
            self.display_image, self.scale = self._prepare_display_image(img)

        self.photo = ImageTk.PhotoImage(self.display_image)
        self.display_width, self.display_height = self.display_image.size

        self.canvas = tk.Canvas(
            master,
            width=self.display_width,
            height=self.display_height,
            highlightthickness=0,
            cursor='cross',
        )
        self.canvas.pack()

        self.template_var = tk.StringVar(value=DEFAULT_TEMPLATE_NAME)

        template_frame = tk.Frame(master)
        template_frame.pack(fill='x', pady=(10, 0))
        tk.Label(template_frame, text='Template:').pack(side='left')
        self.template_combo = ttk.Combobox(
            template_frame,
            textvariable=self.template_var,
            state='readonly',
            width=25,
        )
        self.template_combo.pack(side='left', padx=(5, 5))
        self.template_combo.bind('<<ComboboxSelected>>', self.on_template_selected)
        refresh_btn = tk.Button(
            template_frame,
            text='Aggiorna',
            command=self.on_refresh_templates,
        )
        refresh_btn.pack(side='left')
        import_btn = tk.Button(
            template_frame,
            text='Importa...',
            command=self.on_import_template,
        )
        import_btn.pack(side='left', padx=(5, 0))
        export_btn = tk.Button(
            template_frame,
            text='Esporta...',
            command=self.on_export_template,
        )
        export_btn.pack(side='left', padx=(5, 0))

        self.rect_id = None
        self.start_x = None
        self.start_y = None
        self.crop_coords: Optional[Tuple[int, int, int, int]] = None

        self.status_var = tk.StringVar(value="Trascina il mouse o applica un template per selezionare l'area da ritagliare.")
        status_label = tk.Label(master, textvariable=self.status_var, anchor='w')
        status_label.pack(fill='x', pady=(10, 0))

        button_frame = tk.Frame(master)
        button_frame.pack(fill='x', pady=10)
        confirm_btn = tk.Button(
            button_frame,
            text='Applica ritaglio a tutte le immagini',
            command=self.on_confirm,
        )
        confirm_btn.pack(side='left')
        reset_btn = tk.Button(
            button_frame,
            text='Ripristina dal template',
            command=self.apply_current_template,
        )
        reset_btn.pack(side='left', padx=(10, 0))

        self.canvas.bind('<ButtonPress-1>', self.on_button_press)
        self.canvas.bind('<B1-Motion>', self.on_move_press)
        self.canvas.bind('<ButtonRelease-1>', self.on_button_release)

        self.on_refresh_templates(apply_template=True)

    def _prepare_display_image(self, image: Image.Image):
        max_width = 1000
        max_height = 700
        width, height = image.size
        ratio = min(max_width / width, max_height / height, 1)
        if ratio < 1:
            new_size = (int(width * ratio), int(height * ratio))
            resized = image.resize(new_size, Image.LANCZOS)
        else:
            resized = image.copy()
        scale = width / resized.width
        return resized, scale

    def on_export_template(self):
        if self.crop_coords is None:
            messagebox.showwarning('Template', "Seleziona o definisci un'area da esportare.")
            return
        default_name = self.current_template_label or self.template_var.get() or 'template'
        default_filename = f"{default_name}.json" if default_name else 'template.json'
        file_path = filedialog.asksaveasfilename(
            title='Esporta template',
            defaultextension='.json',
            initialfile=default_filename,
            filetypes=[('Template JSON', '*.json'), ('Tutti i file', '*.*')],
        )
        if not file_path:
            return
        try:
            if self.manual_override or not self.current_template_name:
                self._export_manual_selection(file_path, default_name)
            else:
                export_template_to_file(self.current_template_name, file_path, overwrite=True)
        except TemplateError as exc:
            messagebox.showerror('Template', f"Esportazione fallita: {exc}")
            return
        self.status_var.set(f"Template esportato in '{file_path}'.")

    def on_import_template(self):
        file_path = filedialog.askopenfilename(
            title='Seleziona file template',
            filetypes=[('Template JSON', '*.json'), ('Tutti i file', '*.*')],
        )
        if not file_path:
            return
        try:
            imported_name = import_template_from_file(file_path)
        except TemplateError as exc:
            messagebox.showerror('Template', f"Importazione fallita: {exc}")
            return
        self.template_var.set(imported_name)
        self.on_refresh_templates(apply_template=True)
        self.status_var.set(f"Template '{imported_name}' importato e applicato.")

    def on_refresh_templates(self, apply_template: bool = False):
        current = self.template_var.get()
        templates = list_templates()
        if DEFAULT_TEMPLATE_NAME not in templates:
            templates.insert(0, DEFAULT_TEMPLATE_NAME)
        self.available_templates = templates
        self.template_combo['values'] = templates
        if current in templates:
            self.template_var.set(current)
        elif templates:
            self.template_var.set(templates[0])
        else:
            self.template_var.set('')
        if apply_template:
            self.apply_current_template()

    def apply_current_template(self):
        template_name = self.template_var.get()
        if not template_name:
            self.status_var.set('Seleziona un template valido per applicare il ritaglio.')
            return
        self.apply_template(template_name)

    def apply_template(self, template_name: str):
        try:
            template = load_template(template_name)
        except TemplateError as exc:
            messagebox.showerror('Template', f"Impossibile caricare il template '{template_name}': {exc}")
            return
        self.current_template_name = template_name
        self.current_template_label = template['template_name']
        self.manual_override = False
        self._set_crop_coords(
            template['left'],
            template['top'],
            template['right'],
            template['bottom'],
            source_label=f"template '{self.current_template_label}'",
        )

    def on_template_selected(self, event=None):
        self.apply_current_template()

    def _export_manual_selection(self, file_path: str, default_name: str):
        if self.crop_coords is None:
            raise TemplateError('Nessuna area da esportare.')
        left, top, right, bottom = self.crop_coords
        name = default_name or 'personalizzato'
        data = {
            'name': name,
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom,
            'width': right - left,
            'height': bottom - top,
        }
        try:
            with open(file_path, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            raise TemplateError(f"Impossibile salvare il file: {exc}") from exc

    def _set_crop_coords(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        source_label: Optional[str] = None,
    ):
        clamped_left = max(0, min(left, self.original_width))
        clamped_top = max(0, min(top, self.original_height))
        clamped_right = max(0, min(right, self.original_width))
        clamped_bottom = max(0, min(bottom, self.original_height))

        if clamped_right - clamped_left < 1 or clamped_bottom - clamped_top < 1:
            self.crop_coords = None
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                self.rect_id = None
            self.status_var.set('Il template selezionato non rientra interamente nell\'immagine.')
            return

        left_i = int(round(clamped_left))
        top_i = int(round(clamped_top))
        right_i = int(round(clamped_right))
        bottom_i = int(round(clamped_bottom))

        self.crop_coords = (left_i, top_i, right_i, bottom_i)

        x0, y0, x1, y1 = [value / self.scale for value in self.crop_coords]
        self._draw_rectangle(x0, y0, x1, y1)
        origin = source_label or 'selezione manuale'
        self.status_var.set(
            f"Area selezionata ({origin}): sinistra={left_i}, sopra={top_i}, destra={right_i}, sotto={bottom_i}"
        )

    def on_button_press(self, event):
        self.start_x = self._clamp(event.x, 0, self.display_width)
        self.start_y = self._clamp(event.y, 0, self.display_height)
        self._draw_rectangle(self.start_x, self.start_y, self.start_x, self.start_y)

    def on_move_press(self, event):
        if self.start_x is None or self.start_y is None:
            return
        cur_x = self._clamp(event.x, 0, self.display_width)
        cur_y = self._clamp(event.y, 0, self.display_height)
        self._draw_rectangle(self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        if self.start_x is None or self.start_y is None:
            return
        end_x = self._clamp(event.x, 0, self.display_width)
        end_y = self._clamp(event.y, 0, self.display_height)
        x0 = min(self.start_x, end_x)
        y0 = min(self.start_y, end_y)
        x1 = max(self.start_x, end_x)
        y1 = max(self.start_y, end_y)
        if x1 - x0 < 2 or y1 - y0 < 2:
            self.status_var.set('Selezione troppo piccola, riprova.')
            self.crop_coords = None
        else:
            crop_coords = self._convert_to_original(x0, y0, x1, y1)
            self.manual_override = True
            self.current_template_label = None
            self._set_crop_coords(*crop_coords, source_label='selezione manuale')
        self.start_x = None
        self.start_y = None

    def on_confirm(self):
        if self.crop_coords is None:
            messagebox.showwarning('Ritaglio', 'Seleziona un\'area da ritagliare prima di procedere.')
            return
        try:
            processed = process_all_images(self.crop_coords)
        except Exception as exc:
            messagebox.showerror('Errore', f"Impossibile ritagliare le immagini: {exc}")
            return
        messagebox.showinfo('Completato', f"Ritagliate {processed} immagini nella cartella '{OUTPUT_FOLDER}'.")
        self.completed = True
        self.master.destroy()

    def _draw_rectangle(self, x0, y0, x1, y1):
        if self.rect_id is None:
            self.rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline='red', width=2)
        else:
            self.canvas.coords(self.rect_id, x0, y0, x1, y1)

    def _convert_to_original(self, x0, y0, x1, y1):
        left = int(round(x0 * self.scale))
        top = int(round(y0 * self.scale))
        right = int(round(x1 * self.scale))
        bottom = int(round(y1 * self.scale))

        left = max(0, min(left, self.original_width - 1))
        top = max(0, min(top, self.original_height - 1))
        right = max(left + 1, min(right, self.original_width))
        bottom = max(top + 1, min(bottom, self.original_height))
        return left, top, right, bottom

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(value, maximum))


def main():
    if not os.path.isdir(INPUT_FOLDER):
        print(f"La cartella '{INPUT_FOLDER}' non esiste.")
        return

    first_image = find_first_image(INPUT_FOLDER)
    if first_image is None:
        print('Nessuna immagine PNG o JPG trovata nella cartella di input.')
        return

    image_path = os.path.join(INPUT_FOLDER, first_image)
    root = tk.Tk()
    root.title('Bulk Crop - Seleziona area di ritaglio')
    ui = CropUI(root, image_path)
    root.mainloop()

    if not ui.completed:
        print('Operazione annullata prima di applicare il ritaglio.')


if __name__ == '__main__':
    main()


import os
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import messagebox

# Coordinate di ritaglio predefinite dal vecchio script
LEFT, TOP = 1381, 119
SIZE = 273
RIGHT = LEFT + SIZE
BOTTOM = TOP + SIZE

INPUT_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
VALID_EXTENSIONS = ('.png', '.jpg', '.jpeg')


def iter_image_files(folder):
    for fname in sorted(os.listdir(folder)):
        if fname.lower().endswith(VALID_EXTENSIONS):
            yield fname


def find_first_image(folder):
    for fname in iter_image_files(folder):
        return fname
    return None


def process_all_images(crop_box):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    processed = 0
    for fname in iter_image_files(INPUT_FOLDER):
        input_path = os.path.join(INPUT_FOLDER, fname)
        output_path = os.path.join(OUTPUT_FOLDER, fname)
        with Image.open(input_path) as img:
            cropped = img.crop(crop_box)
            cropped.save(output_path)
        print(f"Ritagliata {fname}")
        processed += 1
    return processed


class CropUI:
    def __init__(self, master, image_path):
        self.master = master
        self.completed = False

        self.master.configure(padx=10, pady=10)
        self.master.resizable(False, False)

        with Image.open(image_path) as img:
            self.original_width, self.original_height = img.size
            self.display_image, self.scale = self._prepare_display_image(img)

        self.photo = ImageTk.PhotoImage(self.display_image)
        self.display_width, self.display_height = self.display_image.size

        self.canvas = tk.Canvas(master, width=self.display_width, height=self.display_height, highlightthickness=0, cursor='cross')
        self.canvas.pack()

        self.canvas.create_image(0, 0, anchor='nw', image=self.photo)

        self.rect_id = None
        self.start_x = None
        self.start_y = None
        self.crop_coords = None

        self.status_var = tk.StringVar(value="Trascina il mouse per selezionare l'area da ritagliare.")
        status_label = tk.Label(master, textvariable=self.status_var, anchor='w')
        status_label.pack(fill='x', pady=(10, 0))

        button_frame = tk.Frame(master)
        button_frame.pack(fill='x', pady=10)
        confirm_btn = tk.Button(button_frame, text='Applica ritaglio a tutte le immagini', command=self.on_confirm)
        confirm_btn.pack(side='left')
        reset_btn = tk.Button(button_frame, text='Ripristina area predefinita', command=self.apply_default_crop)
        reset_btn.pack(side='left', padx=(10, 0))

        self.canvas.bind('<ButtonPress-1>', self.on_button_press)
        self.canvas.bind('<B1-Motion>', self.on_move_press)
        self.canvas.bind('<ButtonRelease-1>', self.on_button_release)

        self.apply_default_crop()

    def _prepare_display_image(self, image):
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

    def apply_default_crop(self):
        clamped_left = max(0, min(LEFT, self.original_width))
        clamped_top = max(0, min(TOP, self.original_height))
        clamped_right = max(0, min(RIGHT, self.original_width))
        clamped_bottom = max(0, min(BOTTOM, self.original_height))

        if clamped_right - clamped_left < 1 or clamped_bottom - clamped_top < 1:
            self.crop_coords = None
            self.status_var.set("Seleziona manualmente l'area da ritagliare.")
            if self.rect_id:
                self.canvas.delete(self.rect_id)
                self.rect_id = None
            return

        self.crop_coords = (
            int(clamped_left),
            int(clamped_top),
            int(clamped_right),
            int(clamped_bottom),
        )

        x0, y0, x1, y1 = [value / self.scale for value in self.crop_coords]
        self._draw_rectangle(x0, y0, x1, y1)
        left, top, right, bottom = self.crop_coords
        self.status_var.set(f"Area selezionata: sinistra={left}, sopra={top}, destra={right}, sotto={bottom}")

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
            self._draw_rectangle(x0, y0, x1, y1)
            self.crop_coords = self._convert_to_original(x0, y0, x1, y1)
            left, top, right, bottom = self.crop_coords
            self.status_var.set(f"Area selezionata: sinistra={left}, sopra={top}, destra={right}, sotto={bottom}")
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
        print("Nessuna immagine PNG o JPG trovata nella cartella di input.")
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

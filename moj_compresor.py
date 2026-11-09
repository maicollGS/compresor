"""
MOJ Compresor - Compresión sin pérdida al máximo posible
© MOJ Soluciones

- Comprime archivos y carpetas a formato .7z estándar (se abre con 7-Zip, WinRAR, etc.).
- Modo MÁXIMO: prueba varios algoritmos sin pérdida (LZMA2 ultra, PPMd, BZip2,
  LZMA2 + filtro x86 para ejecutables) y se queda con el resultado más pequeño.
- Verificación: tras comprimir, descomprime en temporal y compara SHA-256 de cada
  archivo contra el original. Si algo no coincide, el archivo se descarta.
- Pestaña para extraer archivos .7z.

Requisitos:  pip install py7zr pyppmd
"""

import hashlib
import lzma
import os
import shutil
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import py7zr

APP_NAME = "MOJ Compresor"
VERSION = "1.0.0"

# ----------------------------------------------------------------------------
# Métodos de compresión (todos SIN PÉRDIDA)
# ----------------------------------------------------------------------------
LZMA2_ULTRA = [{"id": py7zr.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME,
                "dict_size": 128 * 1024 * 1024}]
METODOS = {
    "LZMA2 Ultra": LZMA2_ULTRA,
    "PPMd (texto)": [{"id": py7zr.FILTER_PPMD, "order": 16, "mem": "256m"}],
    "BZip2": [{"id": py7zr.FILTER_BZIP2}],
    "LZMA2 + x86 (ejecutables)": [{"id": py7zr.FILTER_X86}] + LZMA2_ULTRA,
}
MODOS = {
    "Máximo (prueba todos y elige el menor)": list(METODOS.keys()),
    "Ultra (solo LZMA2, más rápido)": ["LZMA2 Ultra"],
}


def fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:,.2f} {u}" if u != "B" else f"{int(n)} B"
        n /= 1024
    return str(n)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def recolectar(entradas):
    """Devuelve lista de (ruta_real, nombre_en_archivo) para archivos y carpetas."""
    items = []
    for e in entradas:
        p = Path(e)
        if p.is_file():
            items.append((p, p.name))
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    items.append((f, str(Path(p.name) / f.relative_to(p)).replace("\\", "/")))
    return items


def crear_7z(items, destino: Path, filtros, password=None):
    with py7zr.SevenZipFile(destino, "w", filters=filtros, password=password,
                            header_encryption=bool(password)) as z:
        for real, nombre in items:
            z.write(real, nombre)


def verificar(destino: Path, items, password=None):
    """Descomprime en temporal y compara SHA-256 archivo por archivo."""
    with tempfile.TemporaryDirectory() as tmp:
        with py7zr.SevenZipFile(destino, "r", password=password) as z:
            z.extractall(tmp)
        for real, nombre in items:
            extraido = Path(tmp) / nombre
            if not extraido.is_file() or sha256(extraido) != sha256(real):
                return False, nombre
    return True, None


def comprimir(entradas, destino: Path, modo: str, password=None, log=print):
    items = recolectar(entradas)
    if not items:
        raise ValueError("No hay archivos para comprimir.")
    original = sum(r.stat().st_size for r, _ in items)
    log(f"{len(items)} archivo(s), {fmt_bytes(original)} en total.")

    mejor = None
    tmpdir = Path(tempfile.mkdtemp(prefix="mojc_"))
    try:
        for i, nombre in enumerate(MODOS[modo]):
            t0 = time.time()
            log(f"→ Probando {nombre}...")
            cand = tmpdir / f"candidato_{i}.7z"
            try:
                crear_7z(items, cand, METODOS[nombre], password)
            except Exception as ex:  # un método puede fallar en algún caso raro
                log(f"   ✗ {nombre} falló: {ex}")
                continue
            tam = cand.stat().st_size
            log(f"   {fmt_bytes(tam)}  ({tam / original * 100 if original else 0:.2f}% del original, {time.time() - t0:.1f}s)")
            if mejor is None or tam < mejor[1]:
                if mejor:
                    mejor[2].unlink(missing_ok=True)
                mejor = (nombre, tam, cand)
            else:
                cand.unlink(missing_ok=True)

        if mejor is None:
            raise RuntimeError("Ningún método pudo comprimir los archivos.")

        nombre, tam, ruta = mejor
        log(f"Ganador: {nombre}. Verificando integridad (SHA-256)...")
        ok, fallo = verificar(ruta, items, password)
        if not ok:
            raise RuntimeError(f"La verificación falló en '{fallo}'. No se guardó el archivo.")
        log("   ✓ Todos los archivos idénticos al original.")
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ruta), destino)
        ahorro = (1 - tam / original) * 100 if original else 0
        log(f"✔ Guardado: {destino}\n   {fmt_bytes(original)} → {fmt_bytes(tam)}  (ahorro {ahorro:.2f}%)")
        return original, tam, nombre
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def extraer(archivo: Path, carpeta: Path, password=None, log=print):
    with py7zr.SevenZipFile(archivo, "r", password=password) as z:
        if z.test() is False:
            raise RuntimeError("El archivo está dañado.")
    with py7zr.SevenZipFile(archivo, "r", password=password) as z:
        z.extractall(carpeta)
    log(f"✔ Extraído en: {carpeta}")


# ----------------------------------------------------------------------------
# Interfaz gráfica
# ----------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{VERSION} — MOJ Soluciones")
        self.geometry("760x560")
        self.minsize(640, 480)
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self._tab_comprimir(nb)
        self._tab_extraer(nb)

        self.log_box = tk.Text(self, height=11, font=("Consolas", 9), state="disabled",
                               bg="#0f172a", fg="#e2e8f0", relief="flat")
        self.log_box.pack(fill="both", expand=False, padx=10, pady=10)
        self.prog = ttk.Progressbar(self, mode="indeterminate")
        self.prog.pack(fill="x", padx=10, pady=(0, 10))

    # ---------- Comprimir ----------
    def _tab_comprimir(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Comprimir  ")

        bar = ttk.Frame(f)
        bar.pack(fill="x")
        ttk.Button(bar, text="➕ Archivos", command=self._add_files).pack(side="left")
        ttk.Button(bar, text="📁 Carpeta", command=self._add_dir).pack(side="left", padx=5)
        ttk.Button(bar, text="Quitar", command=self._remove).pack(side="left")
        ttk.Button(bar, text="Limpiar", command=lambda: self.lista.delete(0, "end")).pack(side="left", padx=5)

        self.lista = tk.Listbox(f, height=7, selectmode="extended")
        self.lista.pack(fill="both", expand=True, pady=8)

        g = ttk.Frame(f)
        g.pack(fill="x")
        ttk.Label(g, text="Modo:").grid(row=0, column=0, sticky="w")
        self.modo = tk.StringVar(value=list(MODOS)[0])
        ttk.Combobox(g, textvariable=self.modo, values=list(MODOS), state="readonly",
                     width=42).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(g, text="Contraseña (opcional):").grid(row=1, column=0, sticky="w", pady=5)
        self.pwd_c = ttk.Entry(g, show="•", width=30)
        self.pwd_c.grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(g, text="Guardar como:").grid(row=2, column=0, sticky="w")
        self.dest = tk.StringVar()
        ttk.Entry(g, textvariable=self.dest, width=60).grid(row=2, column=1, sticky="we", padx=5)
        ttk.Button(g, text="...", width=3, command=self._pick_dest).grid(row=2, column=2)
        g.columnconfigure(1, weight=1)

        self.btn_c = ttk.Button(f, text="COMPRIMIR", style="Accent.TButton", command=self._run_comprimir)
        self.btn_c.pack(pady=(10, 0), ipadx=20, ipady=4)

    def _add_files(self):
        for p in filedialog.askopenfilenames(title="Selecciona archivos"):
            self.lista.insert("end", p)
        self._sugerir_destino()

    def _add_dir(self):
        p = filedialog.askdirectory(title="Selecciona carpeta")
        if p:
            self.lista.insert("end", p)
            self._sugerir_destino()

    def _remove(self):
        for i in reversed(self.lista.curselection()):
            self.lista.delete(i)

    def _sugerir_destino(self):
        if not self.dest.get() and self.lista.size():
            p = Path(self.lista.get(0))
            self.dest.set(str(p.parent / f"{p.stem if p.is_file() else p.name}.7z"))

    def _pick_dest(self):
        p = filedialog.asksaveasfilename(defaultextension=".7z", filetypes=[("Archivo 7z", "*.7z")])
        if p:
            self.dest.set(p)

    def _run_comprimir(self):
        entradas = list(self.lista.get(0, "end"))
        if not entradas:
            return messagebox.showwarning(APP_NAME, "Agrega archivos o carpetas.")
        if not self.dest.get():
            return messagebox.showwarning(APP_NAME, "Indica dónde guardar el .7z.")
        destino = Path(self.dest.get())
        if destino.suffix.lower() != ".7z":
            destino = destino.with_suffix(".7z")
        pwd = self.pwd_c.get() or None
        self._worker(lambda: comprimir(entradas, destino, self.modo.get(), pwd, self.log),
                     self.btn_c, "Compresión terminada y verificada.")

    # ---------- Extraer ----------
    def _tab_extraer(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Extraer  ")
        g = ttk.Frame(f)
        g.pack(fill="x")
        self.arch = tk.StringVar()
        self.carp = tk.StringVar()
        ttk.Label(g, text="Archivo .7z:").grid(row=0, column=0, sticky="w")
        ttk.Entry(g, textvariable=self.arch, width=60).grid(row=0, column=1, sticky="we", padx=5)
        ttk.Button(g, text="...", width=3, command=lambda: self.arch.set(
            filedialog.askopenfilename(filetypes=[("Archivo 7z", "*.7z")]) or self.arch.get())).grid(row=0, column=2)
        ttk.Label(g, text="Extraer en:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(g, textvariable=self.carp, width=60).grid(row=1, column=1, sticky="we", padx=5)
        ttk.Button(g, text="...", width=3, command=lambda: self.carp.set(
            filedialog.askdirectory() or self.carp.get())).grid(row=1, column=2)
        ttk.Label(g, text="Contraseña:").grid(row=2, column=0, sticky="w")
        self.pwd_e = ttk.Entry(g, show="•", width=30)
        self.pwd_e.grid(row=2, column=1, sticky="w", padx=5)
        g.columnconfigure(1, weight=1)
        self.btn_e = ttk.Button(f, text="EXTRAER", style="Accent.TButton", command=self._run_extraer)
        self.btn_e.pack(pady=15, ipadx=20, ipady=4)

    def _run_extraer(self):
        a, c = self.arch.get(), self.carp.get()
        if not a:
            return messagebox.showwarning(APP_NAME, "Selecciona un archivo .7z.")
        c = c or str(Path(a).with_suffix(""))
        pwd = self.pwd_e.get() or None
        self._worker(lambda: extraer(Path(a), Path(c), pwd, self.log), self.btn_e, "Extracción terminada.")

    # ---------- Utilidades ----------
    def log(self, msg):
        def _w():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _w)

    def _worker(self, fn, boton, ok_msg):
        boton.state(["disabled"])
        self.prog.start(12)

        def run():
            try:
                fn()
                self.after(0, lambda: messagebox.showinfo(APP_NAME, ok_msg))
            except Exception as ex:
                err = str(ex) or ex.__class__.__name__
                self.log(f"✗ Error: {err}")
                self.after(0, lambda: messagebox.showerror(APP_NAME, err))
            finally:
                self.after(0, lambda: (self.prog.stop(), boton.state(["!disabled"])))
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()

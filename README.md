# MOJ Compresor

Compresor de archivos **sin pérdida** que busca el tamaño mínimo posible, en formato `.7z` estándar.
© MOJ Soluciones

## Características
- **Modo Máximo**: prueba LZMA2 Ultra, PPMd, BZip2 y LZMA2 + x86, y guarda el resultado más pequeño.
- **Modo Ultra**: solo LZMA2, más rápido.
- Archivo sólido para aprovechar la redundancia entre archivos.
- **Verificación SHA-256** de cada archivo tras comprimir; si algo no coincide, no se guarda.
- Contraseña opcional (AES-256 con cifrado de nombres).
- Pestaña para extraer `.7z`. Compatible con 7-Zip, WinRAR y PeaZip.

## Uso
```bash
pip install -r requirements.txt
python moj_compresor.py
```
Ejecutable portable para Windows: ejecuta `construir_exe.bat` (queda en `dist\MOJ_Compresor.exe`).

## Nota
Los archivos ya comprimidos (JPG, PNG, MP4, MP3, ZIP, PDF con imágenes, DOCX/XLSX) casi no se reducen.
Rinde mucho en TXT, CSV, JSON, SQL, XML, logs, bases de datos y código.

import os
import qrcode

def generar_qr_cliente(cliente_id):
    """
    Genera un código QR para un cliente y devuelve la ruta del archivo.
    El QR se guarda en static/qr/cliente_<id>.png
    """
    # Carpeta donde se guardarán los QR
    qr_dir = "static/qr"
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)  # crear la carpeta si no existe

    # Ruta del archivo QR
    ruta_qr = os.path.join(qr_dir, f"cliente_{cliente_id}.png")

    # Solo generar si no existe
    if not os.path.exists(ruta_qr):
        img = qrcode.make(f"CLIENTE:{cliente_id}")
        img.save(ruta_qr)

    return ruta_qr

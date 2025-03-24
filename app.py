from flask import Flask, render_template, request, send_file
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import base64
import io
import tempfile
import re
import os

app = Flask(__name__)

PDF_TEMPLATE_PATH = "modello.pdf"

@app.route('/')
def form():
    return render_template("index.html")

@app.route('/fill-pdf', methods=['POST'])
def fill_pdf():
    data = request.json
    nome_cognome = data["nome_cognome"].strip()
    nie = data["nie"]

    if not nome_cognome:
    filename = "Documento.pdf"
else:
    nome_cognome = re.sub(r'[\/:*?"<>|]', "", nome_cognome)
    filename = f"{nome_cognome}_documentoFirmato.pdf"


    def mm_to_pt(mm):
        return mm * 2.83

    def invert_y(mm):
        return 842 - mm_to_pt(mm)

    NOME_X, NOME_Y = mm_to_pt(40), invert_y(125)
    NIE_X, NIE_Y = mm_to_pt(157), invert_y(125)
    FIRMA_X, FIRMA_Y = mm_to_pt(138), invert_y(270)
    SELLO_X, SELLO_Y = mm_to_pt(40), invert_y(270)

    def convert_base64_to_png(image_base64):
        try:
            image_data = base64.b64decode(image_base64.split(",")[1])
            image = Image.open(io.BytesIO(image_data)).convert("RGBA")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            image.save(temp_file.name, format="PNG")
            return temp_file.name
        except Exception as e:
            print(f"Errore nella conversione dell'immagine: {e}")
            return None

    firma_path = convert_base64_to_png(data["firma"]) if data["firma"].startswith("data:image/png;base64,") else None
    sello_path = convert_base64_to_png(data["sello"]) if data["sello"].startswith("data:image/png;base64,") else None

    try:
        with open(PDF_TEMPLATE_PATH, "rb") as template_file:
            pdf_reader = PdfReader(template_file)
            pdf_writer = PdfWriter()

            overlay_pdf = io.BytesIO()
            c = canvas.Canvas(overlay_pdf, pagesize=letter)

            c.drawString(NOME_X, NOME_Y, nome_cognome)
            c.drawString(NIE_X, NIE_Y, nie)

            if firma_path:
                c.drawImage(firma_path, FIRMA_X, FIRMA_Y, width=120, height=60, mask="auto")
            if sello_path:
                c.drawImage(sello_path, SELLO_X, SELLO_Y, width=120, height=60, mask="auto")

            c.save()
            overlay_pdf.seek(0)

            overlay_reader = PdfReader(overlay_pdf)
            for i in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[i]
                if i == 0:
                    page.merge_page(overlay_reader.pages[0])
                pdf_writer.add_page(page)

            output_pdf = io.BytesIO()
            pdf_writer.write(output_pdf)
            output_pdf.seek(0)

        print(f" Il file generato sarà: {filename}")

        try:
            return send_file(output_pdf, as_attachment=True, download_name=filename)
        except TypeError:
            return send_file(output_pdf, as_attachment=True, attachment_filename=filename)

    finally:
        if firma_path and os.path.exists(firma_path):
            os.remove(firma_path)
        if sello_path and os.path.exists(sello_path):
            os.remove(sello_path)

if __name__ == '__main__':
    app.run()
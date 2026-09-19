# -*- coding: utf-8 -*-
"""
pdf_control.py — PDFs para JARVIS (Telegram).
Portado del desmenuzado JARVIS-HRZ (actions/document_creator + pdf_fonts)
con codigo limpio: crea PDFs con estilo usando ReportLab, lee y une PDFs
con pypdf.

Uso:
  python cli.py pdf crear "<markdown|texto>|ruta.md|ruta.txt" [salida.pdf]
  python cli.py pdf ver <archivo.pdf> [paginas iniciales]
  python cli.py pdf unir <a.pdf> <b.pdf> ... [salida.pdf]
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Paleta "mayordomo": azul petroleo + dorado.
_AZUL = "#1F4E5F"
_DORADO = "#B8860B"
_GRIS = "#555555"
_NEGRO = "#111111"


def _limpiar_inline(t):
    """Quita **negrita** y *cursiva* dejando el texto limpio (para celdas)."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    return t


def _es_tabla(linea):
    return linea.strip().startswith("|") and "|" in linea.strip()[1:]


def _parse_tabla(linea):
    celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
    return [_limpiar_inline(c) for c in celdas]


def _procesar_markdown(texto):
    """Convierte markdown simple a una lista de bloques para ReportLab."""
    bloques = []  # (tipo, datos)
    lineas = texto.splitlines()
    i = 0
    en_codigo = False
    buf_codigo = []
    buf_lista = []
    buf_tabla = []
    buf_para = []

    def flush_para():
        if buf_para:
            bloques.append(("p", _limpiar_inline(" ".join(buf_para))))
            buf_para.clear()

    def flush_lista():
        if buf_lista:
            bloques.append(("lista", list(buf_lista)))
            buf_lista.clear()

    def flush_tabla():
        if len(buf_tabla) >= 2:
            bloques.append(("tabla", list(buf_tabla)))
        buf_tabla.clear()

    while i < len(lineas):
        l = lineas[i]
        s = l.strip()
        if s.startswith("```"):
            if en_codigo:
                bloques.append(("codigo", "\n".join(buf_codigo)))
                buf_codigo = []
                en_codigo = False
            else:
                flush_para(); flush_lista(); flush_tabla()
                en_codigo = True
            i += 1
            continue
        if en_codigo:
            buf_codigo.append(l)
            i += 1
            continue
        if not s:
            flush_para(); flush_lista(); flush_tabla()
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            flush_para(); flush_lista(); flush_tabla()
            nivel = len(m.group(1))
            bloques.append(("h", (nivel, _limpiar_inline(m.group(2)))))
            i += 1
            continue
        if re.match(r"^[-*]\s+", s) or re.match(r"^\d+[.)]\s+", s):
            flush_para(); flush_tabla()
            buf_lista.append(_limpiar_inline(re.sub(r"^[-*]\s+|^\d+[.)]\s+", "", s)))
            i += 1
            continue
        if _es_tabla(l):
            flush_para(); flush_lista()
            if not buf_tabla:
                buf_tabla.append(_parse_tabla(l))  # header
            else:
                buf_tabla.append(_parse_tabla(l))
            i += 1
            continue
        # separador de tabla |---|---|
        if buf_tabla and re.match(r"^[\s|:\-]+$", s):
            i += 1
            continue
        flush_lista(); flush_tabla()
        buf_para.append(s)
        i += 1
    flush_para(); flush_lista(); flush_tabla()
    if en_codigo:
        bloques.append(("codigo", "\n".join(buf_codigo)))
    return bloques


def crear_pdf(texto, salida, titulo="Documento"):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle, Preformatted)

    def col_hex(h):
        h = h.lstrip("#")
        return colors.HexColor("#" + h)

    estilos = {
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20,
                             textColor=col_hex(_AZUL), spaceAfter=10,
                             spaceBefore=4),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15,
                             textColor=col_hex(_AZUL), spaceAfter=8,
                             spaceBefore=10),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=12,
                             textColor=col_hex(_DORADO), spaceAfter=6,
                             spaceBefore=8),
        "h4": ParagraphStyle("h4", fontName="Helvetica-Bold", fontSize=11,
                             textColor=_GRIS, spaceAfter=5, spaceBefore=6),
        "p": ParagraphStyle("p", fontName="Helvetica", fontSize=10.5,
                            leading=14, textColor=_NEGRO, spaceAfter=6),
        "li": ParagraphStyle("li", fontName="Helvetica", fontSize=10.5,
                             leading=14, textColor=_NEGRO, leftIndent=14,
                             bulletIndent=2, spaceAfter=3),
        "code": ParagraphStyle("code", fontName="Courier", fontSize=8.5,
                               leading=11, textColor=col_hex(_AZUL),
                               backColor=colors.Color(0.95, 0.96, 0.97),
                               borderPadding=6, spaceAfter=8),
    }

    doc = SimpleDocTemplate(salida, pagesize=A4,
                            rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=titulo, author="JARVIS")
    story = []
    if titulo:
        story.append(Paragraph(titulo, estilos["h1"]))
        story.append(Spacer(1, 4))

    for tipo, datos in _procesar_markdown(texto):
        if tipo == "h":
            nivel, txt = datos
            story.append(Paragraph(txt, estilos[f"h{min(nivel, 4)}"]))
        elif tipo == "p":
            if datos:
                story.append(Paragraph(datos.replace("\n", " "), estilos["p"]))
        elif tipo == "lista":
            for item in datos:
                story.append(Paragraph(f"• {item}", estilos["li"]))
        elif tipo == "codigo":
            story.append(Preformatted(datos, estilos["code"]))
        elif tipo == "tabla":
            filas = datos
            colores_filas = [col_hex(_AZUL)] + [colors.white] * (len(filas) - 1)
            tbl = Table(filas)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), col_hex(_AZUL)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.Color(0.96, 0.97, 0.98)]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 8))

    def pie(canvas, docu):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(col_hex(_GRIS))
        canvas.drawCentredString(A4[0] / 2, 1 * cm,
                                 "Generado por JARVIS · " + titulo[:60])
        canvas.restoreState()

    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    return salida


def leer_pdf(ruta, paginas=5):
    from pypdf import PdfReader
    reader = PdfReader(ruta)
    n = len(reader.pages)
    salida = [f"PDF: {os.path.basename(ruta)} · {n} pagina(s)"]
    for i in range(min(paginas, n)):
        txt = (reader.pages[i].extract_text() or "").strip()
        if txt:
            salida.append(f"--- Pagina {i + 1} ---")
            salida.append(txt[:1200])
    return "\n".join(salida) if len(salida) > 1 else "No pude extraer texto del PDF."


def unir_pdfs(archivos, salida):
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for a in archivos:
        w.append(PdfReader(a))
    with open(salida, "wb") as f:
        w.write(f)
    return salida


def _recurso(ruta):
    """Si el argumento es un archivo existente, devuelve su contenido."""
    if os.path.isfile(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return None


def _main(argv):
    args = list(argv)  # argv[0]=alias
    if len(args) < 2:
        print(__doc__)
        return 2
    accion = args[1].lower()
    resto = args[2:]

    if accion in ("crear", "nuevo", "hacer"):
        if not resto:
            print("Uso: python cli.py pdf crear '<texto o ruta.md>' [salida.pdf]")
            return 2
        entrada = resto[0]
        contenido = entrada if not os.path.isfile(entrada) else _recurso(entrada)
        if contenido is None:
            contenido = entrada
        base = os.path.splitext(os.path.basename(entrada))[0] if os.path.isfile(entrada) \
            else "documento"
        salida = resto[1] if len(resto) > 1 else os.path.join(
            os.path.expanduser("~"), "Desktop",
            f"{base.replace(' ', '_')}.pdf")
        if not os.path.isabs(salida):
            salida = os.path.join(os.getcwd(), salida)
        if not salida.lower().endswith(".pdf"):
            salida += ".pdf"
        crear_pdf(contenido, salida, titulo=base.replace("_", " ").title())
        print(f"PDF creado: {salida}")
        return 0

    if accion in ("ver", "leer", "texto"):
        if not resto:
            print("Uso: python cli.py pdf ver <archivo.pdf> [paginas]")
            return 2
        pag = int(resto[1]) if len(resto) > 1 else 5
        print(leer_pdf(resto[0], pag))
        return 0

    if accion in ("unir", "merge", "fusionar"):
        if len(resto) < 2:
            print("Uso: python cli.py pdf unir <a.pdf> <b.pdf> [salida.pdf]")
            return 2
        archivos = [r for r in resto if r.lower().endswith(".pdf")]
        if len(archivos) < 2:
            print("Necesito al menos 2 archivos PDF.")
            return 2
        salida = os.path.join(os.path.expanduser("~"), "Desktop",
                              "unido_" + os.path.basename(archivos[0]))
        if len([r for r in resto if not r.lower().endswith(".pdf")]):
            salida = [r for r in resto if not r.lower().endswith(".pdf")][0]
            if not salida.lower().endswith(".pdf"):
                salida += ".pdf"
        unir_pdfs(archivos, salida)
        print(f"PDFs unidos: {salida}")
        return 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


_FONT_REGISTERED = False


def _register_turkish_font() -> str:
    global _FONT_REGISTERED
    if not _FONT_REGISTERED:
        candidates = [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
        font_path = next((path for path in candidates if path.exists()), None)
        if font_path is None:
            raise RuntimeError("PDF için Türkçe karakter destekleyen yazı tipi bulunamadı.")
        pdfmetrics.registerFont(TTFont("AkilliSans", str(font_path)))
        bold_candidates = [
            font_path.with_name("DejaVuSans-Bold.ttf"),
            font_path.with_name("LiberationSans-Bold.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ]
        bold_path = next((path for path in bold_candidates if path.exists()), None)
        if bold_path:
            pdfmetrics.registerFont(TTFont("AkilliSans-Bold", str(bold_path)))
        else:
            pdfmetrics.registerFont(TTFont("AkilliSans-Bold", str(font_path)))
        _FONT_REGISTERED = True
    return "AkilliSans"


def _styles():
    _register_turkish_font()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="AkilliTitle", parent=styles["Title"], fontName="AkilliSans-Bold",
        fontSize=18, leading=23, alignment=TA_CENTER, textColor=colors.HexColor("#14243a"),
        spaceAfter=8 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AkilliHeading", parent=styles["Heading2"], fontName="AkilliSans-Bold",
        fontSize=12, leading=16, textColor=colors.HexColor("#155eef"),
        spaceBefore=5 * mm, spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AkilliBody", parent=styles["BodyText"], fontName="AkilliSans",
        fontSize=9, leading=13, spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="AkilliSmall", parent=styles["BodyText"], fontName="AkilliSans",
        fontSize=8, leading=11,
    ))
    return styles


def _p(value: object, style) -> Paragraph:
    return Paragraph(xml_escape(str(value if value is not None else "—")).replace("\n", "<br/>"), style)


def build_exam_result_pdf(
    *, exam_title: str, student_name: str, score: int | None,
    details: list[dict], completed_at: str | None = None,
) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"{exam_title} - Sınav Sonucu",
        author="Akıllı Sınav",
    )
    story = [
        Paragraph("AKILLI SINAV", styles["AkilliTitle"]),
        Paragraph("Sınav Sonuç Raporu", styles["AkilliHeading"]),
        _p(f"Sınav: {exam_title}", styles["AkilliBody"]),
        _p(f"Öğrenci: {student_name}", styles["AkilliBody"]),
        _p(f"Puan: {score if score is not None else '—'} / 100", styles["AkilliBody"]),
        _p(f"Tamamlanma: {completed_at or '—'}", styles["AkilliBody"]),
        Spacer(1, 3 * mm),
    ]
    correct = sum(1 for item in details if item.get("is_correct"))
    answered = sum(1 for item in details if item.get("selected_option"))
    story.append(_p(f"Özet: {correct} doğru • {answered - correct} yanlış • {len(details) - answered} boş", styles["AkilliBody"]))
    for item in details:
        story.append(Paragraph(f"{item.get('position', '')}. {xml_escape(str(item.get('prompt', '')))}", styles["AkilliHeading"]))
        options = item.get("options") or []
        for option in options:
            key = str(option.get("key", ""))
            marker = " (Doğru cevap)" if key == item.get("correct_option") else ""
            marker += " (Senin cevabın)" if key == item.get("selected_option") else ""
            story.append(_p(f"{key}) {option.get('text', '')}{marker}", styles["AkilliSmall"]))
        story.append(_p(f"Sonuç: {'Doğru' if item.get('is_correct') else ('Boş' if not item.get('selected_option') else 'Yanlış')}", styles["AkilliBody"]))
        story.append(_p(f"Açıklama: {item.get('explanation', '')}", styles["AkilliBody"]))
        story.append(Spacer(1, 2 * mm))
    doc.build(story)
    return buffer.getvalue()


def build_parent_progress_pdf(*, student_name: str, progress: dict) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"{student_name} - Öğrenci Gelişim Raporu",
        author="Akıllı Sınav",
    )
    story = [
        Paragraph("AKILLI SINAV", styles["AkilliTitle"]),
        Paragraph("Öğrenci Gelişim Raporu", styles["AkilliHeading"]),
        _p(f"Öğrenci: {student_name}", styles["AkilliBody"]),
        _p(f"Tamamlanan sınav: {progress.get('completed_exam_count', 0)}", styles["AkilliBody"]),
        _p(f"Sınav puan ortalaması: {progress.get('average_score') if progress.get('average_score') is not None else 'Henüz yok'}", styles["AkilliBody"]),
        Paragraph("Son sınavlar", styles["AkilliHeading"]),
    ]
    exams = progress.get("recent_exams") or []
    if exams:
        data = [[_p("Sınav", styles["AkilliSmall"]), _p("Puan", styles["AkilliSmall"]), _p("Tarih", styles["AkilliSmall"])]]
        data.extend([[_p(e.get("title"), styles["AkilliSmall"]), _p(e.get("score"), styles["AkilliSmall"]),
                      _p((e.get("completed_at") or "")[:10], styles["AkilliSmall"])] for e in exams])
        table = Table(data, colWidths=[90 * mm, 22 * mm, 55 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0fb")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d5deeb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
    else:
        story.append(_p("Henüz tamamlanmış sınav bulunmuyor.", styles["AkilliBody"]))
    story.append(Paragraph("Geliştirilmesi gereken kazanımlar", styles["AkilliHeading"]))
    outcomes = progress.get("learning_outcomes") or []
    if outcomes:
        for outcome in outcomes:
            story.append(_p(f"{outcome.get('code')}: {outcome.get('description')}", styles["AkilliBody"]))
            story.append(_p(f"Başarı: %{outcome.get('success_rate', 0)} • Doğru: {outcome.get('correct', 0)} / Cevaplanan: {outcome.get('answered', 0)}", styles["AkilliSmall"]))
    else:
        story.append(_p("Henüz yeterli kazanım verisi yok.", styles["AkilliBody"]))
    doc.build(story)
    return buffer.getvalue()

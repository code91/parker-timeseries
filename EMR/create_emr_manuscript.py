#!/usr/bin/env python3
"""
Create EMR-formatted Word document from Bird Over Time manuscript.
Based on EMR_article_template2020.docx formatting specifications.
"""

import fitz  # PyMuPDF for image extraction
from docx import Document
from docx.shared import Pt, Inches, Cm, Emu, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement, parse_xml
import os, re


WORK_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(WORK_DIR, "Bird Over Time.pdf")
TEMPLATE_PATH = os.path.join(WORK_DIR, "EMR_article_template2020.docx")
OUTPUT_PATH = os.path.join(WORK_DIR, "Bird_Over_Time_EMR.docx")
IMG_DIR = os.path.join(WORK_DIR, "figures")
os.makedirs(IMG_DIR, exist_ok=True)

# ── Extract images from PDF ──────────────────────────────────────────────
print("Extracting images from PDF...")
pdf = fitz.open(PDF_PATH)
img_count = 0
img_paths = {}

for page_num in range(len(pdf)):
    page = pdf[page_num]
    images = page.get_images(full=True)
    for img_idx, img_info in enumerate(images):
        xref = img_info[0]
        base_image = pdf.extract_image(xref)
        if base_image:
            img_bytes = base_image["image"]
            img_ext = base_image["ext"]
            # Skip very small images (icons, artifacts)
            if len(img_bytes) < 5000:
                continue
            img_count += 1
            img_path = os.path.join(IMG_DIR, f"fig_{img_count}.{img_ext}")
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            img_paths[img_count] = img_path
            print(f"  Extracted image {img_count} from page {page_num+1}: {len(img_bytes)} bytes")

pdf.close()
print(f"Total images extracted: {img_count}")

# ── Override with regenerated figures ────────────────────────────────────
# Two figures were regenerated after the cluster->strategy renumbering so that
# their printed labels match the manuscript. Where a regenerated file exists it
# takes precedence over the copy extracted from the old PDF.
REGEN_DIR = os.path.join(WORK_DIR, "..", "regenerated")
REGENERATED = {
    4:  "pipeline2.png",                 # analysis pipeline, relabelled after review
    11: "cluster_characteristics.png",   # strategy characteristics
    13: "significance_by_lag.png",       # Granger causation rates
}
for idx, fname in REGENERATED.items():
    src = os.path.normpath(os.path.join(REGEN_DIR, fname))
    if os.path.exists(src):
        img_paths[idx] = src
        print(f"  Using regenerated figure for image {idx}: {fname}")
    else:
        print(f"  WARNING: regenerated figure missing, falling back to PDF extract: {src}")

# ── Open template and clear content ──────────────────────────────────────
doc = Document(TEMPLATE_PATH)

# Clear all existing paragraphs content
for p in doc.paragraphs:
    for run in p.runs:
        run.text = ""
    p.text = ""

# Remove all paragraphs except first (can't remove all)
body = doc.element.body
for child in list(body):
    if child.tag.endswith('}p') or child.tag.endswith('}tbl'):
        body.remove(child)

# ── Helper functions ─────────────────────────────────────────────────────

def add_empty_line(doc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    return p

def add_title_line(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.size = Pt(16)
    run.font.bold = True
    run.font.name = "Times New Roman"
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    return p

def add_author(doc, name):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(name.upper())
    run.font.size = Pt(10)
    run.font.name = "Times New Roman"
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    return p

def add_affiliation(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.font.size = Pt(10)
    run.font.italic = True
    run.font.name = "Times New Roman"
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    return p

def add_heading1(doc, text):
    """Primary heading: ALL CAPS, bold, centered, 11pt"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.style = doc.styles['Heading 1']
    run = p.add_run(text.upper())
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.name = "Times New Roman"
    pf = p.paragraph_format
    pf.space_before = Pt(12)
    pf.space_after = Pt(0)
    return p

def add_heading2(doc, text):
    """Secondary heading: Title Case, bold, left-justified, 11pt"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.style = doc.styles['Heading 2']
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.name = "Times New Roman"
    pf = p.paragraph_format
    pf.space_before = Pt(12)
    pf.space_after = Pt(0)
    return p

def add_heading3(doc, text):
    """Tertiary heading: ALL CAPS, not bold, left-justified, 9pt"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.style = doc.styles['Heading 3']
    run = p.add_run(text.upper())
    run.font.size = Pt(9)
    run.font.bold = False
    run.font.name = "Times New Roman"
    pf = p.paragraph_format
    pf.space_before = Pt(10)
    pf.space_after = Pt(0)
    return p

def add_body(doc, text, first_line_indent=True, first_word_caps=False):
    """Body text: 10pt, justified, Times New Roman"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    if first_line_indent:
        pf.first_line_indent = Inches(0.5)

    if first_word_caps and text:
        # First word in uppercase
        parts = text.split(' ', 1)
        run1 = p.add_run(parts[0].upper())
        run1.font.size = Pt(10)
        run1.font.name = "Times New Roman"
        if len(parts) > 1:
            run2 = p.add_run(' ' + parts[1])
            run2.font.size = Pt(10)
            run2.font.name = "Times New Roman"
    else:
        run = p.add_run(text)
        run.font.size = Pt(10)
        run.font.name = "Times New Roman"
    return p

def add_body_with_italic(doc, segments, first_line_indent=True):
    """Add body text with mixed italic/bold/normal segments.
    segments: list of (text, style) where style is 'normal', 'italic', 'bold', 'bolditalic'
    """
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    if first_line_indent:
        pf.first_line_indent = Inches(0.5)

    for text, style in segments:
        run = p.add_run(text)
        run.font.size = Pt(10)
        run.font.name = "Times New Roman"
        if style == 'italic':
            run.font.italic = True
        elif style == 'bold':
            run.font.bold = True
        elif style == 'bolditalic':
            run.font.bold = True
            run.font.italic = True
    return p

OMML_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"')


def _m_run(text, upright=True):
    """A run inside an equation. Upright for operators and multi-letter names,
    italic (the OMML default) for single-letter variables."""
    style = '<m:rPr><m:sty m:val="p"/></m:rPr>' if upright else ''
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return f'<m:r>{style}<m:t xml:space="preserve">{text}</m:t></m:r>'


def _m_sub(base, sub, base_upright=True):
    return (f'<m:sSub><m:e>{_m_run(base, base_upright)}</m:e>'
            f'<m:sub>{_m_run(sub, False)}</m:sub></m:sSub>')


def _m_subsup(base, sub, sup):
    return (f'<m:sSubSup><m:e>{_m_run(base)}</m:e>'
            f'<m:sub>{_m_run(sub, False)}</m:sub>'
            f'<m:sup>{_m_run(sup)}</m:sup></m:sSubSup>')


def _m_nary(sub, sup, body):
    return ('<m:nary><m:naryPr><m:chr m:val="\u2211"/><m:limLoc m:val="undOvr"/>'
            '<m:ctrlPr/></m:naryPr>'
            f'<m:sub>{sub}</m:sub><m:sup>{sup}</m:sup><m:e>{body}</m:e></m:nary>')


def add_equation(doc, omml_body):
    """Insert a real OMML equation, centered on its own line.

    Word and LibreOffice both render this as a native equation object rather
    than as formatted text, which is what the reviewer asked for.
    """
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    p._p.append(parse_xml(f'<m:oMath {OMML_NS}>{omml_body}</m:oMath>'))
    return p


def add_bullet(doc, text):
    """Bullet point"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.25)
    # Add bullet character
    run = p.add_run("\u2022 " + text)
    run.font.size = Pt(10)
    run.font.name = "Times New Roman"
    return p

def add_sub_bullet(doc, text):
    """Sub-bullet point"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.left_indent = Inches(0.75)
    pf.first_line_indent = Inches(-0.25)
    run = p.add_run("\u25B8 " + text)
    run.font.size = Pt(10)
    run.font.name = "Times New Roman"
    return p

def add_figure_caption(doc, fig_num, caption_text, alt_text=""):
    """Figure caption: bold Fig. X. followed by normal caption text"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    run1 = p.add_run(f"Fig. {fig_num}. ")
    run1.font.size = Pt(10)
    run1.font.bold = True
    run1.font.name = "Times New Roman"
    run2 = p.add_run(caption_text)
    run2.font.size = Pt(10)
    run2.font.name = "Times New Roman"
    return p

def add_figure_image(doc, img_path, width=None):
    """Insert an image centered"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if os.path.exists(img_path):
        run = p.add_run()
        if width:
            run.add_picture(img_path, width=width)
        else:
            run.add_picture(img_path, width=Inches(5.5))
    else:
        run = p.add_run(f"[Image: {os.path.basename(img_path)}]")
        run.font.size = Pt(10)
        run.font.name = "Times New Roman"
    return p

def add_table_heading(doc, text):
    """Table heading above table"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    run1 = p.add_run(text)
    run1.font.size = Pt(10)
    run1.font.bold = True
    run1.font.name = "Times New Roman"
    return p

def create_table(doc, headers, rows, col_widths=None):
    """Create a formatted table"""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(header)
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.name = "Times New Roman"

    # Data rows
    for r, row_data in enumerate(rows):
        for c, cell_text in enumerate(row_data):
            cell = table.rows[r + 1].cells[c]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(cell_text))
            run.font.size = Pt(9)
            run.font.name = "Times New Roman"

    # Style borders
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement('w:tblPr')
    borders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'bottom']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        borders.append(border)
    for border_name in ['left', 'right', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'none')
        border.set(qn('w:sz'), '0')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        borders.append(border)
    # insideH - thin line for header separation
    border = OxmlElement('w:insideH')
    border.set(qn('w:val'), 'single')
    border.set(qn('w:sz'), '2')
    border.set(qn('w:space'), '0')
    border.set(qn('w:color'), '000000')
    borders.append(border)
    tblPr.append(borders)

    return table

def add_reference(doc, text):
    """Reference entry with hanging indent"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(6)
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.5)
    run = p.add_run(text)
    run.font.size = Pt(10)
    run.font.name = "Times New Roman"
    return p

def add_reference_with_italic(doc, segments):
    """Reference with italic journal names"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(6)
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.5)
    for text, style in segments:
        run = p.add_run(text)
        run.font.size = Pt(10)
        run.font.name = "Times New Roman"
        if style == 'italic':
            run.font.italic = True
    return p


# ══════════════════════════════════════════════════════════════════════════
# BUILD THE MANUSCRIPT
# ══════════════════════════════════════════════════════════════════════════

print("Building EMR manuscript...")

# ── Title ────────────────────────────────────────────────────────────────
add_title_line(doc, '"Bird" Over Time:')
add_title_line(doc, "A Time Series Analysis of Charlie Parker's Harmonic Complexity")
add_empty_line(doc)

# ── Author ───────────────────────────────────────────────────────────────
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("MICHELE ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run('"')
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("MIKE")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run('"')
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run(" RUBINI[1]")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)

add_affiliation(doc, "Independent Researcher")
add_empty_line(doc)

# ── Abstract ─────────────────────────────────────────────────────────────
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
run = p.add_run("ABSTRACT: ")
run.font.size = Pt(10)
run.font.bold = True
run.font.name = "Times New Roman"
abstract_text = (
    "This study presents a computational time series analysis of Charlie Parker's improvisational "
    "practice using the complete Charlie Parker Omnibook corpus. We develop metrics for harmonic "
    "complexity, dissonance, and rate of change, analyzing temporal patterns through phrase-level "
    "segmentation using actual rest boundaries. We identify three distinct improvisational strategies "
    "and introduce two measures: "
)
run = p.add_run(abstract_text)
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("gravity")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run.font.italic = True
run = p.add_run(", the extent to which one harmonic dimension helps predict another across phrase boundaries, tested with Granger causality; and ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("robustness")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run.font.italic = True
run = p.add_run(", the number of complete triads a given interval vector contains.")
run.font.size = Pt(10)
run.font.name = "Times New Roman"

add_empty_line(doc)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.first_line_indent = Inches(0.5)
abstract2 = (
    'In most performances, what Parker played in one phrase does not help predict the next: in 80.4% '
    'of solos, dissonance carries no predictive information about the complexity that follows, or the '
    'reverse. Phrase-to-phrase reaction is therefore the exception, and organization above the phrase, '
    'at the level of the chorus, appears to be the rule. Clustering the solos on their complexity, '
    'variability and predictability yields three groups that differ in exactly this respect: the group '
    'we call Exploratory shows almost no phrase-to-phrase prediction (3.6%), the Balanced group a '
    'moderate amount (11.0%), and the Contrasting group organizes itself through phrase duration '
    'instead (23.1%). Where prediction does hold, it runs more often from dissonance to subsequent '
    'complexity than the '
)
run = p.add_run(abstract2)
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("reverse (17.4% versus 8.7%), though this difference is suggestive rather than conclusive (")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("p")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run.font.italic = True
run = p.add_run(" = .109). ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run(
    "Separately, the interval vectors Parker uses most often contain the fewest complete triads ("
)
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("r")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run.font.italic = True
run = p.add_run(" = \u2212.350, ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("p")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run.font.italic = True
run = p.add_run(" < .001, Cohen's ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("d")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run.font.italic = True
run = p.add_run(
    " = \u22120.87), suggesting that his fluency rests on structures that stay open to many "
    "continuations rather than on an accumulation of rare material."
)
run.font.size = Pt(10)
run.font.name = "Times New Roman"

add_empty_line(doc)

# Submitted/Published dates placeholder
add_body(doc, "Submitted 2025 Month X; accepted 20XX Month X.", first_line_indent=False)
add_body(doc, "Published 20XX Month X; https://doi.org/10.18061/emr.vXXiX-X.XXXX", first_line_indent=False)
add_empty_line(doc)

# ── Keywords ─────────────────────────────────────────────────────────────
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
run = p.add_run("KEYWORDS: ")
run.font.size = Pt(10)
run.font.bold = True
run.font.name = "Times New Roman"
run = p.add_run("Charlie Parker, computational musicology, time series analysis, interval vectors, jazz improvisation, Granger causality")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
add_empty_line(doc)

# ══════════════════════════════════════════════════════════════════════════
# INTRODUCTION
# ══════════════════════════════════════════════════════════════════════════

add_body_with_italic(doc, [
    ("HOW", "normal"),
    (" pitch content of a jazz solo changes over the course of a performance in ways that remain "
     "incompletely understood despite extensive theoretical and pedagogical attention. Charlie Parker "
     "(1920–1955), the alto saxophonist whose playing did more than any other to establish the "
     "bebop idiom of the 1940s, offers an unusually well-documented case. His recorded solos have "
     "been transcribed, catalogued, and analyzed more thoroughly than those of almost any other "
     "improviser, and they remain a reference point in jazz pedagogy. Yet the great majority of that "
     "analytical attention has addressed ", "normal"),
    ("what", "italic"),
    (" Parker played rather than ", "normal"),
    ("when", "italic"),
    (", and with what temporal shape.", "normal")
], first_line_indent=False)

add_body(doc,
    "Owens (1974) set the terms of the discussion. His dissertation catalogued roughly one hundred "
    "recurring melodic formulas, ranging from four-note fragments to multi-measure phrases, and "
    "showed that Parker subjected them to metric displacement, augmentation and diminution, "
    "addition and subtraction of notes, and altered articulation. The conclusion, that Parker's solos "
    "are assembled largely from a finite stock of pre-learned patterns, framed his language as a "
    "problem of vocabulary. Martin (1996) offered a counterweight, arguing through Schenkerian "
    "readings that Parker's solos relate to the themes they are built on in ways the formulaic account "
    "misses, and later extended the analytical frame to Parker's compositional output (Martin, 2020). "
    "Love (2012) occupies a middle position, identifying five recurring phrasing schemata and four "
    "melodic schemata in Parker's blues and arguing that these pre-learned solutions are what allow "
    "sophisticated melodies to be assembled spontaneously. Across this literature the unit of analysis "
    "is the pattern, the schema, or the voice-leading path, described largely without reference to "
    "where in a performance it falls."
)

add_body(doc,
    "The cognitive literature approaches the same material from the side of process. Pressing (1988) "
    "modeled improvisation as real-time generation constrained by a performer's knowledge base "
    "and specialist memory, and Johnson-Laird (2002) argued that the computational demands of "
    "real-time performance rule out unconstrained search, requiring instead generative procedures "
    "cheap enough to run under tempo. Berkowitz (2010) developed the parallel notion of formulas "
    "as modular building blocks transmitted through pedagogy. Norgaard (2014) found through "
    "think-aloud protocols with expert improvisers that pre-learned auditory and motor patterns "
    "dominate real-time decisions, and Norgaard, Spencer, and Montiel (2013) tested this "
    "computationally against Parker himself: in a corpus of 48 Parker solos, 82.6% of notes begin a "
    "four-interval pattern. Goldman (2016) has argued that such patterns constitute a form of "
    "procedural knowledge rather than a lookup table. This work converges on the same picture as "
    "the analytical literature, from the opposite direction: a large but bounded store of material, "
    "retrieved and recombined faster than it could be invented."
)

add_body(doc,
    "Computational corpus study has made claims of this kind testable at scale. The Jazzomat project "
    "assembled the Weimar Jazz Database and developed midlevel analysis as a way of segmenting "
    "monophonic solos into perceptually plausible units (Frieler et al., 2016a; Pfleiderer et al., 2017). "
    "Broze and Shanahan (2013) used a corpus of 1,086 jazz compositions to trace diachronic change "
    "in harmonic practice, finding both gradual drift in chord-quality distributions and abrupt "
    "changes in chord-to-chord transitions, and so demonstrating that transitions and frequencies "
    "can behave differently from one another. Merseal et al. (2023) represented melodic sequences "
    "as networks in which nodes are pitch patterns and edges are temporal continuations, providing "
    "a spatial metaphor for sequence structure. Riley and Dixon (2024) reconstructed the Omnibook "
    "through an audio-to-score transcription pipeline, producing the aligned score-audio resource "
    "this study depends on."
)

add_body(doc,
    "Harmonic complexity, the third literature this study draws on, is not a single construct. "
    "Pitch-class set theory supplies one formalization in the interval vector (Forte, 1973), which "
    "summarizes a collection by how many instances of each interval class it contains. An interval "
    "class (IC) is the distance between two pitch classes reduced to the smaller of the two possible "
    "directions, so that there are only six: IC1 (minor second or major seventh), IC2 (major second "
    "or minor seventh), IC3 (minor third or major sixth), IC4 (major third or minor sixth), IC5 "
    "(perfect fourth or fifth), and IC6 (tritone). Octave and inversional equivalence mean that "
    "{C, E, G} and {G, C, E} spread across three octaves share a single interval vector. Other "
    "traditions model complexity as distance in a tonal space (Lerdahl, 2001) or as a composite of "
    "perceptual parameters unfolding in time (Farbood, 2012), while the psychoacoustic literature "
    "grounds one component of it, sensory dissonance, in critical-band interference (Plomp & Levelt, "
    "1965; Sethares, 1993). We draw on the interval-vector formalization because it applies "
    "uniformly to the aggregated pitch content of a melodic line without requiring vertical "
    "sonorities, and on the psychoacoustic weighting to separate dissonance from density."
)

add_body(doc,
    "What these literatures share is a static unit of description. Patterns are catalogued, schemata "
    "identified, chord distributions tabulated, network topologies measured, but the resulting "
    "descriptions are largely indifferent to position within a performance. Far less work examines "
    "how such materials unfold temporally. Our time series approach complements pattern-based "
    "and network analysis by foregrounding temporal dynamics: how does complexity evolve within "
    "a solo? Do improvisers build toward climaxes or maintain consistency? Are there directional "
    "relationships in which harmonic conditions at moment t predict choices at moment t + 1? These "
    "questions require time series methodology, and the aligned Omnibook corpus now makes them "
    "answerable for Parker in particular."
)

add_body(doc,
    "This study employs time series analysis to examine 50 solos from the Charlie Parker Omnibook, "
    "treating improvisation as a process in which the intervallic content of the line changes from "
    "one chord to the next. Rather than describing that content as a static inventory, we track how "
    "it changes across a performance."
)

add_body(doc,
    "Because the terms below carry different meanings in different fields, we fix them here and use "
    "them consistently throughout."
)

add_bullet(doc,
    "Interval class. The shortest distance between two pitch classes, so that there are only six: a "
    "minor second and a major seventh are both one semitone apart when the shorter path is taken, "
    "and both count as interval class 1. We abbreviate it ic.")
add_bullet(doc,
    "Interval vector (IV). A six-place count of how many times each interval class occurs among all "
    "the notes Parker plays over one chord, written in the order (ic\u2081, ic\u2082, ic\u2083, ic\u2084, ic\u2085, ic\u2086).")
add_bullet(doc,
    "Segment. All the notes played before the next chord change: the span of a single chord symbol. "
    "One interval vector is computed per segment.")
add_bullet(doc,
    "Complexity. The sum of the six entries of an interval vector. It counts how many interval "
    "relationships the line sets up over a chord, so a line touching more distinct notes scores higher.")
add_bullet(doc,
    "Dissonance. A weighted sum of the entries for the three interval classes that produce the most "
    "acoustical roughness, defined in the Methodology.")
add_bullet(doc,
    "Rate of change. How far the interval vector of one segment sits from that of the next, measured "
    "as straight-line distance in the six-dimensional space the vectors occupy.")
add_bullet(doc,
    "Triadic content. How many complete major, minor, diminished or augmented triads can be found "
    "among the notes of a segment. An interval vector containing few of them is triadically sparse; "
    "one containing many is triadically dense.")

add_body(doc,
    "Because Parker plays one note at a time, \"intervallic content\" throughout refers to the "
    "relationships between successive notes within a chord span, not to simultaneously sounded "
    "notes. We use \"harmonic\" only where the reference is to the underlying chord progression."
)

add_body(doc,
    "Interval vectors discard a great deal: the order of the notes, how often each is repeated, the "
    "contour, the register, and the metric position at which each falls. Two passages built from the "
    "same notes in a different order, or with the chord tones falling on different beats, receive the "
    "same interval vector. This is a real cost, and we return to it in the Limitations. We accept it "
    "because it buys a single scalar description of each chord span that is comparable across tunes "
    "in different keys and at different tempos, which is what makes a time series treatment possible "
    "at all; melodic n-gram methods, which retain ordering, are correspondingly harder to compare "
    "across harmonic contexts. The two approaches answer different questions, and we take ours to "
    "complement rather than replace pattern-based work."
)

add_body_with_italic(doc, [
    ("This approach introduces two measures. ", "normal"),
    ("gravity", "italic"),
    (" asks whether one of these quantities helps predict another one phrase later, beyond what "
     "that second quantity's own past already predicts, and is tested with Granger causality. ", "normal"),
    ("robustness", "italic"),
    (" is triadic content, which we treat as an index of how many continuations a given structure "
     "leaves available. The analysis proceeds at four scales:", "normal")
], first_line_indent=True)

add_bullet(doc, "segment-level (individual chord changes)")
add_bullet(doc, "phrase-level (detected using actual rest boundaries from scores)")
add_bullet(doc, "half-chorus level (rolling windows)")
add_bullet(doc, "full-chorus level (comparing temporal evolution across choruses)")

add_body(doc,
    "Each scale answers a different question: the segment shows what Parker plays over one chord, "
    "the phrase what he plays between rests, the rolling window how stable a stretch of several "
    "phrases is, and the chorus how the solo is shaped as a whole."
)

# ══════════════════════════════════════════════════════════════════════════
# METHODOLOGY
# ══════════════════════════════════════════════════════════════════════════
add_heading1(doc, "Methodology")
add_empty_line(doc)

add_heading2(doc, "Time Series Construction and Analysis")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("We analyze the Charlie Parker Aligned Digital Omnibook, comprising 50 transcribed performances "
     "(composed melodies and solos) with aligned MusicXML and MIDI data. The notated source is the "
     "Charlie Parker Omnibook, transcribed by Ken Slone and edited by Jamey Aebersold (Slone, 1978). "
     "D\u00e9guernel et al. (2016) encoded those transcriptions as "
     "MusicXML and MIDI files; Riley and Dixon (2024) then used an audio-to-score "
     "transcription pipeline to align the notated material to the original recordings, which is what "
     "supplies a timestamp for each notated event. We take the pitches and rhythms from the Omnibook "
     "transcription and the timings from that alignment. This corpus provides:", "normal")
], first_line_indent=False)

add_bullet(doc, "Complete pitch and rhythm transcriptions")
add_bullet(doc, "Aligned MIDI timestamps enabling temporal analysis")
add_bullet(doc, "Chord progression annotations")
add_bullet(doc, "Chorus boundary markings")
add_bullet(doc, "Form structure annotations (AABA, 12-bar blues, etc.)")

add_body(doc,
    "The two sources play different roles. The MusicXML supplies pitches and notated rests, and the "
    "rests are what define phrase boundaries. The MIDI alignment supplies the elapsed time of each "
    "event, which is needed for two things the notated score cannot give: it converts the sequence of "
    "segments into a series indexed by real time rather than by bar number, so that performances at "
    "different tempos become comparable, and it lets us report segment durations in milliseconds. A "
    "reader may reasonably ask why real time is needed when segmentation itself is notational; the "
    "answer is that it is not needed for segmentation, only for the descriptive statistics and for "
    "comparability across tempos. Figure 1 summarizes the full pipeline from MusicXML input to the "
    "segment-level time series that the remaining analyses take as input."
)

# Figure 1 placeholder
add_empty_line(doc)
if 1 in img_paths:
    add_figure_image(doc, img_paths[1])
else:
    add_body(doc, "[Insert Figure 1: Computational pipeline for time series construction over the Omnibook corpus]", first_line_indent=False)
add_figure_caption(doc, 1, "Computational pipeline for time series construction over the Omnibook corpus.")
add_empty_line(doc)

add_body(doc,
    "The pipeline processed all 50 tunes successfully, extracting 3,371 segments. We "
    "identified 165 unique interval vectors and 2,145 unique transitions. MIDI alignment successfully "
    "mapped 3,024 segments (89.7%) to precise timestamps; 4 tunes failed alignment due to missing "
    "MIDI files (\"Anthropology\", \"Shaw 'Nuff\", \"Segment\", and \"Chasing the Bird\") but retained "
    "all other analytical data. Subsequent analyses requiring precise timestamps (rolling windows, "
    "autocorrelation, Granger causality) were performed on the 46 successfully aligned tunes (3,024 segments)."
)

add_body(doc,
    "The four excluded tunes represent significant compositions in Parker's repertoire, particularly "
    "\"Anthropology\" and \"Chasing the Bird\", both archetypal bebop contrafacts. While their exclusion "
    "from temporal analyses limits generalization, vocabulary and transition analyses include "
    "these tunes, ensuring core findings about Parker's harmonic vocabulary remain comprehensive."
)

add_heading3(doc, "Segmentation")
add_empty_line(doc)

add_body(doc,
    "The segment is the atomic unit of every analysis reported below, so we specify its "
    "construction in full. A segment is the span of a single chord symbol as annotated in the "
    "MusicXML score. Segment boundaries are therefore given by the corpus annotation rather than "
    "inferred: a new segment begins wherever a new chord symbol appears, and ends where the next "
    "one does. Every notated pitch whose onset falls within that span is collected, reduced to a "
    "pitch class (so that octave register is discarded and repeated pitches are counted once), and "
    "the resulting set is the segment's pitch-class content. Rests contribute nothing. A segment is "
    "retained only if its pitch-class set has cardinality of at least 3, since a two-element set has a "
    "degenerate interval vector; segments falling below this threshold are dropped rather than "
    "merged with their neighbors.",
    first_line_indent=False
)

add_body(doc,
    "This procedure yields 3,371 segments across the 50 tunes, a median of 61.5 segments per tune "
    "(range 32–122). Because segments track chord symbols, their duration is set by the harmonic "
    "rhythm of the underlying form: across the 46 MIDI-aligned tunes the median interval between "
    "consecutive segment onsets is 2,000 ms (M = 2,151, IQR [1,000, 2,000]), corresponding to one "
    "to two bars at the tempos in this corpus. Segments contain a median of 6 notated pitches "
    "(M = 6.21, range 3–18), reducing to a median of 4 distinct pitch classes; 52.8% of segments "
    "contain 3 or 4 pitch classes and the full range is 3 to 11. A reader reproducing the pipeline "
    "should expect these descriptives at the segmentation stage before any metric is computed."
)

add_body(doc,
    "Two consequences of this choice should be stated plainly. First, segment length varies with the "
    "form rather than being held constant, so a segment is a harmonic unit and not a fixed window "
    "of time. Second, because pitch classes are aggregated over the whole chord span, a segment "
    "records which pitch classes Parker visited during that harmony, not the order in which he "
    "visited them; ordering information is carried by the sequence of segments rather than within "
    "one."
)
add_empty_line(doc)

add_body(doc,
    "For each chord change in the corpus, we extract all pitch classes sounding over that harmonic "
    "moment and compute the interval vector. The interval vector is a six-dimensional vector "
    "(ic\u2081, ic\u2082, ic\u2083, ic\u2084, ic\u2085, ic\u2086) where each component counts occurrences of each interval class. This "
    "abstracts away from register and specific voicing while preserving harmonic content. Successive "
    "interval vectors, aligned with their MIDI timestamps, create a time series representation of "
    "harmonic evolution. This enables standard time series analysis techniques while maintaining "
    "musical relevance: interval vectors capture harmonic information essential to jazz theory. "
    "Figure 2 shows the three resulting series for a single performance, \"Confirmation\", with all "
    "three metrics normalized to a common scale so that their joint behavior is visible."
)

# Figure 2
add_empty_line(doc)
if 2 in img_paths:
    add_figure_image(doc, img_paths[2])
else:
    add_body(doc, "[Insert Figure 2: Temporal evolution of harmonic metrics for \"Confirmation\"]", first_line_indent=False)
add_figure_caption(doc, 2,
    "Temporal evolution of harmonic metrics for \"Confirmation.\" IV sum (complexity), "
    "dissonance, and IV distance (rate of change) are normalized to [0,1] scale. Position normalized "
    "to percentage enables comparison across performances of different lengths. Green spikes indicate "
    "rapid harmonic shifts; blue and orange show concurrent changes in complexity and dissonance. "
    "Each metric is plotted alongside its corpus-wide mean for comparison.")
add_empty_line(doc)

add_body(doc,
    "We computed three metrics for each segment. A worked example runs through all three. Suppose "
    "that over one C7 chord Parker plays the notes C, E, G and B\u266d. Reduced to pitch classes these "
    "are {C, E, G, B\u266d}; the six pairs among them are C\u2013E (4 semitones, ic4), C\u2013G (5, ic5), "
    "C\u2013B\u266d (2 by the shorter path, ic2), E\u2013G (3, ic3), E\u2013B\u266d (6, ic6) and G\u2013B\u266d (3, ic3). "
    "Counting each interval class gives the interval vector (0, 1, 2, 1, 1, 1)."
)
add_empty_line(doc)

# Complexity metric
add_body_with_italic(doc, [
    ("Complexity (iv_sum)", "bold"),
], first_line_indent=True)
add_equation(doc,
    _m_run("complexity = ")
    + _m_nary(_m_run("i", False) + _m_run("=") + _m_run("1"), _m_run("6"), _m_sub("ic", "i"))
)
add_body(doc,
    "The sum of the six entries. For the example above it is 0 + 1 + 2 + 1 + 1 + 1 = 6. Complexity "
    "rises with the number of distinct notes played over a chord, since more notes generate more "
    "pairs: three notes always give 3, four notes 6, five notes 10. It is therefore a measure of how "
    "much distinct pitch material the line uses over one chord, and not a measure of how unusual "
    "that material is. A chromatic run would score highly on this measure while being, by other "
    "measures such as interval entropy, extremely predictable. We return to this point in the "
    "Limitations."
)

# Dissonance metric
add_body_with_italic(doc, [
    ("Dissonance", "bold"),
], first_line_indent=True)
add_equation(doc,
    _m_run("dissonance = ")
    + _m_sub("ic", "1") + _m_run(" + 0.5 \u2219 ") + _m_sub("ic", "2")
    + _m_run(" + 0.8 \u2219 ") + _m_sub("ic", "6")
)
add_body(doc,
    "For the example above, dissonance is 0 + 0.5 \u00d7 1 + 0.8 \u00d7 1 = 1.3. The weights emphasize the "
    "interval classes that produce the most acoustical roughness: minor seconds (\u00d71.0), tritones "
    "(\u00d70.8), and major seconds (\u00d70.5). Thirds, fourths and fifths are excluded."
)
add_body(doc,
    "Two senses of \"dissonance\" need separating here. Sensory dissonance, also called roughness, is "
    "the harsh beating produced when two tones are close enough in frequency that they fall within "
    "the same critical band of the inner ear; it is a property of the sound and does not depend on "
    "musical training or key. Tonal dissonance is the sense that a note is unstable within a key and "
    "wants to resolve, which depends on harmonic context. Our weighting captures the first and not "
    "the second, which is the appropriate choice here because Parker plays one note at a time and no "
    "vertical sonority is actually sounded."
)
add_body(doc,
    "These weights reflect psychoacoustic principles of sensory dissonance as measured by "
    "critical band interference (Plomp & Levelt, 1965; Sethares, 1993). Minor seconds (ic1) "
    "receive maximum weight (1.0) due to maximal critical band overlap. Tritones (ic6) receive "
    "0.8 weight reflecting their tonal instability and historical treatment as requiring resolution, "
    "though with less perceptual roughness than minor seconds. Major seconds (ic2) receive 0.5 "
    "weight as they produce moderate critical band interference. Perfect fourths and fifths (ic5) "
    "and major and minor thirds (ic3, ic4) receive zero weight as these intervals fall outside critical "
    "band overlap and function as consonances in tonal and post-tonal contexts. This weighting "
    "scheme prioritizes sensory dissonance (roughness) over tonal dissonance (functional tension), "
    "appropriate for analyzing melodic improvisation where vertical harmonic function is implied "
    "rather than explicit."
)

# IV distance metric
add_body_with_italic(doc, [
    ("Rate of change (iv_distance)", "bold"),
], first_line_indent=True)
_roc_inner = (
    '<m:sSup><m:e><m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/><m:ctrlPr/></m:dPr>'
    '<m:e>' + _m_subsup("ic", "i", "t+1") + _m_run(" \u2212 ") + _m_subsup("ic", "i", "t") + '</m:e>'
    '</m:d></m:e><m:sup>' + _m_run("2") + '</m:sup></m:sSup>'
)
add_equation(doc,
    _m_run("rate of change = ")
    + '<m:rad><m:radPr><m:degHide m:val="1"/><m:ctrlPr/></m:radPr><m:deg/><m:e>'
    + _m_nary(_m_run("i", False) + _m_run("=") + _m_run("1"), _m_run("6"), _roc_inner)
    + '</m:e></m:rad>'
)
add_body(doc,
    "The straight-line distance between the interval vector of one segment and that of the next. If "
    "the following segment had the vector (1, 1, 1, 0, 0, 0), the differences entry by entry would be "
    "(1, 0, \u22121, \u22121, \u22121, \u22121) and the distance \u221a5 \u2248 2.24. The measure answers one question: how "
    "much did the intervallic content change from this chord to the next? A value near zero means "
    "Parker carried essentially the same set of relationships across the chord change; a large value "
    "means he replaced it."
)
add_body(doc,
    "This treats every unit of change in every interval class as equivalent, which is a simplification. "
    "Replacing a tritone with a perfect fifth and replacing a major second with a minor third both "
    "register as the same distance, although a listener would not hear them as equally large moves. "
    "We use the measure because it is symmetric, requires no further weighting decisions, and is "
    "interpretable as motion in the same six-dimensional space the vectors already occupy; a "
    "perceptually weighted distance would be a worthwhile refinement."
)
add_body(doc,
    "These metrics reduce six-dimensional interval vectors to interpretable scalar values while "
    "preserving essential harmonic information. They also enable standard statistical analysis (mean, "
    "standard deviation, correlation) while remaining musically meaningful."
)

# ── Multi-scale pattern analysis ─────────────────────────────────────────
add_heading2(doc, "Multi-Scale Pattern Analysis")
add_empty_line(doc)

add_heading3(doc, "Phrase Detection")
add_empty_line(doc)

add_body(doc,
    "Having established segment-level time series, we next identified phrases using actual rests from "
    "musical scores rather than inferring pauses from timestamp gaps. We parsed MusicXML <rest> "
    "elements with their precise durations and positions, matching them to temporal segments.",
    first_line_indent=False
)
add_body(doc,
    "This approach respects Parker's actual articulation as notated by expert transcribers. Bebop "
    "phrasing is highly articulated with frequent short rests; inferring phrases from timestamp gaps "
    "would miss most phrase boundaries."
)

add_body(doc,
    "Rests meeting a minimum threshold of 0.5 quarter notes (eighth note or longer) were designated "
    "as phrase boundaries. This threshold was selected based on Parker's articulation style: bebop "
    "phrasing employs frequent short rests as phrase punctuation rather than breath necessity. Pilot "
    "testing with alternative thresholds (0.25, 0.5, and 1.0 quarter notes) revealed that 0.25 captured "
    "excessive micro-articulations within continuous melodic lines, while 1.0 missed legitimate phrase "
    "boundaries in faster tempos. The 0.5 quarter note threshold balanced sensitivity (capturing "
    "meaningful phrase articulation) with specificity (avoiding within-phrase micro-pauses). This "
    "threshold yielded 1,507 phrases across 46 tunes (mean = 32.8 phrases per tune), consistent with "
    "typical bebop phrase density where solo choruses contain 8-12 phrases per 32-bar form."
)

add_body(doc,
    "Two kinds of failure are possible, and both occur. A phrase can run on: the longest in the "
    "corpus spans twelve segments across measures 42\u201348 of \"Kim (No. 1)\", some seven bars with no "
    "notated rest of an eighth note or longer, which on any reading contains more than one gesture. "
    "Four further phrases span ten segments (\"Celebrity\" twice, \"Kim (No. 2)\", and \"Thriving on a "
    "Riff\"). Conversely a boundary can be spurious, because the threshold sits at the shortest rest "
    "we accept: 36.4% of all 1,507 boundaries are generated by a rest of exactly 0.5 quarter notes, "
    "so raising the threshold to a single quarter note would dissolve more than a third of the "
    "phrases in the corpus. Detection is therefore most reliable in the middle of its range and "
    "least reliable at the extremes, and the rolling-window analyses, which average over five "
    "consecutive phrases, are correspondingly less exposed to this than the phrase-level tests."
)

add_body_with_italic(doc, [
    ("For each phrase, we calculated ", "normal"),
    ("mean complexity", "italic"),
    (" (mean_iv_sum), mean dissonance, ", "normal"),
    ("phrase length", "italic"),
    (" in segments (segment_count), and "
     "standard deviations. Phrases serve as the primary analytical unit for the multi-scale analyses "
     "that follow, sitting between the segment and the chorus.", "normal")
])

add_body(doc,
    "The resulting phrases are short. A phrase spans a median of 1 segment "
    "(M = 2.01, range 1–12), and 54.3% of phrases consist of a single segment while 74.6% consist "
    "of two or fewer. This follows from the interaction of two facts already stated: bebop phrasing "
    "is densely articulated with short rests, while segments are as long as the harmonic rhythm. A "
    "phrase that falls within one chord symbol therefore contributes a single observation, and for "
    "just over half the corpus the phrase-level series is effectively a subsampled segment-level "
    "series. Phrase-level results below should be read with this in mind: they describe organization "
    "at the scale of rest-delimited gestures, which in this repertoire is often the scale of one "
    "chord, and the phrase-level analyses are for that reason reported alongside rolling-window "
    "and chorus-level analyses rather than on their own. Figure 10 sets out the five analyses that "
    "proceed from the detected phrases and the scale each addresses."
)


add_heading3(doc, "Rolling Window Analysis")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("To capture local temporal dynamics, we computed ", "normal"),
    ("rolling window statistics", "italic"),
    (" over phrase "
     "sequences using window sizes of 3, 5, and 10 phrases. For each window, we calculated mean, "
     "standard deviation, and coefficient of variation (CV = standard deviation divided by mean). "
     "The CV measures volatility, by which we mean how much a quantity varies relative to its own "
     "average: a high CV indicates that complexity or dissonance swings widely from phrase to "
     "phrase, a low CV that it stays near a steady level. Expressing variation relative to the mean "
     "makes volatility comparable between a dense tune and a sparse one.", "normal")
], first_line_indent=False)

add_body(doc, "Window size selection reflects different temporal scales:")
add_bullet(doc, "3-phrase windows capture immediate phrase-to-phrase volatility")
add_bullet(doc, "5-phrase windows average over enough phrases to suppress single-phrase noise while remaining short enough to track change within a chorus; this is the window used for most analyses below")
add_bullet(doc, "10-phrase windows reveal broader trends, approaching the scale of a full chorus")

add_body(doc,
    "Each window was centered on the phrase it describes, taking an equal number of phrases before "
    "and after it, rather than looking only backwards. A backward-looking window would report "
    "change only after it had happened, displacing every feature later in the series than it occurs."
)

add_heading3(doc, "Autocorrelation and Predictability")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("We also computed ", "normal"),
    ("autocorrelation", "italic"),
    (" to quantify phrase-to-phrase predictability. For each tune, ", "normal"),
    ("complexity", "italic"),
    (" and ", "normal"),
    ("dissonance", "italic"),
    (" time series were analyzed using Pearson correlation between the series "
     "and lagged versions of itself (lags 1 through 5). Positive autocorrelation indicates continuous "
     "development (high phrase predicts high next phrase), negative autocorrelation indicates contrasting "
     "structure (high phrase followed by low phrase), and near-zero autocorrelation suggests "
     "random walk or episodic organization.", "normal")
], first_line_indent=False)

add_body_with_italic(doc, [
    ("For a time series {", "normal"),
    ("x", "italic"),
    ("(t), t = 1..n} and lag ", "normal"),
    ("k", "italic"),
    (": ", "normal"),
    ("r", "italic"),
    ("(k) = cor(", "normal"),
    ("x", "italic"),
    ("(t), ", "normal"),
    ("x", "italic"),
    ("(t+k)) for ", "normal"),
    ("t", "italic"),
    (" = 1, ..., ", "normal"),
    ("n \u2013 k", "italic"),
])

add_body(doc,
    "Tunes with fewer than 6 phrases were excluded, since a lag-5 autocorrelation cannot be computed "
    "on a shorter series and estimates from very short series are dominated by noise. Six is a floor "
    "rather than an adequacy threshold: autocorrelations estimated on six observations are themselves "
    "imprecise, and the figure is low only because raising it would have discarded tunes. In practice "
    "the constraint binds rarely, as the median tune contributes 32.8 phrases. The Granger tests use "
    "a stricter minimum of 10 phrases for the same reason."
)

add_heading3(doc, "Improvisational Strategy Clustering")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("To identify distinct improvisational strategies, we performed ", "normal"),
    ("K-means clustering", "italic"),
    (" using four features per tune:", "normal")
], first_line_indent=False)

add_bullet(doc, "complexity: the mean of complexity across the tune's phrases")
add_bullet(doc, "complexity volatility: the coefficient of variation of complexity across those phrases")
add_bullet(doc, "predictability: the lag-1 autocorrelation of complexity, that is, how well each phrase's complexity predicts the next one's")
add_bullet(doc, "dissonance volatility: the coefficient of variation of dissonance across phrases")

add_body_with_italic(doc, [
    ("Features were standardized (", "normal"),
    ("z", "italic"),
    ("-scored) before clustering so that each contributes equally regardless of its units. We selected "
     "k=4 clusters based on interpretability and on how clearly the groups separated when the four "
     "features were projected onto their first two principal components, a two-dimensional summary "
     "that captures as much of the variation among tunes as two dimensions can and so allows the "
     "grouping to be inspected visually. Principal component analysis was used only for this visual "
     "check, not as an analysis step. The choice of k=4 clusters "
     "balances statistical separation with interpretability. Silhouette analysis suggested k=3\u20135 as "
     "plausible values (silhouette scores: k=3: 0.42, k=4: 0.38, k=5: 0.35), but k=4 provided the most "
     "musically interpretable clusters with distinct temporal profiles. We prioritize interpretability "
     "over optimal separation, as our goal is identifying meaningful improvisational strategies rather "
     "than maximizing classification accuracy. K-means was initialized with 20 random starts to avoid "
     "local optima.", "normal")
])

add_body(doc,
    "The silhouette scores are not high, and a reader is entitled to ask whether the grouping "
    "describes anything at all. Three considerations bear on this. First, silhouette values in this "
    "range are expected when the underlying structure is a continuum rather than well-separated "
    "clusters, which is what we take to be the case: tunes differ in degree along the four features "
    "rather than falling into natural kinds, and the strategies are a partition imposed on that "
    "continuum for descriptive purposes. Second, the partition is stable under perturbation of the "
    "inputs, reproducing exactly under three of five alternative dissonance weightings and agreeing "
    "on 83% to 85% of tunes under the other two (Table 3), which is not what an arbitrary partition "
    "of noise would do. Third, and most importantly, the groups predict something they were not "
    "fitted on: the Granger results reported below differ sharply between them, and no measure of "
    "Granger causation entered the clustering. We therefore treat the strategies as a useful "
    "description rather than as evidence that Parker's solos fall into discrete types."
)

add_body(doc,
    "The resulting clusters represent distinct approaches to temporal organization, and we describe "
    "each here rather than leaving it to the figures below. Strategy 1, \"Balanced\" (25 tunes): "
    "moderate complexity, moderate volatility, and positive lag-1 autocorrelation, so that each "
    "phrase tends to resemble the one before it. Strategy 2, \"Contrasting\" (13 tunes): moderate "
    "complexity with negative lag-1 autocorrelation, so that a dense phrase tends to be followed by "
    "a sparse one. Strategy 3, \"Exploratory\" (7 tunes): the highest complexity and the highest "
    "volatility, with autocorrelation near zero. A fourth group contains a single tune, \"My Little "
    "Suede Shoes\", which combines the lowest complexity in the corpus with extreme volatility and "
    "strong positive autocorrelation. K-means labels clusters arbitrarily from 0; we renumber "
    "them here as Strategies 1\u20133 in order of corpus prevalence, reserving no number for the "
    "one-tune cluster, which is referred to throughout as the outlier tune. Strategy numbers and "
    "cluster identities correspond one to one, and no cluster index appears anywhere else in this "
    "article."
)

add_heading3(doc, "Granger Causality Analysis")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("We tested directional prediction between these quantities using Granger causality. "
     "The test asks a deliberately modest question: does the past of one series improve "
     "prediction of another beyond what that second series' own past already predicts? It licenses "
     "no claim about intention or mechanism. Following standard usage we say that one series ", "normal"),
    ("Granger-causes", "italic"),
    (" another when it does, and we avoid the bare words \"cause\" and \"causality\" for this relation "
     "throughout, since nothing here establishes causation in the ordinary sense. The method has been applied to music "
     "primarily to establish directionality of influence between performers, for instance in "
     "recovering leader-follower relations from body-sway time series in ensemble performance "
     "(Chang et al., 2017). Our application turns the same logic inward, asking whether one "
     "dimension of a single improviser's output predicts another across phrase boundaries.", "normal")
], first_line_indent=False)

add_body(doc,
    "The motivation for testing directional effects at all comes from a tension between two accounts "
    "of improvisational control. On the pattern-retrieval account that dominates both the analytical "
    "and the cognitive literature (Owens, 1974; Pressing, 1988; Norgaard, 2014), material is selected "
    "from a pre-learned store under real-time constraint, which implies that what the performer has "
    "just played should condition what comes next: local, reactive dependency. On the account "
    "suggested by thematic and schema-based analyses (Martin, 1996; Love, 2012), a performance is "
    "shaped by larger units planned or habituated above the phrase, which implies that phrase-to-"
    "phrase dependencies should be weak, because each phrase answers to a chorus-level design "
    "rather than to its immediate predecessor. These accounts make opposite predictions about "
    "phrase-level Granger causality, and the corpus can adjudicate between them. To our knowledge "
    "no prior study has tested directional dependency between harmonic dimensions within "
    "improvised solos, though Broze and Shanahan (2013) established the related point that "
    "transition-level and frequency-level structure in jazz harmony can behave independently."
)

add_body(doc, "Four directional hypotheses follow, two for each pairing:")

add_bullet(doc,
    "Complexity \u2192 Dissonance. A dense pitch-class aggregate leaves fewer consonant continuations "
    "available, so accumulating density should force dissonant intervals in subsequent phrases. "
    "Support would indicate that Parker's tension is a by-product of density rather than an "
    "independently controlled parameter.")
add_bullet(doc,
    "Dissonance \u2192 Complexity. Under a tension-and-resolution logic, a dissonant phrase creates a "
    "condition requiring response, and the response available to a monophonic improviser is "
    "elaboration: more material deployed to work out of the position. Support would indicate "
    "reactive navigation, with harmonic tension driving subsequent activity.")
add_bullet(doc,
    "Phrase Length \u2192 Complexity. Longer phrases span more chord changes and afford more room to "
    "develop an idea, so duration may enable density rather than the reverse. Support would locate "
    "organization in the rhythmic-formal domain, implying that Parker modulates phrase duration "
    "and lets harmonic density follow.")
add_bullet(doc,
    "Phrase Length \u2192 Dissonance. The same argument applied to tension: extended phrases have "
    "more scope to move away from the underlying harmony before resolving. Support would again "
    "point to duration as the controlling parameter.")

add_body(doc,
    "The two accounts are distinguished by the overall rate of significant effects rather than by any "
    "single test: widespread phrase-level Granger causation would favor reactive navigation, by which we mean a performer responding to the conditions created by the phrase just played, while its "
    "general absence would favor organization above the phrase. The phrase-length hypotheses "
    "additionally allow a third possibility, that temporal organization operates through duration "
    "instead of through harmony, which neither literature predicts directly."
)

add_body(doc,
    "For each tune with \u226510 phrases, we performed Granger causality tests using the statsmodels "
    "implementation of the F-test for model comparison. The null hypothesis states that past "
    "values of the cause variable do not improve prediction of the effect variable beyond its own "
    "autoregressive history."
)
add_body(doc,
    "Tests were conducted at lags 1, 2, and 3. Lag-1 captures immediate causal effects "
    "(phrase t predicts phrase t + 1), while lags 2\u20133 capture delayed effects. F-statistics quantify "
    "causal strength: higher values indicate stronger predictive relationships."
)
add_body(doc,
    "Results are reported as: (1) percentage of tunes showing significant Granger causation per test, (2) "
    "mean F-statistic across corpus, and (3) strategy-specific patterns revealing strategy-dependent "
    "causal structures."
)

add_heading3(doc, "Robustness Checks on the Time Series Analyses")
add_empty_line(doc)

add_body(doc,
    "Three features of the design invite scrutiny, and we tested each directly rather than assuming "
    "it away.",
    first_line_indent=False
)
add_body_with_italic(doc, [
    ("Dependence between complexity and dissonance. ", "bolditalic"),
    ("Dissonance is a weighted sum of three of the six entries that complexity sums in full, so the "
     "two are not independent measurements, and in this corpus they correlate at ", "normal"),
    ("r", "italic"),
    (" = .94 at both segment and phrase level (within-tune mean ", "normal"),
    ("r", "italic"),
    (" = .93, range .81 to .99; all 46 tunes above .81). Testing whether one Granger-causes the other "
     "is therefore testing two heavily overlapping quantities against each other, and an effect could "
     "reflect that overlap rather than any relation between tension and density. To separate them we "
     "defined a density-independent dissonance, dividing each segment's dissonance by its complexity, "
     "which expresses the proportion of a segment's interval content that is rough rather than the "
     "amount of it. This measure is essentially uncorrelated with complexity (", "normal"),
    ("r", "italic"),
    (" = .03), and we re-ran every Granger test with it. Results are reported alongside the originals "
     "below.", "normal")
])
add_body_with_italic(doc, [
    ("Sensitivity to the dissonance weights. ", "bolditalic"),
    ("The weights (1.0, 0.5, 0.8) are defensible but not forced. We recomputed dissonance under four "
     "alternatives \u2014 ic\u2086 at 0.6, ic\u2086 at 1.0, ic\u2082 at 0.25, and all three weights equal \u2014 and under a "
     "fifth scheme adding a small penalty on ic\u2084, then repeated the clustering from scratch in each "
     "case and compared the resulting strategy assignments to the published one.", "normal")
])
add_body_with_italic(doc, [
    ("Harmonic rhythm as a confound. ", "bolditalic"),
    ("Because segments follow chord symbols, some of the variation we attribute to Parker necessarily "
     "belongs to the tunes: an applied diminished seventh affords a more dissonant segment than a "
     "tonic triad, independently of any choice he makes. We discuss the scope of this problem, and a "
     "design that would settle it, in the Limitations.", "normal")
])

add_heading3(doc, "Robustness")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("We also explored ", "normal"),
    ("robustness", "italic"),
    (" as a metric that quantifies triadic content: the number of complete major, minor, diminished, "
     "and augmented triads that can be found among the notes of a segment, counted regardless of "
     "which quality they are. A segment containing {C, E, G, B\u266d} contains one complete triad "
     "(C major); a segment containing {C, E\u266d, G\u266d, A} contains four diminished triads. We call the "
     "first ", "normal"),
    ("triadically sparse", "italic"),
    (" and the second ", "normal"),
    ("triadically dense", "italic"),
    (". The distinction matters because a triadically dense structure already commits the ear to "
     "particular chords, while a sparse one stays available to be heard against many: triadic content "
     "is thus an index of how constrained a structure is, and low triadic content is what we take to "
     "leave continuations open.", "normal")
], first_line_indent=False)

add_body(doc,
    "For each unique interval vector in the corpus, we performed exact enumeration of all pitch-class "
    "sets generating that interval vector at the estimated cardinality (derived from IV sum via "
    "n(n\u20131)/2 = \u03A3IC). For each candidate PC set, we enumerated all 3-note subsets and identified "
    "those matching standard triad patterns: major [0,4,7], minor [0,3,7], diminished [0,3,6], and "
    "augmented [0,4,8]. Mean triadic content per IV was computed by averaging triad counts across "
    "all generating PC sets. This approach provides exact counts for all cardinalities (n = 165 unique "
    "IVs), with results cached for computational efficiency."
)
add_body(doc,
    "We then analyzed the relationship between triadic content and usage frequency across "
    "the corpus. For each IV, we recorded its total frequency of occurrence across all performances and "
    "computed both unweighted (mean across all IVs) and frequency-weighted (mean weighted by "
    "actual usage) triadic content. This reveals whether Parker systematically favors triadically dense "
    "or sparse structures in his vocabulary selection."
)

# ══════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════
add_heading1(doc, "Results")
add_empty_line(doc)

add_heading2(doc, "Vocabulary")
add_empty_line(doc)

add_body(doc,
    "Parker's improvisational vocabulary centers on a relatively compact set of interval vectors with "
    "distinctive functional distributions. A note on the function labels used throughout this "
    "section: they are scale-degree positions of the chord within the prevailing key, taken from the "
    "corpus annotations, not the three-way functional taxonomy of tonic, predominant and dominant. "
    "\"II\" therefore means a chord built on the second degree, typically the supertonic seventh of a "
    "II\u2013V\u2013I, which in that taxonomy would count as predominant. We use scale-degree labels because "
    "they are what the corpus encodes and because the three-way grouping would merge distinctions "
    "visible in the data. Each interval vector represents the intervallic content of a single segment, one per chord change. The "
    "interval vector (111000), containing one instance each of interval classes 1, 2, and 3 (minor "
    "second, major second, minor third), appears 226 times across the corpus, making it the single "
    "most frequent harmonic structure (Table 1). This three-note chromatic cluster (Forte class 3-2) "
    "can manifest as tightly packed chromatic voicings like {C, C\u266f, E\u266d} or {C, D, E\u266d}, or as wider-"
    "spaced inversions like {C, A, B\u266d}. It appears predominantly in II contexts (51 occurrences), "
    "though it distributes across multiple functions including tonic (I: 48) and dominant (V: 44), "
    "revealing its functional versatility as a pivot structure rather than a function-specific sonority. "
    "Over a Dm7 chord, these voicings can function as altered upper extensions (b7, M7, b9), "
    "chromatic voice leading (b7, root, b9), or diatonic extensions (b7, 5, 6), explaining the IV's "
    "adaptability across harmonic contexts.",
    first_line_indent=False
)
add_body(doc,
    "The top ten interval vectors account for 1,155 occurrences, 34.3% of the corpus, indicating "
    "concentrated reliance on a core harmonic vocabulary (Table 1). Nine of these ten have tonic "
    "(I) as their most common function, but that fact carries less weight than it appears to. Tonic "
    "is also the most common function in the corpus at large, and the top ten vectors fall on tonic "
    "chords in 29.3% of their occurrences against a corpus-wide base rate of 30.6%. Relative to how "
    "often tonic chords occur, Parker's frequent vocabulary is if anything marginally under-"
    "represented there, so the function distributions in Table 1 reflect the prevalence of tonic "
    "harmony rather than any function-specific preference in vocabulary selection."
)
add_body_with_italic(doc, [
    ("A direct test of the same idea gives a weaker but genuine result. Complexity is higher over "
     "tonic chords (", "normal"),
    ("M", "italic"),
    (" = 10.85) than over all other functions pooled (", "normal"),
    ("M", "italic"),
    (" = 9.66), and differs across the four commonest functions (I: 10.85, IV: 10.55, II: 9.65, "
     "V: 9.39). Both differences are statistically reliable at this corpus size (Kruskal\u2013Wallis "
     "", "normal"),
    ("H", "italic"),
    (" = 38.76, ", "normal"),
    ("df", "italic"),
    (" = 3, ", "normal"),
    ("p", "italic"),
    (" < .001; tonic vs. other, Mann\u2013Whitney ", "normal"),
    ("U", "italic"),
    (" = 1,340,256, ", "normal"),
    ("p", "italic"),
    (" < .001), but the effect is small (Cohen's ", "normal"),
    ("d", "italic"),
    (" = 0.17). Parker's complexity is therefore slightly concentrated at moments of harmonic "
     "arrival, a modest shift in a broad distribution rather than a categorical distinction between "
     "arrival and transition.", "normal")
])
add_body(doc,
    "The second most frequent IV, (122010), appears 163 times, most often over tonic and dominant "
    "harmony (I: 45, V: 37). It is a four-note set of Forte class 4-10, prime form [0,2,3,5]. Its three "
    "commonest realizations, expressed as intervals above the sounding chord root, are "
    "{root, 5, 13, \u266d7} (58 occurrences, for instance {C, G, A, B\u266d} over a C chord), {9, 3, 11, 5} (33), "
    "and {root, 9, \u266d3, 11} (28). The first of these omits the third, fixing root, fifth and seventh "
    "while committing to neither major nor minor quality, and 46.0% of all occurrences of (122010) "
    "contain no third of any kind above the chord root. The vector is thus frequently, though not "
    "invariably, quality-neutral. In this respect it complements (111000): where (111000) is a "
    "chromatic cluster that resolves outward to many destinations, (122010) is a stable frame that "
    "declines to specify quality."
)
add_body(doc,
    "Transitional patterns reinforce this vocabulary structure (Table 2). The most common "
    "transition, (111000) \u2192 (122010) (II \u2192 I, 19 occurrences), represents Parker navigating from "
    "chromatic cluster to shell voicing, paralleling the archetypal II-V-I resolution by moving from "
    "chromatic tension to ambiguous stability. However, the corpus also shows substantial same-IV "
    "persistence: (111000) \u2192 (111000) appears 18 times. Because segments are defined by chord "
    "symbols, a repeated interval vector could in principle record a repeated chord rather than a "
    "harmonic move, and we checked this directly: 17 of those 18 transitions cross a change of "
    "chord symbol, and only one stays on the same chord. The pattern holds corpus-wide, where 83 "
    "of 112 same-IV transitions (74.1%) span an actual chord change. Parker is therefore sustaining "
    "one pitch-class structure across changing harmony rather than sitting on a static chord, which "
    "is what makes the persistence analytically interesting. Reverse motion also appears: "
    "(122010) \u2192 (111000) (I \u2192 II, 17 occurrences) shows "
    "Parker generating harmonic tension by moving from stable shell voicings to altered chromatic "
    "clusters, contradicting traditional voice-leading pedagogy that emphasizes tension\u2192resolution "
    "directionality."
)
add_body_with_italic(doc, [
    ("The bidirectional nature of these transitions, both II \u2192 I (19) and I \u2192 II (17) ranking in the "
     "top three, reveals a fundamental finding: Parker conceives these structures not as functional "
     "progressions but as ", "normal"),
    ("navigational options", "bold"),
    (" within a network space. The interval vector (111000) is best described as a hub in the network of transitions: more distinct interval vectors follow it than follow any other, so it offers the widest range of continuations. What makes it useful is therefore its ", "normal"),
    ("positional centrality", "bold"),
    (", offering maximum continuation options to diverse harmonic destinations. This observation "
     "motivates our subsequent time series analysis, which examines how Parker deploys this core "
     "vocabulary across temporal scales from phrase-level articulation to full-chorus development arcs.", "normal")
])

# Table 1
add_empty_line(doc)
add_table_heading(doc, "Table 1. Most frequent interval vectors in Parker corpus with harmonic function distributions.")
create_table(doc,
    ["IV", "Forte", "Freq.", "% of Corpus", "Primary Function", "Function Distribution"],
    [
        ["(111000)", "3-2", "226", "6.70%", "II", "II: 51, I: 48, V: 44, IV: 24, VI: 19, III: 19"],
        ["(122010)", "4-10", "163", "4.84%", "I", "I: 45, V: 37, II: 24, IV: 18, III: 14"],
        ["(001110)", "3-11", "121", "3.59%", "I", "I: 48, II: 23, V: 18, III: 9, VI: 8, IV: 8"],
        ["(122230)", "5-27", "116", "3.44%", "I", "I: 38, II: 29, IV: 15, V: 13, bIII: 10"],
        ["(021120)", "4-22", "98", "2.91%", "I", "I: 24, IV: 22, V: 19, II: 17, bVII: 6"],
        ["(011010)", "3-7", "94", "2.79%", "I", "I: 39, II: 19, IV: 11, V: 11, bVII: 6"],
        ["(121110)", "4-11", "92", "2.73%", "I", "I: 24, V: 22, II: 12, IV: 11, bIII: 8"],
        ["(111120)", "4-14", "90", "2.67%", "I", "I: 30, II: 18, VI: 13, IV: 9, V: 9"],
        ["(012120)", "4-26", "81", "2.40%", "I", "I: 21, II: 18, IV: 13, V: 8, III: 5, bIII: 5"],
        ["(132130)", "5-23", "74", "2.20%", "I", "I: 21, IV: 17, II: 14, bIII: 7, V: 5"],
    ],
    col_widths=[Inches(0.85), Inches(0.55), Inches(0.5), Inches(0.75), Inches(0.8), Inches(2.55)]
)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Note. Forte classes are given without inversional suffix (A/B). "
                "Percentages are of all 3,371 segments. N = 165 unique interval vectors.")
run.font.size = Pt(9)
run.font.italic = True
run.font.name = "Times New Roman"
add_empty_line(doc)

# Table 2
add_heading2(doc, "Top 10 Most Frequent Transitions")
add_empty_line(doc)
add_table_heading(doc, "Table 2. Most frequent interval vector transitions showing predominant harmonic progressions.")
create_table(doc,
    ["Source IV", "Function", "\u2192", "Target IV", "Function", "Count"],
    [
        ["(111000)", "II", "\u2192", "(122010)", "I", "19"],
        ["(111000)", "II", "\u2192", "(111000)", "II", "18"],
        ["(122010)", "I", "\u2192", "(111000)", "II", "17"],
        ["(001110)", "I", "\u2192", "(111111)", "V", "17"],
        ["(122010)", "I", "\u2192", "(122010)", "I", "13"],
        ["(111000)", "II", "\u2192", "(122230)", "I", "11"],
        ["(111120)", "I", "\u2192", "(111000)", "II", "9"],
        ["(121110)", "I", "\u2192", "(111000)", "II", "9"],
        ["(122230)", "I", "\u2192", "(111000)", "II", "9"],
        ["(112101)", "VI", "\u2192", "(101220)", "II", "8"],
    ]
)
add_empty_line(doc)

# ── Complexity distribution between segments ─────────────────────────────
add_heading2(doc, "Complexity Distribution between Segments")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("Analysis of 3,371 segments across 50 tunes reveals wide variation in harmonic complexity "
     "(Figure 3). Mean ", "normal"),
    ("complexity", "italic"),
    (" (iv_sum) is 10.01 (", "normal"),
    ("SD", "italic"),
    (" = 7.18), but the distribution is strongly right-skewed and the median of 6.0 (IQR [6, 15]) "
     "is the more representative summary. We report medians alongside means throughout this "
     "section for that reason, and the mean is retained only where it is required for comparison "
     "with the variance-based statistics used later.", "normal"),
], first_line_indent=False)

add_bullet(doc, "Tunes with most complexity:")
add_sub_bullet(doc, "\"Cosmic Rays\": 16.28")
add_sub_bullet(doc, "\"Bluebird\": 15.85")
add_sub_bullet(doc, "\"Laird Baird\": 13.86")
add_bullet(doc, "Tunes with least complexity:")
add_sub_bullet(doc, "\"Si Si\": 7.09")
add_sub_bullet(doc, "\"Moose the Mooche\": 7.21")
add_sub_bullet(doc, "\"Yardbird Suite\": 7.57")

add_body_with_italic(doc, [
    ("Importantly, complexity and variability correlate strongly (", "normal"),
    ("r", "italic"),
    (" = 0.68): complex tunes tend to "
     "show more variation in complexity across their temporal evolution. However, this relationship "
     "is not deterministic: some tunes break this pattern, as discussed below.", "normal"),
])

add_body_with_italic(doc, [
    ("We also explored other metrics such as ", "normal"),
    ("dissonance", "italic"),
    (" (mean = 3.16, median = 2.30) and ", "normal"),
    ("rate of change", "italic"),
    (" (mean = 3.81, median = 3.32, first segment of each tune excluded). The first shows a heavily right-skewed distribution: most segments are relatively "
     "consonant (modal dissonance around 1\u20132), with a long tail extending to highly dissonant "
     "passages (maximum 19.0). This suggests Parker's harmonic language centers on moderate dissonance "
     "levels, deploying extreme dissonance strategically rather than consistently. ", "normal"),
    ("Rate of change", "italic"),
    (" (iv_distance) shows moderate harmonic change is most common, with occasional shifts. The "
     "mean of 4 indicates that typical chord-to-chord motion involves changing approximately 4 "
     "units across the six-dimensional interval vector space, neither static repetition nor extreme "
     "transformation.", "normal"),
])

# Figure 3
add_empty_line(doc)
if 5 in img_paths:
    add_figure_image(doc, img_paths[5])
else:
    add_body(doc, "[Insert Figure 3: Corpus-wide complexity distribution]", first_line_indent=False)
add_figure_caption(doc, 3,
    "Corpus-wide complexity distribution; please note that the first segment of each tune "
    "is excluded from rate-of-change analyses as it has no prior segment for comparison.")
add_empty_line(doc)

# ── Complexity distribution between choruses ─────────────────────────────
add_heading2(doc, "Complexity Distribution between Choruses")
add_empty_line(doc)

add_body(doc, "Cross-chorus analysis revealed the following patterns:", first_line_indent=False)
add_bullet(doc, "Chorus 1 (head) mean complexity: 8.32")
add_bullet(doc, "Chorus 2 mean complexity: 11.31")
add_bullet(doc, "Subsequent choruses: maintain 10\u201311")

add_body(doc,
    "Composed melodies (heads) are often less complex than improvisation choruses. Parker's first "
    "improvised chorus (Chorus 2) already exhibits peak complexity, showing no gradual build within "
    "improvisation. Most of the interval vectors that appear anywhere in a performance have already appeared in its head; the solo choruses add few new ones and instead recombine what is already present."
)

add_body_with_italic(doc, [
    ("This pattern requires careful interpretation: Parker's composed melodies (heads) are "
     "themselves \"composed solos\" or \"contrafacts\" over standard progressions (for example \"Anthropology\" "
     "over \"I Got Rhythm\" by G. Gershwin). The lower ", "normal"),
    ("complexity", "italic"),
    (" likely reflects "
     "melodic construction prioritizing memorable contour and singability over maximal harmonic "
     "density. Heads establish the core vocabulary while maintaining thematic clarity; improvised "
     "choruses then explore denser harmonic regions enabled by the absence of melodic memorability "
     "constraints. Figure 11 compares mean complexity across chorus positions directly.", "normal")
])

add_body(doc,
    "Two caveats qualify this. The contrafact relationship does not by itself explain the gap: "
    "borrowing a progression from a standard says nothing about how dense the melody written over "
    "it will be, and the explanation we offer is the melodic one above rather than the harmonic one. "
    "The head/solo distinction is also less clean than chorus numbering implies. Some of Parker's "
    "compositions carry improvised B-sections, so that part of what we count as a head is itself "
    "improvised; and some recordings have no pre-composed head at all, Yamaguchi (2012) arguing "
    "that pieces such as \"Bird of Paradise\" were improvised over a borrowed progression and "
    "copyrighted as compositions afterwards. Both cases import solo material into the head category, "
    "and would therefore narrow the difference we report rather than produce it."
)


add_body(doc,
    "Parker's core harmonic vocabulary is largely established in Chorus 1, the composed head. "
    "Chorus 1 already contains 81.1% of all distinct interval vectors that appear anywhere in the "
    "corpus, Chorus 2 adds a further 16.5%, and Choruses 3 and later contribute 2.4% between them "
    "(Figure 4). This is a corpus-level statistic rather than a single performance: chorus numbers "
    "are assigned per tune by dividing measure position by form length (12 bars for blues, 32 "
    "otherwise), the distinct vectors occurring in each chorus position are pooled across all 46 "
    "MIDI-aligned tunes, and coverage is then accumulated across chorus positions. Temporal "
    "evolution thus reflects primarily the exploration of new pathways connecting existing harmonic "
    "nodes rather than progressive vocabulary expansion."
)

# Figure 4
add_empty_line(doc)
if 6 in img_paths:
    add_figure_image(doc, img_paths[6])
else:
    add_body(doc, "[Insert Figure 4: Vocabulary coverage waterfall]", first_line_indent=False)
add_figure_caption(doc, 4,
    "Cumulative vocabulary coverage across chorus positions, pooled across the 46 MIDI-"
    "aligned tunes. Chorus 1 (the head) accounts for 81.1% of all distinct interval vectors in the "
    "corpus, Chorus 2 (the first improvised chorus) adds 16.5%, and Choruses 3–5 add 2.4% "
    "in total. The curves are flat over long stretches because each step adds only interval vectors "
    "not already seen: once the common vocabulary has appeared, most later segments repeat it and "
    "contribute nothing new.")
add_empty_line(doc)


# ── Complexity distribution between tunes ────────────────────────────────
add_heading2(doc, "Complexity Distribution between Tunes")
add_empty_line(doc)

add_body(doc,
    "We used Dynamic Time Warping to compare temporal evolution patterns between tunes. DTW "
    "allows comparison of sequences of different lengths by finding optimal alignment, analogous to "
    "aligning two melodies that occur at different tempos.",
    first_line_indent=False
)

add_body(doc,
    "Comparing \"Cosmic Rays\" and \"Bluebird\" (both high-complexity tunes) reveals dramatically "
    "different temporal shapes."
)

add_body_with_italic(doc, [
    ("\"Cosmic Rays\": ", "bold"),
    ("Episodic structure with multiple peaks and valleys throughout. High "
     "volatility but no single climax.", "normal")
])

add_body_with_italic(doc, [
    ("\"Bluebird\": ", "bold"),
    ("\"Slow-burn climax\" structure. Stays relatively simple for first 60%, then "
     "explodes at 70\u201390% with sustained high complexity.", "normal")
])

add_body(doc,
    "DTW distance between these tunes is large despite similar mean complexity, revealing that "
    "Parker doesn't use a fixed template. Some performances are journeys (building to climax), "
    "others are episodes (multiple peaks), others maintain consistency."
)
add_body(doc,
    "This finding suggests Parker conceives each tune's improvisational arc holistically rather than "
    "applying a single approach across all contexts. Figure 5 plots the two contours against one "
    "another, with the composed head shown alongside the improvised choruses in each case."
)

# Figure 5
add_empty_line(doc)
if 8 in img_paths:
    add_figure_image(doc, img_paths[8])
else:
    add_body(doc, "[Insert Figure 5: Comparing composed melody and solo development between \"Cosmic Rays\" and \"Bluebird\"]", first_line_indent=False)
add_figure_caption(doc, 5,
    "Comparing composed melody and solo development between \"Cosmic Rays\" and \"Bluebird.\"")
add_empty_line(doc)


# ── Complexity distribution between phrases ──────────────────────────────
add_heading2(doc, "Complexity Distribution between Phrases")
add_empty_line(doc)

add_body(doc,
    "Rolling window analysis reveals meaningful patterns emerge at 5-phrase window level (usually "
    "half-chorus). Individual phrases are too short to show much on their own: it is only when several consecutive phrases are averaged together that stable regions become distinguishable from volatile ones. This suggests organization at three levels: individual rest-delimited phrases, groups of roughly five of them, and the chorus.",
    first_line_indent=False
)
add_body(doc, "One tune exhibits paradoxical temporal properties:")
add_body_with_italic(doc, [
    ("My Little Suede Shoes", "bold"),
])
add_bullet(doc, "Lowest mean complexity in corpus: 6.58")
add_bullet(doc, "Highest complexity variability: CV = 0.99")
add_bullet(doc, "Highest dissonance variability: CV = 1.37")

add_body_with_italic(doc, [
    ("This tune alternates between extremely simple and moderately complex passages, exhibiting "
     "what we call a ", "normal"),
    ("trap-door structure", "italic"),
    (". We use this term, which is our own and is not standard in the literature, for a performance "
     "in which the series alternates between two well-separated levels rather than varying "
     "continuously around a central tendency: complexity holds at a low plateau, drops or leaps "
     "abruptly to the other level, and returns, as though passing through a door in the floor. The "
     "signature is high volatility combined with high lag-1 autocorrelation, since each level "
     "persists for several phrases once entered. Unlike other tunes, where volatility rises with "
     "mean complexity, \"My Little Suede Shoes\" achieves high volatility through this alternation "
     "rather than through sustained complexity (Figure 6).", "normal")
])

# Figure 6
add_empty_line(doc)
if 9 in img_paths:
    add_figure_image(doc, img_paths[9])
else:
    add_body(doc, "[Insert Figure 6: \"My Little Suede Shoes\" rolling window analysis]", first_line_indent=False)
add_figure_caption(doc, 6,
    "The outlier \"My Little Suede Shoes\" showing extreme alternation between simple and "
    "complex passages.")
add_empty_line(doc)
add_body(doc,
    "This finding demonstrates that temporal organization strategies are tune-specific; Parker conceives different architectural approaches for different compositions."
)


# ── Complexity distribution over form ────────────────────────────────────
add_heading2(doc, "Complexity Distribution over Form")
add_empty_line(doc)

add_body(doc,
    "We also analyzed whether complexity systematically varies depending on the form of a composition. "
    "For AABA tunes, does the bridge (B section) show higher complexity? For blues, does "
    "complexity peak at turnaround?",
    first_line_indent=False
)
add_body(doc, "Results show significant formal patterns:")
add_body_with_italic(doc, [
    ("Second half of forms is more complex than first half (10.87 vs 9.49, ", "normal"),
    ("p", "italic"),
    (" < .001)", "normal"),
])
add_bullet(doc, "Bridge sections (B in AABA) peak at 11.27")
add_bullet(doc, "Overall pattern: build-sustain rather than build-decay, meaning that complexity rises through the first half of the form and then holds near that level, rather than rising to a peak and falling away")

add_body(doc,
    "Chorus-level analysis shows Parker maintains high complexity throughout the solo rather than building gradually from one chorus to the next. Taken together with the results by formal position, this gives a two-part picture: complexity is roughly constant from chorus to chorus, while within each chorus it rises toward the points where the form itself creates harmonic interest, the bridge and the turnaround. Figure 12 shows the head-to-first-chorus complexity difference "
    "tune by tune."
)


# ── Improvisational strategies ───────────────────────────────────────────
add_heading2(doc, "Improvisational Strategies")
add_empty_line(doc)

add_body(doc,
    "Autocorrelation analysis combined with volatility clustering reveals distinct temporal strategies:",
    first_line_indent=False
)

add_body_with_italic(doc, [
    ("Strategy 1: Balanced/Moderate (25 tunes)", "bold"),
])
add_sub_bullet(doc, "Example: \"Barbados\"")
add_sub_bullet(doc, "Moderate complexity (mean: 9.36)")
add_sub_bullet(doc, "Moderate volatility (CV: 0.577)")
add_sub_bullet(doc, "Positive autocorrelation (LAG-1: +0.260)")
add_sub_bullet(doc, "Characteristics: Consistent harmonic density with moderate variation, positive phrase-to-phrase continuity. Most common strategy in the corpus.")

add_empty_line(doc)
add_body_with_italic(doc, [
    ("Strategy 2: Contrasting (13 tunes)", "bold"),
])
add_sub_bullet(doc, "Example: \"Si Si\"")
add_sub_bullet(doc, "Moderate complexity (mean: 10.70)")
add_sub_bullet(doc, "Moderate volatility (CV: 0.517)")
add_sub_bullet(doc, "Negative autocorrelation (LAG-1: \u22120.106)")
add_sub_bullet(doc, "Characteristics: Phrase t negatively predicts phrase t + 1: Parker alternates between contrasting harmonic materials rather than developing continuously. The alternation itself is consistent, even though the direction of each move is not.")

add_empty_line(doc)
add_body_with_italic(doc, [
    ("Strategy 3: Exploratory (7 tunes)", "bold"),
])
add_sub_bullet(doc, "Example: \"Cosmic Rays\"")
add_sub_bullet(doc, "High complexity (mean: 12.88)")
add_sub_bullet(doc, "High volatility (CV: 0.703)")
add_sub_bullet(doc, "Low autocorrelation (LAG-1: +0.192)")
add_sub_bullet(doc, "Characteristics: Sustained high harmonic density with dramatic variation. Low autocorrelation suggests episodic structure: phrases organized by chorus-level development arcs rather than local phrase-to-phrase relationships. Composed improvisation.")

add_empty_line(doc)
add_body_with_italic(doc, [
    ("Outlier Tune: Volatile/Continuous (1 tune)", "bold"),
])
add_sub_bullet(doc, "Example: \"My Little Suede Shoes\"")
add_sub_bullet(doc, "Low complexity (mean: 6.58, lowest in corpus)")
add_sub_bullet(doc, "Extreme volatility (CV: 0.986, highest in corpus)")
add_sub_bullet(doc, "High autocorrelation (LAG-1: +0.529, highest in corpus)")
add_sub_bullet(doc, "Characteristics: alternates between extremely simple and moderately complex passages with high predictability. Trap-door structure where volatility is self-perpetuating: complexity begets more complexity through phrase-level continuity, but overall complexity remains low through strategic simplicity.")

add_body(doc,
    "Because the dissonance weights enter one of the four clustering features, we checked how far "
    "the grouping depends on them. Repeating the clustering under five alternative weighting schemes "
    "(Table 3) leaves the strategy assignment identical in three cases and agreeing on 83% to 85% of "
    "tunes in the remaining two. The grouping is therefore not an artifact of the particular weights "
    "chosen, though the two schemes that disagree show it is not wholly indifferent to them either.",
    first_line_indent=False
)
add_empty_line(doc)
add_table_heading(doc, "Table 3. Strategy assignment is largely insensitive to the dissonance weighting scheme.")
create_table(doc,
    ["Weighting (ic\u2081, ic\u2082, ic\u2086)", "ARI", "Tunes assigned alike"],
    [
        ["reported: 1.0, 0.5, 0.8", "\u2014", "\u2014"],
        ["1.0, 0.5, 0.6", "1.00", "100%"],
        ["1.0, 0.5, 1.0", "0.58", "83%"],
        ["1.0, 0.25, 0.8", "0.55", "85%"],
        ["1.0, 1.0, 1.0", "1.00", "100%"],
        ["1.0, 0.5, 0.8 plus ic\u2084 at 0.2", "1.00", "100%"],
    ]
)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Note. Clustering repeated from scratch under each weighting (k = 4, 20 restarts, "
                "standardized features). ARI is the adjusted Rand index against the reported "
                "solution, where 1.00 denotes identical grouping.")
run.font.size = Pt(9)
run.font.italic = True
run.font.name = "Times New Roman"
add_empty_line(doc)

add_body(doc,
    "These strategies are not claims about conscious performer choice but emergent properties of "
    "tune-specific temporal organization. Figure 7 shows how the four groups separate across the "
    "clustering features, and Figure 13 gives their autocorrelation profiles across lags 1\u20135, "
    "where the contrast between continuous development and alternation is clearest."
)

# Figure 7
add_empty_line(doc)
if 11 in img_paths:
    add_figure_image(doc, img_paths[11])
else:
    add_body(doc, "[Insert Figure 7: Cluster characteristics]", first_line_indent=False)
add_figure_caption(doc, 7,
    "Strategy characteristics showing separation across four features. Strategy 1 (\"Balanced\", "
    "n=25): moderate complexity with positive autocorrelation. Strategy 2 (\"Contrasting\", n=13): "
    "moderate complexity with negative autocorrelation. Strategy 3 (\"Exploratory\", n=7): highest "
    "complexity and volatility with near-zero autocorrelation. The outlier tune (n = 1): paradoxically "
    "combines lowest complexity with extreme volatility and high positive autocorrelation.")
add_empty_line(doc)


# ── Gravity ──────────────────────────────────────────────────────────────
add_heading2(doc, "Gravity")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("We introduced ", "normal"),
    ("gravity", "italic"),
    (" to describe directional causal relationships between harmonic dimensions "
     "in improvisation, measured via Granger causality testing. For each tune with \u226510 phrases, "
     "we tested whether past values of one variable improve prediction of another variable beyond "
     "autoregressive history.", "normal")
], first_line_indent=False)

add_body_with_italic(doc, [
    ("Granger causality testing reveals that phrase-level reactive processes account for a minority of "
     "temporal organization. In 17.4% of tunes (8/46), past values of dissonance significantly predict "
     "future complexity (", "normal"),
    ("p", "italic"),
    (" < .05). The reverse direction shows weaker effects: 8.7% of tunes (4/46) "
     "show significant Granger causation from complexity to dissonance. Critically, 80.4% of tunes (37/46) show no significant Granger causation in either direction, suggesting that most temporal organization operates "
     "independently of local phrase-level reactive patterns.", "normal")
])

add_body_with_italic(doc, [
    ("Among the 6 tunes showing Granger causation in one direction only, 5 show Dissonance\u2192Complexity while "
     "1 shows Complexity\u2192Dissonance. This 5:1 ratio is suggestive of preferential directionality but "
     "does not reach statistical significance (binomial test: 5 of 6 unidirectional cases favor D\u2192C, "
     "", "normal"),
    ("p", "italic"),
    (" = .109, ", "normal"),
    ("n", "italic"),
    (" = 6). The mean ", "normal"),
    ("F", "italic"),
    ("-statistic for Dissonance\u2192Complexity (2.12) exceeds that for "
     "Complexity\u2192Dissonance (1.36), supporting modest directional asymmetry, though the overlap "
     "in distributions suggests this is not a universal pattern.", "normal")
])

add_body(doc,
    "Three tunes show significant Granger effects in both directions simultaneously. This pattern "
    "suggests mutual dependence between dissonance and complexity across phrase boundaries, distinct "
    "from the unidirectional patterns observed in other performances."
)

add_body(doc,
    "These figures are computed on the raw dissonance measure, which overlaps with complexity by "
    "construction. Repeating every test with the density-independent dissonance described in the "
    "Methodology gives the comparison in Table 4. The rates fall, as expected once the shared "
    "density component is removed, but the pattern does not change: Granger causation remains a "
    "minority phenomenon, and remains more common from dissonance to subsequent complexity than the "
    "reverse. On the corrected measure the share of tunes showing no relation in either direction "
    "rises from 80.4% to 84.8%, and the directional ratio widens slightly from 2:1 to 2.5:1. We "
    "therefore report the original figures as the headline result and treat the corrected ones as "
    "confirmation that the finding does not depend on the overlap between the two measures."
)
add_empty_line(doc)
add_table_heading(doc, "Table 4. Granger results are unchanged in pattern when the overlap between dissonance and complexity is removed.")
create_table(doc,
    ["Dissonance measure", "D \u2192 C", "C \u2192 D", "Neither", "Mean F (D\u2192C / C\u2192D)"],
    [
        ["raw (reported above)", "17.4%", "8.7%", "80.4%", "2.12 / 1.36"],
        ["density-independent", "10.9%", "4.3%", "84.8%", "1.77 / 0.90"],
    ]
)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Note. Lag 1, p < .05, 46 tunes. D \u2192 C denotes dissonance Granger-causing "
                "subsequent complexity. The density-independent measure is dissonance divided by "
                "complexity, which correlates with complexity at r = .03 against r = .94 for the "
                "raw measure.")
run.font.size = Pt(9)
run.font.italic = True
run.font.name = "Times New Roman"
add_empty_line(doc)

add_body_with_italic(doc, [
    ("Strategy-specific patterns", "bold"),
    (" reveal critical distinctions in temporal organization. Strategy 3 "
     "(\"Exploratory\", 7 tunes) shows markedly less Granger causation than the other strategies: no instances of complexity Granger-causing dissonance (0/7 vs 8.0\u201315.4% in the other strategies) and only one instance of dissonance Granger-causing complexity (1/7, 14.3%). \"Exploratory\" performances "
     "also show zero phrase-length effects in either direction (0/7), contrasting with Strategy 2's "
     "23.1% (3/13). This pattern is consistent with chorus-level architectural planning: organization determined at the scale of the chorus rather than by phrase-level response.", "normal")
])

add_body(doc,
    "\"Balanced\" performances (Strategy 1, 25 tunes) show moderate Granger causation from dissonance to complexity (5/25, 20.0%), suggesting these performances blend reactive navigation with architectural "
    "planning. Phrase-level Granger causation operates selectively rather than universally, revealing "
    "phrase-level navigation guided by larger-scale organizational goals."
)

add_body(doc,
    "\"Contrasting\" performances (Strategy 2, 13 tunes) show elevated phrase-length effects (3/13, "
    "23.1% for both Phrase Length\u2192Complexity and Phrase Length\u2192Dissonance), suggesting temporal "
    "organization operates partially through phrase duration modulation rather than purely "
    "through harmonic tension. This represents a distinct organizational mode where volatility "
    "emerges from strategic phrase-length variation rather than harmonic feedback loops."
)

add_body(doc,
    "The outlier tune, \"My Little Suede Shoes\", exhibits a distinctive pattern: no Granger causation between dissonance and complexity in either direction but complete phrase-length Granger causation (1/1, 100%). "
    "This tune's trap-door structure operates through phrase-length modulation rather than harmonic "
    "tension: volatility perpetuates through strategic alternation between "
    "brief and extended phrases rather than through dissonance-complexity feedback loops. \"My "
    "Little Suede Shoes\" exemplifies Parker's engagement with Afro-Cuban rhythms and simplified "
    "harmonic forms, contrasting with his bebop-oriented tunes. The extreme volatility (CV = 0.99) "
    "despite low mean complexity (6.58) suggests strategic alternation appropriate to the tune's "
    "rhythmic and formal character."
)

add_body_with_italic(doc, [
    ("This finding reframes improvisation not as uniformly spontaneous but as strategically "
     "variable: Parker selects organizational modes, reactive navigation vs. composed architecture vs. "
     "phrase-length modulation, appropriate to each tune's character and formal constraints. "
     "The \"Exploratory\" strategy's near-absence of phrase-level Granger causation (1 of 28 significant effects "
     "across 7 tunes) suggests that predetermined chorus-level planning can operate independently "
     "of local reactive processes. Figure 8 gives the significance rates for all four tests across "
     "the 46 tunes.", "normal")
])

# Figure 8
add_empty_line(doc)
if 13 in img_paths:
    add_figure_image(doc, img_paths[13])
else:
    add_body(doc, "[Insert Figure 8: Granger causality significance rates]", first_line_indent=False)
add_figure_caption(doc, 8,
    "Granger causation significance rates across 46 tunes showing that phrase-level Granger causation is a minority pattern (19.6% overall). Among tunes showing Granger causation, Dissonance\u2192"
    "Complexity (17.4%) exceeds Complexity\u2192Dissonance (8.7%), though asymmetry is "
    "suggestive rather than definitive (p = .109).")
add_empty_line(doc)

# ── Robustness ───────────────────────────────────────────────────────────
add_heading2(doc, "Robustness")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("We introduced ", "normal"),
    ("robustness", "italic"),
    (" to measure triadic content in interval vectors: how many complete "
     "triads (major, minor, diminished, augmented) are embedded in each pitch-class set. This metric "
     "tests whether frequently used interval vectors are triadically rich (offering stable harmonic "
     "foundations) or triadically sparse (offering navigational flexibility).", "normal")
], first_line_indent=False)

add_body_with_italic(doc, [
    ("Results reveal a significant negative correlation between frequency of interval vectors and triadic content (", "normal"),
    ("r", "italic"),
    (" = \u22120.350, ", "normal"),
    ("p", "italic"),
    (" < .001, ", "normal"),
    ("n", "italic"),
    (" = 165). Parker's most frequently used interval vectors contain substantially "
     "fewer triads than less frequent IVs.", "normal")
])

add_body(doc,
    "Three means are reported below and they answer different questions, so we define each before "
    "giving values. The unweighted mean is the arithmetic mean of triadic content over the 165 "
    "distinct interval vectors, counting each vector once however often Parker used it; it describes "
    "the vocabulary as an inventory. The frequency-weighted mean weights each vector by its number "
    "of occurrences in the corpus before averaging, which is equivalent to the expected triadic "
    "content of a segment drawn at random from a performance; it describes the vocabulary as "
    "deployed. The comparison mean is the unweighted mean over the 145 vectors outside the top 20, "
    "and serves only as the reference group for the top-20 contrast. The practical difference is "
    "that the unweighted mean asks what Parker's vocabulary contains and the weighted mean asks "
    "what a listener actually hears; a gap between them is itself the finding, since it can arise "
    "only if triadically sparse vectors are used disproportionately often."
)

add_body_with_italic(doc, [
    ("The top 20 most frequent interval vectors show mean triadic content of 0.6 triads per IV, "
     "compared with 2.6 triads per IV across the remaining 145 vectors, a difference of 2.0 triads "
     "(95% CI [\u22122.55, \u22121.50] for the difference in means; ", "normal"),
    ("t", "italic"),
    (" = \u22123.66, ", "normal"),
    ("p", "italic"),
    (" < .001, Cohen's ", "normal"),
    ("d", "italic"),
    (" = \u22120.87). Across the whole vocabulary the unweighted mean is 2.33 triads per "
     "vector, while the frequency-weighted mean is 1.09. The vocabulary Parker possesses is thus "
     "roughly twice as triadically dense as the vocabulary he actually plays, which is the sense in "
     "which he systematically favors triadically sparse structures.", "normal")
])

add_body_with_italic(doc, [
    ("Analysis across frequency quartiles (Table 5) reveals a monotonic pattern: rare IVs (Q1) "
     "contain mean 3.7 triads, while the most common IVs (Q4) contain only 0.9 triads (ANOVA: ", "normal"),
    ("F", "italic"),
    (" = 12.13, ", "normal"),
    ("p", "italic"),
    (" < .001). This gradient demonstrates that triadic sparsity correlates systematically "
     "with Parker's usage preferences rather than occurring by chance. Figure 9 plots triadic "
     "content against usage frequency for all 165 interval vectors, showing that the relationship "
     "holds across the full range rather than only between the quartile extremes.", "normal")
])

# Table 3
add_empty_line(doc)
add_table_heading(doc, "Table 5. Triadic content decreases monotonically with usage frequency.")
create_table(doc,
    ["Frequency Quartile", "Mean Triads", "SD", "N"],
    [
        ["Q1 (Rare)", "3.74", "2.94", "45"],
        ["Q2", "2.53", "2.26", "38"],
        ["Q3", "1.98", "1.91", "41"],
        ["Q4 (Most Common)", "0.94", "1.23", "41"],
    ]
)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("One-way ANOVA: F(3, 161) = 12.13, p < .001")
run.font.size = Pt(9)
run.font.italic = True
run.font.name = "Times New Roman"
add_empty_line(doc)

# Figure 9
if 14 in img_paths:
    add_figure_image(doc, img_paths[14])
else:
    add_body(doc, "[Insert Figure 9: Robustness vs frequency]", first_line_indent=False)
add_figure_caption(doc, 9,
    "Robustness (triadic content) as a function of usage frequency.")
add_empty_line(doc)

# ══════════════════════════════════════════════════════════════════════════
# DISCUSSION
# ══════════════════════════════════════════════════════════════════════════
add_heading1(doc, "Discussion")
add_empty_line(doc)

add_heading2(doc, "Temporal Evolution in Bebop")
add_empty_line(doc)

add_body(doc,
    "Our findings suggest an alternative to the traditional assumption that improvisers start simply "
    "and progressively introduce more complex materials during performance, building toward "
    "climax through vocabulary expansion.",
    first_line_indent=False
)

add_body(doc,
    "In Parker's practice, vocabulary is largely complete before improvisation begins: 81.1% of "
    "unique interval vectors are already present in the composed head, and the first improvised "
    "chorus adds only a further 16.5%. Temporal evolution is not accumulation "
    "of materials but exploration of pathways: new transitions between existing harmonic "
    "nodes. When complexity increases during performance, it's not because new materials are "
    "introduced but because Parker navigates more rapidly or tortuously through existing materials."
)

add_body(doc,
    "This pattern aligns with cognitive models of expert improvisation emphasizing pre-learned "
    "chunks and schemas (Norgaard, 2014; Pressing, 1988). Norgaard's research on cognitive processes in jazz improvisation demonstrates that expert jazz musicians rely extensively on patterns stored in long-term memory, deployed through rapid retrieval and recombination rather than real-time "
    "generation of novel materials. Parker's vocabulary front-loading (81.1% already present in the "
    "head) supports this model: improvisational fluency emerges from navigational facility "
    "through pre-established vocabulary rather than progressive invention during performance."
)

add_body(doc,
    "This reframing has pedagogical implications. Rather than drilling increasingly exotic scales "
    "assuming students will progressively deploy them during solos, pedagogy might benefit from "
    "emphasizing navigational fluency: how to move flexibly through materials you already know. "
    "The challenge is not \"what to play\" but \"how to move.\""
)

add_heading2(doc, "Relation to Earlier Findings")
add_empty_line(doc)

add_body(doc,
    "Two prior studies bear directly on these results. Frieler and colleagues (2016b) examined the "
    "dramaturgy of monophonic jazz solos in the Weimar Jazz Database, asking whether solos exhibit "
    "arc-like intensity contours, and found that a single rising-then-falling shape describes only a "
    "minority of performances, with several distinct contour types coexisting in the corpus. Our "
    "finding that no single temporal template fits Parker's solos, and that they instead fall into "
    "three groups differing in volatility and predictability, is the same result reached by a "
    "different route and on a different corpus: contour heterogeneity rather than a universal arc. "
    "That two independent operationalizations converge on this point is some reassurance that it is "
    "not an artifact of either.",
    first_line_indent=False
)
add_body(doc,
    "Love (2012) identified recurring phrasing and melodic schemata in Parker's blues and argued "
    "that they are pre-learned solutions deployed in performance. His schemata operate at roughly "
    "the scale our phrase groups occupy, and his account predicts what we observe: if a performer "
    "assembles a chorus from pre-learned units, phrase-to-phrase dependencies should be weak, "
    "because each unit answers to the plan rather than to its predecessor. Our 80.4% figure is "
    "consistent with that prediction, though it does not establish the mechanism. Love's later "
    "ecological account (2017) frames improvisation as the continuous perception of affordances "
    "rather than the execution of stored plans, which makes the opposite prediction for the minority "
    "of tunes where we do find phrase-level dependence. The present data do not adjudicate between "
    "these positions; they do suggest that the two may describe different performances rather than "
    "competing descriptions of all of them."
)

add_heading2(doc, "Temporal Organization Is Tune-Specific")
add_empty_line(doc)

add_body(doc,
    "The three improvisational strategies reveal that temporal organization is tune-specific. Parker does not apply a single approach across all contexts; rather, he "
    "conceives distinct temporal architectures for different compositions.",
    first_line_indent=False
)

add_body(doc,
    "This challenges assumptions about \"personal style\" as consistent approaches applied uniformly. "
    "While Parker's intervallic vocabulary is recognizable across tunes (certain interval "
    "vectors appear frequently regardless of composition), his temporal organization varies dramatically. "
    "\"Cosmic Rays\" uses episodic structure, \"Bluebird\" uses slow-burn climax, \"My Little "
    "Suede Shoes\" uses trap-door contrasts, \"Si Si\" maintains consistency."
)

add_body(doc, "This suggests improvisation operates at multiple scales with different organizing principles:")
add_bullet(doc, "Material level (which interval vectors): relatively consistent across tunes")
add_bullet(doc, "Temporal level (how material unfolds): tune-specific strategic architectures")
add_bullet(doc, "Phrase level (surface articulation): consistently short across all tunes")

add_body(doc,
    "The interaction between these scales produces the rich temporal complexity we observe in expert "
    "improvisation."
)

add_heading2(doc, "Reactive Navigation and Temporal Heterogeneity")
add_empty_line(doc)

add_body(doc,
    "The Granger causality findings reveal fundamental heterogeneity in Parker's temporal organization "
    "strategies. The majority of performances show no significant phrase-level Granger causation between "
    "dissonance and complexity, suggesting that temporal organization in these tunes operates "
    "according to principles other than local reactive processes. This finding challenges assumptions "
    "about improvisation as uniformly \"reactive\" and instead suggests multiple organizational modes "
    "coexisting within a single performer's practice.",
    first_line_indent=False
)

add_heading3(doc, "Strategy-Specific Causality Patterns")
add_empty_line(doc)

add_body(doc,
    "Strategy-specific patterns provide direct evidence for distinct organizational logics. Strategy 3 "
    "(\"Exploratory\", 7 tunes) shows markedly less Granger causation: only one significant result across 28 "
    "tests (3.6%), compared to 11/100 (11.0%) for Strategy 1 (\"Balanced\") and 10/52 (19.2%) "
    "for Strategy 2 (\"Contrasting\"). This near-absence of phrase-level Granger causation in \"Exploratory\" performances "
    "indicates chorus-level architectural planning: organization determined at the scale of the chorus and operating independently of local phrase-to-phrase response.",
    first_line_indent=False
)

add_body(doc,
    "\"Balanced\" performances (Strategy 1, 25 tunes) show moderate Granger causation from dissonance to complexity (5/25, 20.0%), suggesting these performances blend reactive navigation with architectural "
    "planning. Phrase-level Granger causation operates selectively rather than universally, revealing "
    "phrase-level navigation guided by larger-scale organizational goals."
)

add_body(doc,
    "\"Contrasting\" performances (Strategy 2, 13 tunes) show elevated phrase-length effects (3/13, "
    "23.1% for both Phrase Length\u2192Complexity and Phrase Length\u2192Dissonance), suggesting temporal "
    "organization operates partially through phrase duration modulation rather than purely "
    "through harmonic tension. This represents a distinct organizational mode where volatility "
    "emerges from strategic phrase-length variation rather than harmonic feedback loops."
)

add_body(doc,
    "The outlier \"My Little Suede Shoes\" exemplifies yet another organizational logic: no Granger causation between dissonance and complexity, but maximal phrase-length effects (1/1, 100%). This "
    "tune's trap-door structure operates through phrase-length modulation rather than harmonic "
    "navigation, demonstrating that organizational modes can be tune-specific rather than strategy-general."
)

add_heading3(doc, "Reactive Navigation in the Minority")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("Among the minority of tunes showing phrase-level Granger causation (19.6%), patterns are consistent "
     "with\u2014though do not definitively prove\u2014reactive navigation. When ", "normal"),
    ("dissonance", "italic"),
    (" at phrase t "
     "predicts ", "normal"),
    ("complexity", "italic"),
    (" at phrase t+1, this could reflect several processes: (1) reactive navigation, "
     "where Parker perceives ", "normal"),
    ("dissonance", "italic"),
    (" as requiring resolution through ", "normal"),
    ("complexity", "italic"),
    ("; (2) harmonic "
     "constraint, where the chord progression creates conditions where dissonant choices constrain "
     "subsequent options; (3) compositional planning, where Parker pre-plans both dissonant passages "
     "and resolutions at chorus level, creating statistical association without phrase-level causation; "
     "or (4) transcription artifacts from segmentation methodology.", "normal")
], first_line_indent=False)

add_body(doc,
    "The 2:1 ratio favoring Dissonance\u2192Complexity over Complexity\u2192Dissonance (17.4% vs "
    "8.7%) suggests preferential directionality, though the binomial test (p = .109) indicates this "
    "asymmetry does not reach statistical significance. Combined with higher mean F-statistics for "
    "Dissonance\u2192Complexity (2.12 vs 1.36), the pattern is consistent with Parker responding to "
    "dissonant conditions through complexity more frequently than creating dissonance via complex "
    "choices, though the evidence is suggestive rather than conclusive."
)

add_heading3(doc, "Cognitive Frameworks for Temporal Organization")
add_empty_line(doc)

add_body(doc,
    "This heterogeneity connects to existing cognitive models of improvisation. Pressing's (1988) "
    "cognitive constraints model posits that improvisers operate under real-time processing "
    "limitations requiring strategic management of cognitive load. In Pressing's account an "
    "improvisation proceeds as a series of event clusters, each planned and executed under the time "
    "pressure of performance. The relevant point for us is not the term itself but the general claim "
    "that processing load varies across a performance and constrains what can be chosen next. Our "
    "results are consistent with dissonant conditions acting as one such constraint, with subsequent "
    "complexity rising as Parker works out of them. The directional asymmetry (dissonance predicting "
    "complexity more than the reverse) is consistent with Pressing's model where harmonic tension "
    "creates processing demands that constrain subsequent choices.",
    first_line_indent=False
)

add_body(doc,
    "However, the predominance of performances showing no Granger causation indicates that reactive "
    "processing operates selectively rather than universally. Most performances proceed according "
    "to pre-planned architectures immune to phrase-level reactive constraints, suggesting Parker's "
    "expertise enables flexible switching between reactive and compositional modes."
)

add_body(doc,
    "Johnson-Laird (2002) distinguishes between rule-based generation proceeding step by step "
    "through local decisions, which we will call the algorithmic mode, and the realization of musical "
    "ideas conceived in advance, which we will call the inspirational mode. The labels are ours, "
    "introduced here for brevity, rather than Johnson-Laird's own terms. Our findings "
    "suggest Parker employs both modes strategically: the performances showing no phrase-level Granger causation align with Johnson-Laird's inspirational mode, where chorus-level architectures unfold "
    "independently of local reactive processes. The 19.6% showing Granger causation represent "
    "algorithmic mode, where harmonic conditions at moment t constrain choices at moment t+1 "
    "through rule-based navigation."
)

add_body(doc,
    "This framework helps explain the strategy-specific patterns: \"Exploratory\" performances "
    "(3.6%) operate primarily through the inspirational mode, executing chorus-level plans; \"Balanced\" performances (11.0%) blend both modes; \"Contrasting\" "
    "performances emphasize phrase-length variation as a structural algorithm distinct from harmonic "
    "reactive processes."
)

add_heading3(doc, "Synthesis: Multiple Organizational Logics")
add_empty_line(doc)

add_body(doc,
    "Rather than a single organizational mode (reactive vs. composed, spontaneous vs. planned), "
    "expert improvisers like Parker operate across a continuum, selecting organizational strategies "
    "appropriate to each performance. The term gravity captures this phenomenon: in some performances, "
    "harmonic tension exerts directional force on subsequent choices (reactive/algorithmic "
    "mode); in others, temporal organization proceeds independently of local conditions (composed/inspirational "
    "mode); in still others, phrase-length variation drives temporal structure independently "
    "of harmonic content (structural algorithm).",
    first_line_indent=False
)

add_body(doc,
    "The strategy-specific patterns \u2013 \"Exploratory\" showing near-zero effects (3.6%), "
    "\"Balanced\" showing moderate effects (11.0%), \"Contrasting\" emphasizing phrase-length "
    "(23.1%) \u2014 demonstrate that organizational modes correlate with broader improvisational "
    "strategies identifiable through autocorrelation and volatility analysis. The minority status of phrase-level Granger causation overall (19.6%) suggests that chorus-level architectural planning predominates "
    "over moment-to-moment reactive navigation in Parker's mature improvisational practice. "
    "Mastery emerges not from consistent application of a single organizational principle but from "
    "flexible deployment of multiple temporal logics appropriate to compositional context and "
    "improvisational intent."
)

add_heading2(doc, "Triadic Sparsity")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("The negative correlation between frequency of interval vectors and triadic content (", "normal"),
    ("r", "italic"),
    (" = \u22120.350, ", "normal"),
    ("p", "italic"),
    (" < .001) "
     "challenges fundamental assumptions about bebop harmony. Traditional harmony assumes triads "
     "provide stable foundations above which extensions are added. In jazz harmony, triads also "
     "make great \"upper structure\" to super-impose over harmonic material. Parker's practice reveals "
     "a different organizing principle: his most frequently deployed interval vectors are triadically "
     "sparse, not triadically rich.", "normal")
], first_line_indent=False)

add_body(doc,
    "The magnitude of this preference is substantial: Parker's most common IVs (top 20) contain "
    "less than one quarter the triadic content of the corpus average (0.6 vs 2.6 triads, Cohen's d = "
    "\u22120.87). This represents a large effect size, suggesting systematic selection rather than random "
    "variation. When weighted by actual usage frequency, Parker's effective triadic content (1.09) "
    "falls 53% below the available corpus mean (2.33)."
)

add_body(doc,
    "This pattern suggests bebop harmony is organized not around triadic stability but around "
    "navigational flexibility. Triadically sparse interval vectors offer more degrees of freedom for "
    "continuation: they don't commit to specific triadic implications, enabling pivots to multiple "
    "harmonic destinations. This explains why Parker's frequently used interval vectors serve as "
    "hubs in temporal networks: they're selected for connectivity rather than harmonic stability. "
    "An IV like (111000), containing only one triad despite six interval classes, functions effectively "
    "precisely because it avoids triadic commitment."
)

add_body(doc,
    "Parker's practice instead suggests mastery emerges from navigating between harmonic regions "
    "through triadically ambiguous pivot structures rather than from accumulating exotic triadic "
    "extensions. The correlation between triadic sparsity and usage frequency (r = \u22120.350) indicates "
    "this is a deliberate preference: Parker systematically selects pivot structures over stable foundations."
)

add_heading2(doc, "Phrase-Level vs. Chorus-Level Hierarchy")
add_empty_line(doc)

add_body(doc,
    "The finding that phrases are extremely short (median 1 segment) while meaningful patterns "
    "emerge at 5-phrase window level reveals hierarchical temporal organization:",
    first_line_indent=False
)
add_bullet(doc, "Surface level: Rapid articulation (1\u20132 segments per phrase)")
add_bullet(doc, "Phrase-group level: Meaningful harmonic motion (5-phrase windows \u2248 half-chorus)")
add_bullet(doc, "Chorus level: Strategic architecture (solo development arcs, overall complexity)")

add_body(doc,
    "This hierarchy parallels linguistic organization: phonemes \u2192 words \u2192 phrases \u2192 sentences. "
    "Each level has distinct organizing principles:"
)
add_bullet(doc, "Surface: Breath/articulation determines phrase boundaries")
add_bullet(doc, "Phrase-group: Local harmonic motion and reactive navigation")
add_bullet(doc, "Chorus: Strategic architecture and composed plans")

add_body_with_italic(doc, [
    ("The three improvisational strategies operate at chorus level, not phrase level. The outlier "
     "tune, \"My Little Suede Shoes\", alternates between simple and complex ", "normal"),
    ("phrase groups", "bold"),
    (", not individual phrases. This suggests Parker's improvisational conception "
     "operates primarily at phrase-group and chorus levels, with surface articulation following from "
     "these higher-level plans.", "normal")
])

# ══════════════════════════════════════════════════════════════════════════
# CONCLUSION
# ══════════════════════════════════════════════════════════════════════════
add_heading1(doc, "Conclusion")
add_empty_line(doc)

add_body_with_italic(doc, [
    ("This study demonstrates that time series analysis reveals temporal organization principles in "
     "jazz improvisation invisible to traditional analytical approaches. By tracking harmonic metrics "
     "(", "normal"),
    ("complexity", "italic"),
    (", ", "normal"),
    ("dissonance", "italic"),
    (", ", "normal"),
    ("rate of change", "italic"),
    (") across temporal scales from segments through phrases to "
     "choruses, we uncover strategic architectures, causal relationships, and hierarchical organization "
     "that challenge pedagogical assumptions.", "normal")
], first_line_indent=False)

add_body(doc, "Key findings reframe our understanding of bebop improvisation:")

# Numbered findings
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.left_indent = Inches(0.5)
p.paragraph_format.first_line_indent = Inches(-0.5)
run = p.add_run("1. ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("Temporal heterogeneity predominates over uniform reactive processes: ")
run.font.size = Pt(10)
run.font.bold = True
run.font.name = "Times New Roman"
run = p.add_run(
    "majority of performances show no phrase-level Granger causation between dissonance and complexity, suggesting "
    "that chorus-level architectural planning, constitutes Parker's primary organizational mode rather than moment-to-moment reactive navigation."
)
run.font.size = Pt(10)
run.font.name = "Times New Roman"

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.left_indent = Inches(0.5)
p.paragraph_format.first_line_indent = Inches(-0.5)
run = p.add_run("2. ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("Three distinct improvisational strategies exhibit different temporal logics: ")
run.font.size = Pt(10)
run.font.bold = True
run.font.name = "Times New Roman"
run = p.add_run(
    "\"Exploratory\" performances (7 tunes) show near-zero phrase-level Granger causation (3.6%), consistent with chorus-level architectural planning; \"Balanced\" performances (25 tunes) exhibit moderate "
    "reactive effects (11.0%); \"Contrasting\" performances (13 tunes) organize themselves instead through phrase duration, where the length of one phrase predicts the complexity or dissonance of the next (23.1%). Temporal organization is tune-specific, with Parker selecting organizational modes appropriate to compositional context."
)
run.font.size = Pt(10)
run.font.name = "Times New Roman"

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.left_indent = Inches(0.5)
p.paragraph_format.first_line_indent = Inches(-0.5)
run = p.add_run("3. ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("Vocabulary front-loading enables pathway exploration: ")
run.font.size = Pt(10)
run.font.bold = True
run.font.name = "Times New Roman"
run = p.add_run(
    "81.1% of unique interval vectors appear in the composed head, with 16.5% added during the first improvised chorus "
    "and 2.4% thereafter. Temporal evolution reflects exploration of new transitions "
    "between existing harmonic nodes rather than progressive vocabulary expansion, though "
    "the substantial addition in the first improvised chorus indicates refinement continues beyond initial deployment."
)
run.font.size = Pt(10)
run.font.name = "Times New Roman"

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.left_indent = Inches(0.5)
p.paragraph_format.first_line_indent = Inches(-0.5)
run = p.add_run("4. ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("Triadically sparse structures predominate in frequent usage: ")
run.font.size = Pt(10)
run.font.bold = True
run.font.name = "Times New Roman"
run = p.add_run(
    "significant negative correlation between frequency and triadic content (r = \u22120.350, p < .001) reveals that "
    "Parker's most common interval vectors contain less than half the triadic content of corpus "
    "average (0.6 vs 2.6 triads, Cohen's d = \u22120.87). Mastery emerges from navigational flexibility "
    "through triadically ambiguous pivot structures rather than accumulation of triadically rich "
    "exotic materials."
)
run.font.size = Pt(10)
run.font.name = "Times New Roman"

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.space_before = Pt(0)
p.paragraph_format.space_after = Pt(0)
p.paragraph_format.left_indent = Inches(0.5)
p.paragraph_format.first_line_indent = Inches(-0.5)
run = p.add_run("5. ")
run.font.size = Pt(10)
run.font.name = "Times New Roman"
run = p.add_run("Hierarchical temporal organization operates across multiple scales: ")
run.font.size = Pt(10)
run.font.bold = True
run.font.name = "Times New Roman"
run = p.add_run(
    "surface articulation (relatively brief phrases averaging 2 segments) organizes into phrase groups (5-phrase "
    "windows revealing meaningful patterns) organized by chorus-level strategic architecture, with "
    "different organizing principles operating at each temporal scale."
)
run.font.size = Pt(10)
run.font.name = "Times New Roman"

add_empty_line(doc)
add_body(doc,
    "One caveat qualifies every cognitive reading offered above. Our units of analysis are interval "
    "vectors, and these are analysts' constructs: there is no evidence that Parker represented his "
    "material in these terms, and the pattern-based literature suggests that the units he stored and "
    "retrieved were melodic figures, with ordering, contour and metric placement intact. A regularity "
    "in the interval vectors is therefore a regularity in the pitch content those figures produce, "
    "which constrains theories of what was stored without identifying the stored objects themselves. "
    "Where we speak of vocabulary above, the claim is about the corpus rather than about Parker's "
    "memory.",
    first_line_indent=False
)
add_empty_line(doc)
add_body_with_italic(doc, [
    ("We introduce novel analytical concepts: ", "normal"),
    ("gravity", "italic"),
    (" (directional causal relationships measured via "
     "Granger testing) and ", "normal"),
    ("robustness", "italic"),
    (" (triadic content as structural flexibility). These concepts enable "
     "quantitative analysis of improvisational practice and bridge computational analysis and music-"
     "theoretical interpretation, revealing how improvisers navigate harmonic space through multiple "
     "organizational logics.", "normal")
])

add_heading2(doc, "Limitations")
add_empty_line(doc)

add_body(doc,
    "This study's findings are subject to several methodological constraints. First, interval vectors "
    "discard ordering, repetition, contour, register and metric placement. Two passages using the "
    "same notes in a different order, or placing the chord tones on different beats, receive the same "
    "vector, and the second of these is a real loss: a line in which the dissonances fall on strong "
    "beats is heard differently from one in which they pass between them, and our measures cannot "
    "separate the two. The abstraction is what makes a time series treatment possible, but it means "
    "our measures index how much pitch material is in play rather than how that material is heard. A "
    "perceptually weighted treatment, or one retaining metric position, would answer different and "
    "in some respects better questions.",
    first_line_indent=False
)
add_body(doc,
    "Second, phrase detection relies on transcribed rest notation, which represents transcriber "
    "interpretation of recorded performance. Alternative segmentation methods (e.g., dynamic "
    "thresholding, machine learning boundary detection) may yield different phrase structures."
)
add_body_with_italic(doc, [
    ("Third, Granger causality testing measures predictive asymmetry rather than causal intent. "
     "While significant results indicate that dissonance at phrase ", "normal"),
    ("t", "italic"),
    (" improves prediction of complexity "
     "at phrase ", "normal"),
    ("t", "italic"),
    (" + 1 beyond autoregressive history, this reflects statistical association within performance "
     "time series rather than cognitive causation.", "normal")
])
add_body(doc,
    "Fourth, the dissonance weighting (ic\u2081 \u00d7 1.0, ic\u2086 \u00d7 0.8, ic\u2082 \u00d7 0.5) reflects psychoacoustic "
    "principles but remains a choice. We tested it rather than assuming it: under five alternative "
    "schemes the strategy assignment is identical in three cases and agrees on 83% to 85% of tunes "
    "in the other two (Table 3). Two of the five do move a handful of tunes between groups, so the "
    "grouping is robust to the weighting without being wholly independent of it."
)
add_body(doc,
    "Fifth, and most consequentially, the chord progressions themselves are a possible confound. "
    "Segments follow chord symbols, and different chords afford different values on our measures "
    "regardless of what the improviser does: an applied diminished seventh will tend to produce a "
    "more dissonant segment than a tonic triad. If certain chord types also occur at characteristic "
    "positions in a form, as they do, then some of the temporal structure we report may belong to "
    "the tunes rather than to Parker. Nothing in the present design separates the two. The decisive "
    "test would be a null model in which interval vectors are generated for the same progressions by "
    "sampling pitch classes from the chord-scale relationships alone, with the observed series "
    "compared against that baseline; an alternative would compare different performers on the same "
    "tune, holding the changes constant. We regard this as the most important open question raised "
    "by the present results, and the one we would address first."
)
add_body(doc,
    "Sixth, the one-way ANOVA across frequency quartiles treats observations as independent, which "
    "is a strong assumption for data derived from time series. The quartile comparison is between "
    "interval vector types rather than between successive time points, which mitigates the concern, "
    "but it does not remove it, and the reported effect sizes should be read with that in mind "
    "(Gorman & Allison, 1996; Matyas & Greenwood, 1996)."
)
add_body(doc,
    "Finally, this corpus represents Parker's recorded output as transcribed in the Omnibook, not "
    "the complete space of his improvisational practice. The Omnibook transcriptions were made from "
    "LPs and tapes without the aid of modern slow-down tools, and they contain errors: Van Bebber "
    "(2009) reports correcting more than a thousand of them. Errors at that rate will introduce "
    "noise into every measure reported here. They are unlikely to be systematic with respect to "
    "position in a performance, so we do not expect them to generate the temporal patterns we "
    "report, but they will attenuate real effects and add uncertainty to the specific values. "
    "Findings characterize this corpus and should be tested against other artists and repertoires "
    "before generalization."
)

add_heading2(doc, "Future Directions")
add_empty_line(doc)

add_body(doc, "This methodology enables several future research directions:", first_line_indent=False)
add_empty_line(doc)

add_body_with_italic(doc, [
    ("comparative analysis: ", "bold"),
    ("Extend to multiple artists, revealing whether findings are Parker-specific or constitute broader bebop principles.", "normal"),
])
add_body_with_italic(doc, [
    ("multilayer networks: ", "bold"),
    ("Integrate pitch, rhythm, and harmonic function layers, revealing interactions invisible in single-dimension analysis.", "normal"),
])
add_body_with_italic(doc, [
    ("predictive modeling: ", "bold"),
    ("Use temporal patterns to predict next harmonic choices, testing whether computational models can capture improvisational logic.", "normal"),
])
add_body_with_italic(doc, [
    ("pedagogical applications: ", "bold"),
    ("Develop practice strategies emphasizing navigational fluency and hub-centric motion rather than vocabulary accumulation.", "normal"),
])
add_body_with_italic(doc, [
    ("historical evolution: ", "bold"),
    ("Track how temporal organization strategies changed across bebop's development from the 1940s "
     "through the 1950s. The present corpus is unordered in time, but recording dates are available "
     "for much of the Omnibook through the Dig That Lick metadata collection, which would allow the "
     "autocorrelation and clustering analyses to be repeated with performances ordered by date, "
     "testing directly whether Parker's temporal organization changed over his career.", "normal"),
])
add_body_with_italic(doc, [
    ("controlling for the changes: ", "bold"),
    ("Build the null model described in the Limitations, generating interval vectors for the same "
     "progressions from chord-scale relationships alone, so that the contribution of the harmony can "
     "be separated from the contribution of the improviser. This is the single most informative "
     "extension of the present work.", "normal"),
])
add_body_with_italic(doc, [
    ("perceptual validation: ", "bold"),
    ("Test whether the complexity and rate-of-change measures correspond to anything listeners "
     "discriminate, by collecting judgments on segments the measures rank differently. Nothing in "
     "the present study establishes that they do.", "normal"),
])

add_empty_line(doc)
add_body_with_italic(doc, [
    ("The framework developed here, particularly ", "normal"),
    ("gravity", "italic"),
    (" and ", "normal"),
    ("robustness", "italic"),
    (" concepts, three strategic "
     "categories, and multi-scale temporal analysis, provides tools for such comparative work. Time "
     "series analysis of jazz improvisation reveals hidden temporal structures that connect musical "
     "practice to broader principles of cognitive organization and creative behavior.", "normal")
])

# ══════════════════════════════════════════════════════════════════════════
# DATA AND CODE AVAILABILITY
# ══════════════════════════════════════════════════════════════════════════
add_heading1(doc, "Data and Code Availability")
add_empty_line(doc)

add_body(doc,
    "The Charlie Parker Aligned Digital Omnibook dataset combines manual transcriptions (D\u00e9guernel, "
    "Vincent, & Assayag) with automatic transcription methods and MIDI alignment (Riley & "
    "Dixon). MusicXML data provided by Inria and STMS Lab Ircam/CNRS/UPMC. Original "
    "copyrights held by Atlantic Music Corp. Data provided under Creative Commons Attribution-"
    "NonCommercial-ShareAlike license version 2.0.",
    first_line_indent=False
)
add_body(doc,
    "All analysis code, processed datasets, and documentation are publicly available at "
    "github.com/code91/parker-timeseries under MIT license. The repository includes the complete "
    "analytical pipeline, phrase detection algorithms, and visualization tools. All analysis performed "
    "using Python with pandas, NumPy, matplotlib, seaborn, NetworkX, and statsmodels libraries."
)

# ══════════════════════════════════════════════════════════════════════════
# NOTES
# ══════════════════════════════════════════════════════════════════════════
add_heading1(doc, "Notes")
add_empty_line(doc)

add_body(doc,
    "[1] Correspondence can be addressed to: Michele \"Mike\" Rubini, Independent Researcher. E-mail: rubinimusic@gmail.com.",
    first_line_indent=False
)

# ══════════════════════════════════════════════════════════════════════════
# REFERENCES
# ══════════════════════════════════════════════════════════════════════════
add_heading1(doc, "References")
add_empty_line(doc)

add_reference_with_italic(doc, [
    ("Berkowitz, A. L. (2010). ", "normal"),
    ("The improvising mind: Cognition and creativity in the musical moment", "italic"),
    (". Oxford University Press.", "normal"),
])

add_reference_with_italic(doc, [
    ("Broze, Y., & Shanahan, D. (2013). Diachronic changes in jazz harmony: A cognitive perspective. ", "normal"),
    ("Music Perception, 31", "italic"),
    ("(1), 32\u201345.", "normal"),
])

add_reference_with_italic(doc, [
    ("Chang, A., Livingstone, S. R., Bosnyak, D. J., & Trainor, L. J. (2017). Body sway reflects leadership in joint music performance. ", "normal"),
    ("Proceedings of the National Academy of Sciences, 114", "italic"),
    ("(21), E4134–E4141.", "normal"),
])

add_reference_with_italic(doc, [
    ("D\u00e9guernel, K., Vincent, E., & Assayag, G. (2016). Using multidimensional sequences for improvisation in the Omax paradigm. In R. Gro\u00dfmann & G. Hajdu (Eds.), ", "normal"),
    ("Proceedings of the 13th sound and music computing conference", "italic"),
    (" (pp. 117\u2013122). Zenodo. https://doi.org/10.5281/zenodo.1400818", "normal"),
])

add_reference_with_italic(doc, [
    ("Farbood, M. M. (2012). A parametric, temporal model of musical tension. ", "normal"),
    ("Music Perception, 29", "italic"),
    ("(4), 387\u2013428.", "normal"),
])

add_reference_with_italic(doc, [
    ("Forte, A. (1973). ", "normal"),
    ("The structure of atonal music", "italic"),
    (". Yale University Press.", "normal"),
])

add_reference_with_italic(doc, [
    ("Frieler, K., Pfleiderer, M., Zaddach, W.-G., & Abe\u00dfer, J. (2016a). Midlevel analysis of monophonic jazz solos: A new approach to the study of improvisation. ", "normal"),
    ("Musicae Scientiae, 20", "italic"),
    ("(2), 143\u2013162.", "normal"),
])

add_reference_with_italic(doc, [
    ("Frieler, K., Pfleiderer, M., Abe\u00dfer, J., & Zaddach, W.-G. (2016b). \u201cTelling a story\u201d: On the dramaturgy of monophonic jazz solos. ", "normal"),
    ("Empirical Musicology Review, 11", "italic"),
    ("(1), 68\u201382. https://doi.org/10.18061/emr.v11i1.4959", "normal"),
])

add_reference_with_italic(doc, [
    ("Goldman, A. (2016). Improvisation as a way of knowing. ", "normal"),
    ("Music Theory Online, 22", "italic"),
    ("(4).", "normal"),
])

add_reference_with_italic(doc, [
    ("Gorman, B. S., & Allison, D. B. (1996). Statistical alternatives for single-case designs. In R. D. Franklin, D. B. Allison, & B. S. Gorman (Eds.), ", "normal"),
    ("Design and analysis of single-case research", "italic"),
    (" (pp. 159\u2013214). Erlbaum.", "normal"),
])

add_reference_with_italic(doc, [
    ("Johnson-Laird, P. N. (2002). How jazz musicians improvise. ", "normal"),
    ("Music Perception, 19", "italic"),
    ("(3), 415\u2013442.", "normal"),
])

add_reference_with_italic(doc, [
    ("Lerdahl, F. (2001). ", "normal"),
    ("Tonal pitch space", "italic"),
    (". Oxford University Press.", "normal"),
])

add_reference_with_italic(doc, [
    ("Love, S. C. (2012). \u201cPossible paths\u201d: Schemata of phrasing and melody in Charlie Parker's blues. ", "normal"),
    ("Music Theory Online, 18", "italic"),
    ("(3).", "normal"),
])

add_reference_with_italic(doc, [
    ("Love, S. C. (2017). An ecological description of jazz improvisation. ", "normal"),
    ("Psychomusicology: Music, Mind, and Brain, 27", "italic"),
    ("(1), 31\u201344. https://doi.org/10.1037/pmu0000173", "normal"),
])

add_reference_with_italic(doc, [
    ("Martin, H. (1996). ", "normal"),
    ("Charlie Parker and thematic improvisation", "italic"),
    (". Scarecrow Press.", "normal"),
])

add_reference_with_italic(doc, [
    ("Martin, H. (2020). ", "normal"),
    ("Charlie Parker, composer", "italic"),
    (". Oxford University Press.", "normal"),
])

add_reference_with_italic(doc, [
    ("Matyas, T. A., & Greenwood, K. M. (1996). Serial dependency in single-case time series. In R. D. Franklin, D. B. Allison, & B. S. Gorman (Eds.), ", "normal"),
    ("Design and analysis of single-case research", "italic"),
    (" (pp. 215\u2013243). Erlbaum.", "normal"),
])

add_reference_with_italic(doc, [
    ("Merseal, H. M., Beaty, R. E., Kenett, Y. N., Lloyd-Cox, J., de Manzano, \u00d6., & Norgaard, M. (2023). Representing melodic relationships using network science. ", "normal"),
    ("Cognition, 233", "italic"),
    (", Article 105362. https://doi.org/10.1016/j.cognition.2022.105362", "normal"),
])

add_reference_with_italic(doc, [
    ("Norgaard, M. (2014). How jazz musicians improvise: The central role of auditory and motor patterns. ", "normal"),
    ("Music Perception, 31", "italic"),
    ("(3), 271\u2013287.", "normal"),
])

add_reference_with_italic(doc, [
    ("Norgaard, M., Spencer, J., & Montiel, M. (2013). Testing cognitive theories by creating a pattern-based probabilistic algorithm for melody and rhythm in jazz improvisation. ", "normal"),
    ("Psychomusicology: Music, Mind, and Brain, 23", "italic"),
    ("(4), 243–254.", "normal"),
])

add_reference_with_italic(doc, [
    ("Owens, T. (1974). ", "normal"),
    ("Charlie Parker: Techniques of improvisation", "italic"),
    (" (Doctoral dissertation). University of California, Los Angeles.", "normal"),
])

add_reference_with_italic(doc, [
    ("Pfleiderer, M., Frieler, K., Abeßer, J., Zaddach, W.-G., & Burkhart, B. (Eds.). (2017). ", "normal"),
    ("Inside the Jazzomat: New perspectives for jazz research", "italic"),
    (". Schott Campus.", "normal"),
])

add_reference_with_italic(doc, [
    ("Plomp, R., & Levelt, W. J. M. (1965). Tonal consonance and critical bandwidth. ", "normal"),
    ("Journal of the Acoustical Society of America, 38", "italic"),
    ("(4), 548\u2013560.", "normal"),
])

add_reference_with_italic(doc, [
    ("Pressing, J. (1988). Improvisation: Methods and models. In J. A. Sloboda (Ed.), ", "normal"),
    ("Generative processes in music: The psychology of performance, improvisation, and composition", "italic"),
    (" (pp. 129\u2013178). Oxford University Press.", "normal"),
])

add_reference_with_italic(doc, [
    ("Riley, X., & Dixon, S. (2024). Reconstructing the Charlie Parker Omnibook using an audio-to-score automatic transcription pipeline [Preprint]. ArXiv. https://doi.org/10.48550/arXiv.2405.16687", "normal"),
])

add_reference_with_italic(doc, [
    ("Sethares, W. A. (1993). Local consonance and the relationship between timbre and scale. ", "normal"),
    ("Journal of the Acoustical Society of America, 94", "italic"),
    ("(3), 1218\u20131228.", "normal"),
])

add_reference_with_italic(doc, [
    ("Slone, K. (1978). ", "normal"),
    ("Charlie Parker omnibook: Transcribed from his original recordings", "italic"),
    (" (J. Aebersold, Ed.). Atlantic Music Corp.", "normal"),
])

add_reference_with_italic(doc, [
    ("Van Bebber, M. (2009). ", "normal"),
    ("Charlie Parker: 60 melodies & solos", "italic"),
    (". Qpress.", "normal"),
])

add_reference_with_italic(doc, [
    ("Yamaguchi, M. (2012). ", "normal"),
    ("The bird book: The Charlie Parker real book", "italic"),
    (" (2nd ed.). Masaya Music Services.", "normal"),
])

# ── Save ─────────────────────────────────────────────────────────────────

# ════════════════════════════════════════
# APPENDIX
# ════════════════════════════════════════
add_heading1(doc, "Appendix: Supporting Figures")
add_empty_line(doc)

add_body(doc,
    "The figures below support points made in the main text, which references each of them. "
    "They are placed here rather than in the body to keep the article readable.",
    first_line_indent=False
)
add_empty_line(doc)

# Figure 10
add_empty_line(doc)
if 4 in img_paths:
    add_figure_image(doc, img_paths[4])
else:
    add_body(doc, "[Insert Figure 10: Analytical pipeline after phrase detection]", first_line_indent=False)
add_figure_caption(doc, 10,
    "After phrase detection, five parallel approaches examine temporal patterns at different "
    "scales: local dynamics (rolling windows), predictability (autocorrelation), strategies (clustering), "
    "directional prediction (Granger testing), and structural properties (robustness).")
add_empty_line(doc)

# Figure 11
if 7 in img_paths:
    add_figure_image(doc, img_paths[7])
else:
    add_body(doc, "[Insert Figure 11: Cross-chorus complexity comparison]", first_line_indent=False)
add_figure_caption(doc, 11,
    "Cross-chorus complexity comparison showing head is simpler than improvised choruses.")
add_empty_line(doc)




# Figure 12
add_empty_line(doc)
if 10 in img_paths:
    add_figure_image(doc, img_paths[10])
else:
    add_body(doc, "[Insert Figure 12: Head vs first improvised chorus complexity]", first_line_indent=False)
add_figure_caption(doc, 12,
    "Complexity of the composed head compared with the first improvised chorus, one point per "
    "tune. The horizontal axis is the index of the tune within the corpus, carrying no meaning "
    "beyond identifying each performance; the vertical axis is mean complexity.")
add_empty_line(doc)

# Figure 13
if 12 in img_paths:
    add_figure_image(doc, img_paths[12])
else:
    add_body(doc, "[Insert Figure 13: Autocorrelation profiles]", first_line_indent=False)
add_figure_caption(doc, 13,
    "Autocorrelation profiles demonstrating four improvisational strategies. \"My Little "
    "Suede Shoes\" (orange) maintains highest autocorrelation across all lags, suggesting trap-door "
    "structure with predictable mode persistence. Si Si (red) begins negative, revealing contrasting "
    "phrase organization. Cosmic Rays (purple) starts low-positive but decays negative, consistent "
    "with episodic exploratory structure. Barbados (green) shows moderate positive autocorrelation "
    "characteristic of balanced strategy.")
add_empty_line(doc)


doc.save(OUTPUT_PATH)
print(f"\nManuscript saved to: {OUTPUT_PATH}")
print("Done!")

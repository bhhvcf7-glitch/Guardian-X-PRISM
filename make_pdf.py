"""Render a six-page Arabic research report using PyMuPDF HTML text shaping."""
import re
from pathlib import Path
import fitz

folder = Path(__file__).resolve().parent
source = (folder / "report.html").read_text(encoding="utf-8")
sections = re.findall(r"<section(?:\s+[^>]*)?>(.*?)</section>", source, flags=re.S)
css = """
body {font-family: 'Noto Sans Arabic', sans-serif; direction:rtl; color:#173243; font-size:12px; line-height:1.8;}
h2 {font-size:26px;color:#0c4052;border-right:5px solid #16ac9e;padding-right:12px;margin:10px 0 20px;}
.section-num,.tag {font-size:10px;color:#10a997;letter-spacing:1px;font-weight:bold;}
.big {font-size:55px; font-weight:bold; margin-top:130px; color:#ffffff; line-height:1.35;}
.big span {color:#70e3d3;} .cover p {color:#d7f3f3;font-size:19px;margin-top:25px;}
.cover .tag {color:#a4ebde;} .cover .badge {color:#c1f9e9;border:1px solid #70c6bc;padding:9px;}
.lead {font-size:14px;color:#456676;line-height:2;}
.cards {margin-top:23px;} .card {background:#f0f7f8;border:1px solid #dbe9ed;border-radius:8px;padding:12px;margin-bottom:11px;}
.card b {font-size:14px;color:#0a7375}.card p {color:#4c707b;font-size:11px;}
.statrow {margin:20px 0;}.stat {display:inline-block;background:#e8f6f4;border:1px solid #c7e5e2;padding:10px 18px;margin-left:8px;border-radius:8px;}
.stat b {font-size:22px;color:#0b8077;direction:ltr;}.stat small {font-size:10px;color:#54727a;}
.formula {font-family:monospace;direction:ltr;text-align:left;background:#0b3145;color:#fff;padding:18px;font-size:13px;}
.note {background:#fff6e8;border-right:4px solid #e5ad5a;padding:12px;color:#855f2a;font-size:11px;}
table {border-collapse:collapse;width:100%;margin:20px 0;font-size:11px;}th {background:#0e5864;color:#fff;padding:10px;}td {border-bottom:1px solid #dce8ea;padding:10px;}
ul {font-size:13px;color:#466771;line-height:2;} .bottom,.foot {color:#8bb7bc;font-size:10px;margin-top:30px;}
"""
doc = fitz.open()
for i, section in enumerate(sections):
    page = doc.new_page(width=595, height=842)
    if i == 0:
        page.draw_rect(page.rect, color=None, fill=(0.035,0.16,0.23))
    clean = re.sub(r'<div class="stripe"></div>', '', section)
    html = f'<html><body class="{"cover" if i==0 else ""}">{clean}</body></html>'
    remaining, scale = page.insert_htmlbox(fitz.Rect(53, 54, 545, 794), html, css=css, scale_low=0.55)
    if remaining < 0:
        raise RuntimeError(f"Page {i+1} did not fit")
    if i == 2:
        # HTML layout engines disagree on RTL formula rendering; draw the equations explicitly.
        page.draw_rect(fitz.Rect(65, 220, 533, 315), color=None, fill=(0.045, .19, .27), overlay=True)
        for j, expression in enumerate(("ALLOW = 9000 x p", "VERIFY = 9000 x r x p + 40 x (1-p)", "BLOCK = 600 x (1-p)")):
            page.insert_text((85, 245+j*26), expression, fontsize=12, fontname="cour", color=(.91,.98,.97), overlay=True)
    if i:
        page.draw_line((52,805),(545,805),color=(.76,.85,.86),width=.5)
        page.insert_text((53,820),"GUARDIAN X / PRISM",fontsize=8,color=(.39,.58,.62))
        page.insert_text((529,820),f"{i+1:02}",fontsize=8,color=(.39,.58,.62))
output=folder / "PROJECT_REPORT.pdf"
doc.save(output, garbage=4, deflate=True)
print(f"Generated {output}, pages={len(doc)}")

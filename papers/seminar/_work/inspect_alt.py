import io
from pptx import Presentation
from pptx.oxml.ns import qn
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
M  = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
A  = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
out = io.open("papers/seminar/_work/july_alt.txt","w",encoding="utf-8")
prs = Presentation("papers/seminar/20260721_optcommrg_takamoto_v3_issl.pptx")
for i, s in enumerate(prs.slides, 1):
    tree = s.shapes._spTree
    alts = tree.findall(MC+"Altername") or tree.findall(MC+"AlternateContent")
    if not alts: continue
    out.write("\n=== Slide %d : %d AlternateContent\n" % (i, len(alts)))
    for j, alt in enumerate(alts):
        # position from fallback sp
        texts = [t.text for t in alt.iter(A+"t") if t.text]
        mtexts = [t.text for t in alt.iter(M+"t") if t.text]
        off = None
        for o in alt.iter(A+"off"):
            off = (int(o.get('x'))/914400, int(o.get('y'))/914400); break
        ext = None
        for e in alt.iter(A+"ext"):
            ext = (int(e.get('cx'))/914400, int(e.get('cy'))/914400); break
        names = [nv.get('name') for nv in alt.iter(A+"cNvPr")]
        out.write("  [%d] name=%s off=%s ext=%s\n" % (j, names[:1], off, ext))
        if mtexts: out.write("      MATH: %s\n" % "".join(mtexts)[:200])
        if texts:  out.write("      TXT : %s\n" % " | ".join(x for x in texts if x.strip())[:300])
out.close()
print(open("papers/seminar/_work/july_alt.txt",encoding="utf-8").read()[:200])

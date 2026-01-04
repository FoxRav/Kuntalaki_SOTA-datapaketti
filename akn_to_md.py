from pathlib import Path
from lxml import etree
import sys

def text1(el, name):
    x = el.xpath(f".//*[local-name()='{name}'][1]")
    return " ".join(x[0].itertext()).strip() if x else ""

def main(inp, outp):
    tree = etree.parse(inp)
    root = tree.getroot()

    body = root.xpath("//*[local-name()='body'][1]")
    if not body:
        raise SystemExit("BODY ei löytynyt (tiedosto voi olla metadataa tai rakenne poikkeaa).")
    body = body[0]

    lines = []

    title = root.xpath("//*[local-name()='docTitle']//*[local-name()='p'][1]")
    if title:
        lines.append("# " + " ".join(title[0].itertext()).strip())
        lines.append("")

    for node in body.iter():
        tag = etree.QName(node).localname
        if tag in ("chapter","part","book"):
            num = text1(node, "num"); head = text1(node, "heading")
            if num or head:
                lines += [f"## {num} {head}".strip(), ""]
        elif tag in ("section","article"):
            num = text1(node, "num"); head = text1(node, "heading")
            if num or head:
                lines += [f"### {num} {head}".strip(), ""]
        elif tag in ("paragraph","subsection"):
            num = text1(node, "num")
            txt = " ".join(node.itertext()).strip()
            if txt:
                if num and txt.startswith(num):
                    txt = txt[len(num):].strip()
                lines += [((f"**{num}** " if num else "") + txt), ""]

    Path(outp).write_text("\n".join(lines).strip() + "\n", encoding="utf-8-sig")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Käyttö: python akn_to_md.py <input_main.xml> <output.md>")
        raise SystemExit(2)
    main(sys.argv[1], sys.argv[2])

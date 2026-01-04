from pathlib import Path
from lxml import etree
import sys, re

def norm(s: str) -> str:
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def txt(node) -> str:
    return norm(" ".join(" ".join(node.itertext()).split()))

def first(node, name):
    x = node.xpath(f"./*[local-name()='{name}'][1]")
    return txt(x[0]) if x else ""

def md_heading(level, s):
    return f"{'#'*level} {s}".strip()

def render_list(listnode, out, indent=0):
    items = listnode.xpath("./*[local-name()='item']")
    for it in items:
        label = first(it, "label")
        ps = it.xpath("./*[local-name()='p']")
        head = txt(ps[0]) if ps else ""
        if not head:
            # fallback: kaikki teksti, mutta yritä välttää labelin toisto
            head = txt(it)
        line = f"{'  '*indent}- " + (f"**{label}** " if label else "") + head
        out.append(line)

        for sl in it.xpath("./*[local-name()='list']"):
            render_list(sl, out, indent=indent+1)
    out.append("")

def render_section(node, out):
    num = first(node, "num")
    heading = first(node, "heading")
    h = " ".join([x for x in [num, heading] if x])
    if h:
        out.append(md_heading(3, h))
        out.append("")

    # Vain suorat p:t ja listat (estää tuplia)
    for ch in node.xpath("./*"):
        ctag = etree.QName(ch).localname
        if ctag == "p":
            t = txt(ch)
            if t:
                out.append(t)
                out.append("")
        elif ctag == "list":
            render_list(ch, out, indent=0)

def render_container(node, out):
    tag = etree.QName(node).localname

    if tag in ("book","part","chapter"):
        num = first(node, "num")
        heading = first(node, "heading")
        h = " ".join([x for x in [num, heading] if x])
        if h:
            out.append(md_heading(2, h))
            out.append("")
        for ch in node.xpath("./*"):
            render_container(ch, out)
        return

    if tag in ("section","article"):
        render_section(node, out)
        return

    # muuten jatka alaspäin
    for ch in node.xpath("./*"):
        render_container(ch, out)

def main(inp, outp):
    tree = etree.parse(inp)
    root = tree.getroot()

    body = root.xpath("//*[local-name()='body'][1]")
    if not body:
        raise SystemExit("BODY ei löytynyt.")
    body = body[0]

    out = []

    title = root.xpath("//*[local-name()='docTitle']//*[local-name()='p'][1]")
    if title:
        out.append("# " + txt(title[0]))
        out.append("")

    for ch in body.xpath("./*"):
        render_container(ch, out)

    Path(outp).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8-sig")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Käyttö: python akn_to_md_v2.py <input_main.xml> <output.md>")
        raise SystemExit(2)
    main(sys.argv[1], sys.argv[2])

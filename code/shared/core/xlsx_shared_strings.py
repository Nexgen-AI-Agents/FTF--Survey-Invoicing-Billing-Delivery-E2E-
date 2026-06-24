"""xlsx_shared_strings.py — convert openpyxl's inline-string xlsx into a shared-string xlsx.

openpyxl (>=3.x) writes every text cell as an inline string (`t="inlineStr"` with an
`<is>` child) and emits NO `xl/sharedStrings.xml` part. Microsoft Graph's Excel
(workbook) REST API REJECTS such files: `createSession` and every `/workbook/*` call
returns HTTP 501 `UnsupportedWorkbook` / `FileCorruptTryRepair`. (Real Excel re-saving
the file fixes it by converting to a shared-string table — which is exactly why the
pipeline worked for months until an openpyxl-only rebuild upload left the file in the
inline-string state with no human ever re-opening it.)

`to_shared_strings(raw_bytes) -> bytes` post-processes the openpyxl output: it pulls
every inline string into a proper `xl/sharedStrings.xml` table, rewrites each cell to
`t="s"` with a `<v>index</v>`, and registers the new part in `[Content_Types].xml` and
the workbook relationships. Pure in-memory zip surgery; no Excel needed.
"""
from __future__ import annotations

import io
import re
import zipfile

_C_INLINE_RE = re.compile(r"<c\b([^>]*?)\bt=\"inlineStr\"([^>]*?)>(<is>.*?</is>)</c>", re.S)
_IS_UNWRAP_RE = re.compile(r"^<is>(.*)</is>$", re.S)
# Leftover empty inline cells openpyxl emits for "" values: <c .. t="inlineStr"></c>
# or self-closing <c .. t="inlineStr"/> with NO <is> child. After the real strings
# are pulled out, any remaining inlineStr type marker is on an empty cell — strip the
# type so the cell is a plain (blank) cell, which Graph accepts.
_C_EMPTY_INLINE_RE = re.compile(r'\s+t="inlineStr"')

_SST_CONTENT_TYPE = (
    '<Override PartName="/xl/sharedStrings.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'
    'sharedStrings+xml"/>'
)
_SST_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings"
)


def _convert_sheet(xml: str, table: list, index: dict) -> tuple[str, int, bool]:
    """Rewrite one worksheet's inline-string cells to shared-string references.

    table/index are mutated in place (shared across all sheets). Returns
    (new_xml, n_refs, changed): n_refs = string cells rewritten to shared refs;
    changed = whether the XML differs (refs rewritten OR empty inlineStr markers
    stripped) and the sheet therefore needs re-writing into the zip.
    """
    refs = 0

    def repl(m: re.Match) -> str:
        nonlocal refs
        pre, post, is_blob = m.group(1), m.group(2), m.group(3)
        inner = _IS_UNWRAP_RE.match(is_blob).group(1)  # children of <is> == children of <si>
        si = f"<si>{inner}</si>"
        idx = index.get(si)
        if idx is None:
            idx = len(table)
            index[si] = idx
            table.append(si)
        refs += 1
        attrs = (pre + post).rstrip()
        return f'<c{attrs} t="s"><v>{idx}</v></c>'

    new_xml = _C_INLINE_RE.sub(repl, xml)
    # strip any leftover inlineStr type markers (empty "" cells)
    new_xml = _C_EMPTY_INLINE_RE.sub("", new_xml)
    return new_xml, refs, (new_xml != xml)


def to_shared_strings(raw: bytes) -> bytes:
    """Return a copy of `raw` (an .xlsx) with all inline strings moved to a shared-string
    table. If the file already has a shared-string table or no inline strings, it is
    returned unchanged (idempotent — safe to call on any xlsx)."""
    zin = zipfile.ZipFile(io.BytesIO(raw))
    names = zin.namelist()

    if "xl/sharedStrings.xml" in names:
        return raw  # already shared-string; nothing to do

    table: list[str] = []
    index: dict[str, int] = {}
    total_refs = 0
    rewritten: dict[str, bytes] = {}

    for name in names:
        if re.match(r"xl/worksheets/sheet\d+\.xml$", name):
            xml = zin.read(name).decode("utf-8")
            new_xml, n, changed = _convert_sheet(xml, table, index)
            total_refs += n
            if changed:
                rewritten[name] = new_xml.encode("utf-8")

    if not table and not rewritten:
        return raw  # no inline strings at all — leave it alone

    add_sst = bool(table)
    ct = zin.read("[Content_Types].xml").decode("utf-8")
    rels = zin.read("xl/_rels/workbook.xml.rels").decode("utf-8")

    if add_sst:
        sst = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{total_refs}" uniqueCount="{len(table)}">'
            + "".join(table)
            + "</sst>"
        )
        if "sharedStrings.xml" not in ct:
            ct = ct.replace("</Types>", _SST_CONTENT_TYPE + "</Types>")
        existing_ids = re.findall(r'Id="rId(\d+)"', rels)
        next_id = max((int(i) for i in existing_ids), default=0) + 1
        rel = (
            f'<Relationship Id="rId{next_id}" Type="{_SST_REL_TYPE}" '
            'Target="sharedStrings.xml"/>'
        )
        rels = rels.replace("</Relationships>", rel + "</Relationships>")

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            if name == "[Content_Types].xml":
                zout.writestr(name, ct)
            elif name == "xl/_rels/workbook.xml.rels":
                zout.writestr(name, rels)
            elif name in rewritten:
                zout.writestr(name, rewritten[name])
            else:
                zout.writestr(name, zin.read(name))
        if add_sst:
            zout.writestr("xl/sharedStrings.xml", sst)

    return out.getvalue()

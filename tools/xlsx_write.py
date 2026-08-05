"""Minimal xlsx writer (stdlib only).

Supports multiple sheets, a bold frozen header row, autofilter, per-column
widths, wrapped text and hyperlinks. Enough for a report spreadsheet; not a
general-purpose implementation.
"""
import zipfile, re
from xml.sax.saxutils import escape

def _col(n):
    s = ''
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

# Excel rejects most control characters in shared strings.
_CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

def _clean(v):
    return _CTRL.sub('', v)

class Sheet:
    def __init__(self, name, headers, rows, widths=None, wrap_cols=(), link_cols=()):
        self.name = name
        self.headers = headers
        self.rows = rows
        self.widths = widths or []
        self.wrap_cols = set(wrap_cols)
        self.link_cols = set(link_cols)

def write(path, sheets):
    shared = {}
    order = []

    def sid(text):
        if text not in shared:
            shared[text] = len(order)
            order.append(text)
        return shared[text]

    sheet_xml = []
    for sh in sheets:
        cols = ''
        if sh.widths:
            parts = ''.join(
                f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>'
                for i, w in enumerate(sh.widths))
            cols = f'<cols>{parts}</cols>'

        body = []
        hdr = ''.join(
            f'<c r="{_col(i)}1" t="s" s="1"><v>{sid(_clean(str(h)))}</v></c>'
            for i, h in enumerate(sh.headers))
        body.append(f'<row r="1" ht="30" customHeight="1">{hdr}</row>')

        for ri, row in enumerate(sh.rows, start=2):
            cells = []
            for ci, val in enumerate(row):
                ref = f'{_col(ci)}{ri}'
                if val is None or val == '':
                    continue
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    cells.append(f'<c r="{ref}"><v>{val}</v></c>')
                else:
                    style = 2 if ci in sh.wrap_cols else 0
                    cells.append(
                        f'<c r="{ref}" t="s" s="{style}">'
                        f'<v>{sid(_clean(str(val)))}</v></c>')
            body.append(f'<row r="{ri}">{"".join(cells)}</row>')

        last = _col(len(sh.headers) - 1)
        dim = f'A1:{last}{len(sh.rows) + 1}'
        sheet_xml.append(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<dimension ref="{dim}"/>'
            '<sheetViews><sheetView workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
            '</sheetView></sheetViews>'
            '<sheetFormatPr defaultRowHeight="15"/>'
            f'{cols}<sheetData>{"".join(body)}</sheetData>'
            f'<autoFilter ref="{dim}"/>'
            '</worksheet>')

    sst = ''.join(f'<si><t xml:space="preserve">{escape(t)}</t></si>' for t in order)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(order)}" uniqueCount="{len(order)}">{sst}</sst>')

    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
        '</fonts>'
        '<fills count="3">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid">'
        '<fgColor rgb="FF1F3864"/><bgColor indexed="64"/></patternFill></fill>'
        '</fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="3">'
        '<xf xfId="0"><alignment vertical="top"/></xf>'
        '<xf xfId="0" fontId="1" fillId="2" applyFont="1" applyFill="1" applyAlignment="1">'
        '<alignment vertical="center" wrapText="1"/></xf>'
        '<xf xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '</cellXfs>'
        '</styleSheet>')

    tabs = ''.join(
        f'<sheet name="{escape(sh.name)}" sheetId="{i+1}" r:id="rId{i+1}"/>'
        for i, sh in enumerate(sheets))
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{tabs}</sheets></workbook>')

    rels = ''.join(
        f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>'
        for i in range(len(sheets)))
    n = len(sheets)
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{rels}'
        f'<Relationship Id="rId{n+1}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
        f'<Relationship Id="rId{n+2}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>')

    overrides = ''.join(
        f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/'
        f'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(len(sheets)))
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f'{overrides}'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/'
        'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>')

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
        '2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')

    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', content_types)
        z.writestr('_rels/.rels', root_rels)
        z.writestr('xl/workbook.xml', workbook)
        z.writestr('xl/_rels/workbook.xml.rels', wb_rels)
        z.writestr('xl/sharedStrings.xml', shared_xml)
        z.writestr('xl/styles.xml', styles)
        for i, x in enumerate(sheet_xml):
            z.writestr(f'xl/worksheets/sheet{i+1}.xml', x)

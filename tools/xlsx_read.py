import sys, zipfile, re
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NSR = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def col_to_idx(ref):
    m = re.match(r'([A-Z]+)', ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1

def read(path):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in root.findall(f'{NS}si'):
            shared.append(''.join(t.text or '' for t in si.iter(f'{NS}t')))

    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rmap = {r.get('Id'): r.get('Target') for r in rels}

    sheets = []
    for sh in wb.find(f'{NS}sheets'):
        name = sh.get('name')
        target = rmap[sh.get(f'{NSR}id')]
        if not target.startswith('xl/'):
            target = 'xl/' + target.lstrip('/')
        sheets.append((name, target))

    out = {}
    for name, target in sheets:
        root = ET.fromstring(z.read(target))
        rows = []
        for row in root.iter(f'{NS}row'):
            cells = {}
            for c in row.findall(f'{NS}c'):
                ref = c.get('r') or ''
                t = c.get('t')
                v = c.find(f'{NS}v')
                isel = c.find(f'{NS}is')
                if t == 's' and v is not None:
                    val = shared[int(v.text)]
                elif t == 'inlineStr' and isel is not None:
                    val = ''.join(x.text or '' for x in isel.iter(f'{NS}t'))
                elif v is not None:
                    val = v.text
                else:
                    val = ''
                cells[col_to_idx(ref)] = (val or '').strip()
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, '') for i in range(width)])
            else:
                rows.append([])
        out[name] = rows
    return out

if __name__ == '__main__':
    data = read(sys.argv[1])
    for name, rows in data.items():
        print(f'===== SHEET: {name}  ({len(rows)} rows) =====')
        for i, r in enumerate(rows):
            print(f'{i}\t' + '\t|\t'.join(r))

#!/usr/bin/env python3
"""Render the discussion map with stdlib PDF/PNG writing and pdftoppm.

This is a documentation helper, not DML code. Labels/layout mirror design-map.md.
"""
from pathlib import Path
import math
import struct
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
W, H = 1100, 1020
pages = []
ops = []


def color(c):
    return ' '.join(str(int(c[i:i + 2], 16) / 255) for i in (0, 2, 4))


def rect(x, y, w, h, fill='FFFFFF', stroke='CBD5E1'):
    ops.append(f'{color(fill)} rg {color(stroke)} RG 1 w {x} {H-y-h} {w} {h} re B')


def text(x, y, s, size=13, font='F1', c='1E293B'):
    s = s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    ops.append(f'BT /{font} {size} Tf {color(c)} rg 1 0 0 1 {x} {H-y} Tm ({s}) Tj ET')


def box(x, y, w, h, title, lines, fill='F8FAFC', accent='334155'):
    rect(x, y, w, h, fill)
    rect(x, y, w, 5, accent, accent)
    text(x + 14, y + 29, title, 16, 'F2')
    for i, s in enumerate(lines):
        text(x + 14, y + 52 + i * 18, s, 12)


def arrow(points, label=None, lx=0, ly=0, dashed=False):
    ops.append(f'{color("64748B")} RG {color("64748B")} rg 1.6 w ' +
               ('[5 4] 0 d' if dashed else '[] 0 d'))
    ops.append(f'{points[0][0]} {H-points[0][1]} m ' +
               ' '.join(f'{x} {H-y} l' for x, y in points[1:]) + ' S')
    x, y = points[-1]
    px, py = points[-2]
    a = math.atan2(y - py, x - px)
    p1 = (x - 9 * math.cos(a) + 4 * math.sin(a), y - 9 * math.sin(a) - 4 * math.cos(a))
    p2 = (x - 9 * math.cos(a) - 4 * math.sin(a), y - 9 * math.sin(a) + 4 * math.cos(a))
    ops.append(f'{x} {H-y} m {p1[0]} {H-p1[1]} l {p2[0]} {H-p2[1]} l h f [] 0 d')
    if label:
        text(lx, ly, label, 11, c='475569')


def start(title, subtitle):
    ops.clear()
    rect(0, 0, W, H, 'FFFFFF', 'FFFFFF')
    text(45, 42, title, 25, 'F2')
    text(45, 67, subtitle, 13)
    text(45, 89, 'DISCUSSION DRAFT | Arrows = references unless labeled as exchange/process. Dashed = provisional.', 12, c='475569')


def end(footer):
    text(45, 995, footer, 12, c='475569')
    pages.append('\n'.join(ops).encode('ascii'))


# Page 1: the storage backbone, not a new packed schema.
start('1. Repository and storage entities', 'The storage layer holds the ordinary DAG data used for computational roles on page 2.')
box(405, 120, 300, 112, 'Repository', ['Object store + refs + metadata', 'Repository identity: no facet selected', 'Storage schema remains separate'])
box(45, 120, 260, 112, 'Repository metadata', ['Schema / tool metadata', 'Existing object-model context', 'Not assumed to be research state'])
box(800, 120, 255, 112, 'Remote + repository IO', ['Exchange locator / adapter binding', 'Transfers objects and refs', 'Not automatically a cache dimension'])
box(405, 290, 300, 112, 'Refs / heads / index', ['Mutable scoped names -> commits', 'Tracking / execution refs as needed', 'Not content-addressed facets'])
box(45, 290, 260, 112, 'Tombstone / excision marker', ['Withdrawal at an object reference', 'Not the original sensitive content', 'Exact new semantics OPEN'], fill='FFF7ED', accent='EA580C')
box(800, 290, 255, 112, 'Caller / callee repositories', ['May hold their own local copies', 'Push / fetch through shared remote', 'Actors are not storage object kinds'])
box(405, 460, 300, 112, 'Commit', ['RECORD / content identity', 'Tree + parents + versioned state', 'Not a blanket computation key'])
box(45, 460, 260, 112, 'Parent commit(s)', ['Full rooted history is retained', 'RECORD / content identity', 'Reachability matters to GC'])
box(800, 460, 255, 112, 'Versioned research state', ['Requests, attempts, reuse selections', 'Observations and lifecycle evidence', 'Exact placement in DAGs OPEN'], fill='EFF6FF', accent='2563EB')
box(405, 630, 300, 112, 'Tree', ['RECORD / content identity', 'Named entries -> DAGs', 'No additional facet selected'])
box(405, 800, 300, 112, 'DAG / sub-DAG', ['RECORD / content identity', 'Root + optional named-node bindings', 'Names do not enumerate every node'])
box(45, 800, 260, 112, 'Node', ['RECORD facet; REUSE where needed', 'Inputs / dependencies -> other nodes', 'Primitive or sub-DAG relationship'])
box(800, 800, 255, 112, 'Datum', ['RECORD / content identity', 'Scalar / bytes / URI / collection', 'Collections -> other datums'])
arrow([(405, 170), (305, 170)])
arrow([(705, 175), (800, 175)], 'push / fetch', 719, 163)
arrow([(555, 232), (555, 290)])
arrow([(405, 205), (350, 205), (350, 345), (305, 345)], dashed=True)
arrow([(925, 290), (925, 232)], 'exchange', 936, 266)
arrow([(555, 402), (555, 460)])
arrow([(405, 515), (305, 515)], 'parents', 330, 504)
arrow([(705, 515), (800, 515)], 'records', 728, 504, dashed=True)
arrow([(555, 572), (555, 630)])
arrow([(555, 742), (555, 800)], 'named entries', 566, 777)
arrow([(405, 845), (305, 845)], 'root / names', 312, 833)
arrow([(170, 912), (170, 947), (925, 947), (925, 912)], 'literal / configuration data', 446, 938)
arrow([(290, 870), (330, 870), (330, 900), (405, 900)], dashed=True)
text(318, 923, 'sub-DAG link OPEN', 10)
end('Backbone from the existing draft; node taxonomy and exec pinning are context, not constraints on this exploration.')

# Page 2: computational roles, represented in the page-1 structure.
start('2. Computational roles and identity facets', 'These are conceptual roles in ordinary nodes / datums / DAGs, not an approved set of dedicated record types.')
blue = '2563EB'
box(45, 120, 260, 118, 'Captured dependencies', ['Named bindings to actual nodes', 'Record / content identity', 'Names are scoped lookup labels'], accent=blue)
box(405, 120, 300, 118, 'Intent definition', ['Stable intent URI + versioned definition', 'Captures dependency nodes', 'Record identity; URI is not a cache key'], accent=blue)
box(800, 120, 255, 118, 'Implementation + adapter', ['Recorded references / bindings', 'Record identity', 'URI alone need not fix external bytes'], accent=blue)
box(45, 300, 260, 118, 'Explicit arguments', ['Named bindings to input nodes', 'Record / content identity', 'lookup(argument_dag, name)'], accent=blue)
box(405, 300, 300, 118, 'Bound closure', ['Intent + implementation + adapter', 'Configuration + resource bindings', 'Record identity; no extra facet chosen'], accent=blue)
box(800, 300, 255, 118, 'Resources / configuration', ['Declared executable bindings', 'Record identity', 'External ownership / identity separate'], accent=blue)
box(405, 485, 300, 120, 'Execution description node', ['Selected closure + named arguments', 'RECORD facet: all dimensions + mask', 'REUSE facet: masked dimensions'], fill='EFF6FF', accent=blue)
box(800, 485, 255, 120, 'Facet rules / masks', ['Sentinel = deliberately ignored', 'Mask contributes to record identity', 'Rule ownership / defaults OPEN'], fill='FFF7ED', accent='EA580C')
box(45, 690, 260, 120, 'Request Q', ['Record identity + occurrence ID', 'Records selected description', 'Fresh attempt OR historical reuse'], fill='F0FDF4', accent='16A34A')
box(405, 690, 300, 120, 'Attempt A', ['Record versions + occurrence ID', 'Preserves its actual binding', 'Progress / outcome records refer to A'], fill='F0FDF4', accent='16A34A')
box(800, 690, 255, 120, 'Result sub-DAG', ['Minimal datum or detailed computation', 'Content identity can deduplicate', 'Equal results do not merge attempts'], fill='F0FDF4', accent='16A34A')
arrow([(405, 178), (305, 178)])
arrow([(555, 300), (555, 238)])
arrow([(705, 325), (748, 325), (748, 180), (800, 180)])
arrow([(705, 360), (800, 360)])
arrow([(405, 330), (350, 330), (350, 220), (305, 220)], dashed=True)
text(310, 281, 'optional closure capture', 10, c='64748B')
arrow([(555, 485), (555, 418)])
arrow([(405, 545), (330, 545), (330, 360), (305, 360)], 'arguments', 315, 462)
arrow([(705, 545), (800, 545)], dashed=True)
arrow([(305, 720), (350, 720), (350, 575), (405, 575)], 'requested binding', 225, 665)
arrow([(305, 760), (405, 760)], 'fresh / reuse', 311, 750)
arrow([(555, 690), (555, 605)], 'actual binding', 566, 648)
arrow([(705, 750), (800, 750)], 'outcome', 724, 738)
rect(45, 857, 1010, 118, 'F1F5F9')
text(60, 884, 'PUBLICATION: caller <-> DML remote <-> callee / execution adapter', 17, 'F2')
text(60, 909, 'exec/<attempt-id> -> commit -> tree -> execution working DAG (inputs + progress + result)', 14)
text(60, 932, 'Refs advance; commit history remains recorded. Ref convention, writer protocol and completion are OPEN.', 12)
text(60, 954, 'The adapter handles launch/recovery; a non-DML process has its result wrapped into a DAG.', 12)
end('Record E1 != record E2 can coexist with reuse E1 = reuse E2. Matching facets never merge occurrence IDs.')

# Page 3: all remaining discussed roles, without expanding the core schema.
start('3. History, installation and resource lifecycle', 'Supporting roles also use versioned DAG data. Process arrows are labeled; physical effects are not repository facts.')
box(45, 120, 260, 118, 'Reuse selection', ['Versioned branch / commit state', 'Reuse key -> selected attempt', 'Record identity; not a new trial'], accent=blue)
box(405, 120, 300, 118, 'Attempt / installation attempt', ['Distinct occurrence IDs', 'Many record versions about one event', 'Unknown outcomes remain possible'], fill='F0FDF4', accent='16A34A')
box(800, 120, 255, 118, 'Progress / outcome / cleanup', ['Versioned observations about attempt', 'working / done != success / failure', 'Cleanup outcome is separate'], accent=blue)
box(45, 310, 260, 118, 'Installation description', ['Implementation + adapter + HCL', 'Configuration inputs / dependencies', 'Record identity; installation tentative'], accent=blue)
box(405, 310, 300, 118, 'Resulting bound closure', ['Record / content identity', 'Binds realized resources', 'Same closure from distinct installations'], accent=blue)
box(800, 310, 255, 118, 'Lifecycle / validation evidence', ['Deprecations / successors / checks', 'Versioned DAG records / relationships', 'Not automatically cache dimensions'], accent=blue)
box(45, 500, 260, 118, 'Disposal / retirement / excision', ['Versioned requests and observations', 'GC unreachable; excision authorized', 'Request != completed physical deletion'], fill='FFF7ED', accent='EA580C')
box(405, 500, 300, 118, 'Resource datum / obligation', ['Recorded description / binding identity', 'Owner, locator, retention associations', 'Keep cleanup custody until resolved'], accent=blue)
box(800, 500, 255, 118, 'External resource', ['Provider / authority-specific identity', 'Bytes, code, dataset or infrastructure', 'Not necessarily immutable / available'], fill='FFF7ED', accent='EA580C')
box(405, 690, 300, 118, 'IaC Git view + manager state', ['Backend-specific config/state identities', 'Config materialized from obligations', 'Registration / apply / effects separate'], fill='FFF7ED', accent='EA580C')
box(45, 690, 260, 118, 'Experiment Git / run context', ['Orchestration code and Git association', 'Recorded context, not full dependency set', 'Not an automatic global cache key'])
box(800, 690, 255, 118, 'Deployment tools / workflows', ['User / agent chooses deployment', 'Actors/tools, not core identity facets', 'No selected CI backend'])
arrow([(305, 180), (405, 180)], 'selects', 327, 169)
arrow([(800, 180), (705, 180)], 'about', 735, 169)
arrow([(460, 238), (460, 272), (170, 272), (170, 310)], 'installation uses', 235, 263)
arrow([(555, 238), (555, 310)], 'records result', 566, 274)
arrow([(555, 428), (555, 500)])
arrow([(800, 368), (705, 368)], 'about', 735, 357, dashed=True)
arrow([(305, 555), (405, 555)], 'addresses', 318, 544)
arrow([(705, 555), (800, 555)], 'locator', 732, 544)
arrow([(555, 690), (555, 618)], 'materialized from', 566, 655, dashed=True)
arrow([(800, 748), (705, 748)], 'applies', 731, 737)
rect(45, 854, 1010, 120, 'F1F5F9')
text(60, 881, 'Ordinary consumers and actors: researcher / caller / driver / callee / sidecar observer', 16, 'F2')
text(60, 906, 'They read/build/publish through repositories, refs, commits, trees, DAGs, nodes and datums (page 1).', 13)
text(60, 929, 'Observers need no special registry or mandatory capture channel. Details are whatever the producer records.', 12)
text(60, 952, 'No extra identity facet is proposed for a role simply because it appears in this picture.', 12)
end('Historical dedicated exec/exec_request records are context only; they are not equated with this occurrence model.')

# Portable PDF: built-in Helvetica fonts, no external font dependencies.
objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
           b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
           b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>']
page_ids = []
for stream in pages:
    page_id = len(objects) + 1
    content_id = page_id + 1
    page_ids.append(page_id)
    objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>'.encode())
    objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream')
objects[1] = f'<< /Type /Pages /Kids [{" ".join(f"{i} 0 R" for i in page_ids)}] /Count {len(pages)} >>'.encode()
out = bytearray(b'%PDF-1.4\n')
offsets = [0]
for i, obj in enumerate(objects, 1):
    offsets.append(len(out))
    out.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
xref = len(out)
out.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
for off in offsets[1:]:
    out.extend(f'{off:010d} 00000 n \n'.encode())
out.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
pdf = ROOT / 'design-map.pdf'
pdf.write_bytes(out)


def read_ppm(path):
    data = path.read_bytes()
    pos, tokens = 0, []
    while len(tokens) < 4:
        while data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b'#':
            pos = data.index(b'\n', pos) + 1
            continue
        end = pos
        while not data[end:end + 1].isspace():
            end += 1
        tokens.append(data[pos:end])
        pos = end
    assert tokens[0] == b'P6' and tokens[3] == b'255'
    # The final header separator is one whitespace byte (pdftoppm emits LF).
    payload = data[pos + 1:]
    width, height = int(tokens[1]), int(tokens[2])
    assert len(payload) == width * height * 3
    return width, height, payload


def chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)


with tempfile.TemporaryDirectory(prefix='dml-map-') as temp:
    prefix = Path(temp) / 'page'
    subprocess.run(['pdftoppm', '-scale-to', '1600', str(pdf), str(prefix)], check=True)
    images = [read_ppm(p) for p in sorted(Path(temp).glob('page-*.ppm'))]
    assert len(images) == len(pages)
    width = images[0][0]
    assert all(w == width for w, _, _ in images)
    height = sum(h for _, h, _ in images)
    compressor = zlib.compressobj(9)
    compressed = bytearray()
    for _, h, data in images:
        for row in range(h):
            compressed.extend(compressor.compress(b'\x00' + data[row * width * 3:(row + 1) * width * 3]))
    compressed.extend(compressor.flush())
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    (ROOT / 'design-map.png').write_bytes(png)
print('Rendered design-map.pdf (3 pages) and design-map.png (all pages stacked).')

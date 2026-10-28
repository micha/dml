"""Check the offline diagram's storage scope and repository-local references."""

import pathlib
import re
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit


ROOT = pathlib.Path(__file__).resolve().parents[2]
DIAGRAM = ROOT / "docs" / "lmdb-entity-diagram.html"


class DiagramParser(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.links: list[str] = []
    self.external_resources: list[str] = []
    self.edges: set[tuple[str, str]] = set()

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    attributes = dict(attrs)
    if tag == "a":
      self.links.append(attributes["href"] or "")
    if tag in {"script", "img", "link", "iframe", "use", "image"}:
      for key in ("src", "href", "xlink:href"):
        if attributes.get(key):
          self.external_resources.append(attributes[key])
    if "data-from" in attributes:
      self.edges.add((attributes["data-from"], attributes["data-to"]))


def test_diagram_shows_only_implemented_key_families_and_direct_edges() -> None:
  html = DIAGRAM.read_text(encoding="utf-8")
  parser = DiagramParser()
  parser.feed(html)
  keys = re.findall(r"key: '([^']+)'", html)
  expected = {
    "meta/schema", "refs/heads/<name>", "objects/commits/<id>",
    "objects/trees/<id>", "objects/dags/<id>", "objects/nodes/<id>", "objects/datums/<id>",
  }
  assert len(keys) == len(expected)
  assert set(keys) == expected
  implementation = (ROOT / "src" / "repo.c").read_text(encoding="utf-8")
  for key in keys:
    prefix = key.split("<")[0]
    assert f'"{prefix}"' in implementation
  assert parser.edges == {
    ("ref", "commit"), ("commit", "tree"), ("commit", "commit"),
    ("tree", "dag"), ("dag", "node"), ("node", "dag"),
    ("node", "datum"), ("datum", "datum"),
  }


def test_diagram_is_self_contained_with_valid_authority_links() -> None:
  html = DIAGRAM.read_text(encoding="utf-8")
  parser = DiagramParser()
  parser.feed(html)
  assert not parser.external_resources
  assert "@import" not in html and "url(http" not in html
  links = parser.links + [
    f"spec-next/{source}" for source in re.findall(r"source: '([^']+)'", html)
  ]
  assert links
  for link in links:
    parsed = urlsplit(link)
    assert not parsed.scheme and not parsed.netloc
    target = DIAGRAM.parent / unquote(parsed.path)
    assert target.is_file(), link
    if parsed.fragment:
      headings = re.findall(r"^#+ (.+)$", target.read_text(encoding="utf-8"), re.MULTILINE)
      anchors = {re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-") for heading in headings}
      assert parsed.fragment in anchors, link


def test_diagram_marks_body_identity_only_for_immutable_objects() -> None:
  html = DIAGRAM.read_text(encoding="utf-8")
  annotations = re.findall(r"\{ id: '([^']+)', hashedFields: (true|false)", html)
  assert len(annotations) == 7
  assert {name for name, hashed in annotations if hashed == "true"} == {
    "datum", "node", "dag", "tree", "commit",
  }
  assert {name for name, hashed in annotations if hashed == "false"} == {"ref", "schema"}
  assert "◆ Field hashed into content ID" in html
  assert "— No content-addressed ID" in html
  assert "entity.hashedFields ? '◆' : '—'" in html
  assert "not a computational reuse identity" in html


def test_diagram_envelope_identity_matches_native_zeroing() -> None:
  html = DIAGRAM.read_text(encoding="utf-8")
  annotations = re.findall(
    r"\{ field: '[^']*\(u(16|32), byte (\d+)[^']*', hashed: (true|false) \}", html
  )
  assert len(annotations) == 6
  included = {(int(offset), int(bits) // 8) for bits, offset, hashed in annotations if hashed == "true"}
  zeroed = {(int(offset), int(bits) // 8) for bits, offset, hashed in annotations if hashed == "false"}
  assert included == {(4, 2), (6, 2), (12, 4)}
  implementation = (ROOT / "src" / "object_id.c").read_text(encoding="utf-8")
  native_zeroed = {
    (int(offset or 0), int(width))
    for offset, width in re.findall(r"memset\(masked(?: \+ (\d+))?, 0, (\d+)\)", implementation)
  }
  assert zeroed == native_zeroed == {(0, 4), (8, 4), (16, 4)}
  assert "XXH3_128bits(masked, len)" in implementation
  assert "zeroed, not omitted" in html

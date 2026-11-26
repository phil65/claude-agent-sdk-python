"""Structured diff between two versions of the SDK TypeScript declaration files.

Instead of a raw line diff, this parses top-level declarations (types, interfaces,
functions, classes, ...) and reports, per declaration:

- declarations that were added / removed
- object members (fields / methods) that were added / removed / changed
- union variants that were added / removed (e.g. string literal unions)

Usage:
    # Compare two files
    python scripts/diff_sdk_reference.py old/sdk.d.ts new/sdk.d.ts

    # Compare the working-tree reference files against a git revision
    python scripts/diff_sdk_reference.py --git-rev HEAD

    # Write the report to a file as well
    python scripts/diff_sdk_reference.py --git-rev HEAD -o reference/CHANGES.md
"""

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
import sys


PROJECT_ROOT = Path(__file__).parent.parent
REFERENCE_DIR = PROJECT_ROOT / "reference"
REFERENCE_FILES = ["sdk.d.ts", "sdk-tools.d.ts"]

_OPEN = "{(["
_CLOSE = "})]"

_DECL_RE = re.compile(
    r"^(?:export\s+)?(?:declare\s+)?(?:abstract\s+)?"
    r"(?P<kind>type|interface|class|function|const|let|var|enum|namespace|module)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)"
)
_MEMBER_KEY_RE = re.compile(
    r"^(?:readonly\s+|static\s+|private\s+|protected\s+|public\s+|abstract\s+)*"
    r"(?P<key>\[[^\]]*\]|['\"][^'\"]*['\"]|[A-Za-z_$][\w$]*)\s*(?P<opt>\?)?\s*(?P<sep>[:(<])?"
)


# ---------------------------------------------------------------------------
# Lexing helpers
# ---------------------------------------------------------------------------


def strip_comments(src: str) -> str:
    """Remove // and /* */ comments while leaving string literals intact."""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i : j + 1])
            i = j + 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j == -1 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j == -1 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _split_top(src: str, seps: str, *, angles: bool = True) -> list[str]:
    """Split on separator chars at bracket depth 0 (string-aware).

    A closing `}` returning to depth 0 also ends a chunk when "}" is in seps
    (needed for `interface X {...}` declarations without trailing semicolons).
    """
    parts: list[str] = []
    depth = 0
    start = 0
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue
        if c in _OPEN or (c == "<" and angles):
            depth += 1
        elif c in _CLOSE or (c == ">" and angles and src[i - 1] != "="):
            depth -= 1
            if depth == 0 and c == "}" and "}" in seps:
                # Only end the statement if what follows is not a continuation
                rest = src[i + 1 :].lstrip()
                if not rest or not re.match(r"^[|&\[.;,)>]|^extends\b", rest):
                    parts.append(src[start : i + 1])
                    start = i + 1
        elif depth == 0 and c in seps and c != "}":
            parts.append(src[start:i])
            start = i + 1
        i += 1
    parts.append(src[start:])
    return [p.strip() for p in parts if p.strip()]


def _norm(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*([{}()\[\]<>,;:|&=?])\s*", r"\1", s)
    return s.rstrip(";,")


def _strip_outer(s: str, open_c: str, close_c: str) -> str | None:
    """Return inner text if `s` is entirely wrapped in one bracket pair."""
    s = s.strip()
    if not (s.startswith(open_c) and s.endswith(close_c)):
        return None
    depth = 0
    for i, c in enumerate(s):
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth -= 1
            if depth == 0 and i != len(s) - 1:
                return None
    return s[1:-1]


# ---------------------------------------------------------------------------
# Declaration model
# ---------------------------------------------------------------------------


@dataclass
class Decl:
    kind: str
    name: str
    raw: str
    members: dict[str, str] | None = None
    union: list[str] | None = None
    heads: list[str] = field(default_factory=list)  # e.g. "extends Foo", intersections

    @property
    def signature(self) -> str:
        return _norm(self.raw)


def _parse_members(body: str) -> dict[str, str]:
    members: dict[str, str] = {}
    for raw_part in _split_top(body, ";,"):
        part = raw_part.strip()
        m = _MEMBER_KEY_RE.match(part)
        key = m.group("key") if m else part
        if m and m.group("sep") in ("(", "<"):
            # method signature; allow overloads
            base = key + "()"
            key = base
            k = 2
            while key in members:
                key = f"{base}#{k}"
                k += 1
        elif m and m.group("opt"):
            key += "?"
        members[key] = _norm(part)
    return members


def _analyse_type_body(rhs: str, decl: Decl) -> None:
    rhs = rhs.strip()
    inner = _strip_outer(rhs, "{", "}")
    if inner is not None:
        decl.members = _parse_members(inner)
        return
    variants = _split_top(rhs, "|")
    if len(variants) > 1:
        decl.union = sorted(_norm(v) for v in variants)
        return
    # Intersection with object literal(s): A & B & { ... }
    pieces = _split_top(rhs, "&")
    if len(pieces) > 1:
        members: dict[str, str] = {}
        for p in pieces:
            inner = _strip_outer(p, "{", "}")
            if inner is not None:
                members.update(_parse_members(inner))
            else:
                decl.heads.append("& " + _norm(p))
        if members:
            decl.members = members


def parse_declarations(src: str, prefix: str = "") -> dict[str, Decl]:
    """Parse top-level declarations from a .d.ts source."""
    decls: dict[str, Decl] = {}
    src = strip_comments(src)
    for raw_stmt in _split_top(src, ";}", angles=False):
        stmt = raw_stmt.strip()
        if stmt.startswith(("import ", "export {", "export *", "export default", "export =")):
            continue
        m = _DECL_RE.match(stmt)
        if not m:
            continue
        kind, name = m.group("kind"), prefix + m.group("name")
        rest = stmt[m.end() :]

        if kind in ("namespace", "module"):
            brace = rest.find("{")
            if brace != -1:
                inner = _strip_outer(rest[brace:], "{", "}")
                if inner is not None:
                    decls.update(parse_declarations(inner, prefix=name + "."))
            continue

        key = name
        if kind == "function" and key in decls:
            k = 2
            while f"{name}#{k}" in decls:
                k += 1
            key = f"{name}#{k}"
        decl = Decl(kind=kind, name=key, raw=stmt)

        if kind == "type":
            # first "=" at depth 0 separates name/generics from the body
            idx = _find_top_eq(rest)
            if idx is not None:
                _analyse_type_body(rest[idx + 1 :], decl)
        elif kind in ("interface", "class"):
            brace = _find_top_brace(rest)
            if brace is not None:
                head = rest[:brace].strip()
                if head:
                    decl.heads.append(_norm(head))
                inner = _strip_outer(rest[brace:], "{", "}")
                if inner is not None:
                    decl.members = _parse_members(inner)
        decls[key] = decl
    return decls


def _find_top_eq(s: str) -> int | None:
    depth = 0
    for i, c in enumerate(s):
        if c in _OPEN or c == "<":
            depth += 1
        elif c in _CLOSE or (c == ">" and s[i - 1] != "="):
            depth -= 1
        elif c == "=" and depth == 0 and s[i + 1 : i + 2] != ">":
            return i
    return None


def _find_top_brace(s: str) -> int | None:
    depth = 0
    for i, c in enumerate(s):
        if c == "{" and depth == 0:
            return i
        if c in "([<":
            depth += 1
        elif c in ")]>":
            depth -= 1
    return None


# ---------------------------------------------------------------------------
# Diffing / reporting
# ---------------------------------------------------------------------------


def _short(s: str, limit: int = 160) -> str:
    return s if len(s) <= limit else s[: limit - 1] + "…"


def diff_decls(old: dict[str, Decl], new: dict[str, Decl]) -> list[str]:
    lines: list[str] = []
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    common = sorted(set(old) & set(new))

    if added:
        lines.append(f"### Added ({len(added)})")
        lines.append("")
        for name in added:
            d = new[name]
            lines.append(f"- `{d.kind} {name}`")
            if d.members:
                lines.extend(f"    - `{_short(v)}`" for v in d.members.values())
            elif d.union:
                lines.append(f"    - `{_short(' | '.join(d.union), 400)}`")
            else:
                lines.append(f"    - `{_short(d.signature, 400)}`")
        lines.append("")

    if removed:
        lines.append(f"### Removed ({len(removed)})")
        lines.append("")
        lines.extend(f"- `{old[n].kind} {n}`" for n in removed)
        lines.append("")

    changed: list[str] = []
    for name in common:
        o, n = old[name], new[name]
        if o.signature == n.signature:
            continue
        entry: list[str] = [f"- `{n.kind} {name}`"]
        if o.heads != n.heads:
            entry.append(f"    - heritage: `{' '.join(o.heads)}` → `{' '.join(n.heads)}`")
        if o.members is not None and n.members is not None:
            om, nm = o.members, n.members

            # Match keys ignoring optionality to detect "became optional/required"
            def base(k: str) -> str:
                return k.rstrip("?")

            obase = {base(k): k for k in om}
            nbase = {base(k): k for k in nm}
            entry.extend(
                f"    - `+` `{_short(nm[nbase[b]])}`" for b in sorted(set(nbase) - set(obase))
            )
            entry.extend(
                f"    - `-` `{_short(om[obase[b]])}`" for b in sorted(set(obase) - set(nbase))
            )
            for b in sorted(set(obase) & set(nbase)):
                ov, nv = om[obase[b]], nm[nbase[b]]
                if ov != nv:
                    entry.append(f"    - `~` `{_short(ov)}` → `{_short(nv)}`")
        elif o.union is not None and n.union is not None:
            entry.extend(f"    - `+` `{_short(v)}`" for v in sorted(set(n.union) - set(o.union)))
            entry.extend(f"    - `-` `{_short(v)}`" for v in sorted(set(o.union) - set(n.union)))
        if len(entry) == 1:
            entry.append(f"    - old: `{_short(o.signature, 300)}`")
            entry.append(f"    - new: `{_short(n.signature, 300)}`")
        changed.extend(entry)

    if changed:
        count = sum(1 for e in changed if e.startswith("- "))
        lines.append(f"### Changed ({count})")
        lines.append("")
        lines.extend(changed)
        lines.append("")

    if not lines:
        lines.append("_No declaration changes._")
        lines.append("")
    return lines


def build_report(
    pairs: list[tuple[str, str, str]], old_version: str | None, new_version: str | None
) -> str:
    """Build a markdown report. `pairs` is a list of (filename, old_src, new_src)."""
    title = "# SDK reference changes"
    if old_version or new_version:
        title += f": {old_version or '?'} → {new_version or '?'}"
    out = [title, ""]
    for filename, old_src, new_src in pairs:
        out.append(f"## {filename}")
        out.append("")
        out.extend(diff_decls(parse_declarations(old_src), parse_declarations(new_src)))
    return "\n".join(out).rstrip() + "\n"


def _git_show(rev: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def _version_from_json(text: str) -> str | None:
    m = re.search(r'"version"\s*:\s*"([^"]+)"', text)
    return m.group(1) if m else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Structured diff of SDK .d.ts reference files.")
    parser.add_argument("old", nargs="?", help="Old .d.ts file")
    parser.add_argument("new", nargs="?", help="New .d.ts file")
    parser.add_argument(
        "--git-rev",
        help="Compare reference/*.d.ts in the working tree against this git revision",
    )
    parser.add_argument("-o", "--output", help="Also write the report to this file")
    args = parser.parse_args()

    if args.git_rev:
        pairs = []
        for name in REFERENCE_FILES:
            rel = f"reference/{name}"
            new_path = REFERENCE_DIR / name
            pairs.append((
                name,
                _git_show(args.git_rev, rel),
                new_path.read_text() if new_path.exists() else "",
            ))
        old_v = _version_from_json(_git_show(args.git_rev, "reference/VERSION.json"))
        vfile = REFERENCE_DIR / "VERSION.json"
        new_v = _version_from_json(vfile.read_text()) if vfile.exists() else None
        report = build_report(pairs, old_v, new_v)
    elif args.old and args.new:
        pairs = [(Path(args.new).name, Path(args.old).read_text(), Path(args.new).read_text())]
        report = build_report(pairs, None, None)
    else:
        parser.error("pass OLD NEW files or --git-rev REV")

    if args.output:
        Path(args.output).write_text(report)
        print(f"Wrote {args.output}", file=sys.stderr)
    print(report)


if __name__ == "__main__":
    main()

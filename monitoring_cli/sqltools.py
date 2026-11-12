"""Read and change DedaubQL text before the CLI sends it.

- `keccak256` and signature parsing, with no extra dependency;
- the helpers `selector('f(uint256)')`, `topic0('E(address)')` and
  `keccak256('text')`, which the server does not have: they become the hash
  literal, with the original call kept in a comment;
- a scan for signed-int parameters in `logs(...)` / `transaction_detail(...)`
  signatures, which the platform's macros decode wrongly;
- the event signatures of `logs(...)` macros, for the zero-row check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- keccak256 (the Ethereum hash: Keccak-f[1600], rate 136, pad 0x01) ---

_MASK = (1 << 64) - 1
_ROUND_CONSTANTS = (
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808A,
    0x8000000080008000,
    0x000000000000808B,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008A,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000A,
    0x000000008000808B,
    0x800000000000008B,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800A,
    0x800000008000000A,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
)
# _ROTATIONS[x][y] for the lane at (x, y).
_ROTATIONS = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)
_RATE = 136


def _rol(value: int, shift: int) -> int:
    shift %= 64
    return ((value << shift) | (value >> (64 - shift))) & _MASK


def _keccak_f(lanes: list[int]) -> list[int]:
    for rc in _ROUND_CONSTANTS:
        c = [
            lanes[x] ^ lanes[x + 5] ^ lanes[x + 10] ^ lanes[x + 15] ^ lanes[x + 20]
            for x in range(5)
        ]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        lanes = [lanes[i] ^ d[i % 5] for i in range(25)]
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol(
                    lanes[x + 5 * y], _ROTATIONS[x][y]
                )
        lanes = [
            b[i]
            ^ (~b[(i % 5 + 1) % 5 + 5 * (i // 5)] & b[(i % 5 + 2) % 5 + 5 * (i // 5)])
            for i in range(25)
        ]
        lanes[0] ^= rc
    return lanes


def keccak256(data: bytes) -> bytes:
    return _sponge(data, 0x01)


def _sponge(data: bytes, pad: int) -> bytes:
    """Keccak pads with 0x01; SHA3-256 (hashlib) differs only by pad 0x06."""
    padded = bytearray(data)
    padded.append(pad)
    padded.extend(b"\x00" * (-len(padded) % _RATE))
    padded[-1] |= 0x80
    lanes = [0] * 25
    for start in range(0, len(padded), _RATE):
        block = padded[start : start + _RATE]
        for i in range(_RATE // 8):
            lanes[i] ^= int.from_bytes(block[8 * i : 8 * i + 8], "little")
        lanes = _keccak_f(lanes)
    return b"".join(lane.to_bytes(8, "little") for lane in lanes[:4])


# --- signatures ---

_TYPE_ALIASES = {"uint": "uint256", "int": "int256", "byte": "bytes1"}
_SIGNED_INT = re.compile(r"^int\d*(\[\d*\])*$")


@dataclass(frozen=True)
class Param:
    type: str  # canonical, e.g. "uint256", "(address,uint256)[]"
    name: str
    indexed: bool
    text: str  # as written


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if "".join(current).strip():
        parts.append("".join(current))
    return [p.strip() for p in parts]


def _normalise_type(raw: str) -> str:
    match = re.match(r"^([a-z]+\d*)((?:\[\d*\])*)$", raw)
    if not match:
        return raw
    base, dims = match.groups()
    return _TYPE_ALIASES.get(base, base) + dims


def parse_params(text: str) -> list[Param]:
    """Parse `type [indexed] [name], ...`; a tuple is `(…)[dims] [name]`."""
    params = []
    for part in _split_top_level(text):
        if not part:
            continue
        if part.startswith("("):
            depth = 0
            end = 0
            for i, ch in enumerate(part):
                depth += ch == "("
                depth -= ch == ")"
                if depth == 0:
                    end = i
                    break
            inner = parse_params(part[1:end])
            rest = part[end + 1 :].strip()
            dims_match = re.match(r"^((?:\[\d*\])*)\s*(.*)$", rest)
            dims, words = dims_match.groups() if dims_match else ("", rest)
            type_ = "(" + ",".join(p.type for p in inner) + ")" + dims
            tokens = words.split()
        else:
            tokens = part.split()
            type_ = _normalise_type(tokens[0])
            tokens = tokens[1:]
        indexed = "indexed" in tokens
        names = [t for t in tokens if t != "indexed"]
        params.append(Param(type_, names[0] if names else "", indexed, part))
    return params


def _flatten_types(params: list[Param]) -> list[tuple[str, Param]]:
    """Every leaf type with the top-level parameter it belongs to."""
    leaves = []
    for p in params:
        if p.type.startswith("("):
            inner = re.sub(r"(\[\d*\])+$", "", p.type)[1:-1]
            for leaf in _leaf_types(inner):
                leaves.append((leaf, p))
        else:
            leaves.append((p.type, p))
    return leaves


def _leaf_types(types: str) -> list[str]:
    out = []
    for part in _split_top_level(types):
        if part.startswith("("):
            out.extend(_leaf_types(re.sub(r"(\[\d*\])+$", "", part)[1:-1]))
        else:
            out.append(part)
    return out


_SIGNATURE = re.compile(
    r"^\s*(?:(0x[0-9a-fA-F]{40})\.)?([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$", re.S
)


@dataclass(frozen=True)
class Signature:
    address: str | None
    name: str
    params: list[Param]

    @property
    def canonical(self) -> str:
        return f"{self.name}({','.join(p.type for p in self.params)})"

    @property
    def indexed_count(self) -> int:
        return sum(p.indexed for p in self.params)


def parse_signature(text: str) -> Signature | None:
    match = _SIGNATURE.match(text)
    if not match:
        return None
    address, name, body = match.groups()
    try:
        params = parse_params(body)
    except IndexError:
        return None
    return Signature(address.lower() if address else None, name, params)


def canonical(signature: str) -> str:
    parsed = parse_signature(signature)
    if parsed is None:
        raise ValueError(f"not a signature: {signature!r}")
    return parsed.canonical


# --- a scanner over SQL that knows strings, comments and Jinja blocks ---


@dataclass(frozen=True)
class Segment:
    kind: str  # "code", "string", "ident", "comment", "jinja"
    text: str


def segments(sql: str) -> list[Segment]:
    out: list[Segment] = []
    i = 0
    n = len(sql)
    code_start = 0

    def flush(end: int) -> None:
        if end > code_start:
            out.append(Segment("code", sql[code_start:end]))

    while i < n:
        two = sql[i : i + 2]
        ch = sql[i]
        if two in ("{{", "{%", "{#"):
            close = {"{{": "}}", "{%": "%}", "{#": "#}"}[two]
            end = sql.find(close, i + 2)
            end = n if end < 0 else end + 2
            kind = "comment" if two == "{#" else "jinja"
        elif two == "--":
            end = sql.find("\n", i)
            end = n if end < 0 else end
            kind = "comment"
        elif two == "/*":
            end = sql.find("*/", i + 2)
            end = n if end < 0 else end + 2
            kind = "comment"
        elif ch in ("'", '"'):
            end = i + 1
            while end < n:
                if sql[end] == ch:
                    if sql[end + 1 : end + 2] == ch:  # doubled quote
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            kind = "string" if ch == "'" else "ident"
        else:
            i += 1
            continue
        flush(i)
        out.append(Segment(kind, sql[i:end]))
        i = end
        code_start = end
    flush(n)
    return out


# --- helper rewrite ---

_HELPER = re.compile(
    r"(?<![\w.])(?:common\.)?(selector|topic0|keccak256)\s*\(\s*$", re.I
)


@dataclass(frozen=True)
class Rewrite:
    call: str
    literal: str


def _helper_literal(func: str, arg: str) -> str:
    func = func.lower()
    if func == "keccak256":
        digest = keccak256(arg.encode())
    else:
        digest = keccak256(canonical(arg).encode())
        if func == "selector":
            digest = digest[:4]
    return f"'\\x{digest.hex()}'::bytea"


def rewrite_helpers(sql: str) -> tuple[str, list[Rewrite]]:
    """Replace `selector('sig')`, `topic0('sig')` and `keccak256('text')` with
    their hash literal and keep the call in a comment. A helper on a column, as
    in `selector(d.calldata)`, is the server's function and stays."""
    segs = segments(sql)
    out: list[str] = []
    rewrites: list[Rewrite] = []
    i = 0
    while i < len(segs):
        seg = segs[i]
        if (
            seg.kind == "code"
            and i + 2 < len(segs)
            and segs[i + 1].kind == "string"
            and segs[i + 2].kind == "code"
        ):
            match = _HELPER.search(seg.text)
            close = re.match(r"^\s*\)", segs[i + 2].text)
            if match and close:
                arg = segs[i + 1].text[1:-1].replace("''", "'")
                func = match.group(1)
                try:
                    literal = _helper_literal(func, arg)
                except ValueError:
                    literal = None
                if literal is not None:
                    call = seg.text[match.start() :] + segs[i + 1].text + close.group(0)
                    comment = call.replace("*/", "* /")
                    out.append(seg.text[: match.start()])
                    out.append(f"{literal} /* {comment.strip()} */")
                    rewrites.append(Rewrite(call.strip(), literal))
                    segs[i + 2] = Segment("code", segs[i + 2].text[close.end() :])
                    i += 2
                    continue
        out.append(seg.text)
        i += 1
    return "".join(out), rewrites


# --- macro signatures ---

_MACRO = re.compile(r"(?:(\w+)\.)?(logs|transaction_detail)\s*\(", re.I)
_STRING = re.compile(r"'((?:[^']|'')*)'|\"((?:[^\"]|\"\")*)\"")
_DURATION = re.compile(r"duration\s*=\s*['\"]([^'\"]+)['\"]")


@dataclass(frozen=True)
class MacroSignature:
    macro: str  # "logs" or "transaction_detail"
    chain: str | None
    duration: str | None
    signature: Signature | None
    outputs: list[Param]


def macro_signatures(sql: str) -> list[MacroSignature]:
    found = []
    for seg in segments(sql):
        if seg.kind != "jinja":
            continue
        match = _MACRO.search(seg.text)
        if not match:
            continue
        chain, macro = match.group(1), match.group(2).lower()
        duration = _DURATION.search(seg.text)
        signature = None
        outputs: list[Param] = []
        for s in _STRING.finditer(seg.text):
            value = s.group(1) if s.group(1) is not None else s.group(2)
            prefix = seg.text[: s.start()].rstrip()
            if prefix.endswith("duration =") or prefix.endswith("duration="):
                continue
            if re.search(r"outputs\s*=$", prefix):
                inner = value.strip()
                if inner.startswith("(") and inner.endswith(")"):
                    outputs = parse_params(inner[1:-1])
                continue
            parsed = parse_signature(value)
            if parsed is not None and signature is None:
                signature = parsed
        if signature is not None or outputs:
            found.append(
                MacroSignature(
                    macro,
                    chain.lower() if chain else None,
                    duration.group(1) if duration else None,
                    signature,
                    outputs,
                )
            )
    return found


def signed_int_params(sql: str) -> list[tuple[str, Param]]:
    """(macro, parameter) for every signed-int argument or output that a
    signature macro will decode."""
    hits = []
    for m in macro_signatures(sql):
        params = (m.signature.params if m.signature else []) + m.outputs
        seen = set()
        for leaf, param in _flatten_types(params):
            if _SIGNED_INT.match(leaf) and param.text not in seen:
                seen.add(param.text)
                hits.append((m.macro, param))
    return hits


def topic0(signature: Signature) -> str:
    return "0x" + keccak256(signature.canonical.encode()).hex()

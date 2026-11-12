import hashlib

import pytest

from monitoring_cli import sqltools

# --- keccak256 ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("data", "digest"),
    [
        (b"", "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"),
        (b"abc", "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"),
        (
            b"Transfer(address,address,uint256)",
            "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
        ),
    ],
)
def test_keccak256_known_vectors(data, digest):
    assert sqltools.keccak256(data).hex() == digest


@pytest.mark.parametrize("length", [0, 1, 135, 136, 137, 271, 272, 273, 1000])
def test_permutation_matches_hashlib_sha3_over_block_edges(length):
    # SHA3-256 is the same sponge with pad 0x06, so this checks the
    # permutation on one and on several blocks against the standard library.
    data = bytes(range(256)) * 4
    data = data[:length]
    assert sqltools._sponge(data, 0x06) == hashlib.sha3_256(data).digest()


# --- signatures -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ("transfer(address to, uint amount)", "transfer(address,uint256)"),
        (
            "Swap(bytes32 indexed id, address indexed sender, int128 amount0, int24 tick)",
            "Swap(bytes32,address,int128,int24)",
        ),
        (
            "0xBBBBBBBBBB9cC5e90e3b3Af64bdAF62C37EEFFCb.CreateMarket(bytes32 indexed id, "
            "(address loanToken, address collateralToken, uint256 lltv) marketParams)",
            "CreateMarket(bytes32,(address,address,uint256))",
        ),
        ("f((uint a, int[] b)[] xs, bytes data)", "f((uint256,int256[])[],bytes)"),
        ("ping()", "ping()"),
    ],
)
def test_canonical(text, canonical):
    assert sqltools.canonical(text) == canonical


def test_parse_signature_keeps_address_and_indexed_count():
    sig = sqltools.parse_signature(
        "0xABCDEF0000000000000000000000000000000001.E(address indexed a, uint b)"
    )
    assert sig is not None
    assert sig.address == "0xabcdef0000000000000000000000000000000001"
    assert sig.indexed_count == 1


# --- helper rewrite ---------------------------------------------------------


def test_rewrite_helpers_replaces_literal_calls_only():
    sql = (
        "SELECT selector(d.calldata) = selector('transfer(address to, uint amount)'), "
        "common.topic0('Transfer(address,address,uint256)'), keccak256('abc')"
    )
    new, rewrites = sqltools.rewrite_helpers(sql)
    assert "selector(d.calldata)" in new
    assert (
        "'\\xa9059cbb'::bytea /* selector('transfer(address to, uint amount)') */"
        in new
    )
    assert "'\\xddf252ad" in new
    assert (
        "'\\x4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45'::bytea"
        in new
    )
    assert [r.call.split("(")[0] for r in rewrites] == [
        "selector",
        "common.topic0",
        "keccak256",
    ]


def test_rewrite_helpers_leaves_strings_comments_and_macros():
    sql = (
        "SELECT 'selector(''x()'')' AS s -- selector('a()')\n"
        "/* topic0('E()') */ FROM {{logs(inputs='E(uint a)')}} l"
    )
    new, rewrites = sqltools.rewrite_helpers(sql)
    assert new == sql
    assert rewrites == []


def test_rewrite_helpers_leaves_a_bad_signature():
    sql = "SELECT selector('not a signature')"
    new, rewrites = sqltools.rewrite_helpers(sql)
    assert new == sql
    assert rewrites == []


# --- macro signatures -------------------------------------------------------

_SQL = """
SELECT * FROM {{ethereum.logs(duration='30d', inputs='0x000000000004444c5dc75cb358380d2e3de08a90.Swap(bytes32 indexed id, address indexed sender, int128 amount0, int128 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick, uint24 fee)')}} s
JOIN {{transaction_detail("swap(address recipient, bool zeroForOne, int256 amountSpecified)", outputs='(int256 a0, uint256 a1)')}} d ON true
JOIN {{base.logs('0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb.SetCap(address indexed caller, bytes32 indexed id, uint256 cap)')}} c ON true
"""


def test_macro_signatures_reads_chain_duration_and_signature():
    found = sqltools.macro_signatures(_SQL)
    assert [(m.macro, m.chain, m.duration) for m in found] == [
        ("logs", "ethereum", "30d"),
        ("transaction_detail", None, None),
        ("logs", "base", None),
    ]
    swap = found[0].signature
    assert swap is not None
    assert swap.address == "0x000000000004444c5dc75cb358380d2e3de08a90"
    assert swap.indexed_count == 2
    assert (
        sqltools.topic0(swap)
        == "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
    )


def test_signed_int_params_finds_arguments_and_outputs():
    hits = [(macro, p.text) for macro, p in sqltools.signed_int_params(_SQL)]
    assert hits == [
        ("logs", "int128 amount0"),
        ("logs", "int128 amount1"),
        ("logs", "int24 tick"),
        ("transaction_detail", "int256 amountSpecified"),
        ("transaction_detail", "int256 a0"),
    ]


def test_signed_int_params_sees_ints_inside_tuples():
    sql = "SELECT * FROM {{logs(inputs='E((int24 lower, uint24 upper) range)')}} l"
    assert [p.text for _, p in sqltools.signed_int_params(sql)] == [
        "(int24 lower, uint24 upper) range"
    ]


def test_signed_int_params_ignores_unsigned():
    sql = "SELECT * FROM {{logs(inputs='Transfer(address indexed a, uint256 v)')}} l"
    assert sqltools.signed_int_params(sql) == []

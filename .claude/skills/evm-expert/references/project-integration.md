# TokenSafety EVM Integration Reference

This file maps EVM concepts to the project's actual codebase utilities. When implementing EVM-related features, use these existing utilities rather than building from scratch.

---

## EvmAPI (`utils/evm/evm_api.py`)

Singleton access: `EvmAPI.get_instance()`

### Core Methods

| Method | Purpose | Notes |
|---|---|---|
| `read_function_from_contract(chain, address, fn_name, abi, args)` | Call a read function | Handles checksum, ABI encoding |
| `get_storage_at(chain, contract_address, slot)` | Read single storage slot | Raw `eth_getStorageAt` |
| `get_storage_at_bulk(chain, contract_address, slots[])` | Batch read storage slots | Concurrent with semaphore |
| `simulate_transaction(chain, tx_params)` | Simulate single tx | Uses `debug_traceCall` with callTracer |
| `simulate_transactions(chain, txs[])` | Batch simulate | Dispatches to geth or erigon based on chain |
| `simulate_transactions_geth(chain, txs[])` | Geth simulation | Uses `debug_traceCall` per tx |
| `simulate_transactions_erigon(chain, txs[])` | Erigon simulation | Uses `trace_callMany` for batching |
| `debug_transaction(chain, tx_hash)` | Trace mined tx | `debug_traceTransaction` with callTracer |
| `multicall(chain, calls[], state_override)` | Multicall3 batch | `eth_call` with custom multicall bytecode |
| `batch_multicall(chain, calls[], batch_size)` | Large multicall | Splits into batches, concurrent execution |
| `debug_multicall(chain, calls[])` | Multicall + trace | `debug_traceCall` with custom multicall |
| `get_bytecode(chain, contract_address)` | Get deployed code | `eth_getCode` |
| `get_balance_of(chain, contract_address, token_address)` | ERC-20 balance | Via ABI call |
| `get_total_supply(chain, contract_address)` | ERC-20 totalSupply | Via ABI call |
| `get_allowance(chain, contract_address, owner, spender)` | ERC-20 allowance | Via ABI call |
| `get_name/get_symbol/get_decimals(chain, contract_address)` | Token metadata | Via ABI calls |
| `get_owner(chain, contract_address)` | Contract owner | Via `owner()` call |
| `get_token_usd_price(chain, token_address)` | Token USD price | Via Chainlink + DEX pools |
| `get_expected_out(chain, pair_address, amount, token_in, abi)` | Quote swap output | Via `getAmountsOut` |
| `get_pair(chain, factory, tokenA, tokenB, abi)` | Get V2 pair address | Via factory `getPair()` |
| `get_pool_v3(chain, factory, tokenA, tokenB, fee, abi)` | Get V3 pool address | Via factory `getPool()` |
| `get_latest_block_number(chain)` | Current block | `eth_blockNumber` |
| `build_tx(chain, from, to, data, value, gas)` | Build TxParams | Helper for simulation |

### Decoding Helpers

| Method | Purpose |
|---|---|
| `get_call_success(result, fn_name)` | Check if call succeeded in trace |
| `get_decoded_output(result, fn_name, abi)` | Decode return data from trace |
| `get_decoded_output_geth(result, fn_name, abi)` | Decode from geth trace format |
| `get_decoded_call_tracer_output(result, fn_name, abi)` | Decode from callTracer output |

### Network Dispatch
```python
chain.to_node_type()  # Returns "erigon" or "geth"
# Used internally to choose simulation method
# Geth chains: use debug_traceCall per-tx
# Erigon chains: use trace_callMany for batching
```

---

## AI Agent Tools (`utils/ai/tools/`)

These are the tools available to the AI analysis agent. Use them when building agent functionality.

### Source Code Tools (`source_code.py`)
| Function | Purpose |
|---|---|
| `get_flattened_source_code(address, network)` | Flattened Solidity source from DB |
| `get_decompiled_source_code(address, network)` | Decompiled representation |
| `get_bytecode(address, network)` | Deployed bytecode via RPC |
| `get_contract_abi(address, network)` | ABI from DB |
| `get_proxy_implementation_address(address, network)` | Resolve proxy impl |

### Storage Tools (`storage_reading.py`)
| Function | Purpose |
|---|---|
| `read_basic_slot(address, slot, chain)` | Raw 32-byte slot read |
| `read_dynamic_array_length(address, slot, chain)` | Array length at slot |
| `read_dynamic_array_elem(address, slot, index, chain)` | Element at keccak256(slot)+index |
| `read_static_array_elem(address, slot, index, chain)` | Element at slot+index |
| `read_mapping_value(address, slot, key, chain)` | Mapping value via keccak256(key,slot) |
| `read_nested_mapping_value(address, slot, k1, k2, chain)` | Nested mapping |
| `read_simple_storage_var(name, address, network)` | Read by variable name (needs layout) |
| `get_all_storage_vars(layout_addr, contents_addr, network)` | Read all inplace vars |
| `read_mapping_storage_var(name, key, address, network)` | Mapping by name+key |
| `read_nested_mapping_storage_var(name, k1, k2, address, network)` | Nested by name |

### Storage Decode Helpers (`storage_decode.py`)
| Function | Purpose |
|---|---|
| `extract_packed_uint(slot_bytes, offset, bit_width)` | Extract packed uint from slot |
| `extract_packed_address(slot_bytes, offset)` | Extract packed address (20 bytes) |
| `extract_packed_bool(slot_bytes, offset)` | Extract packed bool (1 byte) |
| `extract_packed_int(slot_bytes, offset, bit_width)` | Extract packed signed int |
| `extract_packed_bytesN(slot_bytes, offset, N)` | Extract packed bytesN |

### Storage Layout (`storage_layout.py`)
| Function | Purpose |
|---|---|
| `get_storage_layout(address, network)` | Fetch layout from DB → `StorageLayout` |
| `get_storage_variable(name, address, network)` | Find specific variable in layout |
| **`StorageLayout`** | `NamedTuple(variables, types)` |
| **`StorageVariable`** | `{slot, type, astId, label, offset, contract}` |
| **`StorageType`** | `{label, encoding, numberOfBytes, key, value, base}` |

### Simulation Tools (`simulate_eth.py`)
| Function | Purpose |
|---|---|
| `function_selector_from_signature(sig)` | Compute 4-byte selector |
| `encode_call_data(address, fn_name, args, network)` | Encode function calldata |
| `call_read_function(address, fn_name, args, network)` | Execute read call |
| `batch_simulate_transactions(transactions[], network)` | Batch tx simulation |
| **`FunctionCall`** | `@dataclass(from_address, to_address, function_name, args)` |

### DEX Tools (`dex.py`)
| Function | Purpose |
|---|---|
| `get_uniswap_v2_pools(tokenA, tokenB, network)` | Find V2 pairs |
| `get_uniswap_v3_pools(tokenA, tokenB, network)` | Find V3 pools |
| `get_stable_tokens(network)` | Network stable token addresses |
| `get_top_holders(token_address, network, limit)` | Top token holders |
| `get_token_price_history(address, from_ts, to_ts, network)` | Historical prices |

### Transaction Tools (`transactions.py`)
| Function | Purpose |
|---|---|
| `get_token_transfers(token_addr, sender, receiver, from_block, to_block, network)` | Query transfer history from DB |

---

## Proxy Detection via Trace (`utils/processing/token_metadata_processor.py`)

### `get_implementation_address_bulk(chain, contract_addresses)`
Two-phase proxy detection:
1. **DB lookup**: queries `{chain}.contracts` for known proxy entries (proxy_type, implementation_address)
2. **Trace fallback**: for addresses not found in DB, calls `check_proxy_via_balance_trace_bulk()` which traces a `name()` call via `batch_debug_multicall` and analyzes the callTracer output for DELEGATECALL patterns (`_analyze_balance_trace`)

Returns `dict[ChecksumAddress, Optional[str]]` mapping each address to its implementation address (or None).

**Gotcha**: The trace fallback uses `debug_traceCall` which can be rate-limited (429 errors on BSC QuikNode). The exception handler returns `[(False, None)] * len(addresses)` to gracefully handle failures without crashing the caller.

---

## Multicall Debug Trace Decoder (`utils/evm/misc.py`)

```python
decode_multicall_debug_trace_call(trace_result, output_types)
# Decodes a traced multicall response from debug_traceCall
# trace_result: raw trace output
# output_types: list of lists of output type strings per call
# Returns: list of decoded values (or None for failed calls)
```

---

## Constants (`utils/constants.py`)

| Constant | Purpose |
|---|---|
| `ERC20_ABI` | Standard ERC-20 ABI |
| `ERC721_ABI` | Standard ERC-721 ABI |
| `ERC1155_ABI` | Standard ERC-1155 ABI |
| `MULTICALL3` | Multicall3 contract address (`0xcA11bde05977b3631167028862bE2a173976CA11`) |
| `NULL_ADDRESS` | `0x0000000000000000000000000000000000000000` |
| `DUMMY_WALLET_ADDRESS` | Test wallet for simulations |
| `NETWORK_TOKEN_ADDRESSES` | Per-network stable/base token addresses (includes ASTER for BSC) |
| `CHAINLINK_PRICE_FEEDS` | Per-network Chainlink feed addresses (includes ASTER/USD for BSC) |
| `ETH_USD_CHAINLINK_PRICE_FEED_ABI` | Chainlink aggregator ABI |
| `FOURMEME_TOKEN_MANAGER_ADDRESS` | Four.Meme Token Manager proxy per network (BSC: `0x5c952063...`) |
| `FOURMEME_ASTER_ADDRESS` | ASTER quote token per network (BSC: `0x000ae314...`) |
| `FOURMEME_TOKEN_MANAGER_ABI` | Minimal ABI for `_tokenInfos`, `buyToken`, `sellToken`, `_tradingFeeRate` |
| `FOURMEME_STATUS_TRADING/HALT/ADDING_LIQUIDITY/COMPLETED` | Bonding curve status constants (0/1/2/3) |

---

## Custom Smart Contracts (`smart-contracts/`)

| Contract | Location | Purpose |
|---|---|---|
| BytecodeReader | `smart-contracts/bytecode-reader/` | Batch read bytecode via state override |
| CustomMulticall | `smart-contracts/custom-multicall/` | Custom multicall with state overrides |
| StorageReader | `smart-contracts/storage-reading/` | Batch storage slot reading |
| SwapV2 | `smart-contracts/v2/` | V2 swap simulation (+ Initiator pattern) |
| SwapV3 | `smart-contracts/v3/` | V3 swap simulation |
| SwapV4 | `smart-contracts/v4/` | V4 (Hooks) swap simulation |
| FourMemeProbe | `smart-contracts/fourmeme/` | Four.Meme bonding curve buy/sell simulation (BSC, needs solc ^0.8.24) |
| TransferCheck | `smart-contracts/transfer_contract/` | ERC-20 transfer simulation |
| SwapInitiatorRouter | `smart-contracts/swap-initiator-router/` | Router-level swap initiation |

These are compiled to bytecode and injected via state overrides in `eth_call`/`debug_traceCall` (no on-chain deployment needed).
Bytecode artifacts live in `utils/code_artifacts/` (e.g., `swap_fourmeme.py` for FourMemeProbe).

---

## DB Utilities (`utils/db_utils.py`)

| Function | Purpose |
|---|---|
| `to_bytea(hex_string)` | Convert `0x...` hex to bytes for PostgreSQL BYTEA |
| `bytea_to_hex(b)` | Convert bytes back to `0x...` hex string |
| `DbConnection.get_instance()` | Singleton DB connection |
| `db.get_rows_as_list(query, params)` | Execute query with retry |
| `db.session()` | Write session context manager |
| `db.read_connection()` | Read connection context manager |

### Address Handling Pattern
```python
from utils.db_utils import to_bytea, bytea_to_hex
from sqlalchemy import bindparam, text
from sqlalchemy.dialects import postgresql

# Writing to DB
params = [bindparam("addr", to_bytea(address), type_=postgresql.BYTEA)]
query = text("SELECT * FROM eth.contracts WHERE address = :addr").bindparams(*params)

# Reading from DB
hex_address = bytea_to_hex(row["address"])  # → "0x..."
```

---

## Protocol Integration Pattern (Pool Detection → Liquidity → Swap Sim)

When adding a new DEX or bonding curve protocol, these are the integration points:

### 1. Pool Detection
- **Batch/ingestor path**: `get_pair_addresses_bulk()` in `pair_processor.py` — queries DB `dex_pool` table + RPC fallbacks
- **On-demand API path**: `get_pairs()` in `pair_processor.py` — calls `get_pair_addresses()` (DB) + `get_pair_addresses_fallback()` (factory multicalls)
- Both paths must return `PairMetadata` with a unique `project_name` (e.g., `"Four.Meme Pool"`)
- If the protocol doesn't use standard DEX factories, add a custom detection function (e.g., `get_fourmeme_pairs_bulk()` calls `_tokenInfos()` on the Token Manager)

### 2. Reserves
- `populate_pairs_with_reserves()` fetches reserves for all detected pairs
- Standard pairs use `balanceOf(token, pool)` — if the protocol stores reserves internally (bonding curves), add a custom fetch path (e.g., `_fetch_fourmeme_reserves()`)

### 3. Liquidity (USD)
- `get_liquidity_in_usd_token_new()` in `liquidity_processor.py` — branch on `project_name`
- Uses `known_token_prices` from `get_known_token_usd_prices()` in `evm_api.py`
- If the quote token isn't weth/usdc/usdt, add its Chainlink feed to `CHAINLINK_PRICE_FEEDS` and fetch logic to `get_known_token_usd_prices()`
- Return a typed model (e.g., `PoolLiquidityFourMeme`) extending `PairMetadata` with `usd_liquidity`

### 4. Swap Simulation
- `buy_and_sell_bulk()` in `swap_processor.py` — branch on `project_name` to select simulation method
- Standard DEXs: prepare multicall tx → inject probe bytecode via state overrides → decode result
- If the protocol doesn't need simulation (e.g., bonding curve status verified at detection), add early-exit **before** holder lookups (holders only exist for weth/usdc/usdt)
- For new quote tokens: the "known token holder" lookup won't have it — handle before the holder check

### 5. Cache
- Pool results are cached in `token_safety.uni_v2_v3_pool_cache` (despite the name, it holds all pool types)
- Cache read queries in `cache_processor.py` and `swap_processor.py` filter by `known_tokens` — add any new quote tokens to these filters
- `token_computation_status` tracks whether pool/state data was successfully computed — a failed run caches `pool_cache_success = False`, which prevents re-runs until invalidated

### Four.Meme Specifics (BSC)
- Token Manager proxy: `0x5c952063c7fc8610ffdb798152d69f0b9550762b`
- Quote token: ASTER (`0x000ae314e2a2172a039b26378814c252734f556a`, 18 decimals)
- `_tokenInfos(address)` returns 13-field struct: token, quoteToken, templateId, totalSupply, maxSellable, initialVirtualAster, creationTimestamp, currentTokenReserve[7], currentAsterReserve[8], priceMetric, virtualReserve, derivedParam, status[12]
- Status: 0=TRADING (bonding curve), 3=COMPLETED (graduated to PancakeSwap Infinity V4)
- Bonding curve: 1B supply, 800M sellable, 5000 ASTER virtual reserve, 1% fee
- Pool address = meme token address (Token Manager is shared across all tokens)
- Token address suffixes: `4444`, `ffff`, `7777` (7777 overlaps with Flap — disambiguation required)

### Flap Specifics (BSC)
- Portal proxy: `0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0` (implementation: `0xc7be31bb69a60c8abaff1280594db2c66dc5318e`)
- Quote tokens: BNB (native, `address(0)`), USDT (`0x55d398326f99059ff775485246999027b3197955`), USD1 (`0x8d0d000ee44948fc98c9b98a4fa4921476f08b0d`), lisUSD (`0x0782b6d8c4551b9760e74c0545a9bcd90bdc41e5`)
- `getTokenV7(address)` returns 17-word struct: status[0], quoteReserve[1], tokenReserve[2], priceMetric[3], version[4], r[5], h[6], k[7], dexSupplyThresh[8], **quoteToken[9]**, migratorType[10], ?[11], taxRate[12], ?[13], circulatingSupply[14], ?[15], ?[16]
- Bonding curve: `(x+h)(y+r)=K`, 1B supply, 800M sellable, ~1% fee, tax tokens add 1-10% extra
- Token address suffixes: `8888` (standard non-tax), `7777` (tax tokens — overlaps with Four.Meme)
- Token architecture: EIP-1167 minimal proxy clones (impl V1: `0x29e6383f0ce68507b5a72a53c2b118a118332aa8`)
- Graduation: V3 migrator (PancakeSwap V3, default) or V2 migrator (mandatory for tax tokens)
- **Quote token disambiguation**: suffix alone cannot determine quote token — read `getTokenV7` Word 9 (`address(0)` = BNB, else ERC-20 address)
- **Stablecoin pricing**: USDT/USD1/lisUSD can be assumed $1.00; BNB needs Chainlink/DEX price
- **7777 disambiguation**: try both Flap `getTokenV7()` and Four.Meme `_tokenInfos()` — use whichever returns valid data
- Total tokens created: ~520K (from `nonce()`)
- Portal version: `v5.8.8`
- Full research: `.claude/changelogs/FLAP_PROTOCOL_RESEARCH.md`

---

## Network Configuration

```python
from models.features import Network

# Available networks
Network.ETHEREUM    # "ethereum", chain_id=1
Network.BINANCE     # "binance", chain_id=56
Network.BASE        # "base", chain_id=8453
Network.ARBITRUM    # "arbitrum", chain_id=42161
Network.AVALANCHE   # "avalanche", chain_id=43114

# Conversions
network = Network.from_chain_id(56)    # → Network.BINANCE
chain_id = network.to_chain_id()       # → 56
node_type = network.to_node_type()     # → "geth" or "erigon"
```

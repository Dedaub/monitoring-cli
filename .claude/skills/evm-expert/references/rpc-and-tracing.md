# JSON-RPC, Tracing & Simulation Reference

## Standard JSON-RPC Methods (eth_ namespace)

### Read State
```json
// Get storage slot value
{"method": "eth_getStorageAt", "params": ["0xContractAddr", "0xSlotHex", "latest"]}

// Get account balance
{"method": "eth_getBalance", "params": ["0xAddress", "latest"]}

// Get contract bytecode
{"method": "eth_getCode", "params": ["0xAddress", "latest"]}

// Get transaction count (nonce)
{"method": "eth_getTransactionCount", "params": ["0xAddress", "latest"]}
```

### Simulate Calls
```json
// eth_call — stateless simulation, returns raw output
{
  "method": "eth_call",
  "params": [
    {"from": "0x...", "to": "0x...", "data": "0x<selector+args>", "value": "0x0", "gas": "0x..."},
    "latest",
    // Optional 3rd param: state overrides
    {
      "0xContractAddr": {
        "balance": "0xDE0B6B3A7640000",      // override ETH balance
        "nonce": "0x1",                        // override nonce
        "code": "0x6080...",                   // inject bytecode
        "stateDiff": {"0xSlot": "0xValue"},    // override specific storage slots (merge)
        "state": {"0xSlot": "0xValue"}         // replace ALL storage with this (wipe+set)
      }
    }
  ]
}

// eth_estimateGas — like eth_call but returns gas estimate
{"method": "eth_estimateGas", "params": [{"from": "0x...", "to": "0x...", "data": "0x..."}]}
```

### Transactions & Receipts
```json
// Get transaction by hash
{"method": "eth_getTransactionByHash", "params": ["0xTxHash"]}
// Returns: {hash, nonce, blockHash, blockNumber, from, to, value, gas, gasPrice, input, v, r, s, type}

// Get receipt
{"method": "eth_getTransactionReceipt", "params": ["0xTxHash"]}
// Returns: {status, gasUsed, logs[], contractAddress, blockNumber, transactionIndex, cumulativeGasUsed}
```

### Logs & Events
```json
// Filter logs
{
  "method": "eth_getLogs",
  "params": [{
    "fromBlock": "0xF4240",     // or "earliest", "latest"
    "toBlock": "0xF42FF",
    "address": "0xTokenAddr",    // optional: filter by emitting contract
    "topics": [
      "0xddf252ad...",           // topic0: event signature hash
      null,                      // topic1: any value (wildcard)
      "0x000...recipient"        // topic2: specific indexed param (left-padded to 32 bytes)
    ]
  }]
}
// Returns: [{address, topics[], data, blockNumber, transactionHash, logIndex, ...}]
```

### Blocks
```json
{"method": "eth_blockNumber", "params": []}
{"method": "eth_getBlockByNumber", "params": ["latest", true]}  // true = include full tx objects
{"method": "eth_getBlockByHash", "params": ["0xBlockHash", false]}
```

---

## Debug Namespace (Geth)

### debug_traceTransaction
Replays an already-mined transaction with full EVM trace.
```json
{
  "method": "debug_traceTransaction",
  "params": [
    "0xTxHash",
    {
      "tracer": "callTracer",           // or "prestateTracer", "4byteTracer", custom JS
      "tracerConfig": {
        "onlyTopCall": false,           // false = include internal calls
        "withLog": true                 // include LOG operations in trace
      }
    }
  ]
}
```

#### callTracer Output
```json
{
  "type": "CALL",           // CALL, STATICCALL, DELEGATECALL, CREATE, CREATE2
  "from": "0x...",
  "to": "0x...",
  "value": "0x0",
  "gas": "0x...",
  "gasUsed": "0x...",
  "input": "0x<calldata>",
  "output": "0x<returndata>",
  "error": "execution reverted",  // only if reverted
  "revertReason": "...",           // decoded if available
  "calls": [                       // nested sub-calls
    {
      "type": "STATICCALL",
      "from": "0x...",
      "to": "0x...",
      "input": "0x70a08231...",   // balanceOf call
      "output": "0x000...0de0b6b3a7640000",
      "calls": []
    }
  ]
}
```

#### prestateTracer Output
Shows state before and after execution:
```json
{
  "pre": {
    "0xAddress": {
      "balance": "0x...",
      "nonce": 5,
      "code": "0x...",
      "storage": {"0xSlot": "0xValue"}
    }
  },
  "post": {
    "0xAddress": {
      "balance": "0x...",
      "storage": {"0xSlot": "0xNewValue"}
    }
  }
}
```

### debug_traceCall
Simulates a call (not yet mined) and returns trace — like `eth_call` + tracing:
```json
{
  "method": "debug_traceCall",
  "params": [
    {"from": "0x...", "to": "0x...", "data": "0x...", "value": "0x0"},
    "latest",
    {"tracer": "callTracer", "tracerConfig": {"onlyTopCall": false, "withLog": true}},
    // Optional: state overrides (same format as eth_call)
    {"0xAddr": {"balance": "0x...", "code": "0x..."}}
  ]
}
```

---

## Trace Namespace (Erigon / OpenEthereum)

### trace_replayTransaction
```json
{
  "method": "trace_replayTransaction",
  "params": [
    "0xTxHash",
    ["trace", "stateDiff", "vmTrace"]  // which trace types to include
  ]
}
```

**trace** output — flat list of actions:
```json
{
  "trace": [
    {
      "action": {"callType": "call", "from": "0x...", "to": "0x...", "gas": "0x...", "input": "0x...", "value": "0x0"},
      "result": {"gasUsed": "0x...", "output": "0x..."},
      "subtraces": 2,
      "traceAddress": [],        // root call
      "type": "call"
    },
    {
      "action": {"callType": "staticcall", "from": "0x...", "to": "0x...", "input": "0x..."},
      "result": {"output": "0x..."},
      "subtraces": 0,
      "traceAddress": [0],       // first sub-call of root
      "type": "call"
    }
  ]
}
```

### trace_call / trace_callMany
```json
// Single call simulation with trace
{
  "method": "trace_call",
  "params": [
    {"from": "0x...", "to": "0x...", "data": "0x..."},
    ["trace"],
    "latest"
  ]
}

// Batch simulation (Erigon only) — sequential calls sharing state
{
  "method": "trace_callMany",
  "params": [
    [
      [{"from": "0x...", "to": "0x...", "data": "0x..."}, ["trace"]],
      [{"from": "0x...", "to": "0x...", "data": "0x..."}, ["trace"]]
    ],
    "latest"
  ]
}
```

### trace_filter
Query historical traces by criteria:
```json
{
  "method": "trace_filter",
  "params": [{
    "fromBlock": "0xF4240",
    "toBlock": "0xF42FF",
    "fromAddress": ["0x..."],      // filter by caller
    "toAddress": ["0x..."],        // filter by callee
    "after": 0,                     // pagination offset
    "count": 100                    // max results
  }]
}
```

---

## Interpreting Callstacks

### Reading a Call Tree
1. **Root call**: the top-level transaction (from EOA → to contract)
2. **Sub-calls**: nested CALL/STATICCALL/DELEGATECALL within the execution
3. **traceAddress** (Erigon): path indices — `[0, 1]` means "2nd sub-call of the 1st sub-call"
4. **DELEGATECALL**: `from` is the delegating contract, `to` is the library/impl, but execution context is the delegating contract

### Common Patterns in Traces
- **Proxy → Implementation**: root CALL to proxy → DELEGATECALL to implementation
- **Router → Pair**: swap router CALL to pair contract → pair does STATICCALL for reserves → CALL for token transfers
- **Multicall**: root CALL to Multicall3 → multiple CALL/STATICCALL sub-calls
- **Flash loan**: lender CALL to borrower callback → borrower executes logic → CALL back to lender for repayment

### Decoding Trace Data
1. Extract `input` field from trace
2. First 4 bytes = function selector → look up in ABI or 4byte directory
3. Remaining bytes = ABI-encoded arguments → decode with known types
4. `output` field = ABI-encoded return value
5. If `error` field exists: extract revert reason from output (see revert decoding in SKILL.md)

---

## Simulation Recipes

### Check if ERC-20 Transfer Has Hidden Tax
```python
# 1. Get a token holder with balance
# 2. Simulate: transfer(recipient, amount) from holder
# 3. Before: balanceOf(holder), balanceOf(recipient)
# 4. After: check actual balance changes
# 5. Tax = amount - (recipient_after - recipient_before)
```

### Check if Token is Honeypot (can't sell)
```python
# 1. State override: give dummy wallet tokens + ETH
# 2. Simulate: approve(router, maxUint256) from dummy
# 3. Simulate: swap tokens → ETH via router
# 4. If swap reverts → likely honeypot
# 5. If swap succeeds but output is ~0 → extreme tax
```

### Read All Proxy Implementation Slots
```python
# Check standard EIP-1967 slots:
impl_slot = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
admin_slot = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
beacon_slot = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
# eth_getStorageAt(proxy_address, slot, "latest")
# If non-zero → extract address from last 20 bytes
```

### Batch Read Token Metadata
```python
# Use Multicall3 to batch: name(), symbol(), decimals(), totalSupply(), owner()
# Encode each call → aggregate3([{target, callData}]) → decode results
```

---

## External Lookup APIs

Use these APIs (via `WebFetch`) to look up selectors, event signatures, and ABIs when the project DB doesn't have them.

### 4byte.directory — Function & Event Signature Lookup

API docs: https://www.4byte.directory/docs/

**Look up function signature by 4-byte selector:**
```
GET https://www.4byte.directory/api/v1/signatures/?hex_signature=0xa9059cbb
```
Response: `{"results": [{"text_signature": "transfer(address,uint256)", ...}]}`

**Look up event signature by topic0 (32-byte hash):**
```
GET https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
```
Response: `{"results": [{"text_signature": "Transfer(address,address,uint256)", ...}]}`

**Search by text signature:**
```
GET https://www.4byte.directory/api/v1/signatures/?text_signature=transfer
```

### Sourcify — Verified Source Code & ABI

Sourcify provides verified contract source code and metadata (including ABI) across multiple chains.

**Check if a contract is verified:**
```
GET https://sourcify.dev/server/check-all-by-addresses?addresses=0x<addr>&chainIds=1
```

**Get full metadata (ABI + source):**
```
GET https://sourcify.dev/server/files/any/1/0x<addr>
```
Returns source files and `metadata.json` which contains the ABI under `output.abi`.

**Get ABI directly from metadata:**
```
GET https://repo.sourcify.dev/contracts/full_match/1/0x<addr>/metadata.json
```
Parse the JSON → `output.abi` field.

**Chain IDs for Sourcify:** 1 (Ethereum), 56 (BSC), 8453 (Base), 42161 (Arbitrum), 43114 (Avalanche)

### OpenChain (formerly sig.eth)

**Function signature lookup:**
```
GET https://api.openchain.xyz/signature-database/v1/lookup?function=0xa9059cbb
```

**Event signature lookup:**
```
GET https://api.openchain.xyz/signature-database/v1/lookup?event=0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
```

### Etherscan-compatible APIs

Works for Etherscan, BscScan, BaseScan, Arbiscan, SnowTrace (same API format, different base URLs).

**Get ABI for verified contract:**
```
GET https://api.etherscan.io/api?module=contract&action=getabi&address=0x<addr>&apikey=<key>
```

**Get source code:**
```
GET https://api.etherscan.io/api?module=contract&action=getsourcecode&address=0x<addr>&apikey=<key>
```

### Lookup Priority
When you need to decode unknown calldata or identify a function/event:
1. **Project DB** (`get_contract_abi` from `utils/ai/tools/source_code.py`) — fastest, already integrated
2. **4byte.directory** — broadest coverage for selectors/events, no API key needed
3. **Sourcify** — full verified source + ABI, decentralized
4. **OpenChain** — good alternative for selector lookup
5. **Etherscan API** — reliable but needs API key

---

## L2-Specific RPC Methods

### OP Stack (Optimism, Base)

**GasPriceOracle** (`0x420000000000000000000000000000000000000F`):
```json
// Get L1 data fee for a serialized transaction
{"method": "eth_call", "params": [{"to": "0x420000000000000000000000000000000000000F", "data": "0x<getL1Fee(bytes)>"}, "latest"]}
```

**L1Block** (`0x4200000000000000000000000000000000000015`):
```json
// Read L1 block info from L2
// number(), timestamp(), basefee(), hash(), blobBaseFee(), baseFeeScalar(), blobBaseFeeScalar()
```

**IMPORTANT:** `eth_estimateGas` on OP Stack chains only returns L2 execution gas. Total cost = L2 gas + L1 data fee.

### Arbitrum

**ArbGasInfo** (`0x000000000000000000000000000000000000006C`):
```json
// Get L1 gas pricing info
// getPricesInWei(), getL1BaseFeeEstimate(), getCurrentTxL1GasFees()
```

**ArbSys** (`0x0000000000000000000000000000000000000064`):
```json
// Get L2 block number (different from L1)
{"method": "eth_call", "params": [{"to": "0x64", "data": "0xa3b1b31d"}, "latest"]}
// arbBlockNumber()
```

### zkSync

```json
// Get raw block transactions (includes L1→L2 messages)
{"method": "zks_getRawBlockTransactions", "params": [blockNumber]}

// Get bridge contracts
{"method": "zks_getBridgeContracts", "params": []}

// Get L1 batch details
{"method": "zks_getL1BatchDetails", "params": [batchNumber]}
```

### Hardhat Network (Local Development)

```json
// Set arbitrary balance
{"method": "hardhat_setBalance", "params": ["0xAddr", "0xDE0B6B3A7640000"]}

// Set storage slot
{"method": "hardhat_setStorageAt", "params": ["0xAddr", "0xSlot", "0xValue"]}

// Impersonate account
{"method": "hardhat_impersonateAccount", "params": ["0xAddr"]}

// Reset fork
{"method": "hardhat_reset", "params": [{"forking": {"jsonRpcUrl": "url", "blockNumber": 19000000}}]}
```

### Anvil (Foundry Local Node)

```json
// Set balance
{"method": "anvil_setBalance", "params": ["0xAddr", "0xAmount"]}

// Set code
{"method": "anvil_setCode", "params": ["0xAddr", "0xBytecode"]}

// Set storage
{"method": "anvil_setStorageAt", "params": ["0xAddr", "0xSlot", "0xValue"]}

// Impersonate
{"method": "anvil_impersonateAccount", "params": ["0xAddr"]}

// Snapshot & revert
{"method": "evm_snapshot", "params": []}
{"method": "evm_revert", "params": ["0xSnapshotId"]}

// Mine blocks
{"method": "anvil_mine", "params": [numBlocks, intervalSeconds]}
```

### Tenderly Virtual TestNet

```json
// Set ETH balance
{"method": "tenderly_setBalance", "params": ["0xAddr", "0xAmount"]}

// Set ERC-20 balance (auto-detects storage slot)
{"method": "tenderly_setErc20Balance", "params": ["0xToken", "0xWallet", "0xAmount"]}
```

---

## MegaETH-Specific RPC

```json
// Synchronous receipt (instant confirmation, EIP-7966)
{"method": "eth_sendRawTransactionSync", "params": ["0xSignedTx"]}
// Returns receipt immediately instead of tx hash

// Paginated log queries
{"method": "eth_getLogsWithCursor", "params": [{"address": "0x...", "topics": [...], "cursor": "..."}]}

// Subscribe to miniBlocks (WebSocket)
{"method": "eth_subscribe", "params": ["miniBlock"]}
```

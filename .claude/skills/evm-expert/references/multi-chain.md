# Multi-Chain EVM Reference

Comprehensive reference for EVM-compatible chains. Covers chain-specific gas models, precompiles, address derivation differences, and critical gotchas.

---

## Chain Overview

| Chain | ID | Block Time | Finality | EVM Version | Gas Limit | Architecture |
|-------|----|-----------|----------|-------------|-----------|-------------|
| Ethereum | 1 | ~12s | ~15min (32 slots) | cancun | 30M | Canonical EVM |
| Arbitrum One | 42161 | ~0.25s | ~7 days (optimistic) | cancun | 32M L2 | Nitro (optimistic rollup) |
| Optimism | 10 | 2s | ~7 days (optimistic) | cancun | 30M | OP Stack |
| Base | 8453 | 2s | ~7 days (optimistic) | cancun | 30M | OP Stack |
| Polygon PoS | 137 | ~2s | ~30min (checkpoint) | cancun | 30M | Sidechain (own validators) |
| Polygon zkEVM | 1101 | ~5-10s | ~30min (ZK proof) | cancun | 20M | Type-2 ZK rollup |
| zkSync Era | 324 | ~1-2s | ~1hr (ZK proof) | paris (no PUSH0) | varies | zkEVM |
| BNB Smart Chain | 56 | ~3s | ~45s | cancun | 140M | PoSA sidechain |
| Avalanche C-Chain | 43114 | ~2s | ~1s (Snowman) | cancun | 15M | Snowman consensus |
| Monad | 143 | 400ms | 800ms | cancun | 200M (target 160M) | Parallel execution |
| MegaETH | 4326 | realtime | ~1s | custom | varies | Real-time L2 |
| Sei | 1329 | ~390ms | ~390ms (single-slot) | paris (no PUSH0) | varies | Parallel EVM + Cosmos |

---

## Ethereum L2 Architectures

### OP Stack (Optimism, Base, Zora, Mode, etc.)

All OP Stack chains share identical predeploy addresses:

| Predeploy | Address | Purpose |
|-----------|---------|---------|
| L2CrossDomainMessenger | `0x4200000000000000000000000000000000000007` | Cross-chain messaging |
| L2StandardBridge | `0x4200000000000000000000000000000000000010` | Token bridging |
| GasPriceOracle | `0x420000000000000000000000000000000000000F` | L1 data fee calculation |
| L1Block | `0x4200000000000000000000000000000000000015` | L1 block info (number, timestamp, basefee, blobBaseFee) |
| WETH9 | `0x4200000000000000000000000000000000000006` | Wrapped ETH |
| GovernanceToken (OP) | `0x4200000000000000000000000000000000000042` | OP token on L2 |
| L2ToL1MessagePasser | `0x4200000000000000000000000000000000000016` | Withdrawal initiation |
| SuperchainTokenBridge | `0x4200000000000000000000000000000000000028` | Cross-Superchain token bridge |

**Gas Model (Post-Ecotone):**
```
l1DataFee = (l1BaseFeeScalar * l1BaseFee * 16 + l1BlobBaseFeeScalar * l1BlobBaseFee) * compressedTxSize / 1e6
totalFee = l2ExecutionFee + l1DataFee
```
- `eth_estimateGas` only returns L2 execution gas — NOT total cost
- Use `GasPriceOracle.getL1Fee(txData)` for L1 data component

**L2→L1 Withdrawals (3-step, 7-day challenge):**
1. Initiate on L2 via `L2ToL1MessagePasser`
2. Prove on L1 after state root posted (~1-3 hours)
3. Finalize on L1 after 7-day challenge period

**Sender Aliasing:** L1 → L2 contracts add `0x1111000000000000000000000000000000001111` to the sender address (prevents address collision attacks).

### Arbitrum (Nitro)

**ArbOS Precompiles:**
| Precompile | Address | Purpose |
|-----------|---------|---------|
| ArbSys | `0x0000000000000000000000000000000000000064` | L2 block number, withdrawals |
| ArbRetryableTx | `0x000000000000000000000000000000000000006E` | Retryable ticket management |
| ArbGasInfo | `0x000000000000000000000000000000000000006C` | Gas price info |
| ArbAggregator | `0x000000000000000000000000000000000000006D` | Batch poster info |
| ArbWasm | `0x0000000000000000000000000000000000000071` | Stylus WASM program management |

**Arbitrum Stylus:**
- WASM-based execution alongside EVM (shared state and storage)
- 10-100x gas savings for compute-heavy operations
- Two-step deploy: deploy bytecode → activate via `ArbWasm.activateProgram(address)` (~14M gas)
- Storage: `StorageU256` at slot 0 = Solidity `uint256` at slot 0 (fully compatible)
- Limitation: cannot use CREATE/CREATE2 from WASM — factory patterns must be Solidity

**Gas:** Separate L1 + L2 components. `eth_estimateGas` returns only L2 portion. Use `ArbGasInfo` for L1 data component.

---

## ZK Rollups

### zkSync Era

**System Contracts (0x8000+ range):**
| Contract | Address | Purpose |
|----------|---------|---------|
| Bootloader | `0x0000000000000000000000000000000000008001` | Transaction processing |
| NonceHolder | `0x0000000000000000000000000000000000008003` | Nonce management |
| ContractDeployer | `0x0000000000000000000000000000000000008006` | All deployments go through here |
| L1Messenger | `0x0000000000000000000000000000000000008008` | L2→L1 messaging |
| MsgValueSimulator | `0x0000000000000000000000000000000000008009` | ETH value transfers |
| SystemContext | `0x000000000000000000000000000000000000800b` | Block/tx context |

**Critical Differences:**
- **CREATE2 formula is DIFFERENT**: `keccak256(0xff ++ deployer ++ salt ++ keccak256(bytecodeHash) ++ keccak256(constructorInput))` — includes constructor args!
- **No PUSH0 opcode** — compile with `--evm-version paris`
- **All accounts are smart accounts** — no EOAs at protocol level
- Uses `zksolc` compiler (not standard `solc`) — bytecodeHash instead of creation code
- `EXTCODECOPY` only works for self (cannot copy other contracts' code)
- No `SELFDESTRUCT`
- Gas per pubdata: `DEFAULT_GAS_PER_PUBDATA_LIMIT = 50,000`

**Native Account Abstraction:**
- Paymasters: General (arbitrary validation) and Approval-based (ERC-20 payment)
- All transactions can specify a paymaster in the transaction itself (no separate UserOp)

### Polygon zkEVM

- Type-2 ZK rollup (aims for EVM equivalence)
- Chain ID: 1101 (mainnet), 2442 (Cardona testnet)
- LxLy bridge for L1↔L2 with Merkle proofs
- Transaction states: Trusted → Virtual → Consolidated
- AggLayer: unified bridge across multiple Polygon chains

---

## Parallel Execution Chains

### Monad

**Optimistic concurrency control:**
- Transactions execute in parallel, re-execute on conflict
- 400ms block time, 800ms finality
- Per-transaction gas limit: 30M (block: 200M, target 160M)

**Opcode Repricing (CRITICAL — breaks gas assumptions):**
| Operation | Ethereum | Monad | Multiplier |
|-----------|----------|-------|-----------|
| Cold account access | 2,600 | 10,100 | ~4x |
| Cold storage access | 2,100 | 8,100 | ~4x |
| ecRecover | 3,000 | 6,000 | 2x |
| ecMul | 6,000 | 30,000 | 5x |
| ecPairing base | 45,000 | 225,000 | 5x |

**Other Differences:**
- **Gas limit charging** (not gas used) — entire gas limit deducted from balance
- 128 KB contract size limit (vs 24.5 KB on Ethereum)
- Min base fee: 100 MON-gwei
- No EIP-4844 blob support
- Reserve balance: ~10 MON required
- Staking precompile at `0x0000000000000000000000000000000000001000`

### Sei

**EVM ↔ CosmWasm Interoperability:**
| Precompile | Address | Purpose |
|-----------|---------|---------|
| Bank | `0x...1001` | Native token transfers |
| Wasm | `0x...1002` | CosmWasm contract calls from EVM |
| JSON | `0x...1003` | JSON parsing in EVM |
| Address | `0x...1004` | EVM ↔ Cosmos address conversion |
| Staking | `0x...1005` | Delegation operations |
| Governance | `0x...1006` | Voting |
| Distribution | `0x...1007` | Claim rewards |
| IBC | `0x...1009` | Cross-chain transfers |
| Pointer | `0x...100b` | EVM ↔ CosmWasm token interop |

**Critical:** SEI has different decimal representations: 18 (EVM wei) = 6 (Cosmos usei). Pointer contracts enable ERC20↔CW20 and ERC721↔CW721 interop without wrapping.

---

## MegaETH

- **Intrinsic gas: 60,000** (not 21,000) — 21K compute + 39K storage
- SSTORE costs: multiplied by bucket factor (1x = 22.1K gas, 100x = 2.002M gas)
- 512 KB contract code limit (vs 24.5 KB Ethereum)
- 128 KB calldata limit
- `eth_sendRawTransactionSync` — real-time receipts (EIP-7966)
- Gas forwarding: 98/100 (more gas in nested calls than Ethereum's 63/64)
- GasPriceOracle at `0x6342000000000000000000000000000000000002` (microsecond timestamps)

---

## Sidechain Considerations

### BNB Smart Chain (Chain ID 56)
- POA chain — extra `extraData` header field
- Requires `ExtraDataToPOAMiddleware` in Web3.py
- ~3s block time, 140M gas limit
- Different validator set from Ethereum

### Polygon PoS (Chain ID 137)
- Own validator set with checkpoint model on Ethereum L1
- **NOT a true L2** — has own security assumptions
- POL token migration from MATIC
- RootChain (L1): `0x86E4Dc95c7FBdBf52e33D563BbDB00823894C287`
- WPOL (L2): `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270`

### Avalanche C-Chain (Chain ID 43114)
- Snowman consensus (~2s blocks, ~1s finality)
- EVM-compatible with standard tooling
- POA-like extra header fields

---

## Cross-Chain Gotchas Summary

| Issue | Chains Affected | Impact |
|-------|----------------|--------|
| `eth_estimateGas` only returns L2 gas | All L2s | Underestimates actual cost |
| No PUSH0 opcode | zkSync, Sei | Must compile with `paris` target |
| Different CREATE2 formula | zkSync | Deterministic addresses don't match |
| Cold access 4x more expensive | Monad | Gas estimates from Ethereum are wrong |
| Intrinsic gas 60K not 21K | MegaETH | Simple transfers cost more |
| All accounts are smart contracts | zkSync | No EOA assumptions |
| Extra header fields (POA) | BSC, Polygon, Avalanche | Needs middleware for web3.py |
| Sender aliasing on L1→L2 | OP Stack chains | `msg.sender` offset on L2 |
| USDC vs USDC.e (native vs bridged) | Most L2s | Different contract addresses |
| Token decimals vary | All | USDC=6, DAI=18, WBTC=8 — never assume 18 |

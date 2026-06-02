---
name: evm-expert
description: EVM and EVM-compatible chain expert. Use when working with Solidity, Vyper, bytecode, transaction traces, callstacks, logs/events, storage layout, RPC calls, simulation, on-chain data reading, ABI encoding/decoding, oracles, cross-chain messaging, account abstraction, DeFi protocol integration, security analysis, or any Ethereum/EVM-compatible chain task.
---

You are a deep expert in the Ethereum Virtual Machine (EVM) and all EVM-compatible chains. You have comprehensive knowledge of Solidity, Vyper, EVM bytecode, JSON-RPC, transaction tracing, on-chain data analysis, DeFi protocol integration, oracle systems, cross-chain messaging, account abstraction, and smart contract security. Apply the knowledge below and reference the companion files in the `references/` directory for detailed lookups.

# Reference Index

All detailed reference material lives in `references/`. Consult the appropriate file for deep dives:

| File | Contents |
|------|----------|
| `references/evm-internals.md` | Opcode tables, gas costs, memory layout, EIP reference, chain differences |
| `references/solidity-patterns.md` | Solidity/Vyper patterns, DeFi patterns, OZ v5, non-standard tokens (proxies live in `proxies.md`) |
| `references/proxies.md` | Proxy / upgradeable / delegate patterns: EIP-1167/1822/1967/2535/3448/7702, beacon, Diamond, Safe, DSProxy, ERC-6900/7579, detection cheatsheet |
| `references/rpc-and-tracing.md` | JSON-RPC methods, debug/trace namespaces, simulation recipes, L2-specific RPC, external lookup APIs |
| `references/defi-protocols.md` | Uniswap, Aave, Curve, Compound, Maker, Morpho, GMX, Pendle, Lido, EigenLayer, ERC-4626 |
| `references/multi-chain.md` | Chain-specific details: OP Stack, Arbitrum, zkSync, Polygon, Monad, MegaETH, Sei, gas models |
| `references/oracles.md` | Chainlink, Pyth, Redstone: staleness checks, L2 sequencer feeds, decimal normalization |
| `references/security-toolchain.md` | Slither, Echidna, Halmos, Mythril, Certora, Semgrep: analysis workflow, invariant templates |
| `references/cross-chain.md` | LayerZero, Wormhole, Axelar, Hyperlane, CCIP: chain ID mappings, integration patterns |
| `references/account-abstraction.md` | ERC-4337, EIP-7702, Safe, Permit2, ENS, OZ AccessManager, smart account patterns |
| `references/contract-addresses.md` | Production addresses: tokens, DEXes, lending, oracles, bridges — per chain |
| `references/tooling.md` | Foundry, Hardhat, viem, ethers.js, wagmi, cast, Tenderly, The Graph, research tools |
| `references/project-integration.md` | Project-specific codebase integration (EvmAPI, AI tools, DB utilities) |

---

# Core EVM Concepts

## Architecture
- **Stack machine**: 1024 max depth, 256-bit (32-byte) word size
- **Memory**: byte-addressable, linear, volatile (per-call), expands in 32-byte words, costs gas quadratically
- **Storage**: key-value store, 256-bit keys to 256-bit values, persistent across calls, 20,000 gas for SSTORE (cold), 100 gas for SLOAD (warm after EIP-2929)
- **Calldata**: immutable byte array, the input to a transaction or message call
- **Returndata**: byte array returned by the last external call (RETURNDATASIZE, RETURNDATACOPY)
- **Code**: immutable byte array of the contract's deployed bytecode
- **Transient storage** (EIP-1153): TLOAD/TSTORE, cleared after transaction — cheap reentrancy locks

## Gas & EVM Execution
- Each opcode has a fixed base gas cost; some (SSTORE, CALL, CREATE) have dynamic costs
- EIP-2929 (Berlin): cold/warm access lists — first access to a storage slot or address costs more
- EIP-1559: base fee + priority fee; `BASEFEE` opcode
- EIP-3529 (London): reduced gas refunds for SSTORE/SELFDESTRUCT
- EIP-4844 (Dencun): blob transactions for L2 data availability; `BLOBBASEFEE` opcode
- Gas estimation: `eth_estimateGas` simulates execution and returns gas needed
- **L2 WARNING**: `eth_estimateGas` only returns L2 execution gas on rollups — use GasPriceOracle for L1 data component

## Account Model
- **EOA** (Externally Owned Account): has nonce, balance; no code, no storage
- **Contract**: has nonce, balance, code, storage; code is immutable after deployment (except proxies)
- **Smart Account** (ERC-4337): contract that validates UserOperations
- **Delegated EOA** (EIP-7702): EOA temporarily executing smart contract code

## Transaction Types
- **Type 0** (Legacy): `{nonce, gasPrice, gasLimit, to, value, data, v, r, s}`
- **Type 1** (EIP-2930): adds `accessList`
- **Type 2** (EIP-1559): `{maxFeePerGas, maxPriorityFeePerGas}` replaces `gasPrice`
- **Type 3** (EIP-4844): blob transactions for L2 data availability
- **Type 4** (EIP-7702): EOA code delegation with authorization list

---

# Quick Reference: Reading On-Chain Data

| Task | Method / Command |
|------|-----------------|
| Read storage slot | `cast storage <addr> <slot>` / `eth_getStorageAt` |
| Get bytecode | `cast code <addr>` / `eth_getCode` |
| Check proxy impl | `cast storage <addr> 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` |
| Read function | `cast call <addr> "fn(types)(returns)" args` / `eth_call` |
| Get token info | `cast call <addr> "symbol()"`, `"decimals()"`, `"totalSupply()"` |
| Simulate tx | `eth_call` with state overrides (3rd param) |
| Trace tx | `debug_traceTransaction` (Geth) / `trace_replayTransaction` (Erigon) |
| Filter logs | `cast logs --address <addr> --topic0 <sig>` / `eth_getLogs` |
| Batch reads | Multicall3 at `0xcA11bde05977b3631167028862bE2a173976CA11` |

---

# Solidity Storage Layout (Quick Rules)

1. Simple variables: packed right-to-left into 32-byte slots
2. Mappings: `mapping(K => V)` at slot `p` → value at `keccak256(abi.encode(k, p))`
3. Nested mappings: `keccak256(abi.encode(k2, keccak256(abi.encode(k1, p))))`
4. Dynamic arrays: length at slot `p`, elements at `keccak256(p) + i`
5. Strings/bytes: if ≤31 bytes, in-slot; if ≥32 bytes, data at `keccak256(p)`
6. Proxy implementation: EIP-1967 slot `0x360894...bbc` (full proxy pattern catalog in `references/proxies.md`)

---

# ABI Encoding Quick Reference

| Type | Encoding |
|------|----------|
| Static (uint256, address, bool) | Left-padded to 32 bytes |
| Dynamic (bytes, string, T[]) | Offset pointer → length → data |
| Function call | `selector (4 bytes) + abi.encode(args)` |
| Event | topic0 = keccak256(sig), indexed as topics, rest as data |

**Common Selectors:** `transfer` = `0xa9059cbb`, `approve` = `0x095ea7b3`, `balanceOf` = `0x70a08231`

---

# DeFi Integration Essentials

See `references/defi-protocols.md` for complete details.

## Fixed-Point Arithmetic (CRITICAL)
| System | Decimals | Used By |
|--------|----------|---------|
| wad | 18 | Maker tokens, most ERC-20s |
| ray | 27 | Maker rates, Aave indices |
| rad | 45 | Maker Vat internal balance |
| Q64.96 | 96-bit fractional | Uniswap V3 sqrtPriceX96 |
| 30-decimal USD | 30 | GMX V2 sizeDeltaUsd |

## Rebasing Tokens (NEVER store balances directly)
- **stETH**: use wstETH for accounting (1-2 wei rounding loss per transfer)
- **aTokens**: use scaledBalanceOf() (balance changes every block)

## Key Protocol Gotchas
- **Curve**: no universal ABI — each pool type has different function signatures
- **Maker**: MUST call `jug.drip(ilk)` before calculating debt
- **GMX**: multicall is MANDATORY for order creation, 30-decimal USD
- **Morpho**: market ID = `keccak256(abi.encode(...))`, 36-adjusted oracle decimals

---

# Oracle Integration Essentials

See `references/oracles.md` for complete details.

**Always check staleness.** On L2s, **always check sequencer uptime feed.**

| Oracle | Model | Key Pattern |
|--------|-------|-------------|
| Chainlink | Push (on-chain feeds) | `latestRoundData()` + staleness check |
| Pyth | Pull (update in calldata) | Update + read in same tx |
| Redstone | Push + Pull | Calldata-embedded signed packages |

**L2 Sequencer Feeds:** Arbitrum `0xFdB631F5...`, Optimism `0x371EAD81...`, Base `0xBCF85224...`

---

# Multi-Chain Quick Reference

See `references/multi-chain.md` for complete details.

| Chain | ID | Key Difference |
|-------|-----|---------------|
| Ethereum | 1 | Canonical EVM (cancun) |
| Arbitrum | 42161 | Nitro L2, ArbOS precompiles 0x64-0x71 |
| Optimism | 10 | OP Stack, predeploys at 0x4200... |
| Base | 8453 | OP Stack + Coinbase Smart Wallet |
| Polygon | 137 | Sidechain (own validators), NOT a true L2 |
| zkSync | 324 | Different CREATE2, no PUSH0, all smart accounts |
| Monad | 143 | Parallel exec, cold access 4x cost, gas limit charging |
| MegaETH | 4326 | 60K intrinsic gas, instant receipts |
| Sei | 1329 | EVM↔CosmWasm interop via precompiles |

---

# Security Quick Reference

See `references/security-toolchain.md` for complete details.

**Analysis Workflow:** Slither (seconds) → Semgrep (seconds) → Echidna (minutes) → Halmos (minutes) → Mythril (hours) → Certora (hours)

**Top Vulnerability Patterns:**
- Reentrancy → CEI + ReentrancyGuard
- Oracle manipulation → TWAP, staleness checks, Chainlink
- First-depositor inflation (ERC-4626) → virtual offset
- Signature replay → EIP-712 + nonce + deadline + chainId
- USDT approve quirk → SafeERC20.forceApprove()
- Proxy storage collision → EIP-1967 standard slots, ERC-7201 namespaced storage

---

# Cross-Chain Quick Reference

See `references/cross-chain.md` for complete details.

**CRITICAL: No protocol uses standard EVM chain IDs.** Each has its own identifier system.

| Protocol | Ethereum ID | Address Pattern |
|----------|------------|----------------|
| LayerZero V2 | eid 30101 | EndpointV2: `0x1a44076...` (all chains) |
| Wormhole | chain 2 | Core: `0x98f3c9e6...` (Ethereum) |
| Axelar | "ethereum" (string) | Gateway: `0x4F4495...` (Ethereum) |
| CCIP | selector `5009297...` | Router per chain |

---

# Account Abstraction Quick Reference

See `references/account-abstraction.md` for complete details.

| Standard | Key Contract | Pattern |
|----------|-------------|---------|
| ERC-4337 | EntryPoint `0x0000000071727De22E5E9d8BAf0edAc6f37da032` | UserOp → Bundler → EntryPoint → Account |
| EIP-7702 | N/A (tx type) | EOA delegates to implementation contract |
| Safe | Singleton `0x41675C...` | M-of-N multisig with modules |
| Permit2 | `0x000000000022D473...` | One-time approve, per-op signatures |

---

# Foundry Quick Reference

See `references/tooling.md` for complete details.

```bash
# Build & test
forge build && forge test -vvvv

# Fork mainnet at block
forge test --fork-url $RPC --fork-block-number 19000000

# Inspect contract
forge inspect MyContract storage-layout
forge inspect MyContract abi

# Chain interaction
cast call <addr> "balanceOf(address)(uint256)" <user> --rpc-url $RPC
cast storage <addr> <slot> --rpc-url $RPC
cast sig "transfer(address,uint256)"    # → 0xa9059cbb
cast 4byte 0xa9059cbb                  # → transfer(address,uint256)
cast tx <hash> --rpc-url $RPC          # transaction details
cast receipt <hash> --rpc-url $RPC     # receipt with logs

# Local node with fork
anvil --fork-url $RPC --fork-block-number 19000000
```

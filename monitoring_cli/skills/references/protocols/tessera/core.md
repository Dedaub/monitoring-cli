# Tessera ("Tessera V") — Topics, Selectors, Addresses (EVM: Base + BNB Chain)

**Status:** verified against live RPC (publicnode), the **verified Blockscout source** of `TesseraSwap` on Base, locally-recomputed keccak topic0/selectors, and DefiLlama's own volume adapter, on **2026-06-05**.
**Scope:** Tessera is a Wintermute-operated **proprietary / "dark" oracle-priced AMM**. Its primary venue is **Solana** (program `TessVdML9pBGgG9yGks7o4HewRaXVAMuoVj4x83GLQH`, branded "Tessera V", live on Jupiter since 2025‑06). On **EVM** it is deployed as a single immutable settlement contract, `TesseraSwap`, on exactly **two** chains:

| Chain | Chain ID | TesseraSwap | Live since | Verified |
|-------|----------|-------------|-----------|----------|
| **Base** | 8453 | `0x55555522005BcAE1c2424D474BfD5ed477749E3e` | block 37,518,648 · **2025‑10‑30** | yes (Blockscout, "TesseraSwap") |
| **BNB Smart Chain** | 56 | `0x55555522005BcAE1c2424D474BfD5ed477749E3e` | **≈2025‑11‑13** (DefiLlama adapter start) | bytecode byte‑identical to Base |

> **Not deployed (verified `eth_getCode → 0x`) on the other 5 requested chains** — Ethereum (1), Avalanche C‑Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137) — **nor on 20 other EVM chains swept**: Unichain, Berachain, Mantle, Linea, Scroll, Blast, Sei, Sonic, opBNB, Gnosis, Celo, Mode, Polygon zkEVM, Fantom, Ink, HyperEVM, Katana, Plume, Abstract, Worldchain. The vanity address `0x5555…9E3e` has **no code** on any of them. It is a **CREATE2-mined vanity address** (a non-vanity deployer EOA cannot produce a `0x55555522…` address via plain `CREATE`), so a future expansion will almost certainly reuse the **same address** on the new chain — a cheap `eth_getCode` poll at `0x5555…9E3e` is the early-warning tripwire.

This is **not** a Uniswap-style multi-contract, multi-version system. The entire EVM surface is:

1. **`TesseraSwap`** — a ~4.3 KB immutable, non-proxy settlement shell (the only thing that emits events). Same address + byte-identical bytecode on Base and BSC.
2. **`TesseraEngine`** (`ITesseraEngine`) — an **unverified** ~15.6 KB pricing brain that `TesseraSwap` delegates all quoting to. Hot-swappable via `changeTesseraEngine`. Emits **no events** (price updates are pure storage writes — fully "dark").
3. **`tesseraTreasury`** — the market-maker inventory account that funds every fill (grants ~infinite ERC-20 allowance to `TesseraSwap`).
4. **`tesseraOwner`** — a **Gnosis Safe** multisig (per chain) that owns both the swap and the engine.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 TesseraSwap — the **only** event emitted anywhere in the EVM deployment

| topic0 | Event |
|--------|-------|
| `0x97ba0cd8ff13f074b3b1aeace7fa3bf7fe54bdf2d728b6a097e901073b2bad6a` | `TesseraTrade(address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut, address recipient)` |

- **All five fields are non-indexed** (only `topic0` is present; `topics.length == 1`, `data` = 5 × 32-byte words = 160 bytes). You **cannot** filter by token/recipient via topics — decode the `data`.
- `amountIn` is denominated in `tokenIn`, `amountOut` in `tokenOut`. `recipient` is who received `tokenOut` (often an aggregator/router, not the end user).
- Emitted by **both** swap entrypoints (`tesseraSwapWithAllowances` and `tesseraSwapWithCallback`) on the last line, after settlement.
- **`TesseraEngine` emits nothing.** There is no `PriceUpdated`, `EngineChanged`, `TreasuryChanged`, `Killed`, or `OwnershipTransferred` event anywhere — confirmed by an address-filtered log scan returning only `TesseraTrade`. Admin/price changes are **invisible to log subscribers**; detect them via inbound-tx selector matching (§5) or state polling.

To discover every Tessera trade on a chain, subscribe to `topic0 = 0x97ba0cd8…bad6a` filtered to the single `TesseraSwap` address. (publicnode silently returns `[]` for topic-only filters with no `address` — always pin the address.)

---

## 2. Function signatures (chain-agnostic)

Selectors are `keccak256(canonical signature)[0:4]`, **recomputed locally** and matched against the deployed dispatcher (`PUSH4` scan) — all 6 `TesseraSwap` selectors verified present.

### 2.1 TesseraSwap (`0x5555…9E3e`) — full interface (6 functions, nothing else)

| Selector | Signature | Mutability / notes |
|----------|-----------|--------------------|
| `0x3ae8b298` | `tesseraSwapWithAllowances(address tokenIn, address tokenOut, int256 amountSpecified, uint256 amountCheck, address recipient, bytes swapData)` | nonpayable. **Dominant path.** Pulls `tokenIn` from `msg.sender` via allowance, pays `tokenOut` from treasury. Emits `TesseraTrade`. |
| `0x15b8527c` | `tesseraSwapWithCallback(address tokenIn, address tokenOut, int256 amountSpecified, uint256 amountCheck, address recipient, bytes callbackData, bytes swapData)` | nonpayable, **`nonReentrant`**. Flash-style: pays `tokenOut` to `recipient`, then calls `msg.sender.tesseraSwapCallback(amountIn, -amountOut, callbackData)`; requires `tokenIn` balance to have increased by `amountIn` (else revert `"WTA"`). |
| `0x77f65f98` | `tesseraSwapViewAmounts(address tokenIn, address tokenOut, int256 amountSpecified)` | **view (quoter)**. Returns `(uint256 amountIn, uint256 amountOut)` from `engine.swapAmountView`. |
| `0x71ba2687` | `changeTesseraEngine(address newTesseraEngine)` | **owner-only** (`require(msg.sender == tesseraOwner, "ACE")`). Hot-swaps the pricing engine. No event. |
| `0xeeb69de2` | `changeTesseraTreasury(address newTesseraTreasury)` | **owner-only**. Repoints the inventory account. No event. |
| `0x3bf8d620` | `rescueTokens(address[] tokens, uint256[] amounts)` | **owner-only**. Sweeps tokens/ETH **to `tesseraTreasury`** (not arbitrary). `token == address(0)` ⇒ ETH. No event. |

**`amountSpecified` is signed (`int256`)** — exact-in vs exact-out, Uniswap-style:
- `amountSpecified > 0` → **exact input**; check is `amountOut >= amountCheck` (min-out / slippage floor).
- `amountSpecified < 0` → **exact output**; check is `amountIn <= amountCheck` (max-in / slippage cap).
- Failing the check reverts `"ACF"` (Amount Check Failed).

**Settlement (the part that matters for inventory/drain monitoring):** in `tesseraSwapWithAllowances` the order is `tokenOut.safeTransferFrom(treasury → recipient, amountOut)` then `tokenIn.safeTransferFrom(msg.sender → treasury, amountIn)`. The **treasury is the counterparty to every trade** and must keep `TesseraSwap` approved.

Revert-string vocabulary: `"ACF"` (slippage), `"WTA"` (callback under-repay), `"ACE"` (not owner), `"ETH transfer failed"`. Custom errors (OZ v5): `ReentrancyGuardReentrantCall()`, `SafeERC20FailedOperation(address)`.

### 2.2 ITesseraEngine (`0x31e9…0c17`, unverified) — pricing brain

The swap contract calls exactly two engine methods; the rest are admin/registry selectors recovered from the engine's own bytecode (`PUSH4` scan) and resolved via openchain (recomputed to confirm).

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe70c3a4d` | `swapAmount(address tokenIn, address tokenOut, int256 amountSpecified, address sender, bytes swapData)` | Returns `(uint256 amountIn, uint256 amountOut)`. **Where the quote is computed** from the signed/oracle `swapData`. State-mutating (records fill). |
| `0x77c8b706` | `swapAmountView(address tokenIn, address tokenOut, int256 amountSpecified, address sender)` | view. Backs `tesseraSwapViewAmounts`. |
| `0x0329dd62` | `multiSigOwner()` | Returns the controlling Safe (== `tesseraOwner`). |
| `0x22f3e2d4` | `isActive()` | Global live flag. Live value = `true` on both chains. |
| `0x1c02708d` | `killContract()` | **Kill switch (pause).** Owner-gated. No event — flips `isActive()`. |
| `0x6b410e34` | `unkillContract()` | Un-pause. |
| `0x542b7984` | `getAllTesseraPools()` | Returns `address[]` of internal pricing-bucket keys (11 on Base, 16 on BSC at time of writing). **These are zero-code registry addresses, not contracts** — do not monitor them as deployments. |
| `0xeb101276` | `globalPrioFeeThresholddd1337()` | Priority-fee gate. Live value = `0x77359400` = **2 gwei** — swaps/updates must be top-of-block (anti-backrun). |

Other engine selectors exist (≈30 more, mostly unnamed custom pricing/config logic) and are intentionally opaque. The engine also references ERC-1967 errors (`ERC1967NonPayable`, `AddressEmptyCode`) but is **not itself a proxy** (impl slot zero).

### 2.3 Integrator-side callback

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5e176d5d` | `tesseraSwapCallback(int256 amount0Delta, int256 amount1Delta, bytes data)` | Implemented by **callers** of `tesseraSwapWithCallback` (passed `(amountIn, -amountOut, callbackData)`). Tessera itself does not implement it. |

---

## 3. Addresses — Base mainnet (chain ID 8453)

All verified via `eth_getCode` (non-empty) on `https://base-rpc.publicnode.com` and Blockscout. Storage roles decoded from the verified source (`tesseraEngine`=slot0, `tesseraTreasury`=slot1, `tesseraOwner`=slot2) + constructor args.

| Role | Address | One-liner |
|------|---------|-----------|
| **TesseraSwap** (settlement, verified) | `0x55555522005BcAE1c2424D474BfD5ed477749E3e` | The only event source. Immutable, non-proxy, ~4.3 KB. Emits `TesseraTrade`. |
| **TesseraEngine** (`ITesseraEngine`, unverified) | `0x31e99e05Fee3DcE580Af777c3Fd63ee1B3B40c17` | Off-chain-priced quoting brain. ~15.6 KB. Hot-swappable. Emits nothing. Same address on BSC. |
| **tesseraTreasury** (inventory, current) | `0x3DbE077E7986657E95e1CC50089F17a5a4Af0aaE` | MM inventory; counterparty to every fill; grants ~∞ allowance to TesseraSwap. ~4.1 KB contract. Same address on BSC. |
| **tesseraTreasury** (deploy-time, since rotated) | `0xc2cA2485618Af14135E79487492c3A4F2A062Ed5` | Original treasury from constructor; replaced via `changeTesseraTreasury`. Kept for historical-trace decoding. |
| **tesseraOwner / multiSigOwner** (admin) | `0xdbd31ea3DE20a2B36a5bd36c7167699F2450b5C6` | **Gnosis Safe** (`SafeProxy`, master_copy). Owns swap **and** engine. ACE-gated admin. |
| **Deployer (EOA)** | `0xbf2cCF4f2fb47e2159c9F86CB4D4956aa53B64CF` | Created TesseraSwap (tx `0xf1b7997a…3bd500c0`, block 37,518,648). |

Quote assets in practice: **WETH** `0x4200000000000000000000000000000000000006`, **USDC** `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, **cbBTC** `0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf`. ~67% of volume is WETH/USDC, ~29% cbBTC/USDC.

---

## 4. Addresses — BNB Smart Chain (chain ID 56)

All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`. **TesseraSwap bytecode is byte-identical to Base** (same codehash `0xe1101bc87ea881dfbbdf09fb91e88a17e00c9486f98778df7bd4bc52a20d8e1c`). Engine and treasury share Base's addresses; **only the owner Safe differs**.

| Role | Address | One-liner |
|------|---------|-----------|
| **TesseraSwap** | `0x55555522005BcAE1c2424D474BfD5ed477749E3e` | Same address/bytecode as Base. |
| **TesseraEngine** | `0x31e99e05Fee3DcE580Af777c3Fd63ee1B3B40c17` | Same as Base. |
| **tesseraTreasury** | `0x3DbE077E7986657E95e1CC50089F17a5a4Af0aaE` | Same as Base (slot1 identical on-chain). |
| **tesseraOwner / multiSigOwner** (admin) | `0xae3C0084CA8cD758E220a61152ea80c1Ac2BfF74` | **Per-chain** Gnosis Safe (`SafeProxy`, 171 B). Differs from Base. |

---

## 5. Cross-chain summary & "versions"

| | Solana (primary) | Base (8453) | BNB Chain (56) | ETH / Avax / Arb / OP / Polygon |
|---|---|---|---|---|
| Present | **yes** (program `TessVdML…3GLQH`) | yes | yes | **no** (verified `0x`) |
| Live since | 2025‑06‑11 (Jupiter) | 2025‑10‑30 | ≈2025‑11‑13 | — |
| Settlement contract | Solana program | `TesseraSwap 0x5555…9E3e` | `TesseraSwap 0x5555…9E3e` | — |
| Engine | (program logic) | `0x31e9…0c17` | `0x31e9…0c17` (same) | — |
| Treasury | — | `0x3DbE…0aaE` | `0x3DbE…0aaE` (same) | — |
| Owner Safe | — | `0xdbd3…b5C6` | `0xae3C…fF74` (different) | — |

**On "versions":** the Solana brand is "Tessera **V**". On EVM the contract is plainly `TesseraSwap` with **no on-chain version suffix**, and there is currently **one live version** per chain. Upgrades happen two ways, neither of which is a proxy upgrade:
- **Engine rotation** — `changeTesseraEngine` repoints `TesseraSwap` to a new `ITesseraEngine` without redeploying the swap (the engine is where pricing "versions" live).
- **Full redeploy** — a new `TesseraSwap` at a new address (the current one is immutable). Track this by watching `eth_getCode` at `0x5555…9E3e` siblings / new Safe-deployed contracts.

---

## 6. Proxies (old & new)

**There are none.** Every Tessera EVM contract is **non-upgradeable / directly deployed**:
- `TesseraSwap` — EIP-1967 impl/beacon/admin slots all zero; Blockscout `proxy_type: None`. Immutable.
- `TesseraEngine` — impl slot zero; not a proxy (despite referencing ERC-1967 error selectors internally).
- `tesseraTreasury` — plain contract, impl slot zero.
- `tesseraOwner` — the **only** proxy in the system, and it's a **Gnosis Safe** `SafeProxy` (EIP-1167-style master-copy delegate), which is the admin, not a Tessera logic contract.

Mutability is achieved by **pointer swaps in storage** (`changeTesseraEngine`, `changeTesseraTreasury`), not bytecode upgrades. The owner pointer (`tesseraOwner`) has **no setter** — it is fixed at construction (no `transferOwnership`).

---

## 7. Detection invariants & gotchas (monitoring-grade)

- **One event, two chains, one address.** Watch `topic0 0x97ba0cd8…bad6a` at `0x55555522005BcAE1c2424D474BfD5ed477749E3e` on Base (8453) **and** BSC (56). That captures 100% of EVM trade flow.
- **Decode `data`, not topics** — all 5 fields are non-indexed. Layout: `[tokenIn][tokenOut][amountIn][amountOut][recipient]`, each a 32-byte word; addresses in the low 20 bytes.
- **The treasury is the counterparty.** `tokenOut` leaves `tesseraTreasury`; `tokenIn` arrives at it. For drain/inventory alerts, watch the treasury's balances and its allowance to `TesseraSwap` (currently ~`MaxUint256`). A sudden allowance revoke or treasury balance collapse is the meaningful signal — not the swap contract's own balance (it holds ~nothing between calls).
- **Trades usually arrive via aggregators**, so `tx.to` is typically a 1inch/0x/Bebop/router contract, with Tessera as one inner leg (`TesseraTrade` is one of many logs in the receipt). Don't expect `tx.to == TesseraSwap`. The callback variant (`0x15b8527c`) lets integrators repay flash-style.
- **Admin actions emit NO events.** To catch `changeTesseraEngine` / `changeTesseraTreasury` / `rescueTokens`, match inbound-tx **selectors** (`0x71ba2687` / `0xeeb69de2` / `0x3bf8d620`) to `0x5555…9E3e` with `from == tesseraOwner` (the Safe) — or diff storage slots 0/1 over time. A `changeTesseraEngine` to an unexpected address is the highest-severity event (it redirects all pricing).
- **The engine is dark and eventless.** Price/oracle updates happen as silent storage writes; `isActive()` and `killContract()`/`unkillContract()` (pause) flip with **no log**. Poll `isActive()` (selector `0x22f3e2d4`) on `0x31e9…0c17`, or watch Safe→engine transactions, to detect a pause/kill.
- **Priority-fee gate:** `globalPrioFeeThresholddd1337()` = 2 gwei — Tessera swaps are engineered to be top-of-block; low-priority-fee fills may revert.
- **`getAllTesseraPools()` returns zero-code addresses** — internal pricing buckets, not deployable contracts. Don't treat them as monitored targets.
- **No deployment on ETH / Avalanche / Arbitrum / Optimism / Polygon** as of 2026‑06‑05. Any future appearance should reuse `0x5555…9E3e` (deterministic) — a cheap `eth_getCode` poll on those chains is the early-warning tripwire.

---

## 8. Quick-copy constants (Postgres `bytea`-ready)

```
-- topic0 (the only Tessera event)
TesseraTrade            = '\x97ba0cd8ff13f074b3b1aeace7fa3bf7fe54bdf2d728b6a097e901073b2bad6a'

-- addresses (lowercase, no 0x) — Base (8453) AND BNB Chain (56) unless noted
TesseraSwap             = '\x55555522005bcae1c2424d474bfd5ed477749e3e'   -- both chains, identical bytecode
TesseraEngine           = '\x31e99e05fee3dce580af777c3fd63ee1b3b40c17'   -- both chains
tesseraTreasury         = '\x3dbe077e7986657e95e1cc50089f17a5a4af0aae'   -- both chains (current)
tesseraTreasury_orig    = '\xc2ca2485618af14135e79487492c3a4f2a062ed5'   -- Base deploy-time (rotated out)
tesseraOwner_base_safe  = '\xdbd31ea3de20a2b36a5bd36c7167699f2450b5c6'   -- Base Gnosis Safe (admin)
tesseraOwner_bsc_safe   = '\xae3c0084ca8cd758e220a61152ea80c1ac2bff74'   -- BSC  Gnosis Safe (admin)
deployer_base           = '\xbf2ccf4f2fb47e2159c9f86cb4d4956aa53b64cf'   -- Base deployer EOA

-- TesseraSwap function selectors
tesseraSwapWithAllowances = '\x3ae8b298'
tesseraSwapWithCallback   = '\x15b8527c'
tesseraSwapViewAmounts    = '\x77f65f98'
changeTesseraEngine       = '\x71ba2687'   -- admin (no event)
changeTesseraTreasury     = '\xeeb69de2'   -- admin (no event)
rescueTokens              = '\x3bf8d620'   -- admin (no event)

-- engine selectors of interest
engine_swapAmount         = '\xe70c3a4d'
engine_swapAmountView     = '\x77c8b706'
engine_isActive           = '\x22f3e2d4'
engine_killContract       = '\x1c02708d'
engine_unkillContract     = '\x6b410e34'
engine_multiSigOwner      = '\x0329dd62'
```

---

## 9. Verification & sources

**What was verified locally / on-chain (2026‑06‑05):**
- `TesseraTrade` topic0 recomputed with keccak (pycryptodome) and matched against 12,405 live Base logs / 7,041 live BSC logs in a 40k-block window (address-filtered). All 5 fields non-indexed (`topics.length == 1`, `data` = 160 B), matching a sample-decoded trade (WETH→USDC).
- All 6 `TesseraSwap` selectors recomputed with keccak and matched 1:1 to the dispatcher `PUSH4` set `{0x15b8527c, 0x3ae8b298, 0x3bf8d620, 0x71ba2687, 0x77f65f98, 0xeeb69de2}`.
- `eth_getCode` at `0x5555…9E3e`: 4,265 B on Base **and** BSC (byte-identical, codehash `0xe110…8e1c`); `0x` (empty) across **25 other EVM chains swept** — Ethereum, Avalanche, Arbitrum, Optimism, Polygon, Unichain, Berachain, Mantle, Linea, Scroll, Blast, Sei, Sonic, opBNB, Gnosis, Celo, Mode, Polygon zkEVM, Fantom, Ink, HyperEVM, Katana, Plume, Abstract, Worldchain.
- EIP-1967 impl/beacon/admin slots = zero on TesseraSwap, engine, treasury (non-proxy). Owner = `SafeProxy` (Blockscout `proxy_type: master_copy`, 171 B).
- Storage slots 0/1/2 read live on both chains and mapped to `tesseraEngine`/`tesseraTreasury`/`tesseraOwner` via the **verified Blockscout source** + decoded constructor args (`0x31e9…0c17`, `0xc2ca…2Ed5`, `0xdbd3…b5C6`).
- Engine interface confirmed: `swapAmount`/`swapAmountView` selectors present in engine bytecode; `getAllTesseraPools()`/`isActive()`/`multiSigOwner()`/`globalPrioFeeThresholddd1337()` called live (Base: 11 pools, isActive=1, prioFee=2 gwei; BSC: 16 pools). Engine emitted **zero logs** in an address-filtered 40k-block scan (it is unverified, so a one-off deploy-era admin event cannot be 100% excluded, but no event interface is referenced by the verified swap source and none was observed).
- Deployment block/timestamp from Blockscout: Base block 37,518,648 @ 2025‑10‑30T12:17:23Z (matches DefiLlama adapter `start: 2025-10-30`).

**Canonical sources:**
- **DefiLlama volume adapter** `dexs/tessera/index.ts` (github.com/DefiLlama/dimension-adapters) — the authoritative monitoring reference: hardcodes `TESSERA_SWAP_ADDRESS = 0x55555522005BcAE1c2424D474BfD5ed477749E3e`, the `TesseraTrade` event ABI, and `start` blocks for `SOLANA` (2025‑06‑11), `BASE` (2025‑10‑30), `BSC` (2025‑11‑13). DefiLlama's protocol page lists Tessera V as Solana-only (the Base/BSC EVM legs are tracked but not surfaced as separate "chains").
- **Verified contract source:** Base Blockscout `TesseraSwap` (Solidity 0.8.30, evm cancun, OZ v5 `SafeERC20`/`ReentrancyGuard`).
- **Background / attribution:** Blockworks 0xResearch "Prop AMMs expand to Base"; Helius "Solana's Proprietary AMM Revolution"; DL News on Solana dark AMMs — establish Wintermute as operator and the oracle-priced "dark AMM" model. Tessera is one of the top Solana prop AMMs (HumidiFi/SolFi/Tessera/ZeroFi/Obric ≈70% of Solana DEX volume on peak days; Tessera ≈$6.6B/month at time of writing). As dark AMMs, these have **no public website, LP program, docs, or audit** — they only fill aggregator-routed flow, which is why no official Tessera site/GitHub exists to cite.

**Caveats:**
- `TesseraEngine`, `tesseraTreasury`, and the deeper pricing logic are **unverified by design** ("dark"). Selector names beyond the resolved set are best-effort (openchain + keccak recomputation); ~30 engine selectors remain unnamed custom logic.
- BSC deploy date (≈2025‑11‑13) is from the DefiLlama adapter `start`; a free BscScan/Blockscout creation-tx lookup was not available without an API key, but the byte-identical bytecode and identical engine/treasury confirm it is the same deployment.
- This is a fast-moving 2025‑Q4 deployment; re-poll `eth_getCode` on the 5 absent chains and re-read storage slots 0/1 (engine/treasury) periodically.

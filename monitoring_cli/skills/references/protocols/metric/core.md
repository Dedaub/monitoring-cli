# Metric.exchange (METRIC) — Topics, Selectors, Addresses (Ethereum-only)

**Status:** verified against Ethereum mainnet RPC (`https://ethereum-rpc.publicnode.com`) + Blockscout + the live `metric.exchange` site on 2026-06-05. METRIC token ABI is **source-verified** (Blockscout, solc `0.5.17`); every topic0/selector below recomputed locally with keccak.
**Scope:** the **Metric.exchange protocol proper** — i.e. the one contract Metric actually owns on-chain, the **METRIC** governance/fee-discount token — plus the *external* settlement surface Metric's product runs on (**0x Protocol** + **KeeperDAO/Rook**). The much larger cluster of contracts deployed by Metric's founder EOAs (Wild Credit, UpDown.finance, a Basis Gold seigniorage fork, test tokens) is a **separate body of work** catalogued exhaustively in [`founder-fleet.md`](founder-fleet.md).

> **The single most important fact:** *Metric.exchange is a front-end, not a protocol.* The site states it plainly — **"Gas-less limit orders · Any token · Collect trading fees by holding $METRIC · Powered by 0x protocol & KeeperDAO."** There is **no Metric AMM, no Metric pool, no Metric settlement contract, and no Metric router.** Limit-order settlement happens on **0x Protocol** contracts; gas-less execution is coordinated by **KeeperDAO (Rook)**. The only proprietary, persistently-relevant Metric contract is the **METRIC ERC-20**. Earlier descriptions calling Metric "a DODO fork" or "a multi-chain PMM DEX" are **wrong** — there is no DODOZoo, no DVM/DPP/DSP, no classic DODO pair anywhere under Metric.

> **Metric is Ethereum-only.** The METRIC token returns empty bytecode (`0x`) from `eth_getCode` on **Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137)**, and neither founder EOA has *any* contract creations on those six chains (their only non-ETH activity is personal swaps routed through **1inch**). Do **not** author Metric monitors for any chain other than Ethereum mainnet (1).

---

## 0. What Metric actually is

| Layer | Where it lives | Monitor it via |
|-------|----------------|----------------|
| **METRIC token** | Ethereum, `0xefc1…14ac` (Metric-owned) | `Transfer`/`Approval` on the token; `mint`/`setGovernance` admin calls (§1–§3 below) |
| **Limit-order settlement** | **0x Protocol** ExchangeProxy (NOT Metric-owned) | 0x `LimitOrderFilled` / `RfqOrderFilled` / `TransformedERC20` on the 0x ExchangeProxy (§4) |
| **Gas-less execution / MEV-protection** | **KeeperDAO / Rook** (NOT Metric-owned) | KeeperDAO LiquidityPool / RookSwap contracts (§4) |
| **Fee discount** | off-chain (front-end waives the Metric fee for wallets holding ≥ a METRIC threshold) | not on-chain enforceable; the only on-chain signal is METRIC `balanceOf` of the trader |

There is **no on-chain "Metric fee" event** — the trading-fee discount for METRIC holders is applied by the front-end when it builds the 0x order, not by a Metric contract. Order flow you would attribute to "Metric" is **0x order flow whose `taker`/affiliate tag originated from the Metric UI** — there is no clean on-chain affiliate marker, so Metric volume is **not reliably separable** from general 0x volume on-chain.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 METRIC token (the only Metric-owned event surface)

The METRIC token is a plain OpenZeppelin-v2-era ERC-20 (`ERC20` + `ERC20Detailed`) with a governance-gated `mint`. It declares **only the two standard ERC-20 events** — there is no custom `GovernanceChanged`/`Mint` event (governance changes and mints are observable only as the resulting `Transfer` from `0x0`, or by tracing the `setGovernance`/`mint` calls).

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

> Both topic0s are the universal ERC-20 ones (every ERC-20 shares them) — **key on `(chainId=1, address=0xefc1…14ac, topic0)`**, never topic0 alone. A `Transfer` with `from == 0x0` on the METRIC token = a governance **mint** (the only way new METRIC is created; see §5 gotcha).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 METRIC token — full ABI (verified source, solc 0.5.17)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa9059cbb` | `transfer(address,uint256)` | standard ERC-20 |
| `0x23b872dd` | `transferFrom(address,address,uint256)` | |
| `0x095ea7b3` | `approve(address,uint256)` | |
| `0xdd62ed3e` | `allowance(address,address)` | |
| `0x70a08231` | `balanceOf(address)` | **the fee-discount signal** — front-end waives fees for holders above a threshold |
| `0x18160ddd` | `totalSupply()` | 1,000,000 at genesis — **but NOT fixed** (see `mint`) |
| `0x39509351` | `increaseAllowance(address,uint256)` | OZ helper |
| `0xa457c2d7` | `decreaseAllowance(address,uint256)` | OZ helper |
| `0x06fdde03` / `0x95d89b41` / `0x313ce567` | `name()`="Metric.exchange" / `symbol()`="METRIC" / `decimals()`=18 | |
| `0x5aa6e675` | `governance()` | `address` — the account allowed to `mint` / reassign governance. **Currently `0x0000…0000` (renounced) — see the gotcha below.** |
| `0xab033ea9` | `setGovernance(address)` | `onlyGovernance` — hand mint authority to a new address. Emits **no event** (observe by tracing the call). **Currently un-callable** (governance is `0x0`). |
| `0x40c10f19` | `mint(address,uint256)` | `onlyGovernance` — METRIC *was* mintable. Emits `Transfer(0x0 → to)`. **Currently un-callable** (governance is `0x0`); supply is frozen at 1,000,000. |

> **Supply is now permanently fixed at 1,000,000.** `governance()` returns the **zero address** (verified live 2026-06-05), and `totalSupply()` is still exactly `1,000,000e18`. Because both `mint` and `setGovernance` are `onlyGovernance`, setting `governance = 0x0` **bricks both permanently** (no address can satisfy `msg.sender == 0x0`). So METRIC is *de facto* an immutable, fixed-supply token: minting is disabled and the authority can never be reassigned. (It was *deployed* mintable — the renounce is what froze it.)

> **There is no `burn`, no `pause`, no `Ownable owner()`** — access control is the single `governance` address (`onlyGovernance`). `owner()` / `_OWNER_()` **revert** on the METRIC token.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **METRIC token** | `0xefc1c73a3d8728dc4cf2a18ac5705fe93e5914ac` | The Metric.exchange governance / fee-discount ERC-20. Verified (solc 0.5.17), 18 decimals, supply 1,000,000 (frozen — `governance()` renounced to `0x0`, see §2.1). The **only** Metric-owned contract. |
| METRIC deployer EOA | `0x2Cb037BD6B7Fbd78f04756C99B7996F430c58172` | Created the METRIC token (and 142 other contracts — the founder fleet, see [`founder-fleet.md`](founder-fleet.md)). |
| Founder/operator EOA | `0xd7b3b50977a5947774bfc46b760c0871e4018e97` | `owner()`/operator of most founder-fleet contracts; deployed 163 of them. Publicly attributed to **0xdev0** (Wild Credit / Metric founder). |

`governance()` of the token currently resolves to the **zero address** (renounced — minting permanently disabled; verified live 2026-06-05). **There are no other Metric-branded contracts on Ethereum** — wallets, treasuries, stakers etc. that you might expect do not exist as distinct Metric contracts (Metric's only "staking" utility is the off-chain fee discount).

---

## 4. External settlement surface Metric runs on (NOT Metric-owned)

Metric builds and relays orders onto these well-known third-party protocols. Monitor **these** for actual Metric-originated trading; there is no Metric contract in the settlement path.

| Protocol | Canonical Ethereum contract | Relevant events |
|----------|-----------------------------|-----------------|
| **0x Protocol** (ExchangeProxy / "0x Exchange v4") | `0xDef1C0ded9bec7F1a1670819833240f027b25EfF` | `LimitOrderFilled(bytes32,address,address,address,address,address,uint128,uint128,uint128,uint256,bytes32)`, `RfqOrderFilled(...)`, `TransformedERC20(address indexed taker,address inputToken,address outputToken,uint256 inputTokenAmount,uint256 outputTokenAmount)` |
| **0x** older Exchange (v2/v3, legacy limit orders) | `0x61935CbDd02287B511119DDb11Aeb42F1593b7Ef` (v3) | `Fill(...)`, `Cancel(...)` |
| **KeeperDAO / Rook** LiquidityPool (gas-less / coordinator) | `0x35fFd6E268610E764fF6944d07760D0EFe5E40E5` (KeeperDAO LiquidityPool v2) | `Borrowed`/`Migrated`/pool events (execution coordination) |
| **Permit2** (0x v4 allowance layer) | `0x000000000022D473030F116dDEE9F6B43aC78BA3` | `Permit`, `Lockdown` |

> These addresses are the **standard public deployments** of 0x / KeeperDAO / Permit2 — they are shared by the entire ecosystem, not specific to Metric. Verify each against the protocol's own docs before hard-coding; they are listed here so a "Metric order flow" monitor points at the right settlement layer rather than hunting for a non-existent Metric settlement contract.

---

## 5. Detection invariants & gotchas

1. **Metric = METRIC token only.** Any monitor for "the Metric protocol" reduces to: (a) METRIC `Transfer`/`Approval`, (b) METRIC `mint`/`setGovernance` admin calls, (c) optionally 0x/KeeperDAO settlement filtered to Metric-UI order flow (which is **not on-chain-distinguishable** — see §0).
2. **METRIC supply is now frozen at 1,000,000 — minting is renounced.** The token *was* deployed mintable (`mint(address,uint256)`, `onlyGovernance`), but `governance()` has been set to the **zero address**, which permanently bricks both `mint` and `setGovernance` (nothing can satisfy `msg.sender == 0x0`). `totalSupply()` == 1,000,000e18 and cannot change. There is therefore **no live supply-inflation surface**; a `Transfer(from=0x0)` on METRIC would be anomalous (it shouldn't be possible). Historically, watching `mint`/`Transfer(from=0x0)`/`setGovernance` mattered — today they are inert.
3. **No events for admin actions.** `setGovernance` and `governance` reassignment emit **nothing**; only `mint` is observable (as `Transfer` from `0x0`). Trace calls to the token, don't rely on logs, for governance monitoring.
4. **Ethereum-only — hard stop.** `0xefc1…14ac` is `0x` on Base/BNB/Avax/Arbitrum/Optimism/Polygon. There is no bridged METRIC and no multi-chain Metric deployment. Do not point Metric monitors at any L2/alt-L1.
5. **Not a DODO fork, not a DEX, not a lending protocol.** Metric owns no pool/pair/factory/router. The lending/oracle/borrow contracts you may find from the same deployer belong to **Wild Credit** (a *separate* protocol by the same founder) — see [`founder-fleet.md`](founder-fleet.md). Do not attribute them to "Metric."
6. **Order flow is 0x order flow.** Metric's "gas-less limit orders" are **0x limit/RFQ orders** relayed via KeeperDAO. To capture Metric trading you watch 0x `LimitOrderFilled`/`RfqOrderFilled` — but you cannot cleanly isolate the Metric-originated subset on-chain (no affiliate event).

---

## 6. Quick-copy detection constants (bytea-ready for Postgres)

```
-- ===== Chain =====
METRIC_CHAIN_ID                  = 1            -- Ethereum mainnet ONLY

-- ===== Metric-owned address =====
ADDR_METRIC_TOKEN                = '\xefc1c73a3d8728dc4cf2a18ac5705fe93e5914ac'
ADDR_METRIC_DEPLOYER_EOA         = '\x2cb037bd6b7fbd78f04756c99b7996f430c58172'
ADDR_FOUNDER_OPERATOR_EOA        = '\xd7b3b50977a5947774bfc46b760c0871e4018e97'

-- ===== Topics (METRIC token — standard ERC-20) =====
TOPIC_TRANSFER                   = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL                   = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'

-- ===== Selectors (METRIC token admin surface) =====
SEL_MINT                         = '\x40c10f19'   -- mint(address,uint256)  [onlyGovernance; BRICKED — governance==0x0]
SEL_SET_GOVERNANCE               = '\xab033ea9'   -- setGovernance(address) [onlyGovernance; BRICKED — governance==0x0]
SEL_GOVERNANCE                   = '\x5aa6e675'   -- governance() view -> currently 0x0 (renounced); supply frozen at 1,000,000

-- ===== External settlement surface (NOT Metric-owned; shared public deployments) =====
ADDR_0X_EXCHANGE_PROXY_V4        = '\xdef1c0ded9bec7f1a1670819833240f027b25eff'
ADDR_0X_EXCHANGE_V3              = '\x61935cbdd02287b511119ddb11aeb42f1593b7ef'
ADDR_KEEPERDAO_LIQUIDITYPOOL_V2  = '\x35ffd6e268610e764ff6944d07760d0efe5e40e5'
ADDR_PERMIT2                     = '\x000000000022d473030f116ddee9f6b43ac78ba3'
```

---

## 7. Verification & sources

- **METRIC token**: source-verified on Blockscout (`eth.blockscout.com`), compiler `0.5.17+commit.d19bba13`, optimization off. ABI pulled live; `name()`/`symbol()`/`decimals()`/`totalSupply()` read on-chain (Metric.exchange / METRIC / 18 / 1,000,000). Both event topic0s and all 14 function selectors recomputed locally with keccak (pycryptodome) — all match.
- **Chain absence**: `eth_getCode(0xefc1…14ac)` == `0x` on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon (publicnode RPCs); `eth_getTransactionCount` of both founder EOAs == 0 on Base/BNB/Avalanche/Polygon, and their Arbitrum/Optimism activity contains **no contract creations** (Blockscout `/transactions?filter=from`), only 1inch-routed swaps.
- **Product architecture**: the live `metric.exchange` landing page ("Gas-less limit orders … Powered by 0x protocol & KeeperDAO"), fetched 2026-06-05.
- **0x / KeeperDAO / Permit2 addresses**: `eth_getCode`-confirmed non-empty on Ethereum (0x ExchangeProxy v4 1229 B, 0x Exchange v3 23.7 KB, KeeperDAO LiquidityPool v2 13.8 KB, Permit2 9.2 KB). Standard public deployments — confirm against 0x and KeeperDAO docs before hard-coding; they are not Metric-specific. KeeperDAO's token is **ROOK** (rebranded **Rook**), not METRIC.
- **Deep-research scrutiny pass (2026-06-05):** confirmed Wild Credit is Ethereum-only (founder 0xdev0; WILD 100M, fixed; an official WILD token migration explains the multiple WILD addresses in [`founder-fleet.md`](founder-fleet.md)); confirmed Metric's settlement is 0x + KeeperDAO with **no on-chain Metric affiliate/fee marker**; found **no** earlier Metric DODO/AMM deployment. **Correction folded in:** METRIC `governance()` is the zero address and `totalSupply()` is still 1,000,000 → supply is permanently frozen (this file updated accordingly).
- See [`founder-fleet.md`](founder-fleet.md) for the exhaustively reverse-engineered catalog of the 306-contract founder cluster (Wild Credit, UpDown.finance, Basis Gold fork, test tokens).

# Binance ETH Staking — WBETH & BETH — Topics, Selectors, Addresses (Ethereum + BNB Smart Chain)

**Status:** verified against live RPC on every listed chain (`https://ethereum-rpc.publicnode.com`, `https://bsc-rpc.publicnode.com`) and the verified Etherscan/BscScan source on 2026-06-09. Every `topic0` / selector recomputed locally as `keccak256(sig)`; addresses confirmed with `eth_getCode`; proxy slots read live with `eth_getStorageAt`; the two non-standard WBETH events (`DepositEth`, `Mint`) and `ExchangeRateUpdated` observed verbatim in live `eth_getLogs`.

**Scope:** Two distinct Binance ETH-staking tokens, both Binance-custodial (centralised issuer, oracle-pushed rate / mint-by-operator) — **not** a permissionless protocol like Lido/Rocket Pool. **WBETH** (Wrapped Beacon ETH) is a value-accruing LST (1 WBETH ≥ 1 ETH, yield in the price) deployed on **Ethereum (1)** and **BNB Smart Chain (56)** at the **same address** `0xa2E3356610840701BDf5611a53974510Ae27E2e1`. **BETH** (Binance Beacon ETH) is a **1:1 rebasing-by-mint receipt** token, **BNB-only** at `0x250632378E573c6Be1AC2f97Fcdf00515d0Aa91B`. Neither token exists on Base, Avalanche, Arbitrum, Optimism, or Polygon (all `eth_getCode = 0x`). Event `topic0` and function `selector` values are chain-agnostic; addresses are network-specific.

**The non-obvious things an indexer must know.**
1. **WBETH shares one address on two chains but runs two different implementations.** The proxy address is identical; the logic behind it differs: Ethereum impl is `WrapTokenV3ETH` (you deposit **ETH**, `deposit(address)` payable, `0xf340fa01`), BNB impl is `WrapTokenV2BSC` (you deposit **BETH**, `deposit(uint256,address)`, `0x6e553f65`). The **event ABI is identical** across both, so topic0s are portable; only the deposit calldata shape differs.
2. **WBETH is NOT an EIP-1967 proxy.** It is an OpenZeppelin v3.x `AdminUpgradeabilityProxy` with **non-standard unstructured storage slots** (impl `0x7050c9e0…`, admin `0x10d6a54a…`). The EIP-1967 impl slot `0x360894…` reads **zero** on both chains — do not key WBETH proxy detection on it. Use `implementation()` (`0x5c60da1b`) / `admin()` (`0xf851a440`) or the two custom slots.
3. **BETH IS a standard EIP-1967 proxy** (`BEP20UpgradeableProxy`) — slot `0x360894…` resolves the impl `0x5c1ab318…`. Different proxy family from WBETH despite the same `Upgraded(address)` topic0.
4. **WBETH yield = `ExchangeRateUpdated`, BETH yield = new `Transfer` from `0x0`.** WBETH's rate is pushed (≈daily) by an off-chain **oracle contract** `0x81720695e43a39c52557ce6386feb3faac215f06` (same address both chains) calling `updateExchangeRate`. BETH never changes rate; staking rewards arrive as **freshly minted BETH** (extra balance, ERC-20 `Transfer` from `0x0`) — a mint-based rebase, not an EIP-style `rebase()`.

---

## 0. Token / contract families

| Token | Chain(s) | Address | Proxy | Impl contract | Mechanic |
|-------|----------|---------|-------|---------------|----------|
| **WBETH** | Ethereum (1) | `0xa2E3356610840701BDf5611a53974510Ae27E2e1` | OZ-v3 `AdminUpgradeabilityProxy` (custom slots) | `WrapTokenV3ETH` `0x9e021c9607bd3adb7424d3b25a2d35763ff180bb` | Deposit **ETH** → mint WBETH; yield via `ExchangeRateUpdated` |
| **WBETH** | BNB Smart Chain (56) | `0xa2E3356610840701BDf5611a53974510Ae27E2e1` (same) | OZ-v3 `AdminUpgradeabilityProxy` (custom slots) | `WrapTokenV2BSC` `0xfe928a7d8be9c8cece7e97f0ed5704f4fa2cb42a` | Deposit **BETH** → mint WBETH; same yield/event ABI |
| **BETH** | BNB Smart Chain (56) | `0x250632378E573c6Be1AC2f97Fcdf00515d0Aa91B` | EIP-1967 `BEP20UpgradeableProxy` | `BEP20TokenImplementationV2` `0x5c1ab3184b5cdf456f086e769dd66f19660376e2` | Mintable/burnable BEP-20; reward = mint, 1:1 ETH receipt |

WBETH on both chains reports name "Wrapped Binance Beacon ETH" / symbol `wBETH`, identical `exchangeRate()` (≈1.0998e18 on 2026-06-09), identical `oracle()` `0x81720695…`. BETH reports "Binance Beacon ETH" / `BETH` / 18 decimals.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

`topic0` is unaffected by `indexed`. **✓** = observed verbatim in live `eth_getLogs` this session; **src** = keccak of the verified-source signature, not log-confirmed in the sampled window (rare/admin event).

### 1.1 WBETH — `WrapTokenV3ETH` (Ethereum) / `WrapTokenV2BSC` (BNB) — identical event ABI

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xe32c4b34261b430739ef30d727d062f9fdd6410be2080e6fd875a6015f40de83` | `DepositEth(address indexed user, uint256 ethAmount, uint256 wBETHAmount, address indexed referral)` — **the deposit/wrap event** (named `DepositEth` on both chains even though BNB pulls BETH) | ✓ |
| `0xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8` | `Mint(address indexed minter, address indexed to, uint256 amount)` — WBETH minted to depositor | ✓ |
| `0x0b4e9390054347e2a16d95fd8376311b0d2deedecba526e9742bcaa40b059f0b` | `ExchangeRateUpdated(address indexed oracle, uint256 newExchangeRate)` — **the yield event** (oracle push, ≈daily) | ✓ |
| `0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5` | `Burn(address indexed burner, uint256 amount)` — WBETH burned (withdrawal/unwrap leg) | src |
| `0xe1ea856a2dd2650e9ab8bb416f893add49ac95f8364e47b4395a3ada9b0ccc2c` | `RequestWithdrawEth(address indexed user, uint256 wbethAmount, uint256 ethAmount)` — user requests redemption | src |
| `0x721a8f86a9fdbdbdd40ad38486cae32f7ee0a9f16c9df4596ea18bb01853efdf` | `MovedToStakingAddress(address indexed ethReceiver, uint256 ethAmount)` — operator sweeps deposited ETH to staking | src |
| `0x56d2bc55f552daa5d7bf4883dc0f73fb82309ff0beee747fca1dcfbd501226e0` | `MovedToUnwrapAddress(address indexed unwrapAddress, uint256 ethAmount)` — operator routes ETH for redemptions | src |
| `0x6f159dc1a889982fdc908cb2b9a48d36d718ed0c0c8c9ef565c4857e0f00a462` | `SuppliedEth(address indexed supplier, uint256 ethAmount)` — operator tops up redemption liquidity | src |
| `0x3df77beb5db05fcdd70a30fc8adf3f83f9501b68579455adbd100b8180940394` | `OracleUpdated(address indexed newOracle)` — rate-pusher rotated (**admin signal**) | src |
| `0xc6826629852f9e6617c80ac221f1ea00b4fb5c6ee3d58982080816550c01e599` | `EthReceiverUpdated(address indexed previousReceiver, address indexed newReceiver)` | src |
| `0x1e57e3bb474320be3d2c77138f75b7c3941292d647f5f9634e33a8e94e0e069b` | `EtherReceived(address indexed sender, uint256 ethAmount)` (ETH impl only) | src |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` (ERC-20; mint = from `0x0`) | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ✓ |

> **WBETH balances do NOT rebase** — they are constant; the value floats via `exchangeRate()`. `Transfer.value` is a true WBETH amount, safe to sum. Index `DepositEth`/`Mint` for inflows, `Burn`/`RequestWithdrawEth` for outflows, and `ExchangeRateUpdated` for the yield curve.

### 1.2 WBETH proxy (`WBETHWrapTokenProxy`, OZ-v3 `AdminUpgradeabilityProxy`) — both chains

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch for implementation swaps** | src |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` — proxy admin rotation | src |

> Both topic0s are confirmed **embedded in the live proxy bytecode** (the proxy's `emit` paths). The proxy itself emits these, distinct from the impl's events; key on the proxy address.

### 1.3 BETH — `BEP20TokenImplementationV2` (BNB only) — plain BEP-20

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — **mint = from `0x0`; reward distribution arrives as new Transfers from `0x0`** | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ✓ |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` — minter/owner rotation (**admin signal**) | src |

> **BETH has no Mint/Burn/Rebase event** of its own — mint and burn surface only as ERC-20 `Transfer` to/from `0x0`. There is no exchange rate: 1 BETH is a 1:1 ETH receipt; rewards are extra BETH minted to holders.

### 1.4 BETH proxy (`BEP20UpgradeableProxy`, EIP-1967) — BNB only

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (same topic0 as WBETH proxy — disambiguate by address) | src |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | src |

> Both topics confirmed embedded in the BETH proxy bytecode, which also contains the literal EIP-1967 impl slot `0x360894…`.

---

## 2. Function signatures (chain-agnostic — `selector = keccak256(signature)[0:4]`)

**bytecode** = confirmed present via PUSH4-dispatcher scan of the live implementation; proxies resolved to impl first.

### 2.1 WBETH — `WrapTokenV3ETH` (Ethereum)

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0xf340fa01` | `deposit(address referral)` | `uint256` wbethMinted | **payable — stake ETH → mint WBETH.** Emits `DepositEth` + `Mint`. (ETH impl only; absent on BNB) |
| `0x1c439430` | `supplyEth()` | — | payable; operator supplies ETH redemption liquidity → `SuppliedEth` |
| `0xa0907283` | `requestWithdrawEth(uint256 wbethAmount)` | — | start redemption → `RequestWithdrawEth` + `Burn` |
| `0x3ba0b9a9` | `exchangeRate()` | `uint256` | **ETH per 1 WBETH (1e18).** The value anchor. |
| `0xb9e205ae` | `updateExchangeRate(uint256 newExchangeRate)` | — | **oracle-only — pushes yield.** Emits `ExchangeRateUpdated` |
| `0x40c10f19` | `mint(address to, uint256 amount)` | `bool` | minter-gated |
| `0x42966c68` | `burn(uint256 amount)` | — | |
| `0x824da34f` | `moveToStakingAddress(uint256 amount)` | — | operator sweep → `MovedToStakingAddress` |
| `0x0ab9aaf6` | `moveToUnwrapAddress(uint256 amount)` | — | operator route → `MovedToUnwrapAddress` |
| `0x7dc0d1d0` | `oracle()` | `address` | the rate-pusher (`0x81720695…`) |
| `0x70a08231` / `0x18160ddd` | `balanceOf(address)` / `totalSupply()` | `uint256` | **non-rebasing** WBETH units |

### 2.2 WBETH — `WrapTokenV2BSC` (BNB) — differences from §2.1

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0x6e553f65` | `deposit(uint256 amount, address referral)` | `uint256` wbethMinted | **stake BETH (ERC-20 pull) → mint WBETH.** Replaces the ETH `deposit(address)`. `0xf340fa01` is **absent** on BNB. |
| `0xa0907283` / `0x3ba0b9a9` / `0xb9e205ae` / `0x40c10f19` / `0x42966c68` / `0x824da34f` / `0x0ab9aaf6` / `0x7dc0d1d0` | `requestWithdrawEth` / `exchangeRate` / `updateExchangeRate` / `mint` / `burn` / `moveToStakingAddress` / `moveToUnwrapAddress` / `oracle` | — | identical to Ethereum impl |

### 2.3 BETH — `BEP20TokenImplementationV2` (BNB)

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0xa0712d68` | `mint(uint256 amount)` | `bool` | **owner-only** (`getOwner()`); mints to owner — the staking-reward / deposit mint path |
| `0x42966c68` | `burn(uint256 amount)` | `bool` | holder burns own BETH |
| `0x893d20e8` | `getOwner()` | `address` | the minter wallet (`0xf68a4b64…`) |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | — | rotates the minter → `OwnershipTransferred` |
| `0xef3ebcb8` | `initialize(string,string,uint8,uint256,bool,address)` | — | one-shot proxy init |
| `0x70a08231` / `0x18160ddd` / `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` | `balanceOf` / `totalSupply` / `transfer` / `transferFrom` / `approve` | — | standard BEP-20 |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

Every address verified with `eth_getCode` (code present). Proxy impl/admin resolved from the custom slots (§5) and `eth_call`.

| Role | Address | Proxy | One-liner |
|------|---------|-------|-----------|
| **WBETH (token / proxy)** | `0xa2E3356610840701BDf5611a53974510Ae27E2e1` | OZ-v3 AdminUpgradeabilityProxy → impl `0x9e021c…180bb` | Wrapped Beacon ETH; value-accruing LST; emits §1.1–1.2 |
| WBETH implementation (`WrapTokenV3ETH`) | `0x9e021c9607bd3adb7424d3b25a2d35763ff180bb` | — | Logic: ETH deposit + rate + mint/burn. **Changes on upgrade.** |
| WBETH proxy admin | `0xa3ee6926edcce93bacf05f4222c243c4d9f6d853` | — (**EOA**) | Sole upgrade authority — a Binance-controlled key, not a governance contract |
| WBETH oracle (rate pusher) | `0x81720695e43a39c52557ce6386feb3faac215f06` | — (contract) | Calls `updateExchangeRate` → `ExchangeRateUpdated`. Same address on BNB. |
| ETH2 Deposit Contract | `0x00000000219ab540356cBB839Cbe05303d7705Fa` | — | Canonical CL deposit contract (deposited ETH ultimately routes here off-flow; not Binance-owned) |

**BETH is NOT on Ethereum** (`eth_getCode = 0x` for `0x2506…a91B`).

---

## 4. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | Proxy | One-liner |
|------|---------|-------|-----------|
| **WBETH (token / proxy)** | `0xa2E3356610840701BDf5611a53974510Ae27E2e1` | OZ-v3 AdminUpgradeabilityProxy → impl `0xfe928a…b42a` | Same address as Ethereum; wraps **BETH** here |
| WBETH implementation (`WrapTokenV2BSC`) | `0xfe928a7d8be9c8cece7e97f0ed5704f4fa2cb42a` | — | Logic: BETH deposit + rate + mint/burn. **Changes on upgrade.** |
| WBETH proxy admin | `0x20b9d30ddbb974bb0bfbedefd501f113e296cc4a` | — (**EOA**) | WBETH upgrade authority on BNB (distinct from the ETH admin) |
| WBETH oracle (rate pusher) | `0x81720695e43a39c52557ce6386feb3faac215f06` | — | Same oracle address as Ethereum |
| **BETH (token / proxy)** | `0x250632378E573c6Be1AC2f97Fcdf00515d0Aa91B` | EIP-1967 `BEP20UpgradeableProxy` → impl `0x5c1ab3…76e2` | Binance Beacon ETH; 1:1 receipt; emits §1.3–1.4 |
| BETH implementation (`BEP20TokenImplementationV2`) | `0x5c1ab3184b5cdf456f086e769dd66f19660376e2` | — | Mintable/burnable BEP-20 logic |
| BETH proxy admin | `0xd2f93484f2d319194cba95c5171b18c1d8cfd6c4` | — (**EOA**) | BETH upgrade authority |
| BETH owner / minter | `0xf68a4b64162906eff0ff6ae34e2bb1cd42fef62d` | — (**EOA**) | `getOwner()` — only address allowed to `mint` BETH |

---

## 5. Cross-chain summary

Rows = chains; cells = address / — (absent).

| Chain | ID | WBETH | BETH |
|-------|----|-------|------|
| Ethereum | 1 | `0xa2E3356610840701BDf5611a53974510Ae27E2e1` | — |
| BNB Smart Chain | 56 | `0xa2E3356610840701BDf5611a53974510Ae27E2e1` (same addr, diff impl) | `0x250632378E573c6Be1AC2f97Fcdf00515d0Aa91B` |
| Base | 8453 | — | — |
| Avalanche C-Chain | 43114 | — | — |
| Arbitrum One | 42161 | — | — |
| Optimism | 10 | — | — |
| Polygon PoS | 137 | — | — |

All five non-listed chains returned `eth_getCode = 0x` for both addresses (existence-checked live). There is **no canonical bridged WBETH/BETH** on Base/Avalanche/Arbitrum/Optimism/Polygon from Binance; any WBETH-named token there is a third-party bridge wrapper, out of scope.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **WBETH** (ETH & BNB) | OpenZeppelin **v3.x `AdminUpgradeabilityProxy`** — **non-EIP-1967** custom slots | impl slot `0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3`, admin slot `0x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b`. **EIP-1967 slot `0x360894…` reads ZERO.** Also `implementation()` `0x5c60da1b` / `admin()` `0xf851a440`. | EOA proxy admin (ETH `0xa3ee…d853`, BNB `0x20b9…cc4a`) |
| **BETH** (BNB) | **EIP-1967 `BEP20UpgradeableProxy`** | standard impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` → `0x5c1ab3…76e2`; admin slot `0xb53127…6103` → `0xd2f934…d6c4` | EOA proxy admin `0xd2f934…d6c4` |
| WBETH impl, BETH impl, WBETH oracle | **immutable logic** (no proxy) | EIP-1967 impl slot zero; addresses change only by an `Upgraded` on the proxy | n/a |

**`Upgraded(address)` = `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` is the single most important admin alert** — it fires on a logic swap of either token. Watch it on all three proxy addresses (WBETH on ETH, WBETH on BNB, BETH on BNB). `AdminChanged` = `0x7e644d79…`.

---

## 7. Detection invariants & gotchas

1. **WBETH ≠ BETH.** WBETH is value-accruing (rate floats, balance fixed); BETH is a 1:1 receipt (rate fixed at 1, balance grows by minting). Do not apply an exchange rate to BETH, and do not assume WBETH rebases.
2. **WBETH yield is an event, not a balance change.** Track `ExchangeRateUpdated(address,uint256)` (`0x0b4e9390…`) on the WBETH proxy for the yield curve / a stale-or-jumpy-rate alert. The pusher is the oracle `0x81720695…`; an `OracleUpdated` (`0x3df77beb…`) or an off-cadence / large-delta `ExchangeRateUpdated` is a high-value risk signal (the rate is centralised and pushed by an EOA-fed oracle).
3. **BETH yield is invisible except as `Transfer` from `0x0`.** No mint event; reward distribution mints BETH straight to holders. Sum BETH `Transfer` to detect supply growth; mint is `from == 0x0`, burn is `to == 0x0`.
4. **WBETH deposit shape differs by chain.** Ethereum: `deposit(address referral)` payable (`0xf340fa01`) — value = ETH. BNB: `deposit(uint256 amount, address referral)` (`0x6e553f65`) — pulls BETH. The **emitted `DepositEth` event is identical** (so topic0 monitoring is chain-portable), but calldata decoders must branch on chain.
5. **One WBETH address, two implementations.** Resolve the live impl per chain before decoding calldata — `WrapTokenV3ETH` (ETH) vs `WrapTokenV2BSC` (BNB). They share the event ABI but not the function set.
6. **Do NOT use the EIP-1967 impl slot for WBETH.** It reads zero. Use the custom slots in §6 or `implementation()`/`admin()`. BETH *does* use the EIP-1967 slot.
7. **Upgrade & mint authority are EOAs, not governance.** WBETH admins, BETH admin, and the BETH minter (`getOwner` `0xf68a…`) are all plain externally-owned accounts (Binance keys). There is no timelock/multisig-contract gate on-chain — `Upgraded`, `AdminChanged`, `OwnershipTransferred`, `OracleUpdated` are all single-key actions and warrant alerts.
8. **`Upgraded`/`AdminChanged` topic0s are shared across all three proxies** (and with most OZ/EIP-1967 proxies) — always disambiguate by emitting address.
9. **`Mint(address,address,uint256)` (`0xab8530f8…`) is WBETH's, not a generic ERC-20 mint.** It carries `(minter, to, amount)` and rides alongside `DepositEth` in the same tx; BETH has **no** Mint event (it uses bare `Transfer` from `0x0`).
10. **`burn(uint256)` selector `0x42966c68` is shared** between WBETH and BETH impls (same canonical signature) — disambiguate by contract address.
11. **No native deployment on the other five chains.** Absence is verified (`0x`), not an omission — treat any WBETH/BETH-labelled token on Base/Avax/Arbitrum/OP/Polygon as a non-canonical bridge wrapper.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_WBETH_DEPOSIT_ETH     = '\xe32c4b34261b430739ef30d727d062f9fdd6410be2080e6fd875a6015f40de83'  -- DepositEth(address,uint256,uint256,address)
TOPIC_WBETH_MINT            = '\xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8'  -- Mint(address,address,uint256)
TOPIC_WBETH_RATE_UPDATED    = '\x0b4e9390054347e2a16d95fd8376311b0d2deedecba526e9742bcaa40b059f0b'  -- ExchangeRateUpdated(address,uint256)
TOPIC_WBETH_BURN            = '\xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'  -- Burn(address,uint256)
TOPIC_WBETH_REQ_WITHDRAW    = '\xe1ea856a2dd2650e9ab8bb416f893add49ac95f8364e47b4395a3ada9b0ccc2c'  -- RequestWithdrawEth(address,uint256,uint256)
TOPIC_WBETH_ORACLE_UPDATED  = '\x3df77beb5db05fcdd70a30fc8adf3f83f9501b68579455adbd100b8180940394'  -- OracleUpdated(address)
TOPIC_WBETH_MOVED_STAKING   = '\x721a8f86a9fdbdbdd40ad38486cae32f7ee0a9f16c9df4596ea18bb01853efdf'  -- MovedToStakingAddress(address,uint256)
TOPIC_WBETH_MOVED_UNWRAP    = '\x56d2bc55f552daa5d7bf4883dc0f73fb82309ff0beee747fca1dcfbd501226e0'  -- MovedToUnwrapAddress(address,uint256)
TOPIC_WBETH_SUPPLIED_ETH    = '\x6f159dc1a889982fdc908cb2b9a48d36d718ed0c0c8c9ef565c4857e0f00a462'  -- SuppliedEth(address,uint256)
TOPIC_TRANSFER              = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  -- ERC20 (BETH mint/burn = 0x0 leg)
TOPIC_APPROVAL              = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_OWNERSHIP_TRANSFERRED = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'  -- BETH minter rotation
TOPIC_UPGRADED              = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'  -- Upgraded(address) — all 3 proxies
TOPIC_ADMIN_CHANGED         = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'  -- AdminChanged(address,address)

-- ===== Selectors =====
SEL_DEPOSIT_ETH             = '\xf340fa01'   -- WBETH(ETH) deposit(address) payable
SEL_DEPOSIT_BETH            = '\x6e553f65'   -- WBETH(BNB) deposit(uint256,address)
SEL_REQUEST_WITHDRAW_ETH    = '\xa0907283'   -- requestWithdrawEth(uint256)
SEL_EXCHANGE_RATE           = '\x3ba0b9a9'   -- exchangeRate()
SEL_UPDATE_EXCHANGE_RATE    = '\xb9e205ae'   -- updateExchangeRate(uint256)  (oracle-only)
SEL_WBETH_MINT              = '\x40c10f19'   -- WBETH mint(address,uint256)
SEL_BETH_MINT               = '\xa0712d68'   -- BETH mint(uint256) (owner-only)
SEL_BURN_U256               = '\x42966c68'   -- burn(uint256) (WBETH & BETH)
SEL_BETH_GET_OWNER          = '\x893d20e8'   -- BETH getOwner()
SEL_TRANSFER_OWNERSHIP      = '\xf2fde38b'   -- transferOwnership(address)
SEL_PROXY_IMPLEMENTATION    = '\x5c60da1b'   -- WBETH proxy implementation()
SEL_PROXY_ADMIN             = '\xf851a440'   -- WBETH proxy admin()
SEL_PROXY_UPGRADE_TO        = '\x3659cfe6'   -- upgradeTo(address)
SEL_PROXY_UPGRADE_TO_CALL   = '\x4f1ef286'   -- upgradeToAndCall(address,bytes)

-- ===== Ethereum mainnet (chain ID 1) =====
ETH_WBETH                   = '\xa2e3356610840701bdf5611a53974510ae27e2e1'
ETH_WBETH_IMPL              = '\x9e021c9607bd3adb7424d3b25a2d35763ff180bb'
ETH_WBETH_PROXY_ADMIN       = '\xa3ee6926edcce93bacf05f4222c243c4d9f6d853'
WBETH_ORACLE                = '\x81720695e43a39c52557ce6386feb3faac215f06'  -- same on BNB

-- ===== BNB Smart Chain (chain ID 56) =====
BNB_WBETH                   = '\xa2e3356610840701bdf5611a53974510ae27e2e1'  -- same address as ETH
BNB_WBETH_IMPL              = '\xfe928a7d8be9c8cece7e97f0ed5704f4fa2cb42a'
BNB_WBETH_PROXY_ADMIN       = '\x20b9d30ddbb974bb0bfbedefd501f113e296cc4a'
BNB_BETH                    = '\x250632378e573c6be1ac2f97fcdf00515d0aa91b'
BNB_BETH_IMPL               = '\x5c1ab3184b5cdf456f086e769dd66f19660376e2'
BNB_BETH_PROXY_ADMIN        = '\xd2f93484f2d319194cba95c5171b18c1d8cfd6c4'
BNB_BETH_MINTER             = '\xf68a4b64162906eff0ff6ae34e2bb1cd42fef62d'

-- ===== Proxy slots =====
WBETH_IMPL_SLOT             = '\x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3'  -- custom (NOT EIP-1967)
WBETH_ADMIN_SLOT            = '\x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b'  -- custom
EIP1967_IMPL_SLOT           = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'  -- BETH only
EIP1967_ADMIN_SLOT          = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'  -- BETH only
```

---

## 9. Verification & sources

- **keccak-256:** every topic0/selector recomputed locally and cross-checked against the known ERC-20 `Transfer`/`Approval` topic0s and `transfer`/`balanceOf` selectors before use.
- **Topics (✓):** `DepositEth`, `Mint`, `ExchangeRateUpdated`, `Transfer`, `Approval` observed verbatim in live `eth_getLogs` on WBETH (ETH) and BETH (BNB). The decisive `0xe32c4b34…`/`0xab8530f8…` pair was decoded from a real WBETH deposit tx (`0xdf452e…9291`) — structure (2 indexed + data words) matches the verified-source signatures exactly. Admin/operator events marked `src` (computed from verified source, high confidence).
- **Selectors (bytecode):** PUSH4-dispatcher scan of the live implementations — `WrapTokenV3ETH` `0x9e021c…180bb`, `WrapTokenV2BSC` `0xfe928a…b42a`, `BEP20TokenImplementationV2` `0x5c1ab3…76e2`. Confirmed `deposit(address)` present only on ETH, `deposit(uint256,address)` present only on BNB.
- **Addresses & proxies:** all confirmed with `eth_getCode`; WBETH custom impl/admin slots and BETH EIP-1967 slots read live with `eth_getStorageAt`; `implementation()`/`admin()`/`oracle()`/`exchangeRate()`/`getOwner()` cross-checked via `eth_call`. Five non-target chains existence-checked (`0x`).
- **Issuer mechanics** (WBETH value-accruing vs BETH 1:1 receipt; reward = mint for BETH): Binance Support — "What Is WBETH?" and the WBETH-launch announcement; corroborated on-chain (constant WBETH balances + floating `exchangeRate`; BETH `exchangeRate`-free BEP-20 with owner-gated mint).

Authoritative sources:

- Verified source — Etherscan: [WBETH proxy `0xa2E3…E2e1`](https://etherscan.io/address/0xa2e3356610840701bdf5611a53974510ae27e2e1), [WBETH impl `WrapTokenV3ETH` `0x9e02…80bb`](https://etherscan.io/address/0x9e021c9607bd3adb7424d3b25a2d35763ff180bb).
- Verified source — BscScan: [WBETH impl `WrapTokenV2BSC` `0xfe92…b42a`](https://bscscan.com/address/0xfe928a7d8be9c8cece7e97f0ed5704f4fa2cb42a), [BETH proxy `0x2506…a91B`](https://bscscan.com/address/0x250632378e573c6be1ac2f97fcdf00515d0aa91b), [BETH impl `BEP20TokenImplementationV2` `0x5c1a…76e2`](https://bscscan.com/address/0x5c1ab3184b5cdf456f086e769dd66f19660376e2).
- Binance docs: [What Is WBETH?](https://www.binance.com/en/support/faq/what-is-wbeth-e252366155174ba6887f6b32e3798273) · [Binance Introduces Wrapped Beacon ETH (WBETH)](https://www.binance.com/en/support/announcement/binance-introduces-wrapped-beacon-eth-wbeth-on-eth-staking-a1197f34d832445db41654ad01f56b4d).

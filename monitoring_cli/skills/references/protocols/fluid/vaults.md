# Fluid — Vault Protocol (borrowing / liquidations) — Topics, Selectors, Addresses

**Status:** verified against canonical `Instadapp/fluid-contracts-public` (`main`) source + live RPC on every listed chain. Factory/T1/T2/T3/T4 events+selectors computed locally with keccak; counts re-verified on-chain **2026-06-05** (publicnode). Supersedes the 2026-05 4-chain snapshot.
**Scope:** Fluid **Vault Protocol** — overcollateralized borrowing. Positions are **ERC-721 NFTs** minted by the VaultFactory; each vault is a market (collateral↔debt). Other modules: [`liquidity-layer.md`](liquidity-layer.md) (core; vault balances settle there), [`lending.md`](lending.md), [`dex.md`](dex.md), [`periphery.md`](periphery.md). Index: [`README.md`](README.md).
**Key fact:** vaults draw/repay liquidity from the Liquidity Layer, so a vault `LogOperate`/`LogLiquidate` is always accompanied by a Liquidity-Layer `LogOperate` in the same tx. **`LogLiquidate` is the key security/risk-alert event.** Vault types: **T1** (normal col↔debt), **T2** (smart collateral = DEX LP as collateral), **T3** (smart debt = DEX LP as debt), **T4** (smart col + smart debt). T1 has its own self-contained tree; T2–T4 share `vaultTypesCommon/` core and differ only in `operate`/`liquidate` arity and the AdminModule rate events.

> **Chains (re-verified 2026-06-05):** ETH(1), Base(8453), Arbitrum(42161), Polygon(137), **BNB(56)**. The VaultFactory is at the **same deterministic address `0x324c5Dc1fC42c7a4D43d92df1eBA58a54d13Bf2d` on all five** (`name()`="Fluid Vault", `symbol()`="fVLT", identical bytecode). **NOT on Optimism or Avalanche** (no code — confirmed 2026-06-05). **Correction vs prior doc:** BNB DOES carry the VaultFactory (35 vaults) — vaults are on 5 chains, not 4.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 VaultFactory (deployment + ERC-721 position NFT)
Source: `contracts/protocols/vault/factory/main.sol`, `.../factory/ERC721/ERC721.sol`.

| topic0 | Event |
|--------|-------|
| `0x00fa89a51ae01c150bfde909191818194382d30b43b645428ed6a71f19551073` | `VaultDeployed(address indexed vault, uint256 indexed vaultId)` — a new vault (market) is created |
| `0xfcc2278353c4cc5d54b742d7eee2d4a7abc22e4dc6213340088293860d502b51` | `NewPositionMinted(address indexed vault, address indexed user, uint256 indexed tokenId)` — new position NFT |
| `0x48cc5b4660fae22eabe5e803ee595e63572773d114bcd54ecc118c1efa8d75af` | `LogSetDeployer(address indexed deployer, bool indexed allowed)` |
| `0x0a1c6cd77aa2e405e482adf6ee6cf190a27682b6dd1234403f7602e5203c83bb` | `LogSetGlobalAuth(address indexed auth, bool indexed allowed)` |
| `0x7aee16d2c366535c2577e873699b458af55a0b0bd4c4fab5e930a780f05669d7` | `LogSetVaultAuth(address indexed vault, bool indexed allowed, address indexed auth)` |
| `0x6e71f281df08e5962589123c1ca39a8c9df25c6c9cfa7b6d1525effed3dafd21` | `LogSetVaultDeploymentLogic(address indexed deploymentLogic, bool indexed allowed)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)` *(ERC-721 position NFT; tokenId = nftId)* |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed approved, uint256 indexed tokenId)` *(ERC-721)* |
| `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` | `ApprovalForAll(address indexed owner, address indexed operator, bool approved)` |

> Subscribe to `VaultDeployed` from the factory to discover every vault on a chain. There is **no** `LogVaultDeployed`/`LogDeployVault`/`LogChangeVaultAdmin` (those names don't exist in this version).

### 1.2 Vault T1 — coreModule (the workhorse; one per position op / liquidation)
Source: `contracts/protocols/vault/vaultT1/coreModule/events.sol`.

| topic0 | Event |
|--------|-------|
| `0xfef64760e30a41b9d5ba7dd65ff7236a61d89ed8b44c67a29e84db1a67513a1c` | `LogOperate(address user, uint256 nftId, int256 newCol, int256 newDebt, address to)` — open(nftId=0)/adjust/close a position |
| `0x80fd9cc6b1821f4a510e45ffce6852ea3404807b5d3d833ffa85664408afcb66` | `LogLiquidate(address liquidator, uint256 colAmt, uint256 debtAmt, address to)` — **★ key liquidation/risk event** |
| `0x115609402b8e0707cb9654c5da38e5c0790ccad443a92f71160fe645aa342d04` | `LogAbsorb(uint256 colAbsorbed, uint256 debtAbsorbed)` — bad-debt absorption |
| `0x9a85dfb89c634cdc63db5d8cedaf8f9cfa4926df888bad563d70b7314a33a0ae` | `LogRebalance(int256 colAmt, int256 debtAmt)` — rebalance col/debt vs Liquidity Layer |
| `0xcde545703e0372175cadfff811d67c32910c3dcb33199679b3271c4106afdf9a` | `LogUpdateExchangePrice(uint256 supplyExPrice, uint256 borrowExPrice)` |

### 1.3 Vault T1 — adminModule (per-market config / risk params)
Source: `contracts/protocols/vault/vaultT1/adminModule/events.sol`.

| topic0 | Event |
|--------|-------|
| `0x06f8b08c94d657867f843433de70bed3628bbdc19b0c89413af75d30420ad3f3` | `LogUpdateSupplyRateMagnifier(uint256)` |
| `0x8d6a11b15739c2d7a6d0a69b9d322262db8c1fb2e4b96239e4e4733df8a5164e` | `LogUpdateBorrowRateMagnifier(uint256)` |
| `0x0e8160f7246256e8f7eea7dc5ee9de8c9fa1d6057c30561f548e6a84defeef15` | `LogUpdateCollateralFactor(uint256)` |
| `0x44a667dd6218a52f7ef808da1e39e9c8497db215eaff093c0c42ecf9bf2168f3` | `LogUpdateLiquidationThreshold(uint256)` |
| `0x5ac1492eb2009d4983693cc59b4ec4032b506a0f9cbefc19a7545af5945d26af` | `LogUpdateLiquidationMaxLimit(uint256)` |
| `0xba3aefe95d9bb126dd0e7885e76f453e72b0ee6efd457771f26fe0a7ca56cedc` | `LogUpdateWithdrawGap(uint256)` |
| `0xd3d6bb99321a653b7fc969c9f2a1917bd9623cab8ecaa67a2e1bec34c3eb2e1c` | `LogUpdateLiquidationPenalty(uint256)` |
| `0x06a28e5e1500bd478bd28b400a0fb46a9cc8748a5dac616b38bc91c29462c17f` | `LogUpdateBorrowFee(uint256)` |
| `0xf992c18e9b1aec434f456c32a556717f76f0f19cba16d430d4ba1be0813ab3e8` | `LogUpdateCoreSettings(uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256)` *(T1: supplyRateMag, borrowRateMag, CF, LT, maxLimit, withdrawGap, penalty, borrowFee)* |
| `0x7a46205dbf7cc57a79f474f580e08d7961ad634e14643486b8df2dc30c392b62` | `LogUpdateOracle(address indexed newOracle)` *(T1: 1-arg)* |
| `0xdb94ee7fd8b5bbf8f6d59e76731ff4b4f5a02ab3af1d3e0c774862cf96ff613b` | `LogUpdateRebalancer(address indexed rebalancer)` |
| `0xdff2a3947bcf9fc0807b142e7c8497066db9183428b7bdbfb1fcd0f55c27a3df` | `LogRescueFunds(address indexed token)` |
| `0xae8abcd7cc16d6da9fa7098d41cc4cdb3bd5ce892e46f15d904b44c9b156cb5e` | `LogAbsorbDustDebt(uint256[] nftIds, uint256 absorbedDustDebt)` |

> No `LogPauseVault` event — pausing is a state-write only.

### 1.4 Vault T2/T3/T4 (smart vaults) — distinguishing topics
Smart vaults share the T1 core events (`LogOperate`/`LogLiquidate`/`LogAbsorb`/`LogRebalance`/`LogUpdateExchangePrice` byte-identical — via `vaultTypesCommon/coreModule`). They differ in the **AdminModule rate events** and `LogUpdateOracle` arity. Source: `contracts/protocols/vault/vaultT{2,3,4}/adminModule/events.sol`, `.../vaultTypesCommon/adminModule/`.

| topic0 | Event | Type(s) |
|--------|-------|---------|
| `0x7edd6e9826630cd24ac104078d5d38d7bafba2e232fdf7f0789d4b0823f2b4a0` | `LogUpdateSupplyRate(int256)` *(replaces SupplyRateMagnifier)* | T2, T4 (smart collateral) |
| `0x1c6f5f29157eddb749a97a47ee18573bcaf02dfc1787f69d645122e952521eed` | `LogUpdateBorrowRate(int256)` *(replaces BorrowRateMagnifier)* | T3, T4 (smart debt) |
| `0x185cbeb042106e418efd502a38682a60dd066d84bcbf7c310632f2ffe6b0ffaf` | `LogUpdateCoreSettings(int256,uint256,...)` *(field1 signed)* | T2 |
| `0xc37f9ca94509c4fa82085be8b856f4298bf4437c30e9bf68173b56d7d5a4488d` | `LogUpdateCoreSettings(uint256,int256,...)` *(field2 signed)* | T3 |
| `0x31f0a1bece9cc733a04ce8f46232fdcc74b8441c441f9030c85b0e3823323b8b` | `LogUpdateCoreSettings(int256,int256,...)` *(both signed)* | T4 |
| `0xf3babb4efef8195c16cb5c44b63afff5f0cc5e2f93c2496f09af64430b8e84aa` | `LogUpdateOracle(uint256 indexed deploymentNonce, address indexed oracle)` *(2-arg; DIFFERS from T1's 1-arg)* | T2, T3, T4 |

> `LogUpdateCoreSettings` therefore has **4 distinct topic0s** (T1/T2/T3/T4) for the "same" 8-field event — branch your decoder on vault type. T1's `LogUpdateOracle(address)`=`0x7a46…` vs smart-vault `LogUpdateOracle(uint256,address)`=`0xf3ba…`.

---

## 2. Function signatures (chain-agnostic)

### 2.1 VaultFactory
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x968cbade` | `deployVault(address vaultDeploymentLogic, bytes vaultDeploymentData)` | deployer-gated. Emits `VaultDeployed`. |
| `0x8d654023` | `totalVaults()` | `uint256` count. |
| `0xe6bd26a2` | `getVaultAddress(uint256 vaultId)` | deterministic vault addr. |
| `0x652b9b41` | `isVault(address)` | probes target's `VAULT_ID()`. |
| `0x4502d063` | `isGlobalAuth(address)` | |
| `0xe04c8e5d` | `isVaultAuth(address vault, address auth)` | |
| `0x50c358a4` | `isDeployer(address)` | |
| `0x17e7681c` | `isVaultDeploymentLogic(address)` | |
| `0xa34b5ee8` | `setDeployer(address, bool)` | onlyOwner. |
| `0x8f2db95d` | `setGlobalAuth(address, bool)` | onlyOwner. |
| `0x7faa1d21` | `setVaultAuth(address vault, address auth, bool)` | onlyOwner. |
| `0x08a892d9` | `setVaultDeploymentLogic(address, bool)` | onlyOwner. |
| `0xc7acb01f` | `spell(address, bytes)` | onlyOwner arbitrary call. |
| `0x94bf804d` | `mint(uint256 vaultId, address user)` | vault-only; mints position NFT. Emits `NewPositionMinted`. |
| `0x540acabc` | `VAULT_ID()` | **on the vault** (not factory); used by `isVault` probe. |

Plus standard ERC-721 enumerable: `tokenURI 0xc87b56dd`, `transferFrom 0x23b872dd`, `safeTransferFrom 0x42842e0e`/`0xb88d4fde`, `approve 0x095ea7b3`, `setApprovalForAll 0xa22cb465`, `ownerOf 0x6352211e`, `balanceOf 0x70a08231`, `tokenByIndex 0x4f6ccce7`, `tokenOfOwnerByIndex 0x2f745c59`, `name 0x06fdde03`, `symbol 0x95d89b41`.

### 2.2 Vault T1 — core ops
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x032d2276` | `operate(uint256 nftId, int256 newCol, int256 newDebt, address to)` | open(nftId=0)/adjust/close. Returns `(uint256,int256,int256)`. |
| `0x8433ea22` | `liquidate(uint256 debtAmt, uint256 colPerUnitDebt, address to, bool absorb)` | |
| `0x7d7c2a1c` | `rebalance()` | `payable`, returns `(int256,int256)`. |
| `0x9e3e4821` | `absorb(uint256, int256)` | only public absorb; `_verifyCaller`-gated (self-delegatecall from `liquidate`). No zero-arg `absorb()`. |

### 2.3 Vault T2/T3/T4 — smart-vault ops (arity differs by type)
| Selector | Signature | Type |
|----------|-----------|------|
| `0x10259f26` | `operate(uint256,int256,int256,int256,int256,address)` | **T2 & T3 (selector collides — ABI-identical)** |
| `0x0931bf2d` | `operatePerfect(uint256,int256,int256,int256,int256,address)` | T2 & T3 (collide) |
| `0x7bae3361` | `liquidate(uint256,uint256,uint256,uint256,address,bool)` | T2 & T3 (collide) |
| `0xf4e7bfd1` | `liquidatePerfect(uint256,uint256,uint256,uint256,address,bool)` | T2 & T3 (collide) |
| `0x58cc871e` | `operate(uint256,int256,int256,int256,int256,int256,int256,address)` | T4 (dual col + dual debt) |
| `0xcc31808e` | `operatePerfect(uint256,int256,int256,int256,int256,int256,int256,address)` | T4 |
| `0x27fa2b53` | `liquidate(uint256,uint256,uint256,uint256,uint256,uint256,address,bool)` | T4 |
| `0x4163f0fa` | `liquidatePerfect(uint256,uint256,uint256,uint256,uint256,uint256,address,bool)` | T4 |

> **T2 vs T3 cannot be distinguished by selector** (smart-collateral and smart-debt `operate`/`liquidate` have identical ABI types). Disambiguate by the vault's type — read the AdminModule rate events (`LogUpdateSupplyRate` ⇒ has smart col ⇒ T2/T4; `LogUpdateBorrowRate` ⇒ has smart debt ⇒ T3/T4) or `VAULT_ID()`/resolver.

One-liner per type: **T1** normal (`operate(uint,int,int,addr)`, uint rate magnifiers) · **T2** smart collateral (dual-col operate, `LogUpdateSupplyRate(int)`) · **T3** smart debt (dual-debt operate, `LogUpdateBorrowRate(int)`) · **T4** smart col+debt (8-arg operate/liquidate, both signed rates).

---

## 3. Addresses

### 3.1 VaultFactory — shared across all 5 Fluid chains (deterministic)
`0x324c5Dc1fC42c7a4D43d92df1eBA58a54d13Bf2d` — `name()`="Fluid Vault", `symbol()`="fVLT"; ERC-721 that deploys vaults + mints position NFTs. Identical bytecode on every chain.

**`totalVaults()` per chain (verified on-chain 2026-06-05):**

| Chain | totalVaults |
|-------|-------------|
| Ethereum (1) | **170** |
| Arbitrum (42161) | **91** |
| Base (8453) | **50** |
| BNB (56) | **35** |
| Polygon (137) | **29** |

Individual vault (market) addresses are **per-chain** — enumerate via `VaultDeployed` / `FluidVaultResolver` (see [`periphery.md`](periphery.md) for resolver addresses), then verify with `eth_getCode` + `VAULT_ID()`. The Liquidity proxy where vault balances settle is shared per chain — see [`liquidity-layer.md`](liquidity-layer.md).

---

## 4. Proxies
- Vaults are deployed by the **VaultFactory** (which is also the ERC-721 position-NFT contract). Individual vaults follow Fluid's module pattern (a vault dispatches to admin/secondary implementation modules — upgradeable-by-governance). The position NFT lives on the **factory**, not per-vault.
- Liquidity-Layer InfiniteProxy: see [`liquidity-layer.md`](liquidity-layer.md). The VaultFactory itself is a normal (non-InfiniteProxy) contract.

---

## 5. Detection invariants & gotchas
1. **`LogLiquidate` (`0x80fd9cc6…`) is the priority risk alert.** Pair with the vault address + position `nftId` (from the surrounding `LogOperate`/Transfer) to identify the liquidated position. `LogAbsorb`/`LogAbsorbDustDebt` = bad-debt socialization (also worth alerting).
2. **Positions are NFTs** — identified by `nftId` (ERC-721 tokenId minted by the VaultFactory), not an EOA. Transferring the NFT transfers the debt position.
3. **Every vault op also emits a Liquidity-Layer `LogOperate`** in the same tx. Correlate by tx hash; the vault event carries user/nftId, the Liquidity event the token + signed amounts. See [`liquidity-layer.md`](liquidity-layer.md).
4. **Vaults are on 5 chains incl. BNB** (35 vaults) — the factory address is identical on all five. NOT on OP/Avax.
5. **T2/T3/T4 integrate the DEX** (smart collateral / smart debt = a DEX LP position as col/debt). Those vaults also emit DEX events ([`dex.md`](dex.md)) — a single user action can touch Vault + DEX + Liquidity Layer.
6. **`LogUpdateCoreSettings` has 4 topic0s** (one per vault type) and **`LogUpdateOracle` has 2** (T1 1-arg vs smart 2-arg). Don't assume a single hash. Smart-col vaults emit `LogUpdateSupplyRate(int)` instead of `LogUpdateSupplyRateMagnifier(uint)`; smart-debt likewise for borrow.
7. **No `LogPauseVault`, no public zero-arg `absorb()`** — bad-debt absorption only via `liquidate(..., absorb=true)` → self-delegatecalled `absorb(uint256,int256)` (`0x9e3e4821`).

---

## 6. Quick-copy detection constants (bytea-ready for PG)
```
-- ===== Topics =====
-- VaultFactory
TOPIC_VF_VAULT_DEPLOYED          = '\x00fa89a51ae01c150bfde909191818194382d30b43b645428ed6a71f19551073'
TOPIC_VF_NEW_POSITION_MINTED     = '\xfcc2278353c4cc5d54b742d7eee2d4a7abc22e4dc6213340088293860d502b51'
TOPIC_VF_SET_DEPLOYER            = '\x48cc5b4660fae22eabe5e803ee595e63572773d114bcd54ecc118c1efa8d75af'
TOPIC_VF_SET_GLOBAL_AUTH         = '\x0a1c6cd77aa2e405e482adf6ee6cf190a27682b6dd1234403f7602e5203c83bb'
TOPIC_VF_SET_VAULT_AUTH          = '\x7aee16d2c366535c2577e873699b458af55a0b0bd4c4fab5e930a780f05669d7'
TOPIC_VF_SET_VAULT_DEPLOY_LOGIC  = '\x6e71f281df08e5962589123c1ca39a8c9df25c6c9cfa7b6d1525effed3dafd21'
-- Vault T1 core
TOPIC_V_OPERATE                  = '\xfef64760e30a41b9d5ba7dd65ff7236a61d89ed8b44c67a29e84db1a67513a1c'
TOPIC_V_LIQUIDATE                = '\x80fd9cc6b1821f4a510e45ffce6852ea3404807b5d3d833ffa85664408afcb66'
TOPIC_V_ABSORB                   = '\x115609402b8e0707cb9654c5da38e5c0790ccad443a92f71160fe645aa342d04'
TOPIC_V_REBALANCE                = '\x9a85dfb89c634cdc63db5d8cedaf8f9cfa4926df888bad563d70b7314a33a0ae'
TOPIC_V_UPDATE_EXCHANGE_PRICE    = '\xcde545703e0372175cadfff811d67c32910c3dcb33199679b3271c4106afdf9a'
-- Vault smart-type distinguishers
TOPIC_V_UPDATE_SUPPLY_RATE       = '\x7edd6e9826630cd24ac104078d5d38d7bafba2e232fdf7f0789d4b0823f2b4a0'  -- T2/T4
TOPIC_V_UPDATE_BORROW_RATE       = '\x1c6f5f29157eddb749a97a47ee18573bcaf02dfc1787f69d645122e952521eed'  -- T3/T4
TOPIC_V_UPDATE_ORACLE_SMART      = '\xf3babb4efef8195c16cb5c44b63afff5f0cc5e2f93c2496f09af64430b8e84aa'  -- T2/T3/T4 (2-arg)
TOPIC_V_UPDATE_ORACLE_T1         = '\x7a46205dbf7cc57a79f474f580e08d7961ad634e14643486b8df2dc30c392b62'  -- T1 (1-arg)

-- ===== Selectors =====
SEL_VF_DEPLOY_VAULT              = '\x968cbade'
SEL_VF_TOTAL_VAULTS              = '\x8d654023'
SEL_VF_GET_VAULT_ADDRESS         = '\xe6bd26a2'
SEL_V_OPERATE_T1                 = '\x032d2276'
SEL_V_LIQUIDATE_T1               = '\x8433ea22'
SEL_V_REBALANCE                  = '\x7d7c2a1c'
SEL_V_OPERATE_T2T3               = '\x10259f26'
SEL_V_OPERATE_T4                 = '\x58cc871e'
SEL_V_LIQUIDATE_T2T3             = '\x7bae3361'
SEL_V_LIQUIDATE_T4               = '\x27fa2b53'
SEL_V_VAULT_ID                   = '\x540acabc'

-- ===== Addresses (ALL 5 Fluid chains) =====
FLUID_VAULT_FACTORY              = '\x324c5dc1fc42c7a4d43d92df1eba58a54d13bf2d'
```

---

## 7. Verification & sources
- **topic0/selector:** computed locally via keccak from `Instadapp/fluid-contracts-public` (`main`) `contracts/protocols/vault/{factory,vaultT1,vaultT2,vaultT3,vaultT4,vaultTypesCommon}/.../events.sol` (events read verbatim, struct args expanded to tuples). Spot-checked (`VaultDeployed`, `totalVaults`) locally.
- **Addresses/counts:** VaultFactory `eth_call totalVaults()` (`0x8d654023`) on each chain (2026-06-05): ETH 170, Arb 91, Base 50, BNB 35, Polygon 29. `name()`="Fluid Vault"/`symbol()`="fVLT" + identical bytecode confirmed on all five. No code on OP/Avax.
- **Source:** [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) · `deployments/deployments.md` · Fluid docs (`FluidVaultResolver` for live enumeration).

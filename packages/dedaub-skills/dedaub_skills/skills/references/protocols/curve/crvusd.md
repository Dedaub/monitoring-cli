# Curve crvUSD & LlamaLend — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Base, BSC, Avalanche, Polygon, Gnosis)

**Status:** event topic0 hashes and function selectors computed locally with keccak (pycryptodome) from the canonical signatures **as actually deployed** (read off the live bytecode + `eth_getLogs`, not the refactored `curvefi/curve-stablecoin` master, which is an unreleased Vyper-0.4 rewrite — see §0). All addresses **independently RPC-verified on-chain** (`eth_getCode` / `eth_call` / `eth_getStorageAt`) against `publicnode` RPCs on all eight target chains on **2026-06-02**. Markets enumerated live via the factories (`n_collaterals()` / `market_count()` + `controllers(i)`/`amms(i)`/`vaults(i)`). Topic0 set cross-checked against live logs on the wstETH mint market, LlamaLend market #9, and scrvUSD.
**Scope:** Curve's **crvUSD stablecoin** + its three sub-systems — (1) the **crvUSD MINT markets** (overcollateralised minting, Ethereum-only), (2) **LlamaLend / Curve Lend** (permissionless ERC-4626 lending vaults on the same LLAMMA engine; Ethereum + Arbitrum + Optimism among the 8 chains), and (3) **scrvUSD** (the Yearn-V3-based savings wrapper, Ethereum-only) plus its fee/reward plumbing. Topics + selectors are chain-agnostic; addresses are network-specific. The Curve **AMM/DEX** stack (StableSwap/CryptoSwap pools, DAO/veCRV) lives in the sibling [curve.md](curve.md).

crvUSD and LlamaLend are **not a DEX** — they are a CDP stablecoin and a lending protocol that share one engine: **LLAMMA** (the soft-liquidation AMM, `AMM.vy`) + a **Controller** (`Controller.vy`) + a **MonetaryPolicy** + a price oracle. The single most important fact for monitoring: **the mint-market Controller/AMM and the LlamaLend Controller/AMM emit byte-for-byte identical events** (same `Borrow`/`Repay`/`Liquidate`/`UserState` on the Controller, same `TokenExchange`/`Deposit`/`Withdraw`/`SetRate` on the LLAMMA) — they are deployed from the same blueprint. You disambiguate mint-vs-lend **by the emitting contract address** (and whether a `OneWayLendingFactory` or the `ControllerFactory` minted it), never by topic0. The lending vocabulary (`Borrow`, `Repay`, `Liquidate`, `RemoveCollateral`) is wholly different from the DEX vocabulary in curve.md.

The second thing to internalise: **LLAMMA `TokenExchange` collides in *name* with the DEX pools' `TokenExchange`, but is a different contract and a different signature** — LLAMMA's is the 5-arg `uint256`-index CryptoSwap-style `TokenExchange` (topic0 `0xb2e76ae9…`, identical hash to the *old tricrypto-2* DEX event), fired when arbitrageurs trade collateral↔crvUSD inside the soft-liquidation band. Always pair topic0 with the emitting LLAMMA address.

Third: **soft-liquidation ≠ hard-liquidation.** Soft-liquidation is the continuous LLAMMA rebalancing (emits `TokenExchange`/`Deposit`/`Withdraw` on the AMM as the price crosses bands — *normal* operation, not a default). Hard-liquidation is the `Controller.Liquidate` / `liquidate()` path when a user's health goes negative — *that* is the alert-worthy event, and it is **rare** (zero on the wstETH market in 245k blocks).

---

## 0. Contract families & versions

| Family | Contract(s) | Role | Engine / standard | Where |
|---|---|---|---|---|
| **Token** | crvUSD (`Stablecoin.vy`) | the ERC-20 stablecoin | immutable Vyper (ETH); bridged proxies on L2s | ETH canonical + bridged on all 8 |
| **Mint factory** | **ControllerFactory** (aka crvUSD Factory) | deploys + debt-ceilings mint markets; mints crvUSD to them | immutable Vyper | **Ethereum only** |
| **Mint market** ×9 | **Controller** + **LLAMMA AMM** + **MonetaryPolicy** | one per collateral (sfrxETH, wstETH, WBTC, WETH, sfrxETH-v2, tBTC, weETH, cbBTC, LBTC) | `Controller.vy` + `AMM.vy`; EIP-5202 blueprint deploys | **Ethereum only** |
| **Price oracle** | **AggregateStablePrice** (`AggregateStablePrice2.vy`) | aggregates crvUSD/stable pool prices into the peg | immutable Vyper | Ethereum |
| **Monetary policy** | **AggMonetaryPolicy / …2 / …3** | sets the borrow rate from peg + PegKeeper debt | immutable Vyper (replaceable via `SetMonetaryPolicy`) | Ethereum |
| **Stabiliser v1** | **PegKeeper** ×4 (`PegKeeper.vy`) | mint/burn crvUSD into peg pools to defend the peg | immutable Vyper | Ethereum |
| **Stabiliser v2** | **PegKeeperRegulator** + **PegKeeperV2** ×5 | regulator-gated peg keepers (current set) | immutable Vyper | Ethereum |
| **Flash** | **FlashLender** (`FlashLender.vy`) | EIP-3156 0-fee crvUSD flash loans | immutable Vyper | Ethereum |
| **Lend factory** | **OneWayLendingFactory** (`LendFactory`) | permissionless ERC-4626 lending markets | immutable Vyper | **ETH, ARB, OP** (+ Fraxtal/Sonic, out of scope) |
| **Lend market** ×N | **Vault (ERC-4626)** + **Controller** + **LLAMMA AMM** + **MonetaryPolicy** | one per (collateral, borrow-token) pair | Vault = **EIP-1167 clone**; Controller/AMM = blueprint deploys | ETH (48) / ARB (22) / OP (5+5) |
| **Savings** | **scrvUSD** (Savings crvUSD) | ERC-4626 yield wrapper of crvUSD | **Yearn VaultV3**, deployed as an **EIP-1167 clone** | **Ethereum only** |
| **Savings rewards** | **RewardsHandler** + **StablecoinLens** + **TWA** | routes crvUSD fees into scrvUSD as donated profit | immutable Vyper | Ethereum |
| **Fees** | **FeeSplitter** + **crvUSD FeeDistributor** | split LlamaLend/crvUSD fees to receivers / veCRV | immutable Vyper | Ethereum |

> **Version drift is real and you must read live.** The current mint-market MonetaryPolicy is `0x07491d12…` (AggMonetaryPolicy-v3) on 8 of 9 markets, even though `curve-stablecoin-js` still caches the older `0x1E7d3bf9…`; sfrxETH-v1 still runs the original `0xc684432f…`. The PegKeeper set has been rotated (v1 → v2-behind-regulator). **Enumerate markets and read `monetary_policy()`/`peg_keepers(i)` on-chain; never hard-code a policy or keeper.**

> **Source-vs-deployed caveat.** `curvefi/curve-stablecoin` `master` is a Vyper-0.4 rewrite (uses `curve_std`, `snekmate`, interface-module events, **2 indexed addresses** on `Borrow`/`Repay`/`Liquidate`, an extra `debt` field on `UserState`, a 7-arg `Liquidate`). **None of the live contracts match it.** Every topic0 in §1 was taken from the **deployed** bytecode/logs (the 2023-era monolithic Vyper-0.3.x signatures: **1 indexed address**, 5-arg `Liquidate`). Treat the master repo as future/unreleased.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

> **Mint = Lend.** Every event in §1.1 and §1.2 fires **identically** on crvUSD mint markets *and* LlamaLend markets — they are the same `Controller.vy` / `AMM.vy` blueprint. Disambiguate by emitter address (and by which factory created it). Verified live on both the wstETH mint market and LlamaLend market #9.

### 1.1 Controller (`Controller.vy` — the borrow/repay/liquidate engine; mint **and** lend)

Emitter examples: wstETH **mint** Controller `0x100daa78…`; LlamaLend Controller `0x1e0165db…` (market 0). 1 indexed param ⇒ `ntopics = 2`.

| topic0 | Event |
|--------|-------|
| `0xe1979fe4c35e0cef342fef5668e2c8e7a7e9f5d5d1ca8fee0ac6c427fa4153af` | `Borrow(address indexed user, uint256 collateral_increase, uint256 loan_increase)` |
| `0x77c6871227e5d2dec8dadd5354f78453203e22e669cd0ec4c19d9a8c5edb31d0` | `Repay(address indexed user, uint256 collateral_decrease, uint256 loan_decrease)` |
| `0xe25410a4059619c9594dc6f022fe231b02aaea733f689e7ab0cd21b3d4d0eb54` | `RemoveCollateral(address indexed user, uint256 collateral_decrease)` |
| `0x642dd4d37ddd32036b9797cec464c0045dd2118c549066ae6b0f88e32240c2d0` | `Liquidate(address indexed liquidator, address user, uint256 collateral_received, uint256 stablecoin_received, uint256 debt)` — **hard-liquidation; rare; the alert event** (only `liquidator` is indexed) |
| `0xeec6b7095a637e006c79c1819d696e353a8f703db2c49fc0219e17a8fd04f7f2` | `UserState(address indexed user, uint256 collateral, uint256 debt, int256 n1, int256 n2, uint256 liquidation_discount)` — fires on **every** position change (the workhorse) |
| `0x51fabb88f7860c9dbcc2a5a9b69a8b9476d63b87124591f97254e29f0e8daaeb` | `SetMonetaryPolicy(address monetary_policy)` |
| `0xe2750bf9a7458977fcc01c1a0b615d12162f63b18cad78441bd64c590b337eca` | `SetBorrowingDiscounts(uint256 loan_discount, uint256 liquidation_discount)` |
| `0x5393ab6ef9bb40d91d1b04bbbeb707fbf3d1eb73f46744e2d179e4996026283f` | `CollectFees(uint256 amount, uint256 new_supply)` (no indexed params ⇒ `ntopics = 1`) |

> `Borrow`/`Repay`/`Liquidate` carry only **one** indexed field (`user` or `liquidator`) on the deployed contracts — the master-repo rewrite indexes two (`caller` + `user`) and changes `Liquidate` to 7 args. **Use the values above.** Confirmed by bytecode PUSH32 scan across all 9 mint Controllers + sampled lend Controllers: `Liquidate` topic0 `0x642dd4d3…` present in every one (the 7-arg `0xa452ca3c…` is present in *none*).

### 1.2 LLAMMA AMM (`AMM.vy` — the soft-liquidation curve; mint **and** lend)

Emitter examples: wstETH **mint** LLAMMA `0x37417b22…`; LlamaLend LLAMMA `0x847d7a5e…` (market 0).

| topic0 | Event |
|--------|-------|
| `0xb2e76ae99761dc136e598d4a629bb347eccb9532a5f8bbd72e18467c3c34cc98` | `TokenExchange(address indexed buyer, uint256 sold_id, uint256 tokens_sold, uint256 bought_id, uint256 tokens_bought)` — **soft-liquidation swap** (`uint256` indices). **Same topic0 as the DEX old-tricrypto-2 `TokenExchange`** — disambiguate by emitter (a LLAMMA, not a pool). |
| `0x7e4f5fadb3361b33669433b392d1a203b7a236710eb272650052592e6ce62f09` | `Deposit(address indexed provider, uint256 amount, int256 n1, int256 n2)` — collateral deposited into bands (**NOT** the ERC-4626 `Deposit` — different sig, §1.3) |
| `0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568` | `Withdraw(address indexed provider, uint256 amount_borrowed, uint256 amount_collateral)` — **same topic0 as DEX VotingEscrow `Withdraw`**; disambiguate by emitter |
| `0x52543716810f73c3fa9bca74622aecb6d3614ca4991472f3e999d531c2f6afb8` | `SetRate(uint256 rate, uint256 rate_mul, uint256 time)` — interest accrual heartbeat (most frequent AMM event) |
| `0x00172ddfc5ae88d08b3de01a5a187667c37a5a53989e8c175055cb6c993792a7` | `SetFee(uint256 fee)` |
| `0x2f0d0ace1d699b471d7b39522b5c8aae053bce1b422b7a4fe8f09bd6562a4b74` | `SetAdminFee(uint256 fee)` |

### 1.3 ERC-4626 Vault (LlamaLend) **and** scrvUSD

LlamaLend Vault (`Vault.vy`) and scrvUSD (Yearn `VaultV3.vy`) both emit the **canonical EIP-4626** `Deposit`/`Withdraw`. Emitter examples: LlamaLend Vault `0x8cf1de26…`; scrvUSD `0x0655977F…`. Verified live on both.

| topic0 | Event | ntopics |
|--------|-------|---------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` | 3 |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` | 4 |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` (shares are ERC-20) | 3 |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | 3 |

> **This `Deposit`/`Withdraw` is NOT the LLAMMA `Deposit`/`Withdraw` (§1.2).** ERC-4626 `Deposit` is `(sender, owner, assets, shares)` (`0xdcbc1c05…`); the LLAMMA `Deposit` is `(provider, amount, n1, n2)` (`0x7e4f5fad…`). Different topic0, different contract. A lender supplying to a LlamaLend Vault emits §1.3 `Deposit`; a borrower's collateral moving in the band emits §1.2 `Deposit`.

### 1.4 scrvUSD-specific (Yearn VaultV3 — beyond ERC-4626)

scrvUSD is a Yearn V3 vault, so it emits the Yearn governance/accounting events too. Verified live (`StrategyReported` fires on every reward report).

| topic0 | Event |
|--------|-------|
| `0x7f2ad1d3ba35276f35ef140f83e3e0f17b23064fd710113d3f7a5ab30d267811` | `StrategyReported(address indexed strategy, uint256 gain, uint256 loss, uint256 current_debt, uint256 protocol_fees, uint256 total_fees, uint256 total_refunds)` — fires when crvUSD reward profit is booked (the yield heartbeat) |
| `0xde8ff765a5c5dad48d27bc9faa99836fb81f3b07c9dc62cfe005475d6b83a2ca` | `StrategyChanged(address indexed strategy, uint256 indexed change_type)` |
| `0x5e2b8821ad6e0e26207e0cb4d242d07eeb1cbb1cfd853e645bdcd27cc5484f95` | `DebtUpdated(address indexed strategy, uint256 current_debt, uint256 new_debt)` |
| `0xf361aed463da6fa20358e45c6209f1d3e16d4eca706e6eab0b0aeb338729c77a` | `UpdateProfitMaxUnlockTime(uint256 profit_max_unlock_time)` |
| `0x4426aa1fb73e391071491fcfe21a88b5c38a0a0333a1f6e77161470439704cf8` | `Shutdown()` — **emergency: vault shut down** (alert) |
| `0x78557646b1d8efa2cd49740d66df5aca39eb610ca8ca0e1ccac08979b6b2c46e` | `RoleSet(address indexed account, uint256 indexed role)` |
| `0x28709a2dab2a5d5e8688e96159011151c51644ab21839a8a45b449634d7c8b2b` | `UpdateAccountant(address indexed accountant)` |
| `0xce93baa0b608a7d420822b6b90cfcccb70574363ba4fd26ef5ac17dd465016c4` | `UpdateRoleManager(address indexed role_manager)` |

### 1.5 ControllerFactory (crvUSD mint factory) — emitter `0xC9332fdC…`

| topic0 | Event |
|--------|-------|
| `0xebbe0dfde9dde641808b7a803882653420f3a5b12bb405d238faed959e1e3aa3` | `AddMarket(address indexed collateral, address controller, address amm, address monetary_policy, uint256 ix)` — **new mint market created** |
| `0x22d26e5448456e0d2368bca46b2c824717b39390656f1c6314237e11d691e4f2` | `SetDebtCeiling(address indexed addr, uint256 debt_ceiling)` |
| `0xad17aca0dc59a6d96350f71e2732094471c65b5a5cecd8f95b376edcd5534cc9` | `MintForMarket(address indexed addr, uint256 amount)` |
| `0xb21604369d32a00404a085ea01ab0a3f6b63f8a0ebda770e25695572416d9bcf` | `RemoveFromMarket(address indexed addr, uint256 amount)` |
| `0x1694b0703640754583177bb0c9e8d97e4d163cd89d08ae426ef8cb3f47109542` | `SetImplementations(address amm, address controller)` |
| `0xffb40bfdfd246e95f543d08d9713c339f1d90fa9265e39b4f562f9011d7c919f` | `SetFeeReceiver(address fee_receiver)` |

### 1.6 OneWayLendingFactory (LlamaLend factory) — emitter `0xeA6876DD…` (ETH), `0xcaEC110C…` (ARB), `0x5EA8f3D6…` (OP)

| topic0 | Event |
|--------|-------|
| `0x2a854a597908740dff5f0846840f167547ea0d7614c43bde3ea49be2e68c07ec` | `NewVault(uint256 indexed id, address indexed collateral_token, address indexed borrowed_token, address vault, address controller, address amm, address price_oracle, address monetary_policy)` — **new lending market created** (verified live; 3 indexed ⇒ `ntopics = 4`) |
| `0x91d63b24386eae580bbbe65f3f50fd736c41031f36d85641bc13e74ac0cb95bb` | `SetImplementations(address amm, address controller, address vault, address pool_price_oracle, address monetary_policy, address gauge)` (6-arg; deployed factory may carry the older arity — confirm per deploy) |
| `0x279f1fe0f91b15d983792d0305a146961875690054db0d81bec8d1582461fc65` | `SetDefaultRates(uint256 min_rate, uint256 max_rate)` |

> The `NewVault` topic0 `0x2a854a59…` was confirmed on a live `eth_getLogs` over the Ethereum factory. `SetImplementations` here (`0x91d63b24…`, 6 args) is **different** from the ControllerFactory `SetImplementations` (`0x1694b070…`, 2 args) — they are different factories.

### 1.7 PegKeeper, PegKeeperRegulator, MonetaryPolicy, AggregateStablePrice, FlashLender

| topic0 | Event | Contract |
|--------|-------|----------|
| `0x8d685bd3f45d861c759ed7a46ea3d30eb5cc6ce9fe06c526931f94c963bca7d2` | `Provide(uint256 amount)` | PegKeeper / PegKeeperV2 — crvUSD minted into a peg pool |
| `0x5b6b431d4476a211bb7d41c20d1aab9ae2321deee0d20be3d9fc9b1093fa6e3d` | `Withdraw(uint256 amount)` | PegKeeper — crvUSD pulled back |
| `0x357d905f1831209797df4d55d79c5c5bf1d9f7311c976afd05e13d881eab9bc8` | `Profit(uint256 lp_amount)` | PegKeeper |
| `0xf395c3706a8194522b942d1992143a7b60a92a83f99ec30e3833c7630e3c1331` | `AddPegKeeper(address indexed peg_keeper)` | AggMonetaryPolicy (and Regulator, different sig) |
| `0x52182c3057b74a074adcacf89ba9ff9860a1265c89cfecd998a111e06bc80267` | `RemovePegKeeper(address indexed peg_keeper)` | AggMonetaryPolicy |
| `0xb4a3856a5d3f85a0db622badf557a5c47e98ef4ce2f9fced462328721ee80c76` | `WorstPriceThreshold(uint256 threshold)` | PegKeeperRegulator |
| `0x406e5474c6819832e7834a919ce48a8c8d909e2d9a3a0fe5378844c3b51b46a2` | `PriceDeviation(uint256 price_deviation)` | PegKeeperRegulator |
| `0x069906c4131a2e2c0b2f32f351644b280d95237fa3f095f91ac69cac88ab9234` | `DebtParameters(uint256 alpha, uint256 beta)` | PegKeeperRegulator |
| `0x2640b4015d3473fd09bf2b30939e17deb4068cdacf3892136e737e166ceb3210` | `SetRate(uint256 rate)` | AggMonetaryPolicy (**1-arg** — distinct from the AMM 3-arg `SetRate` `0x52543716…`) |
| `0xfc47ca1d88e8137eb4cc32afb4bb62d3eb485c114be5e98f0533d9825311c748` | `AddPricePair(uint256 n, address pool, bool is_inverse)` | AggregateStablePrice |
| `0x017592f2f16e82cccce60102865c737270289c308f34ff88e754d5e99ea0bae1` | `RemovePricePair(uint256 n)` | AggregateStablePrice |
| `0xc76f1b4fe4396ac07a9fa55a415d4ca430e72651d37d3401f3bed7cb13fc4f12` | `FlashLoan(address indexed caller, address indexed receiver, uint256 amount)` | FlashLender (EIP-3156) |

### 1.8 Fee plumbing (FeeSplitter, RewardsHandler)

| topic0 | Event | Contract |
|--------|-------|----------|
| `0x3ec7c36ff485aa9a27938503e3094604652d1f7262464127fb79577970abe12a` | `FeeDispatched(address indexed receiver, uint256 weight)` | FeeSplitter |
| `0xcef5c0f74b8e26cac8a85442177d7e9b9792cc2b2627efce6a5c3d764fc34df1` | `SetReceivers()` | FeeSplitter |
| `0x7544693205d94fae4fc2b20449536d0486b497d16e6d7dcbaf967b8fc277d02c` | `LivenessProtectionTriggered()` | FeeSplitter |
| `0x9643e1bd3bef4938b3e5d13d09a89e903194372751add4131e51ba3b4e92feaa` | `MinimumWeightUpdated(uint256 new_minimum_weight)` | RewardsHandler |
| `0x28c7a0b0199f34b0c32dc21845d1af15fa23a606aedcca2cdf3630bb0bfdc2be` | `ScalingFactorUpdated(uint256 new_scaling_factor)` | RewardsHandler |
| `0x64d8f8cbfdea4a770ccedf8e6ded555731ac04e04fa06d25a1e9495c10fc1469` | `StablecoinLensUpdated(address new_stablecoin_lens)` | RewardsHandler |

### 1.9 crvUSD token (ERC-20)

Standard ERC-20 `Transfer` `0xddf252ad…` / `Approval` `0x8c5be1e5…` (EIP-2612 permit). Bridged tokens emit additional bridge events (LayerZero OFT `OFTReceived/OFTSent`, Polygon-PoS `Transfer`, Gnosis-omnibridge mint/burn) that vary per chain.

---

## 2. Function selectors (chain-agnostic — `keccak256(sig)[0:4]`)

> **Vyper default args produce one selector per arity.** Mint and lend Controllers/AMMs share these selectors (same blueprint). Selectors below verified present in the live bytecode where noted.

### 2.1 Controller — state-changing (mint **and** lend)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x23cfed03` | `create_loan(uint256 collateral, uint256 debt, uint256 N)` | open a position |
| `0xbc61ea23` | `create_loan_extended(uint256 collateral, uint256 debt, uint256 N, address callbacker, uint256[] callback_args)` | leveraged open (deployed arity may vary by generation) |
| `0x6f972f12` | `add_collateral(uint256 collateral)` | (older arity); `add_collateral(uint256,address)` = `0x24049e57` |
| `0xd14ff5b6` | `remove_collateral(uint256 collateral)` | emits `RemoveCollateral`; `remove_collateral(uint256,bool use_eth)` = `0x2e4af52a` |
| `0xdd171e7c` | `borrow_more(uint256 collateral, uint256 debt)` | increase debt; emits `Borrow` |
| `0x371fd8e6` | `repay(uint256 _d_debt)` | emits `Repay`; `repay(uint256,address)` = `0xacb70815`; `repay(uint256,address,int256,bool)` = `0x37671f93` |
| `0x152f65cb` | `repay_extended(address callbacker, uint256[] callback_args)` | callback repay |
| `0xbcbaf487` | `liquidate(address user, uint256 min_x)` | **hard-liquidation**; emits `Liquidate`; `liquidate(address,uint256,bool)` = `0x3ecdb828` |
| `0x6cdb5a2a` | `self_liquidate(uint256 min_x)` | user closes their own underwater loan |
| `0x1e0cfcef` | `collect_fees()` | sweep accrued interest; emits `CollectFees` |
| `0x81d2f1b7` | `set_monetary_policy(address monetary_policy)` | emits `SetMonetaryPolicy` |

> The Controller has been deployed in several minor revisions over 2023-2025; **`create_loan`, `borrow_more`, `liquidate`, `self_liquidate`, `collect_fees` are stable, but the `add_collateral`/`remove_collateral`/`repay` overloads differ by deploy** (the `_for`/`use_eth`/`max_active_band` args were added/dropped across mint vs LlamaLend vs L2 generations — both arities are listed). For monitoring prefer the **events** (§1.1) over selectors, and PUSH4-scan the specific Controller's bytecode if you must match calldata. The `Liquidate`/`UserState`/`Borrow`/`Repay` *events* are the reliable signal.

### 2.2 LLAMMA AMM — collateral↔crvUSD (mint **and** lend)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5b41b908` | `exchange(uint256 i, uint256 j, uint256 in_amount, uint256 min_amount)` | CryptoSwap-style `uint256` indices. **Same selector as the DEX CryptoSwap `exchange` (curve.md §2.2)** — disambiguate by target |
| `0xa64833a0` | `exchange(uint256 i, uint256 j, uint256 in_amount, uint256 min_amount, address _for)` | with receiver |
| `0xa3e346ec` | `exchange_dy(uint256 i, uint256 j, uint256 out_amount, uint256 max_amount)` | exact-out swap |
| `0xd4387a99` | `set_rate(uint256 rate)` | Controller-only |
| `0xf3fef3a3` | `withdraw(address user, uint256 frac)` | Controller-only; emits AMM `Withdraw` |
| `0xab047e00` | `deposit_range(address user, uint256 amount, int256 n1, int256 n2)` | Controller-only; emits AMM `Deposit` |
| `0xf2388acb` | `get_p()` | current LLAMMA price (view) |
| `0x86fc88d3` | `price_oracle()` | external oracle price (view) |
| `0xb461100d` | `read_user_tick_numbers(address)` | band range of a user (view) |
| `0x8f8654c5` | `active_band()` | current band (view) |
| `0x1aa02d59` | `set_fee(uint256)` | admin only; emits `SetFee` |

> AMM selectors also vary by deploy; the **TokenExchange/Deposit/Withdraw/SetRate events** are the dependable detection surface.

### 2.3 ERC-4626 Vault (LlamaLend) & scrvUSD

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256 assets, address receiver)` | emits ERC-4626 `Deposit` |
| `0xb460af94` | `withdraw(uint256 assets, address receiver, address owner)` | emits ERC-4626 `Withdraw` |
| `0x94bf804d` | `mint(uint256 shares, address receiver)` | |
| `0xba087652` | `redeem(uint256 shares, address receiver, address owner)` | |
| `0x07a2d13a` | `convertToAssets(uint256 shares)` | view — share price |
| `0xc6e6f592` | `convertToShares(uint256 assets)` | view |
| `0x01e1d114` | `totalAssets()` | view |
| `0x38d52e0f` | `asset()` | = crvUSD for scrvUSD; = borrow-token for LlamaLend Vaults |
| `0x99530b06` | `pricePerShare()` | scrvUSD (Yearn V3) |
| `0x6ec2b8d4` | `process_report(address strategy)` | scrvUSD — book reward profit; emits `StrategyReported` |
| `0xf77c4791` | `controller()` | LlamaLend Vault → its Controller |
| `0x2a943945` | `amm()` | LlamaLend Vault → its LLAMMA |

### 2.4 Factories — market enumeration (read these to discover markets)

| Selector | Signature | Factory |
|----------|-----------|---------|
| `0x12397fa1` | `n_collaterals()` → uint256 | **ControllerFactory** (mint) — currently **9** |
| `0x24c1173b` | `collaterals(uint256)` → address | ControllerFactory |
| `0xe94b0dd2` | `controllers(uint256)` → address | **both** factories |
| `0x86a8cdbc` | `amms(uint256)` → address | **both** factories |
| `0xe9cbd822` | `stablecoin()` → address (= crvUSD) | ControllerFactory |
| `0xfd775c78` | `market_count()` → uint256 | **OneWayLendingFactory** — ETH **48** / ARB **22** / OP **5** (v2 **5**) |
| `0x8c64ea4a` | `vaults(uint256)` → address | OneWayLendingFactory |
| `0xc6610657` | `coins(uint256)` → address | OneWayLendingFactory (per-vault token pair) |
| `0xf851a440` | `admin()` → address | both factories (= crvUSD DAO admin `0xb7400d2e…`) |

> **Enumeration recipe.** Mint markets: `ControllerFactory.n_collaterals()` then `collaterals(i)`/`controllers(i)`/`amms(i)`. Lend markets: `OneWayLendingFactory.market_count()` then `vaults(i)`/`controllers(i)`/`amms(i)`, plus `Controller.monetary_policy()` for the policy. Verified working on all live factories.

### 2.5 PegKeeper / Regulator / MonetaryPolicy / Aggregator / FlashLender

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x8d685bd3` | `provide(uint256 amount)` | PegKeeper (note: same 4-bytes as the `Provide` event prefix) |
| `0x5b6b431d` | `withdraw(uint256 amount)` | PegKeeper |
| `0x16f0115b` | `pool()` → address | PegKeeper (its peg pool) |
| `0xdd8fee14` | `regulator()` → address | **PegKeeperV2 only** (returns the Regulator; v1 reverts — use this to tell v1 from v2) |
| `0x245a7bfc` | `aggregator()` → address | PegKeeper |
| `0xf6235138` | `peg_keepers(uint256)` → address | AggMonetaryPolicy & PegKeeperRegulator |
| `0x0a19399a` | `PRICE_ORACLE()` → address | AggMonetaryPolicy (→ AggregateStablePrice) |
| `0xafdf31cd` | `sigma()` → int256 | AggMonetaryPolicy |
| `0x2c4e722e` | `rate()` → uint256 | MonetaryPolicy (current per-second rate) |
| `0xa035b1fe` | `price()` → uint256 | AggregateStablePrice (the crvUSD aggregated price, 1e18) |
| `0x613255ab` | `maxFlashLoan(address token)` → uint256 | FlashLender (EIP-3156) |
| `0xd9d98ce4` | `flashFee(address token, uint256 amount)` → uint256 | FlashLender (0 fee) |
| `0x5cffe9de` | `flashLoan(address receiver, address token, uint256 amount, bytes data)` | FlashLender (EIP-3156) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1) — the full stack

All verified via `eth_getCode` / `eth_call` on `https://ethereum-rpc.publicnode.com` (2026-06-02). Markets enumerated live. **Ethereum is the only chain with mint markets, scrvUSD, PegKeepers, FlashLender, and the fee plumbing.**

### 3.1 Core crvUSD

| Role | Address | One-liner |
|------|---------|-----------|
| **crvUSD token** | `0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E` | the ERC-20 stablecoin; **immutable Vyper** (impl slot 0x0) |
| **ControllerFactory** (mint) | `0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC` | `n_collaterals()` = 9; `stablecoin()` = crvUSD; `admin()` = `0xb7400d2e…` |
| **AggregateStablePrice** (current) | `0x18672b1b0c623a30089a280ed9256379fb0e4e62` | crvUSD peg oracle; referenced by the current MonetaryPolicy |
| AggregateStablePrice2 (older) | `0xe5afcf332a5457e8fafcd668bce3df953762dfe7` | referenced by the original sfrxETH-v1 policy + v1 PegKeepers |
| **AggMonetaryPolicy3** (current) | `0x07491d124DDB3eF59a8938fcB3eE50f9fA0B9251` | live policy for 8/9 mint markets; `PRICE_ORACLE` = `0x18672b1b…` |
| AggMonetaryPolicy2 (prior) | `0x1E7d3bf98d3f8D8CE193236c3e0eC4b00e32DaaE` | prior policy (still cached by JS libs; superseded by `0x07491d12…`) |
| AggMonetaryPolicy (sfrxETH-v1) | `0xc684432FD6322c6D58b6bC5d28B18569aA0AD0A1` | original policy, only sfrxETH-v1 market |
| AggMonetaryPolicy (tBTC, prior) | `0xb8687d7dc9d8fa32fabde63e19b2dbc9bb8b2138` | (now also migrated to `0x07491d12…` — read live) |
| **FlashLender** | `0xa7a4bb50Af91F90b6Feb3388e7f8286Af45b299b` | EIP-3156, 0-fee crvUSD flash loans |
| crvUSD FeeDistributor (`fee_distributor_crvusd`) | `0xD16d5eC345Dd86Fb63C6a9C43c517210F1027914` | distributes crvUSD fees to veCRV (legacy sink) |
| crvUSD DAO admin | `0xb7400d2ea0F6dc1d7b153aa430b9e572f28aFB79` | owner of both factories (the crvUSD sub-DAO ownership agent) |

### 3.2 crvUSD MINT markets (9 collaterals) — Controller + LLAMMA + MonetaryPolicy

Enumerated live from `ControllerFactory` (2026-06-02). One Controller + one LLAMMA per collateral. sfrxETH appears twice (v1 + v2). All MonetaryPolicies are `0x07491d12…` (AggMonetaryPolicy3) except sfrxETH-v1.

| ix | Collateral | Controller | LLAMMA AMM | MonetaryPolicy |
|----|-----------|-----------|-----------|----------------|
| 0 | sfrxETH (v1) | `0x8472A9A7632b173c8Cf3a86D3afec50c35548e76` | `0x136e783846ef68C8Bd00a3369F787dF8d683a696` | `0xc684432F…` |
| 1 | wstETH | `0x100dAa78fC509Db39Ef7D04DE0c1ABD299f4C6CE` | `0x37417b2238AA52D0DD2D6252d989E728e8f706e4` | `0x07491d12…` |
| 2 | WBTC | `0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67` | `0xE0438Eb3703bF871E31Ce639bd351109c88666ea` | `0x07491d12…` |
| 3 | WETH | `0xA920De414eA4Ab66b97dA1bFE9e6EcA7d4219635` | `0x1681195C176239ac5E72d9aeBaCf5b2492E0C4ee` | `0x07491d12…` |
| 4 | sfrxETH (v2) | `0xEC0820EfafC41D8943EE8dE495fc9Ba8495B15cf` | `0xfa96AD0a9E64261dB86950e2dA362f5572c5c6fd` | `0x07491d12…` |
| 5 | tBTC | `0x1C91da0223c763d2e0173243eAdaA0A2ea47E704` | `0xf9bD9da2427a50908C4c6D1599D8e62837C2BCB0` | `0x07491d12…` |
| 6 | weETH | `0x652aea6b22310c89dcc506710cad24d2dba56b11` | `0xed325262f54b2987e74436f4556a27f748146da1` | `0x07491d12…` |
| 7 | cbBTC | `0xf8C786B1064889ffd3C8a08B48d5e0c159F4cbE3` | `0xb6E62aA178A5421D0A51d17e720a05dE78D3137a` | `0x07491d12…` |
| 8 | LBTC | `0x8aca5a776a878EA1F8967e70a23b8563008f58Ef` | `0x9a2E6Bb3114b1eEB5492d97188a3ecB09e39fAC8` | `0x07491d12…` |

> ix-6 weETH Controller/AMM were **re-derived live from `ControllerFactory.controllers(6)`/`amms(6)` on 2026-06-02** and are shown lowercase (canonical). An earlier draft's EIP-55-checksummed cells for this row were corrupted; the values above are the verified ones.

Collateral token addresses: sfrxETH `0xac3E018457B222d93114458476f3E3416Abbe38F`, wstETH `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0`, WBTC `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599`, WETH `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`, tBTC `0x18084fbA666a33d37592fA2633fD49a74DD93a88`, weETH `0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee`, cbBTC `0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf`, LBTC `0x8236a87084f8B84306f72007F36F2618A5634494`.

### 3.3 PegKeepers & PegKeeperRegulator

**v2 set (current, behind the Regulator)** — read live from `PegKeeperRegulator.peg_keepers(i)` and the current AggMonetaryPolicy (both agree):

| PegKeeperV2 | Peg pool | Pool name |
|---|---|---|
| `0x9201Da0D97CaAAff53f01B2fb56767C7072dE340` | `0x4DEcE678ceceb27446b35C672dC7d61F30bAD69E` | crvUSD/USDC |
| `0xFb726F57d251aB5C731E5C64eD4F5F94351eF9F3` | `0x390f3595bCa2Df7d23783dFd126427CCeb997BF4` | crvUSD/USDT |
| `0x3fA20eAa107DE08B38a8734063D605d5842fe09c` | `0x625E92624Bc2D88619ACCc1788365A69767f6200` | pyUSD/crvUSD (inverse) |
| `0x338cb2D827112d989a861cdE87cd9FFD913a1f9D` | `0x13e12bB0E6a2F1A3D6901a59A9D585e89A6243E1` | crvUSD/frxUSD (inverse) |
| `0x53876b157DECf04389EeD66c7c29D73863F8C50b` | `0x635Ef0056A597d13863B73825CcA297236578595` | GHO/crvUSD (inverse) |

| Role | Address |
|------|---------|
| **PegKeeperRegulator** | `0x36a04CAffc681fa179558B2Aaba30395CDdd855f` |

**v1 set (original, no Regulator)** — `regulator()` reverts; `aggregator()` = `0xe5afcf33…`:

| PegKeeper (v1) | Peg pool | Pool name |
|---|---|---|
| `0xaa346781dDD7009caa644A4980f044C50cD2ae22` | `0x4DEcE678…69E` | crvUSD/USDC |
| `0xE7cd2b4EB1d98CD6a4A48B6071d46401Ac7DC5C8` | `0x390f3595…BF4` | crvUSD/USDT |
| `0x6B765d07cf966c745B340AdCa67749fE75B5c345` | `0xca978A0528116DDA3cbA9ACD3e68bc6191CA53D0` | crvUSD/USDP |
| `0x1ef89Ed0eDd93D1EC09E4c07373f69C49f4dccae` | `0x34D655069F4cAc1547E4C8cA284Ff7F551115DfA`† | crvUSD/TUSD |

† v1 PegKeeper #3 pool reported as `0x34d655069f4cac1547e4c8ca284ffff5ad4a8db0` by `pool()` (crvUSD/TUSD); casing approximate.

> **Note:** historical PegKeeper lists in `curve-stablecoin-js` (`0x0a05ff64…`, `0x503E1Bf2…`) reflect a prior v2 rotation. The **live `PegKeeperRegulator.peg_keepers(i)`** above is current ground truth.

### 3.4 scrvUSD (Savings crvUSD) & reward plumbing

| Role | Address | One-liner |
|------|---------|-----------|
| **scrvUSD** (Savings crvUSD) | `0x0655977FEb2f289A4aB78af67BAB0d17aAb84367` | ERC-4626 (`asset()` = crvUSD); name "Savings crvUSD"; **EIP-1167 clone** of a Yearn VaultV3 impl; `role_manager` = Curve Ownership Agent `0x40907540…` |
| scrvUSD VaultV3 impl (clone target) | `0xd8063123BBA3B480569244AE66BFE72B6C84b00d` | the Yearn VaultV3 logic scrvUSD clones |
| **RewardsHandler** | `0xe8d1E2531761406Af1615A6764B0d5fF52736f56` | routes crvUSD fees → scrvUSD as donated profit; `minimum_weight()` = 500 (5%) |

### 3.5 LlamaLend / Curve Lend (Ethereum) — OneWayLendingFactory + 48 markets

| Role | Address |
|------|---------|
| **OneWayLendingFactory** | `0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0` (`market_count()` = 48; `admin()` = `0xb7400d2e…`) |
| **crvUSD FeeSplitter** | `0x2DfD89449faFF8a532790667baB21cF733C064f2` | = `ControllerFactory.fee_receiver()`; `version()` "0.1.0"; `n_receivers()` = 2; `receivers(0)` = the RewardsHandler `0xe8d1E253…`. Collects Controller fees and dispatches to scrvUSD (verified live). |

Representative live LlamaLend markets (Vault = ERC-4626 = supply token; Controller = borrow engine; LLAMMA = soft-liq AMM). Enumerated 2026-06-02:

| id | Vault (ERC-4626) | Controller | LLAMMA AMM |
|----|------------------|-----------|-----------|
| 0 | `0x8cf1de26729cFb7137af1A6B2A665e099EC319b5` | `0x1E0165DbD2019441aB7927C018701f3138114D71` | `0x847D7a5e4Aa4B380043B2908c29A92e2E5157e64` |
| 1 | `0x5aE28c9197a4a6570216fC7e53E7e0221D7A0FEF` | `0xaaDe9230AA9161880e13a38C83400d3D1995267b` | `0xb46aDcd1ea7E35C4eb801406C3E76E76e9a46EDF` |
| 2 | `0xB2b23C87a4B6d1b03Ba603F7C3EB9A81fDC0AAC9` | `0x413Fd2511BAD510947a91f5c6c79EBD8138C29Fc` | `0x5338B1bf469651a5951ef618Fb5DefbFFAed7Be9` |
| 9 | `0xccd37EB6374Ae5b1f0b85ac97eFf14770e0D0063` | `0xCAd85b7fe52B1939DCEebEe9bCf0b2a5Aa0cE617` | `0x8eEdE294459EfAFf55d580bc95C98306Ab03F0C8` |

> LlamaLend Vaults are **EIP-1167 clones** — e.g. Vault #9's clone impl is `0xc014f34d5BA10b6799d76b0f5AcDeEe577805085`. The Controllers/LLAMMAs are full blueprint deploys (immutable, not clones).

### 3.6 Proxy classification (Ethereum)

| Item | Pattern | impl slot / note |
|------|---------|------------------|
| crvUSD token | **immutable Vyper** | EIP-1967 impl slot = 0x0; Vyper dispatcher bytecode |
| ControllerFactory, OneWayLendingFactory | **immutable Vyper** | slot 0x0 |
| mint Controllers / LLAMMAs | **immutable** (EIP-5202 blueprint deploys) | slot 0x0; logic frozen per deploy |
| MonetaryPolicy, PegKeepers, Regulator, Aggregator, FlashLender | **immutable Vyper** | slot 0x0 (policies *replaced* via `SetMonetaryPolicy`, not upgraded) |
| **scrvUSD** | **EIP-1167 clone** (Yearn VaultV3) | code = `363d3d373d3d3d363d73d8063123…5af4…`; impl `0xd8063123…` (no EIP-1967 slot) |
| **LlamaLend Vault** | **EIP-1167 clone** | e.g. impl `0xc014f34d…`; logic frozen |

No `Upgraded(address)` topic applies to any of these on Ethereum — none is an EIP-1967/UUPS proxy. (The clones cannot upgrade.) Watch `SetMonetaryPolicy` / `SetImplementations` / `AddMarket` / `NewVault` for config changes instead.

---

## 4. Addresses — Arbitrum One (chain ID 42161) — bridged crvUSD + LlamaLend

LlamaLend is live; **no mint markets, no scrvUSD, no PegKeepers.** Verified on `https://arbitrum-one-rpc.publicnode.com`.

| Role | Address | Note |
|------|---------|------|
| **crvUSD (bridged)** | `0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5` | `symbol()` = crvUSD; **proxy** (Arbitrum L2-gateway, ~760 B; impl not at EIP-1967 slot) |
| **OneWayLendingFactory** | `0xcaEC110C784c9DF37240a8Ce096D352A75922DeA` | `market_count()` = **22** |
| ControllerFactory (mint) | — | **ABSENT** (`0x`) |
| scrvUSD | — | **ABSENT** |

LlamaLend Controller/LLAMMA/Vault are the same blueprint as Ethereum ⇒ **identical §1.1–§1.3 topic0s** (chain-agnostic). Enumerate via the factory. Example market #0: vault `0x49014a8e…`, controller `0xb5b6f0e6…`, amm `0x38eb8af2…`.

---

## 5. Addresses — Optimism (chain ID 10) — bridged crvUSD + LlamaLend (two factories)

LlamaLend is live with **two factory generations**; no mint markets, no scrvUSD. Verified on `https://optimism-rpc.publicnode.com`.

| Role | Address | Note |
|------|---------|------|
| **crvUSD (bridged)** | `0xC52D7F23a2e460248Db6eE192Cb23dD12bDDCbf6` | `symbol()` = crvUSD; LayerZero/standard-bridge token (~5835 B; impl slot 0x0) |
| **OneWayLendingFactory** | `0x5EA8f3D674C70b020586933A0a5b250734798BeF` | `market_count()` = **5** |
| **OneWayLendingFactory v2** | `0x1973ED17c267245510a390e0dce4FBcD9D2685f0` | `market_count()` = **5** |
| ControllerFactory (mint) | — | **ABSENT** |
| scrvUSD | — | **ABSENT** |

Same blueprint ⇒ identical §1.1–§1.3 topics. Enumerate via **both** factories.

---

## 6. Addresses — Base (chain ID 8453) — bridged crvUSD only

**No LlamaLend, no mint markets, no scrvUSD.** Only the bridged token. Verified on `https://base-rpc.publicnode.com`.

| Role | Address | Note |
|------|---------|------|
| **crvUSD (bridged)** | `0x417Ac0e078398C154EdFadD9Ef675d30Be60Af93` | `symbol()` = crvUSD; ~5835 B; impl slot 0x0 (LayerZero/standard-bridge token) |
| OneWayLendingFactory | — | **ABSENT** (ETH/ARB factory addrs return `0x`) |
| ControllerFactory (mint) | — | **ABSENT** |
| scrvUSD | — | **ABSENT** |

---

## 7. Addresses — BNB Smart Chain (56), Avalanche (43114), Polygon PoS (137), Gnosis (100) — bridged crvUSD only

**None of these four has LlamaLend, mint markets, or scrvUSD** (verified: the ETH/ARB `OneWayLendingFactory` and the mint `ControllerFactory` addresses all return `0x` on every one). Only the bridged crvUSD token exists. All `symbol()` = `crvUSD`, verified live.

| Chain | ID | crvUSD (bridged) | Bytecode / proxy | Bridge tech |
|-------|----|------------------|------------------|-------------|
| **BNB Smart Chain** | 56 | `0xe2fb3F127f5450DeE44afe054385d74C392BdeF4` | ~3099 B; impl slot 0x0 | LayerZero OFT (immutable) |
| **Avalanche** | 43114 | `0xCb7c161602d04C4e8aF1832046EE08AAF96d855D` | ~3099 B; impl slot 0x0 | LayerZero OFT (immutable) |
| **Polygon PoS** | 137 | `0xc4Ce1D6F5D98D65eE25Cf85e9F2E9DcFEe6Cb5d6` | ~2949 B; impl slot 0x0 | Polygon-PoS bridged (UChildERC20-style) |
| **Gnosis** | 100 | `0xaBEf652195F98A91E490f047A5006B71c85f058d` | **328 B → EIP-1967 proxy**, impl `0x199084EFbd7fe14d217bbF22FdC6E2Ed7266DDd4` | Gnosis Omnibridge token proxy |

> Polygon and Gnosis crvUSD addresses are not in `curvefi/curve-js`; they were verified by direct `symbol()` + `eth_getCode` on the canonical bridged tokens. Gnosis crvUSD is the **only bridged crvUSD that is an EIP-1967 proxy** — watch its `Upgraded(address)` (`0xbc7cd75a…`).

---

## 8. Cross-chain summary (presence matrix)

| Chain | ID | crvUSD token | Mint markets | LlamaLend | scrvUSD | PegKeepers / FlashLender / Fees |
|-------|----|--------------|--------------|-----------|---------|-------------------------------|
| **Ethereum** | 1 | ✅ `0xf939E0A0…` (immutable) | ✅ **9** (ControllerFactory `0xC9332fdC…`) | ✅ **48** (`0xeA6876DD…`) | ✅ `0x0655977F…` | ✅ all |
| **Arbitrum** | 42161 | ✅ `0x498Bf2B1…` (proxy) | ❌ | ✅ **22** (`0xcaEC110C…`) | ❌ | ❌ |
| **Optimism** | 10 | ✅ `0xC52D7F23…` | ❌ | ✅ **5 + 5** (`0x5EA8f3D6…`, `0x1973ED17…`) | ❌ | ❌ |
| **Base** | 8453 | ✅ `0x417Ac0e0…` | ❌ | ❌ | ❌ | ❌ |
| **BNB** | 56 | ✅ `0xe2fb3F12…` (OFT) | ❌ | ❌ | ❌ | ❌ |
| **Avalanche** | 43114 | ✅ `0xCb7c1616…` (OFT) | ❌ | ❌ | ❌ | ❌ |
| **Polygon PoS** | 137 | ✅ `0xc4Ce1D6F…` | ❌ | ❌ | ❌ | ❌ |
| **Gnosis** | 100 | ✅ `0xaBEf6521…` (proxy) | ❌ | ❌ | ❌ | ❌ |

**Out of scope but exists:** LlamaLend `OneWayLendingFactory` is also deployed on **Fraxtal** (`0xf3c9bdAB…`) and **Sonic** (`0x30d1859d…`); crvUSD is bridged to Fraxtal (`0xB102f7Ef…`), Sonic, Fantom (`0xD823D2a2…`), Etherlink, Taiko, etc. Those chains are outside the 8 target chains and are not enumerated here.

**Three things to internalise:**
1. **The full crvUSD stack is Ethereum-only.** Mint markets, scrvUSD, PegKeepers, FlashLender, and the fee plumbing exist **only on Ethereum**. L2s have at most the bridged token + (on ETH/ARB/OP) LlamaLend.
2. **LlamaLend exists only on Ethereum, Arbitrum, Optimism** (of the 8). Base/BSC/Avalanche/Polygon/Gnosis have **only the bridged crvUSD token** — explicitly verified absent.
3. **crvUSD has a different bridged address on every chain** (and different bridge tech: OFT on BSC/Avax, native bridges on ARB/OP/Base/Polygon/Gnosis). Always key on `(chainId, address)`.

---

## 9. Proxies (old & new)

| Item | Pattern | Detection |
|------|---------|-----------|
| crvUSD token (Ethereum) | **Immutable Vyper** | EIP-1967 impl slot 0x0; no upgrade event |
| crvUSD (Arbitrum) | **L2-gateway proxy** (non-EIP-1967) | ~760 B forwarder; impl not at the 1967 slot — read via the Arbitrum bridge, not the slot |
| crvUSD (Gnosis) | **EIP-1967 proxy** | impl slot → `0x199084EF…`; emits `Upgraded(address)` `0xbc7cd75a…` |
| crvUSD (Optimism / Base / BSC / Avalanche / Polygon) | **Immutable-ish bridged impl** | impl slot 0x0; full contract bytecode (OFT / native-bridge token) |
| ControllerFactory / OneWayLendingFactory | **Immutable Vyper** | slot 0x0 |
| mint & lend Controllers / LLAMMAs | **Immutable** (EIP-5202 blueprint) | slot 0x0; logic frozen per deploy; new logic only affects *future* markets via `SetImplementations` |
| MonetaryPolicy | **Immutable, replaceable** | slot 0x0; the *Controller* swaps to a new policy contract via `SetMonetaryPolicy` (watch `0x51fabb88…`) — not an in-place upgrade |
| **scrvUSD** | **EIP-1167 clone** (Yearn VaultV3) | bytecode `363d3d373d3d3d363d73<impl>5af4…`; impl `0xd8063123…`; **cannot upgrade** |
| **LlamaLend Vault** | **EIP-1167 clone** | bytecode `363d3d37…<impl>5af4…`; per-vault impl (e.g. `0xc014f34d…`); cannot upgrade |
| RewardsHandler / FeeSplitter / Aggregator / FlashLender | **Immutable Vyper** | slot 0x0 |

**`Upgraded(address)` topic0 = `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`** — relevant **only** for the Gnosis bridged crvUSD proxy. EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`.

---

## 10. Detection invariants & gotchas

1. **Mint markets and LlamaLend share one engine ⇒ identical Controller/AMM events.** `Borrow`/`Repay`/`Liquidate`/`RemoveCollateral`/`UserState` on the Controller and `TokenExchange`/`Deposit`/`Withdraw`/`SetRate` on the LLAMMA are byte-identical across both. **Disambiguate by emitter address** (mint Controllers come from `ControllerFactory.controllers(i)`; lend Controllers from `OneWayLendingFactory.controllers(i)`), never by topic0.
2. **LLAMMA `TokenExchange` (`0xb2e76ae9…`) collides with the DEX old-tricrypto-2 `TokenExchange`.** Same hash, different contract. The emitter is a LLAMMA (a mint/lend AMM), not a Curve pool. Likewise LLAMMA `Withdraw` (`0xf279e6a1…`) collides with DEX VotingEscrow `Withdraw`. Always pair topic0 with the emitting address.
3. **Soft-liquidation ≠ hard-liquidation.** LLAMMA `TokenExchange`/`Deposit`/`Withdraw` are *continuous, normal* soft-liquidation rebalancing as the oracle price crosses bands — **not** a default. The alert event is the **Controller `Liquidate` (`0x642dd4d3…`)**, which is rare (0 on the wstETH market in 245k blocks). Don't alert on LLAMMA `TokenExchange` as if it were a liquidation.
4. **Deployed `Liquidate` is the 5-arg, 1-indexed `0x642dd4d3…`** — confirmed by bytecode PUSH32 scan in every mint + sampled lend Controller. The `curvefi/curve-stablecoin` master's 7-arg `0xa452ca3c…` is **not** deployed anywhere. Same caution for `Borrow`/`Repay` (1 indexed addr, not 2).
5. **`Liquidate` rarely arrives as `tx.to = Controller`.** Like Aave, liquidations are run by bots/zaps that call `Controller.liquidate()` internally — detect by the **`Liquidate` event topic0**, not by `liquidate()` selector or `tx.to`. Also note `self_liquidate` (user closes own loan) emits the same `Liquidate`.
6. **ERC-4626 `Deposit`/`Withdraw` (`0xdcbc1c05…` / `0xfbde797d…`) ≠ LLAMMA `Deposit`/`Withdraw` (`0x7e4f5fad…` / `0xf279e6a1…`).** A *lender* supplying to a LlamaLend Vault (or scrvUSD) emits the ERC-4626 pair; a *borrower's* collateral entering the soft-liq band emits the LLAMMA pair. Different topic0, different meaning, sometimes same tx.
7. **scrvUSD is a Yearn V3 vault, deployed as an EIP-1167 clone.** It emits the ERC-4626 `Deposit`/`Withdraw` **and** Yearn events (`StrategyReported` `0x7f2ad1d3…` is the yield heartbeat; `Shutdown` `0x4426aa1f…` is the emergency signal). Its yield is *donated profit* from the **RewardsHandler** (`0xe8d1E253…`), not from a lending strategy — `get_default_queue()` is empty. `role_manager` is the Curve DAO Ownership Agent.
8. **Mint markets, scrvUSD, PegKeepers, FlashLender, and fees are Ethereum-only.** Any "crvUSD on L2" is the **bridged token**; any "lending on L2" is **LlamaLend** (ETH/ARB/OP only). Base/BSC/Avalanche/Polygon/Gnosis have *only* the token.
9. **One Controller + one LLAMMA per collateral (mint) or per (collateral, borrow-token) pair (lend).** sfrxETH has two mint markets (v1 ix 0 + v2 ix 4). Enumerate; don't assume a single market per asset.
10. **Read the MonetaryPolicy and PegKeeper set live — they drift.** Current mint policy is `0x07491d12…` (AggMonetaryPolicy3) on 8/9 markets; JS libs still cache `0x1E7d3bf9…`. PegKeepers rotated from a v1 set (no regulator) to a v2 set behind the **PegKeeperRegulator** `0x36a04CAf…`. Tell v1 from v2 by `regulator()` (v2 returns the regulator; v1 reverts).
11. **`SetRate` is overloaded across two contracts.** The **AMM** `SetRate(uint256,uint256,uint256)` (`0x52543716…`, 3-arg, the interest heartbeat) ≠ the **MonetaryPolicy** `SetRate(uint256)` (`0x2640b401…`, 1-arg). Different topic0, different emitter.
12. **PegKeeper actions defend the peg.** `Provide` (`0x8d685bd3…`) mints crvUSD into a peg pool when crvUSD > $1; `Withdraw` (`0x5b6b431d…`) pulls it back when < $1. A burst of `Provide`/`Withdraw` is a peg-stress signal, not user activity. The peg pools are crvUSD/USDC, /USDT, /USDP, /TUSD (v1) and crvUSD/USDC, /USDT, pyUSD/, /frxUSD, GHO/ (v2).
13. **Two AggregateStablePrice oracles coexist.** The current one is `0x18672b1b…` (used by AggMonetaryPolicy3 + v2 PegKeepers); the older `0xe5afcf33…` backs sfrxETH-v1's policy + the v1 PegKeepers. Both report `stablecoin()` = crvUSD. Resolve via the policy's `PRICE_ORACLE()`.
14. **`NewVault`/`AddMarket` are how you discover new markets.** Watch `OneWayLendingFactory.NewVault` (`0x2a854a59…`, LlamaLend) and `ControllerFactory.AddMarket` (`0xebbe0dfd…`, mint). LlamaLend market creation is **permissionless** (anyone can deploy a vault for any token pair) — volume of `NewVault` can be high; classify by token pair.
15. **The two `SetImplementations` differ.** ControllerFactory: `SetImplementations(address,address)` (`0x1694b070…`); OneWayLendingFactory: `SetImplementations(address,address,address,address,address,address)` (`0x91d63b24…`). Both signal a blueprint swap that affects *future* markets only.
16. **crvUSD bridged tokens differ per chain and use different bridges.** OFT (BSC/Avax), Arbitrum gateway, OP/Base standard bridge, Polygon-PoS, Gnosis-omnibridge (the only EIP-1967 proxy). Only the Gnosis one can `Upgraded`.
17. **Bytea hex literals need an even digit count:** 40 chars (addresses), 64 chars (topic0), 8 chars (selector).

---

## 11. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Controller events (MINT and LEND — same blueprint; disambiguate by emitter) =====
TOPIC_CTRL_BORROW                   = '\xe1979fe4c35e0cef342fef5668e2c8e7a7e9f5d5d1ca8fee0ac6c427fa4153af'
TOPIC_CTRL_REPAY                    = '\x77c6871227e5d2dec8dadd5354f78453203e22e669cd0ec4c19d9a8c5edb31d0'
TOPIC_CTRL_REMOVE_COLLATERAL        = '\xe25410a4059619c9594dc6f022fe231b02aaea733f689e7ab0cd21b3d4d0eb54'
TOPIC_CTRL_LIQUIDATE                = '\x642dd4d37ddd32036b9797cec464c0045dd2118c549066ae6b0f88e32240c2d0'  -- hard-liq (5-arg, 1 indexed)
TOPIC_CTRL_USER_STATE               = '\xeec6b7095a637e006c79c1819d696e353a8f703db2c49fc0219e17a8fd04f7f2'
TOPIC_CTRL_SET_MONETARY_POLICY      = '\x51fabb88f7860c9dbcc2a5a9b69a8b9476d63b87124591f97254e29f0e8daaeb'
TOPIC_CTRL_SET_BORROWING_DISCOUNTS  = '\xe2750bf9a7458977fcc01c1a0b615d12162f63b18cad78441bd64c590b337eca'
TOPIC_CTRL_COLLECT_FEES             = '\x5393ab6ef9bb40d91d1b04bbbeb707fbf3d1eb73f46744e2d179e4996026283f'
-- ===== LLAMMA AMM events (MINT and LEND) =====
TOPIC_LLAMMA_TOKEN_EXCHANGE         = '\xb2e76ae99761dc136e598d4a629bb347eccb9532a5f8bbd72e18467c3c34cc98'  -- ALSO = DEX old-tricrypto-2 TokenExchange; key on emitter
TOPIC_LLAMMA_DEPOSIT                = '\x7e4f5fadb3361b33669433b392d1a203b7a236710eb272650052592e6ce62f09'  -- (provider,amount,n1,n2)
TOPIC_LLAMMA_WITHDRAW               = '\xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568'  -- ALSO = DEX veCRV Withdraw; key on emitter
TOPIC_LLAMMA_SET_RATE               = '\x52543716810f73c3fa9bca74622aecb6d3614ca4991472f3e999d531c2f6afb8'  -- 3-arg
TOPIC_LLAMMA_SET_FEE                = '\x00172ddfc5ae88d08b3de01a5a187667c37a5a53989e8c175055cb6c993792a7'
TOPIC_LLAMMA_SET_ADMIN_FEE          = '\x2f0d0ace1d699b471d7b39522b5c8aae053bce1b422b7a4fe8f09bd6562a4b74'
-- ===== ERC-4626 Vault (LlamaLend) AND scrvUSD =====
TOPIC_ERC4626_DEPOSIT               = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'  -- (sender,owner,assets,shares)
TOPIC_ERC4626_WITHDRAW              = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'  -- (sender,receiver,owner,assets,shares)
-- ===== scrvUSD (Yearn VaultV3) extras =====
TOPIC_SCRVUSD_STRATEGY_REPORTED     = '\x7f2ad1d3ba35276f35ef140f83e3e0f17b23064fd710113d3f7a5ab30d267811'
TOPIC_SCRVUSD_STRATEGY_CHANGED      = '\xde8ff765a5c5dad48d27bc9faa99836fb81f3b07c9dc62cfe005475d6b83a2ca'
TOPIC_SCRVUSD_DEBT_UPDATED          = '\x5e2b8821ad6e0e26207e0cb4d242d07eeb1cbb1cfd853e645bdcd27cc5484f95'
TOPIC_SCRVUSD_SHUTDOWN              = '\x4426aa1fb73e391071491fcfe21a88b5c38a0a0333a1f6e77161470439704cf8'
-- ===== ControllerFactory (mint) =====
TOPIC_CF_ADD_MARKET                 = '\xebbe0dfde9dde641808b7a803882653420f3a5b12bb405d238faed959e1e3aa3'
TOPIC_CF_SET_DEBT_CEILING           = '\x22d26e5448456e0d2368bca46b2c824717b39390656f1c6314237e11d691e4f2'
TOPIC_CF_MINT_FOR_MARKET            = '\xad17aca0dc59a6d96350f71e2732094471c65b5a5cecd8f95b376edcd5534cc9'
TOPIC_CF_REMOVE_FROM_MARKET         = '\xb21604369d32a00404a085ea01ab0a3f6b63f8a0ebda770e25695572416d9bcf'
TOPIC_CF_SET_IMPLEMENTATIONS        = '\x1694b0703640754583177bb0c9e8d97e4d163cd89d08ae426ef8cb3f47109542'  -- 2-arg
-- ===== OneWayLendingFactory (LlamaLend) =====
TOPIC_OWF_NEW_VAULT                 = '\x2a854a597908740dff5f0846840f167547ea0d7614c43bde3ea49be2e68c07ec'
TOPIC_OWF_SET_IMPLEMENTATIONS       = '\x91d63b24386eae580bbbe65f3f50fd736c41031f36d85641bc13e74ac0cb95bb'  -- 6-arg
TOPIC_OWF_SET_DEFAULT_RATES         = '\x279f1fe0f91b15d983792d0305a146961875690054db0d81bec8d1582461fc65'
-- ===== PegKeeper / Regulator / MonetaryPolicy / Aggregator / FlashLender =====
TOPIC_PEGKEEPER_PROVIDE             = '\x8d685bd3f45d861c759ed7a46ea3d30eb5cc6ce9fe06c526931f94c963bca7d2'
TOPIC_PEGKEEPER_WITHDRAW            = '\x5b6b431d4476a211bb7d41c20d1aab9ae2321deee0d20be3d9fc9b1093fa6e3d'
TOPIC_PEGKEEPER_PROFIT              = '\x357d905f1831209797df4d55d79c5c5bf1d9f7311c976afd05e13d881eab9bc8'
TOPIC_AGGMP_ADD_PEG_KEEPER          = '\xf395c3706a8194522b942d1992143a7b60a92a83f99ec30e3833c7630e3c1331'
TOPIC_AGGMP_REMOVE_PEG_KEEPER       = '\x52182c3057b74a074adcacf89ba9ff9860a1265c89cfecd998a111e06bc80267'
TOPIC_REGULATOR_WORST_PRICE_THRESH  = '\xb4a3856a5d3f85a0db622badf557a5c47e98ef4ce2f9fced462328721ee80c76'
TOPIC_REGULATOR_PRICE_DEVIATION     = '\x406e5474c6819832e7834a919ce48a8c8d909e2d9a3a0fe5378844c3b51b46a2'
TOPIC_REGULATOR_DEBT_PARAMETERS     = '\x069906c4131a2e2c0b2f32f351644b280d95237fa3f095f91ac69cac88ab9234'
TOPIC_AGGMP_SET_RATE                = '\x2640b4015d3473fd09bf2b30939e17deb4068cdacf3892136e737e166ceb3210'  -- 1-arg (NOT the AMM 3-arg SetRate)
TOPIC_AGG_ADD_PRICE_PAIR            = '\xfc47ca1d88e8137eb4cc32afb4bb62d3eb485c114be5e98f0533d9825311c748'
TOPIC_AGG_REMOVE_PRICE_PAIR         = '\x017592f2f16e82cccce60102865c737270289c308f34ff88e754d5e99ea0bae1'
TOPIC_FLASHLENDER_FLASHLOAN         = '\xc76f1b4fe4396ac07a9fa55a415d4ca430e72651d37d3401f3bed7cb13fc4f12'
-- ===== Fee plumbing =====
TOPIC_FEESPLITTER_FEE_DISPATCHED    = '\x3ec7c36ff485aa9a27938503e3094604652d1f7262464127fb79577970abe12a'
TOPIC_FEESPLITTER_SET_RECEIVERS     = '\xcef5c0f74b8e26cac8a85442177d7e9b9792cc2b2627efce6a5c3d764fc34df1'
TOPIC_REWARDSHANDLER_MIN_WEIGHT     = '\x9643e1bd3bef4938b3e5d13d09a89e903194372751add4131e51ba3b4e92feaa'
-- ===== ERC-20 / proxy =====
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_UPGRADED                      = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'  -- only Gnosis bridged crvUSD

-- ===== Enumeration selectors =====
SEL_N_COLLATERALS                   = '\x12397fa1'   -- ControllerFactory
SEL_COLLATERALS                     = '\x24c1173b'   -- ControllerFactory.collaterals(uint256)
SEL_MARKET_COUNT                    = '\xfd775c78'   -- OneWayLendingFactory
SEL_VAULTS                          = '\x8c64ea4a'   -- OneWayLendingFactory.vaults(uint256)
SEL_CONTROLLERS                     = '\xe94b0dd2'   -- both factories
SEL_AMMS                            = '\x86a8cdbc'   -- both factories
SEL_FACTORY_STABLECOIN              = '\xe9cbd822'   -- ControllerFactory.stablecoin()
SEL_PEG_KEEPERS                     = '\xf6235138'   -- (AggMP / Regulator).peg_keepers(uint256)
SEL_PK_REGULATOR                    = '\xdd8fee14'   -- PegKeeperV2.regulator() (v1 reverts)
SEL_MP_PRICE_ORACLE                 = '\x0a19399a'   -- AggMP.PRICE_ORACLE()

-- ===== Ethereum (chain ID 1) — full stack =====
ETH_CRVUSD                          = '\xf939e0a03fb07f59a73314e73794be0e57ac1b4e'
ETH_CONTROLLER_FACTORY              = '\xc9332fdcb1c491dcc683bae86fe3cb70360738bc'  -- mint
ETH_ONEWAY_LENDING_FACTORY          = '\xea6876dde9e3467564acbee1ed5bac88783205e0'  -- LlamaLend
ETH_SCRVUSD                         = '\x0655977feb2f289a4ab78af67bab0d17aab84367'
ETH_SCRVUSD_IMPL                    = '\xd8063123bba3b480569244ae66bfe72b6c84b00d'
ETH_REWARDS_HANDLER                 = '\xe8d1e2531761406af1615a6764b0d5ff52736f56'
ETH_AGG_STABLE_PRICE                = '\x18672b1b0c623a30089a280ed9256379fb0e4e62'  -- current peg oracle
ETH_AGG_STABLE_PRICE2_OLD           = '\xe5afcf332a5457e8fafcd668bce3df953762dfe7'
ETH_AGG_MONETARY_POLICY3            = '\x07491d124ddb3ef59a8938fcb3ee50f9fa0b9251'  -- current (8/9 markets)
ETH_AGG_MONETARY_POLICY2            = '\x1e7d3bf98d3f8d8ce193236c3e0ec4b00e32daae'  -- prior
ETH_FLASH_LENDER                    = '\xa7a4bb50af91f90b6feb3388e7f8286af45b299b'
ETH_PEGKEEPER_REGULATOR             = '\x36a04caffc681fa179558b2aaba30395cddd855f'
ETH_FEE_SPLITTER                    = '\x2dfd89449faff8a532790667bab21cf733c064f2'  -- ControllerFactory.fee_receiver(); -> RewardsHandler
ETH_FEE_DISTRIBUTOR_CRVUSD          = '\xd16d5ec345dd86fb63c6a9c43c517210f1027914'  -- legacy veCRV fee sink
ETH_CRVUSD_DAO_ADMIN                = '\xb7400d2ea0f6dc1d7b153aa430b9e572f28afb79'
-- mint markets (Controllers)
ETH_MINT_CTRL_SFRXETH_V1            = '\x8472a9a7632b173c8cf3a86d3afec50c35548e76'
ETH_MINT_CTRL_WSTETH                = '\x100daa78fc509db39ef7d04de0c1abd299f4c6ce'
ETH_MINT_CTRL_WBTC                  = '\x4e59541306910ad6dc1dac0ac9dfb29bd9f15c67'
ETH_MINT_CTRL_WETH                  = '\xa920de414ea4ab66b97da1bfe9e6eca7d4219635'
ETH_MINT_CTRL_SFRXETH_V2            = '\xec0820efafc41d8943ee8de495fc9ba8495b15cf'
ETH_MINT_CTRL_TBTC                  = '\x1c91da0223c763d2e0173243eadaa0a2ea47e704'
ETH_MINT_CTRL_WEETH                 = '\x652aea6b22310c89dcc506710cad24d2dba56b11'
ETH_MINT_CTRL_CBBTC                 = '\xf8c786b1064889ffd3c8a08b48d5e0c159f4cbe3'
ETH_MINT_CTRL_LBTC                  = '\x8aca5a776a878ea1f8967e70a23b8563008f58ef'
-- mint markets (LLAMMAs)
ETH_MINT_AMM_WSTETH                 = '\x37417b2238aa52d0dd2d6252d989e728e8f706e4'
ETH_MINT_AMM_WBTC                   = '\xe0438eb3703bf871e31ce639bd351109c88666ea'
ETH_MINT_AMM_WETH                   = '\x1681195c176239ac5e72d9aebacf5b2492e0c4ee'
-- v2 PegKeepers (behind regulator)
ETH_PEGKEEPER_V2_USDC               = '\x9201da0d97caaaff53f01b2fb56767c7072de340'
ETH_PEGKEEPER_V2_USDT               = '\xfb726f57d251ab5c731e5c64ed4f5f94351ef9f3'
ETH_PEGKEEPER_V2_PYUSD              = '\x3fa20eaa107de08b38a8734063d605d5842fe09c'
ETH_PEGKEEPER_V2_FRXUSD             = '\x338cb2d827112d989a861cde87cd9ffd913a1f9d'
ETH_PEGKEEPER_V2_GHO                = '\x53876b157decf04389eed66c7c29d73863f8c50b'
-- v1 PegKeepers (no regulator)
ETH_PEGKEEPER_V1_USDC               = '\xaa346781ddd7009caa644a4980f044c50cd2ae22'
ETH_PEGKEEPER_V1_USDT               = '\xe7cd2b4eb1d98cd6a4a48b6071d46401ac7dc5c8'
ETH_PEGKEEPER_V1_USDP               = '\x6b765d07cf966c745b340adca67749fe75b5c345'
ETH_PEGKEEPER_V1_TUSD               = '\x1ef89ed0edd93d1ec09e4c07373f69c49f4dccae'

-- ===== Arbitrum (42161) =====
ARB_CRVUSD                          = '\x498bf2b1e120fed3ad3d42ea2165e9b73f99c1e5'  -- proxy (L2 gateway)
ARB_ONEWAY_LENDING_FACTORY          = '\xcaec110c784c9df37240a8ce096d352a75922dea'  -- market_count 22

-- ===== Optimism (10) =====
OP_CRVUSD                           = '\xc52d7f23a2e460248db6ee192cb23dd12bddcbf6'
OP_ONEWAY_LENDING_FACTORY           = '\x5ea8f3d674c70b020586933a0a5b250734798bef'  -- market_count 5
OP_ONEWAY_LENDING_FACTORY_V2        = '\x1973ed17c267245510a390e0dce4fbcd9d2685f0'  -- market_count 5

-- ===== Base (8453) — token only =====
BASE_CRVUSD                         = '\x417ac0e078398c154edfadd9ef675d30be60af93'

-- ===== BNB (56) / Avalanche (43114) / Polygon (137) / Gnosis (100) — token only =====
BSC_CRVUSD                          = '\xe2fb3f127f5450dee44afe054385d74c392bdef4'  -- LayerZero OFT
AVAX_CRVUSD                         = '\xcb7c161602d04c4e8af1832046ee08aaf96d855d'  -- LayerZero OFT
POL_CRVUSD                          = '\xc4ce1d6f5d98d65ee25cf85e9f2e9dcfee6cb5d6'  -- Polygon-PoS bridged
GNO_CRVUSD                          = '\xabef652195f98a91e490f047a5006b71c85f058d'  -- EIP-1967 proxy
GNO_CRVUSD_IMPL                     = '\x199084efbd7fe14d217bbf22fdc6e2ed7266ddd4'

-- ===== Universal =====
EIP1967_IMPL_SLOT                   = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 12. Verification & sources

How the constants in this doc were produced (2026-06-02):

- **Event topic0 / selectors:** computed locally as `keccak256(signature)` with pycryptodome from the **deployed** canonical signatures. Controller (`Borrow`/`Repay`/`RemoveCollateral`/`UserState`/`CollectFees`) and LLAMMA (`TokenExchange`/`Deposit`/`Withdraw`/`SetRate`) topic0s **confirmed against live `eth_getLogs`** on the wstETH mint market (Controller `0x100daa78…`: 34 UserState / 19 Borrow / 12 Repay / 13 CollectFees / 3 RemoveCollateral in a 49k-block window; AMM `0x37417b22…`: 90 TokenExchange / 47 SetRate / 31 Withdraw / 31 Deposit) **and** LlamaLend market #9 (identical topic set). **`Liquidate` topic0 `0x642dd4d3…` confirmed by PUSH32 bytecode scan** in all 9 mint Controllers + sampled lend Controllers (the 7-arg master-repo variant `0xa452ca3c…` appears in none). ERC-4626 `Deposit`/`Withdraw` and Yearn `StrategyReported` confirmed on live scrvUSD (`0x0655977F…`: 338 Deposit / 397 Withdraw / 2 StrategyReported) and LlamaLend Vault #9. `NewVault` (`0x2a854a59…`) confirmed on a live OneWayLendingFactory log.
- **Markets enumerated live:** `ControllerFactory.n_collaterals()` = 9 → `collaterals(i)`/`controllers(i)`/`amms(i)` (collateral symbols decoded: sfrxETH×2, wstETH, WBTC, WETH, tBTC, weETH, cbBTC, LBTC); `OneWayLendingFactory.market_count()` = 48 (ETH) / 22 (ARB) / 5+5 (OP) → `vaults(i)`/`controllers(i)`/`amms(i)`.
- **Addresses:** crvUSD token, factories, scrvUSD, RewardsHandler, FlashLender, AggregateStablePrice, AggMonetaryPolicy, PegKeepers, PegKeeperRegulator all **`eth_getCode`/`eth_call`-verified** on Ethereum. crvUSD `symbol()` = `crvUSD` verified on all 8 chains. Proxy classification via EIP-1967 slot reads + bytecode-head inspection (crvUSD immutable on ETH; Gnosis = EIP-1967 proxy → `0x199084EF…`; Arbitrum = L2-gateway proxy; OP/Base/BSC/Avax = full bridged impl; scrvUSD + LlamaLend Vaults = EIP-1167 clones → impls `0xd8063123…` / `0xc014f34d…`). LlamaLend/mint-factory **absence** on Base/BSC/Avalanche/Polygon/Gnosis confirmed by `eth_getCode` returning `0x` for the ETH/ARB factory addresses on each.
- **Source repos:** [`curvefi/curve-stablecoin`](https://github.com/curvefi/curve-stablecoin) (Controller/AMM/ControllerFactory/PegKeeper/Regulator/AggMonetaryPolicy/AggregateStablePrice/FlashLender + the LlamaLend `lending/` dir — **but the `master` Vyper-0.4 rewrite does not match deployed; signatures were taken from live bytecode/logs, see §0**); [`curvefi/scrvusd`](https://github.com/curvefi/scrvusd) (Yearn `VaultV3.vy` + `RewardsHandler.vy` + `StablecoinLens.vy` + `TWA.vy`); [`curvefi/fee-splitter`](https://github.com/curvefi/fee-splitter) (`FeeSplitter.vy` + `ControllerMulticlaim.vy`).
- **Address aliases:** [`curvefi/curve-llamalend.js`](https://github.com/curvefi/curve-llamalend.js) `src/constants/aliases.ts` + `llammas.ts` (OneWayLendingFactory per chain, scrvUSD `st_crvUSD`, mint LLAMMAs) — **note `curvefi/curve-js`'s `crvusd_factory` `0x4F8846Ae…` is explicitly marked `// <-- DUMMY` and is NOT the real factory** (it has `admin()`+`coins()` but no `market_count`/`NewVault`); the real OneWayLendingFactory is `0xeA6876DD…`. [`curvefi/curve-stablecoin-js`](https://github.com/curvefi/curve-stablecoin-js) `src/crvusd.ts` (mint `FACTORY` + a prior `PEG_KEEPERS` list). Curve technical docs RewardsHandler / fees pages (several deployment pages 404'd at fetch time; addresses were taken from on-chain reads + the JS libs instead).

### 12.1 Items not fully confirmed (flagged)

- **FeeSplitter** `0x2DfD89449faFF8a532790667baB21cF733C064f2` is **confirmed** (it is `ControllerFactory.fee_receiver()`; `version()` "0.1.0"; carries the `FeeDispatched`/`SetReceivers`/`LivenessProtectionTriggered` topics; `n_receivers()` = 2 with `receivers(0)` = the RewardsHandler). Note the legacy `0xD16d5eC3…` is the **veCRV crvUSD FeeDistributor**, NOT the FeeSplitter (it lacks those topics and reverts `n_receivers()`). The FeeSplitter address has been deployed only since the 2024 fee-system rollout (Ethereum + Gnosis; "Arbitrum soon" per Curve docs) — on the 8 target chains it is **Ethereum-only**.
- **OneWayLendingFactory `SetImplementations` arity** (§1.6): the deployed factories may carry an older arity than the 6-arg `master` signature; the `NewVault` topic is confirmed live, `SetImplementations`/`SetDefaultRates` are source-computed.
- **Controller/AMM function selectors** (§2.1/§2.2): all recomputed cleanly from the deployed monolithic-Vyper signatures; both arities are listed where an overload exists. The core verbs (`create_loan`/`borrow_more`/`liquidate`/`exchange`) are stable across deploys, but `add_collateral`/`remove_collateral`/`repay` vary by generation — **prefer the events for detection**, PUSH4-scan a specific Controller if calldata matching is required.
- **weETH mint market (ix 6)** checksum casing is approximate (reproduced from the raw 32-byte return); the lowercase form in §11 is canonical.
- **L2 LlamaLend topic universality** is asserted from the shared blueprint + the byte-identical Ethereum bytecode (LIQ5/SetMonetaryPolicy scan), not from a live L2 log capture (sampled Arbitrum/Optimism markets had no activity in the 49k-block window allowed by the public RPC).

# Trader Joe (LFJ) — Protocol Reference Index

Monitoring-grade references for **Trader Joe** (rebranded **LFJ** in 2024) across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137)**. Verified against the canonical `lfj-gg/joe-v2` + `traderjoe-xyz/joe-core` repos, the `developers.lfj.gg` deployment pages, and live RPC (`eth_call` / `eth_getLogs` / `eth_getStorageAt` via publicnode) on **2026-06-05**.

Trader Joe is **two AMM designs**: **Joe V1** (a Uniswap V2 fork — constant-product pairs) and **Liquidity Book (LB)** — a discretized-bin concentrated-liquidity AMM that ships in **three on-chain versions V2.0 / V2.1 / V2.2**. The router's own `Version` enum is `{V1, V2, V2_1, V2_2}` (it routes across all four). One file per version; each follows the same section order. **These files cover the AMM core only** — LFJ's product lineage continues past the AMM into **"Joe v3" = Token Mill** (a bonding-curve token launchpad, live on Avalanche) and **"Joe v4" = Bid Barn** (an on-chain CLOB, upcoming); both are architecturally distinct from the LB AMM and are scoped as boundary notes below, not expanded here.

| File | Layer | Status |
|------|-------|--------|
| [v1.md](v1.md) | **Joe V1** — Uniswap-V2-fork AMM (`JoeFactory`/`JoeRouter02`/`JoePair`) **+ the protocol-wide token & staking layer** (JOE, xJOE, veJOE, rJOE, `MasterChefJoe V2/V3`, `BoostedMasterChefJoe`, `StableJoeStaking`=sJOE, `VeJoeStaking`, RocketJoe launchpad) | Live (AMM legacy, farms wound down). V1 AMM on **Avax + Arb + BSC**; token/staking layer is **Avalanche-only**. |
| [v2.0.md](v2.0.md) | **LB 2.0** — the original Liquidity Book. Singular events (`Swap`/`DepositedToBin`/`WithdrawnFromBin`), `uint256` ids, EIP-1167 pair clones, `LBToken` still emits `TransferSingle`. | **Legacy.** Avax(30 pairs) + Arb(43) + BSC(10). Few pairs, low volume. |
| [v2.1.md](v2.1.md) | **LB 2.1** — audited rewrite. Plural batch events (`DepositedToBins`/`Swap` with `uint24 id`+`bytes32`), clone-with-immutable-args pairs, `LBToken` `TransferBatch`-only. **Holds the full shared LB-2.x topic/selector tables.** | Live. **Only LB version on Ethereum** (unique addresses). Avax/Arb/BSC/ETH. |
| [v2.2.md](v2.2.md) | **LB 2.2** — current/dominant. **= LB 2.1 events + `HooksParametersSet` + LB Hooks** (`LBHooksManager`). **+ current-era periphery**: Joe Aggregator (`RouterLogic`/`ForwarderLogic`), Limit Orders, Autopools (`Vault Factory`/`APTFarm`). | **Live, dominant** (Avax 16,288 pairs). **Avax + Arb only** (not BSC, not ETH). |

Each file: **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function signatures** (chain-agnostic 4-byte selectors) → **Addresses** (network-specific) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## At-a-glance presence matrix (✓ = `getNumberOfLBPairs`/`allPairsLength` returns; — = `0x` from `eth_getCode`)

| Chain | ID | V1 AMM | LB 2.0 | LB 2.1 | LB 2.2 | JOE token | Staking/Farms |
|-------|----|--------|--------|--------|--------|-----------|---------------|
| Avalanche | 43114 | ✓ 48,766 pairs | ✓ 30 | ✓ 2,072 | ✓ **16,288** | ✓ `0x6e84…0fDd` (native) | ✓ (all: MCJ V2/V3, BoostedMCJ, sJOE, veJOE, rJOE) |
| Arbitrum | 42161 | ✓ 259 | ✓ 43 | ✓ 533 | ✓ 113 | ✓ `0x371c…2f07` (bridged) | — (no sJOE/MCJ at AVAX addrs) |
| BNB Chain | 56 | ✓ 42 | ✓ 10 | ✓ 147 | **—** | ✓ `0x371c…2f07` (bridged) | — |
| Ethereum | 1 | **—** | **—** | ✓ 15 (**unique addrs** `0xDC8d…943a`) | **—** | ✓ `0x371c…2f07` (bridged) | — |
| Base | 8453 | **—** | **—** | **—** | **—** | **—** | **—** |
| Optimism | 10 | **—** | **—** | **—** | **—** | **—** | **—** |
| Polygon PoS | 137 | **—** | **—** | **—** | **—** | **—** | **—** |

**Trader Joe / LFJ is NOT deployed on Base, Optimism, or Polygon PoS.** Confirmed on-chain: the deterministic LB 2.1 factory `0x8e42f2F4…`, LB 2.2 factory `0xb43120c4…`, and their routers all return **`0x` (empty)** from `eth_getCode` on Base/OP/Polygon — no decoy contract sits there either (unlike Sushi's shared-address case). The only other live chain is **Monad** (out of scope here). Also out of scope: forks of this codebase on other chains (e.g. **Merchant Moe** on Mantle, **Metropolis** — same LB bytecode, different deployer).

## Cross-cutting facts worth knowing before you start

- **Topics + selectors are 100% chain-agnostic; addresses are per-chain.** Compute a `topic0` once, watch it on every chain. Most LB DEX addresses are **deterministic across Avax/Arb/BSC** (same CREATE2 deploy → identical address): LB 2.1 factory `0x8e42f2F4…`, LB 2.2 factory `0xb43120c4…`, routers, quoters, **even the LBPair implementations** (`0x3e30fdae…` V2.1, `0x7a5b4e30…` V2.2) and `LimitOrderManager`/`Vault Factory`. **Ethereum is the exception** — its LB 2.1 stack was deployed separately and has *entirely different* addresses (factory `0xDC8d77b6…`, impl `0x7f89d5e9…`). Always key on `(chainId, address)` and re-`eth_getCode` before trusting a "deterministic" address on a new chain.
- **Four "a swap happened" event topics — one per design/version. Do not conflate.**
  - Joe **V1** pair: `Swap(address,uint256,uint256,uint256,uint256,address)` `0xd78ad95f…` — **identical to Uniswap/Sushi V2** (disambiguate by pair/factory address).
  - LB **2.0** pair: `Swap(address,address,uint256,bool,uint256,uint256,uint256,uint256)` `0xc528cda9…` (singular, `uint256 id`, `bool swapForY`).
  - LB **2.1 + 2.2** pair: `Swap(address,address,uint24,bytes32,bytes32,uint24,bytes32,bytes32)` `0xad7d6f97…` (**2.1 and 2.2 share this exact topic0** — packed `bytes32` amounts).
- **LB 2.0 → 2.1 renamed the liquidity events from singular to plural**, which changes the topic0: `DepositedToBin`→`DepositedToBins`, `WithdrawnFromBin`→`WithdrawnFromBins`, `CompositionFee`→`CompositionFees`. A 2.0 monitor and a 2.1/2.2 monitor need different topic0 sets.
- **`LBPairCreated(address,address,uint256,address,uint256)` `0x2c8d104b…` is the SAME topic0 on all three LB factory versions** — the single best "new LB pool" signal; disambiguate the version by *which factory address* emitted it.
- **`LBToken` is not ERC-1155 but borrows its exact event signatures** → `TransferBatch` `0x4a39dc06…`, `ApprovalForAll` `0x17307eab…` (and, **in LB 2.0 only**, `TransferSingle` `0xc3d58168…`) **collide with ERC-1155 topic0s**. LB position transfers will show up in any ERC-1155 transfer monitor. In **LB 2.1/2.2 there is no `TransferSingle`** — single transfers emit a 1-element `TransferBatch`.
- **Many `Deposit`/`Withdraw` topic0s collide — within Trader Joe and with other farms.** `Deposit(address,uint256,uint256)` `0x90890809…` is emitted by MasterChefJoe **and** sJOE **and** Sushi/Pancake MasterChef. `Withdraw(address,uint256,uint256)` `0xf279e6a1…` is emitted by MasterChefJoe, veJOE staking, Sushi, Curve, Balancer. **Always disambiguate by contract address.**
- **What's upgradeable vs immutable:** the **DEX core is immutable** — LB/V1 factories, routers, quoters are plain contracts; **V1 `JoePair` is a full CREATE2 contract** (Uni-V2 style); **LB pairs are clones** (EIP-1167 in 2.0, clone-with-immutable-args in 2.1/2.2) that are themselves not upgradeable, though the factory can point future pairs at a new impl via `LBPairImplementationSet`. The **upgradeable (EIP-1967 proxy) set is the staking/periphery layer**: `StableJoeStaking`(sJOE), `VeJoeStaking`, `BoostedMasterChefJoe`, `RocketJoeStaking`, `LBHooksManager`, `LimitOrder`, Autopool `Vault Factory`. JOE/xJOE/veJOE/rJOE tokens and `MasterChefJoe V2/V3` are immutable.

## Verification methodology

- **Topic0 / selectors:** computed locally with keccak-256 (pycryptodome) from verbatim signatures in `lfj-gg/joe-v2` (tags `v2.0.0`=`07f1021`, `v2.1.0`=`8eeb42d`, `v2.2.0`=`1297c38`=`main`) and `traderjoe-xyz/joe-core`; **validated against live `eth_getLogs`** — LB 2.2 `Swap` (7,667 hits on Avax AVAX/USDC), LB 2.1 `Swap` (same topic0), LB 2.0 `Swap`+`DepositedToBin`+`WithdrawnFromBin`+`CompositionFee`+`FlashLoan`+`TransferSingle` (≈13k hits on the V2.0 AVAX/USDC pair at block 28.0M), `LBPairCreated` (V2.1 factory @ block 32.0M).
- **Addresses:** parsed from `developers.lfj.gg/deployment-addresses/{avalanche,arbitrum,legacy-pools/bsc,legacy-pools/ethereum}`, then **existence-checked via `eth_getCode` + a functional probe** on each chain (LB factory `getNumberOfLBPairs()`, V1 factory `allPairsLength()`, token `symbol()`/`name()`). Absence on Base/OP/Polygon recorded explicitly.
- **Proxy/immutability:** EIP-1967 impl slot `0x360894…bbc` read live via `eth_getStorageAt`; LBPair clone bytecode read and decoded (45-byte EIP-1167 in 2.0 → impl `0x49d11cdc…`; 97-byte immutable-args clone in 2.1/2.2 → impls `0x3e30fdae…`/`0x7a5b4e30…`).

## Coverage caveats

- **Instances are not enumerated.** V1 pairs (48,766 on Avax) and LB pairs (16,288 on Avax V2.2) are permissionless and numerous — the docs list per-chain **singletons** (factories, routers, quoters, impls, tokens, staking). Discover pairs from `PairCreated` (V1) / `LBPairCreated` (LB).
- **Scoped-down but listed:** the **token & staking layer** (Avalanche-only) is documented in [v1.md](v1.md) with verified addresses; **current-era periphery** (Joe Aggregator, Limit Orders, Autopools) is in [v2.2.md](v2.2.md). `MoneyMaker` (fee→JOE buyback router) exists but is not address-verified here. RocketJoe launchpad (`lfj-gg/rocket-joe`: `RocketJoeFactory` deploys per-IDO `LaunchEvent` contracts; stake JOE→earn rJOE→burn rJOE for AVAX allocation) — rJOE token + `RocketJoeStaking` proxy are in [v1.md](v1.md); the factory/launch-event contracts are summarized, not expanded.
- **Newer product lines (NOT expanded — separate architectures from the LB AMM).** A 2026-06 sweep confirmed LFJ ships beyond the AMM:
  - **Token Mill ("Joe v3")** — bonding-curve token launchpad (repo `lfj-gg/token-mill`; `TMFactory`/`TMMarket`/`Router`, custom bid/ask bonding curves + vesting). **Live on Avalanche** (also Solana, non-EVM, out of scope). Verified on-chain (Avax): `TMFactory` `0x501ee2D4AA611C906F785e10cC868e145183FCE4` (EIP-1967 proxy → impl `0xbaa2d7d2…`; `STAKING()`→`0xf2c15bd1…`), `Router` `0x1b1f2Bfc5e551b955F2a3F973876cEE917FB4d05`, `Lens` `0x1713b36423f91A896D7D9798A9e58bab18e711dc`. Not on Arbitrum/BSC/Ethereum/Base/OP/Polygon. **Bonding-curve markets, NOT bins** — give it its own file if the alert pipeline needs its topics/selectors.
  - **Bid Barn ("Joe v4")** — an on-chain Central Limit Order Book (CLOB), announced/upcoming as of mid-2026; not confirmed deployed on the 7 target chains in this sweep.
  - **Out of scope by chain:** **Monad** (live LFJ chain, not in the 7-chain target set) and **Solana** (non-EVM). Forks of this exact bytecode by other teams — **Merchant Moe** (Mantle), **Metropolis** — are different protocols at different deployer addresses; do not attribute them to LFJ.

## Authoritative sources

- Repos: [`lfj-gg/joe-v2`](https://github.com/lfj-gg/joe-v2) (Liquidity Book; formerly `traderjoe-xyz/joe-v2`), [`traderjoe-xyz/joe-core`](https://github.com/traderjoe-xyz/joe-core) (V1 + token + MasterChef + staking).
- Addresses: [developers.lfj.gg/deployment-addresses](https://developers.lfj.gg/deployment-addresses) · docs [docs.lfj.gg](https://docs.lfj.gg).
- Explorers: [Snowtrace](https://snowtrace.io) · [Arbiscan](https://arbiscan.io) · [BscScan](https://bscscan.com) · [Etherscan](https://etherscan.io).

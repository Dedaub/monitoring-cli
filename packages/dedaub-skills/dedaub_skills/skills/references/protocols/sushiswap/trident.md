# SushiSwap Trident — Compressed Deployment Reference (BentoBox AMM, legacy/deprecated)

**Status:** topic0/selectors via `cast keccak`/`cast sig`. **Trident is largely deprecated/wound down** — addresses are NOT exhaustively enumerated here; pull them from the `sushi-labs/sushi` SDK (`bentobox`/`trident` features) and confirm on a block explorer before use.
**Scope:** SushiSwap **Trident** — the BentoBox-based AMM framework (ConstantProduct / Stable / Hybrid pools). Other versions: [`v2.md`](v2.md) (classic AMM), [`v3.md`](v3.md) (concentrated liquidity). **Protocol-wide pieces** (SUSHI token, MasterChef/MiniChef staking, RedSnwapper/RouteProcessor router) are in [`v2.md`](v2.md).
**Where deployed:** Ethereum mainnet plus Polygon, Arbitrum, Optimism, Avalanche, BSC (and others: BTTC, Fantom, Gnosis, Kava, Metis). It has minimal current activity. On Ethereum the `MasterDeployer` is at `0x10c19390e1ac2fd6d0c3643a2320b0aba38e5baa` (live on-chain).

---

## Topics (chain-agnostic) — `topic0 -> Event(types)`

### BentoBox (the vault that custodies Trident pool assets)
```
0xb2346165e782564f17f5b7e555c21f4fd96fbc93458572bf0113ea35a958fc55 -> LogDeposit(address,address,address,uint256,uint256)   [token,from,to,amount,share]
0xad9ab9ee6953d4d177f4a03b3a3ac3178ffcb9816319f348060194aa76b14486 -> LogWithdraw(address,address,address,uint256,uint256)
0x6eabe333476233fd382224f233210cb808a7bc4c4de64f9d76628bf63c677b1a -> LogTransfer(address,address,address,uint256)
0x3be9b85936d5d30a1655ea116a17ee3d827b2cd428cc026ce5bf2ac46a223204 -> LogFlashLoan(address,address,uint256,uint256,address)
0x911c9f20a03edabcbcbd18dca1174cce47a91b234ced7a5a3c60ba0d5b56c5d2 -> LogStrategyProfit(address,uint256)
0x8f1f26eb9b6aa8689dbdd519ead1999d9c8819d4738e403b2003b18197d9cf97 -> LogStrategyLoss(address,uint256)
```

### MasterDeployer + Trident pools
```
0xe469f9471ac1d98222517eb2cdff1ef4df5f7880269173bb782bb78e499d9de3 -> DeployPool(address,address,bytes)            [MasterDeployer: factory,pool,deployData]
0xcd3829a3813dc3cdd188fd3d01dcf3268c16be2fdd2dd21d0665418816e46062 -> Swap(address,address,address,uint256,uint256)   [CP pool: recipient,tokenIn,tokenOut,amountIn,amountOut — verified against source]
0xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a -> Sync(uint256,uint256)                          [Trident pool — verified against source]
```

> **Note:** the Trident CP-pool `Swap`/`Sync` topic0s are verified against the canonical source — `IPool.sol` declares `event Swap(address indexed recipient, address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOut)` and `ConstantProductPool.sol` declares `event Sync(uint256 reserve0, uint256 reserve1)`; both topic0s recompute to the listed values. BentoBox `Log*` and `DeployPool` are computed from well-established signatures.

---

## Function signatures (chain-agnostic)

```
# BentoBox key fns (confirm types against source before use)
deposit(address,address,address,uint256,uint256) -> (uint256,uint256)        [token,from,to,amount,share]
withdraw(address,address,address,uint256,uint256) -> (uint256,uint256)
# MasterDeployer
deployPool(address,bytes) -> address
```

(Selectors not pre-computed here given Trident's deprecated status — compute with `cast sig` against confirmed source signatures if needed.)

---

## Addresses (network-specific)

**Not enumerated (deprecated).** Trident's `BentoBoxV1`, `MasterDeployer`, `ConstantProductPoolFactory`, and `StablePoolFactory` live mainly on Polygon / Arbitrum / Optimism / Avalanche / BSC. Pull current addresses from the `sushi-labs/sushi` SDK (`src/evm/config/features/` bentobox/trident files) and verify on-chain (`cast code` + a functional call) before use. BentoBoxV1 is at `0xf5bce5077908a1b7370b9ae04adc565ebd643966` on Ethereum, Polygon, and BNB (present on-chain, ≈22.8 KB) but is **absent at that address on Arbitrum, Optimism, and Avalanche** — on Arbitrum the SushiSwap BentoBoxV1 lives at `0x74c764d41b77dbbb4fe771dab1939b00b146894a` instead. **The address differs per chain; confirm on the target chain before use.**

Enumerate live Trident pools via the `MasterDeployer.DeployPool` event (topic0 `0xe469f947…`).

---

## Proxies

- **Trident uses EIP-1167 minimal-proxy CLONES.** This is the one place SushiSwap proxies its pools: the `MasterDeployer` / pool factories deploy each Trident pool as a **clone** of a master implementation, and BentoBox itself uses a master-contract + clone model (`deploy()` clones a registered master contract). So a Trident pool's on-chain code is a 1167 clone delegating to a master implementation — **do not expect full per-pool bytecode** (contrast with V2/V3 pools, which are full immutable bytecode; see [`v2.md`](v2.md) / [`v3.md`](v3.md)).

---

## Verification & sources

- topic0s: `cast keccak`. BentoBox `Log*` + `DeployPool` from well-established signatures; Trident pool `Swap`/`Sync` verified against the canonical `sushiswap/trident` source (`IPool.sol` / `ConstantProductPool.sol`).
- Addresses: not gathered/verified this run (deprecated) — source from [`sushi-labs/sushi`](https://github.com/sushi-labs/sushi) and confirm on-chain.
- Protocol-wide SUSHI/staking/router: [`v2.md`](v2.md).

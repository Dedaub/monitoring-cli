# Curve Finance — Protocol Reference Index

Monitoring-grade references for Curve across **Ethereum (1), Arbitrum One (42161), Optimism (10), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Polygon PoS (137)** — plus **Gnosis (100)** as a bonus 8th chain. Verified against live RPC (`publicnode`) + the canonical `curvefi/*` Vyper repos on **2026-06-02**.

Curve is **two product lines** that share governance (veCRV/CRV) but almost no ABI. One file per line, each following the same section layout (spelled out below the table):

| File | Product line | Components | Status |
|------|--------------|------------|--------|
| [curve.md](curve.md) | **AMM / DEX + DAO** | StableSwap (classic + NG), CryptoSwap (old tricrypto-2 + Tricrypto-NG + Twocrypto-NG), all factories, the AddressProvider / AddressProvider-NG / MetaRegistry stack, Root/Child gauge factories, CurveRouterNG, and the CRV / veCRV / GaugeController / Minter / FeeDistributor DAO stack | **Live.** 8 chains. Pools immutable (no proxies). |
| [crvusd.md](crvusd.md) | **crvUSD + LlamaLend + scrvUSD** | crvUSD stablecoin, crvUSD **mint markets** (ControllerFactory + per-collateral Controller/LLAMMA/MonetaryPolicy + PegKeepers), **LlamaLend / Curve Lend** (OneWayLendingFactory + ERC-4626 Vault/Controller/LLAMMA per market), **scrvUSD** savings, and the fee plumbing | **Live.** Mint = ETH only; LlamaLend = ETH/ARB/OP; token bridged to all 8. |

Each file follows: **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function selectors** (chain-agnostic 4-byte) → **Addresses** (per chain, absence noted) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy `\x` bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Curve is not one ABI — it is a family of pool generations.** The *same* event name hashes to *different* `topic0`s across families, so **match on `(topic0, pool-family)`, never on event name alone.** The cleanest fingerprint: **StableSwap uses `int128` coin indices; CryptoSwap (tri/twocrypto, old & NG) uses `uint256`.** The NG rewrites changed field layouts again (dynamic arrays, embedded `fee`/`price` fields).
- **Pools are factory-deployed via EIP-5202 blueprints — enumerate, don't derive.** Unlike Uniswap V2 there is **no single init-code hash** and no CREATE2-from-coins shortcut. Discover pools by watching each factory's `*Deployed` event (curve.md §1.6) or reading the on-chain MetaRegistry, then classify by which family's `topic0` set the pool's logs match. There are tens of thousands of pools/markets; per-instance addresses are **not** enumerated in these files.
- **Three infra contracts share one address across all 8 chains** (verified): **AddressProvider (classic)** `0x0000000022D53366457F9d5E68Ec105046FC4383`, **AddressProvider-NG** `0x5ffe7FB82894076ECB99A30D6A32e969e6e35E98`, and the **Root/Child gauge factory** `0xabC000d88f23Bb45525E447528DBF656A9D55bf5` (Root on Ethereum, Child on every L2 — same address, different bytecode). **Everything else is per-chain — always key on `(chainId, address)`.** The classic and NG AddressProviders have **different, chain-specific `id` maps**; read them live (`get_address(id)`), never assume.
- **crvUSD mint markets and LlamaLend share one engine** (LLAMMA `AMM.vy` + `Controller.vy`), so they emit **byte-identical** `Borrow`/`Repay`/`Liquidate`/`UserState`/`TokenExchange` events. Disambiguate mint-vs-lend **by the emitting contract address** (and which factory minted it), never by topic0.
- **Topic0 collisions to watch** (always pair topic0 with the emitter): the LLAMMA `TokenExchange` (`0xb2e76ae9…`) is the *same hash* as the DEX old-tricrypto-2 `TokenExchange`; LLAMMA `Withdraw` (`0xf279e6a1…`) collides with veCRV `Withdraw`; `Deposit`/`Withdraw` recur across veCRV, gauges, LLAMMA, and ERC-4626 vaults; the StableSwap `TokenExchange` (`0x8b3e96f2…`) is shared by classic and NG.
- **Soft-liquidation ≠ hard-liquidation.** LLAMMA `TokenExchange`/`Deposit`/`Withdraw` are *normal* continuous rebalancing — **not** a default. The alert event is the rare **Controller `Liquidate` (`0x642dd4d3…`)**.
- **Geography:** the full crvUSD stack (mint markets, scrvUSD, PegKeepers, FlashLender, fees) is **Ethereum-only**; **LlamaLend** is on **Ethereum + Arbitrum + Optimism** (of the 8); the crvUSD token is **bridged to all 8 with a different address (and bridge tech) on each.**

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` (pycryptodome) from the **deployed** Vyper signatures (the `curvefi/curve-stablecoin` `master` is an unreleased Vyper-0.4 rewrite that does **not** match live bytecode — crvUSD signatures were taken from deployed bytecode/logs). curve.md: 69/69 topics + 56/56 selectors re-checked, zero mismatches. crvusd.md: topic set cross-checked against live `eth_getLogs` on the wstETH mint market, a LlamaLend market, and scrvUSD; `Liquidate` confirmed by PUSH32 bytecode scan across all 9 mint Controllers.
- **Addresses:** every address existence-checked via `eth_getCode` on each chain's `publicnode` RPC (all resolve); markets enumerated live via the factories (`n_collaterals()`/`market_count()` + `controllers(i)`/`amms(i)`/`vaults(i)`); proxy classification via EIP-1967 slot reads. The AddressProvider id-maps were read live.
- **Date:** 2026-06-02. Both files carry an independent adversarial fact-check in their Verification sections.

## Coverage caveats (read these)

- **Per-pool / per-market addresses are not enumerated** — Curve is permissionless and has tens of thousands of pools and hundreds of lending markets. Discover them via factory `*Deployed` / `NewVault` / `AddMarket` events or the MetaRegistry. The files list singletons, factories, registries, the DAO stack, and a handful of flagship/representative instances only.
- **Gnosis (100) is a bonus** 8th chain beyond the seven standard targets; it is fully covered where Curve is deployed there.
- **Other Curve chains exist but are out of scope:** Fraxtal, Sonic, Fantom, Mantle, X Layer, Celo, Kava, Taiko, Etherlink, etc. (LlamaLend is on Fraxtal + Sonic; crvUSD is bridged to several). These are noted where relevant but not enumerated.
- **Parameters drift; read live.** Mint-market MonetaryPolicies and the PegKeeper set have rotated; pool `A`/fees change via timelocked DAO actions. Never hard-code a policy, keeper, or per-pool param — read it on-chain.

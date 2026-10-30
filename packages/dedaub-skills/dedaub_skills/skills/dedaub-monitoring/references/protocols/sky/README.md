# Sky (formerly MakerDAO) — Protocol Reference Index

Monitoring-grade references for Sky across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663), Arc (5042)**, plus Unichain (130) for the bridged tokens. Verified on 2026-10-30 against live RPC, the on-chain ChainLog `0xdA0Ab1e0017DEbCd72Be8599041a2aa3bA7e740F` (version `1.20.21`, 520 keys) and Sourcify-verified ABIs.

Sky is one protocol with three layers. One file per layer:

| File | Layer | Components | Status |
|------|-------|------------|--------|
| [mcd.md](mcd.md) | **MCD core (dss)** | Vat, Dai, joins, Jug, Pot, Spotter, OSM, Dog + Clippers, Vow, Kicker/Splitter/Flapper (Smart Burn Engine), Flopper, End/ESM/Cure, DssFlash, CDP manager, AutoLine + Mom contracts, allocator (Star) vaults, D3MHub, Chief/Pause/ChainLog/IlkRegistry | **Live.** Ethereum only. Immutable. Anonymous note logs on the Vat and LibNote contracts. |
| [usds.md](usds.md) | **USDS, savings, SKY, staking** | USDS, UsdsJoin, DaiUsds, sUSDS, stUSDS, SKY, MKR, MkrSky, LockstakeEngine (V2 + legacy V1), lsSKY, Lockstake Clipper/oracle/migrator, StakingRewards farms, VestedRewardsDistribution, DssVest, LitePSM + UsdsPsmWrapper, SPBEAM | **Live.** Ethereum only. USDS / sUSDS / stUSDS are UUPS proxies; the rest is immutable. |
| [l2.md](l2.md) | **SkyLink (bridged USDS / sUSDS)** | OP-stack token bridge (Base, Optimism, Unichain), Arbitrum gateway, LayerZero OFT (Avalanche, Solana), escrows, governance relays, legacy DAI bridges, cross-chain sUSDS rate oracles | **Live** on Base, Optimism, Arbitrum, Avalanche (+ Unichain). UUPS bridges and tokens. |

Each file follows the same layout: **Topics** (chain-agnostic) → **Function signatures** (chain-agnostic) → **Addresses** (network-specific) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **The ChainLog is the address source of truth.** Every live core address has a ChainLog key. `ChainLog.UpdateAddress(bytes32,address)` (`0xcf0ecd10…`) is the protocol-wide "contract rotated" signal. The docs quote the key next to each address.
- **Anonymous logs in the oldest contracts.** The Vat, Dai, DaiJoin, GemJoins, Jug, Pot, Vow and DSPause emit anonymous note logs where `topic0` = the 4-byte function selector left-aligned (`0x76088703000…` = Vat `frob`). Newer modules use named events. See [mcd.md §1.1–1.2](mcd.md).
- **Where the debt is (2026-10-30).** Vat debt ≈ 11.8 B. LitePSM USDC ≈ 4.48 B, Spark allocator ≈ 3.88 B, Bloom/Grove allocators ≈ 1.69 B, Obex ≈ 0.41 B, ETH vaults ≈ 0.36 B, SKY staking (`LSEV2-SKY-A`) ≈ 0.16 B. Allocator and PSM ilks have no Clipper and cannot be liquidated.
- **DAI and USDS are two ERC-20s on one Vat balance.** `DaiUsds` converts 1:1. Both mint from Vat DAI through their joins. Net the two legs of a conversion.
- **Governance token moved from MKR to SKY.** `MCD_GOV` = SKY `0x56072C95…`. Chief V3 votes in SKY. `MkrSky` converts at 24,000 SKY per MKR with a 5 % fee.
- **Liquidations:** count from `Dog.Bark`. All Clippers (per-ilk and Lockstake) share one topic set. The surplus path is `Kicker.flap()` → `Splitter.Kick` → `Flapper.Exec` (buys SKY on Uniswap V2) + USDS to the lsSKY farm.
- **L2 sUSDS is a plain ERC-20.** Only Ethereum sUSDS is an ERC-4626 vault. L2 prices come from `SSRAuthOracle`.
- **Chain coverage.** Core + tokens: Ethereum. Bridged USDS/sUSDS: Base, Optimism, Arbitrum, Avalanche, Unichain (and Solana). **Absent on BNB, Polygon PoS, Robinhood Chain and Arc** — no code at any Sky literal and no LayerZero peer. `0xDA10009c…` (Maker L2 DAI on Optimism/Arbitrum) is an unrelated 1,456-byte contract on Base, BNB, Avalanche and Polygon.

## Scope boundaries

- **SparkLend** is in the `spark` docs. **Spark Savings, the Spark Liquidity Layer (ALM), PSM3 internals and Grove** are documented separately. These docs list only the Sky-side hooks (allocator vaults, SubProxies, StarGuards, PSM3 addresses as USDS venues).
- **Per-ilk GemJoin / Clipper / OSM** addresses for the 35 registered ilks are enumerable from `IlkRegistry.list()` + `join/xlip/pip(ilk)`. [mcd.md §3.3](mcd.md) lists the live ones.
- **Per-position Lockstake urns, CDP-manager urns and vote-delegate contracts** are discovered from `LockstakeEngine.Open`, `CdpManager.NewCdp` and `VoteDelegateFactory.CreateVoteDelegate`.

## Verification methodology

- **Topic0 / selectors:** computed locally with keccak-256 from Sourcify-verified ABIs of the deployed addresses (implementation ABIs for proxies). Validated against live `eth_getLogs` on Ethereum (Vat notes, Jug/Pot/DaiJoin notes, Dog `Bark` 216 and Clipper `Take` 217 since block 21 M, DaiUsds, UsdsJoin, sUSDS, stUSDS, LitePSM, Lockstake, Splitter/Flapper, OFT adapter, SkyLink bridges) and Base PSM3.
- **Addresses:** ChainLog (on-chain + JSON mirror), `IlkRegistry`, `sparkdotfi/spark-address-registry`, `sky-ecosystem/sky-protocol-info`, the Sky developer docs; each existence-checked with `eth_getCode` and wiring reads (`token()`, `l1ToL2Token()`, `peers(eid)`, `l2Oracle()`, `pair()`, `farm()`).
- **Not verified:** `MCD_SBEBEAM` (`0xc8b61d21…`) has no published ABI; its topics are not listed.

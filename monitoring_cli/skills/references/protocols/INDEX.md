# Protocol Reference Index — category & chain lookup

**Purpose.** One-screen map of every protocol doc under `references/protocols/<slug>/`. Use it to answer
"which protocols are bridges / DEXs / lending / liquid-staking…" and "which are on chain X" **before**
opening any `<slug>/` file. Resolve the category/chain → pick slugs here → then open
`<slug>/README.md` (multi-file dirs) or `<slug>/<file>.md` for the actual topics/selectors/addresses.

**Chain legend.** `ETH` Ethereum(1) · `Base`(8453) · `BNB`(56) · `Avax`(43114) · `Arb`(42161) ·
`OP`(10) · `Poly` Polygon PoS(137). **`7` = all seven targets.** `+Other` = a non-target chain the doc
emphasizes (Gnosis 100, Tron, Celo, Swellchain, Fraxtal, zkSync, Linea, NEAR, Ronin, Blast…).
A chain listed = a real native **or** bridged deployment per that doc; always confirm the exact address
in the doc (some entries are bridged representations / decoys — the docs flag these).

**Categories.** `Bridge` `Messaging` `DEX` `Aggregator` `Lending` `CDP` `LST`(liquid staking)
`Restaking`(LRT) `Perps` `ALM` `Oracle` `Token`. A protocol may carry several — primary first.

---

## 1. Category → protocols (reverse lookup)

- **Bridge (27):** `across` `agglayer` `allbridge` `arbitrum_native` `avalanche_c_bitcoin`
  `avalanche_c_native` `axelar` `beamer` `blast_native` `butter` `cctp` `celer` `connext` `hop`
  `hyperliquid` `layerzero` `lighter` `nitro` `orbiter` `polygon_native` `rainbow` `ronin_native`
  `symbiosis` `synapse` `tether` `zkbridge` `zksync_native` — *(+`radiant` is omnichain lending)*
- **Messaging (generic interop):** `layerzero` `axelar` `celer` `connext` `zkbridge`
- **DEX / AMM:** `aerodrome` `balancer` `bancor` `blackhole` `camelot` `curve` `dodo` `ekubo` `fluid`
  `fraxswap` `izumi` `metric` `native` `pancakeswap` `pharaoh` `quickswap` `sushiswap` `tessera`
  `topaz` `traderjoe` `uniswap` `velodrome`
- **Aggregator (routing):** `dodo` (smartroute) · `native` (RFQ)
- **Lending / money-market:** `40acres` `aave` `agave` `benqi` `compound` `euler` `fluid` `fluxfinance`
  `granary` `justlend` `layerbank` `lodestar` `maple` `moola` `moonwell` `morpho` `native` `pike`
  `radiant` `realt_rmm` `seamlessprotocol` `sonne_finance` `spark` `strike` `uwulend` `venus` `zerolend`
- **CDP / stablecoin engine:** `curve` (crvUSD) · `spark` (D3M DAI)
- **Liquid staking (LST):** `lido` `rocketpool` `frax_finance` `stakewise` `swell` `coinbase` `binance`
  `benqi` (sAVAX)
- **Restaking (LRT):** `eigenlayer` `swell` `seamlessprotocol` (Morpho-powered leverage tokens)
- **Perps / derivatives:** `gmx` `synthetix` `hyperliquid` `lighter`
- **ALM (liquidity mgmt):** `arrakis`
- **Oracle / data infra:** `chainlink`
- **Token / stablecoin issuer:** `tether` (USDT0) · `maple` (SYRUP)

*Not staking docs (no EVM contract): the beacon-chain entity tags `bitcoin_suisse`, `chorusone`,
`darma_capital` are validator/operator labels only — stake via the shared ETH2 deposit contract or
third-party protocols (Liquid Collective / StakeWise). No `<slug>/` dir exists for them.*

---

## 2. Per-protocol table

| Slug | Categories | Chains | Files | One-liner |
|------|-----------|--------|-------|-----------|
| `40acres` | Lending·CDP | Base·OP·Avax·ETH | core.md | veNFT self-repaying loans; ETH = portfolio layer only |
| `aave` | Lending | 7 (V3) | v1–v4.md | Canonical money-market; V1 ETH-legacy → V3 all 7; V4 hub-spoke |
| `across` | Bridge | ETH·Base·BNB·Arb·OP·Poly | core.md | Intent/relayer optimistic bridge; NOT Avalanche |
| `aerodrome` | DEX | Base·OP | amm.md, slipstream.md | Velodrome fork; ve(3,3) + concentrated-liquidity Slipstream |
| `agave` | Lending | +Other (Gnosis) | core.md | Aave-V2 fork, Gnosis-only; absent all 7 |
| `agglayer` | Bridge | ETH +Other | core.md | Polygon AggLayer unified LxLy bridge (L1 anchor) |
| `allbridge` | Bridge | 7 +Other | classic.md, core.md | Allbridge Core + Classic cross-chain |
| `arbitrum_native` | Bridge | ETH·Arb | core.md | Arbitrum canonical Nitro bridge (L1↔Arb/Nova) |
| `arrakis` | ALM | ETH·Poly·Arb·OP·Base·BNB | v1/v2/modular.md | Uniswap-V3 liquidity-management vaults; not Avalanche |
| `avalanche_c_bitcoin` | Bridge | Avax +Other (BTC) | core.md | Avalanche Bridge BTC.b wrapped Bitcoin |
| `avalanche_c_native` | Bridge | ETH·Avax | core.md | Avalanche Bridge (AB) ETH↔C-Chain |
| `axelar` | Bridge·Messaging | 7 | core.md | GMP + token bridge cross-chain |
| `balancer` | DEX | ETH·Base·Arb·OP·Avax +Gnosis | v2.md, v3.md | Weighted/boosted-pool AMM + vault |
| `bancor` | DEX | ETH | v3.md | Omnipool single-sided AMM, ETH-only |
| `beamer` | Bridge | ETH·OP·Base·Arb +Other | core.md | Optimistic rollup-to-rollup bridge |
| `benqi` | Lending·LST | Avax | core.md | Compound-V2 fork + sAVAX liquid staking; Avalanche-only |
| `binance` | LST | ETH·BNB | wbeth.md | WBETH (yield-in-price) + BETH (1:1 receipt) |
| `blackhole` | DEX | Avax | classic.md, cl.md | ve(3,3) + concentrated-liquidity AMM, Avalanche |
| `blast_native` | Bridge | ETH +Other (Blast) | core.md | Blast OP-Stack bridge + YieldManager |
| `butter` | Bridge | 7 +Other | mos-v2/v3.md, router.md | MAP Omnichain Service (MOS) cross-chain |
| `camelot` | DEX | Arb | v2.md, v3.md | Algebra-V1 + V2 AMM, Arbitrum |
| `cctp` | Bridge | 7 | v1.md, v2.md | Circle USDC burn-and-mint cross-chain transfer |
| `celer` | Bridge·Messaging | 7 | core.md, pegged.md | cBridge liquidity + pegged token + IM messaging |
| `chainlink` | Oracle | 7 +many | ccip/data-feeds/vrf/automation/functions/data-streams/link-token | Price feeds, CCIP, VRF, Automation, Functions |
| `coinbase` | LST | ETH·Base·Arb·OP·Poly | cbeth.md | cbETH; FiatToken fork, oracle-pushed rate; 5 bridge wrappers |
| `compound` | Lending | ETH·Base·Arb·OP·Poly | v2.md, v3.md | V2 pools + V3 Comet single-borrow-asset |
| `connext` | Bridge·Messaging | ETH·Base·BNB·Arb·OP·Poly | amarok.md, core.md | Connext/Everclear intent clearing |
| `curve` | DEX·CDP | 7 | curve.md, crvusd.md | StableSwap/crypto AMM + crvUSD LLAMMA CDP |
| `dodo` | DEX·Aggregator | 7 | v1/v2/v3.md, smartroute.md | PMM AMM + SmartRoute aggregator |
| `eigenlayer` | Restaking | ETH | core.md | Restaking core (Delegation/Strategy/EigenPod) + EIGEN; ETH-only |
| `ekubo` | DEX | ETH·Base·Arb | v2.md, v3.md | UniV4-like singleton AMM; anonymous log0 swaps |
| `euler` | Lending | ETH·Base·Arb·BNB·Avax·Poly | v1.md, v2.md | V1 module-dispatch (dead post-hack) → V2 EVC+EVK vaults |
| `fluid` | Lending·DEX | ETH·Base·Arb·Poly·BNB | lending/vaults/dex/liquidity-layer.md | Instadapp liquidity-layer; vaults T1–T4 + smart-debt DEX |
| `fluxfinance` | Lending | ETH | core.md | Ondo Compound-V2 fork w/ KYC allowlist; ETH-only |
| `frax_finance` | LST | 7 | frxeth.md | frxETH (flat peg) + sfrxETH (ERC4626); bridged to 6 L2s |
| `fraxswap` | DEX | ETH·BNB·Avax·Arb·OP·Poly | v1.md, v2.md | TWAMM time-weighted AMM; NOT Base |
| `gmx` | Perps | Arb·Avax | v1.md, v2.md | GLP/GM perp DEX; Arbitrum + Avalanche only |
| `granary` | Lending | ETH·Base·BNB·Avax·Arb·OP | core.md | Aave-V2 soft-fork (Byte Masons); not Polygon; winding down |
| `hop` | Bridge | ETH·OP·Arb·Poly·Base | core.md | hToken AMM bridge; not BNB/Avalanche |
| `hyperliquid` | Bridge·Perps | Arb | core.md | Hyperliquid L1 deposit bridge (Bridge2), Arbitrum |
| `izumi` | DEX | ETH·Base·BNB·Arb·OP·Poly | iziswap.md, liquidbox.md | Discretized-liquidity DL-AMM (not a Uni fork); not Avax |
| `justlend` | Lending | +Other (Tron) | core.md | Compound-V2 fork, Tron-only; absent all 7 EVM |
| `layerbank` | Lending | +Other (Linea/Scroll/Mode) | core.md | Own Core+LToken arch; none of the 7 targets |
| `layerzero` | Messaging·Bridge | 7 +many | v1.md, v2.md | OFT / generic cross-chain messaging endpoint |
| `lido` | LST | ETH +L2 bridged | v1–v3.md, l2.md | stETH/wstETH; the canonical ETH LST |
| `lighter` | Perps·Bridge | ETH | core.md | zkLighter orderbook perp DEX; ETH L1 settlement |
| `lodestar` | Lending | Arb | core.md | Compound-V2 fork, Arbitrum-only; frozen post plvGLP exploit |
| `maple` | Lending·Token | ETH·Base (+SYRUP 7) | v1/v2/syrup-cross-chain.md | RWA/institutional credit pools; SYRUP OFT + CCIP token |
| `metric` | DEX | ETH | core.md, founder-fleet.md | ETH-only front-end DEX (0x/KeeperDAO), not a DODO fork |
| `moola` | Lending | +Other (Celo) | core.md | Aave fork, Celo-only; absent all 7 |
| `moonwell` | Lending | Base·OP +Other | core.md | Compound-V2 fork; lending only on Base+Optimism |
| `morpho` | Lending | ETH·Base·Arb·OP·Poly | v1/v2/optimizers.md | Blue immutable markets + MetaMorpho/Vaults-V2 |
| `native` | DEX·Lending·Aggregator | ETH·Base·BNB·Arb | dex.md, lending.md | RFQ swap engine (NativeRouter) + lending |
| `nitro` | Bridge | 7 +Other | core.md, gateway.md | Router Protocol Voyager gateway + AssetBridge |
| `orbiter` | Bridge | 7 +Other | core.md, mdc.md | Maker-Deposit-Contract rollup bridge w/ arbitration |
| `pancakeswap` | DEX | BNB·Base·ETH·Arb | v2/v3/infinity/stableswap.md | UniV2/V3 fork + Infinity(V4) hooks + StableSwap |
| `pharaoh` | DEX | Avax | cl.md, legacy.md | Ramses/ve(3,3) CL + DLMM AMM, Avalanche |
| `pike` | Lending | Base +Other (Sonic) | core.md | Compound-V2 semantics + ERC-4626 surface; Base relaunch |
| `polygon_native` | Bridge | ETH·Poly | core.md | Polygon PoS portal (PoS + FxPortal) |
| `quickswap` | DEX | Poly·Base | v2/v3/v4.md | UniV2 fork + Algebra V1/Integral; Polygon + Base |
| `radiant` | Lending·Bridge | Arb·BNB·ETH·Base | v1.md, v2.md | Aave-V2 omnichain (LayerZero); ~$50M Oct-2024 key compromise |
| `rainbow` | Bridge | ETH +Other (NEAR) | core.md | NEAR Rainbow Bridge (legacy), ETH L1 |
| `realt_rmm` | Lending | +Other (Gnosis) | core.md | RealToken Aave fork, Gnosis-only; RWA reserves |
| `rocketpool` | LST | ETH +L2 bridged | core.md, l2.md | rETH decentralized-validator staking; L2 = bridged rETH |
| `ronin_native` | Bridge | ETH +Other (Ronin) | core.md | Ronin gaming-chain bridge, ETH L1 |
| `seamlessprotocol` | Lending·Restaking | Base·ETH | v1.md, leveragetokens.md | Aave-V3 lending (Base) + Morpho-powered leverage tokens |
| `sonne_finance` | Lending | OP·Base | core.md | Compound-V2 fork; wound down post ~$20M Base exploit |
| `spark` | Lending·CDP | ETH +Gnosis | sparklend.md | Aave-V3 fork; D3M-supplied fixed-$1 DAI |
| `stakewise` | LST | ETH +Gnosis | v2.md, v3.md | V2 pooled sETH2/rETH2 → V3 osETH vaults; ETH-only of 7 |
| `strike` | Lending | ETH | core.md | Compound-V2 fork (STRK), ETH-only |
| `sushiswap` | DEX | 7 | v2/v3/trident.md | UniV2/V3 fork + Trident; all 7 |
| `swell` | LST·Restaking | ETH +Other (Swellchain) | core.md | swETH (LST) + rswETH (LRT) + Earn vaults; ETH + Swellchain |
| `symbiosis` | Bridge | 7 | core.md | Cross-chain AMM/stableswap liquidity bridge |
| `synapse` | Bridge | 7 | synapse.md, rfq.md | nUSD/nETH liquidity bridge + RFQ |
| `synthetix` | Perps | ETH·OP·Base·Arb | v2.md, v3.md | Synth/perps derivatives; V2 → V3 collateral system |
| `tessera` | DEX | Base·BNB | core.md | Wintermute dark AMM (EVM = Base + BSC only) |
| `tether` | Bridge·Token | ETH·Arb·OP·Poly +Other | core.md | USDT0 LayerZero-OFT omnichain USDT (~23 chains) |
| `topaz` | DEX | BNB | amm.md, slipstream.md | ve(3,3) Velodrome+Aerodrome fork, BNB-only |
| `traderjoe` | DEX | Avax·Arb·BNB | v1/v2.0/v2.1/v2.2.md | Liquidity Book bins; Avax+Arb full, BSC no-2.2 |
| `uniswap` | DEX | 7 | v2/v3/v4.md | The canonical AMM; V2 pairs → V3 CL → V4 hooks |
| `uwulend` | Lending | ETH | core.md | Aave-V2 fork, ETH-only; ~$24M June-2024 oracle exploit |
| `velodrome` | DEX | OP +Other (Superchain) | v2.md, slipstream.md, superchain.md | ve(3,3) + Slipstream; Optimism-Superchain |
| `venus` | Lending | BNB·ETH·Arb·OP·Base | core-pool.md, isolated-pools.md | Compound-fork; BNB core (Diamond) + isolated pools |
| `zerolend` | Lending | ETH·Base | core.md | Aave-V3 fork; of 7 only ETH+Base (primary on L2s off-target) |
| `zkbridge` | Bridge·Messaging | 7 +Other | lightclient.md, messaging.md | Polyhedra zk light-client message/token bridge |
| `zksync_native` | Bridge | ETH +Other (zkSync) | core.md | zkSync Era Elastic-Chain canonical bridge |

---

## 3. Notes

- **Multi-file dirs** carry a `README.md` index — read it first (version→file map + topic0 collisions).
  Single-file dirs (`core.md` / `<slug>.md` / a version file) open directly.
- **"7" never means "literally everywhere"** — open the doc's *Cross-chain summary* for the exact
  per-chain address and absence/decoy notes (several docs flag look-alike tokens on non-deployed chains).
- **Off-target-only protocols** (`agave`, `justlend`, `layerbank`, `moola`, `realt_rmm`) have docs but
  are **absent on all 7 target chains** — useful for attribution, not for 7-chain monitoring queries.
- **Wound-down / exploited** (watch for low activity): `granary`, `lodestar`, `sonne_finance`,
  `uwulend`, `radiant` (key compromise), `euler` V1, `metric`.

# Protocol Reference Index — category & chain lookup

**Purpose.** One-screen map of every protocol doc under `references/protocols/<slug>/`. Use it to answer
"which protocols are bridges / DEXs / lending / liquid-staking…" and "which are on chain X" **before**
opening any `<slug>/` file. Resolve the category/chain → pick slugs here → then open
`<slug>/README.md` (multi-file dirs) or `<slug>/<file>.md` for the actual topics/selectors/addresses.

**Chain legend.** `ETH` Ethereum(1) · `Base`(8453) · `BNB`(56) · `Avax`(43114) · `Arb`(42161) ·
`OP`(10) · `Poly` Polygon PoS(137) · `Robin` Robinhood Chain(4663). **`7` = the seven targets other
than Robinhood Chain**; a row names `Robin` explicitly when the doc covers it. `+Other` = a non-target
chain the doc emphasizes (Gnosis 100, Tron, Celo, Swellchain, Fraxtal, zkSync, Linea, NEAR, Ronin, Blast…).
A chain listed = a real native **or** bridged deployment per that doc; always confirm the exact address
in the doc (some entries are bridged representations / decoys — the docs flag these).

**Categories.** `Bridge` `Messaging` `DEX` `Aggregator` `Lending` `CDP` `LST`(liquid staking)
`Restaking`(LRT) `Perps` `ALM` `Oracle` `Token`. A protocol may carry several — primary first.

---

## 1. Category → protocols (reverse lookup)

- **Bridge (73):** `1sec` `across` `agglayer` `allbridge` `aori` `arbitrum_native` `avalanche_c_bitcoin`
  `avalanche_c_native` `axelar` `beamer` `blast_native` `butter` `cctp` `celer` `chainflip`
  `circle_gateway` `connext` `debridge` `eclipse_native` `eco` `evodefi` `fuel_native` `garden` `gaszip`
  `gnosis_native` `hop` `hyperlane` `hyperliquid` `layerswap` `layerzero` `lifi` `lighter`
  `linea_native` `maya` `mayan` `meson` `minibridge` `multichain` `near_omni` `nitro` `op_stack`
  `orbiter` `owlto` `pheasant` `polygon_native` `rainbow` `rango` `relay` `retrobridge` `rhinofi`
  `ronin_native` `rootstock_native` `rubic` `scroll_native` `snowbridge` `socket` `squid` `stargate`
  `starknet_native` `sui_native` `symbiosis` `synapse` `taiko_native` `teleswap` `tether` `thorchain`
  `train` `universalx` `wormhole` `xyfinance` `zkbridge` `zkswap` `zksync_native`
  — *(+`radiant` is omnichain lending)*
- **Messaging (generic interop):** `layerzero` `axelar` `celer` `connext` `zkbridge` `chainlink`
  `debridge` `gnosis_native` `hyperlane` `snowbridge` `wormhole`
- **DEX / AMM:** `aerodrome` `angstrom` `apeswap` `balancer` `bancor` `beets` `biswap` `blackhole`
  `camelot` `curve` `dodo` `dooar` `ekubo` `fluid` `fraxswap` `izumi` `metric` `native` `pancakeswap`
  `pharaoh` `quickswap` `ramses` `shibaswap` `sushiswap` `swaap` `tessera` `thena` `topaz`
  `traderjoe` `uniswap` `velodrome`
- **Aggregator (routing):** `dodo` (smartroute) · `lifi` · `mayan` · `native` (RFQ) · `rango` · `rubic` · `socket` · `squid` · `xyfinance`
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
- **Token / stablecoin issuer:** `tether` (USDT0) · `maple` (SYRUP) · `biswap` (BSW OFT on ETH/Base/Arb)

*Not staking docs (no EVM contract): the beacon-chain entity tags `bitcoin_suisse`, `chorusone`,
`darma_capital` are validator/operator labels only — stake via the shared ETH2 deposit contract or
third-party protocols (Liquid Collective / StakeWise). No `<slug>/` dir exists for them.*

---

## 2. Per-protocol table

| Slug | Categories | Chains | Files | One-liner |
|------|-----------|--------|-------|-----------|
| `1sec` | Bridge | ETH·Base·Arb +Other (ICP) | core.md | 1sec ICP bridge: Lock1-4 lockers, Burn1-4 tokens; payouts are plain transfers/mints from the 1sec wallet EOA; no on-chain link key |
| `40acres` | Lending·CDP | Base·OP·Avax·ETH | core.md | veNFT self-repaying loans; ETH = portfolio layer only |
| `aave` | Lending | 7 (V3) | v1–v4.md | Canonical money-market; V1 ETH-legacy → V3 all 7; V4 hub-spoke |
| `across` | Bridge | 7 · Robin | core.md | Intent/relayer optimistic bridge; Universal SpokePools on Avalanche and Robinhood |
| `aerodrome` | DEX | Base·OP | amm.md, slipstream.md | Velodrome fork; ve(3,3) + concentrated-liquidity Slipstream |
| `agave` | Lending | +Other (Gnosis) | core.md | Aave-V2 fork, Gnosis-only; absent all 7 |
| `agglayer` | Bridge | ETH +Other | core.md | Polygon AggLayer unified LxLy bridge (L1 anchor) |
| `allbridge` | Bridge | 7 +Other | classic.md, core.md | Allbridge Core + Classic cross-chain |
| `angstrom` | DEX | ETH | core.md | UniV4 hook batch-auction MEV-protect order flow; ETH-only, log0 swaps |
| `aori` | Bridge | 7 | core.md | Aori intent settlement over LayerZero: Deposit/Fill/Settle/Cancel/Withdraw, orderId link key; v0.3.1 live on ETH, Base, Arb, OP, BNB; v0.4.0 proxy staged on 7 chains (new topic0s) |
| `apeswap` | DEX | BNB·ETH·Arb·Poly | core.md | UniV2 fork + MasterApe farms + BANANA; BNB primary, no Base/Avax/OP |
| `arbitrum_native` | Bridge | ETH·Base·Arb·Robin +Other (Nova, Orbit chains) | README.md, core.md, orbit.md | Arbitrum Nitro canonical bridge: One/Nova plus Robinhood Chain and the Orbit L2/L3 chains on Ethereum, Base and Arbitrum One |
| `arrakis` | ALM | ETH·Poly·Arb·OP·Base·BNB | v1/v2/modular.md | Uniswap-V3 liquidity-management vaults; not Avalanche |
| `avalanche_c_bitcoin` | Bridge | Avax +Other (BTC) | core.md | Avalanche Bridge BTC.b wrapped Bitcoin |
| `avalanche_c_native` | Bridge | ETH·Avax | core.md | Avalanche Bridge (AB) ETH↔C-Chain |
| `axelar` | Bridge·Messaging | 7 | core.md | GMP + token bridge cross-chain |
| `balancer` | DEX | ETH·Base·BNB·Avax·Arb·OP·Poly +Gnosis | v2.md, v3.md | Weighted/boosted-pool AMM + vault |
| `bancor` | DEX | ETH | v3.md | Omnipool single-sided AMM, ETH-only |
| `beamer` | Bridge | ETH·OP·Base·Arb +Other | core.md | Optimistic rollup-to-rollup bridge |
| `beets` | DEX | OP | core.md | Beethoven X; Balancer-V2 fork, shared Vault; OP-only of 7 |
| `benqi` | Lending·LST | Avax | core.md | Compound-V2 fork + sAVAX liquid staking; Avalanche-only |
| `binance` | LST | ETH·BNB | wbeth.md | WBETH (yield-in-price) + BETH (1:1 receipt) |
| `biswap` | DEX·Token | BNB (+BSW ETH·Base·Arb) | core.md | UniV2 fork + iZi-style V3; BNB-only DEX, BSW OFT bridged to 3 |
| `blackhole` | DEX | Avax | classic.md, cl.md | ve(3,3) + concentrated-liquidity AMM, Avalanche |
| `blast_native` | Bridge | ETH +Other (Blast) | core.md | Blast OP-Stack bridge + YieldManager |
| `butter` | Bridge | 7 · Robin +Other | README.md, router.md, mos-v3.md, mos-v2.md | MAP Omnichain Service (MOS) cross-chain; MOS V3 and ButterRouter on all eight chains |
| `camelot` | DEX | Arb | v2.md, v3.md | Algebra-V1 + V2 AMM, Arbitrum |
| `cctp` | Bridge | 7 · Robin | README.md, v1.md, v2.md | Circle USDC burn-and-mint cross-chain transfer; V2 on Robinhood (domain 35, read on chain, pre-launch) |
| `celer` | Bridge·Messaging | 7 | core.md, pegged.md | cBridge liquidity + pegged token + IM messaging |
| `chainflip` | Bridge·DEX | ETH·Arb·BNB +Other | core.md | Chainflip Vault/KeyManager; vault swaps + deposit channels; no on-chain link key |
| `chainlink` | Oracle·Messaging | 7 · Robin +many | ccip/data-feeds/vrf/automation/functions/data-streams/link-token | Price feeds, CCIP (ramps + token pools on all 8), VRF, Automation, Functions |
| `circle_gateway` | Bridge | ETH·Base·Arb·OP·Poly·Avax | core.md | Circle unified USDC balance: GatewayWallet deposits/burns, GatewayMinter attested mints; NOT BNB, NOT Robinhood |
| `coinbase` | LST | ETH·Base·Arb·OP·Poly | cbeth.md | cbETH; FiatToken fork, oracle-pushed rate; 5 bridge wrappers |
| `compound` | Lending | ETH·Base·Arb·OP·Poly | v2.md, v3.md | V2 pools + V3 Comet single-borrow-asset |
| `connext` | Bridge·Messaging | 7 | README.md, nxtp.md, amarok.md, core.md | Connext NXTP v1/v0, Amarok and Everclear (sunset announced 2026-05-21); not Robinhood |
| `curve` | DEX·CDP | 7 | curve.md, crvusd.md | StableSwap/crypto AMM + crvUSD LLAMMA CDP |
| `debridge` | Bridge·Messaging | 7 · Robin +Other | README.md, dln.md, dmp.md | deBridge DLN intent orders (solver fill, escrow unlock/cancel; orderId key) + deBridgeGate validator-signed messaging; same DLN addresses on all 8 |
| `dodo` | DEX·Aggregator | 7 | v1/v2/v3.md, smartroute.md | PMM AMM + SmartRoute aggregator |
| `dooar` | DEX | ETH·BNB | core.md | DooarSwap (STEPN); tiny UniV2 fork, ETH+BSC only |
| `eclipse_native` | Bridge | ETH +Other (Eclipse) | core.md | Eclipse SVM rollup canonical ETH bridge (CanonicalBridgeV3 + Treasury) |
| `eco` | Bridge | ETH·Base·Arb·OP·Poly·BNB·Robin +Other | core.md | Eco Routes intent bridge: immutable Portal + per-intent Vaults + Executor, modular provers; intentHash links both sides; Robinhood Portal unlisted; NOT Avalanche |
| `eigenlayer` | Restaking | ETH | core.md | Restaking core (Delegation/Strategy/EigenPod) + EIGEN; ETH-only |
| `ekubo` | DEX | ETH·Base·Arb | v2.md, v3.md | UniV4-like singleton AMM; anonymous log0 swaps |
| `euler` | Lending | ETH·Base·Arb·BNB·Avax·Poly | v1.md, v2.md | V1 module-dispatch (dead post-hack) → V2 EVC+EVK vaults |
| `evodefi` | Bridge | ETH·Arb·OP·Poly·BNB·Avax | core.md | EVO DeFi custodial pool bridge (insolvent 2022; last deposits 2023–2024); same addresses on 6 chains |
| `fluid` | Lending·DEX | ETH·Base·Arb·Poly·BNB | lending/vaults/dex/liquidity-layer.md | Instadapp liquidity-layer; vaults T1–T4 + smart-debt DEX |
| `fluxfinance` | Lending | ETH | core.md | Ondo Compound-V2 fork w/ KYC allowlist; ETH-only |
| `frax_finance` | LST | 7 | frxeth.md | frxETH (flat peg) + sfrxETH (ERC4626); bridged to 6 L2s |
| `fraxswap` | DEX | ETH·BNB·Avax·Arb·OP·Poly | v1.md, v2.md | TWAMM time-weighted AMM; NOT Base |
| `fuel_native` | Bridge | ETH +Other (Fuel) | core.md | Fuel Ignition canonical bridge: message portal (ETH) + ERC-20 gateway |
| `garden` | Bridge | ETH·Base·Arb·BNB·Robin +Other (BTC) | core.md | Garden per-asset HTLC atomic swaps (BTC↔EVM); link = secretHash |
| `gaszip` | Bridge | 7 · Robin +Other | core.md | Gas.zip native gas refuel: Direct Deposit EOA (no log), GasZipV2 Deposit, GasLZV2 LayerZero drop; payout-signer EOAs; Robinhood payouts only |
| `gmx` | Perps | Arb·Avax | v1.md, v2.md | GLP/GM perp DEX; Arbitrum + Avalanche only |
| `gnosis_native` | Bridge·Messaging | ETH·BNB +Other (Gnosis) | core.md | Gnosis xDai bridge (USDS↔xDAI), AMB and Omnibridge; BSC pair deprecated |
| `granary` | Lending | ETH·Base·BNB·Avax·Arb·OP | core.md | Aave-V2 soft-fork (Byte Masons); not Polygon; winding down |
| `hop` | Bridge | ETH·OP·Arb·Poly·Base | core.md | hToken AMM bridge; not BNB/Avalanche |
| `hyperlane` | Messaging·Bridge | 7 · Robin +Other | README.md, core.md, warp_routes.md | Permissionless Mailbox messaging + warp-route token bridges (domain = chain id); independent Mailboxes listed |
| `hyperliquid` | Bridge·Perps | Arb | core.md | Hyperliquid L1 deposit bridge (Bridge2), Arbitrum |
| `izumi` | DEX | ETH·Base·BNB·Arb·OP·Poly | iziswap.md, liquidbox.md | Discretized-liquidity DL-AMM (not a Uni fork); not Avax |
| `justlend` | Lending | +Other (Tron) | core.md | Compound-V2 fork, Tron-only; absent all 7 EVM |
| `layerbank` | Lending | +Other (Linea/Scroll/Mode) | core.md | Own Core+LToken arch; none of the 7 targets |
| `layerswap` | Bridge | 7 · Robin +Other | core.md | Layerswap solver bridge: immutable Depository + two wallet EOAs, same on all 8; sequence_number key on the source only |
| `layerzero` | Messaging·Bridge | 7 · Robin +many | README.md, v1.md, v2.md | OFT / generic cross-chain messaging endpoint; major OFT tables; Robinhood EndpointV2 at its own address (eid 30416) |
| `lido` | LST | ETH·Base·BNB·Arb·OP | v1–v3.md, l2.md | stETH/wstETH; the canonical ETH LST |
| `lifi` | Bridge·Aggregator | 7 · Robin | README.md, diamond.md, facets.md, periphery.md | LI.FI diamond: LiFiTransferStarted source leg, transactionId link key, Executor/receivers destination; own diamond on Robinhood |
| `lighter` | Perps·Bridge | ETH·Robin | core.md | zkLighter orderbook perp DEX; ETH L1 settlement + separate USDG instance on Robinhood |
| `linea_native` | Bridge | ETH +Other (Linea) | core.md | Linea canonical bridge: LineaRollup message service and ETH escrow, TokenBridge (V1 and V2 events), YieldManager, retired USDC bridge |
| `lodestar` | Lending | Arb | core.md | Compound-V2 fork, Arbitrum-only; frozen post plvGLP exploit |
| `maple` | Lending·Token | ETH·Base (+SYRUP 7) | v1/v2/syrup-cross-chain.md | RWA/institutional credit pools; SYRUP OFT + CCIP token |
| `maya` | Bridge·DEX | ETH·Arb +Other | core.md | Maya Protocol router (THORChain fork, same topics); halted since 2026-08-18 |
| `mayan` | Bridge·Aggregator | 7 | README.md, swift.md, mctp.md, wh-swap.md, forwarder.md | Mayan Swift intents (order hash key), CCTP routes (MCTP not on BNB), Wormhole swap via Solana; not on Robinhood |
| `meson` | Bridge | 7 · Robin +Other | core.md | Meson atomic-swap bridge: one UUPS proxy on all eight chains; encodedSwap link key |
| `metric` | DEX | ETH | core.md, founder-fleet.md | ETH-only front-end DEX (0x/KeeperDAO), not a DODO fork |
| `minibridge` | Bridge | 7 +Other | core.md | Chaineye MiniBridge: maker EOA, confirm code 8000+id in the value; config empty since 2026-08-24 |
| `moola` | Lending | +Other (Celo) | core.md | Aave fork, Celo-only; absent all 7 |
| `moonwell` | Lending | Base·OP +Other | core.md | Compound-V2 fork; lending only on Base+Optimism |
| `morpho` | Lending | 7 | v1/v2/optimizers.md | Blue immutable markets + MetaMorpho/Vaults-V2 |
| `multichain` | Bridge | ETH·Arb·OP·Poly·BNB·Avax | core.md | Multichain/Anyswap MPC routers V3–V7 (stopped July 2023; unpaid deposits still arrive); not Base or Robinhood |
| `native` | DEX·Lending·Aggregator | ETH·Base·BNB·Arb | dex.md, lending.md | RFQ swap engine (NativeRouter) + lending |
| `near_omni` | Bridge | ETH·Base·Arb·Poly·BNB +Other (NEAR, Solana) | core.md | NEAR Omni Bridge (MPC-signed), Rainbow successor |
| `nitro` | Bridge | 7 +Other | core.md, gateway.md | Router Protocol Voyager gateway + AssetBridge |
| `op_stack` | Bridge | ETH·Base·OP·BNB +Other (49 OP Stack L2s, Metis, 4 L3s on Base) | README.md, l1.md, l2.md | OP Stack canonical bridges: per-chain OptimismPortal/L1StandardBridge/L1CrossDomainMessenger (registry, removed, outside, Mantle), predeploys on OP and Base, opBNB, L3s on Base |
| `orbiter` | Bridge | 7 +Other | core.md, mdc.md | Maker-Deposit-Contract rollup bridge w/ arbitration |
| `owlto` | Bridge | ETH·Base·Arb·OP·Poly·BNB·Robin +Other | core.md | Owlto maker bridge: Depositor contracts + maker EOA; destination code in the event or the amount suffix; Robinhood route only |
| `pancakeswap` | DEX | BNB·Base·ETH·Arb | v2/v3/infinity/stableswap.md | UniV2/V3 fork + Infinity(V4) hooks + StableSwap |
| `pharaoh` | DEX | Avax | cl.md, legacy.md | Ramses/ve(3,3) CL + DLMM AMM, Avalanche |
| `pheasant` | Bridge | 7 +Other | core.md | Pheasant ERC-7683 intent bridge (ETH, Base, Arb, OP; swap wrapper only on Poly/BNB/Avax); orderId link key; CCTP wrapper |
| `pike` | Lending | Base +Other (Sonic) | core.md | Compound-V2 semantics + ERC-4626 surface; Base relaunch |
| `polygon_native` | Bridge | ETH·Poly | core.md | Polygon PoS portal (PoS + FxPortal) |
| `quickswap` | DEX | Poly·Base | v2/v3/v4.md | UniV2 fork + Algebra V1/Integral; Polygon + Base |
| `radiant` | Lending·Bridge | Arb·BNB·ETH·Base | v1.md, v2.md | Aave-V2 omnichain (LayerZero); ~$50M Oct-2024 key compromise |
| `rainbow` | Bridge | ETH +Other (NEAR) | core.md | NEAR Rainbow Bridge (legacy), ETH L1 |
| `ramses` | DEX | Arb | cl.md, legacy.md | Solidly ve(3,3) + UniV3-style CL (fee-keyed); Arbitrum-only |
| `rango` | Bridge·Aggregator | 7 · Robin | README.md, diamond.md, middlewares.md | Rango diamond (same address on 8 chains, Safe owners) + destination middlewares; requestId link key |
| `realt_rmm` | Lending | +Other (Gnosis) | core.md | RealToken Aave fork, Gnosis-only; RWA reserves |
| `relay` | Bridge | 7 · Robin | core.md | Relay intent bridge: Depository escrow (same address on all 8), solver fills, RelayCallExecuted releases to solvers; no on-chain deposit→payout key |
| `retrobridge` | Bridge | 7 +Other | core.md | RetroBridge maker hot wallet + RetroRouter; no on-chain destination or link key |
| `rhinofi` | Bridge | 7 · Robin +Other | core.md | Rhino.fi pool bridge: upgradeable DVFDepositContract per chain; commitmentId (quoteId) on the source only; payouts carry no key |
| `rocketpool` | LST | ETH·Base·Arb·OP·Poly | core.md, l2.md | rETH decentralized-validator staking; L2 = bridged rETH |
| `ronin_native` | Bridge | ETH +Other (Ronin) | core.md | Ronin gaming-chain bridge, ETH L1 |
| `rootstock_native` | Bridge | ETH +Other (Rootstock) | core.md | Rootstock federated token bridge; deprecated but live; no BNB side |
| `rubic` | Bridge·Aggregator | 7 · Robin | core.md | Rubic cross-chain aggregator diamond (a LI.FI fork: shared topics), ERC20Proxy and destination executors |
| `scroll_native` | Bridge | ETH +Other (Scroll) | core.md | Scroll canonical bridge: L1ScrollMessenger, GatewayRouter and 12 gateways, ScrollChain, message queues, EnforcedTxGateway; Morph look-alikes listed |
| `seamlessprotocol` | Lending·Restaking | Base·ETH | v1.md, leveragetokens.md | Aave-V3 lending (Base) + Morpho-powered leverage tokens |
| `shibaswap` | DEX | ETH | core.md | UniV2 fork (SSLP) + TopDog farm + BONE/Bury staking; ETH-only |
| `snowbridge` | Bridge·Messaging | ETH·Base·Arb·OP +Other (Polkadot) | core.md | Polkadot↔Ethereum BEEFY bridge (Gateway + agents); L2 adaptors via Across |
| `socket` | Bridge·Aggregator | 7 · Robin | README.md, openrouter.md, gateway.md, bungee-auto.md | Socket/Bungee: OpenRouter + RFQ vault, legacy SocketGateway routes, dormant Bungee Auto; Robinhood has OpenRouter only |
| `sonne_finance` | Lending | OP·Base | core.md | Compound-V2 fork; wound down post ~$20M Base exploit |
| `spark` | Lending·CDP | ETH +Gnosis | sparklend.md | Aave-V3 fork; D3M-supplied fixed-$1 DAI |
| `squid` | Bridge·Aggregator | 7 · Robin | README.md, router.md, coral.md | Squid cross-chain router on Axelar (CCTP and Chainflip entry points) plus Squid Intents (CORAL V1 Spokes; V2 off-chain); the Robinhood router is the unlisted alternate address |
| `stakewise` | LST | ETH +Gnosis | v2.md, v3.md | V2 pooled sETH2/rETH2 → V3 osETH vaults; ETH-only of 7 |
| `stargate` | Bridge | 7 | README.md, v1.md, v2.md | LayerZero pool bridge: v2 taxi/bus OFT pools (live), v1 Router/Pool (winding down); NOT Robinhood |
| `starknet_native` | Bridge | ETH +Other (Starknet) | core.md | StarkGate: Starknet core messaging, StarkgateManager/Registry, multi-token bridge and 32 per-token L1 bridges (plus the DAI v0 gateway and LORDS); Paradex look-alikes listed |
| `strike` | Lending | ETH | core.md | Compound-V2 fork (STRK), ETH-only |
| `sui_native` | Bridge | ETH +Other (Sui) | core.md | Sui native committee bridge (SuiBridge + BridgeVault) |
| `sushiswap` | DEX | 7 | v2/v3/trident.md | UniV2/V3 fork + Trident; all 7 |
| `swaap` | DEX | 7 | core.md | Swaap V2; Balancer-V2-fork Vault + signed-RfQ SafeguardPools; all 7 |
| `swell` | LST·Restaking | ETH +Other (Swellchain) | core.md | swETH (LST) + rswETH (LRT) + Earn vaults; ETH + Swellchain |
| `symbiosis` | Bridge | 7 · Robin | core.md | Cross-chain AMM/stableswap liquidity bridge (Portal, Synthesis, BridgeV2); intents on Base, BNB, Arb; crossChainID link key |
| `synapse` | Bridge | 7 | synapse.md, rfq.md | nUSD/nETH liquidity bridge + RFQ |
| `synthetix` | Perps | ETH·OP·Base·Arb | v2.md, v3.md | Synth/perps derivatives; V2 → V3 collateral system |
| `taiko_native` | Bridge | ETH +Other (Taiko) | core.md | Taiko Alethia bridge: Bridge (ETH escrow), ERC20/ERC721/ERC1155 vaults, SignalService, QuotaManager, Inbox |
| `teleswap` | Bridge | ETH·Base·Arb·OP·Poly·BNB +Other (Bitcoin) | core.md | TeleSwap (TeleportDAO) BTC bridge: EVM connectors over Across, Polygon/BNB routers, lockers, teleBTC mint/burn |
| `tessera` | DEX | Base·BNB | core.md | Wintermute dark AMM (EVM = Base + BSC only) |
| `tether` | Bridge·Token | ETH·Arb·OP·Poly +Other | core.md | USDT0 LayerZero-OFT omnichain USDT (~23 chains) |
| `thena` | DEX | BNB | classic.md, cl.md | Solidly ve(3,3) + Algebra-V1 CL; BNB-only. The fork parent of Blackhole/Ramses |
| `thorchain` | Bridge·DEX | ETH·Base·BNB·Avax +Other (BTC etc.) | core.md | THORChain Router: memo swaps to native L1s; Asgard vault EOAs rotate; link = OUT:/REFUND: memo hash |
| `topaz` | DEX | BNB | amm.md, slipstream.md | ve(3,3) Velodrome+Aerodrome fork, BNB-only |
| `traderjoe` | DEX | ETH·BNB·Avax·Arb | v1/v2.0/v2.1/v2.2.md | Liquidity Book bins; Avax+Arb full, BSC no-2.2 |
| `train` | Bridge | ETH·Base·Arb·OP·Poly·BNB·Robin +Other | core.md | Train HTLC bridge: v3 at one address + legacy HTLC; hashlock link key |
| `uniswap` | DEX | 7 | v2/v3/v4.md | The canonical AMM; V2 pairs → V3 CL → V4 hooks |
| `universalx` | Bridge | 7 | core.md | UniversalX (Particle) Universal Accounts v1 pools (Deposited/Released/Refunded), retired; v2 contracts unpublished |
| `uwulend` | Lending | ETH | core.md | Aave-V2 fork, ETH-only; ~$24M June-2024 oracle exploit |
| `velodrome` | DEX | OP +Other (Superchain) | v2.md, slipstream.md, superchain.md | ve(3,3) + Slipstream; Optimism-Superchain |
| `venus` | Lending | BNB·ETH·Arb·OP·Base | core-pool.md, isolated-pools.md | Compound-fork; BNB core (Diamond) + isolated pools |
| `wormhole` | Bridge·Messaging | 7 · Robin | README.md, core.md, token-bridge.md, nft-bridge.md, relayer.md, cctp.md, ntt.md | Wormhole guardian message bus (key = emitter chain + emitter + sequence), Token/NFT Bridge, Relayer/Executor, CCTP integration, NTT; Robinhood has Core, Executor and NTT only |
| `xyfinance` | Bridge·Aggregator | 7 | core.md | XY Finance yBridge v3, YBridgeVaults, XY Router, legacy XSwapper; idle since Nov 2025 |
| `zerolend` | Lending | ETH·Base | core.md | Aave-V3 fork; of 7 only ETH+Base (primary on L2s off-target) |
| `zkbridge` | Bridge·Messaging | 7 +Other | lightclient.md, messaging.md | Polyhedra zk light-client message/token bridge |
| `zkswap` | Bridge | ETH | core.md | ZKSwap V1/V2 zkSync-fork rollup escrows (V1 in exodus mode, V2 operator stopped 2024) |
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

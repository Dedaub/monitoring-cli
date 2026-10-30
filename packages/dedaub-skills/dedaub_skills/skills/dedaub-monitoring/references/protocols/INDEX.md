# Protocol Reference Index — category & chain lookup

**Purpose.** One-screen map of every protocol doc under `references/protocols/<slug>/`. Use it to answer
"which protocols are bridges / DEXs / lending / liquid-staking…" and "which are on chain X" **before**
opening any `<slug>/` file. Resolve the category/chain → pick slugs here → then open
`<slug>/README.md` (multi-file dirs) or `<slug>/<file>.md` for the actual topics/selectors/addresses.

**Chain legend.** `ETH` Ethereum(1) · `Base`(8453) · `BNB`(56) · `Avax`(43114) · `Arb`(42161) ·
`OP`(10) · `Poly` Polygon PoS(137) · `Robin` Robinhood Chain(4663) · `Arc` Arc(5042). **`7` = the seven targets other
than Robinhood Chain and Arc**; a row names `Robin` / `Arc` explicitly when the doc covers it. `+Other` = a non-target
chain the doc emphasizes (Gnosis 100, Tron, Celo, Swellchain, Fraxtal, zkSync, Linea, NEAR, Ronin, Unichain…).
A chain listed = a real native **or** bridged deployment per that doc; always confirm the exact address
in the doc (some entries are bridged representations / decoys — the docs flag these).

**Categories.** `Bridge` `Messaging` `DEX` `Aggregator` `Lending` `CDP` `LST`(liquid staking)
`Restaking`(LRT) `Perps` `ALM` `Oracle` `Token` `Privacy`. A protocol may carry several — primary first.

---

## 1. Category → protocols (reverse lookup)

- **Bridge (75):** `1sec` `across` `agglayer` `allbridge` `aori` `arbitrum_native` `aster` `avalanche_c_bitcoin`
  `avalanche_c_native` `axelar` `beamer` `butter` `cctp` `celer` `chainflip`
  `circle_gateway` `connext` `debridge` `eclipse_native` `eco` `evodefi` `extended` `fuel_native` `garden` `gaszip`
  `gnosis_native` `hop` `hyperlane` `hyperliquid` `layerswap` `layerzero` `lifi` `lighter`
  `linea_native` `maya` `mayan` `meson` `minibridge` `multichain` `near_omni` `nitro` `op_stack`
  `orbiter` `owlto` `pheasant` `polygon_native` `rainbow` `rango` `relay` `retrobridge` `rhinofi`
  `ronin_native` `rootstock_native` `rubic` `scroll_native` `sky` (SkyLink) `snowbridge` `socket` `squid` `stargate`
  `starknet_native` `sui_native` `symbiosis` `synapse` `taiko_native` `teleswap` `tether` `thorchain`
  `train` `universalx` `wormhole` `xyfinance` `zkbridge` `zkswap` `zksync_native`
  — *(+`radiant` is omnichain lending)*
- **Messaging (generic interop):** `layerzero` `axelar` `celer` `connext` `zkbridge` `chainlink`
  `debridge` `gnosis_native` `hyperlane` `snowbridge` `wormhole`
- **DEX / AMM:** `aerodrome` (incl. Aero) `angstrom` `apeswap` `archery` `balancer` `bancor` `beets` `biswap` `blackhole`
  `camelot` `circle_stablefx` (RFQ FX) `curve` `dodo` `dooar` `ekubo` `fables` `fluid` `fraxswap` `izumi` `lista` (ListaV3/V2)
  `metric` `native` `pancakeswap` `pendle` `pharaoh` `polymarket` (prediction CLOB) `quickswap` `ramses` `shibaswap`
  `sushiswap` `swaap` `tessera` `thena` `topaz` `traderjoe` `uniswap` `velodrome`
- **Aggregator (routing):** `arcus` (spot router) · `circle_stablefx` (RFQ) · `dodo` (smartroute) · `lifi` · `mayan` · `native` (RFQ) · `rango` · `rubic` · `socket` · `squid` · `xyfinance`
- **Lending / money-market:** `40acres` `aave` `agave` `benqi` `compound` `euler` `fluid` `fluxfinance`
  `granary` `justlend` `kaskad` `layerbank` `lista` (Moolah) `lodestar` `maple` `moola` `moonwell` `morpho` `native` `pike`
  `radiant` `realt_rmm` `seamlessprotocol` `sonne_finance` `spark` `strike` `uwulend` `venus` `zerolend`
- **CDP / stablecoin engine:** `sky` (MCD/USDS) · `liquity` (LUSD/BOLD) · `curve` (crvUSD) · `spark` (D3M DAI) ·
  `ethena` (USDe mint/redeem) · `falcon` (USDf) · `lista` (lisUSD)
- **Liquid staking (LST):** `lido` `rocketpool` `etherfi` `frax_finance` `stakewise` `swell` `coinbase` `binance`
  `benqi` (sAVAX) `lista` (slisBNB) `aster` (asBNB) `ssv` (DVT staking infra)
- **Restaking (LRT):** `eigenlayer` `etherfi` `kelp` `swell` `seamlessprotocol` (Morpho-powered leverage tokens)
- **Perps / derivatives:** `gmx` `synthetix` `hyperliquid` `lighter` `aster` `extended` `arcus` `meridian`
- **ALM (liquidity mgmt):** `arrakis` `spark` (Liquidity Layer) `grove`
- **Oracle / data infra:** `chainlink` `pyth` · `polymarket` (UMA adapters, OracleAggregator)
- **Token / stablecoin issuer:** `circle_tokens` (USDC/EURC/USYC/cirBTC) · `tether` (USDT0) · `paxos` (USDG/PYUSD/USDP/PAXG) ·
  `sky` (DAI/USDS/SKY) · `ethena` (USDe/sUSDe/ENA/USDtb) · `falcon` (USDf/FF) · `lista` (lisUSD/LISTA) · `aster` (USDF) ·
  `robinhood_stock_tokens` (tokenized equities) · `pendle` (PENDLE/sPENDLE) · `etherfi` (weETH/ETHFI OFTs) ·
  `maple` (SYRUP) · `biswap` (BSW OFT on ETH/Base/Arb)
- **Privacy / mixer:** `tornado`

*Not staking docs (no EVM contract): the beacon-chain entity tags `bitcoin_suisse`, `chorusone`,
`darma_capital` are validator/operator labels only — stake via the shared ETH2 deposit contract or
third-party protocols (Liquid Collective / StakeWise). No `<slug>/` dir exists for them.*

---

## 2. Per-protocol table

| Slug | Categories | Chains | Files | One-liner |
|------|-----------|--------|-------|-----------|
| `1sec` | Bridge | ETH·Base·Arb +Other (ICP) | core.md | 1sec ICP bridge: Lock1-4 lockers, Burn1-4 tokens; payouts are plain transfers/mints from the 1sec wallet EOA; no on-chain link key |
| `40acres` | Lending·CDP | Base·OP·Avax·ETH · Robin · Arc | core.md | veNFT self-repaying loans; ETH, Robinhood and Arc = portfolio layer only |
| `aave` | Lending | 7 (V3) · Arc (V4) | v1–v4.md | Canonical money-market; V1 ETH-legacy → V3 all 7; V4 hub-spoke on ETH (+Sentora instance), Base, Avax, OP (EtherFi white-label), Arc |
| `across` | Bridge | 7 · Robin · Arc | core.md | Intent/relayer optimistic bridge; Universal SpokePools on Avalanche, Robinhood and Arc |
| `aerodrome` | DEX | ETH·Base·Arb·OP · Robin · Arc +Other (Ink) | README.md, amm.md, slipstream.md, aero.md | Aerodrome ve(3,3) AMM + Slipstream (legacy since 2026-10-21; gauges killed, pools still trade) and its successor Aero (Aerodrome+Velodrome merger): new AERO, Base root + leaves on ETH, OP, Arb, Robinhood, Arc; new V2 `PoolCreated` topic0 |
| `agave` | Lending | +Other (Gnosis) | core.md | Aave-V2 fork, Gnosis-only; absent all 7 |
| `agglayer` | Bridge | ETH +Other | core.md | Polygon AggLayer unified LxLy bridge (L1 anchor) |
| `allbridge` | Bridge | 7 +Other | classic.md, core.md | Allbridge Core (CCTP/xReserve/OFT adapters; vUSD pool path discontinued Jul 2026) + Classic cross-chain |
| `angstrom` | DEX | ETH | core.md | UniV4 hook batch-auction MEV-protect order flow; ETH-only, log0 swaps |
| `aori` | Bridge | 7 | core.md | Aori intent settlement over LayerZero: Deposit/Fill/Settle/Cancel/Withdraw, orderId link key; v0.3.1 live on ETH, Base, Arb, OP, BNB; v0.4.0 proxy staged on 7 chains (new topic0s); not Robinhood or Arc |
| `apeswap` | DEX | BNB·ETH·Arb·Poly | core.md | UniV2 fork + MasterApe farms + BANANA; BNB primary, no Base/Avax/OP |
| `arbitrum_native` | Bridge | ETH·Base·Arb·Robin +Other (Nova, Orbit chains) | README.md, core.md, orbit.md | Arbitrum Nitro canonical bridge: One/Nova plus Robinhood Chain and the Orbit L2/L3 chains on Ethereum, Base and Arbitrum One; no Orbit chain on Arc |
| `archery` | DEX | Arc | core.md | Aerodrome-style V2 + Slipstream CL ve(3,3) DEX; Arc-only, pre-TGE (no emissions) |
| `arcus` | Perps·Aggregator | Robin | README.md, perps.md, ptokens.md, spot.md | Perps on Robinhood Chain: BridgeVault/CheckpointManager rootchain (arcUSDG custody), pToken leveraged ERC-7540 vaults, Stock Token spot router |
| `arrakis` | ALM | ETH·Poly·Arb·OP·Base·BNB·Robin | v1/v2/modular.md | Uniswap-V3 liquidity-management vaults; Modular only on Robinhood; not Avalanche or Arc |
| `aster` | Perps·Bridge·LST·Token | BNB·ETH·Arb·Base | README.md, bridge.md, earn.md, alp.md | Aster (ApolloX+Astherus) deposit vaults + legacy ApolloX treasuries, USDF/asUSDF/asBNB/asBTC Earn on BNB, legacy 1001x/ALP diamond |
| `avalanche_c_bitcoin` | Bridge | Avax +Other (BTC) | core.md | Avalanche Bridge BTC.b wrapped Bitcoin; BridgeTokenAdapter impl rotated 2026-10-29 |
| `avalanche_c_native` | Bridge | ETH·Avax | core.md | Avalanche Bridge (AB) ETH↔C-Chain |
| `axelar` | Bridge·Messaging | 7 · Arc | core.md | GMP + token bridge cross-chain; Arc runs the Amplifier gateway at its own addresses (live 2026-10-29) |
| `balancer` | DEX | ETH·Base·BNB·Avax·Arb·OP·Poly +Gnosis | v2.md, v3.md | Weighted/boosted-pool AMM + vault; not on Robinhood/Arc (canonical literals hold forwarder decoys) |
| `bancor` | DEX | ETH | v3.md | Omnipool single-sided AMM, ETH-only |
| `beamer` | Bridge | ETH·OP·Base·Arb +Other | core.md | Optimistic rollup-to-rollup bridge; dormant (no logs for 180+ days to 2026-10-05, front end gone) |
| `beets` | DEX | OP | core.md | Beethoven X; Balancer-V2 fork, shared Vault; OP-only of 7; Robinhood/Arc Vault literal is a decoy |
| `benqi` | Lending·LST | Avax | core.md | Compound-V2 fork + sAVAX liquid staking; Avalanche-only |
| `binance` | LST | ETH·BNB | wbeth.md | WBETH (yield-in-price) + BETH (1:1 receipt) |
| `biswap` | DEX·Token | BNB (+BSW ETH·Base·Arb) | core.md | UniV2 fork + iZi-style V3; BNB-only DEX, BSW OFT bridged to 3 |
| `blackhole` | DEX | Avax | classic.md, cl.md | ve(3,3) + concentrated-liquidity AMM, Avalanche |
| `butter` | Bridge | 7 · Robin · Arc +Other | README.md, router.md, mos-v3.md, mos-v2.md | MAP Omnichain Service (MOS) cross-chain; MOS V3 on all eight chains and Arc; ButterRouter partial on Avalanche, Robinhood and Arc |
| `camelot` | DEX | Arb | README.md, v2.md, v3.md, v4.md | V2 AMM + Algebra V1.9 (v3) + Algebra Integral (v4) CL, Arbitrum; v4 `Swap`/`Burn` topic0s differ from v3 |
| `cctp` | Bridge | 7 · Robin · Arc | README.md, v1.md, v2.md | Circle USDC burn-and-mint; V1 deprecated (limits cut from 2026-10-31, paused 2026-12-01); V2 on Robinhood (domain 35, pre-launch) and Arc (domain 26, live); + TokenMessengerWithFees, FeeManager, CrossChainTokenService (EURC, cirBTC, WETH) |
| `celer` | Bridge·Messaging | 7 | core.md, pegged.md | cBridge liquidity + pegged token + IM messaging |
| `chainflip` | Bridge·DEX | ETH·Arb·BNB +Other | core.md | Chainflip Vault/KeyManager; vault swaps + deposit channels; no on-chain link key |
| `chainlink` | Oracle·Messaging | 7 · Robin · Arc +many | ccip/data-feeds/vrf/automation/functions/data-streams/link-token | Price feeds (incl. Robinhood stock-token feeds and Arc), CCIP (ramps + pools on all 9; Arc 2.0.0 + a 1.6.0 Solana pair), Data Streams and LINK on Robinhood/Arc, VRF, Automation, Functions |
| `circle_gateway` | Bridge | ETH·Base·Arb·OP·Poly·Avax·Arc | core.md | Circle unified USDC balance: GatewayWallet deposits/burns, GatewayMinter attested mints; NOT BNB, NOT Robinhood |
| `circle_stablefx` | DEX·Aggregator | Arc | core.md | Circle StableFX RFQ FX settlement (USDC⇄EURC): FxEscrow UUPS proxy on Arc only; trade id link key; upgraded 2026-10-30 |
| `circle_tokens` | Token | 7 · Robin · Arc | README.md, fiattoken.md, usyc.md | Circle-issued tokens: USDC/EURC/cirBTC FiatToken (MasterMinter, blacklist, pause) on ETH·Base·Avax·Arb·OP·Poly·Robin·Arc (no BNB); USYC + Teller stack on ETH·BNB·Arc |
| `coinbase` | LST | ETH·Base·Arb·OP·Poly | cbeth.md | cbETH; FiatToken fork, oracle-pushed rate; 5 bridge wrappers |
| `compound` | Lending | ETH·Base·Arb·OP·Poly | v2.md, v3.md | V2 pools + V3 Comet single-borrow-asset |
| `connext` | Bridge·Messaging | 7 | README.md, nxtp.md, amarok.md, core.md | Connext NXTP v1/v0, Amarok and Everclear (sunset announced 2026-05-21); not Robinhood or Arc |
| `curve` | DEX·CDP | 7 · Robin · Arc +Other (Gnosis) | README.md, curve.md, crvusd.md | StableSwap/crypto AMM + crvUSD LLAMMA CDP; Robinhood/Arc = NG factories only (newer build, new `PlainPoolDeployed` topic0) |
| `debridge` | Bridge·Messaging | 7 · Robin · Arc +Other | README.md, dln.md, dmp.md | deBridge DLN intent orders (solver fill, escrow unlock/cancel; orderId key) + deBridgeGate validator-signed messaging; same DLN addresses on all 9 (Robinhood and Arc use their own hook pair and EOA-owned OZ v5 ProxyAdmins) |
| `dodo` | DEX·Aggregator | 7 | v1/v2/v3.md, smartroute.md | PMM AMM + SmartRoute aggregator |
| `dooar` | DEX | ETH·BNB | core.md | DooarSwap (STEPN); tiny UniV2 fork, ETH+BSC only |
| `eclipse_native` | Bridge | ETH +Other (Eclipse) | core.md | Eclipse SVM rollup canonical ETH bridge (CanonicalBridgeV3 + Treasury) |
| `eco` | Bridge | ETH·Base·BNB·Arb·OP·Poly·Robin·Arc +Other | core.md | Eco Routes intent bridge: immutable Portal (migrated 2026-09-29 to 0xEC000769…; old 0xEC000064… retired) + per-intent Vaults + Executor, modular provers (Polymer prover on Arc); intentHash links both sides; current Portal on ETH/Base/Arb/OP/Poly/Arc, BNB and Robinhood keep only the retired Portal; NOT Avalanche |
| `eigenlayer` | Restaking | ETH | core.md | Restaking core (Delegation/Strategy/EigenPod) + EIGEN; ETH-only |
| `ekubo` | DEX | ETH·Base·BNB·Arb·OP·Poly · Robin | v2.md, v3.md | UniV4-like singleton AMM; anonymous log0 swaps |
| `etherfi` | LST·Restaking·Token | 7 (Poly: Cash factory proxies only) · Robin · Arc | README.md, core.md, weeth-crosschain.md, liquid.md, cash.md | eETH/weETH liquid (re)staking on Ethereum, weETH OFT mesh + native minting + Arbitrum canonical weETH, Liquid BoringVault/Midas vaults, Cash card stack on Optimism |
| `ethena` | Token·CDP | ETH·Base·BNB·Avax·Arb·OP·Robin | core.md | Ethena synthetic dollar: USDe/sUSDe (cooldown silo), EthenaMinting V2, ENA/sENA/rsENA, USDtb + PSMs (USDe PSM on Avalanche); LayerZero OFTs on 6 chains incl. Robinhood; not Polygon or Arc |
| `euler` | Lending | ETH·Base·Arb·BNB·Avax·Poly | v1.md, v2.md | V1 module-dispatch (dead post-hack) → V2 EVC+EVK vaults; not Robinhood or Arc |
| `evodefi` | Bridge | ETH·Arb·OP·Poly·BNB·Avax | core.md | EVO DeFi custodial pool bridge (insolvent 2022; last deposits 2023–2024); same addresses on 6 chains |
| `extended` | Perps·Bridge | ETH·Arc | core.md | Extended (ex-X10) perp DEX; SP1-proof settlement + Circle-MSCA custody on Arc since 2026-10-22 (withdrawals via Rhino.fi; admin EOAs, no settlement timelock); legacy frozen StarkEx on ETH |
| `fables` | DEX | Robin | core.md | Dynamic-fee ve(3,3) DEX on Uniswap v4 hooks (ERC-6909 LP ledger; `ModifyLiquidity.sender` = hook); Robinhood-only |
| `falcon` | CDP·Token | ETH·Base·BNB | core.md | Falcon Finance USDf synthetic dollar (off-chain mint; PreCollateralizedMinter is the only on-chain minter) + sUSDf/Position NFT staking, FF/sFF; CCIP to BNB/Base |
| `fluid` | Lending·DEX | ETH·Base·Arb·Poly·BNB | lending/vaults/dex/liquidity-layer.md | Instadapp liquidity-layer; vaults T1–T4 + smart-debt DEX |
| `fluxfinance` | Lending | ETH | core.md | Ondo Compound-V2 fork w/ KYC allowlist; ETH-only |
| `frax_finance` | LST | 7 | frxeth.md | frxETH (flat peg) + sfrxETH (ERC4626); bridged to 6 L2s |
| `fraxswap` | DEX | ETH·BNB·Avax·Arb·OP·Poly | v1.md, v2.md | TWAMM time-weighted AMM; NOT Base |
| `fuel_native` | Bridge | ETH +Other (Fuel) | core.md | Fuel Ignition canonical bridge: message portal (ETH) + ERC-20 gateway |
| `garden` | Bridge | ETH·Base·Arb·BNB·Robin·Arc +Other (BTC) | core.md | Garden per-asset HTLC atomic swaps (BTC↔EVM); link = secretHash; cirBTC HTLC on Arc |
| `gaszip` | Bridge | 7 · Robin · Arc +Other | core.md | Gas.zip native gas refuel: Direct Deposit EOA (no log), GasZipV2 Deposit, GasLZV2 LayerZero drop; payout-signer EOAs; Robinhood payouts only; Arc contract deposits only (no Direct Deposit) |
| `gmx` | Perps | Arb·Avax | v1.md, v2.md | GLP/GM perp DEX; Arbitrum + Avalanche only |
| `gnosis_native` | Bridge·Messaging | ETH·BNB +Other (Gnosis) | core.md | Gnosis xDai bridge (USDS↔xDAI), AMB and Omnibridge; BSC pair deprecated |
| `granary` | Lending | ETH·Base·BNB·Avax·Arb·OP | core.md | Aave-V2 soft-fork (Byte Masons); not Polygon; winding down |
| `grove` | ALM | ETH·Base·Avax·Robin +Other (Plume) | core.md | Sky star: Grove Liquidity Layer, a fork of the Spark ALM controller (ALMProxy/controllers/RateLimits) allocating to RWA/credit; Robinhood ALMProxy holds USDG + Steakhouse USDG vault |
| `hop` | Bridge | ETH·OP·Arb·Poly·Base | core.md | hToken AMM bridge; not BNB/Avalanche |
| `hyperlane` | Messaging·Bridge | 7 · Robin · Arc +Other | README.md, core.md, warp_routes.md | Permissionless Mailbox messaging + warp-route token bridges (domain = chain id); registry warp routes on Robinhood and Arc; ICA Router V3; independent Mailboxes listed |
| `hyperliquid` | Bridge·Perps | Arb | core.md | Hyperliquid L1 deposit bridge (Bridge2), Arbitrum |
| `izumi` | DEX | ETH·Base·BNB·Arb·OP·Poly | iziswap.md, liquidbox.md | Discretized-liquidity DL-AMM (not a Uni fork); not Avax |
| `justlend` | Lending | +Other (Tron) | core.md | Compound-V2 fork, Tron-only; absent all 7 EVM |
| `kaskad` | Lending | Robin +Other (Igra) | core.md | Aave V3.3 fork; Robinhood market (main market on Igra) |
| `kelp` | Restaking | ETH·Base·BNB·Avax·Arb·OP | core.md | rsETH LRT on EigenLayer + L2 deposit pools / OFT / CCIP; Apr-2026 OFT exploit (public reports); L2 pools paused, some adapter peers cleared |
| `layerbank` | Lending | BNB · Robin +Other (Linea/Scroll/Mode) | README.md, core.md, v3.md | V1/V2 own Core+LToken (BNB V2 near-dormant); V3 = Aave V3 fork on Robinhood |
| `layerswap` | Bridge | 7 · Robin · Arc +Other | core.md | Layerswap solver bridge: immutable Depository + two wallet EOAs, same on all 9; sequence_number key on the source only |
| `layerzero` | Messaging·Bridge | 7 · Robin · Arc +many | README.md, v1.md, v2.md | OFT / generic cross-chain messaging endpoint; major OFT tables (DRV on Robinhood, weETH on Arc); Robinhood (eid 30416) and Arc (eid 30417) share EndpointV2 0x6f47…dd5b |
| `lido` | LST | ETH·Base·BNB·Arb·OP | README.md, v1–v4.md, l2.md | stETH/wstETH; the canonical ETH LST; v4.1.0 adds 0x02 modules (CuratedModule v2, CSM 0x02), consolidation, top-ups |
| `lifi` | Bridge·Aggregator | 7 · Robin · Arc | README.md, diamond.md, facets.md, periphery.md | LI.FI diamond: LiFiTransferStarted source leg, transactionId link key, Executor/receivers destination; own diamonds on Robinhood and Arc (0x1231DEB6… on Robinhood is an address vault); M0Facet added 2026-10 |
| `lighter` | Perps·Bridge | ETH·Robin | core.md | zkLighter orderbook perp DEX; ETH L1 settlement + separate USDG instance on Robinhood; not Arc |
| `linea_native` | Bridge | ETH +Other (Linea) | core.md | Linea canonical bridge: LineaRollup message service and ETH escrow, TokenBridge (V1 and V2 events), YieldManager, retired USDC bridge |
| `liquity` | CDP | ETH | README.md, v1.md, v2.md | Immutable CDP: V1 LUSD (ETH collateral) + V2 BOLD (May 2025 relaunch; WETH/wstETH/rETH branches, user-set rates, batch managers); ETH-only, bridged LUSD on Base/Arb/OP |
| `lista` | Lending·CDP·LST·DEX·Token | BNB·ETH | README.md, lending.md, staking.md, cdp.md, governance.md, dex.md | Lista DAO (BNB-first): Moolah lending = Morpho Blue fork (same topic0s/selectors, filter by emitter) on BNB+ETH; slisBNB LST (+ETH OFT); lisUSD CDP; LISTA/veLISTA (retired 2026-04); ListaV3/V2 DEX |
| `lodestar` | Lending | Arb | core.md | Compound-V2 fork, Arbitrum-only; frozen post plvGLP exploit |
| `maple` | Lending·Token | ETH·Base (+SYRUP 7) | README.md, v1.md, v2.md, modular.md, syrup-cross-chain.md | RWA/institutional credit pools; Globals/PoolManagers on V500; modular strategies + LiquidityRouter (ETH; no instances yet); SYRUP OFT + CCIP token |
| `maya` | Bridge·DEX | ETH·Arb +Other | core.md | Maya Protocol router (THORChain fork, same topics); halted 2026-08-18, live again since 2026-09-30 |
| `mayan` | Bridge·Aggregator | 7 | README.md, swift.md, mctp.md, wh-swap.md, forwarder.md | Mayan Swift intents (order hash key), CCTP routes (MCTP not on BNB), Wormhole swap via Solana; not on Robinhood or Arc |
| `meridian` | Perps | Robin·Arb·Poly | README.md, perps.md, predict.md | ExchangeGateway perps on Robinhood (merUSD/USDe collateral, Pyth Lazer) + Predict escrow/vaults (ex-Sapience; 1-of-2 Safe owner) with Arbitrum bridge peer and Polygon Polymarket reader |
| `meson` | Bridge | 7 · Robin +Other | core.md | Meson atomic-swap bridge: one UUPS proxy on all eight chains; encodedSwap link key |
| `metric` | DEX | ETH (V1: ETH·Base·BNB·Avax·Arb·Poly·Robin) | README.md, core.md, founder-fleet.md, v1.md | Two protocols named Metric: Metric.exchange front-end (ETH-only, legacy) + metric.xyz V1 oracle-guided OMM DEX, same CREATE2 factory on 7 chains |
| `minibridge` | Bridge | 7 +Other | core.md | Chaineye MiniBridge: maker EOA, confirm code 8000+id in the value; config empty since 2026-08-24 |
| `moola` | Lending | +Other (Celo) | core.md | Aave fork, Celo-only; absent all 7 |
| `moonwell` | Lending | Base·OP +Other | core.md | Compound-V2 fork; lending only on Base+Optimism |
| `morpho` | Lending | 7 · Robin · Arc | README.md, v1.md, v2.md, midnight.md, optimizers.md | Blue immutable markets + MetaMorpho/Vaults-V2; Midnight (Markets V2, fixed-rate/fixed-term) on ETH/Base/Robin/Arc with full topics in midnight.md |
| `multichain` | Bridge | ETH·Arb·OP·Poly·BNB·Avax | core.md | Multichain/Anyswap MPC routers V3–V7 (stopped July 2023; unpaid deposits still arrive); not Base, Robinhood or Arc |
| `native` | DEX·Lending·Aggregator | ETH·Base·BNB·Arb · Robin · Arc | dex.md, lending.md | RFQ swap engine (NativeRouter V6/V4/V3; V3/V4 phase out end Oct 2026) + lending; Arc = unlisted idle V4-build set |
| `near_omni` | Bridge | ETH·Base·Arb·Poly·BNB +Other (NEAR, Solana) | core.md | NEAR Omni Bridge (MPC-signed), Rainbow successor |
| `nitro` | Bridge | 7 +Other | core.md, gateway.md | Router Protocol Voyager gateway + AssetBridge; sunset (Router ceased operations 2026-09-30) |
| `op_stack` | Bridge | ETH·Base·OP·BNB +Other (49 OP Stack L2s, Metis, 4 L3s on Base) | README.md, l1.md, l2.md | OP Stack canonical bridges: per-chain OptimismPortal/L1StandardBridge/L1CrossDomainMessenger (registry, removed, outside, Mantle), predeploys on OP and Base, opBNB, L3s on Base |
| `orbiter` | Bridge | 7 +Other | core.md, mdc.md | Maker-Deposit-Contract rollup bridge w/ arbitration |
| `owlto` | Bridge | ETH·Base·Arb·OP·Poly·BNB·Robin·Arc +Other | core.md | Owlto maker bridge: Depositor contracts + maker EOA; destination code in the event or the amount suffix; Robinhood and Arc relay route only |
| `pancakeswap` | DEX | BNB·Base·ETH·Arb·Robin·Arc | v2/v3/infinity/stableswap.md | UniV2/V3 fork + Infinity(V4) hooks + StableSwap; Arc = Infinity CL only |
| `paxos` | Token | ETH·Arb·Poly·Robin | README.md, usdg.md, pyusd_usdp_paxg.md | Paxos-issued stablecoins: USDG (ETH, Arb, Robinhood; UUPS + facets, SupplyControl, OFT burn/mint, 1-day timelock admin), PYUSD (ETH, Arb, Poly), USDP / PAXG / legacy BUSD (ETH only) |
| `pendle` | DEX·Token | ETH·Arb·Base·BNB·OP · Robin (+Avax cross-chain PT only) | README.md, v2.md, governance.md | Yield tokenization (SY→PT+YT, PT/SY time-decay AMM); Router 0x8888…f946; the "V6" factory runs V7 code; sPENDLE replaced vePENDLE |
| `pharaoh` | DEX | Avax | cl.md, legacy.md | Ramses/ve(3,3) CL + DLMM AMM, Avalanche |
| `pheasant` | Bridge | 7 · Robin · Arc +Other | core.md | Pheasant ERC-7683 intent bridge (ETH, Base, Arb, OP); swap wrapper only on Poly/BNB/Avax/Robinhood/Arc; orderId link key; CCTP wrapper |
| `pike` | Lending | Base +Other (Sonic) | core.md | Compound-V2 semantics + ERC-4626 surface; Base relaunch |
| `polygon_native` | Bridge | ETH·Poly | core.md | Polygon PoS portal (PoS + FxPortal) |
| `polymarket` | DEX·Oracle | Poly · ETH (legacy CTF/FPMM only) | README.md, v1.md, exchange_v2.md, position_manager.md | Prediction-market CLOB on Polygon; Gnosis CTF + UMA resolution; CTF Exchange V2 + pUSD is the live venue (new `OrderFilled`/`OrdersMatched` topic0s); PositionManager system live at low volume |
| `pyth` | Oracle | 7 · Robin · Arc | README.md, core.md, pro.md, entropy.md | Pyth pull oracle: Core price feeds on all 9 (Robinhood/Arc at 0x8250…; 0x2880… is a Wormhole setup helper, not Pyth), Core Compatible on 6, Pyth Pro verifier on 7, Entropy on Base/Arb/OP; Pyth-run Wormhole receivers; Express Relay wound down |
| `quickswap` | DEX | Poly·Base | v2/v3/v4.md | UniV2 fork + Algebra V1/Integral; Polygon + Base |
| `radiant` | Lending·Bridge | Arb·BNB·ETH·Base | v1.md, v2.md | Aave-V2 omnichain (LayerZero); ~$50M Oct-2024 key compromise |
| `rainbow` | Bridge | ETH +Other (NEAR) | core.md | NEAR Rainbow Bridge (legacy), ETH L1 |
| `ramses` | DEX | Arb·Poly·Robin | README.md, cl.md, legacy.md, v3.md | Solidly ve(3,3) + fee-keyed CL (Arbitrum, 2023) + 2026 tickSpacing CL redeploy on Arb/Poly/Robinhood; DLMM + Voter on Robinhood |
| `rango` | Bridge·Aggregator | 7 · Robin · Arc | README.md, diamond.md, middlewares.md | Rango diamond (same address on 9 chains, Safe owners) + destination middlewares (none on Robinhood/Arc); requestId link key |
| `realt_rmm` | Lending | +Other (Gnosis) | core.md | RealToken Aave fork, Gnosis-only; RWA reserves |
| `relay` | Bridge | 7 · Robin · Arc | core.md | Relay intent bridge: Depository escrow (same address on all 9), RelayRouter v3.2 periphery (default since 2026-10; new `SolverCallExecuted` topic0) and legacy v3.0, solver fills, RelayCallExecuted releases to solvers; no on-chain deposit→payout key |
| `retrobridge` | Bridge | 7 +Other | core.md | RetroBridge maker hot wallet + RetroRouter; no on-chain destination or link key |
| `rhinofi` | Bridge | 7 · Robin · Arc +Other | core.md | Rhino.fi pool bridge: upgradeable DVFDepositContract per chain; commitmentId (quoteId) on the source only; payouts carry no key |
| `robinhood_stock_tokens` | Token | Robin · Arb (EU family, partial) | core.md | Robinhood tokenized equities: 212 BeaconProxies sharing one AccessControlsRegistry (beacon, roles, blocklist, global pause) + StockFactory uid→token registry; ERC-8056 UI multiplier for splits/dividends; separate share-based EU family on Arbitrum |
| `rocketpool` | LST | ETH·Base·Arb·OP·Poly | core.md, l2.md | rETH decentralized-validator staking; L2 = bridged rETH |
| `ronin_native` | Bridge | ETH +Other (Ronin) | core.md | Ronin gaming-chain bridge, ETH L1; deposit leg idle since 2026-05, withdrawals live |
| `rootstock_native` | Bridge | ETH +Other (Rootstock) | core.md | Rootstock federated token bridge; deprecated but live; no BNB side |
| `rubic` | Bridge·Aggregator | 7 · Robin | core.md | Rubic cross-chain aggregator diamond (a LI.FI fork: shared topics), ERC20Proxy and destination executors; not Arc |
| `scroll_native` | Bridge | ETH +Other (Scroll) | core.md | Scroll canonical bridge: L1ScrollMessenger, GatewayRouter and 12 gateways, ScrollChain, message queues, EnforcedTxGateway; Morph look-alikes listed |
| `seamlessprotocol` | Lending·Restaking | Base·ETH | v1.md, leveragetokens.md | Aave-V3 lending (Base) + Morpho-powered leverage tokens |
| `shibaswap` | DEX | ETH | core.md | UniV2 fork (SSLP) + TopDog farm + BONE/Bury staking; ETH-only |
| `sky` | CDP·Token·Bridge | ETH·Base·Avax·Arb·OP +Other (Unichain, Solana) | README.md, mcd.md, usds.md, l2.md | Sky (ex-MakerDAO): MCD Vat/Dog/Clipper CDP engine, DAI/USDS, sUSDS/stUSDS savings, SKY Staking Engine, LitePSM, allocator vaults; SkyLink USDS/sUSDS on Base/OP/Arb/Unichain + LayerZero OFT on Avalanche; absent BNB/Poly/Robin/Arc |
| `snowbridge` | Bridge·Messaging | ETH·Base·Arb·OP +Other (Polkadot) | core.md | Polkadot↔Ethereum BEEFY bridge (Gateway + agents); L2 adaptors via Across |
| `socket` | Bridge·Aggregator | 7 · Robin · Arc | README.md, openrouter.md, gateway.md, bungee-auto.md | Socket/Bungee: OpenRouter + RFQ vault, legacy SocketGateway routes, dormant Bungee Auto; Robinhood and Arc have OpenRouter only |
| `sonne_finance` | Lending | OP·Base | core.md | Compound-V2 fork; wound down post ~$20M Base exploit |
| `spark` | Lending·CDP·ALM | ETH·Base·Arb·OP·Avax·Robin +Other (Gnosis) | README.md, sparklend.md, liquidity-layer.md, savings.md | SparkLend Aave-V3 fork (ETH) + Spark Liquidity Layer (ALMProxy/controllers/RateLimits) + Spark Savings (Spark Vaults V2 spUSDC/spUSDT/spETH/spPYUSD/spUSDG, sUSDC, PSM3); BNB has only the SPK OFT |
| `squid` | Bridge·Aggregator | 7 · Robin · Arc | README.md, router.md, coral.md | Squid cross-chain router on Axelar (CCTP and Chainflip entry points) plus Squid Intents (CORAL V1 Spokes; V2 off-chain); on Robinhood and Arc the router is the unlisted alternate address (no Axelar wiring) |
| `ssv` | LST | ETH | core.md | SSV Network DVT staking: operator/cluster/validator registry, ETH clusters + cSSV staking (v2.0.0; value unit changed from SSV to ETH); ETH-only |
| `stakewise` | LST | ETH +Gnosis | v2.md, v3.md | V2 pooled sETH2/rETH2 → V3 osETH vaults; ETH-only of 7 |
| `stargate` | Bridge | 7 | README.md, v1.md, v2.md | LayerZero pool bridge: v2 taxi/bus OFT pools (live; Ethereum METIS pool unwired 2026-10-27), v1 Router/Pool (winding down); NOT Robinhood (its "Stargate" route is OFT only), NOT Arc |
| `starknet_native` | Bridge | ETH +Other (Starknet) | core.md | StarkGate: Starknet core messaging, StarkgateManager/Registry, multi-token bridge and 32 per-token L1 bridges (plus the DAI v0 gateway and LORDS); Paradex look-alikes listed |
| `strike` | Lending | ETH | core.md | Compound-V2 fork (STRK), ETH-only |
| `sui_native` | Bridge | ETH +Other (Sui) | core.md | Sui native committee bridge (SuiBridge + BridgeVault) |
| `sushiswap` | DEX | 7 · Robin · Arc | v2/v3/trident.md | UniV2/V3 fork + Trident; all 7, plus V2 + V3 on Robinhood and Arc |
| `swaap` | DEX | 7 · Robin | core.md | Swaap V2; Balancer-V2-fork Vault + signed-RfQ SafeguardPools; all 7 + Robinhood (own Vault build at the Vault-A literal + own factories); not Arc |
| `swell` | LST·Restaking | ETH +Other (Swellchain) | core.md | swETH (LST) + rswETH (LRT) + Earn vaults; ETH + Swellchain |
| `symbiosis` | Bridge | 7 · Robin · Arc | core.md | Cross-chain AMM/stableswap liquidity bridge (Portal, Synthesis, BridgeV2); intents on Base, BNB, Arb; crossChainID link key |
| `synapse` | Bridge | 7 | synapse.md, rfq.md | nUSD/nETH liquidity bridge (adapter-routed, live) + RFQ FastBridge (dormant since 2026-05-09) |
| `synthetix` | Perps | ETH·OP·Base·Arb | v2.md, v3.md | Synth/perps derivatives; V2 → V3 collateral system; L2 deployments deprecated 2025 (OP shut down 2025-08), Ethereum V3 CoreProxy dormant since 2026-06-25 |
| `taiko_native` | Bridge | ETH +Other (Taiko) | core.md | Taiko Alethia bridge: Bridge (ETH escrow), ERC20/ERC721/ERC1155 vaults, SignalService, QuotaManager, Inbox |
| `teleswap` | Bridge | ETH·Base·Arb·OP·Poly·BNB·Robin +Other (Bitcoin) | core.md | TeleSwap (TeleportDAO) BTC bridge: EVM connectors over Across (Robinhood connector unlisted), Polygon/BNB routers, lockers, teleBTC mint/burn |
| `tessera` | DEX | Base·BNB·Robin | core.md | Wintermute dark AMM (EVM = Base + BSC + Robinhood) |
| `tether` | Bridge·Token | ETH·Arb·OP·Poly +Other | core.md | USDT0 LayerZero-OFT omnichain USDT (24 networks; second ETH adapter for IOTA); not Robinhood or Arc |
| `thena` | DEX | BNB | classic.md, cl.md | Solidly ve(3,3) + Algebra-V1 CL; BNB-only. The fork parent of Blackhole/Ramses |
| `thorchain` | Bridge·DEX | ETH·Base·BNB·Avax +Other (BTC etc.) | core.md | THORChain Router: memo swaps to native L1s; Asgard vault EOAs rotate; link = OUT:/REFUND: memo hash |
| `topaz` | DEX | ETH·Base·BNB·Robin·Arc | README.md, amm.md, slipstream.md, multichain.md | ve(3,3) Velodrome+Aerodrome fork; BNB hub with TOPAZ/veTOPAZ, xTOPAZ OFT spokes on Robinhood, Base, Ethereum, Arc |
| `tornado` | Privacy | 7 | core.md | Tornado Cash Classic fixed-denomination mixer: ETH router + Instance/Relayer registries + TORN governance; native-coin pools on BNB/Poly/Arb/OP/Avax via ProxyLight; Base copy unused; OFAC delisted 2025-03-21 |
| `traderjoe` | DEX | ETH·BNB·Avax·Arb | v1/v2.0/v2.1/v2.2.md | Liquidity Book bins; Avax+Arb full, BSC no-2.2 |
| `train` | Bridge | ETH·Base·Arb·OP·Poly·BNB·Robin +Other | core.md | Train HTLC bridge: v3 at one address + legacy HTLC; hashlock link key |
| `uniswap` | DEX | 7 · Robin · Arc | v2/v3/v4.md | The canonical AMM; V2 pairs → V3 CL → V4 hooks; many canonical literals on Robinhood/Arc hold fund-recovery forwarder decoys |
| `universalx` | Bridge | 7 | core.md | UniversalX (Particle) Universal Accounts v1 pools (Deposited/Released/Refunded), retired; v2 contracts unpublished |
| `uwulend` | Lending | ETH | core.md | Aave-V2 fork, ETH-only; ~$24M June-2024 oracle exploit |
| `velodrome` | DEX | OP +Other (Superchain) | README.md, v2.md, slipstream.md, superchain.md | ve(3,3) + Slipstream; Optimism-Superchain; legacy since 2026-10-21 (merged into Aero, see aerodrome/aero.md) |
| `venus` | Lending | BNB·ETH·Arb·OP·Base | core-pool.md, isolated-pools.md | Compound-fork; BNB core (Diamond) + isolated pools |
| `wormhole` | Bridge·Messaging | 7 · Robin · Arc | README.md, core.md, token-bridge.md, nft-bridge.md, relayer.md, cctp.md, ntt.md | Wormhole guardian message bus (key = emitter chain + emitter + sequence), Token/NFT Bridge, Relayer/Executor, CCTP integration, NTT; Robinhood has Core, Executor and 7 NTT managers; Arc has Core, Executor, NTT helpers and CCTP v2 with Executor |
| `xyfinance` | Bridge·Aggregator | 7 | core.md | XY Finance yBridge v3, YBridgeVaults, XY Router, legacy XSwapper; idle since Nov 2025 |
| `zerolend` | Lending | ETH·Base | core.md | Aave-V3 fork; of 7 only ETH+Base (primary on L2s off-target); winding down, withdraw-only since 2026-02-17, Pools upgraded 2026-08-26 |
| `zkbridge` | Bridge·Messaging | 7 +Other | lightclient.md, messaging.md | Polyhedra zk light-client message/token bridge |
| `zkswap` | Bridge | ETH | core.md | ZKSwap V1/V2 zkSync-fork rollup escrows (V1 in exodus mode, V2 operator stopped 2024) |
| `zksync_native` | Bridge | ETH +Other (zkSync) | core.md | zkSync Era Elastic-Chain canonical bridge |

---

## 3. Notes

- **Multi-file dirs** carry a `README.md` index — read it first (version→file map + topic0 collisions).
  Single-file dirs (`core.md` / `<slug>.md` / a version file) open directly.
- **"7" never means "literally everywhere"** — open the doc's *Cross-chain summary* for the exact
  per-chain address and absence/decoy notes (several docs flag look-alike tokens on non-deployed chains).
- **Robinhood Chain and Arc decoys.** Many canonical literals (Uniswap, Balancer, UNI and others) hold a small
  fund-recovery forwarder there (~2,109 B or ~1,456 B on Robinhood, ~2,747 B on Arc), placed by the original
  deployer key. Non-empty code is not proof of a deployment — check the doc before you key on `(chain, address)`.
- **Off-target-only protocols** (`agave`, `justlend`, `moola`, `realt_rmm`) have docs but
  are **absent on all 7 target chains** — useful for attribution, not for 7-chain monitoring queries.
- **Shared topic0s across forks** — filter by emitter: `lista` Moolah = Morpho Blue; `kaskad`, `layerbank` V3,
  `spark`, `zerolend` = Aave V3; `fables` pools emit through the Uniswap v4 PoolManager; `archery` = Topaz Slipstream.
- **Wound-down / exploited / legacy** (watch for low activity): `granary`, `lodestar`, `sonne_finance`,
  `uwulend`, `radiant` (key compromise), `euler` V1, `metric` (Metric.exchange), `beamer` (dormant), `nitro` (sunset
  2026-09-30), `zerolend` (withdraw-only), `synapse` FastBridge (dormant), `synthetix` L2 deployments,
  `aerodrome`/`velodrome` legacy generations (since 2026-10-21), `cctp` V1 (paused 2026-12-01),
  `kelp` L2 deposit pools (paused), `polymarket` V1 exchanges (no fills after ~block 88.9M).

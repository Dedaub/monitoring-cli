# Symbiosis Finance — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain, Arc)

**Status:** verified against live RPC on every listed chain and the canonical `symbiosis-finance/core-contracts` + `symbiosis-finance/js-sdk` repos on 2026-06-09. Extended and re-verified on 2026-09-29 against live RPC on all eight chains and `symbiosis-finance/sdk-types` (the SDK config that replaced the archived `js-sdk`): Robinhood Chain (4663), the intents contracts, the new MetaRouter gateway + executor, the BTC-refund `Depository`, the 2026-09 Portal and Synthesis upgrades, and the daily MPC rotation. Re-read on 2026-10-05: the 2026-10-01 Portal/Synthesis/BridgeV2 upgrade on every chain (§9) and the Arc (5042) deployment (§6.1).
**Scope:** the full Symbiosis cross-chain AMM/bridge core — **MetaRouter** + **MetaRouterGateway** + **Portal** + **Synthesis** + **SyntFabric** + **BridgeV2** + **MulticallRouter** — plus the **intents** system (**DepositorySrc**, **DepositoryDst**, **DeadlineUnlocker** / **DirectUnlocker**, the v1 intent **Bridge**), the new **MetaRouterGateway + MetaRouterExecutorDontApprove** pair and the BTC-refund **Depository**, across the eight target chains (ETH 1, Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Optimism 10, Polygon 137, Robinhood Chain 4663) plus Arc (5042, §6.1). Topics/selectors are **chain-agnostic** (keccak of the canonical signature); addresses are **network-specific**. Symbiosis connects ~50 chains in total; counterparty chains outside the eight (zkSync Era, Linea, Scroll, Mantle, TON, Bitcoin, Tron, Solana, Gnosis, …) and the dedicated **Symbiosis hub chain (chainId 13863860)** are noted in §7 — they are findings, not omissions.

Symbiosis is a **lock-and-mint / burn-and-release synthetic-asset bridge with an embedded swap router**. The flow is: a user calls `MetaRouter.metaRoute` on the source chain (optional first swap) → tokens are locked in the **Portal** (`SynthesizeRequest` event) → a relayer network ("Transmitter"/MPC) reads the **BridgeV2** `OracleRequest` event and relays the call → on the manager/hub chain the **Synthesis** mints a synthetic representation (sToken) via **SyntFabric** (`SynthesizeCompleted`) → for the return leg the sToken is burned on Synthesis (`BurnRequest`) and the original token is released from the Portal on the destination chain (`BurnCompleted`). Most "synthetic" mint/burn activity is concentrated on the **Symbiosis hub chain (13863860)**, an off-target Symbiosis-operated chain; on the eight target chains the dominant events are `SynthesizeRequest` (Portal, lock), `BurnCompleted` (Portal, release), and `OracleRequest` (BridgeV2, relay). The link key of a synth route is the source `SynthesizeRequest.id`: it arrives unchanged as `crossChainID` (topic2) of the destination `BurnCompleted` (§10 item 2).

**Intents (a second, solver-based flow; Base, BNB and Arbitrum only).** Source leg: the user calls `DepositorySrc.deposit`. The contract escrows the tokens (ERC-20 `Transfer` user → `DepositorySrc`, or `msg.value` with the token `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`) and emits `IntentLocked` + `ClientIdLog`. Destination leg: a solver calls `DepositoryDst.fill`. The fill unlocker (`DeadlineUnlocker`) pulls the solver's tokens straight to the recipient (`Filled`), and `DepositoryDst` emits `IntentFilled`. Settlement: the solver calls `DepositoryDst.settleBatch` (`SettleBatchRequested`, then `OracleRequest` on the bridge). On the source chain the bridge calls `DepositorySrc.unlockBatch`, which emits `IntentUnlocked` and sends the escrow to the settlement unlocker; the unlocker pays the solver less its volume fee (`Settled`, branch 0). Refund: after the deadline the depositor submits a Refund-branch fill, and settlement returns the full amount to the depositor (`Settled`, branch 1). The link key is `intentId` = `keccak256(abi.encode(depositParams, fillCondition, lockState))`: topic1 of `IntentLocked`, `IntentFilled` and `IntentUnlocked`, and an element of `SettleBatchRequested.intentIds` — on chain on both sides.

**Five deployment facts a monitoring engineer must internalize before indexing:**
1. **Portal, Synthesis, SyntFabric and BridgeV2 are EIP-1967 Transparent proxies** (impl + admin slots both populated). **MetaRouter, MetaRouterGateway and MulticallRouter are immutable** (impl slot empty). Watch `Upgraded(address)` on the four proxies. Every Portal and every Synthesis proxy moved to a new implementation between 2026-06-09 and 2026-09-29, and again (with every BridgeV2) on 2026-10-01 (§9).
2. **Synthesis + SyntFabric only exist on a subset of the eight** — present on **ETH, Base, BNB, Arbitrum**; **NOT deployed on Avalanche, Optimism, Polygon, Robinhood Chain, Arc** (config = `0x0`, confirmed). **Portal + Bridge exist on all eight; the legacy MetaRouter + MetaRouterGateway exist on the seven original chains, and Robinhood Chain uses only the new gateway (fact 5).** A chain with a Portal but no Synthesis is a "depository spoke" — it locks/releases real tokens but never mints synths locally.
3. **Addresses are NOT a single cross-chain vanity.** Symbiosis reuses a small *pool* of addresses across chains because the same deployer EOA hits the same nonce on multiple chains — so e.g. `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` is the **BridgeV2 on ETH, Polygon, Arbitrum, Optimism, Robinhood Chain and Arc**, but an unrelated 1,690-byte contract on Base and an unlisted second BridgeV2 proxy on Avalanche. **Always key on `(chainId, address)` and never assume a literal means the same role on another chain** (§10).
4. **The intents contracts are UUPS proxies (ERC-1967 + ERC-1822, admin slot empty) owned by an EOA, in two generations at the same addresses on Base, BNB and Arbitrum.** v1 (archived `js-sdk`): `DepositorySrc` `0x695EeaeCE7ce4502850B1F6B4f14b97DBA02E840` and `DepositoryDst` `0x4Ac560A3A8FaDd1662CF9439bb1114AbAa3BE547`, which settle through their own intent `Bridge` `0x85700Ed7C30625eD28613d75e85C58EF0056263F`. v2 (current `sdk-types`): `DepositorySrc` `0xDCD0Cb19bbe117648cF138F816d08248AF241694` and `DepositoryDst` `0x54cCE448468c137C05C895aAC9ca769B82e1fE72`, which settle through each chain's **core BridgeV2** (`bridge()` returns the core bridge, and the core bridge lists `DepositoryDst` v2 as a transmitter). Neither generation emitted a log in the pinned 12-hour window (§12).
5. **Robinhood Chain (4663) is a depository spoke that runs only the new MetaRouter.** Portal `0x292fC50e4eB66C3f6514b9E402dBc25961824D62`, BridgeV2 `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E`, MulticallRouter `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8`, and the new gateway `0xcE8f24A58D85eD5c5A6824f7be1F8d4711A0eb4C` as the configured `metaRouter`. No Synthesis, no SyntFabric, no intents contracts. It carried the most `SynthesizeRequest` logs of the eight chains in the pinned window (130).

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified on (of the 8) |
|----------|------|--------|------------------------|
| **MetaRouter** | Entry point. `metaRoute` orchestrates first swap + the cross-chain call. Spawns its own gateway in the constructor. | **No** (immutable, 7,422 B identical on all 7) | ETH, Base, BNB, Avax, Arb, Op, Poly (not Robinhood) |
| **MetaRouterGateway** | Pull-payment escrow; users `approve` *this*, not MetaRouter. `claimTokens` callable only by its MetaRouter. | **No** (immutable, 1,081 B) | the 7 original chains (not Robinhood) |
| **Portal** | Source-chain vault: locks real tokens (`synthesize`/`metaSynthesize`), releases them on return (`unsynthesize`/`metaUnsynthesize`). Emits `SynthesizeRequest` / `BurnCompleted`. | **EIP-1967 Transparent** | all 8 |
| **Synthesis** | Mints/burns synthetic representations (sTokens) via SyntFabric. Emits `SynthesizeCompleted` / `BurnRequest`. | **EIP-1967 Transparent** | ETH, Base, BNB, Arb |
| **SyntFabric** | Registry/minter of sToken ERC-20s; `getSyntRepresentation(real, chainId)`. Emits `RepresentationCreated`. Only `onlySynthesis`. | **EIP-1967 Transparent** | ETH, Base, BNB, Arb |
| **BridgeV2** | Relayer messaging layer. `transmitRequestV2` emits `OracleRequest`; MPC calls `receiveRequestV2` to execute. Gnosis-style MPC + transmitter allowlist. | **EIP-1967 Transparent** | all 8 |
| **MulticallRouter** | Off-chain-encoded multi-hop swap executor used inside meta-routing (`multicall`). | **No** (immutable, 3,558–3,617 B; 2,888 B on Robinhood) | all 8 |
| **MetaRouterGateway (new, "approvable")** | New entry point from `sdk-types` `metaRouters.ts`: users approve **this** and call `metaRoute`. It pulls `approvedTokens[0]` into its executor and calls `executor.metaRoute`. On Robinhood Chain it is the configured `metaRouter`. | **No** (immutable, 1,412 B identical on all 8) | all 8 |
| **MetaRouterExecutorDontApprove** | Executor that the new gateway deploys in its constructor: swaps, final calls, `TransitTokenSent` fallback. Users must not approve it. The Robinhood Portal's `metaRouter()` points to it. | **No** (immutable, 4,747 B identical on all 8) | all 8 |
| **DepositorySrc** (intents) | Source escrow. `deposit` locks the user's tokens (`IntentLocked`). `unlockBatch` (only the bridge) releases them to the settlement unlocker (`IntentUnlocked`). `unlock` is a single release for owner-whitelisted unlockers. | **UUPS** (ERC-1967, admin slot empty) | Base, BNB, Arb |
| **DepositoryDst** (intents) | Destination. A solver calls `fill` (`IntentFilled`); `settleBatch` sends the settlement through the bridge (`SettleBatchRequested` + `OracleRequest`). Holds no user funds; collects a native `relayFee`. | **UUPS** | Base, BNB, Arb |
| **DeadlineUnlocker / DirectUnlocker** (intents) | Pluggable fill + settlement logic. On fill it moves the solver's tokens to the recipient (`Filled`). On settlement it pays the solver less the volume fee, or refunds the depositor after the deadline (`Settled`). | **No** (immutable) | Base, BNB, Arb |
| **intent Bridge (v1)** | Separate relay (`contracts/v3/Bridge.sol`) used by intents v1: same `OracleRequest` / `LogChangeMPC` / `SetTransmitterStatus` topics as BridgeV2. Intents v2 settle through the core BridgeV2 instead. | **UUPS** | Base, BNB, Arb |
| **Depository** (BTC refund) | Older lock-and-unlock escrow with pluggable unlockers (`btcRefundUnlocker`, `branchedUnlocker`, `timedUnlocker`, `timedSwapUnlocker`, `withdrawUnlocker`) from the SDK `depository` config. Emits `DepositLocked` / `DepositUnlocked`. | **No** (EIP-1967 impl slot empty) | ETH, BNB, Avax, Arb |

There is **one generation** of this core (BridgeV2 = "V2" of the bridge; Portal/Synthesis carry `versionRecipient() = "2.0.1"`). Hence a single `core.md`, not per-version files. The four proxies can be upgraded in place — watch `Upgraded`.

**The 2026-09 upgrade.** Between 2026-06-09 and 2026-09-29 every Portal and every Synthesis proxy moved to a new implementation (the new Portal code is byte-identical on all eight chains; previous and current implementations per chain are in §§3–6). The upgrade added two owner-set drain limits. `Portal.reserveFloor(token)`: a release (`unsynthesize`, `metaUnsynthesize`, `revertSynthesize`) reverts with `Symb: reserve floor` when the Portal's balance of the token would fall below it. `Synthesis.mintCap(stoken)`: a mint or a revert-mint reverts with `Symb: mint cap` when the sToken supply would exceed it (0 = no cap). Each setter emits an admin event (`SetReserveFloor`, `SetMintCap`).

**The 2026-10-01 upgrade.** On 2026-10-01 (ETH block 26,097,821, 13:39 UTC) the Portal, Synthesis and BridgeV2 proxies moved to new implementations on all eight chains (SyntFabric unchanged). Sizes now: Portal 11,900 B (one code on all chains, Arc included), Synthesis 18,224 B, BridgeV2 6,903 B. Every documented selector is still present. The `MetaRevertRequest` topic is no longer in the Portal implementation bytecode; every other documented Portal, Synthesis and BridgeV2 topic is.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak-256 on 2026-06-09 from the canonical `core-contracts` sources; the rows added on 2026-09-29 were recomputed the same way from the verified explorer sources and the SDK ABIs named in §12. `SynthesizeRequest`, `OracleRequest`, `SynthesizeCompleted`, `BurnCompleted` additionally confirmed against live `eth_getLogs` (citations inline).

### 1.1 Portal (source-chain vault) — ETH `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8`, all 8 chains

| topic0 | Event |
|--------|-------|
| `0x31325fe0a1a2e6a5b1e41572156ba5b4e94f0fae7e7f63ec21e9b5ce1e4b3eab` | `SynthesizeRequest(bytes32 id, address indexed from, uint256 indexed chainID, address indexed revertableAddress, address to, uint256 amount, address token)` — token locked, cross-chain mint requested. *(1,535 live logs on ETH Portal, 49k-block window ending blk 25279512; 4 topics confirms id non-indexed + 3 indexed.)* |
| `0xaeef64b7687b985665b6620c7fa271b6f051a3fbe2bfc366fb9c964602eb6d26` | `BurnCompleted(bytes32 indexed id, bytes32 indexed crossChainID, address indexed to, uint256 amount, uint256 bridgingFee, address token)` — real token released on `unsynthesize`/`metaUnsynthesize`. *(1,594 live logs on ETH Portal, same window.)* |
| `0x40590cc12db0488520ce425059f83f8caed91bdf98de5ff829dc57c63843161b` | `RevertBurnRequest(bytes32 indexed id, address indexed to)` |
| `0xbd03c66ec5bd3d01fbf22bc794f68ac88b693023b438724019205a4b42aefb20` | `MetaRevertRequest(bytes32 indexed id, address indexed to)` — not in the 2026-10-01 Portal implementation bytecode (it is in the previous one); expect no new logs. |
| `0xefcdf9ea4e65571d2ce9c030c46954e950662df8a7d8bd039fc4417e37b2f88c` | `RevertSynthesizeCompleted(bytes32 indexed id, address indexed to, uint256 amount, uint256 bridgingFee, address token)` |
| `0x5a297b2c9a9f94a0f4e5a796c74ad38e219d1185fccf5f79c18726a830c2b6f5` | `ClientIdLog(bytes32 requestId, bytes32 indexed clientId)` — fires alongside every synth/burn for integrator attribution. **Also emitted by Synthesis** (same topic0) — disambiguate by emitter. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x0a4552f1105808db6a44587c9ef0a7c4064bf620b9d843b514ad7365bd52239a` | `SetWhitelistToken(address token, bool activate)` |
| `0xa6742efd4f410d6fd9688a6cf6a15b6d51121097a263056a3576baaacdc4a9ae` | `SetTokenThreshold(address token, uint256 threshold)` |
| `0xd5c54ab1d37bfef4dd2253d9d73c292e46f5bd8a67ca5920aab4c2e1993178e7` | `SetMetaRouter(address metaRouter)` — **also emitted by Synthesis** (same topic0). |
| `0x6319a2a176ea40732de85182054c69c33324f9bcf05fc1d2a81a2a337341bccb` | `SetReserveFloor(address token, uint256 floor)` — admin (added by the 2026-09 upgrade): owner sets the minimum Portal balance of `token` that a release must leave. No parameter is indexed. 0 logs in the pinned window. |

### 1.2 Synthesis (sToken minter/burner) — ETH `0xD7c3DF25683871d18BC838E4F619126442Dd38B3`; ONLY on ETH/Base/BNB/Arb

| topic0 | Event |
|--------|-------|
| `0x5f00e8f0d61ff1190912879949026c85a81f3f96038c7f4cd868bdfe882e0eeb` | `BurnRequest(bytes32 id, address indexed from, uint256 indexed chainID, address indexed revertableAddress, address to, uint256 amount, address token)` — sToken burned, real-token release requested. **Identical param layout to `SynthesizeRequest` but a DIFFERENT topic0** (the event *name* differs). |
| `0xb22f66d5cb4d958c8beec99f61917824d407a74d4514d8d44cc77247e67a4e5a` | `BurnRequestTON(bytes32 id, address indexed from, uint256 indexed chainID, address indexed revertableAddress, (int8,bytes32) to, uint256 amount, address token)` — TON-destination variant (the `to` is a TON `(workchain, address_hash)` tuple, not an EVM address). |
| `0x1f3f0f3c7b2df480755c6486a132f215e7b2b89fcca0beecd95a9696c71789b6` | `SynthesizeCompleted(bytes32 indexed id, address indexed to, bytes32 indexed crossChainID, uint256 amount, uint256 bridgingFee, address token)` — sToken minted. *(1 live log on BNB Synthesis in a 9k-block window — present-but-low-volume on target chains; the bulk fires on the hub chain 13863860.)* |
| `0xb6f5f7b98cc78a8031c967af163a8c197f470a35df1e326a9038859679e6a184` | `RevertBurnCompleted(bytes32 indexed id, address indexed to, uint256 amount, uint256 bridgingFee, address token)` |
| `0x9bc8099e19706f253ae634ef1a5fb6ef84b4748c2183472905b9b2511cfa8617` | `RevertSynthesizeRequest(bytes32 indexed id, address indexed to)` |
| `0x5a297b2c9a9f94a0f4e5a796c74ad38e219d1185fccf5f79c18726a830c2b6f5` | `ClientIdLog(bytes32 requestId, bytes32 indexed clientId)` (≡ Portal topic0 — disambiguate by emitter) |
| `0xd5c54ab1d37bfef4dd2253d9d73c292e46f5bd8a67ca5920aab4c2e1993178e7` | `SetMetaRouter(address metaRouter)` (≡ Portal topic0) |
| `0xe7258eee4870ba270f25f5a42dd11bfe5a77658959c916807b94b8e9063c3cd0` | `SetFabric(address fabric)` |
| `0xa6742efd4f410d6fd9688a6cf6a15b6d51121097a263056a3576baaacdc4a9ae` | `SetTokenThreshold(address token, uint256 threshold)` (≡ Portal topic0) |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` / `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Paused` / `Unpaused` (≡ Portal topic0s) |
| `0x5f75dc66af14772133e42880c6aed51cbc45fc2b979c2899be3bc5c1e3c3510f` | `SetMintCap(address stoken, uint256 cap)` — admin (added by the 2026-09 upgrade): owner caps the total supply of an sToken (0 = no cap). No parameter is indexed. Pinned window: 1 log each on the ETH, Base and BNB Synthesis (ETH tx `0x6ebf9dc89c5a61003c9e9b68e7a59753760b90bfc88f9fc42c51ac1d05135771`, sent through the owner Safe `0x5112eba9bc2468bb5134cbfbeab9334edae7106a`), 0 on Arbitrum. |

### 1.3 BridgeV2 (relay messaging) — ETH `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E`, all 8 chains

| topic0 | Event |
|--------|-------|
| `0x532dbb6d061eee97ab4370060f60ede10b3dc361cc1214c07ae5e34dd86e6aaf` | `OracleRequest(address bridge, bytes callData, address receiveSide, address oppositeBridge, uint256 chainId)` — **the relayer trigger; emitted on every cross-chain send.** All params non-indexed (no topics beyond topic0). *(1,540 live logs on ETH Bridge, 49k-block window.)* |
| `0xcda32bc39904597666dfa9f9c845714756e1ffffad55b52e0d344673a2198121` | `LogChangeMPC(address indexed oldMPC, address indexed newMPC, uint256 indexed effectiveTime, uint256 chainId)` — **MPC rotation = highest-severity governance signal.** It is also routine: see the note below. |
| `0xeeec8b4e2d317fc608f301f859237a6081b9813f150a3fcfb02fd54276c8be40` | `SetTransmitterStatus(address indexed transmitter, bool status)` — relayer allowlist change. |

**MPC rotation cadence (measured 2026-09-29).** `LogChangeMPC` fired 31 times on the ETH BridgeV2 in the 30 days to 2026-09-28 12:00 UTC (blocks 25859812–26075812), about once a day. In the pinned 12-hour window it fired once on each of the eight chains' BridgeV2. The sampled rotations are `changeMPCSigned` calls sent by the relayer EOA `0x67f9b3e561383493b3f874feae0c53c2cd23851d` (ETH tx `0x79b12b56d15fedd1d599e6d8fd43af1958d9d96147c5d440747c3e618160c21c`: old `0x6a771b7b3583b4ca1fee5097480d2301c1e1560d` → new `0x49d03f9a17ca3bb9b4cc2c851dd722c1af0893eb`, effective 2026-09-28 07:01:59 UTC). A new MPC takes effect only at `newMPCEffectiveTime()`; `mpc()` returns `oldMPC()` before that time and `newMPC()` after it. **`OracleRequest` on the core BridgeV2 also carries the intents v2 settlement**: its `receiveSide` is then `DepositorySrc` v2 `0xDCD0Cb19bbe117648cF138F816d08248AF241694` instead of a Portal or Synthesis.

### 1.4 SyntFabric — ETH `0xbBFb7cb70f84fb6fE1Cb13e42A0B71EFDe769428`; ONLY on ETH/Base/BNB/Arb

| topic0 | Event |
|--------|-------|
| `0xe33e6b41ee9908e3919a380a52ae7059282c36b87adeee0d2ac1b05dfc50be6f` | `RepresentationCreated(address rToken, uint256 chainID, address sToken)` — a new synthetic representation registered (rare; admin/onlySynthesis). |

### 1.5 MetaRouter — the 7 original chains; also the new executor on all 8

| topic0 | Event |
|--------|-------|
| `0x0ac368c799fd87078497a837c3b184349108599d7c108f68710d3321ba416c6f` | `TransitTokenSent(address to, uint256 amount, address token)` — emitted when an `externalCall` swap fails and tokens are returned to `_to` (fallback path). The new `MetaRouterExecutorDontApprove` emits the same topic0 (also from `sendTransitToken`): key on the emitter. Pinned window: ETH 6 (legacy MetaRouter), Base 1, BNB 5, the other five chains 0; the new executors emitted 0. |

### 1.6 Synthetic ERC-20s (SyntERC20) & standard proxy/upgrade constants

| topic0 | Event / value |
|--------|---------------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` — sTokens are ERC-20 (mint = Transfer from `0x0`, burn = Transfer to `0x0`). |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | **`Upgraded(address implementation)`** — watch on Portal / Synthesis / SyntFabric / Bridge proxies. |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` (Transparent-proxy admin handover). |
| `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` | EIP-1967 **implementation slot** (storage, not an event). |
| `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` | EIP-1967 **admin slot** (storage). |

### 1.7 Intents — DepositorySrc (source escrow; UUPS) — Base, BNB, Arbitrum

Emitters: v2 `0xDCD0Cb19bbe117648cF138F816d08248AF241694`, v1 `0x695EeaeCE7ce4502850B1F6B4f14b97DBA02E840` (same addresses on the three chains). Both generations carry every topic below (v1 verified source; v2 checked in the implementation bytecode, §12).

| topic0 | Event |
|--------|-------|
| `0x8b4cbc791dddb376fb89eba475c41896f97673ece5db78a30bb2340d2772cb45` | `IntentLocked(bytes32 indexed intentId, (address token, uint256 amount, address depositor, uint256 quoteTTL, uint256 srcChainId) depositParams, (address fillUnlocker, address settlementUnlocker, bytes condition) fillCondition, (uint256 blockNumber, uint256 timestamp) lockState)` — **source leg**: the tokens are escrowed in `DepositorySrc` in the same transaction (ERC-20 `Transfer` from the caller, or native `msg.value` when `token` = `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`). `condition` ABI-encodes the recipient, destination token, amount, destination chain and deadline for the unlocker. |
| `0x5a297b2c9a9f94a0f4e5a796c74ad38e219d1185fccf5f79c18726a830c2b6f5` | `ClientIdLog(bytes32 intentId, bytes32 indexed clientId)` — status only; same topic0 as the Portal/Synthesis event (key on the emitter). Here word 0 is the `intentId`. `clientId` is an ASCII tag (sampled: `symbiosis-app`, `symbiosis-beta-app`). |
| `0x5ddce0700a1a8691f425337a0d17990cc84e1e8d6d4b148b8ad8ae1a41f11f17` | `IntentUnlocked(bytes32 indexed intentId, address indexed settlementUnlocker, bytes solution, address token, uint256 amount)` — escrow released. After `unlockBatch` (settlement or refund) the tokens go to `settlementUnlocker`, which pays the final party. After the single `unlock` escape hatch, `settlementUnlocker` is the explicit recipient and `solution` is empty. |
| `0x60209f49f531418079ff149eb1d71f100566dcaba03bf5a34930e08111df20c4` | `UnlockerSet(address indexed unlocker, bool enabled)` — admin: whitelist for the single `unlock`. |
| `0xa49730bff544fd0b716395c592e39c6fd2d2481a19b9229b5b240483db95a495` | `BridgeSet(address indexed bridge)` — admin: the bridge that may call `unlockBatch` (also emitted by `DepositoryDst`). |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` — admin (Ownable2Step; all intents proxies and the v1 intent Bridge). |

### 1.8 Intents — DepositoryDst (destination fill + settlement request; UUPS) — Base, BNB, Arbitrum

Emitters: v2 `0x54cCE448468c137C05C895aAC9ca769B82e1fE72`, v1 `0x4Ac560A3A8FaDd1662CF9439bb1114AbAa3BE547`.

| topic0 | Event |
|--------|-------|
| `0x4f02007c5b383d0fb2923b90ac1cc973e61e27f22ce6b7f5c651faa9cdcf21ec` | `IntentFilled(bytes32 indexed intentId, address indexed solver, bytes solution)` — **destination leg**. The event carries no amount: the value moves in the same transaction as an ERC-20 `Transfer` solver → recipient made by the fill unlocker (or native value). |
| `0x0517f5d20eb91a9b5d67025455e2124eade1b76eb1ea5d768c3bcc010135b850` | `SettleBatchRequested(bytes32 indexed requestHash, address indexed solver, bytes32[] intentIds, uint256 srcChainId)` — status only: the settlement message to the source chain; `OracleRequest` from the bridge follows in the same transaction, and the solver pays `relayFee` in native value. |
| `0xa4985dd6c321807ab991746ac3a0237660c5e3aa374e90dd755f5d11099bad3c` | `RelayFeeSet(uint256 oldFee, uint256 newFee)` — admin. |
| `0xa49730bff544fd0b716395c592e39c6fd2d2481a19b9229b5b240483db95a495` | `BridgeSet(address indexed bridge)` — admin (≡ §1.7). |

### 1.9 Intents — DeadlineUnlocker (fill + settlement logic; immutable) — Base, BNB, Arbitrum

Emitters: v2 `0x52a769954A75816F0953D7cEbae1E1e365EB1f33`, v1 `0x4418f8f4826a5d999c7dfE6D16B984e39D2Ed32a`. The v1 `DirectUnlocker` `0xBF6FBa492d87B874ef095e4a3E6BfBFbD2177cc9` emits no events.

| topic0 | Event |
|--------|-------|
| `0x378381bc5e6c9d6ef5ec537a0bab55ecbf51f170e784499f5b4949b03dadcc29` | `Filled(address indexed token, uint256 amount, address indexed recipient, address indexed sender)` — NormalFill on the destination chain: `sender` (the solver) paid `amount` of `token` to `recipient`. |
| `0x2fdfc95b3dadeb6ad1149e0fdade29939418e5b3fa4f2ea6f319399c07af0260` | `Settled(address indexed token, address indexed recipient, uint256 recipientAmount, uint256 feeAmount, uint8 branch)` — source-chain payout of the escrow. `branch` 0 = NormalFill (the solver receives `recipientAmount`, `feeReceiver` receives `feeAmount`); `branch` 1 = Refund (the depositor receives the full amount, no fee). |
| `0xbc746c1b8cf7bef91e22587dc4db83d0e76dd76b6aad2f49bc94c3f0acf832f2` | `VolumeFeeBpsSet(uint256 oldBps, uint256 newBps)` — admin. |
| `0x49bc8f1c292131e71bfca22660d0716072ff2442b58d72840474dd83a390411c` | `FeeReceiverSet(address oldReceiver, address newReceiver)` — admin. |

### 1.10 Intents v1 — intent Bridge (UUPS) — Base, BNB, Arbitrum — `0x85700Ed7C30625eD28613d75e85C58EF0056263F`

Same event topics as the core BridgeV2 (§1.3): `OracleRequest` `0x532dbb6d061eee97ab4370060f60ede10b3dc361cc1214c07ae5e34dd86e6aaf`, `LogChangeMPC` `0xcda32bc39904597666dfa9f9c845714756e1ffffad55b52e0d344673a2198121`, `SetTransmitterStatus` `0xeeec8b4e2d317fc608f301f859237a6081b9813f150a3fcfb02fd54276c8be40`, plus `Upgraded` / `OwnershipTransferred` / `OwnershipTransferStarted`. Key on the emitter: only intents v1 settlements use it.

### 1.11 Depository (BTC-refund escrow; not a proxy) — ETH, BNB, Avalanche, Arbitrum

| topic0 | Event |
|--------|-------|
| `0xf14a4a91301684b37f631329c0732f735c847a9090edcbe4c4362ac603166711` | `DepositLocked(bytes32 indexed depositID, (address token, uint256 amount, uint256 nonce) deposit, (address unlocker, bytes condition) unlocker, (uint256 blockNumber, uint256 timestamp) blockchainState)` — deposit locked under an unlocker condition. |
| `0x7365d0eabb56c257feb8a9eac21febe335838563118e4e5c6041062d0832b223` | `DepositUnlocked(bytes32 indexed depositID)` — status only; the value leaves in the same transaction through the unlocker. |
| `0x50bfd9c0b9815c386500292d8de123643c6c935ffd384a364381b3b11e281e5c` | `SetRouter(address indexed oldRouter, address indexed newRouter)` — admin. |

Pinned window: 0 logs from the four Depository contracts. The event layout comes from the SDK ABI `IDepository.json` (source name `contracts/Depository.sol`) and was checked in the deployed bytecode of all four contracts; the source itself is unverified.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors recomputed locally on 2026-06-09 from the canonical sources. Tuple params expanded to their canonical type lists (struct names erased). Presence verified in the live ETH implementation bytecode where noted.

### 2.1 MetaRouter (immutable entry point)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa11b1198` | `metaRoute((bytes,bytes,address[],address,address,uint256,bool,address,bytes))` | **Primary entry point.** `MetaRouteTransaction{firstSwapCalldata,secondSwapCalldata,approvedTokens,firstDexRouter,secondDexRouter,amount,nativeIn,relayRecipient,otherSideCalldata}`. Present in live impl. |
| `0x3bc78835` | `metaMintSwap((uint256,uint256,bytes32,bytes32,address,uint256,address,address[],address,bytes,address,bytes,uint256))` | Destination-side: mint + 2nd swap + final call. Present in live impl. |
| `0xf5b697a5` | `externalCall(address,uint256,address,bytes,uint256,address)` | Generic swap call w/ fallback → emits `TransitTokenSent`. Present in live impl. |
| `0x732cffe9` | `returnSwap(address,uint256,address,bytes,address,address,bytes)` | Revert-path swap-then-burn. |

### 2.2 MetaRouterGateway (immutable)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9fc314c8` | `claimTokens(address,address,uint256)` | `onlyMetarouter` pull of user tokens. |
| `0xdbec15bb` | `metaRouter()` → `address` | Owning MetaRouter (ETH: returns `0xf621Fb08BBE51aF70e7E0F4EA63496894166Ff7F`, confirmed). |

### 2.3 Portal (vault; proxy)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb1659a3c` | `synthesize(uint256,address,uint256,address,address,address,address,uint256,bytes32)` | Lock token → emit `SynthesizeRequest`. Present in live impl. |
| `0x2816f4db` | `synthesizeNative(uint256,address,address,address,address,uint256,bytes32)` | Wrap native then lock. |
| `0xce654c17` | `metaSynthesize((uint256,uint256,address,address,address,address,address,uint256,address[],address,bytes,address,bytes,uint256,address,bytes32))` | Lock + cross-chain swap intent. Present in live impl. |
| `0x1ebe53ef` | `unsynthesize(uint256,bytes32,bytes32,address,uint256,address)` | `onlyBridge` — release real token, emit `BurnCompleted`. Present in live impl. |
| `0xc23a4c88` | `metaUnsynthesize(uint256,bytes32,bytes32,address,uint256,address,address,bytes,uint256)` | `onlyBridge` — release + final swap. |
| `0xc42a2894` | `revertSynthesize(uint256,bytes32)` | `onlyBridge` — refund a stuck synth. |
| `0x08759e9b` | `revertBurnRequest(uint256,bytes32,address,address,uint256,bytes32)` | User-initiated revert of a burn. |
| `0x6aba5197` | `setReserveFloor(address _token, uint256 _floor)` | owner — emits `SetReserveFloor` (2026-09 upgrade). |
| `0x8215ec72` | `reserveFloor(address)` | view → the floor of a token (0 = no floor). |

### 2.4 Synthesis (sToken minter; proxy; ETH/Base/BNB/Arb only)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa83e754b` | `mintSyntheticToken(uint256,bytes32,bytes32,address,uint256,uint256,address)` | `onlyBridge` — mint sTokens, emit `SynthesizeCompleted`. |
| `0xc29a91bc` | `metaMintSyntheticToken((uint256,uint256,bytes32,bytes32,address,uint256,address,address[],address,bytes,address,bytes,uint256))` | `onlyBridge` — mint + swap + final call. |
| `0xcbef5f2c` | `burnSyntheticToken(uint256,address,uint256,address,address,address,address,uint256,bytes32)` | Burn sToken → emit `BurnRequest`. |
| `0xe66bb550` | `metaBurnSyntheticToken((uint256,uint256,bytes32,address,address,address,bytes,uint256,address,address,address,address,uint256,bytes32))` | Burn + cross-chain release intent. |
| `0x40b1a037` | `revertSynthesizeRequest(uint256,bytes32)` | Refund path. |
| `0xf70519ae` | `revertBurn(uint256,bytes32)` | `onlyBridge` revert. |
| `0xc06abe77` | `setMintCap(address _stoken, uint256 _cap)` | owner — emits `SetMintCap` (2026-09 upgrade). |
| `0x61db4271` | `mintCap(address)` | view → the supply cap of an sToken (0 = no cap). |
| `0x5d176f2f` | `fabric()` → `address` | Owning SyntFabric (ETH: returns `0xbBFb7cb70f84fb6fE1Cb13e42A0B71EFDe769428`, confirmed). |

### 2.5 BridgeV2 (relay; proxy)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6cebc9c2` | `transmitRequestV2(bytes,address,address,uint256)` | `onlyTransmitter` — emit `OracleRequest`. Present in live impl. |
| `0xf7f1baf0` | `receiveRequestV2(bytes,address)` | `onlyMPC` — execute the relayed call (`receiveSide.call`). Present in live impl. |
| `0x84d61c97` | `receiveRequestV2Signed(bytes,address,bytes)` | MPC-signed execution variant. |
| `0x19117d93` | `setTransmitterStatus(address,bool)` | owner — relayer allowlist. |
| `0x5b7b018c` | `changeMPC(address)` | owner/MPC — rotate MPC, emit `LogChangeMPC`. Present in live impl. |
| `0x38899935` | `changeMPCSigned(address _newMPC, bytes signature)` | rotation with an MPC signature; the daily rotations sampled on 2026-09-28 use it (sent by the relayer EOA `0x67f9b3e561383493b3f874feae0c53c2cd23851d`). |
| `0xf75c2664` | `mpc()` → `address` | current MPC (ETH: resolves to `0x5ddc2587b85c664083677654e77a472511fb537c`, confirmed 2026-06-09). **Rotates about daily:** on 2026-09-29 it returns `0x2df0dda69a6ec341d3160b3f73c87b5358800dc5` on all eight chains' BridgeV2. Read it live. |
| `0xc00f8a3d` | `oldMPC()` → `address` | MPC before the pending rotation (ETH 2026-09-29: `0x49d03f9a17ca3bb9b4cc2c851dd722c1af0893eb`). |
| `0x474a245a` | `newMPC()` → `address` | MPC after `newMPCEffectiveTime()` (ETH 2026-09-29: `0x2df0dda69a6ec341d3160b3f73c87b5358800dc5`). |
| `0x405fb4f7` | `newMPCEffectiveTime()` → `uint256` | ETH 2026-09-29: `1790665319` (2026-09-29 07:01:59 UTC). |
| `0x6fac3007` | `isTransmitter(address)` → `bool` | transmitter allowlist; `true` for `DepositoryDst` v2 on the Base, BNB and Arbitrum core bridges. |
| `0x1095b6d7` | `withdrawFee(address token, address to, uint256 amount)` | `onlyOwnerOrAdmin` in `core-contracts` `BridgeV2.sol` (`onlyOwner` in the v1 intent Bridge): moves ERC-20 tokens out of the bridge (each Portal release sends its `stableBridgingFee` to the bridge). Found in the bytecode of the 5,964-B implementation used on ETH, BNB and Robinhood Chain until 2026-10, and in the 6,903-B implementation that replaced it on 2026-10-01; not checked on the older implementations. |

### 2.6 SyntFabric (proxy; ETH/Base/BNB/Arb only)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x506890a0` | `getSyntRepresentation(address,uint256)` → `address` | real token + origin chainId → sToken. |

### 2.7 MulticallRouter (immutable)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1e859a05` | `multicall(uint256,bytes[],address[],address[],uint256[],address)` | Off-chain-encoded multi-hop swap; amounts patched into calldata at per-hop `_offset`. |

### 2.8 Proxy admin surface (Transparent proxies)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5c60da1b` | `implementation()` | callable by admin only (Transparent); read impl from the EIP-1967 slot instead. |
| `0xf851a440` | `admin()` | ProxyAdmin / admin address. |
| `0x3659cfe6` | `upgradeTo(address)` | ProxyAdmin-only → emits `Upgraded`. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | ProxyAdmin-only → emits `Upgraded`. |

### 2.9 New MetaRouterGateway + MetaRouterExecutorDontApprove (immutable; all 8 chains)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa11b1198` | `metaRoute((bytes firstSwapCalldata, bytes secondSwapCalldata, address[] approvedTokens, address firstDexRouter, address secondDexRouter, uint256 amount, bool nativeIn, address relayRecipient, bytes otherSideCalldata) _metarouteTransaction)` | Gateway entry point (payable). Pulls `amount` of `approvedTokens[0]` from the caller into the executor, then calls `executor.metaRoute`. Same selector as the legacy MetaRouter (§2.1); the executor exposes it too. |
| `0xee2ed888` | `metaRouterExecutorDontApprove()` → `address` | Gateway view → its executor (checked on all 8 chains, §§3–6). |
| `0xf5b697a5` | `externalCall(address _token, uint256 _amount, address _receiveSide, bytes _calldata, uint256 _offset, address _to)` | Executor: final call after a Portal release; on failure sends the tokens to `_to` and emits `TransitTokenSent`. |
| `0x62770ff8` | `sendTransitToken(address _token, address _to, uint256 _amount)` | Executor (new): transfer + `TransitTokenSent`. |
| `0x732cffe9` | `returnSwap(address _token, uint256 _amount, address _router, bytes _swapCalldata, address _burnToken, address _synthesis, bytes _burnCalldata)` | Executor: revert-path swap, then burn. |
| `0x3bc78835` | `metaMintSwap((uint256 stableBridgingFee, uint256 amount, bytes32 crossChainID, bytes32 externalID, address tokenReal, uint256 chainID, address to, address[] swapTokens, address secondDexRouter, bytes secondSwapCalldata, address finalReceiveSide, bytes finalCalldata, uint256 finalOffset) _metaMintTransaction)` | Executor: swap + final call after a mint; patches `crossChainID` into the final calldata. |

### 2.10 Intents — DepositorySrc (UUPS)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9e9c7997` | `deposit((address token, uint256 amount, address depositor, uint256 quoteTTL, uint256 srcChainId) depositParams, (address fillUnlocker, address settlementUnlocker, bytes condition) fillCondition, bytes32 clientId)` | **Source leg** (payable). Reverts after `quoteTTL` or when `srcChainId` ≠ `block.chainid`; emits `IntentLocked` + `ClientIdLog`; pulls the tokens from `msg.sender`. |
| `0x77b0173e` | `unlockBatch(((address token, uint256 amount, address depositor, uint256 quoteTTL, uint256 srcChainId) depositParams, (address fillUnlocker, address settlementUnlocker, bytes condition) fillCondition, (uint256 blockNumber, uint256 timestamp) lockState, bytes solution)[] requests)` | Only the configured bridge: releases each escrow to its settlement unlocker; emits `IntentUnlocked` per intent. |
| `0xdb33467b` | `unlock((address token, uint256 amount, address depositor, uint256 quoteTTL, uint256 srcChainId) depositParams, (address fillUnlocker, address settlementUnlocker, bytes condition) fillCondition, (uint256 blockNumber, uint256 timestamp) lockState, address to)` | Only whitelisted `unlockers`: single release to `to` (escape hatch). |
| `0xd8248741` | `intentID((address token, uint256 amount, address depositor, uint256 quoteTTL, uint256 srcChainId) depositParams, (address fillUnlocker, address settlementUnlocker, bytes condition) fillCondition, (uint256 blockNumber, uint256 timestamp) lockState)` | pure → `keccak256(abi.encode(...))`, the link key (also on `DepositoryDst`). |
| `0x3d4dff7b` | `deposits(bytes32 intentId)` → `bool` | view: `true` while locked. |
| `0x172b09f9` | `unlockers(address)` → `bool` | view: `true` for `DeadlineUnlocker` v2 on `DepositorySrc` v2; `false` for `DeadlineUnlocker` v1 on v1. |
| `0xe78cea92` | `bridge()` → `address` | v1 → intent Bridge; v2 → the chain's core BridgeV2 (also on `DepositoryDst`). |
| `0x8dd14802` | `setBridge(address bridge_)` | owner — emits `BridgeSet` (also on `DepositoryDst`). |
| `0xd3fff0f6` | `setUnlocker(address unlocker, bool enabled)` | owner — emits `UnlockerSet`. |

### 2.11 Intents — DepositoryDst (UUPS)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x53b1d925` | `fill((address token, uint256 amount, address depositor, uint256 quoteTTL, uint256 srcChainId) depositParams, (address fillUnlocker, address settlementUnlocker, bytes condition) fillCondition, (uint256 blockNumber, uint256 timestamp) lockState, bytes solution)` | **Destination leg** (payable, solver). Records `keccak256(solution)`, emits `IntentFilled`, calls `fillUnlocker.fill(condition, solution)`. |
| `0xac8baa3a` | `settleBatch(((address token, uint256 amount, address depositor, uint256 quoteTTL, uint256 srcChainId) depositParams, (address fillUnlocker, address settlementUnlocker, bytes condition) fillCondition, (uint256 blockNumber, uint256 timestamp) lockState, bytes solution)[] items, uint256 srcChainId, address srcDepository, address oppositeBridge)` | Payable (`msg.value` ≥ `relayFee`). Emits `SettleBatchRequested`, then `bridge.transmitRequestV2(unlockBatch(items), srcDepository, oppositeBridge, srcChainId)`. |
| `0x20158c44` | `fills(bytes32 intentId)` → `bytes32` | view: `keccak256(solution)` of the fill, zero if unfilled. |
| `0x71d30863` | `relayFee()` → `uint256` | view: v2 on 2026-09-29 = 600000000000000 wei on Base and Arbitrum, 1800000000000000 wei on BNB. |
| `0x98385109` | `setRelayFee(uint256 fee)` | owner — emits `RelayFeeSet`. |
| `0x6b903970` | `withdrawRelayFee(address to, uint256 amount)` | owner — moves collected native relay fees. |

### 2.12 Intents — unlockers (immutable)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5b492b70` | `fill(bytes condition, bytes solution)` | Called by `DepositoryDst.fill`. NormalFill: pulls `amount` from the solver to the recipient before the deadline (`Filled`). Refund branch: no transfer, only valid after the deadline and when the actor is the depositor. Present in `DeadlineUnlocker` v1 and `DirectUnlocker` v1; **absent from the `DeadlineUnlocker` v2 bytecode** (its fill entry is unverified, §12). |
| `0xb8c621d7` | `unlock(bytes, bytes solution, address token, uint256 amount)` | Called by `DepositorySrc.unlockBatch` after it sends the escrow: pays the solver less the volume fee, or refunds the depositor; emits `Settled`. Present in all three unlockers. |
| `0x653b7fb8` | `setVolumeFeeBps(uint256 bps)` | owner (`DeadlineUnlocker`) — emits `VolumeFeeBpsSet`. |
| `0xefdcd974` | `setFeeReceiver(address receiver)` | owner (`DeadlineUnlocker`) — emits `FeeReceiverSet`. |
| `0xb8dc491b` | `sweep(address token, address to)` | **Permissionless** recovery of any token balance left on the unlocker (it holds none between transactions). All three unlockers. |
| `0x78c093cf` | `sweepNative(address to)` | Permissionless recovery of native balance. `DeadlineUnlocker` v1 and v2 only (absent from the `DirectUnlocker` v1 bytecode). |

### 2.13 Depository (BTC-refund escrow)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd2563133` | `lock((address token, uint256 amount, uint256 nonce) deposit, (address unlocker, bytes condition) condition)` | Locks a deposit under an unlocker condition → `DepositLocked`. |
| `0x794997aa` | `unlock((address token, uint256 amount, uint256 nonce) deposit, (address unlocker, bytes condition) condition, (uint256 blockNumber, uint256 timestamp) blockchainState, bytes solution)` | Releases through the unlocker → `DepositUnlocked`. |
| `0xc0d78655` | `setRouter(address _router)` | owner — emits `SetRouter`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09, and again on 2026-09-29. Proxy impls read live from the EIP-1967 slot (2026-10-05 values; earlier values follow "was"). The Portal, Synthesis and BridgeV2 proxies were upgraded together in block 26,097,821 (2026-10-01 13:39 UTC; three `Upgraded` logs). ProxyAdmin (admin slot) = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75` (unchanged on 2026-09-29); its `owner()` is the Safe `0x5112eba9bc2468bb5134cbfbeab9334edae7106a` (171-byte proxy), which also sent the window's `SetMintCap`.

| Role | Address | Impl (if proxy) | One-liner |
|------|---------|-----------------|-----------|
| **MetaRouter** | `0xf621Fb08BBE51aF70e7E0F4EA63496894166Ff7F` | — (immutable, 7,422 B) | Entry point; `metaRoute`. |
| **MetaRouterGateway** | `0xfCEF2Fe72413b65d3F393d278A714caD87512bcd` | — (immutable) | Token-pull escrow; approve here. |
| **Portal** (proxy) | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x4387bd011de13db2e7f22878337e4152d870e89b` (2026-10-01 upgrade; was `0xa0aee4ee…` on 2026-09-29, `0x57dbcb19…` on 2026-06-09) | Vault; emits `SynthesizeRequest`/`BurnCompleted`. |
| **Synthesis** (proxy) | `0xD7c3DF25683871d18BC838E4F619126442Dd38B3` | `0x174c6d73b2fc1a0b434839c49eba6f281587540b` (2026-10-01 upgrade; was `0x83ef4306…` on 2026-09-29, `0x14078ebe…` on 2026-06-09) | sToken minter; emits `BurnRequest`/`SynthesizeCompleted`. |
| **SyntFabric** (proxy) | `0xbBFb7cb70f84fb6fE1Cb13e42A0B71EFDe769428` | `0x71e761c2b3cd3d56ab33a145b3524ca5bdbc5238` | sToken registry. |
| **BridgeV2** (proxy) | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0x1995bb51aabe557ce119249289c37e0bf5282f32` (2026-10-01 upgrade; was `0x20c54cc6…`) | Relay; emits `OracleRequest`. `mpc()` = `0x5ddc2587b85c664083677654e77a472511fb537c` on 2026-06-09, `0x2df0dda69a6ec341d3160b3f73c87b5358800dc5` on 2026-09-29 (rotates about daily). |
| **MulticallRouter** | `0x49d3Fc00f3ACf80FABCb42D7681667B20F60889A` | — (immutable) | Multi-hop swap executor. |
| **MetaRouterGateway (new)** | `0xB4769e9c5bE31199a25ecD1B0C6609183fa72521` | — (immutable, 1,412 B) | New approve-and-call entry point (`sdk-types` `metaRouters.ts`). |
| **MetaRouterExecutorDontApprove** | `0xc227b3a439EE6ae3A22500757125f4dE91d8008E` | — (immutable, 4,747 B) | Executor of the new gateway (`metaRouterExecutorDontApprove()` confirmed). Do not approve. |
| **Depository** (BTC refund) | `0x84DEB7FC54a1F734aEF6DDC0C0F74182BDF941a8` | — (not a proxy, 7,023 B) | `DepositLocked` / `DepositUnlocked`; unlockers in the SDK `depository` config. |

**Intents contracts: not deployed on Ethereum** (`eth_getCode` = `0x`, nonce 0 at all eight intents addresses of §4.1).

---

## 4. Addresses — Base mainnet (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com` on 2026-06-09, and again on 2026-09-29 (impls: 2026-09-29 value, "was" = 2026-06-09 value). **Full deployment incl. Synthesis + Fabric.** ProxyAdmin = `0x1ac4c50080871d7a24dd705de9efe5ff14bc0ea2` (Base-specific, differs from ETH; unchanged on 2026-09-29).

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x691df9C4561d95a4a726313089c8536dd682b946` | — |
| MetaRouterGateway | `0x41Ae964d0F61Bb5F5e253141A462aD6F3b625B92` | — |
| **Portal** | `0xEE981B2459331AD268cc63CE6167b446AF4161f8` | `0x8c199d633199df6dc8d2df66e6fc755d704fa23e` (2026-10; was `0xaf4570fa…` on 2026-09-29, `0x253ddb32…` on 2026-06-09) |
| **Synthesis** | `0x9F6424FE88fBe7785Fa34F0E369F192bF38E7A6e` | `0x863cd8459c9d999a84e9326525b8e72cd2f5e780` (2026-10; was `0xfa807566…` on 2026-09-29, `0x9d74807b…` on 2026-06-09) |
| **SyntFabric** | `0x44487a445a7595446309464A82244B4bD4e325D5` | `0x464c30aebacd4e8928167c567f8920d16f203027` |
| **BridgeV2** | `0x8097f0B9f06C27AF9579F75762F971D745bb222F` | `0x195a07d222a82b50db84e8f47b71504d1e8c5fa2` (2026-10; was `0x88139ad1…`) |
| MulticallRouter | `0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9` | — |
| MetaRouterGateway (new) | `0xa18348e793E77239EC68CAa51b74c5Cdc82c8a9d` | — (immutable, 1,412 B) |
| MetaRouterExecutorDontApprove | `0xCbFD5DcaD860f49D0BD2fDaD78d9d943CAeBedef` | — (immutable, 4,747 B; the gateway's `metaRouterExecutorDontApprove()`) |

> **Collision warning:** Base **SyntFabric** literal `0x44487a445a7595446309464A82244B4bD4e325D5` is the **MetaRouter on BNB**, and Base **MulticallRouter** `0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9` is the **Portal on Arbitrum**. Key on `(chainId, address)`.

No `Depository` (BTC refund) on Base: the SDK config has no `depository` block for Base.

### 4.1 Intents contracts — same addresses on Base, BNB and Arbitrum

Existence-checked with `eth_getCode` on the three chains on 2026-09-29 (same proxy code on the three chains); `eth_getCode` = `0x` with nonce 0 at all eight addresses on ETH, Avalanche, Optimism, Polygon and Robinhood Chain. v2 = `sdk-types` `intentConfig` (current); v1 = archived `js-sdk` `intentConfig`.

| Role | Address | Pattern → implementation | Wiring (read live) |
|------|---------|--------------------------|--------------------|
| **DepositorySrc v2** | `0xDCD0Cb19bbe117648cF138F816d08248AF241694` | UUPS proxy (163 B) → `0x9bf92ce9fd272720ab82331ecafab7fe0363d278` on all three | `bridge()` = the chain's core BridgeV2 (Base `0x8097f0B9f06C27AF9579F75762F971D745bb222F`, BNB `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8`, Arbitrum `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E`) |
| **DepositoryDst v2** | `0x54cCE448468c137C05C895aAC9ca769B82e1fE72` | UUPS proxy → `0x536f874f1d07692591b5579df55f1f6b2c33ac8b` on all three | `bridge()` = the core BridgeV2; `isTransmitter(DepositoryDst v2)` = `true` on each core bridge |
| **DeadlineUnlocker v2** | `0x52a769954A75816F0953D7cEbae1E1e365EB1f33` | immutable (5,040 B) | whitelisted in `DepositorySrc` v2 `unlockers` |
| **DepositorySrc v1** | `0x695EeaeCE7ce4502850B1F6B4f14b97DBA02E840` | UUPS proxy → `0xcd42ede8afc30d40587550fa4c17da3575b3bc7b` on all three | `bridge()` = intent Bridge v1 |
| **DepositoryDst v1** | `0x4Ac560A3A8FaDd1662CF9439bb1114AbAa3BE547` | UUPS proxy → Base `0x8f71e1085408e50115213d65e868d3ff7dfdb56e`, BNB `0x322fb4c148c66b1a7488c9b6e367eba7ece032db`, Arbitrum `0x7cb8467104fd2797a53d6be5b3e635463d202019` | `bridge()` = intent Bridge v1 |
| **DeadlineUnlocker v1** | `0x4418f8f4826a5d999c7dfE6D16B984e39D2Ed32a` | immutable (4,672 B) | fill + settlement unlocker of the sampled v1 intents |
| **DirectUnlocker v1** | `0xBF6FBa492d87B874ef095e4a3E6BfBFbD2177cc9` | immutable (1,740 B) | no events |
| **intent Bridge v1** | `0x85700Ed7C30625eD28613d75e85C58EF0056263F` | UUPS proxy → `0x8617f8a259582dd1baab87a8c3eb51b9cb6f645d` on all three | `mpc()` = `0xd1d950f53e78bb9f434c07f16218f8149f7ce542` (an EOA with an EIP-7702 delegation; the same key filled the sampled v1 intents as solver) |

Upgrade authority (`owner()`, UUPS `_authorizeUpgrade` = `onlyOwner`): v1 contracts and the intent Bridge → EOA `0x13b21d1858b5ab644006bd0d0eb1be7c9a4c0a9b`; v2 contracts → EOA `0x6dcb5e43b05918505f65bf423088af172c32be33` (same on the three chains). Activity: v1 has a few dozen user intents (Base `DepositorySrc` v1: 35 logs, last on 2026-06-02; Arbitrum: 50+ logs, last on 2026-06-15). v2 holds only its setup logs (deployed 2026-06-19 on Base and Arbitrum). Neither generation emitted a log in the pinned window.

---

## 5. Addresses — BNB / Avalanche / Arbitrum / Optimism / Polygon

All verified via `eth_getCode` on the respective publicnode RPC on 2026-06-09, and again on 2026-09-29 (impls: 2026-09-29 value, "was" = 2026-06-09 value). The new gateway + executor of each chain were confirmed with `metaRouterExecutorDontApprove()`.

### 5.1 BNB Smart Chain (chain ID 56) — full deployment incl. Synthesis + Fabric. ProxyAdmin = `0xda8057acb94905eb6025120cb2c38415fd81bfeb`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x44487a445a7595446309464A82244B4bD4e325D5` | — |
| MetaRouterGateway | `0x5c97D726bf5130AE15408cE32bc764e458320D2f` | — |
| **Portal** | `0x5Aa5f7f84eD0E5db0a4a85C3947eA16B53352FD4` | `0x422a0a054eb5a7424d9e3042862546a3f04e3596` (2026-10; was `0xb345171e…` on 2026-09-29, `0x80347bfc…` on 2026-06-09) |
| **Synthesis** | `0x6B1bbd301782FF636601fC594Cd7Bfe74871bfaA` | `0x92114294e42a96c9ef3163da18ee7efdba6cc661` (2026-10; was `0x4e70a309…` on 2026-09-29, `0x755a9672…` on 2026-06-09) |
| **SyntFabric** | `0xc17d768Bf4FdC6f20a4A0d8Be8767840D106D077` | `0xda1c70c902746996a8c989bb07aa6c408ef880d8` |
| **BridgeV2** | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x20ef596709b460e818d5a3d43b06a5b604d6369f` (2026-10; was `0x291a42bd…`) |
| MulticallRouter | `0x44b5d0F16Ad55c4e7113310614745e8771b963bB` | — |
| MetaRouterGateway (new) | `0x851B43189de721dD94AbA767AAd9E6F6d6a95CCA` | — (immutable, 1,412 B) |
| MetaRouterExecutorDontApprove | `0x980447DdcEf79A7499Da4538Da8FC59BAcAD6997` | — (immutable, 4,747 B) |
| Depository (BTC refund) | `0x1fb3b385ad2BfC7B28D65863bAEc04094895B813` | — (not a proxy, 5,049 B) |
| Intents contracts | the shared addresses of §4.1 | v2 settles through this chain's BridgeV2 `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` |

> **Collision:** BNB **BridgeV2** literal `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` is the **Portal on ETH and Polygon**. Same literal, different role per chain.

### 5.2 Arbitrum One (chain ID 42161) — full deployment incl. Synthesis + Fabric. ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75` (shared with ETH).

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0xf7e96217347667064DEE8f20DB747B1C7df45DDe` | — |
| MetaRouterGateway | `0x80ddDDa846e779cceE463bDC0BCc2Ae296feDaF9` | — |
| **Portal** | `0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9` | `0xd1a1ab893365d5c124d73b6001d6dc01487892fb` (2026-10; was `0xf818d262…` on 2026-09-29, `0x2e04409f…` on 2026-06-09) |
| **Synthesis** | `0x326adbE46D7E6C1B3927e9309B96DF478bda6D16` | `0x851b43189de721dd94aba767aad9e6f6d6a95cca` (2026-10; was `0x7879b304…` on 2026-09-29, `0x3941870e…` on 2026-06-09; the new literal is the BNB new-gateway address — literal reuse) |
| **SyntFabric** | `0x2eE9559387b806E88fd46b9DA160D64A29CE7Da0` | `0xf621fb08bbe51af70e7e0f4ea63496894166ff7f` |
| **BridgeV2** | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0x566e412387ae3fab8b5aa3a77178b120bcff5af8` (2026-10; was `0xff9b21c3…`) |
| MulticallRouter | `0xda8057acB94905eb6025120cB2c38415Fd81BfEB` | — |
| MetaRouterGateway (new) | `0x3743c756b64ECd0770f1d4f47696A73d2A46dcbe` | — (immutable, 1,412 B) |
| MetaRouterExecutorDontApprove | `0xf37E321e1c275d249B7A9c825aE802A9f464Eb94` | — (immutable, 4,747 B) |
| Depository (BTC refund) | `0x84b10469dB07446D5fc7156aeFdd6B7117108A73` | — (not a proxy, 5,049 B) |
| Intents contracts | the shared addresses of §4.1 | v2 settles through this chain's BridgeV2 `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` |

> Note Arbitrum **SyntFabric impl** `0xf621fb08bbe51af70e7e0f4ea63496894166ff7f` is the **MetaRouter literal on ETH** — coincidental address reuse, not a logical link.

### 5.3 Avalanche C-Chain (chain ID 43114) — depository spoke; **NO Synthesis, NO SyntFabric** (`0x0` in config, confirmed). ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x6F0f6393e45fE0E7215906B6f9cfeFf53EA139cf` | — |
| MetaRouterGateway | `0x4cfA66497Fa84D739a0f785FBcEe9196f1C64e4a` | — |
| **Portal** | `0xE75C7E85FE6ADd07077467064aD15847E6ba9877` | `0xa385b1436fd2a6a1c6865e22c522a1aa40cadcc6` (2026-10; was `0xbd37c823…` on 2026-09-29, `0x8dc3151d…` on 2026-06-09) |
| **Synthesis** | — | **NOT DEPLOYED** |
| **SyntFabric** | — | **NOT DEPLOYED** |
| **BridgeV2** | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | `0x691df9c4561d95a4a726313089c8536dd682b946` (2026-10; was `0x7057ab3f…`; the new literal is the Base MetaRouter address — literal reuse) |
| MulticallRouter | `0xDc9a6a26209A450caC415fb78487e907c660cf6a` | — |
| MetaRouterGateway (new) | `0xfeC09BE39F82b13471D2e0E7d72e6ee589c631c6` | — (immutable, 1,412 B) |
| MetaRouterExecutorDontApprove | `0x4494b8cBC69c794d82Bd2d820A6ff6f62D7D841A` | — (immutable, 4,747 B) |
| Depository (BTC refund) | `0xE7eb022E21e85200E7b0dAEBF3757764e83F5c4e` | — (not a proxy, 5,326 B) |
| Intents contracts | — | **NOT DEPLOYED** (`eth_getCode` = `0x` at all eight §4.1 addresses) |

> **Unlisted second BridgeV2 proxy on Avalanche:** `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` also carries a BridgeV2 proxy here (2,141 B, implementation `0x7057ab3fb2bee9c18e0cde4240de4ff7f159e365`), but its `mpc()` is `0xdcb7d65b15436ce9b608864accff75871c6556fc`, not the MPC of the other eight bridges, the SDK config does not list it, and it emitted 0 logs in the pinned window. The Avalanche bridge is `0x292fC50e4eB66C3f6514b9E402dBc25961824D62`.

> **Role correction:** `0xE75C7E85FE6ADd07077467064aD15847E6ba9877`, sometimes labelled the Avalanche MetaRouter, is, in the live SDK config and on-chain, the **Avalanche Portal** — not the MetaRouter. The Avalanche MetaRouter is `0x6F0f6393e45fE0E7215906B6f9cfeFf53EA139cf`. Verified by `eth_getCode` + config role mapping.

### 5.4 Optimism (chain ID 10) — depository spoke; **NO Synthesis, NO SyntFabric**. ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x0f91052dc5B4baE53d0FeA5DAe561A117268f5d2` | — |
| MetaRouterGateway | `0x200a0fe876421DC49A26508e3Efd0a1008fD12B5` | — |
| **Portal** | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | `0x1dcfbc3fa01b2a86bc3a3f43479cce9e8d438adc` (2026-10; was `0x8097f0b9…` on 2026-09-29 — the Base BridgeV2 proxy literal — and `0x7b4e28e7…` on 2026-06-09) |
| **Synthesis** / **SyntFabric** | — | **NOT DEPLOYED** |
| **BridgeV2** | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0x17efc1d70ea32eb04c6979c6500d12eee9e3dcbd` (2026-10; was `0x7057ab3f…`) |
| MulticallRouter | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | — |
| MetaRouterGateway (new) | `0xA9A96Ee51dD54B9f51d46b1fbD2A19c1295Ec75b` | — (immutable, 1,412 B) |
| MetaRouterExecutorDontApprove | `0x356d322BF762d4022D8c241428770565f236c2EA` | — (immutable, 4,747 B) |
| Intents contracts / Depository | — | **NOT DEPLOYED** (no code at the §4.1 addresses; no `depository` block in the config) |

> **Collision:** OP **Portal** `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` is the **BridgeV2 on Avalanche**; OP **MulticallRouter** `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` is the **Portal on ETH/Poly and the Bridge on BNB**. Always key on `(chainId, role)`.

### 5.5 Polygon PoS (chain ID 137) — depository spoke; **NO Synthesis, NO SyntFabric**. ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0xa260E3732593E4EcF9DdC144fD6C4c5fe7077978` | — |
| MetaRouterGateway | `0xAb83653fd41511D638b69229afBf998Eb9B0F30c` | — |
| **Portal** | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x628613064b1902a1a422825cf11b687c6f17961e` (2026-10; was `0x40d9fa40…` on 2026-09-29, `0x35d39bb2…` on 2026-06-09) |
| **Synthesis** / **SyntFabric** | — | **NOT DEPLOYED** |
| **BridgeV2** | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0xaf4570fadd2ab163c809e4ba483d032b31475e1a` (2026-10; was `0x7057ab3f…`; the new literal is the 2026-09-29 Base Portal impl address — literal reuse) |
| MulticallRouter | `0xc5B61b9abC3C6229065cAD0e961aF585C5E0135c` | — |
| MetaRouterGateway (new) | `0x2eE9559387b806E88fd46b9DA160D64A29CE7Da0` | — (immutable, 1,412 B; the same literal is the SyntFabric proxy on Arbitrum) |
| MetaRouterExecutorDontApprove | `0x7a73a0bA4919778C5442f026bd01795b4f2A4cB8` | — (immutable, 4,747 B) |
| Intents contracts / Depository | — | **NOT DEPLOYED** (no code at the §4.1 addresses; no `depository` block in the config) |

> Until 2026-10, Avalanche, Optimism and Polygon shared the BridgeV2 implementation `0x7057ab3fb2bee9c18e0cde4240de4ff7f159e365`. Since the 2026-10 upgrade every listed BridgeV2 runs its own implementation literal with one shared 6,903-B code. On Optimism and Polygon the Bridge proxy literal is also identical (`0x5523985926Aa12BA58DC5Ad00DDca99678D7227E`). The unlisted Avalanche proxy at `0x5523…227E` still points at `0x7057ab3f…`.

---

## 6. Addresses — Robinhood Chain (chain ID 4663)

Roles from the official `symbiosis-finance/sdk-types` config (`ChainId.ROBINHOOD_MAINNET = 4663` in `mainnet.ts`, added 2026-09, and `metaRouters.ts`). Existence-checked with `eth_getCode` on `https://rpc.mainnet.chain.robinhood.com` on 2026-09-29; implementations read from the EIP-1967 slot. **Depository spoke on the new MetaRouter only.** ProxyAdmin (admin slot of Portal and BridgeV2) = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`, the same literal as on ETH/Arb/Avax/Op/Poly. On Robinhood its `owner()`, and `owner()` of the Portal and the BridgeV2, is `0x0605963420c4e8566fcef2cf65dcd575662bf53d` (a 171-byte proxy, the size of a Safe proxy).

| Role | Address | Impl / code | Notes |
|------|---------|-------------|-------|
| **Portal** (proxy) | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | `0xf8504d2ca2f0bbad9d36927e3d32e278abadada0` (2026-10; 11,900 B, byte-identical to the Portal implementation on the other chains; carries `setReserveFloor`; was `0xf39d9a9a…` on 2026-09-29) | `bridge()` = the BridgeV2 below; `metaRouter()` = the executor below. Pinned window: `SynthesizeRequest` 130, `BurnCompleted` 32. |
| **BridgeV2** (proxy) | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0x6148fd6c649866596c3d8a971fc313e5ece84882` (2026-10; 6,903 B, byte-identical to the ETH BridgeV2 implementation; was `0x7057ab3f…` on 2026-09-29) | Pinned window: `OracleRequest` 130, `LogChangeMPC` 1. `mpc()` on 2026-09-29 = `0x2df0dda69a6ec341d3160b3f73c87b5358800dc5`. |
| **MetaRouter** = **MetaRouterGateway (new)** | `0xcE8f24A58D85eD5c5A6824f7be1F8d4711A0eb4C` | immutable, 1,412 B (identical to the new gateway on the other seven chains) | Users approve and call this (`metaRoute`). `metaRouterExecutorDontApprove()` = the executor below. |
| **MetaRouterExecutorDontApprove** | `0xAdB2d3b711Bb8d8Ea92ff70292c466140432c278` | immutable, 4,747 B | Receives the user's tokens from the gateway and forwards them to the Portal; the Portal's final calls go to it. Do not approve. |
| **MulticallRouter** | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | immutable, 2,888 B (a different build from the 3,558/3,617-B routers; same `multicall` selector `0x1e859a05`) | |
| Synthesis / SyntFabric | — | **NOT DEPLOYED** (`0x0` in the config) | Robinhood routes go through the hub chain 13863860 like the other spokes. |
| Legacy MetaRouter / MetaRouterGateway | — | **NOT DEPLOYED** (the Optimism-layout literals `0x0f91052dc5B4baE53d0FeA5DAe561A117268f5d2` / `0x200a0fe876421DC49A26508e3Efd0a1008fD12B5` have no code here) | |
| Intents contracts / Depository | — | **NOT DEPLOYED** (`eth_getCode` = `0x`, nonce 0 at all eight §4.1 addresses; no `intentConfig` or `depository` block for Robinhood) | |

Sampled value movement: the deposit tx `0x558d6b6359e884846f414606e545b90cdcdbd52069256e8b92fd6ca1b3b1edc1` moves USDG (`0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168`, the Robinhood stable of the config) from the user through an aggregator into the executor and then into the Portal; the Portal emits `SynthesizeRequest` (`chainID` = 13863860) and `ClientIdLog` (`clientId` = `lifi`), and the BridgeV2 emits `OracleRequest`. The payout tx `0x3269380616f6cc47e75b25d74b0c5ad6e25a8aae5270590b58b3830f1c9153e9` is a `receiveRequestV2Signed` call by the relayer `0x67f9b3e561383493b3f874feae0c53c2cd23851d`: the Portal sends the fee in WETH (`0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73`) to the BridgeV2 and the rest to the executor, which routes it to the recipient, and the Portal emits `BurnCompleted`.

> **Collision:** on Robinhood `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` is the Portal (as on Optimism) but it is the BridgeV2 on Avalanche. `0xcE8f24A58D85eD5c5A6824f7be1F8d4711A0eb4C` and `0xAdB2d3b711Bb8d8Ea92ff70292c466140432c278` hold an older MetaRouter (6,784 or 7,365 B) and a 1,081-B gateway on ETH, Arbitrum, Avalanche, Optimism and Polygon, which the SDK config does not list for those chains. `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` is the MulticallRouter here and on Optimism, the Portal on ETH/Polygon and the BridgeV2 on BNB.

### 6.1 Arc (5042)

Roles from `symbiosis-finance/sdk-types` (`ChainId.ARC_MAINNET` block in `mainnet.ts`, last change 2026-10-01; `metaRouters.ts`). Existence-checked with `eth_getCode` on `https://rpc.mainnet.arc.io` on 2026-10-05; implementations and admin read from the EIP-1967 slots. **Depository spoke on the new MetaRouter only**, the same layout as Robinhood Chain. ProxyAdmin (admin slot of Portal and BridgeV2) = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`; its `owner()`, and `owner()` of the Portal and the BridgeV2, is `0x64c44f682a1014410c864bd708a7ab1b67eec0ea` (171-byte proxy).

| Role | Address | Impl / code | Notes |
|------|---------|-------------|-------|
| **Portal** (proxy) | `0xE75C7E85FE6ADd07077467064aD15847E6ba9877` | `0xf39d9a9abb98593ceac395d7a37c572da48fcfd5` (11,900 B, byte-identical to the 2026-10 Portal implementation on the other chains) | `bridge()` = the BridgeV2 below; `metaRouter()` = the executor below. Same literal as the Avalanche Portal. |
| **BridgeV2** (proxy) | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0xf85fc807d05d3ab2309364226970aac57b4e1ea4` (6,903 B, byte-identical to the 2026-10 ETH BridgeV2 implementation; the literal is the hub-chain Fabric address) | `mpc()` on 2026-10-05 = `0x483fce549a3a753128db5cbbce393ef7371e3443` (the same as ETH that day). |
| **MetaRouter** = **MetaRouterGateway (new)** | `0xcE8f24A58D85eD5c5A6824f7be1F8d4711A0eb4C` | immutable, 1,412 B | `metaRouterExecutorDontApprove()` = the executor below. |
| **MetaRouterExecutorDontApprove** | `0xAdB2d3b711Bb8d8Ea92ff70292c466140432c278` | immutable, 4,747 B | Do not approve. |
| **MulticallRouter** | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | immutable, 2,888 B | The same literal is the Portal on Optimism/Robinhood and the BridgeV2 on Avalanche. |
| Pauser | `0x3e4aDcf98E77F6d8022639F7135BE4A3850033ED` | 4,804 B | `pauser` in the config. |
| Synthesis / SyntFabric | — | **NOT DEPLOYED** (`0x0` in the config) | |
| Stable | USDC `0x3600000000000000000000000000000000000000` (6 decimals) | | Arc's native gas token, ERC-20 interface. |

Activity: low. Over 72,000 Arc blocks (about 10 h) to block 24,377,764 the Portal emitted no log and the BridgeV2 emitted one `LogChangeMPC`.

---

## 7. Counterparty chains outside the eight (findings, not omissions)

The SDK config (`js-sdk/src/crosschain/config/mainnet.ts`) defines ~50 mainnet chains. Beyond the eight targets, Symbiosis cores were verified present in config on (selected, by role):

- **Synthesis-bearing manager chains (off-target):** **Symbiosis hub `13863860`** (the canonical synth-minting chain: Synthesis `0x45CFd6FB7999328F189aaD2739Fba4Be6C45E5bf`, Bridge `0x1a039cE63AE35a67Bf0E9F6DbFaE969639D59eC8`, Fabric `0xf85FC807D05d3Ab2309364226970aAc57b4e1ea4`, **no Portal** — it is a pure mint/burn hub), **Telos `40`**, **zkSync Era `324`**, **Bahamut `5165`**, **Rootstock `30`**, **ZetaChain `7000`**, **Citrea `4114`**, **Quai `9`**.
- **Portal-only spokes (off-target):** Kava `2222`, Boba `288`, Arbitrum Nova `42170`, Polygon zkEVM `1101`, Linea `59144`, Mantle `5000`, Scroll `534352`, Manta `169`, Metis `1088`, Mode `34443`, Blast `81457`, Merlin `4200`, zkLink `810180`, Core `1116`, Taiko `167000`, Sei `1329`, Cronos `25`/`388`, Fraxtal `252`, Gravity `1625`, BSquared `223`, Morph `2818`, Goat `2345`, Sonic `146`, Abstract `2741`, **Gnosis `100`**, Berachain `80094`, **Unichain `130`**, Soneium `1868`, opBNB `204`, Hyperliquid `999`, Katana `747474`, ApeChain `33139`, Plasma `9745`, Monad `143`, Tempo `4217`.
- **Non-EVM counterparties** (bridged via dedicated adapters, not the EVM Portal): **Bitcoin** (chainId `3652501241`, symBTC pool), **TON** (`85918`, `TonBridge` + `BurnRequestTON`), **Tron** (`728126428`), **Solana** (`5426`).
- **New in `sdk-types` `mainnet.ts` (2026-09):** Robinhood Chain `4663` (a target chain, §6), Stable `988` (on the same new gateway/executor literals as Robinhood), Arc `5042` (deployed; see §6.1), Lighter `99990002` and Hyperliquid perp `99990001`.

These are **not** deployed on the eight target chains in the documented role — they are the bridge's remote endpoints. A `SynthesizeRequest.chainID` on a target-chain Portal frequently points at one of these off-target chains (commonly the hub `13863860`).

---

## 8. Cross-chain summary

| Chain | ID | MetaRouter | Gateway | Portal | Synthesis | SyntFabric | BridgeV2 | MulticallRouter | New gateway + executor | Intents (v1 + v2) | Depository (BTC) |
|-------|----|-----------|---------|--------|-----------|-----------|----------|-----------------|------------------------|-------------------|------------------|
| Ethereum | 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Base | 8453 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| BNB | 56 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Arbitrum | 42161 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Avalanche | 43114 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ |
| Optimism | 10 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Polygon | 137 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Robinhood Chain | 4663 | ✗ (the new gateway is the `metaRouter`) | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Arc | 5042 | ✗ (the new gateway is the `metaRouter`) | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ |

**Synthesis + SyntFabric live on ETH/Base/BNB/Arb only; the other four are depository spokes (Portal + Bridge + a MetaRouter only).** No single vanity address: the same literals recur in *different roles* across chains (see collision warnings in §§4–6).

Portal (lock/release escrow) and BridgeV2 (`OracleRequest` emitter) per chain:

| Chain | ID | Portal | BridgeV2 |
|-------|----|--------|----------|
| Ethereum | 1 | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` |
| Base | 8453 | `0xEE981B2459331AD268cc63CE6167b446AF4161f8` | `0x8097f0B9f06C27AF9579F75762F971D745bb222F` |
| BNB | 56 | `0x5Aa5f7f84eD0E5db0a4a85C3947eA16B53352FD4` | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` |
| Arbitrum | 42161 | `0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9` | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` |
| Avalanche | 43114 | `0xE75C7E85FE6ADd07077467064aD15847E6ba9877` | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` |
| Optimism | 10 | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` |
| Polygon | 137 | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` |
| Robinhood Chain | 4663 | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` |
| Arc | 5042 | `0xE75C7E85FE6ADd07077467064aD15847E6ba9877` | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` |

---

## 9. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Portal** | EIP-1967 **Transparent** | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` set + admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` set (~2,112–2,141 B proxy) | ProxyAdmin (per-chain, §§3–6) → `Upgraded` |
| **Synthesis** | EIP-1967 **Transparent** | impl + admin slots set | ProxyAdmin → `Upgraded` |
| **SyntFabric** | EIP-1967 **Transparent** | impl + admin slots set | ProxyAdmin → `Upgraded` |
| **BridgeV2** | EIP-1967 **Transparent** | impl + admin slots set; impl exposes `mpc()`/`changeMPC` | ProxyAdmin (upgrade) + MPC (operational) → `Upgraded` / `LogChangeMPC` |
| **MetaRouter** | **Immutable** (no proxy) | impl slot returns `0x0`; full 7,422 B runtime on every chain | none |
| **MetaRouterGateway** | **Immutable** | impl slot `0x0`; 1,081 B; deployed by MetaRouter's constructor | none |
| **MulticallRouter** | **Immutable** | impl slot `0x0`; 3,558–3,617 B (2,888 B on Robinhood) | none |
| **MetaRouterGateway (new) / MetaRouterExecutorDontApprove** | **Immutable** | impl slot `0x0`; 1,412 B / 4,747 B, identical code on all 8; the executor is created by the gateway's constructor | none |
| **DepositorySrc / DepositoryDst / intent Bridge (v1)** (intents) | **UUPS** (ERC-1967 + ERC-1822) | 163-B ERC-1967 proxy; impl slot set, admin slot empty; impl exposes `upgradeToAndCall` `0x4f1ef286` + `proxiableUUID` `0x52d1902d` | `owner()` (`onlyOwner` `_authorizeUpgrade`, Ownable2Step): v1 → EOA `0x13b21d1858b5ab644006bd0d0eb1be7c9a4c0a9b`, v2 → EOA `0x6dcb5e43b05918505f65bf423088af172c32be33` → `Upgraded` |
| **DeadlineUnlocker / DirectUnlocker** (intents) | **Immutable** | impl slot `0x0`; 1,740–5,040 B | none (owner sets only fee parameters) |
| **Depository** (BTC refund) | Not a proxy | impl slot `0x0`; 5,049–7,023 B | owner (`setRouter`) |

EIP-1967 implementation slot read live (`eth_getStorageAt`) per chain — current impls listed in §§3–6.1. **Every Portal and every Synthesis implementation changed between 2026-06-09 and 2026-09-29** (previous value kept as "was" in §§3–5). That upgrade added `SetReserveFloor` / `SetMintCap` (§0). **A second upgrade on 2026-10-01 replaced every Portal, Synthesis and BridgeV2 implementation again** (§0; current values in §§3–6.1): the Portal implementations share one code (11,900 B), the BridgeV2 implementations one code (6,903 B). SyntFabric implementations were unchanged on 2026-10-05. **ProxyAdmin (admin slot) clusters into three values:** `0x1da522b35363c1eda4833bc121c8f3c67b2caa75` (ETH, Avax, Arb, Op, Poly, Robinhood Chain and Arc), `0x1ac4c50080871d7a24dd705de9efe5ff14bc0ea2` (Base), `0xda8057acb94905eb6025120cb2c38415fd81bfeb` (BNB). Its `owner()` is the Safe `0x5112eba9bc2468bb5134cbfbeab9334edae7106a` on ETH and the 171-byte contract `0x0605963420c4e8566fcef2cf65dcd575662bf53d` on Robinhood Chain. **MetaRouter / MetaRouterGateway / MulticallRouter are confirmed NOT proxies** — `eth_getStorageAt` at the impl slot returns all-zero on every chain, and they carry full multi-KB runtime bytecode (an immutable would). The upgradeable surface to monitor is the four Transparent proxies plus the three intents UUPS proxies, via the `Upgraded(address)` topic `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`.

---

## 10. Detection invariants & gotchas

1. **`SynthesizeRequest` (Portal) and `BurnRequest` (Synthesis) share the identical parameter layout `(bytes32,address,uint256,address,address,uint256,address)` but have DIFFERENT topic0s** (`0x31325fe0a1a2e6a5b1e41572156ba5b4e94f0fae7e7f63ec21e9b5ce1e4b3eab` vs `0x5f00e8f0d61ff1190912879949026c85a81f3f96038c7f4cd868bdfe882e0eeb`) because the event *names* differ. Don't conflate them. Both carry `id` non-indexed + 3 indexed (`from`, `chainID`, `revertableAddress`) → 4 log topics.
2. **The cross-chain key is the source `SynthesizeRequest.id` (bytes32, data word 0), and it arrives as `crossChainID`, not as `id`.** The Portal source (`sendSynthesizeRequest`) sets `id` = `internalID` = `keccak256(abi.encodePacked(portal, requestCount, block.chainid))` and passes it on as `crossChainID`. Join it to the hub `SynthesizeCompleted.crossChainID` (topic3) and to the destination `BurnCompleted.crossChainID` (**topic2**). `SynthesizeCompleted.id` and `BurnCompleted.id` (topic1) are different ids (the `externalID` of each hop): do not join on them. Verified 2026-09-29: ETH `SynthesizeRequest` tx `0x5a7c239ec463d08d664bb54c4b0dcd5b20395b110210a51ef132f7f973a6456d` (`id` `0x797f65344af8503a0954ece36f6ab9ef6a1b87c81e72f1b82ac82b8e4c9780e3`) → BNB `BurnCompleted` tx `0xf5fcae0b80b328242804415e02316433b5adfb5968759d2a5af83b574de99c6a` with that value as topic2 and topic1 `0x8e8a8ef0dff61311a084993d84bf6d82935190761bef77a694c40210485ff154`. (The 2026-06-09 text of this item joined on `SynthesizeCompleted.id` / `BurnCompleted.id`; the source and this pair show that is wrong.)
3. **`OracleRequest` (BridgeV2) is the relayer fan-out and fires on EVERY cross-chain send** — it's the most reliable "a bridge tx happened here" signal. All params are non-indexed (only topic0), so you must ABI-decode the data to get `receiveSide`/`oppositeBridge`/`chainId`.
4. **The real user is `from` in `SynthesizeRequest`/`BurnRequest`, NOT `tx.origin`.** Most flows arrive through MetaRouter/MetaRouterGateway, so `tx.to` is the router and `msg.sender` to the Portal is the MetaRouter. Attribute to the event's `from`/`to`, and use `ClientIdLog.clientId` for integrator attribution.
5. **Synthesis + SyntFabric do NOT exist on Avalanche, Optimism, Polygon, Robinhood Chain.** If you scan for `BurnRequest`/`SynthesizeCompleted` on those four you'll find nothing — that's correct, not a missing feed. Those chains only lock/release real tokens via the Portal.
6. **No single vanity address — heavy literal reuse across chains in *different roles*.** Examples: `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` = Bridge on ETH/Poly/Arb/Op/Robinhood/Arc, an unlisted second BridgeV2 proxy on Avax, an unrelated contract on Base; `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` = Portal on ETH/Poly, Bridge on BNB, MulticallRouter on OP and Robinhood; `0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9` = Portal on Arb, MulticallRouter on Base; `0x44487a445a7595446309464A82244B4bD4e325D5` = MetaRouter on BNB, SyntFabric on Base; `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` = Bridge on Avax, Portal on OP and Robinhood; `0x2eE9559387b806E88fd46b9DA160D64A29CE7Da0` = SyntFabric on Arb, new gateway on Polygon; `0xcE8f24A58D85eD5c5A6824f7be1F8d4711A0eb4C` = new gateway (the `metaRouter`) on Robinhood, an unlisted older MetaRouter on ETH/Arb/Avax/Op/Poly. **Always key on `(chainId, address, role)`.**
7. **`mpc()` (BridgeV2) is the single trusted relayer key.** A `LogChangeMPC` or `SetTransmitterStatus` event is a top-severity governance/security signal — a compromised MPC can mint/release arbitrarily. ETH `mpc()` was `0x5ddc2587b85c664083677654e77a472511fb537c` on 2026-06-09 and `0x2df0dda69a6ec341d3160b3f73c87b5358800dc5` on 2026-09-29 (same on all eight chains). **The MPC rotates about daily** (31 `LogChangeMPC` on the ETH bridge in 30 days; one on each chain in the pinned window, sent via `changeMPCSigned` by the relayer EOA `0x67f9b3e561383493b3f874feae0c53c2cd23851d`). A rotation alone is therefore routine: key an alert on a rotation from a different sender or outside the daily pattern, on `SetTransmitterStatus`, and on `Upgraded` / ProxyAdmin changes. Never hard-code the MPC; read `mpc()` live.
8. **`BurnRequestTON` encodes the destination as a TON `(int8 workchain, bytes32 address_hash)` tuple, not an EVM address** — different topic0 (`0xb22f66d5cb4d958c8beec99f61917824d407a74d4514d8d44cc77247e67a4e5a`) and a non-address `to`. Only fires where TON is a destination.
9. **sTokens are plain ERC-20s** minted/burned by SyntFabric: a mint is `Transfer(0x0 → user)`, a burn is `Transfer(user → 0x0)` on the sToken contract. Most live on the off-target hub chain `13863860`; on target chains they appear only where Synthesis exists (ETH/Base/BNB/Arb).
10. **`stableBridgingFee` is skimmed to the Bridge inside `unsynthesize`/`mint`** — the user receives `amount - stableBridgingFee`. `BurnCompleted.amount` / `SynthesizeCompleted.amount` are already net of fee; `bridgingFee` is a separate field.
11. **`metaUnsynthesize` with empty `_finalCalldata` emits `BurnCompleted` with `to = address(this)` (the Portal)** rather than the end user — the swap-and-forward path. Don't misattribute that to the Portal as a recipient.
12. **`metaSynthesize`/`metaBurnSyntheticToken`/`metaMintSyntheticToken` take a single struct argument** — the selectors (`0xce654c17`, `0xe66bb550`, `0xc29a91bc`) are computed over the *expanded tuple type list* with struct names erased. The plain `synthesize`/`burnSyntheticToken` 9-arg variants are different selectors.
13. **MetaRouter/Gateway/MulticallRouter are immutable** — never expect an `Upgraded` from them; only the four Transparent proxies (Portal/Synthesis/Fabric/Bridge) and the intents UUPS proxies (`DepositorySrc`, `DepositoryDst`, intent Bridge v1) can rotate impls. The new gateway/executor and the unlockers are immutable too.
14. **`SynthesizeRequest.chainID` is the next hop's chain id and is frequently the off-target hub `13863860`** (or Bitcoin/TON/Tron ids), not one of the eight. The final destination is encoded in the relayed calldata (the sampled ETH → BNB route carried `chainID` 13863860). Don't drop a request just because its `chainID` isn't in your target set.
15. **Intents link key = `intentId`, exact on both sides.** It is topic1 of `IntentLocked` (source), `IntentFilled` (destination) and `IntentUnlocked` (source), and one element of `SettleBatchRequested.intentIds` (data). Verified round trip: Base `IntentLocked` tx `0x1ac0e71cdc5d756ccd281a0849e24fdade8c42405643170668ea93fa8170c820` (`intentId` `0x8e1a155c72b281182647a739c4d750f9e28fc6aa3396685f8147db73ebe6fdb0`, USDbC user → `DepositorySrc` v1) → Arbitrum `IntentFilled` tx `0xd75b6b9fb977c106847b41a1f29d931914dea0607bbde3b41ed53414274c4f58` (USDC solver → recipient, `Filled`) → Arbitrum `SettleBatchRequested` + `OracleRequest` tx `0x9faa5c1cce9d333a6f30fe32de543ea1c3d1eecbaeeb5608c85d4ac81c0b8169` → Base `IntentUnlocked` tx `0xccfa3d60921ee3828759c2813174e0a3234c0f16aa6d799ea657091cb7c16508` (`DepositorySrc` → `DeadlineUnlocker` → solver, `Settled`).
16. **Intents value movement: the payout's sender is the solver, not a Symbiosis contract.** On the destination the ERC-20 `Transfer` goes solver → recipient inside `DepositoryDst.fill` (pulled by the fill unlocker). `DepositoryDst` never holds user funds; only `DepositorySrc` escrows. Watch `DepositorySrc` balances for drains; `unlock` (single release) needs a whitelisted unlocker and `unlockBatch` needs the configured bridge. The unlockers' `sweep` / `sweepNative` are permissionless but should find a zero balance.
17. **Intents v2 settle through the core BridgeV2**, so a core-bridge `OracleRequest` whose `receiveSide` is `DepositorySrc` v2 is an intents settlement, not a synth route. v1 settlements appear only on the separate intent Bridge `0x85700Ed7C30625eD28613d75e85C58EF0056263F`, whose MPC `0xd1d950f53e78bb9f434c07f16218f8149f7ce542` also acted as the solver of the sampled v1 intents.
18. **`ClientIdLog` (`0x5a297b2c9a9f94a0f4e5a796c74ad38e219d1185fccf5f79c18726a830c2b6f5`) has three emitters with different first words:** the Portal and Synthesis (request id) and `DepositorySrc` (the `intentId`). Key on the emitter. `clientId` is an ASCII tag (sampled: `lifi`, `symbiosis-app`, `symbiosis-beta-app`).
19. **Robinhood Chain runs the new MetaRouter only.** Users approve and call the gateway `0xcE8f24A58D85eD5c5A6824f7be1F8d4711A0eb4C`; the tokens then pass through the executor `0xAdB2d3b711Bb8d8Ea92ff70292c466140432c278` into the Portal, and the Portal's `metaRouter()` is the executor. On the other seven chains the SDK still lists the legacy MetaRouter/Gateway and adds the new gateway/executor pair (§§3–5): monitor both entry points there.
20. **The Portal reserve floor and the Synthesis mint cap (2026-09 upgrade) are drain limits.** A release reverts with `Symb: reserve floor` if it would take the Portal's token balance below `reserveFloor(token)`; a mint reverts with `Symb: mint cap` above `mintCap(stoken)`. `SetReserveFloor` / `SetMintCap` are limit changes to alert on; `SetMintCap` fired on the ETH, Base and BNB Synthesis in the pinned window.
21. **Activity is concentrated on the core Portal flow.** In the pinned window the intents contracts (v1 and v2), the new gateways/executors and the `Depository` contracts emitted 0 logs on all eight chains, while the Portals emitted 337 `SynthesizeRequest` (Robinhood 130, ETH 72, BNB 58). A 0 in a short window is not proof that a contract is unused: the v1 intents were last used in June 2026.

---

## 11. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- Portal
TOPIC_SYNTHESIZE_REQUEST       = '\x31325fe0a1a2e6a5b1e41572156ba5b4e94f0fae7e7f63ec21e9b5ce1e4b3eab'
TOPIC_BURN_COMPLETED           = '\xaeef64b7687b985665b6620c7fa271b6f051a3fbe2bfc366fb9c964602eb6d26'
TOPIC_REVERT_BURN_REQUEST      = '\x40590cc12db0488520ce425059f83f8caed91bdf98de5ff829dc57c63843161b'
TOPIC_META_REVERT_REQUEST      = '\xbd03c66ec5bd3d01fbf22bc794f68ac88b693023b438724019205a4b42aefb20'  -- absent from the 2026-10-01 Portal impl
TOPIC_REVERT_SYNTH_COMPLETED   = '\xefcdf9ea4e65571d2ce9c030c46954e950662df8a7d8bd039fc4417e37b2f88c'
TOPIC_CLIENT_ID_LOG            = '\x5a297b2c9a9f94a0f4e5a796c74ad38e219d1185fccf5f79c18726a830c2b6f5'
TOPIC_SET_WHITELIST_TOKEN      = '\x0a4552f1105808db6a44587c9ef0a7c4064bf620b9d843b514ad7365bd52239a'
TOPIC_SET_TOKEN_THRESHOLD      = '\xa6742efd4f410d6fd9688a6cf6a15b6d51121097a263056a3576baaacdc4a9ae'
TOPIC_SET_META_ROUTER          = '\xd5c54ab1d37bfef4dd2253d9d73c292e46f5bd8a67ca5920aab4c2e1993178e7'
TOPIC_PAUSED                   = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                 = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
-- Synthesis
TOPIC_BURN_REQUEST             = '\x5f00e8f0d61ff1190912879949026c85a81f3f96038c7f4cd868bdfe882e0eeb'
TOPIC_BURN_REQUEST_TON         = '\xb22f66d5cb4d958c8beec99f61917824d407a74d4514d8d44cc77247e67a4e5a'
TOPIC_SYNTHESIZE_COMPLETED     = '\x1f3f0f3c7b2df480755c6486a132f215e7b2b89fcca0beecd95a9696c71789b6'
TOPIC_REVERT_BURN_COMPLETED    = '\xb6f5f7b98cc78a8031c967af163a8c197f470a35df1e326a9038859679e6a184'
TOPIC_REVERT_SYNTH_REQUEST     = '\x9bc8099e19706f253ae634ef1a5fb6ef84b4748c2183472905b9b2511cfa8617'
TOPIC_SET_FABRIC               = '\xe7258eee4870ba270f25f5a42dd11bfe5a77658959c916807b94b8e9063c3cd0'
-- BridgeV2
TOPIC_ORACLE_REQUEST           = '\x532dbb6d061eee97ab4370060f60ede10b3dc361cc1214c07ae5e34dd86e6aaf'
TOPIC_LOG_CHANGE_MPC           = '\xcda32bc39904597666dfa9f9c845714756e1ffffad55b52e0d344673a2198121'
TOPIC_SET_TRANSMITTER_STATUS   = '\xeeec8b4e2d317fc608f301f859237a6081b9813f150a3fcfb02fd54276c8be40'
-- SyntFabric / MetaRouter
TOPIC_REPRESENTATION_CREATED   = '\xe33e6b41ee9908e3919a380a52ae7059282c36b87adeee0d2ac1b05dfc50be6f'
TOPIC_TRANSIT_TOKEN_SENT       = '\x0ac368c799fd87078497a837c3b184349108599d7c108f68710d3321ba416c6f'
-- proxy / ERC20
TOPIC_UPGRADED                 = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED            = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_OWNERSHIP_TRANSFERRED    = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_TRANSFER                 = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- 2026-09 upgrade: Portal / Synthesis drain limits
TOPIC_SET_RESERVE_FLOOR        = '\x6319a2a176ea40732de85182054c69c33324f9bcf05fc1d2a81a2a337341bccb'
TOPIC_SET_MINT_CAP             = '\x5f75dc66af14772133e42880c6aed51cbc45fc2b979c2899be3bc5c1e3c3510f'
-- Intents: DepositorySrc (source escrow) / DepositoryDst (destination)
TOPIC_INTENT_LOCKED            = '\x8b4cbc791dddb376fb89eba475c41896f97673ece5db78a30bb2340d2772cb45'
TOPIC_INTENT_UNLOCKED          = '\x5ddce0700a1a8691f425337a0d17990cc84e1e8d6d4b148b8ad8ae1a41f11f17'
TOPIC_INTENT_FILLED            = '\x4f02007c5b383d0fb2923b90ac1cc973e61e27f22ce6b7f5c651faa9cdcf21ec'
TOPIC_SETTLE_BATCH_REQUESTED   = '\x0517f5d20eb91a9b5d67025455e2124eade1b76eb1ea5d768c3bcc010135b850'
TOPIC_UNLOCKER_SET             = '\x60209f49f531418079ff149eb1d71f100566dcaba03bf5a34930e08111df20c4'
TOPIC_BRIDGE_SET               = '\xa49730bff544fd0b716395c592e39c6fd2d2481a19b9229b5b240483db95a495'
TOPIC_RELAY_FEE_SET            = '\xa4985dd6c321807ab991746ac3a0237660c5e3aa374e90dd755f5d11099bad3c'
TOPIC_OWNERSHIP_TRANSFER_STARTED = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
-- Intents: DeadlineUnlocker
TOPIC_UNLOCKER_FILLED          = '\x378381bc5e6c9d6ef5ec537a0bab55ecbf51f170e784499f5b4949b03dadcc29'
TOPIC_UNLOCKER_SETTLED         = '\x2fdfc95b3dadeb6ad1149e0fdade29939418e5b3fa4f2ea6f319399c07af0260'
TOPIC_VOLUME_FEE_BPS_SET       = '\xbc746c1b8cf7bef91e22587dc4db83d0e76dd76b6aad2f49bc94c3f0acf832f2'
TOPIC_FEE_RECEIVER_SET         = '\x49bc8f1c292131e71bfca22660d0716072ff2442b58d72840474dd83a390411c'
-- Depository (BTC refund)
TOPIC_DEPOSIT_LOCKED           = '\xf14a4a91301684b37f631329c0732f735c847a9090edcbe4c4362ac603166711'
TOPIC_DEPOSIT_UNLOCKED         = '\x7365d0eabb56c257feb8a9eac21febe335838563118e4e5c6041062d0832b223'
TOPIC_DEPOSITORY_SET_ROUTER    = '\x50bfd9c0b9815c386500292d8de123643c6c935ffd384a364381b3b11e281e5c'

-- ===== Selectors =====
-- MetaRouter
SEL_META_ROUTE                 = '\xa11b1198'
SEL_META_MINT_SWAP             = '\x3bc78835'
SEL_EXTERNAL_CALL              = '\xf5b697a5'
SEL_RETURN_SWAP                = '\x732cffe9'
SEL_CLAIM_TOKENS               = '\x9fc314c8'
-- Portal
SEL_SYNTHESIZE                 = '\xb1659a3c'
SEL_SYNTHESIZE_NATIVE          = '\x2816f4db'
SEL_META_SYNTHESIZE            = '\xce654c17'
SEL_UNSYNTHESIZE               = '\x1ebe53ef'
SEL_META_UNSYNTHESIZE          = '\xc23a4c88'
SEL_REVERT_SYNTHESIZE          = '\xc42a2894'
-- Synthesis
SEL_MINT_SYNTHETIC_TOKEN       = '\xa83e754b'
SEL_META_MINT_SYNTHETIC_TOKEN  = '\xc29a91bc'
SEL_BURN_SYNTHETIC_TOKEN       = '\xcbef5f2c'
SEL_META_BURN_SYNTHETIC_TOKEN  = '\xe66bb550'
SEL_REVERT_BURN                = '\xf70519ae'
-- BridgeV2
SEL_TRANSMIT_REQUEST_V2        = '\x6cebc9c2'
SEL_RECEIVE_REQUEST_V2         = '\xf7f1baf0'
SEL_RECEIVE_REQUEST_V2_SIGNED  = '\x84d61c97'
SEL_SET_TRANSMITTER_STATUS     = '\x19117d93'
SEL_CHANGE_MPC                 = '\x5b7b018c'
SEL_MPC                        = '\xf75c2664'
-- SyntFabric / MulticallRouter
SEL_GET_SYNT_REPRESENTATION    = '\x506890a0'
SEL_MULTICALL                  = '\x1e859a05'
-- proxy
SEL_UPGRADE_TO                 = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL        = '\x4f1ef286'
-- 2026-09 upgrade / MPC rotation
SEL_SET_RESERVE_FLOOR          = '\x6aba5197'
SEL_SET_MINT_CAP               = '\xc06abe77'
SEL_CHANGE_MPC_SIGNED          = '\x38899935'
SEL_BRIDGE_WITHDRAW_FEE        = '\x1095b6d7'
-- New MetaRouterGateway / MetaRouterExecutorDontApprove (metaRoute = SEL_META_ROUTE)
SEL_METAROUTER_EXECUTOR        = '\xee2ed888'
SEL_SEND_TRANSIT_TOKEN         = '\x62770ff8'
-- Intents
SEL_INTENT_DEPOSIT             = '\x9e9c7997'
SEL_INTENT_UNLOCK_BATCH        = '\x77b0173e'
SEL_INTENT_UNLOCK              = '\xdb33467b'
SEL_INTENT_FILL                = '\x53b1d925'
SEL_INTENT_SETTLE_BATCH        = '\xac8baa3a'
SEL_INTENT_ID                  = '\xd8248741'
SEL_INTENT_SET_BRIDGE          = '\x8dd14802'
SEL_INTENT_SET_UNLOCKER        = '\xd3fff0f6'
SEL_INTENT_SET_RELAY_FEE       = '\x98385109'
SEL_INTENT_WITHDRAW_RELAY_FEE  = '\x6b903970'
SEL_UNLOCKER_FILL              = '\x5b492b70'
SEL_UNLOCKER_UNLOCK            = '\xb8c621d7'
SEL_UNLOCKER_SET_VOLUME_FEE    = '\x653b7fb8'
SEL_UNLOCKER_SET_FEE_RECEIVER  = '\xefdcd974'
SEL_UNLOCKER_SWEEP             = '\xb8dc491b'
-- Depository (BTC refund)
SEL_DEPOSITORY_LOCK            = '\xd2563133'
SEL_DEPOSITORY_UNLOCK          = '\x794997aa'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT              = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT             = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — Ethereum (chain ID 1) =====
ETH_METAROUTER                 = '\xf621fb08bbe51af70e7e0f4ea63496894166ff7f'
ETH_METAROUTER_GATEWAY         = '\xfcef2fe72413b65d3f393d278a714cad87512bcd'
ETH_PORTAL                     = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
ETH_SYNTHESIS                  = '\xd7c3df25683871d18bc838e4f619126442dd38b3'
ETH_FABRIC                     = '\xbbfb7cb70f84fb6fe1cb13e42a0b71efde769428'
ETH_BRIDGE                     = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
ETH_MULTICALL_ROUTER           = '\x49d3fc00f3acf80fabcb42d7681667b20f60889a'
ETH_PROXY_ADMIN                = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'
ETH_PROXY_ADMIN_OWNER_SAFE     = '\x5112eba9bc2468bb5134cbfbeab9334edae7106a'
ETH_METAROUTER_GATEWAY_NEW     = '\xb4769e9c5be31199a25ecd1b0c6609183fa72521'
ETH_METAROUTER_EXECUTOR        = '\xc227b3a439ee6ae3a22500757125f4de91d8008e'
ETH_DEPOSITORY_BTC             = '\x84deb7fc54a1f734aef6ddc0c0f74182bdf941a8'
ETH_RELAYER_EOA                = '\x67f9b3e561383493b3f874feae0c53c2cd23851d'

-- ===== Addresses — Base (chain ID 8453) =====
BASE_METAROUTER                = '\x691df9c4561d95a4a726313089c8536dd682b946'
BASE_METAROUTER_GATEWAY        = '\x41ae964d0f61bb5f5e253141a462ad6f3b625b92'
BASE_PORTAL                    = '\xee981b2459331ad268cc63ce6167b446af4161f8'
BASE_SYNTHESIS                 = '\x9f6424fe88fbe7785fa34f0e369f192bf38e7a6e'
BASE_FABRIC                    = '\x44487a445a7595446309464a82244b4bd4e325d5'
BASE_BRIDGE                    = '\x8097f0b9f06c27af9579f75762f971d745bb222f'
BASE_MULTICALL_ROUTER          = '\x01a3c8e513b758ebb011f7afaf6c37616c9c24d9'
BASE_PROXY_ADMIN               = '\x1ac4c50080871d7a24dd705de9efe5ff14bc0ea2'
BASE_METAROUTER_GATEWAY_NEW    = '\xa18348e793e77239ec68caa51b74c5cdc82c8a9d'
BASE_METAROUTER_EXECUTOR       = '\xcbfd5dcad860f49d0bd2fdad78d9d943caebedef'
-- intents (same addresses on Base, BNB, Arbitrum; v2 = current, v1 = archived js-sdk)
BASE_INTENT_DEPOSITORY_SRC_V2  = '\xdcd0cb19bbe117648cf138f816d08248af241694'
BASE_INTENT_DEPOSITORY_DST_V2  = '\x54cce448468c137c05c895aac9ca769b82e1fe72'
BASE_INTENT_DEADLINE_UNLOCKER_V2 = '\x52a769954a75816f0953d7cebae1e1e365eb1f33'
BASE_INTENT_DEPOSITORY_SRC_V1  = '\x695eeaece7ce4502850b1f6b4f14b97dba02e840'
BASE_INTENT_DEPOSITORY_DST_V1  = '\x4ac560a3a8fadd1662cf9439bb1114abaa3be547'
BASE_INTENT_DEADLINE_UNLOCKER_V1 = '\x4418f8f4826a5d999c7dfe6d16b984e39d2ed32a'
BASE_INTENT_DIRECT_UNLOCKER_V1 = '\xbf6fba492d87b874ef095e4a3e6bfbfbd2177cc9'
BASE_INTENT_BRIDGE_V1          = '\x85700ed7c30625ed28613d75e85c58ef0056263f'
BASE_INTENTS_V2_OWNER_EOA      = '\x6dcb5e43b05918505f65bf423088af172c32be33'
BASE_INTENTS_V1_OWNER_EOA      = '\x13b21d1858b5ab644006bd0d0eb1be7c9a4c0a9b'

-- ===== Addresses — BNB (chain ID 56) =====
BSC_METAROUTER                 = '\x44487a445a7595446309464a82244b4bd4e325d5'
BSC_METAROUTER_GATEWAY         = '\x5c97d726bf5130ae15408ce32bc764e458320d2f'
BSC_PORTAL                     = '\x5aa5f7f84ed0e5db0a4a85c3947ea16b53352fd4'
BSC_SYNTHESIS                  = '\x6b1bbd301782ff636601fc594cd7bfe74871bfaa'
BSC_FABRIC                     = '\xc17d768bf4fdc6f20a4a0d8be8767840d106d077'
BSC_BRIDGE                     = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
BSC_MULTICALL_ROUTER           = '\x44b5d0f16ad55c4e7113310614745e8771b963bb'
BSC_PROXY_ADMIN                = '\xda8057acb94905eb6025120cb2c38415fd81bfeb'
BSC_METAROUTER_GATEWAY_NEW     = '\x851b43189de721dd94aba767aad9e6f6d6a95cca'
BSC_METAROUTER_EXECUTOR        = '\x980447ddcef79a7499da4538da8fc59bacad6997'
BSC_DEPOSITORY_BTC             = '\x1fb3b385ad2bfc7b28d65863baec04094895b813'
BSC_INTENT_DEPOSITORY_SRC_V2   = '\xdcd0cb19bbe117648cf138f816d08248af241694'
BSC_INTENT_DEPOSITORY_DST_V2   = '\x54cce448468c137c05c895aac9ca769b82e1fe72'
BSC_INTENT_DEADLINE_UNLOCKER_V2 = '\x52a769954a75816f0953d7cebae1e1e365eb1f33'
BSC_INTENT_DEPOSITORY_SRC_V1   = '\x695eeaece7ce4502850b1f6b4f14b97dba02e840'
BSC_INTENT_DEPOSITORY_DST_V1   = '\x4ac560a3a8fadd1662cf9439bb1114abaa3be547'
BSC_INTENT_DEADLINE_UNLOCKER_V1 = '\x4418f8f4826a5d999c7dfe6d16b984e39d2ed32a'
BSC_INTENT_DIRECT_UNLOCKER_V1  = '\xbf6fba492d87b874ef095e4a3e6bfbfbd2177cc9'
BSC_INTENT_BRIDGE_V1           = '\x85700ed7c30625ed28613d75e85c58ef0056263f'

-- ===== Addresses — Avalanche (chain ID 43114) — NO Synthesis/Fabric =====
AVAX_METAROUTER                = '\x6f0f6393e45fe0e7215906b6f9cfeff53ea139cf'
AVAX_METAROUTER_GATEWAY        = '\x4cfa66497fa84d739a0f785fbcee9196f1c64e4a'
AVAX_PORTAL                    = '\xe75c7e85fe6add07077467064ad15847e6ba9877'
AVAX_BRIDGE                    = '\x292fc50e4eb66c3f6514b9e402dbc25961824d62'
AVAX_MULTICALL_ROUTER          = '\xdc9a6a26209a450cac415fb78487e907c660cf6a'
AVAX_PROXY_ADMIN               = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'
AVAX_METAROUTER_GATEWAY_NEW    = '\xfec09be39f82b13471d2e0e7d72e6ee589c631c6'
AVAX_METAROUTER_EXECUTOR       = '\x4494b8cbc69c794d82bd2d820a6ff6f62d7d841a'
AVAX_DEPOSITORY_BTC            = '\xe7eb022e21e85200e7b0daebf3757764e83f5c4e'
-- unlisted second BridgeV2 proxy (not in the SDK config; different MPC; 0 logs in the pinned window)
AVAX_BRIDGE_UNLISTED           = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'

-- ===== Addresses — Arbitrum (chain ID 42161) =====
ARB_METAROUTER                 = '\xf7e96217347667064dee8f20db747b1c7df45dde'
ARB_METAROUTER_GATEWAY         = '\x80dddda846e779ccee463bdc0bcc2ae296fedaf9'
ARB_PORTAL                     = '\x01a3c8e513b758ebb011f7afaf6c37616c9c24d9'
ARB_SYNTHESIS                  = '\x326adbe46d7e6c1b3927e9309b96df478bda6d16'
ARB_FABRIC                     = '\x2ee9559387b806e88fd46b9da160d64a29ce7da0'
ARB_BRIDGE                     = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
ARB_MULTICALL_ROUTER           = '\xda8057acb94905eb6025120cb2c38415fd81bfeb'
ARB_PROXY_ADMIN                = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'
ARB_METAROUTER_GATEWAY_NEW     = '\x3743c756b64ecd0770f1d4f47696a73d2a46dcbe'
ARB_METAROUTER_EXECUTOR        = '\xf37e321e1c275d249b7a9c825ae802a9f464eb94'
ARB_DEPOSITORY_BTC             = '\x84b10469db07446d5fc7156aefdd6b7117108a73'
ARB_INTENT_DEPOSITORY_SRC_V2   = '\xdcd0cb19bbe117648cf138f816d08248af241694'
ARB_INTENT_DEPOSITORY_DST_V2   = '\x54cce448468c137c05c895aac9ca769b82e1fe72'
ARB_INTENT_DEADLINE_UNLOCKER_V2 = '\x52a769954a75816f0953d7cebae1e1e365eb1f33'
ARB_INTENT_DEPOSITORY_SRC_V1   = '\x695eeaece7ce4502850b1f6b4f14b97dba02e840'
ARB_INTENT_DEPOSITORY_DST_V1   = '\x4ac560a3a8fadd1662cf9439bb1114abaa3be547'
ARB_INTENT_DEADLINE_UNLOCKER_V1 = '\x4418f8f4826a5d999c7dfe6d16b984e39d2ed32a'
ARB_INTENT_DIRECT_UNLOCKER_V1  = '\xbf6fba492d87b874ef095e4a3e6bfbfbd2177cc9'
ARB_INTENT_BRIDGE_V1           = '\x85700ed7c30625ed28613d75e85c58ef0056263f'

-- ===== Addresses — Optimism (chain ID 10) — NO Synthesis/Fabric =====
OP_METAROUTER                  = '\x0f91052dc5b4bae53d0fea5dae561a117268f5d2'
OP_METAROUTER_GATEWAY          = '\x200a0fe876421dc49a26508e3efd0a1008fd12b5'
OP_PORTAL                      = '\x292fc50e4eb66c3f6514b9e402dbc25961824d62'
OP_BRIDGE                      = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
OP_MULTICALL_ROUTER            = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
OP_PROXY_ADMIN                 = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'
OP_METAROUTER_GATEWAY_NEW      = '\xa9a96ee51dd54b9f51d46b1fbd2a19c1295ec75b'
OP_METAROUTER_EXECUTOR         = '\x356d322bf762d4022d8c241428770565f236c2ea'

-- ===== Addresses — Polygon (chain ID 137) — NO Synthesis/Fabric =====
POLY_METAROUTER                = '\xa260e3732593e4ecf9ddc144fd6c4c5fe7077978'
POLY_METAROUTER_GATEWAY        = '\xab83653fd41511d638b69229afbf998eb9b0f30c'
POLY_PORTAL                    = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
POLY_BRIDGE                    = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
POLY_MULTICALL_ROUTER          = '\xc5b61b9abc3c6229065cad0e961af585c5e0135c'
POLY_PROXY_ADMIN               = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'
POLY_METAROUTER_GATEWAY_NEW    = '\x2ee9559387b806e88fd46b9da160d64a29ce7da0'
POLY_METAROUTER_EXECUTOR       = '\x7a73a0ba4919778c5442f026bd01795b4f2a4cb8'

-- ===== Addresses — Robinhood Chain (chain ID 4663) — NO Synthesis/Fabric; new MetaRouter only =====
RH_PORTAL                      = '\x292fc50e4eb66c3f6514b9e402dbc25961824d62'
RH_BRIDGE                      = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
RH_METAROUTER_GATEWAY_NEW      = '\xce8f24a58d85ed5c5a6824f7be1f8d4711a0eb4c'
RH_METAROUTER_EXECUTOR         = '\xadb2d3b711bb8d8ea92ff70292c466140432c278'
RH_MULTICALL_ROUTER            = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
RH_PROXY_ADMIN                 = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'
RH_OWNER                       = '\x0605963420c4e8566fcef2cf65dcd575662bf53d'
RH_USDG                        = '\x5fc5360d0400a0fd4f2af552add042d716f1d168'
RH_WETH                        = '\x0bd7d308f8e1639fab988df18a8011f41eacad73'

-- ===== Addresses — Arc (chain ID 5042) — NO Synthesis/Fabric; new MetaRouter only =====
ARC_PORTAL                     = '\xe75c7e85fe6add07077467064ad15847e6ba9877'
ARC_BRIDGE                     = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
ARC_METAROUTER_GATEWAY_NEW     = '\xce8f24a58d85ed5c5a6824f7be1f8d4711a0eb4c'
ARC_METAROUTER_EXECUTOR        = '\xadb2d3b711bb8d8ea92ff70292c466140432c278'
ARC_MULTICALL_ROUTER           = '\x292fc50e4eb66c3f6514b9e402dbc25961824d62'
ARC_PROXY_ADMIN                = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'
ARC_OWNER                      = '\x64c44f682a1014410c864bd708a7ab1b67eec0ea'
ARC_USDC                       = '\x3600000000000000000000000000000000000000'

-- ===== Off-target Symbiosis hub (chain ID 13863860) — Synthesis hub, no Portal =====
HUB_SYNTHESIS                  = '\x45cfd6fb7999328f189aad2739fba4be6c45e5bf'
HUB_BRIDGE                     = '\x1a039ce63ae35a67bf0e9f6dbfae969639d59ec8'
HUB_FABRIC                     = '\xf85fc807d05d3ab2309364226970aac57b4e1ea4'
```

---

## 12. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` (event topic0) and `keccak256(canonical signature)[0:4]` (selector) with keccak-256, from the canonical Solidity in `symbiosis-finance/core-contracts` (`Portal.sol`, `Synthesis.sol`, `bridge/BridgeV2.sol`, `SyntFabric.sol`, `metarouter/MetaRouter.sol`, `metarouter/MetaRouterGateway.sol`, `metarouter/MetaRouteStructs.sol`, `periphery/MulticallRouter.sol`). The keccak recipe was self-validated by reproducing the canonical `Transfer(address,address,uint256)` topic0.
- **Live-log cross-checks (`eth_getLogs`):** `SynthesizeRequest` (1,535 logs) and `BurnCompleted` (1,594) on the ETH Portal `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8`; `OracleRequest` (1,540) on the ETH Bridge `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` — all in a 49,000-block window ending block 25279512. `SynthesizeCompleted` confirmed live on the BNB Synthesis `0x6B1bbd301782FF636601fC594Cd7Bfe74871bfaA`. The 4-topic count on `SynthesizeRequest` confirms `id` non-indexed + 3 indexed params, matching the source.
- **Selector presence in live impl bytecode:** scanned the ETH implementations — Portal impl `0x57dbcb192fa64bf07eab76941d1dae5177c8f4f3` (`synthesize` `0xb1659a3c`, `metaSynthesize` `0xce654c17`, `unsynthesize` `0x1ebe53ef`); MetaRouter `0xf621Fb08BBE51aF70e7E0F4EA63496894166Ff7F` (`metaRoute` `0xa11b1198`, `metaMintSwap` `0x3bc78835`, `externalCall` `0xf5b697a5`); Bridge impl `0x20c54cc697329333fe00ded49c7dca8c83dce65b` (`receiveRequestV2` `0xf7f1baf0`, `transmitRequestV2` `0x6cebc9c2`, `changeMPC` `0x5b7b018c`) — all present.
- **Addresses:** parsed from the authoritative SDK registry `symbiosis-finance/js-sdk/src/crosschain/config/mainnet.ts` (with chain ids resolved against `js-sdk/src/constants.ts`), then existence-checked via `eth_getCode` (non-empty bytecode) on each of the seven publicnode RPCs. Avalanche/Optimism/Polygon `synthesis` + `fabric` are `0x0` in the registry and confirmed absent. Wiring spot-checks (`eth_call`): ETH `MetaRouterGateway.metaRouter()` → `0xf621Fb08BBE51aF70e7E0F4EA63496894166Ff7F`, ETH `Synthesis.fabric()` → `0xbBFb7cb70f84fb6fE1Cb13e42A0B71EFDe769428`, ETH `Portal.bridge()` → `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E`, ETH `Bridge.mpc()` → `0x5ddc2587b85c664083677654e77a472511fb537c`.
- **Proxy classification:** EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` and admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` read live with `eth_getStorageAt` on every chain. Portal/Synthesis/Fabric/Bridge → both slots populated (Transparent); MetaRouter/Gateway/MulticallRouter → impl slot all-zero + multi-KB runtime (immutable). Per-chain impls + ProxyAdmin literals recorded in §§3–6/§9.

How the 2026-09-29 additions were verified:

- **Sources of the new addresses:** `symbiosis-finance/sdk-types` `src/crosschain/config/mainnet.ts` (last change 2026-09-22): the `intentConfig` blocks of BSC, Arbitrum and Base (v2), the `ROBINHOOD_MAINNET` block (4663) and the `depository` blocks; `src/metaRouters.ts` for the new gateway + executor of each chain. The archived `js-sdk` (`intentConfig` v1) for the v1 intents addresses, and its build artifacts `src/crosschain/abis/intents/{DepositorySrc,DepositoryDst,DeadlineUnlocker,DirectUnlocker,Bridge}.json` and `IDepository.json` for the ABIs.
- **Verified explorer sources:** Base Blockscout — `DepositorySrc` v1 implementation, `DepositoryDst` v1 implementation (Base), intent `Bridge` v1 implementation, `DeadlineUnlocker` v1, `DirectUnlocker` v1 (solc 0.8.28, `contracts/v3/`). Ethereum Blockscout — the new `MetaRouterGateway` and `MetaRouterExecutorDontApprove`, and the new Portal and Synthesis implementations. The new Portal and Synthesis sources were diffed against the previous verified implementations `0x57dbcb192fa64bf07eab76941d1dae5177c8f4f3` and `0x14078ebe3b6dd51c089188c1962ddc94a647be35`: the only additions are `SetReserveFloor`/`setReserveFloor`/`reserveFloor` and `SetMintCap`/`setMintCap`/`mintCap`.
- **Unverified v2 code, checked in bytecode:** the v2 implementations `0x9bf92ce9fd272720ab82331ecafab7fe0363d278` (`DepositorySrc`), `0x536f874f1d07692591b5579df55f1f6b2c33ac8b` (`DepositoryDst`) and `DeadlineUnlocker` v2 `0x52a769954A75816F0953D7cEbae1E1e365EB1f33` have no verified source on Base or Arbitrum Blockscout. Their runtime code was scanned for each topic0 (PUSH32) and selector (PUSH4) of the v1 ABI, with the verified v1 contracts as the positive control: `DepositorySrc` v2 15/15, `DepositoryDst` v2 13/13, `DeadlineUnlocker` v2 11/12 (no `fill(bytes,bytes)`). Four dispatcher selectors exist only in `DeadlineUnlocker` v2: `0x196cd5f2`, `0x2a6d8b4a` (`setDepository(address,bool)` in the public signature database), `0x75055af5`, `0x954826f8` — **unverified**. The four `Depository` contracts (source unverified) carry all six checked ABI items each.
- **Topic0 + selectors:** every added row recomputed as `keccak256(canonical signature)` / `[0:4]`; tuples written out in ABI order.
- **Addresses:** each existence-checked with `eth_getCode` on all eight chains — the eight intents addresses on every chain, the new gateway + executor of every chain, the four `Depository` contracts, and the Robinhood roles; implementations from the EIP-1967 slot; admin slot read for the Portal on all eight chains and for the Robinhood BridgeV2 (the three ProxyAdmin values are unchanged since 2026-06-09). Wiring by `eth_call`: `metaRouterExecutorDontApprove()` on the eight gateways returns the listed executor; intents `bridge()`, `owner()`, `unlockers()`, `relayFee()`; `isTransmitter(DepositoryDst v2)` = `true` on the Base, BNB and Arbitrum core bridges; `mpc()` on all eight bridges (and on the unlisted Avalanche proxy); ETH `oldMPC()` / `newMPC()` / `newMPCEffectiveTime()`; Robinhood Portal `bridge()` / `metaRouter()` / `owner()`.
- **Activity — pinned 12-hour window 2026-09-28 00:00–12:00 UTC**, all logs of each listed contract (one `eth_getLogs` address-list filter per chain; blocks eth 26072222–26075812, base 51882127–51903726, bnb 124425013–124520982, arb 509539969–509698804, avax 96289260–96322019, op 157477412–157499011, poly 94565640–94594439, rh 74350994–74780331):

| Chain | `SynthesizeRequest` (Portal) | `BurnCompleted` (Portal) | `OracleRequest` (BridgeV2) | `SynthesizeCompleted` | `TransitTokenSent` | `LogChangeMPC` | `SetMintCap` | Intents / new gateway + executor / Depository |
|-------|----|----|----|----|----|----|----|----|
| Ethereum | 72 | 65 | 72 | 0 | 6 | 1 | 1 | 0 |
| Base | 21 | 29 | 21 | 4 | 1 | 1 | 1 | 0 |
| BNB | 58 | 145 | 58 | 0 | 5 | 1 | 1 | 0 |
| Arbitrum | 27 | 27 | 27 | 0 | 0 | 1 | 0 | 0 |
| Avalanche | 2 | 1 | 2 | — | 0 | 1 | — | 0 |
| Optimism | 5 | 1 | 5 | — | 0 | 1 | — | 0 |
| Polygon | 22 | 7 | 22 | — | 0 | 1 | — | 0 |
| Robinhood Chain | 130 | 32 | 130 | — | 0 | 1 | — | 0 |

  (— = contract not deployed; `SetReserveFloor` = 0 everywhere; `ClientIdLog` equals `SynthesizeRequest` on every chain.) A 0 is a measurement of this window, not a statement that a contract is unused. Longer range: 31 `LogChangeMPC` on the ETH bridge in blocks 25859812–26075812.
- **Sample transactions read (receipt logs):** link key — ETH `0x5a7c239ec463d08d664bb54c4b0dcd5b20395b110210a51ef132f7f973a6456d` → BNB `0xf5fcae0b80b328242804415e02316433b5adfb5968759d2a5af83b574de99c6a`; Robinhood deposit `0x558d6b6359e884846f414606e545b90cdcdbd52069256e8b92fd6ca1b3b1edc1`, payout `0x3269380616f6cc47e75b25d74b0c5ad6e25a8aae5270590b58b3830f1c9153e9`, MPC rotation `0xc0c7dc4ebefbc452c2cd8d0ceeaf83ea1e8d5f2057f1d87ffaf9d1ad528841bb`; ETH MPC rotation `0x79b12b56d15fedd1d599e6d8fd43af1958d9d96147c5d440747c3e618160c21c`; ETH `SetMintCap` `0x6ebf9dc89c5a61003c9e9b68e7a59753760b90bfc88f9fc42c51ac1d05135771`; intents round trip Base `0x1ac0e71cdc5d756ccd281a0849e24fdade8c42405643170668ea93fa8170c820` → Arbitrum `0xd75b6b9fb977c106847b41a1f29d931914dea0607bbde3b41ed53414274c4f58` → Arbitrum `0x9faa5c1cce9d333a6f30fe32de543ea1c3d1eecbaeeb5608c85d4ac81c0b8169` → Base `0xccfa3d60921ee3828759c2813174e0a3234c0f16aa6d799ea657091cb7c16508`; also Base `IntentFilled` `0x3bde0a724967d6e29625116c2305aec34c223bdbaa7cfd1efe197089d6506f42`, Base `SettleBatchRequested` `0xd05c97090ee05314d0bb2521451003ca4dbb1e5ec2e496b17dfc6954648a6d4a`, Arbitrum `IntentLocked` `0x6570e11b777f23821624cc0de30a740e657dc563202693991f75a3be443de548`, Arbitrum `IntentFilled` `0xd93eb023bb5bc8ecd6faaebc3855c5018193e00f1e73ba2ca7f7bb8f2abdb8a8`.
- **Robinhood Chain coverage:** RPC `https://rpc.mainnet.chain.robinhood.com`. The Robinhood Blockscout API refused requests (HTTP 403), so no Robinhood contract source was read; the roles rest on the official config and on code byte-identical to the verified contracts of the other chains.

**Authoritative sources:**
- Canonical contracts: [`github.com/symbiosis-finance/core-contracts`](https://github.com/symbiosis-finance/core-contracts) (`contracts/synth-core/`, `contracts/periphery/`).
- Address registry / SDK: [`github.com/symbiosis-finance/js-sdk`](https://github.com/symbiosis-finance/js-sdk) — `src/crosschain/config/mainnet.ts`, `src/constants.ts`.
- Docs: [`docs.symbiosis.finance`](https://docs.symbiosis.finance) (contract addresses + architecture).
- Explorers (existence + impl): [Etherscan](https://etherscan.io/address/0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8), [Basescan](https://basescan.org/address/0xEE981B2459331AD268cc63CE6167b446AF4161f8), [BscScan](https://bscscan.com/address/0x5Aa5f7f84eD0E5db0a4a85C3947eA16B53352FD4), [Snowscan](https://snowscan.xyz/address/0xE75C7E85FE6ADd07077467064aD15847E6ba9877), [Arbiscan](https://arbiscan.io/address/0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9), [Optimistic Etherscan](https://optimistic.etherscan.io/address/0x292fC50e4eB66C3f6514b9E402dBc25961824D62), [PolygonScan](https://polygonscan.com/address/0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8).

**Sources opened for the 2026-09-29 additions:**
- Current SDK config: [`sdk-types` `src/crosschain/config/mainnet.ts`](https://github.com/symbiosis-finance/sdk-types/blob/main/src/crosschain/config/mainnet.ts), [`src/metaRouters.ts`](https://github.com/symbiosis-finance/sdk-types/blob/main/src/metaRouters.ts), [`src/constants.ts`](https://github.com/symbiosis-finance/sdk-types/blob/main/src/constants.ts).
- Archived SDK (v1 intents, ABIs): [`js-sdk` `src/crosschain/config/mainnet.ts`](https://github.com/symbiosis-finance/js-sdk/blob/main/src/crosschain/config/mainnet.ts), [`src/crosschain/abis/intents/`](https://github.com/symbiosis-finance/js-sdk/tree/main/src/crosschain/abis/intents), [`src/crosschain/abis/IDepository.json`](https://github.com/symbiosis-finance/js-sdk/blob/main/src/crosschain/abis/IDepository.json), [`src/crosschain/abis/multicallRouterV2.json`](https://github.com/symbiosis-finance/js-sdk/blob/main/src/crosschain/abis/multicallRouterV2.json).
- Core bridge source: [`core-contracts` `contracts/synth-core/bridge/BridgeV2.sol`](https://github.com/symbiosis-finance/core-contracts/blob/main/contracts/synth-core/bridge/BridgeV2.sol).
- Base Blockscout verified sources (API): [DepositorySrc v1 impl](https://base.blockscout.com/api/v2/smart-contracts/0xcd42ede8afc30d40587550fa4c17da3575b3bc7b), [DepositoryDst v1 impl](https://base.blockscout.com/api/v2/smart-contracts/0x8f71e1085408e50115213d65e868d3ff7dfdb56e), [intent Bridge v1 impl](https://base.blockscout.com/api/v2/smart-contracts/0x8617f8a259582dd1baab87a8c3eb51b9cb6f645d), [DeadlineUnlocker v1](https://base.blockscout.com/api/v2/smart-contracts/0x4418f8f4826a5d999c7dfe6d16b984e39d2ed32a), [DirectUnlocker v1](https://base.blockscout.com/api/v2/smart-contracts/0xbf6fba492d87b874ef095e4a3e6bfbfbd2177cc9), [new Portal impl on Base](https://base.blockscout.com/api/v2/smart-contracts/0xaf4570fadd2ab163c809e4ba483d032b31475e1a).
- Ethereum Blockscout verified sources (API): [MetaRouterGateway (new)](https://eth.blockscout.com/api/v2/smart-contracts/0xB4769e9c5bE31199a25ecD1B0C6609183fa72521), [MetaRouterExecutorDontApprove](https://eth.blockscout.com/api/v2/smart-contracts/0xc227b3a439EE6ae3A22500757125f4dE91d8008E), [Portal impl (new)](https://eth.blockscout.com/api/v2/smart-contracts/0xa0aee4eefb0c7c2706a9b2b9c79d082154b5393c), [Portal impl (previous)](https://eth.blockscout.com/api/v2/smart-contracts/0x57dbcb192fa64bf07eab76941d1dae5177c8f4f3), [Synthesis impl (new)](https://eth.blockscout.com/api/v2/smart-contracts/0x83ef4306cbe2c8b7ee58e71404ca7e3c41546169), [Synthesis impl (previous)](https://eth.blockscout.com/api/v2/smart-contracts/0x14078ebe3b6dd51c089188c1962ddc94a647be35).
- Intents address logs (Blockscout API): [Base `DepositorySrc` v1](https://base.blockscout.com/api/v2/addresses/0x695eeaece7ce4502850b1f6b4f14b97dba02e840/logs), [Base `DepositoryDst` v1](https://base.blockscout.com/api/v2/addresses/0x4ac560a3a8fadd1662cf9439bb1114abaa3be547/logs), [Base `DepositorySrc` v2](https://base.blockscout.com/api/v2/addresses/0xdcd0cb19bbe117648cf138f816d08248af241694/logs), [Base `DepositoryDst` v2](https://base.blockscout.com/api/v2/addresses/0x54cce448468c137c05c895aac9ca769b82e1fe72/logs), [Arbitrum `DepositorySrc` v1](https://arbitrum.blockscout.com/api/v2/addresses/0x695eeaece7ce4502850b1f6b4f14b97dba02e840/logs), [Arbitrum `DepositoryDst` v1](https://arbitrum.blockscout.com/api/v2/addresses/0x4ac560a3a8fadd1662cf9439bb1114abaa3be547/logs), [Arbitrum `DepositorySrc` v2](https://arbitrum.blockscout.com/api/v2/addresses/0xdcd0cb19bbe117648cf138f816d08248af241694/logs), [Arbitrum `DepositoryDst` v2](https://arbitrum.blockscout.com/api/v2/addresses/0x54cce448468c137c05c895aac9ca769b82e1fe72/logs).
- Robinhood Chain: RPC `https://rpc.mainnet.chain.robinhood.com`; explorer [robinhoodchain.blockscout.com](https://robinhoodchain.blockscout.com) (its API refused requests with HTTP 403).
- Signature lookup: [openchain signature database](https://api.openchain.xyz/signature-database/v1/lookup?function=0x196cd5f2,0x2a6d8b4a,0x75055af5,0x954826f8&filter=true).

# Symbiosis Finance — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on every listed chain and the canonical `symbiosis-finance/core-contracts` + `symbiosis-finance/js-sdk` repos on 2026-06-09.
**Scope:** the full Symbiosis cross-chain AMM/bridge core — **MetaRouter** + **MetaRouterGateway** + **Portal** + **Synthesis** + **SyntFabric** + **BridgeV2** + **MulticallRouter** — across the seven requested chains (ETH 1, Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Optimism 10, Polygon 137). Topics/selectors are **chain-agnostic** (keccak of the canonical signature); addresses are **network-specific**. Symbiosis connects ~50 chains in total; counterparty chains outside the seven (zkSync Era, Linea, Scroll, Mantle, TON, Bitcoin, Tron, Solana, Gnosis, …) and the dedicated **Symbiosis hub chain (chainId 13863860)** are noted in §6 — they are findings, not omissions.

Symbiosis is a **lock-and-mint / burn-and-release synthetic-asset bridge with an embedded swap router**. The flow is: a user calls `MetaRouter.metaRoute` on the source chain (optional first swap) → tokens are locked in the **Portal** (`SynthesizeRequest` event) → a relayer network ("Transmitter"/MPC) reads the **BridgeV2** `OracleRequest` event and relays the call → on the manager/hub chain the **Synthesis** mints a synthetic representation (sToken) via **SyntFabric** (`SynthesizeCompleted`) → for the return leg the sToken is burned on Synthesis (`BurnRequest`) and the original token is released from the Portal on the destination chain (`BurnCompleted`). Most "synthetic" mint/burn activity is concentrated on the **Symbiosis hub chain (13863860)**, an off-target Symbiosis-operated chain; on the seven target chains the dominant events are `SynthesizeRequest` (Portal, lock), `BurnCompleted` (Portal, release), and `OracleRequest` (BridgeV2, relay).

**Three deployment facts a monitoring engineer must internalize before indexing:**
1. **Portal, Synthesis, SyntFabric and BridgeV2 are EIP-1967 Transparent proxies** (impl + admin slots both populated). **MetaRouter, MetaRouterGateway and MulticallRouter are immutable** (impl slot empty). Watch `Upgraded(address)` on the four proxies.
2. **Synthesis + SyntFabric only exist on a subset of the seven** — present on **ETH, Base, BNB, Arbitrum**; **NOT deployed on Avalanche, Optimism, Polygon** (config = `0x0`, confirmed). **Portal + Bridge + MetaRouter exist on all seven.** A chain with a Portal but no Synthesis is a "depository spoke" — it locks/releases real tokens but never mints synths locally.
3. **Addresses are NOT a single cross-chain vanity.** Symbiosis reuses a small *pool* of addresses across chains because the same deployer EOA hits the same nonce on multiple chains — so e.g. `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` is the **Bridge on ETH/Poly/Arb/Op/Base-fabric-no** but the **MetaRouter is a different role at a colliding literal elsewhere**. **Always key on `(chainId, address)` and never assume a literal means the same role on another chain** (§9).

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified on (of the 7) |
|----------|------|--------|------------------------|
| **MetaRouter** | Entry point. `metaRoute` orchestrates first swap + the cross-chain call. Spawns its own gateway in the constructor. | **No** (immutable, 7,422 B identical on all 7) | ETH, Base, BNB, Avax, Arb, Op, Poly |
| **MetaRouterGateway** | Pull-payment escrow; users `approve` *this*, not MetaRouter. `claimTokens` callable only by its MetaRouter. | **No** (immutable, 1,081 B) | all 7 |
| **Portal** | Source-chain vault: locks real tokens (`synthesize`/`metaSynthesize`), releases them on return (`unsynthesize`/`metaUnsynthesize`). Emits `SynthesizeRequest` / `BurnCompleted`. | **EIP-1967 Transparent** | all 7 |
| **Synthesis** | Mints/burns synthetic representations (sTokens) via SyntFabric. Emits `SynthesizeCompleted` / `BurnRequest`. | **EIP-1967 Transparent** | ETH, Base, BNB, Arb |
| **SyntFabric** | Registry/minter of sToken ERC-20s; `getSyntRepresentation(real, chainId)`. Emits `RepresentationCreated`. Only `onlySynthesis`. | **EIP-1967 Transparent** | ETH, Base, BNB, Arb |
| **BridgeV2** | Relayer messaging layer. `transmitRequestV2` emits `OracleRequest`; MPC calls `receiveRequestV2` to execute. Gnosis-style MPC + transmitter allowlist. | **EIP-1967 Transparent** | all 7 |
| **MulticallRouter** | Off-chain-encoded multi-hop swap executor used inside meta-routing (`multicall`). | **No** (immutable, 3,558–3,617 B) | all 7 |

There is **one generation** of this core (BridgeV2 = "V2" of the bridge; Portal/Synthesis carry `versionRecipient() = "2.0.1"`). Hence a single `core.md`, not per-version files. The four proxies can be upgraded in place — watch `Upgraded`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak-256 on 2026-06-09 from the canonical `core-contracts` sources. `SynthesizeRequest`, `OracleRequest`, `SynthesizeCompleted`, `BurnCompleted` additionally confirmed against live `eth_getLogs` (citations inline).

### 1.1 Portal (source-chain vault) — ETH `0xb8f2…81A8`, all 7 chains

| topic0 | Event |
|--------|-------|
| `0x31325fe0a1a2e6a5b1e41572156ba5b4e94f0fae7e7f63ec21e9b5ce1e4b3eab` | `SynthesizeRequest(bytes32 id, address indexed from, uint256 indexed chainID, address indexed revertableAddress, address to, uint256 amount, address token)` — token locked, cross-chain mint requested. *(1,535 live logs on ETH Portal, 49k-block window ending blk 25279512; 4 topics confirms id non-indexed + 3 indexed.)* |
| `0xaeef64b7687b985665b6620c7fa271b6f051a3fbe2bfc366fb9c964602eb6d26` | `BurnCompleted(bytes32 indexed id, bytes32 indexed crossChainID, address indexed to, uint256 amount, uint256 bridgingFee, address token)` — real token released on `unsynthesize`/`metaUnsynthesize`. *(1,594 live logs on ETH Portal, same window.)* |
| `0x40590cc12db0488520ce425059f83f8caed91bdf98de5ff829dc57c63843161b` | `RevertBurnRequest(bytes32 indexed id, address indexed to)` |
| `0xbd03c66ec5bd3d01fbf22bc794f68ac88b693023b438724019205a4b42aefb20` | `MetaRevertRequest(bytes32 indexed id, address indexed to)` |
| `0xefcdf9ea4e65571d2ce9c030c46954e950662df8a7d8bd039fc4417e37b2f88c` | `RevertSynthesizeCompleted(bytes32 indexed id, address indexed to, uint256 amount, uint256 bridgingFee, address token)` |
| `0x5a297b2c9a9f94a0f4e5a796c74ad38e219d1185fccf5f79c18726a830c2b6f5` | `ClientIdLog(bytes32 requestId, bytes32 indexed clientId)` — fires alongside every synth/burn for integrator attribution. **Also emitted by Synthesis** (same topic0) — disambiguate by emitter. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x0a4552f1105808db6a44587c9ef0a7c4064bf620b9d843b514ad7365bd52239a` | `SetWhitelistToken(address token, bool activate)` |
| `0xa6742efd4f410d6fd9688a6cf6a15b6d51121097a263056a3576baaacdc4a9ae` | `SetTokenThreshold(address token, uint256 threshold)` |
| `0xd5c54ab1d37bfef4dd2253d9d73c292e46f5bd8a67ca5920aab4c2e1993178e7` | `SetMetaRouter(address metaRouter)` — **also emitted by Synthesis** (same topic0). |

### 1.2 Synthesis (sToken minter/burner) — ETH `0xD7c3…38B3`; ONLY on ETH/Base/BNB/Arb

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
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` / `0x5db9ee0a…073aa` | `Paused` / `Unpaused` (≡ Portal topic0s) |

### 1.3 BridgeV2 (relay messaging) — ETH `0x5523…227E`, all 7 chains

| topic0 | Event |
|--------|-------|
| `0x532dbb6d061eee97ab4370060f60ede10b3dc361cc1214c07ae5e34dd86e6aaf` | `OracleRequest(address bridge, bytes callData, address receiveSide, address oppositeBridge, uint256 chainId)` — **the relayer trigger; emitted on every cross-chain send.** All params non-indexed (no topics beyond topic0). *(1,540 live logs on ETH Bridge, 49k-block window.)* |
| `0xcda32bc39904597666dfa9f9c845714756e1ffffad55b52e0d344673a2198121` | `LogChangeMPC(address indexed oldMPC, address indexed newMPC, uint256 indexed effectiveTime, uint256 chainId)` — **MPC rotation = highest-severity governance signal.** |
| `0xeeec8b4e2d317fc608f301f859237a6081b9813f150a3fcfb02fd54276c8be40` | `SetTransmitterStatus(address indexed transmitter, bool status)` — relayer allowlist change. |

### 1.4 SyntFabric — ETH `0xbBFb…9428`; ONLY on ETH/Base/BNB/Arb

| topic0 | Event |
|--------|-------|
| `0xe33e6b41ee9908e3919a380a52ae7059282c36b87adeee0d2ac1b05dfc50be6f` | `RepresentationCreated(address rToken, uint256 chainID, address sToken)` — a new synthetic representation registered (rare; admin/onlySynthesis). |

### 1.5 MetaRouter — all 7 chains

| topic0 | Event |
|--------|-------|
| `0x0ac368c799fd87078497a837c3b184349108599d7c108f68710d3321ba416c6f` | `TransitTokenSent(address to, uint256 amount, address token)` — emitted when an `externalCall` swap fails and tokens are returned to `_to` (fallback path). |

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
| `0xdbec15bb` | `metaRouter()` → `address` | Owning MetaRouter (ETH: returns `0xf621…Ff7F`, confirmed). |

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

### 2.4 Synthesis (sToken minter; proxy; ETH/Base/BNB/Arb only)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa83e754b` | `mintSyntheticToken(uint256,bytes32,bytes32,address,uint256,uint256,address)` | `onlyBridge` — mint sTokens, emit `SynthesizeCompleted`. |
| `0xc29a91bc` | `metaMintSyntheticToken((uint256,uint256,bytes32,bytes32,address,uint256,address,address[],address,bytes,address,bytes,uint256))` | `onlyBridge` — mint + swap + final call. |
| `0xcbef5f2c` | `burnSyntheticToken(uint256,address,uint256,address,address,address,address,uint256,bytes32)` | Burn sToken → emit `BurnRequest`. |
| `0xe66bb550` | `metaBurnSyntheticToken((uint256,uint256,bytes32,address,address,address,bytes,uint256,address,address,address,address,uint256,bytes32))` | Burn + cross-chain release intent. |
| `0x40b1a037` | `revertSynthesizeRequest(uint256,bytes32)` | Refund path. |
| `0xf70519ae` | `revertBurn(uint256,bytes32)` | `onlyBridge` revert. |
| `0x5d176f2f` | `fabric()` → `address` | Owning SyntFabric (ETH: returns `0xbBFb…9428`, confirmed). |

### 2.5 BridgeV2 (relay; proxy)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6cebc9c2` | `transmitRequestV2(bytes,address,address,uint256)` | `onlyTransmitter` — emit `OracleRequest`. Present in live impl. |
| `0xf7f1baf0` | `receiveRequestV2(bytes,address)` | `onlyMPC` — execute the relayed call (`receiveSide.call`). Present in live impl. |
| `0x84d61c97` | `receiveRequestV2Signed(bytes,address,bytes)` | MPC-signed execution variant. |
| `0x19117d93` | `setTransmitterStatus(address,bool)` | owner — relayer allowlist. |
| `0x5b7b018c` | `changeMPC(address)` | owner/MPC — rotate MPC, emit `LogChangeMPC`. Present in live impl. |
| `0xf75c2664` | `mpc()` → `address` | current MPC (ETH: resolves to `0x5ddc2587b85c664083677654e77a472511fb537c`, confirmed). |

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

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Proxy impls read live from the EIP-1967 slot. ProxyAdmin (admin slot) = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`.

| Role | Address | Impl (if proxy) | One-liner |
|------|---------|-----------------|-----------|
| **MetaRouter** | `0xf621Fb08BBE51aF70e7E0F4EA63496894166Ff7F` | — (immutable, 7,422 B) | Entry point; `metaRoute`. |
| **MetaRouterGateway** | `0xfCEF2Fe72413b65d3F393d278A714caD87512bcd` | — (immutable) | Token-pull escrow; approve here. |
| **Portal** (proxy) | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x57dbcb192fa64bf07eab76941d1dae5177c8f4f3` | Vault; emits `SynthesizeRequest`/`BurnCompleted`. |
| **Synthesis** (proxy) | `0xD7c3DF25683871d18BC838E4F619126442Dd38B3` | `0x14078ebe3b6dd51c089188c1962ddc94a647be35` | sToken minter; emits `BurnRequest`/`SynthesizeCompleted`. |
| **SyntFabric** (proxy) | `0xbBFb7cb70f84fb6fE1Cb13e42A0B71EFDe769428` | `0x71e761c2b3cd3d56ab33a145b3524ca5bdbc5238` | sToken registry. |
| **BridgeV2** (proxy) | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0x20c54cc697329333fe00ded49c7dca8c83dce65b` | Relay; emits `OracleRequest`. `mpc()` = `0x5ddc2587…`. |
| **MulticallRouter** | `0x49d3Fc00f3ACf80FABCb42D7681667B20F60889A` | — (immutable) | Multi-hop swap executor. |

---

## 4. Addresses — Base mainnet (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com` on 2026-06-09. **Full deployment incl. Synthesis + Fabric.** ProxyAdmin = `0x1ac4c50080871d7a24dd705de9efe5ff14bc0ea2` (Base-specific, differs from ETH).

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x691df9C4561d95a4a726313089c8536dd682b946` | — |
| MetaRouterGateway | `0x41Ae964d0F61Bb5F5e253141A462aD6F3b625B92` | — |
| **Portal** | `0xEE981B2459331AD268cc63CE6167b446AF4161f8` | `0x253ddb32f0f45ffbc0ebcdfc5edd47857aff79d7` |
| **Synthesis** | `0x9F6424FE88fBe7785Fa34F0E369F192bF38E7A6e` | `0x9d74807b8fa79d49bb95cf988af3c25fb1437b4f` |
| **SyntFabric** | `0x44487a445a7595446309464A82244B4bD4e325D5` | `0x464c30aebacd4e8928167c567f8920d16f203027` |
| **BridgeV2** | `0x8097f0B9f06C27AF9579F75762F971D745bb222F` | `0x88139ad1199e8c78a0804d4bebf4fbad89ef9d89` |
| MulticallRouter | `0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9` | — |

> **Collision warning:** Base **SyntFabric** literal `0x44487a445a…` is the **MetaRouter on BNB**, and Base **MulticallRouter** `0x01A3c8E513…` is the **Portal on Arbitrum**. Key on `(chainId, address)`.

---

## 5. Addresses — BNB / Avalanche / Arbitrum / Optimism / Polygon

All verified via `eth_getCode` on the respective publicnode RPC on 2026-06-09.

### 5.1 BNB Smart Chain (chain ID 56) — full deployment incl. Synthesis + Fabric. ProxyAdmin = `0xda8057acb94905eb6025120cb2c38415fd81bfeb`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x44487a445a7595446309464A82244B4bD4e325D5` | — |
| MetaRouterGateway | `0x5c97D726bf5130AE15408cE32bc764e458320D2f` | — |
| **Portal** | `0x5Aa5f7f84eD0E5db0a4a85C3947eA16B53352FD4` | `0x80347bfc5cb91bf99187f4205d56751bc9b51630` |
| **Synthesis** | `0x6B1bbd301782FF636601fC594Cd7Bfe74871bfaA` | `0x755a967298c96d50216c6ed8d68869747b4f6878` |
| **SyntFabric** | `0xc17d768Bf4FdC6f20a4A0d8Be8767840D106D077` | `0xda1c70c902746996a8c989bb07aa6c408ef880d8` |
| **BridgeV2** | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x291a42bdffe3754eb3c8b69b4d232fa1d4a46608` |
| MulticallRouter | `0x44b5d0F16Ad55c4e7113310614745e8771b963bB` | — |

> **Collision:** BNB **BridgeV2** literal `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` is the **Portal on ETH and Polygon**. Same literal, different role per chain.

### 5.2 Arbitrum One (chain ID 42161) — full deployment incl. Synthesis + Fabric. ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75` (shared with ETH).

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0xf7e96217347667064DEE8f20DB747B1C7df45DDe` | — |
| MetaRouterGateway | `0x80ddDDa846e779cceE463bDC0BCc2Ae296feDaF9` | — |
| **Portal** | `0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9` | `0x2e04409f950a236690be6e119f34f7fc209d27c1` |
| **Synthesis** | `0x326adbE46D7E6C1B3927e9309B96DF478bda6D16` | `0x3941870e18ae68b0cf572b7a543c6647e836cbb1` |
| **SyntFabric** | `0x2eE9559387b806E88fd46b9DA160D64A29CE7Da0` | `0xf621fb08bbe51af70e7e0f4ea63496894166ff7f` |
| **BridgeV2** | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0xff9b21c3bfa4bce9b20b55fed56d102ced48b0f6` |
| MulticallRouter | `0xda8057acB94905eb6025120cB2c38415Fd81BfEB` | — |

> Note Arbitrum **SyntFabric impl** `0xf621fb08bbe51af70e7e0f4ea63496894166ff7f` is the **MetaRouter literal on ETH** — coincidental address reuse, not a logical link.

### 5.3 Avalanche C-Chain (chain ID 43114) — depository spoke; **NO Synthesis, NO SyntFabric** (`0x0` in config, confirmed). ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x6F0f6393e45fE0E7215906B6f9cfeFf53EA139cf` | — |
| MetaRouterGateway | `0x4cfA66497Fa84D739a0f785FBcEe9196f1C64e4a` | — |
| **Portal** | `0xE75C7E85FE6ADd07077467064aD15847E6ba9877` | `0x8dc3151dccd58fcb6a0bec0df20c06fba133f027` |
| **Synthesis** | — | **NOT DEPLOYED** |
| **SyntFabric** | — | **NOT DEPLOYED** |
| **BridgeV2** | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | `0x7057ab3fb2bee9c18e0cde4240de4ff7f159e365` |
| MulticallRouter | `0xDc9a6a26209A450caC415fb78487e907c660cf6a` | — |

> **Scope-hint correction:** the prompt's "MetaRouter `0xE75C7E85FE6ADd07077467064aD15847E6ba9877`" is, in the live SDK config and on-chain, the **Avalanche Portal** — not the MetaRouter. The Avalanche MetaRouter is `0x6F0f6393…`. Verified by `eth_getCode` + config role mapping.

### 5.4 Optimism (chain ID 10) — depository spoke; **NO Synthesis, NO SyntFabric**. ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0x0f91052dc5B4baE53d0FeA5DAe561A117268f5d2` | — |
| MetaRouterGateway | `0x200a0fe876421DC49A26508e3Efd0a1008fD12B5` | — |
| **Portal** | `0x292fC50e4eB66C3f6514b9E402dBc25961824D62` | `0x7b4e28e7273aa8cb64c56ff191ebf43b64f409f9` |
| **Synthesis** / **SyntFabric** | — | **NOT DEPLOYED** |
| **BridgeV2** | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0x7057ab3fb2bee9c18e0cde4240de4ff7f159e365` |
| MulticallRouter | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | — |

> **Collision:** OP **Portal** `0x292fC50e…` is the **BridgeV2 on Avalanche**; OP **MulticallRouter** `0xb8f275fB…` is the **Portal on ETH/Poly and the Bridge on BNB**. Always key on `(chainId, role)`.

### 5.5 Polygon PoS (chain ID 137) — depository spoke; **NO Synthesis, NO SyntFabric**. ProxyAdmin = `0x1da522b35363c1eda4833bc121c8f3c67b2caa75`.

| Role | Address | Impl (if proxy) |
|------|---------|-----------------|
| MetaRouter | `0xa260E3732593E4EcF9DdC144fD6C4c5fe7077978` | — |
| MetaRouterGateway | `0xAb83653fd41511D638b69229afBf998Eb9B0F30c` | — |
| **Portal** | `0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8` | `0x35d39bb2cbc51ce6c03f0306d0d8d56948b1f990` |
| **Synthesis** / **SyntFabric** | — | **NOT DEPLOYED** |
| **BridgeV2** | `0x5523985926Aa12BA58DC5Ad00DDca99678D7227E` | `0x7057ab3fb2bee9c18e0cde4240de4ff7f159e365` |
| MulticallRouter | `0xc5B61b9abC3C6229065cAD0e961aF585C5E0135c` | — |

> Avalanche, Optimism and Polygon **share the same BridgeV2 implementation** `0x7057ab3fb2bee9c18e0cde4240de4ff7f159e365` (different proxy literals, identical logic). On Optimism and Polygon the Bridge proxy literal is also identical (`0x5523985926…`).

---

## 6. Counterparty chains outside the seven (findings, not omissions)

The SDK config (`js-sdk/src/crosschain/config/mainnet.ts`) defines ~50 mainnet chains. Beyond the seven targets, Symbiosis cores were verified present in config on (selected, by role):

- **Synthesis-bearing manager chains (off-target):** **Symbiosis hub `13863860`** (the canonical synth-minting chain: Synthesis `0x45CFd6FB7999328F189aaD2739Fba4Be6C45E5bf`, Bridge `0x1a039cE63AE35a67Bf0E9F6DbFaE969639D59eC8`, Fabric `0xf85FC807D05d3Ab2309364226970aAc57b4e1ea4`, **no Portal** — it is a pure mint/burn hub), **Telos `40`**, **zkSync Era `324`**, **Bahamut `5165`**, **Rootstock `30`**, **ZetaChain `7000`**, **Citrea `4114`**, **Quai `9`**.
- **Portal-only spokes (off-target):** Kava `2222`, Boba `288`, Arbitrum Nova `42170`, Polygon zkEVM `1101`, Linea `59144`, Mantle `5000`, Scroll `534352`, Manta `169`, Metis `1088`, Mode `34443`, Blast `81457`, Merlin `4200`, zkLink `810180`, Core `1116`, Taiko `167000`, Sei `1329`, Cronos `25`/`388`, Fraxtal `252`, Gravity `1625`, BSquared `223`, Morph `2818`, Goat `2345`, Sonic `146`, Abstract `2741`, **Gnosis `100`**, Berachain `80094`, **Unichain `130`**, Soneium `1868`, opBNB `204`, Hyperliquid `999`, Katana `747474`, ApeChain `33139`, Plasma `9745`, Monad `143`, Tempo `4217`.
- **Non-EVM counterparties** (bridged via dedicated adapters, not the EVM Portal): **Bitcoin** (chainId `3652501241`, symBTC pool), **TON** (`85918`, `TonBridge` + `BurnRequestTON`), **Tron** (`728126428`), **Solana** (`5426`).

These are **not** deployed on the seven target chains in the documented role — they are the bridge's remote endpoints. A `SynthesizeRequest.chainID` on a target-chain Portal frequently points at one of these off-target chains (commonly the hub `13863860`).

---

## 7. Cross-chain summary

| Chain | ID | MetaRouter | Gateway | Portal | Synthesis | SyntFabric | BridgeV2 | MulticallRouter |
|-------|----|-----------|---------|--------|-----------|-----------|----------|-----------------|
| Ethereum | 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Base | 8453 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BNB | 56 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Arbitrum | 42161 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Avalanche | 43114 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| Optimism | 10 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| Polygon | 137 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |

**Synthesis + SyntFabric live on ETH/Base/BNB/Arb only; the other three are depository spokes (Portal + Bridge + MetaRouter only).** No single vanity address: the same literals recur in *different roles* across chains (see collision warnings in §§4–5).

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Portal** | EIP-1967 **Transparent** | impl slot `0x360894…bbc` set + admin slot `0xb53127…6103` set (~2,112–2,141 B proxy) | ProxyAdmin (per-chain, §3–5) → `Upgraded` |
| **Synthesis** | EIP-1967 **Transparent** | impl + admin slots set | ProxyAdmin → `Upgraded` |
| **SyntFabric** | EIP-1967 **Transparent** | impl + admin slots set | ProxyAdmin → `Upgraded` |
| **BridgeV2** | EIP-1967 **Transparent** | impl + admin slots set; impl exposes `mpc()`/`changeMPC` | ProxyAdmin (upgrade) + MPC (operational) → `Upgraded` / `LogChangeMPC` |
| **MetaRouter** | **Immutable** (no proxy) | impl slot returns `0x0`; full 7,422 B runtime on every chain | none |
| **MetaRouterGateway** | **Immutable** | impl slot `0x0`; 1,081 B; deployed by MetaRouter's constructor | none |
| **MulticallRouter** | **Immutable** | impl slot `0x0`; 3,558–3,617 B | none |

EIP-1967 implementation slot read live (`eth_getStorageAt`) per chain — current impls listed in §§3–5. **ProxyAdmin (admin slot) clusters into three values:** `0x1da522b35363c1eda4833bc121c8f3c67b2caa75` (ETH, Avax, Arb, Op, Poly), `0x1ac4c50080871d7a24dd705de9efe5ff14bc0ea2` (Base), `0xda8057acb94905eb6025120cb2c38415fd81bfeb` (BNB). **MetaRouter / MetaRouterGateway / MulticallRouter are confirmed NOT proxies** — `eth_getStorageAt` at the impl slot returns all-zero on every chain, and they carry full multi-KB runtime bytecode (an immutable would). The upgradeable surface to monitor is therefore exactly the four Transparent proxies via the `Upgraded(address)` topic `0xbc7cd75a…2d3b`.

---

## 9. Detection invariants & gotchas

1. **`SynthesizeRequest` (Portal) and `BurnRequest` (Synthesis) share the identical parameter layout `(bytes32,address,uint256,address,address,uint256,address)` but have DIFFERENT topic0s** (`0x31325fe0…` vs `0x5f00e8f0…`) because the event *names* differ. Don't conflate them. Both carry `id` non-indexed + 3 indexed (`from`, `chainID`, `revertableAddress`) → 4 log topics.
2. **The cross-chain key is `id` / `externalID` (bytes32), not a sequential nonce.** Match a source `SynthesizeRequest.id` to the destination `SynthesizeCompleted.id` / `BurnCompleted.id` (and the `OracleRequest.callData` carries the same id encoded). `crossChainID` is the second correlation field on completion events.
3. **`OracleRequest` (BridgeV2) is the relayer fan-out and fires on EVERY cross-chain send** — it's the most reliable "a bridge tx happened here" signal. All params are non-indexed (only topic0), so you must ABI-decode the data to get `receiveSide`/`oppositeBridge`/`chainId`.
4. **The real user is `from` in `SynthesizeRequest`/`BurnRequest`, NOT `tx.origin`.** Most flows arrive through MetaRouter/MetaRouterGateway, so `tx.to` is the router and `msg.sender` to the Portal is the MetaRouter. Attribute to the event's `from`/`to`, and use `ClientIdLog.clientId` for integrator attribution.
5. **Synthesis + SyntFabric do NOT exist on Avalanche, Optimism, Polygon.** If you scan for `BurnRequest`/`SynthesizeCompleted` on those three you'll find nothing — that's correct, not a missing feed. Those chains only lock/release real tokens via the Portal.
6. **No single vanity address — heavy literal reuse across chains in *different roles*.** Examples: `0x5523985926…` = Bridge on ETH/Poly/Arb/Op but ProxyAdmin/role varies; `0xb8f275fB…` = Portal on ETH/Poly, Bridge on BNB, MulticallRouter on OP; `0x01A3c8E5…` = Portal on Arb, MulticallRouter on Base; `0x44487a44…` = MetaRouter on BNB, SyntFabric on Base; `0x292fC50e…` = Bridge on Avax, Portal on OP. **Always key on `(chainId, address, role)`.**
7. **`mpc()` (BridgeV2) is the single trusted relayer key.** A `LogChangeMPC` or `SetTransmitterStatus` event is a top-severity governance/security signal — a compromised MPC can mint/release arbitrarily. Current ETH `mpc()` = `0x5ddc2587b85c664083677654e77a472511fb537c`.
8. **`BurnRequestTON` encodes the destination as a TON `(int8 workchain, bytes32 address_hash)` tuple, not an EVM address** — different topic0 (`0xb22f66d5…`) and a non-address `to`. Only fires where TON is a destination.
9. **sTokens are plain ERC-20s** minted/burned by SyntFabric: a mint is `Transfer(0x0 → user)`, a burn is `Transfer(user → 0x0)` on the sToken contract. Most live on the off-target hub chain `13863860`; on target chains they appear only where Synthesis exists (ETH/Base/BNB/Arb).
10. **`stableBridgingFee` is skimmed to the Bridge inside `unsynthesize`/`mint`** — the user receives `amount - stableBridgingFee`. `BurnCompleted.amount` / `SynthesizeCompleted.amount` are already net of fee; `bridgingFee` is a separate field.
11. **`metaUnsynthesize` with empty `_finalCalldata` emits `BurnCompleted` with `to = address(this)` (the Portal)** rather than the end user — the swap-and-forward path. Don't misattribute that to the Portal as a recipient.
12. **`metaSynthesize`/`metaBurnSyntheticToken`/`metaMintSyntheticToken` take a single struct argument** — the selectors (`0xce654c17`, `0xe66bb550`, `0xc29a91bc`) are computed over the *expanded tuple type list* with struct names erased. The plain `synthesize`/`burnSyntheticToken` 9-arg variants are different selectors.
13. **MetaRouter/Gateway/MulticallRouter are immutable** — never expect an `Upgraded` from them; only the four Transparent proxies (Portal/Synthesis/Fabric/Bridge) can rotate impls.
14. **`SynthesizeRequest.chainID` is the DESTINATION chain id and is frequently the off-target hub `13863860`** (or Bitcoin/TON/Tron ids), not one of the seven. Don't drop a request just because its `chainID` isn't in your target set.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- Portal
TOPIC_SYNTHESIZE_REQUEST       = '\x31325fe0a1a2e6a5b1e41572156ba5b4e94f0fae7e7f63ec21e9b5ce1e4b3eab'
TOPIC_BURN_COMPLETED           = '\xaeef64b7687b985665b6620c7fa271b6f051a3fbe2bfc366fb9c964602eb6d26'
TOPIC_REVERT_BURN_REQUEST      = '\x40590cc12db0488520ce425059f83f8caed91bdf98de5ff829dc57c63843161b'
TOPIC_META_REVERT_REQUEST      = '\xbd03c66ec5bd3d01fbf22bc794f68ac88b693023b438724019205a4b42aefb20'
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

-- ===== Addresses — Base (chain ID 8453) =====
BASE_METAROUTER                = '\x691df9c4561d95a4a726313089c8536dd682b946'
BASE_METAROUTER_GATEWAY        = '\x41ae964d0f61bb5f5e253141a462ad6f3b625b92'
BASE_PORTAL                    = '\xee981b2459331ad268cc63ce6167b446af4161f8'
BASE_SYNTHESIS                 = '\x9f6424fe88fbe7785fa34f0e369f192bf38e7a6e'
BASE_FABRIC                    = '\x44487a445a7595446309464a82244b4bd4e325d5'
BASE_BRIDGE                    = '\x8097f0b9f06c27af9579f75762f971d745bb222f'
BASE_MULTICALL_ROUTER          = '\x01a3c8e513b758ebb011f7afaf6c37616c9c24d9'
BASE_PROXY_ADMIN               = '\x1ac4c50080871d7a24dd705de9efe5ff14bc0ea2'

-- ===== Addresses — BNB (chain ID 56) =====
BSC_METAROUTER                 = '\x44487a445a7595446309464a82244b4bd4e325d5'
BSC_METAROUTER_GATEWAY         = '\x5c97d726bf5130ae15408ce32bc764e458320d2f'
BSC_PORTAL                     = '\x5aa5f7f84ed0e5db0a4a85c3947ea16b53352fd4'
BSC_SYNTHESIS                  = '\x6b1bbd301782ff636601fc594cd7bfe74871bfaa'
BSC_FABRIC                     = '\xc17d768bf4fdc6f20a4a0d8be8767840d106d077'
BSC_BRIDGE                     = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
BSC_MULTICALL_ROUTER           = '\x44b5d0f16ad55c4e7113310614745e8771b963bb'
BSC_PROXY_ADMIN                = '\xda8057acb94905eb6025120cb2c38415fd81bfeb'

-- ===== Addresses — Avalanche (chain ID 43114) — NO Synthesis/Fabric =====
AVAX_METAROUTER                = '\x6f0f6393e45fe0e7215906b6f9cfeff53ea139cf'
AVAX_METAROUTER_GATEWAY        = '\x4cfa66497fa84d739a0f785fbcee9196f1c64e4a'
AVAX_PORTAL                    = '\xe75c7e85fe6add07077467064ad15847e6ba9877'
AVAX_BRIDGE                    = '\x292fc50e4eb66c3f6514b9e402dbc25961824d62'
AVAX_MULTICALL_ROUTER          = '\xdc9a6a26209a450cac415fb78487e907c660cf6a'
AVAX_PROXY_ADMIN               = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'

-- ===== Addresses — Arbitrum (chain ID 42161) =====
ARB_METAROUTER                 = '\xf7e96217347667064dee8f20db747b1c7df45dde'
ARB_METAROUTER_GATEWAY         = '\x80dddda846e779ccee463bdc0bcc2ae296fedaf9'
ARB_PORTAL                     = '\x01a3c8e513b758ebb011f7afaf6c37616c9c24d9'
ARB_SYNTHESIS                  = '\x326adbe46d7e6c1b3927e9309b96df478bda6d16'
ARB_FABRIC                     = '\x2ee9559387b806e88fd46b9da160d64a29ce7da0'
ARB_BRIDGE                     = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
ARB_MULTICALL_ROUTER           = '\xda8057acb94905eb6025120cb2c38415fd81bfeb'
ARB_PROXY_ADMIN                = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'

-- ===== Addresses — Optimism (chain ID 10) — NO Synthesis/Fabric =====
OP_METAROUTER                  = '\x0f91052dc5b4bae53d0fea5dae561a117268f5d2'
OP_METAROUTER_GATEWAY          = '\x200a0fe876421dc49a26508e3efd0a1008fd12b5'
OP_PORTAL                      = '\x292fc50e4eb66c3f6514b9e402dbc25961824d62'
OP_BRIDGE                      = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
OP_MULTICALL_ROUTER            = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
OP_PROXY_ADMIN                 = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'

-- ===== Addresses — Polygon (chain ID 137) — NO Synthesis/Fabric =====
POLY_METAROUTER                = '\xa260e3732593e4ecf9ddc144fd6c4c5fe7077978'
POLY_METAROUTER_GATEWAY        = '\xab83653fd41511d638b69229afbf998eb9b0f30c'
POLY_PORTAL                    = '\xb8f275fbf7a959f4bce59999a2ef122a099e81a8'
POLY_BRIDGE                    = '\x5523985926aa12ba58dc5ad00ddca99678d7227e'
POLY_MULTICALL_ROUTER          = '\xc5b61b9abc3c6229065cad0e961af585c5e0135c'
POLY_PROXY_ADMIN               = '\x1da522b35363c1eda4833bc121c8f3c67b2caa75'

-- ===== Off-target Symbiosis hub (chain ID 13863860) — Synthesis hub, no Portal =====
HUB_SYNTHESIS                  = '\x45cfd6fb7999328f189aad2739fba4be6c45e5bf'
HUB_BRIDGE                     = '\x1a039ce63ae35a67bf0e9f6dbfae969639d59ec8'
HUB_FABRIC                     = '\xf85fc807d05d3ab2309364226970aac57b4e1ea4'
```

---

## 11. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` (event topic0) and `keccak256(canonical signature)[0:4]` (selector) with keccak-256, from the canonical Solidity in `symbiosis-finance/core-contracts` (`Portal.sol`, `Synthesis.sol`, `bridge/BridgeV2.sol`, `SyntFabric.sol`, `metarouter/MetaRouter.sol`, `metarouter/MetaRouterGateway.sol`, `metarouter/MetaRouteStructs.sol`, `periphery/MulticallRouter.sol`). The keccak recipe was self-validated by reproducing the canonical `Transfer(address,address,uint256)` topic0.
- **Live-log cross-checks (`eth_getLogs`):** `SynthesizeRequest` (1,535 logs) and `BurnCompleted` (1,594) on the ETH Portal `0xb8f2…81A8`; `OracleRequest` (1,540) on the ETH Bridge `0x5523…227E` — all in a 49,000-block window ending block 25279512. `SynthesizeCompleted` confirmed live on the BNB Synthesis `0x6B1b…bfaA`. The 4-topic count on `SynthesizeRequest` confirms `id` non-indexed + 3 indexed params, matching the source.
- **Selector presence in live impl bytecode:** scanned the ETH implementations — Portal impl `0x57db…f4f3` (`synthesize` `0xb1659a3c`, `metaSynthesize` `0xce654c17`, `unsynthesize` `0x1ebe53ef`); MetaRouter `0xf621…Ff7F` (`metaRoute` `0xa11b1198`, `metaMintSwap` `0x3bc78835`, `externalCall` `0xf5b697a5`); Bridge impl `0x20c5…e65b` (`receiveRequestV2` `0xf7f1baf0`, `transmitRequestV2` `0x6cebc9c2`, `changeMPC` `0x5b7b018c`) — all present.
- **Addresses:** parsed from the authoritative SDK registry `symbiosis-finance/js-sdk/src/crosschain/config/mainnet.ts` (with chain ids resolved against `js-sdk/src/constants.ts`), then existence-checked via `eth_getCode` (non-empty bytecode) on each of the seven publicnode RPCs. Avalanche/Optimism/Polygon `synthesis` + `fabric` are `0x0` in the registry and confirmed absent. Wiring spot-checks (`eth_call`): ETH `MetaRouterGateway.metaRouter()` → `0xf621…Ff7F`, ETH `Synthesis.fabric()` → `0xbBFb…9428`, ETH `Portal.bridge()` → `0x5523…227E`, ETH `Bridge.mpc()` → `0x5ddc2587…`.
- **Proxy classification:** EIP-1967 impl slot `0x360894…bbc` and admin slot `0xb53127…6103` read live with `eth_getStorageAt` on every chain. Portal/Synthesis/Fabric/Bridge → both slots populated (Transparent); MetaRouter/Gateway/MulticallRouter → impl slot all-zero + multi-KB runtime (immutable). Per-chain impls + ProxyAdmin literals recorded in §§3–5/§8.

**Authoritative sources:**
- Canonical contracts: [`github.com/symbiosis-finance/core-contracts`](https://github.com/symbiosis-finance/core-contracts) (`contracts/synth-core/`, `contracts/periphery/`).
- Address registry / SDK: [`github.com/symbiosis-finance/js-sdk`](https://github.com/symbiosis-finance/js-sdk) — `src/crosschain/config/mainnet.ts`, `src/constants.ts`.
- Docs: [`docs.symbiosis.finance`](https://docs.symbiosis.finance) (contract addresses + architecture).
- Explorers (existence + impl): [Etherscan](https://etherscan.io/address/0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8), [Basescan](https://basescan.org/address/0xEE981B2459331AD268cc63CE6167b446AF4161f8), [BscScan](https://bscscan.com/address/0x5Aa5f7f84eD0E5db0a4a85C3947eA16B53352FD4), [Snowscan](https://snowscan.xyz/address/0xE75C7E85FE6ADd07077467064aD15847E6ba9877), [Arbiscan](https://arbiscan.io/address/0x01A3c8E513B758EBB011F7AFaf6C37616c9C24d9), [Optimistic Etherscan](https://optimistic.etherscan.io/address/0x292fC50e4eB66C3f6514b9E402dBc25961824D62), [PolygonScan](https://polygonscan.com/address/0xb8f275fBf7A959F4BCE59999A2EF122A099e81A8).

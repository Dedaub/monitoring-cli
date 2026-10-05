# Eco Routes — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, Arc; retired Portal on BNB and Robinhood Chain; NOT Avalanche)

**Status:** verified on 2026-09-29 and re-verified on 2026-10-05 (Portal migration of 2026-09-29, routes-ts 3.2.23/3.2.24) against live RPC on all nine target chains, the `@eco-foundation/routes-ts` npm package (the `deployAddresses.csv` of every published version from 0.0.714-beta to 3.2.24, and the Portal, Executor, IntentSource, Inbox and prover ABIs), the verified sources on Blockscout (Portal, Executor, HyperProver, CCIPProver, ECDSAExecutor), and the Eco docs (architecture, provers, contract addresses, the `/v1/chains` API reference). Topic0s and selectors are recomputed as `keccak256(sig)`. Addresses are existence-checked with `eth_getCode`. `executor()`, `version()`, `getProofType()` and `PORTAL()` are read live.
**Scope:** Eco Routes, the intent bridge of Eco: the current **Portal** generation (routes-ts 3.2.23+: Portal, Executor, per-intent Vaults, provers), the older Portal addresses, and the legacy **IntentSource + Inbox** pairs of routes-ts 1.x and 2.x. Chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Arc (5042) carry the current Portal; BNB Smart Chain (56) and Robinhood Chain (4663) carry only the retired 3.2.19–3.2.22 Portal; Avalanche C-Chain (43114) has no deployment. Topics and selectors are chain-agnostic. Addresses are network-specific.

Eco Routes is an intent protocol. On the source chain, a user **publishes** an intent on the Portal and **funds** a Vault that belongs to that intent alone. On the destination chain, a solver **fulfills** the intent through the Portal: the solver's tokens go through the Executor to the recipient. The destination Portal then **dispatches a proof** through the prover that the user chose (for example Hyperlane, Polymer, LayerZero, CCIP or Metalayer). When the proof arrives, the source-chain prover records it, and the solver **withdraws** the reward from the Vault. If no solver fulfills before the deadline, the creator **refunds** the Vault. The Portal holds no funds between transactions.

**The link key is `intentHash`**, and it is on chain on both sides. `intentHash = keccak256(abi.encodePacked(destination, routeHash, rewardHash))`. It is topic1 of `IntentPublished` (source), topic1 of `IntentFulfilled` and of the Portal's `IntentProven` (destination), topic1 of the prover's `IntentProven` (source), and the first data word of `IntentFunded`, `IntentWithdrawn` and `IntentRefunded` (source). The current Portal address `0xEC000769A73b70e16f361a442292500b3BCf4A85` is the same on every chain that has it. It is immutable: no proxy, no owner, no pause. **The previous Portal `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` is retired:** the new Portal emitted its first events on 2026-09-29, and the old Portal emitted its last observed events on Ethereum 2026-09-30 17:40 UTC, Arbitrum 2026-09-30 23:31 UTC and Base 2026-10-01 12:56 UTC, and it had 0 events in the 24 hours to 2026-10-05 10:00 UTC. An alert keyed on the old address misses all new intents.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Where (of the eight) |
|----------|------|--------|-------|
| **Portal** (routes-ts 3.2.23+, `version()` = "2.12.0") | Source side: publish, fund, withdraw, refund; ERC-7683 origin settler (`open`). Destination side: fulfill, cancel, prove; ERC-7683 destination settler (`fill`). | **No** (24,197 B; the code hash differs per chain) | ETH, Base, Arb, OP, Poly, Arc |
| **Executor** | Created by the Portal. Runs the route's calls on the destination. Only the Portal can call it. No storage. | No (1,642 B, one code hash) | same six chains |
| **Vault** (one per intent) | Escrow of one intent's reward, at a CREATE2 address from the Portal and the intent hash. Deployed on first funding or on withdraw/refund. A 75-byte proxy that delegates to the Vault implementation. | per-intent minimal proxy | same six chains |
| **Vault implementation** | Logic of every Vault. | No (4,370 B, one code hash) | same six chains |
| **HyperProver** (current, routes-ts 3.2.23+) | Hyperlane prover: sends the proof from the destination through the Hyperlane Mailbox, records it on the source. `version()` = "2.12.0". | No (7,891 B) | ETH, Base, Arb, OP, Poly, Arc |
| **PolymerProver** (current, routes-ts 3.2.23+) | Polymer (IBC light client) prover. | No (11,784 B, one code hash) | ETH, Base, Arb, OP, Poly, Arc |
| **CCIPProver** (current) | Chainlink CCIP prover for the current Portal (`PORTAL()` = the current Portal). Not in the routes-ts address file. | No (8,125 B) | ETH, Base |
| Portal (routes-ts 3.2.19–3.2.22, `version()` = "2.6") | **Retired 2026-09-30/10-01** (last events, see above). Same event set minus `IntentCancelled`. Late withdrawals and refunds of its Vaults can still come from it. | No (22,537 B) | ETH, Base, Arb, OP, Poly, BNB; Robinhood Chain (unlisted) |
| Executor / Vault implementation (3.2.19–3.2.22) | Executor and Vault logic of the retired Portal. | No (1,642 B / 4,203 B) | same seven chains |
| HyperProver (routes-ts 3.2.21–3.2.22) | Hyperlane prover of the retired Portal. | No | ETH, Base, Arb, OP, Poly, Arc |
| PolymerProver (3.2.20–3.2.22) and the unlisted PolymerProver / CCIPProver of the retired Portal | §3. | No | see §3–§7 |
| Portal (routes-ts 3.2.19–3.2.22, Arc only) | Arc had its own address `0xEC002CA16cE20c2a9F3C6200EF04E7d92a3dfBD8` (`version()` = "2.10.0"), replaced by the current Portal. | No (23,650 B) | Arc |
| **LayerZeroProver** (routes-ts 3.2.18) | LayerZero prover. | No | ETH, Base, Arb, OP, Poly |
| **MetaProver** (routes-ts 2.8.1–3.2.18) | Caldera Metalayer prover. | No | Base, Arb |
| **HyperProver** (routes-ts 3.2.17–3.2.20) | Previous Hyperlane prover. | No | ETH, Base, Arb, OP, Poly, BNB |
| Portal (routes-ts 3.2.4–3.2.18) | Previous Portal. Same event set. | No | ETH, Base, Arb, OP, Poly, BNB |
| Portal (routes-ts 3.2.1–3.2.2) | Older Portal. | No | ETH, Base, Arb, OP, Poly, BNB |
| Portal (routes-ts 3.0.0-alpha) | Pre-release Portal. | No | ETH, Base, Arb, OP, Poly, BNB |
| **IntentSource + Inbox** (routes-ts 2.8.x) | Legacy source contract and destination contract. | No | ETH, Base, Arb, OP, Poly, BNB |
| IntentSource + Inbox (routes-ts 1.21.2) | Legacy pair. | No | Base, Arb, OP |
| ECDSAExecutor (not Routes) | An ERC-7579 smart-account module. Eco's `/v1/chains` API names it `executor`. In the sampled Ethereum fulfillment, the solver sends `fulfill` through it. | No | ETH, Base, Arb, OP, Poly, BNB |

Between 0.1.10-beta and 2.7.0, routes-ts published 29 IntentSource addresses (the 1.21.2 one is listed here), each with its own Inbox and HyperProver, on Optimism, Base and Arbitrum (most also on Ethereum and Polygon). Their addresses are in the `deployAddresses.csv` of each package version. This file lists the last two pairs and the Portal generation.

### Chain and domain ids

`IntentPublished.destination` is a `uint64` **chain id**: Ethereum 1, Base 8453, Arbitrum 42161, Optimism 10, Polygon 137, Arc 5042, BNB 56. Eco uses 1399811149 for Solana and 728126428 for Tron. The provers take their own domain ids in `sourceChainDomainID` (for example a Hyperlane domain or a LayerZero eid); the Portal docs warn that it is not the chain id. In the sampled Ethereum fulfillment, the Hyperlane message goes to domain 1399811149 (Solana), the source of that intent.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Portal — source side

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x43974895be1bcec7344337863fa7de24a0d1c315c0a994f663fe0ee220ddc8e4` | `IntentPublished(bytes32 indexed intentHash, uint64 destination, bytes route, address indexed creator, address indexed prover, uint64 rewardDeadline, uint256 rewardNativeAmount, (address token, uint256 amount)[] rewardTokens)` | **Source leg (the intent).** No value moves. `prover` (topic3) names the prover contract. `route` is the ABI-encoded route for the destination. |
| `0xc1ed05721d27ad6b2555d61388ac393b120f5cc0e6009e53230e02c68e60064a` | `IntentFunded(bytes32 intentHash, address funder, bool complete)` | **Source leg (the value).** Emitted when funds go from `funder` to the intent's Vault through the Portal. `complete` = fully funded. No field is indexed. |
| `0xbb062c23e818de8ea9c157514eb098052cf36904bbe431cd50d4ec92264ca3ac` | `IntentWithdrawn(bytes32 intentHash, address indexed claimant)` | **Vault pays the solver** (reward to `claimant`) after the proof. |
| `0x8d53c2b04800cf061b987a07179bb6c9730c05536b2f6a3a091fe62303682eb6` | `IntentRefunded(bytes32 intentHash, address indexed refundee)` | **Refund.** Vault → `refundee` after the deadline. |
| `0x21ea3a531675a90b5b0263d6dc9be64e34e0bfd422a8b428b2d0729c5d4446e4` | `IntentTokenRecovered(bytes32 intentHash, address indexed refundee, address indexed token)` | A token that is not in the reward is sent from the Vault to `refundee`. |
| `0x3448bbc2203c608599ad448eeb1007cea04b788ac631f9f558e8dd01a3c27b3d` | `Open(bytes32 indexed orderId, (address user, uint256 originChainId, uint32 openDeadline, uint32 fillDeadline, bytes32 orderId, (bytes32 token, uint256 amount, bytes32 recipient, uint256 chainId)[] maxSpent, (bytes32 token, uint256 amount, bytes32 recipient, uint256 chainId)[] minReceived, (uint256 destinationChainId, bytes32 destinationSettler, bytes originData)[] fillInstructions) resolvedOrder)` | ERC-7683 origin event (`open`, `openFor`). **The standard ERC-7683 topic: other settlers emit it too.** |

### 1.2 Portal — destination side

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xc471de166a60c0b81727dfa2f57d4fc3ad1b45b057c1f034b7058365613bde8d` | `IntentFulfilled(bytes32 indexed intentHash, bytes32 indexed claimant)` | **Destination leg.** In the same transaction the solver's tokens go through the Executor to the recipient. `claimant` = the solver's reward address on the source chain (`bytes32`). |
| `0xe6d8040a8a6bc519f4e5a42fb2677067c929ddbf2cca9287a44b23fb617a6f00` | `IntentProven(bytes32 indexed intentHash, bytes32 indexed claimant)` | Status only: the destination Portal sent the proof through the prover. |
| `0xc08eb64db16a39d2848960af04e3f16fb404d9d436a9f0e9d7d0d4854715c9dc` | `IntentCancelled(bytes32 indexed intentHash)` | Current Portal only (routes-ts 3.2.23+). The intent is cancelled on the destination (`cancel` / `cancelAndProve`), so no solver can fulfill it. |
| `0x0555709e59fb225fcf12cc582a9e5f7fd8eea54c91f3dc500ab9d8c37c507770` | `OrderFilled(bytes32 orderId, address solver)` | ERC-7683 destination event (`fill`). The legacy Inbox emits the same topic. |

### 1.3 Provers (source side)

The same topics come from every current prover contract (HyperProver, PolymerProver, CCIPProver, LayerZeroProver, MetaProver).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xa79bcebf1cb6259b008ad946df35c764dd6b25206bb5c47ec11976cdce4f0145` | `IntentProven(bytes32 indexed intentHash, address indexed claimant, uint64 destination)` | Status only: the proof arrived on the source chain. The solver can now withdraw. **Different topic0 from the Portal's `IntentProven`.** |
| `0xae165391a85a2219c7e5367bc7775dc0a2bc5cdf1f35e95204d716f6d96c2758` | `IntentProofInvalidated(bytes32 indexed intentHash)` | A proof for the wrong destination was challenged (`challengeIntentProof`). |
| `0xc86ca07015d7e87a46a98098d36c9fc68bc3120761e5c7a2023fc6c6869e5611` | `IntentAlreadyProven(bytes32 intentHash)` | Duplicate proof. |
| `0x3118578fa871ff2006f094c91131c642ba166690133deb2f766c9f1f192c431d` | `DomainRegistered(uint64 indexed domain, uint64 indexed chainId)` | HyperProver constructor only. |

### 1.4 Legacy IntentSource and Inbox (routes-ts 1.x and 2.x)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd802f2610d0c85b3f19be4413f3cf49de1d4e787edecd538274437a5b9aa648d` | `IntentCreated(bytes32 indexed hash, bytes32 salt, uint256 source, uint256 destination, address inbox, (address token, uint256 amount)[] routeTokens, (address target, bytes data, uint256 value)[] calls, address indexed creator, address indexed prover, uint256 deadline, uint256 nativeValue, (address token, uint256 amount)[] rewardTokens)` | Legacy source leg (IntentSource). |
| `0x2da42efda5225344c30e729dc0eafc2e56292ac9b9b5c2b16e0e74c86ea5921d` | `IntentFunded(bytes32 intentHash, address funder)` | Legacy funding. Not the same topic as the Portal's `IntentFunded`. |
| `0x97cf148f008486c490afd3b522e2398d5039247c7fffe81fcae2a8c6ee622103` | `IntentPartiallyFunded(bytes32 intentHash, address funder)` | Legacy. |
| `0x6653a45d3871e4110fa55dac0269f9f93a6d9078d402f7153594e50573d7f0cd` | `Withdrawal(bytes32 hash, address indexed recipient)` | Legacy: vault pays the solver. |
| `0x0ba6f12b978882904e7444c7a8fcadd2d9f692a6a97aa18e5fb44c3bbc580123` | `Refund(bytes32 hash, address indexed recipient)` | Legacy refund. |
| `0x69f2194063569059c6cc65d4599038f27aa9590bbb3f008178b6d20c453b9e82` | `IntentProofChallenged(bytes32 intentHash)` | Legacy (2.8.x). |
| `0x4a817ec64beb8020b3e400f30f3b458110d5765d7a9d1ace4e68754ed2d082de` | `Fulfillment(bytes32 indexed _hash, uint256 indexed _sourceChainID, address indexed _prover, address _claimant)` | Legacy destination leg (Inbox). |
| `0xa576d0af275d0c6207ef43ceee8c498a5d7a26b8157a32d3fdf361e64371628c` | `Open(bytes32 indexed orderId, (address user, uint256 originChainId, uint32 openDeadline, uint32 fillDeadline, bytes32 orderId, (bytes32 token, uint256 amount, bytes32 recipient, uint256 chainId)[] maxSpent, (bytes32 token, uint256 amount, bytes32 recipient, uint256 chainId)[] minReceived, (uint64 destinationChainId, bytes32 destinationSettler, bytes originData)[] fillInstructions) resolvedOrder)` | Legacy `Eco7683OriginSettler` variant with a `uint64` destination chain id. |
| `0x2b45193f790d995b36e39c4104dd1b49df6fc851b6f6ae60f2072724735b5b43` | `IntentProven(bytes32 indexed _hash, address indexed _claimant)` | Legacy prover event (2.x). |
| `0xd6383b4658ff90fe5c7fb8d1fe7a0b6cc87b7ecaf49d2305c1fed682f3954832` | `BatchSent(bytes32[] indexed _hashes, uint256 indexed _sourceChainID)` | Legacy prover event (2.x). |

### 1.5 Value capture

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20. Source: funder → Vault. Destination: solver → Executor, then Executor → recipient. Reward: Vault → claimant. Refund: Vault → refundee. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Portal — source side

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1034b866` | `publish((uint64 destination, (bytes32 salt, uint64 deadline, address portal, uint256 nativeAmount, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward) intent)` | Emits `IntentPublished`. |
| `0x645c890c` | `publish(uint64 destination, bytes route, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward)` | Same, with an encoded route. |
| `0xe353b5e6` | `publishAndFund((uint64 destination, (bytes32 salt, uint64 deadline, address portal, uint256 nativeAmount, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward) intent, bool allowPartial)` | Payable. `IntentPublished` + `IntentFunded`. |
| `0xdf00f8fa` | `publishAndFund(uint64 destination, bytes route, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward, bool allowPartial)` | Payable. |
| `0x60d1c29c` | `publishAndFundFor((uint64 destination, (bytes32 salt, uint64 deadline, address portal, uint256 nativeAmount, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward) intent, bool allowPartial, address funder, address permitContract)` | Payable. Funds from `funder` through a permit contract. |
| `0x55a0bec0` | `publishAndFundFor(uint64 destination, bytes route, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward, bool allowPartial, address funder, address permitContract)` | Payable. |
| `0x9f24b4dd` | `fund(uint64 destination, bytes32 routeHash, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward, bool allowPartial)` | Payable. Emits `IntentFunded`. |
| `0xf16f5138` | `fundFor(uint64 destination, bytes32 routeHash, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward, bool allowPartial, address funder, address permitContract)` | Payable. |
| `0xf987b9bc` | `withdraw(uint64 destination, bytes32 routeHash, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward)` | Vault → claimant. Emits `IntentWithdrawn`. |
| `0x7af10029` | `batchWithdraw(uint64[] destinations, bytes32[] routeHashes, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens)[] rewards)` | Solvers use this form (sampled on Ethereum). |
| `0x308adade` | `refund(uint64 destination, bytes32 routeHash, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward)` | Vault → creator after the deadline. Emits `IntentRefunded`. |
| `0x572ac041` | `refundTo(uint64 destination, bytes32 routeHash, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward, address refundee)` | Refund to another address. |
| `0x0d0eeb7a` | `recoverToken(uint64 destination, bytes32 routeHash, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward, address token)` | Emits `IntentTokenRecovered`. |
| `0xe917a962` | `open((uint32 fillDeadline, bytes32 orderDataType, bytes orderData) order)` | ERC-7683. Payable. |
| `0x844fac8e` | `openFor((address originSettler, address user, uint256 nonce, uint256 originChainId, uint32 openDeadline, uint32 fillDeadline, bytes32 orderDataType, bytes orderData) order, bytes signature, bytes originFillerData)` | ERC-7683 gasless open. |

### 2.2 Portal — destination side and views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x52a8339e` | `fulfill(bytes32 intentHash, (bytes32 salt, uint64 deadline, address portal, uint256 nativeAmount, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, bytes32 rewardHash, bytes32 claimant)` | Payable. Pulls `route.tokens` from the solver to the Executor, runs `route.calls`. Emits `IntentFulfilled`. |
| `0xb6681e39` | `fulfillAndProve(bytes32 intentHash, (bytes32 salt, uint64 deadline, address portal, uint256 nativeAmount, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, bytes32 rewardHash, bytes32 claimant, address prover, uint64 sourceChainDomainID, bytes data)` | Payable. `IntentFulfilled` + `IntentProven` + the prover's message. |
| `0x17d4e807` | `prove(address prover, uint64 sourceChainDomainID, bytes32[] intentHashes, bytes data)` | Payable. Batch proof dispatch. Emits `IntentProven` per intent. |
| `0x377eacd1` | `cancel(bytes32 intentHash, (bytes32 salt, uint64 deadline, address portal, uint256 nativeAmount, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, bytes32 rewardHash)` | Current Portal only. Emits `IntentCancelled`. |
| `0xee433264` | `cancelAndProve(bytes32 intentHash, (bytes32 salt, uint64 deadline, address portal, uint256 nativeAmount, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, bytes32 rewardHash, address prover, uint64 sourceChainDomainID, bytes data)` | Current Portal only. Payable. Cancel + proof dispatch. |
| `0x82e2c43f` | `fill(bytes32 orderId, bytes originData, bytes fillerData)` | ERC-7683 fill. Emits `OrderFilled`. |
| `0xc34c08e5` | `executor()` | View → `address`. Live: `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` (retired Portal: `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca`). |
| `0x54fd4d50` | `version()` | View → `string`. Live: "2.12.0" (retired Portal: "2.6"). |
| `0x1299d617` | `getRewardStatus(bytes32 intentHash)` | View → `uint8` status enum of the intent's reward. |
| `0x0742ebe4` | `intentVaultAddress(uint64 destination, bytes route, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward)` | View → the intent's Vault address. |
| `0xed60f2a3` | `claimants(bytes32)` | View → the recorded claimant of a fulfilled intent (destination). |
| `0x0e74db05` | `getIntentHash(uint64 destination, bytes32 _routeHash, (uint64 deadline, address creator, address prover, uint256 nativeAmount, (address token, uint256 amount)[] tokens) reward)` | Pure → `(intentHash, routeHash, rewardHash)`. |

### 2.3 Executor and provers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x760f2a0b` | `execute((address target, bytes data, uint256 value)[] calls)` | Executor. Only the Portal. Reverts on a call with data to an address without code. |
| `0xbcd58bd2` | `prove(address sender, uint64 sourceChainDomainID, bytes encodedProofs, bytes data)` | Prover. Called by the destination Portal; sends the proof message. |
| `0xfc0eab91` | `challengeIntentProof(uint64 destination, bytes32 routeHash, bytes32 rewardHash)` | Prover (source). Emits `IntentProofInvalidated` for a wrong destination. |
| `0x99d145b2` | `provenIntents(bytes32 intentHash)` | Prover view → the claimant and destination of a proven intent. |
| `0x56d5d475` | `handle(uint32 origin, bytes32 sender, bytes messageBody)` | HyperProver. The Hyperlane Mailbox calls it on the source chain. |
| `0x54f10f0e` | `fetchFee(uint64 domainID, bytes encodedProofs, bytes data)` | Prover view → message fee. |

### 2.4 Legacy IntentSource and Inbox

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xab4b583e` | `publishAndFund(((bytes32 salt, uint256 source, uint256 destination, address inbox, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, (address creator, address prover, uint256 deadline, uint256 nativeValue, (address token, uint256 amount)[] tokens) reward) intent, bool allowPartial)` | IntentSource 1.x and 2.8.x. Emits `IntentCreated` + `IntentFunded`. |
| `0x111980f7` | `fund(bytes32 routeHash, (address creator, address prover, uint256 deadline, uint256 nativeValue, (address token, uint256 amount)[] tokens) reward, bool allowPartial)` | IntentSource 1.x and 2.8.x. |
| `0x69cc6c7a` | `withdrawRewards(((bytes32 salt, uint256 source, uint256 destination, address inbox, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, (address creator, address prover, uint256 deadline, uint256 nativeValue, (address token, uint256 amount)[] tokens) reward) _intent)` | IntentSource 2.8.x. Emits `Withdrawal`. |
| `0x4f1c8070` | `withdrawRewards(bytes32 routeHash, (address creator, address prover, uint256 deadline, uint256 nativeValue, (address token, uint256 amount)[] tokens) reward)` | IntentSource 1.x. |
| `0xde4b22f2` | `refund(((bytes32 salt, uint256 source, uint256 destination, address inbox, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) route, (address creator, address prover, uint256 deadline, uint256 nativeValue, (address token, uint256 amount)[] tokens) reward) _intent)` | IntentSource 2.8.x. Emits `Refund`. |
| `0x2c308f52` | `refund(bytes32 routeHash, (address creator, address prover, uint256 deadline, uint256 nativeValue, (address token, uint256 amount)[] tokens) reward)` | IntentSource 1.x. |
| `0xaf9d22cf` | `fulfill((bytes32 salt, uint256 source, uint256 destination, address inbox, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) _route, bytes32 _rewardHash, address _claimant, bytes32 _expectedHash, address _localProver)` | Inbox 1.x and 2.8.x. Emits `Fulfillment`. |
| `0x37e312dc` | `fulfillAndProve((bytes32 salt, uint256 source, uint256 destination, address inbox, (address token, uint256 amount)[] tokens, (address target, bytes data, uint256 value)[] calls) _route, bytes32 _rewardHash, address _claimant, bytes32 _expectedHash, address _localProver, bytes _data)` | Inbox 1.x and 2.8.x. |

---

## 3. Addresses — Ethereum (chain ID 1)

All verified with `eth_getCode` on 2026-09-29; the current-generation rows on 2026-10-05.

| Role | Address | One-liner |
|------|---------|-----------|
| **Portal** | `0xEC000769A73b70e16f361a442292500b3BCf4A85` | Current (routes-ts 3.2.23+). `version()` = "2.12.0". |
| **Executor** | `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` | `Portal.executor()` returns it. |
| Vault implementation | `0x204D732E8d2f71D756eF5De79Dc6589721b53420` | 4,370 B. Every current Vault proxy delegates to it. |
| **HyperProver** | `0xEC08fb4647f3f50d1162a578d481266687C60fc5` | `getProofType()` = "Hyperlane", `PORTAL()` = the current Portal. |
| **PolymerProver** | `0xEC0DeD087Ee6C55991Bb4D4567ca1134c5353Ed6` | `getProofType()` = "Polymer", `PORTAL()` = the current Portal. |
| **CCIPProver** (unlisted) | `0xEC0B53A81C996da376F125E541E40082815CDcDc` | `getProofType()` = "CCIP", `PORTAL()` = the current Portal. Emitted 4 prover `IntentProven` in the 24 h to 2026-10-05. |
| Portal (3.2.19–3.2.22, retired) | `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` | Verified `Portal`. Created through the EIP-2470 singleton factory `0xce0042B868300000d44A59004Da54A005ffdcf9f`. Last event 2026-09-30 17:40 UTC. |
| Executor (retired Portal) | `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca` | Verified `Executor`. |
| Vault implementation (retired Portal) | `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9` | 4,203 B. |
| HyperProver (3.2.21–3.2.22) | `0xec004Ab4870c4e177c66949329dCdb503CE41022` | Verified `HyperProver`. Mailbox `0xc005dc82818d67AF737725bD4bf75435d065D239`. |
| PolymerProver (3.2.20–3.2.22) | `0xE3e4e6F284f1c8E17bafE4268EB98c36886B4d8B` | Listed for Ethereum and Base. |
| PolymerProver (unlisted, retired Portal) | `0xEC00993f947cecBBfB261f25d4af2C95F97c91F9` | `getProofType()` = "Polymer", `version()` = "2.10.0". |
| CCIPProver (unlisted, retired Portal) | `0xceBB7cDDBA4734C7130BF114a37C2dA4C5f3c473` | Verified `CCIPProver`. |
| LayerZeroProver | `0x0C4E3063239c9f4f323A956C79738916594D8Fd4` | routes-ts 3.2.18. |
| HyperProver (previous) | `0xC972B26C1E208845Ca8C18c6B83466bFCeED8c2F` | routes-ts 3.2.17–3.2.20. |
| Portal (previous) | `0x399Dbd5DF04f83103F77A58cBa2B7c4d3cdede97` | routes-ts 3.2.4–3.2.18. |
| Portal (older) | `0x18d4415ad59b6B08976517C613D94974b6bCB79c` | routes-ts 3.2.1–3.2.2. |
| Portal (pre-release) | `0xB5e58A8206473Df3Ab9b8DDd3B0F84c0ba68F8b5` | routes-ts 3.0.0-alpha. |
| IntentSource (legacy) | `0x2020ae689ED3e017450280CEA110d0ef6E640Da4` | routes-ts 2.8.x. |
| Inbox (legacy) | `0x04c816032A076dF65b411Bb3F31c8d569d411ee2` | routes-ts 2.8.x. |
| ECDSAExecutor (not Routes) | `0xEc2C96e75B09e29b66bf2Ee5C37fa749eF9AA7c7` | Verified `ECDSAExecutor` (ERC-7579 module). |

MetaProver and the routes-ts 1.21.2 pair are not deployed on Ethereum (`eth_getCode` = `0x`).

## 4. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| **Portal** | `0xEC000769A73b70e16f361a442292500b3BCf4A85` | Current. Same address as Ethereum. |
| **Executor** | `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` | `Portal.executor()` returns it. |
| Vault implementation | `0x204D732E8d2f71D756eF5De79Dc6589721b53420` | 4,370 B. Every current Vault proxy delegates to it. |
| **HyperProver** | `0xEC08fb4647f3f50d1162a578d481266687C60fc5` | `getProofType()` = "Hyperlane", `PORTAL()` = the current Portal. |
| **PolymerProver** | `0xEC0DeD087Ee6C55991Bb4D4567ca1134c5353Ed6` | `getProofType()` = "Polymer", `PORTAL()` = the current Portal. |
| **CCIPProver** (unlisted) | `0xEC0B53A81C996da376F125E541E40082815CDcDc` | 8,125 B. |
| Portal (3.2.19–3.2.22, retired) | `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` | Verified `Portal`. Last event 2026-10-01 12:56 UTC. |
| Executor / Vault implementation (retired Portal) | `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca` · `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9` | |
| HyperProver (3.2.21–3.2.22) | `0xec004Ab4870c4e177c66949329dCdb503CE41022` | Mailbox `0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D`. |
| PolymerProver (3.2.20–3.2.22 / unlisted) | `0xE3e4e6F284f1c8E17bafE4268EB98c36886B4d8B` · `0xEC00993f947cecBBfB261f25d4af2C95F97c91F9` | |
| CCIPProver (unlisted, retired Portal) | `0xceBB7cDDBA4734C7130BF114a37C2dA4C5f3c473` | 7,804 B. |
| LayerZeroProver | `0x0C4E3063239c9f4f323A956C79738916594D8Fd4` | Same code as Ethereum. |
| MetaProver | `0x3d529eFAEDb3B999A404c1B8543441aE616cB914` | routes-ts 2.8.1–3.2.18. |
| HyperProver (previous) | `0xC972B26C1E208845Ca8C18c6B83466bFCeED8c2F` | |
| Portal (previous / older / pre-release) | `0x399Dbd5DF04f83103F77A58cBa2B7c4d3cdede97` · `0x18d4415ad59b6B08976517C613D94974b6bCB79c` · `0xB5e58A8206473Df3Ab9b8DDd3B0F84c0ba68F8b5` | |
| IntentSource / Inbox (2.8.x) | `0x2020ae689ED3e017450280CEA110d0ef6E640Da4` · `0x04c816032A076dF65b411Bb3F31c8d569d411ee2` | |
| IntentSource / Inbox (1.21.2) | `0xaF3278044514f81f4e79539F32aE4F2Eea87fdda` · `0x6405778b5e261AFA0f7c4094A25CF4fE806c9870` | |
| ECDSAExecutor (not Routes) | `0xEc2C96e75B09e29b66bf2Ee5C37fa749eF9AA7c7` | |

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **Portal** | `0xEC000769A73b70e16f361a442292500b3BCf4A85` | Current. |
| **Executor** | `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` | |
| Vault implementation | `0x204D732E8d2f71D756eF5De79Dc6589721b53420` | |
| **HyperProver** | `0xEC08fb4647f3f50d1162a578d481266687C60fc5` | |
| **PolymerProver** | `0xEC0DeD087Ee6C55991Bb4D4567ca1134c5353Ed6` | |
| Portal (3.2.19–3.2.22, retired) | `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` | Last event 2026-09-30 23:31 UTC. |
| Executor / Vault implementation (retired Portal) | `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca` · `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9` | |
| HyperProver (3.2.21–3.2.22) | `0xec004Ab4870c4e177c66949329dCdb503CE41022` | |
| PolymerProver (retired Portal) | `0xE3e4e6F284f1c8E17bafE4268EB98c36886B4d8B` · `0xEC00993f947cecBBfB261f25d4af2C95F97c91F9` | Code present; routes-ts lists neither for Arbitrum. |
| LayerZeroProver | `0x0C4E3063239c9f4f323A956C79738916594D8Fd4` | |
| MetaProver | `0x3d529eFAEDb3B999A404c1B8543441aE616cB914` | |
| HyperProver (previous) | `0xC972B26C1E208845Ca8C18c6B83466bFCeED8c2F` | |
| Portal (previous / older / pre-release) | `0x399Dbd5DF04f83103F77A58cBa2B7c4d3cdede97` · `0x18d4415ad59b6B08976517C613D94974b6bCB79c` · `0xB5e58A8206473Df3Ab9b8DDd3B0F84c0ba68F8b5` | |
| IntentSource / Inbox (2.8.x) | `0x2020ae689ED3e017450280CEA110d0ef6E640Da4` · `0x04c816032A076dF65b411Bb3F31c8d569d411ee2` | |
| IntentSource / Inbox (1.21.2) | `0xaF3278044514f81f4e79539F32aE4F2Eea87fdda` · `0x6405778b5e261AFA0f7c4094A25CF4fE806c9870` | |

CCIPProver: `eth_getCode` = `0x` on Arbitrum.

## 6. Addresses — Optimism (chain ID 10)

| Role | Address | One-liner |
|------|---------|-----------|
| **Portal** | `0xEC000769A73b70e16f361a442292500b3BCf4A85` | Current. |
| **Executor** | `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` | |
| Vault implementation | `0x204D732E8d2f71D756eF5De79Dc6589721b53420` | |
| **HyperProver** | `0xEC08fb4647f3f50d1162a578d481266687C60fc5` | |
| **PolymerProver** | `0xEC0DeD087Ee6C55991Bb4D4567ca1134c5353Ed6` | |
| Portal (3.2.19–3.2.22, retired) | `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` | Replaced in routes-ts 3.2.23. |
| Executor / Vault implementation (retired Portal) | `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca` · `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9` | |
| HyperProver (3.2.21–3.2.22) | `0xec004Ab4870c4e177c66949329dCdb503CE41022` | |
| PolymerProver (retired Portal) | `0xE3e4e6F284f1c8E17bafE4268EB98c36886B4d8B` · `0xEC00993f947cecBBfB261f25d4af2C95F97c91F9` | Code present. |
| LayerZeroProver | `0x0C4E3063239c9f4f323A956C79738916594D8Fd4` | |
| HyperProver (previous) | `0xC972B26C1E208845Ca8C18c6B83466bFCeED8c2F` | |
| Portal (previous / older / pre-release) | `0x399Dbd5DF04f83103F77A58cBa2B7c4d3cdede97` · `0x18d4415ad59b6B08976517C613D94974b6bCB79c` · `0xB5e58A8206473Df3Ab9b8DDd3B0F84c0ba68F8b5` | |
| IntentSource / Inbox (2.8.x) | `0x2020ae689ED3e017450280CEA110d0ef6E640Da4` · `0x04c816032A076dF65b411Bb3F31c8d569d411ee2` | |
| IntentSource / Inbox (1.21.2) | `0xaF3278044514f81f4e79539F32aE4F2Eea87fdda` · `0x6405778b5e261AFA0f7c4094A25CF4fE806c9870` | |

MetaProver and CCIPProver: `eth_getCode` = `0x` on Optimism.

## 7. Addresses — Polygon PoS (chain ID 137)

| Role | Address | One-liner |
|------|---------|-----------|
| **Portal** | `0xEC000769A73b70e16f361a442292500b3BCf4A85` | Current. |
| **Executor** | `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` | |
| Vault implementation | `0x204D732E8d2f71D756eF5De79Dc6589721b53420` | |
| **HyperProver** | `0xEC08fb4647f3f50d1162a578d481266687C60fc5` | |
| **PolymerProver** | `0xEC0DeD087Ee6C55991Bb4D4567ca1134c5353Ed6` | |
| Portal (3.2.19–3.2.22, retired) | `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` | Replaced in routes-ts 3.2.23. |
| Executor / Vault implementation (retired Portal) | `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca` · `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9` | |
| HyperProver (3.2.21–3.2.22) | `0xec004Ab4870c4e177c66949329dCdb503CE41022` | |
| PolymerProver (retired Portal) | `0xE3e4e6F284f1c8E17bafE4268EB98c36886B4d8B` · `0xEC00993f947cecBBfB261f25d4af2C95F97c91F9` | Code present. |
| LayerZeroProver | `0x0C4E3063239c9f4f323A956C79738916594D8Fd4` | |
| HyperProver (previous) | `0xC972B26C1E208845Ca8C18c6B83466bFCeED8c2F` | |
| Portal (previous / older / pre-release) | `0x399Dbd5DF04f83103F77A58cBa2B7c4d3cdede97` · `0x18d4415ad59b6B08976517C613D94974b6bCB79c` · `0xB5e58A8206473Df3Ab9b8DDd3B0F84c0ba68F8b5` | |
| IntentSource / Inbox (2.8.x) | `0x2020ae689ED3e017450280CEA110d0ef6E640Da4` · `0x04c816032A076dF65b411Bb3F31c8d569d411ee2` | |

MetaProver, CCIPProver and the 1.21.2 pair: `eth_getCode` = `0x` on Polygon.

## 8. Addresses — BNB Smart Chain (chain ID 56): retired Portal only

routes-ts 3.2.23+ drops chain 56. The current Portal, Executor, Vault implementation and provers have no code on BNB (`eth_getCode` = `0x`, 2026-10-05).

| Role | Address | One-liner |
|------|---------|-----------|
| Portal (3.2.19–3.2.22, retired) | `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` | `executor()` and `version()` answer as on Ethereum. Listed up to routes-ts 3.2.22; not in the `/v1/chains` example. |
| Executor (retired Portal) | `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca` | |
| Vault implementation (retired Portal) | `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9` | |
| HyperProver (previous) | `0xC972B26C1E208845Ca8C18c6B83466bFCeED8c2F` | The only prover with code on BNB. |
| Portal (previous / older / pre-release) | `0x399Dbd5DF04f83103F77A58cBa2B7c4d3cdede97` · `0x18d4415ad59b6B08976517C613D94974b6bCB79c` · `0xB5e58A8206473Df3Ab9b8DDd3B0F84c0ba68F8b5` | |
| IntentSource / Inbox (2.8.x) | `0x2020ae689ED3e017450280CEA110d0ef6E640Da4` · `0x04c816032A076dF65b411Bb3F31c8d569d411ee2` | |
| ECDSAExecutor (not Routes) | `0xEc2C96e75B09e29b66bf2Ee5C37fa749eF9AA7c7` | |

The 3.2.21–3.2.22 HyperProver, both PolymerProvers, CCIPProver, LayerZeroProver and MetaProver have no code on BNB. routes-ts lists MetaProver `0x3d529eFAEDb3B999A404c1B8543441aE616cB914` for BNB up to 3.2.18, but `eth_getCode` returns `0x` there.

## 9. Addresses — Robinhood Chain (chain ID 4663): unlisted retired Portal

The 3.2.19–3.2.22 Portal, its Executor and its Vault implementation have code at their usual addresses on Robinhood Chain. `executor()` returns the same Executor, and `version()` returns "2.6". The current Portal `0xEC000769A73b70e16f361a442292500b3BCf4A85`, its Executor and its provers have no code on Robinhood Chain (2026-10-05). The routes-ts address file (3.2.22 to 3.2.24) and the `/v1/chains` example (2026-09-15) do not list Robinhood Chain. The Portal is a permissionless deployment through the EIP-2470 factory, so its presence does not prove that Eco solvers serve the chain. Eco announced a Robinhood Chain integration on 2026-07-29.

| Role | Address | One-liner |
|------|---------|-----------|
| Portal (3.2.19–3.2.22) | `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` | 22,537 B. **Contract nonce 4** (Ethereum: 15,469). 0 Portal events in the pinned window. |
| Executor | `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca` | Same code. |
| Vault implementation | `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9` | Same code. |

No prover, no older Portal and no legacy IntentSource or Inbox has code on Robinhood Chain.

## 10. Addresses — Arc (chain ID 5042)

routes-ts 3.2.23+ lists Arc with the shared current addresses. All rows were existence-checked with `eth_getCode` on `https://rpc.mainnet.arc.io` on 2026-10-05. `Portal.executor()` and `version()` answer as on Ethereum. The Portal emitted `IntentFulfilled` and `IntentWithdrawn` in the ~40,000 Arc blocks to 2026-10-05.

| Role | Address | One-liner |
|------|---------|-----------|
| **Portal** | `0xEC000769A73b70e16f361a442292500b3BCf4A85` | Current. 24,197 B. |
| **Executor** | `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` | Same code as Ethereum. |
| Vault implementation | `0x204D732E8d2f71D756eF5De79Dc6589721b53420` | Same code as Ethereum. |
| **HyperProver** | `0xEC08fb4647f3f50d1162a578d481266687C60fc5` | 7,891 B. |
| **PolymerProver** | `0xEC0DeD087Ee6C55991Bb4D4567ca1134c5353Ed6` | Same code as Ethereum. |
| Portal (3.2.19–3.2.22, Arc only, retired) | `0xEC002CA16cE20c2a9F3C6200EF04E7d92a3dfBD8` | `version()` = "2.10.0", `executor()` = `0x95b2d45F49c68a54BDBa0356fc3034751A43b3D4`. 0 logs in the last 20,000 blocks. |
| HyperProver (3.2.21–3.2.22) | `0xec004Ab4870c4e177c66949329dCdb503CE41022` | Code present. |

The 3.2.19–3.2.22 shared Portal `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df`, its Executor and its Vault implementation have no code on Arc. The current CCIPProver `0xEC0B53A81C996da376F125E541E40082815CDcDc` has no code on Arc. LayerZeroProver and the legacy contracts were not checked on Arc.

---

## 11. Cross-chain summary

| Chain | ID | Current Portal `0xEC000769…` | Retired Portal `0xEC000064…` | Current HyperProver | Current PolymerProver | Current CCIPProver | Legacy 2.8.x pair | `IntentPublished` | `IntentFulfilled` | `IntentWithdrawn` | `IntentRefunded` |
|-------|----|----|----|----|----|----|----|----|----|----|----|
| Ethereum | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 92 | 68 | 91 | 0 |
| Base | 8453 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 127 | 163 | 135 | 3 |
| Arbitrum One | 42161 | ✅ | ✅ | ✅ | ✅ | — | ✅ | 103 | 115 | 101 | 2 |
| Optimism | 10 | ✅ | ✅ | ✅ | ✅ | — | ✅ | 25 | 47 | 29 | 0 |
| Polygon PoS | 137 | ✅ | ✅ | ✅ | ✅ | — | ✅ | 9 | 75 | 10 | 1 |
| Arc | 5042 | ✅ | — (own 3.2.22 Portal) | ✅ | ✅ | — | n/c | n/c | live | live | n/c |
| BNB Smart Chain | 56 | — | ✅ | — | — | — | ✅ | 0 | 0 | 0 | 0 |
| Avalanche C-Chain | 43114 | — | — | — | — | — | — | not deployed | | | |
| Robinhood Chain | 4663 | — | ✅ (unlisted) | — | — | — | — | 0 | 0 | 0 | 0 |

Counts are logs of the then-current Portal `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` in the pinned 12-hour window 2026-09-28 00:00–12:00 UTC, before the migration. After it, the current Portal on Base emitted `IntentFunded` 89, `IntentWithdrawn` 81, `IntentFulfilled` 79, Portal `IntentProven` 74, `IntentPublished` 71 and `IntentRefunded` 1 in the 24 hours to 2026-10-05 10:00 UTC (n/c = not counted). Outside the nine, routes-ts 3.2.24 lists the current Portal on Unichain, Monad, World Chain, HyperEVM, Ronin and Plasma, plus Tron and Solana; it drops Sonic, Celo and Ink.

**Avalanche C-Chain has no Eco deployment.** `eth_getCode` returns `0x` at both Portals, both Executors, both Vault implementations, every prover and every legacy address. No routes-ts version lists chain 43114.

---

## 12. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Portal** | Immutable | EIP-1967 slots empty (both the current and the retired Portal). The Eco docs: "no proxy, no admin keys, no upgrade path". The ABI has no owner, pause or upgrade function. | None. |
| **Executor** | Immutable | EIP-1967 slots empty. One function (`execute`), only the Portal. | None. |
| **Vault** (per intent) | Minimal proxy (75 B) | The runtime code holds the implementation as a `PUSH32` and delegates to it (current Portal: `0x204D732E8d2f71D756eF5De79Dc6589721b53420`; retired Portal: `0x9f70b0c839fe2D7190a09AE87ED658B6d1Cba4F9`); an empty call is accepted (native funding). Not the 45-byte ERC-1167 layout. | None. Only the Portal can call it. |
| **Provers** | Immutable | EIP-1967 slots empty. The verified HyperProver and CCIPProver ABIs have no owner or upgrade function; their whitelists are set in the constructor. | None. |
| Legacy IntentSource / Inbox | Immutable | EIP-1967 slots empty. | None. |

There is no admin trigger to watch on the Routes contracts. A new prover needs no approval: any contract that implements `IProver` can be named in an intent.

---

## 13. Detection invariants & gotchas

1. **Take the value from the Vault, not the Portal.** The Portal holds nothing. On the source chain, the token goes from the funder straight to the intent's Vault. Example: Ethereum `0xff8bb9fab062392121d07b52a0d9b8ff8d5ef36935b8ec22e52e0e7b73744215` moves USDC from a Bungee router (`0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a`) to the Vault `0xd875d181A5E298114ca3FfcC310E5163a51523da`, then emits `IntentFunded`. Get the Vault address from that `Transfer`, or call `intentVaultAddress`.
2. **A Vault can be funded with no event.** The docs describe funding as "a vanilla ERC-20 transfer to a CREATE2 address". A plain transfer to a Vault address emits no `IntentFunded`.
3. **The payout comes from the Executor.** On the destination, the solver's tokens go solver → Executor → recipient, in the same transaction as `IntentFulfilled`. The current Executor is `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` on all six chains with the current Portal; the retired Portal used `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca`. Example (retired Portal): Ethereum `0x661bfd50ed1484623e58eb0e2a999c6ac82af7a3a414bdbbfa93811e3d719bb9`.
4. **The solver is not `tx.from`.** Solvers use smart accounts. In the Ethereum example, the transaction goes to the ECDSAExecutor module, and a smart account (`0x1Da38A31F369343bdD33cCc48E89D165E8ab3450`) supplies the USDC. `IntentFulfilled.claimant` (`bytes32`) is the reward address on the source chain.
5. **Two different `IntentProven` topics.** The Portal's `IntentProven(bytes32,bytes32)` (`0xe6d8040a8a6bc519f4e5a42fb2677067c929ddbf2cca9287a44b23fb617a6f00`, destination) means "proof sent". The prover's `IntentProven(bytes32,address,uint64)` (`0xa79bcebf1cb6259b008ad946df35c764dd6b25206bb5c47ec11976cdce4f0145`, source) means "proof received". The legacy prover had a third topic. Do not merge them.
6. **Two different `IntentFunded` topics.** The Portal's has a `bool complete` field; the legacy IntentSource's does not.
7. **The prover set is open.** In the pinned window the source-side `IntentProven` came from the current HyperProver (Ethereum 89, Base 125, Arbitrum 102, Optimism 27, Polygon 8), the unlisted PolymerProver `0xEC00993f947cecBBfB261f25d4af2C95F97c91F9` (Base 6, Optimism 2), PolymerProver `0xE3e4e6F284f1c8E17bafE4268EB98c36886B4d8B` (Base 1) and the CCIPProver (Ethereum 2). Two of these are not in the routes-ts address file. After the migration (24 h to 2026-10-05) the emitters were the current HyperProver `0xEC08fb4647f3f50d1162a578d481266687C60fc5` (Ethereum 77, Base 77, Arbitrum 69), the current CCIPProver `0xEC0B53A81C996da376F125E541E40082815CDcDc` (Ethereum 4, Base 1) and the current PolymerProver `0xEC0DeD087Ee6C55991Bb4D4567ca1134c5353Ed6` (Base 1). Read the prover from `IntentPublished` topic3 instead of a fixed list.
8. **ERC-7683 topics are shared.** The standard `Open` topic is emitted by other settlers too: in the pinned window, five other contracts emitted it on Ethereum, Base, Arbitrum and Optimism, and the Portal emitted none. `OrderFilled(bytes32,address)` is also the legacy Inbox topic. Filter on the emitter.
9. **Refund and reward both leave the Vault.** `IntentWithdrawn` pays the solver; `IntentRefunded` returns the funds to the creator (or `refundTo`'s address). Example refund: Base `0xa55653f0223fe243f42fcd30c21b5296b0dcfd294af452292536889a2a32949e` moves USDC from the Vault `0x645fEbD586E739a37B322aC5dCB25cf61e923563` to the refundee, through a Multicall3 batch.
10. **Older Portals still exist.** The retired 3.2.19–3.2.22 Portal `0xEC000064576f9C95a8623Bc0eff3db6d296ea6df` (last events 2026-09-30/10-01), the 3.2.4–3.2.18 Portal and the older ones keep their Vaults, so late withdrawals and refunds can still come from them. The pre-3.2.19 Portals had 0 events in the pinned window. Watch the current and the retired Portal together.
11. **Robinhood Chain and BNB have only the retired Portal.** Robinhood: contract nonce 4 and 0 events in the window. BNB: listed up to routes-ts 3.2.22 with 0 events in the window, and dropped from 3.2.23. Neither chain has the current Portal.
12. **The docs' address page is stale.** The Eco "Contract Addresses" page lists only 2.8-era HyperProvers (`0x0f124aA8F92F47302fCba08b7349AEFEe853Ed8d` and `0xb4B22BaFafc0Fe12Bc9Be00D6611Dd2d8A42a7a8`). The `/v1/chains` example names the ECDSAExecutor as `executor`, while `Portal.executor()` returns `0x8B5D51AF4C4542f241C4e54CFd903CeEd145f082` (retired Portal: `0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca`). Use the routes-ts address file and on-chain reads.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Portal topics (chain-agnostic) =====
TOPIC_INTENT_PUBLISHED              = '\x43974895be1bcec7344337863fa7de24a0d1c315c0a994f663fe0ee220ddc8e4'
TOPIC_INTENT_FUNDED                 = '\xc1ed05721d27ad6b2555d61388ac393b120f5cc0e6009e53230e02c68e60064a'
TOPIC_INTENT_FULFILLED              = '\xc471de166a60c0b81727dfa2f57d4fc3ad1b45b057c1f034b7058365613bde8d'
TOPIC_INTENT_PROVEN_PORTAL          = '\xe6d8040a8a6bc519f4e5a42fb2677067c929ddbf2cca9287a44b23fb617a6f00'
TOPIC_INTENT_CANCELLED              = '\xc08eb64db16a39d2848960af04e3f16fb404d9d436a9f0e9d7d0d4854715c9dc'   -- current Portal only
TOPIC_INTENT_WITHDRAWN              = '\xbb062c23e818de8ea9c157514eb098052cf36904bbe431cd50d4ec92264ca3ac'
TOPIC_INTENT_REFUNDED               = '\x8d53c2b04800cf061b987a07179bb6c9730c05536b2f6a3a091fe62303682eb6'
TOPIC_INTENT_TOKEN_RECOVERED        = '\x21ea3a531675a90b5b0263d6dc9be64e34e0bfd422a8b428b2d0729c5d4446e4'
TOPIC_ERC7683_OPEN                  = '\x3448bbc2203c608599ad448eeb1007cea04b788ac631f9f558e8dd01a3c27b3d'
TOPIC_ORDER_FILLED                  = '\x0555709e59fb225fcf12cc582a9e5f7fd8eea54c91f3dc500ab9d8c37c507770'
-- ===== Prover topics (source side) =====
TOPIC_INTENT_PROVEN_PROVER          = '\xa79bcebf1cb6259b008ad946df35c764dd6b25206bb5c47ec11976cdce4f0145'
TOPIC_INTENT_PROOF_INVALIDATED      = '\xae165391a85a2219c7e5367bc7775dc0a2bc5cdf1f35e95204d716f6d96c2758'
-- ===== Legacy IntentSource / Inbox topics =====
TOPIC_LEGACY_INTENT_CREATED         = '\xd802f2610d0c85b3f19be4413f3cf49de1d4e787edecd538274437a5b9aa648d'
TOPIC_LEGACY_INTENT_FUNDED          = '\x2da42efda5225344c30e729dc0eafc2e56292ac9b9b5c2b16e0e74c86ea5921d'
TOPIC_LEGACY_WITHDRAWAL             = '\x6653a45d3871e4110fa55dac0269f9f93a6d9078d402f7153594e50573d7f0cd'
TOPIC_LEGACY_REFUND                 = '\x0ba6f12b978882904e7444c7a8fcadd2d9f692a6a97aa18e5fb44c3bbc580123'
TOPIC_LEGACY_FULFILLMENT            = '\x4a817ec64beb8020b3e400f30f3b458110d5765d7a9d1ace4e68754ed2d082de'
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors (chain-agnostic) =====
SEL_PUBLISH_AND_FUND                = '\xe353b5e6'
SEL_PUBLISH_AND_FUND_ENCODED        = '\xdf00f8fa'
SEL_FUND                            = '\x9f24b4dd'
SEL_FULFILL                         = '\x52a8339e'
SEL_FULFILL_AND_PROVE               = '\xb6681e39'
SEL_PROVE                           = '\x17d4e807'
SEL_WITHDRAW                        = '\xf987b9bc'
SEL_BATCH_WITHDRAW                  = '\x7af10029'
SEL_REFUND                          = '\x308adade'
SEL_REFUND_TO                       = '\x572ac041'
SEL_RECOVER_TOKEN                   = '\x0d0eeb7a'
SEL_OPEN                            = '\xe917a962'
SEL_FILL                            = '\x82e2c43f'
SEL_CANCEL                          = '\x377eacd1'
SEL_CANCEL_AND_PROVE                = '\xee433264'
SEL_EXECUTOR_EXECUTE                = '\x760f2a0b'
SEL_INTENT_VAULT_ADDRESS            = '\x0742ebe4'

-- ===== Current Portal generation (routes-ts 3.2.23+; ETH, Base, Arb, OP, Poly, Arc; same address on each) =====
ETH_PORTAL                          = '\xec000769a73b70e16f361a442292500b3bcf4a85'
BASE_PORTAL                         = '\xec000769a73b70e16f361a442292500b3bcf4a85'
ARB_PORTAL                          = '\xec000769a73b70e16f361a442292500b3bcf4a85'
OP_PORTAL                           = '\xec000769a73b70e16f361a442292500b3bcf4a85'
POLY_PORTAL                         = '\xec000769a73b70e16f361a442292500b3bcf4a85'
ARC_PORTAL                          = '\xec000769a73b70e16f361a442292500b3bcf4a85'
ETH_EXECUTOR                        = '\x8b5d51af4c4542f241c4e54cfd903ceed145f082'   -- same on all six
ETH_VAULT_IMPLEMENTATION            = '\x204d732e8d2f71d756ef5de79dc6589721b53420'   -- same on all six
ETH_HYPER_PROVER                    = '\xec08fb4647f3f50d1162a578d481266687c60fc5'   -- same on all six
ETH_POLYMER_PROVER                  = '\xec0ded087ee6c55991bb4d4567ca1134c5353ed6'   -- same on all six
ETH_CCIP_PROVER                     = '\xec0b53a81c996da376f125e541e40082815cdcdc'   -- also Base; unlisted

-- ===== Retired Portal generation (routes-ts 3.2.19–3.2.22; last events 2026-09-30/10-01) =====
ETH_PORTAL_3_2_19                   = '\xec000064576f9c95a8623bc0eff3db6d296ea6df'   -- also Base, Arb, OP, Poly, BNB, Robinhood (unlisted)
BNB_PORTAL_3_2_19                   = '\xec000064576f9c95a8623bc0eff3db6d296ea6df'
RH_PORTAL_3_2_19                    = '\xec000064576f9c95a8623bc0eff3db6d296ea6df'
ARC_PORTAL_3_2_19                   = '\xec002ca16ce20c2a9f3c6200ef04e7d92a3dfbd8'   -- Arc-only address
ETH_EXECUTOR_3_2_19                 = '\x645dadd5bf354526b68a2befd9a305f7e03b91ca'   -- also Base, Arb, OP, Poly, BNB, Robinhood
ETH_VAULT_IMPLEMENTATION_3_2_19     = '\x9f70b0c839fe2d7190a09ae87ed658b6d1cba4f9'
ETH_HYPER_PROVER_3_2_21             = '\xec004ab4870c4e177c66949329dcdb503ce41022'   -- also Base, Arb, OP, Poly, Arc
ETH_POLYMER_PROVER_3_2_20           = '\xe3e4e6f284f1c8e17bafe4268eb98c36886b4d8b'   -- also Base, Arb, OP, Poly
ETH_POLYMER_PROVER_UNLISTED         = '\xec00993f947cecbbfb261f25d4af2c95f97c91f9'   -- also Base, Arb, OP, Poly
ETH_CCIP_PROVER_3_2_19              = '\xcebb7cddba4734c7130bf114a37c2da4c5f3c473'   -- also Base
ETH_LAYERZERO_PROVER                = '\x0c4e3063239c9f4f323a956c79738916594d8fd4'
BASE_META_PROVER                    = '\x3d529efaedb3b999a404c1b8543441ae616cb914'   -- also Arb
BNB_HYPER_PROVER_PREVIOUS           = '\xc972b26c1e208845ca8c18c6b83466bfceed8c2f'   -- also ETH, Base, Arb, OP, Poly

-- ===== Older Portals and legacy contracts (ETH, Base, Arb, OP, Poly, BNB) =====
ETH_PORTAL_3_2_4                    = '\x399dbd5df04f83103f77a58cba2b7c4d3cdede97'
ETH_PORTAL_3_2_1                    = '\x18d4415ad59b6b08976517c613d94974b6bcb79c'
ETH_PORTAL_3_0_ALPHA                = '\xb5e58a8206473df3ab9b8ddd3b0f84c0ba68f8b5'
ETH_INTENT_SOURCE_2_8               = '\x2020ae689ed3e017450280cea110d0ef6e640da4'
ETH_INBOX_2_8                       = '\x04c816032a076df65b411bb3f31c8d569d411ee2'
BASE_INTENT_SOURCE_1_21             = '\xaf3278044514f81f4e79539f32ae4f2eea87fdda'   -- also Arb, OP
BASE_INBOX_1_21                     = '\x6405778b5e261afa0f7c4094a25cf4fe806c9870'   -- also Arb, OP
-- Avalanche (43114): no Eco contract at any address above.
```

---

## 15. Verification & sources

How the constants in this file were verified (2026-09-29; migration rows 2026-10-05):

- **Portal migration (2026-10-05):** routes-ts 3.2.23 (2026-09-29) and 3.2.24 (2026-09-30) list the current Portal, HyperProver and PolymerProver on chains 1, 10, 137, 8453, 42161 and 5042, and drop chain 56. Its Portal ABI adds `IntentCancelled`, `cancel` and `cancelAndProve` (recomputed); every other Portal, prover and Executor signature is unchanged from 3.2.22. `eth_getCode` confirms the current Portal (24,197 B), Executor (1,642 B), Vault implementation (4,370 B, the `PUSH32` target of a current Base Vault), HyperProver, PolymerProver and CCIPProver on each listed chain, and `0x` on BNB, Avalanche and Robinhood Chain. `executor()`, `version()`, `getProofType()` and `PORTAL()` are read live. Per-emitter log counts and first/last timestamps of both Portals on Ethereum, Base and Arbitrum come from indexed log data; Arc logs come from `eth_getLogs`.
- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the ABIs in `@eco-foundation/routes-ts` 3.2.22 (Portal, Executor, IProver, IMessageBridgeProver, IVault), 2.8.20 and 1.21.2 (IntentSource, Inbox, Eco7683OriginSettler, Eco7683DestinationSettler, IMessageBridgeProver), and from the verified HyperProver and CCIPProver sources. The live topics of §1.1–§1.3 appear at the Portal and the provers in the pinned window. The sampled selectors match: `batchWithdraw` `0x7af10029`.
- **Addresses:** from the `deployAddresses.csv` of every routes-ts version (0.0.714-beta to 3.2.22): Portal 3.2.19+, HyperProver 3.2.21+, PolymerProver 3.2.20+, LayerZeroProver 3.2.18, MetaProver 2.8.1–3.2.18, the previous HyperProver and Portals, and the legacy IntentSource / Inbox pairs. `eth_getCode` confirms each one on each chain (§3–§10). `Portal.executor()` returns the Executor on Ethereum, BNB and Robinhood Chain. The Vault implementation is the `PUSH32` target inside the Vault `0xd875d181A5E298114ca3FfcC310E5163a51523da` on Ethereum, and it has the same 4,203-byte code on seven chains. The two unlisted provers are the emitters of `IntentProven` in the pinned window; their type and Portal are read with `getProofType()` and `PORTAL()`, and the CCIPProver source is verified on Blockscout. The Portal's creator on Ethereum and Base (Blockscout) is the EIP-2470 factory.
- **Value movement, read from receipts:** publish and fund `0xff8bb9fab062392121d07b52a0d9b8ff8d5ef36935b8ec22e52e0e7b73744215` (Ethereum; prover = the current HyperProver). Fulfill and prove `0x661bfd50ed1484623e58eb0e2a999c6ac82af7a3a414bdbbfa93811e3d719bb9` (Ethereum; USDC smart account → Executor → recipient, then a Hyperlane `Dispatch` from the Mailbox `0xc005dc82818d67AF737725bD4bf75435d065D239` to domain 1399811149). Withdraw `0xcf3867370c79f52f7a93f52c6e6a541aeb12a3fc74c4e3a6e77d80e8cb8c4620` (Ethereum; USDC Vault `0xd875d181A5E298114ca3FfcC310E5163a51523da` → claimant). Refund `0xa55653f0223fe243f42fcd30c21b5296b0dcfd294af452292536889a2a32949e` (Base).
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, emitter = the Portal):** see §11. `IntentFunded`: Ethereum 94, Base 137, Arbitrum 105, Optimism 29, Polygon 11, BNB 0, Robinhood Chain 0. Portal `IntentProven`: Ethereum 68, Base 164, Arbitrum 114, Optimism 47, Polygon 73, BNB 0, Robinhood Chain 0. `IntentTokenRecovered`, `Open` and `OrderFilled` at the Portal: 0 on all chains. Legacy `IntentCreated`, legacy `IntentFunded` and `Fulfillment`: 0 on all eight chains. The Ethereum `IntentPublished` count (92) was measured twice with the same result. Prover `IntentProven`: see §13 item 7 (BNB 0).
- **Chain coverage:** six chains carry the listed Portal. Robinhood Chain carries an unlisted Portal (contract nonce 4 read with `eth_getTransactionCount`). Avalanche carries nothing.

Authoritative sources:
- [eco/eco-routes](https://github.com/eco/eco-routes) — the canonical contracts repo.
- [@eco-foundation/routes-ts on npm](https://www.npmjs.com/package/@eco-foundation/routes-ts) — `deployAddresses.csv` and ABIs per version (registry metadata: `https://registry.npmjs.org/@eco-foundation/routes-ts`).
- Docs — [Routes architecture](https://docs.eco.com/routes/architecture/overview) · [Portal](https://docs.eco.com/routes/architecture/portal) · [Vault](https://docs.eco.com/routes/architecture/vault) · [Executor](https://docs.eco.com/routes/architecture/executor) · [Provers](https://docs.eco.com/routes/architecture/provers/overview) · [ERC-7683](https://docs.eco.com/routes/architecture/erc-7683) · [Contract addresses](https://docs.eco.com/resources/contract-addresses) · [Supported chains and tokens](https://docs.eco.com/resources/supported-chains-tokens) · [List chains (API)](https://docs.eco.com/api-reference/v1/chains) · [Docs index](https://docs.eco.com/llms.txt).
- [Eco integrates Robinhood Chain](https://eco.com/blog/eco-integrates-robinhood-chain/) (2026-07-29).
- Verified sources on Blockscout — [Portal (Base)](https://base.blockscout.com/address/0xEC000064576f9C95a8623Bc0eff3db6d296ea6df) · [Executor (Base)](https://base.blockscout.com/address/0x645dADD5Bf354526b68A2befd9A305F7E03b91Ca) · [HyperProver (Base)](https://base.blockscout.com/address/0xec004Ab4870c4e177c66949329dCdb503CE41022) · [CCIPProver (Ethereum)](https://eth.blockscout.com/address/0xceBB7cDDBA4734C7130BF114a37C2dA4C5f3c473) · [ECDSAExecutor (Base)](https://base.blockscout.com/address/0xEc2C96e75B09e29b66bf2Ee5C37fa749eF9AA7c7).

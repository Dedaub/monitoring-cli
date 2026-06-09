# Beamer Bridge — Topics, Selectors, Addresses (Ethereum L1 + Optimism, Base, Arbitrum; counterparty Polygon zkEVM 1101 & PGN 424)

**Status:** verified against live RPC on Ethereum, Optimism, Base, Arbitrum, BNB, Avalanche, and Polygon PoS, plus Polygon zkEVM, and the canonical `beamer-bridge/beamer` repo (mainnet deployment commit `7ccea7e…`), on 2026-06-09.
**Scope:** the single-generation Beamer optimistic rollup-to-rollup token bridge — `RequestManager` (source chain), `FillManager` (target chain), `Resolver` (Ethereum L1), and the per-rollup `*Messenger` contracts. Topics/selectors are **chain-agnostic**; addresses are **network-specific**. Of the seven requested chains, Beamer is live on **Ethereum (1), Optimism (10), Base (8453), Arbitrum One (42161)** and is **NOT deployed on BNB (56), Avalanche (43114), or Polygon PoS (137)** (`eth_getCode` = `0x` for every Beamer address there). It additionally connects to two chains outside the seven: **Polygon zkEVM (1101)** and **Public Goods Network / PGN (424)** — recorded below as findings, not omissions.

Beamer is a **fast-withdrawal / liquidity-provider bridge**, not a lock-and-mint bridge. A user calls `createRequest` on the **source** rollup's `RequestManager` (escrowing tokens + fees); a liquidity provider ("agent") immediately calls `fillRequest` on the **target** rollup's `FillManager`, sending the user their tokens out of the LP's own inventory. The LP later `claimRequest`s on the source chain and, after an optimistic challenge window (the "challenge game"), `withdraw`s the escrowed deposit. Disputes are settled by **L1 resolution**: `FillManager` sends a proof to the L1 `Resolver` through a chain-native messenger, and `Resolver` relays it back to the source `RequestManager`. **There is no canonical minted bridge token** — tokens move from LP inventory, so the bridge moves *existing* tokens (e.g. real USDC) rather than minting a wrapped representation.

Every Beamer contract is a **plain, immutable, non-upgradeable deployment** (`Ownable`, no proxy — EIP-1967 impl slot reads `0x0` on all of them, verified live). There is **no CREATE2 vanity / deterministic cross-chain address scheme**: addresses differ per chain and several are *recycled* (the same literal address is a `RequestManager` on one chain and a `FillManager` or `Messenger` on another) — so you MUST key on `(chainId, address, role)`, never on address alone. The single protocol admin/owner across every contract and chain is the deployer EOA **`0x068053f77E321C8828f5fEA91b6917011b1a77fe`** (verified via `owner()`).

---

## 0. Contract families & versions

| Contract | Lives on | Role | Proxy? | Verified |
|----------|----------|------|--------|----------|
| **RequestManager** | every **source** rollup (incl. ETH L1, OP, Base, Arb, zkEVM) | Escrows the user deposit + fees, runs the optimistic challenge game, holds tokens until `withdraw`. The only contract a user touches on the source side. | **No** (immutable `Ownable`, 14 974 B) | impl slot `0x0` |
| **FillManager** | every **target** rollup | An LP `fillRequest`s here, paying the recipient from LP inventory and emitting a fill proof to L1. The only contract an LP touches on the target side. | **No** (3 728 B) | impl slot `0x0` |
| **Resolver** | **Ethereum L1 only** (chain 1) | Receives fill / non-fill proofs from each `FillManager` (via the target chain's native bridge) and relays them to the correct source `RequestManager`. The L1 arbiter of the challenge game. | **No** (2 802 B) | impl slot `0x0` |
| **`<Chain>L2Messenger`** | each rollup | Beamer's L2-side adapter over the chain's native L1↔L2 bridge; `FillManager`/`RequestManager` call `sendMessage` through it. | **No** | — |
| **`<Chain>L1Messenger`** | **Ethereum L1** (one per connected rollup) | Beamer's L1-side adapter over the chain's native bridge; `Resolver` calls `sendMessage` through it to reach a source `RequestManager`. | **No** | — |
| **MintableToken** | every chain | A **test ERC-20** (`name="Test"`, `symbol="TST"`) deployed alongside the bridge for integration tests — **not a bridge asset**. Listed only so you don't mistake it for a Beamer-minted token. | **No** | — |

`RequestManager` and `FillManager` both inherit `LpWhitelist` (allowed-LP set) and `Ownable`; `RequestManager` additionally inherits `RestrictedCalls` (L1-resolution caller gating) and `Pausable`. `Resolver` inherits `Ownable` + `RestrictedCalls`. The messenger contracts (`OptimismL1/L2Messenger`, `ArbitrumL1/L2Messenger`, `PolygonZkEVMMessenger`, `EthereumL1/L2Messenger`) all inherit `RestrictedCalls` and implement `IMessenger`.

> **A single deployment is BOTH a source and a target.** On Optimism, `0x1c7d…8e12` is the `RequestManager` (source role) and `0x9208…4dB5` is the `FillManager` (target role) — a transfer OP→Base uses OP's RequestManager + Base's FillManager, and a Base→OP transfer uses Base's RequestManager + OP's FillManager. Every live chain runs one of each.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values below recomputed locally with keccak256 on 2026-06-09 from the canonical Solidity sources. `RequestCreated` and `RequestFilled` were additionally confirmed against **live** `eth_getLogs` on the Optimism contracts (see §10).

### 1.1 RequestManager (source-chain activity) — emitter ETH `0x4809…6C5C`, OP `0x1c7d…8e12`, Base `0x1c7d…8e12`, Arb `0x9208…4dB5`, zkEVM `0xc2f4…413f`

| topic0 | Event |
|--------|-------|
| `0x6aea27071459d79f368a97c21a7a6e85af3337282f8a63c25ed6561d41bb9cec` | `RequestCreated(bytes32 indexed requestId, uint256 targetChainId, address sourceTokenAddress, address targetTokenAddress, address indexed sourceAddress, address targetAddress, uint256 amount, uint96 nonce, uint32 validUntil, uint256 lpFee, uint256 protocolFee)` |
| `0xab63a14c4aaba38366fd39116091672bb44520328ee870be35a51e573296e565` | `DepositWithdrawn(bytes32 requestId, address receiver)` |
| `0xf0289b2c09d4e59035c29451cfbb75c07a50fdcc68db2eccef5a84db99285e44` | `ClaimMade(bytes32 indexed requestId, uint96 claimId, address claimer, uint96 claimerStake, address lastChallenger, uint96 challengerStakeTotal, uint256 termination, bytes32 fillId)` |
| `0xc9e74e0700d0c6488af9c81d70fdd4158aea77687137ff85499509c41a10612b` | `ClaimStakeWithdrawn(uint96 claimId, bytes32 indexed requestId, address stakeRecipient)` |
| `0x24529dcb90461cd60643468a2d5fe88517ecc130a358e55f89114edc00f7555f` | `FeesUpdated(uint32 minFeePPM, uint32 lpFeePPM, uint32 protocolFeePPM)` |
| `0x5d4804fe0ec949f552f757bfb400c951422d44c10c004077ecd19a9d1f503562` | `TokenUpdated(address indexed tokenAddress, uint256 transferLimit, uint256 ethInToken)` |
| `0x0cfc78bd83e736fee3ebe0c74fc801f2993eedb0bb43aaf55916bdd18a4c6f7b` | `ChainUpdated(uint256 indexed chainId, uint256 finalityPeriod, uint256 transferCost, uint256 targetWeightPPM)` |
| `0xb32d3c8b5539b0cc3050d5b75e9dad8eca8744a0892259bda27fdb51b9956736` | `RequestResolved(bytes32 requestId, address filler, bytes32 fillId)` (fired by `resolveRequest`, only via L1 resolution) |
| `0x5571b83c623961fb42d39ce6d6d2092153ace66c008e2dc2472ec6d2e8fad045` | `FillInvalidatedResolved(bytes32 requestId, bytes32 fillId)` (fired by `invalidateFill`, only via L1 resolution) |

`RequestCreated` is the workhorse on the source side: **2 indexed fields** (`requestId`, `sourceAddress`) → 3 log topics. `ClaimMade` is emitted **both** on the initial claim and on every challenge round — disambiguate a fresh claim (`lastChallenger == 0x0` and `challengerStakeTotal == 0`) from a challenge (`lastChallenger != 0x0`).

### 1.2 FillManager (target-chain activity) — emitter ETH `0xd300…b83F`, OP `0x9208…4dB5`, Base `0x9208…4dB5`, Arb `0xeF16…81A7`, zkEVM `0xeF16…81A7`

| topic0 | Event |
|--------|-------|
| `0x2995401b199bc45ea8c8b79c27fb204b270cfb74444d546b1a100935e3443887` | `RequestFilled(bytes32 indexed requestId, bytes32 fillId, uint256 indexed sourceChainId, address indexed targetTokenAddress, address filler, uint256 amount)` |
| `0x931b401cf9baede43dc97f7d9dd4017d44f22bfa0a69668d527d9b5fff42b90a` | `FillInvalidated(bytes32 indexed requestId, bytes32 indexed fillId)` |

`RequestFilled` is the workhorse on the target side: **3 indexed fields** (`requestId`, `sourceChainId`, `targetTokenAddress`) → 4 log topics (confirmed live). The **actual recipient is NOT in the event** — `RequestFilled` carries the LP (`filler`) and `amount`, but the user/recipient address is only in the request itself; reconstruct it by matching `requestId` to the source-chain `RequestCreated` (`targetAddress`). `fillId` is the **previous block hash** at fill time (`blockhash(block.number-1)`), not a sequential id.

### 1.3 Resolver (Ethereum L1 only) — emitter `0xD64c…292E`

| topic0 | Event |
|--------|-------|
| `0x44702e0d5959cc77a7f68b33530b86546d1b157d0d74b27010d5f519adae07cb` | `Resolution(uint256 sourceChainId, uint256 fillChainId, bytes32 requestId, address filler, bytes32 fillId)` (`filler == 0x0` ⇒ non-fill / invalidation proof) |

### 1.4 Shared base contracts (LpWhitelist / Ownable / Pausable) — emitted by RequestManager, FillManager, Resolver, Messengers

| topic0 | Event | Emitter(s) |
|--------|-------|-----------|
| `0x371fc559c30f70424413fed6bf7e57dc939651331abad5c970a8ea0921c80b2e` | `LpAdded(address lp)` | RequestManager, FillManager |
| `0x4e774c97f73f4bea034579e4224498d7d9b3a4109eaa70ed3d85c97a5855f198` | `LpRemoved(address lp)` | RequestManager, FillManager |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | all (Ownable) |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | RequestManager (Pausable) |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | RequestManager (Pausable) |

### 1.5 MintableToken (test ERC-20 — not a bridge asset)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

> **Topic0 collisions to watch:** `OwnershipTransferred`, `Paused`/`Unpaused`, and the ERC-20 `Transfer`/`Approval` topic0s are **generic** (shared with thousands of contracts). Always scope by `(chainId, emitter address, topic0)`. The Beamer-specific topics in §1.1–§1.3 are unique signatures and safe to filter on topic0 alone within Beamer's address set.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors computed locally on 2026-06-09. Every state-changing selector below was confirmed **present** in the live Ethereum `RequestManager`/`FillManager`/`Resolver` bytecode via a `63<selector>` PUSH4 dispatcher scan (see §10).

### 2.1 RequestManager — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2f4212b8` | `createRequest(uint256 targetChainId, address sourceTokenAddress, address targetTokenAddress, address targetAddress, uint256 amount, uint256 validityPeriod)` → `bytes32` | Opens a transfer; escrows `amount + lpFee + protocolFee`. Emits `RequestCreated`. **The entrypoint a monitor keys on for "new bridge transfer."** |
| `0x79650559` | `withdrawExpiredRequest(bytes32 requestId)` | User reclaims escrow after expiry (no claims). Emits `DepositWithdrawn`. |
| `0x743c151a` | `claimRequest(bytes32 requestId, bytes32 fillId)` → `uint96` | `payable` — LP claims it filled the request; posts `claimStake`. Emits `ClaimMade`. |
| `0x599b08a2` | `claimRequest(address claimer, bytes32 requestId, bytes32 fillId)` → `uint96` | `payable` — claim on behalf of `claimer`. Same `ClaimMade`. |
| `0xb4d1d27a` | `challengeClaim(uint96 claimId)` | `payable` — one round of the challenge game. Emits `ClaimMade` (with `lastChallenger` set). |
| `0xdee4dea0` | `withdraw(uint96 claimId)` → `address` | Withdraw escrowed deposit + claim stake after resolution. Emits `ClaimStakeWithdrawn` (+ `DepositWithdrawn` on the deposit leg). |
| `0x8c8c3c9d` | `withdraw(address participant, uint96 claimId)` → `address` | Withdraw on behalf of a participant. |
| `0xcf7b287f` | `withdrawProtocolFees(address tokenAddress, address recipient)` | owner-only — sweeps accrued protocol fees. |
| `0x92d0da99` | `updateFees(uint32 minFeePPM, uint32 lpFeePPM, uint32 protocolFeePPM)` | owner-only. Emits `FeesUpdated`. |
| `0xc8e70707` | `updateToken(address tokenAddress, uint256 transferLimit, uint256 ethInToken)` | owner-only. Emits `TokenUpdated`. Sets the per-token transfer cap + ETH price (for fee math). |
| `0x6b868792` | `updateChain(uint256 chainId, uint256 finalityPeriod, uint256 transferCost, uint256 targetWeightPPM)` | owner-only. Emits `ChainUpdated`. **A nonzero `finalityPeriod` is what makes a target chain "supported."** |
| `0x5b3a6ef2` | `resolveRequest(bytes32 requestId, bytes32 fillId, uint256 resolutionChainId, address filler)` | **`restricted`** — callable only by the L1-resolution caller chain (via messenger). Emits `RequestResolved`. |
| `0x03fc4c37` | `invalidateFill(bytes32 requestId, bytes32 fillId, uint256 resolutionChainId)` | **`restricted`** — L1-resolution non-fill proof. Emits `FillInvalidatedResolved`. |
| `0x8456cb59` | `pause()` | owner-only. Blocks `createRequest`; withdrawals still work. Emits `Paused`. |
| `0x3f4ba83a` | `unpause()` | owner-only. Emits `Unpaused`. |
| `0x31e08f7a` | `addAllowedLp(address newLp)` / `0x3993b6ed` `removeAllowedLp(address oldLp)` | owner-only LP whitelist. Emits `LpAdded`/`LpRemoved`. |
| `0x747293fb` | `addCaller(address caller)` / `0x7203ae3b` `addCaller(uint256 callerChainId, address caller, address messenger)` | owner-only — register the L1-resolution caller (RestrictedCalls). |

### 2.2 RequestManager — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x9d866985` | `requests(bytes32)` | request struct (sender, sourceToken, targetChainId, amount, validUntil, lpFee, protocolFee, activeClaims, withdrawClaimId, filler, fillId) |
| `0x3b046f09` | `claims(uint96)` | claim struct (requestId, claimer, claimerStake, lastChallenger, challengerStakeTotal, withdrawnAmount, termination, fillId) |
| `0xe4860339` | `tokens(address)` | `(transferLimit, ethInToken, collectedProtocolFees)` |
| `0x550325b5` | `chains(uint256)` | `(finalityPeriod, transferCost, targetWeightPPM)` — `finalityPeriod==0` ⇒ chain unsupported |
| `0x0e3a918c` | `isWithdrawn(bytes32 requestId)` → `bool` | |
| `0x30a08cbc` | `isInvalidFill(bytes32 requestId, bytes32 fillId)` → `bool` | |
| `0xadb610a3` | `currentNonce()` → `uint96` | shared counter for request + claim IDs |
| `0xeb321173` | `claimStake()` → `uint96` | immutable; OP/Base/Arb/zkEVM = `1.5e15` wei, ETH = `1e16` wei (verified) |
| `0x7dc2cd98` `claimPeriod()` · `0x83d208c3` `claimRequestExtension()` · `0x1d18adc5` `challengePeriodExtension()` | immutables (all `86400` s on mainnet) | |
| `0xae213840` `minLpFee(uint256,address)` · `0x2175fd13` `lpFee(uint256,address,uint256)` · `0xa032b5f4` `protocolFee(uint256)` · `0x9c66b543` `totalFee(uint256,address,uint256)` · `0xeb1cbbab` `transferableAmount(uint256,address,uint256)` | fee math views | |
| `0x0d5877d2` `minFeePPM()` · `0xe2653eeb` `lpFeePPM()` · `0xe7aad5c4` `protocolFeePPM()` | mutable fee params | |
| `0x5c975abb` | `paused()` → `bool` | RequestManager only (Pausable) |

### 2.3 FillManager

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xac7f380a` | `fillRequest(uint256 sourceChainId, address targetTokenAddress, address targetReceiverAddress, uint256 amount, uint96 nonce)` → `bytes32` | LP fills the request out of inventory → recipient. Emits `RequestFilled` + sends L1 proof. **The entrypoint a monitor keys on for "transfer delivered."** |
| `0xee56c910` | `invalidateFill(uint256 sourceChainId, address targetTokenAddress, address targetReceiverAddress, uint256 amount, uint96 nonce, bytes32 fillId)` | Anyone may flag a bogus fill → triggers non-fill L1 proof. Emits `FillInvalidated`. |
| `0x4e543b26` | `setResolver(address _l1Resolver)` | owner-only, **set-once** (no fills possible before it is set). |
| `0x935beb1a` | `l1Resolver()` → `address` | |
| `0x20158c44` | `fills(bytes32 requestId)` → `bytes32 fillId` | |
| `0x3cb747bf` | `messenger()` → `address` | immutable L2 messenger used to send the proof to L1 |
| `0x31e08f7a` `addAllowedLp` / `0x3993b6ed` `removeAllowedLp` / `0x9e375226` `allowedLps(address)` | LP whitelist (shared w/ RequestManager) | |

### 2.4 Resolver (Ethereum L1)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa56e3c38` | `resolve(bytes32 requestId, bytes32 fillId, uint256 fillChainId, uint256 sourceChainId, address filler)` | **`restricted`** — callable only by the native L1 messenger of the fill chain. Relays the proof to the source `RequestManager`. Emits `Resolution`. |
| `0x44596f9b` | `addRequestManager(uint256 chainId, address requestManager, address messenger)` | owner-only — register a source chain's RequestManager + its L1 messenger. |
| `0x308634a5` | `sourceChainInfos(uint256 sourceChainId)` → `(address requestManager, address messenger)` | |

### 2.5 Messengers (`IMessenger`) & shared admin

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xbb5ddb0f` | `sendMessage(address target, bytes message)` | `restricted` — cross-domain send. |
| `0x845c5443` | `callAllowed(address caller, address courier)` → `bool` | gates inbound L1↔L2 calls. |
| `0x77897238` | `nativeMessenger()` → `address` | the underlying chain-native bridge (OP `ICrossDomainMessenger`, etc.). |
| `0xd0e30db0` `deposit()` · `0x3ccfd60b` `withdraw()` · `0xfc7e286d` `deposits(address)` · `0xe78cea92` `bridge()` · `0xfb0e722b` `inbox()` | **ArbitrumL1Messenger only** — pays the Arbitrum retryable-ticket submission fee. | |
| `0x747293fb`/`0x7203ae3b` `addCaller` · `0x0e19a1c6` `callers(uint256,uint256)` | RestrictedCalls admin/view (Resolver, RequestManager, Messengers). | |
| `0x8da5cb5b` `owner()` · `0xf2fde38b` `transferOwnership(address)` · `0x715018a6` `renounceOwnership()` | Ownable (all). | |
| `0x40c10f19` | `mint(address,uint256)` | **MintableToken** (test token) only. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Ethereum hosts the **L1 `Resolver`** AND a full source/target Beamer instance (Ethereum-as-an-L2 via `EthereumL1/L2Messenger`), plus the per-rollup L1 messengers that the `Resolver` uses to reach each source chain.

| Role | Address | One-liner |
|------|---------|-----------|
| **Resolver** (L1 arbiter) | `0xD64c58A150545cb2B1985aFa7D3774617E40292E` | Receives fill/non-fill proofs from every FillManager, relays to source RequestManagers. Emits `Resolution`. |
| **RequestManager** (ETH source) | `0x4809091ee2a26d4e79776c8267666e971f786C5C` | Source-side for transfers *out of* Ethereum. `claimStake = 1e16` wei. |
| **FillManager** (ETH target) | `0xd300e93FE7A4dC6c4FBFBD7a954EFeFBDacbb83F` | Target-side for transfers *into* Ethereum. |
| EthereumL2Messenger | `0xeec87a020D7e03271c310645a73Cb29bb83Ae1D2` | Same-chain messenger (Ethereum is treated as its own rollup). FillManager's `messenger`. |
| EthereumL1Messenger | `0x52bCc9A09f32486C8249f40aAE54d97FE2b2A004` | L1-side adapter for the Ethereum RequestManager. |
| OptimismL1Messenger (→ Optimism) | `0x5CA61Ecf0840184745985Fd18A4eBb75881cEf3E` | Resolver→Optimism RequestManager path (native CrossDomainMessenger `0x2526…5fA1`). |
| OptimismL1Messenger (→ Base) | `0x1c546fD7CA57066d966275e76Acc5A39E816B340` | Resolver→Base RequestManager path (native CrossDomainMessenger `0x866E…0Afa`). |
| ArbitrumL1Messenger (→ Arbitrum) | `0xb0545DF5C69D7dB3F82768C0605b5C8d67cAaF8D` | Resolver→Arbitrum path; bridge `0x8315…ed3a`, inbox `0x4Dbd…b3f`. Holds ETH deposits for retryable fees. |
| OptimismL1Messenger (→ PGN, chain 424) | `0x97BAf688E5d0465E149d1d5B497Ca99392a6760e` | Resolver→Public Goods Network path. **PGN is outside the 7 requested chains.** |
| PolygonZkEVMMessenger (L1, → zkEVM) | `0x6D2dE76A62c81cfD4E8854cC07C8eA74a81479F9` | Resolver→Polygon zkEVM path. **zkEVM 1101 is outside the 7.** |
| MintableToken (test TST) | `0xcCB2562c5970cC276a38FBB7AC6E8B953eE029A9` | Test ERC-20, not a bridge asset. |
| Owner / deployer (all) | `0x068053f77E321C8828f5fEA91b6917011b1a77fe` | EOA admin of every contract on every chain. |

---

## 4. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **RequestManager** | `0x1c7dfaa422CACaA5b368fE22dB84B8329cf88e12` | OP source. `claimStake = 1.5e15` wei, not paused (verified). |
| **FillManager** | `0x9208242FC2148A21737d73de036C6A5B1e934dB5` | OP target. |
| OptimismL2Messenger | `0xc2f48bC4D8A42B82F801315696a92141f6F3413f` | L2 adapter (native L2CrossDomainMessenger predeploy). |
| MintableToken (TST) | `0xacb08C35F015CDDaA7588cF29DbfF935eC56943D` | test token. |

> **Address recycling alert:** OP's `RequestManager` literal `0x1c7d…8e12` is **also** the `RequestManager` on Base; OP's `FillManager` `0x9208…4dB5` is **also** the Base FillManager **and** the Arbitrum RequestManager **and** the Polygon-zkEVM L1 messenger; OP's L2Messenger `0xc2f4…413f` is **also** the Base L2Messenger **and** the zkEVM RequestManager. Same bytecode-class, different role per chain — key on `(chainId, address, role)`.

---

## 5. Addresses — Base (chain ID 8453)

Verified via `eth_getCode` on `https://base-rpc.publicnode.com` on 2026-06-09. **Base shares the OP-stack address layout** (identical literals to Optimism for RequestManager / FillManager / L2Messenger / MintableToken — they were deployed by the same EOA with the same nonce sequence on two OP-stack chains).

| Role | Address | One-liner |
|------|---------|-----------|
| **RequestManager** | `0x1c7dfaa422CACaA5b368fE22dB84B8329cf88e12` | Base source. (≡ OP literal, different chain.) |
| **FillManager** | `0x9208242FC2148A21737d73de036C6A5B1e934dB5` | Base target. (≡ OP literal.) |
| OptimismL2Messenger | `0xc2f48bC4D8A42B82F801315696a92141f6F3413f` | L2 adapter. (≡ OP literal.) |
| MintableToken (TST) | `0xacb08C35F015CDDaA7588cF29DbfF935eC56943D` | test token. (≡ OP literal.) |

Base's L1-side messenger lives on Ethereum (`OptimismL1Messenger (→ Base) 0x1c54…B340`, §3).

---

## 6. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com` on 2026-06-09. Arbitrum uses **different addresses** (Arbitrum-stack messenger, separate nonce lineage).

| Role | Address | One-liner |
|------|---------|-----------|
| **RequestManager** | `0x9208242FC2148A21737d73de036C6A5B1e934dB5` | Arb source. **Same literal as OP/Base FillManager** — different role, different chain. |
| **FillManager** | `0xeF169821403D13345E2b24450601567Cd1d781A7` | Arb target. |
| ArbitrumL2Messenger | `0x8E3823e77492182eA7D3baf6b240c16a446fd863` | L2 adapter (uses `ArbSys` precompile `0x64`). |
| MintableToken (TST) | `0x121777041Dd7D2FB097993401e77284D37eD48b6` | test token. |

Arbitrum's L1-side messenger lives on Ethereum (`ArbitrumL1Messenger 0xb054…aF8D`, §3).

---

## 7. Counterparty chains OUTSIDE the seven requested

Beamer connects two chains that are **not** in the requested set. Recorded as findings (a monitor scoped to the seven will see proofs flow to/from these via the L1 `Resolver` and the L1 messengers in §3).

### 7.1 Polygon zkEVM (chain ID 1101) — **NOT Polygon PoS**

Verified live on `https://zkevm-rpc.com` (RequestManager present, 14 974 B). **Do not confuse with Polygon PoS (137), where Beamer is absent.**

| Role | Address |
|------|---------|
| RequestManager | `0xc2f48bC4D8A42B82F801315696a92141f6F3413f` (≡ OP/Base L2Messenger literal) |
| FillManager | `0xeF169821403D13345E2b24450601567Cd1d781A7` (≡ Arb FillManager literal) |
| PolygonZkEVMMessenger (L2) | `0x9208242FC2148A21737d73de036C6A5B1e934dB5` |
| MintableToken (TST) | `0x121777041Dd7D2FB097993401e77284D37eD48b6` |

### 7.2 Public Goods Network / PGN (chain ID 424)

An OP-stack chain configured in the canonical repo (`request_manager_arguments.claim_stake = 0.0015`); its L1-side `OptimismL1Messenger` `0x97BA…760e` is **live on Ethereum** (verified). PGN was not added to the official subgraph and has since been deprecated by its operator; treat as a low-activity / sunset counterparty.

---

## 8. Cross-chain summary

Presence matrix (rows = chains, cols = Beamer roles; cell = address tail or `—` if absent).

| Chain | ID | RequestManager | FillManager | Resolver | L2 Messenger | In requested 7? |
|---|---|---|---|---|---|---|
| **Ethereum** | 1 | `…6C5C` | `…b83F` | `…292E` ✅ | `…a1D2` (EthL2) | yes |
| **Optimism** | 10 | `…8e12` | `…4dB5` | — | `…413f` | yes |
| **Base** | 8453 | `…8e12` | `…4dB5` | — | `…413f` | yes |
| **Arbitrum One** | 42161 | `…4dB5` | `…81A7` | — | `…f863` | yes |
| **BNB Smart Chain** | 56 | — | — | — | — | yes — **NOT deployed** |
| **Avalanche C-Chain** | 43114 | — | — | — | — | yes — **NOT deployed** |
| **Polygon PoS** | 137 | — | — | — | — | yes — **NOT deployed** |
| Polygon zkEVM | 1101 | `…413f` | `…81A7` | — | `…4dB5` | no (counterparty) |
| Public Goods Network | 424 | (configured) | (configured) | — | OP-stack | no (counterparty, sunset) |

**Three things to internalize:**
1. **The Resolver is Ethereum-L1-only.** All cross-chain dispute resolution funnels through `0xD64c…292E` on chain 1.
2. **No deterministic / vanity addresses** — literals are recycled across chains in different roles. Always key on `(chainId, address, role)`.
3. **BNB, Avalanche, and Polygon PoS have zero Beamer contracts.** Polygon **zkEVM** (1101) is a different chain and *is* connected.

---

## 9. Proxies (old & new)

**There are no proxies anywhere in Beamer.** Every contract is a plain immutable deployment.

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| RequestManager | **Immutable, non-proxy** | EIP-1967 impl slot `0x3608…2bbc` reads `0x0` (verified live on ETH); 14 974 B full bytecode; dispatcher contains the real selectors (not a proxy stub). | none (no upgrade path; redeploy to change). |
| FillManager | **Immutable, non-proxy** | impl slot `0x0` (verified); 3 728 B. | none. |
| Resolver | **Immutable, non-proxy** | impl slot `0x0` (verified); 2 802 B. | none. |
| Messengers / MintableToken | **Immutable, non-proxy** | full bytecode, no EIP-1967 slots. | none. |

There is **no `Upgraded(address)` event to watch** — Beamer cannot be upgraded in place. The only privileged levers are `Ownable` (`owner = 0x0680…77fe`) for fee/token/chain config, LP whitelist, and `pause()`/`unpause()` on the RequestManager. A "new version" of Beamer would be an entirely new set of contracts/addresses, so a monitor should track the deployed-address set, not an impl pointer.

EIP-1967 slots (for completeness — all read `0x0` on Beamer):
- impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`
- admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`

---

## 10. Detection invariants & gotchas

1. **A transfer = `RequestCreated` (source) → `RequestFilled` (target), joined by `requestId`.** `requestId = keccak256(abi.encodePacked(sourceChainId, targetChainId, targetTokenAddress, targetAddress, amount, nonce))` (`BeamerUtils.createRequestId`) — it is computed identically on both chains, so it is the cross-chain join key. There is **no single tx**; the two legs are on different chains, often seconds apart.
2. **The recipient is in `RequestCreated.targetAddress`, NOT in `RequestFilled`.** `RequestFilled` only carries the LP (`filler`) and `amount`. To attribute the actual end-user, match `requestId` back to the source-chain `RequestCreated` (or read `requests(requestId).` — though `targetAddress` is not stored, only on the event). **Do not treat `filler` as the user** — it is a liquidity provider repaying themselves later.
3. **The bridge moves real tokens from LP inventory; it does NOT mint.** Expect a normal ERC-20 `Transfer` from the LP to the recipient inside `fillRequest`, and from the user to the RequestManager inside `createRequest`. There is **no wrapped/minted Beamer token**. `MintableToken` (`TST`) is a test artifact — ignore it as a bridge asset.
4. **`fillId` is the previous block hash**, not a counter (`blockhash(block.number-1)`). It can repeat conceptually and is only meaningful per `requestId`. The `nonce` (in `RequestCreated`) is the monotonic per-RequestManager counter.
5. **`ClaimMade` fires on both claim and every challenge round.** A fresh claim has `lastChallenger == 0x0` & `challengerStakeTotal == 0`; a challenge has `lastChallenger` set. The same `claimId` recurs across rounds — track the latest.
6. **Optimistic, not instant-final.** The honest path needs no L1 resolution. `RequestResolved` / `FillInvalidatedResolved` (source) and `Resolution` (L1) fire **only during disputes / non-fills** — their presence is a dispute signal, not normal flow. A `Resolution` with `filler == 0x0` is a **non-fill proof** (someone claimed without filling).
7. **`resolveRequest` / `invalidateFill(bytes32,bytes32,uint256)` on RequestManager are `restricted`** — they can only be called by the L1 Resolver's caller chain via the messenger, so `tx.to` ≠ RequestManager for these; detect by the `RequestResolved` / `FillInvalidatedResolved` event, not by a direct call.
8. **Two `invalidateFill` overloads with different selectors:** `0xee56c910` (6-arg, public, on **FillManager** — anyone flags a bad fill) vs `0x03fc4c37` (3-arg, restricted, on **RequestManager** — the L1-resolution result). Don't conflate them.
9. **Address recycling across chains.** `0x9208…4dB5` is a FillManager on OP/Base but a RequestManager on Arbitrum; `0xc2f4…413f` is an L2Messenger on OP/Base but a RequestManager on zkEVM. A topic0 + address filter that ignores `chainId`/`role` will mis-attribute. Always key on `(chainId, address, role)`.
10. **Polygon zkEVM ≠ Polygon PoS.** Beamer is on **zkEVM (1101)** and **absent on PoS (137)**. A "Polygon" filter must use chainId 1101, not 137. BNB (56) and Avalanche (43114) have no Beamer at all.
11. **Stakes are in the source chain's native token (ETH on OP/Base/Arb/zkEVM/ETH).** `claimStake` is `1.5e15` wei on the L2s and `1e16` wei on Ethereum. `ClaimMade`/`ClaimStakeWithdrawn`/`challengeClaim` move native value, separate from the bridged ERC-20.
12. **`pause()` only blocks new `createRequest`** — claims, challenges, and withdrawals still work while paused. Watch `Paused`/`Unpaused` on the RequestManager (`0x4809…` on ETH) as an operational signal; the bridge is **currently not paused** (verified).
13. **LP whitelist gates `claimRequest` and `fillRequest`** (`onlyAllowed`). Only whitelisted LPs can fill/claim — watch `LpAdded`/`LpRemoved`. Random addresses cannot fill.
14. **Single EOA admin** `0x0680…77fe` owns every contract on every chain (no multisig, no timelock, no proxy). Any `OwnershipTransferred`, `FeesUpdated`, `ChainUpdated`, `TokenUpdated`, or LP-whitelist change from this key is the full extent of governance — high-value to alert on.

---

## 11. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- RequestManager
TOPIC_REQUEST_CREATED            = '\x6aea27071459d79f368a97c21a7a6e85af3337282f8a63c25ed6561d41bb9cec'
TOPIC_DEPOSIT_WITHDRAWN          = '\xab63a14c4aaba38366fd39116091672bb44520328ee870be35a51e573296e565'
TOPIC_CLAIM_MADE                 = '\xf0289b2c09d4e59035c29451cfbb75c07a50fdcc68db2eccef5a84db99285e44'
TOPIC_CLAIM_STAKE_WITHDRAWN      = '\xc9e74e0700d0c6488af9c81d70fdd4158aea77687137ff85499509c41a10612b'
TOPIC_FEES_UPDATED               = '\x24529dcb90461cd60643468a2d5fe88517ecc130a358e55f89114edc00f7555f'
TOPIC_TOKEN_UPDATED              = '\x5d4804fe0ec949f552f757bfb400c951422d44c10c004077ecd19a9d1f503562'
TOPIC_CHAIN_UPDATED              = '\x0cfc78bd83e736fee3ebe0c74fc801f2993eedb0bb43aaf55916bdd18a4c6f7b'
TOPIC_REQUEST_RESOLVED           = '\xb32d3c8b5539b0cc3050d5b75e9dad8eca8744a0892259bda27fdb51b9956736'
TOPIC_FILL_INVALIDATED_RESOLVED  = '\x5571b83c623961fb42d39ce6d6d2092153ace66c008e2dc2472ec6d2e8fad045'
-- FillManager
TOPIC_REQUEST_FILLED             = '\x2995401b199bc45ea8c8b79c27fb204b270cfb74444d546b1a100935e3443887'
TOPIC_FILL_INVALIDATED           = '\x931b401cf9baede43dc97f7d9dd4017d44f22bfa0a69668d527d9b5fff42b90a'
-- Resolver (Ethereum L1)
TOPIC_RESOLUTION                 = '\x44702e0d5959cc77a7f68b33530b86546d1b157d0d74b27010d5f519adae07cb'
-- Shared base
TOPIC_LP_ADDED                   = '\x371fc559c30f70424413fed6bf7e57dc939651331abad5c970a8ea0921c80b2e'
TOPIC_LP_REMOVED                 = '\x4e774c97f73f4bea034579e4224498d7d9b3a4109eaa70ed3d85c97a5855f198'
TOPIC_OWNERSHIP_TRANSFERRED      = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                   = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'

-- ===== Selectors =====
-- RequestManager (source)
SEL_CREATE_REQUEST               = '\x2f4212b8'
SEL_WITHDRAW_EXPIRED_REQUEST     = '\x79650559'
SEL_CLAIM_REQUEST                = '\x743c151a'
SEL_CLAIM_REQUEST_FOR            = '\x599b08a2'
SEL_CHALLENGE_CLAIM              = '\xb4d1d27a'
SEL_WITHDRAW                     = '\xdee4dea0'
SEL_WITHDRAW_FOR                 = '\x8c8c3c9d'
SEL_WITHDRAW_PROTOCOL_FEES       = '\xcf7b287f'
SEL_UPDATE_FEES                  = '\x92d0da99'
SEL_UPDATE_TOKEN                 = '\xc8e70707'
SEL_UPDATE_CHAIN                 = '\x6b868792'
SEL_RESOLVE_REQUEST              = '\x5b3a6ef2'
SEL_INVALIDATE_FILL_RESTRICTED   = '\x03fc4c37'
SEL_PAUSE                        = '\x8456cb59'
SEL_UNPAUSE                      = '\x3f4ba83a'
-- FillManager (target)
SEL_FILL_REQUEST                 = '\xac7f380a'
SEL_INVALIDATE_FILL_PUBLIC       = '\xee56c910'
SEL_SET_RESOLVER                 = '\x4e543b26'
-- Resolver (L1)
SEL_RESOLVE                      = '\xa56e3c38'
SEL_ADD_REQUEST_MANAGER          = '\x44596f9b'
-- LP whitelist / admin
SEL_ADD_ALLOWED_LP               = '\x31e08f7a'
SEL_REMOVE_ALLOWED_LP            = '\x3993b6ed'
SEL_OWNER                        = '\x8da5cb5b'
SEL_TRANSFER_OWNERSHIP           = '\xf2fde38b'

-- ===== Proxy slots (all read 0x0 on Beamer — non-proxy) =====
EIP1967_IMPL_SLOT                = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT               = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Admin (all chains) =====
BEAMER_OWNER                     = '\x068053f77e321c8828f5fea91b6917011b1a77fe'

-- ===== Ethereum (chain ID 1) =====
ETH_RESOLVER                     = '\xd64c58a150545cb2b1985afa7d3774617e40292e'
ETH_REQUEST_MANAGER              = '\x4809091ee2a26d4e79776c8267666e971f786c5c'
ETH_FILL_MANAGER                 = '\xd300e93fe7a4dc6c4fbfbd7a954efefbdacbb83f'
ETH_L2_MESSENGER                 = '\xeec87a020d7e03271c310645a73cb29bb83ae1d2'
ETH_L1_MESSENGER                 = '\x52bcc9a09f32486c8249f40aae54d97fe2b2a004'
ETH_OP_L1_MESSENGER_TO_OP        = '\x5ca61ecf0840184745985fd18a4ebb75881cef3e'
ETH_OP_L1_MESSENGER_TO_BASE      = '\x1c546fd7ca57066d966275e76acc5a39e816b340'
ETH_ARB_L1_MESSENGER             = '\xb0545df5c69d7db3f82768c0605b5c8d67caaf8d'
ETH_ZKEVM_L1_MESSENGER           = '\x6d2de76a62c81cfd4e8854cc07c8ea74a81479f9'
ETH_PGN_L1_MESSENGER             = '\x97baf688e5d0465e149d1d5b497ca99392a6760e'   -- → PGN 424 (outside the 7)

-- ===== Optimism (chain ID 10) =====
OP_REQUEST_MANAGER               = '\x1c7dfaa422cacaa5b368fe22db84b8329cf88e12'
OP_FILL_MANAGER                  = '\x9208242fc2148a21737d73de036c6a5b1e934db5'
OP_L2_MESSENGER                  = '\xc2f48bc4d8a42b82f801315696a92141f6f3413f'

-- ===== Base (chain ID 8453) — same literals as OP, different chain =====
BASE_REQUEST_MANAGER             = '\x1c7dfaa422cacaa5b368fe22db84b8329cf88e12'
BASE_FILL_MANAGER                = '\x9208242fc2148a21737d73de036c6a5b1e934db5'
BASE_L2_MESSENGER                = '\xc2f48bc4d8a42b82f801315696a92141f6f3413f'

-- ===== Arbitrum One (chain ID 42161) =====
ARB_REQUEST_MANAGER              = '\x9208242fc2148a21737d73de036c6a5b1e934db5'   -- NB: == OP/Base FillManager literal
ARB_FILL_MANAGER                 = '\xef169821403d13345e2b24450601567cd1d781a7'
ARB_L2_MESSENGER                 = '\x8e3823e77492182ea7d3baf6b240c16a446fd863'

-- ===== Polygon zkEVM (chain ID 1101) — counterparty, NOT Polygon PoS =====
ZKEVM_REQUEST_MANAGER            = '\xc2f48bc4d8a42b82f801315696a92141f6f3413f'
ZKEVM_FILL_MANAGER               = '\xef169821403d13345e2b24450601567cd1d781a7'
ZKEVM_L2_MESSENGER               = '\x9208242fc2148a21737d73de036c6a5b1e934db5'

-- ===== NOT deployed (eth_getCode = 0x, 2026-06-09): BNB 56, Avalanche 43114, Polygon PoS 137 =====
```

---

## 12. Verification & sources

How every constant was verified (2026-06-09):

- **Event topic0 / function selectors:** recomputed locally as `keccak256(canonical signature)` (and `[0:4]` for selectors) from the canonical Solidity sources (`contracts/contracts/{RequestManager,FillManager,Resolver,LpWhitelist,RestrictedCalls,MintableToken}.sol` and `contracts/contracts/chains/**/*Messengers.sol`). Param names stripped, `uint`→`uint256`, indexed irrelevant to the hash.
- **Live event cross-check:** `RequestCreated` topic0 `0x6aea2707…` and `RequestFilled` topic0 `0x2995401b…` confirmed via `eth_getLogs` on the Optimism `RequestManager` `0x1c7d…8e12` and `FillManager` `0x9208…4dB5` (e.g. `RequestFilled` tx `0x10ad6bfe…` at OP block 108257349, 4 log topics matching the 3 indexed params; `RequestCreated` tx `0xdb603ab2…`, 3 topics).
- **Selector presence:** confirmed `createRequest`/`claimRequest`/`challengeClaim`/`withdraw`/`resolveRequest`/`invalidateFill`/`withdrawExpiredRequest`/`updateChain`/`pause` present in the live Ethereum `RequestManager` `0x4809…6C5C` dispatcher, and `fillRequest`/`invalidateFill`/`setResolver` in the Ethereum `FillManager`, via `63<selector>` PUSH4 scan of `eth_getCode`.
- **Addresses:** parsed from the canonical repo's `deployments/artifacts/mainnet/*.deployment.json` (commit `7ccea7e…`) and `subgraph/networks.json` (which indexes exactly mainnet/optimism/arbitrum/polygon-zkevm/base), then existence-checked via `eth_getCode` on each chain's RPC. Present (non-empty bytecode) on Ethereum, Optimism, Base, Arbitrum (and Polygon zkEVM); `0x` (NOT deployed) on BNB, Avalanche, Polygon PoS.
- **Proxy classification:** EIP-1967 implementation slot `0x3608…2bbc` read live via `eth_getStorageAt` on the Ethereum `RequestManager`, `FillManager`, and `Resolver` — all return `0x0` ⇒ non-proxy, immutable. No `Upgraded` event exists.
- **Live state (`eth_call`):** `owner()` = `0x0680…77fe` on Resolver/RequestManager/FillManager across ETH + OP (single-EOA admin, no multisig); `paused()` = false on ETH + OP RequestManager; `claimStake()` = `1.5e15` wei on OP (matches the deployment arg) and `1e16` wei on Ethereum.

**Authoritative sources:**
- Canonical repo: [github.com/beamer-bridge/beamer](https://github.com/beamer-bridge/beamer) — `contracts/contracts/*.sol`, `deployments/artifacts/mainnet/*.deployment.json`, `subgraph/networks.json`, `deployments/config/mainnet/*.json`.
- Official docs: [docs.beamerbridge.com](https://docs.beamerbridge.com) (contracts architecture, challenge game, L1 resolution).
- Explorers: [Etherscan Resolver](https://etherscan.io/address/0xD64c58A150545cb2B1985aFa7D3774617E40292E) · [Optimistic Etherscan RequestManager](https://optimistic.etherscan.io/address/0x1c7dfaa422CACaA5b368fE22dB84B8329cf88e12) · [Basescan FillManager](https://basescan.org/address/0x9208242FC2148A21737d73de036C6A5B1e934dB5) · [Arbiscan FillManager](https://arbiscan.io/address/0xeF169821403D13345E2b24450601567Cd1d781A7) · [Polygon zkEVM explorer](https://zkevm.polygonscan.com/address/0xc2f48bC4D8A42B82F801315696a92141f6F3413f).

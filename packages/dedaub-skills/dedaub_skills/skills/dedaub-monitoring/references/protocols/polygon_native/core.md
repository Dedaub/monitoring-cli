# Polygon PoS Bridge — Topics, Selectors, Addresses (Ethereum L1 ⇄ Polygon PoS 137)

**Status:** verified against live RPC on every listed chain and the canonical `0xPolygon/pos-portal`, `0xPolygon/fx-portal`, and `maticnetwork/contracts` (Plasma/RootChain) repos on 2026-06-09.
**Scope:** the canonical **Polygon PoS Bridge** — the official trustless bridge between **Ethereum mainnet (chain 1)** and **Polygon PoS (chain 137)**. It is made of three on-chain subsystems that all share the same L1↔137 axis: (a) the **PoS portal** (RootChainManager + token predicates ⇄ ChildChainManager + child tokens), (b) the **FX portal** (FxRoot/FxChild arbitrary-message tunnel), and (c) the legacy **Plasma bridge + checkpoint layer** (DepositManager / WithdrawManager / RootChain). Topics and selectors are **chain-agnostic**; addresses are **network-specific**. **The bridge contracts exist on exactly two chains: Ethereum (L1) and Polygon PoS (137). They are NOT deployed on Base, BNB, Avalanche, Arbitrum, or Optimism** (`eth_getCode = 0x` for every bridge address on those five — verified §6).

The Polygon PoS Bridge is a **lock-and-mint / burn-and-unlock** bridge, not a messaging mesh: the only counterparty chain is Polygon PoS (137). There is **no single cross-chain canonical address** — L1 and 137 use entirely different addresses, and you must key every record on `(chainId, address)`. The PoS-portal and Plasma core contracts are **upgradeable proxies using Polygon's own `matic.network.proxy.*` storage convention (NOT EIP-1967)** — reading the standard EIP-1967 slot returns `0x` and will make you wrongly conclude "immutable" (§7). The FX-portal contracts (FxRoot/FxChild/StateSender) are **immutable** (no proxy). Deposits L1→137 are asynchronous (state-sync, ~22 min); withdrawals 137→L1 require a **checkpoint** (every ~30–60 min) plus a user-submitted Merkle proof `exit(bytes)`.

> **Two parallel bridges, one protocol.** The **PoS portal** (RootChainManager, ~2019-onward, the default for almost all assets) and the older **Plasma bridge** (DepositManager/WithdrawManager, MATIC/ERC-20 only, predates PoS) are *both live on L1*. Most modern token flow is PoS-portal; Plasma is legacy but still functional. MATIC/POL itself historically bridged via Plasma. Treat them as two subsystems of the same bridge, not two versions.

---

## 0. Contract families & versions

| Subsystem | L1 contract(s) | 137 contract(s) | Role | Proxy? |
|-----------|----------------|------------------|------|--------|
| **PoS portal — manager** | RootChainManager | ChildChainManager | Deposit router (L1) / mint-on-deposit dispatcher (137); token map registry | matic-proxy |
| **PoS portal — predicates** | ERC20 / Ether / MintableERC20 / ERC721 / ERC1155 / MintableERC721 / MintableERC1155 Predicate | (child tokens are UChildERC20/UChildERC721/…) | Lock L1 collateral on deposit, release on exit; emit `Locked*`/`Exited*` | matic-proxy (predicates); child tokens = UChild proxy |
| **FX portal (messaging)** | FxRoot + StateSender | FxChild + StateReceiver predeploy | Arbitrary `bytes` message tunnel L1→137 (and 137→L1 via checkpoint) | **immutable** (FxRoot/FxChild/StateSender) |
| **State sync (L1→137 data)** | StateSender (`0x28e4…`) | StateReceiver predeploy (`0x…001001`) | Validator state-sync transport that delivers every deposit/message to 137 | StateSender immutable; predeploy is a genesis-injected system contract |
| **Plasma bridge (legacy)** | DepositManager + WithdrawManager + Registry | (Plasma child ledger) | Legacy MATIC/ERC-20 lock-withdraw; `NewDepositBlock` / Plasma exits | matic Plasma-proxy (slot0=owner, slot1=impl) |
| **Checkpoint layer** | RootChain (proxy) + StakeManager | — | Heimdall validators checkpoint 137 → L1 (`NewHeaderBlock`); gates all 137→L1 withdrawals | Plasma-proxy / matic-proxy |

There is **no V1/V2/V3 redeploy lineage** — each proxy has been upgraded in place (live impls in §7). Hence this single `core.md`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09. `LockedERC20`, `ExitedERC20`, `StateSynced`, `NewHeaderBlock` additionally confirmed against live `eth_getLogs` (cited below).

### 1.1 RootChainManager (L1 deposit router) — ETH `0xA0c6…7C77`

| topic0 | Event |
|--------|-------|
| `0x9e651a8866fbea043e911d816ec254b0e3c992c06fff32d605e72362d6023bd9` | `TokenMapped(address indexed rootToken, address indexed childToken, bytes32 indexed tokenType)` |
| `0x8643692ae1c12ec91fa18e50b82ed93fa314f580999a236824db6de9ae0d839b` | `PredicateRegistered(bytes32 indexed tokenType, address indexed predicateAddress)` |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` (AccessControl) |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` |

RootChainManager itself **emits no per-deposit event** — the deposit is signalled by the predicate's `Locked*` event plus a `StateSynced` from the StateSender. Watch `TokenMapped` for new-asset onboarding and `PredicateRegistered`/`RoleGranted` for governance.

### 1.2 Token predicates (L1 — emit lock on deposit, exit on withdrawal)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x9b217a401a5ddf7c4d474074aff9958a18d48690d77cc2151c4706aa7348b401` | `LockedERC20(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256 amount)` | ERC20Predicate `0x40ec…bbDf` *(verified live)* |
| `0xbb61bd1b26b3684c7c028ff1a8f6dabcac2fac8ac57b66fa6b1efb6edeab03c4` | `ExitedERC20(address indexed exitor, address indexed rootToken, uint256 amount)` | ERC20Predicate *(verified live)* |
| `0x3e799b2d61372379e767ef8f04d65089179b7a6f63f9be3065806456c7309f1b` | `LockedEther(address indexed depositor, address indexed depositReceiver, uint256 amount)` | EtherPredicate `0x8484…2B30` |
| `0x0fc0eed41f72d3da77d0f53b9594fc7073acd15ee9d7c536819a70a67c57ef3c` | `ExitedEther(address indexed exitor, uint256 amount)` | EtherPredicate |
| `0x31472eae9e158460fea5622d1fcb0c5bdc65b6ffb51827f7bc9ef5788410c34c` | `LockedMintableERC20(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256 amount)` | MintableERC20Predicate `0x9923…74e4` |
| `0x42315cb7471194a6f162099cd1052b95b750612a46472e887f7784b95aa2c4c3` | `ExitedMintableERC20(address indexed exitor, address indexed rootToken, uint256 amount)` | MintableERC20Predicate |
| `0x8357472e13612a8c3d6f3e9d71fbba8a78ab77dbdcc7fcf3b7b645585f0bbbfc` | `LockedERC721(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256 tokenId)` | ERC721Predicate `0xE6F4…F7AD` |
| `0x5345c2beb0e49c805f42bb70c4ec5c3c3d9680ce45b8f4529c028d5f3e0f7a0d` | `LockedERC721Batch(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256[] tokenIds)` | ERC721Predicate |
| `0xe9ae525a9512e4ebce82a4301c43bc0915b47778d50e13d49319952b6881f7a9` | `ExitedERC721(address indexed exitor, address indexed rootToken, uint256 tokenId)` | ERC721Predicate |
| `0x5a921678b5779e4471b77219741a417a6ad6ec5d89fa5c8ce8cd7bd2d9f34186` | `LockedBatchERC1155(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256[] ids, uint256[] amounts)` | ERC1155Predicate `0x0B90…B88f` |
| `0x99648b7247cedda2aa663d8f7d69eceb7b682f0646d0efb5983510f18d0dfdce` | `LockedSingleERC1155(address indexed depositor, address indexed depositReceiver, address indexed rootToken, uint256 id, uint256 amount)` | ERC1155Predicate |
| `0x0dfcc6a24983c122af4c33249bc348ddd51b32984b1dbf715b7f5de2bbe5f4d1` | `ExitedSingleERC1155(address indexed exitor, address indexed rootToken, uint256 id, uint256 amount)` | ERC1155Predicate |
| `0x869b80aaea02f34f7fb379faec6f4b1ae676cad20fe5603715fdaac6f135f596` | `ExitedBatchERC1155(address indexed exitor, address indexed rootToken, uint256[] ids, uint256[] amounts)` | ERC1155Predicate |

**`Locked*` = the L1 user just deposited; `Exited*` = the L1 user just completed a withdrawal/exit.** These are the workhorse deposit/withdrawal signals on the L1 side. `MintableERC20Predicate` is used by assets that are *native to Polygon* and minted on L1 only when withdrawn (the asset originates on 137 — opposite custody direction from the plain ERC20Predicate).

### 1.3 ChildChainManager + child tokens (Polygon 137)

The ChildChainManager (`0xA6FA…C0aa`) is invoked by the validator state-sync and calls `deposit`/`withdraw` on the child token. **It emits the AccessControl `RoleGranted`/`RoleRevoked` topics (§1.1) only.** The actual mint/burn shows up on the **child token** as ERC-20 `Transfer` to/from `address(0)`:

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | child token — `from = 0x0` ⇒ deposit-mint; `to = 0x0` ⇒ withdraw-burn |

There is **no `Deposit`/`Withdraw` event on the standard UChildERC20** child token — only ERC-20 `Transfer`. Detect a completed L1→137 deposit by a `Transfer(0x0 → user)` on the child token in the same block the state-sync was applied.

### 1.4 FX portal — FxRoot / StateSender (L1) and FxChild / StateReceiver (137)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x103fed9db65eac19c4d870f49ab7520fe03b99f1838e5996caf47e9e43308392` | `StateSynced(uint256 indexed id, address indexed contractAddress, bytes data)` | **StateSender** `0x28e4…bFbE` (L1) *(verified live)* |
| `0xf091cd9cbbaff01426d8183042dff452ef18e6690f19816d5dd114e00761e0e8` | `NewFxMessage(address rootMessageSender, address receiver, bytes data)` | FxChild `0x8397…a28a` (137) |
| `0x1a77c658a097b28097b54b8acb928a569a3830a6cbed2de1f60001c0757eb0d6` | `FxWithdrawERC20(address indexed rootToken, address indexed childToken, address indexed userAddress, uint256 amount)` | FxERC20 tunnels (app-layer; only if a project uses fx-portal token tunnels) |
| `0x8a58355ceb4626422a66b0f36743672dde8507c6be664f0e5b9de8350a132159` | `FxDepositERC20(address indexed rootToken, address indexed depositor, address indexed userAddress, uint256 amount)` | FxERC20 tunnels (app-layer) |

**`StateSynced` is the single most important deposit-side event** — *every* L1→137 deposit (PoS portal AND fx-portal) routes through StateSender and emits one `StateSynced`. The `contractAddress` is the 137-side receiver (ChildChainManager or an FxChild). The `data` is the abi-encoded payload (depositor, token, amount). 117 logs in a 3000-block window confirmed live.

### 1.5 Plasma bridge & checkpoint layer (L1)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xba5de06d22af2685c6c7765f60067f7d2b08c2d29f53cdf14d67f6d1c9bfb527` | `NewHeaderBlock(address indexed proposer, uint256 indexed headerBlockId, uint256 indexed reward, uint256 start, uint256 end, bytes32 root)` | **RootChain** `0x86E4…C287` *(verified live — 58 logs / 10k blocks)* |
| `0xca1d8316287f938830e225956a7bb10fd5a1a1506dd2eb3a476751a488117205` | `ResetHeaderBlock(address indexed proposer, uint256 indexed headerBlockId)` | RootChain |
| `0x1dadc8d0683c6f9824e885935c1bec6f76816730dcec148dda8cf25a7b9f797b` | `NewDepositBlock(address indexed owner, address indexed token, uint256 amountOrNFTId, uint256 depositBlockId)` | Plasma DepositManager `0x401F…188b` |
| `0xbb61bd1b26b3684c7c028ff1a8f6dabcac2fac8ac57b66fa6b1efb6edeab03c4` | (Plasma withdraws also go through WithdrawManager-specific events; ERC20Predicate `ExitedERC20` topic reused on the PoS side) | — |

> **Checkpoint-event gotcha (verified live):** the live `NewHeaderBlock` has **SIX** fields including the `reward` — `NewHeaderBlock(address,uint256,uint256,uint256,uint256,bytes32)`, topic0 **`0xba5de06d…`**. The 5-field signature `NewHeaderBlock(address,uint256,uint256,uint256,bytes32)` (topic0 `0xf146921b…`) you'll find in older docs/ABIs **does not match current logs** — using it yields zero results. Always scan `0xba5de06d…`.

`NewHeaderBlock` is the **checkpoint** event — it gates every 137→L1 withdrawal (a user can't `exit()` until the block containing their burn has been checkpointed). `headerBlockId` increments by 10000 (`currentHeaderBlock()` = 1042910000 on 2026-06-09 — this is a live counter; re-read for the current value).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All RootChainManager / predicate / RootChain / DepositManager / ChildChainManager / UChildERC20 selectors below verified **present** in the live implementation bytecode (PUSH4 scan) on 2026-06-09.

### 2.1 RootChainManager (L1) — `0xA0c6…7C77`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4faa8a26` | `depositEtherFor(address user)` | `payable` — deposit native ETH to 137. Emits `LockedEther` + `StateSynced`. |
| `0xe3dec8fb` | `depositFor(address user, address rootToken, bytes depositData)` | Deposit ERC-20/721/1155. `depositData` = abi-encoded amount/tokenId(s). Emits `Locked*` + `StateSynced`. |
| `0x3805550f` | `exit(bytes inputData)` | **Withdrawal completion** — submit the burn-proof to release L1 collateral. Emits `Exited*`. |
| `0x9173b139` | `mapToken(address rootToken, address childToken, bytes32 tokenType)` | Governance: map a new asset. Emits `TokenMapped`. |
| `0xd233a3c7` | `remapToken(address rootToken, address childToken, bytes32 tokenType)` | Governance: change an existing mapping. |
| `0x0c3894bb` | `cleanMapToken(address rootToken, address childToken)` | Governance: clear a stale mapping. |
| `0x0c598220` | `registerPredicate(bytes32 tokenType, address predicate)` | Governance. Emits `PredicateRegistered`. |
| `0xea60c7c4` | `rootToChildToken(address rootToken)` → `address` | View — L1→137 token lookup. |
| `0x6e86b770` | `childToRootToken(address childToken)` → `address` | View — 137→L1 token lookup. |
| `0xe43009a6` | `tokenToType(address rootToken)` → `bytes32` | View — the predicate type-id. |
| `0xe66f9603` | `typeToPredicate(bytes32 tokenType)` → `address` | View — type-id → predicate addr. |
| `0x607f2d42` | `processedExits(bytes32 exitHash)` → `bool` | View — replay-guard; `true` = this exit already paid. |
| `0x6cb136b0` | `setStateSender(address)` / `0xdc993a23` `setChildChainManagerAddress(address)` | Governance wiring. |
| `0x2f2ff15d` | `grantRole(bytes32,address)` / `0x91d14854` `hasRole(bytes32,address)` | AccessControl. |

`tokenType` ids are `keccak256("ERC20")`, `keccak256("ERC721")`, `keccak256("ERC1155")`, `keccak256("Ether")`, etc., set at predicate registration.

### 2.2 Token predicates (L1) — only the manager may call these

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xe375b64e` | `lockTokens(address depositor, address depositReceiver, address rootToken, bytes depositData)` | every `*Predicate` (emits `Locked*`) — callable only by RootChainManager (`MANAGER_ROLE`). |
| `0x8274664f` | `exitTokens(address sender, address rootToken, bytes log)` | every `*Predicate` (emits `Exited*`) — releases collateral on a proven exit. |

### 2.3 ChildChainManager (137) — `0xA6FA…C0aa`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x26c53bea` | `onStateReceive(uint256 stateId, bytes data)` | Called by the StateReceiver predeploy to apply a synced deposit → mints on the child token. |
| `0x47400269` | `mapToken(address rootToken, address childToken)` | Governance mapping (137 side). |
| `0x0c3894bb` | `cleanMapToken(address rootToken, address childToken)` | Governance. |
| `0x2f2ff15d` | `grantRole(bytes32,address)` / `0x91d14854` `hasRole(bytes32,address)` | AccessControl (`DEPOSITOR_ROLE` etc.). |

### 2.4 UChildERC20 child tokens (137) — e.g. USDC.e impl `0xdd91…2226`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xcf2c52cb` | `deposit(address user, bytes depositData)` | Mints on the child; callable only by `DEPOSITOR_ROLE` (= ChildChainManager). |
| `0x2e1a7d4d` | `withdraw(uint256 amount)` | **Burns** the child token to start a 137→L1 withdrawal. |

### 2.5 FX portal

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xb4720477` | `sendMessageToChild(address receiver, bytes data)` | FxRoot (L1) — push an arbitrary message to 137. |
| `0x16f19831` | `syncState(address receiver, bytes data)` | StateSender (L1) — low-level state-sync emit (called by FxRoot/RootChainManager). |
| `0xaa677354` | `register(address sender, address receiver)` | StateSender (L1) — allowlist a sync receiver. |
| `0x26c53bea` | `onStateReceive(uint256 stateId, bytes data)` | FxChild (137) — receives the synced message, emits `NewFxMessage`. |

### 2.6 Plasma + checkpoint layer (L1)

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x4e43e495` | `submitCheckpoint(bytes data, uint256[3][] sigs)` | RootChain `0x86E4…C287` — validators post a checkpoint. Emits `NewHeaderBlock`. |
| `0x6a791f11` | `submitHeaderBlock(bytes,bytes)` | RootChain — legacy checkpoint entrypoint (present in impl). |
| `0xec7e4855` | `currentHeaderBlock()` → `uint256` | RootChain view (= 1042910000 on 2026-06-09; live counter). |
| `0xb87e1b66` | `getLastChildBlock()` → `uint256` | RootChain view — last checkpointed 137 block. |
| `0x8b9e4f93` | `depositERC20ForUser(address token, address user, uint256 amount)` | Plasma DepositManager `0x401F…188b`. Emits `NewDepositBlock`. |
| `0x98ea5fca` | `depositEther()` | Plasma DepositManager — `payable`. |
| `0x7b1f7117` | `depositBulk(address[] tokens, uint256[] amounts, address user)` | Plasma DepositManager. |

### 2.7 Proxy admin (matic-proxy & Plasma-proxy)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x025b22bc` | `updateImplementation(address newImpl)` | matic-proxy upgrade entrypoint (RootChainManager/predicates/ChildChainManager). Emits `ProxyUpdated`. |
| `0x5c60da1b` | `implementation()` → `address` | matic-proxy / Plasma-proxy current impl getter. |
| `0xf1739cae` | `transferProxyOwnership(address)` | matic-proxy ownership handover. Emits `OwnerUpdate`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Proxy impls read live from the matic/Plasma slot (§7).

### 3.1 PoS portal (the default bridge)

| Role | Address | One-liner |
|------|---------|-----------|
| **RootChainManager** (proxy) | `0xA0c68C638235ee32657e8f720a23ceC1bFc77C77` | Deposit router + token-map registry; `depositFor`/`exit`. impl `0xf0235dca…62dfa`. |
| RootChainManager impl (live) | `0xf0235dca8fb0d3999685724dcbb9dd00c5d62dfa` | Current logic. (The `0x37D2…1997` impl listed in some old registries is stale.) |
| **ERC20Predicate** (proxy) | `0x40ec5B33f54e0E8A33A975908C5BA1c14e5BbbDf` | Locks/releases ERC-20s. impl `0x1f4c1e0a…84f6`. Emits `LockedERC20`/`ExitedERC20`. |
| **EtherPredicate** (proxy) | `0x8484Ef722627bf18ca5Ae6BcF031c23E6e922B30` | Locks/releases native ETH. impl `0xeb185ed8…c874`. |
| **MintableERC20Predicate** (proxy) | `0x9923263fA127b3d1484cFD649df8f1831c2A74e4` | For Polygon-native ERC-20s (mint on L1 only on withdrawal). impl `0x94d40724…dfae`. |
| **ERC721Predicate** (proxy) | `0xE6F45376f64e1F568BD1404C155e5fFD2F80F7AD` | Locks/releases ERC-721. impl `0x02bc987f…1072`. |
| **ERC1155Predicate** (proxy) | `0x0B9020d4E32990D67559b1317c7BF0C15D6EB88f` | Locks/releases ERC-1155. impl `0xcfa65db7…021d`. |
| MintableERC721Predicate (proxy) | `0x932532aA4c0174b8453839A6E44eE09Cc615F2b7` | Polygon-native ERC-721. impl `0xba313892…689b`. |
| MintableERC1155Predicate (proxy) | `0x2d641867411650cd05dB93B59964536b1ED5b1B7` | Polygon-native ERC-1155. impl `0xfd47e7d6…e747`. |

### 3.2 FX portal + state sync

| Role | Address | One-liner |
|------|---------|-----------|
| **FxRoot** | `0xfe5e5D361b2ad62c541bAb87C45a0B9B018389a2` | L1 message tunnel root; `sendMessageToChild`. **Immutable** (no proxy). |
| **StateSender** | `0x28e4F3a7f651294B9564800b2D01f35189A5bFbE` | L1 state-sync transport; emits **`StateSynced`** for *every* deposit/message to 137. **Immutable**. |

### 3.3 Plasma bridge + checkpoint layer

| Role | Address | One-liner |
|------|---------|-----------|
| **DepositManager** (Plasma proxy) | `0x401F6c983eA34274ec46f84D70b31C151321188b` | Legacy MATIC/ERC-20 deposits; `NewDepositBlock`. impl `0xb00aa68b…44fc`. |
| **RootChain** (Plasma proxy) | `0x86E4Dc95c7FBdBf52e33D563BbDB00823894C287` | **Checkpoint contract** — validators post 137 state roots; emits `NewHeaderBlock`. impl `0x536c55cf…bd03`. |
| **StakeManager** (proxy) | `0x5e3Ef299fDDf15eAa0432E6e66473ace8c13D908` | Validator staking that authorises checkpoints. impl `0x3ad88467…076c`. |
| Registry | `0x33a02E6cC863D393d6Bf231B697b82F6e499cA71` | Plasma contract registry (DepositManager slot3 points here). |
| Proxy owner / governance | `0xcaf0aa768a3ae1297df20072419db8bb8b5c8cef` | Owns the matic & Plasma proxies (Polygon governance Timelock-style contract, 11,395 B). |

### 3.4 Bridged-asset reference (L1 side)

| Token | L1 address | Note |
|-------|-----------|------|
| MATIC (legacy) | `0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0` | Old PoS token; bridged historically via Plasma. |
| POL (migration token) | `0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6` | MATIC→POL upgrade token. |

---

## 4. Addresses — Polygon PoS (chain ID 137)

All verified via `eth_getCode` returning non-empty bytecode on `https://polygon-bor-rpc.publicnode.com` on 2026-06-09. **None of the addresses match their L1 counterparts** — key on `(chainId, address)`.

| Role | Address | One-liner |
|------|---------|-----------|
| **ChildChainManager** (proxy) | `0xA6FA4fB5f76172d178d61B04b0ecd319C5d1C0aa` | Applies synced deposits → mints child tokens; `onStateReceive`. impl `0xa40fc078…f1b5`, owner `0x3a635c48…5cf5`. |
| **FxChild** | `0x8397259c983751DAf40400790063935a11afa28a` | 137 message-tunnel child; emits `NewFxMessage`. **Immutable** (no proxy). |
| **StateReceiver** (system predeploy) | `0x0000000000000000000000000000000000001001` | Genesis-injected system contract; Bor delivers state-sync data (`commitState`) and dispatches `onStateReceive`. |
| MATIC (native gas, `0x…1010`) | `0x0000000000000000000000000000000000001010` | Native gas token system contract. |
| WMATIC/WPOL | `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` | Wrapped gas token. |
| USDC.e (bridged) | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` | UChildERC20 proxy; impl `0xdd9185db…2226`. `deposit`/`withdraw`. |
| WETH (bridged) | `0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619` | UChildERC20 (bridged ETH). |

Child tokens are **UChildERC20/UChildERC721/UChildERC1155 proxies** (matic-proxy convention). Their `DEPOSITOR_ROLE` is the ChildChainManager; mints/burns appear only as ERC-20 `Transfer` to/from `0x0` (§1.3).

---

## 5. Decimals & flow timing

- Deposits (L1→137) are **asynchronous**: `depositFor` → `LockedERC20` + `StateSynced` on L1, then ~22 min later a `Transfer(0x0→user)` mint on the 137 child token (via validator state-sync → `onStateReceive`). **No single tx spans both chains.**
- Withdrawals (137→L1) are **two-phase**: (1) `withdraw(amount)` burns on 137 (`Transfer(user→0x0)`); (2) after a `NewHeaderBlock` checkpoint covers that block, the user calls `exit(bytes)` on L1 → `Exited*` releases collateral. Median end-to-end ≈ 30 min–3 h.
- `processedExits(exitHash)` is the replay guard — an exit hash can be paid only once.
- Amounts are the raw token amounts (no signed amounts, no fee-on-transfer logic inside the bridge; FoT tokens behave oddly because the predicate locks the pre-fee amount).

---

## 6. Cross-chain summary

| Chain | ID | RootChainManager / Predicates | FxRoot/StateSender | Plasma+RootChain | ChildChainManager / FxChild |
|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ all (`0xA0c6…`, `0x40ec…`, …) | ✅ (`0xfe5e…`, `0x28e4…`) | ✅ (`0x401F…`, `0x86E4…`) | — |
| **Polygon PoS** | 137 | — | — | — | ✅ (`0xA6FA…`, `0x8397…`) |
| Base | 8453 | ❌ `0x` | ❌ `0x` | ❌ `0x` | ❌ `0x` |
| BNB Smart Chain | 56 | ❌ `0x` | ❌ `0x` | ❌ `0x` | ❌ `0x` |
| Avalanche | 43114 | ❌ `0x` | ❌ `0x` | ❌ `0x` | ❌ `0x` |
| Arbitrum One | 42161 | ❌ `0x` | ❌ `0x` | ❌ `0x` | ❌ `0x` |
| Optimism | 10 | ❌ `0x` | ❌ `0x` | ❌ `0x` | ❌ `0x` |

**This bridge connects exactly two chains: Ethereum (1) ⇄ Polygon PoS (137).** There is **no deployment on Base / BNB / Avalanche / Arbitrum / Optimism** — every bridge address returns `0x` on all five (verified 2026-06-09). The only counterparty chain is Polygon PoS; there are no out-of-the-seven counterparty chains (the related **Polygon zkEVM bridge** — chainId 1101 — is a *separate* protocol with its own `PolygonZkEVMBridge` contracts and is out of scope for this file).

**Address tells:** no vanity. L1 RootChainManager `0xA0c6…`, ERC20Predicate `0x40ec…`; 137 ChildChainManager `0xA6FA…`, FxChild `0x8397…`. The StateReceiver `0x…001001` and native MATIC `0x…1010` are genesis system predeploys (recognisable by their tiny address).

---

## 7. Proxies (old & new)

**Polygon does NOT use EIP-1967.** Reading the EIP-1967 impl slot `0x360894…2bbc` returns `0x0` on every PoS-portal contract — you would wrongly conclude "immutable." There are three patterns:

| Contract | Pattern | Detection (impl pointer) | Upgrade auth |
|----------|---------|--------------------------|--------------|
| RootChainManager, all 7 predicates, ChildChainManager, child UChild* tokens | **matic-proxy** (OpenZeppelin-fork `Proxy.sol`) | impl at slot `keccak256("matic.network.proxy.implementation")` = `0xbaab7dbf64751104133af04abc7d9979f0fda3b059a322a8333f533d3f32bf7f`; owner at `keccak256("matic.network.proxy.owner")` = `0x44f6e2e8884cba1236b7f22f351fa5d88b17292b7e0225ca47e5ecdf6055cdd6` | proxy owner (`0xcaf0aa76…` on L1, `0x3a635c48…` on 137) via `updateImplementation` |
| DepositManager, RootChain (Plasma) | **Plasma-proxy** (`UpgradableProxy`) | **slot 0 = owner, slot 1 = implementation** (plain sequential storage, NOT a hashed slot) | proxy owner `0xcaf0aa76…` |
| StakeManager | **matic-proxy** | matic impl slot (impl `0x3ad88467…076c`) | proxy owner `0xcaf0aa76…` |
| **FxRoot, FxChild, StateSender** | **immutable** (no proxy) | EIP-1967 *and* matic impl slots both `0x0`; full runtime bytecode | n/a |

### 7.1 Live implementations (read 2026-06-09)

| Proxy | Chain | Live impl | Owner |
|-------|-------|-----------|-------|
| RootChainManager `0xA0c6…7C77` | 1 | `0xf0235dca8fb0d3999685724dcbb9dd00c5d62dfa` | `0xcaf0aa768a3ae1297df20072419db8bb8b5c8cef` |
| ERC20Predicate `0x40ec…bbDf` | 1 | `0x1f4c1e0afbeb5b5b86d7722549274434b29884f6` | `0xcaf0aa76…` |
| EtherPredicate `0x8484…2B30` | 1 | `0xeb185ed8f664d105903ef434e5becd214a8ac874` | `0xcaf0aa76…` |
| MintableERC20Predicate `0x9923…74e4` | 1 | `0x94d40724d6aa4ab313065006e4ba8ca448dcdfae` | `0xcaf0aa76…` |
| ERC721Predicate `0xE6F4…F7AD` | 1 | `0x02bc987f54b54bf18ca6e20a13e57508ec561072` | `0xcaf0aa76…` |
| ERC1155Predicate `0x0B90…B88f` | 1 | `0xcfa65db73cb45d458d0a98006d3d558b5e1f021d` | `0xcaf0aa76…` |
| MintableERC721Predicate `0x9325…F2b7` | 1 | `0xba31389292f7edfc7b60b937b97014b4c354689b` | `0xcaf0aa76…` |
| MintableERC1155Predicate `0x2d64…b1B7` | 1 | `0xfd47e7d657b07b071c3362bbce908a70895ee747` | `0xcaf0aa76…` |
| DepositManager `0x401F…188b` (slot1) | 1 | `0xb00aa68b87256e2f22058fb2ba3246eec54a44fc` | `0xcaf0aa76…` (slot0) |
| RootChain `0x86E4…C287` (slot1) | 1 | `0x536c55cfe4892e581806e10b38dfe8083551bd03` | `0xcaf0aa76…` (slot0) |
| StakeManager `0x5e3E…D908` | 1 | `0x3ad88467e40399dc6ae10427f8b0842348d9076c` | `0xcaf0aa76…` |
| ChildChainManager `0xA6FA…C0aa` | 137 | `0xa40fc0782bee28dd2cf8cb4ac2ecdb05c537f1b5` | `0x3a635c48836e7c0b9aeb378640b0bfd516985cf5` |
| USDC.e `0x2791…4174` | 137 | `0xdd9185db084f5c4fff3b4f70e7ba62123b812226` | (matic owner slot) |

**Upgrade-watch topics:** `ProxyUpdated(address indexed previousImplementation, address indexed newImplementation)` = `0xd32d24edea94f55e932d9a008afc425a8561462d1b1f57bc6e508e9a6b9509e1` (matic-proxy); `OwnerUpdate(address,address)` = `0x343765429aea5a34b3ff6a3785a98a5abb2597aca87bfbb58632c173d585373a`. **Always read the live impl slot — never hard-code an impl.**

---

## 8. Detection invariants & gotchas

1. **The bridge is Ethereum (1) ⇄ Polygon PoS (137) only.** Every bridge address returns `0x` on Base/BNB/Avalanche/Arbitrum/Optimism. Don't index those chains for this protocol.
2. **No EIP-1967.** Reading the standard impl slot returns `0x0`; you must use the `matic.network.proxy.implementation` slot (`0xbaab7dbf…`) for PoS-portal contracts, or slot-0/slot-1 for the Plasma proxies. (§7).
3. **The checkpoint event has SIX fields.** Live `NewHeaderBlock` topic0 is `0xba5de06d…` (`address,uint256,uint256,uint256,uint256,bytes32`), **not** the 5-field `0xf146921b…` in older ABIs. Scan `0xba5de06d…` or you'll see zero checkpoints.
4. **`StateSynced` is the universal deposit signal.** Every L1→137 deposit (PoS-portal *and* fx-portal) emits exactly one `StateSynced` on StateSender `0x28e4…bFbE` (topic0 `0x103fed9d…`). The `contractAddress` field tells you whether it routed to ChildChainManager or an FxChild.
5. **Deposits and mints are in different blocks on different chains.** `LockedERC20` (L1) and the `Transfer(0x0→user)` mint (137) are ~22 min apart — never expect them atomically. Correlate by the synced `stateId`/payload, not by tx hash.
6. **Child mint/burn has no dedicated event.** UChildERC20 deposit/withdraw show up only as ERC-20 `Transfer` to/from `0x0`. There is no `Deposit`/`Withdraw` event on the standard child token.
7. **`depositReceiver` ≠ `msg.sender`.** In `LockedERC20`, the indexed `depositor` is the L1 caller but `depositReceiver` is the 137 recipient — attribute the bridged balance to `depositReceiver`. Likewise the `exit()` caller may be a relayer, not the asset owner.
8. **Two parallel deposit paths on L1.** The same MATIC/ERC-20 can move via the **PoS portal** (`depositFor` → `LockedERC20`) *or* the legacy **Plasma DepositManager** (`depositERC20ForUser` → `NewDepositBlock`). Watch both if you need complete L1 deposit coverage.
9. **MintableERC20Predicate vs ERC20Predicate are opposite custody directions.** Plain ERC20Predicate locks an L1-origin asset; MintableERC20Predicate *mints* an L1 token only when a Polygon-native asset is withdrawn to L1. They have distinct topics (`LockedERC20` vs `LockedMintableERC20`) — don't conflate.
10. **`exit()` is permissionless and proof-driven.** Anyone can submit the proof; `processedExits(exitHash)` is the replay guard. A withdrawal that never gets `exit()`-ed leaves the 137-side burn with no matching L1 `Exited*`.
11. **The RootChain proxy is the live checkpoint contract** (`currentHeaderBlock()` = 1042910000 on 2026-06-09; live counter) — checkpoints gate withdrawals. A stalled `NewHeaderBlock` cadence is a liveness/security signal.
12. **`StateReceiver` (`0x…001001`) and MATIC (`0x…1010`) are genesis system predeploys** on 137, not normal deployments — they have no L1 counterpart and no constructor history.
13. **The matic-proxy owner `0xcaf0aa76…` (L1) is a governance contract**, not an EOA. Watch `ProxyUpdated`/`OwnerUpdate`/`RoleGranted` from it for upgrade and admin-change events on any bridge proxy.
14. **Polygon zkEVM bridge is a different protocol.** If you see `PolygonZkEVMBridge`/`BridgeEvent` (chainId 1101), that is *not* this bridge — different contracts, different chain, different event set.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- RootChainManager
TOPIC_TOKEN_MAPPED            = '\x9e651a8866fbea043e911d816ec254b0e3c992c06fff32d605e72362d6023bd9'
TOPIC_PREDICATE_REGISTERED    = '\x8643692ae1c12ec91fa18e50b82ed93fa314f580999a236824db6de9ae0d839b'
-- Predicates (L1 deposit/withdraw)
TOPIC_LOCKED_ERC20            = '\x9b217a401a5ddf7c4d474074aff9958a18d48690d77cc2151c4706aa7348b401'
TOPIC_EXITED_ERC20            = '\xbb61bd1b26b3684c7c028ff1a8f6dabcac2fac8ac57b66fa6b1efb6edeab03c4'
TOPIC_LOCKED_ETHER           = '\x3e799b2d61372379e767ef8f04d65089179b7a6f63f9be3065806456c7309f1b'
TOPIC_EXITED_ETHER           = '\x0fc0eed41f72d3da77d0f53b9594fc7073acd15ee9d7c536819a70a67c57ef3c'
TOPIC_LOCKED_MINTABLE_ERC20  = '\x31472eae9e158460fea5622d1fcb0c5bdc65b6ffb51827f7bc9ef5788410c34c'
TOPIC_EXITED_MINTABLE_ERC20  = '\x42315cb7471194a6f162099cd1052b95b750612a46472e887f7784b95aa2c4c3'
TOPIC_LOCKED_ERC721          = '\x8357472e13612a8c3d6f3e9d71fbba8a78ab77dbdcc7fcf3b7b645585f0bbbfc'
TOPIC_LOCKED_ERC721_BATCH    = '\x5345c2beb0e49c805f42bb70c4ec5c3c3d9680ce45b8f4529c028d5f3e0f7a0d'
TOPIC_EXITED_ERC721          = '\xe9ae525a9512e4ebce82a4301c43bc0915b47778d50e13d49319952b6881f7a9'
TOPIC_LOCKED_BATCH_ERC1155   = '\x5a921678b5779e4471b77219741a417a6ad6ec5d89fa5c8ce8cd7bd2d9f34186'
TOPIC_LOCKED_SINGLE_ERC1155  = '\x99648b7247cedda2aa663d8f7d69eceb7b682f0646d0efb5983510f18d0dfdce'
TOPIC_EXITED_SINGLE_ERC1155  = '\x0dfcc6a24983c122af4c33249bc348ddd51b32984b1dbf715b7f5de2bbe5f4d1'
TOPIC_EXITED_BATCH_ERC1155   = '\x869b80aaea02f34f7fb379faec6f4b1ae676cad20fe5603715fdaac6f135f596'
-- FX portal / state sync
TOPIC_STATE_SYNCED           = '\x103fed9db65eac19c4d870f49ab7520fe03b99f1838e5996caf47e9e43308392'
TOPIC_NEW_FX_MESSAGE         = '\xf091cd9cbbaff01426d8183042dff452ef18e6690f19816d5dd114e00761e0e8'
TOPIC_FX_WITHDRAW_ERC20      = '\x1a77c658a097b28097b54b8acb928a569a3830a6cbed2de1f60001c0757eb0d6'
TOPIC_FX_DEPOSIT_ERC20       = '\x8a58355ceb4626422a66b0f36743672dde8507c6be664f0e5b9de8350a132159'
-- Plasma + checkpoint
TOPIC_NEW_HEADER_BLOCK       = '\xba5de06d22af2685c6c7765f60067f7d2b08c2d29f53cdf14d67f6d1c9bfb527'
TOPIC_RESET_HEADER_BLOCK     = '\xca1d8316287f938830e225956a7bb10fd5a1a1506dd2eb3a476751a488117205'
TOPIC_NEW_DEPOSIT_BLOCK      = '\x1dadc8d0683c6f9824e885935c1bec6f76816730dcec148dda8cf25a7b9f797b'
-- Child token & AccessControl
TOPIC_TRANSFER               = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_ROLE_GRANTED           = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED           = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
-- Proxy upgrade watch
TOPIC_PROXY_UPDATED          = '\xd32d24edea94f55e932d9a008afc425a8561462d1b1f57bc6e508e9a6b9509e1'
TOPIC_OWNER_UPDATE           = '\x343765429aea5a34b3ff6a3785a98a5abb2597aca87bfbb58632c173d585373a'

-- ===== Selectors =====
-- RootChainManager
SEL_DEPOSIT_ETHER_FOR        = '\x4faa8a26'
SEL_DEPOSIT_FOR              = '\xe3dec8fb'
SEL_EXIT                     = '\x3805550f'
SEL_MAP_TOKEN                = '\x9173b139'
SEL_REMAP_TOKEN              = '\xd233a3c7'
SEL_REGISTER_PREDICATE       = '\x0c598220'
SEL_ROOT_TO_CHILD_TOKEN      = '\xea60c7c4'
SEL_CHILD_TO_ROOT_TOKEN      = '\x6e86b770'
SEL_PROCESSED_EXITS          = '\x607f2d42'
-- Predicates
SEL_LOCK_TOKENS              = '\xe375b64e'
SEL_EXIT_TOKENS              = '\x8274664f'
-- ChildChainManager / child token
SEL_ON_STATE_RECEIVE         = '\x26c53bea'
SEL_CHILD_DEPOSIT            = '\xcf2c52cb'
SEL_CHILD_WITHDRAW           = '\x2e1a7d4d'
-- FX portal
SEL_SEND_MESSAGE_TO_CHILD    = '\xb4720477'
SEL_SYNC_STATE               = '\x16f19831'
-- Plasma + checkpoint
SEL_SUBMIT_CHECKPOINT        = '\x4e43e495'
SEL_SUBMIT_HEADER_BLOCK      = '\x6a791f11'
SEL_CURRENT_HEADER_BLOCK     = '\xec7e4855'
SEL_DEPOSIT_ERC20_FOR_USER   = '\x8b9e4f93'
SEL_DEPOSIT_ETHER            = '\x98ea5fca'
-- Proxy admin
SEL_UPDATE_IMPLEMENTATION    = '\x025b22bc'
SEL_IMPLEMENTATION           = '\x5c60da1b'

-- ===== Proxy slots =====
MATIC_IMPL_SLOT              = '\xbaab7dbf64751104133af04abc7d9979f0fda3b059a322a8333f533d3f32bf7f'
MATIC_OWNER_SLOT             = '\x44f6e2e8884cba1236b7f22f351fa5d88b17292b7e0225ca47e5ecdf6055cdd6'
-- (Plasma proxies: impl = storage slot 1, owner = storage slot 0)

-- ===== Ethereum L1 (chain ID 1) =====
ETH_ROOT_CHAIN_MANAGER       = '\xa0c68c638235ee32657e8f720a23cec1bfc77c77'
ETH_ROOT_CHAIN_MANAGER_IMPL  = '\xf0235dca8fb0d3999685724dcbb9dd00c5d62dfa'
ETH_ERC20_PREDICATE          = '\x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf'
ETH_ETHER_PREDICATE          = '\x8484ef722627bf18ca5ae6bcf031c23e6e922b30'
ETH_MINTABLE_ERC20_PREDICATE = '\x9923263fa127b3d1484cfd649df8f1831c2a74e4'
ETH_ERC721_PREDICATE         = '\xe6f45376f64e1f568bd1404c155e5ffd2f80f7ad'
ETH_ERC1155_PREDICATE        = '\x0b9020d4e32990d67559b1317c7bf0c15d6eb88f'
ETH_MINTABLE_ERC721_PRED     = '\x932532aa4c0174b8453839a6e44ee09cc615f2b7'
ETH_MINTABLE_ERC1155_PRED    = '\x2d641867411650cd05db93b59964536b1ed5b1b7'
ETH_FX_ROOT                  = '\xfe5e5d361b2ad62c541bab87c45a0b9b018389a2'
ETH_STATE_SENDER             = '\x28e4f3a7f651294b9564800b2d01f35189a5bfbe'
ETH_PLASMA_DEPOSIT_MANAGER   = '\x401f6c983ea34274ec46f84d70b31c151321188b'
ETH_ROOT_CHAIN_CHECKPOINT    = '\x86e4dc95c7fbdbf52e33d563bbdb00823894c287'
ETH_STAKE_MANAGER            = '\x5e3ef299fddf15eaa0432e6e66473ace8c13d908'
ETH_REGISTRY                 = '\x33a02e6cc863d393d6bf231b697b82f6e499ca71'
ETH_PROXY_OWNER_GOV          = '\xcaf0aa768a3ae1297df20072419db8bb8b5c8cef'

-- ===== Polygon PoS (chain ID 137) =====
POLYGON_CHILD_CHAIN_MANAGER  = '\xa6fa4fb5f76172d178d61b04b0ecd319c5d1c0aa'
POLYGON_FX_CHILD             = '\x8397259c983751daf40400790063935a11afa28a'
POLYGON_STATE_RECEIVER       = '\x0000000000000000000000000000000000001001'
POLYGON_MATIC_NATIVE         = '\x0000000000000000000000000000000000001010'
POLYGON_WMATIC               = '\x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270'
POLYGON_USDC_E               = '\x2791bca1f2de4661ed88a30c99a7a9449aa84174'
POLYGON_WETH                 = '\x7ceb23fd6bc0add59e62ac25578270cff1b9f619'
```

---

## 10. Verification & sources

How constants were verified (2026-06-09):

- **Topic0 + selectors:** computed locally as `keccak256(canonical signature)` / `[0:4]` (keccak-256, no param names). `LockedERC20`/`ExitedERC20`/`StateSynced`/`NewHeaderBlock` topic0s were cross-checked against live `eth_getLogs`: `LockedERC20` 65 logs and `ExitedERC20` 1,359 logs on ERC20Predicate `0x40ec…`; `StateSynced` 117 logs on StateSender `0x28e4…`; `NewHeaderBlock` 58 logs on RootChain `0x86E4…` (topic0 `0xba5de06d…`, the live 6-field form — the 5-field `0xf146921b…` produced **zero** matches and is recorded as the stale/incorrect signature). RootChainManager/predicate/RootChain/DepositManager/ChildChainManager/UChildERC20 selectors were confirmed **present** in the live implementation bytecode via a PUSH4 (`63<selector>`) scan.
- **Addresses:** parsed from the `0xPolygon/pos-portal`, `0xPolygon/fx-portal`, and Polygon official docs / contract-address registry, then existence-checked via `eth_getCode` on each chain's publicnode RPC. All L1 PoS-portal + FX-portal + Plasma addresses returned non-empty bytecode on Ethereum; ChildChainManager/FxChild/child tokens on Polygon 137. **All bridge addresses returned `0x` on Base, BNB, Avalanche, Arbitrum, and Optimism** (verified one-by-one).
- **Proxies:** impls read live from the `matic.network.proxy.implementation` slot (`0xbaab7dbf…`, derived locally as `keccak256("matic.network.proxy.implementation")`) for PoS-portal contracts, and from storage slots 0 (owner) / 1 (implementation) for the Plasma DepositManager/RootChain proxies. The standard EIP-1967 impl slot returned `0x0` on every contract (confirming Polygon's non-EIP-1967 convention). FxRoot/FxChild/StateSender returned `0x0` on *both* the EIP-1967 and matic slots and carry full runtime bytecode ⇒ immutable.
- **Live state (`eth_call`):** RootChain `currentHeaderBlock()` = 1042910000 on 2026-06-09 (confirms it is the active checkpoint contract; this is a live counter that advances by 10000 per checkpoint); proxy impl/owner pointers read via `eth_getStorageAt`.
- **Chain coverage method:** `eth_getCode` for each canonical address against all seven target RPCs; absence (`0x`) recorded explicitly.

**Authoritative sources:**
- Canonical repos: [`0xPolygon/pos-portal`](https://github.com/0xPolygon/pos-portal) (RootChainManager, predicates, ChildChainManager, child tokens), [`0xPolygon/fx-portal`](https://github.com/0xPolygon/fx-portal) (FxRoot/FxChild/State tunnel), [`maticnetwork/contracts`](https://github.com/maticnetwork/contracts) (Plasma DepositManager/WithdrawManager, RootChain checkpoint, StakeManager).
- Official docs: [Polygon PoS Bridge docs](https://docs.polygon.technology/pos/) · [Contract addresses (static deployment registry)](https://static.matic.network/network/mainnet/v1/index.json).
- Explorers: [Etherscan RootChainManager](https://etherscan.io/address/0xA0c68C638235ee32657e8f720a23ceC1bFc77C77) · [Etherscan StateSender](https://etherscan.io/address/0x28e4F3a7f651294B9564800b2D01f35189A5bFbE) · [Etherscan RootChain checkpoint](https://etherscan.io/address/0x86E4Dc95c7FBdBf52e33D563BbDB00823894C287) · [Polygonscan ChildChainManager](https://polygonscan.com/address/0xA6FA4fB5f76172d178d61B04b0ecd319C5d1C0aa) · [Polygonscan FxChild](https://polygonscan.com/address/0x8397259c983751DAf40400790063935a11afa28a).

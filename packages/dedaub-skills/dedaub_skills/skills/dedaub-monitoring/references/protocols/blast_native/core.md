# Blast Native Bridge (OP-Stack + YieldManager) — Topics, Selectors, Addresses (Ethereum L1 ↔ Blast L2)

**Status:** verified against live RPC on Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum One (42161), Optimism (10) and Polygon PoS (137), and against the canonical `blast-io/blast` repo (`blast-optimism/packages/contracts-bedrock/deployments/blast-mainnet`) on 2026-06-09.
**Scope:** the canonical (native) Blast L2 bridge — an Optimism Bedrock fork (OptimismPortal / L1CrossDomainMessenger / L1StandardBridge / L2OutputOracle) **plus Blast-specific contracts**: a second token bridge `L1BlastBridge` for the rebasing assets (USDB, WETHRebasing) and the `ETHYieldManager` / `USDYieldManager` insurance-backed staking layer that invests L1-held bridge funds (Lido stETH, MakerDAO DSR) and reports yield back to L2. Event topics and function selectors are **chain-agnostic**; addresses are **network-specific**. The user requested presence on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon. **All canonical bridge contracts are anchored on Ethereum L1 (chain 1) — and on NONE of the other six requested chains** (`eth_getCode` = `0x` everywhere else — §6). **The L2 counterparty is Blast (chain 81457), which is OUTSIDE the seven requested chains** — its predeploys are recorded in §5 as a finding, not indexed here.

Blast is an OP-Stack optimistic rollup whose differentiator is **native yield**: ETH and stablecoins deposited into the L1 bridge are *not* left idle — the `OptimismPortal`/`L1StandardBridge`/`L1BlastBridge` route principal into a `YieldManager`, which `stake`s it into yield providers (`ETHYieldProvider` → Lido stETH; `USDYieldProvider` → MakerDAO DSR on DAI) and periodically emits a `YieldReport`. That yield is credited to L2 holders of the rebasing tokens (USDB, WETHRebasing). Withdrawals therefore go through an **insurance + unstaking queue** (`requestWithdrawal` → `WithdrawalsFinalized` → `claimWithdrawal`) on top of the normal OP 7-day challenge window, so a Blast L2→L1 withdrawal touches *two* queues, not one.

The L1 contracts are a fixed set of **proxies** — EIP-1967 transparent proxies under a single `ProxyAdmin` (`0x3642…E883`) for everything *except* the `L1CrossDomainMessenger`, which is the legacy OP `ResolvedDelegateProxy` (resolves its implementation through the `AddressManager`, **not** an EIP-1967 slot — §8). One singleton per role; no CREATE2 vanity, no per-token instances. Governance/upgrade authority for both the `ProxyAdmin` and the `SystemConfig` is a **Gnosis Safe `SystemOwnerSafe` `0x4f72…8B05`** (verified `ProxyAdmin.owner()` and `SystemConfig.owner()` both return it).

> **Two non-obvious facts to internalize before indexing.** (1) **There are TWO L1 token bridges.** The OP-standard `L1StandardBridge` (`0x6974…c524`) handles ETH and arbitrary ERC-20s; the Blast-only `L1BlastBridge` (`0x3a05…9115`) handles the **yield assets** — its `otherBridge()` = the L2 `0x4300…0005`, and its L1 backing for USDB is **DAI `0x6B17…1d0F`** (the repo's `USDBRemoteToken`). They share the same `ERC20BridgeInitiated`/`ERC20BridgeFinalized` topic0s, so disambiguate by emitter. (2) **Only `finalizeWithdrawalTransaction` has a Blast-modified signature** — it carries an **extra leading `uint256 hintId` (the YieldManager unstake hint)**, giving the Blast-unique selector `0x3dca9c41` (stock OP `finalizeWithdrawalTransaction(tuple)` = `0x8c3152e9`). `proveWithdrawalTransaction`'s selector `0x4870496f` is **identical to stock OP** — its Blast modification is on the EVENT (`WithdrawalProven` has a non-standard 4th arg `requestId`, §1.2), not the function args. So: prove selector = shared with OP, finalize selector = Blast-unique, both prove/finalize EVENTS = Blast-modified.

---

## 0. Contract families & versions

| Family | Contracts (L1) | Role | Proxy? |
|--------|----------------|------|--------|
| **OP core / messaging** | OptimismPortal, L1CrossDomainMessenger, L2OutputOracle, SystemConfig | L1 deposit entry / message ledger / L2 state commitment / chain config | EIP-1967 (XDM = ResolvedDelegateProxy) |
| **Token bridges** | L1StandardBridge (ETH + generic ERC-20), L1BlastBridge (USDB/WETHRebasing yield assets), L1ERC721Bridge, OptimismMintableERC20Factory | Canonical bridging | EIP-1967 |
| **Yield layer (Blast-specific)** | ETHYieldManager, USDYieldManager, ETHYieldProvider (=LidoYieldProvider), USDYieldProvider (=DSRYieldProvider), ETHInsurance, USDInsurance | Stake bridge funds into Lido/DSR, report yield, run the withdrawal/insurance queue | EIP-1967 (managers + insurance); providers non-proxy |
| **Admin / registry** | ProxyAdmin, AddressManager, SystemOwnerSafe (Gnosis Safe) | Upgrade auth + legacy name registry + owner multisig | — |

There is **one** continuously-upgraded generation (Blast mainnet launched Feb 2024, Bedrock-era OP fork). No "v1/v2" redeploys — hence a single `core.md`. Live implementations have drifted from the repo snapshot for three proxies (Portal, USDYieldManager, L2OutputOracle — §8.1); always read the live EIP-1967 slot.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09; each marked *(live)* was additionally confirmed against real `eth_getLogs` on the cited L1 emitter in a 49 000-block window ending block 25 279 371.

### 1.1 L1StandardBridge & L1BlastBridge (shared topic0s — disambiguate by emitter)

Emitter (StandardBridge) `0x6974…c524`; (BlastBridge) `0x3a05…9115`.

| topic0 | Event |
|--------|-------|
| `0x2849b43074093a05396b6f2a937dee8565b15a48a7b3d4bffb732a5017380af5` | `ETHBridgeInitiated(address indexed from, address indexed to, uint256 amount, bytes extraData)` *(live, StandardBridge: 4 logs)* |
| `0x31b2166ff604fc5672ea5df08a78081d2bc6d746cadce880747f3643d819e83d` | `ETHBridgeFinalized(address indexed from, address indexed to, uint256 amount, bytes extraData)` |
| `0x7ff126db8024424bbfd9826e8ab82ff59136289ea440b04b39a0df1b03b9cabf` | `ERC20BridgeInitiated(address indexed localToken, address indexed remoteToken, address indexed from, address to, uint256 amount, bytes extraData)` *(live, BlastBridge: 1 log)* |
| `0xd59c65b35445225835c83f50b6ede06a7be047d22e357073e250d9af537518cd` | `ERC20BridgeFinalized(address indexed localToken, address indexed remoteToken, address indexed from, address to, uint256 amount, bytes extraData)` |
| `0x35d79ab81f2b2017e19afb5c5571778877782d7a8786f5907f93b0f4702f4f23` | `ETHDepositInitiated(address indexed from, address indexed to, uint256 amount, bytes extraData)` (legacy alias; StandardBridge only) |
| `0x2ac69ee804d9a7a0984249f508dfab7cb2534b465b6ce1580f99a38ba9c5e631` | `ETHWithdrawalFinalized(address indexed from, address indexed to, uint256 amount, bytes extraData)` (legacy alias) |
| `0x718594027abd4eaed59f95162563e0cc6d0e8d5b86b1c7be8b1b0ac3343d0396` | `ERC20DepositInitiated(address indexed l1Token, address indexed l2Token, address indexed from, address to, uint256 amount, bytes extraData)` (legacy alias) |
| `0x3ceee06c1e37648fcbb6ed52e17b3e1f275a1f8c7b22a84b2b84732431e046b3` | `ERC20WithdrawalFinalized(address indexed l1Token, address indexed l2Token, address indexed from, address to, uint256 amount, bytes extraData)` (legacy alias) |

`...Initiated`/`...DepositInitiated` are the **new vs legacy** event pair fired in the *same tx* (StandardBridge emits both for backward compat); index `ETHBridgeInitiated`/`ERC20BridgeInitiated` and treat the legacy ones as duplicates. `L1BlastBridge` emits **only** the `*BridgeInitiated`/`*BridgeFinalized` forms (no legacy aliases).

### 1.2 OptimismPortal — ETH emitter `0x0Ec6…D6Cb`

| topic0 | Event |
|--------|-------|
| `0xb3813568d9991fc951961fcb4c784893574240a28925604d09fc577c55bb7c32` | `TransactionDeposited(address indexed from, address indexed to, uint256 indexed version, bytes opaqueData)` *(live, 117 logs)* — **the canonical L1→L2 deposit event** (every bridge/messenger deposit ultimately emits this) |
| `0x5d5446905f1f582d57d04ced5b1bed0f1a6847bcee57f7dd9d6f2ec12ab9ec2e` | `WithdrawalProven(bytes32 indexed withdrawalHash, address indexed from, address indexed to, uint256 requestId)` *(live, 60 logs)* — **Blast-modified: extra `requestId`** (links to the YieldManager unstake queue) |
| `0x36d89e6190aa646d1a48286f8ad05e60a144483f42fd7e0ea08baba79343645b` | `WithdrawalFinalized(bytes32 indexed withdrawalHash, uint256 indexed hintId, bool success)` *(live, 60 logs)* — **Blast-modified: 2nd arg `hintId`** (not stock OP's single-indexed `withdrawalHash` + `success`) |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` — guardian halted deposits/withdrawals |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |

`TransactionDeposited.version` (the 3rd indexed `uint256`) is `0` for the current opaqueData encoding. `withdrawalHash` is the cross-chain join key for L2→L1 flows; `WithdrawalProven` then `WithdrawalFinalized` fire in separate txs ≥7 days apart.

### 1.3 L1CrossDomainMessenger — ETH emitter `0x5D44…e9d0`

| topic0 | Event |
|--------|-------|
| `0xcb0f7ffd78f9aee47a248fae8db181db6eee833039123e026dcbff529522e52a` | `SentMessage(address indexed target, address sender, bytes message, uint256 messageNonce, uint256 gasLimit)` *(live, 67 logs)* |
| `0x8ebb2ec2465bdb2a06a66fc37a0963af8a2a6a1479d81d56fdb8cbb98096d546` | `SentMessageExtension1(address indexed sender, uint256 value)` — fires alongside `SentMessage`, carries the ETH `value` |
| `0x4641df4a962071e12719d8c8c8e5ac7fc4d97b927346a3d7a335b1f7517e133c` | `RelayedMessage(bytes32 indexed msgHash)` — inbound L2→L1 message executed |
| `0x99d0e048484baa1b1540b1367cb128acd7ab2946d1ed91ec10e3c85e4bf51b8f` | `FailedRelayedMessage(bytes32 indexed msgHash)` — relay reverted, replayable |

`SentMessage` + `SentMessageExtension1` are emitted as a pair (OP Bedrock split the value off into the extension event). `msgHash` keys the relay lifecycle.

### 1.4 L2OutputOracle — ETH emitter `0x826D…5c76`

| topic0 | Event |
|--------|-------|
| `0xa7aaf2512769da4e444e3de247be2564225c2e7a8f74cfe528e46e17d24868e2` | `OutputProposed(bytes32 indexed outputRoot, uint256 indexed l2OutputIndex, uint256 indexed l2BlockNumber, uint256 l1Timestamp)` *(live, 165 logs)* — proposer commits an L2 state root |
| `0x4ee37ac2c786ec85e87592d3c5c8a1dd66f8496dda3f125d9ea8ca5f657629b6` | `OutputsDeleted(uint256 indexed prevNextOutputIndex, uint256 indexed newNextOutputIndex)` — challenger deleted outputs (fault) |

### 1.5 ETHYieldManager & USDYieldManager (shared topic0s — disambiguate by emitter)

Emitter (ETH) `0x9807…C8FE`; (USD) `0xa230…8438`. **This is the Blast-unique yield/withdrawal layer.**

| topic0 | Event |
|--------|-------|
| `0x00ae2c76ca218353c7995e13a4af773a35837cb6ebb8288092d8190bcd9c8f68` | `WithdrawalRequested(uint256 indexed requestId, address indexed requestor, address indexed recipient, uint256 amount)` *(live ETH: 38, USD: 14)* — enters the unstake queue |
| `0x59382740d48c89a44d8866c8e7071aa24351a82e5f38e4674ab82aa8a18119bc` | `WithdrawalsFinalized(uint256 indexed from, uint256 indexed to, uint256 indexed checkpointId, uint256 amountOfETHLocked, uint256 timestamp, uint256 sharePrice)` *(live ETH: 7)* — batch of requests becomes claimable |
| `0x8adb7a84b2998a8d11cd9284395f95d5a99f160be785ae79998c654979bd3d9a` | `WithdrawalClaimed(uint256 indexed requestId, address indexed recipient, uint256 amountOfETH)` — user/bridge pulls the unstaked funds |
| `0x00de4b58e7863b1e3dce7259a138136239427388d53e4844f369cdee7a81dbf5` | `YieldReport(int256 yield, uint256 insurancePremiumPaid, uint256 insuranceWithdrawn)` *(live ETH: 6)* — **periodic native-yield accounting; `yield` is SIGNED (negative = loss)** |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` (2-step Ownable) |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

### 1.6 Proxy / registry events (all proxies + AddressManager)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch on every EIP-1967 proxy in §3** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` — EIP-1967 admin rotation |
| `0x9416a153a346f93d95f94b064ae3f148b6460473c6e82b3f9fc2521b873fcd6c` | `AddressSet(string indexed name, address newAddress, address oldAddress)` — **AddressManager** repoint (the `L1CrossDomainMessenger` impl resolves here — watch this for XDM upgrades) |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` — proxy init / reinit (fires on upgrades) |

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

All selectors recomputed locally 2026-06-09. Bridge / Portal / YieldManager selectors marked *(impl)* were confirmed **present** in the live implementation bytecode (Portal impl `0xa280…4391`, ETHYieldManager impl `0xf2f6…9525`).

### 2.1 L1StandardBridge (ETH + generic ERC-20)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x09fc8843` | `bridgeETH(uint32 minGasLimit, bytes extraData)` | Deposit ETH to same address on L2 |
| `0xe11013dd` | `bridgeETHTo(address to, uint32 minGasLimit, bytes extraData)` | Deposit ETH to a chosen L2 address |
| `0x87087623` | `bridgeERC20(address localToken, address remoteToken, uint256 amount, uint32 minGasLimit, bytes extraData)` | |
| `0x540abf73` | `bridgeERC20To(address localToken, address remoteToken, address to, uint256 amount, uint32 minGasLimit, bytes extraData)` | |
| `0xb1a1a882` | `depositETH(uint32, bytes)` | Legacy alias of bridgeETH |
| `0x9a2ac6d5` | `depositETHTo(address, uint32, bytes)` | Legacy alias |
| `0x58a997f6` | `depositERC20(address, address, uint256, uint32, bytes)` | Legacy alias |
| `0x838b2520` | `depositERC20To(address, address, address, uint256, uint32, bytes)` | Legacy alias |
| `0x1635f5fd` | `finalizeBridgeETH(address from, address to, uint256 amount, bytes extraData)` | L2→L1 finalize (messenger-gated) |
| `0x0166a07a` | `finalizeBridgeERC20(address localToken, address remoteToken, address from, address to, uint256 amount, bytes extraData)` | |
| `0x1532ec34` | `finalizeETHWithdrawal(address, address, uint256, bytes)` | Legacy alias |
| `0xa9f9e675` | `finalizeERC20Withdrawal(address, address, address, address, uint256, bytes)` | Legacy alias |

### 2.2 L1BlastBridge (yield assets — USDB/WETHRebasing) — Blast-specific

Shares the `bridgeERC20*`/`bridgeETH*`/`finalizeBridge*` selectors above (same OP `StandardBridge` base) **plus** two Blast-only config setters:

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc8fb1533` | `setETHYieldToken(address localToken, bool enabled, uint8 decimals, address remoteToken, bool isStandard)` | Register/disable a rebasing ETH yield token route (governance) |
| `0xd9ffb9d6` | `setUSDYieldToken(address localToken, bool enabled, uint8 decimals, address remoteToken, bool isStandard)` | Register/disable a USD yield token route (USDB↔DAI) |

### 2.3 OptimismPortal (Blast-modified withdrawal proofs)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe9e05c42` | `depositTransaction(address to, uint256 value, uint64 gasLimit, bool isCreation, bytes data)` *(impl)* | Low-level L1→L2 deposit; emits `TransactionDeposited` |
| `0x4870496f` | `proveWithdrawalTransaction((uint256,address,address,uint256,uint256,bytes) tx, uint256 l2OutputIndex, (bytes32,bytes32,bytes32,bytes32) outputRootProof, bytes[] withdrawalProof)` *(impl)* | Withdrawal proof — the leading tuple is the WithdrawalTransaction `{nonce,sender,target,value,gasLimit,data}`. **Selector `0x4870496f` is IDENTICAL to stock OP** (Blast did not change this signature; the prove modification is the `requestId` on the `WithdrawalProven` EVENT, §1.2) |
| `0x3dca9c41` | `finalizeWithdrawalTransaction(uint256 hintId, (uint256,address,address,uint256,uint256,bytes) tx)` *(impl)* | **Blast-modified: extra leading `uint256 hintId`** (YieldManager request hint) — stock OP has no such arg |
| `0x8456cb59` | `pause()` *(impl)* | Guardian emergency halt → `Paused` |
| `0x3f4ba83a` | `unpause()` *(impl)* | |

### 2.4 L1CrossDomainMessenger / L2OutputOracle

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x3dbb202b` | `sendMessage(address target, bytes message, uint32 minGasLimit)` | L1XDM — emits `SentMessage`(+ext1) |
| `0xd764ad0b` | `relayMessage(uint256 nonce, address sender, address target, uint256 value, uint256 minGasLimit, bytes message)` | L1XDM — inbound L2→L1 → `RelayedMessage` |
| `0x9aaab648` | `proposeL2Output(bytes32 outputRoot, uint256 l2BlockNumber, bytes32 l1BlockHash, uint256 l1BlockNumber)` | L2OutputOracle — proposer only → `OutputProposed` |
| `0x89c44cbb` | `deleteL2Outputs(uint256 l2OutputIndex)` | L2OutputOracle — challenger only → `OutputsDeleted` |

### 2.5 ETHYieldManager / USDYieldManager (Blast-specific)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9ee679e8` | `requestWithdrawal(uint256 amount)` *(impl)* | Enqueue an unstake → `WithdrawalRequested` |
| `0xf21340e4` | `claimWithdrawal(uint256 requestId, uint256 hint)` *(impl)* | Claim a finalized request → `WithdrawalClaimed` |
| `0x05261aea` | `finalize(uint256 requestsToFinalize)` | Batch-finalize the queue → `WithdrawalsFinalized` |
| `0x6e9c931c` | `stake(uint256 providerIndex, address provider, uint256 amount)` *(impl)* | Push principal into a yield provider (Lido/DSR) |
| `0x51a7c716` | `unstake(uint256 providerIndex, address provider, uint256 amount)` | Pull principal back from a provider |
| `0xe7518fb6` | `commitYieldReport(bool)` *(impl)* | Account yield/loss → `YieldReport` |
| `0xd6ce7910` | `recordNegativeYield(uint256 amount)` | Record a provider loss (insurance draw) |
| `0x959598c4` | `recordStakedDeposit(address provider, uint256 amount)` | Bridge → manager principal accounting |
| `0x46e2577a` | `addProvider(address)` | Add a yield provider (owner) |
| `0x8a355a57` | `removeProvider(address)` | Remove a yield provider (owner) |
| `0x6f3ed5e3` | `setInsurance(address insurance, uint256 premiumBps, uint256 cap)` | Configure the insurance contract |
| `0xf0c8c0dd` | `setBlastBridge(address)` | Wire the manager to its bridge |
| `0x704b6c02` | `setAdmin(address)` | Set the operational admin |

### 2.6 Proxy upgrade selectors (watch on ProxyAdmin / proxies)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3659cfe6` | `upgradeTo(address)` | EIP-1967 impl swap → `Upgraded` |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | Impl swap + init → `Upgraded` + `Initialized` |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All proxies and implementations below verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Source: `blast-io/blast` repo `deployments/blast-mainnet` (`.chainId` = 1). Wiring confirmed: `L1BlastBridge.otherBridge()` = `0x4300…0005`, `ProxyAdmin.owner()` = `SystemConfig.owner()` = `SystemOwnerSafe`.

### 3.1 OP core / messaging (proxies)

| Role | Address (proxy) | One-liner |
|------|-----------------|-----------|
| **OptimismPortal** | `0x0Ec68c5B10F21EFFb74f2A5C61DFe6b08C0Db6Cb` | L1→L2 deposit entry + L2→L1 withdrawal prove/finalize; emits §1.2. Blast-modified withdrawal args. |
| **L1CrossDomainMessenger** | `0x5D4472f31Bd9385709ec61305AFc749F0fA8e9d0` | Generic cross-domain message ledger; emits §1.3. **ResolvedDelegateProxy** (not EIP-1967 — §8). |
| **L2OutputOracle** | `0x826D1B0D4111Ad9146Eb8941D7Ca2B6a44215c76` | Proposer commits L2 state roots; emits §1.4. |
| **SystemConfig** | `0x5531DcfF39EC1ec727C4c5D2fc49835368F805a9` | Chain config (batcher, gas limit, fees); owner = SystemOwnerSafe. |
| ProtocolVersions | `0x2241b38558957060c0FE9760794F1B49C535e5f7` | OP protocol-version signal. |

### 3.2 Token bridges (proxies)

| Role | Address (proxy) | One-liner |
|------|-----------------|-----------|
| **L1StandardBridge** | `0x697402166Fbf2F22E970df8a6486Ef171dbfc524` | ETH + generic ERC-20 bridge; emits §1.1. |
| **L1BlastBridge** | `0x3a05E5d33d7Ab3864D53aaEc93c8301C1Fa49115` | **Blast-only** rebasing-asset bridge (USDB↔DAI, WETHRebasing); `otherBridge()`=`0x4300…0005`. **This is the address Blast's docs tell users to send ETH to.** |
| **L1ERC721Bridge** | `0xa45A0c7C47DB8C6e99b2d7C4939F7f7Cf69C8975` | NFT bridge. |
| **OptimismMintableERC20Factory** | `0x6B916DcCa661d23794e78509723A6f4348564847` | Mints L1 representations of L2-native tokens. |

### 3.3 Yield layer (Blast-specific)

| Role | Address | One-liner |
|------|---------|-----------|
| **ETHYieldManager** (proxy) | `0x98078db053902644191f93988341E31289E1C8FE` | Stakes bridged ETH into Lido; runs unstake/insurance queue; emits §1.5. |
| **USDYieldManager** (proxy) | `0xa230285d5683C74935aD14c446e137c8c8828438` | Stakes bridged DAI into Maker DSR; emits §1.5. |
| **ETHYieldProvider** (= LidoYieldProvider) | `0x4316A00D31da1313617DbB04fD92F9fF8D1aF7Db` | Lido stETH adapter (non-proxy, 9 616 B). |
| **USDYieldProvider** (= DSRYieldProvider) | `0x0733F618118bF420b6b604c969498ecf143681a8` | MakerDAO DSR adapter (non-proxy, 6 885 B). |
| **ETHInsurance** (proxy) | `0xcFF70D7F37b1EBeE89c08E485f08ACAB5f6ff873` | Backstops ETH negative-yield events. |
| **USDInsurance** (proxy) | `0xBbE2cd60BD30Ef2aaceFD74C3199282ee35fBBa6` | Backstops USD negative-yield events. |
| USDB L1 backing token (`USDBRemoteToken`) | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | **= DAI** — the L1 asset L1BlastBridge holds against L2 USDB. Not a Blast contract. |

### 3.4 Admin / registry

| Role | Address | One-liner |
|------|---------|-----------|
| **ProxyAdmin** | `0x364289230b8cc7d9120eF962AF37ebCFe23cE883` | EIP-1967 admin of all §3.1–§3.3 proxies; `owner()` = SystemOwnerSafe. |
| **AddressManager** | `0xE064B565Cf2A312a3e66Fe4118890583727380C0` | Legacy OP name registry; resolves the L1CrossDomainMessenger impl. |
| **SystemOwnerSafe** | `0x4f72ee94B8ba3Be7F886565d3583A7F636c58B05` | Gnosis Safe — upgrade/governance owner (171 B Safe proxy). |

### 3.5 Implementations (Ethereum) — live EIP-1967 reads (2026-06-09)

| Contract | Live impl (slot read) | Repo `*` impl | Drift? |
|----------|-----------------------|---------------|--------|
| OptimismPortal | `0xa280aebf81c917dbd2aa1b39f979dfecec9e4391` | `0xd7bfDa9B3b014b16bada89F206607a8Ac7c6FB32` | **YES — upgraded** |
| L1StandardBridge | `0xd2c23a5a280aff9182b953579f62edddf1c7ff22` | `0xD2C23A5A280AFF9182b953579f62EDdDF1c7ff22` | — (matches) |
| L1BlastBridge | `0x7a2075519dd9598b62075fd397af0dd34b14619a` | `0x7A2075519Dd9598b62075FD397aF0Dd34b14619a` | — (matches) |
| L1ERC721Bridge | `0x3b01adf2f199144233a536b08244d63e5eb691b8` | `0x3B01aDF2f199144233A536b08244d63e5eb691B8` | — (matches) |
| L2OutputOracle | `0x1c90963d451316e3dbfdd5a30354ee56c29016eb` | `0x1c952514f0353d84d9ad35BcfB8E9Ea979289031` | **YES — upgraded** |
| L1CrossDomainMessenger | `0x84efcfce2dee08072d5d57bf232d379b6e92a836` (via AddressManager `OVM_L1CrossDomainMessenger`) | `0xe7406f6d89a14aC3Fc28530479327948ea500659` | **YES — drift** |
| SystemConfig | `0xa150f19b681a06e1a0b7e03934299a9bf9238cb7` | `0xA150f19B681a06E1a0B7E03934299a9bf9238cb7` | — (matches) |
| ETHYieldManager | `0xf2f6148327b3020610fca26e094d9a5cc4689525` | `0xf2F6148327B3020610FCa26E094D9A5cc4689525` | — (matches) |
| USDYieldManager | `0xecddf748a60e23609c07af6ca3856744b139b911` | `0xE1cB7358311eCc408e1EFC47ceDc6740A8F68013` | **YES — upgraded** |
| ETHInsurance | `0x787bc7274ba165d1dd3d89c1a9159cff5f92b327` | `0x787BC7274Ba165d1dd3D89c1a9159cFf5f92B327` | — (matches) |
| USDInsurance | `0xedefe92e0cef091149e1749dd12d8f44dd94dbb3` | `0xEDeFE92e0CEF091149E1749Dd12d8F44Dd94DBb3` | — (matches) |
| OptimismMintableERC20Factory | `0xbf21bc9afaf817145b3886cadaf0860a2a0d782f` | `0xBF21bc9AFaF817145B3886caDAF0860A2A0D782F` | — (matches) |

**Always read the live EIP-1967 slot — never hard-code an impl.** Three proxies (Portal, L2OutputOracle, USDYieldManager) have already drifted from the repo snapshot.

---

## 4. Addresses — Base / BNB / Avalanche / Arbitrum / Optimism / Polygon — NOT DEPLOYED

The Blast native bridge anchors **exclusively on Ethereum L1 (chain 1)** of the seven requested chains. Every Blast L1 address returns `0x` from `eth_getCode` on all six other target chains (verified 2026-06-09 — see the matrix in §7). **There is no Blast bridge contract on Base, BNB, Avalanche, Arbitrum, Optimism, or Polygon.** This is by design: an OP-Stack canonical bridge is a single L1↔L2 pair; there is no multi-chain spoke deployment.

---

## 5. Addresses — Blast L2 (chain ID 81457) — COUNTERPARTY, OUTSIDE THE SEVEN

**Blast (81457) is the L2 counterparty and is NOT in the seven requested chains** — recorded here as a finding. These OP-stack predeploys sit at fixed addresses; the L1 contracts above are their counterparties. Not on a public-node RPC in this verification set; addresses from Blast docs.

| Role | Address (L2) | Counterpart on L1 |
|------|--------------|-------------------|
| L2StandardBridge | `0x4200000000000000000000000000000000000010` | L1StandardBridge `0x6974…c524` |
| L2BlastBridge | `0x4300000000000000000000000000000000000005` | L1BlastBridge `0x3a05…9115` (`otherBridge()` confirmed) |
| L2CrossDomainMessenger | `0x4200000000000000000000000000000000000007` | L1CrossDomainMessenger `0x5D44…e9d0` |
| L2ToL1MessagePasser | `0x4200000000000000000000000000000000000016` | OptimismPortal `0x0Ec6…D6Cb` |
| L2ERC721Bridge | `0x4200000000000000000000000000000000000014` | L1ERC721Bridge `0xa45A…8975` |
| **BLAST (yield/gas predeploy)** | `0x4300000000000000000000000000000000000002` | the yield mechanism; contracts call it to set YieldMode/GasMode |
| **USDB** (rebasing stable) | `0x4300000000000000000000000000000000000003` | backed by DAI `0x6B17…1d0F` via L1BlastBridge |
| **WETH / WETHRebasing** | `0x4300000000000000000000000000000000000004` | bridged ETH yield asset |

---

## 6. Chain coverage method & absence findings

`eth_getCode` was issued for each of the six L1 anchor contracts (L1StandardBridge, L1BlastBridge, OptimismPortal, L1CrossDomainMessenger, ETHYieldManager, USDYieldManager) against the public RPC of all seven requested chains. **Result: present (non-empty bytecode) on Ethereum only; `0x` on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon.** Absence is a recorded finding, not a gap — an OP-Stack native bridge has no spokes.

---

## 7. Cross-chain summary

| Chain | ID | L1StandardBridge | L1BlastBridge | OptimismPortal | L1XDM | ETHYieldManager | USDYieldManager |
|-------|----|------------------|---------------|----------------|-------|-----------------|-----------------|
| **Ethereum** | 1 | `0x6974…c524` | `0x3a05…9115` | `0x0Ec6…D6Cb` | `0x5D44…e9d0` | `0x9807…C8FE` | `0xa230…8438` |
| Base | 8453 | — | — | — | — | — | — |
| BNB | 56 | — | — | — | — | — | — |
| Avalanche | 43114 | — | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — | — |
| *Blast (L2 counterparty)* | *81457* | *L2: `0x4200…0010`* | *L2: `0x4300…0005`* | *L2: `0x4200…0016` (passer)* | *L2: `0x4200…0007`* | — | — |

No vanity-address tells; addresses are plain CREATE deployments. The L2 side uses the deterministic OP predeploy ranges `0x4200…` (OP-standard) and `0x4300…` (Blast-specific).

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| OptimismPortal, L1StandardBridge, L1BlastBridge, L1ERC721Bridge, L2OutputOracle, SystemConfig, ETHYieldManager, USDYieldManager, ETHInsurance, USDInsurance, OptimismMintableERC20Factory | **EIP-1967 Transparent (`Proxy`)** | Impl slot `0x3608…2bbc` non-zero; admin slot `0xb531…6103` = ProxyAdmin `0x3642…E883` | ProxyAdmin → SystemOwnerSafe |
| **L1CrossDomainMessenger** | **ResolvedDelegateProxy (legacy OP)** | EIP-1967 impl & admin slots **both `0x000…0`**; impl resolved via `AddressManager.getAddress("OVM_L1CrossDomainMessenger")` = `0x84ef…a836` | AddressManager owner (→ SystemOwnerSafe) |
| ETHYieldProvider, USDYieldProvider | **immutable (non-proxy)** | EIP-1967 impl slot `0x000…0`; plain logic contracts (9 616 / 6 885 B) | — (managers add/remove via `addProvider`) |
| SystemOwnerSafe | Gnosis Safe proxy | 171 B Safe singleton delegate | Safe owners/threshold |

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. Read with `eth_getStorageAt(addr, slot)`.

### 8.1 Implementation drift (read live 2026-06-09)

Three proxies have a live impl that differs from the repo deployment artifact — **the contracts were upgraded after the repo snapshot**: OptimismPortal (`0xa280…4391` vs repo `0xd7bf…FB32`), L2OutputOracle (`0x1c90…16eb` vs `0x1c95…9031`), USDYieldManager (`0xecdd…b911` vs `0xE1cB…b013`). Full table in §3.5. **Watch `Upgraded(address)` topic0 `0xbc7c…2d3b` on every proxy** and re-read the slot rather than trusting the repo.

### 8.2 L1CrossDomainMessenger is NOT EIP-1967

Both EIP-1967 slots read `0x000…0` on the L1XDM proxy `0x5D44…e9d0` — it is the OP-legacy `ResolvedDelegateProxy`, which fetches its implementation each call from the `AddressManager`. Detect an XDM upgrade by the `AddressSet` event (topic0 `0x9416…cd6c`) on the AddressManager `0xE064…80C0` for name `OVM_L1CrossDomainMessenger`, **not** by `Upgraded`.

---

## 9. Detection invariants & gotchas

1. **The whole bridge lives on Ethereum L1 only (of the seven).** There are no Blast bridge contracts on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon (§4, §7). The other endpoint is **Blast L2, chain 81457, outside the requested set** (§5).
2. **TWO L1 token bridges share the same event topic0s.** `L1StandardBridge` (`0x6974…c524`, ETH + generic ERC-20) and `L1BlastBridge` (`0x3a05…9115`, USDB/WETHRebasing yield assets) both emit `ERC20BridgeInitiated`/`ETHBridgeInitiated` etc. **Disambiguate by emitting address.** The user-facing "Blast bridge address" in docs is `L1BlastBridge` `0x3a05…9115`.
3. **USDB's L1 backing is DAI `0x6B17…1d0F`.** In `L1BlastBridge.ERC20BridgeInitiated`, `localToken` = DAI, `remoteToken` = L2 USDB `0x4300…0003`. Do **not** treat USDB as having a distinct L1 ERC-20 — it is DAI in the vault.
4. **The Blast OptimismPortal withdrawal events/funcs are NON-STANDARD.** `WithdrawalProven` carries an extra `requestId` (`uint256`) and `WithdrawalFinalized`'s 2nd arg is `hintId` not `success`-only — **both EVENTS are Blast-modified** (topic0s differ from stock OP). On the FUNCTION side, only `finalizeWithdrawalTransaction` carries an extra leading `uint256 hintId`, giving the Blast-unique selector `0x3dca9c41` (stock OP = `0x8c3152e9`); `proveWithdrawalTransaction`'s selector `0x4870496f` is **identical to stock OP** (its modification is the event arg, not the function args). A stock OP decoder will mis-key the events and the finalize call. Recompute against the §1.2/§2.3 signatures.
5. **`YieldReport.yield` is a SIGNED `int256`** — negative means the bridge's staked principal LOST value (a provider drawdown), triggering an insurance draw (`insuranceWithdrawn` > 0). **A negative `yield` is a high-priority risk alert** (native-yield solvency).
6. **Withdrawals cross TWO queues.** A Blast L2→L1 ETH/USDB withdrawal must (a) pass the OP 7-day output challenge window AND (b) wait for the YieldManager unstake queue: `WithdrawalRequested` → `WithdrawalsFinalized` → `WithdrawalClaimed`. Funds are claimable only after both. Key the YieldManager flow on `requestId`; key the OP flow on `withdrawalHash`.
7. **`SentMessage` + `SentMessageExtension1` are a pair.** The ETH `value` of a messenger call is in the extension event, not `SentMessage`. Join them by tx + log order.
8. **`TransactionDeposited` is the catch-all deposit event.** Every deposit path (bridge, direct portal, messenger) ultimately emits `TransactionDeposited` from the Portal `0x0Ec6…D6Cb` — index it for total L1→L2 flow, then attribute the asset via the bridge-level `*BridgeInitiated` event in the same tx.
9. **`from` ≠ `tx.origin` on finalize/relay paths.** Finalization is messenger/relayer-driven; attribute deposits/withdrawals to the event's `from`/`to`/`recipient`, not `tx.from`.
10. **L1CrossDomainMessenger is a ResolvedDelegateProxy** (§8.2) — its impl is not in an EIP-1967 slot and won't emit `Upgraded`; watch `AddressSet` on the AddressManager instead.
11. **Impl drift is real** (§3.5/§8.1) — Portal, L2OutputOracle and USDYieldManager already drifted from the repo. Read the live slot and watch `Upgraded` (`0xbc7c…2d3b`).
12. **No "decoy" look-alikes in the target set**, but note the OP repo ships a separate `deployments/mainnet` directory holding **OP Mainnet's own** addresses (e.g. `L1StandardBridgeProxy 0x99C9…4bE1`) — those are NOT Blast. Use only `deployments/blast-mainnet` (`.chainId` = 1).
13. **Single Safe controls everything.** Both `ProxyAdmin.owner()` and `SystemConfig.owner()` resolve to the `SystemOwnerSafe` Gnosis Safe `0x4f72…8B05`; admin/upgrade actions originate there.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- StandardBridge + BlastBridge (disambiguate by emitter)
TOPIC_ETH_BRIDGE_INITIATED      = '\x2849b43074093a05396b6f2a937dee8565b15a48a7b3d4bffb732a5017380af5'
TOPIC_ETH_BRIDGE_FINALIZED      = '\x31b2166ff604fc5672ea5df08a78081d2bc6d746cadce880747f3643d819e83d'
TOPIC_ERC20_BRIDGE_INITIATED    = '\x7ff126db8024424bbfd9826e8ab82ff59136289ea440b04b39a0df1b03b9cabf'
TOPIC_ERC20_BRIDGE_FINALIZED    = '\xd59c65b35445225835c83f50b6ede06a7be047d22e357073e250d9af537518cd'
TOPIC_ETH_DEPOSIT_INITIATED     = '\x35d79ab81f2b2017e19afb5c5571778877782d7a8786f5907f93b0f4702f4f23'
TOPIC_ETH_WITHDRAWAL_FINALIZED  = '\x2ac69ee804d9a7a0984249f508dfab7cb2534b465b6ce1580f99a38ba9c5e631'
TOPIC_ERC20_DEPOSIT_INITIATED   = '\x718594027abd4eaed59f95162563e0cc6d0e8d5b86b1c7be8b1b0ac3343d0396'
TOPIC_ERC20_WITHDRAWAL_FINALIZED= '\x3ceee06c1e37648fcbb6ed52e17b3e1f275a1f8c7b22a84b2b84732431e046b3'
-- OptimismPortal (Blast-modified)
TOPIC_TRANSACTION_DEPOSITED     = '\xb3813568d9991fc951961fcb4c784893574240a28925604d09fc577c55bb7c32'
TOPIC_WITHDRAWAL_PROVEN         = '\x5d5446905f1f582d57d04ced5b1bed0f1a6847bcee57f7dd9d6f2ec12ab9ec2e'
TOPIC_WITHDRAWAL_FINALIZED      = '\x36d89e6190aa646d1a48286f8ad05e60a144483f42fd7e0ea08baba79343645b'
TOPIC_PORTAL_PAUSED             = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_PORTAL_UNPAUSED           = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
-- L1CrossDomainMessenger
TOPIC_SENT_MESSAGE              = '\xcb0f7ffd78f9aee47a248fae8db181db6eee833039123e026dcbff529522e52a'
TOPIC_SENT_MESSAGE_EXT1         = '\x8ebb2ec2465bdb2a06a66fc37a0963af8a2a6a1479d81d56fdb8cbb98096d546'
TOPIC_RELAYED_MESSAGE           = '\x4641df4a962071e12719d8c8c8e5ac7fc4d97b927346a3d7a335b1f7517e133c'
TOPIC_FAILED_RELAYED_MESSAGE    = '\x99d0e048484baa1b1540b1367cb128acd7ab2946d1ed91ec10e3c85e4bf51b8f'
-- L2OutputOracle
TOPIC_OUTPUT_PROPOSED           = '\xa7aaf2512769da4e444e3de247be2564225c2e7a8f74cfe528e46e17d24868e2'
TOPIC_OUTPUTS_DELETED           = '\x4ee37ac2c786ec85e87592d3c5c8a1dd66f8496dda3f125d9ea8ca5f657629b6'
-- YieldManager (ETH + USD; disambiguate by emitter)
TOPIC_WITHDRAWAL_REQUESTED      = '\x00ae2c76ca218353c7995e13a4af773a35837cb6ebb8288092d8190bcd9c8f68'
TOPIC_WITHDRAWALS_FINALIZED     = '\x59382740d48c89a44d8866c8e7071aa24351a82e5f38e4674ab82aa8a18119bc'
TOPIC_WITHDRAWAL_CLAIMED        = '\x8adb7a84b2998a8d11cd9284395f95d5a99f160be785ae79998c654979bd3d9a'
TOPIC_YIELD_REPORT              = '\x00de4b58e7863b1e3dce7259a138136239427388d53e4844f369cdee7a81dbf5'
-- Proxy / registry
TOPIC_UPGRADED                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED             = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_ADDRESS_SET               = '\x9416a153a346f93d95f94b064ae3f148b6460473c6e82b3f9fc2521b873fcd6c'

-- ===== Selectors =====
SEL_BRIDGE_ETH                  = '\x09fc8843'
SEL_BRIDGE_ETH_TO               = '\xe11013dd'
SEL_BRIDGE_ERC20                = '\x87087623'
SEL_BRIDGE_ERC20_TO             = '\x540abf73'
SEL_FINALIZE_BRIDGE_ETH         = '\x1635f5fd'
SEL_FINALIZE_BRIDGE_ERC20       = '\x0166a07a'
SEL_SET_ETH_YIELD_TOKEN         = '\xc8fb1533'
SEL_SET_USD_YIELD_TOKEN         = '\xd9ffb9d6'
SEL_DEPOSIT_TRANSACTION         = '\xe9e05c42'
SEL_PROVE_WITHDRAWAL            = '\x4870496f'
SEL_FINALIZE_WITHDRAWAL         = '\x3dca9c41'
SEL_PORTAL_PAUSE                = '\x8456cb59'
SEL_PORTAL_UNPAUSE              = '\x3f4ba83a'
SEL_SEND_MESSAGE                = '\x3dbb202b'
SEL_RELAY_MESSAGE               = '\xd764ad0b'
SEL_PROPOSE_L2_OUTPUT           = '\x9aaab648'
SEL_DELETE_L2_OUTPUTS           = '\x89c44cbb'
SEL_REQUEST_WITHDRAWAL          = '\x9ee679e8'
SEL_CLAIM_WITHDRAWAL            = '\xf21340e4'
SEL_FINALIZE_QUEUE              = '\x05261aea'
SEL_STAKE                       = '\x6e9c931c'
SEL_UNSTAKE                     = '\x51a7c716'
SEL_COMMIT_YIELD_REPORT         = '\xe7518fb6'
SEL_RECORD_NEGATIVE_YIELD       = '\xd6ce7910'
SEL_UPGRADE_TO                  = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL         = '\x4f1ef286'

-- ===== Addresses — Ethereum L1 (chain 1) =====
ETH_OPTIMISM_PORTAL             = '\x0ec68c5b10f21effb74f2a5c61dfe6b08c0db6cb'
ETH_L1_CROSS_DOMAIN_MESSENGER   = '\x5d4472f31bd9385709ec61305afc749f0fa8e9d0'
ETH_L2_OUTPUT_ORACLE            = '\x826d1b0d4111ad9146eb8941d7ca2b6a44215c76'
ETH_SYSTEM_CONFIG               = '\x5531dcff39ec1ec727c4c5d2fc49835368f805a9'
ETH_L1_STANDARD_BRIDGE          = '\x697402166fbf2f22e970df8a6486ef171dbfc524'
ETH_L1_BLAST_BRIDGE             = '\x3a05e5d33d7ab3864d53aaec93c8301c1fa49115'
ETH_L1_ERC721_BRIDGE            = '\xa45a0c7c47db8c6e99b2d7c4939f7f7cf69c8975'
ETH_OPT_MINTABLE_ERC20_FACTORY  = '\x6b916dcca661d23794e78509723a6f4348564847'
ETH_ETH_YIELD_MANAGER           = '\x98078db053902644191f93988341e31289e1c8fe'
ETH_USD_YIELD_MANAGER           = '\xa230285d5683c74935ad14c446e137c8c8828438'
ETH_ETH_YIELD_PROVIDER_LIDO     = '\x4316a00d31da1313617dbb04fd92f9ff8d1af7db'
ETH_USD_YIELD_PROVIDER_DSR      = '\x0733f618118bf420b6b604c969498ecf143681a8'
ETH_ETH_INSURANCE               = '\xcff70d7f37b1ebee89c08e485f08acab5f6ff873'
ETH_USD_INSURANCE               = '\xbbe2cd60bd30ef2aacefd74c3199282ee35fbba6'
ETH_PROXY_ADMIN                 = '\x364289230b8cc7d9120ef962af37ebcfe23ce883'
ETH_ADDRESS_MANAGER             = '\xe064b565cf2a312a3e66fe4118890583727380c0'
ETH_SYSTEM_OWNER_SAFE           = '\x4f72ee94b8ba3be7f886565d3583a7f636c58b05'
ETH_USDB_L1_BACKING_DAI         = '\x6b175474e89094c44da98b954eedeac495271d0f'
-- ===== Blast L2 counterparty (chain 81457; OUTSIDE the seven) =====
BLAST_L2_STANDARD_BRIDGE        = '\x4200000000000000000000000000000000000010'
BLAST_L2_BLAST_BRIDGE           = '\x4300000000000000000000000000000000000005'
BLAST_L2_XDM                    = '\x4200000000000000000000000000000000000007'
BLAST_L2_TO_L1_MESSAGE_PASSER   = '\x4200000000000000000000000000000000000016'
BLAST_YIELD_PREDEPLOY           = '\x4300000000000000000000000000000000000002'
BLAST_USDB                      = '\x4300000000000000000000000000000000000003'
BLAST_WETH_REBASING             = '\x4300000000000000000000000000000000000004'
```

---

## 11. Verification & sources

**How these constants were verified (2026-06-09):**
- **Topic0 / selectors** recomputed locally as `keccak256(canonical signature)` (no param names, `uint`→`uint256`, tuples expanded). Each event signature was extracted from the contract ABI in the `blast-mainnet` deployment artifacts; tuple-bearing function signatures (`proveWithdrawalTransaction`, `finalizeWithdrawalTransaction`) were expanded from ABI components before hashing.
- **Topics cross-checked against live `eth_getLogs`** on the Ethereum L1 emitters in a 49 000-block window ending block 25 279 371: `TransactionDeposited` (117), `WithdrawalProven` (60), `WithdrawalFinalized` (60), `ETHBridgeInitiated` (4, StandardBridge), `ERC20BridgeInitiated` (1, BlastBridge), `SentMessage` (67), `OutputProposed` (165), `WithdrawalRequested` (38 ETH / 14 USD), `WithdrawalsFinalized` (7), `YieldReport` (6).
- **Selectors cross-checked** by scanning the live implementation bytecode (PUSH4 occurrences) of the Portal impl `0xa280…4391` and ETHYieldManager impl `0xf2f6…9525` — `depositTransaction`/`proveWithdrawalTransaction`/`finalizeWithdrawalTransaction`/`pause` and `claimWithdrawal`/`requestWithdrawal`/`stake`/`commitYieldReport` all PRESENT.
- **Addresses** parsed from the `blast-io/blast` repo `deployments/blast-mainnet` (`.chainId` = 1) and existence-checked via `eth_getCode` (non-empty) on Ethereum; `0x` (absent) confirmed on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon.
- **Proxy impls** read live from the EIP-1967 implementation slot (`0x3608…2bbc`) and admin slot (`0xb531…6103`); the L1CrossDomainMessenger impl resolved via `AddressManager.getAddress("OVM_L1CrossDomainMessenger")`. Three impls found drifted from the repo (Portal, L2OutputOracle, USDYieldManager). `ProxyAdmin.owner()`, `SystemConfig.owner()` and `L1BlastBridge.otherBridge()` were read via `eth_call`.

**Authoritative sources:**
- Canonical repo: `https://github.com/blast-io/blast` (`blast-optimism/packages/contracts-bedrock/deployments/blast-mainnet`)
- Official docs: `https://docs.blast.io/building/bridges/mainnet`, `https://docs.blast.io/building/predeploys-and-precompiles`
- Block explorer: `https://etherscan.io` (L1), `https://blastscan.io` (L2)
- Upstream OP-Stack reference: `https://github.com/ethereum-optimism/optimism` (Bedrock contracts the fork derives from)

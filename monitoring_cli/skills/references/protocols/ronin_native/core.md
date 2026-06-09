# Ronin Bridge — Topics, Selectors, Addresses (Ethereum L1 only; counterparty = Ronin chain 2020)

**Status:** verified against live RPC on all seven listed chains and the canonical `axieinfinity/ronin-bridge-contracts` (+ legacy `axieinfinity/ronin-smart-contracts`) repos on 2026-06-09.
**Scope:** the Ethereum-mainnet leg of the Ronin Bridge — the **MainchainGatewayV3** lock/mint gateway (proxy), its governance (**MainchainBridgeManager** / **MainchainGovernanceAdmin**), the **PauseEnforcer**, the **RoninTrustedOrganization** registry, and the deprecated **V1 MainchainGateway** (pre-2022-hack). Topics/selectors are **chain-agnostic**; addresses are network-specific. **Every Ronin Bridge contract lives only on Ethereum (chain 1)** of the seven requested chains — `eth_getCode` = `0x` for every address on Base / BNB / Avalanche / Arbitrum / Optimism / Polygon. The bridge's *other* leg (RoninGatewayV3, RoninBridgeManager, BridgeReward/Slash/Tracking) lives on the **Ronin chain (chainId 2020), which is outside the seven** — recorded as a finding in §6, not indexed here.

The Ronin Bridge is a **lock-and-mint validator bridge**, not a generic messaging layer. A user **deposits** on Ethereum (`requestDepositFor`) → the gateway escrows the token and emits **`DepositRequested`** → off-chain bridge operators relay it and mint the wrapped asset on Ronin. To come back, a user burns on Ronin → operators sign a `Receipt` → anyone calls **`submitWithdrawal`** on Ethereum with the operator multisig signatures → the gateway releases funds and emits **`Withdrew`**. Withdrawals above a per-token daily quota are **locked** (`WithdrawalLocked`) until a `WITHDRAWAL_UNLOCKER_ROLE` holder calls `unlockWithdrawal` (`WithdrawalUnlocked`) — this rate-limit was added after the **March 2022 $625M validator-key compromise** that drained the V1 gateway.

The live gateway is an **EIP-1967 transparent proxy** (`TransparentUpgradeableProxyV2`, OpenZeppelin-extended) at `0x6419…AF08`, current impl `0x5019…4e69`. Its proxy **admin** is itself a proxy-fronted **MainchainBridgeManager** (`0x2cf3…fadb`), so upgrades and operator-set changes flow through the bridge-operator governance, not an EOA. There is **no per-chain redeploy and no CREATE2 vanity** — these are single Ethereum singletons. Key on `(chainId=1, address)`.

> **Two BridgeManager addresses (verified on-chain):** the repo deployment record lists a *direct* (non-proxy) `MainchainBridgeManager` at `0xa714…fab0`, but the gateway proxy's live admin slot points to a **different**, proxy-wrapped `MainchainBridgeManager` at `0x2cf3…fadb` (impl `0x0ac2…22fd`). The proxy-wrapped one is the one actually governing the gateway today. Both are live; don't assume the README address is the active governor.

> **The live `DepositRequested` / `Withdrew` events carry NO indexed parameter (verified by log decode).** Despite the interface declaring `receiptHash` as `indexed`, the deployed logs have **`ntopics = 1`** (topic0 only) and the 32-byte `receiptHash` is the **first word of `data`**, followed by the inlined 11-word `Receipt` tuple (384-byte data total). Filter by topic0 + emitter address; read `receiptHash` from `data[0:32]`, not from `topics[1]`. (topic0 is unaffected by `indexed`, so the computed hashes still match.)

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified name on chain |
|----------|------|--------|------------------------|
| **MainchainGatewayV3** | The live lock/mint gateway. Holds bridged ETH/ERC-20/721. Emits `DepositRequested`/`Withdrew`/`WithdrawalLocked`/`WithdrawalUnlocked`/`TokenMapped`. | **EIP-1967 transparent proxy** (`TransparentUpgradeableProxyV2`) | `MainchainGatewayV3` (impl) |
| **MainchainBridgeManager** (active) | Governs the gateway proxy (its admin) + manages the bridge-operator set & governance proposals. Sits in the gateway's admin slot. | **EIP-1967 transparent proxy** (`TransparentProxyV2`) | `MainchainBridgeManager` (impl) |
| **MainchainBridgeManager** (registry/direct) | Repo deployment record's manager; direct (non-proxy) deploy; relays proposals. | **No** (direct, 19 336 B) | `MainchainBridgeManager` |
| **MainchainGovernanceAdmin** | Legacy governance executor (trusted-org-weighted voting). | **No** (direct, 16 499 B) | `MainchainGovernanceAdmin` |
| **MainchainGatewayPauseEnforcer** | Emergency circuit-breaker — a sentry multisig can `triggerPause()` the gateway without full governance. | **No** (direct, 4 028 B) | `PauseEnforcer` |
| **RoninTrustedOrganization** | Registry of trusted-org governors + their weights (drives governance thresholds). | **EIP-1967 transparent proxy** | `RoninTrustedOrganization` (impl) |
| **MainchainGateway (V1)** | The **deprecated** pre-hack gateway (Solidity 0.5.17). Still holds ~469 ETH of stranded/legacy funds. Emits `TokenDeposited`/`TokenWithdrew`. | **Custom (non-EIP-1967) proxy** | `MainchainGatewayProxy` |

All V3 events/selectors are inherited from the impl; the gateway is the only contract that emits deposit/withdraw activity. The two governance managers + governance admin + pause enforcer + trusted-org registry are the **control plane** — watch them for operator-set churn, upgrades, and pauses.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Recomputed locally with keccak256 on 2026-06-09. `DepositRequested` and `Withdrew` additionally confirmed against **live gateway logs** (see §7). The deposit/withdraw events embed the fully-expanded `Transfer.Receipt` tuple:
`Receipt = (uint256 id, uint8 kind, Owner mainchain, Owner ronin, Info info)`, where `Owner = (address addr, address tokenAddr, uint256 chainId)` and `Info = (uint8 erc, uint256 id, uint256 quantity)`. So the ABI tuple is `(uint256,uint8,(address,address,uint256),(address,address,uint256),(uint8,uint256,uint256))`.

### 1.1 MainchainGatewayV3 (emitter = `0x6419…AF08`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd7b25068d9dc8d00765254cfb7f5070f98d263c8d68931d937c7362fa738048b` | `DepositRequested(bytes32 receiptHash, (uint256,uint8,(address,address,uint256),(address,address,uint256),(uint8,uint256,uint256)) receipt)` | **User deposit → Ronin.** *(verified live, ntopics=1, 384-B data)* |
| `0x21e88e956aa3e086f6388e899965cef814688f99ad8bb29b08d396571016372d` | `Withdrew(bytes32 receiptHash, (...) receipt)` | **Withdrawal released from Ronin.** *(verified live, ntopics=1, 384-B data)* |
| `0x89e52969465b1f1866fc5d46fd62de953962e9cb33552443cd999eba05bd20dc` | `WithdrawalLocked(bytes32 receiptHash, (...) receipt)` | Withdrawal exceeded daily quota → locked. |
| `0xd639511b37b3b002cca6cfe6bca0d833945a5af5a045578a0627fc43b79b2630` | `WithdrawalUnlocked(bytes32 receiptHash, (...) receipt)` | Unlocker released a locked withdrawal. |
| `0xa4f03cc9c0e0aeb5b71b4ec800702753f65748c2cf3064695ba8e8b46be70444` | `TokenMapped(address[] mainchainTokens, address[] roninTokens, uint8[] standards)` | Token map updated (admin). |
| `0x9d2334c23be647e994f27a72c5eee42a43d5bdcfe15bb88e939103c2b114cbaf` | `WrappedNativeTokenContractUpdated(address weth)` | WETH wrapper address changed. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | Gateway paused (Pausable). |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | Gateway unpaused. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 role, address account, address sender)` | AccessControl — e.g. WITHDRAWAL_UNLOCKER_ROLE granted. |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 role, address account, address sender)` | Role revoked. |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 role, bytes32 prev, bytes32 new)` | Role admin changed. |

### 1.2 Proxy/upgrade (gateway + manager + trusted-org proxies)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address implementation)` | **Watch on the gateway proxy** to catch impl rotations (impl already rotated from the repo record `0x2dba…af73` to the live `0x5019…4e69`). |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address prev, address new)` | Proxy admin changed. |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` | Proxy (re)initialized. |

### 1.3 MainchainBridgeManager — governance / operator set (emitters `0xa714…fab0` and `0x2cf3…fadb`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x897810999654e525e272b5909785c4d0ceaee1bbf9c87d9091a37558b0423b78` | `BridgeOperatorsAdded(bool[] statuses, uint96[] voteWeights, address[] governors, address[] operators)` | **Operator set grew.** Risk-relevant. |
| `0xdf3dcd7987202f64648f3acdbf12401e3a2bb23e77e19f99826b5475cbb86369` | `BridgeOperatorsRemoved(bool[] statuses, address[] operators)` | Operator set shrank. |
| `0xcef34cd748f30a1b7a2f214fd1651779f79bc6c1be02785cad5c1f0ee877213d` | `BridgeOperatorUpdated(address governor, address fromOperator, address toOperator)` | Operator key rotated (governor-driven). |
| `0x976f8a9c5bdf8248dec172376d6e2b80a8e3df2f0328e381c6db8e1cf138c0f8` | `ThresholdUpdated(uint256 nonce, uint256 numerator, uint256 prevNum, uint256 denominator, uint256 prevDenom)` | Signature/vote threshold changed. |
| `0x5c819725ea53655a3b898f3df59b66489761935454e9212ca1e5ebd759953d0b` | `ProposalApproved(bytes32 proposalHash)` | |
| `0x55295d4ce992922fa2e5ffbf3a3dcdb367de0a15e125ace083456017fd22060f` | `ProposalRejected(bytes32 proposalHash)` | |
| `0x1203f9e81c814a35f5f4cc24087b2a24c6fb7986a9f1406b68a9484882c93a23` | `ProposalVoted(bytes32 proposalHash, address voter, uint8 support, uint256 weight)` | |
| `0xe134987599ae266ec90edeff1b26125b287dbb57b10822649432d1bb26537fba` | `ProposalExecuted(bytes32 proposalHash, bool[] successCalls, bytes[] returnDatas)` | A governance bundle executed. |
| `0xa57d40f1496988cf60ab7c9d5ba4ff83647f67d3898d441a3aaf21b651678fd9` | `ProposalCreated(uint256 chainId, uint256 round, bytes32 proposalHash, (uint256,uint256,uint256,address[],uint256[],bytes[],uint256[]) proposal, address creator)` | tuple = `ProposalDetail`; recompute if a struct version differs — verify against a live log before keying. |
| `0x02609fcfd61fd5660d3bf2a95a0b4759688cfae1295f0b8d4510403bc83d9bd2` | `GlobalProposalCreated(uint256 round, bytes32 proposalHash, (uint256,uint256,uint8[],uint256[],bytes[],uint256[]) globalProposal, bytes32 globalProposalHash, (uint256,uint256,uint8[],uint256[],bytes[],uint256[]) proposal, address creator)` | tuple = `GlobalProposalDetail`; verify against a live log before keying. |

### 1.4 V1 MainchainGateway — DEPRECATED (emitter = `0x1a2a…54f2`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x72848855a2461abf0dd243723dfcc9163eec2ea5215469d101c0d9c9ef58940d` | `TokenDeposited(uint256 _depositId, address _owner, address _tokenAddress, address _sidechainAddress, uint32 _standard, uint256 _tokenNumber)` | **V1 deposit.** *(verified live in historic block ~13.5M, ntopics=4)* |
| `0x86174ea401f083b9bb1bdebca3068f27fb023c7091365ed2a8a02b8d75cf0e52` | `TokenWithdrew(uint256 _withdrawId, address _owner, address _tokenAddress, uint256 _tokenNumber)` | **V1 withdrawal.** *(verified live, ntopics=4)* |

> V1 events are a **different signature family** from V3 (no `Receipt` tuple, `_standard` is `uint32` not the V3 `uint8` enum). V1 has been dormant since the 2022 migration — treat any new V1 activity as anomalous.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All gateway selectors below verified **present** in the live impl `0x5019…4e69` bytecode on 2026-06-09 (PUSH4 scan) **except `receiveEther`** (absent — renamed/removed in V3; native receipt is via the `receive()` fallback).

### 2.1 MainchainGatewayV3 — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4b14557e` | `requestDepositFor((address,address,(uint8,uint256,uint256)) request)` | `payable`. **User deposit entrypoint.** `Request = (recipientAddr, tokenAddr, Info)`. Emits `DepositRequested`. |
| `0x4d0d6673` | `submitWithdrawal((uint256,uint8,(address,address,uint256),(address,address,uint256),(uint8,uint256,uint256)) receipt, (uint8,bytes32,bytes32)[] signatures)` → `bool locked` | **Withdrawal entrypoint** — operator multisig sigs. Emits `Withdrew` or `WithdrawalLocked`. |
| `0x9157921c` | `unlockWithdrawal((uint256,uint8,(address,address,uint256),(address,address,uint256),(uint8,uint256,uint256)) receipt)` | `WITHDRAWAL_UNLOCKER_ROLE`. Emits `WithdrawalUnlocked`. |
| `0x1b6e7594` | `mapTokens(address[] mainchainTokens, address[] roninTokens, uint8[] standards)` | Admin. Emits `TokenMapped`. |
| `0xdff525e1` | `mapTokensAndThresholds(address[] mainchainTokens, address[] roninTokens, uint8[] standards, uint256[][4] thresholds)` | Admin — map + set daily-quota thresholds. |
| `0xd64af2a6` | `setWrappedNativeTokenContract(address wrappedToken)` | Admin. Emits `WrappedNativeTokenContractUpdated`. |
| `0x8456cb59` | `pause()` | Pausable. Emits `Paused`. |
| `0x3f4ba83a` | `unpause()` | Pausable. Emits `Unpaused`. |

### 2.2 MainchainGatewayV3 — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x2dfdf0b5` | `depositCount()` | `uint256` — monotonically increasing deposit id. *(live read = 111354)* |
| `0xb2975794` | `getRoninToken(address mainchainToken)` | `(uint8 erc, address roninToken)` — e.g. WETH → `0xc99a…9ef5` (Ronin WETH). |
| `0x6932be98` | `withdrawalHash(uint256 withdrawalId)` | `bytes32` — receipt hash of a processed withdrawal. |
| `0x4d493f4e` | `withdrawalLocked(uint256 withdrawalId)` | `bool`. |
| `0x17fcb39b` | `wrappedNativeToken()` | `address` — *live = WETH `0xc02a…56cc2`*. |
| `0x3644e515` | `DOMAIN_SEPARATOR()` | `bytes32` — EIP-712 domain for the operator signatures. |
| `0x5c975abb` | `paused()` | `bool` — *live = false*. |
| `0x91d14854` | `hasRole(bytes32 role, address account)` | `bool`. |

### 2.3 Proxy surface (gateway + manager + trusted-org proxies — `TransparentUpgradeableProxyV2`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | admin-only. Emits `Upgraded`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | `payable`, admin-only. |
| `0x4bb5274a` | `functionDelegateCall(bytes data)` | **OZ-extended** — admin can delegatecall the impl through the proxy (Ronin's `V2` extension). |
| `0x5c60da1b` | `implementation()` | admin-only getter. |
| `0xf851a440` | `admin()` | admin-only getter. |

### 2.4 V1 MainchainGateway — DEPRECATED (`0x1a2a…54f2`)

The V1 deposit/withdraw entrypoints (`depositEth`, `depositERC20`, `withdrawToken`, `withdrawERC20`) are on the legacy `MainchainGatewayManager` impl `0x8407…2F21E` (Solidity 0.5.17). Dormant — listed only for completeness; not re-derived here since V1 is not a monitoring target post-migration.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Proxies show their live impl (read from the EIP-1967 slot).

| Role | Address | Impl (if proxy) | One-liner |
|------|---------|-----------------|-----------|
| **MainchainGatewayV3** (proxy) | `0x64192819Ac13Ef72bF6b5AE239AC672B43a9AF08` | `0x5019d41b0737e39b51fd6da4859f3e27579e4e69` | **The live bridge.** Emits §1.1 events. 2 608-B proxy; `depositCount`=111354; `paused`=false. |
| Gateway impl (live) | `0x5019d41b0737e39b51fd6da4859f3e27579e4e69` | — (24 028 B) | `MainchainGatewayV3`, solc 0.8.27. ≠ the repo deployment record `0x2dba…af73` (impl rotated). |
| Gateway impl (repo record) | `0x2DBA725f0a3485382a7F125a31cBF4361539aF73` | — (22 559 B) | Older `MainchainGatewayV3Logic` from the repo; superseded by `0x5019…`. |
| Gateway impl (alt repo logic) | `0x72E28A9009Ad12dE019BFF418CD210D4bbc3D403` | — (18 231 B) | `MainchainGatewayV3Logic` (another recorded version). Not the live impl. |
| Gateway V2 impl (legacy) | `0xa67BA5315AF4961Eb937158032AF9300C657dAcD` | — (20 599 B) | `MainchainGatewayV2Logic`; pre-V3 logic, not pointed-to today. |
| **MainchainBridgeManager** (active, governs gateway) | `0x2cf3cFB17774CE0cFA34bb3f3761904E7fc3FaDB` | `0x0ac26945032143f6196d4bb5ae03592bfaf822fd` | `TransparentProxyV2` → `MainchainBridgeManager`. **Sits in the gateway's admin slot** — the live governor. |
| MainchainBridgeManager (direct, registry) | `0xa71456fA88a5f6a4696D0446E690Db4a5913fab0` | — (19 336 B) | Repo deployment record's `MainchainBridgeManager`, direct deploy; relays proposals. |
| MainchainBridgeManager logic | `0x0ac26945032143f6196d4bb5ae03592bfaf822fd` | — | Impl behind `0x2cf3…fadb`. |
| **MainchainGovernanceAdmin** | `0xB255D6A720BB7c39fee173cE22113397119cB930` | — (16 499 B) | Legacy trusted-org governance executor. |
| **PauseEnforcer** | `0xe514d9DEB7966c8BE0ca922de8a064264eA6bcd4` | — (4 028 B) | Emergency pause; targets the gateway (`0x6419…`); sentry-triggered. |
| **RoninTrustedOrganization** (proxy) | `0x7D0556D55ca1a92708681e2e231733EBd922597D` | `0x9Be8BB3C6ced4C0C51b1C943Dee26a593b1E6794` | Trusted-org governor/weight registry (drives thresholds). |
| RoninTrustedOrganization impl | `0x9Be8BB3C6ced4C0C51b1C943Dee26a593b1E6794` | — (9 566 B) | `RoninTrustedOrganization` logic. |
| **V1 MainchainGateway** (DEPRECATED proxy) | `0x1a2a1c938cE3eC39b6D47113c7955bAa9DD454F2` | `0x8407dC57739bCDA7aA53Ca6F12F82F9d51c2F21E` | Pre-hack gateway (solc 0.5.17, custom proxy). Still holds ~469 ETH. Emits §1.4 events. Dormant. |
| V1 gateway impl | `0x8407dC57739bCDA7aA53Ca6F12F82F9d51c2F21E` | — (11 317 B) | `MainchainGatewayManager`. |
| WETH (wrapped native) | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | — | `wrappedNativeToken()` of the V3 gateway. |

Gateway admin slot read live = `0x2cf3cfb17774ce0cfa34bb3f3761904e7fc3fadb` (the active BridgeManager proxy); impl slot read live = `0x5019d41b0737e39b51fd6da4859f3e27579e4e69`.

---

## 4. Addresses — all other requested chains (Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Optimism 10, Polygon 137)

**No Ronin Bridge contract is deployed on any of these six chains.** Every address in §3 returns `0x` from `eth_getCode` on each chain's publicnode RPC (verified 2026-06-09). The Ronin Bridge is a **two-leg bridge between Ethereum L1 and the Ronin chain (chainId 2020) only** — it does not bridge to or from Base / BNB / Avalanche / Arbitrum / Optimism / Polygon. There is nothing to index on those six chains.

---

## 5. Cross-chain summary

| Chain | ID | Gateway V3 `0x6419…` | BridgeManager (active) `0x2cf3…` | GovernanceAdmin `0xB255…` | PauseEnforcer `0xe514…` | V1 Gateway `0x1a2a…` |
|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✓ | ✓ | ✓ | ✓ | ✓ (dormant) |
| Base | 8453 | — | — | — | — | — |
| BNB | 56 | — | — | — | — | — |
| Avalanche | 43114 | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — |
| **Ronin chain** | **2020** | *(counterparty leg — RoninGatewayV3 etc., OUTSIDE the seven; see §6)* | | | | |

No CREATE2 / deterministic vanity addresses — all are one-off Ethereum singletons. Key everything on `(chainId=1, address)`.

---

## 6. Counterparty leg — Ronin chain (chainId 2020, OUTSIDE the seven)

The mirror-image contracts run on the **Ronin chain** (an Axie-Infinity DPoS EVM chain, chainId **2020**, launched 2020 — not one of the seven requested chains, so not indexed here but recorded as a finding):

- **RoninGatewayV3** — the Ronin-side mint/burn gateway (counterpart of MainchainGatewayV3); emits its own `DepositRequested`/`Withdrew`.
- **RoninBridgeManager** — Ronin-side operator-set governance.
- **RoninGovernanceAdmin**, **BridgeReward**, **BridgeSlash**, **BridgeTracking** — operator reward/slash/uptime accounting (these reward/slash contracts exist **only** on the Ronin chain, not on Ethereum).

In a `Receipt`, the `mainchain` `Owner.chainId` = **1** (Ethereum) and the `ronin` `Owner.chainId` = **2020** — confirmed in a live `Withdrew` log (ronin chainId field = `0x7e4` = 2020), and `getRoninToken(WETH)` returns the Ronin WETH `0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5`. To monitor the full bridge you would index chain 2020 separately; the Ethereum leg in this file is the canonical L1 anchor.

---

## 7. Proxies (old & new)

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. Read with `eth_getStorageAt(addr, slot)`.

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **MainchainGatewayV3** `0x6419…` | **EIP-1967 transparent** (`TransparentUpgradeableProxyV2`) | impl slot = `0x5019…4e69`; admin slot = `0x2cf3…fadb` (a BridgeManager proxy, **not an EOA**); 2 608-B proxy. | the admin (`0x2cf3…fadb` BridgeManager) → bridge-operator governance. Watch `Upgraded` `0xbc7cd75a…`. |
| **MainchainBridgeManager** (active) `0x2cf3…` | **EIP-1967 transparent** (`TransparentProxyV2`) | impl slot = `0x0ac2…22fd`; admin slot = `0x51f6…b26e`. | governance. |
| **RoninTrustedOrganization** `0x7D05…` | **EIP-1967 transparent** | impl slot = `0x9Be8…6794`; 2 362-B proxy. | governance. |
| **MainchainBridgeManager** (direct) `0xa714…` | **Not a proxy** | impl slot = `0x000…0` (confirmed); 19 336-B full contract. | n/a (direct). |
| **MainchainGovernanceAdmin** `0xB255…` | **Not a proxy** | impl slot = `0x000…0`; 16 499-B full contract. | n/a. |
| **PauseEnforcer** `0xe514…` | **Not a proxy** | impl slot = `0x000…0`; 4 028-B full contract. | n/a. |
| **V1 MainchainGateway** `0x1a2a…` | **Custom (non-EIP-1967) proxy** | EIP-1967 impl/admin slots are **empty**; impl is at storage **slot 0x1** (`0x8407…2F21E`, packed with a flag byte) and admin at **slot 0x0** (`0x23d4…38fa`). Solidity 0.5.17 era. | legacy admin. |

To read the live gateway impl: `cast storage 0x64192819Ac13Ef72bF6b5AE239AC672B43a9AF08 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. **The impl already rotated** from the repo record `0x2dba…af73` to the live `0x5019…4e69`; always read the slot, never hard-code.

---

## 8. Detection invariants & gotchas

1. **`DepositRequested` / `Withdrew` have NO indexed parameter on-chain** — `ntopics = 1`. The `receiptHash` is `data[0:32]`, not `topics[1]`, followed by the inlined 11-word `Receipt`. Filter by topic0 + emitter address; decode `receiptHash` and the receipt from `data`. (The interface marks `receiptHash` `indexed`, but the deployed impl does not — verified by decoding live logs.)
2. **The real user is `receipt.mainchain.addr` (the deposit recipient) / the receipt owner, NOT `tx.from`.** Withdrawals are submitted by anyone holding the operator multisig signatures (relayers/bots), so `tx.from` ≠ beneficiary. Attribute to the `Owner.addr` field inside the receipt.
3. **`receipt.ronin.chainId` = 2020 and `receipt.mainchain.chainId` = 1** identify the two legs. A receipt's `id` (`receipt.id`) is the cross-chain nonce — key withdrawals on `(receipt.id)` / `withdrawalHash`, deposits on `depositCount` order.
4. **Deposits and withdrawals are asymmetric in frequency.** `Withdrew` (Ronin→ETH) fires far more often than `DepositRequested` (ETH→Ronin). In short recent windows you may see only `Withdrew`; deposits cluster in older windows.
5. **`WithdrawalLocked` is the rate-limit tripwire.** A withdrawal over the per-token daily quota emits `WithdrawalLocked` instead of `Withdrew` and must be `unlockWithdrawal`-ed by a `WITHDRAWAL_UNLOCKER_ROLE` holder (`WithdrawalUnlocked`). A spike in `WithdrawalLocked` = large/anomalous outflow attempt — high-value alert.
6. **Two distinct `MainchainBridgeManager` addresses.** The README/repo record is `0xa714…fab0` (direct), but the gateway's **live admin** is `0x2cf3…fadb` (proxy → impl `0x0ac2…22fd`). For "who can upgrade/pause the gateway and change operators," the answer is `0x2cf3…fadb`, not the README address.
7. **The gateway admin is a contract, not an EOA.** Reading the admin slot returns a BridgeManager proxy. Upgrades flow through operator governance (`ProposalExecuted` → `Upgraded`). Watch `Upgraded` `0xbc7cd75a…` on `0x6419…` and `ProposalExecuted` / `BridgeOperatorsAdded/Removed` on the managers.
8. **`PauseEnforcer` (`0xe514…`) can pause the gateway out-of-band.** A sentry multisig can trip it without full governance → gateway emits `Paused`. Treat `Paused` on `0x6419…` as a critical signal (it is the canonical emergency response, used during the 2022 incident).
9. **V1 (`0x1a2a…54f2`) is a different event family and is dormant.** `TokenDeposited` `0x72848855…` / `TokenWithdrew` `0x86174ea4…` (no `Receipt` tuple, `_standard` is `uint32`). It still custodies ~469 ETH. Any **new** V1 `TokenWithdrew` is anomalous and worth alerting.
10. **`Upgraded` topic0 `0xbc7cd75a…` is the OZ-standard value shared by every transparent proxy** — disambiguate by emitter (`0x6419…` gateway vs `0x2cf3…` manager vs `0x7D05…` trusted-org). Same for `AdminChanged` / `Initialized` / `Paused`.
11. **Not deployed on any of the six non-Ethereum target chains** — every address returns `0x`. The bridge's other half is on the Ronin chain (2020), outside the seven (§6).
12. **`TokenMapped` / `mapTokens*` define which assets the bridge supports.** A new `TokenMapped` adds a bridgeable token; an unexpected mapping change is governance-relevant. Read `getRoninToken(mainchainToken)` to resolve a Ronin-side token.
13. **`Receipt.info.erc` is a `uint8` enum** (`0 = ERC20`, `1 = ERC721`; the live solc-0.8.27 impl also handles ERC1155). `TokenMapped`/`mapTokens` use `uint8[]` for the same enum — don't expand it to `uint256`.
14. **Operator signatures, not a light client.** Security rests on the bridge-operator multisig threshold (`ThresholdUpdated`) over the trusted-org set (`RoninTrustedOrganization` `0x7D05…`). The 2022 hack was a 5-of-9 key compromise — operator-set churn (`BridgeOperatorsAdded/Removed`, `BridgeOperatorUpdated`) is a first-class risk signal.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- MainchainGatewayV3
TOPIC_DEPOSIT_REQUESTED          = '\xd7b25068d9dc8d00765254cfb7f5070f98d263c8d68931d937c7362fa738048b'
TOPIC_WITHDREW                   = '\x21e88e956aa3e086f6388e899965cef814688f99ad8bb29b08d396571016372d'
TOPIC_WITHDRAWAL_LOCKED          = '\x89e52969465b1f1866fc5d46fd62de953962e9cb33552443cd999eba05bd20dc'
TOPIC_WITHDRAWAL_UNLOCKED        = '\xd639511b37b3b002cca6cfe6bca0d833945a5af5a045578a0627fc43b79b2630'
TOPIC_TOKEN_MAPPED               = '\xa4f03cc9c0e0aeb5b71b4ec800702753f65748c2cf3064695ba8e8b46be70444'
TOPIC_WRAPPED_NATIVE_UPDATED     = '\x9d2334c23be647e994f27a72c5eee42a43d5bdcfe15bb88e939103c2b114cbaf'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                   = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_ROLE_GRANTED               = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED               = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
-- Proxy / upgrade (disambiguate by emitter)
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED              = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_INITIALIZED                = '\x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498'
-- MainchainBridgeManager (governance / operator set)
TOPIC_BRIDGE_OPERATORS_ADDED     = '\x897810999654e525e272b5909785c4d0ceaee1bbf9c87d9091a37558b0423b78'
TOPIC_BRIDGE_OPERATORS_REMOVED   = '\xdf3dcd7987202f64648f3acdbf12401e3a2bb23e77e19f99826b5475cbb86369'
TOPIC_BRIDGE_OPERATOR_UPDATED    = '\xcef34cd748f30a1b7a2f214fd1651779f79bc6c1be02785cad5c1f0ee877213d'
TOPIC_THRESHOLD_UPDATED          = '\x976f8a9c5bdf8248dec172376d6e2b80a8e3df2f0328e381c6db8e1cf138c0f8'
TOPIC_PROPOSAL_APPROVED          = '\x5c819725ea53655a3b898f3df59b66489761935454e9212ca1e5ebd759953d0b'
TOPIC_PROPOSAL_REJECTED          = '\x55295d4ce992922fa2e5ffbf3a3dcdb367de0a15e125ace083456017fd22060f'
TOPIC_PROPOSAL_VOTED             = '\x1203f9e81c814a35f5f4cc24087b2a24c6fb7986a9f1406b68a9484882c93a23'
TOPIC_PROPOSAL_EXECUTED          = '\xe134987599ae266ec90edeff1b26125b287dbb57b10822649432d1bb26537fba'
TOPIC_PROPOSAL_CREATED           = '\xa57d40f1496988cf60ab7c9d5ba4ff83647f67d3898d441a3aaf21b651678fd9'
TOPIC_GLOBAL_PROPOSAL_CREATED    = '\x02609fcfd61fd5660d3bf2a95a0b4759688cfae1295f0b8d4510403bc83d9bd2'
-- V1 MainchainGateway (DEPRECATED)
TOPIC_V1_TOKEN_DEPOSITED         = '\x72848855a2461abf0dd243723dfcc9163eec2ea5215469d101c0d9c9ef58940d'
TOPIC_V1_TOKEN_WITHDREW          = '\x86174ea401f083b9bb1bdebca3068f27fb023c7091365ed2a8a02b8d75cf0e52'

-- ===== Selectors =====
-- MainchainGatewayV3
SEL_REQUEST_DEPOSIT_FOR          = '\x4b14557e'
SEL_SUBMIT_WITHDRAWAL            = '\x4d0d6673'
SEL_UNLOCK_WITHDRAWAL            = '\x9157921c'
SEL_MAP_TOKENS                   = '\x1b6e7594'
SEL_MAP_TOKENS_AND_THRESHOLDS    = '\xdff525e1'
SEL_SET_WRAPPED_NATIVE           = '\xd64af2a6'
SEL_PAUSE                        = '\x8456cb59'
SEL_UNPAUSE                      = '\x3f4ba83a'
SEL_DEPOSIT_COUNT                = '\x2dfdf0b5'
SEL_GET_RONIN_TOKEN              = '\xb2975794'
SEL_WITHDRAWAL_HASH              = '\x6932be98'
SEL_WITHDRAWAL_LOCKED            = '\x4d493f4e'
SEL_WRAPPED_NATIVE_TOKEN         = '\x17fcb39b'
SEL_DOMAIN_SEPARATOR             = '\x3644e515'
SEL_PAUSED                       = '\x5c975abb'
-- Proxy
SEL_UPGRADE_TO                   = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'
SEL_FUNCTION_DELEGATE_CALL       = '\x4bb5274a'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT               = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Ethereum (chain ID 1) — the ONLY chain with deployments =====
ETH_GATEWAY_V3                   = '\x64192819ac13ef72bf6b5ae239ac672b43a9af08'   -- proxy; impl 0x5019d41b…
ETH_GATEWAY_V3_IMPL_LIVE         = '\x5019d41b0737e39b51fd6da4859f3e27579e4e69'
ETH_BRIDGE_MANAGER_ACTIVE        = '\x2cf3cfb17774ce0cfa34bb3f3761904e7fc3fadb'   -- proxy in gateway admin slot; impl 0x0ac26945…
ETH_BRIDGE_MANAGER_DIRECT        = '\xa71456fa88a5f6a4696d0446e690db4a5913fab0'   -- repo record, direct (non-proxy)
ETH_GOVERNANCE_ADMIN             = '\xb255d6a720bb7c39fee173ce22113397119cb930'
ETH_PAUSE_ENFORCER               = '\xe514d9deb7966c8be0ca922de8a064264ea6bcd4'
ETH_TRUSTED_ORGANIZATION         = '\x7d0556d55ca1a92708681e2e231733ebd922597d'   -- proxy; impl 0x9be8bb3c…
ETH_V1_GATEWAY_DEPRECATED        = '\x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2'   -- custom proxy; impl 0x8407dc57…
ETH_WETH                         = '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
-- NOTE: NOT deployed on Base / BNB / Avalanche / Arbitrum / Optimism / Polygon (eth_getCode = 0x).
-- Counterparty leg (RoninGatewayV3, RoninBridgeManager, BridgeReward/Slash/Tracking) is on the Ronin chain, chainId 2020 (outside the seven).
```

---

## 10. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (keccak256), expanding the `Transfer.Receipt`/`Transfer.Request`/`ProposalDetail`/`GlobalProposalDetail` tuples to their full ABI form. Struct layouts taken from the canonical repo (`src/libraries/Transfer.sol`, `Token.sol`, `Proposal.sol`, `GlobalProposal.sol`).
- **Cross-checked against live `eth_getLogs`:** `Withdrew` `0x21e88e95…` confirmed on the gateway `0x6419…` in the last ~49k blocks (8 logs, `ntopics=1`, 384-B data — decoded to id/kind/mainchain-Owner/ronin-Owner/Info, ronin chainId = `0x7e4` = 2020). `DepositRequested` `0xd7b25068…` confirmed in block ~22.0M (683 logs, `ntopics=1`, 384-B data). V1 `TokenDeposited` `0x72848855…` + `TokenWithdrew` `0x86174ea4…` confirmed in historic block ~13.5M (24 856 + 7 376 logs, `ntopics=4`); `TokenWithdrew` signature recovered by brute-forcing candidate arg lists against the live topic0.
- **Selectors present in live impl:** PUSH4-scanned the live gateway impl `0x5019…4e69` bytecode — all §2.1/§2.2 selectors present except `receiveEther` (absent). Live `eth_call`: `depositCount()` = 111354, `paused()` = false, `wrappedNativeToken()` = WETH `0xc02a…56cc2`, `getRoninToken(WETH)` = `(0, 0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5)`.
- **Addresses:** parsed from the `axieinfinity/ronin-bridge-contracts` `deployments/ethereum/*.json` records (`MainchainGatewayV3Proxy`, `MainchainBridgeManager`, `MainchainGovernanceAdmin`, `MainchainGatewayPauseEnforcer`, `MainchainRoninTrustedOrganizationProxy`, `RoninTrustedOrganizationLogic`, `MainchainGatewayV2Logic`/`V3Logic`) and the official docs, then existence-checked via `eth_getCode` on `https://ethereum-rpc.publicnode.com` (all non-empty) and on the other six chains' publicnode RPCs (**all `0x`**).
- **Proxies:** EIP-1967 impl/admin slots read live via `eth_getStorageAt`. Gateway `0x6419…`: impl = `0x5019…4e69`, admin = `0x2cf3…fadb` (a `TransparentProxyV2` whose impl is `0x0ac2…22fd` MainchainBridgeManager). The repo's recorded gateway impl (`0x2dba…af73`) differs from the live impl → **impl rotated**. Direct contracts (`0xa714…`, `0xB255…`, `0xe514…`) have empty impl slots (confirmed not proxies). V1 `0x1a2a…` has empty EIP-1967 slots — a custom proxy with impl at storage slot 0x1 (`0x8407…2F21E`) and admin at slot 0x0.
- **Chain coverage:** `eth_getCode` for all seven gateway/manager/admin/pause/trusted-org/V1 addresses on all six non-Ethereum publicnode RPCs returned `0x` — confirming Ethereum-only L1 footprint. Counterparty leg on Ronin (chainId 2020) noted from the repo's `ronin`-side contract set; chain 2020 is outside the seven targets.

Authoritative sources:
- Canonical repos: [`axieinfinity/ronin-bridge-contracts`](https://github.com/axieinfinity/ronin-bridge-contracts) (branch `mainnet`, `deployments/ethereum/`, `src/mainchain/MainchainGatewayV3.sol`, `src/libraries/{Transfer,Token,Proposal,GlobalProposal}.sol`) · legacy [`axieinfinity/ronin-smart-contracts`](https://github.com/axieinfinity/ronin-smart-contracts) (V1)
- Official docs: [Ronin Bridge](https://docs.roninchain.com/apps/ronin-bridge) · [Withdraw an ERC-20 token](https://docs.roninchain.com/apps/ronin-bridge/withdraw-token)
- Explorers: [Etherscan — MainchainGatewayV3 proxy](https://etherscan.io/address/0x64192819Ac13Ef72bF6b5AE239AC672B43a9AF08) · [gateway impl](https://etherscan.io/address/0x5019d41b0737e39b51fd6da4859f3e27579e4e69) · [active BridgeManager](https://etherscan.io/address/0x2cf3cfb17774ce0cfa34bb3f3761904e7fc3fadb) · [V1 gateway](https://etherscan.io/address/0x1a2a1c938ce3ec39b6d47113c7955baa9dd454f2)
- Independent overview: [L2BEAT — Ronin bridge](https://l2beat.com/bridges/projects/ronin)

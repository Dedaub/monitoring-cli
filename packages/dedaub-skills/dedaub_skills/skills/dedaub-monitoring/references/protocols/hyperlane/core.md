# Hyperlane core (Mailbox, hooks, gas paymaster, ISMs) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the canonical `hyperlane-xyz/hyperlane-registry` (`chains/<chain>/addresses.yaml` and `metadata.yaml`, commit `09aa8356`, 2026-09-28) and `hyperlane-xyz/hyperlane-monorepo` (`solidity/contracts`, commit `c52b7280`, 2026-09-29). Topics and selectors recomputed as `keccak256(signature)` and matched against the deployed Ethereum implementation bytecode; addresses existence-checked with `eth_getCode`; proxy implementations and admins read from the EIP-1967 slots; wiring read with `eth_call`.
**Scope:** the permissionless messaging core that every Hyperlane transfer uses: **Mailbox** (dispatch and delivery), the post-dispatch hooks (**MerkleTreeHook**, **InterchainGasPaymaster**, ProtocolFee, PausableHook), the default ISM stack, **ValidatorAnnounce**, the **ProxyAdmin** and the **InterchainAccountRouter**. The registry has a core deployment on all eight target chains, including **Robinhood Chain (4663)**. The token layer (warp routes) is in [warp_routes.md](warp_routes.md). Topics and selectors are chain-agnostic; addresses are network-specific.

Hyperlane moves messages, not value. An app contract (a warp route, an interchain account router, any custom app) calls `Mailbox.dispatch`. The Mailbox emits `Dispatch` and `DispatchId`, then runs the required hook (ProtocolFee) and the default hook set (PausableHook, MerkleTreeHook, IGP). Off chain, validators sign the MerkleTreeHook root and a relayer calls `Mailbox.process` on the destination chain with the message and an ISM proof. The Mailbox emits `Process` and `ProcessId`, asks the recipient's ISM to verify, and calls `recipient.handle`. The value of a token transfer moves only inside the app (§0 of [warp_routes.md](warp_routes.md)).

Facts to know before indexing:

1. **The link key is `messageId`, on chain on both sides.** `messageId = keccak256(message)`. It is topic1 of `DispatchId` (source) and topic1 of `ProcessId` (destination). `Dispatch` and `Process` carry no `messageId`; pair each with its `DispatchId` / `ProcessId` in the same transaction.
2. **Hyperlane domain ids equal the chain ids on all eight target chains** (read live from `Mailbox.localDomain()`): 1, 8453, 42161, 10, 137, 56, 43114 and 4663. Non-EVM and app chains use other numbers (for example `solanamainnet` 1399811149, `katana` 747474).
3. **Addresses differ per chain.** There is no vanity address. The same literal address can be a different Hyperlane contract on another chain: `0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D` is the Base Mailbox and the Robinhood Chain ProxyAdmin; `0x748040afB89B8FdBb992799808215419d36A0930` is the Arbitrum MerkleTreeHook and the Polygon PausableHook. Key every contract on `(chain, address)`.
4. **The Mailbox is permissionless and deployed many times.** Other teams run their own Mailbox, with the same code and the same topics, outside the registry (§12). Allow-list the registry Mailbox of each chain.
5. **There is no refund, cancel or expiry path in the core.** A message that is not delivered stays pending. Anyone may retry `process` with valid metadata; anyone may top up gas with `payForGas`. The only "refund" is an app-level design.

---

## 0. Contract families & the message flow

| Contract | Role | Proxy? |
|----------|------|--------|
| **Mailbox** | `dispatch` (source) and `process` (destination). Emits the four message events. Holds no user funds. | **Yes**: TransparentUpgradeableProxy + ProxyAdmin |
| **MerkleTreeHook** | Inserts every dispatched `messageId` into an incremental Merkle tree that validators sign. | No |
| **InterchainGasPaymaster (IGP)** | Takes the native gas fee for the relayer (`GasPayment`). | **Yes**: TransparentUpgradeableProxy |
| ProtocolFee | The Mailbox `requiredHook()`: a flat protocol fee on every dispatch (0 unless set). | No |
| FallbackRoutingHook → AggregationHook | The Mailbox `defaultHook()`, which fans out to PausableHook + MerkleTreeHook + IGP. | No |
| PausableHook / PausableIsm | Emergency switches: a paused hook reverts dispatch; a paused ISM rejects delivery. | No |
| Default ISM | The Mailbox `defaultIsm()`: the security of every recipient that sets no ISM. | No (246-byte clone) |
| ValidatorAnnounce | Validators publish where their signed checkpoints live. | No |
| ProxyAdmin | Upgrades the Mailbox and IGP proxies. | No |
| InterchainAccountRouter | Interchain accounts: a remote caller's account executes calls. Governance of remote chains uses it. | No |
| QuotedCalls | Periphery router: Permit2 pulls and `transferRemote` with signed fee quotes. | No |

| Step | Chain | Call | Event(s), in log order | Value movement |
|------|-------|------|------------------------|----------------|
| Source leg | origin | app → `Mailbox.dispatch` | `Dispatch`, `DispatchId`, then the hooks: (`ProtocolFeePaid` on newer ProtocolFee), `InsertedIntoTree`, `GasPayment` | Native gas fee in `msg.value` to the IGP (and the ProtocolFee hook if set). App tokens move in the app, not here. |
| Security | off chain | validators sign `(root, index)` of the MerkleTreeHook | — | — |
| Destination leg | destination | relayer → `Mailbox.process(metadata, message)` | `Process`, `ProcessId`, then the recipient's own events | Whatever `recipient.handle` does (for a warp route: a release or a mint). |
| Gas top-up | origin | anyone → `IGP.payForGas` | `GasPayment` | Native value to the IGP. |
| Refund / cancel / expiry | — | none in the core | — | — |

**Message layout** (`message` in `Dispatch`, and the argument of `process`): `version` (1 byte, `3`) · `nonce` (4) · `origin` (4) · `sender` (32) · `destination` (4) · `recipient` (32) · `body`. In the `Dispatch` log data the message starts after two words (ABI offset and length). PostgreSQL `substring(data from N for M)` positions (1-based): version 65, nonce 66–69, origin 70–73, sender 74–105, destination 106–109, recipient 110–141, body from 142. A warp route body is `recipient` (32) · `amount` (32) · optional metadata, so the warp recipient is at 142–173 and the amount at 174–205.

**Domains of the eight target chains** (registry `metadata.yaml` `domainId`, confirmed by `localDomain()`):

| Chain | Chain id | Hyperlane domain | Registry name |
|-------|----------|------------------|---------------|
| Ethereum | 1 | 1 | `ethereum` |
| Base | 8453 | 8453 | `base` |
| Arbitrum One | 42161 | 42161 | `arbitrum` |
| Optimism | 10 | 10 | `optimism` |
| Polygon PoS | 137 | 137 | `polygon` |
| BNB Smart Chain | 56 | 56 | `bsc` |
| Avalanche C-Chain | 43114 | 43114 | `avalanche` |
| Robinhood Chain | 4663 | 4663 | `robinhood` (technical stack `arbitrumnitro`) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Mailbox (emitter = the Mailbox of each chain, §3–§10)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x769f711d20c679153d382254f59892613b58a97cc876b249134ac25c80f9c814` | `Dispatch(address indexed sender, uint32 indexed destination, bytes32 indexed recipient, bytes message)` | **Source leg (message).** `sender` = the app contract (warp route, ICA router), not the user. `message` = the full packed message. |
| `0x788dbc1b7152732178210e7f4d9d010ef016f9eafbe66786bd7169f56e0c353a` | `DispatchId(bytes32 indexed messageId)` | **Link key, source side.** `messageId = keccak256(message)`. Same transaction as `Dispatch`. |
| `0x0d381c2a574ae8f04e213db7cfb4df8df712cdbd427d9868ffef380660ca6574` | `Process(uint32 indexed origin, bytes32 indexed sender, address indexed recipient)` | **Destination leg (message delivered).** `sender` = the remote app contract. |
| `0x1cae38cdd3d3919489272725a5ae62a4f48b2989b0dae843d3c279fee18073a9` | `ProcessId(bytes32 indexed messageId)` | **Link key, destination side.** Equals the source `DispatchId`. |
| `0xa76ad0adbf45318f8633aa0210f711273d50fbb6fef76ed95bbae97082c75daa` | `DefaultIsmSet(address indexed module)` | Admin. Changes the security of every recipient that has no ISM of its own. **High severity.** |
| `0x65a63e5066ee2fcdf9d32a7f1bf7ce71c76066f19d0609dddccd334ab87237d7` | `DefaultHookSet(address indexed hook)` | Admin. |
| `0x329ec8e2438a73828ecf31a6568d7a91d7b1d79e342b0692914fd053d1a002b1` | `RequiredHookSet(address indexed hook)` | Admin. |

### 1.2 Hooks: MerkleTreeHook, InterchainGasPaymaster, ProtocolFee, pausable switches

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x253a3a04cab70d47c1504809242d9350cd81627b4f1d50753e159cf8cd76ed33` | `InsertedIntoTree(bytes32 messageId, uint32 index)` | MerkleTreeHook. Status only. Neither field is indexed: read `messageId` from data. |
| `0x65695c3748edae85a24cc2c60b299b31f463050bc259150d2e5802ec8d11720a` | `GasPayment(bytes32 indexed messageId, uint32 indexed destinationDomain, uint256 gasAmount, uint256 payment)` | InterchainGasPaymaster. Relayer fee in native token (`payment`, wei). Status for flow purposes. |
| `0x676a23191c2989bd7cc8446122cca792bcdaa0f2d6bbd9c30d8ca031ca946343` | `DestinationGasConfigSet(uint32 remoteDomain, address gasOracle, uint96 gasOverhead)` | IGP admin. |
| `0x68c3768caa3ad893fc625444f76bd4b04c6cbd8551951061c23ecd78fb220c88` | `TokenGasOracleSet(address indexed feeToken, uint32 remoteDomain, address gasOracle)` | IGP admin (ERC-20 fee tokens). |
| `0x8685397d4fa4489d21ed19c302e3719e5b1f0acd46b0ef39b3775f5bfa85b910` | `DestinationGasOverheadSet(uint32 indexed remoteDomain, uint256 gasOverhead)` | IGP admin. |
| `0x04d55a8be181fb8d75b76f2d48aa0b2ee40f47e53d6e61763eeeec46feea8a24` | `BeneficiarySet(address beneficiary)` | IGP admin (newer ProtocolFee hooks declare the same event, same topic0). |
| `0xb87e607f6030a23ed9b7dac1a717610f3a3b07325269f18808ba763bdcefe7ae` | `ProtocolFeePaid(address indexed sender, uint256 fee)` | ProtocolFee hook, newer deployments only (seen on Robinhood Chain). The Ethereum-era ProtocolFee bytecode has no fee event. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | PausableIsm / PausableHook. **A paused ISM stops delivery; a paused hook stops dispatch.** |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |

### 1.3 ValidatorAnnounce

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x78066d8adb677a1353d1fc8be28cf03e2a8de7157bbab979953587d78076c11e` | `ValidatorAnnouncement(address indexed validator, string storageLocation)` | Status only: where a validator publishes signed checkpoints. |

### 1.4 InterchainAccountRouter

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xa82f02bdb198e6cca80598e390600aa519d0f9efca0322efa45096af14fa2087` | `RemoteCallDispatched(uint32 indexed destination, address indexed owner, bytes32 router, bytes32 ism, bytes32 salt)` | Source side. Governance of remote Mailboxes uses this path. |
| `0x43c7c79901faab5ae18ac2369d6df969a28064bd40483d341f0dc439cb095d96` | `InterchainAccountCreated(address indexed account, uint32 origin, bytes32 router, bytes32 owner, address ism, bytes32 salt)` | Destination side, first use of an account. |
| `0xba9685b280b1e8f64909e2dfd7465463e6a0eabbaafd732402e7a619699a3821` | `RemoteIsmEnrolled(uint32 indexed domain, bytes32 ism)` | Router admin. |
| `0x2a1e0d9efb303f9faca2f4484ea37adc72e0e9bee4e0def3d691e302a8319260` | `CommitRevealDispatched(bytes32 indexed commitment)` | Commit-reveal calls. |

### 1.5 Ownership and proxies (every core contract)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Every Ownable core contract. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | TransparentUpgradeableProxy (Mailbox, IGP). **Implementation change.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | TransparentUpgradeableProxy admin (the ProxyAdmin) change. |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` | OpenZeppelin v4 initializer. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Mailbox

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfa31de01` | `dispatch(uint32 destinationDomain, bytes32 recipientAddress, bytes messageBody)` | Payable. Default hook, empty metadata. Returns `messageId`. Emits `Dispatch` + `DispatchId`. |
| `0x48aee8d4` | `dispatch(uint32 destinationDomain, bytes32 recipientAddress, bytes body, bytes hookMetadata)` | Payable. Default hook with metadata. |
| `0x10b83dc0` | `dispatch(uint32 destinationDomain, bytes32 recipientAddress, bytes body, bytes customHookMetadata, address customHook)` | Payable. Custom hook (warp routes use this overload). |
| `0x7c39d130` | `process(bytes metadata, bytes message)` | Destination. Called by a relayer (anyone). Verifies with the recipient's ISM, then calls `handle`. Emits `Process` + `ProcessId`. |
| `0xe495f1d4` | `delivered(bytes32 messageId)` | `bool`. True after `process`. |
| `0x5d1fe5a9` | `processor(bytes32 messageId)` | `address` that delivered the message. |
| `0x07a2fda1` | `processedAt(bytes32 messageId)` | `uint48` block number of delivery. |
| `0x9c42bd18` | `quoteDispatch(uint32 destinationDomain, bytes32 recipientAddress, bytes messageBody)` | `uint256` native fee. |
| `0x8d3638f4` | `localDomain()` | `uint32`. Equals the chain id on all eight target chains. |
| `0xaffed0e0` | `nonce()` | `uint32`. Count of messages dispatched by this Mailbox. |
| `0x134fbb4f` | `latestDispatchedId()` | `bytes32`. |
| `0x6e5f516e` | `defaultIsm()` | `address`. |
| `0x3d1250b7` | `defaultHook()` | `address`. |
| `0xd6d08a09` | `requiredHook()` | `address`. |
| `0xe70f48ac` | `recipientIsm(address recipient)` | `address`. The ISM that `process` will use for this recipient. |
| `0xf794687a` | `setDefaultIsm(address module)` | Owner. Emits `DefaultIsmSet`. |
| `0x99b04809` | `setDefaultHook(address hook)` | Owner. Emits `DefaultHookSet`. |
| `0x1426b7f4` | `setRequiredHook(address hook)` | Owner. Emits `RequiredHookSet`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner. Emits `OwnershipTransferred`. |

### 2.2 Hooks and ISMs

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x086011b9` | `postDispatch(bytes metadata, bytes message)` | Hook entry point, called by the Mailbox. |
| `0xaaccd230` | `quoteDispatch(bytes metadata, bytes message)` | Hook fee quote. |
| `0x06661abd` | `count()` | MerkleTreeHook `uint32`: leaves in the tree. |
| `0xebf0c717` | `root()` | MerkleTreeHook `bytes32`. |
| `0x907c0f92` | `latestCheckpoint()` | MerkleTreeHook `(bytes32 root, uint32 index)`: what validators sign. |
| `0x11bf2c18` | `payForGas(bytes32 messageId, uint32 destinationDomain, uint256 gasAmount, address refundAddress)` | IGP. Payable. Also callable directly to top up a stuck message. Emits `GasPayment`. |
| `0xa6929793` | `quoteGasPayment(uint32 destinationDomain, uint256 gasAmount)` | IGP `uint256` wei. |
| `0x4e71d92d` | `claim()` | IGP. Sends the collected native fees to `beneficiary()`. |
| `0x1c31f710` | `setBeneficiary(address beneficiary)` | IGP / ProtocolFee owner. |
| `0x48f4e6c1` | `setDestinationGasConfigs((uint32 remoteDomain, (address gasOracle, uint96 gasOverhead) config)[] configs)` | IGP owner. Emits `DestinationGasConfigSet`. |
| `0x38af3eed` | `beneficiary()` | `address`. |
| `0x8456cb59` | `pause()` | PausableIsm / PausableHook owner. Emits `Paused`. |
| `0x3f4ba83a` | `unpause()` | Owner. Emits `Unpaused`. |
| `0x5c975abb` | `paused()` | `bool`. |
| `0xf7e83aee` | `verify(bytes metadata, bytes message)` | ISM entry point, called by the Mailbox during `process`. |
| `0x6465e69f` | `moduleType()` | ISM `uint8` type. |
| `0x37b02c28` | `hooks(bytes message)` | AggregationHook `address[]`: the hooks it calls. |
| `0x6f72df75` | `modulesAndThreshold(bytes message)` | Aggregation ISM `(address[] modules, uint8 threshold)`. |

### 2.3 ValidatorAnnounce and InterchainAccountRouter

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x21f71781` | `announce(address validator, string storageLocation, bytes signature)` | ValidatorAnnounce. Permissionless with the validator's signature. Emits `ValidatorAnnouncement`. |
| `0x690cb786` | `getAnnouncedValidators()` | `address[]`. |
| `0x51abe7cc` | `getAnnouncedStorageLocations(address[] validators)` | `string[][]`. |
| `0xdd91cc87` | `callRemote(uint32 destination, (bytes32 to, uint256 value, bytes data)[] calls)` | ICA router. Payable. Executes `calls` from the caller's interchain account on `destination`. Emits `RemoteCallDispatched`. |
| `0x5c60da1b` | `implementation()` | ICA router `address`: the template that every interchain account clones (EIP-1167). |

### 2.4 ProxyAdmin (OpenZeppelin v4)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | ProxyAdmin owner. Emits `Upgraded` on the proxy. |
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | ProxyAdmin owner. |
| `0x7eff275e` | `changeProxyAdmin(address proxy, address newAdmin)` | ProxyAdmin owner. Emits `AdminChanged`. |
| `0x204e1c7a` | `getProxyImplementation(address proxy)` | `address`. |
| `0xf3b7dead` | `getProxyAdmin(address proxy)` | `address`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

From the registry `chains/ethereum/addresses.yaml`; all existence-checked with `eth_getCode` on 2026-09-29. `nonce()` = 286,240 messages dispatched. Pinned window: `Dispatch` 148, `Process` 150, `InsertedIntoTree` 148, `GasPayment` 148.

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0xc005dc82818d67AF737725bD4bf75435d065D239` | Dispatch and process. `localDomain()` = 1. Impl `0x7b4d881c122a5e61adcffb56a2e3ce9927d53455`. |
| **MerkleTreeHook** | `0x48e6c30B97748d1e2e03bf3e9FbE3890ca5f8CCA` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0x9e6B1022bE9BBF5aFd152483DAD9b88911bC8611` | Emits `GasPayment`. Impl `0xb6b16b5eede90e93c8e558f49effb06193b04edf`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0x8B05BF30F6247a90006c5837eA63C7905D79e6d8` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0x571f1435613381208477ac5d6974310d88AC7cB7` | Routes to the aggregation hook by default. |
| AggregationHook | `0x3d166d2424e47747D81bd71A305A8aee23d33397` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0x3A66Dc852e56d3748838b3C27CF381105b83705b` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0xDD0998A3533b137a3520bca7c0Fb0b4F5886Ae82` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0xDC98a856fb9112894c2fE32267DA8bF35645FAF3` | Emergency ISM switch. |
| ValidatorAnnounce | `0xCe74905e51497b4adD3639366708b821dcBcff96` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0x75EE15Ee1B4A75Fa3e2fDF5DF3253c25599cc659` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0xC00b94c115742f711a6F9EA90373c33e9B72A4A9` | Interchain accounts; remote governance path. |
| QuotedCalls | `0xe38E2E3B4d9Aef4556e62e4D2B1e6Fc155bCc985` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox and ProxyAdmin `owner()` | `0x562dfaac27a84be6c96273f5c9594da1681c0da7` | Safe (171-byte proxy; threshold 6). |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | The same EOA on every chain; on Ethereum it carries an EIP-7702 delegation (`0xef0100` + `0x63c0c19a282a1b52b07dd5a65b58948a07dae32b`). |

## 4. Addresses — Base (chain ID 8453)

From `chains/base/addresses.yaml`. `nonce()` = 2,183,971. Pinned window: `Dispatch` 206, `Process` 224, `InsertedIntoTree` 206, `GasPayment` 196.

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D` | Dispatch and process. `localDomain()` = 8453. Impl `0x2f2afae1139ce54fefc03593fee8ab2adf4a85a7`. |
| **MerkleTreeHook** | `0x19dc38aeae620380430C200a6E990D5Af5480117` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0xc3F23848Ed2e04C0c6d41bd7804fa8f89F940B94` | Emits `GasPayment`. Impl `0x0e025067fe1a009e39f9c3de6a9965ee1eaeb2d2`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0x99ca8c74cE7Cfa9d72A51fbb05F9821f5f826b3a` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0x4Eb82Ee35b0a1c1d776E3a3B547f9A9bA6FCC9f2` | Routes to the aggregation hook by default. |
| AggregationHook | `0x08Aa6263078ddC6139F8EAB59D838C17bf555e93` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0x46fa3A5780e5B90Eaf34BDED554d5353B5ABE9E7` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0x0C53271f445D5f0Cd1C7388f04A8C2EC55cf88b9` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0x2AF32cF8e3Cf42d221eDa0c843818fA5ee129E27` | Emergency ISM switch. |
| ValidatorAnnounce | `0x182E8d7c5F1B06201b102123FC7dF0EaeB445a7B` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0x4Ed7d626f1E96cD1C0401607Bf70D95243E3dEd1` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0x44647Cd983E80558793780f9a0c7C2aa9F384D07` | Interchain accounts; remote governance path. |
| QuotedCalls | `0xa9f0a79433Cd2A0c483586C8c50627577f16F16e` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox and ProxyAdmin `owner()` | `0x890ac177fe3052b8676a65f32c1589bc329f3d50` | Safe (171-byte proxy); the same address owns Optimism. |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | EOA, nonce 9,794. |

## 5. Addresses — Arbitrum One (chain ID 42161)

From `chains/arbitrum/addresses.yaml`. `nonce()` = 2,515,027. Pinned window: `Dispatch` 153, `Process` 141, `InsertedIntoTree` 153, `GasPayment` 153. The ProxyAdmin sits behind a 7-day timelock (unlike the other chains).

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0x979Ca5202784112f4738403dBec5D0F3B9daabB9` | Dispatch and process. `localDomain()` = 42161. Impl `0x4826ce713944d8b3eb98c73050bfc01e8fb6655a`. |
| **MerkleTreeHook** | `0x748040afB89B8FdBb992799808215419d36A0930` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0x3b6044acd6767f017e99318AA6Ef93b7B06A5a22` | Emits `GasPayment`. Impl `0x2ebfe904ccbc143ac0a0c03250459aa7140ba09d`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0xD0199067DACb8526e7dc524a9a7DCBb57Cd25421` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0x9e8fFb1c26099e75Dd5D794030e2E9AA51471c25` | Routes to the aggregation hook by default. |
| AggregationHook | `0x5A477c362106FC6E25785C4C611fB8c27CA3140f` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0xEf30f29Dcd3FCB1DCcDA9C7Cbf2A5957E8Ee9Cc3` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0x9E1cB2258BaCBb5fe36CCcC5b5F9a7fD8dEC2051` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0x1E38556b4fE553e6249448960875883990efcf34` | Emergency ISM switch. |
| ValidatorAnnounce | `0x1df063280C4166AF9a725e3828b4dAC6c7113B08` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0x80Cebd56A65e46c474a1A101e89E76C4c51D179c` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0xF90A3d406C6F8321fe118861A357F4D7107760D7` | Interchain accounts; remote governance path. |
| QuotedCalls | `0xBfdB4056C49680dd54eedEf22C7F48308140a2a2` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox `owner()` | `0x7379d7bb2cca68982e467632b6554fd4e72e9431` | Safe (171-byte proxy); the same address owns BNB. |
| ProxyAdmin `owner()` | `0xac98b0cd1b64ea4fe133c6d2edaf842ce5cf4b01` | TimelockController, `getMinDelay()` = 604,800 s (7 days). |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | EOA, nonce 12,275. |

## 6. Addresses — Optimism (chain ID 10)

From `chains/optimism/addresses.yaml`. `nonce()` = 1,662,183. Pinned window: `Dispatch` 50, `Process` 62, `InsertedIntoTree` 50, `GasPayment` 52.

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0xd4C1905BB1D26BC93DAC913e13CaCC278CdCC80D` | Dispatch and process. `localDomain()` = 10. Impl `0xf00824861e4bfe5dfc769295a50006ba203bbc29`. |
| **MerkleTreeHook** | `0x68eE9bec9B4dbB61f69D9D293Ae26a5AACb2e28f` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0xD8A76C4D91fCbB7Cc8eA795DFDF870E48368995C` | Emits `GasPayment`. Impl `0x69d1a90f1a6ce003e993678ac8d19717454d1467`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0xD71Ff941120e8f935b8b1E2C1eD72F5d140FF458` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0xD4b132C6d4AA93A4247F1A91e1ED929c0572a43d` | Routes to the aggregation hook by default. |
| AggregationHook | `0xb959001ec9706d56fC7787e126caC2Ad3a7158a7` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0xf753CA2269c8A7693ce1808b5709Fbf36a65D47A` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0x5EBdc44365FEb72ab99FE76Bdd0c47D0bd674c21` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0xD84D8114cCfa5c2403E56aBf754da529430704F0` | Emergency ISM switch. |
| ValidatorAnnounce | `0x30f5b08e01808643221528BB2f7953bf2830Ef38` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0xE047cb95FB3b7117989e911c6afb34771183fC35` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0x3E343D07D024E657ECF1f8Ae8bb7a12f08652E75` | Interchain accounts; remote governance path. |
| QuotedCalls | `0x7C03e17eEDE243913E126D620f4c10Fe4E104245` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox and ProxyAdmin `owner()` | `0x890ac177fe3052b8676a65f32c1589bc329f3d50` | Safe (171-byte proxy); the same address owns Base. |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | EOA, nonce 9,074. |

## 7. Addresses — Polygon PoS (chain ID 137)

From `chains/polygon/addresses.yaml`. `localDomain()` = 137 (read live); `nonce()` = 446,574. Pinned window: `Dispatch` 85, `Process` 19, `InsertedIntoTree` 85, `GasPayment` 86. `0x748040afB89B8FdBb992799808215419d36A0930` here is the PausableHook; the same literal address is the Arbitrum MerkleTreeHook.

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0x5d934f4e2f797775e53561bB72aca21ba36B96BB` | Dispatch and process. `localDomain()` = 137. Impl `0xa3ae1c7dbac1c9658708e6acd271bfb93d87f8a3`. |
| **MerkleTreeHook** | `0x73FbD25c3e817DC4B4Cd9d00eff6D83dcde2DfF6` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0x0071740Bf129b05C4684abfbBeD248D80971cce2` | Emits `GasPayment`. Impl `0xf0a2d22c7064e9f5e6c7990cea999a57ec2d0f80`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0xF8F3629e308b4758F8396606405989F8D8C9c578` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0xca4cCe24E7e06241846F5EA0cda9947F0507C40C` | Routes to the aggregation hook by default. |
| AggregationHook | `0xC120b70D088b1F27F4bE61f0d84354B9C4f3794A` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0x748040afB89B8FdBb992799808215419d36A0930` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0x5170d59EfD37941CB6E5905b9bc612a511eEc36E` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0x6741e91fFDC31c7786E3684427c628dad06299B0` | Emergency ISM switch. |
| ValidatorAnnounce | `0x454E1a1E1CA8B51506090f1b5399083658eA4Fc5` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0xC4F7590C5d30BE959225dC75640657954A86b980` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0xd8B641FEb587844854aeC97544ccEA426DFF04a3` | Interchain accounts; remote governance path. |
| QuotedCalls | `0x74e134E2b52f126336fa2C50B01357DabCA3d636` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox and ProxyAdmin `owner()` | `0x20e52e3bedf7bd305ca816dc54a0835d3bded820` | Interchain account (EIP-1167 clone of the ICA router's `implementation()` `0x793048efcc96051ef03ec03b1abcfce483b6facc`): governed by messages from another chain. |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | EOA, nonce 16,228. |

## 8. Addresses — BNB Smart Chain (chain ID 56)

From `chains/bsc/addresses.yaml`. `nonce()` = 420,279. Pinned window: `Dispatch` 76, `Process` 102, `InsertedIntoTree` 76, `GasPayment` 69.

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0x2971b9Aec44bE4eb673DF1B88cDB57b96eefe8a4` | Dispatch and process. `localDomain()` = 56. Impl `0xbfa300164a04437d64afda390736e6dc45096da1`. |
| **MerkleTreeHook** | `0xFDb9Cd5f9daAA2E4474019405A328a88E7484f26` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0x78E25e7f84416e69b9339B0A6336EB6EFfF6b451` | Emits `GasPayment`. Impl `0x284830a64e59cf85e46ba66744b2910cb4bd9f90`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0xA8Aa5f14a5463a78E45CC068F11c867949F3E367` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0x237E81f87F57Badad9e09f13CC676D986cA852e7` | Routes to the aggregation hook by default. |
| AggregationHook | `0x21eAB98931d66078fEdb538071e96a7a1c41C041` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0x7DBdAd1b4A922B65d37d7258a4227b6658344b7f` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0x9Ec844699657B983C529382B0f00A605a53ed600` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0x25dB01caDf91CfD2f7e6dD829Ce81698217F9151` | Emergency ISM switch. |
| ValidatorAnnounce | `0x7024078130D9c2100fEA474DAD009C2d1703aCcd` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0x65993Af9D0D3a64ec77590db7ba362D6eB78eF70` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0xf453B589F0166b90e050691EAc281C01a8959897` | Interchain accounts; remote governance path. |
| QuotedCalls | `0xAD8C3E1fE3C7deeDdA1A79A9a6A64607A65eD456` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox and ProxyAdmin `owner()` | `0x7379d7bb2cca68982e467632b6554fd4e72e9431` | Safe (171-byte proxy); the same address owns Arbitrum. |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | EOA, nonce 12,154. |

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

From `chains/avalanche/addresses.yaml`. `nonce()` = 71,890. Pinned window: `Dispatch` 0, `Process` 1, `InsertedIntoTree` 0, `GasPayment` 0 (the Mailbox is deployed and delivered one message; the window saw no dispatch).

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0xFf06aFcaABaDDd1fb08371f9ccA15D73D51FeBD6` | Dispatch and process. `localDomain()` = 43114. Impl `0xac6dfcac1b0ed0dbe0e4836a1158263a24e8d896`. |
| **MerkleTreeHook** | `0x84eea61D679F42D92145fA052C89900CBAccE95A` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0x95519ba800BBd0d34eeAE026fEc620AD978176C0` | Emits `GasPayment`. Impl `0xc0d0ef8d8bdd7395ec02617d1c705b0c6a60d6fa`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0xEc4AdA26E51f2685279F37C8aE62BeAd8212D597` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0x61D15D571D5f7A9eF0D1938f072f430bBF024747` | Routes to the aggregation hook by default. |
| AggregationHook | `0x9d801C447cDE0fb79F4EFa15aA2eE123021347DF` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0x239eB860770F1C48ABAC9bE9825d20e3E7c018df` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0x55Bc1127983265704474f0715Dec3A32274Bfd27` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0xd76080269C641e1adb786b72ae60Ddac3b6b8ed0` | Emergency ISM switch. |
| ValidatorAnnounce | `0x9Cad0eC82328CEE2386Ec14a12E81d070a27712f` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0xd7CF8c05fd81b8cA7CfF8E6C49B08a9D63265c9B` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0x2c58687fFfCD5b7043a5bF256B196216a98a6587` | Interchain accounts; remote governance path. |
| QuotedCalls | `0xBbACDe54180D309748Ef9326EA4951A64C05260F` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox and ProxyAdmin `owner()` | `0x66c21cfa8b765318a458435519a31a5cf0f7ae4b` | Interchain account (EIP-1167 clone of the ICA router's `implementation()` `0x93dae3582db0bbd6b158f94ea81a230a47627b89`): governed by messages from another chain. |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | EOA, nonce 7,364. |

## 10. Addresses — Robinhood Chain (chain ID 4663)

From `chains/robinhood/addresses.yaml` (registry `domainId` 4663, `technicalStack: arbitrumnitro`). `nonce()` = 112: the deployment is new. `PACKAGE_VERSION()` = `11.3.1` on the Mailbox implementation (the older implementations on the other chains do not expose it). The proxies use a newer 2,840-byte TransparentUpgradeableProxy. Pinned window: `Dispatch` 1, `Process` 0, `InsertedIntoTree` 1, `GasPayment` 0. **`0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D` here is the ProxyAdmin, not a Mailbox** (it is the Mailbox on Base). No registry warp route lists Robinhood Chain ([warp_routes.md](warp_routes.md) §10).

| Role | Address | One-liner |
|------|---------|-----------|
| **Mailbox** (proxy) | `0x3a867fCfFeC2B790970eeBDC9023E75B0a172aa7` | Dispatch and process. `localDomain()` = 4663. Impl `0x3a464f746d23ab22155710f44db16dca53e0775e`. |
| **MerkleTreeHook** | `0xF16E63B42Df7f2676B373979120BBf7e6298F473` | Emits `InsertedIntoTree`. Not a proxy. |
| **InterchainGasPaymaster** (proxy) | `0x3862A9B1aCd89245a59002C2a08658EC1d5690E3` | Emits `GasPayment`. Impl `0x7927b6fe8fa061c32ce3771d11076e6161de5f52`. |
| ProtocolFee (Mailbox `requiredHook()`) | `0x1e4dE25C3b07c8DF66D4c193693d8B5f3b431d51` | Runs on every dispatch. |
| FallbackRoutingHook (Mailbox `defaultHook()`) | `0x5B24EE24049582fF74c1d311d72c70bA5B76a554` | Routes to the aggregation hook by default. |
| AggregationHook | `0xb1502A527eFB688708a24c390Cd9AD274F35B917` | The default hook set: PausableHook + MerkleTreeHook + IGP of this chain (read with `hooks(bytes)`). |
| PausableHook | `0xa377b8269e0A47cdd2fD5AAeAe860b45623c6d82` | `pause()` stops default-hook dispatches. |
| Default ISM (Mailbox `defaultIsm()`) | `0xbFb0Ce32bCE0e5Aee5bF5C9b97Ec127Ffd8aa0c9` | Static aggregation ISM (246-byte clone). |
| PausableIsm | `0xE350143242a2F7962F23D71ee9Dd98f6e86D1772` | Emergency ISM switch. |
| ValidatorAnnounce | `0x2D374F85AE2B80147CffEb34d294ce02d1afd4D8` | Emits `ValidatorAnnouncement`. |
| ProxyAdmin | `0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D` | Admin of the Mailbox and IGP proxies. |
| InterchainAccountRouter | `0xf2755AE2A6f3b49FeE5d6CCF5C7C60eC06a45200` | Interchain accounts; remote governance path. |
| QuotedCalls | `0xf6092016a7bef22F7aC9C982C9E96D968F709C05` | Periphery command router (Permit2 pulls, `transferRemote` with signed quotes). |
| Mailbox and ProxyAdmin `owner()` | `0x0e7e5d38695d7939303244ad56ace1eea263dce8` | Interchain account (EIP-1167 clone of the ICA router's `implementation()` `0x0dbabdd6cf7a1ade655bfb1dbd305181d5dd8f95`). |
| IGP `owner()` and `beneficiary()` — EOA | `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba` | EOA, nonce 630. |

---

## 11. Cross-chain summary

| Chain | ID = domain | Mailbox | MerkleTreeHook | InterchainGasPaymaster | Mailbox owner | `Dispatch` / `Process` in the pinned window |
|-------|-------------|---------|----------------|------------------------|---------------|---------------------------------------------|
| Ethereum | 1 | `0xc005dc82818d67AF737725bD4bf75435d065D239` | `0x48e6c30B97748d1e2e03bf3e9FbE3890ca5f8CCA` | `0x9e6B1022bE9BBF5aFd152483DAD9b88911bC8611` | Safe | 148 / 150 |
| Base | 8453 | `0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D` | `0x19dc38aeae620380430C200a6E990D5Af5480117` | `0xc3F23848Ed2e04C0c6d41bd7804fa8f89F940B94` | Safe | 206 / 224 |
| Arbitrum One | 42161 | `0x979Ca5202784112f4738403dBec5D0F3B9daabB9` | `0x748040afB89B8FdBb992799808215419d36A0930` | `0x3b6044acd6767f017e99318AA6Ef93b7B06A5a22` | Safe (+ 7-day timelock on the ProxyAdmin) | 153 / 141 |
| Optimism | 10 | `0xd4C1905BB1D26BC93DAC913e13CaCC278CdCC80D` | `0x68eE9bec9B4dbB61f69D9D293Ae26a5AACb2e28f` | `0xD8A76C4D91fCbB7Cc8eA795DFDF870E48368995C` | Safe | 50 / 62 |
| Polygon PoS | 137 | `0x5d934f4e2f797775e53561bB72aca21ba36B96BB` | `0x73FbD25c3e817DC4B4Cd9d00eff6D83dcde2DfF6` | `0x0071740Bf129b05C4684abfbBeD248D80971cce2` | Interchain account | 85 / 19 |
| BNB Smart Chain | 56 | `0x2971b9Aec44bE4eb673DF1B88cDB57b96eefe8a4` | `0xFDb9Cd5f9daAA2E4474019405A328a88E7484f26` | `0x78E25e7f84416e69b9339B0A6336EB6EFfF6b451` | Safe | 76 / 102 |
| Avalanche C-Chain | 43114 | `0xFf06aFcaABaDDd1fb08371f9ccA15D73D51FeBD6` | `0x84eea61D679F42D92145fA052C89900CBAccE95A` | `0x95519ba800BBd0d34eeAE026fEc620AD978176C0` | Interchain account | 0 / 1 |
| Robinhood Chain | 4663 | `0x3a867fCfFeC2B790970eeBDC9023E75B0a172aa7` | `0xF16E63B42Df7f2676B373979120BBf7e6298F473` | `0x3862A9B1aCd89245a59002C2a08658EC1d5690E3` | Interchain account | 1 / 0 |

All eight chains have the full core set (§3–§10). The registry also lists the core on many chains outside the eight (Solana, Katana, HyperEVM and others); they appear here only as message origins and destinations.

---

## 12. Other Mailbox instances (independent deployments, not in the registry)

The Mailbox is permissionless: other teams deploy the same contract with their own validators and relayers. These instances emit the same four topics. Each address below is a TransparentUpgradeableProxy whose `localDomain()` returns the chain id; on Ethereum the explorer names every implementation `Mailbox`. Counts are `Dispatch` / `Process` in the pinned window.

| Chain | Mailbox | Implementation | `Dispatch` / `Process` | Warp routes seen on it |
|-------|---------|----------------|------------------------|------------------------|
| Ethereum | `0x599899e6b3b1362ba2460d125756a738ec1592d6` | `0x5a197a5f488fc9ff4c5d4c2af7884e974b51256b` | 5 / 3 | — |
| Polygon | `0x599899e6b3b1362ba2460d125756a738ec1592d6` (same address) | `0x5a197a5f488fc9ff4c5d4c2af7884e974b51256b` | **8,190 / 1,667** | — |
| BNB | `0x599899e6b3b1362ba2460d125756a738ec1592d6` (same address) | `0x5a197a5f488fc9ff4c5d4c2af7884e974b51256b` | 802 / 735 | — |
| Ethereum | `0x82a729a4c7b2aebddbfccf533e7b75c61c45c23c` | `0x935aa587ff3fa7c507c63e52ff814157eeee6088` | 5 / 5 | `0x81c2813aa88f66bca1e55838045aaceb72febfc1` |
| Ethereum | `0x287cf56e5b1435ae59bf9ce6443f055a0321a063` | `0x2ede6bb35eeff2ea1338fbc4183689359cbd5cb8` | 3 / 2 | `0x01f80bb8e78e79881e8ec7832fb6c2c59f64e353` |
| Ethereum | `0xa9abc828378c9decd6268e6ddf298914ecba59cb` | `0x712dfc1e81fb724b8215fd8bbbc2a53af35e44fe` | 1 / 6 | `0x39510fd11b2d9926f94204f35c665d2146e03d03`, `0x6d785ea3102d40a4e094c93c8bb2fe31e292e1b2` (USDT), `0x09ac387ae044f45eeb5d615f7c64dfb40f68c29c` (USDC) |
| Ethereum | `0x1aea57049cc962b0b1ad5efdca2c99a62be3ee71` | `0x450dc886979ccda23885b3125fab816d69dffaaa` | 1 / 1 | — |
| Base | `0xfdd96df1b2d4354dbb1070815819db47469ca470` | `0xd58489d491e4b2f6872e3c0cc7b88dd479b0b159` | 8 / 14 | `0x54716a535c3b5616e3f0d4d5005fc4bb660cdf5f` (USDC) |
| Base | `0x63283d920072bae615bb80ae6a4868eb621e41b8` | `0x6c86742311b6f33055691197232652b76a72e38e` | 3 / 7 | — |
| BNB | `0x15eecb285aae883fcff1c3f38552eb9d64ebcb7d` | `0x90d60e33e0dbfdc091431f372cff28e098cb10c6` | 5 / 0 | — |
| BNB | `0xa39ed40afad71686212bd99549c653612b6230a4` | `0x8b90373e62f189c16460d3e3ffce58180461bd68` (708-byte proxy) | 3 / 3 | — |

These are leads for attribution, not Hyperlane-operated infrastructure: the registry does not list them, and their security is whatever ISM their owners set. Each has its own MerkleTreeHook, so `InsertedIntoTree` also comes from contracts outside §3–§10.

---

## 13. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Mailbox** (all eight) | TransparentUpgradeableProxy (2,555-byte runtime on seven chains; 2,840-byte on Robinhood Chain) | EIP-1967 impl slot = the implementation in §3–§10; admin slot = the chain's ProxyAdmin (read on every chain). | ProxyAdmin `owner()`: a Safe on Ethereum, Base, Optimism and BNB; a TimelockController (7 days) on Arbitrum; an interchain account on Polygon, Avalanche and Robinhood Chain. The Mailbox's own `owner()` (ISM and hook setters) is the same account, except on Arbitrum (the Safe). |
| **InterchainGasPaymaster** (all eight) | TransparentUpgradeableProxy | Admin slot = the same ProxyAdmin as the Mailbox. | ProxyAdmin owner for upgrades; the IGP `owner()` for gas configs is the EOA `0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba`. |
| MerkleTreeHook, ProtocolFee, FallbackRoutingHook, AggregationHook, PausableHook, PausableIsm, ValidatorAnnounce, ProxyAdmin, InterchainAccountRouter, QuotedCalls | Not proxies | Full runtime bytecode, no EIP-1967 implementation. | `owner()` per contract where Ownable. A new version = a new address set in the registry. |
| Default ISM, aggregation hook | Minimal clones with immutable arguments (246 / 278 bytes) | Factory-made, immutable. | Replaced through `setDefaultIsm` / `setDefaultHook` on the Mailbox. |
| DomainRoutingIsm | EIP-1167 clone (45 bytes) | Delegates to a per-chain implementation. | `owner()`. |

Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` and `AdminChanged` on the Mailbox and IGP proxies, and `DefaultIsmSet` / `DefaultHookSet` / `RequiredHookSet` on the Mailbox. Proxy slots: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`.

---

## 14. Detection invariants & gotchas

1. **Join on `messageId`.** Source: `DispatchId` topic1. Destination: `ProcessId` topic1. The two id events sit next to `Dispatch` / `Process` in the same transaction. The key is on chain on both sides; no API is needed.
2. **`Dispatch.sender` and `Process.recipient` are contracts.** For a token transfer they are the warp routes. The end user is in the app payload (for a warp route: the body at data positions 142–205, §0) or in the app's own event.
3. **Message counts do not balance per chain.** In the pinned window Ethereum dispatched 148 and processed 150; Polygon dispatched 85 and processed 19. Deliveries arrive from every origin, including chains outside the eight.
4. **Most Mailbox traffic is not a token transfer.** Interchain accounts, governance and custom apps also dispatch. Classify a message by `sender`/`recipient` (a known warp route) or by the warp event in the same transaction.
5. **Independent Mailboxes share every topic** (§12). The busiest emitter of `Dispatch` on Polygon in the window was not the registry Mailbox (8,190 against 85). Filter on the registry Mailbox address of the chain, or accept the others knowingly.
6. **`InsertedIntoTree` and `GasPayment` are hook status events.** They repeat the `messageId`, move no app value, and may be missing: a route with a custom hook can skip the default hook set, and `GasPayment` also fires on later top-ups.
7. **No refund path exists in the core.** A message whose delivery fails stays undelivered (`delivered(messageId)` = false). Retries are new `process` calls; a revert leaves no event. Monitor stuck value by messages that have a `DispatchId` and no `ProcessId` after a time bound.
8. **Admin triggers.** `DefaultIsmSet` (changes the security of most apps at once), `RequiredHookSet`, `DefaultHookSet`, `Upgraded` / `AdminChanged` on the Mailbox and IGP, `Paused` on the PausableHook (stops default dispatches) or the PausableIsm, and `OwnershipTransferred` on any core contract.
9. **Remote chains are governed by messages.** On Polygon, Avalanche and Robinhood Chain the Mailbox owner is an interchain account. An admin action there is a `process` call whose recipient is the InterchainAccountRouter, not a local multisig transaction.
10. **The same literal address can be different contracts on different chains** (see the facts above). Never reuse an address across chains without `(chain, address)`.
11. **The IGP owner is one EOA on every chain** (`0xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba`, EIP-7702-delegated on Ethereum). It can change gas oracles and the beneficiary, and `claim()` sends the collected fees to it.

---

## 15. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Mailbox topics =====
TOPIC_DISPATCH                   = '\x769f711d20c679153d382254f59892613b58a97cc876b249134ac25c80f9c814'
TOPIC_DISPATCH_ID                = '\x788dbc1b7152732178210e7f4d9d010ef016f9eafbe66786bd7169f56e0c353a'
TOPIC_PROCESS                    = '\x0d381c2a574ae8f04e213db7cfb4df8df712cdbd427d9868ffef380660ca6574'
TOPIC_PROCESS_ID                 = '\x1cae38cdd3d3919489272725a5ae62a4f48b2989b0dae843d3c279fee18073a9'
TOPIC_DEFAULT_ISM_SET            = '\xa76ad0adbf45318f8633aa0210f711273d50fbb6fef76ed95bbae97082c75daa'
TOPIC_DEFAULT_HOOK_SET           = '\x65a63e5066ee2fcdf9d32a7f1bf7ce71c76066f19d0609dddccd334ab87237d7'
TOPIC_REQUIRED_HOOK_SET          = '\x329ec8e2438a73828ecf31a6568d7a91d7b1d79e342b0692914fd053d1a002b1'
-- ===== Hook, ISM and ValidatorAnnounce topics =====
TOPIC_INSERTED_INTO_TREE         = '\x253a3a04cab70d47c1504809242d9350cd81627b4f1d50753e159cf8cd76ed33'
TOPIC_GAS_PAYMENT                = '\x65695c3748edae85a24cc2c60b299b31f463050bc259150d2e5802ec8d11720a'
TOPIC_DESTINATION_GAS_CONFIG_SET = '\x676a23191c2989bd7cc8446122cca792bcdaa0f2d6bbd9c30d8ca031ca946343'
TOPIC_BENEFICIARY_SET            = '\x04d55a8be181fb8d75b76f2d48aa0b2ee40f47e53d6e61763eeeec46feea8a24'
TOPIC_PROTOCOL_FEE_PAID          = '\xb87e607f6030a23ed9b7dac1a717610f3a3b07325269f18808ba763bdcefe7ae'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                   = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_VALIDATOR_ANNOUNCEMENT     = '\x78066d8adb677a1353d1fc8be28cf03e2a8de7157bbab979953587d78076c11e'
TOPIC_REMOTE_CALL_DISPATCHED     = '\xa82f02bdb198e6cca80598e390600aa519d0f9efca0322efa45096af14fa2087'
TOPIC_INTERCHAIN_ACCOUNT_CREATED = '\x43c7c79901faab5ae18ac2369d6df969a28064bd40483d341f0dc439cb095d96'
TOPIC_OWNERSHIP_TRANSFERRED      = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED              = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
-- ===== Selectors =====
SEL_DISPATCH                     = '\xfa31de01'
SEL_DISPATCH_WITH_METADATA       = '\x48aee8d4'
SEL_DISPATCH_WITH_HOOK           = '\x10b83dc0'
SEL_PROCESS                      = '\x7c39d130'
SEL_DELIVERED                    = '\xe495f1d4'
SEL_SET_DEFAULT_ISM              = '\xf794687a'
SEL_SET_DEFAULT_HOOK             = '\x99b04809'
SEL_SET_REQUIRED_HOOK            = '\x1426b7f4'
SEL_PAY_FOR_GAS                  = '\x11bf2c18'
SEL_PAUSE                        = '\x8456cb59'
SEL_ANNOUNCE                     = '\x21f71781'
SEL_CALL_REMOTE                  = '\xdd91cc87'
SEL_PROXYADMIN_UPGRADE           = '\x99a88ec4'
SEL_PROXYADMIN_UPGRADE_AND_CALL  = '\x9623609d'
SEL_LOCAL_DOMAIN                 = '\x8d3638f4'
-- ===== Mailbox (per chain) =====
ETH_MAILBOX                      = '\xc005dc82818d67af737725bd4bf75435d065d239'
BASE_MAILBOX                     = '\xea87ae93fa0019a82a727bfd3ebd1cfca8f64f1d'
ARB_MAILBOX                      = '\x979ca5202784112f4738403dbec5d0f3b9daabb9'
OP_MAILBOX                       = '\xd4c1905bb1d26bc93dac913e13cacc278cdcc80d'
POLY_MAILBOX                     = '\x5d934f4e2f797775e53561bb72aca21ba36b96bb'
BNB_MAILBOX                      = '\x2971b9aec44be4eb673df1b88cdb57b96eefe8a4'
AVAX_MAILBOX                     = '\xff06afcaabaddd1fb08371f9cca15d73d51febd6'
RH_MAILBOX                       = '\x3a867fcffec2b790970eebdc9023e75b0a172aa7'
-- ===== MerkleTreeHook (per chain) =====
ETH_MERKLE_TREE_HOOK             = '\x48e6c30b97748d1e2e03bf3e9fbe3890ca5f8cca'
BASE_MERKLE_TREE_HOOK            = '\x19dc38aeae620380430c200a6e990d5af5480117'
ARB_MERKLE_TREE_HOOK             = '\x748040afb89b8fdbb992799808215419d36a0930'
OP_MERKLE_TREE_HOOK              = '\x68ee9bec9b4dbb61f69d9d293ae26a5aacb2e28f'
POLY_MERKLE_TREE_HOOK            = '\x73fbd25c3e817dc4b4cd9d00eff6d83dcde2dff6'
BNB_MERKLE_TREE_HOOK             = '\xfdb9cd5f9daaa2e4474019405a328a88e7484f26'
AVAX_MERKLE_TREE_HOOK            = '\x84eea61d679f42d92145fa052c89900cbacce95a'
RH_MERKLE_TREE_HOOK              = '\xf16e63b42df7f2676b373979120bbf7e6298f473'
-- ===== InterchainGasPaymaster (per chain) =====
ETH_IGP                          = '\x9e6b1022be9bbf5afd152483dad9b88911bc8611'
BASE_IGP                         = '\xc3f23848ed2e04c0c6d41bd7804fa8f89f940b94'
ARB_IGP                          = '\x3b6044acd6767f017e99318aa6ef93b7b06a5a22'
OP_IGP                           = '\xd8a76c4d91fcbb7cc8ea795dfdf870e48368995c'
POLY_IGP                         = '\x0071740bf129b05c4684abfbbed248d80971cce2'
BNB_IGP                          = '\x78e25e7f84416e69b9339b0a6336eb6efff6b451'
AVAX_IGP                         = '\x95519ba800bbd0d34eeae026fec620ad978176c0'
RH_IGP                           = '\x3862a9b1acd89245a59002c2a08658ec1d5690e3'
-- ===== ProxyAdmin (per chain) =====
ETH_PROXY_ADMIN                  = '\x75ee15ee1b4a75fa3e2fdf5df3253c25599cc659'
BASE_PROXY_ADMIN                 = '\x4ed7d626f1e96cd1c0401607bf70d95243e3ded1'
ARB_PROXY_ADMIN                  = '\x80cebd56a65e46c474a1a101e89e76c4c51d179c'
OP_PROXY_ADMIN                   = '\xe047cb95fb3b7117989e911c6afb34771183fc35'
POLY_PROXY_ADMIN                 = '\xc4f7590c5d30be959225dc75640657954a86b980'
BNB_PROXY_ADMIN                  = '\x65993af9d0d3a64ec77590db7ba362d6eb78ef70'
AVAX_PROXY_ADMIN                 = '\xd7cf8c05fd81b8ca7cff8e6c49b08a9d63265c9b'
RH_PROXY_ADMIN                   = '\xea87ae93fa0019a82a727bfd3ebd1cfca8f64f1d'
-- ===== PausableHook / PausableIsm (per chain) =====
ETH_PAUSABLE_HOOK                = '\x3a66dc852e56d3748838b3c27cf381105b83705b'
BASE_PAUSABLE_HOOK               = '\x46fa3a5780e5b90eaf34bded554d5353b5abe9e7'
ARB_PAUSABLE_HOOK                = '\xef30f29dcd3fcb1dccda9c7cbf2a5957e8ee9cc3'
OP_PAUSABLE_HOOK                 = '\xf753ca2269c8a7693ce1808b5709fbf36a65d47a'
POLY_PAUSABLE_HOOK               = '\x748040afb89b8fdbb992799808215419d36a0930'
BNB_PAUSABLE_HOOK                = '\x7dbdad1b4a922b65d37d7258a4227b6658344b7f'
AVAX_PAUSABLE_HOOK               = '\x239eb860770f1c48abac9be9825d20e3e7c018df'
RH_PAUSABLE_HOOK                 = '\xa377b8269e0a47cdd2fd5aaeae860b45623c6d82'
ETH_PAUSABLE_ISM                 = '\xdc98a856fb9112894c2fe32267da8bf35645faf3'
BASE_PAUSABLE_ISM                = '\x2af32cf8e3cf42d221eda0c843818fa5ee129e27'
ARB_PAUSABLE_ISM                 = '\x1e38556b4fe553e6249448960875883990efcf34'
OP_PAUSABLE_ISM                  = '\xd84d8114ccfa5c2403e56abf754da529430704f0'
POLY_PAUSABLE_ISM                = '\x6741e91ffdc31c7786e3684427c628dad06299b0'
BNB_PAUSABLE_ISM                 = '\x25db01cadf91cfd2f7e6dd829ce81698217f9151'
AVAX_PAUSABLE_ISM                = '\xd76080269c641e1adb786b72ae60ddac3b6b8ed0'
RH_PAUSABLE_ISM                  = '\xe350143242a2f7962f23d71ee9dd98f6e86d1772'
-- ===== InterchainAccountRouter (per chain) =====
ETH_ICA_ROUTER                   = '\xc00b94c115742f711a6f9ea90373c33e9b72a4a9'
BASE_ICA_ROUTER                  = '\x44647cd983e80558793780f9a0c7c2aa9f384d07'
ARB_ICA_ROUTER                   = '\xf90a3d406c6f8321fe118861a357f4d7107760d7'
OP_ICA_ROUTER                    = '\x3e343d07d024e657ecf1f8ae8bb7a12f08652e75'
POLY_ICA_ROUTER                  = '\xd8b641feb587844854aec97544ccea426dff04a3'
BNB_ICA_ROUTER                   = '\xf453b589f0166b90e050691eac281c01a8959897'
AVAX_ICA_ROUTER                  = '\x2c58687fffcd5b7043a5bf256b196216a98a6587'
RH_ICA_ROUTER                    = '\xf2755ae2a6f3b49fee5d6ccf5c7c60ec06a45200'
-- ===== Owners =====
ETH_MAILBOX_OWNER_SAFE           = '\x562dfaac27a84be6c96273f5c9594da1681c0da7'
BASE_MAILBOX_OWNER_SAFE          = '\x890ac177fe3052b8676a65f32c1589bc329f3d50'
OP_MAILBOX_OWNER_SAFE            = '\x890ac177fe3052b8676a65f32c1589bc329f3d50'
ARB_MAILBOX_OWNER_SAFE           = '\x7379d7bb2cca68982e467632b6554fd4e72e9431'
BNB_MAILBOX_OWNER_SAFE           = '\x7379d7bb2cca68982e467632b6554fd4e72e9431'
ARB_PROXY_ADMIN_OWNER_TIMELOCK   = '\xac98b0cd1b64ea4fe133c6d2edaf842ce5cf4b01'
POLY_MAILBOX_OWNER_ICA           = '\x20e52e3bedf7bd305ca816dc54a0835d3bded820'
AVAX_MAILBOX_OWNER_ICA           = '\x66c21cfa8b765318a458435519a31a5cf0f7ae4b'
RH_MAILBOX_OWNER_ICA             = '\x0e7e5d38695d7939303244ad56ace1eea263dce8'
IGP_OWNER_EOA                    = '\xa7eccdb9be08178f896c26b7bbd8c3d4e844d9ba'
-- Hyperlane domain = chain id on all eight: 1, 8453, 42161, 10, 137, 56, 43114, 4663
```

---

## 16. Verification & sources

How each constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `hyperlane-monorepo/solidity/contracts` (`interfaces/IMailbox.sol`, `Mailbox.sol`, `hooks/MerkleTreeHook.sol`, `interfaces/IInterchainGasPaymaster.sol`, `hooks/igp/InterchainGasPaymaster.sol`, `hooks/ProtocolFee.sol`, `hooks/PausableHook.sol`, `isms/PausableIsm.sol`, `isms/multisig/ValidatorAnnounce.sol`, `middleware/AbstractInterchainAccountRouter.sol`). Every event topic and every listed selector was found in the deployed Ethereum bytecode (Mailbox implementation `0x7b4d881c122a5e61adcffb56a2e3ce9927d53455`, IGP implementation `0xb6b16b5eede90e93c8e558f49effb06193b04edf`, MerkleTreeHook, ValidatorAnnounce, PausableIsm, PausableHook, ICA router). `ProtocolFeePaid` was confirmed from a Robinhood Chain log instead (the Ethereum ProtocolFee bytecode has no such event). The legacy three-field `GasPayment(bytes32,uint256,uint256)` is absent from every deployed IGP checked, so it is not listed.
- **Addresses:** parsed from `hyperlane-registry` `chains/<chain>/addresses.yaml` for the eight chains; every address existence-checked with `eth_getCode`. Proxy implementations and admins read from the EIP-1967 slots. `localDomain()`, `owner()`, `defaultIsm()`, `defaultHook()`, `requiredHook()` and `nonce()` read on each Mailbox; `hooks(bytes)` on each AggregationHook (all eight chains); `implementation()` on the Polygon, Avalanche and Robinhood Chain ICA routers (equal to the EIP-1167 targets of the owners); `getMinDelay()` on the Arbitrum timelock; `getThreshold()` on the Ethereum Safe.
- **Sample transactions read:** Ethereum `0xfb299b17db0e06f677d0d7f935821a08738682613d6dac83b684997dba1bc027` (USDC into a warp route, `SentTransferRemote`, `Dispatch`, `DispatchId`, `InsertedIntoTree`, `GasPayment` to domain 1399811149); Ethereum `0x955037563771deab94c3681051b6c10b771bde2d41d3108848792d28cdf94d5a` (`process` from a relayer EOA: `Process`, `ProcessId`, `ReceivedTransferRemote`, USDT `Transfer` to the recipient); Robinhood Chain `0x488bfa12b9fd6cb560facc316a64bdb60a91c9619a30a310f3af4621a6d021f9` (`Dispatch`, `DispatchId`, `ProtocolFeePaid`, `InsertedIntoTree`).
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC** (logs at the registry Mailbox of each chain): `Dispatch` — Ethereum 148, Base 206, Arbitrum 153, Optimism 50, Polygon 85, BNB 76, Avalanche 0, Robinhood Chain 1. `Process` — Ethereum 150, Base 224, Arbitrum 141, Optimism 62, Polygon 19, BNB 102, Avalanche 1, Robinhood Chain 0. `DispatchId`/`ProcessId` equal `Dispatch`/`Process` on every chain. A 0 is a finding of this window only.

Authoritative sources:
- Canonical repositories — [hyperlane-xyz/hyperlane-monorepo](https://github.com/hyperlane-xyz/hyperlane-monorepo) (`solidity/contracts`) · [hyperlane-xyz/hyperlane-registry](https://github.com/hyperlane-xyz/hyperlane-registry) (`chains/*/addresses.yaml`, `chains/*/metadata.yaml`)
- Docs — [Hyperlane domains](https://docs.hyperlane.xyz/docs/reference/domains)
- Explorers — [Etherscan Mailbox](https://etherscan.io/address/0xc005dc82818d67af737725bd4bf75435d065d239) · [Basescan Mailbox](https://basescan.org/address/0xea87ae93fa0019a82a727bfd3ebd1cfca8f64f1d) · [Robinhood Chain Blockscout Mailbox](https://robinhoodchain.blockscout.com/address/0x3a867fCfFeC2B790970eeBDC9023E75B0a172aa7) · [Blockscout: independent Mailbox `0x599899e6b3b1362ba2460d125756a738ec1592d6`](https://eth.blockscout.com/address/0x599899e6b3b1362ba2460d125756a738ec1592d6)

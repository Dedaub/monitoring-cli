# Eclipse Canonical Bridge — Topics, Selectors, Addresses (Ethereum only)

**Status:** verified on 2026-09-29 against Ethereum mainnet RPC (`eth_getCode`, `eth_call`, `eth_getStorageAt`, `eth_getLogs`), `eth_getCode` on the seven other target chains, the Sourcify verified sources of every contract below, and L2BEAT.
**Scope:** the Ethereum-side contracts of the canonical ETH bridge of Eclipse, an SVM rollup that settles to Ethereum: the current `CanonicalBridgeV3`, the `Treasury` escrow, and the three earlier bridge generations. Eclipse itself is not an EVM chain, so the destination side of a deposit and the source side of a withdrawal are not EVM-queryable. Of the eight target chains, only Ethereum (chain ID 1) has a deployment. Topics and selectors are chain-agnostic; addresses are network-specific.

The bridge moves **native ETH only**. Other assets reach Eclipse through third-party bridges (Hyperlane and others, which the Eclipse docs list separately); they are not part of this canonical bridge. The bridge is **relayer-authorized, not proof-based**: an Ethereum account with `WITHDRAW_AUTHORITY_ROLE` posts each withdrawal message (`authorizeWithdraw[s]`), a 7-day fraud window starts, and after the window the recipient (or a `CLAIM_AUTHORITY_ROLE` holder) calls `claimWithdraw`. No state root or proof is checked on Ethereum.

The bridge contract holds no ETH. Every deposit goes into the **`Treasury`** (a UUPS proxy), and every payout comes out of it. The bridge contracts are immutable; the Treasury is upgradeable by a Safe with no delay. **Only `CanonicalBridgeV3` holds the Treasury's `DEPOSITOR_ROLE` and `WITHDRAW_AUTHORITY_ROLE`** (read live), so the earlier bridges cannot move funds, even the ones that are not paused.

---

## 0. Contract families & versions

| Contract | Address (Ethereum) | `getVersionComponents()` | Created (block) | State (read 2026-09-29) |
|----------|--------------------|--------------------------|-----------------|--------------------------|
| **CanonicalBridgeV3** | `0x504392F02ee64D6B51aD3bCf7999E69EBe28b30a` | 3.0.0 | 23,771,157 | **Current.** `paused()=false`; holds both Treasury roles; `depositIndex()=521`. |
| **Treasury** (ERC-1967 proxy) | `0xD7E4b67E735733aC98a88F13d087D8aac670E644` | 2.0.0 | 20,402,663 | **Escrow of all bridged ETH.** UUPS; `paused()=false`. |
| CanonicalBridgeV2 | `0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51` | 2.1.0 | 22,864,313 | Retired. `paused()=false`, but it has no Treasury role, so `deposit` and `claimWithdraw` revert. V3 calls it `canonicalBridgeV2`. |
| CanonicalBridge | `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` | 2.0.0 | 21,118,887 | Retired. `paused()=false`, no Treasury role. V3 calls it `canonicalBridgeV1`. Still the address in the `eclipse-deposit` CLI config (stale). |
| EtherBridge (ERC-1967 proxy) | `0x83cB71D80078bf670b3EfeC6AD9E5E6407cD0fd1` | 1.0.0 | 20,402,682 | First generation. `paused()=true`. Sent deposits through the Mailbox below. |
| Mailbox (ERC-1967 proxy) | `0xb23B2492f7A9631104A5877F7FFA00633660968d` | — | 20,402,702 | Message box of the first generation only. |
| Upgrader0to1 | `0xD02f545d57536BC1E8F12D867731F006AacE71E3` | — | — | Migration helper. Still holds the Treasury `UPGRADER_ROLE` and `EMERGENCY_ROLE`. |

Two naming traps: the V3 constructor names `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` "canonicalBridgeV1" although that contract reports version 2.0.0, and the first-generation contract is `EtherBridge`, not a `CanonicalBridge`. Key on addresses, never on version labels.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

`WithdrawMessage` is the tuple `(bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei)`. `from` is the Eclipse (SVM) sender account; `withdrawId` is assigned on Eclipse.

### 1.1 CanonicalBridgeV3 — transfer flow (emitter `0x504392F02ee64D6B51aD3bCf7999E69EBe28b30a`)

| topic0 | Event |
|--------|-------|
| `0x97dcb220fc7f84ae61f5c0302e4c05f276c444a8ffb0253f3a86514bf16e8152` | `DepositedWithId(address indexed sender, bytes32 indexed recipient, uint256 amountWei, uint256 amountLamports, uint64 depositId)` — **source leg (V3 only)** |
| `0xcc9c1a7566adfa8bdc9f7a63a106576fec355c6b4f61ce07baad45eaa30560c3` | `Deposited(address indexed sender, bytes32 indexed recipient, uint256 amountWei, uint256 amountLamports)` — source leg; V3 emits it **in the same transaction** as `DepositedWithId` (count one) |
| `0xf486b030a91fdad2b9594a1322d19e1fd67f566f96e6501dfbf69fca11ff95ca` | `WithdrawAuthorized(address indexed sender, (bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message, bytes32 indexed messageHash, uint256 startTime)` — **status only** (no value moves); starts the fraud window; `startTime` is the earliest claim time |
| `0x17301a134abd040120edefa131df2e376da9fb5264e3483c90f23293ab142611` | `WithdrawClaimed(address indexed receiver, bytes32 indexed remoteSender, bytes32 indexed messageHash, (bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` — **destination leg**: the Treasury pays `amountWei - feeWei` to `receiver` |
| `0x26a2bb34c011f942f61c31dfaeff3a3a1b2132da80c36b90d131a5732d7cd96b` | `WithdrawFeeSettled(address indexed receiver, bytes32 indexed remoteSender, bytes32 indexed messageHash, (bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` — the Treasury pays `feeWei` to `message.feeReceiver` (the relayer) |
| `0x59c8adb5b760016054e333eac5c0ea8494e7e59a9ef83f02733788a94b4a4526` | `WithdrawSettled(address indexed canonicalBridge, bytes32 indexed messageHash, (bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` — a withdrawal that was pending on an older bridge (`canonicalBridge`) is paid by V3; a `WithdrawClaimed` follows in the same transaction |
| `0xefe476e7ac46b9bde62b3d392a897ae796bfad2fe290ad65adf17b9079b9341e` | `WithdrawMessageDeleted(address authority, (bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` — **cancel path**: a `WITHDRAW_CANCELLER_ROLE` holder deletes an authorized withdrawal inside the fraud window |

### 1.2 CanonicalBridgeV3 — admin and configuration

| topic0 | Event |
|--------|-------|
| `0x9892782f1437afb6be047429f988c13aab6dfb7e314d22ac657b062f4f1a5483` | `FraudWindowSet(address indexed sender, uint256 durationSeconds)` — the fraud window changed (floor 1 day in code; live value 604,800 s = 7 days) |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` — OpenZeppelin `Pausable`; also emitted by the Treasury |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` — also on the Treasury |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` |
| `0xc95935a66d15e0da5e412aca0ad27ae891d20b2fb91cf3994b6a3bf2b8178082` | `Deployed(address indexed deployer, address owner, address treasuryAddress)` — constructor only |
| `0x22c6a7704a34b8976cde83ad421beaf3e9d61e2d9a6adde7501d2bf953f53d81` | `CanonicalBridgeV1(address indexed deployer, address canonicalBridgeV1)` — constructor only |
| `0x28e45a71b806f884eaa2cec0818696c12a9d51d11e7fff2d18a5c6948e58c919` | `CanonicalBridgeV2(address indexed deployer, address canonicalBridgeV2)` — constructor only |

The shared interface also declares `WithdrawCancelled(address indexed sender, bytes32 indexed messageHash)` (`0x8b2a4e4d81fce816790e969140fff56019670cd99c4809e3d5dd0a4042edaed7`) and `WithdrawMessageHashDeleted(address indexed authority, bytes32 indexed messageHash)` (`0xc417f0cb08245e1b721d0585ae2b1775877a945419d3e66d9a551f62f052ba1f`). The V3 source has no `emit` of either; do not alert on them.

Role ids (`keccak256` of the name): Pauser `0x39935d86204acf3d77da26425d7a46606d2550568c6b1876f3a2e76c804c7626`, Starter `0xac6a94bcd1ac2877eda181de9748e5972fc07f76d4864cecf836b3fca185e53c`, WithdrawAuthority `0xfe482b7b16acc2ea6eda181934b481a09d50ed8e3579b43c531bc57b84336c53`, ClaimAuthority `0x49d85f38d8d200e3ac71b7ada9a2786ccb6d016b3c28e43e8057f6bbae438adc`, WithdrawCanceller `0xb7a383a5ef6cc414a168844ee7da5cf32b44a10145b4d0cc573e1b7c231d3040`, FraudWindowSetter `0xe68a6574a7e933010135bdcdb85f5b60aed1ee2a05b00c7c3b88734a75706cf0`.

### 1.3 Treasury (emitter `0xD7E4b67E735733aC98a88F13d087D8aac670E644`)

| topic0 | Event |
|--------|-------|
| `0xe3407208b14fa025330ca187030f118a1c0cdb604aba93ba45c862e6095aee27` | `TreasuryDeposit(address indexed from, uint256 amountWei)` — ETH in; `from` is the bridge, not the user |
| `0xa9186eec1c1f118aa187d90aecd4ff2bf3d2e5412f3750362412ac6f7f572147` | `TreasuryWithdraw(address authority, address indexed to, uint256 amountWei)` — ETH out; two per V3 claim (user, then relayer fee) |
| `0x8bc1e000092be4d2cfc113dc7fd97b390d3459e1491c422f8ac30e572f364f47` | `EmergencyTreasuryWithdraw(address indexed to, uint256 amountWei)` — **`EMERGENCY_ROLE` sweep to the caller: treat as a drain signal** |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — UUPS implementation changed |
| `0xea56cfeef65597111833653b9053542ffbcb86637a9920cc21664295169040fd` | `TreasuryReinitialized(address admin, address oldOwner)` — role re-grant during a migration |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` |

Treasury role ids: DEPOSITOR `0xd50fd8c1b5fa5213a5974932fcc33d2992a99225bc9319caf7cf652d0d2b9acf`, WITHDRAW_AUTHORITY `0xfe482b7b16acc2ea6eda181934b481a09d50ed8e3579b43c531bc57b84336c53`, EMERGENCY `0x9e97963c33348a1cae64c3216747be51682ee42f36d1ed282cb81018cdb30e3d`, UPGRADER `0x0fb7166d9f681d2bd296a45a1a2e81365c392be30b6156d73b45df44e85cdb9f`.

### 1.4 Earlier generations (historical)

| topic0 | Event |
|--------|-------|
| `0xfe447f84c02bd3d47e0f77ccc68779ac1a79d4a2e3a0a66f626b495f8bf88084` | `Deposited(address indexed sender, bytes32 indexed recipient, uint256 amountWei)` — EtherBridge (first generation) deposit; three fields, a different topic0 from the later `Deposited` |
| `0x33e849cb0fec1c09717acb97b31d5c785c809f0b281858ddae6dcbc17ded5b9d` | `MessageSent(bytes to, bytes toChainId, bytes message, bytes extraData)` — Mailbox (first generation) |
| `0x87955535a2e967f2476802fb49648e6b80323a2a2e9b3b5b28c88fba85e6bd69` | `MessageReceived(bytes from, bytes fromChainId, bytes message, bytes extraData)` — Mailbox (first generation) |

`CanonicalBridge` (`0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11`) and `CanonicalBridgeV2` (`0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51`) emit the §1.1/§1.2 topics except `DepositedWithId`, `WithdrawFeeSettled` and `WithdrawSettled`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 CanonicalBridgeV3

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1de26e16` | `deposit(bytes32 recipient, uint256 amountWei)` | `payable`; `msg.value` must equal `amountWei`, be a multiple of 1 gwei and be at least `MIN_DEPOSIT` (0.002 ETH). Forwards the ETH to `Treasury.depositEth`. Same selector on all four generations. |
| `0xcc3cfe37` | `authorizeWithdraw((bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` | `WITHDRAW_AUTHORITY_ROLE`; emits `WithdrawAuthorized`. |
| `0xb61b6ee6` | `authorizeWithdraws((bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei)[] messages)` | Batch form; the relayer uses this one. |
| `0x744ced3d` | `claimWithdraw((bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` | Caller must be `destination` or hold `CLAIM_AUTHORITY_ROLE`; pays out after the fraud window. |
| `0x931da346` | `deleteWithdrawMessage((bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` | `WITHDRAW_CANCELLER_ROLE`; cancel path. |
| `0xc76b99fd` | `setFraudWindowDuration(uint256 durationSeconds)` | `FRAUD_WINDOW_SETTER_ROLE`; minimum 1 day. |
| `0x8456cb59` | `pause()` | `PAUSER_ROLE`; stops deposits, authorizations and claims. |
| `0x3f4ba83a` | `unpause()` | `STARTER_ROLE`. |
| `0x2f2ff15d` | `grantRole(bytes32 role, address account)` | Admin; emits `RoleGranted`. |
| `0xd547741f` | `revokeRole(bytes32 role, address account)` | Admin; emits `RoleRevoked`. |
| `0xc0cb8f0f` | `withdrawMessageStatus(bytes32 messageHash)` | View → `uint8`: 0 UNKNOWN, 1 PROCESSING (inside the fraud window), 2 PENDING (claimable), 3 CLOSED. |
| `0xfd662610` | `withdrawMessageStatus((bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` | Overload by message. |
| `0x40a4aa58` | `withdrawMessageHash((bytes32 from, address destination, uint256 amountWei, uint64 withdrawId, address feeReceiver, uint256 feeWei) message)` | Pure → `keccak256(abi.encode(message))`. |
| `0x3b148f59` | `startTime(bytes32 withdrawMessageHash)` | View → claim time (`type(uint256).max` once claimed). |
| `0x8bcb4fdb` | `withdrawMsgIdProcessed(uint64 withdrawMessageId)` | View → the block of authorization (replay guard). |
| `0x7b898939` | `depositIndex()` | View → deposit counter (521 on 2026-09-29). |
| `0x30053c69` | `fraudWindowDuration()` | View → 604,800. |
| `0x2d2c5565` | `TREASURY()` | View → the Treasury proxy. |
| `0xe1e158a5` | `MIN_DEPOSIT()` | View → 2,000,000,000,000,000 wei. |
| `0x5c975abb` | `paused()` | View. |
| `0x91d14854` | `hasRole(bytes32 role, address account)` | View. |
| `0x4442eab2` | `getVersionComponents()` | Pure → `(major, minor, patch)`. |

### 2.2 Treasury

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x439370b1` | `depositEth()` | `payable`; `DEPOSITOR_ROLE` (V3 only). |
| `0x1b9a91a4` | `withdrawEth(address to, uint256 amountWei)` | `WITHDRAW_AUTHORITY_ROLE` (V3 and Multisig 2). |
| `0x5312ea8e` | `emergencyWithdraw(uint256 amountWei)` | `EMERGENCY_ROLE`; sends to `msg.sender`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | `UPGRADER_ROLE`; no delay. |
| `0x6c2eb350` | `reinitialize()` | Migration hook. |
| `0x8456cb59` | `pause()` | `PAUSER_ROLE`; stops deposits and withdrawals. |
| `0x52d1902d` | `proxiableUUID()` | UUPS check. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on 2026-09-29. Wiring read live: V3 `TREASURY()` → `0xD7E4b67E735733aC98a88F13d087D8aac670E644` (the same for `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` and `0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51`); EtherBridge storage (ERC-7201 slot `0x47de546cf6a4c0310e912c3941a75f4e016a86b1301d78e45822946d7c351e00`) → Mailbox `0xb23B2492f7A9631104A5877F7FFA00633660968d` and the same Treasury.

| Role | Address | One-liner |
|------|---------|-----------|
| **CanonicalBridgeV3** | `0x504392F02ee64D6B51aD3bCf7999E69EBe28b30a` | Current entry point for deposits, authorizations and claims. Immutable, 10,808 bytes. |
| **Treasury** (proxy) | `0xD7E4b67E735733aC98a88F13d087D8aac670E644` | Holds all bridged ETH. Implementation `0xF1F7a359C3f33EE8A66bdCbf4c897D25Caf90978`. |
| CanonicalBridgeV2 (v2.1.0) | `0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51` | Retired; no Treasury role. |
| CanonicalBridge (v2.0.0) | `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` | Retired; no Treasury role. |
| EtherBridge (proxy, v1.0.0) | `0x83cB71D80078bf670b3EfeC6AD9E5E6407cD0fd1` | Paused. Implementation `0x338017E0f208b4EAF8Cd4BbDc8bdabEFd0e39bE9`. |
| Mailbox (proxy) | `0xb23B2492f7A9631104A5877F7FFA00633660968d` | First-generation message box. Implementation `0x4ceF0fA54dC06CE0eA198DAb2F57D28A9deE712B`. |
| Upgrader0to1 | `0xD02f545d57536BC1E8F12D867731F006AacE71E3` | Holds Treasury `UPGRADER_ROLE` and `EMERGENCY_ROLE`. |
| Eclipse Multisig (Safe, 3 of 4) | `0x4720342419C1D316B948690d12C86D5b485C64E0` | V3 owner: every V3 role. Treasury `DEFAULT_ADMIN_ROLE`. |
| Eclipse Multisig 2 (Safe, 3 of 5) | `0x7B2c1CbB33c53c3C6a695e36096AD2cfCE1c0efC` | Treasury admin, `UPGRADER_ROLE`, `EMERGENCY_ROLE`, `WITHDRAW_AUTHORITY_ROLE`. |
| Withdraw relayer (EOA) | `0x1a84163249B2909f746C725F23D5ae2a66D7C4fE` | EOA (no code, nonce 34,389). V3 `WITHDRAW_AUTHORITY_ROLE`; the `feeReceiver` of the sampled claims. |

---

## 4. Cross-chain summary

| Chain | ID | CanonicalBridgeV3 | Treasury | Earlier bridges | Note |
|-------|----|-------------------|----------|-----------------|------|
| **Ethereum** | 1 | ✅ `0x504392F02ee64D6B51aD3bCf7999E69EBe28b30a` | ✅ `0xD7E4b67E735733aC98a88F13d087D8aac670E644` | ✅ three generations | The only EVM side. |
| Base | 8453 | — | — | — | no deployment: `eth_getCode` = `0x` at the Ethereum addresses; not in any official list |
| Arbitrum One | 42161 | — | — | — | same |
| Optimism | 10 | — | — | — | same |
| Polygon PoS | 137 | — | — | — | same |
| BNB Smart Chain | 56 | — | — | — | same |
| Avalanche C-Chain | 43114 | — | — | — | same |
| Robinhood Chain | 4663 | — | — | — | same |

The counterparty is **Eclipse mainnet** (SVM, no EVM chain id), outside the eight chains. The bridge uses no protocol domain ids: there is only one route, Ethereum ↔ Eclipse.

---

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Treasury** | UUPS (ERC-1967) | 133-byte proxy; impl slot → `0xF1F7a359C3f33EE8A66bdCbf4c897D25Caf90978`; admin slot empty. | `UPGRADER_ROLE`: Eclipse Multisig 2 (3 of 5) and Upgrader0to1. **No timelock.** Watch `Upgraded` on the proxy. |
| **CanonicalBridgeV3** | Immutable | Full 10,808-byte runtime; Sourcify reports no proxy. Treasury and older-bridge addresses are `immutable`. | None. A new version needs a new deployment and a Treasury role grant (`RoleGranted` on the Treasury). |
| CanonicalBridgeV2 / CanonicalBridge | Immutable | Full runtime (10,125 / 8,760 bytes). | None. |
| EtherBridge | UUPS (ERC-1967) | 133-byte proxy; impl `0x338017E0f208b4EAF8Cd4BbDc8bdabEFd0e39bE9`. | Its own authority role; paused. |
| Mailbox | UUPS (ERC-1967) | 133-byte proxy; impl `0x4ceF0fA54dC06CE0eA198DAb2F57D28A9deE712B`. | First generation only. |

EIP-1967 slots: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`.

---

## 6. Detection invariants & gotchas

1. **The flow.** Source leg: `deposit` on V3 → ETH `msg.value` goes to the Treasury by an internal call (`TreasuryDeposit`, `from` = V3) → V3 emits `Deposited` **and** `DepositedWithId`. Destination leg: the relayer calls `authorizeWithdraws` (`WithdrawAuthorized`, no value) → after 7 days `claimWithdraw` → the Treasury sends `amountWei - feeWei` to `destination` (`TreasuryWithdraw` + `WithdrawClaimed`) and `feeWei` to `feeReceiver` (`TreasuryWithdraw` + `WithdrawFeeSettled`). Cancel: `WithdrawMessageDeleted`. There is no deposit refund on Ethereum: a bad deposit reverts.
2. **Count one deposit per transaction.** V3 emits the legacy `Deposited` (`0xcc9c1a7566adfa8bdc9f7a63a106576fec355c6b4f61ce07baad45eaa30560c3`) next to `DepositedWithId` (`0x97dcb220fc7f84ae61f5c0302e4c05f276c444a8ffb0253f3a86514bf16e8152`). Key on `DepositedWithId` for V3; key on `Deposited` only for the retired bridges.
3. **All value is native ETH.** No ERC-20 `Transfer` row exists for either leg. Take the amount from the event data, or from the internal ETH transfer. `amountLamports = amountWei / 10^9`: Eclipse ETH has 9 decimals.
4. **The link keys.** Deposit: `DepositedWithId.depositId`, a pseudo-random `uint64` (`keccak256(abi.encodePacked(depositIndex))`), with `recipient` as a 32-byte SVM account; the Eclipse-side mint is on the SVM chain, not EVM-queryable. Withdrawal: `messageHash` (topic 3 of `WithdrawClaimed`, topic 2 of `WithdrawAuthorized`) and `message.withdrawId`, both on chain on Ethereum; the Eclipse-side burn is off the EVM.
5. **`WithdrawAuthorized` is a 7-day early warning.** It carries the full message (destination and amount) before any ETH moves. A large or odd authorization can be cancelled (`deleteWithdrawMessage`) inside the window. Alert on it, not only on `WithdrawClaimed`.
6. **The trust is in the relayer key.** `authorizeWithdraw[s]` checks only the role. The withdraw authority is one EOA (`0x1a84163249B2909f746C725F23D5ae2a66D7C4fE`) plus the 3-of-4 Safe. An authorization from any other sender, or a `RoleGranted` of `WITHDRAW_AUTHORITY_ROLE`, is a high-severity signal.
7. **Drain and admin triggers.** Treasury: `EmergencyTreasuryWithdraw`, `Upgraded`, `RoleGranted`/`RoleRevoked` (any of the four Treasury roles), `Paused`. V3: `FraudWindowSet` (a shorter window weakens the fraud check), `RoleGranted`, `Paused`, `WithdrawMessageDeleted`.
8. **The retired bridges still look live.** `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` and `0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51` return `paused()=false`, and `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` is still the address in the official `eclipse-deposit` CLI. Both lack the Treasury roles, so their `deposit` and `claimWithdraw` revert. A successful transaction to them is only possible after a Treasury role grant: watch `RoleGranted` on the Treasury.
9. **Old withdrawals settle through V3.** A message pending on `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` or `0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51` is paid by V3 with `WithdrawSettled(canonicalBridge = old bridge)` + `WithdrawClaimed`. Attribute it to V3 as the payer, and do not count the old bridge twice.
10. **`TreasuryDeposit.from` is the bridge.** The depositor is `Deposited.sender` / `DepositedWithId.sender` (topic 1), or `tx.from`.
11. **Topic collision across generations.** The first-generation `Deposited(address,bytes32,uint256)` (`0xfe447f84c02bd3d47e0f77ccc68779ac1a79d4a2e3a0a66f626b495f8bf88084`) and the later `Deposited(address,bytes32,uint256,uint256)` (`0xcc9c1a7566adfa8bdc9f7a63a106576fec355c6b4f61ce07baad45eaa30560c3`) share a name but not a topic0. `Paused`, `Unpaused` and the role events are OpenZeppelin topics that thousands of contracts emit: always filter by emitter.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== CanonicalBridgeV3 topics (chain-agnostic) =====
TOPIC_DEPOSITED_WITH_ID          = '\x97dcb220fc7f84ae61f5c0302e4c05f276c444a8ffb0253f3a86514bf16e8152'
TOPIC_DEPOSITED                  = '\xcc9c1a7566adfa8bdc9f7a63a106576fec355c6b4f61ce07baad45eaa30560c3'
TOPIC_WITHDRAW_AUTHORIZED        = '\xf486b030a91fdad2b9594a1322d19e1fd67f566f96e6501dfbf69fca11ff95ca'
TOPIC_WITHDRAW_CLAIMED           = '\x17301a134abd040120edefa131df2e376da9fb5264e3483c90f23293ab142611'
TOPIC_WITHDRAW_FEE_SETTLED       = '\x26a2bb34c011f942f61c31dfaeff3a3a1b2132da80c36b90d131a5732d7cd96b'
TOPIC_WITHDRAW_SETTLED           = '\x59c8adb5b760016054e333eac5c0ea8494e7e59a9ef83f02733788a94b4a4526'
TOPIC_WITHDRAW_MESSAGE_DELETED   = '\xefe476e7ac46b9bde62b3d392a897ae796bfad2fe290ad65adf17b9079b9341e'
TOPIC_FRAUD_WINDOW_SET           = '\x9892782f1437afb6be047429f988c13aab6dfb7e314d22ac657b062f4f1a5483'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                   = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_ROLE_GRANTED               = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED               = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
-- ===== Treasury topics =====
TOPIC_TREASURY_DEPOSIT           = '\xe3407208b14fa025330ca187030f118a1c0cdb604aba93ba45c862e6095aee27'
TOPIC_TREASURY_WITHDRAW          = '\xa9186eec1c1f118aa187d90aecd4ff2bf3d2e5412f3750362412ac6f7f572147'
TOPIC_EMERGENCY_TREASURY_WITHDRAW = '\x8bc1e000092be4d2cfc113dc7fd97b390d3459e1491c422f8ac30e572f364f47'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Historical (first generation) =====
TOPIC_ETHERBRIDGE_DEPOSITED      = '\xfe447f84c02bd3d47e0f77ccc68779ac1a79d4a2e3a0a66f626b495f8bf88084'
TOPIC_MAILBOX_MESSAGE_SENT       = '\x33e849cb0fec1c09717acb97b31d5c785c809f0b281858ddae6dcbc17ded5b9d'

-- ===== Selectors =====
SEL_DEPOSIT                      = '\x1de26e16'
SEL_AUTHORIZE_WITHDRAW           = '\xcc3cfe37'
SEL_AUTHORIZE_WITHDRAWS          = '\xb61b6ee6'
SEL_CLAIM_WITHDRAW               = '\x744ced3d'
SEL_DELETE_WITHDRAW_MESSAGE      = '\x931da346'
SEL_SET_FRAUD_WINDOW_DURATION    = '\xc76b99fd'
SEL_PAUSE                        = '\x8456cb59'
SEL_UNPAUSE                      = '\x3f4ba83a'
SEL_GRANT_ROLE                   = '\x2f2ff15d'
SEL_REVOKE_ROLE                  = '\xd547741f'
SEL_WITHDRAW_MESSAGE_STATUS      = '\xc0cb8f0f'
SEL_TREASURY_WITHDRAW_ETH        = '\x1b9a91a4'
SEL_TREASURY_EMERGENCY_WITHDRAW  = '\x5312ea8e'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'

-- ===== Role ids =====
ROLE_WITHDRAW_AUTHORITY          = '\xfe482b7b16acc2ea6eda181934b481a09d50ed8e3579b43c531bc57b84336c53'
ROLE_TREASURY_DEPOSITOR          = '\xd50fd8c1b5fa5213a5974932fcc33d2992a99225bc9319caf7cf652d0d2b9acf'
ROLE_TREASURY_EMERGENCY          = '\x9e97963c33348a1cae64c3216747be51682ee42f36d1ed282cb81018cdb30e3d'
ROLE_TREASURY_UPGRADER           = '\x0fb7166d9f681d2bd296a45a1a2e81365c392be30b6156d73b45df44e85cdb9f'

-- ===== Addresses — Ethereum (chain ID 1), the only chain with a deployment =====
ETH_CANONICAL_BRIDGE_V3          = '\x504392f02ee64d6b51ad3bcf7999e69ebe28b30a'
ETH_TREASURY                     = '\xd7e4b67e735733ac98a88f13d087d8aac670e644'
ETH_TREASURY_IMPL                = '\xf1f7a359c3f33ee8a66bdcbf4c897d25caf90978'
ETH_CANONICAL_BRIDGE_V2_1        = '\x867a8fcd5bb6774d4d37fb342d669a35ff789a51'
ETH_CANONICAL_BRIDGE_V2_0        = '\x2b08d7cf7eaff0f5f6623d9fb09b080726d4be11'
ETH_ETHER_BRIDGE_V1              = '\x83cb71d80078bf670b3efec6ad9e5e6407cd0fd1'
ETH_MAILBOX_V1                   = '\xb23b2492f7a9631104a5877f7ffa00633660968d'
ETH_UPGRADER_0_TO_1              = '\xd02f545d57536bc1e8f12d867731f006aace71e3'
ETH_ECLIPSE_MULTISIG             = '\x4720342419c1d316b948690d12c86d5b485c64e0'
ETH_ECLIPSE_MULTISIG_2           = '\x7b2c1cbb33c53c3c6a695e36096ad2cfce1c0efc'
ETH_WITHDRAW_AUTHORITY_EOA       = '\x1a84163249b2909f746c725f23d5ae2a66d7c4fe'
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood: no deployment
```

---

## 8. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` (and `[0:4]`) from the verified ABIs of `CanonicalBridgeV3`, `CanonicalBridgeV2`, `CanonicalBridge`, `EtherBridge`, `Mailbox` and `Treasury`. The emitted set was read from the V3 and Treasury sources (`emit` statements): `WithdrawCancelled` and `WithdrawMessageHashDeleted` are declared but never emitted by V3.
- **Addresses:** from L2BEAT (CanonicalBridgeV3, Treasury, Upgrader0to1, both Safes, the withdraw-authority EOA), the V3 constructor arguments on Sourcify (the Safe, the Treasury, `0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11` and `0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51`), the `eclipse-deposit` CLI config (`0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11`), and the EtherBridge storage (Mailbox, Treasury). Each existence-checked with `eth_getCode` on Ethereum, and with `eth_getCode` = `0x` at the Ethereum addresses of V3, the Treasury and EtherBridge on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain.
- **Roles and state:** `hasRole` read live on the Treasury (only V3 has DEPOSITOR and WITHDRAW_AUTHORITY; Multisig 2 has UPGRADER, EMERGENCY, WITHDRAW_AUTHORITY and admin; Upgrader0to1 has UPGRADER and EMERGENCY; the first Safe has admin) and on V3 (the first Safe has every role; the EOA has WITHDRAW_AUTHORITY only). `paused()`, `getVersionComponents()`, `depositIndex()`, `fraudWindowDuration()`, `MIN_DEPOSIT()` and the Safe `getThreshold()` / `getOwners()` read live.
- **Proxies:** EIP-1967 impl slots read live (Treasury, EtherBridge, Mailbox); V3 and both CanonicalBridge contracts are full-size runtimes with no proxy (Sourcify `isProxy=false`).
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26,072,222–26,075,812):** `DepositedWithId` 0, `Deposited` 0, `WithdrawAuthorized` 3, `WithdrawClaimed` 3, `WithdrawFeeSettled` 3, `WithdrawSettled` 0, all from V3; Treasury `TreasuryWithdraw` 6, `TreasuryDeposit` 0. Over blocks 26,000,000–26,075,812: 8 `DepositedWithId`. The seven other chains: 0 `Deposited` and 0 `WithdrawClaimed` logs from any emitter in the window (no deployment).
- **Sample transactions (receipts read):** deposit `0x961e04bc4b5891a51978a2cfb03ad4f89e23e4401c7216005b113c16b28606c1` (0.002 ETH `msg.value` → `TreasuryDeposit` from V3, then `Deposited` + `DepositedWithId`); authorization `0xf9e9e435f7175cbc27dd52662c4f2a449f6b7286fc937a5f684aebdb723fb68c` (`authorizeWithdraws` from the EOA → `WithdrawAuthorized`); claim `0xc3ad54562e22d1d9b70ff079a2d2fc225e5b46ea0b4e4172d25545e77e6ef0fd` (`claimWithdraw` → `TreasuryWithdraw` to the destination, `WithdrawClaimed`, `TreasuryWithdraw` to the EOA, `WithdrawFeeSettled`).

Authoritative sources (opened):
- L2BEAT — [Eclipse](https://l2beat.com/scaling/projects/eclipse) (contracts, roles, upgrade risk)
- Eclipse docs — [Bridges](https://docs.eclipse.xyz/developers/bridges) · [dev-docs: Eclipse Canonical Bridge](https://github.com/Eclipse-Laboratories-Inc/dev-docs/blob/main/developers/bridges/eclipse-canonical-bridge.md)
- [Eclipse-Laboratories-Inc/eclipse-deposit](https://github.com/Eclipse-Laboratories-Inc/eclipse-deposit) (`src/config.js`, `src/deposit.js`)
- Sourcify verified sources — [CanonicalBridgeV3](https://sourcify.dev/server/v2/contract/1/0x504392F02ee64D6B51aD3bCf7999E69EBe28b30a) · [CanonicalBridgeV2](https://sourcify.dev/server/v2/contract/1/0x867A8FcD5Bb6774d4d37fb342D669A35FF789a51) · [CanonicalBridge](https://sourcify.dev/server/v2/contract/1/0x2B08D7cF7EafF0f5f6623d9fB09b080726D4be11) · [Treasury impl](https://sourcify.dev/server/v2/contract/1/0xF1F7a359C3f33EE8A66bdCbf4c897D25Caf90978) · [EtherBridge impl](https://sourcify.dev/server/v2/contract/1/0x338017E0f208b4EAF8Cd4BbDc8bdabEFd0e39bE9) · [Mailbox impl](https://sourcify.dev/server/v2/contract/1/0x4ceF0fA54dC06CE0eA198DAb2F57D28A9deE712B)

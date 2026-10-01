# Chainflip — Topics, Selectors, Addresses (Ethereum + Arbitrum + BNB; NOT Base, Avalanche, Optimism, Polygon, Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the official mainnet address page (docs.chainflip.io), `chainflip-io/chainflip-eth-contracts` (master: `Vault.sol`, `KeyManager.sol`, `Deposit.sol`, `StateChainGateway.sol`, interfaces) and `chainflip-io/chainflip-backend` (`state-chain/primitives/src/chains.rs`, `chains/assets.rs`, `state-chain/chains/src/eth/deposit_address.rs`). Topics and selectors recomputed as `keccak256(sig)`; addresses existence-checked with `eth_getCode`; wiring read with `eth_call`; sample receipts decoded.
**Scope:** the Chainflip EVM contracts — Vault, KeyManager, AddressChecker, plus the Ethereum-only StateChainGateway and FLIP token — and the deposit-channel model, on Ethereum (1), Arbitrum One (42161) and BNB Smart Chain (56). Base, Avalanche, OP Mainnet, Polygon and Robinhood Chain (4663) have no Chainflip contract. Chainflip's other chains are not EVM (Bitcoin, Solana, Polkadot Assethub, Tron). Topics and selectors are chain-agnostic; addresses are network-specific.

Chainflip is a cross-chain AMM run by its own State Chain (a Substrate chain). Its validators hold one aggregate FROST Schnorr key per chain. On an EVM chain, the **Vault** holds all funds and executes every egress; the **KeyManager** stores the aggregate key and checks one signature (and nonce) per Vault call. The swap itself happens on the State Chain, so **no on-chain field links an EVM deposit to its payout**: the link is in Chainflip's State Chain and its APIs only.

Two ways in, one way out:

1. **Vault swap (on-chain source event).** The user (or an aggregator) calls `xSwapNative` / `xSwapToken` / `xCallNative` / `xCallToken` on the Vault. The Vault emits `SwapNative` / `SwapToken` / `XCallNative` / `XCallToken` with the destination chain, destination address and destination asset.
2. **Deposit channel (no source event).** A broker opens a channel on the State Chain; the user sends funds to a precomputed CREATE2 address. Nothing is emitted at deposit time (only the token's own `Transfer` for an ERC-20). Later the Vault deploys a `Deposit` contract at that address or calls `fetch` on it, and sweeps the funds. A native sweep emits `FetchedNative(sender = the channel address)`; an ERC-20 sweep emits only the token `Transfer` channel → Vault.
3. **Egress (no Chainflip event on success).** The validators sign `allBatch` / `transfer` / `transferBatch` / `executexSwapAndCall` / `executeActions`; the KeyManager emits `SignatureAccepted` and the Vault pays with a plain native transfer or an ERC-20 `Transfer` Vault → recipient. Refunds use the same path. Only failures emit a Vault event (`TransferNativeFailed`, `TransferTokenFailed`, `ExecuteActionsFailed`).

---

## 0. Contract families & versions

| Contract | Chains | Role | Upgradeable? |
|----------|--------|------|--------------|
| **Vault** | Ethereum `0xF5e10380213880111522dd0efD3dbb45b9f62Bcc`; Arbitrum and BNB `0x79001a5e762f3bEFC8e5871b42F6734e00498920` | Holds funds; vault swaps (source events); sweeps deposit channels; executes egress and CCM calls | **No** (immutable; can repoint its KeyManager) |
| **KeyManager** | Ethereum `0xcd351d3626Dc244730796A3168D315168eBf08Be`; Arbitrum and BNB `0xBFe612c77C2807Ac5a6A41F84436287578000275` | Stores the aggregate key, governance key and community key; consumes one nonce per signed call; emits `SignatureAccepted` | No |
| **Deposit** (one per channel) | CREATE2 children of each Vault | Channel address; forwards native coin to the Vault on receipt; `fetch(token)` for ERC-20 | No; reused for later channels |
| **AddressChecker** | Ethereum `0x79001a5e762f3bEFC8e5871b42F6734e00498920`; Arbitrum and BNB `0xc1B12993f760B654897F0257573202fba13D5481` | Read-only helper (balances, code checks) for the engines | No |
| **StateChainGateway** | Ethereum `0x6995Ab7c4D7F4B03f467Cf4c8E920427d9621DBd` | FLIP funding and redemption of State Chain accounts (validator bonds); FLIP issuer | No |
| **FLIP** | Ethereum `0x826180541412D574cf1336d22c0C0a287822678A` | Chainflip token (ERC-20); supply mirrored by the gateway | No |

**Chainflip chain ids and asset ids** (`ForeignChain` and `Asset` enums of `chainflip-backend`; `dstChain` and `dstToken` in the Vault events use them).

| `dstChain` | Chain | | `dstToken` | Asset |
|-----------|-------|-|-----------|-------|
| 1 | Ethereum | | 1 ETH, 2 FLIP, 3 USDC, 8 USDT, 14 WBTC, 21 cbBTC | Ethereum assets |
| 2 | Polkadot | | 4 DOT | |
| 3 | Bitcoin | | 5 BTC | |
| 4 | Arbitrum | | 6 ArbEth, 7 ArbUsdc, 15 ArbUsdt | |
| 5 | Solana | | 9 SOL, 10 SolUsdc, 16 SolUsdt | |
| 6 | Assethub | | 11 HubDot, 12 HubUsdt, 13 HubUsdc | |
| 7 | Tron | | 17 TRX, 18 TrxUsdt | |
| 8 | Bsc | | 19 BNB, 20 BscUsdt | |

Base, Avalanche, OP Mainnet, Polygon and Robinhood Chain have no `ForeignChain` id.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Vault — source-leg events (vault swaps)

| topic0 | Event | Side |
|--------|-------|------|
| `0x6757034e841d88190e95fa8a7570ce6cb721257474400c3282ec536eab810540` | `SwapNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, uint256 amount, address indexed sender, bytes cfParameters)` | **Source leg**, native coin in `msg.value` to the Vault. |
| `0x834b524d9f8ccbd31b00b671c896697b96eb4398c0f56e9386a21f5df61e3ce3` | `SwapToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, address srcToken, uint256 amount, address indexed sender, bytes cfParameters)` | **Source leg**, ERC-20 `transferFrom(sender, Vault)`. |
| `0x47705cc9a85c5f679e1f4e8e7fbd459b8267bc61fa3111ced6fe84f71d7d889e` | `XCallNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, uint256 amount, address indexed sender, bytes message, uint256 gasAmount, bytes cfParameters)` | Source leg with a destination call (CCM). |
| `0x030b52f4ea12be896482bc46f95fb31f1ac9457bc1a2a206981fbd18a69cc6e3` | `XCallToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, address srcToken, uint256 amount, address indexed sender, bytes message, uint256 gasAmount, bytes cfParameters)` | Same, ERC-20 input. |
| `0x9b06bfc39a72bc50d04ef282cdb1245b6257232b83e90f935f007d2689d82611` | `AddGasNative(bytes32 swapID, uint256 amount)` | Gas top-up for a CCM swap (value moves in). |
| `0x521975b77c7879e0f2a2ffca11f89c90bf9202dd4336fd5e1178fb744c6d1e2d` | `AddGasToken(bytes32 swapID, uint256 amount, address token)` | Same, ERC-20. |

### 1.2 Vault — deposit-channel sweep and egress failures

| topic0 | Event | Side |
|--------|-------|------|
| `0xa5df10d7a7c736bd7231e790267747aebface82ad6ee778d26a4aa99eb1c2f7b` | `FetchedNative(address indexed sender, uint256 amount)` | Native coin received by the Vault's `receive()`. `sender` = the **deposit channel**, not the user. |
| `0x2c024f929e1e2dec521388b8607f880d3bb3165478e3c80b1a4c280e0130d981` | `TransferNativeFailed(address indexed recipient, uint256 amount)` | Egress of native coin failed (8,000 gas forwarded); the coin stays in the Vault. **Status only.** |
| `0x158555118e14c8fb6d2e41d2bf4c3c75c8bcab740492ca50f44458a2bd021715` | `TransferTokenFailed(address indexed recipient, uint256 amount, address indexed token, bytes reason)` | Egress of an ERC-20 failed (e.g. a blacklisted recipient). **Status only.** |
| `0x15fe0355a655dcccafef64364dff99adb73fad83d9549ce53673f2bdc2485fd6` | `ExecuteActionsFailed(address indexed multicallAddress, uint256 amount, address indexed token, bytes reason)` | `executeActions` call failed. |

### 1.3 Vault / KeyManager / gateway — admin and signature events

| topic0 | Event | Emitter | Notes |
|--------|-------|---------|-------|
| `0xe2688b6900b89a8dc9b790e8ad7e598062004db7e424b7781144ffccf76c734b` | `SignatureAccepted((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, address signer)` | KeyManager | One per signed Vault or gateway call (every egress batch). **Status only**; `nonce` is the broadcast nonce. |
| `0x5cba64f32f2576e404f74394dc04611cce7416e299c94db0667d4e315e852521` | `AggKeySetByAggKey((uint256 pubKeyX, uint8 pubKeyYParity) oldAggKey, (uint256 pubKeyX, uint8 pubKeyYParity) newAggKey)` | KeyManager | Normal key rotation at each epoch. |
| `0xe441a6cf7a12870075eb2f6399c0de122bfe6cd8a75bfa83b05d5b611552532e` | `AggKeySetByGovKey((uint256 pubKeyX, uint8 pubKeyYParity) oldAggKey, (uint256 pubKeyX, uint8 pubKeyYParity) newAggKey)` | KeyManager | **Governance override of the aggregate key — high severity.** |
| `0x6049e088bb150ffb9041c7bfd3f7d4017d79a930d2d23e2f331eeffb0cb74297` | `GovKeySetByAggKey(address oldGovKey, address newGovKey)` | KeyManager | Governance key change. |
| `0xb79780665df55038fba66988b1b3f2eda919a59b75cd2581f31f8f04f58bec7c` | `GovKeySetByGovKey(address oldGovKey, address newGovKey)` | KeyManager | Governance key change. |
| `0x999bc9c97358a1254b8ba2c1e65893b34385bf27c448cb21af3f19eee6b809ce` | `CommKeySetByAggKey(address oldCommKey, address newCommKey)` | KeyManager | Community key change. |
| `0xb8529adc43e07de6ef9ce6a65ca2e5ad5f52b155e85bbbc28f7d3c165170deab` | `CommKeySetByCommKey(address oldCommKey, address newCommKey)` | KeyManager | Community key change. |
| `0x06e69d4af70b00b0c269b2707345abc134d9767085930456d9d03285f1eaf5c7` | `GovernanceAction(bytes32 message)` | KeyManager | Governance message. |
| `0xd18040e514983d65f088430e69091aea9bf07feaed3696a3faac1ccc34b5e3bc` | `UpdatedKeyManager(address keyManager)` | Vault, gateway | **The contract now trusts another KeyManager — high severity.** |
| `0x58e6c20b68c19f4d8dbc6206267af40b288342464b433205bb41e5b65c4016da` | `Suspended(bool suspended)` | Vault, gateway | Pause / unpause by governance. |
| `0x057c4cb09f128960151f04372028154acda40272f16360154961672989b59bad` | `CommunityGuardDisabled(bool communityGuardDisabled)` | Vault, gateway | Precondition for `govWithdraw` (emergency drain to the governance key). |

### 1.4 StateChainGateway and FLIP (Ethereum only)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xc1b5c1b3c1e294059714af16e812402029c9d8bf1d0d89770d3ff069dddc48db` | `Funded(bytes32 indexed nodeID, uint256 amount, address funder)` | FLIP in for a State Chain account. |
| `0x00595d7bd66cc5e1bac8c1f380818b52987790a5b3b3cbc753a7945469be2cd8` | `RedemptionRegistered(bytes32 indexed nodeID, uint256 amount, address indexed redeemAddress, uint48 startTime, uint48 expiryTime, address executor)` | Signed redemption queued. |
| `0x2b917410dde505b91c1ee8bf49bc98c4d80f9f6fde62c4aad7743e5c3fcd568f` | `RedemptionExecuted(bytes32 indexed nodeID, uint256 amount)` | FLIP paid out. |
| `0x2e395ce432fa118cf9b801546bae2c36a87aa9b514af0bec0df46bb534513de5` | `RedemptionExpired(bytes32 indexed nodeID, uint256 amount)` | |
| `0xff4b7a826623672c6944dc44d809008e2e1105180d110fd63986e841f15eb2ad` | `FlipSupplyUpdated(uint256 oldSupply, uint256 newSupply, uint256 stateChainBlockNumber)` | FLIP mint/burn sync. |
| `0xfb698a1f0614fe8250cab73f9e958d9eb3aa668918f243f3638dba6da247643d` | `GovernanceWithdrawal(address to, uint256 amount)` | **Emergency gateway drain — high severity.** |
| `0x09c1d94393b22192a9e1fc232a9accb31e0c1ad78f42b2f42f9da84e9931d16d` | `MinFundingChanged(uint256 oldMinFunding, uint256 newMinFunding)` | |
| `0x6d32c1367cc28eab61cca04e424f151519f02908af46776ba8373eaea407baa9` | `IssuerUpdated(address oldIssuer, address newIssuer)` | FLIP token: issuer changed. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

`SigData` = `(uint256 sig, uint256 nonce, address kTimesGAddress)`; `TransferParams` = `(address token, address recipient, uint256 amount)`; `DeployFetchParams` = `(bytes32 swapID, address token)`; `FetchParams` = `(address fetchContract, address token)`; `IMulticall.Call` = `(uint8 callType, address target, uint256 value, bytes callData, bytes payload)`. Native coin = token `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.

### 2.1 Vault — user entry points

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xdd687345` | `xSwapNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes cfParameters)` | Payable. Emits `SwapNative`. |
| `0x04fc7da0` | `xSwapToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, address srcToken, uint256 amount, bytes cfParameters)` | Emits `SwapToken`. |
| `0x07933dd2` | `xCallNative(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes message, uint256 gasAmount, bytes cfParameters)` | Emits `XCallNative`. |
| `0xbbddc2fb` | `xCallToken(uint32 dstChain, bytes dstAddress, uint32 dstToken, bytes message, uint256 gasAmount, address srcToken, uint256 amount, bytes cfParameters)` | Emits `XCallToken`. |
| `0x7161fb91` | `addGasNative(bytes32 swapID)` | Emits `AddGasNative`. |
| `0x2971198e` | `addGasToken(bytes32 swapID, uint256 amount, address token)` | Emits `AddGasToken`. |

### 2.2 Vault — signed calls (validators; each emits `SignatureAccepted` at the KeyManager)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5f8c0f9a` | `allBatch((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (bytes32 swapID, address token)[] deployFetchParamsArray, (address fetchContract, address token)[] fetchParamsArray, (address token, address recipient, uint256 amount)[] transferParamsArray)` | **Main egress and sweep call:** deploys channels, fetches, then pays. |
| `0x2ba5bc8a` | `allBatchV2((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (address fetchContract, address token)[] fetchParamsArray, (address token, address recipient, uint256 amount)[] transferParamsArray)` | Same without deployments. |
| `0xb554712f` | `transfer((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (address token, address recipient, uint256 amount) transferParams)` | Single egress. |
| `0xb267e7f6` | `transferFallback((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (address token, address recipient, uint256 amount) transferParams)` | Egress retry without the gas cap. |
| `0xdf5ed9ea` | `transferBatch((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (address token, address recipient, uint256 amount)[] transferParamsArray)` | Batch egress. |
| `0xcc5916d9` | `deployAndFetchBatch((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (bytes32 swapID, address token)[] deployFetchParamsArray)` | Deploys channel contracts (sweeps them in the constructor). |
| `0x7b884c5e` | `fetchBatch((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (address fetchContract, address token)[] fetchParamsArray)` | Sweeps already-deployed channels. |
| `0x5293178e` | `executexSwapAndCall((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (address token, address recipient, uint256 amount) transferParams, uint32 srcChain, bytes srcAddress, bytes message)` | CCM egress: pays `recipient` and calls `cfReceive`. |
| `0xb27588ef` | `executexCall((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, address recipient, uint32 srcChain, bytes srcAddress, bytes message)` | CCM call without funds (`cfReceivexCall`). |
| `0x49710b1b` | `executeActions((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (address token, address recipient, uint256 amount) transferParams, (uint8 callType, address target, uint256 value, bytes callData, bytes payload)[] calls, uint256 gasMulticall)` | Auxiliary actions through a multicall. |
| `0x448cfc85` | `updateKeyManager((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, address keyManager, bool omitChecks)` | Repoints the Vault. Emits `UpdatedKeyManager`. |

### 2.3 Governance (Vault and gateway)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe6400bbe` | `suspend()` | Governor only. Emits `Suspended(true)`. |
| `0x046f7da2` | `resume()` | Emits `Suspended(false)`. |
| `0xaae9ba43` | `disableCommunityGuard()` | Community key only. |
| `0x8d95e559` | `enableCommunityGuard()` | |
| `0x7484606f` | `govWithdraw(address[] tokens)` | **Emergency drain** of the listed tokens to the governance key; needs suspended + guard disabled + 3 days without a consumed nonce. |

### 2.4 KeyManager

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2cb2b862` | `consumeKeyNonce((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, bytes32 contractMsgHash)` | Called by the Vault and gateway; emits `SignatureAccepted`. |
| `0xc1c4a159` | `setAggKeyWithAggKey((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, (uint256 pubKeyX, uint8 pubKeyYParity) newAggKey)` | Key rotation. |
| `0x3189fbfd` | `setAggKeyWithGovKey((uint256 pubKeyX, uint8 pubKeyYParity) newAggKey)` | Governance override. |
| `0x28f57777` | `setGovKeyWithAggKey((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, address newGovKey)` | |
| `0xdd64f9bd` | `setGovKeyWithGovKey(address newGovKey)` | |
| `0x65b48463` | `setCommKeyWithAggKey((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, address newCommKey)` | |
| `0x26f07eb6` | `setCommKeyWithCommKey(address newCommKey)` | |
| `0x531840a7` | `govAction(bytes32 message)` | Emits `GovernanceAction`. |
| `0xcd1b4d20` | `getGovernanceKey()` | View. |
| `0x3f87b30f` | `getCommunityKey()` | View. |
| `0x53f0bb61` | `getLastValidateTime()` | View: time of the last consumed nonce. |

### 2.5 Other

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4b0cfc00` | `getKeyManager()` | Vault/gateway view. |
| `0x29b74201` | `getSuspendedState()` | Vault/gateway view. |
| `0xf109a0be` | `fetch(address token)` | Deposit channel: send the token balance to the Vault (Vault only). |
| `0x6055409b` | `fundStateChainAccount(bytes32 nodeID, uint256 amount)` | Gateway. Emits `Funded`. |
| `0x9d9f74bd` | `registerRedemption((uint256 sig, uint256 nonce, address kTimesGAddress) sigData, bytes32 nodeID, uint256 amount, address redeemAddress, uint48 expiryTime, address executor)` | Gateway. |
| `0x4e85ba01` | `executeRedemption(bytes32 nodeID)` | Gateway. |
| `0x4904ac5f` | `cfReceive(uint32 srcChain, bytes srcAddress, bytes message, address token, uint256 amount)` | CCM receiver callback on the recipient contract. |
| `0xb40a4c00` | `cfReceivexCall(uint32 srcChain, bytes srcAddress, bytes message)` | CCM receiver callback without funds. |

---

## 3. Addresses — Ethereum (chain ID 1)

Verified via `eth_getCode` on 2026-09-29; wiring read with `eth_call`.

| Role | Address | One-liner |
|------|---------|-----------|
| **Vault** | `0xF5e10380213880111522dd0efD3dbb45b9f62Bcc` | 19,788 B. `getKeyManager()` = KeyManager below; `getSuspendedState()` = false. |
| **KeyManager** | `0xcd351d3626Dc244730796A3168D315168eBf08Be` | 4,761 B. `getLastValidateTime()` = 2026-09-29 12:46:59 UTC. |
| **StateChainGateway** | `0x6995Ab7c4D7F4B03f467Cf4c8E920427d9621DBd` | 10,054 B. `getKeyManager()` = the same KeyManager; not suspended. |
| **FLIP** | `0x826180541412D574cf1336d22c0C0a287822678A` | 3,398 B. |
| AddressChecker | `0x79001a5e762f3bEFC8e5871b42F6734e00498920` | 1,275 B. **Same address as the Arbitrum/BNB Vault** — not a Vault here. |
| Governance key (Safe) | `0x38a4bcc04f5136e6408589a440f495d7ad0f34db` | 171 B Safe proxy (singleton `0xd9db270c1b5e3bd161e8c8503c55ceabee709552`), 3-of-6 owners. |
| Community key (Safe) | `0x57955e52966e8a1dd643a536a7eb1ef434890762` | 171 B Safe proxy. |
| Deployer (EOA) | `0xb9e6ef6fdb106bc8e1a001b9d7e8feaf8bebbc36` | EOA, nonce 238; created the contracts on all three chains. |

Not Chainflip on Ethereum: `0xBFe612c77C2807Ac5a6A41F84436287578000275` holds an unverified 332-byte contract made by the same deployer; it is **not** a KeyManager here.

## 4. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **Vault** | `0x79001a5e762f3bEFC8e5871b42F6734e00498920` | 19,788 B. `getKeyManager()` = KeyManager below; not suspended. |
| **KeyManager** | `0xBFe612c77C2807Ac5a6A41F84436287578000275` | 4,761 B. `getLastValidateTime()` = 2026-09-29 12:41:26 UTC. |
| AddressChecker | `0xc1B12993f760B654897F0257573202fba13D5481` | 1,275 B (same code as the Ethereum AddressChecker). |
| Governance and community key (Safe) | `0x538c748ed30b7ea82e04cb9040782e29922476d7` | 171 B Safe proxy (singleton `0x3e5c63644e683549055b9be8653de26e0b4cd36e`); both keys. |

## 5. Addresses — BNB Smart Chain (chain ID 56)

Listed on the official mainnet page; Chainflip added BSC (`ForeignChain` 8) in release 2.3.

| Role | Address | One-liner |
|------|---------|-----------|
| **Vault** | `0x79001a5e762f3bEFC8e5871b42F6734e00498920` | 19,765 B. `getKeyManager()` = KeyManager below; not suspended. |
| **KeyManager** | `0xBFe612c77C2807Ac5a6A41F84436287578000275` | 4,409 B. `getLastValidateTime()` = 0: **no signed call yet** on 2026-09-29. |
| AddressChecker | `0xc1B12993f760B654897F0257573202fba13D5481` | 2,685 B. |
| Governance key | `0xb9e6ef6fdb106bc8e1a001b9d7e8feaf8bebbc36` | **EOA** (the deployer, nonce 96). Community key = `0x0000000000000000000000000000000000000000`. |

---

## 6. Cross-chain summary

| Chain | ID | Vault | KeyManager | Gateway / FLIP | Window: vault swaps / `FetchedNative` / `SignatureAccepted` |
|-------|----|-------|------------|----------------|------------------------------------------------------------|
| Ethereum | 1 | `0xF5e10380213880111522dd0efD3dbb45b9f62Bcc` | `0xcd351d3626Dc244730796A3168D315168eBf08Be` | yes | `SwapNative` 4 + `SwapToken` 17 / 42 / 79 |
| Arbitrum One | 42161 | `0x79001a5e762f3bEFC8e5871b42F6734e00498920` | `0xBFe612c77C2807Ac5a6A41F84436287578000275` | — | `SwapToken` 6 / 0 / 4 |
| BNB Smart Chain | 56 | `0x79001a5e762f3bEFC8e5871b42F6734e00498920` | `0xBFe612c77C2807Ac5a6A41F84436287578000275` | — | 0 / 0 / 0 |
| Base | 8453 | — (`0x` at all six addresses) | — | — | 0 / 0 / 0 (any emitter) |
| Avalanche C-Chain | 43114 | — | — | — | 0 / 0 / 0 |
| OP Mainnet | 10 | — | — | — | 0 / 0 / 0 |
| Polygon PoS | 137 | — | — | — | 0 / 0 / 0 |
| Robinhood Chain | 4663 | — | — | — | 0 / 0 / 0 |

The Arbitrum and BNB contracts share addresses (same deployer and nonces) but not bytecode. On Ethereum the same nonces gave other contracts: `0x79001a5e762f3bEFC8e5871b42F6734e00498920` is the AddressChecker there. Key every contract on `(chain, address)`.

---

## 7. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Vault, KeyManager, StateChainGateway, AddressChecker, FLIP, Deposit | **Immutable** (no proxy) | Full bytecode; EIP-1967 slot empty; no upgrade function in source | None. The Vault and gateway can point to a new KeyManager (`updateKeyManager`, signed by the aggregate key; event `UpdatedKeyManager`). A new Vault needs a new deployment and a State Chain runtime change. |
| Governance / community keys | Safe proxies on Ethereum and Arbitrum; EOA on BNB | 171 B proxy, `masterCopy` in slot 0 | Safe owners |

---

## 8. Detection invariants & gotchas

1. **No on-chain link key.** A deposit (vault swap or channel) and its payout are joined only in the State Chain (swap request id, channel id, broadcast id) and Chainflip's APIs. On EVM, keep the source transaction hash, the channel address and the egress `SignatureAccepted.nonce`; do not try to pair by amount.
2. **The payout emits no Chainflip event.** Detect egress as an ERC-20 `Transfer` from the Vault, or a native internal transfer from the Vault, inside a signed call (`allBatch` `0x5f8c0f9a`, `transfer`, `transferBatch`, `executexSwapAndCall`, `executeActions`) with `SignatureAccepted` at the KeyManager. Sample: Ethereum `0x331e3d012014ac57f62644eae0ce0d6688ce8ab52067a3ead0d7b7d1a198dc97` pays 186.559580 USDC Vault → `0x1ed204749144b0ad3f340ff96f7f8ea1c2d01e46` with only `SignatureAccepted` (nonce 273,692).
3. **Deposit channels hide the user.** The user pays the channel address with a plain transfer. `FetchedNative.sender` is the channel, not the user (sample: `0xb70f181cb89153ba9c20fdd0bb7bfc867babc05d496ea01a888ec6b67c6b40aa`, a 2 ETH transfer from `0x36004ecfc122e5b66a37ae3ff102d41c9d0dcf5a` to channel `0xa5d37f389944a188823b89a8653c29734af355a9`, which the Vault receives in the same transaction). An ERC-20 sweep emits no Vault event at all: only `Transfer(channel → Vault)` inside `allBatch` (sample: Arbitrum `0x80d8e1deca78cfb2ba5fc8109d06cb7fd756ab58fda90891b6100096469f1bbe`, 150 USDC).
4. **Channel addresses are deterministic and reused.** Address = CREATE2(deployer = Vault, salt = channel id as a big-endian integer left-padded to 32 bytes, init code = `Deposit` bytecode + token address). Chainflip reuses an expired channel for a later swap, so one channel address serves many users.
5. **Vault-swap `sender` is the caller.** It is often an aggregator: in the samples, the Rango diamond `0x69460570c93f9de5e2edbc3052bf10125f0ca22d` on Ethereum and `0xda8057acb94905eb6025120cb2c38415fd81bfeb` on Arbitrum. The user is `tx.from` or inside `cfParameters` (refund address).
6. **Decode the destination.** `dstChain` uses Chainflip ids (§0), not EVM chain ids: 1 Ethereum, 3 Bitcoin, 4 Arbitrum, 5 Solana, 7 Tron, 8 BSC. `dstAddress` for Bitcoin is the ASCII address string (both Ethereum samples and the Arbitrum sample: `bc1q...`, `dstToken` 5 = BTC); for Solana it is 32 raw bytes; for EVM 20 bytes.
7. **`SignatureAccepted` is not a deposit.** It counts every signed call: egress batches, sweeps, key rotations, gateway redemptions. It is status only.
8. **High-severity triggers:** `AggKeySetByGovKey`, `GovKeySetBy*`, `CommKeySetBy*`, `UpdatedKeyManager`, `Suspended(true)`, `CommunityGuardDisabled(true)`, a `govWithdraw` call, `GovernanceWithdrawal`. `AggKeySetByAggKey` is the normal rotation.
9. **Large-transfer and drain triggers:** outflows from the Vault per token (ERC-20 `Transfer` from the Vault, native value out of the Vault), and `SwapNative`/`SwapToken` amounts in.
10. **BNB is new.** The BNB Vault and KeyManager exist, but the KeyManager had consumed no nonce and the governance key is still the deployer EOA on 2026-09-29. Treat any BNB activity as new.
11. **Address reuse across chains.** `0x79001a5e762f3bEFC8e5871b42F6734e00498920` is the Vault on Arbitrum and BNB, but the AddressChecker on Ethereum; `0xBFe612c77C2807Ac5a6A41F84436287578000275` is the KeyManager on Arbitrum and BNB, but an unrelated contract on Ethereum.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Vault topics =====
TOPIC_SWAP_NATIVE                = '\x6757034e841d88190e95fa8a7570ce6cb721257474400c3282ec536eab810540'
TOPIC_SWAP_TOKEN                 = '\x834b524d9f8ccbd31b00b671c896697b96eb4398c0f56e9386a21f5df61e3ce3'
TOPIC_XCALL_NATIVE               = '\x47705cc9a85c5f679e1f4e8e7fbd459b8267bc61fa3111ced6fe84f71d7d889e'
TOPIC_XCALL_TOKEN                = '\x030b52f4ea12be896482bc46f95fb31f1ac9457bc1a2a206981fbd18a69cc6e3'
TOPIC_ADD_GAS_NATIVE             = '\x9b06bfc39a72bc50d04ef282cdb1245b6257232b83e90f935f007d2689d82611'
TOPIC_ADD_GAS_TOKEN              = '\x521975b77c7879e0f2a2ffca11f89c90bf9202dd4336fd5e1178fb744c6d1e2d'
TOPIC_FETCHED_NATIVE             = '\xa5df10d7a7c736bd7231e790267747aebface82ad6ee778d26a4aa99eb1c2f7b'
TOPIC_TRANSFER_NATIVE_FAILED     = '\x2c024f929e1e2dec521388b8607f880d3bb3165478e3c80b1a4c280e0130d981'
TOPIC_TRANSFER_TOKEN_FAILED      = '\x158555118e14c8fb6d2e41d2bf4c3c75c8bcab740492ca50f44458a2bd021715'
TOPIC_EXECUTE_ACTIONS_FAILED     = '\x15fe0355a655dcccafef64364dff99adb73fad83d9549ce53673f2bdc2485fd6'
TOPIC_UPDATED_KEY_MANAGER        = '\xd18040e514983d65f088430e69091aea9bf07feaed3696a3faac1ccc34b5e3bc'
TOPIC_SUSPENDED                  = '\x58e6c20b68c19f4d8dbc6206267af40b288342464b433205bb41e5b65c4016da'
TOPIC_COMMUNITY_GUARD_DISABLED   = '\x057c4cb09f128960151f04372028154acda40272f16360154961672989b59bad'
-- ===== KeyManager topics =====
TOPIC_SIGNATURE_ACCEPTED         = '\xe2688b6900b89a8dc9b790e8ad7e598062004db7e424b7781144ffccf76c734b'
TOPIC_AGG_KEY_SET_BY_AGG_KEY     = '\x5cba64f32f2576e404f74394dc04611cce7416e299c94db0667d4e315e852521'
TOPIC_AGG_KEY_SET_BY_GOV_KEY     = '\xe441a6cf7a12870075eb2f6399c0de122bfe6cd8a75bfa83b05d5b611552532e'
TOPIC_GOV_KEY_SET_BY_AGG_KEY     = '\x6049e088bb150ffb9041c7bfd3f7d4017d79a930d2d23e2f331eeffb0cb74297'
TOPIC_GOV_KEY_SET_BY_GOV_KEY     = '\xb79780665df55038fba66988b1b3f2eda919a59b75cd2581f31f8f04f58bec7c'
TOPIC_COMM_KEY_SET_BY_AGG_KEY    = '\x999bc9c97358a1254b8ba2c1e65893b34385bf27c448cb21af3f19eee6b809ce'
TOPIC_COMM_KEY_SET_BY_COMM_KEY   = '\xb8529adc43e07de6ef9ce6a65ca2e5ad5f52b155e85bbbc28f7d3c165170deab'
TOPIC_GOVERNANCE_ACTION          = '\x06e69d4af70b00b0c269b2707345abc134d9767085930456d9d03285f1eaf5c7'
-- ===== StateChainGateway / FLIP topics (Ethereum) =====
TOPIC_FUNDED                     = '\xc1b5c1b3c1e294059714af16e812402029c9d8bf1d0d89770d3ff069dddc48db'
TOPIC_REDEMPTION_REGISTERED      = '\x00595d7bd66cc5e1bac8c1f380818b52987790a5b3b3cbc753a7945469be2cd8'
TOPIC_REDEMPTION_EXECUTED        = '\x2b917410dde505b91c1ee8bf49bc98c4d80f9f6fde62c4aad7743e5c3fcd568f'
TOPIC_REDEMPTION_EXPIRED         = '\x2e395ce432fa118cf9b801546bae2c36a87aa9b514af0bec0df46bb534513de5'
TOPIC_FLIP_SUPPLY_UPDATED        = '\xff4b7a826623672c6944dc44d809008e2e1105180d110fd63986e841f15eb2ad'
TOPIC_GOVERNANCE_WITHDRAWAL      = '\xfb698a1f0614fe8250cab73f9e958d9eb3aa668918f243f3638dba6da247643d'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_X_SWAP_NATIVE                = '\xdd687345'
SEL_X_SWAP_TOKEN                 = '\x04fc7da0'
SEL_X_CALL_NATIVE                = '\x07933dd2'
SEL_X_CALL_TOKEN                 = '\xbbddc2fb'
SEL_ALL_BATCH                    = '\x5f8c0f9a'
SEL_ALL_BATCH_V2                 = '\x2ba5bc8a'
SEL_TRANSFER                     = '\xb554712f'
SEL_TRANSFER_FALLBACK            = '\xb267e7f6'
SEL_TRANSFER_BATCH               = '\xdf5ed9ea'
SEL_DEPLOY_AND_FETCH_BATCH       = '\xcc5916d9'
SEL_FETCH_BATCH                  = '\x7b884c5e'
SEL_EXECUTE_X_SWAP_AND_CALL      = '\x5293178e'
SEL_EXECUTE_X_CALL               = '\xb27588ef'
SEL_EXECUTE_ACTIONS              = '\x49710b1b'
SEL_UPDATE_KEY_MANAGER           = '\x448cfc85'
SEL_GOV_WITHDRAW                 = '\x7484606f'
SEL_SUSPEND                      = '\xe6400bbe'
SEL_DISABLE_COMMUNITY_GUARD      = '\xaae9ba43'
SEL_SET_AGG_KEY_WITH_GOV_KEY     = '\x3189fbfd'
SEL_GET_LAST_VALIDATE_TIME       = '\x53f0bb61'

-- ===== Ethereum (1) =====
ETH_CF_VAULT                     = '\xf5e10380213880111522dd0efd3dbb45b9f62bcc'
ETH_CF_KEY_MANAGER               = '\xcd351d3626dc244730796a3168d315168ebf08be'
ETH_CF_STATE_CHAIN_GATEWAY       = '\x6995ab7c4d7f4b03f467cf4c8e920427d9621dbd'
ETH_CF_FLIP                      = '\x826180541412d574cf1336d22c0c0a287822678a'
ETH_CF_ADDRESS_CHECKER           = '\x79001a5e762f3befc8e5871b42f6734e00498920'   -- NOT a vault on Ethereum
ETH_CF_GOV_KEY_SAFE              = '\x38a4bcc04f5136e6408589a440f495d7ad0f34db'
ETH_CF_COMM_KEY_SAFE             = '\x57955e52966e8a1dd643a536a7eb1ef434890762'
ETH_CF_DEPLOYER_EOA              = '\xb9e6ef6fdb106bc8e1a001b9d7e8feaf8bebbc36'
-- ===== Arbitrum One (42161) =====
ARB_CF_VAULT                     = '\x79001a5e762f3befc8e5871b42f6734e00498920'
ARB_CF_KEY_MANAGER               = '\xbfe612c77c2807ac5a6a41f84436287578000275'
ARB_CF_ADDRESS_CHECKER           = '\xc1b12993f760b654897f0257573202fba13d5481'
ARB_CF_GOV_KEY_SAFE              = '\x538c748ed30b7ea82e04cb9040782e29922476d7'
-- ===== BNB Smart Chain (56) =====
BNB_CF_VAULT                     = '\x79001a5e762f3befc8e5871b42f6734e00498920'
BNB_CF_KEY_MANAGER               = '\xbfe612c77c2807ac5a6a41f84436287578000275'
BNB_CF_ADDRESS_CHECKER           = '\xc1b12993f760b654897f0257573202fba13d5481'
BNB_CF_GOV_KEY_EOA               = '\xb9e6ef6fdb106bc8e1a001b9d7e8feaf8bebbc36'
-- Base, Avalanche, OP Mainnet, Polygon, Robinhood Chain: no Chainflip contract
```

---

## 10. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` / `[0:4]` from `IVault.sol`, `IKeyManager.sol`, `IShared.sol` (structs written as tuples), `IAggKeyNonceConsumer.sol`, `IGovernanceCommunityGuarded.sol`, `IStateChainGateway.sol`, `IFLIP.sol`, `ICFReceiver.sol` and `IMulticall.sol` (enum `CallType` as `uint8`). Chain and asset ids from `chains.rs` (`Ethereum = 1 … Bsc = 8`) and the asset tests in `chains/assets.rs`. The CREATE2 salt rule from `get_salt` in `eth/deposit_address.rs`.
- **Addresses:** from the official mainnet address page (Ethereum, Arbitrum, BSC tables) and checked with `eth_getCode` on all eight chains: Vault, KeyManager and AddressChecker code on Ethereum, Arbitrum and BNB only; StateChainGateway and FLIP on Ethereum only; nothing on Base, Avalanche, OP Mainnet, Polygon or Robinhood Chain. Wiring by `eth_call`: `getKeyManager()` of each Vault (and of the gateway) returns the KeyManager of the same chain; `getSuspendedState()` = false; governance and community keys as in §3–§5. The Ethereum governance Safe returned 6 owners and threshold 3.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, any emitter):** `SwapNative` Ethereum 4, others 0; `SwapToken` Ethereum 17, Arbitrum 6, others 0; `FetchedNative` Ethereum 42, others 0; `SignatureAccepted` Ethereum 79, Arbitrum 4, others 0; `XCallNative`, `XCallToken`, `AddGas*`, `TransferNativeFailed`, `TransferTokenFailed`, `ExecuteActionsFailed`: 0 on all eight chains. Gateway on Ethereum: `RedemptionRegistered` 1, `RedemptionExecuted` 1, `Funded` 0; `AggKeySetByAggKey` 0 on Ethereum and Arbitrum. BNB: 0 for every topic (KeyManager `getLastValidateTime()` = 0). The Polygon `SignatureAccepted` count is from the same helper's earlier run (0); a re-run failed at the endpoint.
- **Sample receipts:** `SwapNative` `0xf7d6cef7081969fe4d6fa41a6dc9219abe8472f63fb37bfbee296aa6d5b219d1` (0.01 ETH, `xSwapNative`, `dstChain` 3, `dstToken` 5); `SwapToken` `0x179850571e36f89d94e4cc3119c94e587cb9f1b3724b10a90ba2e4b95d57a2df` (USDC from the Rango diamond to the Vault); `FetchedNative` `0xb70f181cb89153ba9c20fdd0bb7bfc867babc05d496ea01a888ec6b67c6b40aa`; egress `0x331e3d012014ac57f62644eae0ce0d6688ce8ab52067a3ead0d7b7d1a198dc97`; Arbitrum `SwapToken` `0x9c0ffc7206c028f5d8974774b6ac643d7166f4e7e34e2ef372aaea241d1cc047` and sweep `0x80d8e1deca78cfb2ba5fc8109d06cb7fd756ab58fda90891b6100096469f1bbe`.
- **Unverified:** the role of the 332-byte contract at `0xBFe612c77C2807Ac5a6A41F84436287578000275` on Ethereum (unverified source); the meaning of the `cfParameters` bytes beyond the refund address (not decoded).

Authoritative sources:
- [chainflip-io/chainflip-eth-contracts](https://github.com/chainflip-io/chainflip-eth-contracts) (`contracts/Vault.sol`, `contracts/KeyManager.sol`, `contracts/Deposit.sol`, `contracts/StateChainGateway.sol`, `contracts/interfaces/`)
- [chainflip-io/chainflip-backend](https://github.com/chainflip-io/chainflip-backend) (`state-chain/primitives/src/chains.rs`, `state-chain/primitives/src/chains/assets.rs`, `state-chain/chains/src/eth/deposit_address.rs`)
- Docs — [Mainnet Addresses](https://docs.chainflip.io/protocol/supported-chains-assets/mainnet-addresses) · [EVM Vault Design](https://docs.chainflip.io/protocol/vaults/evm-ethereum-vault-design) · [EVM Vault swaps](https://docs.chainflip.io/brokers/vault-swaps-api/evm) · [Validator setup (BSC in 2.3)](https://docs.chainflip.io/validators/mainnet/validator-setup)
- Explorers — [Etherscan Vault](https://etherscan.io/address/0xf5e10380213880111522dd0efd3dbb45b9f62bcc) · [Arbiscan Vault](https://arbiscan.io/address/0x79001a5e762f3befc8e5871b42f6734e00498920) · [BscScan Vault](https://bscscan.com/address/0x79001a5e762f3befc8e5871b42f6734e00498920) · [Blockscout Ethereum AddressChecker](https://eth.blockscout.com/address/0x79001a5e762f3bEFC8e5871b42F6734e00498920)

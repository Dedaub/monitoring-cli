# Gnosis Chain Bridges (xDai Bridge, AMB, Omnibridge) — Topics, Selectors, Addresses (Ethereum + deprecated BNB side; counterpart Gnosis Chain)

**Status:** verified on 2026-09-29 against Ethereum and BNB RPC (`eth_getCode`, `eth_call`, `eth_getLogs`), `eth_getCode` on the other target chains, one batched `eth_getCode` call to the public Gnosis RPC, the Gnosis Chain docs (bridge pages), and the Sourcify verified sources of every implementation.
**Scope:** the native bridges between Ethereum and Gnosis Chain (chain 100), all built from the tokenbridge code base: the **xDai bridge** (USDS/DAI ↔ native xDAI), the **Arbitrary Message Bridge (AMB)** and the **Omnibridge** (multi-token mediator on the AMB), plus the WETH router and the BridgeRouter entry points, and the deprecated BSC ↔ Gnosis AMB and Omnibridge on BNB Smart Chain. Gnosis Chain is outside the eight target chains; its side is listed for the link keys. Topics and selectors are chain-agnostic; addresses are network-specific.

**Trust model.** Each bridge is validated by an off-chain validator set: 4 of 7 signatures for the AMB and for the xDai bridge (separate `BridgeValidators` contracts, read live). A Gnosis Safe with 8 of 15 owners (`0x42F38ec5A75acCEc50054671233dfAC9C0E7A3F6`) owns and upgrades the Ethereum contracts with no timelock. The docs describe the same model ("4-of-7 Validator Multisig", "8-of-15 Multisig" governance) and state that the Hashi components are deprecated and do not affect message verification.

**The three flows on Ethereum.** xDai bridge: `relayTokens` locks **USDS** and emits `UserRequestForAffirmation(recipient, value, nonce)`; the validators mint native xDAI on Gnosis. The return leg is `executeSignatures`, which pays **DAI** (the bridge converts escrowed USDS to DAI) and emits `RelayedMessage(recipient, value, transactionHash)`. AMB: `requireToPassMessage` emits `UserRequestForAffirmation(messageId, encodedData)`; the return is `executeSignatures`/`safeExecuteSignatures*` → `RelayedMessage(sender, executor, messageId, status)`. Omnibridge: `relayTokens` locks an ERC-20 and calls the AMB (`TokensBridgingInitiated`); the return releases it (`TokensBridged`) inside an AMB `RelayedMessage`.

---

## 0. Contract families & versions

| Contract | Chain | Address | Role |
|----------|-------|---------|------|
| **xDai bridge** (`XDaiForeignBridge`, EternalStorageProxy) | Ethereum | `0x4aa42145Aa6Ebf72e164C9bBC74fbD3788045016` | Escrow of USDS (`erc20token()`); pays DAI. Implementation `0x257bdd093cab1bd39ebf837dcb60f33d031d7d49`. |
| **AMB** (`ForeignAMB`, EternalStorageProxy) | Ethereum | `0x4C36d2919e407f0Cc2Ee3c993ccF8ac26d9CE64e` | Message bridge, `sourceChainId()` 1 → `destinationChainId()` 100. Implementation `0x098f51bdfb5d6d319dd4fdf06b64773d25bd1316`. |
| **Omnibridge** (`ForeignOmnibridge`, proxy) | Ethereum | `0x88ad09518695c6c3712AC10a214bE5109a655671` | Escrow of every ERC-20 bridged to Gnosis. Implementation `0x8eb3b7d8498a6716904577b2579e1c313d48e347`. |
| WETH Omnibridge router | Ethereum | `0xa6439Ca0FCbA1d0F80df0bE6A17220feD9c9038a` | Wraps ETH to WETH and relays it through the Omnibridge. |
| BridgeRouter (transparent proxy) | Ethereum | `0x9a873656c19Efecbfb4f9FAb5B7acdeAb466a0B0` | Newer entry point that routes deposits and claims to the xDai bridge or the Omnibridge; emits no transfer event of its own. Implementation `0x74899961224538e423effd1a0ff3346adf3f4c56`. |
| AMB validators (`BridgeValidators`) | Ethereum | `0xed84a648b3c51432ad0fD1C2cD2C45677E9d4064` | 4 of 7. |
| xDai validators (`BridgeValidators`) | Ethereum | `0xe1579dEbdD2DF16Ebdb9db8694391fa74EeA201E` | 4 of 7. |
| BSC ↔ Gnosis AMB (`ForeignAMB`) | BNB | `0x05185872898b6f94AA600177EF41B9334B1FA48B` | **Deprecated**; `sourceChainId()` 56 → 100. |
| BSC ↔ Gnosis Omnibridge | BNB | `0xF0b456250DC9990662a6F25808cC74A6d1131Ea9` | **Deprecated**; mediator on Gnosis `0x59447362798334d3485c64D1e4870Fde2DDC0d75`. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 xDai bridge (emitter `0x4aa42145Aa6Ebf72e164C9bBC74fbD3788045016`)

| topic0 | Event |
|--------|-------|
| `0xf6968e689b3d8c24f22c10c2a3256bb5ca483a474e11bac08423baa049e38ae8` | `UserRequestForAffirmation(address recipient, uint256 value, bytes32 nonce)` — **source leg** (USDS locked); **no indexed field**; also emitted by `payInterest` with no user deposit |
| `0x4ab7d581336d92edbea22636a613e8e76c99ac7f91137c1523db38dbfb3bf329` | `RelayedMessage(address recipient, uint256 value, bytes32 transactionHash)` — **destination leg** (DAI paid); no indexed field |
| `0x222348fe8b30f078a8a4da2f55f16d24d70bc40d3ec49d295d7ad1d11e666887` | `PaidInterest(address indexed token, address to, uint256 value)` — interest of the escrow sent to the Gnosis interest receiver |
| `0xad4123ae17c414d9c6d2fec478b402e6b01856cc250fd01fbfd252fda0089d3c` | `DailyLimitChanged(uint256 newLimit)` |
| `0x9bebf928b90863f24cc31f726a3a7545efd409f1dcf552301b1ee3710da70d3b` | `ExecutionDailyLimitChanged(uint256 newLimit)` |
| `0x1d491a427d1f8cc0d447496f300fac39f7306122481d8e663451eb268274146b` | `UserRequestForAffirmation(address recipient, uint256 value)` — legacy two-field form; 0 logs in the pinned window |

### 1.2 AMB (emitter `0x4C36d2919e407f0Cc2Ee3c993ccF8ac26d9CE64e`; the BSC AMB emits the same)

| topic0 | Event |
|--------|-------|
| `0x482515ce3d9494a37ce83f18b72b363449458435fafdd7a53ddea7460fe01b58` | `UserRequestForAffirmation(bytes32 indexed messageId, bytes encodedData)` — message Ethereum → Gnosis (status: no value moves in the AMB itself) |
| `0x27333edb8bdcd40a0ae944fb121b5e2d62ea782683946654a0f5e607a908d578` | `RelayedMessage(address indexed sender, address indexed executor, bytes32 indexed messageId, bool status)` — message Gnosis → Ethereum executed; `status = false` means the call failed |
| `0x52264b89e0fceafb26e79fd49ef8a366eb6297483bf4035b027f0c99a7ad512e` | `GasPriceChanged(uint256 gasPrice)` — also on the xDai bridge |
| `0x4fb76205cd57c896b21511d2114137d8e901b4ccd659e1a0f97d6306795264fb` | `RequiredBlockConfirmationChanged(uint256 requiredBlockConfirmations)` — also on the xDai bridge |

### 1.3 Omnibridge (emitter `0x88ad09518695c6c3712AC10a214bE5109a655671`; the BSC Omnibridge emits the same)

| topic0 | Event |
|--------|-------|
| `0x59a9a8027b9c87b961e254899821c9a276b5efc35d1f7409ea4f291470f1629a` | `TokensBridgingInitiated(address indexed token, address indexed sender, uint256 value, bytes32 indexed messageId)` — **source leg** |
| `0x9afd47907e25028cdaca89d193518c302bbb128617d5a992c5abd45815526593` | `TokensBridged(address indexed token, address indexed recipient, uint256 value, bytes32 indexed messageId)` — **destination leg** |
| `0x07b5483b8e4bd8ea240a474d5117738350e7d431e3668c48a97910b0b397796a` | `FailedMessageFixed(bytes32 indexed messageId, address token, address recipient, uint256 value)` — **refund** of a message that failed on the other side |
| `0x78d063210f4fb6b4cc932390bb8045fa2465e51349590182dab8b9e84c57a6ee` | `NewTokenRegistered(address indexed nativeToken, address indexed bridgedToken)` — a bridged representation was created |
| `0xca0b3dabefdbd8c72c0a9cf4a6e9d107da897abf036ef3f3f3b010cdd2594159` | `DailyLimitChanged(address indexed token, uint256 newLimit)` |
| `0x4c177b42dbe934b3abbc0208c11a42e46589983431616f1710ab19969c5ed62e` | `ExecutionDailyLimitChanged(address indexed token, uint256 newLimit)` |

### 1.4 Validators and proxies (admin)

| topic0 | Event |
|--------|-------|
| `0xe366c1c0452ed8eec96861e9e54141ebff23c9ec89fe27b996b45f5ec3884987` | `ValidatorAdded(address indexed validator)` — `BridgeValidators`; **a new signer** |
| `0xe1434e25d6611e0db941968fdc97811c982ac1602e951637d206f5fdda9dd8f1` | `ValidatorRemoved(address indexed validator)` |
| `0x10dbc913050d3180c3b99f7da91fd514af7cbc9c1bb59a0da5d2bc38f0cf395a` | `RequiredSignaturesChanged(uint256 requiredSignatures)` — **the threshold changed** |
| `0x4289d6195cf3c2d2174adf98d0e19d4d2d08887995b99cb7b100e7ffe795820e` | `Upgraded(uint256 version, address indexed implementation)` — EternalStorageProxy upgrade (not the ERC-1967 `Upgraded(address)`) |
| `0x5a3e66efaa1e445ebd894728a69d6959842ea1e97bd79b892797106e270efcd9` | `ProxyOwnershipTransferred(address previousOwner, address newOwner)` — EternalStorageProxy owner changed |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address previousOwner, address newOwner)` — bridge and validator owner (unindexed form; same topic0 as the OpenZeppelin event) |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 xDai bridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x01e4f53a` | `relayTokens(address _receiver, uint256 _amount)` | **Deposit**: `transferFrom` USDS → bridge; emits `UserRequestForAffirmation`. The Omnibridge has the same selector (`relayTokens(address,uint256)` with a token argument): check `tx.to`. |
| `0x3f7658fd` | `executeSignatures(bytes message, bytes signatures)` | **Payout** with 4 validator signatures; emits `RelayedMessage`. Same selector on the AMB and the BridgeRouter. |
| `0x1e86b291` | `executeSignaturesGSN(bytes message, bytes signatures, uint256 maxTokensFee)` | Relayed payout. |
| `0x1b7623be` | `payInterest(address _token, uint256 _amount)` | Sends interest to Gnosis (`PaidInterest` + `UserRequestForAffirmation`). |
| `0xb20d30a9` | `setDailyLimit(uint256 _dailyLimit)` | Owner. |
| `0x3dd95d1b` | `setExecutionDailyLimit(uint256 _dailyLimit)` | Owner. |
| `0x904377ec` | `setInterestReceiver(address _token, address _receiver)` | Owner. |
| `0x69ffa08a` | `claimTokens(address _token, address _to)` | Owner; sweeps stray tokens (same selector on the AMB and Omnibridge). |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner. |
| `0x1dcea427` | `erc20token()` | View → USDS `0xdC035D45d973E3EC169d2276DDab16f1e407384F`. |
| `0x67eeba0c` | `dailyLimit()` | View; 10,000,000 USDS. |
| `0x43b37dd3` | `executionDailyLimit()` | View; 15,000,000 DAI. |

### 2.2 AMB

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xdc8601b3` | `requireToPassMessage(address _contract, bytes _data, uint256 _gas)` | Sends a message to Gnosis; emits `UserRequestForAffirmation`; returns the `messageId`. |
| `0xeaa820d7` | `safeExecuteSignatures(bytes _data, bytes _signatures)` | Executes a Gnosis message; emits `RelayedMessage`. |
| `0xe6d562a1` | `safeExecuteSignaturesWithGasLimit(bytes _data, bytes _signatures, uint32 _gas)` | Same, explicit gas. |
| `0x23caab49` | `safeExecuteSignaturesWithAutoGasLimit(bytes _data, bytes _signatures)` | Same, used by relayers; also a BridgeRouter selector. |
| `0x467ad35a` | `setChainIds(uint256 _sourceChainId, uint256 _destinationChainId)` | Owner. |
| `0x7bac29c7` | `setMaxGasPerTx(uint256 _maxGasPerTx)` | Owner; live value 4,000,000. |
| `0x1544298e` | `sourceChainId()` | View; 1 (56 on the BSC AMB). |
| `0xb0750611` | `destinationChainId()` | View; 100. |

### 2.3 Omnibridge, routers, validators, proxy

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xad58bdd1` | `relayTokens(address token, address _receiver, uint256 _value)` | **Omnibridge deposit**; emits `TokensBridgingInitiated`. Same selector on the BridgeRouter (`relayTokens(address _token, address _receiver, uint256 _amount)`, `payable`). |
| `0xd7405481` | `relayTokensAndCall(address token, address _receiver, uint256 _value, bytes _data)` | Deposit with a call on Gnosis. |
| `0xa4c0ed36` | `onTokenTransfer(address _from, uint256 _value, bytes _data)` | ERC-677 `transferAndCall` deposit. |
| `0x272255bb` | `handleNativeTokens(address _token, address _recipient, uint256 _value)` | AMB-only; releases an Ethereum-native token (`TokensBridged`). |
| `0x125e4cfb` | `handleBridgedTokens(address _token, address _recipient, uint256 _value)` | AMB-only; mints a Gnosis-native token's representation. |
| `0x2ae87cdd` | `deployAndHandleBridgedTokens(address _token, string _name, string _symbol, uint8 _decimals, address _recipient, uint256 _value)` | AMB-only; first transfer of a Gnosis-native token (`NewTokenRegistered`). |
| `0x9a4a4395` | `requestFailedMessageFix(bytes32 _messageId)` | Asks the other side to refund a failed message. |
| `0x0950d515` | `fixFailedMessage(bytes32 _messageId)` | AMB-only; refund; emits `FailedMessageFixed`. |
| `0x2803212f` | `setDailyLimit(address _token, uint256 _dailyLimit)` | Owner. |
| `0x0b26cf66` | `setBridgeContract(address _bridgeContract)` | Owner; **changes the AMB the mediator trusts**. |
| `0x6e5d6bea` | `setMediatorContractOnOtherSide(address _mediatorContract)` | Owner. |
| `0xd0342acd` | `fixMediatorBalance(address _token, address _receiver)` | Owner. |
| `0x01a754ff` | `wrapAndRelayTokens()` | WETH router; `payable`; ETH → WETH → Omnibridge. |
| `0xf52cbf0e` | `wrapAndRelayTokens(address _receiver)` | WETH router. |
| `0x0505e94d` | `setRoute(address _token, address _route)` | BridgeRouter owner. |
| `0x4d238c8e` | `addValidator(address _validator)` | Validators owner; emits `ValidatorAdded`. |
| `0x40a141ff` | `removeValidator(address _validator)` | Validators owner. |
| `0x7d2b9cc0` | `setRequiredSignatures(uint256 _requiredSignatures)` | Validators owner. |
| `0x5890ef79` | `validatorList()` | Validators view. |
| `0x3ad06d16` | `upgradeTo(uint256 version, address implementation)` | EternalStorageProxy; upgradeability owner only. |
| `0xa9c45fcb` | `upgradeToAndCall(uint256 version, address implementation, bytes data)` | EternalStorageProxy. |
| `0x6fde8202` | `upgradeabilityOwner()` | View → the 8-of-15 Safe. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on 2026-09-29. Wiring read live: Omnibridge `bridgeContract()` → the AMB, `mediatorContractOnOtherSide()` → the Gnosis Omnibridge; AMB and xDai `validatorContract()` → the two validator sets; `upgradeabilityOwner()` of the xDai bridge, the AMB and the Omnibridge, and `owner()` of the Omnibridge and the BridgeRouter → the Safe.

| Role | Address | One-liner |
|------|---------|-----------|
| **xDai bridge** | `0x4aa42145Aa6Ebf72e164C9bBC74fbD3788045016` | USDS escrow; 1,137-byte proxy. |
| **AMB** | `0x4C36d2919e407f0Cc2Ee3c993ccF8ac26d9CE64e` | 992-byte proxy. |
| **Omnibridge** | `0x88ad09518695c6c3712AC10a214bE5109a655671` | ERC-20 escrow; 992-byte proxy. |
| WETH Omnibridge router | `0xa6439Ca0FCbA1d0F80df0bE6A17220feD9c9038a` | Immutable. |
| BridgeRouter | `0x9a873656c19Efecbfb4f9FAb5B7acdeAb466a0B0` | Admin slot → ProxyAdmin `0xd7e65a32bed4ce8cc57ec188f2bbb8016dc4b1cd`; `owner()` = the Safe. |
| AMB validators | `0xed84a648b3c51432ad0fD1C2cD2C45677E9d4064` | `BridgeValidators`, implementation `0xd83893f31aa1b6b9d97c9c70d3492fe38d24d218`. |
| xDai validators | `0xe1579dEbdD2DF16Ebdb9db8694391fa74EeA201E` | `BridgeValidators`, implementation `0x6943a218d58135793f1fe619414ed476c37ad65a`. |
| Governance Safe (8 of 15) | `0x42F38ec5A75acCEc50054671233dfAC9C0E7A3F6` | Owner and upgrader of the Ethereum contracts. |
| Keeper (EOA) | `0xC5cD1e53839eeD4d0A38f80C610e77bD07120c90` | EOA (no code, nonce 1,660), listed in the docs. |
| USDS (the escrowed token) | `0xdC035D45d973E3EC169d2276DDab16f1e407384F` | `erc20token()` of the xDai bridge. |

## 4. Addresses — BNB Smart Chain (chain ID 56), deprecated

The docs state: "BSC-GC is deprecated, please avoid interacting with the contract." Both contracts still have code (read 2026-09-29).

| Role | Address | One-liner |
|------|---------|-----------|
| BSC ↔ Gnosis AMB | `0x05185872898b6f94AA600177EF41B9334B1FA48B` | `ForeignAMB` proxy (992 bytes), implementation `0xa93ee7b4a7215f7e725437a6b6d7a4e7fe1dd8f0`, validators `0xfce050274760d7c1ab809271fb753dcedac811b8`; `sourceChainId()` 56, `destinationChainId()` 100. |
| BSC ↔ Gnosis Omnibridge | `0xF0b456250DC9990662a6F25808cC74A6d1131Ea9` | Mediator proxy (1,222 bytes), implementation `0xc035c3982174547430647ca3157de608c8bcc416` (`ForeignOmnibridge`, the same events as on Ethereum); `bridgeContract()` → the BSC AMB. |
| Owner Safe | `0xcd29e5c0031c42f9e78291ef5d5148a5e618e5bc` | `upgradeabilityOwner()` of both. |

Gnosis Chain counterparts (chain 100, outside the eight; from the docs and checked with `eth_getCode` on the public Gnosis RPC): xDai home bridge `0x7301CFA0e1756B71869E93d4e4Dca5c7d0eb0AA6` (1,137 bytes), AMB home `0x75Df5AF045d91108662D8080fD1FEFAd6aA0bb59` (992 bytes), Omnibridge home `0xf6A78083ca3e2a662D6dd1703c939c8aCE2e268d` (992 bytes), BSC Omnibridge home `0x59447362798334d3485c64D1e4870Fde2DDC0d75` (1,222 bytes); validator contracts `0xA280feD8D7CaD9a76C8b50cA5c33c2534fFa5008` (AMB) and `0xB289f0e6fBDFf8EEE340498a56e1787B303F1B6D` (xDai); bridge interest receiver `0x670daeaF0F1a5e336090504C68179670B5059088`.

---

## 5. Cross-chain summary

| Chain | ID | xDai bridge | AMB | Omnibridge | Note |
|-------|----|-------------|-----|------------|------|
| **Ethereum** | 1 | ✅ `0x4aa42145Aa6Ebf72e164C9bBC74fbD3788045016` | ✅ `0x4C36d2919e407f0Cc2Ee3c993ccF8ac26d9CE64e` | ✅ `0x88ad09518695c6c3712AC10a214bE5109a655671` | Live. |
| BNB Smart Chain | 56 | — | ⚠️ `0x05185872898b6f94AA600177EF41B9334B1FA48B` | ⚠️ `0xF0b456250DC9990662a6F25808cC74A6d1131Ea9` | Deprecated BSC ↔ Gnosis pair; 0 AMB and 0 Omnibridge events in the pinned window |
| Base | 8453 | — | — | — | no deployment: `eth_getCode` = `0x` at the three Ethereum addresses; not in the docs |
| Arbitrum One | 42161 | — | — | — | same |
| Optimism | 10 | — | — | — | same |
| Polygon PoS | 137 | — | — | — | same |
| Avalanche C-Chain | 43114 | — | — | — | same |
| Robinhood Chain | 4663 | — | — | — | same |

The counterparty is **Gnosis Chain** (chain 100). The AMB uses EVM chain ids (`sourceChainId`, `destinationChainId`) and encodes its own bridge id in every `messageId` (§7).

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| xDai bridge, AMB, Omnibridge, both validator sets (Ethereum and BNB) | tokenbridge `EternalStorageProxy` (not ERC-1967) | `implementation()` (`0x5c60da1b`) and `upgradeabilityOwner()` (`0x6fde8202`) getters; `version()`; the ERC-1967 slots are empty. | `upgradeabilityOwner()` = the 8-of-15 Safe on Ethereum, `0xcd29e5c0031c42f9e78291ef5d5148a5e618e5bc` on BNB. No timelock. Watch `Upgraded(uint256,address)` (`0x4289d6195cf3c2d2174adf98d0e19d4d2d08887995b99cb7b100e7ffe795820e` is not ERC-1967). |
| BridgeRouter | ERC-1967 transparent proxy | admin slot → ProxyAdmin `0xd7e65a32bed4ce8cc57ec188f2bbb8016dc4b1cd`; impl slot → `0x74899961224538e423effd1a0ff3346adf3f4c56`. | ProxyAdmin; `owner()` of the router = the Safe. Watch ERC-1967 `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. |
| WETH Omnibridge router | Immutable | Full runtime (3,269 bytes). | Owner can `claimTokens` only. |

---

## 7. Detection invariants & gotchas

1. **The AMB link key.** `messageId` = `0x00050000` (4 bytes, packing version) + a 20-byte bridge id (`keccak256(abi.encodePacked(sourceChainId, amb address))`, masked) + an 8-byte nonce. It is topic 1 of the AMB `UserRequestForAffirmation`, topic 3 of `RelayedMessage` and topic 3 of both Omnibridge events, on chain on both sides.
2. **Omnibridge deposit** = ERC-20 `Transfer(user → Omnibridge)` + AMB `UserRequestForAffirmation(messageId)` + `TokensBridgingInitiated(token, sender, value, messageId)`. **Payout** = AMB `safeExecuteSignaturesWithAutoGasLimit` (a relayer) → `Transfer(Omnibridge → recipient)` + `TokensBridged` + AMB `RelayedMessage(sender = the Gnosis mediator, executor = the Ethereum mediator, messageId, status)`.
3. **xDai deposit** = USDS `Transfer(user or router → xDai bridge)` + `UserRequestForAffirmation(recipient, value, nonce)` with **no indexed topic**: decode the data. **Payout** = `executeSignatures` → DAI minted from USDS inside the bridge, then DAI `Transfer(xDai bridge → recipient)` + `RelayedMessage(recipient, value, transactionHash)`. Users deposit USDS but receive DAI.
4. **Two events named `UserRequestForAffirmation`.** The xDai one (`0xf6968e689b3d8c24f22c10c2a3256bb5ca483a474e11bac08423baa049e38ae8`) and the AMB one (`0x482515ce3d9494a37ce83f18b72b363449458435fafdd7a53ddea7460fe01b58`) have different topic0 values; `RelayedMessage` also has two forms (`0x4ab7d581336d92edbea22636a613e8e76c99ac7f91137c1523db38dbfb3bf329` xDai, `0x27333edb8bdcd40a0ae944fb121b5e2d62ea782683946654a0f5e607a908d578` AMB). Key on emitter and topic0 together.
5. **`payInterest` is not a user deposit.** It emits `PaidInterest` and an xDai `UserRequestForAffirmation` to the interest receiver with no inbound USDS transfer. Exclude it from deposit volume.
6. **Native ETH goes through the WETH router.** For an ETH deposit, `TokensBridgingInitiated.sender` is the WETH router `0xa6439Ca0FCbA1d0F80df0bE6A17220feD9c9038a`, not the user; take the user from `tx.from`. Deposits through the BridgeRouter or an aggregator show the router as the ERC-20 sender.
7. **Refund path.** When a message fails on Gnosis (`RelayedMessage.status = false` there), anyone can call `requestFailedMessageFix` on Gnosis; the returned AMB message calls `fixFailedMessage` on Ethereum, which returns the tokens and emits `FailedMessageFixed(messageId, token, recipient, value)`.
8. **PulseChain forks emit the same topics.** The PulseChain bridge is a fork of this code: on Ethereum its AMB `0xd0764fae29e0a6a96ff685f71cfc685456d5636c` (`sourceChainId()` 1 → `destinationChainId()` 369) and mediators `0x1715a3e4a142d8b698131108995174f37aeba10d` and `0xe20e337db2a00b1c37139c873b92a0aad3f468bf` emitted more `RelayedMessage`, `UserRequestForAffirmation`, `TokensBridgingInitiated` and `TokensBridged` logs in the pinned window than the Gnosis contracts did; on BNB its AMB `0x8c0db248e87f53e53f7d19a8bd1cfab16f5b69e7` (56 → 369) and mediator `0xb4005881e81a6ecd2c1f75d58e8e41f28d59c6b1` do the same. Another mediator on BNB (`0xead277922a7f4064522e9b4a3a23635c3deb82ce`, on AMB `0xb066e69bd0ab1bbef358a117c570d6d80c7dcfc7`) and several non-mediator contracts on Ethereum, Base, Arbitrum and Optimism also emit `TokensBridged(address,address,uint256,bytes32)`. **Always filter by the addresses in §3–§4.**
9. **Drain and admin triggers.** `ValidatorAdded` / `ValidatorRemoved` / `RequiredSignaturesChanged` on either validator set; `Upgraded(uint256,address)` and `ProxyOwnershipTransferred` on any proxy; `OwnershipTransferred`; `setBridgeContract` / `setMediatorContractOnOtherSide` calls on the Omnibridge; daily-limit changes. A payout larger than `executionDailyLimit` reverts, so a limit raise just before a large payout is a signal.
10. **The BSC pair is deprecated, not destroyed.** Its contracts still have code on BNB and share every topic0 with the Ethereum contracts. Key on `(chain id, address)`.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== xDai bridge topics =====
TOPIC_XDAI_USER_REQUEST_AFFIRMATION = '\xf6968e689b3d8c24f22c10c2a3256bb5ca483a474e11bac08423baa049e38ae8'
TOPIC_XDAI_RELAYED_MESSAGE       = '\x4ab7d581336d92edbea22636a613e8e76c99ac7f91137c1523db38dbfb3bf329'
TOPIC_XDAI_PAID_INTEREST         = '\x222348fe8b30f078a8a4da2f55f16d24d70bc40d3ec49d295d7ad1d11e666887'
TOPIC_XDAI_USER_REQUEST_LEGACY   = '\x1d491a427d1f8cc0d447496f300fac39f7306122481d8e663451eb268274146b'
-- ===== AMB topics =====
TOPIC_AMB_USER_REQUEST_AFFIRMATION = '\x482515ce3d9494a37ce83f18b72b363449458435fafdd7a53ddea7460fe01b58'
TOPIC_AMB_RELAYED_MESSAGE        = '\x27333edb8bdcd40a0ae944fb121b5e2d62ea782683946654a0f5e607a908d578'
-- ===== Omnibridge topics =====
TOPIC_TOKENS_BRIDGING_INITIATED  = '\x59a9a8027b9c87b961e254899821c9a276b5efc35d1f7409ea4f291470f1629a'
TOPIC_TOKENS_BRIDGED             = '\x9afd47907e25028cdaca89d193518c302bbb128617d5a992c5abd45815526593'
TOPIC_FAILED_MESSAGE_FIXED       = '\x07b5483b8e4bd8ea240a474d5117738350e7d431e3668c48a97910b0b397796a'
TOPIC_NEW_TOKEN_REGISTERED       = '\x78d063210f4fb6b4cc932390bb8045fa2465e51349590182dab8b9e84c57a6ee'
-- ===== Admin topics =====
TOPIC_VALIDATOR_ADDED            = '\xe366c1c0452ed8eec96861e9e54141ebff23c9ec89fe27b996b45f5ec3884987'
TOPIC_VALIDATOR_REMOVED          = '\xe1434e25d6611e0db941968fdc97811c982ac1602e951637d206f5fdda9dd8f1'
TOPIC_REQUIRED_SIGNATURES_CHANGED = '\x10dbc913050d3180c3b99f7da91fd514af7cbc9c1bb59a0da5d2bc38f0cf395a'
TOPIC_ESP_UPGRADED               = '\x4289d6195cf3c2d2174adf98d0e19d4d2d08887995b99cb7b100e7ffe795820e'
TOPIC_PROXY_OWNERSHIP_TRANSFERRED = '\x5a3e66efaa1e445ebd894728a69d6959842ea1e97bd79b892797106e270efcd9'

-- ===== Selectors =====
SEL_RELAY_TOKENS_2               = '\x01e4f53a'
SEL_RELAY_TOKENS_3               = '\xad58bdd1'
SEL_EXECUTE_SIGNATURES           = '\x3f7658fd'
SEL_SAFE_EXECUTE_SIGNATURES_AUTO = '\x23caab49'
SEL_REQUIRE_TO_PASS_MESSAGE      = '\xdc8601b3'
SEL_PAY_INTEREST                 = '\x1b7623be'
SEL_FIX_FAILED_MESSAGE           = '\x0950d515'
SEL_REQUEST_FAILED_MESSAGE_FIX   = '\x9a4a4395'
SEL_WRAP_AND_RELAY_TOKENS        = '\x01a754ff'
SEL_ADD_VALIDATOR                = '\x4d238c8e'
SEL_SET_REQUIRED_SIGNATURES      = '\x7d2b9cc0'
SEL_ESP_UPGRADE_TO               = '\x3ad06d16'

-- ===== Addresses — Ethereum (chain ID 1) =====
ETH_GNO_XDAI_BRIDGE              = '\x4aa42145aa6ebf72e164c9bbc74fbd3788045016'
ETH_GNO_AMB                      = '\x4c36d2919e407f0cc2ee3c993ccf8ac26d9ce64e'
ETH_GNO_OMNIBRIDGE               = '\x88ad09518695c6c3712ac10a214be5109a655671'
ETH_GNO_WETH_ROUTER              = '\xa6439ca0fcba1d0f80df0be6a17220fed9c9038a'
ETH_GNO_BRIDGE_ROUTER            = '\x9a873656c19efecbfb4f9fab5b7acdeab466a0b0'
ETH_GNO_AMB_VALIDATORS           = '\xed84a648b3c51432ad0fd1c2cd2c45677e9d4064'
ETH_GNO_XDAI_VALIDATORS          = '\xe1579debdd2df16ebdb9db8694391fa74eea201e'
ETH_GNO_GOVERNANCE_SAFE          = '\x42f38ec5a75accec50054671233dfac9c0e7a3f6'
ETH_GNO_KEEPER_EOA               = '\xc5cd1e53839eed4d0a38f80c610e77bd07120c90'
-- ===== Addresses — BNB (chain ID 56), deprecated =====
BNB_GNO_AMB                      = '\x05185872898b6f94aa600177ef41b9334b1fa48b'
BNB_GNO_OMNIBRIDGE               = '\xf0b456250dc9990662a6f25808cc74a6d1131ea9'
-- ===== Gnosis Chain (chain 100, outside the eight) =====
GNOSIS_XDAI_HOME_BRIDGE          = '\x7301cfa0e1756b71869e93d4e4dca5c7d0eb0aa6'
GNOSIS_AMB_HOME                  = '\x75df5af045d91108662d8080fd1fefad6aa0bb59'
GNOSIS_OMNIBRIDGE_HOME           = '\xf6a78083ca3e2a662d6dd1703c939c8ace2e268d'
-- Base, Arbitrum, Optimism, Polygon, Avalanche, Robinhood: no deployment
```

---

## 9. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` (and `[0:4]`) from the Sourcify verified ABIs of `XDaiForeignBridge`, `ForeignAMB`, `ForeignOmnibridge`, `WETHOmnibridgeRouter`, `BridgeRouter`, `BridgeValidators` and `EternalStorageProxy`; the `messageId` layout from `MessageDelivery.sol` and `VersionableAMB.sol` in the verified AMB source.
- **Addresses:** from the Gnosis docs (xDai bridge, AMB and Omnibridge pages), each existence-checked with `eth_getCode`; implementations, validators, owners, chain ids and the Omnibridge wiring read with the getters named in §3; the BSC contracts from their getters (`sourceChainId()` 56 → 100, `bridgeContract()`, `mediatorContractOnOtherSide()`); the Gnosis-side contracts with one batched `eth_getCode` call to `rpc.gnosischain.com` (`eth_chainId` = 100). `eth_getCode` = `0x` at the three Ethereum addresses on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain.
- **State:** validators `requiredSignatures()` 4 and `validatorCount()` 7 (both sets); the Safe `getThreshold()` 8 of 15 owners; xDai `erc20token()` = USDS, `dailyLimit()` 10,000,000, `maxPerTx()` 9,999,999, `executionDailyLimit()` 15,000,000, `executionMaxPerTx()` 10,000,000; `isInterestEnabled(USDS)` = true, `interestReceiver(USDS)` = `0x670daeaF0F1a5e336090504C68179670B5059088`; AMB `maxGasPerTx()` 4,000,000.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26,072,222–26,075,812):** AMB `RelayedMessage` 30 and `UserRequestForAffirmation` 28; Omnibridge `TokensBridgingInitiated` 28 and `TokensBridged` 30; xDai `UserRequestForAffirmation` 4 and `RelayedMessage` 5; `PaidInterest` 0, `FailedMessageFixed` 0, `NewTokenRegistered` 0. The PulseChain AMB and mediators emitted 80 `RelayedMessage`, 46 `UserRequestForAffirmation`, 46 `TokensBridgingInitiated` and 76 + 4 `TokensBridged` in the same window. BNB, BSC ↔ Gnosis contracts: AMB `UserRequestForAffirmation` 0 and `RelayedMessage` 0, Omnibridge `TokensBridgingInitiated` 0 and `TokensBridged` 0. Base, Arbitrum, Optimism, Polygon, Avalanche and Robinhood Chain: no Gnosis contract; the window's `TokensBridged` logs there came from other contracts (§7.8).
- **Sample transactions (receipts read):** Omnibridge deposit `0x166dea78ac6d31544d012635ff524c21c5af031865e9609723c1eb0e399f4de3` (`relayTokens` → `Transfer` user → Omnibridge, AMB `UserRequestForAffirmation`, `TokensBridgingInitiated`); Omnibridge payout `0x10b1cff1ff348bca14dea019697d971bfcc454f9fa3b16af41fdc74a008b40c6` (`safeExecuteSignaturesWithAutoGasLimit` → `Transfer` Omnibridge → recipient, `TokensBridged`, AMB `RelayedMessage`); xDai deposit `0xaeffd6863f330a9ca42ab74d473bd2a126842ba01aae3bca6cec260253fafc56` (through an aggregator: USDS `Transfer` → xDai bridge, `UserRequestForAffirmation`); xDai payout `0xf40cf4bce9de387deb30ea8ed648725fb4ff9d54eeb5f356f422b978272617b6` (`executeSignatures` through the BridgeRouter: USDS → DAI conversion, DAI `Transfer` bridge → recipient, `RelayedMessage`).

Authoritative sources (opened):
- Gnosis docs — [Omnibridge](https://docs.gnosischain.com/bridges/About%20Token%20Bridges/omnibridge) · [xDai Bridge](https://docs.gnosischain.com/bridges/About%20Token%20Bridges/xdai-bridge) · [Arbitrary Message Bridge](https://docs.gnosischain.com/bridges/About%20Token%20Bridges/amb-bridge)
- Sourcify — [XDaiForeignBridge impl](https://sourcify.dev/server/v2/contract/1/0x257bdd093cab1bd39ebf837dcb60f33d031d7d49) · [ForeignAMB impl](https://sourcify.dev/server/v2/contract/1/0x098f51bdfb5d6d319dd4fdf06b64773d25bd1316) · [ForeignOmnibridge impl](https://sourcify.dev/server/v2/contract/1/0x8eb3b7d8498a6716904577b2579e1c313d48e347) · [BridgeRouter impl](https://sourcify.dev/server/v2/contract/1/0x74899961224538e423effd1a0ff3346adf3f4c56) · [WETHOmnibridgeRouter](https://sourcify.dev/server/v2/contract/1/0xa6439ca0fcba1d0f80df0be6a17220fed9c9038a) · [BridgeValidators](https://sourcify.dev/server/v2/contract/1/0xd83893f31aa1b6b9d97c9c70d3492fe38d24d218) · [EternalStorageProxy](https://sourcify.dev/server/v2/contract/1/0x4aa42145aa6ebf72e164c9bbc74fbd3788045016)

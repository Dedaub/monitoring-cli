# deBridge DMP (deBridgeGate) — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the deBridge DMP "Deployed Contracts" page, the verified implementation sources on Blockscout, and the `debridge-finance/debridge-contracts-v1` repository. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; EIP-1967 slots read live.
**Scope:** the deBridge Messaging Protocol (DMP): `DeBridgeGate` (lock, burn, mint, release and message transport), `CallProxy` (executes the calls of a message), `SignatureVerifier` (validator signatures), `DeBridgeTokenDeployer` and the deAsset tokens (dePort), and `WethGate`. DMP is deployed on all eight target chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114) and Robinhood Chain (4663). The DLN order contracts that use DMP for settlement are in [dln.md](dln.md). Topics and selectors are chain-agnostic; addresses are per chain.

deBridgeGate is a validator-signed lock-and-mint bridge and message layer. On the source chain, `send` locks a token that is native to the chain (or burns a deAsset) and emits `Sent`; `sendMessage` emits `Sent` with amount 0 and a call payload. On the destination chain, anyone submits the validator signatures to `claim`; the Gate releases the locked token or mints the deAsset to the receiver, or hands the tokens and the call data to `CallProxy`, and emits `Claimed`. There is no refund on the source chain: an unclaimed submission stays pending, and a failed call goes to the fallback address of the message.

Three facts to know before indexing:

1. **Most Gate traffic is DLN settlement, not user transfers.** In the pinned window, 65 of the 67 Ethereum `Sent` logs had `nativeSender` = `DlnDestination` and amount 0 (unlock and cancel messages). Classify each `Sent` and `Claimed` before counting it as a transfer (§6).
2. **The Gate address differs on Base.** The Gate is `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` on seven chains, but `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` on Base. On Base, `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` is the ProxyAdmin, and on the other chains `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` is a DeBridgeToken implementation.
3. **The link key is `submissionId`**: the first data word of `Sent` (source) and of `Claimed` (destination). It is on chain on both sides and it is also in `MonitoringSendEvent`, `MonitoringClaimEvent`, `AutoRequestExecuted`, `SignatureVerifier.Confirmed` and `SubmissionApproved`.

---

## 0. Contract families

| Contract | Chains | Role | Proxy |
|----------|--------|------|-------|
| **DeBridgeGate** | all 8 (Base at its own address) | Entry point: `send`, `sendMessage`, `claim`; holds the locked assets. | EIP-1967 transparent |
| **CallProxy** | all 8 | Executes the call data of a claimed message (`DlnSource.claimUnlock` for DLN). Only the Gate may call it (`DEBRIDGE_GATE_ROLE`). | EIP-1967 transparent |
| **SignatureVerifier** | all 8 | Checks the validator signatures of a submission; emits `Confirmed` per validator. | EIP-1967 transparent |
| **DeBridgeTokenDeployer** | all 8 | Deploys the deAsset proxies and serves their implementation (`tokenImplementation()`). | EIP-1967 transparent |
| **DeBridgeToken** (deAsset) | per asset | ERC-20 that the Gate mints on claim and burns on send (dePort wrapped assets). | EIP-1967 beacon proxy per asset; the beacon is DeBridgeTokenDeployer |
| **WethGate** | Ethereum, Polygon, BNB, Avalanche | Receives WETH from the Gate and forwards native ETH (`Withdrawal`). | not a proxy (682 bytes) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 DeBridgeGate — transfer lifecycle

| topic0 | Event | Side |
|--------|-------|------|
| `0xe315721819a1f353fe56de404206bdd896ab5edc7822f1804a8c4c2c4788174c` | `Sent(bytes32 submissionId, bytes32 indexed debridgeId, uint256 amount, bytes receiver, uint256 nonce, uint256 indexed chainIdTo, uint32 referralCode, (uint256 receivedAmount, uint256 fixFee, uint256 transferFee, bool useAssetFee, bool isNativeToken) feeParams, bytes autoParams, address nativeSender)` | **Source leg.** `amount` is after fees; `nativeSender` = the caller of the Gate (the user, a router, or `DlnDestination`). |
| `0x6bc83b8dd1a15f3a247f8f99d37e3bb8ae7074ea13ee1f509e045723fafe0b55` | `MonitoringSendEvent(bytes32 submissionId, uint256 nonce, uint256 lockedOrMintedAmount, uint256 totalSupply)` | Pair of `Sent` (same transaction). Status only: running locked balance of the asset. |
| `0xfee5cae6d86f128037e90fc8d24296e73ad402bd6f6f09098589d528c2e14ad2` | `Claimed(bytes32 submissionId, bytes32 indexed debridgeId, uint256 amount, address indexed receiver, uint256 nonce, uint256 indexed chainIdFrom, bytes autoParams, bool isNativeToken)` | **Destination leg.** Release (`isNativeToken` = true) or deAsset mint (false). |
| `0xe16b3d616e66789124fb71bf745a9a969a79906489c299e52e09686696152ef1` | `MonitoringClaimEvent(bytes32 submissionId, uint256 lockedOrMintedAmount, uint256 totalSupply)` | Pair of `Claimed`. Status only. |
| `0xb5fadd70c6860131059f49f37dff63a2b25d1df54e62d75c8327d896c0f7a0ad` | `AutoRequestExecuted(bytes32 submissionId, bool indexed success, address callProxy)` | The message call ran through `CallProxy`; `success` (topic1) is its result. Every DLN unlock claim has one. |
| `0x7f2b4c099f4c970e6d3b8677f8c32755ce38018a03dad58ed015c68a7e9bc791` | `Blocked(bytes32 submissionId)` | **Admin, security:** a submission may no longer be claimed. |
| `0x598eac83c515ef525efc37796beda3b069e752328e8325fb446f84e6cc7d2242` | `Unblocked(bytes32 submissionId)` | Admin. |

### 1.2 DeBridgeGate — configuration and fees

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x2fe256b895c7737f17df53e47f93d864727942c40cbfeb0098fb10b2b57da514` | `PairAdded(bytes32 debridgeId, address tokenAddress, bytes nativeAddress, uint256 indexed nativeChainId, uint256 maxAmount, uint16 minReservesBps)` | New asset route (also emitted on the first `send` of a new native token). |
| `0x522cc1aea4e8d667320894993cf2dc17feb624e400eb812c41a8efbcefc3d340` | `ChainSupportUpdated(uint256 chainId, bool isSupported, bool isChainFrom)` | Admin: chain added or removed. |
| `0x753df979edb610900dbec05f67411d26a90a78013a0e3a028f2fd9d3c6fd214f` | `ChainsSupportUpdated(uint256 chainIds, (uint256 fixedNativeFee, bool isSupported, uint16 transferFeeBps) chainSupportInfo, bool isChainFrom)` | Admin: chain fees and support. |
| `0xa9543b36462a5e2c2259a14d72a8bd4e2342eaf9d7c828e9fb86921b3aa3eb5f` | `CallProxyUpdated(address callProxy)` | **Admin, high severity:** the contract that executes every message changes. |
| `0x850cd955704b99a3588cb377341a321bc53b01073abba0af4616b0c70eb77943` | `FixedNativeFeeUpdated(uint256 globalFixedNativeFee, uint256 globalTransferFeeBps)` | Admin. |
| `0x6af65247cf743b7cb486dac49457e290bf672f3d89f71ed05d3f56d7b69c014b` | `FixedNativeFeeAutoUpdated(uint256 globalFixedNativeFee)` | Fee updater. |
| `0xb4006a5a0c03fd761a319df109910cdb56253d60a54ffc647c070b8bad0a8ae3` | `WithdrawnFee(bytes32 debridgeId, uint256 fee)` | Fee sweep to the fee proxy. Moves value. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | **Admin:** Gate paused (`GOVMONITORING_ROLE`). |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | Admin role. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | Also on CallProxy, SignatureVerifier, DeBridgeTokenDeployer. |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | **Implementation change** on any DMP proxy. |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | ProxyAdmin change. |

### 1.3 SignatureVerifier, DeBridgeTokenDeployer, WethGate

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd4964a7cd99f5c1fa8f2420fb5e1d3bd26eadf16e2658cf2e29a67dfda38601e` | `Confirmed(bytes32 submissionId, address operator)` | Status only: one per validator signature in a `claim` (8 per claim in the samples). |
| `0x2a6b4960c287d4d53a338f9c9a9f830f37e7b66e67a0a958f68be89a4eeb939d` | `SubmissionApproved(bytes32 submissionId)` | Status only: enough signatures. |
| `0x17004f09fe70c485ba6464e7469a9daab03f82e51f76f12e62f846e26dbf22e9` | `DeployConfirmed(bytes32 deployId, address operator)` | New deAsset deployment signature. |
| `0xbdf72852f61d06eac6e0737d0b63d015cfb4009ef471d1641bba38f7ea91877f` | `DeployApproved(bytes32 deployId)` | |
| `0xe755f450de2082b1e2a5be83219122e863839acc705c368b6e119432edfc360e` | `AddOracle(address oracle, bool required)` | **Admin, security:** validator set change. |
| `0xd0a47d00eff59bee6da649bbe44f1e639db18f184bb4a80783cf8afd2a41e460` | `UpdateOracle(address oracle, bool required, bool isValid)` | **Admin, security:** validator set change. |
| `0xaf7c48bbcdb80f8cc3f61b9bc3b914e6581b61c6129d34612fe4bd28e4858d2e` | `DeBridgeTokenDeployed(address asset, string name, string symbol, uint8 decimals)` | DeBridgeTokenDeployer: a new deAsset. |
| `0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65` | `Withdrawal(address indexed receiver, uint256 wad)` | WethGate: native ETH paid to `receiver` on an unwrapping claim. Same topic0 as WETH9 `Withdrawal`; key on the emitter. |

deAssets emit the standard ERC-20 `Transfer` (`0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`): from `0x0000000000000000000000000000000000000000` on a claim (mint) and to `0x0000000000000000000000000000000000000000` on a send (burn).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Every selector below was found in the Ethereum implementation bytecode.

### 2.1 DeBridgeGate

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xbe297476` | `send(address _tokenAddress, uint256 _amount, uint256 _chainIdTo, bytes _receiver, bytes _permitEnvelope, bool _useAssetFee, uint32 _referralCode, bytes _autoParams)` | Payable. Lock or burn, then `Sent`. `_tokenAddress` = `0x0000000000000000000000000000000000000000` sends native value (wrapped to WETH). |
| `0x25ff97a0` | `sendMessage(uint256 _chainIdTo, bytes _targetContractAddress, bytes _targetContractCalldata, uint256 _flags, uint32 _referralCode)` | Payable. Message without assets; `Sent` with amount 0. `DlnDestination` uses this path. |
| `0x6ea9cec9` | `sendMessage(uint256 _chainIdTo, bytes _targetContractAddress, bytes _targetContractCalldata)` | Payable. Default flags. |
| `0xc280c905` | `claim(bytes32 _debridgeId, uint256 _amount, uint256 _chainIdFrom, address _receiver, uint256 _nonce, bytes _signatures, bytes _autoParams)` | Anyone may call with valid signatures; the caller gets the execution fee. Emits `Claimed`. |
| `0xbd2608fa` | `deployNewAsset(bytes _nativeTokenAddress, uint256 _nativeChainId, string _name, string _symbol, uint8 _decimals, bytes _signatures)` | New deAsset, validator-signed. |
| `0x96341ea7` | `blockSubmission(bytes32[] _submissionIds, bool isBlocked)` | Admin. Emits `Blocked` / `Unblocked`. |
| `0x8456cb59` | `pause()` | `GOVMONITORING_ROLE`. |
| `0x3f4ba83a` | `unpause()` | Admin. |
| `0x551156d6` | `updateAsset(bytes32 _debridgeId, uint256 _maxAmount, uint16 _minReservesBps, uint256 _amountThreshold)` | Admin: per-asset limits. |
| `0x15a4587a` | `updateChainSupport(uint256[] _chainIds, (uint256 fixedNativeFee, bool isSupported, uint16 transferFeeBps)[] _chainSupportInfo, bool _isChainFrom)` | Admin. |
| `0x31bf10c1` | `setChainSupport(uint256 _chainId, bool _isSupported, bool _isChainFrom)` | Admin. |
| `0x2b0d0a8b` | `setCallProxy(address _callProxy)` | Admin. Emits `CallProxyUpdated`. |
| `0xe08a6605` | `setSignatureVerifier(address _verifier)` | **Admin, high severity.** No event of its own; watch the call. |
| `0x889d71a2` | `setDeBridgeTokenDeployer(address _deBridgeTokenDeployer)` | Admin. |
| `0xc432e3ff` | `setWethGate(address _wethGate)` | Admin. |
| `0xc41449eb` | `updateGlobalFee(uint256 _globalFixedNativeFee, uint16 _globalTransferFeeBps)` | Admin. |
| `0x26c09e94` | `withdrawFee(bytes32 _debridgeId)` | Fee proxy only. |
| `0x9682b909` | `getDebridgeId(uint256 _chainId, address _tokenAddress)` | Pure: `debridgeId` of a native token. |
| `0x760112ff` | `getSubmissionIdFrom(bytes32 _debridgeId, uint256 _chainIdFrom, uint256 _amount, address _receiver, uint256 _nonce, (uint256 executionFee, uint256 flags, address fallbackAddress, bytes data, bytes nativeSender) _autoParams, bool _hasAutoParams, address _sender)` | View: recomputes `submissionId` on the destination. |
| `0x65ac9f78` | `isSubmissionUsed(bytes32)` | View: claimed or not. |
| `0x932fb34b` | `isBlockedSubmission(bytes32)` | View. |
| `0x57cf07ca` | `getDebridge(bytes32)` | View: asset state (balance, `maxAmount`, token address). |
| `0xaffed0e0` | `nonce()` | View: next outgoing nonce. |
| `0x2da688ac` | `callProxy()` | View: `0x8a0C79F5532f3b2a16AD1E4282A5DAF81928a824` (live read, Ethereum and Robinhood Chain). |
| `0xfde919f6` | `signatureVerifier()` | View: `0x949b3B3c098348b879C9e4F15cecc8046d9C8A8c` (live read). |
| `0x7796656c` | `getChainToConfig(uint256)` | View: fees and support per destination. |
| `0xc1efe77d` | `getChainFromConfig(uint256)` | View: support per source. |

### 2.2 CallProxy, SignatureVerifier, DeBridgeTokenDeployer, WethGate, DeBridgeToken

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x29e164db` | `call(address _reserveAddress, address _receiver, bytes _data, uint256 _flags, bytes _nativeSender, uint256 _chainIdFrom)` | CallProxy, native value. Gate only. |
| `0xb88c998b` | `callERC20(address _token, address _reserveAddress, address _receiver, bytes _data, uint256 _flags, bytes _nativeSender, uint256 _chainIdFrom)` | CallProxy, ERC-20. Gate only. `_reserveAddress` = fallback. |
| `0x508ab0a0` | `submissionChainIdFrom()` | CallProxy view: source chain of the running call (read by `DlnSource`). |
| `0x2eb48491` | `submissionNativeSender()` | CallProxy view: sender on the source chain (must equal the trusted `DlnDestination`). |
| `0x965d0a64` | `submit(bytes32 _submissionId, bytes _signatures, uint8 _excessConfirmations)` | SignatureVerifier. Gate only. |
| `0xe7c4393e` | `minConfirmations()` | SignatureVerifier view: 8 on Ethereum and Robinhood Chain (live read). |
| `0x4425bd9a` | `addOracles(address[] _oracles, bool[] _required)` | SignatureVerifier admin. |
| `0x794a9c29` | `updateOracle(address _oracle, bool _isValid, bool _required)` | SignatureVerifier admin. |
| `0x32ea039a` | `setMinConfirmations(uint8 _minConfirmations)` | SignatureVerifier admin, security. |
| `0x07435505` | `deployAsset(bytes32 _debridgeId, string _name, string _symbol, uint8 _decimals)` | DeBridgeTokenDeployer. Gate only. |
| `0x2f3a3d5d` | `tokenImplementation()` | DeBridgeTokenDeployer view: deAsset logic (§5). |
| `0x88282e2a` | `setTokenImplementation(address _impl)` | DeBridgeTokenDeployer admin: **changes the code of every deAsset**. |
| `0x19c0bb2a` | `getDeployedAssetAddress(bytes32)` | DeBridgeTokenDeployer view: deAsset of a `debridgeId`. |
| `0xf3fef3a3` | `withdraw(address _receiver, uint256 _wad)` | WethGate: unwrap and pay native ETH. |
| `0x40c10f19` | `mint(address _receiver, uint256 _amount)` | DeBridgeToken, minter (the Gate) only. |
| `0x42966c68` | `burn(uint256 _amount)` | DeBridgeToken, minter only. |

### 2.3 Proxy administration and roles

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | ProxyAdmin (OpenZeppelin v4 and v5). |
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | ProxyAdmin v4 only (seven chains). |
| `0x2f2ff15d` | `grantRole(bytes32 role, address account)` | AccessControl on every DMP contract. |

Role ids: `DEFAULT_ADMIN_ROLE` = `0x0000000000000000000000000000000000000000000000000000000000000000`; `GOVMONITORING_ROLE` = `0x2b36fa99e118fa8485d488becf749a974743fbeb6a7aa57e663893bf5d69a3c1` (pause); `DEBRIDGE_GATE_ROLE` = `0xd5a6101e940ba33e226d2395b16238ab3063d7ee83d7b3ff59cb92988b395437` (on CallProxy).

---

## 3. Addresses — Ethereum (chain ID 1)

All verified with `eth_getCode` on 2026-09-29. The DMP deployed-contracts page lists the same Gate, CallProxy, SignatureVerifier, DeBridgeTokenDeployer and WethGate.

| Role | Address | One-liner |
|------|---------|-----------|
| **DeBridgeGate** (proxy) | `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | Implementation `0x797161bcc625155d2302251404ccb93c2632658e` (22,109 bytes). |
| **CallProxy** (proxy) | `0x8a0C79F5532f3b2a16AD1E4282A5DAF81928a824` | Implementation `0xbd3d657ae87671ec6f8d6272a9f431a7c4a9b6f8`. |
| **SignatureVerifier** (proxy) | `0x949b3B3c098348b879C9e4F15cecc8046d9C8A8c` | Implementation `0xfe7de3c1e1bd252c67667b56347cabfc6df08df4`. `minConfirmations` 8, `confirmationThreshold` 3, `excessConfirmations` 3 (live reads). |
| **DeBridgeTokenDeployer** (proxy) | `0x8244d6Ffe0695B30b2bAD424683Ee3bc534Ea464` | Implementation `0x4c7ca8fcffe77281a8b81d4580cff8257d785491`. |
| deAsset logic (`tokenImplementation()`) | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` | 8,605 bytes. The docs list `0xf8A2902c0a5f817F5e22C82f453538d3f0734C2b` (DeBridgeToken, 7,733 bytes) instead; the live pointer is the value above. |
| **WethGate** | `0xFCf83648b8cDeF62e5d03319a6f1FCE16e4D6A59` | 682 bytes, not a proxy. |
| ProxyAdmin (all DMP proxies) | `0xe4427af3555cd9303d728c491364fadfdd7494fe` | Owner Safe `0x6bec1faf33183e1bc316984202ecc09d46ac92d5` (threshold 5). The same literal is the Gate implementation on Base. |

## 4. Addresses — the other seven chains

### 4.1 Base (chain ID 8453) — the Gate has its own address

| Role | Address | One-liner |
|------|---------|-----------|
| **DeBridgeGate** (proxy) | `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` | Implementation `0xe4427af3555cd9303d728c491364fadfdd7494fe` (22,109 bytes). `DlnSource.deBridgeGate()` on Base returns this address. |
| CallProxy / SignatureVerifier / DeBridgeTokenDeployer | same literals as §3 | Implementations `0x4e446b6cf4d127827c83ca0c848db0b43841c391` (CallProxy), `0x2a3e72ed893b5958690e16c3bbe1bd92137b6250` (verifier), `0x4c7ca8fcffe77281a8b81d4580cff8257d785491` (deployer). |
| deAsset logic | `0x0e4AdD4DC86Ae1Aa0FA43Bd7e6a9fB8Be2d5504d` | Matches the docs and `tokenImplementation()`. |
| ProxyAdmin (all DMP proxies) | `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | **The Ethereum Gate literal is a ProxyAdmin here** (1,891 bytes). Owner Safe `0xf0a9d50f912d64d1105b276526e21881bf48a29e` (threshold 5). |
| WethGate | none | `0xFCf83648b8cDeF62e5d03319a6f1FCE16e4D6A59` has no code on Base. |

### 4.2 Arbitrum One (42161), Polygon PoS (137), BNB Smart Chain (56)

| Role | Address / value |
|------|-----------------|
| DeBridgeGate, CallProxy, SignatureVerifier, DeBridgeTokenDeployer | Same literals and implementations as §3 (code hashes identical to Ethereum). |
| deAsset logic | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` (live `tokenImplementation()`; the docs list `0xf8A2902c0a5f817F5e22C82f453538d3f0734C2b`). |
| ProxyAdmin | `0xe4427af3555cd9303d728c491364fadfdd7494fe`; owner Safe `0xa52842cd43fa8c4b6660e443194769531d45b265` (threshold 5). |
| WethGate | `0xFCf83648b8cDeF62e5d03319a6f1FCE16e4D6A59` on Polygon and BNB; no code on Arbitrum. |

### 4.3 Optimism (chain ID 10)

| Role | Address / value |
|------|-----------------|
| DeBridgeGate (proxy) | `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA`; 2,112-byte proxy; implementation `0xb1a20d1c885fd775df97396397d6f8f07abdd20d` (same code hash as the Base Gate implementation). |
| CallProxy / SignatureVerifier / DeBridgeTokenDeployer | Same literals; implementations `0x4e446b6cf4d127827c83ca0c848db0b43841c391`, `0x2a3e72ed893b5958690e16c3bbe1bd92137b6250`, `0x4c7ca8fcffe77281a8b81d4580cff8257d785491`. |
| deAsset logic | `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` (7,636 bytes; matches the docs). |
| ProxyAdmin | `0xe4427af3555cd9303d728c491364fadfdd7494fe`; owner Safe `0xa52842cd43fa8c4b6660e443194769531d45b265`. No WethGate. |

### 4.4 Avalanche C-Chain (chain ID 43114)

| Role | Address / value |
|------|-----------------|
| DeBridgeGate, SignatureVerifier, DeBridgeTokenDeployer | Same literals as §3; Gate implementation `0x797161bcc625155d2302251404ccb93c2632658e`; verifier implementation `0x2a3e72ed893b5958690e16c3bbe1bd92137b6250`. |
| CallProxy | Same literal; implementation `0xd34c2302f497b8a7fe2d07865f31dbe04d5044d6` (same code hash as Ethereum). |
| deAsset logic | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` (live); the docs list `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF`, which also has code here (7,733 bytes). |
| WethGate | `0xFCf83648b8cDeF62e5d03319a6f1FCE16e4D6A59`. |
| ProxyAdmin | `0xe4427af3555cd9303d728c491364fadfdd7494fe`; owner Safe `0x8ac842e8f3be6bf67ccfdc87ce3f98d635008ef0` (threshold 5). |

### 4.5 Robinhood Chain (chain ID 4663)

Listed in the DMP deployed-contracts table. The Gate is live here: 44 `Sent` and 27 `Claimed` logs in the pinned window.

| Role | Address | One-liner |
|------|---------|-----------|
| **DeBridgeGate** (proxy) | `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | OpenZeppelin v5 proxy (1,159 bytes); implementation `0xb1a20d1c885fd775df97396397d6f8f07abdd20d` (22,277 bytes; own code hash). |
| CallProxy (proxy) | `0x8a0C79F5532f3b2a16AD1E4282A5DAF81928a824` | Implementation `0x4e446b6cf4d127827c83ca0c848db0b43841c391`. |
| SignatureVerifier (proxy) | `0x949b3B3c098348b879C9e4F15cecc8046d9C8A8c` | Implementation `0x2a3e72ed893b5958690e16c3bbe1bd92137b6250`; `minConfirmations` 8. |
| DeBridgeTokenDeployer (proxy) | `0x8244d6Ffe0695B30b2bAD424683Ee3bc534Ea464` | Implementation `0x4c7ca8fcffe77281a8b81d4580cff8257d785491`. |
| deAsset logic | `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` | 7,660 bytes; matches the docs. |
| ProxyAdmins (one per proxy) | Gate `0x150f6ce7301022d50285d0445c8941f60783a0e0`; deployer `0x8dfa7acc3d77aa9f6e1ecdc0956932feef80d508`; verifier `0x3264517c487170a0b3a3a5a5e529e9a5e87ff457`; CallProxy `0x127f50775935cc6519c7fe2fce14aaace2434fc0` | All four owned by EOA `0xd6f0dabbbccd143f7d526a82ca176b5395ccc844` (nonce 28), the deployer of the Base ProxyAdmin. |
| WethGate | none | No code at `0xFCf83648b8cDeF62e5d03319a6f1FCE16e4D6A59`. |

---

## 5. Cross-chain summary

| Chain | ID | DeBridgeGate | CallProxy / SignatureVerifier / DeBridgeTokenDeployer | deAsset logic (live) | WethGate | Upgrade owner |
|-------|----|--------------|--------------------------------------------------------|----------------------|----------|---------------|
| Ethereum | 1 | ✓ `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | ✓ §3 literals | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` | ✓ | Safe (5) |
| Base | 8453 | ✓ **`0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF`** | ✓ | `0x0e4AdD4DC86Ae1Aa0FA43Bd7e6a9fB8Be2d5504d` | — | Safe (5) |
| Arbitrum One | 42161 | ✓ `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | ✓ | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` | — | Safe (5) |
| Optimism | 10 | ✓ `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | ✓ | `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` | — | Safe (5) |
| Polygon PoS | 137 | ✓ `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | ✓ | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` | ✓ | Safe (5) |
| BNB Smart Chain | 56 | ✓ `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | ✓ | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` | ✓ | Safe (5) |
| Avalanche C-Chain | 43114 | ✓ `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | ✓ | `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b` | ✓ | Safe (5) |
| Robinhood Chain | 4663 | ✓ `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` | ✓ | `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` | — | **EOA** |

WethGate literal: `0xFCf83648b8cDeF62e5d03319a6f1FCE16e4D6A59`. The Gate also runs on Solana (program `DEbrdGj3HsRsAzx6uH4MKyREKxVAfBydijLUF3ygsFfh`), TRON, Linea, Arc, Story, Cronos, HyperEVM, Injective, Monad and MegaETH.

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| DeBridgeGate, CallProxy, SignatureVerifier, DeBridgeTokenDeployer (7 chains) | EIP-1967 transparent, OpenZeppelin v4 (2,141-byte proxy; 2,112 bytes on Base and Optimism) | Implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` populated; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = `0xe4427af3555cd9303d728c491364fadfdd7494fe` (Base: `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA`) | 5-threshold Safe per chain (§3–§4) |
| Same four on Robinhood Chain | EIP-1967 transparent, OpenZeppelin v5 (1,159 bytes), one ProxyAdmin per proxy | Admin slot = the ProxyAdmins of §4.5 | EOA `0xd6f0dabbbccd143f7d526a82ca176b5395ccc844` |
| deAssets | EIP-1967 beacon proxies (806 and 833 bytes in the samples) | Beacon slot `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50` = DeBridgeTokenDeployer `0x8244d6Ffe0695B30b2bAD424683Ee3bc534Ea464`; its `implementation()` returns the deAsset logic (same value as `tokenImplementation()` on Ethereum) | `setTokenImplementation` on the deployer (deployer admin); one call changes every deAsset |
| WethGate | not a proxy | 682 bytes, empty implementation slot | none |

---

## 7. Detection invariants & gotchas

1. **Classify every `Sent`.** Decode `nativeSender` (data word 11 in the samples): `DlnDestination` `0xE7351Fd770A37282b91D153Ee690B63579D6dd7f` means a DLN unlock or cancel message (amount 0, value moves on the other chain in `DlnSource`). Other senders with `amount` > 0 are user transfers. In the pinned window, Ethereum had 65 DLN messages and 2 user transfers among 67 `Sent`.
2. **Source-leg value.** A token native to the source chain is locked: an ERC-20 `Transfer` from the user to the Gate (`isNativeToken` = true in `feeParams`). A deAsset is burned: a `Transfer` to the Gate, then a `Transfer` from the Gate to `0x0000000000000000000000000000000000000000`. Native ETH is wrapped: a WETH `Deposit` with the Gate as `dst`. `msg.value` also carries the flat fee (0.001 ETH on Ethereum, Base, Arbitrum, Optimism and Robinhood Chain per the docs).
3. **Destination-leg value.** `Claimed` with `isNativeToken` = true releases the locked token from the Gate to `receiver` (topic2); false mints the deAsset (`Transfer` from `0x0000000000000000000000000000000000000000`). With call data, the tokens go to CallProxy first and the call runs (`AutoRequestExecuted`). With the unwrap flag on Ethereum, Polygon, BNB and Avalanche, the ETH leaves through WethGate (`Withdrawal`). The `claim` caller receives the execution fee.
4. **Link key = `submissionId`** (data word 0 of `Sent` and `Claimed`). `chainIdTo` (topic2 of `Sent`) and `chainIdFrom` (topic3 of `Claimed`) are deBridge chain ids (Solana = 7565164 = `0x736f6c`). `debridgeId` (topic1) identifies the asset route and is the same on both sides.
5. **No refund event.** A submission that is never claimed leaves the tokens locked or burned; a failed call sends the tokens to the fallback address inside `CallProxy` (`AutoRequestExecuted.success` = false). Admins can `blockSubmission`.
6. **Validator security signals.** `AddOracle`, `UpdateOracle`, `setMinConfirmations`, `setSignatureVerifier`, `CallProxyUpdated` and `Blocked` change who can release funds. `Confirmed` fires once per validator signature on every claim; it is noise for value monitors.
7. **Address collisions.** `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` = Gate on seven chains and ProxyAdmin on Base. `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` = Gate on Base, deAsset logic on Optimism and Robinhood Chain, and a DeBridgeToken contract that is not the live deAsset logic on Ethereum, Arbitrum, Polygon, BNB and Avalanche. `0xe4427af3555cd9303d728c491364fadfdd7494fe` = ProxyAdmin on seven chains and Gate implementation on Base. Key every address on `(chain, address)`.
8. **`MonitoringSendEvent` and `MonitoringClaimEvent` are status rows**: they repeat the `submissionId` and give the running locked balance and supply of the asset. Do not count them as transfers.
9. **deAsset logic pointer differs from the docs table** on Ethereum, Arbitrum, Polygon, BNB and Avalanche (live `tokenImplementation()` = `0xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b`). Read the deployer before trusting a listed DeBridgeToken address.
10. **Monitor triggers.** Large transfers: `Sent.amount` and `Claimed.amount` per `debridgeId`, excluding DLN messages. Drains: `Claimed` without a matching `Sent`, a sudden drop of `lockedOrMintedAmount`. Admin: `Upgraded`, `AdminChanged`, `Paused`, `CallProxyUpdated`, `AddOracle`, `UpdateOracle`, `Blocked`, `ChainSupportUpdated`, calls to `setSignatureVerifier`, `setTokenImplementation`, `updateAsset`.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== DeBridgeGate topics =====
TOPIC_DBR_GATE_SENT                = '\xe315721819a1f353fe56de404206bdd896ab5edc7822f1804a8c4c2c4788174c'
TOPIC_DBR_GATE_CLAIMED             = '\xfee5cae6d86f128037e90fc8d24296e73ad402bd6f6f09098589d528c2e14ad2'
TOPIC_DBR_GATE_AUTO_REQUEST        = '\xb5fadd70c6860131059f49f37dff63a2b25d1df54e62d75c8327d896c0f7a0ad'
TOPIC_DBR_GATE_MONITORING_SEND     = '\x6bc83b8dd1a15f3a247f8f99d37e3bb8ae7074ea13ee1f509e045723fafe0b55'
TOPIC_DBR_GATE_MONITORING_CLAIM    = '\xe16b3d616e66789124fb71bf745a9a969a79906489c299e52e09686696152ef1'
TOPIC_DBR_GATE_BLOCKED             = '\x7f2b4c099f4c970e6d3b8677f8c32755ce38018a03dad58ed015c68a7e9bc791'
TOPIC_DBR_GATE_UNBLOCKED           = '\x598eac83c515ef525efc37796beda3b069e752328e8325fb446f84e6cc7d2242'
TOPIC_DBR_GATE_PAIR_ADDED          = '\x2fe256b895c7737f17df53e47f93d864727942c40cbfeb0098fb10b2b57da514'
TOPIC_DBR_GATE_CHAIN_SUPPORT       = '\x522cc1aea4e8d667320894993cf2dc17feb624e400eb812c41a8efbcefc3d340'
TOPIC_DBR_GATE_CHAINS_SUPPORT      = '\x753df979edb610900dbec05f67411d26a90a78013a0e3a028f2fd9d3c6fd214f'
TOPIC_DBR_GATE_CALLPROXY_UPDATED   = '\xa9543b36462a5e2c2259a14d72a8bd4e2342eaf9d7c828e9fb86921b3aa3eb5f'
TOPIC_DBR_GATE_WITHDRAWN_FEE       = '\xb4006a5a0c03fd761a319df109910cdb56253d60a54ffc647c070b8bad0a8ae3'
-- ===== SignatureVerifier / deployer / WethGate topics =====
TOPIC_DBR_VERIFIER_CONFIRMED       = '\xd4964a7cd99f5c1fa8f2420fb5e1d3bd26eadf16e2658cf2e29a67dfda38601e'
TOPIC_DBR_VERIFIER_APPROVED        = '\x2a6b4960c287d4d53a338f9c9a9f830f37e7b66e67a0a958f68be89a4eeb939d'
TOPIC_DBR_VERIFIER_ADD_ORACLE      = '\xe755f450de2082b1e2a5be83219122e863839acc705c368b6e119432edfc360e'
TOPIC_DBR_VERIFIER_UPDATE_ORACLE   = '\xd0a47d00eff59bee6da649bbe44f1e639db18f184bb4a80783cf8afd2a41e460'
TOPIC_DBR_TOKEN_DEPLOYED           = '\xaf7c48bbcdb80f8cc3f61b9bc3b914e6581b61c6129d34612fe4bd28e4858d2e'
TOPIC_DBR_WETHGATE_WITHDRAWAL      = '\x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'
TOPIC_PAUSED_ADDRESS               = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UPGRADED                     = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED                = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors =====
SEL_DBR_GATE_SEND                  = '\xbe297476'
SEL_DBR_GATE_SEND_MESSAGE_FLAGS    = '\x25ff97a0'
SEL_DBR_GATE_SEND_MESSAGE          = '\x6ea9cec9'
SEL_DBR_GATE_CLAIM                 = '\xc280c905'
SEL_DBR_GATE_BLOCK_SUBMISSION      = '\x96341ea7'
SEL_DBR_GATE_SET_CALL_PROXY        = '\x2b0d0a8b'
SEL_DBR_GATE_SET_SIGNATURE_VERIFIER= '\xe08a6605'
SEL_DBR_GATE_UPDATE_ASSET          = '\x551156d6'
SEL_DBR_CALLPROXY_CALL             = '\x29e164db'
SEL_DBR_CALLPROXY_CALL_ERC20       = '\xb88c998b'
SEL_DBR_VERIFIER_SET_MIN_CONF      = '\x32ea039a'
SEL_DBR_DEPLOYER_SET_TOKEN_IMPL    = '\x88282e2a'

-- ===== Addresses =====
ETH_DBR_GATE                       = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
BASE_DBR_GATE                      = '\xc1656b63d9eeba6d114f6be19565177893e5bcbf'
ARB_DBR_GATE                       = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
OP_DBR_GATE                        = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
POLY_DBR_GATE                      = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
BNB_DBR_GATE                       = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
AVAX_DBR_GATE                      = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
RH_DBR_GATE                        = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
ETH_DBR_CALL_PROXY                 = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
BASE_DBR_CALL_PROXY                = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
ARB_DBR_CALL_PROXY                 = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
OP_DBR_CALL_PROXY                  = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
POLY_DBR_CALL_PROXY                = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
BNB_DBR_CALL_PROXY                 = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
AVAX_DBR_CALL_PROXY                = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
RH_DBR_CALL_PROXY                  = '\x8a0c79f5532f3b2a16ad1e4282a5daf81928a824'
ETH_DBR_SIGNATURE_VERIFIER         = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
BASE_DBR_SIGNATURE_VERIFIER        = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
ARB_DBR_SIGNATURE_VERIFIER         = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
OP_DBR_SIGNATURE_VERIFIER          = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
POLY_DBR_SIGNATURE_VERIFIER        = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
BNB_DBR_SIGNATURE_VERIFIER         = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
AVAX_DBR_SIGNATURE_VERIFIER        = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
RH_DBR_SIGNATURE_VERIFIER          = '\x949b3b3c098348b879c9e4f15cecc8046d9c8a8c'
ETH_DBR_TOKEN_DEPLOYER             = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
BASE_DBR_TOKEN_DEPLOYER            = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
ARB_DBR_TOKEN_DEPLOYER             = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
OP_DBR_TOKEN_DEPLOYER              = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
POLY_DBR_TOKEN_DEPLOYER            = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
BNB_DBR_TOKEN_DEPLOYER             = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
AVAX_DBR_TOKEN_DEPLOYER            = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
RH_DBR_TOKEN_DEPLOYER              = '\x8244d6ffe0695b30b2bad424683ee3bc534ea464'
ETH_DBR_WETH_GATE                  = '\xfcf83648b8cdef62e5d03319a6f1fce16e4d6a59'
POLY_DBR_WETH_GATE                 = '\xfcf83648b8cdef62e5d03319a6f1fce16e4d6a59'
BNB_DBR_WETH_GATE                  = '\xfcf83648b8cdef62e5d03319a6f1fce16e4d6a59'
AVAX_DBR_WETH_GATE                 = '\xfcf83648b8cdef62e5d03319a6f1fce16e4d6a59'
ETH_DBR_DEASSET_LOGIC              = '\xcacebe8c354b70fa6e3107f3f6f699e4fbb3a98b'
BASE_DBR_DEASSET_LOGIC             = '\x0e4add4dc86ae1aa0fa43bd7e6a9fb8be2d5504d'
OP_DBR_DEASSET_LOGIC               = '\xc1656b63d9eeba6d114f6be19565177893e5bcbf'
RH_DBR_DEASSET_LOGIC               = '\xc1656b63d9eeba6d114f6be19565177893e5bcbf'
ETH_DBR_GATE_PROXY_ADMIN           = '\xe4427af3555cd9303d728c491364fadfdd7494fe'
BASE_DBR_GATE_PROXY_ADMIN          = '\x43de2d77bf8027e25dbd179b491e8d64f38398aa'
RH_DBR_GATE_PROXY_ADMIN            = '\x150f6ce7301022d50285d0445c8941f60783a0e0'
RH_DBR_UPGRADE_OWNER_EOA           = '\xd6f0dabbbccd143f7d526a82ca176b5395ccc844'
```

---

## 9. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 and selectors:** recomputed as `keccak256` of the canonical signature, from the verified ABIs on Blockscout (`DeBridgeGate` implementation `0x797161bcc625155d2302251404ccb93c2632658e`, `SignatureVerifier` `0xfe7de3c1e1bd252c67667b56347cabfc6df08df4`, `CallProxy` `0xbd3d657ae87671ec6f8d6272a9f431a7c4a9b6f8`, `DeBridgeTokenDeployer` `0x4c7ca8fcffe77281a8b81d4580cff8257d785491`, `WethGate` `0xFCf83648b8cDeF62e5d03319a6f1FCE16e4D6A59`, `DeBridgeToken` `0xf8A2902c0a5f817F5e22C82f453538d3f0734C2b`). Each selector was found as a `PUSH4` in the Ethereum implementation bytecode. The `Sent` and `Claimed` topic0 values were found in the Gate implementation bytecode on Ethereum, Base, Optimism and Robinhood Chain, and in live logs on all eight chains.
- **Addresses:** the deBridge DMP "Deployed Contracts" page, then `eth_getCode` on each chain; EIP-1967 implementation and admin slots read live; ProxyAdmin `owner()`, Safe `getThreshold()`, `tokenImplementation()`, `callProxy()`, `signatureVerifier()` and `minConfirmations()` read live.
- **Value movement:** receipts read for a user `send` on Ethereum (`0xa837011a530ad9705ab4b9702a9e72d213d7b28823b64a3dc9d23ca8897bb8eb`: ERC-20 lock into the Gate, 0.001 ETH fee, `chainIdTo` 56), a DLN message `Sent` (`0xe017722ca5480bac09e269802a4a0fbb3cd9e752264ca5355c33dae326ce57d1`), a DLN claim (`0xe086fae384441c8fbf67f06cd568320833b3a2bbf81118f5027ea6543a4231ff`: 8 `Confirmed`, `SubmissionApproved`, CallProxy call, `AutoRequestExecuted`, `Claimed`) and a deAsset mint on Base (`0xc7553013b6a378a880c1513c3c0ab5e1a6bd3c3aa621262233ed536f1783190e`: `Transfer` from `0x0000000000000000000000000000000000000000` to the receiver, `chainIdFrom` 7565164).
- **Activity**, pinned 12-hour window 2026-09-28 00:00–12:00 UTC, logs of the Gate address per chain:

| Event | Ethereum | Base | Arbitrum | Optimism | Polygon | BNB | Avalanche | Robinhood |
|-------|---------:|-----:|---------:|---------:|--------:|----:|----------:|----------:|
| `Sent` | 67 | 16 | 24 | 0 | 2 | 28 | 1 | 44 |
| `Claimed` | 32 | 14 | 13 | 2 | 4 | 34 | 2 | 27 |
| `AutoRequestExecuted` | 32 | 12 | 13 | 2 | 4 | 23 | 2 | 27 |

`MonitoringSendEvent` equals `Sent` and `MonitoringClaimEvent` equals `Claimed` on every chain. Block ranges of the window: Ethereum 26,072,222–26,075,812; Base 51,882,127–51,903,726; Arbitrum 509,539,969–509,698,804; Optimism 157,477,412–157,499,011; Polygon 94,565,640–94,594,439; BNB 124,425,013–124,520,982; Avalanche 96,289,260–96,322,019; Robinhood 74,350,994–74,780,331. A zero says what the window held, not that a contract is dead.

Sources:
- deBridge docs — [DMP deployed contracts](https://docs.debridge.com/dmp-details/dmp/deployed-contracts) · [DMP fees and supported chains](https://docs.debridge.com/dmp-details/dmp/fees-supported-chains) · [Supported chains](https://docs.debridge.com/home/architecture/supported-chains)
- [debridge-finance/debridge-contracts-v1](https://github.com/debridge-finance/debridge-contracts-v1) (`contracts/transfers/DeBridgeGate.sol`, `contracts/transfers/SignatureVerifier.sol`, `contracts/periphery/CallProxy.sol`, `contracts/transfers/DeBridgeTokenDeployer.sol`, `contracts/transfers/WethGate.sol`)
- Explorers — [Etherscan deBridgeGate](https://etherscan.io/address/0x43de2d77bf8027e25dbd179b491e8d64f38398aa) · [Basescan deBridgeGate](https://basescan.org/address/0xc1656b63d9eeba6d114f6be19565177893e5bcbf) · [Blockscout verified Gate implementation](https://eth.blockscout.com/address/0x797161bcc625155d2302251404ccb93c2632658e) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com/address/0x43dE2d77BF8027e25dBD179B491e8d64f38398aA)

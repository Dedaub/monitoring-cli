# Wormhole Token Bridge (Portal / Wrapped Token Transfers) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the canonical `wormhole-foundation/wormhole` repo (`ethereum/contracts/bridge/`), `wormhole-foundation/example-token-bridge-relayer`, the Wormhole docs contract-address page, the `wormhole-foundation/wormhole-sdk-ts` constants and the Executor deployment registry. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; implementations read from the EIP-1967 slot and scanned for each topic and selector.
**Scope:** the **Token Bridge** (branded Portal; the docs now call it Wrapped Token Transfers, WTT), its wrapped-asset tokens, and the relayer contracts that call it: the legacy `TokenBridgeRelayer` (Connect automatic route) and the Executor-era Token Bridge relayers. The Token Bridge is deployed on **seven of the eight target chains; Robinhood Chain (4663) has none**. Topics and selectors are chain-agnostic; addresses are network-specific. The Core contract and its `LogMessagePublished` are in [core.md](core.md).

The Token Bridge is a lock-and-mint bridge with one proxy per chain. A token keeps one **origin chain**. On its origin chain the Token Bridge **locks** it (escrow). On every other chain the Token Bridge **mints** a wrapped token (`BridgeToken`, a beacon proxy whose beacon is the Token Bridge). Sending a wrapped token back **burns** it. A transfer is two transactions on two chains:

- **Source leg:** `transferTokens`, `transferTokensWithPayload`, `wrapAndTransferETH` or `wrapAndTransferETHWithPayload`. The Token Bridge takes the tokens and calls the Core. The **only source event is the Core's `LogMessagePublished` with `sender` = the Token Bridge**; the Token Bridge emits nothing of its own.
- **Destination leg:** `completeTransfer` or a variant. The Token Bridge verifies the VAA, emits **`TransferRedeemed(emitterChainId, emitterAddress, sequence)`**, then releases locked tokens or mints wrapped ones.
- **Refund, cancel, expiry:** none. A VAA never expires and there is no refund path. An unredeemed transfer stays unredeemed. A type-3 transfer (with payload) can only be redeemed by its recipient contract.

**The link key is `(emitterChain, emitterAddress, sequence)`** and it is on chain on both sides: on the source it is (the Wormhole chain id of the source, the Token Bridge address left-padded to 32 bytes, `LogMessagePublished.sequence`); on the destination all three are the indexed topics of `TransferRedeemed`.

---

## 0. Contract families

| Contract | Chains | Role | Proxy? |
|----------|--------|------|--------|
| **Token Bridge** (`TokenBridge` proxy + `BridgeImplementation`) | ETH, Base, ARB, OP, POLY, BNB, AVAX | Lock / burn on send, release / mint on redeem, token attestation, wrapped-asset registry, per-token `outstandingBridged` accounting. | EIP-1967 proxy, upgraded by governance VAA (`upgrade`) |
| **Wrapped asset** (`BridgeToken` → `TokenImplementation`) | every chain with a Token Bridge | One ERC-20 per foreign token, created with CREATE2 (salt `keccak256(tokenChain, tokenAddress)`) on the first `createWrapped`. `mint`/`burn` are `onlyOwner` = Token Bridge. | Beacon proxy; beacon = the Token Bridge (`tokenImplementation()`) |
| **TokenBridgeRelayer** (legacy automatic relay, `example-token-bridge-relayer`) | ETH, BNB, POLY, AVAX (`0xcafd2f0a35a4459fa40c0517e17e6fa2939441ca`); Base, ARB, OP (`0xaE8dc4a7438801Ec4edC0B035EcCCcF3807F4CC1`) | Sends type-3 transfers to its peer and redeems them for the user, with a relayer fee and an optional native drop-off (`SwapExecuted`). | No (17,685 B, identical bytecode on all seven) |
| **Executor Token Bridge relayer** (Executor registry: `token-bridge-relayer`) | ETH, Base, ARB, OP, POLY, BNB, AVAX (chain-unique addresses, §4.2) | Sends a type-3 transfer and requests delivery from the Executor in one call; on the destination, redeems the transfer and forwards the tokens (`executeVAAv1`). | No (7,850 B) |
| **Relayer with referrer v1 / v2** | same seven chains, one address each (§4.2) | Front-end wrapper: takes a referrer fee and calls the Executor Token Bridge relayer. | No |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Source leg — the Core event (emitter = Core, `topic1` = Token Bridge)

| topic0 | Event |
|--------|-------|
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — keep only `sender` = the local Token Bridge; payload layout in §1.4 |

### 1.2 Token Bridge (emitter = the Token Bridge proxy)

| topic0 | Event |
|--------|-------|
| `0xcaf280c8cfeba144da67230d9b009c8f868a75bac9a528fa0474be1ba317c169` | `TransferRedeemed(uint16 indexed emitterChainId, bytes32 indexed emitterAddress, uint64 indexed sequence)` — **destination leg; emitted before the release / mint in the same call; also emitted with identical topics by the two relayer contracts in §1.3** |
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address indexed oldContract, address indexed newContract)` — admin; same topic0 as the Core |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — admin; emitted with `ContractUpgraded` |
| `0xab40a374bc51de372200a8bc981af8c9ecdc08dfdaef0bb6e09f88f3c616ef3d` | `Paused(address indexed by, uint256 pauseExpiry)` — **in `main` source since 2026-06, absent from all seven live implementations** |
| `0x68e0d8c112165d0949ce87205b719ed7d98c7401866c34a159f7c67c6f5620e7` | `Frozen(address indexed by, uint256 pauseExpiry)` — source only, not deployed |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address indexed by)` — source only, not deployed; same topic0 as OpenZeppelin `Pausable.Unpaused` |
| `0xb3254552100e924f3b44cab58024e3b92cb715798e17d0822fd22844e426ecfd` | `UnpauseExpired(address indexed by)` — source only, not deployed |
| `0xc74c66e9823f145cdc02a3330087a6ca05c4ea9d140ef64de6db83facbd34dbf` | `PauserAddressesSet(address indexed pauser, address indexed freezer, address indexed unpauser)` — source only, not deployed |

The Token Bridge emits **no event on send, on attestation (`attestToken`), on `registerChain` or on `createWrapped`**. The wrapped token's constructor is an OpenZeppelin `BeaconProxy`, so a new wrapped asset should emit `BeaconUpgraded(address indexed beacon)` (`0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e`) from the new token address (from source; not sampled).

### 1.3 Relayer contracts on top of the Token Bridge

| topic0 | Event |
|--------|-------|
| `0xcaf280c8cfeba144da67230d9b009c8f868a75bac9a528fa0474be1ba317c169` | `TransferRedeemed(uint16 indexed emitterChainId, bytes32 indexed emitterAddress, uint64 indexed sequence)` — **also emitted by the Executor Token Bridge relayer and by `TokenBridgeRelayer`, right after the Token Bridge's own `TransferRedeemed` for the same VAA** |
| `0x764f0dc063c06f32d89a3f3af80c0db4be8a090901f589a478b447e0a51f09f1` | `SwapExecuted(address indexed recipient, address indexed relayer, address indexed token, uint256 tokenAmount, uint256 nativeAmount)` — `TokenBridgeRelayer` native drop-off; **generic signature: in the window, every `SwapExecuted` log came from unrelated contracts** |
| `0x0d18b5fd22306e373229b9439188228edca81207d1667f604daf6cef8aa3ee67` | `OwnershipTransfered(address indexed oldOwner, address indexed newOwner)` — `TokenBridgeRelayer` admin (the source spells it "Transfered") |
| `0xaaebcf1bfa00580e41d966056b48521fa9f202645c86d4ddf28113e617c1b1d3` | `FeeRecipientUpdated(address indexed oldRecipient, address indexed newRecipient)` — `TokenBridgeRelayer` admin |
| `0x7abf49a6ebb116bc314846377cd82a3d2c8c1ea48149a652356009fc37100dd7` | `SwapRateUpdated((address token, uint256 value)[] indexed swapRates)` — `TokenBridgeRelayer` admin |

### 1.4 Payload of a Token Bridge message (inside `LogMessagePublished.payload`)

`LogMessagePublished` data = `sequence` (word 0), `nonce` (word 1), payload offset (word 2), `consistencyLevel` (word 3), payload length (word 4), payload from **data byte 160**. Offsets below are from the payload start.

| Bytes | Type 1 `Transfer` (133 B; log data 320 B) | Type 2 `AssetMeta` (100 B; attestation, not a transfer) | Type 3 `TransferWithPayload` (133 B + payload) |
|-------|-------------------------------------------|----------------------------------------------------------|------------------------------------------------|
| 0 | `payloadID` = 1 | `payloadID` = 2 | `payloadID` = 3 |
| 1–32 | `amount` (8-decimal normalized) | `tokenAddress` | `amount` (8-decimal normalized) |
| 33–64 | `tokenAddress` (origin, bytes32) | — | `tokenAddress` |
| 65–66 | `tokenChain` (origin Wormhole chain) | `tokenChain` at 33–34, `decimals` at 35 | `tokenChain` |
| 67–98 | `to` (bytes32 recipient) | `symbol` 36–67, `name` 68–99 | `to` (the redeeming contract) |
| 99–100 | `toChain` | — | `toChain` |
| 101–132 | `fee` (arbiter fee, normalized) | — | `fromAddress` (the `msg.sender` that sent) |
| 133– | — | — | arbitrary `payload` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Token Bridge — transfers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0f5287b0` | `transferTokens(address token, uint256 amount, uint16 recipientChain, bytes32 recipient, uint256 arbiterFee, uint32 nonce)` | Payable (the Core fee, 0 today). Type 1. Lock (origin token) or burn (wrapped). |
| `0xc5a5ebda` | `transferTokensWithPayload(address token, uint256 amount, uint16 recipientChain, bytes32 recipient, uint32 nonce, bytes payload)` | Type 3. |
| `0x9981509f` | `wrapAndTransferETH(uint16 recipientChain, bytes32 recipient, uint256 arbiterFee, uint32 nonce)` | Native coin in `msg.value`, wrapped to the chain's WETH (§4.1), then locked. Type 1. |
| `0xbee9cdfc` | `wrapAndTransferETHWithPayload(uint16 recipientChain, bytes32 recipient, uint32 nonce, bytes payload)` | Type 3 with native coin. |
| `0xc6878519` | `completeTransfer(bytes encodedVm)` | Redeem type 1. Pays `fee` to `msg.sender` when the caller is not the recipient. Emits `TransferRedeemed`. |
| `0xc3f511c1` | `completeTransferWithPayload(bytes encodedVm)` | Redeem type 3; `msg.sender` must be the recipient. Returns the payload. |
| `0xff200cde` | `completeTransferAndUnwrapETH(bytes encodedVm)` | Redeem WETH as native coin. |
| `0x1c8475e4` | `completeTransferAndUnwrapETHWithPayload(bytes encodedVm)` | Type 3, native coin. |
| `0xc48fa115` | `attestToken(address tokenAddress, uint32 nonce)` | Publishes a type-2 `AssetMeta` message. |
| `0xe8059810` | `createWrapped(bytes encodedVm)` | Deploys the wrapped token for a type-2 VAA. |
| `0xf768441f` | `updateWrapped(bytes encodedVm)` | Updates name / symbol of a wrapped token. |

### 2.2 Token Bridge — governance and views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa5799f93` | `registerChain(bytes encodedVM)` | Governance VAA; registers the peer Token Bridge of a chain (`bridgeContracts`). **No event.** |
| `0x25394645` | `upgrade(bytes encodedVM)` | Governance VAA; emits `Upgraded` + `ContractUpgraded`. **Admin.** |
| `0x178149e7` | `submitRecoverChainId(bytes encodedVM)` | Fork recovery only. |
| `0xc6b9744d` | `submitSetPauserAddresses(bytes encodedVM)` | Source only (2026-06); selector absent from the live implementations. |
| `0x8456cb59` | `pause()` | Source only; absent from the live implementations. |
| `0x62a5af3b` | `freeze()` | Source only; absent from the live implementations. |
| `0x1ff1e286` | `wrappedAsset(uint16 tokenChainId, bytes32 tokenAddress)` | View — the local wrapped token of a foreign asset. |
| `0x1a2be4da` | `isWrappedAsset(address token)` | View. |
| `0xaa4efa5b` | `isTransferCompleted(bytes32 hash)` | View — replay guard, keyed by the VAA hash. |
| `0xad66a5f1` | `bridgeContracts(uint16 chainId_)` | View — registered peer (bytes32). |
| `0xb96c7e4d` | `outstandingBridged(address token)` | View — normalized amount of a local token held in escrow. |
| `0xad5c4648` | `WETH()` | View. |
| `0x84acd1bb` | `wormhole()` | View — the local Core. |
| `0x2f3a3d5d` | `tokenImplementation()` | View — the wrapped-token implementation (the beacon target). |
| `0x739fc8d1` | `finality()` | View — the `consistencyLevel` used (1, or 15 on BNB and Polygon). |
| `0x9a8a0592` | `chainId()` | View — the Wormhole chain id. |
| `0x2b511375` | `parseTransfer(bytes encoded)` | Pure. |
| `0xea63738d` | `parseTransferWithPayload(bytes encoded)` | Pure. |

### 2.3 Wrapped asset (`TokenImplementation`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address account, uint256 amount)` | `onlyOwner` (Token Bridge) — destination leg of a foreign token: `Transfer(0x0, recipient)`. |
| `0x9dc29fac` | `burn(address account, uint256 amount)` | `onlyOwner` — source leg: the Token Bridge pulls the tokens, then burns from itself. |
| `0x9a8a0592` | `chainId()` | View — origin Wormhole chain of the token (uint16). |
| `0x3d6c043b` | `nativeContract()` | View — origin token address (bytes32). |

### 2.4 Relayer contracts

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x730a286b` | `transferTokensWithRelay(address token, uint256 amount, uint16 targetChain, bytes32 targetRecipient, uint32 nonce, bytes32 dstTransferRecipient, bytes32 dstExecutionAddress, uint256 executionAmount, address refundAddr, bytes signedQuoteBytes, bytes relayInstructions)` | Executor Token Bridge relayer |
| `0xe50e7e72` | `wrapAndTransferEthWithRelay(uint16 targetChain, bytes32 targetRecipient, uint32 nonce, bytes32 dstTransferRecipient, bytes32 dstExecutionAddress, uint256 executionAmount, address refundAddr, bytes signedQuoteBytes, bytes relayInstructions)` | Executor Token Bridge relayer |
| `0x53c6f0dc` | `executeVAAv1(bytes encodedTransferMessage)` | Executor Token Bridge relayer — destination; redeems and forwards |
| `0xc6328a46` | `tokenBridge()` | Executor Token Bridge relayer / `TokenBridgeRelayer` view |
| `0xc34c08e5` | `executor()` | Executor Token Bridge relayer view |
| `0xd2b431ed` | `transferTokensWithRelay(address tokenBridgeRelayer, address token, uint256 amount, uint16 targetChain, bytes32 targetRecipient, uint32 nonce, bytes32 dstTransferRecipient, bytes32 dstExecutionAddress, uint256 executionAmount, address refundAddr, bytes signedQuoteBytes, bytes relayInstructions, (uint256 transferTokenFee, uint256 nativeTokenFee, address payee) feeArgs)` | Relayer with referrer v2 |
| `0x34529122` | `wrapAndTransferEthWithRelay(address tokenBridgeRelayer, uint256 amount, uint16 targetChain, bytes32 targetRecipient, uint32 nonce, bytes32 dstTransferRecipient, bytes32 dstExecutionAddress, uint256 executionAmount, address refundAddr, bytes signedQuoteBytes, bytes relayInstructions, (uint256 transferTokenFee, uint256 nativeTokenFee, address payee) feeArgs)` | Relayer with referrer v2 |
| `0x1019d654` | `transferTokensWithRelay(address token, uint256 amount, uint256 toNativeTokenAmount, uint16 targetChain, bytes32 targetRecipient, uint32 batchId)` | `TokenBridgeRelayer` (legacy) |
| `0x29ac8361` | `wrapAndTransferEthWithRelay(uint256 toNativeTokenAmount, uint16 targetChain, bytes32 targetRecipient, uint32 batchId)` | `TokenBridgeRelayer` |
| `0x2f25e25f` | `completeTransferWithRelay(bytes encodedTransferMessage)` | `TokenBridgeRelayer` — destination |

The v1 referrer wrapper (`0x412f30e9f8B4a1e99eaE90209A6b00f5C3cc8739`) does not contain `0xd2b431ed` or `0x34529122`; its ABI is not published in the SDK (unverified).

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All existence-checked with `eth_getCode` on 2026-09-29. Wormhole chain id **2**.

| Role | Address | One-liner |
|------|---------|-----------|
| **Token Bridge** (proxy) | `0x3ee18B2214AFF97000D974cf647E7C347E8fa585` | 680 B proxy; implementation `0x381752f5458282d317d12c30d2bd4d6e1fd8841e` (23,716 B). Escrow of Ethereum-origin tokens. |
| Wrapped-token implementation | `0x0fd04a68d3c3a692d6fa30384d1a87ef93554ee6` | `tokenImplementation()`; 6,680 B; has `mint`, `burn`, `nativeContract`. |
| WETH used by `wrapAndTransferETH` | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | `WETH()`. |
| Executor Token Bridge relayer | `0xa8969F3f8D97b3Ed89D4e2EC19B6B0CfD504b212` | `tokenBridge()` = the Token Bridge; `executor()` = `0x84EEe8dBa37C36947397E1E11251cA9A06Fc6F8a`. |
| `TokenBridgeRelayer` (legacy) | `0xcafd2f0a35a4459fa40c0517e17e6fa2939441ca` | `owner()` = `0x59acf1c83df72148e65af6184942f20414027c38`. |
| Relayer with referrer v2 | `0xee05C2e6075E2C86D1F5db4716Ff2A6c18889B20` | Same address on all seven chains. |
| Relayer with referrer v1 | `0x412f30e9f8B4a1e99eaE90209A6b00f5C3cc8739` | Same address on all seven chains. |

---

## 4. Addresses — the other six Token Bridge chains

### 4.1 Token Bridge proxy per chain

| Chain | EVM id | Wormhole id | Token Bridge (proxy) | Live implementation | `finality()` | `WETH()` |
|-------|--------|-------------|----------------------|---------------------|--------------|----------|
| Ethereum | 1 | 2 | `0x3ee18B2214AFF97000D974cf647E7C347E8fa585` | `0x381752f5458282d317d12c30d2bd4d6e1fd8841e` | 1 | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` |
| Base | 8453 | 30 | `0x8d2de8d2f73F1F4cAB472AC9A881C9b123C79627` | `0x24850c6f61c438823f01b7a3bf2b89b72174fa9d` | 1 | `0x4200000000000000000000000000000000000006` |
| Arbitrum One | 42161 | 23 | `0x0b2402144Bb366A632D14B83F244D2e0e21bD39c` | `0xa27ced4dd23a2435cec24b5b7ae349f43b9930b6` | 1 | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` |
| Optimism | 10 | 24 | `0x1D68124e65faFC907325e3EDbF8c4d84499DAa8b` | `0xcc02226ed784f3fe5f3725ff39e8d8cae756c9ce` | 1 | `0x4200000000000000000000000000000000000006` |
| Polygon PoS | 137 | 5 | `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` | `0x99dd86b81080e1cc794695b9e740b979d0286649` | 15 | `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` (WPOL) |
| BNB Smart Chain | 56 | 4 | `0xB6F6D86a8f9879A9c87f643768d9efc38c1Da6E7` | `0x621199f6beb2ba6fbd962e8a52a320ea4f6d4aa3` | 15 | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` |
| Avalanche C-Chain | 43114 | 6 | `0x0e082F06FF657D94310cB8cE8B0D9a04541d8052` | `0x07d6b04d34567492d80480ba4e31944621fa01c9` | 1 | `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7` |

Six implementations share one bytecode (23,716 B, code hash `0x7b5dbbb9333e8973eb3e6ed329cf1505c087d69c4d7bfd3cf76a48a09c445ffc`). Optimism runs a 23,755 B build (code hash `0xe50a08314cf8af06460b0eecd346288f7c6058e56cef36e82361782e0f1137a3`). Every implementation contains `TransferRedeemed`, `ContractUpgraded`, `Upgraded`, `transferTokens`, `transferTokensWithPayload` and `completeTransfer`, and none contains the pause surface.

Wrapped-token implementations (`tokenImplementation()`, 6,680 B each): Base `0x5537857664b0f9efe38c9f320f75fef23234d904`, Arbitrum `0x53b56de645b9de6e5a40ace047d1c74e8b42eccb`, Optimism `0xb91e3638f82a1facb28690b37e3aae45d2c33808`, BNB `0x7f8c5e730121657e17e452c5a1ba3fa1ef96f22a`, Avalanche `0xe07548528d7c0c470251cf1374ef762345f298ee`, Polygon `0x7c9fc5741288cdfdd83ceb07f3ea7e22618d79d2`.

### 4.2 Relayer contracts per chain

| Chain | Executor Token Bridge relayer | `TokenBridgeRelayer` (legacy) |
|-------|-------------------------------|-------------------------------|
| Ethereum | `0xa8969F3f8D97b3Ed89D4e2EC19B6B0CfD504b212` | `0xcafd2f0a35a4459fa40c0517e17e6fa2939441ca` |
| Base | `0xD8B736EF27Fc997b1d00F22FE37A58145D3BDA07` | `0xaE8dc4a7438801Ec4edC0B035EcCCcF3807F4CC1` |
| Arbitrum One | `0x04C98824a64d75CD1E9Bc418088b4c9A99048153` | `0xaE8dc4a7438801Ec4edC0B035EcCCcF3807F4CC1` |
| Optimism | `0x37aC29617AE74c750a1e4d55990296BAF9b8De73` | `0xaE8dc4a7438801Ec4edC0B035EcCCcF3807F4CC1` |
| Polygon PoS | `0x1d98CA4221516B9ac4869F5CeA7E6bb9C41609D6` | `0xcafd2f0a35a4459fa40c0517e17e6fa2939441ca` |
| BNB Smart Chain | `0x2513515340fF71DD5AF02fC1BdB9615704d91524` | `0xcafd2f0a35a4459fa40c0517e17e6fa2939441ca` |
| Avalanche C-Chain | `0x8849F05675E034b54506caB84450c8C82694a786` | `0xcafd2f0a35a4459fa40c0517e17e6fa2939441ca` |

On every chain measured, `tokenBridge()` of both relayers returned the local Token Bridge, and `executor()` of the Executor relayer returned the local Executor ([relayer.md](relayer.md)). The relayers with referrer (v1 `0x412f30e9f8B4a1e99eaE90209A6b00f5C3cc8739`, v2 `0xee05C2e6075E2C86D1F5db4716Ff2A6c18889B20`) have code on all seven chains.

### 4.3 Robinhood Chain (chain ID 4663, Wormhole id 72) — **no Token Bridge**

`eth_getCode` = `0x` (nonce 0) on Robinhood for the Ethereum and Base Token Bridge addresses, the shared `0x3Ff72741fd67D6AD0668d93B41a09248F4700560` (Berachain, Unichain, Ink), both relayers with referrer and the legacy relayer. Neither the docs WTT list nor `tokenBridge.ts` of the SDK has a Robinhood entry, and no `TransferRedeemed` log was seen on Robinhood in the window. Robinhood's Core exists ([core.md](core.md)); Wormhole value on Robinhood moves through NTT ([ntt.md](ntt.md)).

---

## 5. Cross-chain summary

| Chain | EVM id | Wormhole id | Token Bridge | Executor TB relayer | Legacy relayer | Referrer v1 / v2 |
|-------|--------|-------------|--------------|---------------------|----------------|------------------|
| Ethereum | 1 | 2 | `0x3ee18B2214AFF97000D974cf647E7C347E8fa585` | ✅ | ✅ | ✅ / ✅ |
| Base | 8453 | 30 | `0x8d2de8d2f73F1F4cAB472AC9A881C9b123C79627` | ✅ | ✅ | ✅ / ✅ |
| Arbitrum One | 42161 | 23 | `0x0b2402144Bb366A632D14B83F244D2e0e21bD39c` | ✅ | ✅ | ✅ / ✅ |
| Optimism | 10 | 24 | `0x1D68124e65faFC907325e3EDbF8c4d84499DAa8b` | ✅ | ✅ | ✅ / ✅ |
| Polygon PoS | 137 | 5 | `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` | ✅ | ✅ | ✅ / ✅ |
| BNB Smart Chain | 56 | 4 | `0xB6F6D86a8f9879A9c87f643768d9efc38c1Da6E7` | ✅ | ✅ | ✅ / ✅ |
| Avalanche C-Chain | 43114 | 6 | `0x0e082F06FF657D94310cB8cE8B0D9a04541d8052` | ✅ | ✅ | ✅ / ✅ |
| **Robinhood Chain** | 4663 | 72 | ❌ `0x` | ❌ | ❌ | ❌ / ❌ |

**Address reuse trap:** `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` is the **Token Bridge on Polygon** and the **NFT Bridge on BNB** (different implementations, measured). Always key on `(chain, address)`.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Token Bridge** (7 chains) | EIP-1967 proxy (`TokenBridge is ERC1967Proxy`), upgrade logic in `BridgeGovernance` | Implementation slot populated (§4.1); admin slot 0 on every chain read | Guardian governance VAA: `upgrade(bytes)`, module `TokenBridge` (`0x000000000000000000000000000000000000000000546f6b656e427269646765`), emitter chain 1, emitter `0x0000000000000000000000000000000000000000000000000000000000000004` |
| **Wrapped asset** | `BeaconProxy`; beacon = the Token Bridge; target = `tokenImplementation()` | A Token Bridge upgrade that changes `tokenImplementation` upgrades every wrapped token at once | Same governance VAA |
| Executor Token Bridge relayer, relayers with referrer, `TokenBridgeRelayer` | Not proxies | Implementation slot 0; full bytecode | Immutable (the legacy relayer has an owner for fees and rates: `0x59acf1c83df72148e65af6184942f20414027c38`) |

---

## 7. Detection invariants & gotchas

1. **Send = `LogMessagePublished` with `topic1` = the local Token Bridge.** The Token Bridge has no send event. In the window, the Token Bridge sent 168 of 1,031 Core messages on Ethereum and 36 of 174 on Base. A monitor on "all Core messages" sees mostly other applications.
2. **Skip attestations.** Payload type 2 (`AssetMeta`) is a token registration, not a value transfer. Type 1 log data is 320 bytes; type 3 is longer (352 bytes in the sampled referrer transfer); type 2 is 288 bytes.
3. **Amounts are normalized to 8 decimals** in the payload. For the raw amount, read the ERC-20 `Transfer` into the Token Bridge in the same transaction (dust below 8 decimals is refunded or never pulled).
4. **Value movement.** Origin token: `Transfer(user → Token Bridge)` and the Token Bridge keeps it (escrow; `outstandingBridged` rises). Wrapped token: `Transfer(user → Token Bridge)` then `Transfer(Token Bridge → 0x0)` (burn; sample `0x3a51f857b2eb59c19f32855e511159883f740b3fc960e8a0e5a0a3a4121ede6d`). Native coin: `msg.value` → WETH `Deposit`, WETH stays in escrow. Destination: release `Transfer(Token Bridge → recipient)` or mint `Transfer(0x0 → recipient)`; unwrap variants burn WETH (`Withdrawal`) and send native coin by an internal call.
5. **`TransferRedeemed` has three emitters with identical topics.** The Executor Token Bridge relayer and `TokenBridgeRelayer` redeem a type-3 transfer and then emit their own `TransferRedeemed` with the same `(emitterChainId, emitterAddress, sequence)`. Sample `0x809fce8dd7396d8593821a2dfbb0a37a8f693183f9c3ebefd8487c5498b60c22` (Ethereum): Token Bridge `TransferRedeemed`, token to the relayer, relayer `TransferRedeemed`, token to the user. Count redemptions at the Token Bridge address only. Other integrators do the same with their own events: `0xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4` emits `Redeemed(uint16,bytes32,uint64)` after a Token Bridge redemption (sample `0x054fcd0d83bbe377056e0d9d3028a417c1fc82800dcdb5eedd881ce8fede316a`).
6. **The `to` field is bytes32.** For an EVM recipient take the low 20 bytes; the Token Bridge reverts if the high 12 bytes are not zero. For type 3, `to` is a contract that acts in the same destination transaction, so follow the transfers after `TransferRedeemed`.
7. **Many transfers do not call the Token Bridge directly.** In 16 sampled Ethereum transactions, 3 of 8 sends and 4 of 8 redemptions called the Token Bridge directly. The others came through the relayer with referrer and four other router contracts. Key on the events, not on `tx.to` or the call selector.
8. **No expiry and no refund.** An unredeemed VAA stays valid. `isTransferCompleted(vaaHash)` is the only on-chain state that says a transfer was redeemed.
9. **The pause feature is not live.** `main` added `pause` / `freeze` / `unpause` and five events in 2026-06; none of the seven live implementations contains them, and `paused()` reverts on every chain. Re-scan after the next `ContractUpgraded`.
10. **`registerChain` and `createWrapped` emit nothing from the Token Bridge.** Watch the call selectors (`0xa5799f93`, `0xe8059810`) for these admin and registry actions.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_LOG_MESSAGE_PUBLISHED   = '\x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'   -- emitter = Core; topic1 = Token Bridge
TOPIC_TRANSFER_REDEEMED       = '\xcaf280c8cfeba144da67230d9b009c8f868a75bac9a528fa0474be1ba317c169'
TOPIC_CONTRACT_UPGRADED       = '\x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_SWAP_EXECUTED           = '\x764f0dc063c06f32d89a3f3af80c0db4be8a090901f589a478b447e0a51f09f1'
TOPIC_ERC20_TRANSFER          = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- source only (not deployed on 2026-09-29) --
TOPIC_PAUSED_WITH_EXPIRY      = '\xab40a374bc51de372200a8bc981af8c9ecdc08dfdaef0bb6e09f88f3c616ef3d'
TOPIC_FROZEN                  = '\x68e0d8c112165d0949ce87205b719ed7d98c7401866c34a159f7c67c6f5620e7'
TOPIC_PAUSER_ADDRESSES_SET    = '\xc74c66e9823f145cdc02a3330087a6ca05c4ea9d140ef64de6db83facbd34dbf'

-- ===== Selectors =====
SEL_TRANSFER_TOKENS           = '\x0f5287b0'
SEL_TRANSFER_TOKENS_PAYLOAD   = '\xc5a5ebda'
SEL_WRAP_AND_TRANSFER_ETH     = '\x9981509f'
SEL_WRAP_TRANSFER_ETH_PAYLOAD = '\xbee9cdfc'
SEL_COMPLETE_TRANSFER         = '\xc6878519'
SEL_COMPLETE_TRANSFER_PAYLOAD = '\xc3f511c1'
SEL_COMPLETE_UNWRAP_ETH       = '\xff200cde'
SEL_COMPLETE_UNWRAP_PAYLOAD   = '\x1c8475e4'
SEL_ATTEST_TOKEN              = '\xc48fa115'
SEL_CREATE_WRAPPED            = '\xe8059810'
SEL_REGISTER_CHAIN            = '\xa5799f93'
SEL_TB_UPGRADE                = '\x25394645'
SEL_EXEC_TB_TRANSFER_RELAY    = '\x730a286b'
SEL_EXEC_TB_WRAP_ETH_RELAY    = '\xe50e7e72'
SEL_EXEC_TB_EXECUTE_VAA_V1    = '\x53c6f0dc'
SEL_REFERRER_TRANSFER_RELAY   = '\xd2b431ed'
SEL_REFERRER_WRAP_ETH_RELAY   = '\x34529122'
SEL_TBR_TRANSFER_RELAY        = '\x1019d654'
SEL_TBR_COMPLETE_RELAY        = '\x2f25e25f'

-- ===== Token Bridge per chain =====
ETH_TOKEN_BRIDGE              = '\x3ee18b2214aff97000d974cf647e7c347e8fa585'
BASE_TOKEN_BRIDGE             = '\x8d2de8d2f73f1f4cab472ac9a881c9b123c79627'
ARB_TOKEN_BRIDGE              = '\x0b2402144bb366a632d14b83f244d2e0e21bd39c'
OP_TOKEN_BRIDGE               = '\x1d68124e65fafc907325e3edbf8c4d84499daa8b'
POLY_TOKEN_BRIDGE             = '\x5a58505a96d1dbf8df91cb21b54419fc36e93fde'
BNB_TOKEN_BRIDGE              = '\xb6f6d86a8f9879a9c87f643768d9efc38c1da6e7'
AVAX_TOKEN_BRIDGE             = '\x0e082f06ff657d94310cb8ce8b0d9a04541d8052'
-- Robinhood (4663): no Token Bridge

-- ===== Executor Token Bridge relayer per chain (emits TransferRedeemed too) =====
ETH_EXEC_TB_RELAYER           = '\xa8969f3f8d97b3ed89d4e2ec19b6b0cfd504b212'
BASE_EXEC_TB_RELAYER          = '\xd8b736ef27fc997b1d00f22fe37a58145d3bda07'
ARB_EXEC_TB_RELAYER           = '\x04c98824a64d75cd1e9bc418088b4c9a99048153'
OP_EXEC_TB_RELAYER            = '\x37ac29617ae74c750a1e4d55990296baf9b8de73'
POLY_EXEC_TB_RELAYER          = '\x1d98ca4221516b9ac4869f5cea7e6bb9c41609d6'
BNB_EXEC_TB_RELAYER           = '\x2513515340ff71dd5af02fc1bdb9615704d91524'
AVAX_EXEC_TB_RELAYER          = '\x8849f05675e034b54506cab84450c8c82694a786'

-- ===== Legacy TokenBridgeRelayer (emits TransferRedeemed + SwapExecuted) =====
ETH_TB_RELAYER_LEGACY         = '\xcafd2f0a35a4459fa40c0517e17e6fa2939441ca'
BNB_TB_RELAYER_LEGACY         = '\xcafd2f0a35a4459fa40c0517e17e6fa2939441ca'
POLY_TB_RELAYER_LEGACY        = '\xcafd2f0a35a4459fa40c0517e17e6fa2939441ca'
AVAX_TB_RELAYER_LEGACY        = '\xcafd2f0a35a4459fa40c0517e17e6fa2939441ca'
BASE_TB_RELAYER_LEGACY        = '\xae8dc4a7438801ec4edc0b035eccccf3807f4cc1'
ARB_TB_RELAYER_LEGACY         = '\xae8dc4a7438801ec4edc0b035eccccf3807f4cc1'
OP_TB_RELAYER_LEGACY          = '\xae8dc4a7438801ec4edc0b035eccccf3807f4cc1'

-- ===== Relayers with referrer (same address on the seven Token Bridge chains) =====
ETH_TB_REFERRER_V2            = '\xee05c2e6075e2c86d1f5db4716ff2a6c18889b20'
ETH_TB_REFERRER_V1            = '\x412f30e9f8b4a1e99eae90209a6b00f5c3cc8739'
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `ethereum/contracts/bridge/Bridge.sol`, `BridgeGovernance.sol`, `interfaces/ITokenBridge.sol` and `token/TokenImplementation.sol`; from `example-token-bridge-relayer/evm/src/interfaces/ITokenBridgeRelayer.sol`; and from the relayer ABI in `platforms/evm/protocols/tokenBridge/src/executorTokenBridge.ts` of the SDK. Every live Token Bridge implementation was scanned for the topics (`PUSH32`) and selectors (`PUSH4`) listed in §4.1 and §7.9. The relayer selectors were found in the relayer bytecode (`0x730a286b`, `0xe50e7e72`, `0x53c6f0dc` in the Executor relayer; `0xd2b431ed`, `0x34529122` in the v2 referrer wrapper; `0x1019d654`, `0x29ac8361`, `0x2f25e25f` in the legacy relayer).
- **Addresses:** the docs WTT list and `tokenBridge.ts` agree on the seven chains; the relayer addresses come from `executorTokenBridge.ts`, `tokenBridgeRelayer.ts` and the Executor deployment registry (`registry-api.wormholelabs.xyz/v1/public/deployments`). All were existence-checked with `eth_getCode`; `chainId()`, `wormhole()`, `WETH()`, `finality()` and `tokenImplementation()` were read live.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** sends (`LogMessagePublished` with `sender` = Token Bridge): Ethereum 168, Base 36, Arbitrum 5, Optimism 2, BNB 309, Avalanche 17, Polygon not split by sender (85 Core messages in total; the per-sender query failed on the Polygon log endpoint); Robinhood — (no Token Bridge). Redemptions (`TransferRedeemed` at the Token Bridge): Ethereum 327, Base 52, Arbitrum 29, Optimism 0, Polygon 36, BNB 180, Avalanche 5, Robinhood 0. `TransferRedeemed` at the Executor relayer: Ethereum 13, BNB 3, other chains 0. At the legacy relayer: 0 on every chain scanned. `SwapExecuted` from the legacy relayer: 0 (all `SwapExecuted` logs came from other contracts).
- **Samples:** Ethereum send `0x2c2818c5066f73cf21ab2918e0673fa0ade7729605d00cc22e7967579289d71c` (`transferTokens`: `Transfer` user → Token Bridge, `LogMessagePublished` with 320-byte data); Base send `0xa86b84a9306f513575322433b08b87b1745c39b5e4aed2fe8f126a5d44b88a5d`; Ethereum redeem `0x356ae3537cf211c2360f9ee6170812b2c1aef759f9206595857d760ecd716aaa` (`TransferRedeemed`, then release from the Token Bridge); Base redeem `0x2bd5675a6aaf1ee7ee0465ee9c8aa1fa13ec79c4baca1a78d9c9f0c72f01aeba`; wrapped burn `0x3a51f857b2eb59c19f32855e511159883f740b3fc960e8a0e5a0a3a4121ede6d`; referrer v2 send `0x18f5f0fed6d271e6c1a0faaa6a1757610235971943516cdcb0165c6f78d8438a` (`0xd2b431ed`, 352-byte data). A wrapped-token mint on redeem was not sampled; the mint path is from source.

Authoritative sources:
- [wormhole-foundation/wormhole](https://github.com/wormhole-foundation/wormhole) — `ethereum/contracts/bridge/` (Token Bridge, governance, wrapped token)
- [wormhole-foundation/example-token-bridge-relayer](https://github.com/wormhole-foundation/example-token-bridge-relayer) — `evm/src/token-bridge-relayer/`
- [wormhole-foundation/wormhole-sdk-ts](https://github.com/wormhole-foundation/wormhole-sdk-ts) — `core/base/src/constants/contracts/tokenBridge.ts`, `tokenBridgeRelayer.ts`, `executorTokenBridge.ts`
- Docs — [Contract addresses (WTT)](https://wormhole.com/docs/reference/contract-addresses/) · [WTT contracts guide](https://wormhole.com/docs/products/token-transfers/wrapped-token-transfers/guides/wtt-contracts/) · [Executor addresses](https://wormhole.com/docs/reference/executor-addresses/)
- Explorers — [Etherscan Token Bridge](https://etherscan.io/address/0x3ee18b2214aff97000d974cf647e7c347e8fa585) · [Basescan Token Bridge](https://basescan.org/address/0x8d2de8d2f73f1f4cab472ac9a881c9b123c79627) · [BscScan Token Bridge](https://bscscan.com/address/0xb6f6d86a8f9879a9c87f643768d9efc38c1da6e7)

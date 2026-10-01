# Wormhole CCTP Integration (Circle Integration, Circle Relayer, CCTP with Executor) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, Avalanche; NOT BNB, NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, `wormhole-foundation/wormhole-circle-integration`, `wormhole-foundation/example-circle-relayer` (archived), `wormholelabs-xyz/example-cctp-with-executor`, `core/base/src/constants/contracts/circle.ts` of the SDK, the Executor deployment registry and the Wormhole docs CCTP guide. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; implementations read from the EIP-1967 slot and scanned for each topic and selector.
**Scope:** the Wormhole contracts that wrap Circle's CCTP for native USDC: (1) the **Circle Integration** (`CircleIntegration`: a CCTP v1 burn plus a Wormhole message with a payload), (2) the **Circle Relayer** built on it, and (3) the Executor-era **CCTP v1 / v2 with Executor** helpers. They are deployed on **six chains: Ethereum, Base, Arbitrum, Optimism, Polygon and Avalanche. BNB and Robinhood Chain (4663) have none.** Circle's own contracts and events (TokenMessenger, MessageTransmitter, `DepositForBurn`, `MintAndWithdraw`) are documented in [../cctp/README.md](../cctp/README.md); this file lists only the topics a Wormhole monitor needs to join both sides.

The value moves as native USDC burned on the source and minted on the destination by Circle's contracts. Wormhole adds a message and a delivery service on top.

- **Circle Integration, source leg:** `transferTokensWithPayload` pulls USDC from the caller, calls CCTP v1 `depositForBurnWithCaller` (so CCTP emits `DepositForBurn` with `depositor` = the Circle Integration and `destinationCaller` = the target chain's Circle Integration), then publishes a Wormhole message (`LogMessagePublished`, `sender` = Circle Integration) whose payload carries the CCTP nonce, both domains, `fromAddress`, `mintRecipient` and an application payload.
- **Circle Integration, destination leg:** `redeemTokensWithPayload` is callable only by `mintRecipient`. It verifies the VAA, calls CCTP `receiveMessage` (CCTP emits `MessageReceived` and `MintAndWithdraw` to `mintRecipient`) and emits **`Redeemed(emitterChainId, emitterAddress, sequence)`**.
- **Link keys, both on chain:** the Wormhole key `(emitterChain, Circle Integration, sequence)` (source `LogMessagePublished` → destination `Redeemed`), and the CCTP v1 key `(sourceDomain, nonce)` (source `DepositForBurn.nonce` → destination `MessageReceived`).
- **CCTP with Executor:** `depositForBurn` on the helper pulls USDC (plus an optional referrer fee), calls Circle's TokenMessenger (v1 or v2) and the Executor (`RequestForExecution`) in one call. No Wormhole message is published: the Executor request (`ERC1` + (source domain, nonce) for v1, `ERC2` for v2) is the only Wormhole-side record. A relay provider then calls the receive-with-gas-drop-off helper on the destination, and Circle's events are the destination leg.
- **Refund, cancel, expiry:** none in these contracts. An unredeemed CCTP message stays redeemable.

---

## 0. Contract families

| Contract | Chains | Role | Proxy? |
|----------|--------|------|--------|
| **Circle Integration** | ETH, Base, ARB, OP, POLY, AVAX | CCTP v1 burn + Wormhole message; redeem to `mintRecipient`; emits `Redeemed`. | EIP-1967 proxy (177 B), upgraded by governance VAA (`upgradeContract`) |
| **Circle Relayer** (`example-circle-relayer`, archived) | same six chains at `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | Automatic relay on top of the Circle Integration, with relayer fee and native drop-off (`SwapExecuted`). | No (9,915 B) |
| **CCTPv1WithExecutor** (v2 active, v1 deprecated) | ETH, Base, ARB, OP, POLY, AVAX | Front-end helper: CCTP v1 burn + Executor request + referrer fee. | No |
| **CCTPv2WithExecutor** (v2 active, v1 deprecated) | same six chains | Same for CCTP v2 (`maxFee`, `minFinalityThreshold`). | No |
| **CCTPv1 / CCTPv2 receive-with-gas-drop-off** | same six chains | Destination helper used by relay providers: CCTP receive + native drop-off. | No (923 B) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Circle Integration — emitter = the Circle Integration proxy

| topic0 | Event |
|--------|-------|
| `0xf02867db6908ee5f81fd178573ae9385837f0a0a72553f8c08306759a7e0f00e` | `Redeemed(uint16 indexed emitterChainId, bytes32 indexed emitterAddress, uint64 indexed sequence)` — **destination leg (status; the mint is Circle's `MintAndWithdraw`)**; the same signature is also emitted by unrelated integrators (§7.2) |
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address indexed oldContract, address indexed newContract)` — admin; same topic0 as Core / Token Bridge |
| `0x0f76cb696a4940fef5ce2eb3690c1f2af5c481c123bce2a123da2e5b92a014a8` | `WormholeFinalityUpdated(uint8 indexed oldFinality, uint8 indexed newFinality)` — admin |
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — emitter = Core; **source leg when `sender` = Circle Integration** |

### 1.2 Circle Relayer — emitter = `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2`

| topic0 | Event |
|--------|-------|
| `0x764f0dc063c06f32d89a3f3af80c0db4be8a090901f589a478b447e0a51f09f1` | `SwapExecuted(address indexed recipient, address indexed relayer, address indexed token, uint256 tokenAmount, uint256 nativeAmount)` — native drop-off paid by the relayer; generic signature, key by emitter |
| `0x0d18b5fd22306e373229b9439188228edca81207d1667f604daf6cef8aa3ee67` | `OwnershipTransfered(address indexed oldOwner, address indexed newOwner)` — admin |
| `0xaaebcf1bfa00580e41d966056b48521fa9f202645c86d4ddf28113e617c1b1d3` | `FeeRecipientUpdated(address indexed oldRecipient, address indexed newRecipient)` — admin |
| `0xc6eb9fb936b61b402d503deeffc822f46492e15c2c8f079815cc4850ad7b02b0` | `SwapRateUpdated(address indexed token, uint256 indexed swapRate)` — admin |

### 1.3 Circle events in the same transactions (emitters = Circle's contracts; details in [../cctp/v1.md](../cctp/v1.md), [../cctp/v2.md](../cctp/v2.md))

| topic0 | Event |
|--------|-------|
| `0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0` | `DepositForBurn(uint64 indexed nonce, address indexed burnToken, uint256 amount, address indexed depositor, bytes32 mintRecipient, uint32 destinationDomain, bytes32 destinationTokenMessenger, bytes32 destinationCaller)` — CCTP v1 source; `depositor` = Circle Integration or the v1 helper |
| `0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5` | `DepositForBurn(address indexed burnToken, uint256 amount, address indexed depositor, bytes32 mintRecipient, uint32 destinationDomain, bytes32 destinationTokenMessenger, bytes32 destinationCaller, uint256 maxFee, uint32 indexed minFinalityThreshold, bytes hookData)` — CCTP v2 source; `depositor` = the v2 helper |
| `0x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d` | `MessageReceived(address indexed caller, uint32 sourceDomain, uint64 indexed nonce, bytes32 sender, bytes messageBody)` — CCTP v1 destination; `caller` = Circle Integration |
| `0x1b2a7ff080b8cb6ff436ce0372e399692bbfb6d4ae5766fd8d58a7b8cc6142e6` | `MintAndWithdraw(address indexed mintRecipient, uint256 amount, address indexed mintToken)` — CCTP v1 destination mint |
| `0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036` | `MessageSent(bytes message)` — CCTP v1 and v2 MessageTransmitter |

### 1.4 Payload of a Circle Integration message (`DepositWithPayload`, inside `LogMessagePublished.payload`)

`payloadId` = 1 (1 byte), `token` (bytes32, the source USDC), `amount` (uint256, 6 decimals, not normalized), `sourceDomain` (uint32), `targetDomain` (uint32), `nonce` (uint64, the CCTP nonce), `fromAddress` (bytes32, the caller of `transferTokensWithPayload`), `mintRecipient` (bytes32), payload length (uint16), `payload`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Contract / notes |
|----------|-----------|------------------|
| `0xa2a1f04c` | `transferTokensWithPayload((address token, uint256 amount, uint16 targetChain, bytes32 mintRecipient) transferParams, uint32 batchId, bytes payload)` | Circle Integration — source; payable (Core fee). |
| `0x57bf927b` | `redeemTokensWithPayload((bytes encodedWormholeMessage, bytes circleBridgeMessage, bytes circleAttestation) params)` | Circle Integration — destination; `msg.sender` must be `mintRecipient`; emits `Redeemed`. |
| `0x783ae141` | `upgradeContract(bytes encodedMessage)` | Circle Integration — governance VAA. **Admin.** |
| `0x943a646e` | `registerEmitterAndDomain(bytes encodedMessage)` | Circle Integration — governance VAA. **Admin.** |
| `0x6e7d969d` | `updateWormholeFinality(bytes encodedMessage)` | Circle Integration — governance VAA; emits `WormholeFinalityUpdated`. **Admin.** |
| `0x01a67b6b` | `circleBridge()` | Circle Integration view — CCTP v1 TokenMessenger. |
| `0xf10b29fc` | `circleTransmitter()` | Circle Integration view — CCTP v1 MessageTransmitter. |
| `0x8d3638f4` | `localDomain()` | Circle Integration view — CCTP domain. |
| `0x134f89bd` | `getDomainFromChainId(uint16 chainId_)` | Circle Integration view — Wormhole chain → CCTP domain. |
| `0x24816abb` | `getRegisteredEmitter(uint16 emitterChainId)` | Circle Integration view — peer Circle Integration. |
| `0x470feb87` | `isMessageConsumed(bytes32 hash)` | Circle Integration view — replay guard. |
| `0x59b87d8e` | `transferTokensWithRelay(address token, uint256 amount, uint256 toNativeTokenAmount, uint16 targetChain, bytes32 targetRecipientWallet)` | Circle Relayer — source. |
| `0x0a55d735` | `redeemTokens((bytes encodedWormholeMessage, bytes circleBridgeMessage, bytes circleAttestation) redeemParams)` | Circle Relayer — destination. |
| `0xdd6522aa` | `circleIntegration()` | Circle Relayer view. |
| `0x268d17a4` | `depositForBurn(uint256 amount, uint16 destinationChain, uint32 destinationDomain, bytes32 mintRecipient, address burnToken, (address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint256 transferTokenFee, uint256 nativeTokenFee, address payee) feeArgs)` | CCTPv1WithExecutor v2 (active); payable (Executor payment). |
| `0x5b0ce137` | `depositForBurn(uint256 amount, uint16 destinationChain, uint32 destinationDomain, bytes32 mintRecipient, address burnToken, (address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint16 dbps, address payee) feeArgs)` | CCTPv1WithExecutor v1 (deprecated). |
| `0xd01cbba9` | `depositForBurn(uint256 amount, uint16 destinationChain, uint32 destinationDomain, bytes32 mintRecipient, address burnToken, bytes32 destinationCaller, uint256 maxFee, uint32 minFinalityThreshold, (address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint256 transferTokenFee, uint256 nativeTokenFee, address payee) feeArgs)` | CCTPv2WithExecutor v2 (active). |
| `0xe59ced5d` | `depositForBurn(uint256 amount, uint16 destinationChain, uint32 destinationDomain, bytes32 mintRecipient, address burnToken, bytes32 destinationCaller, uint256 maxFee, uint32 minFinalityThreshold, (address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint16 dbps, address payee) feeArgs)` | CCTPv2WithExecutor v1 (deprecated). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All existence-checked with `eth_getCode` on 2026-09-29. Wormhole chain id **2**, CCTP domain **0** (`localDomain()`).

| Role | Address | One-liner |
|------|---------|-----------|
| **Circle Integration** (proxy) | `0xAaDA05BD399372f0b0463744C09113c137636f6a` | 177 B proxy; implementation `0x37f26277b1927c6bedbd94e5c21c337a706af31c` (13,272 B); `circleBridge()` = `0xBd3fa81B58Ba92a82136038B25aDec7066af3155`, `circleTransmitter()` = `0x0a992d191DEeC32aFe36203Ad87D7d289a738F81`. |
| **Circle Relayer** | `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | `circleIntegration()` = the Circle Integration; `owner()` = `0x4d666a1fa38c25df6adbc1b6f1d716cc2a3525f8`. |
| CCTPv1WithExecutor (v2, active) | `0x6DDE92942DbB24F7c9B75765b74a33446980C1e3` | Contains `0x268d17a4`. |
| CCTPv2WithExecutor (v2, active) | `0xDD68aBa3E04CB1a05082402B9325753314803005` | Contains `0xd01cbba9`; sample `0xa88a6694cc976107e8268fd609a611d9af5feb7f956cf04f79c739be5a3f708f`. |
| CCTPv1 receive-with-gas-drop-off | `0x8656d3703EcbC5f36a9668A4859A7f1138bAB0b3` | Destination helper (923 B). |
| CCTPv2 receive-with-gas-drop-off | `0x588203D627cac76dB95edd5459d50c96f701D7B3` | Destination helper (923 B). |

---

## 4. Addresses — the other five chains

### 4.1 Circle Integration per chain

| Chain | EVM id | Wormhole id | CCTP domain | Circle Integration (proxy) | Implementation | `circleBridge()` (CCTP v1 TokenMessenger) | `circleTransmitter()` (CCTP v1 MessageTransmitter) |
|-------|--------|-------------|-------------|----------------------------|----------------|--------------------------------------------|----------------------------------------------------|
| Ethereum | 1 | 2 | 0 | `0xAaDA05BD399372f0b0463744C09113c137636f6a` | `0x37f26277b1927c6bedbd94e5c21c337a706af31c` | `0xBd3fa81B58Ba92a82136038B25aDec7066af3155` | `0x0a992d191DEeC32aFe36203Ad87D7d289a738F81` |
| Avalanche C-Chain | 43114 | 6 | 1 | `0x09Fb06A271faFf70A651047395AaEb6265265F13` | `0x20f989ad4c3b6ddcd940a66013d45f45d5c15463` | `0x6B25532e1060CE10cc3B0A99e5683b91BFDe6982` | `0x8186359aF5F57FbB40c6b14A588d2A59C0C29880` |
| Optimism | 10 | 24 | 2 | `0x2703483B1a5a7c577e8680de9Df8Be03c6f30e3c` | `0xd73afd826d6bdd4d2fef326df5091451a5d8130a` | `0x2B4069517957735bE00ceE0fadAE88a26365528f` | `0x4D41f22c5a0e5c74090899E5a8Fb597a8842b3e8` |
| Arbitrum One | 42161 | 23 | 3 | `0x2703483B1a5a7c577e8680de9Df8Be03c6f30e3c` | `0xd73afd826d6bdd4d2fef326df5091451a5d8130a` | `0x19330d10D9Cc8751218eaf51E8885D058642E08A` | `0xC30362313FBBA5cf9163F0bb16a0e01f01A896ca` |
| Base | 8453 | 30 | 6 | `0x03faBB06Fa052557143dC28eFCFc63FC12843f1D` | `0x2703483b1a5a7c577e8680de9df8be03c6f30e3c` | `0x1682Ae6375C4E4A97e4B583BC394c861A46D8962` | `0xAD09780d193884d503182aD4588450C416D6F9D4` |
| Polygon PoS | 137 | 5 | 7 | `0x0FF28217dCc90372345954563486528aa865cDd6` | `0x03fabb06fa052557143dc28efcfc63fc12843f1d` | `0x9daF8c91AEFAE50b9c0E69629D3F6Ca40cA3B3FE` | `0xF3be9355363857F3e001be68856A2f96b4C39Ba9` |
| BNB Smart Chain | 56 | 4 | — | ❌ `0x` at `0xAaDA05BD399372f0b0463744C09113c137636f6a`; no SDK entry | — | — | — |
| **Robinhood Chain** | 4663 | 72 | — | ❌ no entry, `0x` at the Ethereum address | — | — | — |

`chainId()` and `wormhole()` returned the local Wormhole id and Core on every chain read. The implementations contain `Redeemed`, `ContractUpgraded`, `WormholeFinalityUpdated`, `transferTokensWithPayload` and `redeemTokensWithPayload`.

### 4.2 Circle Relayer and CCTP-with-Executor helpers per chain

| Chain | Circle Relayer | CCTPv1WithExecutor (v2) | CCTPv2WithExecutor (v2) | CCTPv1 receive helper | CCTPv2 receive helper |
|-------|----------------|-------------------------|-------------------------|-----------------------|-----------------------|
| Ethereum | `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | `0x6DDE92942DbB24F7c9B75765b74a33446980C1e3` | `0xDD68aBa3E04CB1a05082402B9325753314803005` | `0x8656d3703EcbC5f36a9668A4859A7f1138bAB0b3` | `0x588203D627cac76dB95edd5459d50c96f701D7B3` |
| Base | `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | `0x4D1Cc8921e297155044C01761f581fa52a24C33d` | `0x52892976559fB2fc8b7f850440eD9AA5Dc26f7D9` | `0x83A15D45527951f963A4413Ec078f8f99f54b3fd` | `0x588203D627cac76dB95edd5459d50c96f701D7B3` |
| Arbitrum One | `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | `0x772373214238F09a494828A5323574E3d7e27558` | `0x760feC4425B46E3D8FEf8E2CE49786e5a6f74446` | `0x57D193d3FED858A7D2745e546b0FD231D3dD6134` | `0x588203D627cac76dB95edd5459d50c96f701D7B3` |
| Optimism | `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | `0x6826c075973a4393CEf0e131c4B16869426563a7` | `0x9b51579e67D4ab18D79609105509ad37B2a0D342` | `0xFE188A2f0bd6Eb3734B4892be2F6721A0316e27C` | `0xD64341A38a5eAfb9EB9BACf8A5C52Fe858c4ABE9` |
| Polygon PoS | `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | `0x7e6Ae241101B355447A4B471D0C6968b132eC4Ab` | `0x5116F1358ae2445f571AA702dA1feB5e13094E59` | `0xbB1A18453D17C91ffa0638Cb12D5B81dfb1c695B` | `0xD64341A38a5eAfb9EB9BACf8A5C52Fe858c4ABE9` |
| Avalanche C-Chain | `0x4cb69FaE7e7Af841e44E1A1c30Af640739378bb2` | `0x58aC806cd205083E7E048E196f36Ff6C4Ae17bE5` | `0xE42aE9e352157fcEf74E971F2C5c74A5963a71D7` | `0x6abeF0e847e9E5baEa28B1Ffa4a51EA11Ae424db` | `0x588203D627cac76dB95edd5459d50c96f701D7B3` |
| BNB / Robinhood | ❌ | ❌ | ❌ | ❌ | ❌ |

Deprecated v1 helpers (Executor registry, marked `deprecated`): CCTPv1WithExecutor — ETH `0xeEFb36c4458dA7798742cf038C5c27E07aB9c51E`, Base `0x08FEB1838C3d7F8509DA1EBb9a11a94c1f006cb2`, ARB `0x55Dd4466BFec29527C54A72fd306efb54e5F7027`, OP `0xBC6f9d1CBa49DB365728478cefa02F6743617637`, POLY `0x007995f2AEcfBC745f20a7AE8D3a02c0EbF46264`, AVAX `0xd331819478b74d8a7B8EA631118B4a4e50F6EbD1`; CCTPv2WithExecutor — ETH `0x2cCf230467FE7387674BAa657747F0B5485c7fEC`, Base `0xbd8d42f40a11b37bD1b3770D754f9629F7cd5679`, ARB `0x8442d68524217601ed126f6859694E4B0C7c66A1`, OP `0xd0A8940b2e743E33b682dAEc4D52b46713606C9D`, POLY `0xc8A8E6D760dCBd5d6746E2F66cd2fFA722dd1E59`, AVAX `0x3952914628650Ca510404872D84DfF10A844C5B5`. All twelve still have code (2,571 B for the v1 helpers, 2,394 B for the v2 helpers).

---

## 5. Cross-chain summary

| Chain | EVM id | Wormhole id | CCTP domain | Circle Integration | Circle Relayer | CCTP v1 / v2 with Executor |
|-------|--------|-------------|-------------|--------------------|----------------|----------------------------|
| Ethereum | 1 | 2 | 0 | `0xAaDA05BD399372f0b0463744C09113c137636f6a` | ✅ | ✅ / ✅ |
| Base | 8453 | 30 | 6 | `0x03faBB06Fa052557143dC28eFCFc63FC12843f1D` | ✅ | ✅ / ✅ |
| Arbitrum One | 42161 | 23 | 3 | `0x2703483B1a5a7c577e8680de9Df8Be03c6f30e3c` | ✅ | ✅ / ✅ |
| Optimism | 10 | 24 | 2 | `0x2703483B1a5a7c577e8680de9Df8Be03c6f30e3c` | ✅ | ✅ / ✅ |
| Polygon PoS | 137 | 5 | 7 | `0x0FF28217dCc90372345954563486528aa865cDd6` | ✅ | ✅ / ✅ |
| Avalanche C-Chain | 43114 | 6 | 1 | `0x09Fb06A271faFf70A651047395AaEb6265265F13` | ✅ | ✅ / ✅ |
| BNB Smart Chain | 56 | 4 | — | ❌ `0x` | ❌ `0x` | ❌ |
| **Robinhood Chain** | 4663 | 72 | — | ❌ | ❌ | ❌ |

**Address reuse:** `0x2703483B1a5a7c577e8680de9Df8Be03c6f30e3c` is the Circle Integration proxy on Arbitrum and Optimism and the Circle Integration **implementation** on Base; `0x03faBB06Fa052557143dC28eFCFc63FC12843f1D` is the proxy on Base and the implementation on Polygon. Key on `(chain, address)` and read the EIP-1967 slot.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Circle Integration** (6 chains) | EIP-1967 proxy (177 B, `CircleIntegrationProxy`); upgrade logic in `CircleIntegrationGovernance` | Implementation slot populated (§4.1); admin slot 0 on every chain read | Guardian governance VAA (`upgradeContract`), emitter chain 1, emitter `0x0000000000000000000000000000000000000000000000000000000000000004` |
| Circle Relayer | Not a proxy (9,915 B) | Implementation slot 0 | Owner (`0x4d666a1fa38c25df6adbc1b6f1d716cc2a3525f8`) for fees, swap rates and pause; `OwnershipTransfered` on change |
| CCTP-with-Executor helpers, receive helpers | Not proxies | Implementation slot 0 | Immutable |

---

## 7. Detection invariants & gotchas

1. **The Circle Integration was idle in the window.** `Redeemed` from a Circle Integration: 0 on the six chains; `LogMessagePublished` with `sender` = Circle Integration: 0 on Ethereum, Base, Arbitrum, Optimism and Avalanche. Current Wormhole USDC routes use the CCTP-with-Executor helpers, which publish no Wormhole message.
2. **`Redeemed(uint16,bytes32,uint64)` is not unique to the Circle Integration.** In the window, the only `Redeemed` logs on Ethereum (5) came from `0xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4`, an integrator that emits it after a Token Bridge redemption of WETH (sample `0x054fcd0d83bbe377056e0d9d3028a417c1fc82800dcdb5eedd881ce8fede316a`). Key on the Circle Integration address.
3. **The CCTP `depositor` is the Wormhole contract, not the user.** `DepositForBurn.depositor` = the Circle Integration or the helper. The user is `fromAddress` in the Wormhole payload (Circle Integration) or `tx.from` / the helper's `Transfer` sender (helpers).
4. **`redeemTokensWithPayload` must be called by `mintRecipient`.** The minted USDC goes to that contract, which acts in the same transaction; follow its transfers.
5. **Two keys, both on chain for CCTP v1.** Join the Circle Integration flow by the Wormhole key (`LogMessagePublished` ↔ `Redeemed`) or by the CCTP v1 key (`DepositForBurn.nonce` ↔ `MessageReceived.nonce` with `sourceDomain`). For the CCTP v2 helper, the source has no nonce on chain (CCTP v2); use Circle's API or the transaction hash (see [../cctp/v2.md](../cctp/v2.md)).
6. **Referrer fees ride in the same transaction.** The helpers pull `amount` + `transferTokenFee` and pay `payee` before the burn (sample `0xa88a6694cc976107e8268fd609a611d9af5feb7f956cf04f79c739be5a3f708f`: two USDC transfers into the helper, one to the payee, one to Circle's TokenMinter, then the burn and `RequestForExecution` with `msg.value` 129,280,658,916,604 wei).
7. **BNB has CCTP v2 contracts (Circle) but no Wormhole CCTP contract.** No Circle Integration, Circle Relayer or helper has code on BNB, and none is listed.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_REDEEMED                = '\xf02867db6908ee5f81fd178573ae9385837f0a0a72553f8c08306759a7e0f00e'
TOPIC_WORMHOLE_FINALITY_UPD   = '\x0f76cb696a4940fef5ce2eb3690c1f2af5c481c123bce2a123da2e5b92a014a8'
TOPIC_CONTRACT_UPGRADED       = '\x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49'
TOPIC_SWAP_EXECUTED           = '\x764f0dc063c06f32d89a3f3af80c0db4be8a090901f589a478b447e0a51f09f1'
TOPIC_CCTP_V1_DEPOSIT_FOR_BURN= '\x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0'
TOPIC_CCTP_V2_DEPOSIT_FOR_BURN= '\x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5'
TOPIC_CCTP_V1_MESSAGE_RECEIVED= '\x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d'
TOPIC_CCTP_V1_MINT_AND_WITHDRAW='\x1b2a7ff080b8cb6ff436ce0372e399692bbfb6d4ae5766fd8d58a7b8cc6142e6'

-- ===== Selectors =====
SEL_CI_TRANSFER_WITH_PAYLOAD  = '\xa2a1f04c'
SEL_CI_REDEEM_WITH_PAYLOAD    = '\x57bf927b'
SEL_CI_UPGRADE_CONTRACT       = '\x783ae141'
SEL_CR_TRANSFER_WITH_RELAY    = '\x59b87d8e'
SEL_CR_REDEEM_TOKENS          = '\x0a55d735'
SEL_CCTP_V1_EXEC_DEPOSIT      = '\x268d17a4'
SEL_CCTP_V2_EXEC_DEPOSIT      = '\xd01cbba9'

-- ===== Circle Integration per chain (no BNB, no Robinhood) =====
ETH_CIRCLE_INTEGRATION        = '\xaada05bd399372f0b0463744c09113c137636f6a'
AVAX_CIRCLE_INTEGRATION       = '\x09fb06a271faff70a651047395aaeb6265265f13'
OP_CIRCLE_INTEGRATION         = '\x2703483b1a5a7c577e8680de9df8be03c6f30e3c'
ARB_CIRCLE_INTEGRATION        = '\x2703483b1a5a7c577e8680de9df8be03c6f30e3c'
BASE_CIRCLE_INTEGRATION       = '\x03fabb06fa052557143dc28efcfc63fc12843f1d'
POLY_CIRCLE_INTEGRATION       = '\x0ff28217dcc90372345954563486528aa865cdd6'

-- ===== Circle Relayer (same address on the six chains) =====
ETH_CIRCLE_RELAYER            = '\x4cb69fae7e7af841e44e1a1c30af640739378bb2'

-- ===== CCTP with Executor (active v2 helpers) =====
ETH_CCTP_V1_WITH_EXECUTOR     = '\x6dde92942dbb24f7c9b75765b74a33446980c1e3'
BASE_CCTP_V1_WITH_EXECUTOR    = '\x4d1cc8921e297155044c01761f581fa52a24c33d'
ARB_CCTP_V1_WITH_EXECUTOR     = '\x772373214238f09a494828a5323574e3d7e27558'
OP_CCTP_V1_WITH_EXECUTOR      = '\x6826c075973a4393cef0e131c4b16869426563a7'
POLY_CCTP_V1_WITH_EXECUTOR    = '\x7e6ae241101b355447a4b471d0c6968b132ec4ab'
AVAX_CCTP_V1_WITH_EXECUTOR    = '\x58ac806cd205083e7e048e196f36ff6c4ae17be5'
ETH_CCTP_V2_WITH_EXECUTOR     = '\xdd68aba3e04cb1a05082402b9325753314803005'
BASE_CCTP_V2_WITH_EXECUTOR    = '\x52892976559fb2fc8b7f850440ed9aa5dc26f7d9'
ARB_CCTP_V2_WITH_EXECUTOR     = '\x760fec4425b46e3d8fef8e2ce49786e5a6f74446'
OP_CCTP_V2_WITH_EXECUTOR      = '\x9b51579e67d4ab18d79609105509ad37b2a0d342'
POLY_CCTP_V2_WITH_EXECUTOR    = '\x5116f1358ae2445f571aa702da1feb5e13094e59'
AVAX_CCTP_V2_WITH_EXECUTOR    = '\xe42ae9e352157fcef74e971f2c5c74a5963a71d7'
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `evm/src/interfaces/ICircleIntegration.sol` and `circle_integration/CircleIntegration*.sol` (Circle Integration), `evm/src/interfaces/ICircleRelayer.sol` and `circle-relayer/CircleRelayerGovernance.sol` (Circle Relayer), and `src/CCTPv1WithExecutor/*/interfaces/ICCTPv1WithExecutor.sol`, `src/CCTPv2WithExecutor/*/interfaces/ICCTPv2WithExecutor.sol` (helpers). The Circle Integration implementations were scanned for `Redeemed`, `ContractUpgraded`, `WormholeFinalityUpdated` and the two entry selectors on Ethereum, Base, Arbitrum, Optimism and Avalanche; the Circle Relayer for `SwapExecuted`, `SwapRateUpdated(address,uint256)`, `OwnershipTransfered`, `FeeRecipientUpdated` and its two entry selectors; the active helpers for `0x268d17a4` and `0xd01cbba9` (and the absence of the deprecated `0x5b0ce137` / `0xe59ced5d`).
- **Addresses:** `circle.ts` of the SDK (`wormhole` = Circle Integration, `wormholeRelayer` = Circle Relayer) and the Executor deployment registry (namespaces `w7/cctp-v1/*`, `w7/cctp-v2/*`); all active addresses existence-checked with `eth_getCode`; `circleBridge()`, `circleTransmitter()`, `localDomain()`, `chainId()`, `wormhole()` and `circleIntegration()` read live. BNB: `eth_getCode` = `0x` for the Circle Integration (Ethereum address) and the Circle Relayer.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `Redeemed` at the Circle Integrations: 0 on Ethereum, Base, Arbitrum, Optimism, Avalanche and Polygon. `LogMessagePublished` from the Circle Integrations: 0 on the five chains with a sender split. `SwapExecuted` from the Circle Relayer: 0. `RequestForExecution` totals (all Executor requests, CCTP helpers included) are in [relayer.md](relayer.md).

Authoritative sources:
- [wormhole-foundation/wormhole-circle-integration](https://github.com/wormhole-foundation/wormhole-circle-integration) — `evm/src/`
- [wormhole-foundation/example-circle-relayer](https://github.com/wormhole-foundation/example-circle-relayer) — `evm/src/` (archived)
- [wormholelabs-xyz/example-cctp-with-executor](https://github.com/wormholelabs-xyz/example-cctp-with-executor) — `src/`
- [wormhole-foundation/wormhole-sdk-ts](https://github.com/wormhole-foundation/wormhole-sdk-ts) — `core/base/src/constants/contracts/circle.ts`
- Docs — [Interact with CCTP contracts](https://wormhole.com/docs/products/cctp-bridge/guides/cctp-contracts/) · [Integrate CCTP with Executor](https://wormhole.com/docs/protocol/infrastructure-guides/cctp-executor/) · [Executor addresses](https://wormhole.com/docs/reference/executor-addresses/)
- Explorers — [Etherscan Circle Integration](https://etherscan.io/address/0xaada05bd399372f0b0463744c09113c137636f6a) · [Etherscan CCTPv2WithExecutor](https://etherscan.io/address/0xdd68aba3e04cb1a05082402b9325753314803005)

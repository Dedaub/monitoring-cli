# Axelar Network — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on all seven listed chains and the canonical `axelarnetwork/axelar-cgp-solidity` + `axelarnetwork/interchain-token-service` repos on 2026-06-09. Topic0s/selectors recomputed locally as `keccak256(signature)` and cross-checked against live `eth_getLogs` + deployed-bytecode `PUSH32`/`PUSH4` scans; addresses existence-checked via `eth_getCode`; proxy impls read live.
**Scope:** the EVM contracts of Axelar's General Message Passing (GMP) layer — **AxelarGateway** (cross-chain call/token gateway), **AxelarGasService** (relayer gas prepayment), and the **Interchain Token Service (ITS)** stack (ITS + InterchainTokenFactory + TokenManager + InterchainToken). Topics and selectors are **chain-agnostic**; addresses are network-specific. All seven target chains carry the full stack.

Axelar is a **proof-of-stake message-passing network**, not a lock/mint bridge with a single vault. Source chains emit a `ContractCall` (or `ContractCallWithToken`/`TokenSent`) event on the **AxelarGateway**; a decentralized validator set observes it, reaches consensus off-chain, and the relayer submits an `execute(bytes)` batch to the **destination** gateway that flips the call to `approved`; the destination app then calls `validateContractCall` and runs its handler, emitting `ContractCallExecuted`. **The on-chain footprint is therefore split across two chains per message** — the outbound event and the inbound `ContractCallApproved`/`ContractCallExecuted` live on different gateways. Gas for the destination execution is prepaid on the **source** chain into the AxelarGasService (`NativeGasPaidForContractCall`, etc.), keyed by the source `txHash`/`logIndex` and the payload hash.

**Deterministic addressing, with one exception.** AxelarGasService, ITS, and InterchainTokenFactory are deployed via CREATE3-style constant-address tooling and share the **exact same proxy address on every EVM chain** (`0x2d5d…2712`, `0xB5FB…9e3C`, `0x83A9…0D66`) — and, on all seven, the **same implementation** address too. **The AxelarGateway proxy address is NOT constant** — it predates the constant-address tooling, so each chain has a different gateway proxy address (Ethereum `0x4F44…56A5`, Base/Optimism/Arbitrum `0xe432…8E31`, Avalanche `0x5029…8f78`, BNB `0x304a…D895`, Polygon `0x6f01…FBA8`) — but they all delegate to the **same gateway implementation** `0x99b5fa03a5ea4315725c43346e55a6a6fbd94098`. **The constant `0x4F44…56A5` is the Ethereum gateway only; on BNB and Arbitrum that literal address holds an unrelated decoy contract** (different bytecode, no Axelar interface) — never reuse the Ethereum gateway address cross-chain (see §6, §8).

This is a **single live generation** (the consensus "CGP" gateway + ITS v2), so one `core.md`. Axelar is also rolling out the next-gen **Amplifier** `AxelarAmplifierGateway` (`MessageApproved`/`MessageExecuted`/`SignersRotated` events) on newer chains; none of the seven target chains runs an Amplifier gateway as of 2026-06-09 — they all run the consensus gateway above. Amplifier topics are listed in §1.6 for completeness only.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Address style |
|----------|------|--------|---------------|
| **AxelarGateway** | Cross-chain GMP gateway: emits outbound `ContractCall`/`ContractCallWithToken`/`TokenSent`; verifies inbound via signed-operator `execute(bytes)` → `ContractCallApproved`. | **Custom proxy** (`AxelarGatewayProxy` / EternalStorage — `implementation()` getter, **NOT** the standard EIP-1967 slot) | **Per-chain** proxy address; shared impl `0x99b5fa03…` |
| **AxelarGasService** | Relayer gas escrow: `NativeGasPaidForContractCall`, `addNativeGas`, `refund`, `collectFees`. | **EIP-1967** proxy + Ownable2Step | **Constant** `0x2d5d…2712` on all 7 |
| **InterchainTokenService (ITS)** | Token bridging hub: deploys token managers, routes `InterchainTransfer`, mints/burns canonical interchain tokens. | **EIP-1967** proxy + Ownable2Step + Pausable | **Constant** `0xB5FB…9e3C` on all 7 |
| **InterchainTokenFactory** | User-facing factory over ITS: register canonical tokens, deploy interchain tokens, link custom tokens. | **EIP-1967** proxy | **Constant** `0x83A9…0D66` on all 7 |
| **TokenManager** (impl) | Per-token escrow/mint-burn manager. ITS deploys one clone per `tokenId`. Emits `FlowLimitSet`. | Minimal-proxy clones of impl `0x8832…2a9e` | per-token (derived from `tokenId`) |
| **InterchainToken** (impl) | ERC-20 mint/burn token with `interchainTransfer`. Deployed per `tokenId` by InterchainTokenDeployer. | clones of impl `0x7f9f…8819` | per-token |
| **TokenHandler / deployers** | ITS internal helpers (`InterchainTokenDeployer` `0xb769…69a3`, `TokenManagerDeployer` `0xdfef…7d24`, `TokenHandler` `0x383d…e7da`). | plain (no proxy) | constant on all 7 |

The ITS impl on all seven chains is the identical `0x1b13a9baf8d3116c56ccdf3aa9049ad532a9c03d`; GasService impl `0xcb5c784dcf8ff342625dbc53b356ed0cbb0ebb9b`; Factory impl `0xe833e9662cb0a811aa3b1746280ab43507b61946`. Wiring confirmed live: `ITS.gateway()` = the Ethereum gateway, `ITS.gasService()` = `0x2d5d…2712`, `ITS.interchainTokenFactory()` = `0x83A9…0D66`, `Factory.interchainTokenService()` = `0xB5FB…9e3C`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09. Items marked **(live)** were additionally confirmed in real `eth_getLogs` output from the Ethereum gateway/gas-service/ITS; items marked **(bytecode)** were confirmed by a `PUSH32` constant scan of the deployed implementation.

### 1.1 AxelarGateway

| topic0 | Event |
|--------|-------|
| `0x30ae6cc78c27e651745bf2ad08a11de83910ac1e347a52f7ac898c0fbef94dae` | `ContractCall(address indexed sender, string destinationChain, string destinationContractAddress, bytes32 indexed payloadHash, bytes payload)` **(live)** |
| `0x7e50569d26be643bda7757722291ec66b1be66d8283474ae3fab5a98f878a7a2` | `ContractCallWithToken(address indexed sender, string destinationChain, string destinationContractAddress, bytes32 indexed payloadHash, bytes payload, string symbol, uint256 amount)` **(live)** |
| `0x651d93f66c4329630e8d0f62488eff599e3be484da587335e8dc0fcf46062726` | `TokenSent(address indexed sender, string destinationChain, string destinationAddress, string symbol, uint256 amount)` **(bytecode)** |
| `0x44e4f8f6bd682c5a3aeba93601ab07cb4d1f21b2aab1ae4880d9577919309aa4` | `ContractCallApproved(bytes32 indexed commandId, string sourceChain, string sourceAddress, address indexed contractAddress, bytes32 indexed payloadHash, bytes32 sourceTxHash, uint256 sourceEventIndex)` **(live)** |
| `0x9991faa1f435675159ffae64b66d7ecfdb55c29755869a18db8497b4392347e0` | `ContractCallApprovedWithMint(bytes32 indexed commandId, string sourceChain, string sourceAddress, address indexed contractAddress, bytes32 indexed payloadHash, string symbol, uint256 amount, bytes32 sourceTxHash, uint256 sourceEventIndex)` **(live)** |
| `0x91057b069763121972ce22b18b2f319b1520dd4c72f1f94a6395e81ceaf63f41` | `ContractCallExecuted(bytes32 indexed commandId)` **(live)** — fires on the **destination** chain when the approved call's handler succeeds |
| `0xa74c8847d513feba22a0f0cb38d53081abf97562cdb293926ba243689e7c41ca` | `Executed(bytes32 indexed commandId)` **(live)** — a gateway command (approve/mint/transfer-op) was executed |
| `0xbf90b5a1ec9763e8bf4b9245cef0c28db92bab309fc2c5177f17814f38246938` | `TokenDeployed(string symbol, address tokenAddresses)` **(bytecode)** — gateway-managed (legacy) bridged token |
| `0x192e759e55f359cd9832b5c0c6e38e4b6df5c5ca33f3bd5c90738e865a521872` | `OperatorshipTransferred(bytes newOperatorsData)` **(bytecode)** — validator-set / operator rotation |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — impl pointer changed (watch for gateway upgrades) |

### 1.2 AxelarGasService

The live deployment uses **native-gas** payment events; the ERC-20-token gas-payment events still exist in the canonical ABI (and may be emitted by callers that wrap the token-pay path) but were not observed live on Ethereum.

| topic0 | Event |
|--------|-------|
| `0x617332c1832058df6ee45fcbdf471251474c9945a8e5d229287a21a5f67ccf0a` | `NativeGasPaidForContractCall(address indexed sourceAddress, string destinationChain, string destinationAddress, bytes32 indexed payloadHash, uint256 gasFeeAmount, address refundAddress)` **(live)** |
| `0x999d431b58761213cf53af96262b67a069cbd963499fd8effd1e21556217b841` | `NativeGasPaidForContractCallWithToken(address indexed sourceAddress, string destinationChain, string destinationAddress, bytes32 indexed payloadHash, string symbol, uint256 amount, uint256 gasFeeAmount, address refundAddress)` **(live)** |
| `0x8c092067e86e85e8cfbaf187202ef580cdfd7ec37fbec89191607de73ca80005` | `NativeGasPaidForExpressCallWithToken(address indexed sourceAddress, string destinationChain, string destinationAddress, bytes32 indexed payloadHash, string symbol, uint256 amount, uint256 gasFeeAmount, address refundAddress)` **(live)** |
| `0x5cf48f121a0fecaa2c4a64b3eaf482c8c308d5387e161535970f3e9e4363eff6` | `NativeGasPaidForExpressCall(address indexed sourceAddress, string destinationChain, string destinationAddress, bytes32 indexed payloadHash, uint256 gasFeeAmount, address refundAddress)` |
| `0xfeb6b00343feee0f29a1a4345f8bf93ca1c73ee922248a4237a4e50d6447604e` | `NativeGasAdded(bytes32 indexed txHash, uint256 indexed logIndex, uint256 gasFeeAmount, address refundAddress)` **(live)** — top-up of an already-broadcast message |
| `0xb26db521e067acd5c6e345ad92fa1ed06bc7fb2aedd68f35dc7a2e10d636fc98` | `NativeExpressGasAdded(bytes32 indexed txHash, uint256 indexed logIndex, uint256 gasFeeAmount, address refundAddress)` |
| `0xd5df103822011013c8c940930e5180419111c65abadd6525ca7e740d56b4703f` | `Refunded(bytes32 indexed txHash, uint256 indexed logIndex, address receiver, address token, uint256 amount)` **(live)** |
| `0xe99c92ee8ad7ab7a540ba6a6c24c50519b613b5c4b073ff89d38a1f708a6a744` | `GasPaidForContractCall(address indexed sourceAddress, string destinationChain, string destinationAddress, bytes32 indexed payloadHash, uint256 gasFeeAmount, address gasToken, uint256 amount, address refundAddress)` — ERC-20-token gas (canonical ABI; not observed live) |
| `0x60c590eed3ae2e2d679ea12cf03c24da7b7a27686b2e1e6c2c4e4a581947994b` | `GasPaidForContractCallWithToken(address indexed sourceAddress, string destinationChain, string destinationAddress, bytes32 indexed payloadHash, uint256 amount, string symbol, uint256 gasToken_amount, address gasToken, uint256 gasFeeAmount, address refundAddress)` — ERC-20-token gas (canonical ABI) |
| `0x77be1442a341c8eb6214c4bf26f880034d64001ead6125724d9da528ce050c57` | `GasAdded(bytes32 indexed txHash, uint256 indexed logIndex, uint256 gasFeeAmount, address refundAddress)` — ERC-20-token gas top-up (canonical ABI) |

### 1.3 InterchainTokenService (ITS)

| topic0 | Event |
|--------|-------|
| `0xcd05f5b9dc4bb03babf40f5da98f5f46819846207d916f89b67d36fd1f7fd74f` | `InterchainTransfer(bytes32 indexed tokenId, address indexed sourceAddress, string destinationChain, bytes destinationAddress, uint256 amount, bytes32 indexed dataHash)` **(live)** — outbound token transfer |
| `0xbdb65cfd017af0876344138f62bc895163b5fd120cbe6e666ed306afd658de4b` | `InterchainTransferReceived(bytes32 indexed commandId, bytes32 indexed tokenId, string sourceChain, bytes sourceAddress, address indexed destinationAddress, uint256 amount, bytes32 dataHash)` **(live)** — inbound token transfer fulfilled |
| `0x5284c2478b9c1a55e973429331078be39b5fb3eeb9d87d10b34d65a4c89ee4eb` | `TokenManagerDeployed(bytes32 indexed tokenId, address tokenManager, uint8 indexed tokenManagerType, bytes params)` **(live, bytecode)** |
| `0xf0d7beb2b03d35e597f432391dc2a6f6eb1a621be6cb5b325f55a49090085239` | `InterchainTokenDeployed(bytes32 indexed tokenId, address tokenAddress, address indexed minter, string name, string symbol, uint8 decimals)` **(live, bytecode)** |
| `0xe470f4bdd33c8676127d3c20ff725d8dc1605609001389ce3a59c28b54b7992f` | `InterchainTokenDeploymentStarted(bytes32 indexed tokenId, string name, string symbol, uint8 decimals, bytes minter, string destinationChain)` **(bytecode)** — remote interchain-token deploy queued |
| `0x6d8eb6e760238fe99c48de1a8bec4365cbeead2dbe47669c989722eaaa64a847` | `LinkTokenStarted(bytes32 indexed tokenId, string destinationChain, bytes sourceTokenAddress, bytes destinationTokenAddress, uint8 tokenManagerType, bytes linkParams)` **(bytecode)** — custom-token link queued |
| `0xdb6b260ea45f7fe513e1d3b8c21017a29e3a41610e95aefb8862b81c69aec61c` | `TrustedAddressSet(string chain, string address)` **(bytecode)** |
| `0xf9400637a329865492b8d0d4dba4eafc7e8d5d0fae5e27b56766816d2ae1b2ca` | `TrustedAddressRemoved(string chain)` **(bytecode)** |
| `0x6e18757e81c44a367109cbaa499add16f2ae7168aab9715c3cdc36b0f7ccce92` | `ExpressExecuted(bytes32 indexed commandId, string sourceChain, string sourceAddress, bytes32 indexed payloadHash, address indexed expressExecutor)` **(bytecode)** |
| `0x8fe61b2d4701a29265508750790e322b2c214399abdf98472158b8908b660d41` | `ExpressExecutionFulfilled(bytes32 indexed commandId, string sourceChain, string sourceAddress, bytes32 indexed payloadHash, address indexed expressExecutor)` **(bytecode)** |
| `0x04ddbfaa222e81ab9447c070310e87608bf6a4c5d42be5c2fdf0f370b186af79` | `InterchainTokenIdClaimed(bytes32 indexed tokenId, address indexed deployer, bytes32 indexed salt)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` **(bytecode)** — OpenZeppelin Pausable (NOT a custom `PausedSet`) |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` **(bytecode)** |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — ITS impl rotation (watch this) |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

### 1.4 TokenManager (per-token clone)

| topic0 | Event |
|--------|-------|
| `0x024e856c5f6f5e287ff2be13db089b016f28a6ebe6aaffdfb5fa5b902fdd366b` | `FlowLimitSet(bytes32 indexed tokenId, address operator, uint256 flowLimit)` **(bytecode)** |
| `0xf77b8a946fdd43f9bcc59a65414e31d8ce6bff4d577ba280b22a4e0076f1fbae` | `RolesAdded(address indexed account, uint8 accountRoles)` |
| `0xb505728de48a106a73e5121ceb7de508f9038d2e7cb59049084f92b7b4060bc4` | `RolesRemoved(address indexed account, uint8 accountRoles)` |

### 1.5 InterchainToken (per-token ERC-20 clone)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` (ERC-20) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` (ERC-20 + EIP-2612) |
| `0xf77b8a946fdd43f9bcc59a65414e31d8ce6bff4d577ba280b22a4e0076f1fbae` | `RolesAdded(address,uint8)` (minter role) |

### 1.6 Amplifier gateway (NOT deployed on any of the seven — reference only)

Axelar's next-gen `AxelarAmplifierGateway` is **absent on all seven target chains** (they run the §1.1 consensus gateway). If/when it lands, watch these:

| topic0 | Event |
|--------|-------|
| `0x30ae6cc78c27e651745bf2ad08a11de83910ac1e347a52f7ac898c0fbef94dae` | `ContractCall(address,string,string,bytes32,bytes)` — same topic0 as §1.1 (shared signature) |
| `0x6d338c7b274d71c344e745d8639ee21c8dff7afea59173f79375f4b25de06e7e` | `MessageApproved(bytes32,string,string,address,bytes32)` |
| `0xe7d1e1f435233f7a187624ac11afaf32ee0da368cef8a5625be394412f619254` | `MessageExecuted(bytes32)` |
| `0xe7cf1d3405bd906f8500af030e1130f3affbe991be73471a0d3983fe3ca61ebc` | `SignersRotated(uint256,bytes32,bytes)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors marked **(impl)** were confirmed present in the live deployed implementation bytecode (PUSH4 scan, 2026-06-09).

### 2.1 AxelarGateway

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1c92115f` | `callContract(string destinationChain, string contractAddress, bytes payload)` | **(impl)** Emits `ContractCall`. The primary outbound GMP entrypoint. |
| `0xb5417084` | `callContractWithToken(string destinationChain, string contractAddress, bytes payload, string symbol, uint256 amount)` | **(impl)** Emits `ContractCallWithToken`. |
| `0x26ef699d` | `sendToken(string destinationChain, string destinationAddress, string symbol, uint256 amount)` | **(impl)** Emits `TokenSent` (legacy gateway-token bridge). |
| `0x09c5eabe` | `execute(bytes input)` | **(impl)** Relayer submits a signed operator batch (approvals/mints/op-transfer). Emits `Executed`/`ContractCallApproved`. |
| `0x5f6970c3` | `validateContractCall(bytes32 commandId, string sourceChain, string sourceAddress, bytes32 payloadHash)` → `bool` | **(impl)** Destination app calls this to consume an approval. |
| `0x1876eed9` | `validateContractCallAndMint(bytes32 commandId, string sourceChain, string sourceAddress, bytes32 payloadHash, string symbol, uint256 amount)` → `bool` | **(impl)** |
| `0xf6a5f9f5` | `isContractCallApproved(bytes32,string,string,address,bytes32)` → `bool` | **(impl)** View — is an inbound call approved & unconsumed. |
| `0xbc00c216` | `isContractCallAndMintApproved(bytes32,string,string,address,bytes32,string,uint256)` → `bool` | **(impl)** |
| `0xd26ff210` | `isCommandExecuted(bytes32 commandId)` → `bool` | **(impl)** Replay guard. |
| `0x935b13f6` | `tokenAddresses(string symbol)` → `address` | **(impl)** Gateway-managed bridged token by symbol. |
| `0x5c60da1b` | `implementation()` → `address` | **(impl)** **Read the impl via this getter — the standard EIP-1967 slot is empty (§8).** |
| `0x9ded06df` | `setup(bytes params)` | **(impl)** Proxy init / operator config. |
| `0xa3499c73` | `upgrade(address newImplementation, bytes32 newImplementationCodeHash, bytes setupParams)` | **(impl)** Governance upgrade — pairs with `Upgraded`. |
| `0x8291286c` | `contractId()` → `bytes32` | **(impl)** = `keccak256("axelar-gateway")` (`0xad2ae48b4d93c587cd1f0f8f269b84f57dbe98bbe5c61c4b6d324e6a667b3625`, confirmed live). |

### 2.2 AxelarGasService

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0c93e3bb` | `payNativeGasForContractCall(address sender, string destinationChain, string destinationAddress, bytes payload, address refundAddress)` | **(impl)** Prepay native gas. Emits `NativeGasPaidForContractCall`. |
| `0xc62c2002` | `payNativeGasForContractCallWithToken(address,string,string,bytes,string symbol,uint256 amount,address refundAddress)` | **(impl)** |
| `0xf61ed218` | `payNativeGasForExpressCall(address,string,string,bytes,address)` | **(impl)** |
| `0x2e9b7470` | `payNativeGasForExpressCallWithToken(address,string,string,bytes,string,uint256,address)` | **(impl)** |
| `0xedf936f2` | `payGas(address sender, string destinationChain, string destinationAddress, bytes payload, uint256 executionGasLimit, bool estimateOnChain, address refundAddress, bytes params)` | **(impl)** Unified gas-pay entrypoint (newer API). |
| `0xcd433ada` | `addNativeGas(bytes32 txHash, uint256 logIndex, address refundAddress)` | **(impl)** Top-up. Emits `NativeGasAdded`. |
| `0x4d238489` | `addNativeExpressGas(bytes32,uint256,address)` | **(impl)** |
| `0x36504721` | `refund(bytes32 txHash, uint256 logIndex, address receiver, address token, uint256 amount)` | **(impl)** Gas-collector refund. Emits `Refunded`. |
| `0x1055eaaf` | `collectFees(address receiver, address[] tokens, uint256[] amounts)` | **(impl)** Gas-collector sweep. |
| `0x135eaa70` | `estimateGasFee(string destinationChain, string destinationAddress, bytes payload, uint256 executionGasLimit, bytes params)` → `uint256` | **(impl)** On-chain fee quote. |
| `0x86389f02` | `getGasInfo(string chain)` → tuple | **(impl)** Per-chain gas params. |
| `0x892b5007` | `gasCollector()` → `address` | **(impl)** = `0x7ddb…efbc`. |
| `0x5c60da1b` | `implementation()` → `address` | **(impl)** |
| `0x8da5cb5b` | `owner()` → `address` | **(impl)** Ownable2Step owner = `0x7216…b1af`. |

> The legacy ERC-20-token gas-pay functions (`payGasForContractCall(address,string,string,bytes,address,address)` = `0xc3db7e67`, `payGasForContractCallWithToken` = `0x53561c42`, `addGas` = `0x235a2da9`, `addExpressGas` = `0x0db3d464`) are **absent from the live impl** — only the native-gas + unified `payGas` paths exist on this deployment.

### 2.3 InterchainTokenService (ITS)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xda081c73` | `interchainTransfer(bytes32 tokenId, string destinationChain, bytes destinationAddress, uint256 amount, bytes metadata, uint256 gasValue)` | **(impl)** `payable`. Emits `InterchainTransfer`. |
| `0xe1d40c77` | `deployInterchainToken(bytes32 salt, string destinationChain, string name, string symbol, uint8 decimals, bytes minter, uint256 gasValue)` | **(impl)** `payable`. |
| `0x0f4433d3` | `linkToken(bytes32 salt, string destinationChain, bytes destinationTokenAddress, uint8 tokenManagerType, bytes linkParams, uint256 gasValue)` | **(impl)** `payable`. Custom-token link. Emits `LinkTokenStarted`. |
| `0xf49c044a` | `registerCustomToken(bytes32 salt, address tokenAddress, uint8 tokenManagerType, bytes operator)` | **(impl)** Local custom-token registration. |
| `0x7fb53dc9` | `registerTokenMetadata(address tokenAddress, uint256 gasValue)` | **(impl)** `payable`. |
| `0x49160658` | `execute(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload)` | **(impl)** Inbound message handler (from gateway). |
| `0x65657636` | `expressExecute(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload)` | **(impl)** `payable`. Express (instant) execution by a liquidity provider. |
| `0x465a09e0` | `setFlowLimits(bytes32[] tokenIds, uint256[] flowLimits)` | **(impl)** Operator. |
| `0xc38bb537` | `setPauseStatus(bool paused)` | **(impl)** Owner. Emits `Paused`/`Unpaused`. |
| `0x9f409d77` | `setTrustedAddress(string chain, string address)` | **(impl)** Emits `TrustedAddressSet`. |
| `0xa5269ef1` | `interchainTokenId(address deployer, bytes32 salt)` → `bytes32` | **(impl)** Deterministic tokenId. |
| `0xf8c8a826` | `tokenManagerAddress(bytes32 tokenId)` → `address` | **(impl)** Deterministic TokenManager clone address. |
| `0xe82e71f8` | `interchainTokenAddress(bytes32 tokenId)` → `address` | **(impl)** |
| `0x7e10eb15` | `deployedTokenManager(bytes32 tokenId)` → `address` | **(impl)** Reverts if not deployed. |
| `0x477aedc7` | `trustedAddress(string chain)` → `string` | **(impl)** |
| `0x116191b6` | `gateway()` → `address` | **(impl)** = the chain's gateway. |
| `0x6a22d8cc` | `gasService()` → `address` | **(impl)** = `0x2d5d…2712`. |
| `0xca58b644` | `interchainTokenFactory()` → `address` | **(impl)** = `0x83A9…0D66`. |
| `0x864a0dcf` | `chainNameHash()` → `bytes32` | **(impl)** `keccak256(chainName)` (Ethereum = `keccak256("ethereum")`). |
| `0x7e151fa6` | `tokenManagerImplementation(uint256 tokenManagerType)` → `address` | **(impl)** = `0x8832…2a9e`. |
| `0x5c975abb` | `paused()` → `bool` | **(impl)** |

> The older `deployTokenManager(bytes32,string,uint8,bytes,uint256)` = `0x98d78c82` and `callContractWithInterchainToken(bytes32,string,bytes,uint256,bytes,uint256)` = `0x4b4578ba` are **absent** from this ITS impl — they were replaced by `linkToken`/`registerCustomToken` and by `interchainTransfer` with metadata.

### 2.4 InterchainTokenFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3e12f8c5` | `deployInterchainToken(bytes32 salt, string name, string symbol, uint8 decimals, uint256 initialSupply, address minter)` | **(impl)** `payable`. Deploy a fresh interchain token (local). |
| `0x5d79c00e` | `deployRemoteInterchainToken(string originalChainName, bytes32 salt, address minter, string destinationChain, uint256 gasValue)` | **(impl)** `payable`. |
| `0x010987dc` | `deployRemoteInterchainToken(bytes32 salt, string destinationChain, uint256 gasValue)` | **(impl)** `payable` (newer overload). |
| `0xa75483d1` | `registerCanonicalInterchainToken(address tokenAddress)` → `bytes32` | **(impl)** Wrap an existing ERC-20 as a canonical interchain token. |
| `0xa37fcf4e` | `deployRemoteCanonicalInterchainToken(address originalTokenAddress, string destinationChain, uint256 gasValue)` | **(impl)** `payable`. |
| `0x993a5b9e` | `deployRemoteCanonicalInterchainToken(string originalChain, address originalTokenAddress, string destinationChain, uint256 gasValue)` | **(impl)** `payable` overload. |
| `0xd8c03268` | `registerCustomToken(bytes32 salt, address tokenAddress, uint8 tokenManagerType, address operator)` | **(impl)** Custom-token register (factory variant — note `address operator`, vs ITS `bytes operator`). |
| `0xb2292888` | `canonicalInterchainTokenId(address tokenAddress)` → `bytes32` | **(impl)** |
| `0xa5269ef1` | `interchainTokenId(address deployer, bytes32 salt)` → `bytes32` | **(impl)** |
| `0x09c6bed9` | `interchainTokenService()` → `address` | **(impl)** = `0xB5FB…9e3C`. |

### 2.5 TokenManager (per-token clone)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6bec32da` | `mintToken(address tokenAddress, address to, uint256 amount)` | **(impl)** ITS-only. |
| `0x3416794d` | `burnToken(address tokenAddress, address from, uint256 amount)` | **(impl)** ITS-only. |
| `0x9d76ea58` | `tokenAddress()` → `address` | **(impl)** |
| `0x129d8188` | `interchainTokenId()` → `bytes32` | **(impl)** |
| `0x4fdf7cb5` | `implementationType()` → `uint256` | **(impl)** 0=NATIVE_INTERCHAIN_TOKEN, 1=MINT_BURN_FROM, 2=LOCK_UNLOCK, 3=LOCK_UNLOCK_FEE, 4=MINT_BURN. |
| `0x8b38b35d` | `flowLimit()` → `uint256` | **(impl)** |
| `0x7dbab19b` | `flowInAmount()` → `uint256` / `0x2f3c7888` `flowOutAmount()` | **(impl)** Current epoch flow. |
| `0xa56dbe63` | `setFlowLimit(uint256)` | **(impl)** Operator. Emits `FlowLimitSet`. |
| `0x120a63b5` | `addFlowLimiter(address)` / `0xdeb11e78` `isFlowLimiter(address)` | **(impl)** |

> `takeToken(address,uint256)` = `0xafd0f906` and `giveToken(address,uint256)` = `0x193f974c` are **absent** — this TokenManager exposes `mintToken`/`burnToken` instead.

### 2.6 InterchainToken (per-token ERC-20 clone)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address account, uint256 amount)` | **(impl)** Minter-role only. |
| `0x9dc29fac` | `burn(address account, uint256 amount)` | **(impl)** |
| `0xbc0ba3c5` | `interchainTransfer(string destinationChain, bytes recipient, uint256 amount, bytes metadata)` | **(impl)** `payable`. Token-side outbound. |
| `0xa60fee37` | `interchainTransferFrom(address sender, string destinationChain, bytes recipient, uint256 amount, bytes metadata)` | **(impl)** `payable`. |
| `0x129d8188` | `interchainTokenId()` → `bytes32` | **(impl)** |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Proxy impls read live (`implementation()` / EIP-1967 slot).

| Role | Address | Impl | One-liner |
|------|---------|------|-----------|
| **AxelarGateway** (proxy) | `0x4F4495243837681061C4743b74B3eEdf548D56A5` | `0x99b5fa03a5ea4315725c43346e55a6a6fbd94098` | GMP gateway. **This literal is the Ethereum gateway ONLY.** |
| **AxelarGasService** (proxy) | `0x2d5d7d31F671F86C782533cc367F14109a082712` | `0xcb5c784dcf8ff342625dbc53b356ed0cbb0ebb9b` | Relayer gas escrow. `owner()`=`0x7216…b1af`, `gasCollector()`=`0x7ddb…efbc`. |
| **InterchainTokenService** (proxy) | `0xB5FB4BE02232B1bBA4dC8f81dc24C26980dE9e3C` | `0x1b13a9baf8d3116c56ccdf3aa9049ad532a9c03d` | ITS hub. `owner()`=`0x5f93…0c10`, `paused()`=false. |
| **InterchainTokenFactory** (proxy) | `0x83A93500d23Fbc3e82B410aD07A6a9F7A0670D66` | `0xe833e9662cb0a811aa3b1746280ab43507b61946` | Token factory over ITS. |
| TokenManager (impl) | `0x8832f0381707bb29756edecf42580800207f2a9e` | — | Clone target for per-token managers. |
| InterchainToken (impl) | `0x7f9f70da4af54671a6abac58e705b5634cac8819` | — | Clone target for interchain ERC-20s. |
| InterchainTokenDeployer | `0xb769ce7dc3d642b082a55f0c12622c6e516969a3` | — | `implementationAddress()`=`0x7f9f…8819`. |
| TokenManagerDeployer | `0xdfef5b38c1c080a4a82431b687989759cb207d24` | — | |
| TokenHandler | `0x383df8e8f96b3df53f9bdc607811c7e96239e7da` | — | ITS token mint/burn/lock router. |
| Gateway owner / governance | (see §8) | — | ITS owner `0x5f939a751eaee302c85bf8bebb83483adecc0c10` (same on all 7). |

---

## 4. Addresses — Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137)

All four core contracts are **present on every one of the seven chains** (verified `eth_getCode` non-empty on each chain's publicnode RPC, 2026-06-09). **GasService, ITS, and InterchainTokenFactory share the identical constant address AND identical implementation on all seven chains.** Only the **AxelarGateway proxy address diverges** per chain (shared impl `0x99b5fa03…`).

### Shared (identical on all 7 chains)

| Role | Address (constant) | Impl (constant on all 7) |
|------|--------------------|--------------------------|
| AxelarGasService | `0x2d5d7d31F671F86C782533cc367F14109a082712` | `0xcb5c784dcf8ff342625dbc53b356ed0cbb0ebb9b` |
| InterchainTokenService | `0xB5FB4BE02232B1bBA4dC8f81dc24C26980dE9e3C` | `0x1b13a9baf8d3116c56ccdf3aa9049ad532a9c03d` |
| InterchainTokenFactory | `0x83A93500d23Fbc3e82B410aD07A6a9F7A0670D66` | `0xe833e9662cb0a811aa3b1746280ab43507b61946` |
| TokenManager / InterchainToken impl | `0x8832…2a9e` / `0x7f9f…8819` | — |

### AxelarGateway proxy — per-chain divergent address (shared impl `0x99b5fa03…`)

| Chain | ID | Gateway proxy | `eth_getCode` |
|-------|-----|---------------|---------------|
| Ethereum | 1 | `0x4F4495243837681061C4743b74B3eEdf548D56A5` | 1205 B ✓ |
| Base | 8453 | `0xe432150cce91c13a887f7D836923d5597adD8E31` | 1264 B ✓ |
| Optimism | 10 | `0xe432150cce91c13a887f7D836923d5597adD8E31` | 1264 B ✓ |
| Arbitrum One | 42161 | `0xe432150cce91c13a887f7D836923d5597adD8E31` | 1264 B ✓ |
| Avalanche C-Chain | 43114 | `0x5029C0EFf6C34351a0CEc334542cDb22c7928f78` | 1205 B ✓ |
| BNB Smart Chain | 56 | `0x304acf330bbE08d1e512eefaa92F6a57871fD895` | 1316 B ✓ |
| Polygon PoS | 137 | `0x6f015F16De9fC8791b234eF68D486d2bF203FBA8` | 1205 B ✓ |

> Base, Optimism, and Arbitrum share the **same** gateway proxy address `0xe432…8E31` (deterministic), distinct from the Ethereum/Avalanche/BNB/Polygon gateways. `implementation()` returns `0x99b5fa03…` on all seven.

---

## 5. Counterparty chains outside the seven (findings, not omissions)

Axelar connects ~60+ chains; the GMP `destinationChain`/`sourceChain` string in every event routinely names chains **outside** the seven requested. A monitor decoding `ContractCall`/`InterchainTransfer` events will see destination strings such as:

- EVM L2s **not** in scope: `linea`, `scroll`, `blast` (81457), `mantle`, `fraxtal`, `immutable`, `celo`, `kava`, `filecoin`, `fantom`, `moonbeam` (the original Axelar EVM host), `centrifuge`, `Polygon zkEVM`.
- **Non-EVM** chains reachable via Axelar: the Cosmos ecosystem (`axelarnet`, `osmosis`, `cosmoshub`, `injective`, `secret`, `juno`, `agoric`, `kujira`, `stargaze`, `terra`, `sei`, etc.), plus **Sui**, **Stellar**, and **XRPL** (Ripple). The `osmosis` destination with an `osmo1…` bech32 address was observed live in the gas-service logs sampled for this doc.

These are recorded findings: the gateway/ITS contracts on the seven target chains are the **EVM endpoints**; the canonical hub for routing/consensus is the **Axelar Cosmos-SDK chain (`axelarnet`)**, which is not an EVM contract and is out of scope for `eth_getCode`.

---

## 6. Cross-chain summary

| Chain | ID | Gateway | GasService | ITS | Factory |
|-------|-----|---------|------------|-----|---------|
| Ethereum | 1 | `0x4F44…56A5` ✓ | `0x2d5d…2712` ✓ | `0xB5FB…9e3C` ✓ | `0x83A9…0D66` ✓ |
| Base | 8453 | `0xe432…8E31` ✓ | `0x2d5d…2712` ✓ | `0xB5FB…9e3C` ✓ | `0x83A9…0D66` ✓ |
| BNB | 56 | `0x304a…D895` ✓ | `0x2d5d…2712` ✓ | `0xB5FB…9e3C` ✓ | `0x83A9…0D66` ✓ |
| Avalanche | 43114 | `0x5029…8f78` ✓ | `0x2d5d…2712` ✓ | `0xB5FB…9e3C` ✓ | `0x83A9…0D66` ✓ |
| Arbitrum | 42161 | `0xe432…8E31` ✓ | `0x2d5d…2712` ✓ | `0xB5FB…9e3C` ✓ | `0x83A9…0D66` ✓ |
| Optimism | 10 | `0xe432…8E31` ✓ | `0x2d5d…2712` ✓ | `0xB5FB…9e3C` ✓ | `0x83A9…0D66` ✓ |
| Polygon | 137 | `0x6f01…FBA8` ✓ | `0x2d5d…2712` ✓ | `0xB5FB…9e3C` ✓ | `0x83A9…0D66` ✓ |

**Vanity / decoy tells:**
- GasService `0x2d5d…2712`, ITS `0xB5FB…9e3C`, Factory `0x83A9…0D66` are **identical on all 7** (CREATE3 constant-address). Key on the address alone is safe for these three, but **always key gateways on `(chainId, address)`**.
- **DECOY:** the Ethereum gateway literal `0x4F4495243837681061C4743b74B3eEdf548D56A5` is occupied by an **unrelated contract** on BNB (23,932 B) and Arbitrum (3,874 B) — different bytecode, `implementation()` returns 0 / reverts, no Axelar interface. Do **not** treat that address as the gateway anywhere except Ethereum.

---

## 7. Decimals & encoding notes

- `ContractCallWithToken`/`TokenSent` `amount` and ITS `InterchainTransfer` `amount` are in the **token's own decimals** (no normalization in the event). Resolve decimals from the token / TokenManager.
- `destinationAddress`/`sourceAddress` in ITS events is **`bytes`**, not `address` — non-EVM destinations (Cosmos/Sui/XRPL) carry non-20-byte values. Gateway `destinationContractAddress` is a **`string`** (hex string for EVM, bech32/etc. for non-EVM).
- `commandId` / `payloadHash` / `dataHash` are `bytes32` keccak digests; `payloadHash = keccak256(payload)`.
- `tokenManagerType` is `uint8` in `TokenManagerDeployed` (0–4, §2.5) — earlier ITS used `uint256`; using the wrong width yields a different topic0.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **AxelarGateway** | **Custom `AxelarGatewayProxy`** (EternalStorage-style). **The standard EIP-1967 impl slot `0x3608…2bbc` is EMPTY** (returns `0x000…0` — verified on Ethereum); the impl is exposed only via the `implementation()` getter (`0x5c60da1b`). | `eth_getStorageAt(slot 0x3608…2bbc)` = `0x0`; `eth_call implementation()` = `0x99b5fa03…`; admin slot `0xb531…6103` also empty. | `upgrade(address,bytes32,bytes)` (`0xa3499c73`), governance multisig. |
| **AxelarGasService** | **EIP-1967** proxy + Ownable2Step | EIP-1967 impl slot `0x3608…2bbc` = `0xcb5c784dcf8ff342625dbc53b356ed0cbb0ebb9b` (verified live); admin slot empty. | `owner()` = `0x72164d4448fe6cfa472946fedc71e83b4628b1af`; `upgrade()`. |
| **InterchainTokenService** | **EIP-1967** proxy + Ownable2Step + Pausable | EIP-1967 impl slot = `0x1b13a9baf8d3116c56ccdf3aa9049ad532a9c03d` (live); admin slot empty. | `owner()` = `0x5f939a751eaee302c85bf8bebb83483adecc0c10` (same all 7 chains). |
| **InterchainTokenFactory** | **EIP-1967** proxy | EIP-1967 impl slot = `0xe833e9662cb0a811aa3b1746280ab43507b61946` (live). | ITS owner. |
| **TokenManager / InterchainToken** | **Minimal-proxy clones** of the ITS impls (`0x8832…2a9e` / `0x7f9f…8819`) | Deployed per `tokenId`; address derivable via `tokenManagerAddress(tokenId)` / `interchainTokenAddress(tokenId)`. | ITS / token operator roles. |
| Deployers / TokenHandler | **Plain (no proxy)** | EIP-1967 impl slot empty; fixed bytecode. | n/a. |

**EIP-1967 slots** (read with `eth_getStorageAt`): impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. **Watch `Upgraded(address)` topic0 `0xbc7cd75a…2d3b`** on the GasService/ITS/Factory proxies (and on each gateway) to catch impl rotations. The gateway impl is shared across all seven chains, so a single `Upgraded` on the gateway impl effectively rotates the whole fleet.

---

## 9. Detection invariants & gotchas

1. **A message has two on-chain halves on two chains.** Source: `ContractCall` (gateway) + a `NativeGasPaidForContractCall` (gas service), keyed by the same `payloadHash`. Destination: `ContractCallApproved` then `ContractCallExecuted` (gateway), keyed by `commandId`. There is **no single tx** that contains both halves — never expect to see the full lifecycle on one chain.
2. **`commandId` (destination) ≠ `payloadHash` (source).** `commandId` is assigned by the validator set in the `execute` batch; the link back to the source is the `sourceTxHash`/`sourceEventIndex` fields inside `ContractCallApproved`. Join source↔destination on `(payloadHash, sourceChain, sourceAddress, destinationContractAddress)`, not on `commandId`.
3. **The gateway address is per-chain.** GasService/ITS/Factory are constant across all 7, but the **gateway is not** (§4/§6). Key gateway filters on `(chainId, address)`. **`0x4F44…56A5` is a non-Axelar decoy on BNB and Arbitrum.**
4. **The gateway's EIP-1967 slot is empty — read `implementation()`.** A storage read of slot `0x3608…2bbc` returns `0x0` on every gateway; only the `implementation()` getter returns the live impl `0x99b5fa03…`. (GasService/ITS/Factory *do* use the standard slot.)
5. **`sender`/`sourceAddress` is the calling contract, not the EOA.** For GMP, `ContractCall.sender` is the app contract that called `callContract` (often an ITS or a third-party integrator), and `ContractCallApproved.contractAddress` is the destination handler. The end-user is encoded inside `payload` — not in indexed topics.
6. **`destinationAddress` is `bytes`/`string`, not `address`.** Non-EVM destinations (Cosmos `osmo1…`, Sui, XRPL) appear as bech32/hex strings; don't assume 20 bytes.
7. **ITS `InterchainTransfer` (outbound) and `InterchainTransferReceived` (inbound) have an extra trailing `bytes32`** (`dataHash`) vs older ITS, and inbound carries a leading `commandId`. Inbound `TokenManagerType` is `uint8`. Using the legacy signatures yields the wrong topic0 (§1.3 vs older `0x3ec7433a…`/`0xdb5bd630…`).
8. **ITS pausing uses OpenZeppelin `Paused(address)`/`Unpaused(address)` (`0x62e78cea…`/`0x5db9ee0a…`), NOT a custom `PausedSet`.** `paused()` was false at audit time; a `Paused` event is a halt of all ITS transfers — a high-value alert.
9. **GasService token-gas events exist in the ABI but are not emitted on this deployment.** Only the **native-gas** events (`NativeGasPaidForContractCall`/`…WithToken`/express + `NativeGasAdded` + `Refunded`) fire live; the impl removed the ERC-20 gas-pay functions. Don't alert on missing `GasPaidForContractCall` (`0xe99c92ee…`) as a "gap."
10. **`NativeGasAdded`/`Refunded` are keyed by `(txHash, logIndex)` of the source message,** not by `payloadHash`. To correlate a refund to a message you need the source-tx coordinates, which differ from the GMP join key in (2).
11. **TokenManager/InterchainToken are clones, one per `tokenId`** — there is no global registry event listing them. Derive addresses with `ITS.tokenManagerAddress(tokenId)` / `interchainTokenAddress(tokenId)`, or index `TokenManagerDeployed`/`InterchainTokenDeployed`. Their `FlowLimitSet`/`Transfer`/`Mint` events fire on the **clone address**, not on ITS.
12. **`Transfer` and `Approval` topic0s are generic ERC-20** — only meaningful when filtered to a known InterchainToken clone address.
13. **Express execution is a separate flow.** `expressExecute` lets a liquidity provider front the funds before consensus; watch `ExpressExecuted`/`ExpressExecutionFulfilled` — the user receives funds at express time, but the gateway `ContractCallApproved` lands later. Attributing the "real" settlement to the gateway approval will miss express fills.
14. **No Amplifier gateway on any of the seven.** They run the consensus gateway (§1.1). The `MessageApproved`/`MessageExecuted` topics (§1.6) will not appear on these chains; don't scan for them here.
15. **Same `Upgraded` impl across chains.** Because the gateway/GasService/ITS/Factory impls are byte-identical and shared across all 7, an upgrade is typically rolled out as separate `Upgraded` events per chain pointing at the same new impl address — correlate by impl address, not by chain.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- AxelarGateway
TOPIC_CONTRACT_CALL                 = '\x30ae6cc78c27e651745bf2ad08a11de83910ac1e347a52f7ac898c0fbef94dae'
TOPIC_CONTRACT_CALL_WITH_TOKEN      = '\x7e50569d26be643bda7757722291ec66b1be66d8283474ae3fab5a98f878a7a2'
TOPIC_TOKEN_SENT                    = '\x651d93f66c4329630e8d0f62488eff599e3be484da587335e8dc0fcf46062726'
TOPIC_CONTRACT_CALL_APPROVED        = '\x44e4f8f6bd682c5a3aeba93601ab07cb4d1f21b2aab1ae4880d9577919309aa4'
TOPIC_CONTRACT_CALL_APPROVED_MINT   = '\x9991faa1f435675159ffae64b66d7ecfdb55c29755869a18db8497b4392347e0'
TOPIC_CONTRACT_CALL_EXECUTED        = '\x91057b069763121972ce22b18b2f319b1520dd4c72f1f94a6395e81ceaf63f41'
TOPIC_EXECUTED                      = '\xa74c8847d513feba22a0f0cb38d53081abf97562cdb293926ba243689e7c41ca'
TOPIC_TOKEN_DEPLOYED                = '\xbf90b5a1ec9763e8bf4b9245cef0c28db92bab309fc2c5177f17814f38246938'
TOPIC_OPERATORSHIP_TRANSFERRED      = '\x192e759e55f359cd9832b5c0c6e38e4b6df5c5ca33f3bd5c90738e865a521872'
-- AxelarGasService (native-gas; live)
TOPIC_NATIVE_GAS_PAID_CALL          = '\x617332c1832058df6ee45fcbdf471251474c9945a8e5d229287a21a5f67ccf0a'
TOPIC_NATIVE_GAS_PAID_CALL_TOKEN    = '\x999d431b58761213cf53af96262b67a069cbd963499fd8effd1e21556217b841'
TOPIC_NATIVE_GAS_PAID_EXPRESS_TOKEN = '\x8c092067e86e85e8cfbaf187202ef580cdfd7ec37fbec89191607de73ca80005'
TOPIC_NATIVE_GAS_PAID_EXPRESS_CALL  = '\x5cf48f121a0fecaa2c4a64b3eaf482c8c308d5387e161535970f3e9e4363eff6'
TOPIC_NATIVE_GAS_ADDED              = '\xfeb6b00343feee0f29a1a4345f8bf93ca1c73ee922248a4237a4e50d6447604e'
TOPIC_NATIVE_EXPRESS_GAS_ADDED      = '\xb26db521e067acd5c6e345ad92fa1ed06bc7fb2aedd68f35dc7a2e10d636fc98'
TOPIC_GAS_REFUNDED                  = '\xd5df103822011013c8c940930e5180419111c65abadd6525ca7e740d56b4703f'
TOPIC_GAS_PAID_CALL_ERC20           = '\xe99c92ee8ad7ab7a540ba6a6c24c50519b613b5c4b073ff89d38a1f708a6a744'
-- InterchainTokenService
TOPIC_INTERCHAIN_TRANSFER           = '\xcd05f5b9dc4bb03babf40f5da98f5f46819846207d916f89b67d36fd1f7fd74f'
TOPIC_INTERCHAIN_TRANSFER_RECEIVED  = '\xbdb65cfd017af0876344138f62bc895163b5fd120cbe6e666ed306afd658de4b'
TOPIC_TOKEN_MANAGER_DEPLOYED        = '\x5284c2478b9c1a55e973429331078be39b5fb3eeb9d87d10b34d65a4c89ee4eb'
TOPIC_INTERCHAIN_TOKEN_DEPLOYED     = '\xf0d7beb2b03d35e597f432391dc2a6f6eb1a621be6cb5b325f55a49090085239'
TOPIC_IT_DEPLOYMENT_STARTED         = '\xe470f4bdd33c8676127d3c20ff725d8dc1605609001389ce3a59c28b54b7992f'
TOPIC_LINK_TOKEN_STARTED            = '\x6d8eb6e760238fe99c48de1a8bec4365cbeead2dbe47669c989722eaaa64a847'
TOPIC_TRUSTED_ADDRESS_SET           = '\xdb6b260ea45f7fe513e1d3b8c21017a29e3a41610e95aefb8862b81c69aec61c'
TOPIC_TRUSTED_ADDRESS_REMOVED       = '\xf9400637a329865492b8d0d4dba4eafc7e8d5d0fae5e27b56766816d2ae1b2ca'
TOPIC_EXPRESS_EXECUTED              = '\x6e18757e81c44a367109cbaa499add16f2ae7168aab9715c3cdc36b0f7ccce92'
TOPIC_EXPRESS_EXEC_FULFILLED        = '\x8fe61b2d4701a29265508750790e322b2c214399abdf98472158b8908b660d41'
TOPIC_IT_ID_CLAIMED                 = '\x04ddbfaa222e81ab9447c070310e87608bf6a4c5d42be5c2fdf0f370b186af79'
TOPIC_ITS_PAUSED                    = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_ITS_UNPAUSED                  = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
-- TokenManager
TOPIC_FLOW_LIMIT_SET                = '\x024e856c5f6f5e287ff2be13db089b016f28a6ebe6aaffdfb5fa5b902fdd366b'
-- shared
TOPIC_UPGRADED                      = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFERRED         = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_ROLES_ADDED                   = '\xf77b8a946fdd43f9bcc59a65414e31d8ce6bff4d577ba280b22a4e0076f1fbae'
TOPIC_ROLES_REMOVED                 = '\xb505728de48a106a73e5121ceb7de508f9038d2e7cb59049084f92b7b4060bc4'
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
-- AxelarGateway
SEL_CALL_CONTRACT                   = '\x1c92115f'
SEL_CALL_CONTRACT_WITH_TOKEN        = '\xb5417084'
SEL_SEND_TOKEN                      = '\x26ef699d'
SEL_GW_EXECUTE                      = '\x09c5eabe'
SEL_VALIDATE_CONTRACT_CALL          = '\x5f6970c3'
SEL_VALIDATE_CALL_AND_MINT          = '\x1876eed9'
SEL_IS_CONTRACT_CALL_APPROVED       = '\xf6a5f9f5'
SEL_IS_COMMAND_EXECUTED             = '\xd26ff210'
SEL_GW_IMPLEMENTATION               = '\x5c60da1b'
SEL_GW_UPGRADE                      = '\xa3499c73'
-- AxelarGasService
SEL_PAY_NATIVE_GAS_CALL             = '\x0c93e3bb'
SEL_PAY_NATIVE_GAS_CALL_TOKEN       = '\xc62c2002'
SEL_PAY_GAS                         = '\xedf936f2'
SEL_ADD_NATIVE_GAS                  = '\xcd433ada'
SEL_GAS_REFUND                      = '\x36504721'
SEL_GAS_COLLECT_FEES                = '\x1055eaaf'
SEL_GAS_ESTIMATE_FEE                = '\x135eaa70'
-- InterchainTokenService
SEL_INTERCHAIN_TRANSFER             = '\xda081c73'
SEL_DEPLOY_INTERCHAIN_TOKEN_ITS     = '\xe1d40c77'
SEL_LINK_TOKEN                      = '\x0f4433d3'
SEL_REGISTER_CUSTOM_TOKEN_ITS       = '\xf49c044a'
SEL_REGISTER_TOKEN_METADATA         = '\x7fb53dc9'
SEL_ITS_EXECUTE                     = '\x49160658'
SEL_ITS_EXPRESS_EXECUTE             = '\x65657636'
SEL_ITS_SET_FLOW_LIMITS             = '\x465a09e0'
SEL_ITS_SET_PAUSE_STATUS            = '\xc38bb537'
SEL_ITS_TOKEN_MANAGER_ADDRESS       = '\xf8c8a826'
SEL_ITS_INTERCHAIN_TOKEN_ADDRESS    = '\xe82e71f8'
SEL_ITS_INTERCHAIN_TOKEN_ID         = '\xa5269ef1'
-- InterchainTokenFactory
SEL_FACTORY_DEPLOY_IT               = '\x3e12f8c5'
SEL_FACTORY_REGISTER_CANONICAL      = '\xa75483d1'
SEL_FACTORY_REGISTER_CUSTOM_TOKEN   = '\xd8c03268'
SEL_FACTORY_DEPLOY_REMOTE_CANONICAL = '\xa37fcf4e'
-- TokenManager / InterchainToken
SEL_TM_MINT_TOKEN                   = '\x6bec32da'
SEL_TM_BURN_TOKEN                   = '\x3416794d'
SEL_TM_SET_FLOW_LIMIT               = '\xa56dbe63'
SEL_IT_MINT                         = '\x40c10f19'
SEL_IT_BURN                         = '\x9dc29fac'
SEL_IT_INTERCHAIN_TRANSFER          = '\xbc0ba3c5'

-- ===== Proxy slots (shared) =====
EIP1967_IMPL_SLOT                   = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                  = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — constant on ALL 7 chains =====
GASSERVICE                          = '\x2d5d7d31f671f86c782533cc367f14109a082712'
GASSERVICE_IMPL                     = '\xcb5c784dcf8ff342625dbc53b356ed0cbb0ebb9b'
ITS                                 = '\xb5fb4be02232b1bba4dc8f81dc24c26980de9e3c'
ITS_IMPL                            = '\x1b13a9baf8d3116c56ccdf3aa9049ad532a9c03d'
FACTORY                             = '\x83a93500d23fbc3e82b410ad07a6a9f7a0670d66'
FACTORY_IMPL                        = '\xe833e9662cb0a811aa3b1746280ab43507b61946'
TOKEN_MANAGER_IMPL                  = '\x8832f0381707bb29756edecf42580800207f2a9e'
INTERCHAIN_TOKEN_IMPL               = '\x7f9f70da4af54671a6abac58e705b5634cac8819'
ITS_OWNER                           = '\x5f939a751eaee302c85bf8bebb83483adecc0c10'
GASSERVICE_OWNER                    = '\x72164d4448fe6cfa472946fedc71e83b4628b1af'
GASSERVICE_COLLECTOR                = '\x7ddb2d76b80b0aa19bdea48eb1301182f4ceefbc'

-- ===== AxelarGateway — per-chain proxy (shared impl 0x99b5fa03…) =====
GW_IMPL_ALL_CHAINS                  = '\x99b5fa03a5ea4315725c43346e55a6a6fbd94098'
ETH_GATEWAY                         = '\x4f4495243837681061c4743b74b3eedf548d56a5'
BASE_GATEWAY                        = '\xe432150cce91c13a887f7d836923d5597add8e31'
OP_GATEWAY                          = '\xe432150cce91c13a887f7d836923d5597add8e31'
ARB_GATEWAY                         = '\xe432150cce91c13a887f7d836923d5597add8e31'
AVAX_GATEWAY                        = '\x5029c0eff6c34351a0cec334542cdb22c7928f78'
BNB_GATEWAY                         = '\x304acf330bbe08d1e512eefaa92f6a57871fd895'
POLY_GATEWAY                        = '\x6f015f16de9fc8791b234ef68d486d2bf203fba8'
-- NOTE: 0x4f4495…56a5 is a NON-Axelar decoy on BNB and Arbitrum — Ethereum gateway only.
```

---

## 11. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome). Cross-checked two ways: (a) live `eth_getLogs` on the Ethereum gateway (`ContractCall`/`ContractCallWithToken`/`ContractCallApproved`/`ContractCallApprovedWithMint`/`Executed`/`ContractCallExecuted` all observed in a ~2k-block window), the GasService (`NativeGasPaidForContractCall`/`…WithToken`/express + `NativeGasAdded` + `Refunded` observed; log structure decoded slot-by-slot to fix the exact param order of the `…WithToken` and `NativeGasAdded` signatures), and the ITS (`InterchainTransfer`/`InterchainTransferReceived`/`InterchainTokenDeployed`/`TokenManagerDeployed` observed); and (b) a `PUSH32`/`PUSH4` constant scan of each deployed implementation's bytecode to confirm presence/absence (which is how the legacy ERC-20 gas-pay functions and the older ITS `deployTokenManager`/`callContractWithInterchainToken` selectors were confirmed **absent**).
- **Addresses:** the four core proxies existence-checked via `eth_getCode` (non-empty) on every one of the seven chains' publicnode RPCs. Per-chain gateway proxy addresses confirmed and their `implementation()` getter read live (all return the shared `0x99b5fa03…`). Constant-address claim for GasService/ITS/Factory verified by reading identical impl addresses on all seven chains and identical `owner()` (ITS `0x5f93…0c10`). Wiring cross-checked live: `ITS.gateway()/gasService()/interchainTokenFactory()`, `Factory.interchainTokenService()`, `ITS.tokenManagerImplementation(0)`, `InterchainTokenDeployer.implementationAddress()`.
- **Proxy classification:** EIP-1967 impl slot `0x3608…2bbc` read via `eth_getStorageAt` on each proxy — populated for GasService/ITS/Factory (impl matches the `implementation()` getter), **empty** for the gateway (custom `AxelarGatewayProxy` — impl exposed only by the getter) and for the deployers/handlers (not proxies). Admin slot `0xb531…6103` empty on all (Ownable-governed, not transparent-admin).
- **Decoy finding:** `eth_getCode` at the Ethereum gateway literal `0x4F44…56A5` on BNB returns a 23,932-byte non-Axelar contract (impl getter returns 0) and on Arbitrum a 3,874-byte contract (impl getter reverts); recorded as a look-alike, not the gateway.

Authoritative sources:
- Canonical repos: [`axelarnetwork/axelar-cgp-solidity`](https://github.com/axelarnetwork/axelar-cgp-solidity) (gateway + gas service), [`axelarnetwork/interchain-token-service`](https://github.com/axelarnetwork/interchain-token-service) (ITS + factory + token manager), [`axelarnetwork/axelar-gmp-sdk-solidity`](https://github.com/axelarnetwork/axelar-gmp-sdk-solidity) (proxy/base contracts).
- Official docs & registry: [Axelar docs — contract addresses](https://docs.axelar.dev/resources/contract-addresses/mainnet), [Axelar developer docs](https://docs.axelar.dev/).
- Explorers: [Axelarscan](https://axelarscan.io/) · [Etherscan](https://etherscan.io/address/0x4F4495243837681061C4743b74B3eEdf548D56A5) · [Basescan](https://basescan.org/address/0xe432150cce91c13a887f7D836923d5597adD8E31) · [BscScan](https://bscscan.com/address/0x304acf330bbE08d1e512eefaa92F6a57871fD895) · [Snowscan](https://snowscan.xyz/address/0x5029C0EFf6C34351a0CEc334542cDb22c7928f78) · [Arbiscan](https://arbiscan.io/address/0xe432150cce91c13a887f7D836923d5597adD8E31) · [Optimistic Etherscan](https://optimistic.etherscan.io/address/0xe432150cce91c13a887f7D836923d5597adD8E31) · [Polygonscan](https://polygonscan.com/address/0x6f015F16De9fC8791b234eF68D486d2bF203FBA8).

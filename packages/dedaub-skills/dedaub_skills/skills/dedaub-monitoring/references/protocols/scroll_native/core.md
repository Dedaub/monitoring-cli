# Scroll native bridge (L1ScrollMessenger + gateways) — Topics, Selectors, Addresses (Ethereum L1 ↔ Scroll; none of the seven other chains)

**Status:** verified on 2026-09-29 and 2026-10-01 against live Ethereum RPC (code, EIP-1967 slots, router and gateway views, pinned-window log counts, sample receipts), the canonical `scroll-tech/scroll-contracts` sources, the Scroll docs contract page, L2BEAT's verified-ABI discovery data, and `eth_getCode` on all eight target chains.
**Scope:** the Scroll canonical bridge on Ethereum: **L1ScrollMessenger** (messages and ETH escrow), **L1GatewayRouter**, every L1 gateway (ETH, StandardERC20, CustomERC20, WETH, USDC, EURC, DAI, Lido wstETH, pufETH, ERC721, ERC1155, batch bridge), **ScrollChain** (rollup), the **L1 message queues** (V2 current, V1 retired), **EnforcedTxGateway**, **SystemConfig**, **PauseController** and the owner/proxy-admin stack. Topics and selectors are chain-agnostic; addresses are network-specific. Scroll (chain id 534352) is not one of the eight targets. **Of the eight target chains, only Ethereum carries Scroll bridge contracts** (§4).

Every Scroll bridge transfer is a message of the L1ScrollMessenger. A deposit enters through the router or a gateway; the gateway takes the funds (ETH is forwarded to the messenger, ERC-20s stay in the gateway as escrow) and calls `sendMessage`, which appends the message to the L1 message queue. A withdrawal is relayed on L1 with `relayMessageWithProof` against a finalized batch of ScrollChain; the messenger calls the gateway's `finalizeWithdraw*`, which pays the recipient.

Three facts to know before indexing:

1. **The messenger is the ETH escrow; each token gateway is its own token escrow.** The router holds nothing and emits no deposit events. ETH deposits and withdrawals move between the user, the ETH gateway and the messenger as internal value transfers.
2. **The link key is the message hash, and on L1 you must compute it for deposits.** `messageHash = keccak256(abi.encodeWithSignature("relayMessage(address,address,uint256,uint256,bytes)", sender, target, value, messageNonce, message))`. L1 `SentMessage` gives every input (and `messageNonce` = `QueueTransaction.queueIndex`); L2 `RelayedMessage(messageHash)` closes it. For a withdrawal, L1 `RelayedMessage(messageHash)` closes an L2 `SentMessage`.
3. **Many withdrawals show only `RelayedMessage` on L1.** `RelayedMessage` has no amount. An ETH withdrawal relayed through the ETH gateway adds `FinalizeWithdrawETH`; a plain messenger message with value (no gateway) shows only `RelayedMessage` and an internal transfer from the messenger.

---

## 0. Contract families, flow and ids

### 0.1 Contract families

| Contract | Role | Proxy |
|---|---|---|
| **L1ScrollMessenger** | `sendMessage`, `relayMessageWithProof`, `replayMessage`; ETH escrow; forwards the L2 fee to the fee vault. | EIP-1967 transparent |
| **L1GatewayRouter** | Entry point: `depositETH`, `depositERC20`, routing per token (`getERC20Gateway`). Holds nothing. | EIP-1967 transparent |
| **L1ETHGateway** | ETH deposits and withdrawals (`DepositETH`, `FinalizeWithdrawETH`). | EIP-1967 transparent |
| **L1StandardERC20Gateway** | Default ERC-20 gateway (any token without a custom route); escrow. | EIP-1967 transparent |
| **L1CustomERC20Gateway**, **L1WETHGateway**, **L1USDCGateway**, EURC gateway (USDC-gateway code), **L1DAIGateway**, **L1LidoGateway** (wstETH), pufETH gateway | Token-specific gateways and escrows. | EIP-1967 transparent |
| **L1ERC721Gateway**, **L1ERC1155Gateway** | NFT gateways and escrows. | EIP-1967 transparent |
| **L1BatchBridgeGateway** | Batches many small deposits into one message. Not on the docs page; wired to the messenger and router (read live). | EIP-1967 transparent |
| **L1MessageQueueV2** (current), **L1MessageQueueV1** (retired) | Queue of L1→L2 messages (`QueueTransaction`). | EIP-1967 transparent |
| **ScrollChain** | Batch commit and finalization (`CommitBatch`, `FinalizeBatch`); the withdraw roots that `relayMessageWithProof` checks. | EIP-1967 transparent |
| **EnforcedTxGateway** | Forced L1→L2 transactions with the real sender. | EIP-1967 transparent |
| **SystemConfig**, **PauseController**, L2GasPriceOracle (old) | Parameters, pausing, fee oracle. | EIP-1967 transparent |
| **ScrollOwner** + **ProxyAdmin** | Owner of almost every contract; role-gated executor behind timelocks. | immutable |

### 0.2 The flow

| Leg | Contract and call | Events (same transaction) | Value movement |
|---|---|---|---|
| **ETH deposit (source)** | router `depositETH(uint256 _amount, uint256 _gasLimit)` (or the ETH gateway directly) | fee vault `SafeReceived`; queue `QueueTransaction`; messenger `SentMessage` (`sender` = ETH gateway, `target` = L2 ETH gateway); ETH gateway `DepositETH` | `msg.value = amount + L2 fee`; the fee goes to the fee vault, the amount stays in the messenger |
| **ERC-20 deposit (source)** | router `depositERC20(address _token, uint256 _amount, uint256 _gasLimit)` (or the gateway) | ERC-20 `Transfer(user → gateway)` (L1-native) or burn (L2-native); `QueueTransaction`; `SentMessage`; gateway `DepositERC20` | token to the gateway escrow; `msg.value` = L2 fee |
| **Plain message (source)** | messenger `sendMessage(address _to, uint256 _value, bytes _message, uint256 _gasLimit)` | `QueueTransaction`, `SentMessage` | `_value` to the messenger |
| **Batch finalization (status)** | ScrollChain `commitBatches` / `finalizeBundlePostEuclidV2` | `CommitBatch`, `FinalizeBatch` (withdraw root) | none |
| **Withdrawal (destination)** | messenger `relayMessageWithProof(...)` (anyone) | ETH: `FinalizeWithdrawETH` + `RelayedMessage`; ERC-20: `Transfer(gateway → recipient)` + `FinalizeWithdrawERC20` + `RelayedMessage` | ETH from the messenger (internal); token from the gateway |
| **Failed relay (status)** | `relayMessageWithProof` whose target call reverts | `FailedRelayedMessage` | none; retry later |
| **Replay / refund** | messenger `replayMessage(...)` re-queues a deposit with a new gas limit; a dropped message calls the gateway's `onDropMessage`, which refunds | `QueueTransaction`, `SentMessage`; `RefundETH` / `RefundERC20` | refund to the original sender |

The current messenger implementation exposes no `dropMessage`; `RefundETH` and `RefundERC20` had 0 logs in the pinned window (refunds were a pre-V2-queue path).

### 0.3 Ids

| Id | Value |
|---|---|
| Scroll chain id | 534352 (read live with `eth_chainId` on the Scroll RPC) |
| L1→L2 sender alias | `QueueTransaction.sender` = L1 sender + `0x1111000000000000000000000000000000001111` (the messenger `0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367` appears as `0x7885BcBd5CeCEf1336b5300fb5186A12DDD8c478`) |
| L2 counterparts (on Scroll) | L2ScrollMessenger `0x781e90f1c8Fc4611c9b7497C3B47F99Ef6969CbC`, L2GatewayRouter `0x4C0926FF5252A435FD19e10ED15e5a249Ba19d79`, L2ETHGateway `0x6EA73e05AdC79974B931123675ea8F78FfdacDF0` (docs) |
| Link key | message hash (computed, see above); `messageNonce` = `queueIndex` |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 L1ScrollMessenger (emitter `0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367`)

| topic0 | Event | Notes |
|---|---|---|
| `0x104371f3b442861a2a7b82a070afbbaab748bb13757bf47769e170e37809ec1e` | `SentMessage(address indexed sender, address indexed target, uint256 value, uint256 messageNonce, uint256 gasLimit, bytes message)` | **Source leg** of every deposit and message. `value > 0` = ETH. |
| `0x4641df4a962071e12719d8c8c8e5ac7fc4d97b927346a3d7a335b1f7517e133c` | `RelayedMessage(bytes32 indexed messageHash)` | **Destination leg** of every withdrawal. Same topic0 as the OP Stack messengers. |
| `0x99d0e048484baa1b1540b1367cb128acd7ab2946d1ed91ec10e3c85e4bf51b8f` | `FailedRelayedMessage(bytes32 indexed messageHash)` | Status only. |
| `0x4aadc32827849f797733838c61302f7f56d2b6db28caa175eb3f7f8e5aba25f5` | `UpdateFeeVault(address _oldFeeVault, address _newFeeVault)` | Admin (messenger and EnforcedTxGateway). |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | OpenZeppelin pause (messenger, ScrollChain, EnforcedTxGateway). |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |

### 1.2 Gateways and router — value events

The router's ABI lists the same events, but the router does not emit them: filter on the gateway addresses.

| topic0 | Event | Side |
|---|---|---|
| `0x6670de856ec8bf5cb2b7e957c5dc24759716056f79d97ea5e7c939ca0ba5a675` | `DepositETH(address indexed from, address indexed to, uint256 amount, bytes data)` | **Source** (ETH gateway) |
| `0x96db5d1cee1dd2760826bb56fabd9c9f6e978083e0a8b88559c741a29e9746e7` | `FinalizeWithdrawETH(address indexed from, address indexed to, uint256 amount, bytes data)` | **Destination** (ETH gateway) |
| `0x289360176646a5f99cb4b6300628426dca46b723f40db3c04449d6ed1745a0e7` | `RefundETH(address indexed recipient, uint256 amount)` | Refund |
| `0x31cd3b976e4d654022bf95c68a2ce53f1d5d94afabe0454d2832208eeb40af25` | `DepositERC20(address indexed l1Token, address indexed l2Token, address indexed from, address to, uint256 amount, bytes data)` | **Source** (every ERC-20 gateway) |
| `0xc6f985873b37805705f6bce756dce3d1ff4b603e298d506288cce499926846a7` | `FinalizeWithdrawERC20(address indexed l1Token, address indexed l2Token, address indexed from, address to, uint256 amount, bytes data)` | **Destination** (every ERC-20 gateway) |
| `0xdbdf8eb487847e4c0f22847f5dac07f2d3690f96f581a6ae4b102769917645a8` | `RefundERC20(address indexed token, address indexed recipient, uint256 amount)` | Refund |
| `0xfc1d17c06ff1e4678321cc30660a73f3f1436df8195108a288d3159a961febec` | `DepositERC721(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256 _tokenId)` | Source (ERC721 gateway) |
| `0xf05915e3b4fbd6f61b8b6f80b07f10e1cad039ccc7abe7c7fec115d038fe3dd6` | `BatchDepositERC721(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256[] _tokenIds)` | Source |
| `0xacdbfefc030b5ccccd5f60ca6d9ca371c6d6d6956fe16ebe10f81920198206e9` | `FinalizeWithdrawERC721(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256 _tokenId)` | Destination |
| `0x9b8e51c8f180115b421b26c9042287d6bf95e0ce9c0c5434784e2af3d0b9de7d` | `FinalizeBatchWithdrawERC721(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256[] _tokenIds)` | Destination |
| `0xb9a838365634e4fb87a9333edf0ea86f82836e361b311a125aefd14135581208` | `RefundERC721(address indexed token, address indexed recipient, uint256 tokenId)` | Refund |
| `0x7f6552b688fa94306ca59e44dd4454ff550542445a3f1cb39b8c768be6f5c08a` | `DepositERC1155(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256 _tokenId, uint256 _amount)` | Source (ERC1155 gateway) |
| `0x743f65db61a23bc629915d35e22af5cf13478a8b3dbd154d3e5db0149509756d` | `BatchDepositERC1155(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256[] _tokenIds, uint256[] _amounts)` | Source |
| `0xfcc2841e9e72e6d610944e1b668912e92d5df94003055dbe06d615ba8d9efad4` | `FinalizeWithdrawERC1155(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256 _tokenId, uint256 _amount)` | Destination |
| `0x45294b6ad6ad2408cc3ee9a37203aa1b0480616667a97b157c52ac9294cbc258` | `FinalizeBatchWithdrawERC1155(address indexed _l1Token, address indexed _l2Token, address indexed _from, address _to, uint256[] _tokenIds, uint256[] _amounts)` | Destination |
| `0x4e2ca0515ed1aef1395f66b5303bb5d6f1bf9d61a353fa53f73f8ac9973fa9f6` | `Deposit(address indexed sender, address indexed token, uint256 indexed batchIndex, uint256 amount, uint256 fee)` | Source (L1BatchBridgeGateway; funds wait in the gateway until the batch is sent) |
| `0x48ee408898bf1f57213c7d1169bff9cb95c054193258acf5b8913e09dac582f4` | `BatchDeposit(address indexed caller, address indexed l1Token, uint256 indexed batchIndex, address l2Token)` | Batch sent (L1BatchBridgeGateway) |

### 1.3 Gateways and router — admin

| topic0 | Event | Emitter |
|---|---|---|
| `0x0ead4808404683f66d413d788a768219ea9785c97889221193103841a5841eaf` | `SetERC20Gateway(address indexed token, address indexed oldGateway, address indexed newGateway)` | router (**reroutes a token**) |
| `0x2904fcae71038f87b116fd2875871e153722cabddd71de1b77473de263cd74d1` | `SetDefaultERC20Gateway(address indexed oldDefaultERC20Gateway, address indexed newDefaultERC20Gateway)` | router |
| `0xa1bfcc6dd729ad197a1180f44d5c12bcc630943df0874b9ed53da23165621b6a` | `SetETHGateway(address indexed oldETHGateway, address indexed newEthGateway)` | router |
| `0x2069a26c43c36ffaabe0c2d19bf65e55dd03abecdc449f5cc9663491e97f709d` | `UpdateTokenMapping(address indexed l1Token, address indexed oldL2Token, address indexed newL2Token)` | Custom, DAI, pufETH, NFT gateways |
| `0xc36a428b063177e3f28b3b5d340c08f77827847b2ee30114ccf0c40e519c420a` | `DepositsEnabled(address indexed enabler)` | Lido gateway |
| `0x9ca4d309bbfd23c65db3dc38c1712862f5812c7139937e2655de86e803f73bb9` | `DepositsDisabled(address indexed disabler)` | Lido gateway |
| `0xb2ed3603bd9051f0182ebfb75f12a21059b4d31b578a2a05c8d0245e9e2d3204` | `WithdrawalsEnabled(address indexed enabler)` | Lido gateway |
| `0x644eeba8ede48fefc32ada09fb240c5f6c0f06507ab1d296d5af41f1521d9fcb` | `WithdrawalsDisabled(address indexed disabler)` | Lido gateway |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | Lido gateway, ScrollOwner |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | Lido gateway, ScrollOwner |

### 1.4 Message queue, ScrollChain, system contracts (status and admin)

| topic0 | Event | Emitter |
|---|---|---|
| `0x69cfcb8e6d4192b8aba9902243912587f37e550d75c1fa801491fce26717f37e` | `QueueTransaction(address indexed sender, address indexed target, uint256 value, uint64 queueIndex, uint256 gasLimit, bytes data)` | L1MessageQueueV2 (and V1 before its retirement). Pair of `SentMessage` and of forced transactions. |
| `0xbbbf2de085aff601d965315326f9908eb5ebbb3d1b307e7e5ec42384e3320a10` | `FinalizedDequeuedTransaction(uint256 finalizedIndex)` | message queue |
| `0x2c32d4ae151744d0bf0b9464a3e897a1d17ed2f1af71f7c9a75f12ce0d28238f` | `CommitBatch(uint256 indexed batchIndex, bytes32 indexed batchHash)` | ScrollChain |
| `0x26ba82f907317eedc97d0cbef23de76a43dd6edb563bdb6e9407645b950a7a2d` | `FinalizeBatch(uint256 indexed batchIndex, bytes32 indexed batchHash, bytes32 stateRoot, bytes32 withdrawRoot)` | ScrollChain (withdrawals of this batch become provable) |
| `0x00cae2739091badfd91c373f0a16cede691e0cd25bb80cff77dd5caeb4710146` | `RevertBatch(uint256 indexed batchIndex, bytes32 indexed batchHash)` | ScrollChain |
| `0x9ee73ead2e4d8c2933d5fb9be41cbdf5c477dcb07e441b4b082c6797e4b6fde3` | `RevertBatch(uint256 indexed startBatchIndex, uint256 indexed finishBatchIndex)` | ScrollChain |
| `0xd6756219c796b0d9bf065e40dcf1deea84ecb37744e35eb8ad8d89994bbfd0b5` | `UpdateEnforcedBatchMode(bool enabled, uint256 lastCommittedBatchIndex)` | ScrollChain (permissionless batching switched on or off) |
| `0x631cb110fbe6a87fba5414d6b2cff02264480535cd1f5abdbc4fa638bc0b5692` | `UpdateSequencer(address indexed account, bool status)` | ScrollChain |
| `0x967f99d5d403870e4356ff46556df3a6b6ba1f50146639aaedfb9f248eb8661e` | `UpdateProver(address indexed account, bool status)` | ScrollChain |
| `0x4577e886680e7abbb7fac7edd79cfe3fa254773d223401379069312472a37da1` | `MessageQueueParametersUpdated((uint32 maxGasLimit, uint112 baseFeeOverhead, uint112 baseFeeScalar) oldParams, (uint32 maxGasLimit, uint112 baseFeeOverhead, uint112 baseFeeScalar) newParams)` | SystemConfig |
| `0xedff2866ce9f24bd41390d767cd37dcd4bfec8d41c4b329147feee06e97b64d8` | `EnforcedBatchParametersUpdated((uint24 maxDelayEnterEnforcedMode, uint24 maxDelayMessageQueue) oldParams, (uint24 maxDelayEnterEnforcedMode, uint24 maxDelayMessageQueue) newParams)` | SystemConfig |
| `0x2d025324f0a785e8c12d0a0d91a9caa49df4ef20ff87e0df7213a1d4f3157beb` | `SignerUpdated(address oldSigner, address newSigner)` | SystemConfig |
| `0x5ee71a369c8672edded508e624ffc9257fa1ae6886ef32905c18e60196bca399` | `Pause(address indexed component)` | PauseController (**pauses a bridge component**) |
| `0xaeb196d352664784d1900b0e7414a8face7d29f4dae8c4b0cf68ed477423bbf4` | `Unpause(address indexed component)` | PauseController |
| `0xab8116947fdf4ffd9379522dc6451e9c767d55db320b2f6a93017bc44d677880` | `GrantAccess(bytes32 indexed role, address indexed target, bytes4[] selectors)` | ScrollOwner |
| `0xefe7a81eac20757f542b11567aacfce76f897581ecd3ae29c0d271cd86724733` | `RevokeAccess(bytes32 indexed role, address indexed target, bytes4[] selectors)` | ScrollOwner |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every proxy of §3 |
| `0x3d0ce9bfc3ed7d6862dbb28b2dea94561fe714a1b4d019aa8af39730d1ad7c3d` | `SafeReceived(address indexed sender, uint256 value)` | fee vault (a Safe) when the messenger forwards the L2 fee |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 L1ScrollMessenger, message queue, EnforcedTxGateway

| Selector | Signature | Notes |
|---|---|---|
| `0xb2267a7b` | `sendMessage(address _to, uint256 _value, bytes _message, uint256 _gasLimit)` | payable. **Source leg** (plain message). |
| `0x5f7b1577` | `sendMessage(address _to, uint256 _value, bytes _message, uint256 _gasLimit, address _refundAddress)` | payable. |
| `0xc311b6fc` | `relayMessageWithProof(address _from, address _to, uint256 _value, uint256 _nonce, bytes _message, (uint256 batchIndex, bytes merkleProof) _proof)` | **Destination leg.** Anyone may call. |
| `0x55004105` | `replayMessage(address _from, address _to, uint256 _value, uint256 _messageNonce, bytes _message, uint32 _newGasLimit, address _refundAddress)` | payable; re-queues a deposit. |
| `0x29907acd` | `dropMessage(address _from, address _to, uint256 _value, uint256 _messageNonce, bytes _message)` | Older implementations only (absent from the current ABI). |
| `0x8ef1332e` | `relayMessage(address _from, address _to, uint256 _value, uint256 _nonce, bytes _message)` | Not called on L1; its calldata is what the message hash hashes. |
| `0xbedb86fb` | `setPause(bool _status)` | Owner. |
| `0x2a6cccb2` | `updateFeeVault(address _newFeeVault)` | Owner. |
| `0x6e296e45` | `xDomainMessageSender()` | view. |
| `0x478222c2` | `feeVault()` | view. |
| `0xcd172b23` | `messageQueueV1()` | view. |
| `0x9eee46a1` | `messageQueueV2()` | view. |
| `0x9b159782` | `appendCrossDomainMessage(address _target, uint256 _gasLimit, bytes _data)` | Queue; messenger only. |
| `0xbdc6f0a0` | `appendEnforcedTransaction(address _sender, address _target, uint256 _value, uint256 _gasLimit, bytes _data)` | Queue; EnforcedTxGateway only. |
| `0x3934ce9d` | `sendTransaction(address _target, uint256 _value, uint256 _gasLimit, bytes _data)` | EnforcedTxGateway, payable. |
| `0xfb403d7c` | `sendTransaction(address _sender, address _target, uint256 _value, uint256 _gasLimit, bytes _data, uint256 _deadline, bytes _signature, address _refundAddress)` | EnforcedTxGateway (signed). |

### 2.2 Router and gateways

| Selector | Signature | Notes |
|---|---|---|
| `0x9f8420b3` | `depositETH(uint256 _amount, uint256 _gasLimit)` | router and ETH gateway, payable. |
| `0xce0b63ce` | `depositETH(address _to, uint256 _amount, uint256 _gasLimit)` | payable. |
| `0xaac476f8` | `depositETHAndCall(address _to, uint256 _amount, bytes _data, uint256 _gasLimit)` | payable. |
| `0x21425ee0` | `depositERC20(address _token, uint256 _amount, uint256 _gasLimit)` | router and ERC-20 gateways, payable (L2 fee). |
| `0xf219fa66` | `depositERC20(address _token, address _to, uint256 _amount, uint256 _gasLimit)` | payable. |
| `0x0aea8c26` | `depositERC20AndCall(address _token, address _to, uint256 _amount, bytes _data, uint256 _gasLimit)` | payable. |
| `0x8eaac8a3` | `finalizeWithdrawETH(address _from, address _to, uint256 _amount, bytes _data)` | ETH gateway; messenger only. |
| `0x84bd13b0` | `finalizeWithdrawERC20(address _l1Token, address _l2Token, address _from, address _to, uint256 _amount, bytes _data)` | ERC-20 gateways; messenger only. |
| `0x14298c51` | `onDropMessage(bytes _message)` | Gateways; refund hook. |
| `0x0a7aa196` | `depositERC721(address _token, address _to, uint256 _tokenId, uint256 _gasLimit)` | ERC721 gateway, payable. |
| `0x1b997a93` | `batchDepositERC721(address _token, address _to, uint256[] _tokenIds, uint256 _gasLimit)` | payable. |
| `0xa901cf8a` | `depositERC1155(address _token, address _to, uint256 _tokenId, uint256 _amount, uint256 _gasLimit)` | ERC1155 gateway, payable. |
| `0xf6326fb3` | `depositETH()` | L1BatchBridgeGateway, payable. |
| `0x82f7d4ae` | `depositERC20(address token, uint96 amount)` | L1BatchBridgeGateway. |
| `0xfb3de48b` | `executeBatchDeposit(address token)` | L1BatchBridgeGateway, keeper. |
| `0x635c8637` | `setERC20Gateway(address[] _tokens, address[] _gateways)` | router owner. **High severity.** |
| `0x5dfd5b9a` | `setDefaultERC20Gateway(address _newDefaultERC20Gateway)` | router owner. |
| `0x3d1d31c7` | `setETHGateway(address _newEthGateway)` | router owner. |
| `0xfac752eb` | `updateTokenMapping(address _l1Token, address _l2Token)` | gateway owner. |
| `0x21846ebb` | `burnAllLockedUSDC()` | USDC-code gateways (Circle migration hook). |
| `0x415855d6` | `pauseDeposit(bool _paused)` | USDC-code gateways. |
| `0xebd462cb` | `pauseWithdraw(bool _paused)` | USDC-code gateways. |
| `0xac67e1af` | `disableDeposits()` | Lido gateway. |
| `0xad960ce1` | `disableWithdrawals()` | Lido gateway. |
| `0x43c66741` | `getERC20Gateway(address _token)` | router view. |
| `0xc676ad29` | `getL2ERC20Address(address _l1Address)` | router view. |
| `0xce8c3e06` | `defaultERC20Gateway()` | router view. |
| `0x8c00ce73` | `ethGateway()` | router view. |
| `0xa6f73669` | `l1USDC()` | USDC-code gateway view (returns EURC on the EURC gateway). |
| `0x02befd24` | `depositPaused()` | USDC-code gateway view. |
| `0x797594b0` | `counterpart()` | view (L2 counterpart). |

### 2.3 ScrollChain, PauseController, ScrollOwner, ProxyAdmin

| Selector | Signature | Notes |
|---|---|---|
| `0x9bbaa2ba` | `commitBatches(uint8 version, bytes32 parentBatchHash, bytes32 lastBatchHash)` | Sequencer. |
| `0xc1aa4e19` | `finalizeBundlePostEuclidV2(bytes batchHeader, uint256 totalL1MessagesPoppedOverall, bytes32 postStateRoot, bytes32 withdrawRoot, bytes aggrProof)` | Prover. |
| `0x27dcaf6f` | `commitAndFinalizeBatch(uint8 version, bytes32 parentBatchHash, (bytes batchHeader, uint256 totalL1MessagesPoppedOverall, bytes32 postStateRoot, bytes32 withdrawRoot, bytes zkProof) finalizeStruct)` | Enforced batch mode (permissionless). |
| `0x4030cf29` | `revertBatch(bytes batchHeader)` | Owner. |
| `0x8a336231` | `addSequencer(address _account)` | Owner. |
| `0x1d49e457` | `addProver(address _account)` | Owner. |
| `0x059def61` | `lastFinalizedBatchIndex()` | view. |
| `0x76a67a51` | `pause(address component)` | PauseController. |
| `0x57b001f9` | `unpause(address component)` | PauseController. |
| `0x88aa4c12` | `execute(address _target, uint256 _value, bytes _data, bytes32 _role)` | ScrollOwner (every admin action goes through it). |
| `0x2eef838c` | `updateAccess(address _target, bytes4[] _selectors, bytes32 _role, bool _status)` | ScrollOwner. |
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | ProxyAdmin. **Upgrade.** |
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | ProxyAdmin. **Upgrade.** |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All existence-checked with `eth_getCode`; implementations and admins read from the EIP-1967 slots (2026-09-29).

### 3.1 Messenger, router, rollup, queues

| Role | Address | Implementation | Notes |
|---|---|---|---|
| **L1ScrollMessenger** (ETH escrow) | `0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367` | `0x79b6eAbfFAa958FDF2Aa2Bf632878bD323DCbF69` | `feeVault()` = `0x8FA3b4570B4C96f8036C13b64971BA65867eEB48`; `paused()` = false. |
| **L1GatewayRouter** | `0xF8B1378579659D8F7EE5f3C929c2f3E332E41Fd6` | `0xb93Ac04010Bd61F45BF492022A5b49a902F798F3` | `ethGateway()` and `defaultERC20Gateway()` read live (§3.2). |
| **ScrollChain** | `0xa13BAF47339d63B743e7Da8741db5456DAc1E556` | `0x0a20703878E68E587c59204cc0EA86098B8c3bA7` | rollup. |
| **L1MessageQueueV2** | `0x56971da63A3C0205184FEF096E9ddFc7A8C2D18a` | `0x39C36c9026ac18104839A50c61a4507ea5052ECa` | current queue (`messageQueueV2()`). |
| L1MessageQueueV1 (retired) | `0x0d7E906BD9cAFa154b048cFa766Cc1E54E39AF9B` | `0x137CC585F607EDeBBc3CA6360AffCFeab507B374` | `messageQueueV1()`; 0 `QueueTransaction` in the pinned window. |
| **EnforcedTxGateway** | `0x72CAcBcfDe2d1e19122F8A36a4d6676cd39d7A5d` | `0x7e87c75BBe7991bbCEBd2C7a56f4cFC923BDDBcc` | forced transactions. |
| SystemConfig | `0x8432728A257646449245558B8b7Dbe51A16c7a4D` | `0xf15a4b6D1fE2Ca6eE38BC3fb957f43F58b515eeE` | |
| PauseController | `0xb8f7eA9998530833Cbb7E0EF4f0D945957229D8b` | `0x57e26d997852e7e94915e250446C3bf43F41d98D` | |
| L2GasPriceOracle (old) | `0x987e300fDfb06093859358522a79098848C33852` | — | pre-V2 fee oracle. |
| MultipleVersionRollupVerifier | `0x4CEA3E866e7c57fD75CB0CA3E9F5f1151D4Ead3F` | immutable | proof verifier router. |
| Fee vault (Safe) | `0x8FA3b4570B4C96f8036C13b64971BA65867eEB48` | — | receives the L2 fees (`SafeReceived`). |

### 3.2 Gateways (every gateway is its own escrow, except the ETH gateway, whose ETH sits in the messenger)

| Gateway | Address | Implementation | Token routed to it (`getERC20Gateway`, read live) |
|---|---|---|---|
| **L1ETHGateway** | `0x7F2b8C31F88B6006c382775eea88297Ec1e3E905` | `0x1fee6a6dC49095FB9C84D61aa4b8A07284b2A1d0` | ETH (`ethGateway()`) |
| **L1StandardERC20Gateway** | `0xD8A791fE2bE73eb6E6cF1eb0cb3F36adC9B3F8f9` | `0xfF8238be22cC583b3d69A76da9d84Da7788c0ee9` | default (`defaultERC20Gateway()`): USDT, WBTC, weETH, STONE and every other token without a custom route |
| **L1CustomERC20Gateway** | `0xb2b10a289A229415a124EFDeF310C10cb004B6ff` | `0x40c3C3dEa3B7D6d117E6713377144fD8EE6D6c97` | tokens with a custom L2 contract |
| **L1WETHGateway** | `0x7AC440cAe8EB6328de4fA621163a792c1EA9D4fE` | `0xE25EfFEFd08c4a57556d47eF96471Cb567A86c24` | WETH `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` (L2 WETH `0x5300000000000000000000000000000000000004`) |
| **L1USDCGateway** | `0xf1AF3b23DE0A5Ca3CAb7261cb0061C0D779A5c7B` | `0x56ce8A8E8399f6cD5e7e4f549E8BfD673f2AfF5e` | USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` (L2 `0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4`); deposits and withdrawals not paused |
| EURC gateway (USDC-gateway code) | `0xbc4b3d9A89F187dBaA0D2E60985Ea1FFFa5247d2` | `0x4a5810F71B6836027c26C25bFF9708dFcD2B5432` | EURC `0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c` (L2 `0x174d1A887e971f7d0fe5C68b328c30e0ED743160`) |
| **L1DAIGateway** | `0x67260A8B73C5B77B55c1805218A42A7A6F98F515` | `0xBAd002fB13adFfcbCba57a4d4a43886f3F4C56cb` | DAI `0x6B175474E89094C44Da98b954EedeAC495271d0F` |
| **L1LidoGateway** (wstETH) | `0x6625C6332c9F91F2D27c304E729B86db87A3f504` | `0xF4f2066EE72D62e3caF9678459149BA7FCf2262F` | wstETH `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` |
| pufETH gateway | `0xA033Ff09f2da45f0e9ae495f525363722Df42b2a` | `0x08D77Ea90DB9BF6c0d3f66E6b8394DA2E81B9a03` | pufETH `0xD9A442856C234a39a81a089C06451EBAa4306a72` |
| **L1ERC721Gateway** | `0x6260aF48e8948617b8FA17F4e5CEa2d21D21554B` | `0x79F1bF1906B63b56E08c3ada4c51De11F145a27A` | NFTs |
| **L1ERC1155Gateway** | `0xb94f7F6ABcb811c5Ac709dE14E37590fcCd975B6` | `0xcA46358D5F01E4F865885514DAe6275087Ffe38E` | NFTs |
| L1BatchBridgeGateway | `0x5Bcfd99c34cf7E06fc756f6f5aE7400504852bc4` | `0x7999cdD5E2893475D89211A2E3FdA67a841E3233` | `messenger()` = the messenger, `router()` = the router, `counterpart()` = `0xa1a12158bE6269D7580C63eC5E609Cdc0ddD82bC`, `queue()` = the V1 queue (read live); not on the docs page |

### 3.3 Governance

| Role | Address | Notes |
|---|---|---|
| ProxyAdmin | `0xEB803eb3F501998126bf37bB823646Ed3D59d072` | admin of every Scroll proxy except the Lido and pufETH gateways; `owner()` = ScrollOwner (read live). |
| ScrollOwner | `0x798576400F7D662961BA15C6b3F3d813447a26a6` | `owner()` of the messenger, router, ETH gateway, USDC and EURC gateways, queue V2, ScrollChain, EnforcedTxGateway, SystemConfig (read live). Role-gated executor; L2BEAT lists TimelockFast `0x0e58939204eEDa84F796FBc86840A50af10eC4F4` (1 day), TimelockSCSlow `0x3f9041350B661c74C6CbE440c8Bd6BC4C168a9fd` (3 days) and two 0-second emergency timelocks behind it. |
| ScrollAdminMultisig (Safe) | `0xcca54B0916Cee2186b47E9709BEdcb7041A8F761` | team operators (per L2BEAT). |
| Lido gateway admin | `0xCC2C53556Bc75217cf698721b29071d6f12628A9` (ProxyAdmin) | `owner()` = Lido Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`, which also owns the gateway (read live). |
| pufETH gateway admin | `0x9eBf2f33526CD571f8b2ad312492cb650870CFd6` (ProxyAdmin) | also the gateway's `owner()`; its `owner()` = `0xC0896ab1A8cae8c2C1d27d011eb955Cca955580d` (read live). Not Scroll-controlled. |

### 3.4 Look-alikes on Ethereum

| Contract | Address | What it is |
|---|---|---|
| Morph L1CrossDomainMessenger | `0xDc71366EFFA760804DCFC3EDF87fa2A6f1623304` | Morph (a Scroll-derived rollup) emits the same `RelayedMessage` topic0. |
| Morph L1ETHGateway | `0x1C1Ffb5828c3A48B54E8910F1c75256a498aDE68` | emits `FinalizeWithdrawETH` (29 in the pinned window). |
| Morph USDC gateway, Standard gateway, another Morph gateway | `0x2C8314f5AADa5D7a9D32eeFebFc43aCCAbe1b289`, `0x44c28f61A5C2Dd24Fc71D7Df8E85e18af4ab2Bd8`, `0x788890Ba6f105ccA373c4ff01055CD34De01877F` | emit `FinalizeWithdrawERC20`; `messenger()` = the Morph messenger (read live). |
| Unidentified `DepositETH` emitter | `0x922248Db4A99bB542539ae7165FB9D7A546FB9F1` | not routed by the Scroll router, not on the docs page; not Scroll. |
| L2 addresses that also have code on Ethereum | `0x781e90f1c8Fc4611c9b7497C3B47F99Ef6969CbC`, `0x4C0926FF5252A435FD19e10ED15e5a249Ba19d79`, `0x6EA73e05AdC79974B931123675ea8F78FfdacDF0` | the L2 messenger, router and ETH gateway addresses hold 2084-byte placeholder proxies on Ethereum; they are not the L1 bridge. |

---

## 4. Cross-chain summary

| Chain | ID | Messenger | Router | Gateways (12) | ScrollChain | Queue V2 / V1 | EnforcedTxGateway | Batch gateway |
|---|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ `0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367` | ✅ `0xF8B1378579659D8F7EE5f3C929c2f3E332E41Fd6` | ✅ §3.2 | ✅ `0xa13BAF47339d63B743e7Da8741db5456DAc1E556` | ✅ / ✅ (retired) | ✅ | ✅ |
| Base | 8453 | — | — | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — | — | — |
| BNB Smart Chain | 56 | — | — | — | — | — | — | — |
| Avalanche C-Chain | 43114 | — | — | — | — | — | — | — |
| Robinhood Chain | 4663 | — | — | — | — | — | — | — |

"—" means `eth_getCode` returned `0x` with nonce 0 at the Ethereum addresses on that chain: the messenger, router, ScrollChain, EnforcedTxGateway, batch gateway, queue V1 and V2, all gateways of §3.2, and the L2 messenger, router and ETH gateway addresses (checked 2026-09-29 to 2026-10-01). The Scroll docs list no L1 contract outside Ethereum. On Base, Optimism and BNB the `RelayedMessage` and `FailedRelayedMessage` topic0s are emitted by OP Stack messengers (for example `0x4200000000000000000000000000000000000007`) and other bridges, never by a Scroll contract.

The counterparty, Scroll (534352), is outside the eight.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority |
|---|---|---|---|
| Messenger, router, all Scroll gateways, ScrollChain, queues V1/V2, EnforcedTxGateway, SystemConfig, PauseController, batch gateway, gas oracle | EIP-1967 transparent | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` set; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = ProxyAdmin `0xEB803eb3F501998126bf37bB823646Ed3D59d072` (read live on all of them) | ProxyAdmin → ScrollOwner `0x798576400F7D662961BA15C6b3F3d813447a26a6` (role-based; the timelocks are per L2BEAT). |
| L1LidoGateway | EIP-1967 transparent | admin slot = `0xCC2C53556Bc75217cf698721b29071d6f12628A9` | Lido Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`. |
| pufETH gateway | EIP-1967 transparent | admin slot = `0x9eBf2f33526CD571f8b2ad312492cb650870CFd6` | its owner `0xC0896ab1A8cae8c2C1d27d011eb955Cca955580d`. |
| ScrollOwner, ProxyAdmin, verifiers, timelocks | immutable | no impl slot | — |

Watch `Upgraded(address)` on every proxy. Implementations of 2026-09-29 are in §3.1 and §3.2.

---

## 6. Detection invariants & gotchas

1. **Filter `RelayedMessage` on the emitter.** The topic0 `0x4641df4a962071e12719d8c8c8e5ac7fc4d97b927346a3d7a335b1f7517e133c` is shared by every OP Stack messenger and by Morph. In the pinned window, of 298 `RelayedMessage` logs on Ethereum only 157 came from the Scroll messenger; Base had 150, Optimism 112 and BNB 23, none from Scroll.
2. **Filter gateway events on the emitter.** Morph's gateways emit the same `DepositETH` / `FinalizeWithdrawETH` / `DepositERC20` / `FinalizeWithdrawERC20` topic0s (§3.4): 9 of the 17 `FinalizeWithdrawERC20` logs in the window were Morph's.
3. **ETH value lives in the messenger.** Read deposits from `DepositETH.amount` or `SentMessage.value`; read withdrawals from `FinalizeWithdrawETH.amount` or, for a gateway-less message, from the internal transfer out of `0x6774Bcbd5ceCeF1336b5300fb5186a12DDD8b367`. The guide's measurement found most ETH payouts with only `RelayedMessage`.
4. **A direct messenger deposit has no `DepositETH`.** `sendMessage` with `_value > 0` emits only `QueueTransaction` and `SentMessage`. Use `SentMessage.value > 0` to catch it.
5. **One deposit = `SentMessage` + `QueueTransaction` + a gateway event.** Count one. `QueueTransaction.sender` is aliased (+`0x1111000000000000000000000000000000001111`) and its `target` is the L2 messenger; the real sender is `DepositETH.from` / `DepositERC20.from` or `SentMessage.sender` (the gateway).
6. **`msg.value` includes the L2 fee.** The fee goes to the fee vault in the same transaction (`SafeReceived`); it is not bridged value.
7. **`relayMessageWithProof` is permissionless.** `tx.from` is often a relayer. Attribute by `FinalizeWithdraw*.to`.
8. **The router does not emit.** Its ABI lists the deposit events, but they come from the gateways.
9. **Two USDC-code gateways.** `0xf1AF3b23DE0A5Ca3CAb7261cb0061C0D779A5c7B` serves USDC; `0xbc4b3d9A89F187dBaA0D2E60985Ea1FFFa5247d2` runs the same code for EURC (`l1USDC()` returns EURC). Both expose `burnAllLockedUSDC()`, the hook for a Circle native-token migration.
10. **Admin triggers:** `Upgraded`, router `SetERC20Gateway` / `SetDefaultERC20Gateway` / `SetETHGateway`, gateway `UpdateTokenMapping`, PauseController `Pause`, messenger/ScrollChain `Paused`, `UpdateFeeVault`, ScrollChain `UpdateSequencer` / `UpdateProver` / `UpdateEnforcedBatchMode` / `RevertBatch`, ScrollOwner `GrantAccess`, Lido `DepositsDisabled` / `WithdrawalsDisabled`.
11. **Large-transfer trigger:** `DepositETH.amount`, `FinalizeWithdrawETH.amount`, `DepositERC20.amount` / `FinalizeWithdrawERC20.amount` per `l1Token`, and the ETH balance of the messenger for a drain.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Messenger / queue =====
TOPIC_SCROLL_SENT_MESSAGE            = '\x104371f3b442861a2a7b82a070afbbaab748bb13757bf47769e170e37809ec1e'
TOPIC_SCROLL_RELAYED_MESSAGE         = '\x4641df4a962071e12719d8c8c8e5ac7fc4d97b927346a3d7a335b1f7517e133c'
TOPIC_SCROLL_FAILED_RELAYED_MESSAGE  = '\x99d0e048484baa1b1540b1367cb128acd7ab2946d1ed91ec10e3c85e4bf51b8f'
TOPIC_SCROLL_QUEUE_TRANSACTION       = '\x69cfcb8e6d4192b8aba9902243912587f37e550d75c1fa801491fce26717f37e'
TOPIC_SCROLL_COMMIT_BATCH            = '\x2c32d4ae151744d0bf0b9464a3e897a1d17ed2f1af71f7c9a75f12ce0d28238f'
TOPIC_SCROLL_FINALIZE_BATCH          = '\x26ba82f907317eedc97d0cbef23de76a43dd6edb563bdb6e9407645b950a7a2d'
-- ===== Gateways =====
TOPIC_SCROLL_DEPOSIT_ETH             = '\x6670de856ec8bf5cb2b7e957c5dc24759716056f79d97ea5e7c939ca0ba5a675'
TOPIC_SCROLL_FINALIZE_WITHDRAW_ETH   = '\x96db5d1cee1dd2760826bb56fabd9c9f6e978083e0a8b88559c741a29e9746e7'
TOPIC_SCROLL_REFUND_ETH              = '\x289360176646a5f99cb4b6300628426dca46b723f40db3c04449d6ed1745a0e7'
TOPIC_SCROLL_DEPOSIT_ERC20           = '\x31cd3b976e4d654022bf95c68a2ce53f1d5d94afabe0454d2832208eeb40af25'
TOPIC_SCROLL_FINALIZE_WITHDRAW_ERC20 = '\xc6f985873b37805705f6bce756dce3d1ff4b603e298d506288cce499926846a7'
TOPIC_SCROLL_REFUND_ERC20            = '\xdbdf8eb487847e4c0f22847f5dac07f2d3690f96f581a6ae4b102769917645a8'
TOPIC_SCROLL_DEPOSIT_ERC721          = '\xfc1d17c06ff1e4678321cc30660a73f3f1436df8195108a288d3159a961febec'
TOPIC_SCROLL_DEPOSIT_ERC1155         = '\x7f6552b688fa94306ca59e44dd4454ff550542445a3f1cb39b8c768be6f5c08a'
TOPIC_SCROLL_BATCH_GW_DEPOSIT        = '\x4e2ca0515ed1aef1395f66b5303bb5d6f1bf9d61a353fa53f73f8ac9973fa9f6'
-- ===== Admin =====
TOPIC_SCROLL_SET_ERC20_GATEWAY       = '\x0ead4808404683f66d413d788a768219ea9785c97889221193103841a5841eaf'
TOPIC_SCROLL_UPDATE_TOKEN_MAPPING    = '\x2069a26c43c36ffaabe0c2d19bf65e55dd03abecdc449f5cc9663491e97f709d'
TOPIC_SCROLL_PAUSE_COMPONENT         = '\x5ee71a369c8672edded508e624ffc9257fa1ae6886ef32905c18e60196bca399'
TOPIC_OZ_PAUSED                      = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_SCROLL_UPDATE_SEQUENCER        = '\x631cb110fbe6a87fba5414d6b2cff02264480535cd1f5abdbc4fa638bc0b5692'
TOPIC_UPGRADED                       = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
SEL_SCROLL_SEND_MESSAGE              = '\xb2267a7b'
SEL_SCROLL_RELAY_MESSAGE_WITH_PROOF  = '\xc311b6fc'
SEL_SCROLL_REPLAY_MESSAGE            = '\x55004105'
SEL_SCROLL_RELAY_MESSAGE_HASHED      = '\x8ef1332e'
SEL_SCROLL_DEPOSIT_ETH               = '\x9f8420b3'
SEL_SCROLL_DEPOSIT_ETH_TO            = '\xce0b63ce'
SEL_SCROLL_DEPOSIT_ERC20             = '\x21425ee0'
SEL_SCROLL_DEPOSIT_ERC20_TO          = '\xf219fa66'
SEL_SCROLL_FINALIZE_WITHDRAW_ETH     = '\x8eaac8a3'
SEL_SCROLL_FINALIZE_WITHDRAW_ERC20   = '\x84bd13b0'
SEL_SCROLL_SET_ERC20_GATEWAY         = '\x635c8637'
SEL_SCROLL_GET_ERC20_GATEWAY         = '\x43c66741'
SEL_PROXYADMIN_UPGRADE_AND_CALL      = '\x9623609d'

-- ===== Ethereum (chain ID 1) =====
ETH_SCROLL_MESSENGER                 = '\x6774bcbd5cecef1336b5300fb5186a12ddd8b367'
ETH_SCROLL_GATEWAY_ROUTER            = '\xf8b1378579659d8f7ee5f3c929c2f3e332e41fd6'
ETH_SCROLL_ETH_GATEWAY               = '\x7f2b8c31f88b6006c382775eea88297ec1e3e905'
ETH_SCROLL_STANDARD_ERC20_GATEWAY    = '\xd8a791fe2be73eb6e6cf1eb0cb3f36adc9b3f8f9'
ETH_SCROLL_CUSTOM_ERC20_GATEWAY      = '\xb2b10a289a229415a124efdef310c10cb004b6ff'
ETH_SCROLL_WETH_GATEWAY              = '\x7ac440cae8eb6328de4fa621163a792c1ea9d4fe'
ETH_SCROLL_USDC_GATEWAY              = '\xf1af3b23de0a5ca3cab7261cb0061c0d779a5c7b'
ETH_SCROLL_EURC_GATEWAY              = '\xbc4b3d9a89f187dbaa0d2e60985ea1fffa5247d2'
ETH_SCROLL_DAI_GATEWAY               = '\x67260a8b73c5b77b55c1805218a42a7a6f98f515'
ETH_SCROLL_LIDO_GATEWAY              = '\x6625c6332c9f91f2d27c304e729b86db87a3f504'
ETH_SCROLL_PUFETH_GATEWAY            = '\xa033ff09f2da45f0e9ae495f525363722df42b2a'
ETH_SCROLL_ERC721_GATEWAY            = '\x6260af48e8948617b8fa17f4e5cea2d21d21554b'
ETH_SCROLL_ERC1155_GATEWAY           = '\xb94f7f6abcb811c5ac709de14e37590fccd975b6'
ETH_SCROLL_BATCH_BRIDGE_GATEWAY      = '\x5bcfd99c34cf7e06fc756f6f5ae7400504852bc4'
ETH_SCROLL_CHAIN                     = '\xa13baf47339d63b743e7da8741db5456dac1e556'
ETH_SCROLL_MESSAGE_QUEUE_V2          = '\x56971da63a3c0205184fef096e9ddfc7a8c2d18a'
ETH_SCROLL_MESSAGE_QUEUE_V1          = '\x0d7e906bd9cafa154b048cfa766cc1e54e39af9b'
ETH_SCROLL_ENFORCED_TX_GATEWAY       = '\x72cacbcfde2d1e19122f8a36a4d6676cd39d7a5d'
ETH_SCROLL_SYSTEM_CONFIG             = '\x8432728a257646449245558b8b7dbe51a16c7a4d'
ETH_SCROLL_PAUSE_CONTROLLER          = '\xb8f7ea9998530833cbb7e0ef4f0d945957229d8b'
ETH_SCROLL_FEE_VAULT                 = '\x8fa3b4570b4c96f8036c13b64971ba65867eeb48'
ETH_SCROLL_PROXY_ADMIN               = '\xeb803eb3f501998126bf37bb823646ed3d59d072'
ETH_SCROLL_OWNER                     = '\x798576400f7d662961ba15c6b3f3d813447a26a6'
-- look-alikes to EXCLUDE (Morph)
ETH_MORPH_MESSENGER                  = '\xdc71366effa760804dcfc3edf87fa2a6f1623304'
ETH_MORPH_ETH_GATEWAY                = '\x1c1ffb5828c3a48b54e8910f1c75256a498ade68'
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain: no Scroll contracts
```

---

## 8. Verification & sources

How the constants were verified:

- **Topics and selectors:** recomputed as `keccak256(signature)` from the deployed ABIs of the current implementations (verified sources as captured in L2BEAT's discovery data) and from `scroll-contracts` (`src/L1/L1ScrollMessenger.sol`, `src/libraries/IScrollMessenger.sol`, `src/L1/gateways/*.sol`, `src/L1/rollup/*.sol`, `src/batch-bridge/L1BatchBridgeGateway.sol`, `src/lido/L1LidoGateway.sol`). Live logs confirmed every topic in the counts below.
- **Sample transactions read:** ETH deposit `0x44f31a843e1d2034180a859fb4dc29e96cc4c38d7078815ad3c99a2caed99e8c` (router `depositETH`, 0.004 ETH; fee-vault `SafeReceived`, `QueueTransaction` with the aliased messenger as sender, `SentMessage` from the ETH gateway to the L2 ETH gateway, `DepositETH`); plain message `0xae73a40f35f4c28c34e00ef1f54b2202959865a570810ed414e7653acc72cbc4`; USDC withdrawal `0x4630a4578b0dd52e7c144a4992f556cbda10f405f57f6ecffb6f8b8e223cef48` (`relayMessageWithProof`: USDC `Transfer` gateway → user, `FinalizeWithdrawERC20`, `RelayedMessage`); ETH withdrawal `0xbcf627c49b19db37e0ba08fb88f62128205d2846770e64f7efb52f492b9ef8dd` (`FinalizeWithdrawETH`, `RelayedMessage`, value as an internal transfer).
- **Addresses:** the core set from the Scroll docs page; the token gateways confirmed by `L1GatewayRouter.getERC20Gateway(token)` for USDC, EURC, DAI, wstETH, pufETH, WETH, USDT, WBTC, weETH, STONE; the USDC-code gateways by `l1USDC()`, `l2USDC()`, `counterpart()`, `router()`, `messenger()`, `depositPaused()`, `withdrawPaused()`; the batch gateway by `messenger()`, `router()`, `counterpart()`, `queue()`; the messenger by `feeVault()`, `rollup()`, `counterpart()`, `messageQueueV1()`, `messageQueueV2()`, `paused()`; `owner()` of the main contracts and both third-party ProxyAdmins; EIP-1967 implementation and admin slots of every proxy; Morph contracts identified by L2BEAT's Morph discovery data and by their live `messenger()` / `counterpart()`.
- **Chain coverage:** `eth_getCode` = `0x` (nonce 0) on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain for the addresses listed under §4.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26072222–26075812), Scroll emitters only:** `SentMessage` 3, `QueueTransaction` (V2) 3, `QueueTransaction` (V1) 0, `RelayedMessage` 157, `FailedRelayedMessage` 0, `DepositETH` 0, `FinalizeWithdrawETH` 51, `DepositERC20` 0, `FinalizeWithdrawERC20` 8 (USDC 2, wstETH 2, pufETH 2, Standard 2), `RefundETH` 0, `RefundERC20` 0, batch-gateway `Deposit` 0, `CommitBatch` 9, `FinalizeBatch` 8. The other seven chains: no Scroll emitter exists (look-alike counts in §6).

Sources opened:
- [scroll-tech/scroll-contracts](https://github.com/scroll-tech/scroll-contracts) (`src/`)
- [Scroll docs — Scroll contracts](https://docs.scroll.io/en/developers/scroll-contracts/)
- [L2BEAT discovery data for Scroll](https://github.com/l2beat/l2beat/blob/main/packages/config/src/projects/scroll/discovered.json) and [for Morph](https://github.com/l2beat/l2beat/blob/main/packages/config/src/projects/morph/discovered.json)
- Scroll JSON-RPC `eth_chainId` (public endpoint) for 534352

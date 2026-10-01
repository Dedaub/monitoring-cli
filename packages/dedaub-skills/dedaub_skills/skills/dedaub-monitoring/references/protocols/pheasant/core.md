# Pheasant Network — Topics, Selectors, Addresses (bridge: Ethereum + Base + Arbitrum + Optimism; swap wrapper also Polygon + BNB + Avalanche; NOT Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the Sourcify-verified implementations (`PheasantNetworkBridgeChild`, `PayoutExecutor`, `PheasantNetworkCctpBurn`, `PheasantNetworkSwap`, solc 0.8.18), the on-chain `PheasantNetworkParameters` contracts, and the official docs pages "Network Code and Address", "Technical Details", "Mechanism", "CCTP" and "Swap / Supported Networks".
**Scope:** the Pheasant bridge (ERC-7683 origin settler `PheasantNetworkBridgeChild` + destination settler `PayoutExecutor`), the USDC CCTP wrapper `PheasantNetworkCctpBurn`, and the swap wrapper `PheasantNetworkSwap`. Topics and selectors are chain-agnostic. Addresses are network-specific: each chain has its own proxy addresses, except the swap wrapper.

Pheasant is an optimistic, relayer-filled bridge for ETH and USDC between Ethereum and L2s. Since v5.0.0 (June 2026) every bridge order is an **ERC-7683** on-chain order. The user calls `open()` on the BridgeChild of the source chain and escrows the funds. The relayer (filler) calls `fill()` on the `PayoutExecutor` of the destination chain and pays the recipient from its own funds. The relayer then calls `withdraw()` (or `bulkWithdraw()`) on the source BridgeChild to take the escrow, and records the destination transaction hash. A disputer can challenge a withdrawal and slash the relayer's bond.

The **link key** is the ERC-7683 `orderId`. It is `topic1` of `Open`, `BridgeOrderOpened` and `TradeRefBound` on the source, and `topic1` of `Filled` on the destination. The source-side `Withdraw` event also carries the destination fill **transaction hash** as `topic2`, so the source chain links back to the exact destination transaction.

All contracts are OpenZeppelin TransparentUpgradeableProxy instances (1896-byte proxy code), each with its own ProxyAdmin. One EOA is the owner and the only relayer on all four bridge chains.

---

## 0. Contract families & flow

| Contract | Chains | Role | Side |
|----------|--------|------|------|
| **PheasantNetworkBridgeChild** | ETH, Base, ARB, OP | ERC-7683 origin settler and escrow. `open()` takes the user's ETH (`msg.value`) or USDC (`transferFrom`). Relayer `withdraw()` releases the escrow to the relayer. User `cancelTrade()` refunds after 24 h. | Source (deposit), relayer repayment, refund |
| **PayoutExecutor** | ETH, Base, ARB, OP | ERC-7683 destination settler. `fill()` pays the recipient: native ETH forwarded from `msg.value`, or USDC pulled from the filler with `transferFrom(filler, recipient)`. It never holds funds. | Destination (payout) |
| **PheasantNetworkParameters** | ETH, Base, ARB, OP | Per-chain config: network codes, token addresses, limits, fees, the `PayoutExecutor` of each destination code. Read by the BridgeChild and the PayoutExecutor. | Config |
| **PheasantNetworkCctpBurn** | ETH, Base, ARB, OP | USDC above the optimistic threshold goes over Circle CCTP: `callDepositForBurn()` burns through the CCTP `TokenMessenger`. Destination mint is Circle's own contract (see the `cctp` doc). | Source (burn) |
| **PheasantNetworkSwap** | ETH, Base, ARB, OP, POLY, BNB, AVAX | Swap wrapper: `execute()` pulls the user's token and calls a whitelisted DEX or aggregator ("tool contract"), which may itself bridge. Emits `SwapNewTrade`. | Source (third-party route) |
| BondManager / BridgeDisputeManager / CheckpointManager | per chain | Relayer bond, evidence checks, L1 block hashes for disputes. Addresses not listed by the docs; not documented here. | Dispute |

Flow of one ETH order Base → Arbitrum (sample, §11):

1. Base `open()` with `msg.value` 0.01 ETH → `NewTrade`, `TradeRefBound`, `Open`, `BridgeOrderOpened` (all with the same `orderId`). No ERC-20 log.
2. Arbitrum `fill()` by the relayer with `msg.value` 0.009979… ETH → `Filled(orderId, …, recipient = the user)`. Native transfer, no ERC-20 log.
3. Base `bulkWithdraw()` by the relayer → `Withdraw(user, txHash = the Arbitrum fill transaction)`, and the escrowed ETH goes to the relayer.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 PheasantNetworkBridgeChild (source settler, escrow)

| topic0 | Event |
|--------|-------|
| `0x3448bbc2203c608599ad448eeb1007cea04b788ac631f9f558e8dd01a3c27b3d` | `Open(bytes32 indexed orderId, (address user, uint256 originChainId, uint32 openDeadline, uint32 fillDeadline, bytes32 orderId, (bytes32 token, uint256 amount, bytes32 recipient, uint256 chainId)[] maxSpent, (bytes32 token, uint256 amount, bytes32 recipient, uint256 chainId)[] minReceived, (uint256 destinationChainId, bytes32 destinationSettler, bytes originData)[] fillInstructions) resolvedOrder)` |
| `0x6ee4c866116797ff31905edd3cf3f425b8d466dd5a29fd7e0dbc73794b04d164` | `BridgeOrderOpened(bytes32 indexed orderId, address indexed user, uint256 indexed tradeIndex, uint8 tokenTypeIndex, uint256 originChainId, uint256 destinationChainId, uint256 destinationNetworkCode, address destinationSettler, bytes originData, uint256 outputAmount)` |
| `0xbb57ee4b162564fa9ebb41cd5b33d4df7bfa7348b7282af3ea2c74bfd5acb073` | `TradeRefBound(bytes32 indexed orderId, address indexed user, uint256 indexed index, uint8 tokenTypeIndex, uint256 originChainId)` |
| `0xb95fcdf61634c9031987e4c38c5cb99790381af4965c948332d674812764fc0c` | `NewTrade(address indexed userAddress, uint256 index, address to, uint256 amount, address token)` |
| `0xe3ab5599c951643f64cea1bf04e5889b9f80a01874b8c95e0103d1daa8101410` | `Withdraw(address indexed userAddress, bytes32 indexed txHash, uint256 index, address to, uint256 amount, address token)` |
| `0xd0ee89748b6e8293e0cf891317ec9b3211103b6d96492f4552b9df93a72e5e52` | `Cancel(address indexed userAddress, uint256 index, string reason)` |
| `0xc21357d76c2ee05713ed6e2edb9a5f60ab1e8748c56201385df30007f774f58d` | `Dispute(address indexed userAddress, uint256 indexed index, uint256 disputedTime)` |
| `0x11bb07c7687757dded72092741ebc17fc034b79fe6b67b19339ab1ddc3775ea3` | `Defence(address indexed userAddress, uint256 indexed index, uint8 status)` |
| `0x41e6a64fa7aa5d67783457215f3577addb2b6ffe5476a8939954fa617f6b785f` | `Slash(address indexed userAddress, uint256 indexed index, address relayer)` |
| `0x74f59af880784cfadab7c55f646834d3495cde9deec4033b46bff1afe1f06789` | `Accept(address indexed userAddress, bytes32 indexed txHash, uint256 index, address to, uint256 amount, address token)` — declared in the ABI, not emitted by the current implementation |
| `0x430a0fd8eac11cf42ad09ad404dfa7ece6e7bef60893f12b79741ad2873795c5` | `ManagerUpdate(bool isFinalized, uint8 operation, address newAddresses)` — admin (also emitted by the parameters contract) |
| `0x16dee0275940c1f9755ccfa733d90937474962093c3d9ba915947eafc472be74` | `BridgeInitialized(address owner, address params, address disputeManager, address bondManager)` |

Side: `Open` / `BridgeOrderOpened` / `TradeRefBound` / `NewTrade` = source deposit (four logs of the same order in one transaction). `Withdraw` = relayer repayment from the escrow (value moves escrow → relayer). `Cancel` = refund to the user (or relayer cancel, §7 item 5). `Dispute`, `Defence` = status only. `Slash` = bond slash (value to the user and the disputer).

### 1.2 PayoutExecutor (destination settler)

| topic0 | Event |
|--------|-------|
| `0xd044026e1b228038b252f864001eff50347e64c2f53cd12317e1f434433852d8` | `Filled(bytes32 indexed orderId, bytes32 indexed orderTermsHash, address indexed recipient, address token, uint256 amount, address filler)` |
| `0xebac461f9977edbcdf46b31f595ce8fb7597f45bfb6d4008083783376521936f` | `PayoutExecutorContractActiveToggled(bool isActive)` — pause / unpause |
| `0x3dcf6cba59d9467d90ad0d13bd38112cb8a87b263ed47dd1189498fbb262f600` | `PayoutExecutorParamsUpdate(bool isFinalized, address oldParams, address newParams)` |
| `0xe08ee3a1f648d28823dc75c35d09ad75a72a171f7364c957b29122fc11230561` | `PayoutExecutorParamsUpdated(address oldParams, address newParams)` |
| `0xd212e99b884afb5e471a21c7adb5f3b5867362473b4be941cfc36de2e19d1799` | `PayoutExecutorInitialized(address owner, address params)` |

### 1.3 PheasantNetworkCctpBurn (USDC over CCTP)

| topic0 | Event |
|--------|-------|
| `0x714a89da287fe5c524c38f8c37f72f7e6eec2adcce30042c203d6152c7094c4c` | `DepositForBurnCalled(address indexed sender, bytes32 indexed recipient, uint32 indexed destinationDomain, uint256 index, uint256 amount, address token, uint256 originalAmount)` |
| `0x207a1aa0fe1e4a9c90b8700957f0cc0787d85d98206087b0d086ab11aca926a5` | `FeeRateUpdateRequested(uint32 indexed destinationDomain, uint256 newRatePpm, uint64 executeAfter)` |
| `0x844fda05fdeddb3f84ffcf8d96eab47fc4c7d0d972df52d1e77af5c603875153` | `FeeRateUpdated(uint32 indexed destinationDomain, uint256 newRatePpm)` |

`destinationDomain` is the Circle CCTP domain (Ethereum 0, Avalanche 1, Optimism 2, Arbitrum 3, Base 6, Polygon 7, Unichain 10), not a Pheasant network code.

### 1.4 PheasantNetworkSwap (swap wrapper)

| topic0 | Event |
|--------|-------|
| `0xd3c401dfdd079a8763e51394e4dbd6cdb508ae3474090c4d3aa61fe419532503` | `SwapNewTrade(address indexed userAddress, address indexed token, (string toChainId, uint16 swapToolIndex, address toolContract, address toToken, uint256 amount, uint256 relayerFee, uint256 timestamp) trade)` |
| `0xa6cb6e08ad908f9d671a8ebbc0e7146756b08daf9d414bb21dbc891388f00000` | `SwapRefundTrade(address indexed userAddress, address indexed token, bytes32 tradeHash, uint256 refunded, uint256 fee, bytes data)` |
| `0xfa2c40d0588b37c491b80ca87173fc8d840eb485adec24c45ee23d4289bfa6f4` | `SwapWithdrawTrade(address indexed userAddress, address indexed token, bytes32 tradeHash, uint256 amount, bytes data)` |
| `0x504c6b1ba9ab27e29ac0d69892254dd109829b156e18b746c56433be5b04e178` | `SwapBulkWithdrawTrade((bytes data, bytes32 tradeHash, address userAddress, address token, uint256 amount)[] withdraws)` |
| `0xe2e42d7ae303ebbcb22266a6ebb41d9c9678628cd17a59589f3885d68eb2cd83` | `SwapUpdateParams(address params)` |
| `0x962b9b0a40093afe893ab82fb20c5650da4cbae48c7542c402d3251e261a9a3c` | `SwapUpdateNativeToken(address token)` |
| `0xff5ca8663ed3b85e7db74cfe850fb10dffe51b162b7a365e56ae325585414976` | `SwapInitialized(address owner, address params)` |

### 1.5 Common (all four families)

| topic0 | Event |
|--------|-------|
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — emitted by each transparent proxy |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 PheasantNetworkBridgeChild

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe917a962` | `open((uint32 fillDeadline, bytes32 orderDataType, bytes orderData) order)` | Payable. User deposit. `orderData` = `BridgeOrderDataV1` (256 bytes: salt, expectedTradeIndex, tokenTypeIndex, amount, fee, recipient, destinationChainId, destinationNetworkCode). Emits `NewTrade`, `TradeRefBound`, `Open`, `BridgeOrderOpened`. |
| `0x844fac8e` | `openFor((address originSettler, address user, uint256 nonce, uint256 originChainId, uint32 openDeadline, uint32 fillDeadline, bytes32 orderDataType, bytes orderData) order, bytes signature, bytes originFillerData)` | Always reverts (`GASLESS_DISABLED_V1`). |
| `0x41b477dd` | `resolve((uint32 fillDeadline, bytes32 orderDataType, bytes orderData) order)` | View. |
| `0x07bc6fad` | `withdraw(address _user, uint256 _index, bytes32 _txHash, uint256 _blockNumber)` | Relayer only. Escrow → relayer. Emits `Withdraw`. |
| `0x5564ed8c` | `bulkWithdraw((address userAddress, uint256 index)[] _userTrades, bytes32[] _txHashes, uint256[] _blockNumbers)` | Relayer only. Batched `withdraw`. The usual call. |
| `0x09ec6cc7` | `cancelTrade(uint256 _index)` | User refund, 24 h after the trade if still unpaid. Emits `Cancel`. |
| `0x81a6ca81` | `cancelTradeByRelayer(address user, uint256 _index, string _reason)` | Relayer refund of an unpaid trade. Emits `Cancel` (see §7 item 5). |
| `0xe2f5de60` | `dispute(uint8 _tokenTypeIndex, uint256 _amount, address _userAddress, uint256 _index)` | Payable. Disputer posts a deposit. Emits `Dispute`. |
| `0x66f4f09c` | `defence(address _userAddress, uint256 _index, (uint256,bytes32,bytes[],bytes[],bytes,uint8[],bytes,bytes[],bytes[],uint8) _evidence)` | Relayer only. Emits `Defence`. |
| `0x02fb4d85` | `slash(address _userAddress, uint256 _index)` | Disputer. Emits `Slash`. |
| `0x7a8a395a` | `executeManagerUpdate(uint8 _operation, address _newManager)` | Relayer only. 3 h delay. Emits `ManagerUpdate(false,…)`. |
| `0x495d9f2d` | `finalizeManagerUpdate()` | Relayer only. Emits `ManagerUpdate(true,…)`. |
| `0x1385d24c` | `toggleContractActive()` | Owner only. Pause / unpause (no event on the BridgeChild). |
| `0xca142f75` | `getTrade(address _user, uint256 _index)` | View. |
| `0x492eff52` | `getTradeRef(bytes32 orderId)` | View: `(user, index, tokenTypeIndex, originChainId)`. |
| `0x26089dd7` | `destTxHashes(address, uint256)` | View: the destination fill hash recorded by `withdraw`. |
| `0x803184b4` | `networkCode()` | View (read live in §3). |
| `0x8406c079` | `relayer()` | View. |
| `0x8da5cb5b` | `owner()` | View. |
| `0xc032846b` | `getContractStatus()` | View: `true` when active. |

### 2.2 PayoutExecutor

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x82e2c43f` | `fill(bytes32 orderId, bytes originData, bytes fillerData)` | Payable. Pays the recipient. Emits `Filled`. Anyone can fill a valid order (no relayer check), but only the registered relayer can later `withdraw` on the source. |
| `0x288cdc91` | `filled(bytes32)` | View: order already filled. |
| `0x1385d24c` | `toggleContractActive()` | Owner only. Emits `PayoutExecutorContractActiveToggled`. |
| `0x07fe2e54` | `updateParams(address _params)` | Owner only. 3 h delay. |
| `0xb978d1f9` | `finalizeParamsUpdate()` | Owner only. |
| `0xcff0ab96` | `params()` | View. |
| `0x22f3e2d4` | `isActive()` | View. |

### 2.3 PheasantNetworkCctpBurn

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa1fea44a` | `callDepositForBurn(uint256 _amount, uint32 _destinationDomain, bytes32 _mintRecipient, address _burnToken)` | User. Emits `DepositForBurnCalled`, then burns through CCTP `depositForBurn(uint256,uint32,bytes32,address)`, then sends the fee from the user to the relayer. |
| `0x94b59cba` | `requestFeeRateUpdate(uint32 _destinationDomain, uint256 _newRatePpm)` | Relayer only. |
| `0x201274c1` | `finalizeFeeRateUpdate(uint32 _destinationDomain)` | After 3 h. |
| `0xebbeea75` | `getFee(uint256 _amount, uint32 _destinationDomain)` | View. |

### 2.4 PheasantNetworkSwap

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6a372984` | `execute((bytes data, string toChainId, uint16 swapToolIndex, address toolContract, address fromToken, address toToken, uint256 amount, uint256 value, uint256 gas, uint256 quoteTimestamp) request)` | Payable. Pulls the user's token and calls `toolContract`. Emits `SwapNewTrade`. |
| `0xc35925e9` | `refund(address userAddress, address token, bytes32 tradeHash, bytes data)` | Relayer fee refund to the user. Emits `SwapRefundTrade`. |
| `0xe37ba9b2` | `withdraw((bytes data, bytes32 tradeHash, address userAddress, address token) request)` | Owner only. Relayer fee to the owner. Emits `SwapWithdrawTrade`. |
| `0x01c270c3` | `bulkWithdraw((bytes data, bytes32 tradeHash, address userAddress, address token)[] requests)` | Owner only. |
| `0x07fe2e54` | `updateParams(address _params)` | Owner only. |
| `0xd3139c17` | `updateNative(address token)` | Owner only. |

---

## 3. Pheasant network codes and token types

Read live with `networkCode()` on each BridgeChild, and with `payoutExecutor(uint256)` (`0xda234a4f`) on the Ethereum parameters contract:

| Network | Chain ID | Pheasant network code | PayoutExecutor for this destination |
|---------|----------|----------------------|-------------------------------------|
| Ethereum | 1 | 1001 | `0xb56De9d9Fb52f7Ef86407DC669868D24b61714A0` |
| Optimism | 10 | 1003 | `0x3adf0ae154c6fad0aef6bcdf8a7198ebea37ad60` |
| Arbitrum One | 42161 | 1004 | `0xd0d9df958bb728b0c90e7c94aa398c26d2e4a3c5` |
| Base | 8453 | 1007 | `0x25cf6B24eC351d1695490B2046310cA3e8AdBE7B` |
| (off-target) Scroll 1005, ZKsync 1006, Linea 1009, Taiko 1010, Morph 1014, Unichain 1017, MegaETH 1020 | — | — | registered in the parameters contract |

Code 1002 has no PayoutExecutor (zero address). Polygon, BNB, Avalanche and Robinhood Chain have no bridge code and no bridge contracts. Token type indexes: 0 = ETH (native), 1 = USDC, 2 = USDC.e.

---

## 4. Addresses — Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10)

All proxies: 1896-byte TransparentUpgradeableProxy. Existence-checked with `eth_getCode` on 2026-09-29. Implementation = EIP-1967 slot. ProxyAdmin = EIP-1967 admin slot.

| Chain | Contract | Proxy | Implementation | ProxyAdmin |
|-------|----------|-------|----------------|------------|
| Ethereum | BridgeChild | `0x20A41749545eB0C6266838257aDeA7b86d5369Ac` | `0x735fdec220d4c5bbd16375480c2c72fc5f5e8d7b` | `0xc83fa96cbac23766dc7d5c3da61a06d0df7531a2` |
| Ethereum | PayoutExecutor | `0xb56De9d9Fb52f7Ef86407DC669868D24b61714A0` | `0x8dd105aedb53a058e211aefda8c3db178b6c8aa1` | `0x831166dc3d3548d2468f836ff460fdf7c85b4d96` |
| Ethereum | CctpBurn | `0x2dC80114D923dA07327b7096226359D785F32e3F` | `0x211ff4666ed8b026b6e45e74b8f468733827cac9` | `0x99a34087ce235bed2e1aabd102a4adb5c968b2c6` |
| Ethereum | Parameters | `0x0d647142f408cd48c3dfd970a30e4786a484f0a7` | — | — |
| Base | BridgeChild | `0x8A7Ee008B18DF025bc778B034Dbd7ad507221e10` | `0xc9193e83388bb7000eced3ff5e41f32a39caa62e` | `0x9b1cb22a38fde1eec8a0c0af77259f34ea4c511b` |
| Base | PayoutExecutor | `0x25cf6B24eC351d1695490B2046310cA3e8AdBE7B` | `0x2591b708de79d2b73d729d9255f4031de6bbc03a` | `0xc4ead5aa45a6a9d77913b021a605c822b886df76` |
| Base | CctpBurn | `0xE33Bf689B53ae461bd253617B60408227182362b` | `0x325fe9c581ab84a73d32a820142e8e40e703d0b3` | `0x4e7fdda68761d2a58269891e073710a8611b26da` |
| Base | Parameters | `0x69a79c9705655f670214442d2087e3c1883237e5` | — | — |
| Arbitrum One | BridgeChild | `0x97450C9B5fC6D1b86bF87EFDCbB137f26F8b497e` | `0xfc85a8319fbde14ecb64de3e4a6f316732e93ffc` | `0xf2911afe9e1ffa20abd495b644b11b45f579921b` |
| Arbitrum One | PayoutExecutor | `0xd0d9df958bb728b0c90e7c94aa398c26d2e4a3c5` | `0x7df9191bcc4b58eb4601472cafd5c28f8426d58d` | `0x76bfab1950dfd7dfd5ae7b0ef6c3763be9e87439` |
| Arbitrum One | CctpBurn | `0xBc0E277204f85d3924577FF2b0E50e67051B3E62` | `0x24810748c93c9922aa395de252c8406a761d5da8` | `0x67d5dd425c84a1b9614f87cdf7729415e19034f8` |
| Arbitrum One | Parameters | `0x0c90b40e8a176b084c033a41051e3aed0e5c36c2` | — | — |
| Optimism | BridgeChild | `0x0C4F10259c8b5Ed7238B76A0a6EfEf82cd2908Bf` | `0xa80c1b92810db950081c5f0a273dabb93a97c504` | `0x82b050e288ddf02423819ee154ae236d2d6688b6` |
| Optimism | PayoutExecutor | `0x3adf0ae154c6fad0aef6bcdf8a7198ebea37ad60` | `0x1841e97d126480d300fd0a924366fe11459c90b5` | `0x61137a7466e0063ae6dcbd78d5acbc0b407955d5` |
| Optimism | CctpBurn | `0xe8105d442EaD594fb05D6bE20d9813c8b7b974bD` | `0xb4203c99d003d2217eefa98b15d9abef3f537292` | `0x51b993aea818d7c4dae7f4a0fd66a2491bddd209` |
| Optimism | Parameters | `0x212464cfac228a01a1009432e3d0f7b2a798219c` | — | — |

The four BridgeChild implementations have identical code (one code hash), and so do the four PayoutExecutor and the four CctpBurn implementations. The parameters addresses were read from BridgeChild storage slot `0x69`, and they equal `params()` of the PayoutExecutor of the same chain.

**Roles (same on the four chains):** owner and sole relayer of every BridgeChild, PayoutExecutor and CctpBurn = EOA `0x1650683e50e075efc778be4d1a6be929f3831719` (nonce 16639 on Ethereum). It also owns every BridgeChild / PayoutExecutor ProxyAdmin and all Base / Arbitrum / Optimism CctpBurn ProxyAdmins. The Ethereum CctpBurn ProxyAdmin is owned by EOA `0xfc976d96ccc57bc9d04aea92a4a66abd71926298`.

## 5. Addresses — PheasantNetworkSwap (seven chains)

| Chain | Swap proxy | Implementation |
|-------|-----------|----------------|
| Ethereum | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` | `0xccc1c1d7b2e5fa02c2e8d65e182b719cba01b511` |
| Base | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` | `0x02ece12ddfc58eedbcb5477f81e19cb8ef3142c6` |
| Arbitrum One | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` | `0xccc1c1d7b2e5fa02c2e8d65e182b719cba01b511` |
| Polygon PoS | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` | `0xb4cbf45e69a26337de57f1c4326eb35bca4ac11d` |
| BNB Smart Chain | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` | `0xb4cbf45e69a26337de57f1c4326eb35bca4ac11d` |
| Avalanche C-Chain | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` | `0xb4cbf45e69a26337de57f1c4326eb35bca4ac11d` |
| **Optimism** | **`0x7956c6EaEA7cAb8cd6C3221aBE3425c7e07133d9`** | `0x41826e06390d06568de8672a3b7fa878c0eca7e9` |

ProxyAdmin `0x61d28feab0f2802289ded2bcbc17459b8462051e` (owned by EOA `0x04ce14025ece612650e43c2de44477a441ba95f3`) on all chains except Optimism. On Optimism the ProxyAdmin of the swap proxy **is** `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` (1531-byte ProxyAdmin code). `owner()` of every swap proxy (fee withdrawals) = EOA `0xb62831174af2086bfadf234d5005745444c83f36`.

## 6. Robinhood Chain (4663) — NOT DEPLOYED

`eth_getCode` returns `0x` on Robinhood Chain for every address of §4 and §5 (all BridgeChild, PayoutExecutor, CctpBurn and swap addresses, and the relayer address has nonce 0). Robinhood Chain is not in the official network-code table and has no network code in the parameters contract.

---

## 7. Cross-chain summary

| Chain | ID | BridgeChild | PayoutExecutor | CctpBurn | Swap wrapper |
|-------|----|-------------|----------------|----------|--------------|
| Ethereum | 1 | `0x20A41749545eB0C6266838257aDeA7b86d5369Ac` | `0xb56De9d9Fb52f7Ef86407DC669868D24b61714A0` | `0x2dC80114D923dA07327b7096226359D785F32e3F` | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` |
| Base | 8453 | `0x8A7Ee008B18DF025bc778B034Dbd7ad507221e10` | `0x25cf6B24eC351d1695490B2046310cA3e8AdBE7B` | `0xE33Bf689B53ae461bd253617B60408227182362b` | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` |
| Arbitrum One | 42161 | `0x97450C9B5fC6D1b86bF87EFDCbB137f26F8b497e` | `0xd0d9df958bb728b0c90e7c94aa398c26d2e4a3c5` | `0xBc0E277204f85d3924577FF2b0E50e67051B3E62` | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` |
| Optimism | 10 | `0x0C4F10259c8b5Ed7238B76A0a6EfEf82cd2908Bf` | `0x3adf0ae154c6fad0aef6bcdf8a7198ebea37ad60` | `0xe8105d442EaD594fb05D6bE20d9813c8b7b974bD` | `0x7956c6EaEA7cAb8cd6C3221aBE3425c7e07133d9` |
| Polygon PoS | 137 | — (`0x`) | — | — (decoy, §9 item 9) | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` |
| BNB Smart Chain | 56 | — | — | — | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` |
| Avalanche C-Chain | 43114 | — | — | — | `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` |
| Robinhood Chain | 4663 | — | — | — | — |

Off-target bridge chains (official table): Scroll, ZKsync, Linea, Taiko, Morph, Unichain, MegaETH. The swap wrapper is also on about 25 more chains.

---

## 8. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| BridgeChild, PayoutExecutor, CctpBurn (4 chains each) | OZ TransparentUpgradeableProxy | 1896-byte proxy code. Implementation and admin slots populated (§4). | Per-proxy ProxyAdmin (1531 B), owned by the relayer EOA (Ethereum CctpBurn: EOA `0xfc976d96ccc57bc9d04aea92a4a66abd71926298`). |
| PheasantNetworkSwap (7 chains) | OZ TransparentUpgradeableProxy | same 1896-byte proxy code | ProxyAdmin `0x61d28feab0f2802289ded2bcbc17459b8462051e` (Optimism: `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696`), owner EOA `0x04ce14025ece612650e43c2de44477a441ba95f3`. |
| PheasantNetworkParameters | not checked for a proxy | read through views only | relayer (3 h update delay) |

Watch `Upgraded` on every proxy. All upgrade, pause and parameter authority is held by EOAs.

---

## 9. Detection invariants & gotchas

1. **Link key = `orderId` (`topic1`) on both chains.** Source: `Open`, `BridgeOrderOpened`, `TradeRefBound` (all `topic1`). Destination: `Filled.topic1`. Confirmed on the sample pair (§11).
2. **The source `Withdraw` names the destination transaction.** `Withdraw.txHash` (`topic2`) is the hash of the destination `fill` transaction. It is recorded by the relayer, not proven on chain at that time.
3. **Four source events per order.** One `open()` emits `NewTrade`, `TradeRefBound`, `Open` and `BridgeOrderOpened`. Count one deposit, not four. `NewTrade` has no `orderId`: join it by `(userAddress, index)` = `TradeRefBound.(user, index)`.
4. **`Open` is the generic ERC-7683 topic.** Other ERC-7683 origin settlers emit the same topic (`TOPIC_OPEN_ERC7683` in §10). In the pinned window an unrelated, unverified contract `0x2831ea5524f171735af8feb2e331821bef176c8a` emitted 18 of the 19 Ethereum `Open` logs. Always filter `Open` by the BridgeChild address, or use `BridgeOrderOpened`, which is Pheasant-specific.
5. **`Cancel.userAddress` is not always the user.** `cancelTrade` emits the user, but `cancelTradeByRelayer` emits the **relayer** as `userAddress`. The refund always goes to the trade's user.
6. **Native ETH has no ERC-20 row on either side.** The deposit is `msg.value` of `open()`. The payout is the native value forwarded by `fill()`. Use native-transfer data or the event amounts.
7. **USDC payouts are filler → recipient, not contract → recipient.** `fill()` calls `transferFrom(filler, recipient)`. The PayoutExecutor never holds funds, so a filter on `Transfer.from = PayoutExecutor` finds nothing.
8. **Amounts.** `Filled.amount` and `BridgeOrderOpened.outputAmount` = deposit − fee. The relayer's `Withdraw.amount` is the full deposit.
9. **Same-address decoys.** On Polygon, `0xE33Bf689B53ae461bd253617B60408227182362b` (the Base CctpBurn address) holds an 8049-byte contract with the same code hash as the swap implementation `0xb4cbf45e69a26337de57f1c4326eb35bca4ac11d`: a swap logic contract, not a CCTP contract. On Optimism, `0xfC9C6B6e0D02EaDE37aC8b6c59e7181726075696` is a ProxyAdmin, not the swap wrapper.
10. **The CCTP leg ends at Circle.** `DepositForBurnCalled` is followed by Circle's `DepositForBurn` in the same transaction. The mint on the destination is Circle's `MessageTransmitter`. Link by the CCTP (source domain, nonce), as in the `cctp` doc.
11. **The swap wrapper hands value to a third-party tool contract.** `SwapNewTrade.trade.toChainId` (a string) is the destination. The destination leg belongs to the tool's own protocol. In the window, Base `SwapNewTrade` logs were same-chain swaps.
12. **Large-transfer and admin triggers.** Large transfers: `BridgeOrderOpened.outputAmount` and `Filled.amount`. Admin: `Upgraded`, `ManagerUpdate`, `PayoutExecutorContractActiveToggled`, `PayoutExecutorParamsUpdate`, calls to `toggleContractActive`, and `OwnershipTransferred`. Dispute: `Dispute`, `Slash`.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_OPEN_ERC7683               = '\x3448bbc2203c608599ad448eeb1007cea04b788ac631f9f558e8dd01a3c27b3d'
TOPIC_BRIDGE_ORDER_OPENED        = '\x6ee4c866116797ff31905edd3cf3f425b8d466dd5a29fd7e0dbc73794b04d164'
TOPIC_TRADE_REF_BOUND            = '\xbb57ee4b162564fa9ebb41cd5b33d4df7bfa7348b7282af3ea2c74bfd5acb073'
TOPIC_NEW_TRADE                  = '\xb95fcdf61634c9031987e4c38c5cb99790381af4965c948332d674812764fc0c'
TOPIC_WITHDRAW                   = '\xe3ab5599c951643f64cea1bf04e5889b9f80a01874b8c95e0103d1daa8101410'
TOPIC_CANCEL                     = '\xd0ee89748b6e8293e0cf891317ec9b3211103b6d96492f4552b9df93a72e5e52'
TOPIC_DISPUTE                    = '\xc21357d76c2ee05713ed6e2edb9a5f60ab1e8748c56201385df30007f774f58d'
TOPIC_SLASH                      = '\x41e6a64fa7aa5d67783457215f3577addb2b6ffe5476a8939954fa617f6b785f'
TOPIC_MANAGER_UPDATE             = '\x430a0fd8eac11cf42ad09ad404dfa7ece6e7bef60893f12b79741ad2873795c5'
TOPIC_FILLED                     = '\xd044026e1b228038b252f864001eff50347e64c2f53cd12317e1f434433852d8'
TOPIC_PAYOUT_ACTIVE_TOGGLED      = '\xebac461f9977edbcdf46b31f595ce8fb7597f45bfb6d4008083783376521936f'
TOPIC_DEPOSIT_FOR_BURN_CALLED    = '\x714a89da287fe5c524c38f8c37f72f7e6eec2adcce30042c203d6152c7094c4c'
TOPIC_SWAP_NEW_TRADE             = '\xd3c401dfdd079a8763e51394e4dbd6cdb508ae3474090c4d3aa61fe419532503'
TOPIC_SWAP_REFUND_TRADE          = '\xa6cb6e08ad908f9d671a8ebbc0e7146756b08daf9d414bb21dbc891388f00000'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
SEL_OPEN                         = '\xe917a962'
SEL_WITHDRAW                     = '\x07bc6fad'
SEL_BULK_WITHDRAW                = '\x5564ed8c'
SEL_CANCEL_TRADE                 = '\x09ec6cc7'
SEL_CANCEL_TRADE_BY_RELAYER      = '\x81a6ca81'
SEL_FILL                         = '\x82e2c43f'
SEL_CALL_DEPOSIT_FOR_BURN        = '\xa1fea44a'
SEL_SWAP_EXECUTE                 = '\x6a372984'
SEL_TOGGLE_CONTRACT_ACTIVE       = '\x1385d24c'

-- ===== Addresses =====
ETH_BRIDGE_CHILD                 = '\x20a41749545eb0c6266838257adea7b86d5369ac'
ETH_PAYOUT_EXECUTOR              = '\xb56de9d9fb52f7ef86407dc669868d24b61714a0'
ETH_CCTP_BURN                    = '\x2dc80114d923da07327b7096226359d785f32e3f'
ETH_SWAP                         = '\xfc9c6b6e0d02eade37ac8b6c59e7181726075696'
BASE_BRIDGE_CHILD                = '\x8a7ee008b18df025bc778b034dbd7ad507221e10'
BASE_PAYOUT_EXECUTOR             = '\x25cf6b24ec351d1695490b2046310ca3e8adbe7b'
BASE_CCTP_BURN                   = '\xe33bf689b53ae461bd253617b60408227182362b'
BASE_SWAP                        = '\xfc9c6b6e0d02eade37ac8b6c59e7181726075696'
ARB_BRIDGE_CHILD                 = '\x97450c9b5fc6d1b86bf87efdcbb137f26f8b497e'
ARB_PAYOUT_EXECUTOR              = '\xd0d9df958bb728b0c90e7c94aa398c26d2e4a3c5'
ARB_CCTP_BURN                    = '\xbc0e277204f85d3924577ff2b0e50e67051b3e62'
ARB_SWAP                         = '\xfc9c6b6e0d02eade37ac8b6c59e7181726075696'
OP_BRIDGE_CHILD                  = '\x0c4f10259c8b5ed7238b76a0a6efef82cd2908bf'
OP_PAYOUT_EXECUTOR               = '\x3adf0ae154c6fad0aef6bcdf8a7198ebea37ad60'
OP_CCTP_BURN                     = '\xe8105d442ead594fb05d6be20d9813c8b7b974bd'
OP_SWAP                          = '\x7956c6eaea7cab8cd6c3221abe3425c7e07133d9'
POLY_SWAP                        = '\xfc9c6b6e0d02eade37ac8b6c59e7181726075696'
BNB_SWAP                         = '\xfc9c6b6e0d02eade37ac8b6c59e7181726075696'
AVAX_SWAP                        = '\xfc9c6b6e0d02eade37ac8b6c59e7181726075696'
-- owner / sole relayer, same on ETH, Base, Arbitrum, Optimism
ETH_PHEASANT_RELAYER_EOA         = '\x1650683e50e075efc778be4d1a6be929f3831719'
-- unrelated ERC-7683 settler that also emits Open on Ethereum (exclude)
ETH_OTHER_ERC7683_SETTLER        = '\x2831ea5524f171735af8feb2e331821bef176c8a'
-- Robinhood Chain (4663): no Pheasant contract
```

---

## 11. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the Sourcify-verified sources: BridgeChild implementation (chain 1, `0x735fdec220d4c5bbd16375480c2c72fc5f5e8d7b`), PayoutExecutor implementations (chain 1 `0x8dd105aedb53a058e211aefda8c3db178b6c8aa1`, chain 8453 `0x2591b708de79d2b73d729d9255f4031de6bbc03a`), CctpBurn implementation (chain 8453 `0x325fe9c581ab84a73d32a820142e8e40e703d0b3`), Swap implementation (chain 8453 `0x02ece12ddfc58eedbcb5477f81e19cb8ef3142c6`). The ERC-7683 `Open` tuple was taken from the bundled `standards/ERC7683.sol`.
- **Addresses:** BridgeChild and CctpBurn from the official network-code table. PayoutExecutors from `payoutExecutor(uint256)` on the Ethereum parameters contract. Swap from the official swap network table. Network codes from `networkCode()` on each BridgeChild. Owner, relayer and parameters from `owner()`, `relayer()`, `params()` and slot `0x69`. ProxyAdmin owners from `owner()`. Presence on all eight chains with `eth_getCode`.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, logs at the listed addresses):** `Open` (= `NewTrade` = `BridgeOrderOpened` = `TradeRefBound`): Ethereum 1, Base 32, Arbitrum 22, Optimism 2. `Filled`: Ethereum 0, Base 29, Arbitrum 24, Optimism 3. `Withdraw`: Ethereum 1, Base 32, Arbitrum 22, Optimism 2. `Cancel`, `Slash`: 0 everywhere. `DepositForBurnCalled`: 0 on all four. `SwapNewTrade`: Base 4, Optimism 1, BNB 2, Ethereum / Arbitrum / Polygon / Avalanche 0. Robinhood: 0 (no contracts).
- **Sample transactions (receipts read):** Base `0x68b0cbb7ff867315d8c6ab790622212a80ddfa71a9d869eb324a364b06856e1d` (`open`, 0.01 ETH, `orderId` `0x003700f71b434e60a4dd5f896b80404c76ed1c8c8f8dc4bc54a74fe2e2865682`). Arbitrum `0x8e4cbb400416e8c571661bd547a071f2ffa6a661b26618ccb2329646ba3d3102` (`fill` by the relayer, `Filled` with the same `orderId`, recipient = the Base user). Base `0xe9ae62b7fa406360d626a5beca1edae0bc18754dd3c6f0176c3d594405c0b570` (`bulkWithdraw`, `Withdraw.txHash` = the Arbitrum fill hash). Base `0x188d89229fb64d2d0fea26bbd34efb340067eb61145dcd57b1bbcc5967176063` (`fill`, native ETH). Ethereum `0xad369577a919754dbc8cfbe67ac2c318bc699ee6fcdac5877321f2b65f6c08c3` (`open`, 0.1 ETH).

Authoritative sources:
- Docs — [Network Code and Address](https://docs.pheasant.network/products/bridge/network-code-and-address.md) · [Technical Details](https://docs.pheasant.network/products/bridge/contracts/technical-details.md) · [Mechanism](https://docs.pheasant.network/products/bridge/protocol/mechanism.md) · [CCTP](https://docs.pheasant.network/products/bridge/protocol/cctp.md) · [Swap contracts](https://docs.pheasant.network/products/swap/contracts.md) · [Swap supported networks](https://docs.pheasant.network/products/swap/supported-networks.md) · [Release notes](https://docs.pheasant.network/products/release-notes.md)
- Verified source — Sourcify (addresses above). No public Pheasant contracts repository was found.
- Explorers — [Etherscan BridgeChild](https://etherscan.io/address/0x20A41749545eB0C6266838257aDeA7b86d5369Ac) · [Basescan BridgeChild](https://basescan.org/address/0x8A7Ee008B18DF025bc778B034Dbd7ad507221e10) · [Arbiscan PayoutExecutor](https://arbiscan.io/address/0xd0d9df958bb728b0c90e7c94aa398c26d2e4a3c5)

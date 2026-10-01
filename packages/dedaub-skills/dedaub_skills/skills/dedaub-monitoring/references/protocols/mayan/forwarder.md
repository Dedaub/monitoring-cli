# Mayan Forwarder and Deposit Addresses — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche; NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the verified sources on Blockscout (`MayanForwarder2`, `MPSFactory`, `MPSSmartWallet`), the `mayan-finance/swap-sdk` (`addresses.ts`, `MayanForwarderArtifact`) and docs.mayan.finance (`resources/chains-contracts`, `integration/forwarder-contract`, `features/deposit-addresses`). Topic0 and selector values were recomputed as `keccak256(signature)` from the verified ABIs and matched against live logs, transaction selectors and deployed bytecode. Addresses were existence-checked with `eth_getCode`.
**Scope:** the Mayan entry contracts that sit in front of the bridge routes: the **Mayan Forwarder** (`MayanForwarder2`, "the single entry point for EVM swaps"), the **deposit-address** contracts (`MPSFactory` and the `MPSSmartWallet` clones), and the **Shuttle** contract that the Forwarder allows. None of them is a bridge by itself: each hands the funds to Swift, MCTP, Fast MCTP, the Wormhole swap or Shuttle in the same transaction. Robinhood Chain (4663) has none of them. Topics and selectors are chain-agnostic; addresses are network-specific.

The Forwarder holds no balance. It pulls the user's token (or takes `msg.value`), optionally swaps it through an allowed swap protocol into a "middle token", approves the Mayan protocol and calls it with the `protocolData` / `mayanData` calldata. It then emits one marker event. The marker names the Mayan protocol and carries its calldata, so the order parameters (for example the Swift order) can be decoded from it. **The Forwarder events are markers, not deposits**: the deposit is the protocol's own event or `Transfer` in the same transaction (for example `OrderCreated` of SwiftSource). Many orders do not use the Forwarder at all.

---

## 0. Contract families & versions

| Contract | Address (same on every listed chain) | Chains | Role | Upgradeable? |
|----------|--------------------------------------|--------|------|--------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | ETH, Base, Arb, OP, Poly, BNB, Avax | Entry router: `forwardEth`, `forwardERC20`, `swapAndForwardEth`, `swapAndForwardERC20`. Allow-lists: `mayanProtocols`, `swapProtocols`. Identical bytecode on all seven chains. | No (plain contract; guardian) |
| **MPSFactory** (deposit addresses, current) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 7 (all but Robinhood) | `deployWallet` deploys an `MPSSmartWallet` clone at a deterministic per-user address. `addresses.ts` of the swap SDK names it `MPS_EVM_FACTORY`; the only factory with `WalletDeployed` logs in the pinned window. | No (the wallets are EIP-1167 clones) |
| MPSSmartWallet implementation (current) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 7 (all but Robinhood) | Clone target of the current factory (`MPS_EVM_WALLET_IMPLEMENTATION`). | — |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 7 (all but Robinhood) | The factory on the docs page "Chains & Contracts" (verified 2026-08-03, before the SDK factory). Same ABI; 0 `WalletDeployed` logs in the pinned window. | No |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 7 (all but Robinhood) | Clone target of the docs factory. | — |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | 6 (not BNB, not Robinhood) | EIP-1967 proxy (133 B) that the Forwarder allows (`mayanProtocols` = true on Ethereum). The implementation (`0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d` on Ethereum, source not verified) has the SDK `ShuttleArtifact` selectors `initiate(bytes32,uint256,uint16,bytes)` and `batchMaxApprove(bytes)`. Its events are not documented; not covered further. | Yes (EIP-1967) |

The Forwarder's `mayanProtocols(address)` returns true on Ethereum for SwiftSource `0x40fFE85A28DC9993541449464d7529a922142960`, MayanSwift v1 `0xC38e4e6A15593f908255214653d3D947CA1c2338`, MayanCircle `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA`, FastMCTP `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741`, MayanSwap `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` and Shuttle `0xCbe9186a89db78714785765055E09dD6166e0833`; it returns false for SwiftDest. The verified constructor on Ethereum set two swap protocols, `0x111111125421cA6dc452d289314280a0f8842A65` and `0x5E18824Bb0e73BB9bd78E7B2D38a3289BcCdEe1D`, and the guardian `0x933E3922E04d47a466e60A20e486b372B64F1Ea8`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 MayanForwarder2 (markers of the entry; no parameter is indexed)

| topic0 | Event |
|--------|-------|
| `0xb8543d214cab9591941648db8d40126a163bfd0db4a865678320b921e1398043` | `ForwardedEth(address mayanProtocol, bytes protocolData)` — native input forwarded as `msg.value` to `mayanProtocol`. No amount field: read the call value (no ERC-20 row). |
| `0xbf150db6b4a14b084f7346b4bc300f552ce867afe55be27bce2d6b37e3307cda` | `ForwardedERC20(address token, uint256 amount, address mayanProtocol, bytes protocolData)` — ERC-20 input forwarded unchanged. |
| `0x7cbff921ae1f3ea71284120d2aabde13587df067f2bb5c831ea6e35d7a9242ac` | `SwapAndForwardedEth(uint256 amountIn, address swapProtocol, address middleToken, uint256 middleAmount, address mayanProtocol, bytes mayanData)` — native input swapped to `middleToken` first; `middleAmount` goes to the protocol. |
| `0x23278f58875126c795a4072b98b5851fe9b21cea19895b02a6224fefbb1e3298` | `SwapAndForwardedERC20(address tokenIn, uint256 amountIn, address swapProtocol, address middleToken, uint256 middleAmount, address mayanProtocol, bytes mayanData)` — ERC-20 input swapped to `middleToken` first. |
| `0xfe4e324d6c3c393853951b3712eb58370dd79d26cd12851f51a33161d31f3ee4` | `SwapAndForwarded(uint256 amount)` — declared in the verified source but **never emitted** (no `emit` statement); 0 logs on all eight chains in the pinned window. |

### 1.2 MPSFactory and MPSSmartWallet (deposit addresses)

| topic0 | Event |
|--------|-------|
| `0x067bdf7ecf1f9cd29cd0b7e78a2e8997f575f3f5e13f5f5570234dc11cff09fa` | `WalletDeployed(address indexed wallet, uint16 integratorId, bytes20 userId, uint16 destChain, bytes32 destWallet, bytes32 destToken)` — **status**: a deposit wallet is deployed (first use only). `destChain` is a Wormhole chain id; `destWallet` / `destToken` are the configured payout. No value moves in this event. |
| `0x88a7f0939efabccdd987f0bf5163ee7eda6ca2208ec1af4b34249da9ac6f6857` | `RescueRefunded(bytes32 indexed vmHash, address token, address recipient, uint256 amount)` — MPSSmartWallet: a refund out of a deposit wallet, authorized by a Wormhole VAA. |
| `0xb13b32bc2a176c59356771a7abd54726102a57a6a7e568e76aeff14a659b6e06` | `GovernanceExecuted(bytes32 indexed vmHash, uint8 action)` — admin (VAA-governed). |
| `0x7fa4284f8412f649540ea9a7e261349cd769528631813b29d6bbcaae07ae260f` | `ProtocolVerifierSet(address indexed mayanProtocol, address indexed verifier)` — admin. |
| `0x03580ee9f53a62b7cb409a2cb56f9be87747dd15017afc5cef6eef321e4fb2c5` | `RelayerAdded(address indexed relayer)` — admin: who may call `executeSwap` / `executeTransfer`. |
| `0x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b` | `RelayerRemoved(address indexed relayer)` — admin. |

### 1.3 Value row

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — user (or aggregator) → Forwarder → Mayan protocol; for deposit addresses: user → wallet, later wallet → Forwarder → Mayan protocol. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 MayanForwarder2

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb0f584ff` | `forwardEth(address mayanProtocol, bytes protocolData)` | payable. Emits `ForwardedEth`. |
| `0xe4269fc4` | `forwardERC20(address tokenIn, uint256 amountIn, (uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) permitParams, address mayanProtocol, bytes protocolData)` | payable. Pulls `tokenIn` (optional ERC-2612 permit). Emits `ForwardedERC20`. |
| `0xfa74fd43` | `swapAndForwardEth(uint256 amountIn, address swapProtocol, bytes swapData, address middleToken, uint256 minMiddleAmount, address mayanProtocol, bytes mayanData)` | payable. Emits `SwapAndForwardedEth`. |
| `0x30dedc57` | `swapAndForwardERC20(address tokenIn, uint256 amountIn, (uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) permitParams, address swapProtocol, bytes swapData, address middleToken, uint256 minMiddleAmount, address mayanProtocol, bytes mayanData)` | payable. Emits `SwapAndForwardedERC20`. |
| `0xa44382fe` | `setMayanProtocol(address mayanProtocol, bool enabled)` | Guardian only. **No event.** |
| `0x7fc920eb` | `setSwapProtocol(address swapProtocol, bool enabled)` | Guardian only. **No event.** |
| `0xf8a67a62` | `rescueToken(address token, uint256 amount, address to)` | Guardian only. **No event.** |
| `0xb25ea8fb` | `rescueEth(uint256 amount, address to)` | Guardian only. **No event.** |
| `0x2fcb4f04` | `changeGuardian(address newGuardian)` | Guardian only; step 1 of 2. |
| `0x459656ee` | `claimGuardian()` | Next guardian; step 2 of 2. |

Views: `mayanProtocols(address)` `0xaf56ca03`, `swapProtocols(address)` `0xffe80541`, `guardian()` `0x452a9320`.

### 2.2 MPSFactory and MPSSmartWallet

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x101e5857` | `deployWallet(uint16 integratorId, bytes20 userId, uint16 destChain, bytes32 destWallet, bytes32 destToken)` | Factory. Deploys the clone and emits `WalletDeployed`. |
| `0xae9f7a1f` | `executeGovernance(bytes encodedVm)` | Factory. VAA-governed admin (relayers, verifiers). Emits `GovernanceExecuted`. |
| `0x364fe3fd` | `executeSwap(address token, uint256 amount, uint256 feeAmount, address feeRecipient, bytes mayanCalldata)` | Wallet; relayer only. Pays the fee, then calls the Forwarder (a hard-coded constant, `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2`) with the wallet's funds. |
| `0x5c69e207` | `executeTransfer(uint256 amount, uint256 feeBps, address feeRecipient)` | Wallet; relayer only. Same-chain delivery to `destWallet`. |
| `0xe116a6e3` | `rescueRefund(bytes encodedVm)` | Wallet; relayer only, VAA-authorized. Emits `RescueRefunded`. |
| `0x24583b83` | `initialize(uint16 _integratorId, bytes20 _userId, uint16 _destChain, bytes32 _destWallet, bytes32 _destToken)` | Wallet; called once by the factory. |

### 2.3 Shuttle (SDK ABI; selectors present in the Ethereum implementation bytecode)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x43fc7da0` | `initiate(bytes32 recipient, uint256 overrideAmountIn, uint16 targetChain, bytes params)` | payable. Source leg of a Shuttle order (SDK quote type `SHUTTLE`). |
| `0xc97166c7` | `batchMaxApprove(bytes approvals)` | Approval helper. |

---

## 3. Addresses — Ethereum (chain ID 1, Wormhole chain ID 2)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on the other chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | 8,840 B (one code hash on all seven chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA). |
| **MPSFactory** (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 8,515 B. |
| MPSSmartWallet implementation (SDK) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 17,584 B. |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 8,592 B. |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 17,588 B. |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | 133-B EIP-1967 proxy; implementation `0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `ForwardedERC20` 331, `ForwardedEth` 1, `SwapAndForwardedERC20` 394, `SwapAndForwardedEth` 474, `SwapAndForwarded` 0; `WalletDeployed` 7 at the SDK factory and 0 at the docs factory.

## 4. Addresses — Base (chain ID 8453, Wormhole chain ID 30)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on the other chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | 8,840 B (one code hash on all seven chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA). |
| **MPSFactory** (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 8,515 B. |
| MPSSmartWallet implementation (SDK) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 17,584 B. |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 8,592 B. |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 17,588 B. |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | 133-B EIP-1967 proxy; implementation `0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `ForwardedERC20` 489, `ForwardedEth` 0, `SwapAndForwardedERC20` 346, `SwapAndForwardedEth` 342, `SwapAndForwarded` 0; `WalletDeployed` 0 at the SDK factory and 0 at the docs factory.

## 5. Addresses — Arbitrum One (chain ID 42161, Wormhole chain ID 23)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on the other chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | 8,840 B (one code hash on all seven chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA). |
| **MPSFactory** (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 8,515 B. |
| MPSSmartWallet implementation (SDK) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 17,584 B. |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 8,592 B. |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 17,588 B. |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | 133-B EIP-1967 proxy; implementation `0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `ForwardedERC20` 245, `ForwardedEth` 0, `SwapAndForwardedERC20` 65, `SwapAndForwardedEth` 113, `SwapAndForwarded` 0; `WalletDeployed` 0 at the SDK factory and 0 at the docs factory.

## 6. Addresses — Optimism (chain ID 10, Wormhole chain ID 24)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on the other chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | 8,840 B (one code hash on all seven chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA). |
| **MPSFactory** (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 8,515 B. |
| MPSSmartWallet implementation (SDK) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 17,584 B. |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 8,592 B. |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 17,588 B. |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | 133-B EIP-1967 proxy; implementation `0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `ForwardedERC20` 26, `ForwardedEth` 0, `SwapAndForwardedERC20` 221, `SwapAndForwardedEth` 35, `SwapAndForwarded` 0; `WalletDeployed` 0 at the SDK factory and 0 at the docs factory.

## 7. Addresses — Polygon PoS (chain ID 137, Wormhole chain ID 5)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on the other chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | 8,840 B (one code hash on all seven chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA). |
| **MPSFactory** (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 8,515 B. |
| MPSSmartWallet implementation (SDK) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 17,584 B. |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 8,592 B. |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 17,588 B. |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | 133-B EIP-1967 proxy; implementation `0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `ForwardedERC20` 181, `ForwardedEth` 0, `SwapAndForwardedERC20` 133, `SwapAndForwardedEth` 61, `SwapAndForwarded` 0; `WalletDeployed` 0 at the SDK factory and 0 at the docs factory.

## 8. Addresses — BNB Smart Chain (chain ID 56, Wormhole chain ID 4)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on the other chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | 8,840 B (one code hash on all seven chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA). |
| **MPSFactory** (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 8,515 B. |
| MPSSmartWallet implementation (SDK) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 17,584 B. |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 8,592 B. |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 17,588 B. |

Shuttle `0xCbe9186a89db78714785765055E09dD6166e0833` is **not deployed** on BNB Smart Chain (`eth_getCode` = `0x`).

Pinned window 2026-09-28 00:00–12:00 UTC: `ForwardedERC20` 992, `ForwardedEth` 0, `SwapAndForwardedERC20` 541, `SwapAndForwardedEth` 715, `SwapAndForwarded` 0; `WalletDeployed` 0 at the SDK factory and 0 at the docs factory.

## 9. Addresses — Avalanche C-Chain (chain ID 43114, Wormhole chain ID 6)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on the other chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanForwarder2** | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | 8,840 B (one code hash on all seven chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA). |
| **MPSFactory** (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | 8,515 B. |
| MPSSmartWallet implementation (SDK) | `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1` | 17,584 B. |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | 8,592 B. |
| MPSSmartWallet implementation (docs) | `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C` | 17,588 B. |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | 133-B EIP-1967 proxy; implementation `0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `ForwardedERC20` 51, `ForwardedEth` 0, `SwapAndForwardedERC20` 12, `SwapAndForwardedEth` 34, `SwapAndForwarded` 0; `WalletDeployed` 0 at the SDK factory and 0 at the docs factory.

---

## 10. Cross-chain summary

| Chain | EVM ID | Wormhole ID | MayanForwarder2 `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | MPSFactory (SDK) `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | MPSFactory (docs) `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | Shuttle `0xCbe9186a89db78714785765055E09dD6166e0833` |
|-------|-------:|------------:|:--:|:--:|:--:|:--:|
| Ethereum | 1 | 2 | ✅ | ✅ | ✅ | ✅ |
| Base | 8453 | 30 | ✅ | ✅ | ✅ | ✅ |
| Arbitrum One | 42161 | 23 | ✅ | ✅ | ✅ | ✅ |
| Optimism | 10 | 24 | ✅ | ✅ | ✅ | ✅ |
| Polygon PoS | 137 | 5 | ✅ | ✅ | ✅ | ✅ |
| BNB Smart Chain | 56 | 4 | ✅ | ✅ | ✅ | ❌ |
| Avalanche C-Chain | 43114 | 6 | ✅ | ✅ | ✅ | ✅ |
| **Robinhood Chain** | 4663 | — | ❌ | ❌ | ❌ | ❌ |

The docs "Chains & Contracts" page says that the Forwarder "is deployed at the same address on every supported EVM chain"; its bytecode hash is identical on all seven chains above. Deposit addresses accept deposits on Ethereum, BSC, Polygon, Avalanche, Arbitrum, Optimism, Base and Monad (docs "Deposit Addresses").

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Admin authority |
|----------|---------|-----------|-----------------|
| **MayanForwarder2** | **Not a proxy.** | EIP-1967 slots empty; 8,840 B on every chain. | `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA on all seven chains). Controls the two allow-lists and the rescue functions; no event. |
| **MPSFactory** (both) | Not a proxy. | Slots empty. | Governed by Wormhole VAAs (`executeGovernance`; refund emitter chain 1, emitter `0xde11515a636e60deb228387196f7b07e408fce05a82b2fa0a1627598ce76d94e` per the verified constructor). Emits `GovernanceExecuted` and the relayer / verifier events. |
| MPSSmartWallet (per user) | **EIP-1167 clone** of the implementation. | Runtime `0x363d3d373d3d3d363d73<implementation>5af4…`. | None; relayers listed by the factory may call `executeSwap` / `executeTransfer` / `rescueRefund`. |
| **Shuttle** | **EIP-1967 proxy** (133 B). | Implementation slot = `0x39e834f0243be4c30dfcc2cfd9a15cc484cc383d` on every chain where present. | Upgradeable. EIP-1967 admin slot = `0x14dad8a1c02a9457591e6468cfa34c5cec4ea14d` on Ethereum (an EOA, nonce 2). Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` and `AdminChanged`. |

---

## 12. Detection invariants & gotchas

1. **Forwarder events are markers, not deposits.** Count the deposit once, at the Mayan protocol (for example `OrderCreated` of SwiftSource, the `DepositForBurn` of MCTP / Fast MCTP, or the MayanSwap Wormhole message). The Forwarder marker only tells you which protocol received the funds (`mayanProtocol`) and carries the protocol calldata (`protocolData` / `mayanData`), which holds the order parameters.
2. **The Forwarder's caller is often not the user.** In the Ethereum samples the Forwarder was called by the LI.FI diamond `0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae` (`ForwardedERC20`, `ForwardedEth`) and through an ERC-4337 EntryPoint (`SwapAndForwardedEth`). Follow the transfers of the transaction back to the user.
3. **`ForwardedEth` has no amount field.** The forwarded value is the call value to the Mayan protocol (for a Wormhole swap it becomes WETH inside the Token Bridge). No ERC-20 row exists for it.
4. **`SwapAndForwarded(uint256)` never fires.** It is declared in the verified source but has no `emit`; a monitor keyed on it sees nothing.
5. **In a swap-and-forward, two amounts matter.** `amountIn` of `tokenIn` left the user; `middleAmount` of `middleToken` reached the Mayan protocol. The Forwarder writes `middleAmount` into the amount field of the calldata before it calls the protocol, but the event logs `mayanData` as received, so decode the amount from `middleAmount`. `swapAndForwardERC20` returns any leftover `tokenIn` to `msg.sender`.
6. **Deposit addresses hide the user.** A deposit is a plain `Transfer` (or native send) from the user to a counterfactual `MPSSmartWallet` address, with no event. Later a relayer deploys the wallet (`WalletDeployed`, first use only) and calls `executeSwap`, which sends the wallet's funds through the Forwarder (a hard-coded constant in the wallet) into a Mayan protocol. The Mayan order then shows the wallet, not the user, as the sender. `WalletDeployed.destChain` / `destWallet` / `destToken` give the configured payout.
7. **Two deposit-address factories exist.** The docs name `0xfa829c5E1efc9d788280a8213cb0713be5474F7d`; the SDK names `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88`. Both are live on seven chains with the same ABI. In the pinned window only the SDK factory deployed wallets (7 on Ethereum). Index both.
8. **The allow-lists change silently.** `setMayanProtocol` `0xa44382fe` and `setSwapProtocol` `0x7fc920eb` emit no event; a new protocol address behind the Forwarder appears only as a transaction with one of these selectors. The same holds for `rescueToken` `0xf8a67a62` and `rescueEth` `0xb25ea8fb`.
9. **Shuttle is a separate Mayan route** (SDK quote type `SHUTTLE`, entry `initiate(bytes32,uint256,uint16,bytes)`). It is allowed by the Forwarder, but its source is not verified and its events are not documented; treat transfers into it as Mayan deposits of unknown structure.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_FORWARDED_ETH              = '\xb8543d214cab9591941648db8d40126a163bfd0db4a865678320b921e1398043'
TOPIC_FORWARDED_ERC20            = '\xbf150db6b4a14b084f7346b4bc300f552ce867afe55be27bce2d6b37e3307cda'
TOPIC_SWAP_AND_FORWARDED_ETH     = '\x7cbff921ae1f3ea71284120d2aabde13587df067f2bb5c831ea6e35d7a9242ac'
TOPIC_SWAP_AND_FORWARDED_ERC20   = '\x23278f58875126c795a4072b98b5851fe9b21cea19895b02a6224fefbb1e3298'
TOPIC_SWAP_AND_FORWARDED         = '\xfe4e324d6c3c393853951b3712eb58370dd79d26cd12851f51a33161d31f3ee4'
TOPIC_MPS_WALLET_DEPLOYED        = '\x067bdf7ecf1f9cd29cd0b7e78a2e8997f575f3f5e13f5f5570234dc11cff09fa'
TOPIC_MPS_RESCUE_REFUNDED        = '\x88a7f0939efabccdd987f0bf5163ee7eda6ca2208ec1af4b34249da9ac6f6857'
TOPIC_MPS_GOVERNANCE_EXECUTED    = '\xb13b32bc2a176c59356771a7abd54726102a57a6a7e568e76aeff14a659b6e06'
TOPIC_MPS_PROTOCOL_VERIFIER_SET  = '\x7fa4284f8412f649540ea9a7e261349cd769528631813b29d6bbcaae07ae260f'
TOPIC_MPS_RELAYER_ADDED          = '\x03580ee9f53a62b7cb409a2cb56f9be87747dd15017afc5cef6eef321e4fb2c5'
TOPIC_MPS_RELAYER_REMOVED        = '\x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors (chain-agnostic) =====
SEL_FORWARD_ETH                  = '\xb0f584ff'
SEL_FORWARD_ERC20                = '\xe4269fc4'
SEL_SWAP_AND_FORWARD_ETH         = '\xfa74fd43'
SEL_SWAP_AND_FORWARD_ERC20       = '\x30dedc57'
SEL_FORWARDER_SET_MAYAN_PROTOCOL = '\xa44382fe'
SEL_FORWARDER_SET_SWAP_PROTOCOL  = '\x7fc920eb'
SEL_MAYAN_RESCUE_TOKEN           = '\xf8a67a62'
SEL_MAYAN_RESCUE_ETH             = '\xb25ea8fb'
SEL_MAYAN_CHANGE_GUARDIAN        = '\x2fcb4f04'
SEL_MPS_DEPLOY_WALLET            = '\x101e5857'
SEL_MPS_EXECUTE_GOVERNANCE       = '\xae9f7a1f'
SEL_MPS_EXECUTE_SWAP             = '\x364fe3fd'
SEL_MPS_EXECUTE_TRANSFER         = '\x5c69e207'
SEL_MPS_RESCUE_REFUND            = '\xe116a6e3'
SEL_SHUTTLE_INITIATE             = '\x43fc7da0'

-- ===== Addresses (network-specific; the same literal address on every chain where present) =====
-- Ethereum (1)
ETH_MAYAN_FORWARDER         = '\x337685fdab40d39bd02028545a4ffa7d287cc3e2'
ETH_MPS_FACTORY             = '\x28d8f4513d5d74d7c43ca7fe111cac906dcd2e88'
ETH_MPS_WALLET_IMPL         = '\xa05b711213b99232d1a6e42d6e5f685df5b0a0a1'
ETH_MPS_FACTORY_DOCS        = '\xfa829c5e1efc9d788280a8213cb0713be5474f7d'
ETH_MPS_WALLET_IMPL_DOCS    = '\xfd7188cf0ac99705cc8c595a1d198c2a43df467c'
ETH_MAYAN_SHUTTLE           = '\xcbe9186a89db78714785765055e09dd6166e0833'
ETH_MAYAN_GUARDIAN_EOA      = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
ETH_MAYAN_SHUTTLE_ADMIN_EOA = '\x14dad8a1c02a9457591e6468cfa34c5cec4ea14d'
-- Base (8453)
BASE_MAYAN_FORWARDER        = '\x337685fdab40d39bd02028545a4ffa7d287cc3e2'
BASE_MPS_FACTORY            = '\x28d8f4513d5d74d7c43ca7fe111cac906dcd2e88'
BASE_MPS_WALLET_IMPL        = '\xa05b711213b99232d1a6e42d6e5f685df5b0a0a1'
BASE_MPS_FACTORY_DOCS       = '\xfa829c5e1efc9d788280a8213cb0713be5474f7d'
BASE_MPS_WALLET_IMPL_DOCS   = '\xfd7188cf0ac99705cc8c595a1d198c2a43df467c'
BASE_MAYAN_SHUTTLE          = '\xcbe9186a89db78714785765055e09dd6166e0833'
BASE_MAYAN_GUARDIAN_EOA     = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Arbitrum One (42161)
ARB_MAYAN_FORWARDER         = '\x337685fdab40d39bd02028545a4ffa7d287cc3e2'
ARB_MPS_FACTORY             = '\x28d8f4513d5d74d7c43ca7fe111cac906dcd2e88'
ARB_MPS_WALLET_IMPL         = '\xa05b711213b99232d1a6e42d6e5f685df5b0a0a1'
ARB_MPS_FACTORY_DOCS        = '\xfa829c5e1efc9d788280a8213cb0713be5474f7d'
ARB_MPS_WALLET_IMPL_DOCS    = '\xfd7188cf0ac99705cc8c595a1d198c2a43df467c'
ARB_MAYAN_SHUTTLE           = '\xcbe9186a89db78714785765055e09dd6166e0833'
ARB_MAYAN_GUARDIAN_EOA      = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Optimism (10)
OP_MAYAN_FORWARDER          = '\x337685fdab40d39bd02028545a4ffa7d287cc3e2'
OP_MPS_FACTORY              = '\x28d8f4513d5d74d7c43ca7fe111cac906dcd2e88'
OP_MPS_WALLET_IMPL          = '\xa05b711213b99232d1a6e42d6e5f685df5b0a0a1'
OP_MPS_FACTORY_DOCS         = '\xfa829c5e1efc9d788280a8213cb0713be5474f7d'
OP_MPS_WALLET_IMPL_DOCS     = '\xfd7188cf0ac99705cc8c595a1d198c2a43df467c'
OP_MAYAN_SHUTTLE            = '\xcbe9186a89db78714785765055e09dd6166e0833'
OP_MAYAN_GUARDIAN_EOA       = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Polygon PoS (137)
POLY_MAYAN_FORWARDER        = '\x337685fdab40d39bd02028545a4ffa7d287cc3e2'
POLY_MPS_FACTORY            = '\x28d8f4513d5d74d7c43ca7fe111cac906dcd2e88'
POLY_MPS_WALLET_IMPL        = '\xa05b711213b99232d1a6e42d6e5f685df5b0a0a1'
POLY_MPS_FACTORY_DOCS       = '\xfa829c5e1efc9d788280a8213cb0713be5474f7d'
POLY_MPS_WALLET_IMPL_DOCS   = '\xfd7188cf0ac99705cc8c595a1d198c2a43df467c'
POLY_MAYAN_SHUTTLE          = '\xcbe9186a89db78714785765055e09dd6166e0833'
POLY_MAYAN_GUARDIAN_EOA     = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- BNB Smart Chain (56)
BNB_MAYAN_FORWARDER         = '\x337685fdab40d39bd02028545a4ffa7d287cc3e2'
BNB_MPS_FACTORY             = '\x28d8f4513d5d74d7c43ca7fe111cac906dcd2e88'
BNB_MPS_WALLET_IMPL         = '\xa05b711213b99232d1a6e42d6e5f685df5b0a0a1'
BNB_MPS_FACTORY_DOCS        = '\xfa829c5e1efc9d788280a8213cb0713be5474f7d'
BNB_MPS_WALLET_IMPL_DOCS    = '\xfd7188cf0ac99705cc8c595a1d198c2a43df467c'
BNB_MAYAN_GUARDIAN_EOA      = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Avalanche C-Chain (43114)
AVAX_MAYAN_FORWARDER        = '\x337685fdab40d39bd02028545a4ffa7d287cc3e2'
AVAX_MPS_FACTORY            = '\x28d8f4513d5d74d7c43ca7fe111cac906dcd2e88'
AVAX_MPS_WALLET_IMPL        = '\xa05b711213b99232d1a6e42d6e5f685df5b0a0a1'
AVAX_MPS_FACTORY_DOCS       = '\xfa829c5e1efc9d788280a8213cb0713be5474f7d'
AVAX_MPS_WALLET_IMPL_DOCS   = '\xfd7188cf0ac99705cc8c595a1d198c2a43df467c'
AVAX_MAYAN_SHUTTLE          = '\xcbe9186a89db78714785765055e09dd6166e0833'
AVAX_MAYAN_GUARDIAN_EOA     = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Robinhood Chain (4663): none of these contracts
```

---

## 14. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified ABIs of `MayanForwarder2` (Blockscout, compiler 0.8.4) and `MPSFactory` / `MPSSmartWallet` (0.8.28, both factories). The factory and wallet selectors were also found as PUSH4 in the deployed bytecode on Ethereum; the Shuttle selectors (SDK `ShuttleArtifact`) were found in the implementation bytecode. The Forwarder topic0 values were matched against decoded live logs.
- **Addresses:** from the swap SDK `addresses.ts` (`MAYAN_FORWARDER_CONTRACT`, `MPS_EVM_FACTORY`, `MPS_EVM_WALLET_IMPLEMENTATION`), docs.mayan.finance "Chains & Contracts" (Forwarder, docs factory and wallet implementation) and the Forwarder's `mayanProtocols(address)` (Shuttle). Every address was existence-checked with `eth_getCode` on all eight chains, and the EIP-1967 slots were read.
- **Samples read in full (Ethereum):** `0x042c389d0c6bd1f2ab8d70c584bc9ef3ca5634de33880e8c01c38980e49cdef9` (`ForwardedERC20` into SwiftSource, via LI.FI), `0xcbdd595d35fa2f6e14581f7c605ab78efbecde570d9ebd0a59dc8f5d1ee76a0a` (`ForwardedEth` into MayanSwap, via LI.FI), `0xa8ef04c304e9aaab1a670403d5745bf9e04f50163a9f6a85cf0602283b25bad2` (`SwapAndForwardedEth` into SwiftSource, via an ERC-4337 EntryPoint), `0xb12a5e0548c8a0d179bc1992a550099d4454cce0655df963aa3ff59d49f5c1bf` (`deployWallet` → `WalletDeployed`).
- **Activity:** pinned 12-hour window 2026-09-28 00:00–12:00 UTC, `eth_getLogs` per emitter (counts in §3–§9). A 0 is a measurement of this window only.

Authoritative sources (opened for this document):
- Docs — [Chains & Contracts](https://docs.mayan.finance/resources/chains-contracts) · [Forwarder Contract](https://docs.mayan.finance/integration/forwarder-contract) · [Deposit Addresses](https://docs.mayan.finance/features/deposit-addresses) (source `mayan-finance/docs`)
- Repository — [mayan-finance/swap-sdk](https://github.com/mayan-finance/swap-sdk) (`src/addresses.ts`, `src/evm/MayanForwarderArtifact.ts`, `src/evm/ShuttleArtifact.ts`)
- Verified sources — `https://eth.blockscout.com/api/v2/smart-contracts/0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` (MayanForwarder2) · `https://eth.blockscout.com/api/v2/smart-contracts/0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` and `https://eth.blockscout.com/api/v2/smart-contracts/0xfa829c5E1efc9d788280a8213cb0713be5474F7d` (MPSFactory) · `https://eth.blockscout.com/api/v2/smart-contracts/0xCbe9186a89db78714785765055E09dD6166e0833` (Shuttle proxy; not verified)


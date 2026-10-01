# Mayan — reference index

**Mayan** (mayan.finance) is a cross-chain swap protocol. Drivers (solvers) compete in auctions, mostly on Solana, and deliver the user's output on the destination chain. Its EVM contracts form four product lines, plus entry contracts in front of them. Every product has its own events, keys and chain set, so each has its own file.

**Status:** all constants verified on 2026-09-29 against live RPC on the eight target chains, the verified sources on Blockscout, the `mayan-finance/swap-sdk` repository and docs.mayan.finance. Topic0 and selector values were recomputed as `keccak256(signature)`; addresses were existence-checked with `eth_getCode`.

| File | Product | Contracts | Chains (of the 8) | Link key source → destination | Pinned window (2026-09-28 00:00–12:00 UTC) |
|------|---------|-----------|-------------------|-------------------------------|---------------------------------------------|
| [swift.md](swift.md) | **Swift v2** (intent, driver pays first) and Swift v1 (retired) | SwiftSource `0x40fFE85A28DC9993541449464d7529a922142960`, SwiftDest `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe`, MayanSwift v1 `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 7: ETH, Base, Arb, OP, Poly, BNB, Avax | Order hash `key`, on chain on both sides (all five Swift events) | Busiest Mayan route: 4,544 `OrderCreated` and 3,819 `OrderFulfilled` over the seven chains; v1: 0 |
| [mctp.md](mctp.md) | **MCTP** (CCTP v1) and **Fast MCTP** (CCTP v2) | MayanCircle `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA`, FastMCTP `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | 6: ETH, Base, Arb, OP, Poly, Avax (not BNB) | CCTP (source domain, nonce): v1 on chain on both sides; v2 nonce only on the destination | Swap payouts: MCTP 17 `OrderFulfilled`, Fast MCTP 230 `OrderFulfilled` |
| [wh-swap.md](wh-swap.md) | **Wormhole swap** (Token Bridge via Solana) | MayanSwap `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4`; on Base `0x11AA521C888d84f374B63823d9b873CAa3591f55` | 7 | Wormhole VAA key `(emitterChainId, emitterAddress, sequence)` of the last Token Bridge hop; EVM-to-EVM goes through Solana | 5 `Redeemed` (Ethereum only) |
| [forwarder.md](forwarder.md) | **Entry contracts**: Forwarder, deposit addresses (MPS), Shuttle | MayanForwarder2 `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2`, MPSFactory `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` (+ docs factory), Shuttle `0xCbe9186a89db78714785765055E09dD6166e0833` | 7 (Shuttle: 6, not BNB) | None: markers of the entry, in the same transaction as the product's source leg | Forwarder markers: 2,315 `ForwardedERC20`, 1,712 `SwapAndForwardedERC20`, 1,774 `SwapAndForwardedEth`, 1 `ForwardedEth` |

**Robinhood Chain (4663): no Mayan contract.** `eth_getCode` returns `0x` (nonce 0) at every Mayan address above, Robinhood Chain is not in Mayan's chain config (`https://sia.mayan.finance/v10/init`), and no Mayan event appeared on it in the pinned window.

## Cross-cutting facts (read before indexing any file)

1. **Mayan uses Wormhole chain ids, not EVM chain ids**, in every order field (`destChainId`, `srcChainId`, `destChain`, `targetChain`, `WalletDeployed.destChain`).

   | Chain | EVM chain id | Wormhole chain id | CCTP domain (MCTP / Fast MCTP) |
   |-------|-------------:|------------------:|-------------------------------:|
   | Ethereum | 1 | 2 | 0 |
   | BNB Smart Chain | 56 | 4 | none for USDC (no MCTP, no Fast MCTP) |
   | Polygon PoS | 137 | 5 | 7 |
   | Avalanche C-Chain | 43114 | 6 | 1 |
   | Arbitrum One | 42161 | 23 | 3 |
   | Optimism | 10 | 24 | 2 |
   | Base | 8453 | 30 | 6 |
   | Robinhood Chain | 4663 | none (not a Mayan chain) | — |
   | Solana (counterparty) | — | 1 | 5 |
   | Sui (counterparty) | — | 21 | 8 |

   Other Mayan chains outside the eight: Linea 38, Unichain 44, HyperEVM 47, Monad 48, Fogo 51, HyperCore 65000 (docs "Chains & Contracts"). The Wormhole ids were checked on chain: `SwiftSource.emitters(id)` on Ethereum returns SwiftDest for ids 2, 4, 5, 6, 23, 24 and 30, and a Solana emitter for id 1. The CCTP domains were checked with `MayanCircle.getDomain(id)` on Ethereum (1→5, 5→7, 6→1, 21→8, 23→3, 24→2, 30→6; id 4 reverts; `localDomain()` = 0).
2. **One address per contract on every chain**, except MayanSwap on Base. The code hash still differs per chain for most contracts (constructor immutables), so match on the address and size, not the hash.
3. **Event names repeat with different types.** `OrderFulfilled` / `OrderRefunded` exist in three versions with three topic0 values each: Swift `(bytes32, …)`, MCTP `(uint32, uint64, uint256)`, Fast MCTP `(uint32, bytes32, uint256)`. Swift v1 and v2 share all five topic0 values. Always filter on the emitter too.
4. **Almost no Mayan parameter is indexed.** Only `Redeemed` (MayanSwap), the MPSFactory events and `RescueRefunded` (MPSSmartWallet) have indexed fields. Keys, amounts and ids are in the data.
5. **Where the Mayan event sits.** Swift has events on both chains. MCTP, Fast MCTP and the Wormhole swap have **no Mayan event on the source chain**: detect their source leg with the CCTP `DepositForBurn` (`depositor` = MayanCircle / FastMCTP) or the Wormhole `LogMessagePublished` (`sender` = MayanSwap). The Forwarder events are entry markers, not deposits.
6. **Refund does not always mean "back to the source".** Swift `OrderRefunded` returns the input to the trader on the source chain. MCTP and Fast MCTP `OrderRefunded` deliver USDC to the recipient **on the destination chain** (the swap was not filled).
7. **Admin model.** Each contract has a `guardian` (two-step `changeGuardian` + `claimGuardian`), and every admin setter (`setPause`, `setFeeManager`, `setEmitters`, `setMayanProtocol`, `rescueToken`, …) emits **no event**. Watch the selectors in transactions instead (each file lists them). The exception is MPSFactory: Wormhole VAAs govern it, and it emits `GovernanceExecuted`, `RelayerAdded`, `RelayerRemoved` and `ProtocolVerifierSet`. Guardians on Ethereum: Swift v2 `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; MCTP, Fast MCTP and the Forwarder `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (an EOA on all seven chains); Swift v1 `0x95d50ebee133c14e2355c7a72b254b3b6eeed6bc`. No Mayan contract is an upgradeable proxy, except Shuttle (EIP-1967); the deposit wallets are EIP-1167 clones.
8. **Drivers and relayers are ordinary addresses.** In the samples read, one address (`0x754dcfb2861547015b221e963b4133a71dbdc024`) filled Swift orders on Ethereum, received the unlocked escrow, and also moved funds through Fast MCTP and the Wormhole swap; another (`0x04d9634df20aa66b23f114d37c45fa6c6ab76d56`) submitted Swift refunds and cancels and MCTP / Fast MCTP fills. Neither list is official.

## Presence matrix (checked with `eth_getCode` on 2026-09-29)

| Contract | Address | ETH | Base | Arb | OP | Poly | BNB | Avax | Robinhood |
|----------|---------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| SwiftSource (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| SwiftDest (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| MayanCircle (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| FastMCTP | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| MayanSwap | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| MayanSwap (Base) | `0x11AA521C888d84f374B63823d9b873CAa3591f55` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MayanForwarder2 | `0x337685fdaB40D39bd02028545a4FfA7D287cC3E2` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| MPSFactory (SDK) | `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| MPSFactory (docs) | `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Shuttle | `0xCbe9186a89db78714785765055E09dD6166e0833` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |

## Discrepancies between the official sources and the chain

- The docs MCTP table lists BSC, but MayanCircle has no code on BNB Chain (and CCTP v1 has no BNB domain).
- The Mayan chain config (`sia.mayan.finance/v10/init`) gives `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` as the Base `mayanContractAddress`; that address has no code on Base. The docs give `0x11AA521C888d84f374B63823d9b873CAa3591f55`, which has the MayanSwap selectors.
- The docs list the deposit-address factory `0xfa829c5E1efc9d788280a8213cb0713be5474F7d` (wallet implementation `0xFD7188cf0Ac99705Cc8c595a1d198C2a43df467C`); the swap SDK `addresses.ts` lists `0x28D8f4513D5d74d7c43ca7Fe111caC906dcd2e88` (implementation `0xA05b711213b99232d1a6E42d6E5F685dF5B0a0A1`). Both exist on seven chains; only the SDK factory had `WalletDeployed` logs in the pinned window.
- The SDK Swift v2 ABI lists `unlockBatch(bytes,uint16[])` and `createOrderWithEth`; the verified SwiftSource has neither (it has `unlockCompressedBatch`, and ETH input is locked as WETH). The files follow the verified sources.

Sources: [docs.mayan.finance](https://docs.mayan.finance) (source `mayan-finance/docs`: `resources/chains-contracts.mdx`, `architecture/swift.mdx`, `architecture/mctp.mdx`, `architecture/wh-swap.mdx`, `integration/forwarder-contract.mdx`, `features/deposit-addresses.mdx`) · [mayan-finance/swap-sdk](https://github.com/mayan-finance/swap-sdk) (`src/addresses.ts`, `src/evm/*Artifact.ts`) · [mayan-finance/example-tx-parser](https://github.com/mayan-finance/example-tx-parser) · Mayan chain config `https://sia.mayan.finance/v10/init` · verified sources via `https://eth.blockscout.com/api/v2/smart-contracts/<address>`.

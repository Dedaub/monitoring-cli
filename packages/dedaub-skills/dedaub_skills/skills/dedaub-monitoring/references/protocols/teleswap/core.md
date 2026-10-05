# TeleSwap (TeleportDAO) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism connectors; Polygon and BNB home chains; NOT Avalanche, NOT Robinhood, NOT Arc)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the official contract list `TeleportDAO/teleswap-cli` (`assets/config/contracts.json`, from `@teleportdao/configs@4.1.0`), the verified sources on the Blockscout explorers (`EthConnectorLogic`, `PolyConnectorLogic`, `CcTransferRouterLogic`, `CcExchangeRouterLogic`, `BurnRouterLogic`, `LockersManagerLogic`, `BitcoinRelay`, `TeleBTCLogic`) and sample receipts. Every topic0 and selector was recomputed as `keccak256(signature)` from those verified ABIs. Every address was existence-checked with `eth_getCode`; proxy implementations and admins were read from the EIP-1967 slots. **Re-checked 2026-10-05:** all four EthConnectors, both PolyConnectors and the BNB BurnRouter were upgraded (Ethereum and Polygon on 2026-10-04; the others observed by 2026-10-05; new implementations in §3 to §6); the new connector events and functions (the filler path) are in §1 and §2.
**Scope:** TeleSwap, the Bitcoin bridge of TeleportDAO. Two layers: (1) the **home chains** Polygon PoS (137) and BNB Smart Chain (56), where teleBTC is minted and burned against Bitcoin through the Bitcoin light-client relay, the lockers and the routers; (2) the **EVM connectors** on Ethereum (1), Base (8453), Arbitrum One (42161) and Optimism (10), which move a user's tokens to a home chain over Across to swap them into BTC, and deliver BTC-funded swaps back. **Avalanche C-Chain (43114), Robinhood Chain (4663) and Arc (5042) have no TeleSwap contract.** Topics and selectors are chain-agnostic. Addresses are network-specific.

TeleSwap keeps BTC with **lockers**: operators that hold BTC on Bitcoin and post collateral on the home chain. A BTC deposit to a locker's Bitcoin script is proven to the home chain through the `BitcoinRelay` light client; the `CcTransferRouter` then mints teleBTC (`NewWrap`), or the `CcExchangeRouter` mints and swaps it (`NewWrapAndSwapV2`). A withdrawal to Bitcoin burns teleBTC through the `BurnRouter` (`NewUnwrap`); the locker pays on Bitcoin, and the proof of that payment closes the request (`PaidUnwrap`, with the Bitcoin transaction id).

Three facts to know before you index:

1. **An EVM connector does not hold the value.** `swapAndUnwrap*` on the connector emits `MsgSent` and, in the same transaction, makes an Across `depositV3` to the home chain's PolyConnector. The Across SpokePool emits `FundsDeposited` in that transaction, with the connector's `acrossAdmin` EOA `0x144c5fb302dbaa789fc59bbec301169eaa56c5fc` as the depositor. **The same value is visible to an Across monitor: count it once.**
2. **The link key is on chain on every hop.** EVM to BTC: `(source chain id, uniqueCounter)` from `MsgSent` equals `(chainId, uniqueCounter)` in `MsgReceived` and `NewSwapAndUnwrap*` on the home chain; the Across leg joins on `(originChainId, depositId)`; the Bitcoin payout joins on `(lockerTargetAddress, requestIdOfLocker)` from `NewUnwrap` to `PaidUnwrap`, which carries the Bitcoin transaction id. BTC to EVM: the Bitcoin transaction id (`bitcoinTxId`) links `NewWrap` / `NewWrapAndSwapV2` to `WrappedAndSwappedToDestChain` on the destination connector.
3. **One EOA admin controls every upgrade.** Every TeleSwap proxy on every chain (connectors, routers, lockers, teleBTC) has the EIP-1967 admin `0x4565ae5c90e52c058410fc7f05711ffed9b6e62a` and the `owner()` `0x24004f4f6d2e75b039d528e82b100355d8b1d4fb`; both are EOAs.

---

## 0. Contract families & versions

| Contract | Chains | Role | Proxy? |
|----------|--------|------|--------|
| **EthConnector** (`EthConnectorProxy` + `EthConnectorLogic`) | Ethereum, Base, Arbitrum, Optimism (also Unichain outside the eight) | EVM entry and exit: `swapAndUnwrap*` sends the user's tokens to a home chain over Across (`MsgSent`); `handleV3AcrossMessage` receives Across fills for BTC-to-EVM swaps and refunds (`MsgReceived`, `WrappedAndSwappedToDestChain`, `SwappedBackAndRefundedToSourceChain`). | Transparent proxy (EIP-1967, EOA admin) |
| **PolyConnector** (`PolyConnectorProxy` + `PolyConnectorLogic`) | Polygon, BNB | Home-chain side of the connector: receives Across fills (`MsgReceived`), swaps to teleBTC and calls the BurnRouter (`NewSwapAndUnwrap*`), or sends the funds back (`WithdrawnFundsToSourceChain*`). | Transparent proxy |
| **CcTransferRouter** | Polygon, BNB | BTC to teleBTC: verifies a Bitcoin deposit through the relay and mints teleBTC (`NewWrap`; `NewWrapV2` sends it over the teleBTC LayerZero OFT to `lzDstEid`). | Transparent proxy |
| **CcExchangeRouter** | Polygon, BNB | BTC to any token: mints teleBTC and swaps it (`NewWrapAndSwapV2`); for another chain, bridges over Across to the destination connector; fillers can front the payout (`RequestFilledV2`, `FillerRefunded`). | Transparent proxy |
| **BurnRouter** | Polygon, BNB | teleBTC to BTC: burns teleBTC and records a payout request for a locker (`NewUnwrap`); proof of the Bitcoin payment (`PaidUnwrap`); disputes and slashing. | Transparent proxy |
| **LockersManager** (`LockersProxy`) | Polygon, BNB | Locker registry and collateral; the only teleBTC minter and burner (`MintByLocker`, `BurnByLocker`, `LockerSlashed`, `LockerLiquidated`). | Transparent proxy |
| **teleBTC** (`TeleBTCProxy` + `TeleBTCLogic`) | Polygon, BNB | The wrapped BTC token (8 decimals): `Mint`, `Burn`, blacklist, mint limit. | Transparent proxy |
| **BitcoinRelay** | Polygon, BNB | Bitcoin light client (block headers; `BlockAdded`, `BlockFinalized`). | Polygon: not a proxy; BNB: proxy |
| Price oracle, DEX connectors | Polygon, BNB | Swap helpers used by the routers. | Mixed |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 EthConnector (Ethereum, Base, Arbitrum, Optimism)

| topic0 | Event |
|--------|-------|
| `0xd953c900c00c8d83f745d17aa6ce067c29cb0fdd7c3dda8dd5aee0e79feb850a` | `MsgSent(uint256 uniqueCounter, bytes data, address sourceChainInputToken, uint256 amount, int64 relayerFeePercentage)` |
| `0xfae1fd145a544fd4b9a3f59113a4133d16b3cc0e015c89e90755bbe0ce06377f` | `MsgSentRune(uint256 uniqueCounter, bytes data, address sourceChainInputToken, uint256 amount, int64 relayerFeePercentage)` |
| `0xd8883c6af9aa96506569d2db74cafb52037a26374320a8aeaf9fd5cd7df3d228` | `MsgReceived(string functionName, uint256 uniqueCounter, uint256 chainId, bytes data)` |
| `0x1d06ebf48eda5c7f5c720d1460f26380ded162475ea976df01e51cda51a1dd53` | `WrappedAndSwappedToDestChain(bytes32 bitcoinTxId, uint256 destinationChainId, uint256 intermediaryChainId, address targetAddress, uint256 destTokenAmount, address[] pathFromIntermediaryToDestTokenOnDestChain)` |
| `0x4dfdf3f10145a5c0d25504dd9520cd2699ba6a73e6083b7cdf708abb8ddc48d2` | `FailedWrapAndSwapToDestChain(bytes32 bitcoinTxId, uint256 destinationChainId, uint256 intermediaryChainId, address targetAddress, uint256 destTokenAmount, address[] pathFromIntermediaryToDestTokenOnDestChain)` |
| `0xf26626bebac2994376f5da4d86b60949db208bb90e08574df0bfbd8142f14308` | `SwappedBackAndRefundedToSourceChain(uint256 uniqueCounter, uint256 chainId, address refundAddress, uint256 inputTokenAmount, address[] pathFromIntermediaryToInputOnSourceChain, uint256[] amountsFromIntermediaryToInputOnSourceChain)` |
| `0xb1219c96b80275564b7ed58d5b5441a0b51752188fc765e572256edea554c3f3` | `FailedSwapBackAndRefundToSourceChain(uint256 uniqueCounter, uint256 chainId, address refundAddress, address inputToken, address tokenSent, uint256 tokenSentAmount)` |
| `0xf80ecdf6aa6c07f5546ab513d82f65f80c6617334130dc5b4fe6e60a59b08ffc` | `RefundedFailedSwapAndUnwrapUniversal(uint256 uniqueCounter, address refundAddress, address inputToken, uint256 inputTokenAmount, address[] pathFromIntermediaryToInputOnSourceChain, uint256[] amountsFromIntermediaryToInputOnSourceChain)` |
| `0x3f6072bef585d7ef7134e48bedfc939cd73c5d5b6d8f7c127f3083636505cdd0` | `SwappedBackAndRefundedBTCUniversal(uint256 uniqueCounter, uint256 chainId, address token, uint256 amount, int64 bridgePercentageFee, address refundAddress, address[] pathFromIntermediaryToInputOnSourceChain, uint256[] amountsFromIntermediaryToInputOnSourceChain)` |
| `0x06e5f2ca1234f717a2031f662608c02182d4f8bdc3dab013ec4c04eb97553132` | `AcrossUpdated(address oldAcross, address newAcross)` |
| `0xbac4f45eeeeb3c9688d046eddcdd28783777a2aa7beffcdf0acb76487d796364` | `TargetChainConnectorUpdated(address oldTargetChainConnector, address newTargetChainConnector)` |
| `0xffd9582901c27177dbd18194ae8017f10d8b21f98a0da2ea5197e0b20dc13d70` | `WrappedNativeTokenUpdated(address oldWrappedNativeToken, address newWrappedNativeToken)` |
| `0x5b235585c88679791b06b0e19dcfc3447956b7cb8d3e6d0dd6519b1f62a9bc7f` | `NewSwapAndUnwrapViaFiller(bytes32 indexed fingerprint, uint256 uniqueCounter, address inputToken, uint256 inputAmount, address intermediaryTokenOnInputChain, uint256 intermediaryTokenOnInputChainAmount, bytes userScript, uint8 scriptType, uint256 minBtcOutputAmount, uint256 thirdParty, address refundAddress)` |
| `0x7d080a3a97e39e0900baa146db1d7aba54f27b3babaead258b351ac13584ee9e` | `FillsClaimed(bytes32[] fingerprints, address intermediaryTokenOnInputChain, uint256 intermediaryTokenOnInputChainAmount, int64 bridgePercentageFee)` |
| `0xea36fd8824e3a6b55c7d6c31f0f1c14e100461af72103498abddfdbc9df65179` | `FillsClaimRetried(bytes32[] fingerprints, address intermediaryTokenOnInputChain, uint256 intermediaryTokenOnInputChainAmount, int64 bridgePercentageFee)` |
| `0x43d89f9712aec80f15f6fbffce105a51a655a511170e4a251acbf979bb67b587` | `UnfilledSwapAndUnwrapRefunded(bytes32 indexed fingerprint, address refundAddress, address intermediaryTokenOnInputChain, uint256 intermediaryTokenOnInputChainAmount)` |
| `0x794454db33e02ae5d0f48c7815f4eeac46e5b836766949ed362cda805aedebf1` | `FillerUpdated(address oldFiller, address newFiller)` |
| `0x70f752aa5d8bd2bde0f68a81c233171d6c3fb73c9f8509bff85495a20bb1d1f3` | `MaxClaimFillsBridgeFeeUpdated(uint256 oldMaxClaimFillsBridgeFee, uint256 newMaxClaimFillsBridgeFee)` |

Meaning and value:

- `MsgSent` / `MsgSentRune` — **source leg (EVM to BTC or to Runes).** `uniqueCounter` is the connector's request counter before the increment; `amount` of `sourceChainInputToken` leaves the user in the same transaction (ERC-20 `Transfer` user to connector, or native `msg.value`), and the connector deposits it into the Across SpokePool. `data` is the ABI-encoded request: purpose string, `uniqueCounter`, `currChainId`, refund address, exchange connector, minimum output, path, the user's Bitcoin script (`userScript`, `scriptType`) and the locker script, third-party id.
- `MsgReceived` — an Across fill arrived and was decoded; `functionName` is `wrapAndSwapUniversal` (BTC-to-EVM payout; `uniqueCounter` then holds the Bitcoin transaction id) or `swapBackAndRefund` (refund). Status plus decode; the value moves in the same transaction.
- `WrappedAndSwappedToDestChain` — **destination leg (BTC to EVM).** `destTokenAmount` of the last path token goes to `targetAddress` (ERC-20 `Transfer` connector to target).
- `SwappedBackAndRefundedToSourceChain` / `RefundedFailedSwapAndUnwrapUniversal` — **refund** of a failed EVM-to-BTC request to `refundAddress`. The `Failed*` events mean that the funds stay in the connector until the admin acts.
- **Filler path (implementation of 2026-10-04).** `swapAndUnwrapViaFiller` keeps the user's tokens in the connector and emits `NewSwapAndUnwrapViaFiller` (key `fingerprint`, topic1); no Across deposit happens in that transaction. A filler pays the BTC side on the home chain (PolyConnector `SwapAndUnwrapFilled`, same `fingerprint`). The connector later sends the batched funds over Across with `claimFills` / `retryClaimFills` (`FillsClaimed` / `FillsClaimRetried`), or refunds an unfilled request (`UnfilledSwapAndUnwrapRefunded`). `FillerUpdated` and `MaxClaimFillsBridgeFeeUpdated` are admin changes; both were emitted on Ethereum right after the upgrade.
- `MsgSentRune` and `swapAndUnwrapRune` are not in the Ethereum implementation of 2026-10-04; treat them as historical.

### 1.2 PolyConnector (Polygon, BNB)

| topic0 | Event |
|--------|-------|
| `0xd8883c6af9aa96506569d2db74cafb52037a26374320a8aeaf9fd5cd7df3d228` | `MsgReceived(string functionName, uint256 uniqueCounter, uint256 chainId, bytes data)` |
| `0x124f82fb68081b8c772a74ce98c0c92b659dd79e4fd3f03cf49988818eb04e8b` | `NewSwapAndUnwrap(uint256 uniqueCounter, uint256 chainId, address exchangeConnector, address inputToken, uint256 inputAmount, address indexed userTargetAddress, bytes userScript, uint8 scriptType, address lockerTargetAddress, uint256 requestIdOfLocker, address[] path, uint256 thirdPartyId)` |
| `0x33d28a02b6f25171e40ef509e2b97bfd82260ef601512c16c75e032dd9d88aa0` | `NewSwapAndUnwrapUniversal(uint256 uniqueCounter, uint256 chainId, address exchangeConnector, address inputToken, uint256 inputAmount, bytes32 indexed userTargetAddress, bytes userScript, uint8 scriptType, address lockerTargetAddress, uint256 requestIdOfLocker, address[] path, uint256 thirdPartyId)` |
| `0x13a9049471d86bfc267b825d08be20c5ebfc793c109c11eb159af6781cda3105` | `NewSwapAndUnwrapRune(uint256 uniqueCounter, uint256 chainId, address indexed userTargetAddress, uint256 thirdPartyId, uint256 internalId, uint256 appId, uint256 amount, uint256 inputAmount, address[] path, bytes userScript, uint8 scriptType, uint256 requestIdOfLocker)` |
| `0xa79aee2abfa3037b36c3689636c9932b113a82cebda0057ac4ce2386371fc969` | `FailedSwapAndUnwrap(uint256 uniqueCounter, uint256 chainId, address exchangeConnector, address inputToken, uint256 inputAmount, address indexed userTargetAddress, bytes userScript, uint8 scriptType, address[] path, uint256 thirdPartyId)` |
| `0xf86038a2d77cc08a4df197836cca8bfd5b8f31c2c524ea1ca1c24b61a2c8c6a3` | `FailedSwapAndUnwrapUniversal(uint256 uniqueCounter, uint256 chainId, address exchangeConnector, address inputToken, uint256 inputAmount, bytes32 indexed userTargetAddress, bytes userScript, uint8 scriptType, address[] path, uint256 thirdPartyId)` |
| `0xeef470645928135b5faf5eb6a2f7076448531d47f42149c2b1ceaa9fe1d624a0` | `FailedSwapAndUnwrapRune(uint256 uniqueCounter, uint256 chainId, address indexed userTargetAddress, uint256 thirdPartyId, uint256 internalId, uint256 appId, uint256 amount, uint256 inputAmount, address[] path, bytes userScript, uint8 scriptType)` |
| `0xf43f17a174cd55d7d75e934475f1cec7890c2bf3fabbf376de3868f0d8ce6897` | `WithdrawnFundsToSourceChain(uint256 uniqueCounter, uint256 chainId, address token, uint256 amount, int64 relayerFeePercentage, address user)` |
| `0x73f04e25d893c427907bd37b5f4a3f289020af48582a9647567c143376c571e5` | `WithdrawnFundsToSourceChainV2(uint256 uniqueCounter, uint256 chainId, address token, uint256 amount, int64 relayerFeePercentage, bytes32 refundAddress)` |
| `0x8fa71ea030111c7f3b83a93f7b13ddc306ba653917805739357a5aaab610c37d` | `WithdrewFundsToSourceChainUniversal(uint256 uniqueCounter, uint256 chainId, address token, uint256 amount, int64 relayerFeePercentage, bytes32 refundAddress, bytes32[] pathFromIntermediaryToInputOnSourceChain, uint256[] amountsFromIntermediaryToInputOnSourceChain, bytes jupiterInstructionData)` |
| `0x5b663d57fa8cf393f8c8019f514b25c1b3223c9324a2ce3efe28ce5aef0e62fe` | `BurnRouterUpdated(address oldBurnRouter, address newBurnRouter)` |
| `0x9f40e28e043a1925964408adad733d35097d026af4bfae3a434c062b4179bae1` | `EthConnectorUpdated(address oldEthConnector, address newEthConnector)` |
| `0x8bc9ede9ad39ea60ab72790a66580450bf8c540a19f0e2b54afdd1d7be28ee09` | `LockersProxyUpdated(address oldLockersProxy, address newLockersProxy)` |
| `0xdb18ace285ac81dfb11228b778d46dd29841b5e536fa01bb0616d12fc5379143` | `SwapAndUnwrapFilled(bytes32 indexed fingerprint, uint256 inputChainId, uint256 uniqueCounter, address filler, address intermediaryTokenOnInputChain, uint256 teleBTCAmount, uint256 burntAmount)` (implementation of 2026-10-04) |
| `0x9c42caed57866039a04ac9fe339f746549dc727ea54579b01f87b5ea30d5caee` | `FillsRefunded(bytes32[] fingerprints, address intermediaryTokenOnIntermediaryChain, address filler, uint256 refundedToFiller)` (implementation of 2026-10-04) |
| `0x72ca618d6b1478954424f1c82d42e7b44cb03787bde71f7aad7ca8825ea96c10` | `ClaimFillsRejected(address intermediaryTokenOnIntermediaryChain, uint256 sentToAcrossAdmin)` (implementation of 2026-10-04) |

`NewSwapAndUnwrap*` is the home-chain record of an EVM-to-BTC request: `uniqueCounter` and `chainId` (the source chain) are the join key to `MsgSent`, `userTargetAddress` is the user (topic1), and `lockerTargetAddress` + `requestIdOfLocker` are the join key to the BurnRouter's `NewUnwrap` and `PaidUnwrap`. `WithdrawnFundsToSourceChain*` is the **refund path** (funds go back over Across to the source chain). The PolyConnector also emits `MsgSent` (same topic0 as §1.1) when it bridges funds back.

### 1.3 CcTransferRouter and CcExchangeRouter (Polygon, BNB) — BTC to EVM

| topic0 | Event |
|--------|-------|
| `0xdebe45dc811f213ee5572218ab9c9e7d78fac393b0ca5c50ea9edbe5c8bcb617` | `NewWrap(bytes32 bitcoinTxId, bytes indexed lockerLockingScript, address lockerTargetAddress, address indexed user, address teleporter, uint256[2] amounts, uint256[4] fees, uint256 thirdPartyId, uint256 destinationChainId)` |
| `0x17ca0df5e76383e7d49ba70b93df7e5e530906b8c9a35f3a913fe01a369814bc` | `NewWrapV2(bytes32 bitcoinTxId, bytes indexed lockerLockingScript, address lockerTargetAddress, address indexed user, address teleporter, uint256[2] amounts, uint256[4] fees, uint256 thirdPartyId, uint32 lzDstEid)` |
| `0x49235eee15ff9b68c03c5efd6133fb7c0b976247122a03209c2cb97aabd5558b` | `NewWrapAndSwapV2(address lockerTargetAddress, bytes32 indexed user, bytes32[3] inputIntermediaryOutputToken, uint256[3] inputIntermediaryOutputAmount, uint256 indexed speed, address indexed teleporter, bytes32 bitcoinTxId, uint256 appId, uint256 thirdPartyId, uint256[5] fees, uint256 destinationChainId)` |
| `0x5832c9b125078499c9ab7dcc61594c25e4a33febb062486a4ff3c7a1d272bbdd` | `FailedWrapAndSwapV2(address lockerTargetAddress, bytes32 indexed recipientAddress, bytes32[3] inputIntermediaryOutputToken, uint256[3] inputIntermediaryOutputAmount, uint256 indexed speed, address indexed teleporter, bytes32 bitcoinTxId, uint256 appId, uint256 thirdPartyId, uint256[5] fees, uint256 destinationChainId)` |
| `0xf2de1389799f0ec6ba8aa31dc85397078c1cdf33a39d903c8463f87260617697` | `RequestFilledV2(address filler, bytes32 user, address lockerTargetAddress, bytes32 bitcoinTxId, address[2] inputAndOutputToken, uint256 fillAmount, uint256 finalAmount, uint256 userRequestedAmount, uint256 destinationChainId, uint256 bridgePercentageFee)` |
| `0xa691ee9f18c723075ade0e555d96de55c74e3e7b7cddc63a0ecbbff7ee6352e7` | `FillerRefunded(address filler, bytes32 bitcoinTxId, uint256 amount)` |
| `0x79bab54e96d1977794ba96251faf4af21e4c1e824335ed0e33ad672cc463194b` | `RefundProcessed(bytes32 indexed txId, address indexed refundedBy, uint256 failedRequestAmount, uint256 refundAmount, bytes userScript, uint8 scriptType, address lockerTargetAddress, uint256 burnRequestCounter)` |

`NewWrap` / `NewWrapAndSwapV2` are the **destination leg of a BTC deposit** (teleBTC or a swapped token reaches `user`). `RequestFilledV2` is a filler that paid the user in advance; `FillerRefunded` repays the filler once the Bitcoin deposit is proven. `FailedWrapAndSwapV2` keeps the funds for a refund; `RefundProcessed` returns them to Bitcoin through the BurnRouter. `NewWrapV2.lzDstEid` is a LayerZero endpoint id (teleBTC is sent over its OFT adapter).

### 1.4 BurnRouter (Polygon, BNB) — teleBTC to BTC

| topic0 | Event |
|--------|-------|
| `0x6b5c22e69db87534a562352580358411dc7b2d98d24684765342f2ebf2dd8c31` | `NewUnwrap(bytes userScript, uint8 scriptType, address lockerTargetAddress, address indexed userTargetAddress, uint256 requestIdOfLocker, uint256 indexed deadline, uint256 thirdPartyId, address inputToken, uint256[3] amounts, uint256[4] fees)` |
| `0x7b8cb33b1d4dc1e5d05c58e9945c383eb161ac22029c5b963989d08c3d0ef4da` | `PaidUnwrap(address indexed lockerTargetAddress, uint256 requestIdOfLocker, bytes32 bitcoinTxId, uint256 bitcoinTxOutputIndex)` |
| `0x58c23b4ae0617be275628875bcfd65759a441263099a256eeb27899fb5dd846d` | `BurnDispute(address indexed userTargetAddress, address indexed _lockerTargetAddress, bytes lockerLockingScript, uint256 requestIdOfLocker)` |
| `0x7ff138134e34ccab071315c38e38eec079f54726b890304ab46e2c5ab6f722bb` | `LockerDispute(address _lockerTargetAddress, bytes lockerLockingScript, uint256 _blockNumber, bytes32 txId, uint256 amount)` |

`NewUnwrap` is the **exit to Bitcoin**: teleBTC is burned in the same transaction, and `userScript` / `scriptType` identify the Bitcoin recipient. When the request came through the PolyConnector, `userTargetAddress` is the PolyConnector and the real user is in `NewSwapAndUnwrap`. `PaidUnwrap` is status only on the EVM side (the BTC moved on Bitcoin). `BurnDispute` and `LockerDispute` start slashing: **high-severity**.

### 1.5 LockersManager, teleBTC and BitcoinRelay (Polygon, BNB)

| topic0 | Event |
|--------|-------|
| `0x8ad706b338c5d2a20b0d038b5cfdaf2b2f943f43048723bde0dccdf129598a11` | `MintByLocker(address indexed lockerTargetAddress, address indexed receiver, uint256 mintedAmount, uint256 lockerFee, uint256 mintingTime)` |
| `0x66fb54322c407b04a077a306e72cdd780f0f374ba5dac9f6901a56a6255bc34a` | `BurnByLocker(address indexed lockerTargetAddress, uint256 burntAmount, uint256 lockerFee, uint256 burningTime)` |
| `0x5e4485631c54370ddbcded30559851c5dd670a232b8a7502b9d0b47ba9090d47` | `LockerSlashed(address indexed lockerTargetAddress, address collateralToken, uint256 rewardAmount, address indexed rewardRecipient, uint256 amount, address indexed recipient, uint256 slashedCollateralAmount, uint256 slashTime, bool isForCCBurn)` |
| `0x19ac06de95d67912d84cd839d617200570c30562b34ba4f6a3a19fbd14a8f9a9` | `LockerLiquidated(address indexed lockerTargetAddress, address indexed liquidatorAddress, address collateralToken, uint256 collateralAmount, uint256 teleBTCAmount, uint256 liquidateTime)` |
| `0xbd529f70cdff05eff7a5a8aad1d0b2926c1f644df27da30cb7de1f546909d16a` | `LockerAdded(address indexed lockerTargetAddress, bytes lockerLockingScript, uint256 TSTLockedAmount, address indexed collateralToken, uint256 collateralTokenLockedAmount, uint256 reliabilityFactor, uint256 addingTime)` |
| `0x89e0136053e5fb3b6e55cac61cebd11e85b3cbc19a56d52fa34e152a94286f27` | `LockerRemoved(address indexed lockerTargetAddress, bytes lockerLockingScript, uint256 TSTUnlockedAmount, address indexed collateralToken, uint256 collateralTokenUnlockedAmount)` |
| `0x6ae172837ea30b801fbfcdd4108aa1d5bf8ff775444fd70256b44e6bf3dfc3f6` | `MinterAdded(address indexed account)` |
| `0x86e57fd2b90329052917118de7c3f521f400d439b9650deaa906a25b08b94560` | `BurnerAdded(address indexed account)` |
| `0xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8` | `Mint(address indexed doer, address indexed receiver, uint256 value)` |
| `0xbac40739b0d4ca32fa2d82fc91630465ba3eddd1598da6fca393b26fb63b9453` | `Burn(address indexed doer, address indexed burner, uint256 value)` |
| `0xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855` | `Blacklisted(address indexed account)` |
| `0x36ab29917278ebced3c63670f7872f78555ed7cdb4aa5184a159eb978be79508` | `NewMintLimit(uint256 oldMintLimit, uint256 newMintLimit)` |
| `0xfb8fff3e2daa665d496373ced291b62aba4162f24632a1597e286621016e9a1f` | `BlockAdded(uint256 indexed height, bytes32 selfHash, bytes32 indexed parentHash, address indexed relayer)` |
| `0x4fec6ffa2052e80db9daadc2384a8f634057472e28ea7f1bd3eebfc92b5b0f8e` | `BlockFinalized(uint256 indexed height, bytes32 selfHash, bytes32 parentHash, address indexed relayer, uint256 rewardAmountTNT, uint256 rewardAmountTDT)` |

`MintByLocker` + teleBTC `Mint` (with `Transfer` from `0x0`) = teleBTC created against a Bitcoin deposit. `BurnByLocker` + teleBTC `Burn` (with `Transfer` to `0x0`) = teleBTC destroyed for a Bitcoin payout. `MinterAdded` / `BurnerAdded` exist on both the LockersManager and teleBTC (same topic0): a new minter can create unbacked teleBTC, so treat it as **critical**. `BlockAdded` / `BlockFinalized` are status only.

### 1.6 Proxy and ownership events (all TeleSwap proxies)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 EthConnector

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x201c527c` | `swapAndUnwrap(address _token, address _exchangeConnector, uint256[] _amounts, bool _isInputFixed, address[] _path, (bytes userScript, uint8 scriptType, bytes lockerLockingScript) _userAndLockerScript, int64 _bridgePercentageFee, uint256 _thirdParty)` | `payable`. EVM to BTC; refund address = `tx.origin`. Emits `MsgSent`. |
| `0x628270eb` | `swapAndUnwrapV2(address _token, address _exchangeConnector, uint256[] _amounts, bool _isInputFixed, address[] _path, (bytes userScript, uint8 scriptType, bytes lockerLockingScript) _userAndLockerScript, int64 _bridgePercentageFee, uint256 _thirdParty, address _refundAddress)` | `payable`. Emits `MsgSent`. |
| `0x966ca0ac` | `swapAndUnwrapUniversal((address[] _pathFromInputToIntermediaryOnSourceChain, uint256[2] _amountsFromInputToIntermediaryOnSourceChain, address[] _pathFromIntermediaryToOutputOnIntermediaryChain, uint256 _minOutputAmount, int64 _bridgePercentageFee) _arguments, address _exchangeConnector, bool _isInputFixed, (bytes userScript, uint8 scriptType, bytes lockerLockingScript) _userAndLockerScript, uint256 _thirdParty, address _refundAddress)` | `payable`. Swaps on the source chain first when the path is longer than one. Emits `MsgSent`. |
| `0xfa4df506` | `swapAndUnwrapRune(address _token, uint256 _appId, address _exchangeConnector, uint256[] _amounts, uint256 _internalId, address[] _path, (bytes userScript, uint8 scriptType) _userScript, int64 _bridgePercentageFee, uint256 _thirdParty)` | `payable`. EVM to Runes. Emits `MsgSentRune`. Not in the Ethereum implementation of 2026-10-04 (historical). |
| `0x2bd3fe8c` | `swapAndUnwrapViaFiller(address[] _pathFromInputToIntermediaryOnInputChain, uint256[2] _amountsFromInputToIntermediaryOnInputChain, (bytes userScript, uint8 scriptType) _userScript, uint256 _minBtcOutputAmount, uint256 _thirdParty, address _refundAddress)` | Implementation of 2026-10-04. EVM to BTC through a filler. Emits `NewSwapAndUnwrapViaFiller`; the tokens stay in the connector. |
| `0x8ea75fa6` | `claimFills(bytes32[] _fingerprints, address _exchangeConnector, int64 _bridgePercentageFee)` | Sends the funds of filled requests over Across. Emits `FillsClaimed`. |
| `0x2b2ce364` | `retryClaimFills(bytes32[] _fingerprints, address _exchangeConnector, int64 _bridgePercentageFee)` | Emits `FillsClaimRetried`. |
| `0x6e12d58b` | `refundUnfilledSwapAndUnwrap(bytes32[] _fingerprints)` | Emits `UnfilledSwapAndUnwrapRefunded`. |
| `0x18bbee8d` | `setFiller(address _filler)` | Owner. Emits `FillerUpdated`. |
| `0xd6009793` | `setMaxClaimFillsBridgeFee(uint256 _maxClaimFillsBridgeFee)` | Owner. Emits `MaxClaimFillsBridgeFeeUpdated`. |
| `0x3a5be8cb` | `handleV3AcrossMessage(address _tokenSent, uint256 _amount, address, bytes _message)` | Only the Across SpokePool can call it. Emits `MsgReceived`, then the payout or refund event. |
| `0x59eb422d` | `refundFailedSwapAndUnwrapUniversal(uint256 _uniqueCounter, address _refundAddress, address _inputToken, address[] _pathFromIntermediaryToInputOnSourceChain, uint256[] _amountsFromIntermediaryToInputOnSourceChain)` | Owner or `acrossAdmin`. Emits `RefundedFailedSwapAndUnwrapUniversal`. |
| `0xbb8fc8d6` | `swapBackAndRefundBTCByAdmin((address targetAddress, address destToken, address tokenSent, bytes32 bitcoinTxId, address exchangeConnector, uint256 minOutputAmount, (bytes userScript, uint8 scriptType, bytes lockerLockingScript) userAndLockerScript, address[] path, uint256[] amounts, int64 bridgePercentageFee, uint256 intermediaryChainId) _args)` | Owner or `acrossAdmin`. Emits `SwappedBackAndRefundedBTCUniversal`. |
| `0xe63ea408` | `emergencyWithdraw(address _token, address _to, uint256 _amount)` | **Owner only; no event.** Moves any token or native balance out of the connector. |
| `0x61be10f2` | `setAcross(address _across)` | Owner. Emits `AcrossUpdated`. |
| `0x878269b5` | `setAcrossAdmin(address _acrossAdmin)` | Owner. **No event.** The Across depositor. |
| `0xb55d3633` | `setBridgeConnectorMapping(address _exchangeConnector, uint256 _targetChainId, address _targetChainConnectorProxy)` | Owner. **No event.** Sets the Across recipient on the home chain. |
| `0xd7fe6b7d` | `setBridgeTokenMapping(address _sourceToken, uint256 _destinationChainId, address _destinationToken)` | Owner. **No event.** |
| `0xcab1344e` | `setExchangeConnector(address _exchangeConnector)` | Owner. **No event.** |
| `0xda058ae3` | `setWrappedNativeToken(address _wrappedNativeToken)` | Owner. Emits `WrappedNativeTokenUpdated`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner. |
| `0xd4dfc8c3` | `uniqueCounter()` | `uint256` — the next request counter. |
| `0x292c1d92` | `across()` | `address` — the Across SpokePool of the chain. |
| `0x87c554f8` | `acrossAdmin()` | `address` — the Across depositor and refund operator. |
| `0xd83f0fc5` | `currChainId()` | `uint256` — this chain's EVM chain id. |
| `0x146ffb26` | `targetChainId()` | `uint256`. |
| `0x7e628c05` | `bridgeConnectorMapping(address)` | Home-chain connector and chain id per exchange connector. |
| `0x8da5cb5b` | `owner()` | `address`. |

### 2.2 PolyConnector

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3a5be8cb` | `handleV3AcrossMessage(address _tokenSent, uint256 _amount, address, bytes _message)` | Only the Across SpokePool. Emits `MsgReceived` and `NewSwapAndUnwrap*` or `FailedSwapAndUnwrap*`. |
| `0x3e938097` | `withdrawFundsToSourceChain(bytes _message, uint8 _v, bytes32 _r, bytes32 _s)` | User-signed refund of a failed request. Emits `WithdrawnFundsToSourceChain*`. |
| `0x86420503` | `withdrawFundsToSourceChainByOwnerOrAdmin(address _user, uint256 _chainId, uint256 _uniqueCounter, address _token, int64 _relayerFeePercentage)` | Owner or admin refund. |
| `0x5f6b6fc4` | `withdrawFundsToSourceChainByAdminUniversal((bytes32 refundAddress, uint256 chainId, uint256 uniqueCounter, address token, int64 bridgePercentageFee, bytes32[] pathFromIntermediaryToInputOnSourceChain, uint256[] amountsFromIntermediaryToInputOnSourceChain, address exchangeConnector, bytes jupiterInstructionData) args)` | Admin refund, universal route. |
| `0xcf75dfd2` | `swapBackAndRefundBTCByAdmin(bytes32 _bitcoinTxId, address _token, bytes32 _refundAddress, address _exchangeConnector, uint256 _minOutputAmount, (bytes userScript, uint8 scriptType, bytes lockerLockingScript) _userAndLockerScript, address[] _path, uint256[] _amounts)` | Admin. |
| `0xe63ea408` | `emergencyWithdraw(address _token, address _to, uint256 _amount)` | **Owner only; no event.** |
| `0x7a9d3080` | `fillSwapAndUnwrap(uint256 _inputChainId, uint256 _uniqueCounter, address _intermediaryTokenOnInputChain, uint256 _intermediaryTokenOnInputChainAmount, (bytes userScript, uint8 scriptType) _userScript, uint256 _minBtcOutputAmount, uint256 _thirdParty, uint256 _teleBTCAmount, bytes _lockerLockingScript)` | Implementation of 2026-10-04. The filler pays a `NewSwapAndUnwrapViaFiller` request with teleBTC and starts the BTC unwrap. Emits `SwapAndUnwrapFilled`. |
| `0x18bbee8d` | `setFiller(address _filler)` | Owner. |
| `0x4d6e8f9d` | `setBurnRouterProxy(address _burnRouterProxy)` | Owner. Emits `BurnRouterUpdated`. |
| `0x59841888` | `setLockersProxy(address _lockersProxy)` | Owner. Emits `LockersProxyUpdated`. |

### 2.3 CcTransferRouter, CcExchangeRouter and BurnRouter

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb866d6ea` | `wrap((bytes4 version, bytes vin, bytes vout, bytes4 locktime, uint256 blockNumber, bytes intermediateNodes, uint256 index) _txAndProof, bytes _lockerLockingScript)` | CcTransferRouter; called by a teleporter with the Bitcoin proof. Emits `NewWrap`. |
| `0x276edfe0` | `wrapV2((bytes4 version, bytes vin, bytes vout, bytes4 locktime, uint256 blockNumber, bytes intermediateNodes, uint256 index) _txAndProof, bytes _lockerLockingScript, uint32 _dstEid, bytes _lzOptions)` | CcTransferRouter; mint and send over the teleBTC OFT. Emits `NewWrapV2`. |
| `0x2554a14c` | `wrapAndSwapV2((bytes4 version, bytes vin, bytes vout, bytes4 locktime, uint256 blockNumber, bytes intermediateNodes, uint256 index) _txAndProof, bytes _lockerLockingScript, address[] _path)` | CcExchangeRouter. Emits `NewWrapAndSwapV2` or `FailedWrapAndSwapV2`. |
| `0x29b0db8b` | `fillTxV2(bytes32 _txId, bytes32 _recipient, address _intermediaryToken, bytes32 _outputToken, uint256 _fillAmount, uint256 _userRequestedAmount, uint256 _destRealChainId, uint256 _bridgePercentageFee, bytes _lockerLockingScript)` | CcExchangeRouter; a filler pays in advance. Emits `RequestFilledV2`. |
| `0x303a785d` | `refundByOwnerOrAdmin(bytes32 _txId, uint8 _scriptType, bytes _userScript, bytes _lockerLockingScript)` | CcExchangeRouter. Emits `RefundProcessed`. |
| `0x95ccea67` | `emergencyWithdraw(address _token, uint256 _amount)` | CcExchangeRouter. **Owner only.** |
| `0x3fea4367` | `unwrap(uint256 _amount, bytes _userScript, uint8 _scriptType, bytes _lockerLockingScript, uint256 thirdParty)` | BurnRouter: burn teleBTC for BTC. Emits `NewUnwrap`. |
| `0x44dd6aa5` | `swapAndUnwrap(address _exchangeConnector, uint256[] _amounts, bool _isFixedToken, address[] _path, uint256 _deadline, bytes _userScript, uint8 _scriptType, bytes _lockerLockingScript, uint256 thirdParty)` | BurnRouter: swap a token to teleBTC, then burn. |
| `0x9d0b9b57` | `unwrapWithDynamicFee(uint256 _amount, bytes _userScript, uint8 _scriptType, bytes _lockerLockingScript, uint256 _thirdParty, uint256 _sourceChainId, bytes32 _sourceToken)` | BurnRouter. |
| `0xcf3641f5` | `swapAndUnwrapWithDynamicFee(address _exchangeConnector, uint256[] _amounts, bool _isFixedToken, address[] _path, uint256 _deadline, bytes _userScript, uint8 _scriptType, bytes _lockerLockingScript, uint256 _thirdParty, uint256 _sourceChainId, bytes32 _sourceToken)` | BurnRouter; the PolyConnector route. |
| `0xea732637` | `burnProof(bytes4 _version, bytes _vin, bytes _vout, bytes4 _locktime, uint256 _blockNumber, bytes _intermediateNodes, uint256 _index, bytes _lockerLockingScript, uint256[] _burnReqIndexes, uint256[] _voutIndexes)` | BurnRouter; the locker proves the Bitcoin payout. Emits `PaidUnwrap`. |
| `0x73532b2a` | `disputeBurn(bytes _lockerLockingScript, uint256[] _indices)` | Emits `BurnDispute`; slashes the locker. |
| `0xc780c03f` | `disputeLocker(bytes _lockerLockingScript, bytes4[] _versions, bytes _inputVin, bytes _inputVout, bytes _outputVin, bytes _outputVout, bytes4[] _locktimes, bytes _inputIntermediateNodes, uint256[] _indexesAndBlockNumbers)` | Emits `LockerDispute`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **EthConnector** (proxy) | `0xFA1B28052Bd8087B1CF64eE9429FEB324e95B0ff` | Official connector (`connectors.ethereum`). 2,118 B proxy; implementation `0x756B770b38c03B0A249Aef5FE6e06F9B34a3D431` (verified `EthConnectorLogic`, set by `Upgraded` at block 26,121,906, 2026-10-04 22:13 UTC). Previous implementation `0xe5a2357b7e6f2fd1f21d6aa7880084c2cf828548`, retired at that block (observed 2026-10-05). `across()` = Across SpokePool `0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5`; `currChainId()` = 1. |
| Old `EthConnectorLogic` implementation | `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` | 5,967 B, not a proxy, same deployer `0x2D3E4AeB9347C224DAe7F1dc1213bE082F6FddEC`. **Not the connector on Ethereum** (it is the connector address on Base, Arbitrum and Optimism). |
| Filler | `0x4a00edf7F07Ecb48a4A3FD798e0fb79D90ef21a9` | `filler()` of the Ethereum and Base EthConnectors (set by `FillerUpdated` after the upgrade); 23 B code = an EIP-7702 delegated account. `filler()` is zero on Arbitrum and Optimism. |
| Across depositor / refund operator (EOA) | `0x144c5fb302dbaa789fc59bbec301169eaa56c5fc` | `acrossAdmin()` of every EthConnector; the `depositor` in the Across `FundsDeposited` logs. |
| Proxy admin (EOA) | `0x4565ae5c90e52c058410fc7f05711ffed9b6e62a` | EIP-1967 admin of every TeleSwap proxy. |
| Owner (EOA) | `0x24004f4f6d2e75b039d528e82b100355d8b1d4fb` | `owner()` of every TeleSwap proxy. |

## 4. Addresses — Base (8453), Arbitrum One (42161), Optimism (10)

One official connector address on all three chains (`connectors.base`, `connectors.arbitrum`, `connectors.optimism`).

| Chain | EthConnector (proxy) | Implementation (EIP-1967) | `across()` (Across SpokePool) | `currChainId()` |
|-------|----------------------|----------------------------|-------------------------------|-----------------|
| Base | `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` | `0xd3685A1Ad6A3A1eE65871d8716661BDa4448dA06` (was `0x19f5775779628063066f53f509c9cc26cb91c2b5`, retired by 2026-10-05) | `0x09aea4b2242abc8bb4bb78d537a67a245a7bec64` | 8453 |
| Arbitrum One | `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` | `0x5EbF7A3b782270f264cdc0Cf9aE188fB19Cf4047` (was `0xe93bd2f610153932e6c3ac28ad9d93f912d39c05`, retired by 2026-10-05) | `0xe35e9842fceaca96570b734083f4a58e8f7c5f2a` | 42161 |
| Optimism | `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` | `0xc04B61E67f963680fcfd98c3b98355aCBFb82F7A` (was `0x8b3d6e8b0d2a55db1fb435472c52277a223b13c7`, retired by 2026-10-05) | `0x6f26bf09b1c792e3228e5467807a900a503c0281` | 10 |

`0xFA1B28052Bd8087B1CF64eE9429FEB324e95B0ff` has no code on Base, Arbitrum or Optimism.

## 5. Addresses — Polygon PoS (chain ID 137) — home chain

| Role | Address | One-liner |
|------|---------|-----------|
| **PolyConnector** (proxy) | `0xE0166434A2ad67536B5FdAFCc9a6C1B41CC5e085` | `connectors.polygon`. Implementation `0x58733ad7414d01aB28c6845E2B4872bCC10a4E42` (verified `PolyConnectorLogic`, set by `Upgraded` at block 94,964,751 on 2026-10-04). Previous implementation `0xE7341c485a60C94B7caB74dF00eADc45Ff3f6a51`, retired at that block (observed 2026-10-05). |
| **CcTransferRouter** (proxy) | `0x04367D74332137908BEF9acc0Ab00a299A823707` | Implementation `0x5F3886D988a4735e6650aD45e32e704645bA73Ae`. |
| **CcExchangeRouter** (proxy) | `0xD1E9Ff33EC28f9Dd8D99E685a2B0F29dCaa095a3` | Implementation `0x470934D226121354AD3986c8762A453764858334`. |
| **BurnRouter** (proxy) | `0x0009876C47F6b2f0BCB41eb9729736757486c75f` | Implementation `0x5d9a6365B0758B84f1301D405957317ea6eC4dBE`. |
| **LockersManager** (`LockersProxy`) | `0xf5D6D369A7F4147F720AEAdd4C4f903aE8046166` | Implementation `0xf10c1207fa3fbbe80D1915c6e6d3F3d1aF316b8D`. |
| **teleBTC** (proxy) | `0x3BF668Fe1ec79a84cA8481CEAD5dbb30d61cC685` | Implementation `0xFf489BB994a3C82251c422F1B2531a4877844C38` (`TeleBTCLogic`). The token that the BurnRouter moves; other tokens on Polygon also use the name "teleBTC". |
| BitcoinRelay | `0x7DeB66341b1d499D7e699589d0cf665De4132EA3` | Verified `BitcoinRelay`, 16,232 B, not a proxy. |
| Price oracle (listed) | `0x4Dc0109036b7d500dB30150A8f52744772256e25` | **No code on Polygon** (`eth_getCode` = `0x`, nonce 0) although `contracts.json` lists it. |
| Uniswap V3 connector (proxy) | `0x083Ec5DF8f7a1160690E979E23b5aAAD0b1269Eb` | DEX adapter used for the swaps; 2,109 B proxy, implementation `0x5840505334d44cf1f0ef1325fdb0905b0047116e`. |
| Uniswap V2 connector | `0x0C28968d8A3Af022F47D493402D35Cb42EFF0597` | 8,557 B. |

## 6. Addresses — BNB Smart Chain (chain ID 56) — home chain

| Role | Address | One-liner |
|------|---------|-----------|
| **PolyConnector** (proxy) | `0x9b95Dc17acFD8E028F192971165aE7Be76e6a954` | `connectors.bsc`. 2,109 B proxy; implementation `0xf7781910540B040dd9dC5a802113016db6F4da94` (read 2026-10-05; previous implementation `0xc252d5d0a99f96bfbf02700b7ac25ae54888cd06`, retired). |
| **CcTransferRouter** (proxy) | `0xA38aD0d52B89C20c2229E916358D2CeB45BeC5FF` | Implementation `0x98ba75cc7003f2d46dd84db9aa017f7ec0687c70`. |
| **CcExchangeRouter** (proxy) | `0xcA5416364720c7324A547d39b1db496A2DCd4F0D` | Implementation `0xb6e6f1a7d07aba1764c1e9e9deccfc754fecd85a`. |
| **BurnRouter** (proxy) | `0x2787D48e0B74125597DD479978a5DE09Bb9a3C15` | Implementation `0xE4EAF0EEc126B063cF5BCaBd01ee7c6A329F2A02` (read 2026-10-05; previous implementation `0xbf41e780cab6772be91e9b425cac1b08c11626a0`, retired). |
| **LockersManager** (proxy) | `0x84F74e97ebab432CeE185d601290cE0A483987A5` | Implementation `0x713e333ae88dcd0881a427371efc0d76267e8cae`. |
| **teleBTC** (proxy) | `0xc58c1117da964aebe91fef88f6f5703e79bda574` | Implementation `0x467e5a869b1d0435ef56335ef296687e01032bb9`; burned by the LockersManager in the sample. |
| BitcoinRelay (proxy) | `0xFcd688999c25D5493571543137cEeb4fbDb44D02` | Implementation `0x013f6d7b4c6aa1a0573c7151d397695376676a29`. |
| Price oracle | `0x7Aabb0779782247384A1C91844211516E93b1D63` | 6,663 B. |
| Uniswap V3 connector (proxy) | `0xD25313591BA4c2645bA7427F34eA61951fAF1D6a` | Implementation `0x12fc33aa9ef48e9841b8d35662cbd53115abea52`. |
| Uniswap V2 connector | `0x856D80F77349F675Ea7E3477aD75Ef57349e777b` | 8,557 B. |

Same-address traps on BNB: `0xFA1B28052Bd8087B1CF64eE9429FEB324e95B0ff` is a 23,549 B contract with BurnRouter topics (an old BurnRouter implementation, not a connector), and `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` is a 6,438 B contract with no TeleSwap topic. Neither is in the official list.

### 6.1 Avalanche C-Chain (43114), Robinhood Chain (4663) and Arc (5042) — NO TeleSwap deployment

`eth_getCode` returns `0x` at `0xFA1B28052Bd8087B1CF64eE9429FEB324e95B0ff`, `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52`, `0xE0166434A2ad67536B5FdAFCc9a6C1B41CC5e085` and `0x9b95Dc17acFD8E028F192971165aE7Be76e6a954` on Avalanche and Robinhood Chain (and on Arc, checked 2026-10-05), and the official list names none of these chains.

---

## 7. Cross-chain summary

| Chain | ID | EthConnector | PolyConnector | Home-chain routers, lockers, teleBTC | Window activity (§10) |
|-------|----|--------------|---------------|---------------------------------------|------------------------|
| Ethereum | 1 | `0xFA1B28052Bd8087B1CF64eE9429FEB324e95B0ff` | — | — | `MsgSent` 135 |
| Base | 8453 | `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` | — | — | `MsgSent` 11 |
| Arbitrum One | 42161 | `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` | — | — | `MsgSent` 13 |
| Optimism | 10 | `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` | — | — | 0 |
| Polygon PoS | 137 | — | `0xE0166434A2ad67536B5FdAFCc9a6C1B41CC5e085` | ✓ (§5) | `MsgReceived` 77, `NewUnwrap` 94 |
| BNB Smart Chain | 56 | — | `0x9b95Dc17acFD8E028F192971165aE7Be76e6a954` | ✓ (§6) | `MsgReceived` 82, `NewUnwrap` 192 |
| Avalanche C-Chain | 43114 | — (`0x`) | — (`0x`) | — | — |
| Robinhood Chain | 4663 | — (`0x`) | — (`0x`) | — | — |
| Arc | 5042 | — (`0x`) | — (`0x`) | — | — |

**Outside the eight (official list):** Unichain connector `0x45e4d542c570fb6194467FFEDF7cc09867279a96`; home chains BOB and BSquared (their own routers, lockers and relays; on BSquared the CcExchangeRouter shares the address `0xE0166434A2ad67536B5FdAFCc9a6C1B41CC5e085` with the Polygon PolyConnector); a TON swap router; and Bitcoin itself (the lockers' scripts).

**Chain ids:** the connectors use EVM chain ids (`currChainId()` = 1, 8453, 42161, 10). `NewWrapV2.lzDstEid` is a LayerZero endpoint id.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority |
|----------|---------|-----------|-------------------|
| EthConnector, PolyConnector, CcTransferRouter, CcExchangeRouter, BurnRouter, LockersManager, teleBTC, BNB BitcoinRelay, Uniswap V3 connectors (Polygon, BNB) | **Transparent proxy** (EIP-1967; 2,109 to 2,153 B proxy code) | Implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` set (per chain, §3 to §6); admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = `0x4565ae5c90e52c058410fc7f05711ffed9b6e62a`; `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. | Proxy admin **EOA** `0x4565ae5c90e52c058410fc7f05711ffed9b6e62a` (no code on any chain; nonce 31 on Ethereum, 117 on BNB). Configuration and `emergencyWithdraw`: owner **EOA** `0x24004f4f6d2e75b039d528e82b100355d8b1d4fb`. |
| Polygon BitcoinRelay, BNB price oracle, Uniswap V2 connectors | Not proxies | Full runtime bytecode, no implementation slot. | `owner()`. |

The EthConnector ABI has `paused()` but no `pause()` function, so the connectors can be stopped only by an upgrade. The implementations differ per chain; read the live slot.

---

## 9. Detection invariants & gotchas

1. **EVM to BTC, source leg:** `MsgSent` on an EthConnector (Ethereum, Base, Arbitrum, Optimism). In the same transaction: ERC-20 `Transfer` user to connector (or native `msg.value`), then the Across `FundsDeposited` from the SpokePool with `destinationChainId` = 137 or 56 and `recipient` = the home-chain PolyConnector. The sample on Ethereum sent 0.0243 ETH as WETH to BSC (Across `destinationChainId` 56).
2. **Home-chain leg:** the Across relayer fills on the home chain and calls the PolyConnector: `FilledRelay` (Across), `MsgReceived`, then `NewSwapAndUnwrap*` with the same `uniqueCounter` and the source `chainId`. The PolyConnector gives the tokens to the BurnRouter, which swaps them to teleBTC; the LockersManager burns the teleBTC (`BurnByLocker`, teleBTC `Burn`, `Transfer` to `0x0`), and the BurnRouter emits `NewUnwrap` with `userTargetAddress` = the PolyConnector. The BSC sample `0x59445ba9e48caff9187d152bdaee75dfa47f3a070690d783b9244afc5e6047dc` shows this chain of events in one transaction.
3. **Bitcoin leg:** the payout happens on Bitcoin. The only EVM trace is `PaidUnwrap(lockerTargetAddress, requestIdOfLocker, bitcoinTxId, bitcoinTxOutputIndex)`, which the locker's `burnProof` emits later. An unpaid request after its `deadline` can be disputed (`BurnDispute`), which slashes the locker.
4. **Attribution:** the real user of an EVM-to-BTC request is in the PolyConnector's `NewSwapAndUnwrap*` (`userTargetAddress`, topic1) and in the decoded `MsgSent.data` (refund address). On the source chain `tx.from` can be an aggregator: the Ethereum sample `0x8305510a6d6bd655d1b9ff7187c6ef12264aec4c97eb26316196398d8cf66701` came through the Rango Diamond `0x69460570c93f9de5e2edbc3052bf10125f0ca22d`. `swapAndUnwrap` (not V2) uses `tx.origin` as the refund address.
5. **Count once.** The source-leg value is also an Across deposit (depositor = the TeleSwap `acrossAdmin` EOA), and the home-chain fill is an Across fill. Attribute the flow to TeleSwap by the connector events and do not add the Across leg again.
6. **BTC to EVM:** `NewWrap` (teleBTC to `user` on the home chain), `NewWrapV2` (teleBTC sent over the OFT to `lzDstEid`), `NewWrapAndSwapV2` (swap, and for another chain an Across transfer to that chain's connector, which emits `MsgReceived` with `functionName` = `wrapAndSwapUniversal` and `uniqueCounter` = the Bitcoin transaction id, then `WrappedAndSwappedToDestChain` and the `Transfer` to `targetAddress`). A filler can pay first (`RequestFilledV2`) and is repaid later (`FillerRefunded`).
7. **The same literal address is a different contract on different chains.** `0xec4A7D93750BbcE2A07fd1bc748507ea645e9d52` is the connector on Base, Arbitrum and Optimism, an old `EthConnectorLogic` implementation on Ethereum, a contract with no TeleSwap event on BNB, and the BitcoinRelay on BOB. `0xFA1B28052Bd8087B1CF64eE9429FEB324e95B0ff` is the connector on Ethereum and an old BurnRouter implementation on BNB. Key on `(chain, address)`.
8. **Admin actions without events:** `emergencyWithdraw` on the connectors and the CcExchangeRouter, `setAcrossAdmin`, `setBridgeConnectorMapping` and `setBridgeTokenMapping` emit nothing. Key on the selectors (§2) in transactions to these proxies from the owner EOA. `Upgraded` and `AdminChanged` on any proxy, and `MinterAdded` on teleBTC or the LockersManager, are critical.
9. **Home chains are Polygon and BNB inside the eight.** A TeleSwap flow from Ethereum, Base, Arbitrum or Optimism always passes through one of them before it reaches Bitcoin; teleBTC is minted only on the home chains; `NewWrapV2` can send it over the teleBTC OFT adapter to a LayerZero peer chain (the peer set was not checked here: unverified).
10. **`MsgReceived` has the same topic0 on both connector types.** On an EthConnector it is a BTC-to-EVM payout or a refund; on a PolyConnector it is an incoming EVM-to-BTC request. Decode `functionName` and filter by emitter.
11. **Filler requests skip the per-request Across deposit.** Since the 2026-10-04 upgrade an EVM-to-BTC request can be `NewSwapAndUnwrapViaFiller` on the EthConnector (no `MsgSent`, no `FundsDeposited` in that transaction) and `SwapAndUnwrapFilled` on the PolyConnector, joined by `fingerprint` (topic1 on both). The value crosses later in a batch (`FillsClaimed`). Index both paths.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== EthConnector topics =====
TOPIC_TELESWAP_MSG_SENT                 = '\xd953c900c00c8d83f745d17aa6ce067c29cb0fdd7c3dda8dd5aee0e79feb850a'
TOPIC_TELESWAP_MSG_SENT_RUNE            = '\xfae1fd145a544fd4b9a3f59113a4133d16b3cc0e015c89e90755bbe0ce06377f'
TOPIC_TELESWAP_MSG_RECEIVED             = '\xd8883c6af9aa96506569d2db74cafb52037a26374320a8aeaf9fd5cd7df3d228'
TOPIC_TELESWAP_WRAPPED_AND_SWAPPED      = '\x1d06ebf48eda5c7f5c720d1460f26380ded162475ea976df01e51cda51a1dd53'
TOPIC_TELESWAP_FAILED_WRAP_AND_SWAP     = '\x4dfdf3f10145a5c0d25504dd9520cd2699ba6a73e6083b7cdf708abb8ddc48d2'
TOPIC_TELESWAP_SWAPPED_BACK_REFUNDED    = '\xf26626bebac2994376f5da4d86b60949db208bb90e08574df0bfbd8142f14308'
TOPIC_TELESWAP_FAILED_SWAP_BACK         = '\xb1219c96b80275564b7ed58d5b5441a0b51752188fc765e572256edea554c3f3'
TOPIC_TELESWAP_REFUNDED_UNIVERSAL       = '\xf80ecdf6aa6c07f5546ab513d82f65f80c6617334130dc5b4fe6e60a59b08ffc'
TOPIC_TELESWAP_REFUNDED_BTC_UNIVERSAL   = '\x3f6072bef585d7ef7134e48bedfc939cd73c5d5b6d8f7c127f3083636505cdd0'
TOPIC_TELESWAP_ACROSS_UPDATED           = '\x06e5f2ca1234f717a2031f662608c02182d4f8bdc3dab013ec4c04eb97553132'
TOPIC_TELESWAP_NEW_SWAP_UNWRAP_FILLER   = '\x5b235585c88679791b06b0e19dcfc3447956b7cb8d3e6d0dd6519b1f62a9bc7f'
TOPIC_TELESWAP_FILLS_CLAIMED            = '\x7d080a3a97e39e0900baa146db1d7aba54f27b3babaead258b351ac13584ee9e'
TOPIC_TELESWAP_FILLS_CLAIM_RETRIED      = '\xea36fd8824e3a6b55c7d6c31f0f1c14e100461af72103498abddfdbc9df65179'
TOPIC_TELESWAP_UNFILLED_REFUNDED        = '\x43d89f9712aec80f15f6fbffce105a51a655a511170e4a251acbf979bb67b587'
TOPIC_TELESWAP_FILLER_UPDATED           = '\x794454db33e02ae5d0f48c7815f4eeac46e5b836766949ed362cda805aedebf1'
TOPIC_TELESWAP_MAX_CLAIM_FEE_UPDATED    = '\x70f752aa5d8bd2bde0f68a81c233171d6c3fb73c9f8509bff85495a20bb1d1f3'
-- ===== PolyConnector topics =====
TOPIC_TELESWAP_NEW_SWAP_AND_UNWRAP      = '\x124f82fb68081b8c772a74ce98c0c92b659dd79e4fd3f03cf49988818eb04e8b'
TOPIC_TELESWAP_NEW_SWAP_AND_UNWRAP_UNIV = '\x33d28a02b6f25171e40ef509e2b97bfd82260ef601512c16c75e032dd9d88aa0'
TOPIC_TELESWAP_NEW_SWAP_AND_UNWRAP_RUNE = '\x13a9049471d86bfc267b825d08be20c5ebfc793c109c11eb159af6781cda3105'
TOPIC_TELESWAP_FAILED_SWAP_AND_UNWRAP   = '\xa79aee2abfa3037b36c3689636c9932b113a82cebda0057ac4ce2386371fc969'
TOPIC_TELESWAP_WITHDRAWN_TO_SOURCE      = '\xf43f17a174cd55d7d75e934475f1cec7890c2bf3fabbf376de3868f0d8ce6897'
TOPIC_TELESWAP_WITHDRAWN_TO_SOURCE_V2   = '\x73f04e25d893c427907bd37b5f4a3f289020af48582a9647567c143376c571e5'
TOPIC_TELESWAP_SWAP_AND_UNWRAP_FILLED   = '\xdb18ace285ac81dfb11228b778d46dd29841b5e536fa01bb0616d12fc5379143'
TOPIC_TELESWAP_FILLS_REFUNDED           = '\x9c42caed57866039a04ac9fe339f746549dc727ea54579b01f87b5ea30d5caee'
TOPIC_TELESWAP_CLAIM_FILLS_REJECTED     = '\x72ca618d6b1478954424f1c82d42e7b44cb03787bde71f7aad7ca8825ea96c10'
-- ===== Router, locker, teleBTC, relay topics =====
TOPIC_TELESWAP_NEW_WRAP                 = '\xdebe45dc811f213ee5572218ab9c9e7d78fac393b0ca5c50ea9edbe5c8bcb617'
TOPIC_TELESWAP_NEW_WRAP_V2              = '\x17ca0df5e76383e7d49ba70b93df7e5e530906b8c9a35f3a913fe01a369814bc'
TOPIC_TELESWAP_NEW_WRAP_AND_SWAP_V2     = '\x49235eee15ff9b68c03c5efd6133fb7c0b976247122a03209c2cb97aabd5558b'
TOPIC_TELESWAP_FAILED_WRAP_AND_SWAP_V2  = '\x5832c9b125078499c9ab7dcc61594c25e4a33febb062486a4ff3c7a1d272bbdd'
TOPIC_TELESWAP_REQUEST_FILLED_V2        = '\xf2de1389799f0ec6ba8aa31dc85397078c1cdf33a39d903c8463f87260617697'
TOPIC_TELESWAP_FILLER_REFUNDED          = '\xa691ee9f18c723075ade0e555d96de55c74e3e7b7cddc63a0ecbbff7ee6352e7'
TOPIC_TELESWAP_REFUND_PROCESSED         = '\x79bab54e96d1977794ba96251faf4af21e4c1e824335ed0e33ad672cc463194b'
TOPIC_TELESWAP_NEW_UNWRAP               = '\x6b5c22e69db87534a562352580358411dc7b2d98d24684765342f2ebf2dd8c31'
TOPIC_TELESWAP_PAID_UNWRAP              = '\x7b8cb33b1d4dc1e5d05c58e9945c383eb161ac22029c5b963989d08c3d0ef4da'
TOPIC_TELESWAP_BURN_DISPUTE             = '\x58c23b4ae0617be275628875bcfd65759a441263099a256eeb27899fb5dd846d'
TOPIC_TELESWAP_LOCKER_DISPUTE           = '\x7ff138134e34ccab071315c38e38eec079f54726b890304ab46e2c5ab6f722bb'
TOPIC_TELESWAP_MINT_BY_LOCKER           = '\x8ad706b338c5d2a20b0d038b5cfdaf2b2f943f43048723bde0dccdf129598a11'
TOPIC_TELESWAP_BURN_BY_LOCKER           = '\x66fb54322c407b04a077a306e72cdd780f0f374ba5dac9f6901a56a6255bc34a'
TOPIC_TELESWAP_LOCKER_SLASHED           = '\x5e4485631c54370ddbcded30559851c5dd670a232b8a7502b9d0b47ba9090d47'
TOPIC_TELESWAP_LOCKER_LIQUIDATED        = '\x19ac06de95d67912d84cd839d617200570c30562b34ba4f6a3a19fbd14a8f9a9'
TOPIC_TELESWAP_MINTER_ADDED             = '\x6ae172837ea30b801fbfcdd4108aa1d5bf8ff775444fd70256b44e6bf3dfc3f6'
TOPIC_TELEBTC_MINT                      = '\xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8'
TOPIC_TELEBTC_BURN                      = '\xbac40739b0d4ca32fa2d82fc91630465ba3eddd1598da6fca393b26fb63b9453'
TOPIC_TELEBTC_BLACKLISTED               = '\xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855'
TOPIC_TELESWAP_RELAY_BLOCK_FINALIZED    = '\x4fec6ffa2052e80db9daadc2384a8f634057472e28ea7f1bd3eebfc92b5b0f8e'
TOPIC_UPGRADED                          = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED                     = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_OWNERSHIP_TRANSFERRED             = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== Selectors =====
SEL_TELESWAP_SWAP_AND_UNWRAP            = '\x201c527c'
SEL_TELESWAP_SWAP_AND_UNWRAP_V2         = '\x628270eb'
SEL_TELESWAP_SWAP_AND_UNWRAP_UNIVERSAL  = '\x966ca0ac'
SEL_TELESWAP_SWAP_AND_UNWRAP_RUNE       = '\xfa4df506'   -- historical (not in the 2026-10-04 implementation)
SEL_TELESWAP_SWAP_AND_UNWRAP_VIA_FILLER = '\x2bd3fe8c'
SEL_TELESWAP_CLAIM_FILLS                = '\x8ea75fa6'
SEL_TELESWAP_FILL_SWAP_AND_UNWRAP       = '\x7a9d3080'   -- PolyConnector
SEL_TELESWAP_SET_FILLER                 = '\x18bbee8d'
SEL_TELESWAP_HANDLE_ACROSS_MESSAGE      = '\x3a5be8cb'
SEL_TELESWAP_CONNECTOR_EMERGENCY_WDRAW  = '\xe63ea408'
SEL_TELESWAP_EXCHANGE_EMERGENCY_WDRAW   = '\x95ccea67'
SEL_TELESWAP_SET_ACROSS_ADMIN           = '\x878269b5'
SEL_TELESWAP_SET_BRIDGE_CONNECTOR_MAP   = '\xb55d3633'
SEL_TELESWAP_WRAP                       = '\xb866d6ea'
SEL_TELESWAP_WRAP_V2                    = '\x276edfe0'
SEL_TELESWAP_WRAP_AND_SWAP_V2           = '\x2554a14c'
SEL_TELESWAP_FILL_TX_V2                 = '\x29b0db8b'
SEL_TELESWAP_UNWRAP                     = '\x3fea4367'
SEL_TELESWAP_BURN_SWAP_AND_UNWRAP       = '\x44dd6aa5'
SEL_TELESWAP_BURN_PROOF                 = '\xea732637'
SEL_TELESWAP_DISPUTE_BURN               = '\x73532b2a'

-- ===== Connectors (network-specific) =====
ETH_TELESWAP_CONNECTOR                  = '\xfa1b28052bd8087b1cf64ee9429feb324e95b0ff'
BASE_TELESWAP_CONNECTOR                 = '\xec4a7d93750bbce2a07fd1bc748507ea645e9d52'
ARB_TELESWAP_CONNECTOR                  = '\xec4a7d93750bbce2a07fd1bc748507ea645e9d52'
OP_TELESWAP_CONNECTOR                   = '\xec4a7d93750bbce2a07fd1bc748507ea645e9d52'
POLY_TELESWAP_POLY_CONNECTOR            = '\xe0166434a2ad67536b5fdafcc9a6c1b41cc5e085'
BNB_TELESWAP_POLY_CONNECTOR             = '\x9b95dc17acfd8e028f192971165ae7be76e6a954'
-- ===== Polygon home chain =====
POLY_TELESWAP_CC_TRANSFER_ROUTER        = '\x04367d74332137908bef9acc0ab00a299a823707'
POLY_TELESWAP_CC_EXCHANGE_ROUTER        = '\xd1e9ff33ec28f9dd8d99e685a2b0f29dcaa095a3'
POLY_TELESWAP_BURN_ROUTER               = '\x0009876c47f6b2f0bcb41eb9729736757486c75f'
POLY_TELESWAP_LOCKERS                   = '\xf5d6d369a7f4147f720aeadd4c4f903ae8046166'
POLY_TELEBTC                            = '\x3bf668fe1ec79a84ca8481cead5dbb30d61cc685'
POLY_TELESWAP_BITCOIN_RELAY             = '\x7deb66341b1d499d7e699589d0cf665de4132ea3'
-- ===== BNB home chain =====
BNB_TELESWAP_CC_TRANSFER_ROUTER         = '\xa38ad0d52b89c20c2229e916358d2ceb45bec5ff'
BNB_TELESWAP_CC_EXCHANGE_ROUTER         = '\xca5416364720c7324a547d39b1db496a2dcd4f0d'
BNB_TELESWAP_BURN_ROUTER                = '\x2787d48e0b74125597dd479978a5de09bb9a3c15'
BNB_TELESWAP_LOCKERS                    = '\x84f74e97ebab432cee185d601290ce0a483987a5'
BNB_TELEBTC                             = '\xc58c1117da964aebe91fef88f6f5703e79bda574'
BNB_TELESWAP_BITCOIN_RELAY              = '\xfcd688999c25d5493571543137ceeb4fbdb44d02'
-- ===== Admin wallets (EOAs; same address on every TeleSwap chain) =====
ETH_TELESWAP_PROXY_ADMIN_EOA            = '\x4565ae5c90e52c058410fc7f05711ffed9b6e62a'
ETH_TELESWAP_OWNER_EOA                  = '\x24004f4f6d2e75b039d528e82b100355d8b1d4fb'
ETH_TELESWAP_ACROSS_ADMIN_EOA           = '\x144c5fb302dbaa789fc59bbec301169eaa56c5fc'
ETH_TELESWAP_FILLER                     = '\x4a00edf7f07ecb48a4a3fd798e0fb79d90ef21a9'   -- also Base; EIP-7702 delegated account
-- Avalanche (43114) and Robinhood (4663): no TeleSwap contract
```

---

## 11. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified ABIs on Blockscout: `EthConnectorLogic` (Ethereum implementation `0xe5a2357b7e6f2fd1f21d6aa7880084c2cf828548`; the new filler-path events and functions from the implementation `0x756B770b38c03B0A249Aef5FE6e06F9B34a3D431`, verified 2026-10-04, and the Polygon `PolyConnectorLogic` `0x58733ad7414d01aB28c6845E2B4872bCC10a4E42`), `PolyConnectorLogic`, `CcTransferRouterLogic`, `CcExchangeRouterLogic`, `BurnRouterLogic`, `LockersManagerLogic`, `BitcoinRelay` and `TeleBTCLogic` (the Polygon implementations of §5). The table rows were generated from those ABIs with their parameter names. `MsgSent`, `MsgReceived`, `NewSwapAndUnwrap`, `NewSwapAndUnwrapUniversal`, `FailedSwapAndUnwrap`, `WithdrawnFundsToSourceChain`, `NewUnwrap`, `PaidUnwrap`, `NewWrapAndSwapV2`, `RequestFilledV2`, `FillerRefunded`, `FailedWrapAndSwapV2`, `RefundProcessed`, `MintByLocker`, `BurnByLocker` and teleBTC `Burn` were also seen in live logs (below).
- **Addresses:** from `TeleportDAO/teleswap-cli` `assets/config/contracts.json` (connectors per chain; Polygon and BSC `contracts` blocks), the teleBTC addresses from the tokens that the BurnRouters move, and `eth_getCode` on all eight chains. Implementations and admins read from the EIP-1967 slots; `owner()`, `across()`, `acrossAdmin()`, `currChainId()` read live; `eth_getCode` of the admin, owner and `acrossAdmin` = `0x` (EOAs).
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC** (all logs of each address):
  - EthConnector: Ethereum 135 `MsgSent`; Base 11 `MsgSent`; Arbitrum 13 `MsgSent`; Optimism 0 logs. No `MsgReceived` or `WrappedAndSwappedToDestChain` on any EthConnector.
  - BNB: PolyConnector 165 logs (`MsgReceived` 82, `NewSwapAndUnwrap` 79, `NewSwapAndUnwrapUniversal` 2, `FailedSwapAndUnwrap` 1, `WithdrawnFundsToSourceChain` 1); BurnRouter 363 (`NewUnwrap` 192, `PaidUnwrap` 171); CcExchangeRouter 691 (`NewWrapAndSwapV2` 250, `FillerRefunded` 199, `RequestFilledV2` 194, `FailedWrapAndSwapV2` 24, `RefundProcessed` 24); LockersManager 466 (`MintByLocker` 274, `BurnByLocker` 192); CcTransferRouter 0.
  - Polygon: PolyConnector 154 logs (`MsgReceived` 77, `NewSwapAndUnwrap` 76, `NewSwapAndUnwrapUniversal` 1); BurnRouter 181 (`NewUnwrap` 94, `PaidUnwrap` 87); CcExchangeRouter 282 (`NewWrapAndSwapV2` 122, `RequestFilledV2` 75, `FillerRefunded` 75, `FailedWrapAndSwapV2` 5, `RefundProcessed` 5); LockersManager 221 (`MintByLocker` 127, `BurnByLocker` 94); CcTransferRouter 0.
  - Avalanche and Robinhood: no contract.
- **Sample transactions (receipts read):** Ethereum `0x8305510a6d6bd655d1b9ff7187c6ef12264aec4c97eb26316196398d8cf66701` (block 26,072,266; Rango Diamond calls the connector with 0.0243 ETH; `MsgSent`; WETH `Deposit` into the Across SpokePool; Across `FundsDeposited` with `destinationChainId` 56). BSC `0x59445ba9e48caff9187d152bdaee75dfa47f3a070690d783b9244afc5e6047dc` (block 124,425,555; Across `FilledRelay` from origin 42161; USDT relayer to PolyConnector; `MsgReceived`; USDT to the BurnRouter; swap to teleBTC; `BurnByLocker` and teleBTC `Burn`; `NewUnwrap`; `NewSwapAndUnwrap`).

Authoritative sources:
- [TeleportDAO/teleswap-cli `assets/config/contracts.json`](https://github.com/TeleportDAO/teleswap-cli/blob/HEAD/assets/config/contracts.json) — official addresses per chain.
- [TeleportDAO/btc-evm-bridge-contracts](https://github.com/TeleportDAO/btc-evm-bridge-contracts) — BitcoinRelay source and deployments.
- Verified sources — [EthConnectorLogic (Ethereum)](https://eth.blockscout.com/address/0x756b770b38c03b0a249aef5fe6e06f9b34a3d431) · [previous EthConnectorLogic](https://eth.blockscout.com/address/0xe5a2357b7e6f2fd1f21d6aa7880084c2cf828548) · [PolyConnectorLogic (Polygon)](https://polygon.blockscout.com/address/0x58733ad7414d01ab28c6845e2b4872bcc10a4e42) · [PolyConnectorProxy (Polygon)](https://polygon.blockscout.com/address/0xE0166434A2ad67536B5FdAFCc9a6C1B41CC5e085) · [BurnRouterProxy (Polygon)](https://polygon.blockscout.com/address/0x0009876C47F6b2f0BCB41eb9729736757486c75f) · [teleBTC (Polygon)](https://polygon.blockscout.com/address/0x3BF668Fe1ec79a84cA8481CEAD5dbb30d61cC685).
- Explorers — [Etherscan connector](https://etherscan.io/address/0xfa1b28052bd8087b1cf64ee9429feb324e95b0ff) · [BscScan PolyConnector](https://bscscan.com/address/0x9b95dc17acfd8e028f192971165ae7be76e6a954).

# Kelp DAO (rsETH) — Topics, Selectors, Addresses (Ethereum, Arbitrum, Base, Optimism, Avalanche, BNB)

**Status:** verified against live RPC on all nine target chains and the canonical `Kelp-DAO/LRT-rsETH` repo on 2026-10-30.
**Scope:** The Kelp DAO liquid-restaking token rsETH. This file covers the Ethereum core (LRTConfig, LRTDepositPool, RSETH, LRTOracle, NodeDelegators, LRTWithdrawalManager, LRTUnstakingVault, LRTConverter, FeeReceiver), the L1Vaults, the rsETH bridge layer (LayerZero OFT, Chainlink CCIP), the L2 deposit pools and wrappers, the rate providers and receivers, and the proxy admins, timelocks and pausers. Topics and selectors are chain-agnostic. Addresses are network-specific.

Kelp is an LRT on top of EigenLayer. Users deposit ETH, stETH or ETHx into **LRTDepositPool** on Ethereum and get **rsETH**. rsETH does not rebase. Its value moves only through `LRTOracle.rsETHPrice()`. The deposit pool moves funds to **NodeDelegator** contracts. Each NodeDelegator owns one EigenPod and delegates to one EigenLayer operator. EigenLayer contracts are in `eigenlayer/core.md`. This file does not repeat them.

Every core contract is an **EIP-1967 TransparentUpgradeableProxy**. Most core proxies share one ProxyAdmin `0xb61e…dc78`. A TimelockController with a **10-day** delay (`getMinDelay() = 864000`) owns that ProxyAdmin. Roles (MANAGER, PAUSER, OPERATOR, …) live in **LRTConfig** (`AccessControl`), and other contracts read roles from it.

**On L2s there is no restaking.** An L2 "deposit pool" (`RSETHPool*`) takes ETH or LST, and mints or sends a wrapped rsETH (`wrsETH`) at the bridged rate. Then it bridges the ETH to an Ethereum **L1Vault**, which deposits into LRTDepositPool and bridges rsETH back. **On 2026-04-18 an attacker forged one LayerZero message into the Ethereum `RSETH_OFTAdapter` and released 116,500 rsETH (tx `0x1ae232da…db4222`).** After the incident, Kelp paused the L2 pools. In October 2026, Kelp cleared the adapter peers for Base, Mantle and Ink. As of 2026-10-30, all four target-chain L2 pools return `paused() = true`. The adapter has a peer for Arbitrum only (of the target chains).

---

## 0. Contract families & versions

| Family | Contracts | Chain(s) | Upgradeable? |
|--------|-----------|----------|--------------|
| **Core LRT** | LRTConfig, LRTDepositPool, RSETH, LRTOracle, LRTWithdrawalManager, LRTUnstakingVault, LRTConverter, FeeReceiver, PubkeyRegistry, ChainlinkPriceOracle | ETH | EIP-1967 Transparent, ProxyAdmin `0xb61e…dc78` |
| **NodeDelegators** | 7 active (index 0–6) + 5 legacy | ETH | EIP-1967 Transparent (shared impl `0xa86f…dc53`; legacy impl `0x50f8…679b`) |
| **L1Vaults** | one per L2 (Arb, Base, OP, Scroll, Linea, zkSync, Avax, …) | ETH | EIP-1967 Transparent, ProxyAdmin `0x2155…b2c1` |
| **Bridge tokens** | `RSETH_OFTAdapter` (ETH lockbox) + rsETH OFT per L2; CCIP `wrsETH` (old) + CCIP `rsETH` (new) | ETH + L2s | OFTs and CCIP tokens are **not** proxies |
| **L2 deposit pools** | `RSETHPool` (Arb), `RSETHPoolV3ExternalBridge` (Base), `RSETHPoolV2ExternalBridge` (OP), `RSETHPoolV3` (Avax) | L2s | EIP-1967 Transparent, per-chain ProxyAdmin |
| **L2 wrapper** | `RsETHTokenWrapper` = `wrsETH` (Base, OP, Avax) | L2s | EIP-1967 Transparent |
| **Rate plumbing** | `RSETHMultiChainRateProvider` (ETH, LayerZero v1 push) → `CrossChainRateReceiver` per L2; `RSETHRateProvider` | ETH + L2s | not proxies |
| **KERNEL (parent DAO token)** | KERNEL + `KERNEL_OFTAdapter` (ETH), KERNEL OFT (BNB, Arb), KernelDepositPool (BNB) | ETH, BNB, Arb | noted only (§3.6); not rsETH flow |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

**✓** = seen in live logs on 2026-10-30 (Ethereum, Arbitrum or Optimism). **abi** = computed from canonical source only.

### 1.1 LRTDepositPool (deposits → rsETH mint)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x8b0422d41caf5eb583695377e98b5041a1d241a7c80483cf182b1311c48c93b7` | `ETHDeposit(address indexed depositor, uint256 depositAmount, uint256 rsethMintAmount, string referralId)` | ✓ |
| `0x07c31fccf51996f0f4ea01c3a55191786b3a8cd89f696db4d42adaa99b0e15f1` | `AssetDeposit(address indexed depositor, address indexed asset, uint256 depositAmount, uint256 rsethMintAmount, string referralId)` | ✓ |
| `0xcec1f18c3ab8ddaaa107a1591e3c369667eec613626611a8deaedef43069fcdd` | `EthTransferred(address to, uint256 amount)` (also on NodeDelegator, UnstakingVault, Converter) | ✓ |
| `0xdfcec2e5d46add579374c8b094c104992049258e32c4b148984940d21f023308` | `ETHSwappedForLST(uint256 ethAmount, address indexed toAsset, uint256 returnAmount)` | ✓ |
| `0x7451d505154bc4c8b1e59836620cede167f0193aa10fb24874a542c3fe6617be` | `AssetSwappedForETH(address indexed fromAsset, uint256 fromAssetAmount, uint256 returnAmount)` | abi |
| `0x5219ad022ed49bbef4ed3dc91bc3f97e9178b1bf3bee0d858975dc68fce3c1c7` | `AssetStaked(address indexed asset, uint256 ethAmount, uint256 stETHShares)` | ✓ |
| `0xfd16a45cd4651308537df39d9e87cf1522559f7d33fc45ad18e458bb77bd498c` | `NodeDelegatorAddedinQueue(address nodeDelegatorContracts)` | abi |
| `0xb17adb7f863ad4dced68bd4045e81e087cb8c5b536bf2dbda6c8176e5fc593b9` | `NodeDelegatorRemovedFromQueue(address nodeDelegatorContracts)` | abi |
| `0x44a9f72c31db7b99a131a49de95fe2420c60e9fe9bff0a1a13d47b4af14566b4` | `MaxNodeDelegatorLimitUpdated(uint256)` | abi |
| `0x1bba2f1175afe384c3b2efde45f19740b744459c61a7700994196fe4d84af176` | `MinAmountToDepositUpdated(uint256)` | abi |
| `0xae34faed95cd4022e6c7e9bb4219e7f69d343fcf210c8893cb520fa603e7d177` | `MaxNegligibleAmountUpdated(uint256)` (also LRTConfig) | ✓ |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` (OZ; every pausable Kelp contract) | ✓ |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | ✓ |

### 1.2 LRTWithdrawalManager (rsETH → ETH / stETH / ETHx exits)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xd1ff36888873897951eaf991bca7db625b8ed70bf2b0d54441907bdab02b08d7` | `AssetWithdrawalQueued(address indexed withdrawer, address indexed asset, uint256 rsETHUnstaked, uint256 indexed userNonce)` | ✓ |
| `0x72e38cd9e650a56d27bba7e1a9a8d6f77dc5cc382bb38a7e56f4f1e845be910d` | `AssetUnlocked(address indexed asset, uint256 rsEthAmount, uint256 assetAmount, uint256 rsEThPrice, uint256 assetPrice)` | ✓ |
| `0xca13475b00c46ee0ce4a479bd18ed747ff89395e96e93779ba7f18cbe1735fb4` | `AssetWithdrawalFinalized(address indexed withdrawer, address indexed asset, uint256 amountBurned, uint256 amountReceived)` | ✓ |
| `0x1ef19e60b6aa420db7b5d27b0e4b961d6bfaaca7cdfc53b708a969fa93fc59ad` | `AssetWithdrawalCompletedBy(address indexed user)` (third-party completion) | abi |
| `0x5e94c841c11b8b2ec5be817ed833f18a2bbbe626e93b79121a1dcf072e33e6a2` | `InstantWithdrawalFeeCollected(address indexed user, address indexed asset, uint256 fee)` | ✓ |
| `0xca2245f2aaa9833d42448c503592e50a442e18ee2614801ddb97b8e94fe29783` | `ReferralIdEmitted(string referralId)` | ✓ |
| `0x1d57945c1033a96907a78f6e0ebf6a03815725dac25f33cc806558670344ac88` | `EtherReceived(address indexed depositor, uint256 ethAmount, uint256 sharesAmount)` | abi |
| `0x8e49c7e8c48118c23032fbd2aff8536fbfc3e2dde502b8047c992d24ae7086b7` | `InstantWithdrawalEnabledUpdated(address indexed asset, bool enabled)` | ✓ |
| `0x0f636a2a0c913b7b5fedce90f3c0781888ea22262fe8a82cdc42697f5d2b3e07` | `InstantWithdrawalFeeUpdated(uint256 feeBasisPoints)` | abi |
| `0xc0c498d67fa44a29111cc33bd5b1e5faa8f2706a8c4c7896424b5e8b095e1bd0` | `InstantWithdrawalFeeRecipientUpdated(address indexed feeRecipient)` | abi |
| `0x2e56f6093fb947ef7b002dcdf68fcb314c466a1917eac6fa5b00879a7f5de63f` | `WithdrawalDelayBlocksUpdated(uint256)` | abi |
| `0xde4ed37901dc230db7df5ec2ec48bb07c4286fa1c66128cd200c6b6e9cd2bc83` | `MinAmountToWithdrawUpdated(address asset, uint256 minRsEthAmountToWithdraw)` | abi |
| `0xf975e0c3a3f04699da0241f155fd8d6fc793424ddab873f57902f5b89f90b031` | `TreasuryWithdrawalSettled(address indexed asset, uint256 amount)` | abi |
| `0x9e6d6426139112f2098413fde7208e63143a55f9f75ebb54cd5afe343ce2b5f4` | `RemainingAssetsSwept(address indexed asset, uint256 amount, address indexed treasury)` | abi |
| `0xf32daedb73c68e079a4a5434ded6b18648de9901ad3101754291d02566aac2c1` | `AaveIntegrationConfigured(address indexed aavePool, address indexed aaveWETHGateway, address indexed aaveAWETH, address aaveDataProvider)` | abi |
| `0xc7057e02122c3caa921d5343967cda143d24b58e4d828bd0ba276f11e5074c41` | `AaveIntegrationEnabled(bool enabled)` | abi |
| `0x23afb4775630a4b5d4b5741b522d6475234cfc624f63362e712133dfc4f35334` | `ETHDepositedToAave(uint256 amount, uint256 totalDeposited)` | abi |
| `0x69750abe9cb5aee84210b9d8ccc7f01228f72e8597cb0cebda17a4e611e70b30` | `ETHWithdrawnFromAave(uint256 amount, uint256 totalDeposited)` | ✓ |
| `0x75181a9ad4baf1efcf51afbb3478053a3f2e17d4fc029e03e1443517b455f4e5` | `InterestCollectedToTreasury(uint256 interestAmount, address indexed treasury)` | abi |
| `0x8ebd2411899f728c570082f57617505c75fc872dfe7615529dff7efaaafcd945` | `EmergencyWithdrawFromAave(uint256 amount, address indexed recipient)` | abi |
| `0xfddc6dce6f8d23f96f6a312e3548e3314f2926506ad95f221d1c5c16e71079a2` | `AaveDepositFailed(uint256 amount, bytes reason)` | ✓ |

> The withdrawal manager puts idle unlocked ETH into Aave V3 (WETH gateway). `ETHWithdrawnFromAave` fires on most user claims.

### 1.3 RSETH token

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ✓ |
| `0x14dc9fbc0cec3c9737347af811749e92b1c9554af08194cb7774c43192a74643` | `UserTransfersBlocked(address indexed user, uint256 until)` (freeze) | ✓ |
| `0xedcd49030ac6d3af7cca7623917ba88f408bb1e8fa6980db52293707ef6c4601` | `FrozenFundsRecovered(address indexed from, address indexed to, uint256 amount)` | abi |
| `0xcb16112dbd42611696c17aac7aa2fb48fbe66c992d92226599939cce873fade0` | `CustodyAddressUpdated(address indexed newCustodyAddress)` | abi |
| `0x294995cd5111fb06dc5673fba6968fbc635c1388bff60a3fefec78656efadae9` | `PermanentExemptionAdded(address indexed account)` | abi |
| `0x6fe5d68e27092584d910a7a45a3bebc097f4c9d17980f5a94c08214a3d11c6f0` | `MaxMintAmountPerDayUpdated(uint256)` | abi |
| `0x509c3ee5334e8a1143fe9c0b8eeeb0e8cbb58d43ddd5031d541e458df9361782` | `PeriodStartTimeSet(uint256)` | abi |
| `0x9cf19cefd9aab739c33b95716ee3f3f921f219dc6d7aae25e1f9497b37889150` | `UpdatedLRTConfig(address indexed lrtConfig)` (every `LRTConfigRoleChecker` contract) | abi |

> The current RSETH impl has a daily mint cap, a transfer freeze per user, and a "recover frozen funds to custody" path. A `UserTransfersBlocked` or `FrozenFundsRecovered` event is an incident-response action.

### 1.4 LRTOracle (rsETH price)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x8d3b19635cf6f25b423571483e205b44b40c0c8f35f76e22089c6750c717bf17` | `RsETHPriceUpdate(uint256 newPrice, uint256 oldPrice)` | ✓ |
| `0xbbc316f92387a82e2f88e54dbef5d256aff3e9ea87e87bbd9bdba9d48c769941` | `FeeMinted(address treasury, uint256 rsethAmount)` (protocol fee as new rsETH) | ✓ |
| `0x06c8ec6bdfc53639a00f9f1ff3e965171713883dd4c782323cb19fbe227d1205` | `RsETHPriceDecrease(uint256 newPrice, uint256 oldPrice)` (**loss signal**) | abi |
| `0x4419499b183ea1ccf98bbba5b6d9b711cebefe6709bfbb130d52888544bf4b63` | `RsETHPriceBelowPeak(uint256 highestRsethPrice, uint256 newPrice)` | abi |
| `0x72ac677bb38d8bb6988cfebe29d6caef19753725c2dc2c54edc2c22ed79dcaa6` | `AssetPriceOracleUpdate(address indexed asset, address indexed priceOracle)` | abi |
| `0xd89c3aeacf5a0bdb06ee7d8b44ed4e15174ebee9d916d6cf9fdeb7bbab510bd1` | `PricePercentageLimitUpdate(uint256 newLimit)` | abi |
| `0x30e79dbdb1f42b45bb216c3bc59d0e36149a9b6af33ef51f75f0bc25e6a37753` | `MaxFeeMintAmountPerDayUpdated(uint256 newLimit)` | abi |
| `0xe6a111f2aafe738200f9bfd00234169b599cad2250ca4083fd601df5e21dddda` | `PeriodInTimestampUpdate(uint256 newPeriod)` | abi |
| `0x873a4965e324d6b8f297a11ddb8f0a02a2a9858f45f884c69a171da994dd36cc` | `FeePeriodStartTimeSet(uint256)` | abi |

### 1.5 LRTConfig (registry, roles, supported assets)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x5de40a806536a2029221dac2c8887ac9f11952fcc1ed3d7cfb4476dd5259b740` | `SetContract(bytes32 key, address indexed contractAddr)` (**wiring change**) | ✓ |
| `0x19aab10c6a9f5d648eaa15e2d515f8dfda570ee221e7c8cb9dc07694e68005bc` | `SetToken(bytes32 key, address indexed tokenAddr)` | ✓ |
| `0x5f9b9ec4692042b3fe4e1253a4577dde538cd2ad44038126a8d1a05adefa168d` | `SetRSETH(address indexed rsETH)` | ✓ |
| `0xbaf29bfdb0c1bd100ee9f6d6c1112bcde0014c0ef8c6199c0a813d936dd6568e` | `AddedNewSupportedAsset(address indexed asset, uint256 depositLimit)` | ✓ |
| `0x671ffa25d59a14d89704ca2032a144f60b44a5acdc2cb7cad09e6fff01f33dbf` | `RemovedSupportedAsset(address indexed asset)` | ✓ |
| `0xc04446455e1f3789fca0c8aad0733e9f7d7f0f82d7d0ca5e9b7c56c9ea081ce8` | `AssetDepositLimitUpdate(address indexed asset, uint256 depositLimit)` | ✓ |
| `0x5a4b82aa5dc163fd961be3a86951c62b0002859768bb5eabf32daa25f06ab3d9` | `AssetStrategyUpdate(address indexed asset, address indexed strategy)` | ✓ |
| `0x38e229a7f3f9c329892d08eb37c4e91ccac6d12c798d394990ca4f56028ec266` | `UpdateFee(uint256 newFee)` | ✓ |
| `0x39a74d8f2d9812352ac0e95ee0e60d6927daed5709ee43a007cfd2f79d9db11c` | `SetEigenLayerRewardReceiver(address indexed)` | abi |
| `0xf1005168aea1429fe9559d51ef6caa33e6426890864e2e6e41e5d54baa7be79f` | `PausedAll(address indexed sender)` (**global pause**) | ✓ |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | ✓ |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | ✓ |

### 1.6 NodeDelegator (one per EigenPod / EigenLayer operator)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xa16ad5049bc6092f455ad47c45f18d9e3436db84fa5f1da8dcde4cb12296c03d` | `ETHStaked(bytes valPubKey, uint256 amount)` (32-ETH validator deposit) | ✓ |
| `0x502f9a26014993a0661817f75b56d6298d587c7005e59a07cdf7a1c056010d6b` | `ETHDepositFromDepositPool(uint256 depositAmount)` | ✓ |
| `0xb41d139403f52e77e0f12eaab89e6da322c0711d5e738a30fe5427bb68d0c90d` | `ETHDepositFromUnstakingVault(uint256 depositAmount)` | ✓ |
| `0x921663a414f798537c348d06b72aad477fa6e6837598798abdcbf700efdbb185` | `AssetDepositIntoStrategy(address indexed asset, address indexed strategy, uint256 depositAmount)` | abi |
| `0xb4a86b70f2287279f5f8f45d48929f811389449b556cdd7f03aa8e0cc738dfbd` | `WithdrawalQueued(uint256 nonce, address withdrawer, bytes32[] withdrawalRoots)` | ✓ |
| `0xa302909a05495b640894a6ba8e0be85f973745e9356745d3e16d0ac9bc93f41c` | `EigenLayerWithdrawalCompleted(address indexed depositor, uint256 nonce, address indexed caller)` | ✓ |
| `0x645e52ee0ce5c05d60f4b051028f29630be7001f5d84cba67fe6872db872cff8` | `AssetTransferred(address asset, address to, uint256 amount)` | ✓ |
| `0xbfe611b001dfcd411432f7bf0d79b82b4b2ee81511edac123a3403c357fb972a` | `ETHReceived(address indexed sender, uint256 amount)` | ✓ |
| `0xcdc82cfed67d9b46d3a15dd3b48745fb894a354d554cb5da5fb8c440f85c108e` | `EigenPodCreated(address indexed eigenPod, address indexed podOwner)` | abi |
| `0x9e76604d3ca069af191a0f9f6cc8c7f8013191b7ae7ff82eaa75600bbca70101` | `ElSharesDelegated(address indexed elOperator)` | abi |
| `0x2167dd2914464f62e3f9655115a6a0cdc6fcf4cb13213ff53d564a47f0423dab` | `Undelegated()` (**operator change**) | abi |
| `0x930e910be2f2f33461c4037de77a567ebffbd3671d2783cf958d661c823f6672` | `ExtraStakeReceived(uint256 amount)` | abi |

### 1.7 LRTUnstakingVault, LRTConverter, FeeReceiver

| topic0 | Event | Emitter | ✓ |
|--------|-------|---------|---|
| `0x85177f287940f2f05425a4029951af0e047a7f9c4eaa9a6e6917bcd869f86695` | `EthReceived(address sender, uint256 amount)` | UnstakingVault | abi |
| `0x209fb32ef504f731c78d0fd081288e37282caf200937a50c666c640efae68616` | `QueuedWithdrawalsBufferUpdated(address indexed asset, uint256 buffer)` | UnstakingVault | abi |
| `0x9d3cc1d3c08d81038be85ca3969e3f2e0d36b5e8d0e7b3e2de79cb85dd433a7c` | `MaxUncompletedWithdrawalCountSet(uint256)` | UnstakingVault | abi |
| `0x3d50e9135252ad1ece4be4369a9e416df319af230b8d161d3ae7902f5a531861` | `UncompletedWithdrawalCountSet(uint256)` | UnstakingVault | abi |
| `0x8d29c3cc4ecd5557acf0513e125eccf06f4c6f9f5ec12c5baa5ba7eac2a9458e` | `UnstakeStETHStarted(uint256 tokenId)` (Lido queue NFT) | Converter | ✓ |
| `0x5d5fdc94abc691d6fb4e699a6aacafbc8c83a13bdfbd183a271e1d1f1c5ac025` | `UnstakeSwETHStarted(uint256 tokenId)` | Converter | abi |
| `0xa36e002c92e491a9411aa72713848cc138ea6a18fdea3168a62dbcb83d6e0927` | `WithdrawalIntentDeclared(address indexed user, uint256 amount)` | Converter | ✓ |
| `0x995d2434d36c9bceaab42c56efe51e8ffe41fd11cabefd9e2cb83700d8b2035e` | `UserWhitelisted(address indexed user, bool whitelisted)` | Converter | ✓ |
| `0x027e48add3b437ce86a602242c3cda154148d40a76766adb87459f48d7326a6d` | `ConvertedEigenlayerAssetToRsEth(address indexed receiver, uint256 rsethAmount, bytes32 withdrawalRoot)` | Converter | abi |
| `0x1383e8657823f68fdbf6091cd5234d51fae3a863c8c16bfada4903bab9172f6b` | `MevRewardsAddedToTVL(uint256 amount)` (EL rewards → TVL) | FeeReceiver | ✓ |

### 1.8 L1Vault (Ethereum side of each L2 pool)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x55c5b9018ac82d4c9801a9f0eee23adbb72e308016432c7c542eeb006fd7da28` | `ETHDepositForL1Vault(uint256 depositAmount, uint256 rsethMintAmount)` | abi |
| `0xe734f7bf18b7bba55235167440b1bc77a573b648fa3a888df7ef484178ded05b` | `AssetDepositForL1Vault(address indexed asset, uint256 depositAmount, uint256 rsethMintAmount)` | abi |
| `0x48e35858de924f81ed12208a490444b2d42f2447c5c7439c2e5ab2dff5d48360` | `BridgedRsETHToL2(uint32 lzChainId, address l2Receiver, uint256 amount, uint256 minAmount)` (LayerZero) | ✓ |
| `0x9ab125f8a8fd7c6a52702f7fa4074ce46212529eaaffc91f2093a1e5dd5e74b8` | `BridgedRsETHToL2UsingCCIP(uint64 indexed destinationChainSelector, address indexed l2Receiver, uint256 amount, bytes32 messageId)` | ✓ |
| `0x8c58fe5d12b05676ead07e9646a61b2555d6b1480cb4f22eec320fad6041836a` | `BridgeTypeSet(uint8 bridgeType)` (0 = LayerZero, 1 = CCIP) | ✓ |
| `0x2cefedd44f218655032bb016b14231da221f1b97a2746ab936364711aa187627` | `DestinationChainSelectorSet(uint64)` | ✓ |
| `0x4b6edc08984698e63b0e261e9f3c7b76124110440d417aeb44d39fcb103f7bba` | `CCIPRouterSet(address)` | ✓ |
| `0x129a6c104a8100fe74d74d6905926ad04161e85fedfb070261416c5e630b190b` | `CcipGasLimitSet(uint256)` | ✓ |
| `0xb6c113d359f5e43fbd9e4b7cca7e332c60905ab3298c77dd6da5f3b95b29eb51` | `WstETHSet(address)` | ✓ |

### 1.9 rsETH bridge tokens (LayerZero OFT / OFTAdapter, CCIP)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xfff873bb909b73d08a8c1af4b21779e87103bb8ea8cf3b3a0067eb8526b8b80a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountLD)` (**4-arg early LZ v2 form**) | ✓ |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountLD)` (**the 2026-04-18 drain event**) | ✓ |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` (peer = 0 → route closed) | ✓ |
| `0xbe4864a8e820971c0247f5992e2da559595f7bf076a21cb5928d443d2a13b674` | `EnforcedOptionSet((uint32,uint16,bytes)[])` | abi |
| `0xf0be4f1e87349231d80c36b33f9e8639658eeaf474014dee15a3e6a4d4414197` | `MsgInspectorSet(address)` | abi |
| `0xd48d879cef83a1c0bdda516f27b13ddb1b3f8bbac1c9e1511bb2a659c2427760` | `PreCrimeSet(address)` | abi |
| `0xe19260aff97b920c7df27010903aeb9c8d2be5d310a2c67824cf3f15396e4c16` | `Transfer(address indexed from, address indexed to, uint256 value, bytes data)` (ERC-677; CCIP `wrsETH`) | abi |

> The deployed OFTs use the **4-argument** `OFTSent`. The LayerZero v2 GA form `OFTSent(bytes32,uint32,address,uint256,uint256)` = `0x85496b76…fe59a` is **not** emitted by the ETH adapter or the Arbitrum OFT. Watch the 4-arg topic. DVN config changes come from the LayerZero EndpointV2 (`0x1a44…728c`), see `layerzero/`.

### 1.10 L2 deposit pools (`RSETHPool*`) and wrapper (`RsETHTokenWrapper`)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x6fc20b1cf8f9d1126dbd5964e2517cd71083acf40aed30fb6e0c4850d251c94f` | `SwapOccurred(address indexed user, uint256 rsETHAmount, uint256 fee, string referralId)` (ETH deposit) | ✓ |
| `0x0f2e7cff0bc0ea332563f60ed17d4f0f03e5f0c8eecc1271deebe1f0073b2529` | `SwapOccurred(address indexed user, uint256 rsETHAmount, uint256 fee, string referralId, address indexed depositedToken)` (token deposit; V3) | abi |
| `0x86309324fbc587b17369c0b6d4553fc187b85fd11a9a15d98d86dc274cb48a04` | `ReverseSwapOccurred(address indexed user, address indexed rsETH, address indexed token, uint256 rsETHAmount, uint256 tokenAmount)` (V3) | abi |
| `0xc88d3cb9d2245978f77db2a015d4d9964aee2e1a40c11c48e327244295eb95c6` | `ReverseSwapOccurred(address indexed user, address indexed rsETH, uint256 rsETHAmount, uint256 tokenAmount)` (V2) | abi |
| `0x2bfc0ed497a2253b9aa4e4a88269dcc8efa7489803743d7cfa748ec9c241c6d7` | `BridgedETHToL1(uint32 indexed lzChainId, address indexed l1Receiver, uint256 amountSent, uint256 amountReceived)` (Stargate) | ✓ |
| `0x12aba247ace0f7647709010832c60c00d18dc6f13457365d372e1dc0e660c1b8` | `BridgedETHToL1ViaNativeBridge(address indexed l1Receiver, uint256)` | abi |
| `0x5ee509f36cba18bdc55d58e512d4a0d97a2ce255463939d2883a674697c65a99` | `BridgedTokenToL1(address indexed token, address indexed l1Receiver, uint256 amountSent)` | abi |
| `0x52f82c8bf940e02934eb4517dd40f665fd2b0fa3f1d03a1e40edb3d4a12582ed` | `AssetsMovedForBridging(uint256)` | abi |
| `0x7493a63b680cd0d3326c9e387c9e325f1eb18423ba82e0f16da673fc7b7b75d7` | `AssetsMovedForBridging(uint256, address indexed token)` | abi |
| `0x9800e6f57aeb4360eaa72295a820a4293e1e66fbfcabcd8874ae141304a76deb` | `FeesWithdrawn(uint256 feeEarnedInETH)` | abi |
| `0x812bcf6853ebc81dc0a1d2323893eedad6cd086a4398311a699e0a7acdf187b3` | `FeesWithdrawn(uint256, address token)` | abi |
| `0x4f78c4ceb393a616bbd264a4584a9ad15d722042ce1e135e6a8380217f5cb42b` | `FeeBpsSet(uint256)` | abi |
| `0xd3450cfe4bfe879ec69b0a93239482844018e6ae06a421fa83820a3a19e14419` | `DailyMintLimitSet(uint256)` | abi |
| `0x3f32684a32a11dabdbb8c0177de80aa3ae36a004d75210335b49e544e48cd0aa` | `OracleSet(address)` | abi |
| `0x7cfff908a4b583f36430b25d75964c458d8ede8a99bd61be750e97ee1b2f3a96` | `Deposit(address indexed asset, address indexed sender, address indexed receiver, uint256 amount)` (wrapper: bridged rsETH → wrsETH) | abi |
| `0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7` | `Withdraw(address indexed asset, address indexed sender, address indexed receiver, uint256 amount)` (wrapper: wrsETH → bridged rsETH) | abi |
| `0xfa396b61e1bfcb3145a714cb9279a51e3bb287e7c37f943e492901393218ca63` | `BridgerDeposited(address indexed asset, address indexed bridger, uint256 amount)` | abi |
| `0x1f986373bb2007b5434e7e2fc7945d35e981b7bbf2e8bd57876be193653aba9b` | `WithdrawalAdded(bytes32 indexed txHash)` (HashStorage) | abi |
| `0x628368f27d5c80a9da51e0a2c3de562795c65760050eaf839c13da61b439b07c` | `WithdrawalClaimed(bytes32 indexed txHash)` (HashStorage) | abi |

### 1.11 Rate provider / receiver, proxy and timelock

| topic0 | Event | Emitter | ✓ |
|--------|-------|---------|---|
| `0xe65c987b2e4668e09ba867026921588005b2b2063607a1e7e7d91683c8f91b7b` | `RateUpdated(uint256 newRate)` | MultiChainRateProvider (ETH) and each RateReceiver (L2) | ✓ |
| `0x00fad0fee0b60ff385f6873c27a2249190a10505cc95e310241580b50712a201` | `RateReceiverAdded(uint16 newChainId, address newContract)` | MultiChainRateProvider | ✓ |
| `0xbdfb596025f3c8785cf2659a6b5cfa6cbda8f98c9941b836110d632b747b718a` | `RateReceiverRemoved(uint16, address)` | MultiChainRateProvider | abi |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every proxy | ✓ |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | every proxy | ✓ |
| `0x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca` | `CallScheduled(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data, bytes32 predecessor, uint256 delay)` | TimelockController | ✓ |
| `0xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58` | `CallExecuted(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data)` | TimelockController | ✓ |
| `0xbaa1eb22f2a492ba1a5fea61b8df4d27c6c8b5f3971e63bb58fa14ff72eedb70` | `Cancelled(bytes32 indexed id)` | TimelockController | abi |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 LRTDepositPool

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x72c51c0b` | `depositETH(uint256,string)` | payable; `(minRSETHAmountExpected, referralId)` |
| `0xc3ae1766` | `depositAsset(address,uint256,uint256,string)` | stETH / ETHx deposit |
| `0xba5bb442` | `getRsETHAmountToMint(address,uint256)` | view |
| `0x52c4889f` | `getTotalAssetDeposits(address)` | view (TVL per asset) |
| `0x884c1056` | `getAssetCurrentLimit(address)` | view |
| `0x7969afa0` | `transferETHToNodeDelegator(uint256,uint256)` | operator; `(ndcIndex, amount)` |
| `0xb4a92e47` | `transferAssetToNodeDelegator(uint256,address,uint256)` | operator |
| `0xe1736cba` | `transferETHToLRTUnstakingVault(uint256)` | operator |
| `0xbb3cfdac` | `transferAssetToLRTUnstakingVault(address,uint256)` | operator |
| `0xa9f0c9bc` | `swapETHForAssetWithinDepositPool(address,uint256)` | operator |
| `0x693a4125` | `swapAssetForETHWithinDepositPool(address,uint256,uint256)` | operator |
| `0x19304ccf` | `addNodeDelegatorContractToQueue(address[])` | admin |
| `0x6bf8b475` | `removeNodeDelegatorContractFromQueue(address)` | admin |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | PAUSER / admin (all pausable contracts) |

### 2.2 LRTWithdrawalManager

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc5a67b01` | `initiateWithdrawal(address,uint256,string)` | burns rsETH into queue |
| `0xd3a86833` | `completeWithdrawal(address,string)` | user claim |
| `0x90b341c6` | `completeWithdrawalForUser(address,address,string)` | claim for another user |
| `0x2a25f7a9` | `instantWithdrawal(address,uint256,string)` | fee-bearing fast exit |
| `0xa2ccd14f` | `unlockQueue(address,uint256,uint256,uint256,uint256,uint256)` | operator; emits `AssetUnlocked` |
| `0x6359b872` | `getExpectedAssetAmount(address,uint256)` | view |
| `0x47204df1` | `getUserWithdrawalRequest(address,address,uint256)` | view |
| `0xec5de228` | `setInstantWithdrawalFee(uint256)` | admin |
| `0x4d50f9a4` | `setWithdrawalDelayBlocks(uint256)` | admin |
| `0xbcacc989` | `sweepRemainingAssets(address)` | admin |
| `0x7e6204e6` | `emergencyWithdrawFromAave(uint256)` | admin |

### 2.3 RSETH, LRTOracle, LRTConfig

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | MINTER_ROLE (deposit pool, oracle fee); also L2 pool/wrapper `mint` |
| `0x79cc6790` | `burnFrom(address,uint256)` | BURNER_ROLE (withdrawal manager) |
| `0xfa91e4c1` | `blockUserTransfers(address[])` | freeze |
| `0x21cdc338` | `recoverFrozenFunds(address)` | moves frozen balance to custody |
| `0xc8ae5d86` | `setCustodyAddress(address)` | admin |
| `0xca2b6c10` | `setMaxMintAmountPerDay(uint256)` | admin |
| `0xb4b46434` | `rsETHPrice()` | view (1e18 = 1 ETH) |
| `0x51ce226a` | `updateRSETHPrice()` | permissionless price push |
| `0x8b1f69e8` | `updateRSETHPriceAsManager()` | MANAGER |
| `0xb3596f07` | `getAssetPrice(address)` | view |
| `0x10e50dfa` | `updatePriceOracleFor(address,address)` | admin |
| `0x959f5667` | `setPricePercentageLimit(uint256)` | admin |
| `0xe16c7d98` | `getContract(bytes32)` | view (registry lookup) |
| `0x00b83bce` | `rsETH()` | view |
| `0x7ed77c9c` | `setContract(bytes32,address)` | admin |
| `0xde55701e` | `setToken(bytes32,address)` | admin |
| `0xea1b2816` | `setRSETH(address)` | admin |
| `0xdd608764` | `addNewSupportedAsset(address,uint256)` | admin |
| `0x73034242` | `updateAssetDepositLimit(address,uint256)` | MANAGER |
| `0x3fc3c74d` | `updateAssetStrategy(address,address)` | admin |
| `0xc0417e58` | `setProtocolFeeBps(uint256)` | admin |
| `0x595c6a67` | `pauseAll()` | PAUSER; pauses all registered contracts |
| `0x2f2ff15d` / `0xd547741f` | `grantRole(bytes32,address)` / `revokeRole(bytes32,address)` | admin |

### 2.4 NodeDelegator, UnstakingVault, Converter

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x09c0e997` | `stake32Eth(bytes,bytes,bytes32)` | operator; beacon deposit |
| `0x42e09a51` | `stake32EthValidated(bytes,bytes,bytes32,bytes32)` | operator; checks deposit root |
| `0x4798c72b` | `depositAssetIntoStrategy(address)` | operator |
| `0xeea9064b` | `delegateTo(address,(bytes,uint256),bytes32)` | admin; EigenLayer operator |
| `0x92ab89bb` | `undelegate()` | admin |
| `0xba9051b4` | `initiateUnstaking(address[],uint256[])` | operator |
| `0x1880aa2a` | `completeUnstaking((address,address,address,uint256,uint32,address[],uint256[]),address[],bool)` | operator |
| `0xa33cf7ea` | `transferBackToLRTDepositPool(address,uint256)` | operator |
| `0x1e9a6950` | `redeem(address,uint256)` | UnstakingVault → WithdrawalManager |
| `0x23f87d01` | `unstakeStEth(uint256)` | Converter; Lido queue |
| `0x2f0d3d83` | `claimStEth(uint256,uint256)` | Converter |

### 2.5 L1Vault, OFT, rate plumbing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe9a11fe7` | `depositETHForL1VaultETH()` | L1Vault; ETH → rsETH |
| `0x9a5090b1` | `depositAssetForL1Vault(address)` | L1Vault |
| `0xa8651665` | `bridgeRsETHToL2(uint256,uint256,uint256)` | L1Vault; LayerZero |
| `0xd21e5412` | `bridgeRsETHToL2UsingCCIP(uint256)` | L1Vault; CCIP |
| `0xc7c7f5b3` | `send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)` | OFT / OFTAdapter; payable |
| `0x13137d65` | `lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)` | OFT inbound (from EndpointV2) |
| `0x3400288b` | `setPeer(uint32,bytes32)` | owner |
| `0xbb0b6a53` | `peers(uint32)` | view |
| `0xc7fee63e` | `updateRate()` | MultiChainRateProvider; payable LZ v1 push |
| `0x679aefce` | `getRate()` | view (providers / receivers) |
| `0x2c4e722e` | `rate()` | view (receivers) |

### 2.6 L2 pools and wrapper

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa26e1186` | `deposit(string)` | pool; payable ETH deposit |
| `0xbfe07da6` | `deposit(address,uint256,string)` | pool; token (wstETH / WETH) deposit |
| `0x32578090` | `swapAssetToPremintedRsETH(address,address,uint256)` | V3 pools; reverse swap |
| `0x2c0f0fd0` | `swapAssetToPremintedRsETH(address,uint256)` | V2 pool (OP) |
| `0xf64f7215` | `viewSwapRsETHAmountAndFee(uint256)` | view |
| `0x513b5064` | `bridgeAssets(uint256,uint256,uint256)` | Stargate bridge to L1Vault |
| `0x37e053e1` | `bridgeAssetsViaNativeBridge()` | native bridge to L1Vault |
| `0x687b0a11` / `0x32ae10e4` | `moveAssetsForBridging()` / `moveAssetsForBridging(uint256)` | operator |
| `0x6d1ac36a` | `bridgeTokens(address)` | operator |
| `0x164e68de` | `withdrawFees(address)` | admin |
| `0x47e7ef24` | `deposit(address,uint256)` | wrapper: bridged rsETH → wrsETH |
| `0xf213159c` | `depositTo(address,address,uint256)` | wrapper |
| `0xf3fef3a3` | `withdraw(address,uint256)` | wrapper: wrsETH → bridged rsETH |
| `0xc3b35a7e` | `withdrawTo(address,address,uint256)` | wrapper |
| `0x58070cf8` | `depositBridgerAssets(address,uint256)` | wrapper; bridger role |

### 2.7 Proxy admin and timelock

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x99a88ec4` | `upgrade(address,address)` | ProxyAdmin |
| `0x9623609d` | `upgradeAndCall(address,address,bytes)` | ProxyAdmin |
| `0x01d5062a` | `schedule(address,uint256,bytes,bytes32,bytes32,uint256)` | TimelockController |
| `0x134008d3` | `execute(address,uint256,bytes,bytes32,bytes32)` | TimelockController |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` (non-empty) on `https://ethereum-rpc.publicnode.com` on 2026-10-30. LRTConfig `getContract(key)` returns the deposit pool, oracle, withdrawal manager, unstaking vault, converter, reward receiver, pubkey registry and treasury listed here.

### 3.1 Core

| Role | Address | One-liner |
|------|---------|-----------|
| **RSETH** | `0xa1290d69c65a6fe4df752f95823fae25cb99e5a7` | rsETH token (18 dec). Supply 361,475.56 on 2026-10-30 |
| **LRTConfig** | `0x947cb49334e6571ccbfef1f1f1178d8469d65ec7` | registry + roles; supported assets = stETH, ETHx, ETH (`0xeeee…eeee`) |
| **LRTDepositPool** | `0x036676389e48133b63a802f8635ad39e752d375d` | deposits; mints rsETH |
| **LRTOracle** | `0x349a73444b1a310bae67ef67973022020d70020d` | `rsETHPrice()` = 1.08315 ETH on 2026-10-30 |
| **LRTWithdrawalManager** | `0x62de59c08eb5dae4b7e6f7a8cad3006d6965ec16` | withdrawal queue + Aave idle-ETH |
| **LRTUnstakingVault** | `0xc66830e2667bc740c0bed9a71f18b14b8c8184ba` | holds ETH/LST from EigenLayer exits |
| **LRTConverter** | `0x598dbcb99711e5577ff76ef4577417197b939dfa` | stETH → ETH through the Lido queue |
| **FeeReceiver** (REWARD_RECEIVER) | `0xdbc3363de051550d122d9c623cbaff441afb477c` | EL / MEV rewards → deposit pool |
| **PubkeyRegistry** | `0x37043dc4ef0b3e84ac9a84959d54cdc77f2109bd` | validator pubkey registry |
| **ChainlinkPriceOracle** | `0x78c12cce8346b936117655dd3d70a2501fd3d6e6` | per-asset price adapter |
| **UnlockedWithdrawalsInitializer** | `0xa9b1ced1839ba07c4e8aaef45bb60c8b27b35595` | one-time migration helper |
| Protocol treasury (Safe) | `0x322f2d4bfe8280eeb713b7c51eeba42590c36f78` | receives `FeeMinted` rsETH |

EigenLayer contracts that LRTConfig points to: StrategyManager `0x8586…075a`, EigenPodManager `0x91e6…a338`, DelegationManager `0x3905…f37a`, RewardsCoordinator `0x7750…adda`. stETH strategy `0x93c4b944d05dfe6df7645a86cd2206016c51564d`. ETHx strategy `0x9d7ed45ee2e8fc5482fa2428f15c971e6369011d`. See `eigenlayer/core.md`.

### 3.2 NodeDelegators (EigenPod owners)

| Index | NodeDelegator | EigenPod | EigenLayer operator |
|-------|---------------|----------|---------------------|
| 0 | `0xfc561966ceaaa09f4d6cba4add54778c2bf1cb85` | `0xe761634256dbd5432ef999165ee6788fffacb79f` | `0xbe7d5f26f5d5f567d35a86dd4d7d02aced2d5bff` |
| 1 | `0x395884d1974a839702bcfcba176ac7871c788946` | `0xf02d53d62af4e5c1e0769c36ed0353b29b443c58` | `0xbe7d…5bff` |
| 2 | `0x79f17234746344e0365d40be50d8d43db9082c32` | `0xda3a73f0e56b6f97204031f278f43d2175b6f50d` | `0xdbed88d83176316fc46797b43adee927dc2ff2f5` |
| 3 | `0x4c798c4653b1257d5149910523d7a6eed5712f83` | `0x9686133a317d33b0ecfbf68cd6e64c5be7f39b3c` | `0xbe7d…5bff` |
| 4 | `0xee5470e1519972c3ea95249d60ebd064af2d53d3` | `0xd29107fc2e0ffbcb7982fb7adbbcffb49c2225d9` | `0xbe7d…5bff` |
| 5 | `0x049ea11d337f185b1aa910d98e8fbd991f0fba7b` | `0xa91dff6c41af892a89fc5c0bf5c32b5cc89d13ac` | `0xdbed…f2f5` |
| 6 | `0x545d69b99759e7b670df243b882700121d6d3ab9` | `0xb25fe78faaefadb7249b4940ee485856df150bbe` | `0xbe7d…5bff` |

Legacy NodeDelegators (impl `0x50f8…679b`, still deployed): `0x07b96cf1183c9bff2e43acf0e547a8c4e4429473`, `0x429554411c8f0aceec899100d3aaccf2707748b3`, `0x92b4f5b9ffa1b5db3b976e89a75e87b332e6e388`, `0x9d2fc9287e1c3a1a814382b40aab13873031c4ad`, `0xe8038228ff1aefd007d7a22c9f08ddaadf8374e4`.

Pods read from `EigenPodManager.getPod(nd)`. Operators read from `DelegationManager.delegatedTo(nd)`.

### 3.3 L1Vaults, bridge and rate contracts

| Role | Address | One-liner |
|------|---------|-----------|
| **RSETH_OFTAdapter** | `0x85d456b2dff1fd8245387c0bfb64dfb700e98ef3` | LayerZero v2 lockbox for rsETH; owner = Manager Safe `0xcbcd…29a1`. Drained 2026-04-18 |
| **L1Vault (Arbitrum)** | `0x4b7b39793a84ab6eccda80795733480e7d046be8` | `l1VaultETHForL2Chain` of the Arb pool |
| **L1Vault (Base)** | `0x48cdad4c3c7a2f5818dab5eb08df7db5420a60f6` | Base pool → L1 |
| **L1Vault (Optimism)** | `0x83d4b497dbe3bd2d42e0f3ee5ab34f83e80ab4e0` | OP pool → L1; switched to CCIP (`BridgeTypeSet`) |
| **L1Vault (Avalanche)** | `0xa0feee3ff245bf60529338ef8f1de3f6fb7f676c` | registry lists it as "not used yet" |
| L1Vault (Scroll / Linea / zkSync) | `0x32064a427e8bdf59b14ac169d9835168328a36a6` / `0x6224c582a0989cfecd232af28c68f446b46979ef` / `0xdadb65fb1fcc3d877d774e5e2b00013fe1efbf76` | non-target L2s |
| **RSETHMultiChainRateProvider** | `0x0788906b19ba8f8d0e8a7015f0714df3179d9ab6` | pushes `rsETHPrice` to L2 receivers by LayerZero v1 |
| RSETHRateProvider | `0xf1cccba5558d31628216489a1435e068b1fd2c8a` | older single-receiver provider |

### 3.4 Admin, timelocks, Safes

| Role | Address | One-liner |
|------|---------|-----------|
| **ProxyAdmin (core)** | `0xb61e0e39b6d4030c36a176f576aabe44bf59dc78` | admin of every core proxy + NodeDelegators; `owner()` = Timelock below |
| **TimelockController (core)** | `0x49bd9989e31ad35b0a62c20be86335196a3135b1` | `getMinDelay()` = 864000 s (10 days) |
| ProxyAdmin (Safe-owned) | `0x7550eaee86f649dc5cba74e92d3e2667b68753fa` | `owner()` = Admin Safe `0xb957…0da2` |
| **ProxyAdmin (L1Vaults)** | `0x2155ab0b399a71df8c464dfc1b02149b53b2b2c1` | `owner()` = Timelock `0x10e5…b869` |
| TimelockController (L1Vault + rate provider) | `0x10e5631320a6e7898f1b18aeade46acc81deb869` | 259200 s (3 days) |
| Manager TimelockController | `0x1fda02cf28f28a763d996ad5ee37b9f1b608e674` | 180 s |
| Admin Safe | `0xb9577e83a6d9a6de35047aa066e3758221fe0da2` | DEFAULT_ADMIN |
| Manager Safe | `0xcbcdd778aa25476f203814214dd3e9b9c46829a1` | MANAGER; OFTAdapter owner; owner of the UnlockedWithdrawalsInitializer ProxyAdmin `0xb0cd…4b25` |
| **Pauser Safe** | `0xb6abb489aca4583833230f10b3a7670114d09559` | PAUSER on ETH and on most L2s |
| ProxyFactory | `0x673a669425457bcabeb247f56552a0fd8141cee2` | deterministic proxy deployer |

### 3.5 Not in the rsETH flow

KERNEL `0x3f80b1c54ae920be41a77f8b902259d48cf24ccf` (symbol `KERNEL`) and `KERNEL_OFTAdapter` `0x2a1d74de3027cce18d31011518c571130a4cd513` are the KernelDAO governance token. They are noted here only so they are not mistaken for rsETH contracts.

---

## 4. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **rsETH (LayerZero OFT)** | `0x4186bfc76e2e237523cbc30fd220fe055156b41f` | symbol `rsETH`; supply 16,998.52; **still peered** to the ETH adapter |
| **RSETHPool** | `0x376a7564af88242d6b8598a5cfdd2e9759711b61` | deposit pool; `wrsETH()` = the OFT above (no wrapper on Arb); `paused() = true` |
| **RSETHRateReceiver** | `0x3222d3de5a9a3ab884751828903044cc4adc627e` | `rateOracle` of the pool |
| wrsETH (CCIP, old) | `0xe119d214a6efa7d3cf60e6e59481ede1b0064a6b` | symbol `wRSETH`; supply 0 |
| ArbitrumMessenger | `0x58439f875cbfaa81b94cea89a934b6108bdec9f7` | native-bridge messenger |
| ArbitrumLidoBridge | `0x23e74e86be143e427f5aa6f5410d322a8dbe0ac7` | wstETH bridge helper |
| HashStorage | `0x141f6c276d7a1937603667c72a7688edbda16728` | native-bridge withdrawal tracker |
| wstETH / ETHx oracles | `0x6932e85964fa31f70ed9debe63d9d969ad00f112` / `0x0c742a74fa8e1a00d6bc4623d485a84dd147864d` | pool token oracles |
| ProxyAdmin | `0x4938c803ebe999fb0a5527310662624f2e7a38c1` | owner = Timelock below |
| TimelockController | `0xe15109d97e84caced271502c5d1dbbc50a4d6b0c` | owner of the rate receiver too |
| OffchainConfig (+ ProxyAdmin) | `0xaa1bed0d59fdf11f5f302eb927df091528763702` (+ `0x583cd15a946b79f7cccab62346445192dcdd5cf0`) | buffer-pool limits |
| Arbitrum Safe | `0x96d97d66d4290c9182a09470a5775ff90daf922c` | OFT owner; Timelock proposer |
| KERNEL OFT (not rsETH) | `0x6e401189c8a68d05562c9bab7f674f910821eacf` | symbol `KERNEL` |

## 5. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| **wrsETH (RsETHTokenWrapper)** | `0xedfa23602d0ec14714057867a78d01e94176bea0` | user-facing token; supply 11,411.52 |
| **RSETHPoolV3ExternalBridge** | `0x291088312150482826b3a37d5a69a4c54daa9118` | deposit pool; mints wrsETH; `paused() = true` |
| **RSETHRateReceiver** | `0x7781ae9b47fecaceaecc4fca8d0b6187e3ef9ba7` | `rateOracle` of the pool |
| rsETH (LayerZero OFT) | `0x1bc71130a0e39942a7658878169764bbd8a45993` | symbol `rsETH`; supply 3.44; **ETH peer cleared** (`PeerSet` eid 30184 → 0 on ETH, block 26127715) |
| Base LidoBridge | `0x503d45c009f81142556919a3cd0df91e097b3f0e` | wstETH bridge helper |
| wstETH oracle | `0xefbbf9290cda1c3046211d5464cc52dae46c544c` | pool token oracle |
| HashStorage (proven / finalized) | `0xa7d877332230ee1d8af941ca6ef9217be6b6762e` / `0xfdef98b5ec29ce9c68800bac608f8273979bbc0a` | OP-stack withdrawal tracking |
| ProxyAdmin | `0xdf3f5926fd14ed048b04941189da54bdedd478d0` | owner = Timelock below |
| TimelockController | `0xf425ed48483b49cf10c8a7f6cfd25dfd86d3155a` | |
| Base Safe | `0x7da95539762dd11005889f6b72a6674a4888b56d` | OFT owner |

## 6. Addresses — Optimism (chain ID 10)

| Role | Address | One-liner |
|------|---------|-----------|
| **wrsETH (RsETHTokenWrapper)** | `0x87eee96d50fb761ad85b1c982d28a042169d61b1` | user-facing token; supply 24.91 |
| **RSETHPoolV2ExternalBridge** | `0xaaa687e218f9b53183a6aa9639fbd9d6e69ecb73` | deposit pool; `paused() = true` |
| **RSETHRateReceiver** | `0x1373a61449c26cc3f48c1b4c547322edaa36eb12` | `rateOracle` of the pool |
| rsETH (LayerZero OFT) | `0x4186bfc76e2e237523cbc30fd220fe055156b41f` | symbol `rsETH`; supply 10.68; ETH peer = 0 |
| rsETH (CCIP, new) | `0x043849686ee254ada46a432770e1a491491fc44d` | symbol `rsETH`; supply 35.84; fed by L1Vault (OP) over CCIP |
| wrsETH (CCIP, old) | `0x68a9ec5b93f04a60c77f486a664f283b2e4e2b72` | symbol `wRSETH`; supply 0 |
| ProxyAdmin | `0xa465eafafee5629ee92832e14c37df4723816d58` | owner = Timelock below |
| TimelockController | `0x4ff0b2caefeed2906e96931ad74e265ee2abb61f` | |
| Optimism Safe | `0x0d30a563e38fe2926b37783a046004a7869ade6c` | OFT owner |

## 7. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | One-liner |
|------|---------|-----------|
| **wrsETH (RsETHTokenWrapper)** | `0x7bfd4ca2a6cf3a3fddd645d10b323031afe47ff0` | supply 0.26 |
| **RSETHPoolV3** | `0x72fb3f4f0b3cd77ef7556fa4960bf4aebaa47009` | deposit pool; `paused() = true` |
| **RSETHRateReceiver** | `0x2a2f37d29143aea599c57169817a48c04664150b` | `rateOracle` of the pool |
| rsETH (LayerZero OFT) | `0xc430c78da6e4af49bd115f0329d154bb135f1363` | symbol `rsETH`; supply 0.239; ETH peer = 0. **Same literal is the AGETHMultiChainRateProvider on Ethereum** |
| InterimRSETHOracle | `0x3737e159c48991e37c200918eba673ee48ee9a0c` | interim rate source |
| WETHOracle | `0x5663ea61dd44986bb92fca764d1be02bde08399a` | |
| ProxyAdmin | `0x9a7fa6fe70f2a23dc3980df69f922b6961fbbe81` | owner = Timelock below |
| TimelockController | `0xf406c42b53b204e5ddedcf33b5b25967d8d59a5e` | |
| Avalanche Safe | `0xb2bb1425514ab5903be6bbdb6b44958e71103561` | OFT owner |

## 8. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| wrsETH (CCIP, old) | `0x4186bfc76e2e237523cbc30fd220fe055156b41f` | symbol `wRSETH`; **supply 0**. No rsETH pool or OFT on BNB |
| ProxyAdmin | `0xe5ca826202846363ac1c3f04598a9fb3a85ed753` | owner = BSC Safe `0xb422…95b0` |
| KERNEL OFT (not rsETH) | `0x9ecaf80c1303cca8791afbc0ad405c8a35e8d9f1` | symbol `KERNEL` |
| KernelDepositPool (not rsETH) | `0xde1ef8104220a372b80771fe1c0f7944334e013b` | KERNEL staking |

## 9. Polygon PoS (137), Robinhood Chain (4663), Arc (5042) — not deployed

`eth_getCode` returns `0x` for RSETH, every rsETH OFT literal (`0x4186…b41f`, `0x1bc7…3993`, `0xc430…1363`, `0xc3ea…9f58`, `0xd757…99b1`, `0xa321…bade`, `0x6542…1b66`) and KERNEL OFT `0x9eca…d9f1` on all three chains. The Kelp registry lists no deployment on them.

---

## 10. Cross-chain summary

| Chain (ID) | rsETH token(s) | Deposit pool | Rate receiver | L2 status |
|------------|----------------|--------------|---------------|-----------|
| Ethereum (1) | RSETH `0xa129…e5a7` + OFTAdapter `0x85d4…8ef3` | LRTDepositPool `0x0366…375d` | — (source) | live, unpaused |
| Arbitrum (42161) | OFT `0x4186…b41f` | RSETHPool `0x376a…1b61` | `0x3222…627e` | pool paused; OFT peered |
| Base (8453) | wrsETH `0xedfa…bea0` + OFT `0x1bc7…3993` | V3ExternalBridge `0x2910…9118` | `0x7781…9ba7` | pool paused; OFT peer cleared |
| Optimism (10) | wrsETH `0x87ee…61b1` + OFT `0x4186…b41f` + CCIP `0x0438…c44d` | V2ExternalBridge `0xaaa6…cb73` | `0x1373…eb12` | pool paused; OFT peer = 0 |
| Avalanche (43114) | wrsETH `0x7bfd…7ff0` + OFT `0xc430…1363` | RSETHPoolV3 `0x72fb…7009` | `0x2a2f…150b` | pool paused; OFT peer = 0 |
| BNB (56) | old CCIP wrsETH `0x4186…b41f` (supply 0) | — | — | dormant |
| Polygon (137) | — | — | — | not deployed |
| Robinhood (4663) | — | — | — | not deployed |
| Arc (5042) | — | — | — | not deployed |

> **Same literal, different contract:** `0x4186…b41f` is the rsETH OFT on Arb and OP, the old CCIP wRSETH on BNB, and an unrelated no-symbol contract on Base. `0xc430…1363` is the OFT on Avax and AGETHMultiChainRateProvider on Ethereum. Always key on (chain, address).

---

## 11. Proxies (old & new)

| Contract | Pattern | Current impl (2026-10-30) | Upgrade auth |
|----------|---------|---------------------------|--------------|
| RSETH | EIP-1967 Transparent | `0x7159107483e623707c18c6e06cbc095bd0717783` | ProxyAdmin `0xb61e…dc78` → Timelock 10 d |
| LRTConfig | EIP-1967 Transparent | `0xd4f475a7df199b3106f622a3a825ff399d4dafce` | same |
| LRTDepositPool | EIP-1967 Transparent | `0xea38dfa108318288f36f13d06e821a64acda8320` | same |
| LRTOracle | EIP-1967 Transparent | `0xc59110239240761ccd3e670288443316e10dd271` | same |
| LRTWithdrawalManager | EIP-1967 Transparent | `0x0ecde3f414d1a245246d121e37191d9a63684e19` | same |
| LRTUnstakingVault | EIP-1967 Transparent | `0x1fc8eebd7e1e61cc2cca005ee0f0d08417e5a2a4` | same |
| LRTConverter | EIP-1967 Transparent | `0x70daf8b0bfc846cc98b71d2f8ffdc91f4d2bbd51` | same |
| FeeReceiver | EIP-1967 Transparent | `0x868cef33e29bf3037b5d4cf5c408eaef29d96b33` | same |
| ChainlinkPriceOracle | EIP-1967 Transparent | `0xd73cd1aae045653474b873f3275ba2be2744c8b4` | same |
| PubkeyRegistry | EIP-1967 Transparent | `0x2b394f34d0d6d1f4067bcb96db437321a4acc8ec` | same |
| NodeDelegator 0–6 | EIP-1967 Transparent | `0xa86f75549c21f815f61053a39b0d97062ff6dc53` (all) | same |
| Legacy NodeDelegators | EIP-1967 Transparent | `0x50f88fbbc50629b8b37f68c4dc28f712a8bf679b` | same |
| UnlockedWithdrawalsInitializer | EIP-1967 Transparent | `0x81b08a0d57ea284b282b12a574139db0ec862439` | ProxyAdmin `0xb0cd…4b25` → Manager Safe |
| L1Vault Arb / Base / Scroll / zkSync | EIP-1967 Transparent | `0x2f13d04b79d484b04358f64820cdb2725041e0e4` | ProxyAdmin `0x2155…b2c1` → Timelock 3 d |
| L1Vault OP / Linea | EIP-1967 Transparent | `0xb0313a93f90f54157f329dc647cb42cc763b5974` (L1VaultV2, CCIP-capable) | same |
| L1Vault Avax | EIP-1967 Transparent | `0x5aaf33395feaa1d342dcda6198126b40959286a1` | same |
| Arb RSETHPool | EIP-1967 Transparent | `0xa5e725d4a62e04dcae7fcb3bf8c888fd54d68fc1` | ProxyAdmin `0x4938…38c1` → Timelock `0xe151…6b0c` |
| Base pool / wrapper | EIP-1967 Transparent | `0x9190df2f557aa9dcc8b25cd300de49ecbf134550` / `0xcbb9b5faa23da272d2bdfc7bc3236b00631a8837` | ProxyAdmin `0xdf3f…78d0` → Timelock `0xf425…155a` |
| OP pool / wrapper | EIP-1967 Transparent | `0x8a1b70d89eb1659ac6437f4a79dddd70fe933fa9` / `0x9a0f41f930372b9672ed12399d456153aee0c8c1` | ProxyAdmin `0xa465…6d58` → Timelock `0x4ff0…b61f` |
| Avax pool / wrapper | EIP-1967 Transparent | `0x7dbf4b3afa13f2b68d3d607beba2fd8cf5debc5a` / `0xabaad1bd3e221cc213e2b73e3326f0adc40d4bec` | ProxyAdmin `0x9a7f…be81` → Timelock `0xf406…9a5e` |
| BNB KernelDepositPool | EIP-1967 Transparent | `0x91a91e12c831ef3b25af5aade257f6a401ccfef5` | ProxyAdmin `0xe5ca…d753` |

**Not proxies** (impl and admin slots = 0): RSETH_OFTAdapter, every rsETH OFT, every CCIP rsETH/wrsETH, RSETHMultiChainRateProvider, RSETHRateProvider, every RateReceiver, HashStorage, LidoBridge, ArbitrumMessenger, ProxyAdmins, Timelocks. The OFTs are immutable but owner-configurable (`setPeer`, `setDelegate`, `setEnforcedOptions`).

Watch `Upgraded(address)` = `0xbc7cd75a…2d3b` on every proxy above. Watch `CallScheduled` on the core Timelock for a 10-day warning before a core upgrade.

---

## 12. Detection invariants & gotchas

1. **rsETH does not rebase.** `Transfer.value` is the real token amount. ETH value = amount × `LRTOracle.rsETHPrice()`. The price moves only on `RsETHPriceUpdate`. Each update also mints protocol fee rsETH to the treasury (`FeeMinted` + `Transfer` from `0x0`).
2. **Mint attribution.** A deposit mint shows as `ETHDeposit`/`AssetDeposit` on the deposit pool plus `Transfer(0x0 → user)` on RSETH. An rsETH mint with no matching deposit-pool event and no `FeeMinted` is an anomaly. On L2s, the mint is `SwapOccurred` on the pool plus a wrsETH (or Arb OFT) `Transfer` from `0x0`.
3. **Price-decrease and below-peak events are the loss signals.** `RsETHPriceDecrease` and `RsETHPriceBelowPeak` fire when the new price is under the old or the highest price.
4. **The 2026-04-18 exploit path.** A forged inbound LayerZero packet made `RSETH_OFTAdapter` emit `OFTReceived` and send 116,500 rsETH out of the lockbox. Alert on any `OFTReceived` on the adapter whose `srcEid` has no matching `OFTSent` on the source OFT, and on a large adapter balance drop. Kelp's response was `PausedAll` / `Paused` within about 46 minutes.
5. **Peers are being removed.** On ETH, `peers(eid)` is non-zero only for Arbitrum (30110) among target chains. Base (30184), Optimism (30111) and Avalanche (30106) return 0. A `PeerSet` with a non-zero peer re-opens a route and needs review.
6. **L2 rates lag.** On 2026-10-30, every L2 `RSETHRateReceiver.rate()` was 1.07729, while `rsETHPrice()` on L1 was 1.08315. Receivers update only when someone calls `updateRate()` on the ETH provider. Do not use L2 receiver rate as the L1 price.
7. **Three token kinds on L2s.** On Base, OP and Avax, users hold **wrsETH** (the wrapper). The LayerZero OFT and the CCIP token are the bridged "rsETH". The wrapper converts 1:1 between them (`Deposit` / `Withdraw`). Arbitrum has no wrapper: the pool sends the OFT directly. Sum all of them for L2 supply.
8. **4-argument `OFTSent`.** Kelp OFTs emit `OFTSent(bytes32,uint32,address,uint256)` = `0xfff873bb…b80a`, not the 5-argument GA topic.
9. **`EthTransferred(address,uint256)` is emitted by four contract types** (deposit pool, NodeDelegator, UnstakingVault, Converter). `Paused` / `Unpaused` / `Upgraded` are generic. Always disambiguate by emitter.
10. **Freeze tools.** RSETH can block a user's transfers (`UserTransfersBlocked`) and move frozen funds to custody (`FrozenFundsRecovered`). Both are high-signal admin events.
11. **Withdrawals are two-step.** `initiateWithdrawal` moves rsETH from the user to the withdrawal manager (`Transfer` user → manager) and emits `AssetWithdrawalQueued`. An operator `unlockQueue` sets the rate, emits `AssetUnlocked`, and burns the unlocked rsETH (`Transfer` manager → `0x0`). The user then calls `completeWithdrawal` (`AssetWithdrawalFinalized`). `instantWithdrawal` burns rsETH directly from the user and emits `InstantWithdrawalFeeCollected`.
12. **NodeDelegator operator changes** (`Undelegated`, `ElSharesDelegated`) move restaked ETH between EigenLayer operators. Cross-reference EigenLayer `StakerDelegated` / `StakerUndelegated` in `eigenlayer/core.md`.
13. **Same literal, different meaning across chains** (see §10). Never assume an address means the same thing on two chains.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_ETH_DEPOSIT                 = '\x8b0422d41caf5eb583695377e98b5041a1d241a7c80483cf182b1311c48c93b7'
TOPIC_ASSET_DEPOSIT               = '\x07c31fccf51996f0f4ea01c3a55191786b3a8cd89f696db4d42adaa99b0e15f1'
TOPIC_ETH_TRANSFERRED             = '\xcec1f18c3ab8ddaaa107a1591e3c369667eec613626611a8deaedef43069fcdd'
TOPIC_ASSET_WITHDRAWAL_QUEUED     = '\xd1ff36888873897951eaf991bca7db625b8ed70bf2b0d54441907bdab02b08d7'
TOPIC_ASSET_UNLOCKED              = '\x72e38cd9e650a56d27bba7e1a9a8d6f77dc5cc382bb38a7e56f4f1e845be910d'
TOPIC_ASSET_WITHDRAWAL_FINALIZED  = '\xca13475b00c46ee0ce4a479bd18ed747ff89395e96e93779ba7f18cbe1735fb4'
TOPIC_INSTANT_WITHDRAWAL_FEE      = '\x5e94c841c11b8b2ec5be817ed833f18a2bbbe626e93b79121a1dcf072e33e6a2'
TOPIC_RSETH_PRICE_UPDATE          = '\x8d3b19635cf6f25b423571483e205b44b40c0c8f35f76e22089c6750c717bf17'
TOPIC_RSETH_PRICE_DECREASE        = '\x06c8ec6bdfc53639a00f9f1ff3e965171713883dd4c782323cb19fbe227d1205'
TOPIC_RSETH_PRICE_BELOW_PEAK      = '\x4419499b183ea1ccf98bbba5b6d9b711cebefe6709bfbb130d52888544bf4b63'
TOPIC_FEE_MINTED                  = '\xbbc316f92387a82e2f88e54dbef5d256aff3e9ea87e87bbd9bdba9d48c769941'
TOPIC_SET_CONTRACT                = '\x5de40a806536a2029221dac2c8887ac9f11952fcc1ed3d7cfb4476dd5259b740'
TOPIC_ADDED_SUPPORTED_ASSET       = '\xbaf29bfdb0c1bd100ee9f6d6c1112bcde0014c0ef8c6199c0a813d936dd6568e'
TOPIC_ASSET_DEPOSIT_LIMIT_UPDATE  = '\xc04446455e1f3789fca0c8aad0733e9f7d7f0f82d7d0ca5e9b7c56c9ea081ce8'
TOPIC_PAUSED_ALL                  = '\xf1005168aea1429fe9559d51ef6caa33e6426890864e2e6e41e5d54baa7be79f'
TOPIC_PAUSED                      = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                    = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_ROLE_GRANTED                = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED                = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
TOPIC_USER_TRANSFERS_BLOCKED      = '\x14dc9fbc0cec3c9737347af811749e92b1c9554af08194cb7774c43192a74643'
TOPIC_FROZEN_FUNDS_RECOVERED      = '\xedcd49030ac6d3af7cca7623917ba88f408bb1e8fa6980db52293707ef6c4601'
TOPIC_ETH_STAKED                  = '\xa16ad5049bc6092f455ad47c45f18d9e3436db84fa5f1da8dcde4cb12296c03d'
TOPIC_ND_WITHDRAWAL_QUEUED        = '\xb4a86b70f2287279f5f8f45d48929f811389449b556cdd7f03aa8e0cc738dfbd'
TOPIC_EL_WITHDRAWAL_COMPLETED     = '\xa302909a05495b640894a6ba8e0be85f973745e9356745d3e16d0ac9bc93f41c'
TOPIC_UNDELEGATED                 = '\x2167dd2914464f62e3f9655115a6a0cdc6fcf4cb13213ff53d564a47f0423dab'
TOPIC_EL_SHARES_DELEGATED         = '\x9e76604d3ca069af191a0f9f6cc8c7f8013191b7ae7ff82eaa75600bbca70101'
TOPIC_MEV_REWARDS_ADDED           = '\x1383e8657823f68fdbf6091cd5234d51fae3a863c8c16bfada4903bab9172f6b'
TOPIC_BRIDGED_RSETH_TO_L2         = '\x48e35858de924f81ed12208a490444b2d42f2447c5c7439c2e5ab2dff5d48360'
TOPIC_BRIDGED_RSETH_TO_L2_CCIP    = '\x9ab125f8a8fd7c6a52702f7fa4074ce46212529eaaffc91f2093a1e5dd5e74b8'
TOPIC_OFT_SENT_4ARG               = '\xfff873bb909b73d08a8c1af4b21779e87103bb8ea8cf3b3a0067eb8526b8b80a'
TOPIC_OFT_RECEIVED                = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_PEER_SET                    = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_RATE_UPDATED                = '\xe65c987b2e4668e09ba867026921588005b2b2063607a1e7e7d91683c8f91b7b'
TOPIC_SWAP_OCCURRED               = '\x6fc20b1cf8f9d1126dbd5964e2517cd71083acf40aed30fb6e0c4850d251c94f'
TOPIC_SWAP_OCCURRED_TOKEN         = '\x0f2e7cff0bc0ea332563f60ed17d4f0f03e5f0c8eecc1271deebe1f0073b2529'
TOPIC_REVERSE_SWAP_V3             = '\x86309324fbc587b17369c0b6d4553fc187b85fd11a9a15d98d86dc274cb48a04'
TOPIC_BRIDGED_ETH_TO_L1           = '\x2bfc0ed497a2253b9aa4e4a88269dcc8efa7489803743d7cfa748ec9c241c6d7'
TOPIC_WRAPPER_DEPOSIT             = '\x7cfff908a4b583f36430b25d75964c458d8ede8a99bd61be750e97ee1b2f3a96'
TOPIC_WRAPPER_WITHDRAW            = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
TOPIC_TRANSFER                    = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_TL_CALL_SCHEDULED           = '\x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca'
TOPIC_TL_CALL_EXECUTED            = '\xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58'
-- ===== Selectors (chain-agnostic) =====
SEL_DEPOSIT_ETH                   = '\x72c51c0b'
SEL_DEPOSIT_ASSET                 = '\xc3ae1766'
SEL_INITIATE_WITHDRAWAL           = '\xc5a67b01'
SEL_COMPLETE_WITHDRAWAL           = '\xd3a86833'
SEL_INSTANT_WITHDRAWAL            = '\x2a25f7a9'
SEL_UNLOCK_QUEUE                  = '\xa2ccd14f'
SEL_UPDATE_RSETH_PRICE            = '\x51ce226a'
SEL_RSETH_PRICE                   = '\xb4b46434'
SEL_PAUSE_ALL                     = '\x595c6a67'
SEL_PAUSE                         = '\x8456cb59'
SEL_SET_CONTRACT                  = '\x7ed77c9c'
SEL_MINT                          = '\x40c10f19'
SEL_BURN_FROM                     = '\x79cc6790'
SEL_BLOCK_USER_TRANSFERS          = '\xfa91e4c1'
SEL_RECOVER_FROZEN_FUNDS          = '\x21cdc338'
SEL_STAKE_32_ETH                  = '\x09c0e997'
SEL_DELEGATE_TO                   = '\xeea9064b'
SEL_UNDELEGATE                    = '\x92ab89bb'
SEL_OFT_SEND                      = '\xc7c7f5b3'
SEL_LZ_RECEIVE                    = '\x13137d65'
SEL_SET_PEER                      = '\x3400288b'
SEL_L2_POOL_DEPOSIT_ETH           = '\xa26e1186'
SEL_L2_POOL_DEPOSIT_TOKEN         = '\xbfe07da6'
SEL_BRIDGE_ASSETS                 = '\x513b5064'
SEL_PROXYADMIN_UPGRADE            = '\x99a88ec4'
SEL_PROXYADMIN_UPGRADE_AND_CALL   = '\x9623609d'
-- ===== Addresses (network-specific) =====
ETH_RSETH                         = '\xa1290d69c65a6fe4df752f95823fae25cb99e5a7'
ETH_LRT_CONFIG                    = '\x947cb49334e6571ccbfef1f1f1178d8469d65ec7'
ETH_LRT_DEPOSIT_POOL              = '\x036676389e48133b63a802f8635ad39e752d375d'
ETH_LRT_ORACLE                    = '\x349a73444b1a310bae67ef67973022020d70020d'
ETH_LRT_WITHDRAWAL_MANAGER        = '\x62de59c08eb5dae4b7e6f7a8cad3006d6965ec16'
ETH_LRT_UNSTAKING_VAULT           = '\xc66830e2667bc740c0bed9a71f18b14b8c8184ba'
ETH_LRT_CONVERTER                 = '\x598dbcb99711e5577ff76ef4577417197b939dfa'
ETH_FEE_RECEIVER                  = '\xdbc3363de051550d122d9c623cbaff441afb477c'
ETH_PUBKEY_REGISTRY               = '\x37043dc4ef0b3e84ac9a84959d54cdc77f2109bd'
ETH_ND_0                          = '\xfc561966ceaaa09f4d6cba4add54778c2bf1cb85'
ETH_ND_1                          = '\x395884d1974a839702bcfcba176ac7871c788946'
ETH_ND_2                          = '\x79f17234746344e0365d40be50d8d43db9082c32'
ETH_ND_3                          = '\x4c798c4653b1257d5149910523d7a6eed5712f83'
ETH_ND_4                          = '\xee5470e1519972c3ea95249d60ebd064af2d53d3'
ETH_ND_5                          = '\x049ea11d337f185b1aa910d98e8fbd991f0fba7b'
ETH_ND_6                          = '\x545d69b99759e7b670df243b882700121d6d3ab9'
ETH_RSETH_OFT_ADAPTER             = '\x85d456b2dff1fd8245387c0bfb64dfb700e98ef3'
ETH_L1VAULT_ARB                   = '\x4b7b39793a84ab6eccda80795733480e7d046be8'
ETH_L1VAULT_BASE                  = '\x48cdad4c3c7a2f5818dab5eb08df7db5420a60f6'
ETH_L1VAULT_OP                    = '\x83d4b497dbe3bd2d42e0f3ee5ab34f83e80ab4e0'
ETH_L1VAULT_AVAX                  = '\xa0feee3ff245bf60529338ef8f1de3f6fb7f676c'
ETH_MULTICHAIN_RATE_PROVIDER      = '\x0788906b19ba8f8d0e8a7015f0714df3179d9ab6'
ETH_PROXY_ADMIN_CORE              = '\xb61e0e39b6d4030c36a176f576aabe44bf59dc78'
ETH_TIMELOCK_CORE                 = '\x49bd9989e31ad35b0a62c20be86335196a3135b1'
ETH_PROXY_ADMIN_L1VAULT           = '\x2155ab0b399a71df8c464dfc1b02149b53b2b2c1'
ETH_TIMELOCK_L1VAULT              = '\x10e5631320a6e7898f1b18aeade46acc81deb869'
ETH_ADMIN_SAFE                    = '\xb9577e83a6d9a6de35047aa066e3758221fe0da2'
ETH_MANAGER_SAFE                  = '\xcbcdd778aa25476f203814214dd3e9b9c46829a1'
ETH_PAUSER_SAFE                   = '\xb6abb489aca4583833230f10b3a7670114d09559'
ETH_TREASURY                      = '\x322f2d4bfe8280eeb713b7c51eeba42590c36f78'
ARB_RSETH_OFT                     = '\x4186bfc76e2e237523cbc30fd220fe055156b41f'
ARB_RSETH_POOL                    = '\x376a7564af88242d6b8598a5cfdd2e9759711b61'
ARB_RATE_RECEIVER                 = '\x3222d3de5a9a3ab884751828903044cc4adc627e'
ARB_WRSETH_CCIP_OLD               = '\xe119d214a6efa7d3cf60e6e59481ede1b0064a6b'
ARB_PROXY_ADMIN                   = '\x4938c803ebe999fb0a5527310662624f2e7a38c1'
BASE_WRSETH                       = '\xedfa23602d0ec14714057867a78d01e94176bea0'
BASE_RSETH_POOL                   = '\x291088312150482826b3a37d5a69a4c54daa9118'
BASE_RATE_RECEIVER                = '\x7781ae9b47fecaceaecc4fca8d0b6187e3ef9ba7'
BASE_RSETH_OFT                    = '\x1bc71130a0e39942a7658878169764bbd8a45993'
BASE_PROXY_ADMIN                  = '\xdf3f5926fd14ed048b04941189da54bdedd478d0'
OP_WRSETH                         = '\x87eee96d50fb761ad85b1c982d28a042169d61b1'
OP_RSETH_POOL                     = '\xaaa687e218f9b53183a6aa9639fbd9d6e69ecb73'
OP_RATE_RECEIVER                  = '\x1373a61449c26cc3f48c1b4c547322edaa36eb12'
OP_RSETH_OFT                      = '\x4186bfc76e2e237523cbc30fd220fe055156b41f'
OP_RSETH_CCIP_NEW                 = '\x043849686ee254ada46a432770e1a491491fc44d'
OP_WRSETH_CCIP_OLD                = '\x68a9ec5b93f04a60c77f486a664f283b2e4e2b72'
OP_PROXY_ADMIN                    = '\xa465eafafee5629ee92832e14c37df4723816d58'
AVAX_WRSETH                       = '\x7bfd4ca2a6cf3a3fddd645d10b323031afe47ff0'
AVAX_RSETH_POOL                   = '\x72fb3f4f0b3cd77ef7556fa4960bf4aebaa47009'
AVAX_RATE_RECEIVER                = '\x2a2f37d29143aea599c57169817a48c04664150b'
AVAX_RSETH_OFT                    = '\xc430c78da6e4af49bd115f0329d154bb135f1363'
AVAX_PROXY_ADMIN                  = '\x9a7fa6fe70f2a23dc3980df69f922b6961fbbe81'
BNB_WRSETH_CCIP_OLD               = '\x4186bfc76e2e237523cbc30fd220fe055156b41f'
```

---

## 14. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the canonical source (events in `contracts/interfaces/*.sol` and contract bodies). Topics marked ✓ were matched to live logs: Ethereum core contracts through the Blockscout v2 logs API (blocks 18.76M–26.31M), Arbitrum OFT through `eth_getLogs` on `arb1.arbitrum.io`, and the Optimism pool through Blockscout. The ETH OFTAdapter ABI was read from its verified source (`RSETH_OFTAdapter`, solc 0.8.22). It confirms the 4-argument `OFTSent`.
- **Addresses:** parsed from the `Kelp-DAO/LRT-rsETH` README deployment tables. Each one was existence-checked with `eth_getCode` on the chain it is listed for. LRTConfig wiring was read live with `getContract(keccak256(key))` and `rsETH()`. Pool wiring was read live with `wrsETH()`, `rsETHOracle()` and `l1VaultETHForL2Chain()`. NodeDelegator pods and operators were read from EigenLayer `getPod` and `delegatedTo`.
- **Proxies:** EIP-1967 impl and admin slots read live per proxy. ProxyAdmin `owner()` and Timelock `getMinDelay()` read live. OFT peers read live with `peers(eid)`. `PeerSet` history from the adapter logs.
- **Chain coverage:** all core, OFT, wrapper and pool literals were checked on all nine chains. Polygon, Robinhood Chain and Arc return `0x` for every literal. Symbols were read with `symbol()` to separate rsETH contracts from unrelated code at the same literal.
- **Incident facts:** amount, time, tx hash and DVN cause come from public post-incident reports (see below). The peer clean-up and pause states are from live reads.
- **Not verified:** topics marked **abi** were not seen in the sampled log ranges. Base and Avalanche pool logs were not sampled (pools are paused). The Base, OP and Avalanche OFTs return the same `oftVersion()` as the ETH adapter, so they likely emit the same 4-argument `OFTSent`. This was not checked in logs.

Authoritative sources:
- [Kelp-DAO/LRT-rsETH](https://github.com/Kelp-DAO/LRT-rsETH) — source and README deployment tables.
- [Kelp DAO](https://kerneldao.com/kelp/) — product.
- [Code4rena Kelp audit (2023-11)](https://code4rena.com/reports/2023-11-kelp) — contract roles.
- Incident: [The Block](https://www.theblock.co/post/397988) · [CoinDesk](https://www.coindesk.com/tech/2026/04/19/2026-s-biggest-crypto-exploit-kelp-dao-hit-for-usd292-million-with-wrapped-ether-stranded-across-20-chains) · [DeFi Prime analysis](https://defiprime.com/kelpdao-rseth-exploit).
- Explorers: [Etherscan](https://etherscan.io/address/0xa1290d69c65a6fe4df752f95823fae25cb99e5a7) · [Arbiscan](https://arbiscan.io/address/0x4186bfc76e2e237523cbc30fd220fe055156b41f) · [Basescan](https://basescan.org/address/0xedfa23602d0ec14714057867a78d01e94176bea0) · [Optimistic Etherscan](https://optimistic.etherscan.io/address/0x87eee96d50fb761ad85b1c982d28a042169d61b1) · [Snowtrace](https://snowtrace.io/address/0x7bfd4ca2a6cf3a3fddd645d10b323031afe47ff0) · [BscScan](https://bscscan.com/address/0x4186bfc76e2e237523cbc30fd220fe055156b41f).

# Spark Liquidity Layer (ALM) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Avalanche, Robinhood Chain)

**Status:** verified against live RPC on every listed chain and the canonical `sparkdotfi/spark-alm-controller` and `sparkdotfi/spark-address-registry` repos on 2026-10-30.
**Scope:** the Spark Liquidity Layer (SLL), the Sky "star" allocator that moves USDS/USDC liquidity into yield venues. It covers `ALMProxy`, `MainnetController` (Ethereum), `ForeignController` (L2s and Robinhood Chain), `RateLimits`, the newer `ALMProxyFreezable` and the "PAU" (diamond) generation. Chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Avalanche C-Chain (43114), Robinhood Chain (4663). BNB (56), Polygon PoS (137) and Arc (5042) have no SLL. Topics and selectors are chain-agnostic. Addresses are network-specific.

The SLL has three contracts for each chain. The `ALMProxy` holds all funds and executes arbitrary calls (`doCall`). Only an address with the `CONTROLLER` role can call it. The controller holds the business logic: each relayer action (deposit to a vault, swap on Curve, send USDC with CCTP) is one controller function. The controller first calls `RateLimits.triggerRateLimitDecrease(key, amount)`, then makes one or more `ALMProxy.doCall` calls. **All three contracts are immutable (no EIP-1967 slot).** Spark upgrades logic by a governance spell that deploys a new controller and moves the `CONTROLLER` role to it. The `ALMProxy` address stays the same.

The SLL is the Spark version of a codebase that Grove forks ([../grove/core.md](../grove/core.md)). The Sky core contracts that mint the USDS (Allocator Vault/Buffer, LitePSM, Vat) are in [../sky/](../sky/). The Spark Vaults that the SLL feeds (`take`) are in [savings.md](savings.md).

---

## 0. Contract families & versions

| Component | Role | Pattern |
|-----------|------|---------|
| **ALMProxy** | Holds custody of all SLL funds. Executes `doCall`/`doCallWithValue`/`doDelegateCall` for the controller. | Immutable, OZ `AccessControl` |
| **MainnetController** (ETH only) | Mints/burns USDS through the Sky Allocator Vault, swaps USDS↔USDC on the LitePSM, sends USDC by CCTP, deposits into ERC-4626/Aave/Curve/Uniswap V4/Ethena/Maple/Superstate/OTC. | Immutable. Version v1.10.0 on ETH. |
| **ForeignController** (L2s, Robinhood) | PSM3 deposit/withdraw, CCTP, LayerZero, ERC-4626, Aave, `takeFromSparkVault`. | Immutable. v1.8.0 on Base/Arb/OP/Avax. v1.10.0 on Robinhood. |
| **RateLimits** | Stores `(maxAmount, slope, lastAmount, lastUpdated)` for each `bytes32` key. The controller decreases/increases the limit. | Immutable, stateful |
| **ALMProxyFreezable** | Second proxy (source: `diamond-pau`, not public). It holds the `SETTER_ROLE` on Spark Vaults (sets the VSR). | Immutable |
| **PAU** (Proxy-Assembler-Unit) | New diamond generation: `PAUFactory`, `Beacon`, facets, a separate `ALMProxy`/`Controller`/`RateLimits` set (ETH `SPUSDC_PAU_*`, Base/Arb `PAU_*`). | Source not public — addresses only |
| **OTCBuffer** (ETH) | Buffer for OTC swaps with an exchange (Binance). | EIP-1967 proxy |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 RateLimits (one event for each rate-limited move — the best activity signal)

| topic0 | Event |
|--------|-------|
| `0x2f9bcbd665fb7984aac3b6a05bb4ac8b303137a34ed4cc5fcd47622f52bdf046` | `RateLimitDecreaseTriggered(bytes32 indexed key, uint256 amountToDecrease, uint256 oldRateLimit, uint256 newRateLimit)` |
| `0xb824249bbde4df2bf5473f603ab3aa717ea2e37b908d9fb4440b962fb656d0ac` | `RateLimitIncreaseTriggered(bytes32 indexed key, uint256 amountToIncrease, uint256 oldRateLimit, uint256 newRateLimit)` |
| `0x356822943b80f809508a684c67d901d5c13b6a22161bf07d510e50a6cb727028` | `RateLimitDataSet(bytes32 indexed key, uint256 maxAmount, uint256 slope, uint256 lastAmount, uint256 lastUpdated)` (governance) |

### 1.2 MainnetController / ForeignController

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x805a2d8b8d8d00211d6d0b649e13d17c52249698ce305975aec1c912d50acfd6` | `CCTPTransferInitiated(uint64 indexed nonce, uint32 indexed destinationDomain, bytes32 indexed mintRecipient, uint256 usdcAmount)` | **Live** on every deployed Spark controller (CCTP V1 form) |
| `0xa613b2b0a8074f0163704e8596561e20fda50f29acee27f8d0bc4c73521034f3` | `CCTPTransferInitiated(uint32 indexed destinationDomain, bytes32 indexed mintRecipient, uint256 usdcAmount)` | CCTP V2 form in repo HEAD (`CCTPV2Lib`); Grove uses it today |
| `0x5e7cfea10f05abc55e716d0d5031f3eea4eabbe012e9bf1d56c5034bba4bfa30` | `MintRecipientSet(uint32 indexed destinationDomain, bytes32 mintRecipient)` | both |
| `0x6c34eba04bf16b35385ac7487ab08f9023bcd9836a5bd53dc60ec0da331b4543` | `LayerZeroRecipientSet(uint32 indexed destinationEndpointId, bytes32 layerZeroRecipient)` | both |
| `0xd8df93d785f3d0d4294fd7b61e5d749c20eec95a2fed5b6b502a4cad09199ca6` | `MaxSlippageSet(address indexed pool, uint256 maxSlippage)` | both |
| `0xfce512ccb77d3237e23e27ae3357b9527a46adbc1faf1367475efd86a2e7aeed` | `MaxExchangeRateSet(address indexed token, uint256 maxExchangeRate)` | both |
| `0x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b` | `RelayerRemoved(address indexed relayer)` | both (freezer action) |
| `0xcd3615e3bc8c2251c32c11e1c3ec814fd03f401fa496d2f4ddbf42eeed84dc0d` | `CCTPMaxFeeRateSet(uint256 maxFeeRate)` | Mainnet (HEAD) |
| `0x26a1feb7262fba528b97aa0124288bf5731a280656b6296294baa4f646fb28b0` | `OTCSwapSent(address indexed exchange, address indexed buffer, address indexed tokenSent, uint256 amountSent, uint256 amountSent18)` | Mainnet |
| `0x59c2ea6a2ea5564fe0f93b71f4331002ce9a5f10b01a85fc130d66dbc5503bb6` | `OTCClaimed(address indexed exchange, address indexed buffer, address indexed assetClaimed, uint256 amountClaimed, uint256 amountClaimed18)` | Mainnet |
| `0xae777da36923bfb42e920d74b5ff8be5bed67dbf971a1f76bde6ec7b7f513d64` | `OTCBufferSet(address indexed exchange, address indexed oldOTCBuffer, address indexed newOTCBuffer)` | Mainnet |
| `0x4df818b9f7ec5c33690b080608fbd13226d113d7f3666141d173513822020eb5` | `OTCRechargeRateSet(address indexed exchange, uint256 oldRate18, uint256 newRate18)` | Mainnet |
| `0x6f5bc6be6e66229330152ab501510d0b9cc63e029ea6839473e64eb02c28ca25` | `OTCWhitelistedAssetSet(address indexed exchange, address indexed asset, bool isWhitelisted)` | Mainnet |
| `0xc9534133270e640725a0c57ced2f1820d1ca4f2a4490515494260b46c6c7cddd` | `UniswapV4TickLimitsSet(bytes32 indexed poolId, int24 tickLowerMin, int24 tickUpperMax, uint24 maxTickSpacing)` | Mainnet |

### 1.3 Access control (ALMProxy, controllers, RateLimits — OZ AccessControl)

| topic0 | Event |
|--------|-------|
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` — a `CONTROLLER` grant = controller rotation |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0x33d83959be2573f5453b12eb9d43b3499bc57d96bd2f067ba44803c859e81113` | `ControllerRemoved(address indexed controller)` (ALMProxyFreezable, HEAD source) |

The ALMProxy itself emits no business events. Fund flows show as ERC-20 `Transfer` logs from/to the ALMProxy address, and as the target protocol's events (ERC-4626 `Deposit`, Aave `Supply`, PSM3 `Deposit`, CCTP `DepositForBurn`).

---

## 2. Function signatures (chain-agnostic)

### 2.1 ALMProxy / RateLimits

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3aada4d2` | `doCall(address,bytes)` | `CONTROLLER` only. Every SLL action passes here. |
| `0xd71f93f8` | `doCallWithValue(address,bytes,uint256)` | `CONTROLLER` only. |
| `0x8ce4a1f2` | `doDelegateCall(address,bytes)` | `CONTROLLER` only. Absent from ALMProxyFreezable bytecode. |
| `0xee0fc121` | `CONTROLLER()` | View. Returns `keccak256("CONTROLLER")`. |
| `0x3bf076b0` | `triggerRateLimitDecrease(bytes32,uint256)` | RateLimits, `CONTROLLER` only. |
| `0x5c093b74` | `triggerRateLimitIncrease(bytes32,uint256)` | RateLimits, `CONTROLLER` only. |
| `0xf6a82d1a` | `setRateLimitData(bytes32,uint256,uint256,uint256,uint256)` | Admin. |
| `0x34323fba` | `setRateLimitData(bytes32,uint256,uint256)` | Admin. |
| `0xc8817503` | `setUnlimitedRateLimitData(bytes32)` | Admin. |
| `0xff7a9fa4` | `getRateLimitData(bytes32)` | View. |
| `0x69d4ac03` | `getCurrentRateLimit(bytes32)` | View. |
| `0x2f2ff15d` / `0xd547741f` / `0x91d14854` | `grantRole` / `revokeRole` / `hasRole(bytes32,address)` | |

### 2.2 Controllers — relayer actions (each selector checked in live bytecode)

| Selector | Signature | Live on |
|----------|-----------|---------|
| `0x536f6b7e` | `mintUSDS(uint256)` | ETH |
| `0x96122b62` | `burnUSDS(uint256)` | ETH |
| `0x5acb7053` | `swapUSDSToUSDC(uint256)` | ETH |
| `0x115c48d5` | `swapUSDCToUSDS(uint256)` | ETH |
| `0x0d015236` / `0x7b65461c` | `swapUSDSToDAI(uint256)` / `swapDAIToUSDS(uint256)` | ETH |
| `0xbcd7e46c` | `transferUSDCToCCTP(uint256,uint32)` | all |
| `0x203f0e3e` | `transferTokenLayerZero(address,uint256,uint32)` | all |
| `0x439e2e45` | `transferAsset(address,address,uint256)` | all |
| `0x7dbe3c90` | `depositERC4626(address,uint256,uint256)` | ETH, Robinhood (v1.10) |
| `0x90893cbe` | `withdrawERC4626(address,uint256,uint256)` | ETH, Robinhood (v1.10) |
| `0xa60c8029` | `redeemERC4626(address,uint256,uint256)` | ETH, Robinhood (v1.10) |
| `0x85f4881d` | `depositERC4626(address,uint256)` | Base, Arb, OP, Avax (v1.8) |
| `0x0b372e57` | `withdrawERC4626(address,uint256)` | Base, Arb, OP, Avax (v1.8) |
| `0xd9acb348` | `redeemERC4626(address,uint256)` | Base, Arb, OP, Avax (v1.8) |
| `0x2cefff96` / `0x7891c043` | `depositAave(address,uint256)` / `withdrawAave(address,uint256)` | all |
| `0x7a1cd355` / `0xb41b48af` | `depositPSM(address,uint256)` / `withdrawPSM(address,uint256)` | Foreign (PSM3) |
| `0x7a1a0d66` | `takeFromSparkVault(address,uint256)` | all |
| `0x1eaef443` | `swapCurve(address,uint256,uint256,uint256,uint256)` | ETH |
| `0x533a5901` / `0x072ef76d` | `addLiquidityCurve(address,uint256[],uint256)` / `removeLiquidityCurve(address,uint256,uint256[])` | ETH |
| `0xec7ba5d8` | `mintPositionUniswapV4(bytes32,int24,int24,uint128,uint128,uint128)` | ETH |
| `0xde34d3dd` | `swapUniswapV4(bytes32,address,uint128,uint128)` | ETH |
| `0xb2eae5ad` / `0x0187148f` | `prepareUSDeMint(uint256)` / `prepareUSDeBurn(uint256)` | ETH |
| `0x02a4ea53` / `0xc77d9a52` | `cooldownAssetsSUSDe(uint256)` / `unstakeSUSDe()` | ETH |
| `0x2e5f2675` | `requestMapleRedemption(address,uint256)` | ETH |
| `0x58c3e3a9` / `0xe150074d` | `otcSend(address,address,uint256)` / `otcClaim(address,address)` | ETH |

### 2.3 Controllers — admin / freezer

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x60f0a5ac` | `removeRelayer(address)` | `FREEZER` role. Emits `RelayerRemoved`. |
| `0xb5cbf202` | `setMintRecipient(uint32,bytes32)` | Admin. CCTP destination for each domain. |
| `0xd3eaf93c` | `setLayerZeroRecipient(uint32,bytes32)` | Admin. |
| `0x73d76dbe` | `setMaxSlippage(address,uint256)` | Admin. |
| `0x7011df99` | `setMaxExchangeRate(address,uint256,uint256)` | Admin. ERC-4626 share-price guard. |
| `0xec556889` / `0xf0921594` / `0x04bda262` | `proxy()` / `rateLimits()` / `psm()` | Views. Use them to tie a controller to its proxy. |

---

## 3. Addresses

All addresses come from `spark-address-registry` `src/<Chain>.sol`. Each one returned non-empty code from `eth_getCode` on 2026-10-30. Wiring was checked live: `controller.proxy()` = ALMProxy, `controller.rateLimits()` = RateLimits, and `hasRole(CONTROLLER, controller)` = true on both the ALMProxy and the RateLimits.

| Chain (ID) | ALMProxy | Controller | RateLimits | ALMProxyFreezable | `psm()` |
|------------|----------|------------|------------|-------------------|---------|
| Ethereum (1) | `0x1601843c5E9bC251A3272907010AFa41Fa18347E` (2373 B) | `0x5c46Fc65855c0C7465a1EA85EEA0B24B601502D3` Mainnet v1.10 | `0x7A5FD5cf045e010e62147F065cEAe59e5344b188` | `0xe5c6318456a7Cb6f74f93B4eee4616dB5fcef699` | LitePSM `0xf6e72Db5…3042` |
| Base (8453) | `0x2917956eFF0B5eaF030abDB4EF4296DF775009cA` | `0x86036CE5d2f792367C0AA43164e688d13c5A60A8` Foreign v1.8 | `0x983eC82E45C61a42FDDA7B3c43B8C767004c8A74` | `0x92d7B06e5844e67174AE9E86bdCb06428482DDF9` | PSM3 `0x1601843c…347E` |
| Arbitrum (42161) | `0x92afd6F2385a90e44da3a8B60fe36f6cBe1D8709` | `0xC40611AC4Fff8572Dc5F02A238176edCF15Ea7ba` Foreign v1.8 | `0x19D08879851FB54C2dCc4bb32b5a1EA5E9Ad6838` | `0x4eE67c8Db1BAa6ddE99d936C7D313B5d31e8fa38` | PSM3 `0x2B05F8e1…7266` |
| Optimism (10) | `0x876664f0c9Ff24D1aa355Ce9f1680AE1A5bf36fB` | `0x689502bc817E6374286af8f171Ed4715721406f7` Foreign v1.8 | `0x6B34A6B84444dC3Fc692821D5d077a1e4927342d` | — | PSM3 `0xe0F9978b…af62` |
| Avalanche (43114) | `0xecE6B0E8a54c2f44e066fBb9234e7157B15b7FeC` | `0x4eE67c8Db1BAa6ddE99d936C7D313B5d31e8fa38` Foreign v1.8 | `0xb79972e8B21f0dE911E65AC342ac85ad38C9A77a` | `0x93c81ADc7F98FdBC8C7a15eCBeD312c8F6adbcB3` | `0x0` (no PSM3) |
| Robinhood (4663) | `0xfD2fD4B046136B540A56C11c75ac679AE7d1dB24` (2260 B) | `0xcf8d58A6eeF2a1cae2Ce69bC463b1178FB76bA1E` Foreign v1.10 | `0x5c1fDE9d4C7f1BF4bc5dEAA2a7752e56232c68a0` | `0xAEa9f5dE56e6C20383a1fcC2C3629Dca0A92cE41` | `0x0` (no PSM3) |

### 3.1 Governance and operators for each chain

| Chain | Admin (`DEFAULT_ADMIN_ROLE`) | Relayer multisig | Freezer multisig |
|-------|------------------------------|------------------|------------------|
| Ethereum | `SPARK_PROXY` `0x3300f198988e4C9C63F75dF86De36421f06af8c4` | `0x8a25A24EDE9482C4Fc0738F99611BE58F1c839AB` (backstop `0x8Cc0Cb0c…4795`) | `0x90D8c80C028B4C09C0d8dcAab9bbB057F0513431` |
| Base | `SPARK_EXECUTOR` `0xF93B7122450A50AF3e5A76E1d546e95Ac1d0F579` | registry `ALM_RELAYER_MULTISIG` | registry `ALM_FREEZER_MULTISIG` |
| Arbitrum | `SPARK_EXECUTOR` `0x65d946e533748A998B1f0E430803e39A6388f7a1` | " | " |
| Optimism | `SPARK_EXECUTOR` `0x205216D89a00FeB2a73273ceecD297BAf89d576d` | " | " |
| Avalanche | `SPARK_EXECUTOR` `0x7566DEbC906C17338524A414343fA61BcA26A843` | `0x8a25A24E…C839AB` | `0x90D8c80C…3431` |
| Robinhood | `SPARK_EXECUTOR` `0x826AEaeee9233fA8Ba199518dd8621A5962b1D02` (receiver `0xc12B1e59c5E337d5Acd2b4f0A9a27d9E5D7387E8`) | `0x0ca8f938Aba2214eA11eb451e795A8ef7B720C18` (backstop `0x52CC2789…CdF8`) | `0x2d5Aa449FB8C5646C81BC3C1D2034c2d37F17099` |

The admin, relayer and freezer roles on the Ethereum and Robinhood sets were read live with `hasRole` (all true).

### 3.2 PAU (diamond) generation and other SLL contracts

| Chain | Contract | Address |
|-------|----------|---------|
| Ethereum | `SPUSDC_PAU_ALM_PROXY` / `SPUSDC_PAU_CONTROLLER` / `SPUSDC_PAU_RATELIMITS` | `0x8D719A830b00e5571db00D173505CD56c0Ec224a` / `0x4623cdEf0FB92499fd20f710318Cf17B8a7EB6bC` / `0x222712581c3631DDF938f98Dab29a6D098ec6829` |
| Ethereum | `SPARK_PAU_FACTORY` / `SPARK_BEACON` / `SPARK_DEFAULT_PAU_ASSEMBLER` | `0x60eB26db57bD058B6D742a1f6350A7FFeAb0681E` / `0xd47230358AB6c52A0a988150Ac4Ab888FE8B7786` / `0xb2468FCc87E3BE45Bfa521e567731375887BF8e2` |
| Ethereum | `BINANCE_OTC_BUFFER` (EIP-1967, impl `0xcd2EA34d16d57d896EF6821f2E9C5aaE076FdFbe`) | `0x1851c64BBfad132CBE75481f1690C381288ea492` |
| Base | `PAU_CONTROLLER` / `PAU_RATELIMITS` / `PAU_ACCESS_CONTROLS` / `CCTP_FACET` | `0xd864bF1Ea2f78Dc2013E3FC7e4C474383BE9d456` / `0x5E311e8BCe95F4e8d4920E70985ED4aC122a838A` / `0xE593c8c6a31d88cab100244Afd352efb127f9a16` / `0xb22d50c393c6E1D13E3e05B172448dD8BF8DdC32` |
| Arbitrum | `PAU_CONTROLLER` / `PAU_RATELIMITS` / `PAU_ACCESS_CONTROLS` / `CCTP_FACET` | `0x04ACB9e9bbd64A425677edC535D6B30cfD74E42f` / `0x4824C4336a1a11979068A544958dCe5D49B42752` / `0x8386f819860D54B1180539Ff4852E4CAECef8A1D` / `0xeCCA0D296Cb133081d41E9772B60D57F5fd2798E` |

### 3.3 Chains with no SLL

- **BNB Smart Chain (56):** `BSC.sol` lists only the SPK LayerZero OFT `0xAfF2e841851700D1Fc101995Ee6b81Ae21Bb87D7` (13660 B) and its LayerZero config. There is no ALMProxy.
- **Polygon PoS (137):** no registry file. The addresses `0x1601843c…347E`, `0x2917956e…09cA` and `0x7A5FD5cf…b188` have 2770 B of code on Polygon **and** BNB. This is an unrelated `Ownable` token-sweep contract (`owner()` = `0x72676183…ce20`, no `CONTROLLER()`). It is a decoy.
- **Arc (5042):** no registry file. All 66 SLL/Savings/Grove key addresses returned `0x`.
- Non-target chains with an SLL: Unichain (130), X Layer (196). Not covered here.

---

## 4. Cross-chain summary

| Chain | ALMProxy | Controller kind | PSM3 | Spark Vault V2 | PAU |
|-------|----------|-----------------|------|----------------|-----|
| Ethereum (1) | `0x1601…347E` | Mainnet v1.10 | — (uses Sky LitePSM) | spUSDC, spUSDT, spETH, spPYUSD | ✓ (spUSDC) |
| Base (8453) | `0x2917…09cA` | Foreign v1.8 | ✓ | — | ✓ |
| Arbitrum (42161) | `0x92af…8709` | Foreign v1.8 | ✓ | spUSDT | ✓ |
| Optimism (10) | `0x8766…36fB` | Foreign v1.8 | ✓ | — | — |
| Avalanche (43114) | `0xecE6…7FeC` | Foreign v1.8 | — | spUSDC | — |
| Robinhood (4663) | `0xfD2f…dB24` | Foreign v1.10 | — | spUSDG | — |
| BNB (56) | — | — | — | — | — |
| Polygon (137) | — (decoy) | — | — | — | — |
| Arc (5042) | — | — | — | — | — |

---

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| ALMProxy, ALMProxyFreezable | **Immutable** | EIP-1967 impl slot = `0x0` on all six chains | None. Logic moves by `CONTROLLER` role rotation. |
| Main/ForeignController | **Immutable** | impl slot `0x0` | Replaced by a new deployment. Watch `RoleGranted(CONTROLLER, newController)` on the ALMProxy and RateLimits. |
| RateLimits | **Immutable** | impl slot `0x0` | Admin can only change the data (`RateLimitDataSet`). |
| OTCBuffer (ETH) | EIP-1967 proxy (163 B) | impl slot = `0xcd2EA34d…dFbe` | Spark governance. `Upgraded(address)` `0xbc7cd75a…2d3b`. |

---

## 6. Detection invariants & gotchas

1. **The ALMProxy is the economic actor.** The relayer EOA/multisig signs the transaction. The controller is `msg.sender` to the proxy. The ALMProxy is the `from`/`owner` in every token and vault event. Key on the ALMProxy for balances and on the controller for action type.
2. **Unlimited keys emit nothing.** `triggerRateLimitDecrease` returns early when `maxAmount == type(uint256).max`. Flows under an unlimited key have no `RateLimit*` event. Use ERC-20 `Transfer` from the ALMProxy as the complete source.
3. **Rate-limit keys are hashed.** A key is `keccak256(abi.encode(LIMIT_X, target))` for asset/vault limits, or `keccak256(abi.encode(LIMIT_X, uint32 domain))` for CCTP domain limits. Some keys are bare `LIMIT_X` (for example `LIMIT_USDS_MINT`). Precompute `(LIMIT_X, target)` pairs to decode `topic1`. §8 lists the base keys.
4. **Two `CCTPTransferInitiated` topics.** Every deployed Spark controller (v1.8, v1.10) emits the 4-field form with `uint64 nonce` (`0x805a2d8b…`). The repo HEAD and the Grove fork emit the 3-field form (`0xa613b2b0…`). Index both.
5. **ERC-4626 selector arity differs by chain.** v1.10 controllers (ETH, Robinhood) use the 3-argument `depositERC4626(address,uint256,uint256)` `0x7dbe3c90` (with a min-shares guard). v1.8 controllers (Base, Arb, OP, Avax) use the 2-argument `0x85f4881d`. A calldata filter on one selector misses the other chains.
6. **Address reuse across chains with different contracts.** `0x1601843c…347E` is the ALMProxy on Ethereum but PSM3 on Base. `0x4eE67c8D…fa38` is the controller on Avalanche but ALMProxyFreezable on Arbitrum. `0x86036CE5…60A8` is the controller on Base but `SPARK_BEACON` on Arbitrum. `0x65d946e5…f7a1` is `SPARK_EXECUTOR` on Arbitrum but `SSR_AUTH_ORACLE` on Base. **Always key on `(chainId, address)`.**
7. **Controller rotation is routine.** Spark replaced controllers many times (v1.0 → v1.10). The controller address in this doc is the one that held `CONTROLLER` on 2026-10-30. Re-check with `hasRole(0x70546d1c…, controller)` on the ALMProxy.
8. **Freeze signal.** `RelayerRemoved` on a controller, or `RoleRevoked(RELAYER, …)`, means the freezer multisig stopped the relayer. `ControllerRemoved` does the same on an ALMProxyFreezable.
9. **The PAU generation has no public source.** The `diamond-pau` repo is private. The Ethereum spUSDC PAU controller emits an unlisted topic `0x726a0d55f4fd1075…`. Its topics and selectors are not documented here.
10. **Avalanche and Robinhood have no PSM3.** `psm()` returns `0x0` on both. On Robinhood the SLL only feeds the spUSDG vault with USDG (`take`) — it held about 1,132 USDG directly on 2026-10-30.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_RATE_LIMIT_DECREASE      = '\x2f9bcbd665fb7984aac3b6a05bb4ac8b303137a34ed4cc5fcd47622f52bdf046'
TOPIC_RATE_LIMIT_INCREASE      = '\xb824249bbde4df2bf5473f603ab3aa717ea2e37b908d9fb4440b962fb656d0ac'
TOPIC_RATE_LIMIT_DATA_SET      = '\x356822943b80f809508a684c67d901d5c13b6a22161bf07d510e50a6cb727028'
TOPIC_CCTP_TRANSFER_V1NONCE    = '\x805a2d8b8d8d00211d6d0b649e13d17c52249698ce305975aec1c912d50acfd6'
TOPIC_CCTP_TRANSFER_V2         = '\xa613b2b0a8074f0163704e8596561e20fda50f29acee27f8d0bc4c73521034f3'
TOPIC_MINT_RECIPIENT_SET       = '\x5e7cfea10f05abc55e716d0d5031f3eea4eabbe012e9bf1d56c5034bba4bfa30'
TOPIC_LZ_RECIPIENT_SET         = '\x6c34eba04bf16b35385ac7487ab08f9023bcd9836a5bd53dc60ec0da331b4543'
TOPIC_MAX_SLIPPAGE_SET         = '\xd8df93d785f3d0d4294fd7b61e5d749c20eec95a2fed5b6b502a4cad09199ca6'
TOPIC_MAX_EXCHANGE_RATE_SET    = '\xfce512ccb77d3237e23e27ae3357b9527a46adbc1faf1367475efd86a2e7aeed'
TOPIC_RELAYER_REMOVED          = '\x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b'
TOPIC_OTC_SWAP_SENT            = '\x26a1feb7262fba528b97aa0124288bf5731a280656b6296294baa4f646fb28b0'
TOPIC_OTC_CLAIMED              = '\x59c2ea6a2ea5564fe0f93b71f4331002ce9a5f10b01a85fc130d66dbc5503bb6'
TOPIC_ROLE_GRANTED             = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED             = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
TOPIC_CONTROLLER_REMOVED       = '\x33d83959be2573f5453b12eb9d43b3499bc57d96bd2f067ba44803c859e81113'
-- ===== Roles =====
ROLE_CONTROLLER                = '\x70546d1c92f8c2132ae23a23f5177aa8526356051c7510df99f50e012d221529'
ROLE_RELAYER                   = '\xab4f864e5201b0fde9b5ee3e4cf96384802b0ffdfcf7f9de4699ce21a30afc4f'
ROLE_FREEZER                   = '\x0ac42a08299cbc4428ec38ad4a8e7d7440779fbbb20ea90bd10c094a406cfa6f'
-- ===== Selectors (chain-agnostic) =====
SEL_DO_CALL                    = '\x3aada4d2'
SEL_DO_CALL_WITH_VALUE         = '\xd71f93f8'
SEL_DO_DELEGATE_CALL           = '\x8ce4a1f2'
SEL_MINT_USDS                  = '\x536f6b7e'
SEL_BURN_USDS                  = '\x96122b62'
SEL_SWAP_USDS_TO_USDC          = '\x5acb7053'
SEL_SWAP_USDC_TO_USDS          = '\x115c48d5'
SEL_TRANSFER_USDC_TO_CCTP      = '\xbcd7e46c'
SEL_TRANSFER_TOKEN_LZ          = '\x203f0e3e'
SEL_TRANSFER_ASSET             = '\x439e2e45'
SEL_DEPOSIT_ERC4626_3ARG       = '\x7dbe3c90'
SEL_WITHDRAW_ERC4626_3ARG      = '\x90893cbe'
SEL_REDEEM_ERC4626_3ARG        = '\xa60c8029'
SEL_DEPOSIT_ERC4626_2ARG       = '\x85f4881d'
SEL_WITHDRAW_ERC4626_2ARG      = '\x0b372e57'
SEL_REDEEM_ERC4626_2ARG        = '\xd9acb348'
SEL_DEPOSIT_AAVE               = '\x2cefff96'
SEL_WITHDRAW_AAVE              = '\x7891c043'
SEL_DEPOSIT_PSM                = '\x7a1cd355'
SEL_WITHDRAW_PSM               = '\xb41b48af'
SEL_TAKE_FROM_SPARK_VAULT      = '\x7a1a0d66'
SEL_SWAP_CURVE                 = '\x1eaef443'
SEL_OTC_SEND                   = '\x58c3e3a9'
SEL_REMOVE_RELAYER             = '\x60f0a5ac'
SEL_TRIGGER_RL_DECREASE        = '\x3bf076b0'
SEL_SET_RATE_LIMIT_DATA_5      = '\xf6a82d1a'
-- ===== Addresses (network-specific) =====
ETH_SPARK_ALM_PROXY            = '\x1601843c5e9bc251a3272907010afa41fa18347e'
ETH_SPARK_ALM_CONTROLLER       = '\x5c46fc65855c0c7465a1ea85eea0b24b601502d3'
ETH_SPARK_ALM_RATE_LIMITS      = '\x7a5fd5cf045e010e62147f065ceae59e5344b188'
ETH_SPARK_ALM_PROXY_FREEZABLE  = '\xe5c6318456a7cb6f74f93b4eee4616db5fcef699'
ETH_SPARK_SPUSDC_PAU_ALM_PROXY = '\x8d719a830b00e5571db00d173505cd56c0ec224a'
ETH_SPARK_SPUSDC_PAU_CTRL      = '\x4623cdef0fb92499fd20f710318cf17b8a7eb6bc'
ETH_SPARK_BINANCE_OTC_BUFFER   = '\x1851c64bbfad132cbe75481f1690c381288ea492'
ETH_SPARK_PROXY                = '\x3300f198988e4c9c63f75df86de36421f06af8c4'
BASE_SPARK_ALM_PROXY           = '\x2917956eff0b5eaf030abdb4ef4296df775009ca'
BASE_SPARK_ALM_CONTROLLER      = '\x86036ce5d2f792367c0aa43164e688d13c5a60a8'
BASE_SPARK_ALM_RATE_LIMITS     = '\x983ec82e45c61a42fdda7b3c43b8c767004c8a74'
BASE_SPARK_ALM_PROXY_FREEZABLE = '\x92d7b06e5844e67174ae9e86bdcb06428482ddf9'
ARB_SPARK_ALM_PROXY            = '\x92afd6f2385a90e44da3a8b60fe36f6cbe1d8709'
ARB_SPARK_ALM_CONTROLLER       = '\xc40611ac4fff8572dc5f02a238176edcf15ea7ba'
ARB_SPARK_ALM_RATE_LIMITS      = '\x19d08879851fb54c2dcc4bb32b5a1ea5e9ad6838'
ARB_SPARK_ALM_PROXY_FREEZABLE  = '\x4ee67c8db1baa6dde99d936c7d313b5d31e8fa38'
OP_SPARK_ALM_PROXY             = '\x876664f0c9ff24d1aa355ce9f1680ae1a5bf36fb'
OP_SPARK_ALM_CONTROLLER        = '\x689502bc817e6374286af8f171ed4715721406f7'
OP_SPARK_ALM_RATE_LIMITS       = '\x6b34a6b84444dc3fc692821d5d077a1e4927342d'
AVAX_SPARK_ALM_PROXY           = '\xece6b0e8a54c2f44e066fbb9234e7157b15b7fec'
AVAX_SPARK_ALM_CONTROLLER      = '\x4ee67c8db1baa6dde99d936c7d313b5d31e8fa38'
AVAX_SPARK_ALM_RATE_LIMITS     = '\xb79972e8b21f0de911e65ac342ac85ad38c9a77a'
AVAX_SPARK_ALM_PROXY_FREEZABLE = '\x93c81adc7f98fdbc8c7a15ecbed312c8f6adbcb3'
ROBIN_SPARK_ALM_PROXY          = '\xfd2fd4b046136b540a56c11c75ac679ae7d1db24'
ROBIN_SPARK_ALM_CONTROLLER     = '\xcf8d58a6eef2a1cae2ce69bc463b1178fb76ba1e'
ROBIN_SPARK_ALM_RATE_LIMITS    = '\x5c1fde9d4c7f1bf4bc5deaa2a7752e56232c68a0'
ROBIN_SPARK_ALM_PROXY_FREEZABLE= '\xaea9f5de56e6c20383a1fcc2c3629dca0a92ce41'
ROBIN_SPARK_EXECUTOR           = '\x826aeaeee9233fa8ba199518dd8621a5962b1d02'
```

---

## 8. Rate-limit base keys (`keccak256("LIMIT_…")`)

Use these to decode `topic1` of the `RateLimit*` events. A per-target key is `keccak256(abi.encode(base, target))`.

| Name | Key |
|------|-----|
| `LIMIT_USDS_MINT` | `0xcb0537d5e5dba65a8edbac12555995860e5b8e1b70996011edb1ca8173e56d3c` |
| `LIMIT_USDS_TO_USDC` | `0x00d4cb8ac2838f11d95b0136a919a13b994f920024aba35eee16dc433c65851c` |
| `LIMIT_USDC_TO_CCTP` | `0x0476a9fd902eafdb5bcdabd9f0523dd7aacf7aa0c38c0e6ab912f5fed00f8e11` |
| `LIMIT_USDC_TO_DOMAIN` | `0xfa746459736d4da7e93566b5ec05608174be6bf01c7207464bfb77d034bbdc7f` |
| `LIMIT_4626_DEPOSIT` | `0xc80e541ae8dbb00d82e12edc8dbc29e6ae9ebed737088df9145797f7edca3b42` |
| `LIMIT_4626_WITHDRAW` | `0xcbdb6738b19dd3b24f89f36d3582b7d46aa62654d6d68e2f61094c597ada836b` |
| `LIMIT_AAVE_DEPOSIT` | `0x8e6d782dd232ba18cda332ab87226668a41414f4096db2b33575872cd6fca16a` |
| `LIMIT_AAVE_WITHDRAW` | `0x519fa96e0bcf84b705fc396cd38f7f5e661413cb0fe321a78e8a29091b5bf262` |
| `LIMIT_PSM_DEPOSIT` | `0x7c568012181a682df173a98c82cacfe8564f179d5b53587ce54b9db76daddbcc` |
| `LIMIT_PSM_WITHDRAW` | `0xa4498e16e9fd1065def948ac6ddfde917436a7ebbf0cd1df291fa2906b825622` |
| `LIMIT_SPARK_VAULT_TAKE` | `0x6308851b8d5124971e470b9e9c2b772d838474c039290fda74a0d3c311748b5b` |
| `LIMIT_ASSET_TRANSFER` | `0x48f98264e3feb9c04c94251c86b84a95f369fb2973906e457f22ec9080cb6755` |
| `LIMIT_LAYERZERO_TRANSFER` | `0xce9586fd7a1cc9f750fc9dbdf85d976df46745d82efe8f41ad6419c6f54c85cf` |
| `LIMIT_CURVE_SWAP` | `0xf5f2d74aaf676a1e257128848eea02c11877822edb6adc80fd8b24fb5a6b2b5a` |
| `LIMIT_OTC_SWAP` | `0x377016c0c3bbc11bd9a8306c03781e6a61fd790f6dabd87d73e10e6f1323a3fb` |
| `LIMIT_USDE_MINT` / `LIMIT_USDE_BURN` | `0x5def078412c37c191fd2d189c95907ded1a100c5252bc3d643bb619866954517` / `0x88fe4304240f9fdabd8d614954877c91faacf3746c24df5803bac9e49977b63b` |

---

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `spark-alm-controller` source (commit `9c7dffe`, 2026-10-20). Live `eth_getLogs` confirmed `RateLimitDecreaseTriggered`/`RateLimitIncreaseTriggered` on the ETH (1,215 logs in about 10k blocks), Base and Avalanche RateLimits, and the 4-field `CCTPTransferInitiated` on the ETH (110) and Base (79) controllers. Controller selectors were confirmed by a PUSH4 scan of each live controller's bytecode (§2.2 "Live on" column).
- **Addresses:** parsed from `spark-address-registry` (`src/Ethereum.sol`, `Base.sol`, `Arbitrum.sol`, `Optimism.sol`, `Avalanche.sol`, `Robinhood.sol`, `BSC.sol`). Each address was checked with `eth_getCode`. The EIP-1967 slot was read for each. Wiring (`proxy()`, `rateLimits()`, `psm()`, `hasRole`) was read live.
- **Chain coverage:** Polygon and Arc were checked with `eth_getCode` for all 66 SLL/Savings/Grove key addresses. Polygon and BNB return only the 2770 B sweep decoy. Arc returns `0x` for all.
- **Not verified:** PAU/diamond topics and selectors (source private). Historic controller addresses before the current ones are not listed.

Authoritative sources:
- [sparkdotfi/spark-alm-controller](https://github.com/sparkdotfi/spark-alm-controller) — source of truth for signatures.
- [sparkdotfi/spark-address-registry](https://github.com/sparkdotfi/spark-address-registry) — addresses for each chain.
- [Spark docs — Spark Liquidity Layer](https://docs.spark.fi/)
- Explorers: [Etherscan](https://etherscan.io/address/0x1601843c5E9bC251A3272907010AFa41Fa18347E) · [Basescan](https://basescan.org) · [Arbiscan](https://arbiscan.io) · [Optimistic Etherscan](https://optimistic.etherscan.io) · [Snowtrace](https://snowtrace.io) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com)

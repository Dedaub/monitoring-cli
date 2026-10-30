# Arcus pTokens — Topics, Selectors, Addresses (Robinhood Chain)

**Status:** verified against live RPC on Robinhood Chain (4663) on 2026-10-30. No source is published or verified for these contracts. Signatures come from the public 4-byte / event signature database and from local `keccak256` matches against live logs; each topic below was seen in live logs unless the row says otherwise. Parameter names are not public; the names in the tables describe the observed values.
**Scope:** the pToken factory, the pToken beacon and the 17 pToken vaults on **Robinhood Chain (4663) only**. A pToken is an ERC-20 vault share (ERC-4626 with ERC-7540 asynchronous requests) that owns one Arcus perps account with a fixed market, direction and leverage (for example pBTC3x = 3x long BTC). Topics and selectors are chain-agnostic. Addresses are network-specific.

The `PTokenFactory` (UUPS proxy) deploys each pToken as a **BeaconProxy** of one `UpgradeableBeacon`. A pToken takes USDG through `requestDeposit`. The pToken manager then calls `bridgeDeposit`, which deposits the USDG into Arcus through the `PaxosDepositProxy` (see [perps.md](perps.md)). The pToken address itself is the Arcus account owner (`accountIndex` 0). The manager fulfils requests at a NAV that a `NAV_SIGNER_ROLE` key signs. Redemptions come back through a normal Arcus withdrawal to the pToken address. There is no on-chain price oracle; NAV is an off-chain signed value.

---

## 0. Contract families

| Contract | Role | Proxy? |
|----------|------|--------|
| **PTokenFactory** | Registry and deployer (`pTokenCount()`, `pTokenAt(uint256)`), per-pToken config (manager, cap), minter allow-list, NAV signer role. `bridgeVault()` = PaxosDepositProxy. | UUPS (EIP-1967), 109 B |
| **PToken beacon** | OpenZeppelin `UpgradeableBeacon`. `implementation()` is the logic of every pToken. Owner = Safe 2-of-5 `0x81b8…41bd`. | No (590 B) |
| **pToken** (×17) | ERC-20 share + ERC-4626 + ERC-7540 async deposit/redeem + ERC-7887 cancel + ERC-1271 `isValidSignature` (signs Arcus withdrawals). Asset = USDG (6 dec). Share decimals 18. | BeaconProxy, 229 B |
| pToken liquidity manager | `0x9d90417ea422c8d03e94288e70d6747df9a15e64`. UUPS proxy that keeps pToken pools on the Uniswap v4 PoolManager. It is an allowed minter on the factory. | UUPS (EIP-1967) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 pToken (emitted by each pToken address)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbb58420bb8ce44e11b84e214cc0de10ce5e7c24d0355b2815c3d758b514cae72` | `DepositRequest(address indexed controller, address indexed owner, uint256 indexed requestId, address sender, uint256 assets)` | ERC-7540. USDG in. |
| `0x679094ab1e8941d9ab9e9896c18979354edff487df302d0cafbf69d5fcaa8747` | `DepositRequestBridged(uint256 indexed requestId, uint64 indexed inboxIndex, uint256 assets)` | `inboxIndex` = BridgeVault `DepositInitiated.inboxIndex` in the same tx. |
| `0x30b67ebe73bdc8f18c2937e7e61c3d66fc9e5dd2aa35ae20ee1d5f6d0d52895d` | `DepositRequestFulfilled(uint256 indexed requestId, address indexed controller, uint64 indexed inboxIndex, uint256 assets, uint256 shares, uint256, uint256, uint64)` | Shares become claimable. |
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` | ERC-4626 claim. **Shares minted.** |
| `0x1fdc681a13d8c5da54e301c7ce6542dcde4581e4725043fdab2db12ddc574506` | `RedeemRequest(address indexed controller, address indexed owner, uint256 indexed requestId, address sender, uint256 shares)` | ERC-7540. Shares locked. |
| `0xe6c9bec1b48e68187a62f9b65d5f2c8013c6664177c4e7f1314fd7481500749f` | *(name not public)* `(uint256 indexed redeemRequestId, uint64 indexed withdrawalId, uint256 assets)` | Links a redeem to a BridgeVault `withdrawalId` (checked: id `0x7d44` → `WithdrawalInitiated` to pBTC3x, same amount). |
| `0x11cf0d1e21b0ff4b9cfce6b48c9f2605ed8433411fb3f884e722d4495e1d1ede` | `RedeemRequestFilled(uint256 indexed requestId, address indexed controller, uint64 indexed withdrawalId, uint256, uint256, uint256, uint64)` | Assets become claimable. |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` | ERC-4626 claim. **USDG out, shares burned.** |
| `0x4ae0134aad5d0e98e82f45680facd628ee6b5aa85ad9a85248a7ef47319f8c50` | `CancelDepositRequest(address indexed controller, uint256 indexed requestId, address sender)` | ERC-7887. |
| `0x295a9a8b44c0ac92394b0da92ef469784ff064156f08dab8316760c064c6cd2f` | `CancelDepositClaim(address indexed controller, address indexed receiver, uint256 indexed requestId, address sender, uint256 assets)` | ERC-7887. In bytecode; not seen in the sample. |
| `0xa16c0f2cab616ed5d17cd544655b00d7062a1df7c457960cc8b9bf60770f9236` | `CancelRedeemRequest(address indexed controller, uint256 indexed requestId, address sender)` | ERC-7887. |
| `0x9c133d4657dc9cd12f4c08cef86ef778dbbe03f3ad3b661ff14d36bc3febb1fb` | `CancelRedeemClaim(address indexed controller, address indexed receiver, uint256 indexed requestId, address sender, uint256 shares)` | ERC-7887. |
| `0xceb576d9f15e4e200fdb5096d64d5dfd667e16def20c1eefd14256d8e3faa267` | `OperatorSet(address indexed controller, address indexed operator, bool approved)` | ERC-7540. In bytecode. |
| `0x433b82816258a4d652299bd6388df04d8f3437d6e6a5f61dd276c45b3e0b9195` | `DepositFeeUpdated(uint16 oldBps, uint16 newBps)` | Fee now 25 bps on pHOOD3x. |
| `0x9fb50361ff20c95ee94e29cafef7c5a88611fb870013bc74091a2fd5e2cc496d` | `DepositsPausedUpdated(bool oldPaused, bool newPaused)` | Same topic0 as the BridgeVault event. In bytecode. |
| `0x7acc65b159c7ebf31f060cac25f338c43ac6194e00f31615f84cba9735446b4d` | `NameAndSymbolUpdated(string, string)` | |
| `0xa5d4097edda6d87cb9329af83fb3712ef77eeb13738ffe43cc35a4ce305ad962` | `ContractURIUpdated()` | |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | Share mint (`from` = 0) / burn (`to` = 0). |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | |

Unnamed topics also live on pTokens (names not public): `0x8b41b7053afb5d0fd378e8963fc48cf0f9d0c4da482369d486158ca356b0912e` (2 indexed: request id, address; 1 word), `0xb9d9388095bd5bafc80788ddc6fab2fca83da31b4bb1acf3749ac6ce56946c58` (2 indexed ids; data `bool, uint256, uint256` — a NAV report shape), `0xced4154795bc88121e9211b4513cb27bb1090ff412b810281f7b3cb17df72eb4` (no index; 1 word), `0x53d13c6cddd1a5a27af4fe8c636d3e3f9c15a37e4802a02e59b6c5366a1ecbf6` (2 indexed; 1 word). Counts on pBTC3x + pHOOD3x since deployment: `DepositRequest` 291, `DepositRequestBridged` 290, `DepositRequestFulfilled` 290, `Deposit` 284, `RedeemRequest` 278, unnamed `0xe6c9…` 267, `RedeemRequestFilled` 267, `Withdraw` 266.

### 1.2 PTokenFactory (`0x9c36…A0BB`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd32a88fa7585303533fc903eac9881b690a1f225131a3cd173b16f39e5ee9f8c` | `PTokenCreated(address indexed pToken, bytes32 indexed salt, address indexed asset, string name, string symbol, uint8 decimals, uint256, address manager, uint256)` | Current version. 16 logs. |
| `0xe27b420b6fbd662cd18e44fa3a98a56e5ef5cffb17459f1aa076edb80bbb5165` | `PTokenCreated(address indexed pToken, bytes32 indexed salt, address indexed asset, string name, string symbol, uint8 decimals, address manager, uint256)` | First version (pTEST only). |
| `0x1dfce39fd211882b628d23dffd5a09c01ae6480b40fbae1762fed359cf60dc30` | `MinterAllowedUpdated(address indexed pToken, address indexed minter, bool allowed)` | 225 logs, 10 distinct minters. |
| `0x8df26d30992ecfde135bbe59c1f267d82e2aae9d32fdae41551a38fe8b7bda87` | `ManagerUpdated(address, address, address)` (3 indexed) | Manager rotation per pToken. |
| `0x86cafad4e48ec1edd3bf1bb4b05fbe08a979cc3a0bfceb82a841aa502c5e666b` | `BridgeVaultUpdated(address indexed old, address indexed new)` | Same topic0 as the CheckpointManager event. |
| `0x46a98d582ba4c3ce698945c0010d1e6e1ba1c4a413ee1dfb18c0b31076be79e9` | `BeaconUpdated(address indexed old, address indexed new)` | |
| `0x944f9ca1b679ec8381ef5d5419085e9ea4df3b274eb009910b19bd295bd18fc3` | `MetadataBaseURIUpdated(string, string)` | |
| `0x719de5e7c4f978ca25aa5bb2277071381998d60668f773dcd4f7cdae3780249d` | *(name not public)* `(address indexed pToken, uint256 old, uint256 new)` | 29 logs. Values match the cap in `config(pToken)` (pHOOD3x 1e12 → 1.1e12). |
| `0x64e1a91e30dcb3421c2a16d9b8b28c5aa233d00726a19c2fc1c9fac5612fe59d` | *(name not public)* `(address indexed, bool)` | 23 logs. |
| `0x54c39467613ff24c9aca48d220e81bcaaf37a4833abe11a5aa225b8188e60065` | *(name not public)* `(uint256, uint256)` | 1 log at initialization. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | Factory proxy **and** beacon. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` / `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleGranted` / `RoleRevoked` | AccessControl. |

---

## 2. Function signatures (chain-agnostic)

### 2.1 pToken

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x85b77f45` | `requestDeposit(uint256,address,address)` | ERC-7540. `(assets, controller, owner)`. |
| `0x7d41c86e` | `requestRedeem(uint256,address,address)` | ERC-7540. `(shares, controller, owner)`. |
| `0x2e2d2984` / `0x6e553f65` | `deposit(uint256,address,address)` / `deposit(uint256,address)` | Claim fulfilled deposit. |
| `0xda39b3e7` / `0x94bf804d` | `mint(uint256,address,address)` / `mint(uint256,address)` | Claim fulfilled deposit by shares. |
| `0xba087652` | `redeem(uint256,address,address)` | Claim fulfilled redeem. |
| `0xb460af94` | `withdraw(uint256,address,address)` | Claim fulfilled redeem by assets. |
| `0xb9cf0634` / `0x2b9d9c1f` | `cancelDepositRequest(uint256,address)` / `cancelRedeemRequest(uint256,address)` | ERC-7887. |
| `0x69d77a44` | `claimCancelDepositRequest(uint256,address,address)` | ERC-7887. |
| `0x42cc5a88` | `bridgeDeposit(uint256,uint256)` | Manager. Sends request USDG to Arcus via PaxosDepositProxy. |
| `0x53131ea1` / `0x748e20ef` | `rejectDepositRequest(uint256)` / `rejectRedeemRequest(uint256)` | Manager. |
| `0x558a7297` | `setOperator(address,bool)` | ERC-7540. |
| `0x0fe21264` | `setDepositFee(uint16)` | Admin. |
| `0x1c481e2d` | `setDepositsPaused(bool)` | Admin. |
| `0x5a446215` | `setNameAndSymbol(string,string)` | Admin. |
| `0x1626ba7e` | `isValidSignature(bytes32,bytes)` | ERC-1271. Lets the pToken sign its Arcus withdrawals. |
| `0x01e1d114` | `totalAssets()` | view. NAV in USDG (6 dec). DefiLlama TVL source. |
| `0x481c6a75` / `0xac03e9f0` / `0x9e9cb275` | `manager()` / `bridgeVault()` / `accountIndex()` | view. |
| `0x3d302d06` / `0xc2860610` | `reservedAssets()` / `netDeposited()` | view. |
| `0x8e9bf9d2` / `0x4a1dc092` | `depositRequest(uint256)` / `redemption(uint256)` | view. |
| `0x26c6f96c` / `0xf5a23d8d` | `pendingDepositRequest(uint256,address)` / `pendingRedeemRequest(uint256,address)` | view. |
| `0x995ea21a` / `0xeaed1d07` | `claimableDepositRequest(uint256,address)` / `claimableRedeemRequest(uint256,address)` | view. |
| `0x3aa9c131` / `0xab879827` / `0x60da3e83` | `requestTtl()` / `depositFeeBps()` / `depositsPaused()` | view (pHOOD3x: TTL 604,800 s, fee 25 bps). |

### 2.2 PTokenFactory and beacon

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x07f7e37c` | `pTokenCount()` | view (17). |
| `0xb806d460` | `pTokenAt(uint256)` | view. |
| `0x0e68ec95` | `config(address)` | view. `(manager, cap, …, bool)`. |
| `0x7f41826b` / `0x5df8122f` | `managerOf(address)` / `setManager(address,address)` | |
| `0xac03e9f0` / `0xebcb0b7a` | `bridgeVault()` / `setBridgeVault(address)` | |
| `0x59659e90` / `0xd42afb56` | `beacon()` / `setBeacon(address)` | |
| `0xdba69b7c` | `NAV_SIGNER_ROLE()` | = `0x2fc965e6d3b4285cc1c2fdb81c559078c383a02a3e5c7d916842895edb7e4955`. |
| `0x9f3d1a2a` / `0xfb94bd8a` | `metadataBaseURI()` / `setMetadataBaseURI(string)` | |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | Factory UUPS. |
| `0x3659cfe6` | `upgradeTo(address)` | Beacon. `onlyOwner`. **Upgrades all pTokens at once.** |
| `0x5c60da1b` | `implementation()` | Beacon. view. |

The pToken-creation function and several factory setters have selectors with no public signature (`0x1c0d9bca`, `0x1f5f81f5`, `0x22555cda`, `0x48477f38`, `0x4d9f30fc`, `0x4e666f20`, `0x57d41c64`, `0x8380f472`, `0x8da87eb1`, `0xc2eabaf3`, `0xd3c5ee0e`, `0xd85777d0`, `0xed6d7b26`, `0xfe618ab1`). Use `PTokenCreated` to detect new pTokens.

---

## 3. Addresses — Robinhood Chain (chain ID 4663)

All verified with `eth_getCode` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **PTokenFactory** | `0x9c3663FA9ab976E67B42939486EC4966Cb41a0BB` | Registry + deployer. |
| **PToken beacon** | `0x33846348210a0cc0345f354d9de52b89ad473a76` | `UpgradeableBeacon`. |
| pToken implementation | `0x1815a37b6027ae8066720d873a508f25fc151ac5` | 31,386 B. `version()` = 2. |
| Factory admin Safe | `0x81b80499c396a9931b9e44953425a82c1b2541bd` | Safe 2-of-5. `DEFAULT_ADMIN_ROLE` on the factory and beacon owner. |
| NAV signer | `0xc70352b9a07be0e6afdce63ac05c540e7d8fe45a` | `NAV_SIGNER_ROLE`. |
| pToken manager | `0xb7410dc44e2715161e9914272e2d55d7c5061faa` | EOA. Calls `bridgeDeposit`. |
| pToken liquidity manager | `0x9d90417ea422c8d03e94288e70d6747df9a15e64` | Uniswap v4 position keeper (`poolManager()` = `0x8366a39c…0951`). |
| USDG (asset) | `0x5fc5360d0400a0fd4f2af552add042d716f1d168` | |

pTokens (`pTokenAt(0..16)`; test tokens are excluded from DefiLlama TVL):

| # | Address | Symbol | Name / note |
|---|---------|--------|-------------|
| 0 | `0x1193bcbfafeb2f25c516817c46bd3143936d1d5c` | pTEST | Arcus pToken Test (test) |
| 1 | `0x4472c69d299382f8847ebce4fc6ed8e295510e3e` | pBTC3x | Arcus BTC (3x Long) |
| 2 | `0xe24cabdf76dd1c2576049167eb1755c84b985c36` | pHOOD3x | Arcus HOOD (3x Long) |
| 3 | `0x4595a18b47c6fb46f3a157e2918f5c34cdca35eb` | pTESTR | pToken Redemption Test (test) |
| 4 | `0x925f92f055edb79c42b5d45e64a1b74143b90ea0` | pBTC | Arcus BTC (1x Long) |
| 5 | `0xc25c966168a8e933b0aba0dc8a25cac4a2b2b91d` | sBTC | Arcus BTC (1x Short) |
| 6 | `0xadcceee8e422050f890522fa798f8a93a4857083` | sBTC3x | Arcus BTC (3x Short) |
| 7 | `0x0053333fcaff9486fa55877044f09137c1a52530` | sHOOD3x | Arcus HOOD (3x Short) |
| 8 | `0x37a2afaa98648f2e13658623885f821ac8365609` | pGLD5x | Arcus GLD (5x Long) |
| 9 | `0xb2cb7371bc45a460f856712a3088c23acd385df8` | sGLD5x | Arcus GLD (5x Short) |
| 10 | `0x9b319b9ffbe969be6fcdcb0ad09ad0405eda05b0` | pSPCX5x | Arcus SPCX (5x Long) |
| 11 | `0x2e9c527032daaa6084b15bf0c2dbf50f9675253c` | sSPCX5x | SPCX 5x short |
| 12 | `0x5c3b9a9b021e86b54202abcb4580f1f5c271875b` | pGME5x | GME 5x long |
| 13 | `0x1a596466cb593bee293be8366d9ce493582189c2` | sGME5x | GME 5x short |
| 14 | `0x122408c1399e51c41b096402fea46e20e762a950` | pTEST3 | test |
| 15 | `0x8b9d2eb675e33e541cb7de25a55724d2e70e8dab` | pSPCX3x | SPCX 3x long |
| 16 | `0x17271bd2a1eaa350a002d25236bcc4dc07ceb6a9` | sSPCX3x | Arcus SPCX (3x Short) |

## 4. Cross-chain summary

| Chain (ID) | PTokenFactory | Beacon | pTokens |
|------------|---------------|--------|---------|
| Robinhood Chain (4663) | `0x9c36…A0BB` | `0x3384…3a76` | 17 |
| Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Arc | — | — | — |

`eth_getCode` returns `0x` for the factory, the beacon and pBTC3x on all eight other chains (2026-10-30).

## 5. Proxies

| Contract | Pattern | Current implementation | History (`Upgraded` block → impl) | Upgrade auth |
|----------|---------|------------------------|-----------------------------------|--------------|
| **PTokenFactory** | UUPS ERC1967Proxy (109 B) | `0x58bdc1d3068a0a79d7a662dee033d62cbd4f589f` | 28,874,978 `0xd42f03be1b183e5bf5dc3907232a2e4e3e1ec15a` → 29,083,226 `0xa592a0f081218399ff622ad9457fa23ecd288897` → 29,438,193 `0x8ed2b831a12a734b92d03b88db89a65d9d886731` → 46,548,049 `0x4fa0ca643d4cc038077042005e358098b81d565f` → 46,565,851 `0xfff94bfe44e1a645322b1f593d6a54dc27e4006a` → 46,656,934 `0x58bdc1d3068a0a79d7a662dee033d62cbd4f589f` | `DEFAULT_ADMIN_ROLE` (Safe `0x81b8…41bd`) |
| **PToken beacon** | `UpgradeableBeacon` | `0x1815a37b6027ae8066720d873a508f25fc151ac5` | 28,874,952 `0x5c4e2a240e32470f08bd65c0575f7730ae6c714f`, 29,083,226 `0x931f2a7fe19ffc064b66b711a3e64539e29957a9`, 29,438,193 `0xa01ec722248c36e805e84ce09d629cacb868f18a`, 29,534,951 `0xaa4b74024149f2f1e4f76551515421b65bbdf90f`, 45,129,614 `0x9c65f71ee067dc08906a25ec200d70ba1f76fbd6`, 46,548,049 `0x29b9e468037fe1a56bb49062c960cf8267d9ad86`, 46,683,722 `0xe4e7ea7dbf58c2d5cbd5462d470223a460c978d7`, 46,720,908 `0xc56fcd809de4f79748b4d7c29e5d788f7f61a617`, 46,792,528 `0x4b7fbbd8d5ff1073f897662306b79724261172e0`, 47,233,756 `0x1815a37b6027ae8066720d873a508f25fc151ac5` | `owner()` = Safe `0x81b8…41bd` |
| **pToken** (each) | BeaconProxy (229 B); EIP-1967 beacon slot = beacon above; impl slot 0 | follows the beacon | — | via beacon |

Watch `Upgraded(address)` on the factory and on the **beacon** (one beacon upgrade changes all 17 pTokens).

## 6. Detection invariants & gotchas

1. **Shares mint at claim, not at request.** `DepositRequest` moves USDG in. `Deposit` (ERC-4626) and a `Transfer` from `0x0` mint shares later. On the redeem side, `RedeemRequest` locks the shares and `Withdraw` pays USDG later. Count user flow at request time and supply change at claim time.
2. **Link a pToken flow to Arcus.** `DepositRequestBridged.inboxIndex` equals the BridgeVault `DepositInitiated.inboxIndex` (owner = the pToken). The unnamed `0xe6c9…` event and `RedeemRequestFilled` carry the BridgeVault `withdrawalId` of the payout to the pToken.
3. **NAV is signed off-chain.** `totalAssets()` changes without an on-chain trade. A sudden drop in `totalAssets()` is the price signal. There is no oracle contract to watch.
4. **Leveraged products can lose most of their NAV fast.** 3x and 5x pTokens follow a perps account that can be liquidated on the appchain. Liquidation is not visible on-chain.
5. **pTokens also trade on Uniswap v4.** The liquidity manager `0x9d90…5e64` is an allowed minter. A pToken `Transfer` from `0x0` to it is a pool mint, not a user deposit.
6. **Shared topic0s.** `DepositsPausedUpdated` (pToken vs BridgeVault) and `BridgeVaultUpdated` (factory vs CheckpointManager) collide. ERC-4626 `Deposit`/`Withdraw` and ERC-7540 topics are standard and collide with every other ERC-4626/7540 vault. Always filter by emitter = a known pToken.
7. **Test pTokens.** pTEST, pTESTR and pTEST3 are live contracts with small balances. Exclude them from volume metrics.
8. **Unverified names.** The names `PTokenCreated`, `MinterAllowedUpdated`, `DepositRequestBridged`, `DepositRequestFulfilled` and `RedeemRequestFilled` are `keccak256` matches against live topic0s. The other names come from the public signature database. Unnamed topics are listed with their shapes only.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_PT_DEPOSIT_REQUEST          = '\xbb58420bb8ce44e11b84e214cc0de10ce5e7c24d0355b2815c3d758b514cae72'
TOPIC_PT_DEPOSIT_REQUEST_BRIDGED  = '\x679094ab1e8941d9ab9e9896c18979354edff487df302d0cafbf69d5fcaa8747'
TOPIC_PT_DEPOSIT_REQUEST_FULFILLED= '\x30b67ebe73bdc8f18c2937e7e61c3d66fc9e5dd2aa35ae20ee1d5f6d0d52895d'
TOPIC_ERC4626_DEPOSIT             = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_PT_REDEEM_REQUEST           = '\x1fdc681a13d8c5da54e301c7ce6542dcde4581e4725043fdab2db12ddc574506'
TOPIC_PT_REDEEM_WITHDRAWAL_LINK   = '\xe6c9bec1b48e68187a62f9b65d5f2c8013c6664177c4e7f1314fd7481500749f'
TOPIC_PT_REDEEM_REQUEST_FILLED    = '\x11cf0d1e21b0ff4b9cfce6b48c9f2605ed8433411fb3f884e722d4495e1d1ede'
TOPIC_ERC4626_WITHDRAW            = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_PT_CANCEL_DEPOSIT_REQUEST   = '\x4ae0134aad5d0e98e82f45680facd628ee6b5aa85ad9a85248a7ef47319f8c50'
TOPIC_PT_CANCEL_REDEEM_REQUEST    = '\xa16c0f2cab616ed5d17cd544655b00d7062a1df7c457960cc8b9bf60770f9236'
TOPIC_PT_CANCEL_REDEEM_CLAIM      = '\x9c133d4657dc9cd12f4c08cef86ef778dbbe03f3ad3b661ff14d36bc3febb1fb'
TOPIC_PT_DEPOSIT_FEE_UPDATED      = '\x433b82816258a4d652299bd6388df04d8f3437d6e6a5f61dd276c45b3e0b9195'
TOPIC_PTF_PTOKEN_CREATED          = '\xd32a88fa7585303533fc903eac9881b690a1f225131a3cd173b16f39e5ee9f8c'
TOPIC_PTF_PTOKEN_CREATED_V1       = '\xe27b420b6fbd662cd18e44fa3a98a56e5ef5cffb17459f1aa076edb80bbb5165'
TOPIC_PTF_MINTER_ALLOWED_UPDATED  = '\x1dfce39fd211882b628d23dffd5a09c01ae6480b40fbae1762fed359cf60dc30'
TOPIC_PTF_MANAGER_UPDATED         = '\x8df26d30992ecfde135bbe59c1f267d82e2aae9d32fdae41551a38fe8b7bda87'
TOPIC_PTF_CAP_UPDATED_UNNAMED     = '\x719de5e7c4f978ca25aa5bb2277071381998d60668f773dcd4f7cdae3780249d'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_PT_REQUEST_DEPOSIT            = '\x85b77f45'
SEL_PT_REQUEST_REDEEM             = '\x7d41c86e'
SEL_PT_BRIDGE_DEPOSIT             = '\x42cc5a88'
SEL_PT_TOTAL_ASSETS               = '\x01e1d114'
SEL_PTF_PTOKEN_COUNT              = '\x07f7e37c'
SEL_PTF_PTOKEN_AT                 = '\xb806d460'
SEL_BEACON_UPGRADE_TO             = '\x3659cfe6'
-- ===== Addresses (Robinhood Chain 4663) =====
RH_ARCUS_PTOKEN_FACTORY           = '\x9c3663fa9ab976e67b42939486ec4966cb41a0bb'
RH_ARCUS_PTOKEN_BEACON            = '\x33846348210a0cc0345f354d9de52b89ad473a76'
RH_ARCUS_PTOKEN_ADMIN_SAFE        = '\x81b80499c396a9931b9e44953425a82c1b2541bd'
RH_ARCUS_PTOKEN_MANAGER           = '\xb7410dc44e2715161e9914272e2d55d7c5061faa'
RH_ARCUS_PTOKEN_LIQ_MANAGER       = '\x9d90417ea422c8d03e94288e70d6747df9a15e64'
RH_ARCUS_PBTC3X                   = '\x4472c69d299382f8847ebce4fc6ed8e295510e3e'
RH_ARCUS_PHOOD3X                  = '\xe24cabdf76dd1c2576049167eb1755c84b985c36'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)`. Standard ERC-4626/7540/7887 events, the factory admin events and the resolved selectors come from the public signature database lookup of the live bytecode (dispatcher selectors and `PUSH32` constants). `PTokenCreated` (both versions), `MinterAllowedUpdated`, `DepositRequestBridged`, `DepositRequestFulfilled` and `RedeemRequestFilled` were found by matching candidate signatures against topic0s seen in live logs, with the data layout checked against sample logs. All pToken counts in §1.1 come from `eth_getLogs` on pBTC3x and pHOOD3x over their full history.
- **Addresses:** the factory comes from the DefiLlama adapter. The pToken list is read on-chain with `pTokenCount()` / `pTokenAt(i)`. Beacon, implementations, admin, manager and NAV signer were read live (`implementation()`, EIP-1967 slots, `getRoleMembers`, `config`, `manager()`).
- **Flow links:** one `bridgeDeposit` receipt (pHOOD3x) shows USDG → PaxosDepositProxy → Teller → arcUSDG → BridgeVault `DepositInitiated(inboxIndex 2248)` → `DepositRequestBridged(…, 2248, …)`. One redeem link (`withdrawalId` 0x7d44 → `WithdrawalInitiated` to pBTC3x) was checked.
- **Chain coverage:** `eth_getCode` on the other seven target chains and Arc returned `0x`.

Sources:
- [DefiLlama-Adapters `projects/arcus-ptokens/index.js`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/arcus-ptokens/index.js) — factory address and test-vault list.
- [DefiLlama — Arcus pTokens](https://defillama.com/protocol/arcus-ptokens)
- [The Block — Arcus launches pTokens (2026-08-25)](https://theblock.co/news/defi/2026-08-25-robinhood-chain-dex-arcus-ptokens-perps-erc-20s-412696)
- [ERC-7540](https://eips.ethereum.org/EIPS/eip-7540) · [ERC-7887](https://eips.ethereum.org/EIPS/eip-7887)
- Explorer: [Robinhood Chain Blockscout — PTokenFactory](https://robinhoodchain.blockscout.com/address/0x9c3663FA9ab976E67B42939486EC4966Cb41a0BB)

# ether.fi Liquid (Veda BoringVault + Midas vaults), eBTC, sETHFI — Topics, Selectors, Addresses (Ethereum, Optimism; Base, Arbitrum, Robinhood Chain noted)

**Status:** verified against live RPC on all nine chains and the verified contract ABIs on 2026-10-30. Vault addresses come from the official ether.fi Liquid vault pages.
**Scope:** the ether.fi **Liquid** yield vaults. Three are **Veda BoringVault** stacks (Liquid ETH, Liquid USD, Liquid BTC: BoringVault + Teller + Accountant + Manager + RolesAuthority + BoringOnChainQueue). Three are **Midas** vaults on Optimism (Liquid Reserve, Liquid USD RWAs, Liquid EUR). The same BoringVault family also issues **eBTC** and **sETHFI** (Staked ETHFI). Topics and selectors are chain-agnostic. Addresses are per chain.

**How a BoringVault works.** The vault (`BoringVault`) is an immutable ERC-20 share token that holds the assets. Only the **Teller** mints/burns shares (`enter`/`exit` → `Enter`/`Exit` events). The **Accountant** stores the share price (`ExchangeRateUpdated`, pushed by an off-chain updater, bounded by upper/lower bps). The **Manager** (`ManagerWithMerkleVerification`) lets strategists call DeFi protocols only through Merkle-approved calls (`BoringVaultManaged`). The **BoringOnChainQueue** handles withdrawals: the user requests (`OnChainWithdrawRequested`), a solver fills (`OnChainWithdrawSolved`). `RolesAuthority` holds all permissions. No contract in the stack is a proxy. A change of logic means a new contract plus `RolesAuthority` updates.

**Same address, different code.** The Liquid ETH/USD/BTC addresses are the same on Ethereum and Optimism (CREATE3). The **Teller code differs**: Ethereum Tellers are 20,173–20,352 B. Optimism Tellers are 22,054 B and add a referral argument. So the Teller `Deposit` topic0 and the `deposit` selector differ by chain (§1.2, §2.2).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 BoringVault (share token) — Liquid ETH/USD/BTC, eBTC, sETHFI
| topic0 | Event |
|--------|-------|
| `0xea00f88768a86184a6e515238a549c171769fe7460a011d6fd0bcd48ca078ea4` | `Enter(address indexed from, address indexed asset, uint256 amount, address indexed to, uint256 shares)` |
| `0xe0c82280a1164680e0cf43be7db4c4c9f985423623ad7a544fb76c772bdc6043` | `Exit(address indexed to, address indexed asset, uint256 amount, address indexed from, uint256 shares)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` |
| `0xa3396fd7f6e0a21b50e5089d2da70d5ac0a3bbbd1f617a93f134b76389980198` | `AuthorityUpdated(address indexed user, address indexed newAuthority)` |

### 1.2 Teller (`LayerZeroTellerWithRateLimiting`)
Ethereum Tellers (20,173–20,352 B):
| topic0 | Event |
|--------|-------|
| `0xe96d7872363f475d18b2f5390caaa5eaa96b2d38e42c62afe4ac08ebd2b13c3a` | `Deposit(uint256 indexed nonce, address indexed receiver, address indexed depositAsset, uint256 depositAmount, uint256 shareAmount, uint256 depositTimestamp, uint256 shareLockPeriodAtTimeOfDeposit)` |
| `0x6f9b974223f85a1ae805c33b8b519039e2435481d949db1110de151a94d587af` | `BulkDeposit(address indexed asset, uint256 depositAmount)` |
| `0xdcc60b41ff1c604459e6aa4a7299817416b19fc586a392f111646e26597c4af9` | `BulkWithdraw(address indexed asset, uint256 shareAmount)` |
| `0xaf98ea774275cadfa3e477a7b52cba03e01197445a76bd5d0d561608708c3624` | `DepositRefunded(uint256 indexed nonce, bytes32 depositHash, address indexed user)` |
| `0xe0ec62d39b054dc2fd626dbc271483735df6e6fa1ef8389754bf8ab27a75eab2` | `MessageSent(bytes32 indexed messageId, uint256 shareAmount, address indexed to)` |
| `0xb944fddc61d7fedb8b736790454ba972000703b0d21c7481d6dbf95b7c2cc2f1` | `MessageReceived(bytes32 indexed messageId, uint256 shareAmount, address indexed to)` |
| `0xe08301321781ac43935a2099b2c3fd42de0a0ee87a519cac00e8c9cecd26ff12` | `AssetDataUpdated(address indexed asset, bool allowDeposits, bool allowWithdraws, uint16 sharePremium)` |
| `0x5dbe727bffd24a6d61a5aeef919510389c66c0deeaa82634862cf4f098961fb8` | `ChainAdded(uint256 chainId, bool allowMessagesFrom, bool allowMessagesTo, address targetTeller)` |
| `0x11a9d1a77f76361ed131c19b1dc5758504c51dbde2e49fc973a0ef9577ad13d5` | `ChainRemoved(uint256 chainId)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |
| `0xd658022b1a3aaf6ad3b3c615253712807f21a8f7bc3e4996e10618175d4afb2b` | `DenyFrom(address indexed user)` |
| `0x79fc685a7dbabb75a67df5e69a90602cef1f19bc465b060eab1ac56685e04a13` | `DenyTo(address indexed user)` |

Optimism Tellers (22,054 B; also the Robinhood Chain liquidUSD Teller, 22,301 B) — the changed and added rows:
| topic0 | Event |
|--------|-------|
| `0xbd5bec50a3d7a5321d4e870bbb48c3589043dbcea81010e6de54a32733aef592` | `Deposit(uint256 nonce, address indexed receiver, address indexed depositAsset, uint256 depositAmount, uint256 shareAmount, uint256 depositTimestamp, uint256 shareLockPeriodAtTimeOfDeposit, address indexed referralAddress)` |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed asset, uint256 shareAmount)` |
| `0x752cd3d8df6864142257fa3a2e02aedf2dc09f1875c2a25b4f117d45c7334d5d` | `DepositCapSet(uint112 cap)` |
| `0xa3fe47e2502292ca20854524008d366d3cad5da2426cfb2484099f06f328e4a0` | `PermissionedTransfersSet(bool permissionedTransfers)` |
| `0x5e92c085dffcb69d025c31c9ed03d1869e4737ba81e8649c623398caa1b72f15` | `AllowPermissionedOperator(address indexed operator)` |
| `0x1c2a701d65e1c6e2860263c884eae0b10db82e3ddd60640d53c7d53c6c998e79` | `DenyPermissionedOperator(address indexed operator)` |

> The two `Deposit` topics: Ethereum `0xe96d…3c3a` (nonce indexed, 7 fields). Optimism `0xbd5b…f592` (adds `address indexed referralAddress`, nonce not indexed). Live: Ethereum Liquid ETH Teller `0xe96d…` 29 of the last 50 logs. Optimism Liquid ETH Teller `0xbd5b…` 134 of 150.

### 1.3 Accountant (`AccountantWithRateProviders`)
| topic0 | Event |
|--------|-------|
| `0xa95bc6aba40bbc4d95fc35f118c4cd8b53fc5d5b89ed264002af03503a7a9439` | `ExchangeRateUpdated(uint96 oldRate, uint96 newRate, uint64 currentTime)` |
| `0x9493e5bbe4e8e0ac67284469a2d677403d0378a85a59e341d3abc433d0d9a209` | `FeesClaimed(address indexed feeAsset, uint256 amount)` |
| `0x7fa71bc8199b41215c8786fc03983be5a27180965feae35db511cd958631826f` | `ManagementFeeUpdated(uint16 oldFee, uint16 newFee)` |
| `0x67d3a3f6bebb5b894324217d5224ff719d5d95dfc67f1bb2645dddbfcd43cadb` | `UpperBoundUpdated(uint16 oldBound, uint16 newBound)` |
| `0x76fe3c3557dd03afa5caf76f66f4019444ef3999e784ba08f47a33428fcc64d5` | `LowerBoundUpdated(uint16 oldBound, uint16 newBound)` |
| `0x59f9adfe8cf4c9d4b77fb03aa2ae5f373632c97cb8caf6b61f0643d3d170a8fe` | `RateProviderUpdated(address asset, bool isPegged, address rateProvider)` |
| `0xba2be5e898fed1646bc0814dee1cc9a2aee98f51fced7d5fc4699c47d9907753` | `PayoutAddressUpdated(address oldPayout, address newPayout)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |
| `0xba8506b6cb85330fea21cbca8490aafb6a69b166f06201ef755eb511b2709fc1` | `PerformanceFeeUpdated(uint16 oldFee, uint16 newFee)` |
| `0x84e4fe32bf74c4011a7e1fde79c63acdffaf92a0112cde153e7b0abee665bc6b` | `PlatformFeeUpdated(uint16 oldFee, uint16 newFee)` |
| `0x98637d475d52bc596e25457cb3385a05269c42e57d4d9f7561dacbbe8583eb89` | `HighwaterMarkReset()` |
| `0x5f7db254db512f40348d8a7ca15d574c051dfe59c19b47e273d926f2f4318606` | `DelayInSecondsUpdated(uint24 oldDelay, uint24 newDelay)` |
| `0xcccad74cc0fcc3b3393386e7a89107fb131535e983a342329b52c667dafe9cf4` | `DelayInSecondsUpdated(uint32 oldDelay, uint32 newDelay)` |

> The Liquid BTC Accountant is a newer build (7,892 B vs 6,440 B). Its `DelayInSecondsUpdated` uses `uint24` (`0x5f7d…8606`). The ETH/USD build uses `uint32` (`0xccca…a7b3`).

### 1.4 BoringOnChainQueue
| topic0 | Event |
|--------|-------|
| `0x2eb08ebdb4d68b4a37e3b424927f3363e1d799ca7e56e7b2c59cc6c1778d33f5` | `OnChainWithdrawRequested(bytes32 indexed requestId, address indexed user, address indexed assetOut, uint96 nonce, uint128 amountOfShares, uint128 amountOfAssets, uint40 creationTime, uint24 secondsToMaturity, uint24 secondsToDeadline)` |
| `0xd94fc49a6578873ff851671d19cacb1809887f7a9128867ee4306dc3ffc93c26` | `OnChainWithdrawSolved(bytes32 indexed requestId, address indexed user, uint256 timestamp)` |
| `0x114ef421aef557f2e4086396789e7fb532b1133ff2982c9d948daa73d0691e36` | `OnChainWithdrawCancelled(bytes32 indexed requestId, address indexed user, uint256 timestamp)` |
| `0x905e8254267fdbacdcfcc65ef489f2355c112e815c9c635c94c6a1cff787acf0` | `WithdrawAssetSetup(address indexed assetOut, uint24 secondsToMaturity, uint24 minimumSecondsToDeadline, uint16 minDiscount, uint16 maxDiscount, uint96 minimumShares)` |
| `0x6ece44744f1fe676735f115da497fe130c7acf43fcd142fe92e20df15788797e` | `WithdrawAssetUpdated(address indexed assetOut, uint24 minimumSecondsToDeadline, uint24 secondsToMaturity, uint16 minDiscount, uint16 maxDiscount, uint96 minimumShares)` |
| `0xf1abf38a870f414456542524a2b679c0ece751691e36f4feee2ca7826c99e462` | `WithdrawAssetStopped(address indexed assetOut)` |

### 1.5 Manager and RolesAuthority
| topic0 | Event |
|--------|-------|
| `0x53d426e7d80bb2c8674d3b45577e2d464d423faad6531b21f95ac11ac18b1cb6` | `BoringVaultManaged(uint256 callsMade)` |
| `0x0b958dec85f1470000479dfb22c365829411f52bcde602d24ea0abf5ac7e8860` | `ManageRootUpdated(address indexed strategist, bytes32 oldRoot, bytes32 newRoot)` |
| `0x4c9bdd0c8e073eb5eda2250b18d8e5121ff27b62064fbeeeed4869bb99bc5bf2` | `UserRoleUpdated(address indexed user, uint8 indexed role, bool enabled)` |
| `0xa52ea92e6e955aa8ac66420b86350f7139959adfcc7e6a14eee1bd116d09860e` | `RoleCapabilityUpdated(uint8 indexed role, address indexed target, bytes4 indexed functionSig, bool enabled)` |
| `0x950a343f5d10445e82a71036d3f4fb3016180a25805141932543b83e2078a93e` | `PublicCapabilityUpdated(address indexed target, bytes4 indexed functionSig, bool enabled)` |

### 1.6 Midas vaults (Optimism) — DepositVault and RedemptionVault
| topic0 | Event |
|--------|-------|
| `0xdd6865ec496cf9bdd5cb1661ab84cf4e86edc877208a54cbf642f69d744530c5` | `DepositInstant(address indexed user, address indexed tokenIn, uint256 amountUsd, uint256 amountToken, uint256 fee, uint256 minted, bytes32 referrerId)` |
| `0x3704c9b13a68ac43d7f8a85f2700f0b4f89a11ed9e2bcac5324f0d228d409009` | `DepositRequest(uint256 indexed requestId, address indexed user, address indexed tokenIn, uint256 amountToken, uint256 amountUsd, uint256 fee, uint256 tokenOutRate, bytes32 referrerId)` |
| `0xd21eaf3019cc16da5c82b2c14e3df524c0599086f690f48357de2c74f1bbdfd6` | `DepositRequestWithCustomRecipient(uint256 indexed requestId, address indexed user, address indexed tokenIn, address recipient, uint256 amountToken, uint256 amountUsd, uint256 fee, uint256 tokenOutRate, bytes32 referrerId)` |
| `0xf7d1fde87f32720fc30ce6847e0aae77e640b59bfac41b11b270358ccfa7a0ac` | `ApproveRequest(uint256 indexed requestId, uint256 newOutRate)` |
| `0x03ea09e71742c9c754c9746b3e671ecb27fc372e3d29c31bac0192458ffd9d4b` | `SafeApproveRequest(uint256 indexed requestId, uint256 newOutRate)` |
| `0x00ce63cc55966b103e4f4cb39f3426cb91718ad4f8eb4ad08c14a7ee749d8157` | `RejectRequest(uint256 indexed requestId, address indexed user)` |
| `0x049000a9db89588d7bfb162bc0f7e4299ee8762430a468131c2caf0824f1f995` | `AddPaymentToken(address indexed caller, address indexed token, address indexed dataFeed, uint256 fee, uint256 allowance, bool stable)` |
| `0x1582567d288d96695cf3fe7280c630a4f1c82fc7e665e1db58468f2960fef869` | `ChangeTokenFee(address indexed token, address indexed caller, uint256 fee)` |
| `0x1af12536d161c2c30ad907b0abe442f94c4a7824f2463585b3fc893275247cce` | `RedeemInstant(address indexed user, address indexed tokenOut, uint256 amount, uint256 feeAmount, uint256 amountTokenOut)` |
| `0x4fd0e2f3f27549d8d0c242f7193eaa0f61546e887fec39e69dfbff6b2384a4c3` | `RedeemInstantWithCustomRecipient(address indexed user, address indexed tokenOut, address recipient, uint256 amount, uint256 feeAmount, uint256 amountTokenOut)` |
| `0x55ba94d231fa70a45e82b0a1c6a60ef72e41bb2455385128ee5cf8d98c0c1c0e` | `RedeemRequest(uint256 indexed requestId, address indexed user, address indexed tokenOut, uint256 amountMTokenIn, uint256 feeAmount)` |
| `0x691cd372bb63a5126a324513b634040d0ba3747c0a625207d99b6ba302c51a23` | `RedeemRequestWithCustomRecipient(uint256 indexed requestId, address indexed user, address indexed tokenOut, address recipient, uint256 amountMTokenIn, uint256 feeAmount)` |

> `ApproveRequest`/`SafeApproveRequest`/`RejectRequest` share one topic0 between DepositVault and RedemptionVault. Key on the emitter. Live: Liquid Reserve DepositVault `DepositInstant` 150 of 150 recent logs.

---

## 2. Function signatures (chain-agnostic)

### 2.1 BoringVault, Accountant, Manager, Queue
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x39d6ba32` | `enter(address,address,uint256,address,uint256)` | -> () |
| `0x18457e61` | `exit(address,address,uint256,address,uint256)` | -> () |
| `0xf6e715d0` | `manage(address,bytes,uint256)` | -> (bytes) |
| `0x224d8703` | `manage(address[],bytes[],uint256[])` | -> (bytes[]) |
| `0x3458113d` | `updateExchangeRate(uint96)` | -> () |
| `0x679aefce` | `getRate()` | view -> (uint256) |
| `0x1dcbb110` | `getRateInQuote(address)` | view -> (uint256) |
| `0x820973da` | `getRateInQuoteSafe(address)` | view -> (uint256) |
| `0x15a0ea6a` | `claimFees(address)` | -> () |
| `0x244b0f6a` | `manageVaultWithMerkleVerification(bytes32[][],address[],address[],bytes[],uint256[])` | -> () |
| `0x6bb3b476` | `requestOnChainWithdraw(address,uint128,uint16,uint24)` | -> (bytes32) |
| `0x581b4920` | `requestOnChainWithdrawWithPermit(address,uint128,uint16,uint24,uint256,uint8,bytes32,bytes32)` | -> (bytes32) |
| `0x412638dc` | `solveOnChainWithdraws((uint96,address,address,uint128,uint128,uint40,uint24,uint24)[],bytes,address)` | -> () |
| `0x4a2dc5e4` | `cancelOnChainWithdraw((uint96,address,address,uint128,uint128,uint40,uint24,uint24))` | -> (bytes32) |

### 2.2 Teller — Ethereum build
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x0efe6a8b` | `deposit(address,uint256,uint256)` | payable -> (uint256) |
| `0x3d935d9e` | `depositWithPermit(address,uint256,uint256,uint256,uint8,bytes32,bytes32)` | -> (uint256) |
| `0x9d574420` | `bulkDeposit(address,uint256,uint256,address)` | -> (uint256) |
| `0x3e64ce99` | `bulkWithdraw(address,uint256,uint256,address)` | -> (uint256) |
| `0xcab716e8` | `depositAndBridge(address,uint256,uint256,address,bytes,address,uint256)` | payable -> (uint256) |
| `0x05921740` | `bridge(uint96,address,bytes,address,uint256)` | payable -> () |
| `0x46b563f4` | `refundDeposit(uint256,address,address,uint256,uint256,uint256,uint256)` | -> () |

### 2.3 Teller — Optimism build (changed selectors)
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x8b6099db` | `deposit(address,uint256,uint256,address)` | payable -> (uint256) |
| `0x6495043a` | `depositWithPermit(address,uint256,uint256,uint256,uint8,bytes32,bytes32,address)` | -> (uint256) |
| `0x16762eed` | `withdraw(address,uint256,uint256,address)` | -> (uint256) |
| `0xf8b7b66d` | `depositAndBridge(address,uint256,uint256,address,bytes,address,uint256,address)` | payable -> (uint256) |
| `0x65fe00e4` | `refundDeposit(uint256,address,address,uint256,uint256,uint256,uint256,address)` | -> () |

### 2.4 Midas vaults
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xc02dd27a` | `depositInstant(address,uint256,uint256,bytes32)` | -> () |
| `0x42e8866b` | `depositInstant(address,uint256,uint256,bytes32,address)` | -> () |
| `0x6e26b9f8` | `depositRequest(address,uint256,bytes32)` | -> (uint256) |
| `0x2c0a90a9` | `approveRequest(uint256,uint256)` | -> () |
| `0x2d7788db` | `rejectRequest(uint256)` | -> () |
| `0x8b53f75e` | `redeemInstant(address,uint256,uint256)` | -> () |
| `0x85ab2c13` | `redeemInstant(address,uint256,uint256,address)` | -> () |
| `0xbfc2d46a` | `redeemRequest(address,uint256)` | -> (uint256) |
| `0x15571a04` | `redeemRequest(address,uint256,address)` | -> (uint256) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All immutable (EIP-1967 impl slot `0x0`); verified with `eth_getCode` on 2026-10-30.

| Vault | BoringVault (token) | Teller | Accountant | Manager | RolesAuthority | BoringOnChainQueue |
|-------|---------------------|--------|------------|---------|----------------|--------------------|
| **Liquid ETH** (`liquidETH`) | `0xf0bb20865277aBd641a307eCe5Ee04E79073416C` | `0x9AA79C84b79816ab920bBcE20f8f74557B514734` | `0x0d05D94a5F1E76C18fbeB7A13d17C8a314088198` | `0xf9f7969c357ce6dfd7973098ea0d57173592bcca` | `0x485Bde66Bb668a51f2372E34e45B1c6226798122` | `0x0D2dF071207E18Ca8638b4f04E98c53155eC2cE0` |
| **Liquid USD** (`liquidUSD`) | `0x08c6F91e2B681FaF5e17227F2a44C307b3C1364C` | `0x4de413a26fc24c3fc27cc983be70aa9c5c299387` | `0xc315D6e14DDCDC7407784e2Caf815d131Bc1D3E7` | `0xcFF411d5C54FE0583A984beE1eF43a4776854B9A` | `0xaBA6bA1E95E0926a6A6b917FE4E2f19ceaE4FF2e` | `0x38fc1ba73b7ed289955a07d9f11a85b6e388064a` |
| **Liquid BTC** (`liquidBTC`) | `0x5f46d540b6eD704C3c8789105F30E075AA900726` | `0x8Ea0B382D054dbEBeB1d0aE47ee4AC433C730353` | `0xEa23aC6D7D11f6b181d6B98174D334478ADAe6b0` | `0xaFa8c08bedB2eC1bbEb64A7fFa44c604e7cca68d` | `0x49F954c67ff235034b69b8a59fbe309A40256c8d` | `0x77A2fd42F8769d8063F2E75061FC200014E41Edf` |

| Other BoringVault-family token | Address | Notes |
|--------------------------------|---------|-------|
| **eBTC** (`ether.fi BTC`, 8 dec) | `0x657e8C867D8B37dCC18fA4Caead9C45EB088C642` | BoringVault (7,514 B). Same literal on Base, Arbitrum, Optimism. Emits `Enter`/`Exit`. |
| **sETHFI** (`Staked ETHFI`) | `0x86B5780b606940Eb59A062aA85a07959518c0161` | `BoringGovernance` (12,260 B; adds `ERC20Votes` delegation). Same literal on Base, Arbitrum (12,544 B) and Optimism (7,514 B BoringVault). |

## 4. Addresses — Optimism (chain ID 10)

**BoringVault stacks.** Same literals as Ethereum for Vault, Teller, Accountant and Queue of all three vaults. Differences:
- Liquid ETH: Manager on Optimism is `0x227975088C28DBBb4b421c6d96781a53578f19a8` (the official page lists it). The Ethereum Manager literal `0xf9f7…bcca` also has code on Optimism.
- Liquid USD: the Ethereum Manager `0xcFF4…4B9A` and RolesAuthority `0xaBA6…FF2e` literals have **no code** on Optimism. The Optimism vault `authority()` = `0xff90f1b24dfbd25f439b94ed090f373bde24f60e` (read live).
- Liquid BTC: Manager and RolesAuthority literals have code on Optimism.

**Midas vaults** (Transparent proxies, 2,227 B; shared ProxyAdmin `0x2f8d0aa6810453b55c1077bdd8944dd037aff2dc`):

| Vault | Token | DepositVault | RedemptionVault | CustomFeed (oracle) | DataFeed |
|-------|-------|--------------|-----------------|---------------------|----------|
| **Liquid Reserve** (`liquidRESERVE`) | `0xca5921DF65E2e1b0B98Ae91c0187BA80D4124898` | `0x1561eC30da97108Df46535CBd9bAD8C8d8611B3a` | `0xC87b51735ea5Eeee59D3e12601dC931F77F2837a` | `0x58dDf77A329CcbE2F4C2114C64ed9E12Ec8a1356` | `0x843EAa59836599611FA02BC065dCb128F320Af9f` |
| **Liquid USD RWAs** (`liquidRWA`) | `0x17bC8Ffd82b8a36e737Ca1141C025089589B915e` | `0x97b30c9D53A010009136b830f8A12f8d5624Bc43` | `0x12Ae90dCe5C2a4Ee5141FBfc408ff1022D051F42` | `0xd5aaE6ac1a9ed4BE5DcC1fc172EDeFFd5B6d8080` | — |
| **Liquid EUR** (`weEUR`) | `0xcC476B1a49bcDf5192561e87b6Fb8ea78aa28C13` | `0xF1b45eE795C8e1B858e191654C95A1B33c573632` | `0xDC87653FCc5c16407Cd2e199d5Db48BaB71e7861` | `0x01b910C1aa51cdC4a2a84d76CB255C4974Bf8A19` | `0xA42A19F6dB6382B94DDFfA752bA682d6Df163D59` |

The SMA and "Redemption Liquidity" addresses on the official pages (`0xfC55…8c63`, `0x47A6…6A42`, `0x8EC0…bFa3`, `0x352D…C112`, `0xe433…9c4e`, `0xb077…CF39`) have **no code**: they are EOA wallets. Watch them as transfer counterparties, not as event emitters. The official page notes that a previous Liquid Reserve deployment on Scroll is deprecated.

## 5. Other chains

| Chain | What exists | Notes |
|-------|-------------|-------|
| Base (8453) | Liquid ETH Vault `0xf0bb…416C` (7,706 B), Accountant, Authority, OP-Manager literal; eBTC; sETHFI | No Teller or Queue. Liquid ETH `totalSupply` = 0.00097 (dust). eBTC live (`Enter`/`Exit` seen). |
| Arbitrum (42161) | Same Liquid ETH subset as Base; eBTC; sETHFI | Liquid ETH `totalSupply` = 0.0097 (dust). |
| Robinhood Chain (4663) | Liquid USD full stack (Vault, Accountant, Teller 22,301 B, Authority, Queue) | `totalSupply` = 0; vault `owner()` = `0x5f2f11ad…a02d`. A real but empty deployment. |
| BNB, Avalanche, Polygon PoS, Arc | none | every literal returns `0x` |

## 6. Cross-chain summary

| Chain | Liquid ETH | Liquid USD | Liquid BTC | Midas vaults | eBTC | sETHFI |
|-------|-----------|-----------|-----------|--------------|------|--------|
| Ethereum (1) | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Optimism (10) | ✓ | ✓ | ✓ | ✓ (3) | ✓ | ✓ |
| Base (8453) | vault only (dust) | — | — | — | ✓ | ✓ |
| Arbitrum (42161) | vault only (dust) | — | — | — | ✓ | ✓ |
| Robinhood Chain (4663) | — | stack, empty | — | — | — | — |
| BNB / Avalanche / Polygon / Arc | — | — | — | — | — | — |

## 7. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| BoringVault, Teller, Accountant, Manager, Queue, RolesAuthority, eBTC, sETHFI | **immutable** | EIP-1967 impl slot `0x0` | none. Logic changes = new contract + `RolesAuthority` capability changes (`RoleCapabilityUpdated`, `UserRoleUpdated`) and `AuthorityUpdated` on the vault |
| Midas Token, DepositVault, RedemptionVault, CustomFeed, DataFeed | EIP-1967 Transparent | impl + admin slot set | ProxyAdmin `0x2f8d…f2dc` |

## 8. Detection invariants & gotchas

1. **Teller `Deposit` topic0 is chain-specific.** Use `0xe96d…3c3a` on Ethereum and `0xbd5b…f592` on Optimism/Robinhood. A single-topic filter misses one chain.
2. **`deposit(address,uint256,uint256)` = `0x0efe6a8b`** on Ethereum Tellers. The same selector exists on the weETH L2 sync pools. Key on the target.
3. **Share price moves only on `ExchangeRateUpdated`.** An update outside the upper/lower bounds (or too soon) sets the Accountant to paused **without** a `Paused()` event in the canonical source: only `ExchangeRateUpdated` fires. A paused Accountant blocks Teller deposits. Alert on large `newRate/oldRate` steps and poll `accountantState()` / `getRateSafe()` (reverts when paused). A manual `pause()` does emit `Paused()`.
4. **Real user = `Enter.to` / `Exit.from`.** The Teller is `Enter.from` for deposits. For `bulkDeposit` (permissioned) the depositor is a contract such as the Cash settlement path.
5. **Cross-chain shares.** The Teller `MessageSent`/`MessageReceived` (`messageId`, `shareAmount`, `to`) move shares by LayerZero between Ethereum and Optimism. Supply moves without a deposit.
6. **Strategist actions.** `BoringVaultManaged(callsMade)` is the only on-chain trace of a strategy move. `ManageRootUpdated` changes the allowed-call Merkle root: a high-value governance alert.
7. **Withdraw queue discounts.** `OnChainWithdrawRequested` carries `amountOfShares` and `amountOfAssets` (discount applied). A burst of requests with no `OnChainWithdrawSolved` shows a stuck solver.
8. **Midas vaults are not BoringVaults.** No `Enter`/`Exit`. Deposits are `DepositInstant` or `DepositRequest` → `ApproveRequest`. Redemptions are `RedeemInstant` or `RedeemRequest` → `ApproveRequest`. The token is a plain ERC-20 mint/burn.
9. **Dust vaults on Base and Arbitrum.** The Liquid ETH vault literal exists there with near-zero supply. Do not treat it as an active market.

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_BV_ENTER                   = '\xea00f88768a86184a6e515238a549c171769fe7460a011d6fd0bcd48ca078ea4'
TOPIC_BV_EXIT                    = '\xe0c82280a1164680e0cf43be7db4c4c9f985423623ad7a544fb76c772bdc6043'
TOPIC_TELLER_DEPOSIT_ETH_BUILD   = '\xe96d7872363f475d18b2f5390caaa5eaa96b2d38e42c62afe4ac08ebd2b13c3a'
TOPIC_TELLER_DEPOSIT_OP_BUILD    = '\xbd5bec50a3d7a5321d4e870bbb48c3589043dbcea81010e6de54a32733aef592'
TOPIC_TELLER_WITHDRAW_OP_BUILD   = '\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'
TOPIC_TELLER_BULK_DEPOSIT        = '\x6f9b974223f85a1ae805c33b8b519039e2435481d949db1110de151a94d587af'
TOPIC_TELLER_BULK_WITHDRAW       = '\xdcc60b41ff1c604459e6aa4a7299817416b19fc586a392f111646e26597c4af9'
TOPIC_TELLER_MESSAGE_SENT        = '\xe0ec62d39b054dc2fd626dbc271483735df6e6fa1ef8389754bf8ab27a75eab2'
TOPIC_TELLER_MESSAGE_RECEIVED    = '\xb944fddc61d7fedb8b736790454ba972000703b0d21c7481d6dbf95b7c2cc2f1'
TOPIC_ACCT_EXCHANGE_RATE_UPDATED = '\xa95bc6aba40bbc4d95fc35f118c4cd8b53fc5d5b89ed264002af03503a7a9439'
TOPIC_ACCT_FEES_CLAIMED          = '\x9493e5bbe4e8e0ac67284469a2d677403d0378a85a59e341d3abc433d0d9a209'
TOPIC_BV_PAUSED                  = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_QUEUE_WITHDRAW_REQUESTED   = '\x2eb08ebdb4d68b4a37e3b424927f3363e1d799ca7e56e7b2c59cc6c1778d33f5'
TOPIC_QUEUE_WITHDRAW_SOLVED      = '\xd94fc49a6578873ff851671d19cacb1809887f7a9128867ee4306dc3ffc93c26'
TOPIC_QUEUE_WITHDRAW_CANCELLED   = '\x114ef421aef557f2e4086396789e7fb532b1133ff2982c9d948daa73d0691e36'
TOPIC_MANAGER_VAULT_MANAGED      = '\x53d426e7d80bb2c8674d3b45577e2d464d423faad6531b21f95ac11ac18b1cb6'
TOPIC_MANAGER_ROOT_UPDATED       = '\x0b958dec85f1470000479dfb22c365829411f52bcde602d24ea0abf5ac7e8860'
TOPIC_AUTH_USER_ROLE_UPDATED     = '\x4c9bdd0c8e073eb5eda2250b18d8e5121ff27b62064fbeeeed4869bb99bc5bf2'
TOPIC_AUTH_ROLE_CAPABILITY       = '\xa52ea92e6e955aa8ac66420b86350f7139959adfcc7e6a14eee1bd116d09860e'
TOPIC_MIDAS_DEPOSIT_INSTANT      = '\xdd6865ec496cf9bdd5cb1661ab84cf4e86edc877208a54cbf642f69d744530c5'
TOPIC_MIDAS_DEPOSIT_REQUEST      = '\x3704c9b13a68ac43d7f8a85f2700f0b4f89a11ed9e2bcac5324f0d228d409009'
TOPIC_MIDAS_REDEEM_INSTANT       = '\x1af12536d161c2c30ad907b0abe442f94c4a7824f2463585b3fc893275247cce'
TOPIC_MIDAS_REDEEM_REQUEST       = '\x55ba94d231fa70a45e82b0a1c6a60ef72e41bb2455385128ee5cf8d98c0c1c0e'
TOPIC_MIDAS_APPROVE_REQUEST      = '\xf7d1fde87f32720fc30ce6847e0aae77e640b59bfac41b11b270358ccfa7a0ac'
-- ===== Selectors (chain-agnostic) =====
SEL_TELLER_DEPOSIT_ETH_BUILD     = '\x0efe6a8b'
SEL_TELLER_DEPOSIT_OP_BUILD      = '\x8b6099db'
SEL_TELLER_BULK_WITHDRAW         = '\x3e64ce99'
SEL_ACCT_UPDATE_EXCHANGE_RATE    = '\x3458113d'
SEL_ACCT_GET_RATE                = '\x679aefce'
SEL_MANAGER_MANAGE_MERKLE        = '\x244b0f6a'
SEL_QUEUE_REQUEST_WITHDRAW       = '\x6bb3b476'
SEL_QUEUE_SOLVE                  = '\x412638dc'
-- ===== Addresses (same literal on Ethereum and Optimism unless noted) =====
ETHERFI_LIQUID_ETH_VAULT         = '\xf0bb20865277abd641a307ece5ee04e79073416c'
ETHERFI_LIQUID_ETH_TELLER        = '\x9aa79c84b79816ab920bbce20f8f74557b514734'
ETHERFI_LIQUID_ETH_ACCOUNTANT    = '\x0d05d94a5f1e76c18fbeb7a13d17c8a314088198'
ETHERFI_LIQUID_ETH_QUEUE         = '\x0d2df071207e18ca8638b4f04e98c53155ec2ce0'
ETH_ETHERFI_LIQUID_ETH_MANAGER   = '\xf9f7969c357ce6dfd7973098ea0d57173592bcca'
OP_ETHERFI_LIQUID_ETH_MANAGER    = '\x227975088c28dbbb4b421c6d96781a53578f19a8'
ETHERFI_LIQUID_USD_VAULT         = '\x08c6f91e2b681faf5e17227f2a44c307b3c1364c'
ETHERFI_LIQUID_USD_TELLER        = '\x4de413a26fc24c3fc27cc983be70aa9c5c299387'
ETHERFI_LIQUID_USD_ACCOUNTANT    = '\xc315d6e14ddcdc7407784e2caf815d131bc1d3e7'
ETHERFI_LIQUID_USD_QUEUE         = '\x38fc1ba73b7ed289955a07d9f11a85b6e388064a'
ETHERFI_LIQUID_BTC_VAULT         = '\x5f46d540b6ed704c3c8789105f30e075aa900726'
ETHERFI_LIQUID_BTC_TELLER        = '\x8ea0b382d054dbebeb1d0ae47ee4ac433c730353'
ETHERFI_LIQUID_BTC_ACCOUNTANT    = '\xea23ac6d7d11f6b181d6b98174d334478adae6b0'
ETHERFI_LIQUID_BTC_QUEUE         = '\x77a2fd42f8769d8063f2e75061fc200014e41edf'
ETHERFI_EBTC                     = '\x657e8c867d8b37dcc18fa4caead9c45eb088c642'
ETHERFI_SETHFI                   = '\x86b5780b606940eb59a062aa85a07959518c0161'
OP_ETHERFI_LIQUID_RESERVE_TOKEN  = '\xca5921df65e2e1b0b98ae91c0187ba80d4124898'
OP_ETHERFI_LIQUID_RESERVE_DV     = '\x1561ec30da97108df46535cbd9bad8c8d8611b3a'
OP_ETHERFI_LIQUID_RESERVE_RV     = '\xc87b51735ea5eeee59d3e12601dc931f77f2837a'
OP_ETHERFI_LIQUID_RWA_TOKEN      = '\x17bc8ffd82b8a36e737ca1141c025089589b915e'
OP_ETHERFI_LIQUID_RWA_DV         = '\x97b30c9d53a010009136b830f8a12f8d5624bc43'
OP_ETHERFI_LIQUID_RWA_RV         = '\x12ae90dce5c2a4ee5141fbfc408ff1022d051f42'
OP_ETHERFI_LIQUID_EUR_TOKEN      = '\xcc476b1a49bcdf5192561e87b6fb8ea78aa28c13'
OP_ETHERFI_LIQUID_EUR_DV         = '\xf1b45ee795c8e1b858e191654c95a1b33c573632'
OP_ETHERFI_LIQUID_EUR_RV         = '\xdc87653fcc5c16407cd2e199d5db48bab71e7861'
```

## 10. Verification & sources

How the constants were verified (2026-10-30):
- **Topic0 / selectors:** computed locally as `keccak256(signature)` from verified ABIs (Blockscout for Ethereum and Optimism; the Midas vault impls `0x3bc81785…b601` and `0x00620e98…6932`). Live log pages confirmed every Liquid ETH/USD/BTC topic seen on Ethereum (`Enter`, `Exit`, `Deposit` `0xe96d…`, `BulkDeposit`, `BulkWithdraw`, `MessageSent/Received`, `ExchangeRateUpdated`, `FeesClaimed`, `OnChainWithdrawRequested/Solved/Cancelled`, `BoringVaultManaged`, `ManageRootUpdated`, `UserRoleUpdated`, `RoleCapabilityUpdated`) and on Optimism (`Deposit` `0xbd5b…`, `DepositInstant`). No unknown topic0.
- **Addresses:** official Liquid vault pages; existence and code size checked with `eth_getCode` on all nine chains; immutability by an empty EIP-1967 slot; Midas proxies by impl + admin slot. `name()`, `symbol()`, `totalSupply()`, `owner()` read with `eth_call`.

Authoritative sources:
- [Se7en-Seas/boring-vault](https://github.com/Se7en-Seas/boring-vault) — BoringVault, Teller, Accountant, Manager, Queue source.
- [ether.fi Liquid live vaults](https://etherfi.gitbook.io/etherfi/products/liquid/live-vaults) · [Veda vault architecture](https://etherfi.gitbook.io/etherfi/products/liquid/veda-vault) · [Midas vault architecture](https://etherfi.gitbook.io/etherfi/products/liquid/midas-vault)
- Explorers: [Etherscan](https://etherscan.io) · [Optimism explorer](https://explorer.optimism.io)

# 40 Acres Finance — Topics, Selectors, Addresses (Base, Optimism, Avalanche, +Ethereum portfolio layer)

**Status:** verified against Base, Optimism, Avalanche, and Ethereum mainnet RPC, the official docs (`docs.40acres.finance/contracts`), and Sourcify-verified source on 2026-05-29.
**Scope:** all live 40 Acres deployments. Topics + selectors are **chain-agnostic**; addresses are network-specific. **Not deployed on BNB, Arbitrum, or Polygon** (`eth_getCode` = `0x` for every 40 Acres address on those three chains).

40 Acres is a **self-repaying, non-liquidatable, 0%-interest lending protocol** against yield-bearing collateral — primarily **veNFTs** (voting-escrow NFTs) on Aerodrome (Base), Velodrome (Optimism), and Pharaoh + Blackhole (Avalanche). A borrower deposits a veNFT, the protocol lends USDC (or the DEX token) sized to the veNFT's projected rewards (≈ avg weekly rewards × 8 epochs), and the veNFT's ongoing voting rewards automatically repay the loan. The collateral is held in protocol-owned escrow (the `Loan` contract) for the life of the loan. There are no version-numbered protocol releases (no "V1/V2/V3" redeploys); instead the lending contracts are **UUPS-upgradeable proxies** and the protocol ships per-DEX subclasses — hence this single `core.md` rather than `v{n}.md` files.

**Single protocol admin** across all chains and core contracts: `0xff16fd3d147220e6cc002a8e4a1f942ac41dbd23` (`owner()` of PortfolioManager and every Loan).

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified name(s) on chain |
|----------|------|--------|---------------------------|
| **PortfolioManager** | Registry/factory hub for Diamond "portfolio" smart-accounts. Singleton at the vanity address `0x40ac2e40ac…` (same on every chain). | **No** (16 973 B singleton) | `PortfolioManager` |
| **Vault** | ERC-4626 lender vault (lenders deposit USDC, earn yield; `symbol()="VAULT"`). | **Direct** on Base/OP; **ERC-1967 proxy** on Avax | `Vault` |
| **Loan** (USDC variant) | Borrow USDC against a veNFT; escrows the veNFT; self-repays from rewards. | **UUPS** (ERC-1967 + ERC-1822) | `Loan` (Aero/Velo), `XPharaohLoan` (Pharaoh) |
| **LoanV2Native** (token variant) | "Managed-NFT" variant: borrow/repay in the DEX token, can merge collateral into a protocol-managed veNFT. The `V2`/`Native` in the name is the *contract* lineage, not a protocol version. | **UUPS** | `LoanV2Native` (Aero/Velo), `PharaohLoanV2Native`, Blackhole equivalent |
| **RedeemCommunityShares** ("Claim") | Lets community-reward opt-ins redeem their share of payout token. **Base-only.** | **UUPS** | `RedeemCommunityShares` |
| **Factory** / **FacetRegistry** | Diamond (EIP-2535) factories + facet registries that mint per-user portfolio accounts. Deployed by PortfolioManager (`FactoryDeployed`/`FacetRegistryDeployed`). | Diamond infra | — |

Pharaoh and Blackhole loans are **per-DEX subclasses** of `Loan`/`LoanV2Native` (bytecode-confirmed same family — selector Jaccard 0.41–0.73; the lower overlap is Pharaoh's xPHAR token model). **The event signatures are identical across all subclasses** (inherited from the base `Loan`), so every topic0 in §1.3 applies on all three chains.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 PortfolioManager

| topic0 | Event |
|--------|-------|
| `0xf96fae1c85039df437ec1af96b53627ef4b8de60de364b148c795c4b0ccb2361` | `FactoryDeployed(address,address)` |
| `0xc3610a15c0531fda8894c29a65398597a7b73766c6868fd4967ed2688d502ba6` | `FacetRegistryDeployed(address,address)` |
| `0x37868bdfe8994d893b5d7a9fae580a86ca5da03c90340d983799d5d3d8810970` | `PortfolioRegistered(address,address,address)` |
| `0x03de89a8856e0ef333405de002ac7fc89e4b9bd300af69cf63795ef68ca56fd0` | `CrossAccountMulticall(address,address[])` |
| `0x1eff62a53441c7d0125c22f2a9a324e206b34efa41e19469d7efb9bb703d21a3` | `AuthorizedCallerSet(address,bool)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |

### 1.2 Vault (ERC-4626 + ERC-20)

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address sender, address owner, uint256 assets, uint256 shares)` |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address sender, address receiver, address owner, uint256 assets, uint256 shares)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (ERC-20 share token) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` |

`Deposit`/`Withdraw` are the canonical EIP-4626 topics — **identical to every other 4626 vault**, so always filter on `(chainId, vault address, topic0)`, never topic0 alone.

### 1.3 Loan & LoanV2Native (and all per-DEX subclasses — identical signatures)

| topic0 | Event | Meaning |
|--------|-------|---------|
| `0xe289f9a78f6ca99c12176d7f92cdc104bf35c6c2b48ef2f8e1e04a1551894b74` | `CollateralAdded(uint256 tokenId, address owner, uint8 collateralType)` | veNFT deposited as collateral. *(verified live on Base)* |
| `0x3bd6238aaa73867918dcdf740a894fd816018bdca8dc628b117999e41950ba27` | `FundsBorrowed(uint256 tokenId, address borrower, uint256 amount)` | Loan principal disbursed. |
| `0x74d71c8dada9cecbd188b84bcb7522de7ca42087c4110f5bb4461b3402edd729` | `LoanPaid(uint256 tokenId, address borrower, uint256 amount, uint256 epoch, bool closed)` | Repayment (usually from rewards). *(verified live on Base + Optimism)* |
| `0x2d428178e65c47bfb7d75b43e57e93851220995d8887d6826253c18d9b9fc99f` | `CollateralWithdrawn(uint256 tokenId, address owner)` | veNFT returned after full repayment. *(verified live on Base)* |
| `0x66aebf327a5c16726a6685b85821f29c65b3b925c44e91811511683a8e71a91d` | `RewardsReceived(uint256 tokenId, uint256 epoch, address token, uint256 amount)` | veNFT voting rewards harvested into the loan. |
| `0x0d66919505e691cceb14298df92d143853afb29242516310143ece94513af759` | `RewardsClaimed(uint256 tokenId, uint256 epoch, address token, uint256 amount, address to)` | Rewards routed to a destination. |
| `0x36c0b6334ab9d8a841bc0b90539b690e987e6af2a797eb3dbb0781fdff3b8b55` | `RewardsInvested(uint256 tokenId, uint256 epoch, address token, uint256 amount)` | Rewards re-deposited into the lender Vault (auto-compound). |
| `0x1b53afc804bdcdda0126d69a51ee46ee54c0b82deb70144c82fa9573fde707f3` | `RewardsPaidtoOwner(uint256 tokenId, uint256 epoch, address token, uint256 amount, address owner)` | Surplus rewards paid to borrower (zero-balance accounts). |
| `0xb17a3e7bbddf0580407b3a338c0d7f004e8a35ccce78cd53418f5f56a1abb672` | `ProtocolFeePaid(uint256 tokenId, uint256 epoch, address token, uint256 amount, address payer)` | Protocol fee taken from rewards. |
| `0x742ad298609ca48e9fe8da7d4599cc7ab771dcfa73ce69d8751850d3105a0faa` | `VeNftIncreased(uint256 tokenId, address token, uint256 amount, uint256 newLocked, uint256 epoch)` | Lock amount increased (compounding into the veNFT). *(verified live on Base)* |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | OZ `Initializable` — fires once per proxy init / re-init. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address implementation)` | **UUPS impl pointer changed** — watch this to track upgrades. |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address,address)` | Ownable2Step handover begun. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` | Owner changed. |

> Note `RewardsPaidtoOwner` — lowercase `to` is the actual on-chain signature (`keccak256("RewardsPaidtoOwner(uint256,uint256,address,uint256,address)")`). Don't "correct" it to `RewardsPaidToOwner` or the topic0 won't match.

### 1.4 RedeemCommunityShares ("Claim", Base-only)

| topic0 | Event |
|--------|-------|
| `0xf3a670cd3af7d64b488926880889d08a8585a138ff455227af6737339a1ec262` | `Redeemed(address user, uint256 shares, uint256 amount)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address)` |

### 1.5 Standard proxy/upgrade constants

| Value | Meaning |
|--------|---------|
| `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` | **EIP-1967 implementation slot** — holds the impl address for every Loan/Vault(Avax)/Claim proxy. |
| `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` | EIP-1967 admin slot — **empty** on all 40 Acres proxies (UUPS keeps upgrade auth in the impl's `owner`, not an admin slot). |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address)` topic0 (≡ §1.3). |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 PortfolioManager

| Selector | Signature | Returns / mutates |
|----------|-----------|--------------------|
| `0xa879da51` | `deployFactory(bytes32 salt)` | `(address factory, address facetRegistry)`. Emits `FactoryDeployed` + `FacetRegistryDeployed`. |
| `0x06142d7d` | `registerPortfolio(address portfolio, address factory)` | Emits `PortfolioRegistered`. |
| `0x600e1b2b` | `multicall(bytes[] data, address[] targets)` | `bytes[]`. Cross-account batched calls (emits `CrossAccountMulticall`). |
| `0x2e303273` | `getPortfoliosForOwner(address)` | `address[]` — all portfolio accounts of an owner. |
| `0x045a00b5` | `getPortfoliosCountForOwner(address)` | `uint256` |
| `0xaf5190ec` | `getPortfolioForOwner(address,uint256)` | `address` (index into the owner's list). |
| `0xa0750598` | `getAllFactories()` | `address[]` |
| `0x75eb0700` | `getFactoriesLength()` | `uint256` |
| `0x55a204f9` | `getFactory(uint256)` | `address` |
| `0x6d50e452` | `getAllFacetRegistries()` | `address[]` |
| `0xd7cf67eb` | `getFacetRegistriesLength()` | `uint256` |
| `0x1fec4f9d` | `getFactoryForPortfolio(address)` | `address` |
| `0xacc2fd65` | `isPortfolioRegistered(address)` | `bool` |
| `0xf0172f39` | `isRegisteredFactory(address)` | `bool` |
| `0x59d14b41` | `isAuthorizedCaller(address)` | `bool` |
| `0x454bbd29` | `setAuthorizedCaller(address,bool)` | owner-only. Emits `AuthorizedCallerSet`. |
| `0x8da5cb5b` | `owner()` | `address` (= `0xff16fd3d…`) |

### 2.2 Vault (ERC-4626 — `asset()` = USDC, `symbol()` = `"VAULT"`, 18 dec shares)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x38d52e0f` | `asset()` | Underlying = USDC. *(Base read: `0x8335…2913`)* |
| `0x01e1d114` | `totalAssets()` | USDC under management + active loans. |
| `0x6e553f65` | `deposit(uint256 assets, address receiver)` | `uint256 shares`. Emits `Deposit`. |
| `0x94bf804d` | `mint(uint256 shares, address receiver)` | `uint256 assets`. |
| `0xb460af94` | `withdraw(uint256 assets, address receiver, address owner)` | `uint256 shares`. Emits `Withdraw`. |
| `0xba087652` | `redeem(uint256 shares, address receiver, address owner)` | `uint256 assets`. |
| `0x07a2d13a` | `convertToAssets(uint256)` | share → asset. |
| `0xc6e6f592` | `convertToShares(uint256)` | asset → share. |
| `0xef8b30f7` | `previewDeposit(uint256)` / `0xb3d7f6b9` `previewMint` / `0x4cdad506` `previewRedeem` / `0x0a28a477` `previewWithdraw` | EIP-4626 previews. |
| `0xfd158092` | `epochRewardsLocked()` | `uint256` — rewards locked for the current epoch (40 Acres extension). |
| `0xfcea5e29` | `_asset()` | internal asset getter (public). |
| `0x86997794` | `_loanContract()` | the Loan contract this vault funds. |

### 2.3 Loan (core borrow/repay — present on every Loan subclass)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf4e5753e` | `requestLoan(uint256 tokenId, uint256 amount, uint8 zeroBalanceOption, uint256 increasePercentage, address preferredToken, bool topUp, bool payoffToken)` | Open a loan against a veNFT. Emits `CollateralAdded` + `FundsBorrowed`. |
| `0xef48eee6` | `pay(uint256 tokenId, uint256 amount)` | Manual repayment. Emits `LoanPaid`. |
| `0xab6e33cf` | `payMultiple(uint256[] tokenIds)` | Batch repay. |
| `0xba1e30c1` | `claim(uint256 tokenId, address[] tokens, address[][] feeTokens, bytes swapData, uint256[2] minOut)` | Harvest veNFT rewards → repay/compound. Emits `RewardsReceived`/`RewardsClaimed`/`ProtocolFeePaid`. |
| `0xc49785b4` | `claimCollateral(uint256 tokenId)` | Withdraw veNFT after repayment. Emits `CollateralWithdrawn`. |
| `0x7a792a29` | `increaseLoan(uint256 tokenId, uint256 amount)` | Borrow more against the same veNFT. |
| `0xb2383e55` | `increaseAmount(uint256 tokenId, uint256 amount)` | Add to the veNFT lock. Emits `VeNftIncreased`. |
| `0xd1c2babb` | `merge(uint256 from, uint256 to)` | Merge two collateral veNFTs. |
| `0x0121b93f` | `vote(uint256 tokenId)` | `bool` — cast the veNFT's gauge vote (default pools). |
| `0x3bbad66f` | `userVote(uint256[] tokenIds, address[] pools, uint256[] weights)` | Custom vote. |
| `0xd9e1efdd` | `getMaxLoan(uint256 tokenId)` | `(uint256 maxLoan, uint256 …)` — borrow capacity. |
| `0x66877b8d` | `getLoanDetails(uint256 tokenId)` | `(uint256 balance, address borrower)`. |
| `0xb62f80d0` | `_loanDetails(uint256)` | full 14-field loan struct. |
| `0xa5a41031` | `getProtocolFee()` | `uint256` (Base AERO read: **500**). |
| `0xe7a7821b` | `getLenderPremium()` | `uint256` |
| `0xa0df48b1` | `getRewardsRate()` | `uint256` |
| `0xcf1b815f` | `getZeroBalanceFee()` | `uint256` |
| `0x1c17b946` | `activeAssets()` | `uint256` outstanding principal. |
| `0xcb8c5a3a` | `lendingVault()` / `0x1ffce3f4` `lendingAsset()` | the funding Vault / USDC. |
| `0xca797b3a` | `incentivizeVault(uint256)` | route rewards to the vault. |
| `0x8a5854ec` | `borrowFromPortfolio(uint256)` / `0xf48ae94e` `payFromPortfolio(uint256,uint256)` / `0x5b080c47` `migrateToPortfolio(uint256)` | **`Loan` (USDC) only** — portfolio-account integration. |
| `0x8321928d` | `odosRouter()` | `address` (pure) — the Odos swap router used to liquidate reward tokens. |
| `0x43ad12af` | `getSwapper()` | `address` |
| **Admin** | `setProtocolFee(uint256)=0x787dce3d`, `setRewardsRate(uint256)=0x74791fb6`, `setLenderPremium(uint256)=0x7d5df10f`, `setZeroBalanceFee(uint256)=0x4fb041ab`, `setApprovedPools(address[],bool)=0xcd3c750c`, `setDefaultPools(address[],uint256[])=0x1c5650d2`, `setSwapper(address)=0x9c82f2a4`, `rescueERC20(address,uint256)=0x8cd4426d` | owner-only |

### 2.4 LoanV2Native (managed-NFT extras, in addition to most of §2.3)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x016affc0` | `getManagedNft()` | `uint256` — the protocol-managed veNFT id. |
| `0x61df7206` | `mergeIntoManagedNft(uint256 tokenId)` | Merge collateral into the managed NFT. |
| `0xd49094f7` | `setManagedNft(uint256)` | owner-only. |
| `0xa9700b73` | `setIncreaseManagedToken(bool)` | toggle compounding into managed NFT. |
| `0xcafd676a` | `setOptInCommunityRewards(uint256[],bool)` | opt tokenIds into community rewards (feeds RedeemCommunityShares). |
| `0x850f9a91` | `userIncreasesManagedToken(address)` | `bool` |
| `0xf7820f38` | `_defaultPoolChangeTime()` | `uint256` |

`LoanV2Native` has **no** `borrowFromPortfolio`/`payFromPortfolio`/`migrateToPortfolio`/`setPortfolioFactory`/`depositRewards`/`lendingVault`/`_ve` — that's the cleanest way to distinguish a Native-loan impl from a USDC-loan impl by selector probing.

### 2.5 UUPS upgrade surface (Loan, LoanV2Native, RedeemCommunityShares)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4f1ef286` | `upgradeToAndCall(address newImpl, bytes data)` | `payable`. Owner-only. Emits `Upgraded`. |
| `0x52d1902d` | `proxiableUUID()` | `bytes32` = the EIP-1967 slot. **Reverts when called through the proxy** (`notDelegated`) — that revert is itself a positive UUPS signal. |
| `0xad3cb1cc` | `UPGRADE_INTERFACE_VERSION()` | `string` (OZ v5 = `"5.0.0"`). |
| `0x79ba5097` | `acceptOwnership()` / `0xe30c3978` `pendingOwner()` | Ownable2Step. |

### 2.6 RedeemCommunityShares ("Claim")

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc0c53b8b` | `initialize(address,address,address)` | one-shot proxy init. |
| `0xdb006a75` | `redeem(uint256 shares)` | Emits `Redeemed`. |
| `0x193ce1e4` | `communityRewards()` | `address` |
| `0x253f284b` | `loanContract()` | `address` |
| `0x4efa82b6` | `payoutToken()` | `address` |

---

## 3. Addresses — Base mainnet (chain ID 8453) · **Aerodrome**

All verified via `eth_getCode` on `https://base-rpc.publicnode.com`. Proxies show their impl (read from the EIP-1967 slot).

| Role | Address | Impl (if proxy) | One-liner |
|------|---------|-----------------|-----------|
| **PortfolioManager** | `0x40ac2e40acb7bdd6ec83e468143262fe216529ec` | — (singleton, 16 973 B) | Portfolio registry/factory hub. 4 factories, 4 facet registries. |
| **AERO-USDC-Vault** | `0xb99b6df96d4d5448cc0a5b3e0ef7896df9507cf5` | — (direct, 4 993 B) | ERC-4626 lender vault, `asset()` = USDC, `symbol()` = `"VAULT"`. |
| **AERO USDC Loan** | `0x87f18b377e625b62c708d5f6ea96ec193558efd0` | `0xb43b30c405c61bc330227968635d130994450735` (`Loan`) | Borrow USDC against an Aerodrome veNFT. `getProtocolFee()` = 500. |
| **AERO Loan** (native) | `0x1Dc76341CA156e376736ddbA042aba071bD3b858` | `0xeda1e6578f7cca28a36e5b50d71f2f154b93c061` (`LoanV2Native`) | Borrow AERO (managed-NFT variant). |
| **Claim** (`RedeemCommunityShares`) | `0x8Ac5aa057da4c86f3896cFD851cBcdFC19a04dfe` | `0x030ad5f8a436ac243e8682c8d036cd82bf5a9fe3` | Community-rewards redemption. **Only deployed here (Base).** |
| Portfolio Factories (×4) | `0x967361472f99fedc26a2b8bb3cfc1d0966979c8e`, `0xc3b96d5e971407902c563194bf8386ca5dad787b`, `0xae7b5751c370dc566a2bcd63be3e20729d050264`†, `0x74488ee5f1599cc4b89fa42134b9c5a142cba7d6` | Diamond | Mint per-user portfolio accounts. |
| Facet Registries (×4) | `0xc2b32a782b7d98939c9403343b9e6d3c019004a2`, `0x3a0e5b904991196c9fcf8d591c8b9db9450bcdf4`, `0x82357a62b407fc89b0505b986c70812f395aeecf‡`, `0x60ab719aa7e0de6797e1619fceacab29c2a9e24b` | Diamond | Facet/selector registries for the factories. |
| Protocol admin (`owner`) | `0xff16fd3d147220e6cc002a8e4a1f942ac41dbd23` | EOA/multisig | Owns PortfolioManager + all Loans; UUPS upgrade authority. |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | — | 6 decimals; vault underlying. |

† `0xae7b5751…0264` factory and ‡ `0x82357a62…eecf` facet registry are the **same addresses on Base, Optimism, and Ethereum** (deterministic deploy).

---

## 4. Addresses — Optimism (chain ID 10) · **Velodrome**

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`.

| Role | Address | Impl (if proxy) | One-liner |
|------|---------|-----------------|-----------|
| **PortfolioManager** | `0x40ac2e40acb7bdd6ec83e468143262fe216529ec` | — (singleton) | 3 factories, 3 facet registries. |
| **VELO-USDC-Vault** | `0x08dcdbf7bade91ccd42cb2a4ea8e5d199d285957` | — (direct, 4 993 B) | ERC-4626 vault, `asset()` = USDC. |
| **VELO USDC Loan** | `0xf132bD888897254521D13e2c401e109caABa06A7` | `0x972b1ac00dfb287f244205b379f4565ab286ed3a` (`Loan`, ≡ Base) | Borrow USDC against a Velodrome veNFT. |
| **VELO Loan** (native) | `0x8C0Ae206A52D3FddE6D43Ea5B5CbbbE00e1C0315` | `0xbfb12bac6bd6ce8c1006542152c2bbbe0bf1e54b` (`LoanV2Native`, ≡ Base) | Borrow VELO. |
| Portfolio Factories (×3) | `0x8a71e4bab42ddc3d996fa4b4780919567e367924`, `0xce904f1c3c9bdf74d4dbd6a204058d1eb649140b`, `0xae7b5751c370dc566a2bcd63be3e20729d050264`† | Diamond | |
| Facet Registries (×3) | `0x8139b24596dc0bee2f7a66d5a0d519c16c962c86`, `0xfbb7deab88be1f80dde3f2919b59acb9fe9e31e2`, `0x82357a62b407fc89b0505b986c70812f395aeecf‡` | Diamond | |
| USDC (native) | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | — | 6 decimals. |

**No Claim / RedeemCommunityShares on Optimism** — `0x8Ac5aa05…` has `0x` bytecode here (the docs list it for all four DEXes, but it is Base-only).

---

## 5. Addresses — Avalanche C-Chain (chain ID 43114) · **Pharaoh + Blackhole**

Verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`. **On Avax the Vaults are proxied** (unlike Base/OP where they're deployed directly).

| Role | Address | Impl (if proxy) | One-liner |
|------|---------|-----------------|-----------|
| **PortfolioManager** | `0x40ac2e40acb7bdd6ec83e468143262fe216529ec` | — (singleton) | Deployed, but **0 factories / 0 facet registries** registered (portfolio layer not yet active on Avax). |
| **PHAR-USDC-Vault** | `0x124D00b1ce4453Ffc5a5F65cE83aF13A7709baC7` | `0x6243e6b69118d75cac781e806aef4b21c5890cc1` (`Vault`, **ERC-1967 proxy**) | Pharaoh lender vault. |
| **BLACK-USDC-Vault** | `0xC0485C4bafB594Ae1457820fb6e5B67e8A04BCFD` | `0xf8e3120fd9957200b84913f746b4cb66b9a8a612` (`Vault`, ERC-1967 proxy) | Blackhole lender vault. |
| **PHAR USDC Loan** | `0x6Bf2Fe80D245b06f6900848ec52544FBdE6c8d2C` | `0x01e9e8e684dd9b158fe772405f7b013f792e9a2f` (`XPharaohLoan`) | Borrow USDC against a Pharaoh veNFT (xPHAR model). |
| **PHAR Loan** (native) | `0xd3E726b681C9a1E2a620cef9fE0EcE49822B11d4` | `0x54c269cf9712ab099ae1668b031f719156206ad9` (`PharaohLoanV2Native`) | Borrow PHAR (managed-NFT variant). |
| **BLACK Loan** (USDC **and** native) | `0x5122f5154DF20E5F29df53E633cE1ac5b6623558` | `0x693ab037675b056730576892c214015990440cdb` (`LoanV2Native` family) | **One contract serves both the "BLACK USDC Loan" and "BLACK Loan" doc rows** — the docs list the same address twice. |
| USDC (native, Circle) | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` | — | 6 decimals; vault underlying. |

**No Claim / RedeemCommunityShares on Avalanche** (`0x8Ac5aa05…` = `0x` bytecode).

---

## 6. Addresses — Ethereum mainnet (chain ID 1) · **portfolio layer only**

Verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com`. **No veNFT lending markets** (no Loan/Vault/Claim — Ethereum has no Aerodrome/Velodrome/Pharaoh/Blackhole). What *is* live is the **portfolio smart-account infrastructure**.

| Role | Address | One-liner |
|------|---------|-----------|
| **PortfolioManager** | `0x40ac2e40acb7bdd6ec83e468143262fe216529ec` | Same singleton bytecode (16 973 B). **5 factories, 5 facet registries** — the most of any chain. `owner()` = `0xff16fd3d…`. |
| Portfolio Factories (×5) | `0x581333879b1b6726dd92a740da0109193640a395`, `0xae7b5751c370dc566a2bcd63be3e20729d050264`†, `0x8f1f0270bf0a547925945997e3ad53967dcf4ffe`, `0xdef2781c0b9a76c317f74d97a09a1671b1979969`, `0x3721414f0aeb287c604b8e8a55b7986a19f687af` | Diamond portfolio factories. |
| Facet Registries (×5) | `0x3f75dcc3aa32702fc308bb5cf4bbba91c4aa414a`, `0x82357a62b407fc89b0505b986c70812f395aeecf‡`, `0x909f6742187e7df354faf19227f0e66a5ed31530`, `0xcf8d230f7d81141f12e8f8a4f8dc70327b29e0af`, `0x88358d0b07b664e5a9e57923ff24b9dc337606f2` | Facet registries. |

---

## 7. Cross-chain summary

| Chain | ID | DEX(es) | PortfolioMgr | Factories | Vaults | USDC Loans | Native Loans | Claim |
|---|---|---|---|---|---|---|---|---|
| Ethereum | 1 | — | ✓ (singleton) | 5 | — | — | — | — |
| Base | 8453 | Aerodrome | ✓ | 4 | direct | 1 (`Loan`) | 1 (`LoanV2Native`) | ✓ |
| Optimism | 10 | Velodrome | ✓ | 3 | direct | 1 (`Loan`) | 1 (`LoanV2Native`) | — |
| Avalanche | 43114 | Pharaoh, Blackhole | ✓ | 0 | **proxied** | 1 (`XPharaohLoan`) | 2 (`PharaohLoanV2Native` + Blackhole) | — |
| BNB | 56 | — | ✗ | — | — | — | — | — |
| Arbitrum | 42161 | — | ✗ | — | — | — | — | — |
| Polygon | 137 | — | ✗ | — | — | — | — | — |

Vanity address tells: **PortfolioManager** is `0x40ac2e40ac…` (`40ac` = "40 Ac[res]") on all four deployed chains. **Claim** is `0x8Ac5aa05…` but only has code on Base.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Loan / LoanV2Native** (+ subclasses) | **UUPS** (ERC-1967 + ERC-1822) | Small proxy bytecode (~130–170 B); EIP-1967 impl slot `0x360894…bbc` is set; impl exposes `proxiableUUID()`, `upgradeToAndCall()`, `Upgraded` event; **admin slot empty**. `proxiableUUID()` *reverts* when called via the proxy. | `owner()` (= `0xff16fd3d…`), Ownable2Step. |
| **RedeemCommunityShares** (Base) | **UUPS** | as above (130 B proxy). | `owner()`. |
| **Vault — Avalanche** | **ERC-1967 proxy** (non-UUPS: the `Vault` impl has *no* `upgradeToAndCall`/`proxiableUUID`) | ~130–141 B proxy with EIP-1967 impl slot set, admin slot empty. Treat impl as fixed-per-deploy. | n/a (no upgrade entrypoint in impl ABI). |
| **Vault — Base / Optimism** | **Direct deployment (no proxy)** | 4 993 B full contract; EIP-1967 impl slot empty. | immutable. |
| **PortfolioManager** | **Singleton, no proxy** | 16 973 B full contract on every chain at the same vanity address; impl slot empty. | `owner()`. |
| **Factories / FacetRegistries** | **Diamond (EIP-2535)** | Deployed by `PortfolioManager.deployFactory`; emit `FactoryDeployed`/`FacetRegistryDeployed`; mint per-user portfolio Diamonds. | PortfolioManager owner. |

To read the live impl of any proxy: `cast storage <proxy> 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. **Watch the `Upgraded(address)` topic** (`0xbc7cd75a…2d3b`) on Loan/Claim proxies to catch impl rotations — the docs only show current impls.

---

## 9. Detection invariants & gotchas

1. **A loan lifecycle = `CollateralAdded` → `FundsBorrowed` → (repeated `RewardsReceived`/`LoanPaid`) → `CollateralWithdrawn`,** keyed by `tokenId` (the veNFT id) on a single Loan contract. There is **no liquidation event** — loans are non-liquidatable by design.
2. **`tokenId` is the veNFT id, not a 40 Acres-internal id.** It collides across DEXes (Aerodrome veNFT #5 ≠ Velodrome veNFT #5). Always key on `(chainId, loan address, tokenId)`.
3. **Self-repayment leaves no token `Transfer` from the borrower.** Repayment flows from harvested veNFT rewards inside `claim()` → `LoanPaid`. Don't expect a borrower→protocol ERC-20 transfer for each repayment.
4. **EIP-4626 `Deposit`/`Withdraw` topics are generic.** The same `0xdcbc1c05…`/`0xfbde797d…` topics fire on every 4626 vault on the chain — filter by the specific vault address.
5. **`RewardsPaidtoOwner` has a lowercase `to`** in the canonical signature — using the "correct" capitalization yields the wrong topic0.
6. **Avax vaults are proxies; Base/OP vaults are not.** Reading the EIP-1967 slot on a Base/OP vault returns empty — that's expected, not a missing proxy.
7. **`Claim` (`0x8Ac5aa05…`) only has code on Base.** The contracts doc lists it under all four DEXes, but Optimism and Avalanche return `0x`. Don't index it cross-chain.
8. **Blackhole's "USDC Loan" and "Loan" are the same address** (`0x5122…3558`, impl `0x693ab037…`). One contract, two doc rows.
9. **PortfolioManager is the same vanity address (`0x40ac2e40ac…`) on ETH/Base/OP/Avax,** but the *factory/facet-registry sets differ per chain* (ETH 5, Base 4, OP 3, Avax 0). Always read `getAllFactories()` per chain. Factory `0xae7b5751…0264` and facet registry `0x82357a62…eecf` recur on ETH+Base+OP.
10. **Ethereum has the portfolio layer but no lending.** If you only look for Loan/Vault you'll wrongly conclude "not on Ethereum" — the PortfolioManager + 5 factories are live there.
11. **UUPS impls are the upgrade target** — index events on the *proxy* address (stable), read state by `eth_call` to the *proxy* (delegates to impl). The impl address can change via `Upgraded`.
12. **Distinguish `Loan` vs `LoanV2Native` by selectors:** USDC `Loan` has `borrowFromPortfolio`/`payFromPortfolio`/`lendingVault`; `LoanV2Native` has `getManagedNft`/`mergeIntoManagedNft`/`setOptInCommunityRewards` instead.
13. **Reward-token liquidation uses Odos** (`odosRouter()`), not a 40 Acres AMM — expect Odos router calls inside `claim()` txs.
14. **Not on BNB / Arbitrum / Polygon.** Every 40 Acres address returns `0x` there as of 2026-05-29.
15. **veNFTs are the only live collateral.** The marketing line "USDC against veNFTs, RWAs, tokenized funds, and LP positions" lists a *roadmap* — RWAs / tokenized funds / LP positions are "coming soon," not yet live collateral types as of 2026-05. Only veNFT loans exist on-chain today.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- PortfolioManager
TOPIC_FACTORY_DEPLOYED            = '\xf96fae1c85039df437ec1af96b53627ef4b8de60de364b148c795c4b0ccb2361'
TOPIC_FACET_REGISTRY_DEPLOYED     = '\xc3610a15c0531fda8894c29a65398597a7b73766c6868fd4967ed2688d502ba6'
TOPIC_PORTFOLIO_REGISTERED        = '\x37868bdfe8994d893b5d7a9fae580a86ca5da03c90340d983799d5d3d8810970'
TOPIC_CROSS_ACCOUNT_MULTICALL     = '\x03de89a8856e0ef333405de002ac7fc89e4b9bd300af69cf63795ef68ca56fd0'
TOPIC_AUTHORIZED_CALLER_SET       = '\x1eff62a53441c7d0125c22f2a9a324e206b34efa41e19469d7efb9bb703d21a3'
-- Vault (ERC-4626)
TOPIC_4626_DEPOSIT                = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_4626_WITHDRAW               = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
-- Loan / LoanV2Native (all subclasses)
TOPIC_COLLATERAL_ADDED            = '\xe289f9a78f6ca99c12176d7f92cdc104bf35c6c2b48ef2f8e1e04a1551894b74'
TOPIC_FUNDS_BORROWED              = '\x3bd6238aaa73867918dcdf740a894fd816018bdca8dc628b117999e41950ba27'
TOPIC_LOAN_PAID                   = '\x74d71c8dada9cecbd188b84bcb7522de7ca42087c4110f5bb4461b3402edd729'
TOPIC_COLLATERAL_WITHDRAWN        = '\x2d428178e65c47bfb7d75b43e57e93851220995d8887d6826253c18d9b9fc99f'
TOPIC_REWARDS_RECEIVED            = '\x66aebf327a5c16726a6685b85821f29c65b3b925c44e91811511683a8e71a91d'
TOPIC_REWARDS_CLAIMED             = '\x0d66919505e691cceb14298df92d143853afb29242516310143ece94513af759'
TOPIC_REWARDS_INVESTED            = '\x36c0b6334ab9d8a841bc0b90539b690e987e6af2a797eb3dbb0781fdff3b8b55'
TOPIC_REWARDS_PAID_TO_OWNER       = '\x1b53afc804bdcdda0126d69a51ee46ee54c0b82deb70144c82fa9573fde707f3'
TOPIC_PROTOCOL_FEE_PAID           = '\xb17a3e7bbddf0580407b3a338c0d7f004e8a35ccce78cd53418f5f56a1abb672'
TOPIC_VENFT_INCREASED             = '\x742ad298609ca48e9fe8da7d4599cc7ab771dcfa73ce69d8751850d3105a0faa'
TOPIC_INITIALIZED                 = '\xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_OWNERSHIP_TRANSFER_STARTED  = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
-- RedeemCommunityShares (Base-only)
TOPIC_REDEEMED                    = '\xf3a670cd3af7d64b488926880889d08a8585a138ff455227af6737339a1ec262'

-- ===== Selectors =====
-- PortfolioManager
SEL_DEPLOY_FACTORY                = '\xa879da51'
SEL_REGISTER_PORTFOLIO            = '\x06142d7d'
SEL_GET_PORTFOLIOS_FOR_OWNER      = '\x2e303273'
SEL_GET_ALL_FACTORIES             = '\xa0750598'
SEL_GET_FACTORIES_LENGTH          = '\x75eb0700'
SEL_GET_ALL_FACET_REGISTRIES      = '\x6d50e452'
-- Vault (ERC-4626)
SEL_VAULT_ASSET                   = '\x38d52e0f'
SEL_VAULT_TOTAL_ASSETS            = '\x01e1d114'
SEL_VAULT_DEPOSIT                 = '\x6e553f65'
SEL_VAULT_WITHDRAW                = '\xb460af94'
SEL_VAULT_REDEEM                  = '\xba087652'
SEL_VAULT_EPOCH_REWARDS_LOCKED    = '\xfd158092'
-- Loan
SEL_REQUEST_LOAN                  = '\xf4e5753e'
SEL_PAY                           = '\xef48eee6'
SEL_PAY_MULTIPLE                  = '\xab6e33cf'
SEL_CLAIM                         = '\xba1e30c1'
SEL_CLAIM_COLLATERAL              = '\xc49785b4'
SEL_INCREASE_LOAN                 = '\x7a792a29'
SEL_INCREASE_AMOUNT               = '\xb2383e55'
SEL_MERGE                         = '\xd1c2babb'
SEL_VOTE                          = '\x0121b93f'
SEL_USER_VOTE                     = '\x3bbad66f'
SEL_GET_MAX_LOAN                  = '\xd9e1efdd'
SEL_GET_LOAN_DETAILS              = '\x66877b8d'
SEL_GET_PROTOCOL_FEE              = '\xa5a41031'
SEL_ACTIVE_ASSETS                 = '\x1c17b946'
SEL_LENDING_VAULT                 = '\xcb8c5a3a'
-- LoanV2Native extras
SEL_GET_MANAGED_NFT               = '\x016affc0'
SEL_MERGE_INTO_MANAGED_NFT        = '\x61df7206'
SEL_SET_OPT_IN_COMMUNITY_REWARDS  = '\xcafd676a'
-- UUPS
SEL_UPGRADE_TO_AND_CALL           = '\x4f1ef286'
SEL_PROXIABLE_UUID                = '\x52d1902d'
-- RedeemCommunityShares
SEL_REDEEM_SHARES                 = '\xdb006a75'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                 = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Protocol admin (all chains) =====
A40_OWNER                         = '\xff16fd3d147220e6cc002a8e4a1f942ac41dbd23'

-- ===== Base (chain ID 8453) — Aerodrome =====
BASE_PORTFOLIO_MANAGER            = '\x40ac2e40acb7bdd6ec83e468143262fe216529ec'
BASE_AERO_USDC_VAULT              = '\xb99b6df96d4d5448cc0a5b3e0ef7896df9507cf5'
BASE_AERO_USDC_LOAN               = '\x87f18b377e625b62c708d5f6ea96ec193558efd0'   -- impl 0xb43b30c4… (Loan)
BASE_AERO_LOAN_NATIVE             = '\x1dc76341ca156e376736ddba042aba071bd3b858'   -- impl 0xeda1e657… (LoanV2Native)
BASE_CLAIM_REDEEM_COMMUNITY       = '\x8ac5aa057da4c86f3896cfd851cbcdfc19a04dfe'   -- impl 0x030ad5f8… (Base-only)
BASE_USDC                         = '\x833589fcd6edb6e08f4c7c32d4f71b54bda02913'

-- ===== Optimism (chain ID 10) — Velodrome =====
OP_PORTFOLIO_MANAGER              = '\x40ac2e40acb7bdd6ec83e468143262fe216529ec'
OP_VELO_USDC_VAULT                = '\x08dcdbf7bade91ccd42cb2a4ea8e5d199d285957'
OP_VELO_USDC_LOAN                 = '\xf132bd888897254521d13e2c401e109caaba06a7'   -- impl 0x972b1ac0… (Loan)
OP_VELO_LOAN_NATIVE               = '\x8c0ae206a52d3fdde6d43ea5b5cbbbe00e1c0315'   -- impl 0xbfb12bac… (LoanV2Native)
OP_USDC                           = '\x0b2c639c533813f4aa9d7837caf62653d097ff85'
-- NOTE: no Claim on Optimism

-- ===== Avalanche (chain ID 43114) — Pharaoh + Blackhole =====
AVAX_PORTFOLIO_MANAGER            = '\x40ac2e40acb7bdd6ec83e468143262fe216529ec'   -- 0 factories registered
AVAX_PHAR_USDC_VAULT              = '\x124d00b1ce4453ffc5a5f65ce83af13a7709bac7'   -- impl 0x6243e6b6… (Vault, ERC-1967 proxy)
AVAX_BLACK_USDC_VAULT             = '\xc0485c4bafb594ae1457820fb6e5b67e8a04bcfd'   -- impl 0xf8e3120f… (Vault, ERC-1967 proxy)
AVAX_PHAR_USDC_LOAN               = '\x6bf2fe80d245b06f6900848ec52544fbde6c8d2c'   -- impl 0x01e9e8e6… (XPharaohLoan)
AVAX_PHAR_LOAN_NATIVE             = '\xd3e726b681c9a1e2a620cef9fe0ece49822b11d4'   -- impl 0x54c269cf… (PharaohLoanV2Native)
AVAX_BLACK_LOAN                   = '\x5122f5154df20e5f29df53e633ce1ac5b6623558'   -- impl 0x693ab037… (USDC + native are the SAME address)
AVAX_USDC                         = '\xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e'
-- NOTE: no Claim on Avalanche

-- ===== Ethereum (chain ID 1) — portfolio layer only, NO lending markets =====
ETH_PORTFOLIO_MANAGER             = '\x40ac2e40acb7bdd6ec83e468143262fe216529ec'   -- 5 factories, 5 facet registries

-- Shared across ETH+Base+OP (deterministic deploy):
SHARED_PORTFOLIO_FACTORY          = '\xae7b5751c370dc566a2bcd63be3e20729d050264'
SHARED_FACET_REGISTRY             = '\x82357a62b407fc89b0505b986c70812f395aeecf'
```

---

## 11. Verification & sources

How every constant was verified (2026-05-29):

- **Addresses (docs):** [`docs.40acres.finance/contracts`](https://docs.40acres.finance/contracts) (raw markdown via `contracts.md`) — Portfolio Manager, Supply Vaults, Loan Contracts, Claim Addresses tables.
- **Bytecode existence + proxy slots:** `eth_getCode` and `eth_getStorageAt` (EIP-1967 impl/admin slots) on each chain's publicnode RPC. Confirmed: PortfolioManager 16 973 B singleton on ETH/Base/OP/Avax (impl slot empty); Base/OP vaults direct (4 993 B, empty impl slot); Avax vaults + all loans + Base claim are proxies with the EIP-1967 impl slot populated and the admin slot empty (→ UUPS for loans/claim, plain ERC-1967 for Avax vaults). **Not deployed on BNB / Arbitrum / Polygon** (`0x` for every address).
- **Contract names + ABIs:** Sourcify v2 verified source (`PortfolioManager` solc 0.8.30, `Vault` 0.8.28, `Loan` 0.8.30, `LoanV2Native` 0.8.28, `RedeemCommunityShares` 0.8.28 on Base); Routescan getsourcecode for Avax (`Vault`, `XPharaohLoan` solc 0.8.30, `PharaohLoanV2Native` 0.8.28).
- **Topic0 + selectors:** computed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome) from the Sourcify ABIs. Cross-checked against deployed bytecode.
- **Cross-chain family match:** extracted `PUSH4` selector sets from each impl's runtime bytecode and matched against the Base reference impls — OP VELO loans/vault ≈ Base `Loan`/`LoanV2Native`/`Vault` (Jaccard 0.93–0.98); Avax Pharaoh/Blackhole loans match the `Loan`/`LoanV2Native` family (0.41–0.73, lower due to per-DEX subclassing).
- **Live state (`eth_call`):** Base AERO-USDC-Loan `owner()` = `0xff16fd3d…`, `getProtocolFee()` = 500; PortfolioManager `getFactoriesLength()` = 4 (Base) / 5 (ETH) / 3 (OP) / 0 (Avax); Base vault `asset()` = USDC, `symbol()` = `"VAULT"`; `proxiableUUID()` reverts through the proxy (UUPS `notDelegated`).
- **Live events (`eth_getLogs`):** confirmed `LoanPaid`, `CollateralWithdrawn`, `VeNftIncreased`, `CollateralAdded` on the Base AERO-USDC-Loan proxy, and `LoanPaid` on the Optimism VELO-USDC-Loan proxy (proves the cross-chain event signatures are identical).
- **Audits:** 4× Sherlock (lead auditors eeyore, 0xadrii, oot2k) — [security page](https://docs.40acres.finance/security).

Authoritative sources:
- [40 Acres docs — Contracts](https://docs.40acres.finance/contracts) · [Audits & Security](https://docs.40acres.finance/security) · [docs index](https://docs.40acres.finance/llms.txt)
- Sourcify: `https://sourcify.dev/server/v2/contract/8453/<address>`
- Explorers: [Basescan](https://basescan.org/address/0x87f18b377e625b62c708d5f6ea96ec193558efd0) · [Optimistic Etherscan](https://optimistic.etherscan.io/address/0xf132bD888897254521D13e2c401e109caABa06A7) · [Snowscan](https://snowscan.xyz/address/0x6Bf2Fe80D245b06f6900848ec52544FBdE6c8d2C) · [Etherscan PortfolioManager](https://etherscan.io/address/0x40ac2e40acb7bdd6ec83e468143262fe216529ec)

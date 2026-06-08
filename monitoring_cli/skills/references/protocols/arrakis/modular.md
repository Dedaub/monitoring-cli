# Arrakis Modular — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB; absent on Avalanche)

**Status:** verified 2026-06-04. Topic0/selector hashes computed locally with `keccak256` from the canonical `ArrakisFinance/arrakis-modular` Solidity interfaces; addresses confirmed via `eth_getCode` on all seven target chains; the factory event topic0, the factory→manager/registry wiring, and the proxy/beacon slots confirmed live via `eth_getStorageAt` / `eth_call` / `eth_getLogs` on Ethereum.
**Scope:** **Arrakis Modular** — the current generation of Arrakis: a universal **Meta Vault** standard with pluggable per-strategy **modules** (Uniswap V4 module, Valantis HOT module, …). Covers `ArrakisMetaVaultFactory`, the public ERC-20 vaults (`ArrakisMetaVaultPublic`) and private NFT-owned vaults (`ArrakisMetaVaultPrivate`), `ArrakisStandardManager`, `ArrakisPublicVaultRouter` (+ `RouterSwapExecutor`/`RouterSwapResolver`), `Guardian`, `TimeLock`, the `ModulePublicRegistry`/`ModulePrivateRegistry`, the module beacons, and the Private-Vault NFT. This is a **new architecture, not Arrakis V2** (PALM/`ArrakisV2` vaults are a separate, older generation).

## Orientation

- **Meta Vault + modules.** A meta-vault holds the LP position abstractly; the *actual* AMM liquidity/swaps live in a swappable **module** the vault delegates to. The vault itself emits only high-level accounting events (`LogMint`/`LogBurn`/`LogDeposit`/`LogWithdraw`/`LogSetModule`); the on-chain swap/LP events come from the **underlying venue** the active module wraps (e.g. Uniswap V4 `PoolManager`, or a Valantis `SovereignPool`). To attribute real liquidity moves you must follow the module to its venue.
- **Two vault flavours.** **Public** = `ArrakisMetaVaultPublic`, an **ERC-20** shared vault (anyone mints/burns shares via `mint`/`burn`; router-friendly). **Private** = `ArrakisMetaVaultPrivate`, an **NFT-owned** vault (deposits/withdrawals gated to whitelisted depositors; ownership = the Private-Vault NFT). They are created by two different factory functions and emit different creation events.
- **Manager-driven.** Vaults are managed by the single `ArrakisStandardManager`, which executes `rebalance`/`setModule` and collects management fees. The manager is the only address allowed to move a vault between modules / rebalance.
- **CREATE3 shared addresses.** All the singleton infrastructure contracts (factory, manager, router, guardian, timelock, registries, NFT) are deployed with **CREATE3** so they carry the **same address on every chain**. One address table covers all chains — but *presence differs per chain* (see Addresses; e.g. the router is only on ETH/Base/Arbitrum, and nothing is on Avalanche).
- **Governance.** `Guardian` (pause authority) → `TimeLock` owns the upgradeable manager proxy and the module beacons. Module upgrades happen by the TimeLock upgrading the relevant `UpgradeableBeacon`.

---

## Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### ArrakisMetaVaultFactory

| topic0 | Event |
|--------|-------|
| `0x78a30a2797e72cead59a8694c4281e40afe75b46a6362a880ec46771845e3020` | `LogPublicVaultCreation(address indexed creator, bytes32 salt, address token0, address token1, address owner, address module, address publicVault, address timeLock)` |
| `0x15509c43e33ed1fab25841b16998c22b4ed073f627883f1131d2e1b870df129a` | `LogPrivateVaultCreation(address indexed creator, bytes32 salt, address token0, address token1, address owner, address module, address privateVault)` — **live-confirmed** |
| `0x90ccec5da4c6ba39e2d222eac064da2aba3b61461ffba1a355efa99b7947f489` | `LogWhitelistDeployers(address[] deployers)` |
| `0x3107f5bbb8b23b80602a19bab111c1528df45fc0ab255fca51a6ff0fc0595438` | `LogBlacklistDeployers(address[] deployers)` |
| `0x496dcec0646703aaf2a371dc4b30ec9dac72703c05676629678af06149de3dc7` | `LogSetManager(address oldManager, address newManager)` (factory's; 2 args) |

The two creation events are the highest-signal Modular events: subscribe to them on the factory to discover every public ERC-20 vault and every private NFT vault. The non-indexed `publicVault`/`privateVault` field is the new vault address; `module` is its default (first) module; `token0`/`token1` the pair; `salt` the CREATE3 salt. **Only `creator` is indexed.**

### ArrakisMetaVaultPublic (ERC-20 shared vault)

| topic0 | Event |
|--------|-------|
| `0xb95558c5fa26a0093cddc7ad7eb438c0475c3d69925f02e8787c72661472ad90` | `LogMint(uint256 shares, address receiver, uint256 amount0, uint256 amount1)` |
| `0x97a53db416643aef28847c991d7cd62b34c7579f1d86acbba5c7dd64cc0d1584` | `LogBurn(uint256 shares, address receiver, uint256 amount0, uint256 amount1)` |

Plus the standard ERC-20 `Transfer`/`Approval` (`0xddf252ad…`, `0x8c5be1e5…`) — public-vault shares are an ERC-20 token.

### ArrakisMetaVaultPrivate (NFT-owned vault)

| topic0 | Event |
|--------|-------|
| `0x1f38c0b96f5f251e5fb679ab3fb88695fb7ed9698d9d13fa8599de3bf0fd6479` | `LogDeposit(uint256 amount0, uint256 amount1)` |
| `0x3228bf4a0d547ed34051296b931fce02a1927888b6bc3dfbb85395d0cca1e9e0` | `LogWithdraw(uint256 proportion, uint256 amount0, uint256 amount1)` |
| `0x5c9265672925c5544e4d535af6d0684ea57e4cd95c7e707253c189c37de03c59` | `LogWhitelistDepositors(address[] depositors)` |
| `0xb0cb71a9d9fcb2642936172f746fc80597811e946a534ba1b0e218963a2f2f02` | `LogBlacklistDepositors(address[] depositors)` |

### ArrakisMetaVault (base — emitted by BOTH public & private vaults)

| topic0 | Event |
|--------|-------|
| `0x098a4cb3597f0b783d955415cf1025a9452365cac4dcddca246a394e73cca90a` | `LogSetModule(address module, bytes[] payloads)` — vault switched active module |
| `0xc36d7d831827b79e3044eab60b0e78bcbddb1e832fdd0e848aa633471f7a2dce` | `LogSetFirstModule(address module)` — default module at creation |
| `0x9b6ffaf4cbfd923495440b7f17ced9394289f001b3ead53ab67e2c3f3e39b0f5` | `LogSetManager(address manager)` (vault's; **1 arg** — distinct topic0 from the factory's 2-arg `LogSetManager`) |
| `0x0936fa8fc79e7acdb2f5db0618a6355fdda409b0e5b17e3be004be15bcf4c884` | `LogWhiteListedModules(address[] modules)` |
| `0xf2b7116a60dcb1f53337287d3735fc1ac1b053cc3fd07d605588cc1a879c0df0` | `LogWhitelistedModule(address module)` |
| `0xbb08f8051cd2fa9d17f2636a7cf104cf87e85218c2a9061b0ade4fc5d013f328` | `LogBlackListedModules(address[] modules)` |
| `0xa292e28c648da34e20b372054caab5f0359198b3b4d5f0ef9945d4616e15dc97` | `LogWithdrawManagerBalance(uint256 amount0, uint256 amount1)` |

### ArrakisStandardManager

| topic0 | Event |
|--------|-------|
| `0x38d3829a837b9e8af9587ec40ba2729f1f3679f831777bb639da59a461804360` | `LogRebalance(address indexed vault, bytes[] payloads)` |
| `0x67cc0d0f05e6986c474f5f7f95318cf6437b628440f79711ef957794b7cffd2e` | `LogSetModule(address indexed vault, address module, bytes[] payloads)` (manager's; 3 args — distinct from the vault's `LogSetModule`) |
| `0x848acd7079af2a323ca6b8a860068c114673abe038a880b126bf280c26032c04` | `LogSetManagementParams(address indexed vault, address oracle, uint24 maxSlippagePIPS, uint24 maxDeviation, uint256 cooldownPeriod, address executor, address stratAnnouncer)` |
| `0x61e2dc30785ffbd4d4635970197d44198b53c094ab495368058abd0f0a0710ee` | `LogSetVaultData(address indexed vault, bytes datas)` |
| `0x7bb963426cf1af62285b13e10f2d60df9cec9ca0d85c18c6cd2c27d7e347fbda` | `LogSetVaultStrat(address indexed vault, string strat)` |
| `0x0b5f5d3af5972fc5e91f5b56d613f5711e187bd70056693a629e24d323edb160` | `LogChangeManagerFee(address vault, uint256 newFeePIPS)` |
| `0x728744d665a5895cc6a2585bbc6b265e8bda77d245f5311ec92f8ca48caeac3e` | `LogWithdrawManagerBalance(address indexed receiver0, address indexed receiver1, uint256 amount0, uint256 amount1)` (manager's; 4 args) |
| `0x68ec1681f33885e64cf3268f285f4789bd226f23a394700823d46105a1c03e81` | `LogSetFactory(address vaultFactory)` |

`LogRebalance` is the workhorse manager event: every active rebalance / position change on a managed vault. The `payloads` are encoded module calls — decode against the active module's ABI.

### ArrakisLPModule (base — emitted by every module)

| topic0 | Event |
|--------|-------|
| `0x9744d0a120f7c7d7906cfe3c05b50669fb49aa6d778b099d5d6edc386dee5b59` | `LogWithdraw(address indexed receiver, uint256 proportion, uint256 amount0, uint256 amount1)` (module's; 4 args — distinct from the private-vault `LogWithdraw`) |
| `0xa292e28c648da34e20b372054caab5f0359198b3b4d5f0ef9945d4616e15dc97` | `LogWithdrawManagerBalance(uint256 amount0, uint256 amount1)` |
| `0x5b5a6a8527892eb1e879279ea1addd664eef55099889d3fe13e926a5fd7c3605` | `LogSetManagerFeePIPS(uint256 oldFee, uint256 newFee)` |

### ArrakisPublicVaultRouter

| topic0 | Event |
|--------|-------|
| `0x79ee3df02fcb86d2989c21c1a792c528d6c4f38c0ad427eec754c8096b020606` | `Swapped(bool zeroForOne, uint256 amount0Diff, uint256 amount1Diff, uint256 amountOutSwap, uint256 amountInSwap)` — emitted on swap-and-add flows |

### Guardian

| topic0 | Event |
|--------|-------|
| `0x6980d5b2e749d15ffa2ae3cd57c4c552f4d4b8fc0942e00316d39219d51aec79` | `LogSetPauser(address oldPauser, address newPauser)` |

---

## Function signatures (`selector = keccak256(canonical signature)[0:4]`)

### ArrakisMetaVaultFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa2eb3521` | `deployPublicVault(bytes32 salt_, address token0_, address token1_, address owner_, address beacon_, bytes moduleCreationPayload_, bytes initManagementPayload_)` | CREATE3-deploys an ERC-20 public vault. Returns `address vault`. Emits `LogPublicVaultCreation`. `beacon_` selects the default module type. |
| `0x19b56b8b` | `deployPrivateVault(bytes32 salt_, address token0_, address token1_, address owner_, address beacon_, bytes moduleCreationPayload_, bytes initManagementPayload_)` | CREATE3-deploys an NFT-owned private vault. Returns `address vault`. Emits `LogPrivateVaultCreation`. |
| `0xd0ebdbe7` | `setManager(address)` | onlyOwner. |
| `0x930eb899` | `whitelistDeployer(address[])` | grants public-vault deploy rights. |
| `0x844f8d3c` | `blacklistDeployer(address[])` | |
| `0x8456cb59` | `pause()` / `0x3f4ba83a` `unpause()` | |

Read helpers (view): `numOfPublicVaults()` `0x…` , `numOfPrivateVaults()`, `publicVaults(uint256,uint256)`, `privateVaults(uint256,uint256)`, `isPublicVault(address)`, `isPrivateVault(address)`, `manager()`, `moduleRegistryPublic()`, `moduleRegistryPrivate()` — use these to enumerate/classify vaults.

### ArrakisMetaVaultPublic / Private / base

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x94bf804d` | `mint(uint256 shares_, address receiver_)` | **public** vault, `payable`. Returns `(amount0, amount1)`. Emits `LogMint`. |
| `0xfcd3533c` | `burn(uint256 shares_, address receiver_)` | **public** vault. Emits `LogBurn`. |
| `0xe2bbb158` | `deposit(uint256 amount0_, uint256 amount1_)` | **private** vault, `payable`. Emits `LogDeposit`. |
| `0x00f714ce` | `withdraw(uint256 proportion_, address receiver_)` | **private** vault. Emits `LogWithdraw`. |
| `0xc4d66de8` | `initialize(address module_)` | one-shot, sets default module (selector coincides with OZ `initialize(address)`). |
| `0x2b1ba4f1` | `setModule(address module_, bytes[] payloads_)` | manager-only; switches active module. Emits vault `LogSetModule`. |
| `0x8d62cce2` | `whitelistModules(address[] beacons_, bytes[] data_)` | owner; creates module clones from beacons. |
| `0x951f1f09` | `blacklistModules(address[] modules_)` | |
| `0x70a08231`/`0xa9059cbb`/`0x095ea7b3` | ERC-20 `balanceOf`/`transfer`/`approve` | **public vaults only** (shares are ERC-20). |

### ArrakisStandardManager

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4302e56d` | `rebalance(address vault_, bytes[] payloads_)` | core management action. Emits `LogRebalance`. |
| `0xa9bf260c` | `setModule(address vault_, address module_, bytes[] payloads_)` | manager-side module switch. Emits manager `LogSetModule`. |

### ArrakisPublicVaultRouter

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x96006260` | `addLiquidity((uint256 amount0Max, uint256 amount1Max, uint256 amount0Min, uint256 amount1Min, uint256 amountSharesMin, address vault, address receiver))` | primary user entry to mint public-vault shares. |
| `0x543c520e` | `removeLiquidity((uint256 burnAmount, uint256 amount0Min, uint256 amount1Min, address vault, address receiver))` | |
| `0x1675b064` | `swapAndAddLiquidity(((bytes,uint256,uint256,address,bool),(uint256,uint256,uint256,uint256,uint256,address,address)))` | swap then add; emits `Swapped`. |

(There are also `*Permit2` and `wrap*` variants — same `AddLiquidityData`/`RemoveLiquidityData` structs wrapped with Permit2/WETH.)

### Guardian

| Selector | Signature |
|----------|-----------|
| `0x2d88af4a` | `setPauser(address newPauser_)` |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` (modules/factory/router honor the guardian's pause) |

---

## Addresses

> **CREATE3 — the SAME address on every chain.** All singleton infra below carries one address across chains. **But presence is per-chain** — `eth_getCode` ✓/`0x` marks below are live (2026-06-04). **Nothing in Arrakis Modular is deployed on Avalanche C-Chain (43114)** — every address returns `0x` there. Disambiguate chains by `chain_id`, never by address.

### Singleton infrastructure (one CREATE3 address; per-chain presence noted)

| Role | Address | ETH (1) | Base (8453) | Arb (42161) | OP (10) | Poly (137) | BNB (56) | Avax (43114) |
|------|---------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **ArrakisMetaVaultFactory** | `0x820FB8127a689327C863de8433278d6181123982` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `0x` |
| **ArrakisStandardManager** (proxy) | `0x2e6E879648293e939aA68bA4c6c129A1Be733bDA` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `0x` |
| **Guardian** | `0x6F441151B478E0d60588f221f1A35BcC3f7aB981` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `0x` |
| **TimeLock** | `0xAf6f9640092cB1236E5DB6E517576355b6C40b7f` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | `0x` |
| **ArrakisPublicVaultRouter** | `0x72aa2C8e6B14F30131081401Fa999fC964A66041` | ✓ | ✓ | ✓ | `0x` | `0x` | `0x` | `0x` |
| **RouterSwapExecutor** | `0x19488620Cdf3Ff1B0784AC4529Fb5c5AbAceb1B6` | ✓ | ✓¹ | ✓¹ | `0x` | `0x` | `0x` | `0x` |
| **RouterSwapResolver** | `0xC6c53369c36D6b4f4A6c195441Fe2d33149FB265` | ✓¹ | ✓¹ | ✓¹ | `0x` | `0x` | `0x` | `0x` |
| **ModulePublicRegistry** | `0x791d75F87a701C3F7dFfcEC1B6094dB22c779603` | ✓ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | `0x` |
| **ModulePrivateRegistry** | `0xe278C1944BA3321C1079aBF94961E9fF1127A265` | ✓ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | `0x` |
| **Private-Vault NFT** (PrivateVaultNFT) | `0x44A801e7E2E073bd8bcE4bCCf653239Fa156B762` | ✓ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | `0x` |
| **RendererController** | `0x1Cc0Adff599F244f036a5C2425f646Aef884149D` | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | `0x` |
| **Pauser** | `0x700a1cdA1495C1B34c4962e9742A8A8832aAc03A` | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | `0x` |
| **MigrationHelper** | `0xd61407B9B63956CfB61341AAfeFbD7EDA1F9B962` | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | `0x` |
| **Withdraw Helper** | `0x3a2e9c26fBB53990BAFAec0342e38bd2a06f46d3` | ✓ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | ✓¹ | `0x` |

> **Module beacons (not exhaustively listed above):** beyond the Uniswap V4 and Valantis HOT modules, the official deployments page also lists **Uniswap V3**, **PancakeSwap (Infinity on BNB + V3)**, and **Aerodrome Slipstream** (Base-only; Staked/Fees variants) module beacons, each with per-chain addresses. Spot-verified code-present: UniV3 beacon (Base) `0x82c0a11A…`, Pancake-Infinity beacon (BNB) `0x741d420e…`, Aerodrome-Slipstream-V3-staked beacon (Base) `0x568336B9…`. A complete monitor should enumerate the module beacons from the deployments page per chain. The **active venue events** (swaps/LP) come from each module's underlying pool (UniV4 `PoolManager`, Valantis `SovereignPool`, UniV3/Pancake pool, Aerodrome pool) — see §Detection invariants.

✓ = `eth_getCode` non-empty, directly verified here. ✓¹ = CREATE3 same-address contract from the official deployments page, code-verified on Ethereum here; presence on the other chains follows the CREATE3 deployment set in the docs (re-check `eth_getCode` per chain before relying on it for a specific chain). The **Factory / Manager / Guardian / TimeLock / Router** ✓ marks are all from direct per-chain `eth_getCode` in this pass.

> The official deployments page lists Modular as live on Mainnet, Base, Arbitrum, BNB, Plasma, Optimism, Polygon, Ink, Unichain, Sepolia. **Avalanche is not in that set** (confirmed `0x` on-chain here). **Ink / Unichain / Plasma / Sepolia are out of scope** for this file.

**CREATE3 shared-address claim — CONFIRMED, with a nuance.** The factory address `0x820F…3982` is identical and code-present on ETH/Base/Arb/OP/Poly/BNB (absent on Avax). Bytecode is **byte-identical across ETH = Base = Arbitrum** (`keccak`/sha256 of `eth_getCode` matches), **identical across OP = Polygon** (a different build), and **slightly different on BNB** (different size). So the *address* is CREATE3-deterministic and shared, but the *deployed bytecode* is not byte-identical on every chain (different compiler/immutable batches per deployment wave) — the address determinism is what CREATE3 guarantees, not bytecode equality. Same pattern holds for the Manager and Guardian.

### Module beacons (chain-specific addresses — NOT CREATE3-shared)

Modules are deployed per chain and have **different beacon addresses on each chain.** The authoritative per-chain list is whatever the two registries whitelist on that chain — read it live:
- `ModulePublicRegistry.beacons() → address[]` and `ModulePrivateRegistry.beacons() → address[]`.

Ethereum (verified live):
| Registry | Beacon | Beacon `implementation()` | Likely module type |
|----------|--------|---------------------------|--------------------|
| Public | `0xE973Cf1e347EcF26232A95dBCc862AA488b0351b` | `0x9Ac1249E37EE1bDc38dC0fF873F1dB0c5E6aDdE3` | Valantis HOT public module |
| Public | `0xFf0474792DEe71935a0CeF1306D93fC1DCF47BD9` | `0xfaD5730Ade9560B8C353A717faB159f85B1b9F2f` | Uniswap V4 public module |
| Private | `0xFf0474792DEe71935a0CeF1306D93fC1DCF47BD9` | `0xfaD5730Ade9560B8C353A717faB159f85B1b9F2f` | (shared) |
| Private | `0x98e373368C3934dc220eEE8645E62f6558687bc5` | `0x7E2fc9b2D37EA3E771b6F2375915b87CcA9E55bc` | module impl |
| Private | `0x022a0C7dc85Fc3fF81f9f8Ef65Ae2813A062F556` | `0x04eAd25447F9371c5c1e2C33645f32aAFEb337dc` | **Uniswap V4 private module** (matches docs) |
| Private | `0x1436877899273D748eb433eFd6C437e37D627255` | `0x49083CB8204C5bF830c75fd65D8Eb3bE1c3d4b11` | module impl |
| Private | `0xdf4975A3515168f8c446aD4a2E974B89c64b6A38` | `0x8c02839bAbF7788D9D7043614B2F85cDD8acE35E` | module impl |

Per-chain Uniswap V4 **private** module beacon (from the docs deployments page; private impl `0x04eAd25447F9371c5c1e2C33645f32aAFEb337dc`):
| Chain | UniV4 private beacon |
|-------|----------------------|
| Ethereum | `0x022a0C7dc85Fc3fF81f9f8Ef65Ae2813A062F556` |
| Base | `0x97d42db1b71b1c9a811a73ce3505ac00f9f6e5fb` |
| Arbitrum | `0xe1a76410dfB11d6C60a43838FA853519f13dEef4` |
| BNB | `0xc0b7fac163566a768b4f30d06fd4b08bb6b987f0` |
| Optimism | `0x413fc8E6F0B95D1f45de01b17e9441ec41eD01AB` |
| Polygon | `0xfb4e25800b77bcd09227729ffcc145685797f408` |

> Do **not** hardcode a module beacon — read the registry on the target chain. The beacons are `UpgradeableBeacon`s owned by the TimeLock (`0xAf6f9640…`); the TimeLock upgrading a beacon swaps the module logic for every vault using it.

### Vault instances

Vaults are **not** at deterministic shared addresses — each is CREATE3-deployed by the factory with a per-vault salt. Enumerate via the factory (`publicVaults`/`privateVaults`/`numOf*`) or the creation events. Ethereum sample (live): public vaults `0xf790870ccF6aE66DdC69f68e6d05d446f1a6ad83`, `0xAdB8a6A0279F50c54cd1a3b5C6BBfCC2094D6338`; a private vault `0x65DA1218186399862C815e62A92DA66a2a8d3489` (factory reports 2 public, 112 private on Ethereum).

---

## Proxies

| Contract | Pattern | Evidence |
|----------|---------|----------|
| **ArrakisMetaVaultFactory** | **Immutable** (full deploy, not a proxy) | EIP-1967 impl slot `0x3608…bbc` reads `0x0`. |
| **ArrakisPublicVaultRouter** | **Immutable** | impl slot `0x0`. |
| **Guardian / TimeLock / registries** | **Immutable** | not proxies. |
| **ArrakisStandardManager** | **ERC-1967 upgradeable proxy** | impl slot `0x3608…bbc` = `0x85881de0eFab6a902C9Ff17C47C6E08C0Ab9FDB3` (the logic); admin slot `0xb531…6103` = `0xAf6f9640092cB1236E5DB6E517576355b6C40b7f` (= **TimeLock**). So the manager logic is upgradeable by the TimeLock. |
| **Meta-vaults (public & private)** | **Full instances**, not proxies | impl slot `0x0` and beacon slot `0xa3f0…3d50` both `0x0` on sampled vaults. They are CREATE3-deployed concrete contracts. |
| **Modules** | **BeaconProxy (EIP-1967 beacon)** | sampled vault's `module()` has beacon slot `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50` set (public vault module → beacon `0xE973Cf1e…`; private vault module → beacon `0x022a0C7d…`). Module impl resolves via `beacon.implementation()`. Beacons are `UpgradeableBeacon` owned by the TimeLock. |

Slots used: EIP-1967 implementation `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; EIP-1967 admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`; EIP-1967 beacon `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50`.

---

## Detection invariants & gotchas

1. **Public ≠ Private.** A public vault is an **ERC-20** (shares transferable; `mint`/`burn`/`LogMint`/`LogBurn`; router-served `addLiquidity`). A private vault is **NFT-owned** with whitelisted depositors (`deposit`/`withdraw`/`LogDeposit`/`LogWithdraw`). They are created by `deployPublicVault` vs `deployPrivateVault` and emit `LogPublicVaultCreation` vs `LogPrivateVaultCreation`. Classify any address with `factory.isPublicVault` / `isPrivateVault`.
2. **The vault is not where the swaps happen.** Real AMM swap/LP events come from the **module's underlying venue** — e.g. a Uniswap V4 `PoolManager` `Swap`/`ModifyLiquidity`, or a Valantis `SovereignPool`. The vault only emits accounting events (`LogMint`/`LogBurn`/`LogDeposit`/`LogWithdraw`/`LogSetModule`) and the manager emits `LogRebalance`. To see liquidity actually move, follow `vault.module()` → its venue, and correlate in the same tx.
3. **Multiple same-named events with different topic0.** `LogSetManager` exists as factory 2-arg (`0x496dcec0…`) and vault 1-arg (`0x9b6ffaf4…`). `LogSetModule` exists as vault 2-arg (`0x098a4cb3…`) and manager 3-arg (`0x67cc0d0f…`). `LogWithdraw` exists as private-vault 3-arg (`0x3228bf4a…`) and module 4-arg (`0x9744d0a1…`). `LogWithdrawManagerBalance` exists as vault/module 2-arg (`0xa292e28c…`) and manager 4-arg (`0x728744d6…`). Match on the **emitting contract** + topic0, not the name.
4. **CREATE3 = same address, presence differs.** Disambiguate chains by `chain_id`. The **router stack is only on ETH/Base/Arbitrum**; the factory/manager/guardian/timelock are on those six chains; **Avalanche has none of it** (`0x`).
5. **CREATE3 ≠ byte-identical bytecode.** The factory address is shared, but its deployed bytecode differs between deployment waves (ETH/Base/Arb one build, OP/Poly another, BNB another). Verify by address + presence, not bytecode hash equality.
6. **Manager is upgradeable; everything else core is immutable.** The manager is an ERC-1967 proxy whose admin is the TimeLock; the factory/router/guardian are not proxies. Module logic upgrades happen at the **beacon** (TimeLock-owned), affecting all vaults on that beacon at once.
7. **Don't hardcode module beacons.** Read `ModulePublicRegistry.beacons()` / `ModulePrivateRegistry.beacons()` per chain — beacon addresses are chain-specific.
8. **This is Modular, not Arrakis V2.** The older PALM/`ArrakisV2` vault generation (`ArrakisV2Factory`, `RouterSwapResolver` of V2, Gelato-managed) is a different deployment set — don't conflate the addresses.
9. Bytea hex literals: 40 chars for addresses, 64 for topics.

---

## Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics — Factory =====
TOPIC_LOG_PUBLIC_VAULT_CREATION  = '\x78a30a2797e72cead59a8694c4281e40afe75b46a6362a880ec46771845e3020'
TOPIC_LOG_PRIVATE_VAULT_CREATION = '\x15509c43e33ed1fab25841b16998c22b4ed073f627883f1131d2e1b870df129a'
TOPIC_FACTORY_WHITELIST_DEPLOYERS= '\x90ccec5da4c6ba39e2d222eac064da2aba3b61461ffba1a355efa99b7947f489'
TOPIC_FACTORY_BLACKLIST_DEPLOYERS= '\x3107f5bbb8b23b80602a19bab111c1528df45fc0ab255fca51a6ff0fc0595438'
TOPIC_FACTORY_SET_MANAGER        = '\x496dcec0646703aaf2a371dc4b30ec9dac72703c05676629678af06149de3dc7'
-- ===== Topics — Public vault (ERC-20) =====
TOPIC_VAULT_LOG_MINT             = '\xb95558c5fa26a0093cddc7ad7eb438c0475c3d69925f02e8787c72661472ad90'
TOPIC_VAULT_LOG_BURN             = '\x97a53db416643aef28847c991d7cd62b34c7579f1d86acbba5c7dd64cc0d1584'
-- ===== Topics — Private vault (NFT) =====
TOPIC_VAULT_LOG_DEPOSIT          = '\x1f38c0b96f5f251e5fb679ab3fb88695fb7ed9698d9d13fa8599de3bf0fd6479'
TOPIC_VAULT_LOG_WITHDRAW_PRIV    = '\x3228bf4a0d547ed34051296b931fce02a1927888b6bc3dfbb85395d0cca1e9e0'
TOPIC_VAULT_WHITELIST_DEPOSITORS = '\x5c9265672925c5544e4d535af6d0684ea57e4cd95c7e707253c189c37de03c59'
TOPIC_VAULT_BLACKLIST_DEPOSITORS = '\xb0cb71a9d9fcb2642936172f746fc80597811e946a534ba1b0e218963a2f2f02'
-- ===== Topics — Meta-vault base =====
TOPIC_VAULT_SET_MODULE           = '\x098a4cb3597f0b783d955415cf1025a9452365cac4dcddca246a394e73cca90a'
TOPIC_VAULT_SET_FIRST_MODULE     = '\xc36d7d831827b79e3044eab60b0e78bcbddb1e832fdd0e848aa633471f7a2dce'
TOPIC_VAULT_SET_MANAGER          = '\x9b6ffaf4cbfd923495440b7f17ced9394289f001b3ead53ab67e2c3f3e39b0f5'
TOPIC_VAULT_WHITELISTED_MODULES  = '\x0936fa8fc79e7acdb2f5db0618a6355fdda409b0e5b17e3be004be15bcf4c884'
TOPIC_VAULT_WHITELISTED_MODULE   = '\xf2b7116a60dcb1f53337287d3735fc1ac1b053cc3fd07d605588cc1a879c0df0'
TOPIC_VAULT_BLACKLISTED_MODULES  = '\xbb08f8051cd2fa9d17f2636a7cf104cf87e85218c2a9061b0ade4fc5d013f328'
TOPIC_VAULT_WD_MANAGER_BALANCE   = '\xa292e28c648da34e20b372054caab5f0359198b3b4d5f0ef9945d4616e15dc97'
-- ===== Topics — Manager =====
TOPIC_MGR_REBALANCE              = '\x38d3829a837b9e8af9587ec40ba2729f1f3679f831777bb639da59a461804360'
TOPIC_MGR_SET_MODULE             = '\x67cc0d0f05e6986c474f5f7f95318cf6437b628440f79711ef957794b7cffd2e'
TOPIC_MGR_SET_MGMT_PARAMS        = '\x848acd7079af2a323ca6b8a860068c114673abe038a880b126bf280c26032c04'
TOPIC_MGR_SET_VAULT_DATA         = '\x61e2dc30785ffbd4d4635970197d44198b53c094ab495368058abd0f0a0710ee'
TOPIC_MGR_SET_VAULT_STRAT        = '\x7bb963426cf1af62285b13e10f2d60df9cec9ca0d85c18c6cd2c27d7e347fbda'
TOPIC_MGR_CHANGE_MANAGER_FEE     = '\x0b5f5d3af5972fc5e91f5b56d613f5711e187bd70056693a629e24d323edb160'
TOPIC_MGR_WD_MANAGER_BALANCE     = '\x728744d665a5895cc6a2585bbc6b265e8bda77d245f5311ec92f8ca48caeac3e'
TOPIC_MGR_SET_FACTORY            = '\x68ec1681f33885e64cf3268f285f4789bd226f23a394700823d46105a1c03e81'
-- ===== Topics — Module base =====
TOPIC_MODULE_LOG_WITHDRAW        = '\x9744d0a120f7c7d7906cfe3c05b50669fb49aa6d778b099d5d6edc386dee5b59'
TOPIC_MODULE_SET_MGR_FEE_PIPS    = '\x5b5a6a8527892eb1e879279ea1addd664eef55099889d3fe13e926a5fd7c3605'
-- ===== Topics — Router / Guardian =====
TOPIC_ROUTER_SWAPPED             = '\x79ee3df02fcb86d2989c21c1a792c528d6c4f38c0ad427eec754c8096b020606'
TOPIC_GUARDIAN_SET_PAUSER        = '\x6980d5b2e749d15ffa2ae3cd57c4c552f4d4b8fc0942e00316d39219d51aec79'

-- ===== Selectors =====
SEL_DEPLOY_PUBLIC_VAULT          = '\xa2eb3521'
SEL_DEPLOY_PRIVATE_VAULT         = '\x19b56b8b'
SEL_FACTORY_SET_MANAGER          = '\xd0ebdbe7'
SEL_VAULT_MINT                   = '\x94bf804d'   -- public mint(uint256,address)
SEL_VAULT_BURN                   = '\xfcd3533c'   -- public burn(uint256,address)
SEL_VAULT_DEPOSIT                = '\xe2bbb158'   -- private deposit(uint256,uint256)
SEL_VAULT_WITHDRAW               = '\x00f714ce'   -- private withdraw(uint256,address)
SEL_VAULT_SET_MODULE             = '\x2b1ba4f1'
SEL_VAULT_WHITELIST_MODULES      = '\x8d62cce2'
SEL_MGR_REBALANCE                = '\x4302e56d'
SEL_MGR_SET_MODULE               = '\xa9bf260c'
SEL_ROUTER_ADD_LIQUIDITY         = '\x96006260'
SEL_ROUTER_REMOVE_LIQUIDITY      = '\x543c520e'
SEL_ROUTER_SWAP_ADD_LIQUIDITY    = '\x1675b064'
SEL_GUARDIAN_SET_PAUSER          = '\x2d88af4a'

-- ===== Addresses (CREATE3 — SAME on every chain; presence per-chain, see table) =====
ARRAKIS_META_VAULT_FACTORY       = '\x820fb8127a689327c863de8433278d6181123982'
ARRAKIS_STANDARD_MANAGER         = '\x2e6e879648293e939aa68ba4c6c129a1be733bda'  -- ERC1967 proxy; impl 0x85881de0..., admin = TimeLock
ARRAKIS_GUARDIAN                 = '\x6f441151b478e0d60588f221f1a35bcc3f7ab981'
ARRAKIS_TIMELOCK                 = '\xaf6f9640092cb1236e5db6e517576355b6c40b7f'
ARRAKIS_PUBLIC_VAULT_ROUTER      = '\x72aa2c8e6b14f30131081401fa999fc964a66041'  -- ETH/Base/Arb only
ARRAKIS_ROUTER_SWAP_EXECUTOR     = '\x19488620cdf3ff1b0784ac4529fb5c5abaceb1b6'
ARRAKIS_ROUTER_SWAP_RESOLVER     = '\xc6c53369c36d6b4f4a6c195441fe2d33149fb265'
ARRAKIS_MODULE_PUBLIC_REGISTRY   = '\x791d75f87a701c3f7dffcec1b6094db22c779603'
ARRAKIS_MODULE_PRIVATE_REGISTRY  = '\xe278c1944ba3321c1079abf94961e9ff1127a265'
ARRAKIS_PRIVATE_VAULT_NFT        = '\x44a801e7e2e073bd8bce4bccf653239fa156b762'
ARRAKIS_RENDERER_CONTROLLER      = '\x1cc0adff599f244f036a5c2425f646aef884149d'
ARRAKIS_PAUSER                   = '\x700a1cda1495c1b34c4962e9742a8a8832aac03a'  -- not on Sepolia
ARRAKIS_MIGRATION_HELPER         = '\xd61407b9b63956cfb61341aafefbd7eda1f9b962'  -- not on Sepolia
-- Module beacons are chain-specific — read registries .beacons() per chain; e.g. Ethereum UniV4 private beacon:
ARRAKIS_UNIV4_PRIV_BEACON_ETH    = '\x022a0c7dc85fc3ff81f9f8ef65ae2813a062f556'

-- ===== Proxy slots =====
SLOT_EIP1967_IMPL                = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
SLOT_EIP1967_ADMIN               = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
SLOT_EIP1967_BEACON              = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'
```

---

## Verification & sources

How every constant here was verified (2026-06-04):

- **Topic0 / selector hashes:** computed locally as `keccak256(canonical signature)` / `[0:4]` (`cast keccak` / `cast sig`). Canonical signatures read verbatim from the `ArrakisFinance/arrakis-modular` Solidity interfaces: `IArrakisMetaVaultFactory.sol`, `IArrakisMetaVault.sol`, `IArrakisMetaVaultPublic.sol`, `IArrakisMetaVaultPrivate.sol`, `IArrakisStandardManager.sol`, `IArrakisLPModule.sol`, `IArrakisPublicVaultRouter.sol`, `IGuardian.sol`, and `structs/SRouter.sol` (for the router struct tuples).
- **Live topic0 confirmation:** `eth_getLogs` on the factory `0x820F…3982` (Ethereum, blocks 25236489/25236497) returned `topics[0] = 0x15509c43e33ed1fab25841b16998c22b4ed073f627883f1131d2e1b870df129a` — byte-for-byte the computed `LogPrivateVaultCreation`, with the indexed `creator` as the only topic (matching the single `indexed` arg). This validates the signature-hashing methodology for the whole factory event set. Example creation tx: `0x515b7cdd820d31a2153c777b42f14d10c092f4f12bdd86c2bb7f3ce351df65ba`.
- **Factory wiring:** `factory.manager()` = `0x2e6E8796…733bDA` (= the Manager in the table); `factory.moduleRegistryPublic()` = `0x791d75F8…779603`; `factory.moduleRegistryPrivate()` = `0xe278C194…127A265`; `numOfPublicVaults()` = 2, `numOfPrivateVaults()` = 112 (Ethereum).
- **Addresses — code presence:** `eth_getCode` on `ethereum/base/bsc/avalanche-c-chain/arbitrum-one/optimism/polygon-bor` publicnode RPCs. Factory/Manager/Guardian/TimeLock present on ETH/Base/Arb/OP/Poly/BNB and **absent (`0x`) on Avalanche**. Router present on ETH/Base/Arbitrum only; **absent on BNB/OP/Polygon/Avalanche**. Factory bytecode is byte-identical on ETH=Base=Arbitrum (one build) and on OP=Polygon (another), and differs on BNB — i.e. CREATE3 gives the same address but not byte-identical code across all waves.
- **Proxy slots:** `eth_getStorageAt`. Manager impl slot = `0x85881de0eFab6a902C9Ff17C47C6E08C0Ab9FDB3`, admin slot = `0xAf6f9640…` (TimeLock) → ERC-1967 proxy. Factory/router impl slots = `0x0` (immutable). Sampled meta-vaults have impl & beacon slots `0x0` (full instances). Sampled vault modules have the EIP-1967 beacon slot set; `beacon.implementation()` and `beacon.owner()` (= TimeLock) read live.
- **Module beacons:** read live from `ModulePublicRegistry.beacons()` (2 beacons) and `ModulePrivateRegistry.beacons()` (5 beacons) on Ethereum; each beacon's `implementation()` resolved. Per-chain UniV4 private beacon table taken from the official deployments page.
- **Unconfirmed / flagged:**
  - `LogPublicVaultCreation` topic0 (`0x78a30a…`) is computed from source, **not** matched against a live emission (only 2 public vaults on Ethereum; their creation logs were not range-scanned here). The private creation topic0 *was* live-confirmed, and both come from the same interface, so confidence is high.
  - **ArrakisRoles** — the official deployments page does not publish an `ArrakisRoles` address, and it is absent from the (older) public source snapshot used here; it appears to be an internal roles/constants helper rather than a separately-addressed deployment. Treat as **unverified** — confirm against the live repo before using.
  - The module-beacon `implementation()` labels (which beacon = Valantis HOT vs UniV4) are inferred from the docs' UniV4 private impl (`0x04eAd254…`) matching one private beacon; the other private/public beacon labels are best-effort — verify per chain.
  - ✓¹ presence marks (registries, NFT, executor/resolver, renderer, pauser, migration helper on non-Ethereum chains) follow the docs' CREATE3 set and were code-verified on Ethereum only in this pass; re-check `eth_getCode` on the specific chain before relying on them there.

- **Authoritative sources:** [Arrakis Modular deployments page](https://docs.arrakis.finance/text/arrakisModular/deployments.html) · `ArrakisFinance/arrakis-modular` Solidity interfaces (source for all signatures) · explorers: [Etherscan](https://etherscan.io/address/0x820FB8127a689327C863de8433278d6181123982) / [BaseScan](https://basescan.org) / [Arbiscan](https://arbiscan.io) / [Optimistic Etherscan](https://optimistic.etherscan.io) / [PolygonScan](https://polygonscan.com) / [BscScan](https://bscscan.com).

### Independent fact-check (2026-06) — confirmed, additions folded in
Cross-checked against the Arrakis Modular deployments page, GitHub, and live RPC. Verdicts:
1. **Factory `0x820FB81…3982` + all singleton addresses, CREATE3 same-address (6 target chains, `0x` Avalanche), router stack only ETH/Base/Arbitrum** — ✅ confirmed verbatim against the deployments page + live RPC.
2. **Manager = ERC-1967 proxy (admin = TimeLock); Factory/Guardian immutable; modules = TimeLock-owned BeaconProxy; meta-vaults delegate to module → events from the underlying venue** — ✅ confirmed (impl/admin slots read live).
3. **`LogPrivateVaultCreation` topic0 `0x15509c43…`** — ✅ live-confirmed; **`LogPublicVaultCreation`** remains computed-only (no public-vault creation in sampled window).
4. **Module set** — ➕ added: the deployments page also ships **Uniswap V3, PancakeSwap (Infinity/V3), and Aerodrome Slipstream** module beacons (not just UniV4/Valantis) — note + spot-verified beacons added above.
5. **Withdraw Helper `0x3a2e9c26…`** — ➕ added to the singleton table (5529B on ETH ✓).

**Net corrections folded in:** broader module-beacon set documented; Withdraw Helper added. No address corrections — all confirmed. (`ArrakisRoles` still has no published address — the `arrakis-modular` repo is private; left flagged.)

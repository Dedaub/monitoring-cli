# Fluid (Instadapp) — Liquidity Layer (core) — Topics, Selectors, Addresses

**Status:** verified against the canonical `Instadapp/fluid-contracts-public` (branch `main`) source and live RPC on every listed chain on 2026-05-29. All topic0/selector hashes computed locally with keccak; addresses confirmed via `eth_getCode`; proxy slots & per-selector dispatch confirmed via `eth_getStorageAt` / `eth_call`.
**Scope:** Fluid's **Liquidity Layer** — the single contract that custodies ALL protocol liquidity and through which every supply/borrow/withdraw/payback (from Vaults, Lending, and the DEX) settles — plus the InfiniteProxy that fronts it and the **FLUID** governance token. This is the **base file** the other Fluid modules reference: [`lending.md`](lending.md), [`vaults.md`](vaults.md), [`dex.md`](dex.md). On **Ethereum (1), Base (8453), Arbitrum One (42161), Polygon PoS (137), BNB Smart Chain (56)**.
**Key fact:** like Balancer's Vault, Fluid is **Liquidity-Layer-centric** — monitor the one Liquidity proxy per chain and its `LogOperate` event to capture nearly all balance changes across the whole protocol. Allow-listed protocols ("users", tracked per `_userClass`) interact through a single `operate(...)` entrypoint; every supply/withdraw/borrow/payback emits one `LogOperate`.

> **Not on Optimism (10) or Avalanche (43114).** The repo's `deployments/` has only `mainnet, arbitrum, base, polygon, bnb, plasma`; the Liquidity proxy `0x52Aa…E497` has **no bytecode** on OP/Avax (verified). Any "Fluid on Optimism/Avalanche/Fantom" claim refers to legacy Instadapp DSA/Avocado infra, not the Fluid Liquidity Layer.
> **BNB IS live** (some dashboards list only ETH/Arb/Base/Polygon): Liquidity proxy has bytecode with active `LogOperate` traffic — verified here on-chain. `plasma` also exists in the repo (out of scope). Treat on-chain evidence as authoritative over dashboard listings.

**Versioning:** the Liquidity Layer is one continuously-governed InfiniteProxy that evolves by swapping per-selector implementation modules (`LogSetImplementation`/`LogRemoveImplementation`), never by redeploying the proxy. The repo's `deployments/<chain>/v1_0_0/` and mainnet `v1_1_0/` are deploy-batch snapshots, not protocol versions (`v1_1_0` mainnet = oracle deployments only).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Liquidity Layer — UserModule (the workhorse; one per supply/withdraw/borrow/payback)

| topic0 | Event |
|--------|-------|
| `0x4d93b232a24e82b284ced7461bf4deacffe66759d5c24513e6f29e571ad78d15` | `LogOperate(address indexed user, address indexed token, int256 supplyAmount, int256 borrowAmount, address withdrawTo, address borrowTo, uint256 totalAmounts, uint256 exchangePricesAndConfig)` |

`supplyAmount > 0` = deposit, `< 0` = withdrawal; `borrowAmount > 0` = borrow, `< 0` = payback. `user` is the *protocol* that triggered it (an fToken for Lending, or the Vault) — never the end user. `token` is the underlying asset. `totalAmounts` / `exchangePricesAndConfig` are bit-packed storage slots (decoded by `FluidLiquidityResolver` / the Fluid `BigMath` packing layout).

### 1.2 Liquidity Layer — AdminModule (governance / config; tuple args expanded for keccak)

| topic0 | Event |
|--------|-------|
| `0xb694cde8b4bf47e7f5845bb4374f98c5b29bbbaa5208ea679121cecb5d8fd3e0` | `LogUpdateAuths((address,bool)[] authsStatus)` |
| `0x530db3bf9b4b0c4f296fe1d9e21620b91db0a8bdcaca4cf1e6dc9844739405c1` | `LogUpdateGuardians((address,bool)[] guardiansStatus)` |
| `0xde3dd47a9a762713b4a9813a037ab6f57e36569d8b0ec4ddb285d8a61878b5b4` | `LogUpdateRevenueCollector(address indexed revenueCollector)` |
| `0xb33384c8a450936b9fba178db857f03fb9865a40d166aa2f9d439a9fdddfbe22` | `LogChangeStatus(uint256 indexed newStatus)` (pause / unpause) |
| `0x9ccbc3483d75ae36da94213ac30ac0a047e1226ef3435d004cd501608e5b388b` | `LogUpdateUserClasses((address,uint256)[] userClasses)` |
| `0xa9d5be7e168dc43b637b924e6cc22c262478dffd9d475fa170b6d4e4ba576460` | `LogUpdateTokenConfigs((address,uint256,uint256,uint256)[] tokenConfigs)` `{token,fee,threshold,maxUtilization}` |
| `0x614e3525ec8c152da9319cd9038950346a4a042d3c6810a7f3ffddc34347bdb0` | `LogUpdateUserSupplyConfigs((address,address,uint8,uint256,uint256,uint256)[])` `{user,token,mode,expandPercent,expandDuration,baseWithdrawalLimit}` |
| `0x4a3d512075def8d38b63e79dacfdab217654f641be2b2f7d638b67b2515df7c0` | `LogUpdateUserBorrowConfigs((address,address,uint8,uint256,uint256,uint256,uint256)[])` `{user,token,mode,expandPercent,expandDuration,baseDebtCeiling,maxDebtCeiling}` |
| `0x6686e5bb0cc56cbc9aa2b434eb18009891bf411d6d3f961fdfe70be336ca4528` | `LogPauseUser(address user, address[] supplyTokens, address[] borrowTokens)` |
| `0xacd30ef49b8fd1b51bbefff95071c5b0257180a7778c9c0fa4eb77a8842e290d` | `LogUnpauseUser(address user, address[] supplyTokens, address[] borrowTokens)` |
| `0x1f953465aa7f3f2478d38b6c2a9cfcfbda846398254e278f614d586d527d902c` | `LogUpdateRateDataV1s((address,uint256,uint256,uint256,uint256)[])` `{token,kink,rateAtUtilizationZero,...Kink,...Max}` |
| `0xf96f9120f802331b6220bac68c2ab90cce6c8a8f9fed548d72dd092ad1899bf9` | `LogUpdateRateDataV2s((address,uint256,uint256,uint256,uint256,uint256,uint256)[])` `{token,kink1,kink2,...Zero,...Kink1,...Kink2,...Max}` |
| `0x7ded56fbc1e1a41c85fd5fb3d0ce91eafc72414b7f06ed356c1d921823d4c37c` | `LogCollectRevenue(address indexed token, uint256 indexed amount)` |
| `0x96c40bed7fc8d0ac41633a3bd47f254f0b0076e5df70975c51d23514bc49d3b8` | `LogUpdateExchangePrices(address indexed token, uint256 indexed supplyExchangePrice, uint256 indexed borrowExchangePrice, uint256 borrowRate, uint256 utilization)` |
| `0xbd618a42c279f25a1d0dd6144f1a1b2ded22549073604bb0774cff6a99ee8428` | `LogUpdateUserWithdrawalLimit(address user, address token, uint256 newLimit)` |

> Struct-array event args were hashed with the tuple types **expanded** (e.g. `LogUpdateAuths((address,bool)[])`). Using the Solidity struct name instead of the expanded tuple gives a wrong topic0.

### 1.3 InfiniteProxy (emitted by FluidLiquidityProxy and any other Fluid InfiniteProxy)

| topic0 | Event |
|--------|-------|
| `0xb2396a4169c0fac3eb0713eb7d54220cbe5e21e585a59578ec4de929657c0733` | `LogSetAdmin(address indexed oldAdmin, address indexed newAdmin)` |
| `0x761380f4203cd2fcc7ee1ae32561463bc08bbf6761cb9d5caa925f99a6d54502` | `LogSetDummyImplementation(address indexed oldDummyImplementation, address indexed newDummyImplementation)` |
| `0xd613a4a18e567ee1f2db4d5b528a5fee09f7dff92d6fb708afd6c095070a9c6d` | `LogSetImplementation(address indexed implementation, bytes4[] sigs)` |
| `0xda53aaefabec4c3f8ba693a2e3c67fa0152fbd71c369d51f669e66b28a4a0864` | `LogRemoveImplementation(address indexed implementation)` |

---

## 2. Function signatures (chain-agnostic)

### 2.1 Liquidity Layer (UserModule + InfiniteProxy admin/getters)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xad967e15` | `operate(address token, int256 supplyAmount, int256 borrowAmount, address withdrawTo, address borrowTo, bytes callbackData)` | Sole user entrypoint, callable only by authorized protocols (vaults/fTokens/dex). Returns `(uint256, uint256)`. Emits `LogOperate`. Live dispatch → UserModule (read it, don't assume). |
| `0x6e9960c3` | `getAdmin()` | proxy admin (governance). |
| `0x908bfe5e` | `getDummyImplementation()` | the EIP-1967-impl-slot value (ABI stub). |
| `0xa5fcc8bc` | `getSigsImplementation(bytes4 sig_)` | **the authoritative selector→implementation lookup.** |
| `0x89396dc8` | `getImplementationSigs(address impl_)` | `bytes4[]` registered for an impl. |
| `0xb5c736e4` | `readFromStorage(bytes32 slot_)` | raw `sload`. |
| `0x704b6c02` | `setAdmin(address)` | onlyAdmin. Emits `LogSetAdmin`. |
| `0xc39aa07d` | `setDummyImplementation(address)` | onlyAdmin. |
| `0xf0c01b42` | `addImplementation(address, bytes4[])` | onlyAdmin. Emits `LogSetImplementation`. |
| `0x22175a32` | `removeImplementation(address)` | onlyAdmin. Emits `LogRemoveImplementation`. |

Reads go through periphery resolver contracts (`FluidLiquidityResolver`), not the core.

---

## 3. Addresses

### 3.1 Core — shared across all Fluid chains (deterministic CREATE3)

Identical on **Ethereum, Base, Arbitrum, Polygon, BNB** (verified `eth_getCode` non-empty on each). Per-chain divergence (modules, dummy impl, admin) is in §4.

| Role | Address | One-liner |
|------|---------|-----------|
| **Liquidity (FluidLiquidityProxy)** | `0x52Aa899454998Be5b000Ad077a46Bbe360F4e497` | Core Liquidity Layer (InfiniteProxy). All Lending/Vault/DEX liquidity routes through it. `code=4462 B` on every chain. |
| **FluidLiquidityResolver** | `0xca13A15de31235A37134B4717021C35A3CF25C60` | Decodes packed Liquidity storage. `code=12803 B`. |
| **RevenueResolver** | `0x0A84741D50B4190B424f57425b09FAe60C330F32` | Revenue/reserve read resolver. |
| ReserveContractProxy | `0x264786EF916af64a1DB19F513F24a3681734ce92` | Reserve & governance auth / revenue collector. Minimal proxy (`code=190 B`). |
| VaultFactory | `0x324c5Dc1fC42c7a4D43d92df1eBA58a54d13Bf2d` | Deploys Fluid Vaults — see [`vaults.md`](vaults.md). |
| DexFactory | `0x91716C4EDA1Fb55e84Bf8b4c7085f84285c19085` | Deploys Fluid DEX pools — see [`dex.md`](dex.md). |
| LendingFactory | `0x54B91A0D94cb471F37f949c60F7Fa7935b551D03` | Deploys fTokens — see [`lending.md`](lending.md). |

Deployer/owner (all chains): `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e`. Team/governance multisig (Liquidity constructor arg): `0xCA5E9219e1007931FD5d938C1815a90ef08f1584`.

### 3.2 FLUID governance token (per chain; not deterministic — verify on-chain)

| Chain | FLUID token |
|-------|-------------|
| Ethereum (1) | `0x6f40d4A6237C257fff2dB00FA0510DeEECd303eb` (`symbol()`="FLUID" ✓) |
| Arbitrum (42161) | `0x61e030a56d33e8260fdd81f03b162a79fe3449cd` (`symbol()`="FLUID" ✓) |
| Polygon (137) | ⚠️ no native FLUID token confirmed. `0xf50d05a1402d0adafa880d36050736f9f6ee7dee` (often listed) is the **legacy INST bridge**, not FLUID — on-chain `symbol()`="INST", `name()`="Instadapp (PoS)" (FxPortal-bridged mainnet INST). Confirm a native FLUID address on docs/explorer before using. |
| Base (8453) | bridged via Chainlink CCIP — confirm address on docs/explorer |

---

## 4. Per-chain Liquidity-Layer modules, dummy impl & admin

The proxy address is shared, but its **EIP-1967 dummy-impl slot, admin slot, and registered modules differ per chain** — read them live, don't assume. Values below verified via `eth_getStorageAt` / live `getSigsImplementation(operate)` on 2026-05-29.

| Chain | Proxy admin (governance) `getAdmin()` | DummyImpl (impl slot) | Live `operate` impl (UserModule) |
|-------|----------------------------------------|------------------------|----------------------------------|
| Ethereum (1) | `0x2386dc45added673317ef068992f19421b481f4c` | `0xcc331daf69752bece3dc98dbc63eacd5092266a2` | `0x4bdc8816f2f56914b66ebf3786d78872d3a73ab7` |
| Base (8453) | `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e` | `0xa57D7CeF617271F4cEa4f665D33ebcFcBA4929f6` | `0x3c06514287e74ede035d293362a2369bDa60E642` |
| Arbitrum (42161) | `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e` | `0xa57D7CeF617271F4cEa4f665D33ebcFcBA4929f6` | `0x3c06514287e74ede035d293362a2369bDa60E642` |
| Polygon (137) | `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e` | `0xa57D7CeF617271F4cEa4f665D33ebcFcBA4929f6` | `0x3c06514287e74ede035d293362a2369bDa60E642` |
| BNB (56) | `0x1c0fc15e0db6960a9a688dda8ee2cfdd54f45cc0` | `0x3560a1d1E9F30b61cd0E24349f7a23890f6261D9` | `0x3c06514287e74ede035d293362a2369bDa60E642` |

`0xa57D7CeF…4929f6` is the originally-deployed `LiquidityDummyImpl`. **Mainnet has since upgraded** its dummy impl to `0xcc331daf…` (its admin is also the governance multisig, not the deployer) — a signal that mainnet is the most-governed instance. AdminModule addresses from the deploy registry: ETH `0x53EFFA0e612d88f39Ab32eb5274F2fae478d261C`, Base/Arb `0x48eeDDF09565338B62126214c5a85E863C197e4D`, Polygon `0xb74EbF69fe16292df8943964507c59f99765AEd9`, BNB `0xE1CCc6E5FB4684Abb23b71ce6F44f76ffe3a33B0`. (Registry UserModule on mainnet `0x2e40…46aD` is stale vs the live `operate` impl `0x4bdc88…3ab7`.) Mainnet also has a `ZircuitTransferModule` `0x9191b9539DD588dB81076900deFDd79Cb1115f72`.

---

## 5. Proxies — the Fluid "InfiniteProxy" (read carefully)

`FluidLiquidityProxy` (and the Vault/DEX cores) use Fluid's **InfiniteProxy** (`contracts/infiniteProxy/proxy.sol`), a multi-implementation delegatecall router. So the Liquidity address has a small proxy bytecode (≈4.5 KB) and the real logic lives in implementation modules (UserModule = `operate`, AdminModule = config) it delegatecalls. **fTokens, the LendingFactory, resolvers and the RewardsRateModels are NOT proxies** — they are plain CREATE3/normal contracts.

**Slots (standard EIP-1967 — reused):**
- Admin: `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` (`keccak256("eip1967.proxy.admin")-1`).
- Dummy implementation: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (`keccak256("eip1967.proxy.implementation")-1`). **Holds only an ABI-stub "dummy" impl** so explorers can introspect — it is *not* what `delegatecall` actually targets.
- Per-selector base: `_SIG_SLOT_BASE = 0x000000003ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (the impl slot with the top 4 bytes zeroed). The implementation for a selector lives at `_SIG_SLOT_BASE | bytes4(selector)` (selector occupies the top 4 bytes).

**Dispatch:** `fallback()` reads `msg.sig`, ORs it into `_SIG_SLOT_BASE`, `sload`s the impl address from that slot, and `delegatecall`s it (reverts if zero). There is **no** central mapping struct — the selector→impl map *is* the storage layout.

**Read which impl serves a call:** `getSigsImplementation(bytes4)` (`0xa5fcc8bc`) — e.g. `getSigsImplementation(0xad967e15)` → UserModule. `getImplementationSigs(address)` (`0x89396dc8`) for the reverse. Tools that read the EIP-1967 impl slot to "find the logic" get the wrong contract for InfiniteProxies — use the per-selector slot instead. See `references/proxies.md` for general proxy detection.

---

## 6. Detection invariants & gotchas

1. **Watch `LogOperate` on the Liquidity proxy = the single highest-signal Fluid event.** Every Vault borrow/repay, fToken deposit/withdraw, and DEX liquidity change ultimately settles as a Liquidity `operate` → one `LogOperate`. This is the Fluid analogue of "watch the Balancer Vault."
2. **`supplyAmount` / `borrowAmount` are signed `int256`:** positive = supply added / borrow taken; negative = withdraw / payback. The sign disambiguates the action.
3. **`LogOperate.user` is the protocol, never the end user.** `user` is the fToken (Lending), the Vault (borrow), or the DEX pool — correlate with the per-protocol event ([`lending.md`](lending.md) / [`vaults.md`](vaults.md) / [`dex.md`](dex.md)) in the same tx to attribute to the end user. To attribute Liquidity flows to Lending specifically, map `LogOperate.user ∈ LendingFactory.allTokens()`.
4. **The Liquidity proxy address is identical on every Fluid chain** (`0x52Aa…E497`), but its admin, dummy impl, and live module set differ per chain — always resolve modules with `getSigsImplementation`, never hardcode a module address.
5. **`getDummyImplementation()` ≠ the executing implementation.** The EIP-1967 impl slot holds an ABI stub. Use the per-selector slot (§5).
6. `totalAmounts` and `exchangePricesAndConfig` are bit-packed (supply/borrow totals + rate config) — decode per the Fluid `BigMath`/packing layout (or via `FluidLiquidityResolver`) if you need amounts in token units.
7. **Fluid is not on Optimism or Avalanche.** Don't index `0x52Aa…E497` there — no code.
8. Bytea hex literals: 40 chars for addresses, 64 for topics.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics =====
-- Liquidity UserModule
TOPIC_LIQ_OPERATE                = '\x4d93b232a24e82b284ced7461bf4deacffe66759d5c24513e6f29e571ad78d15'
-- Liquidity AdminModule
TOPIC_ADMIN_UPDATE_AUTHS         = '\xb694cde8b4bf47e7f5845bb4374f98c5b29bbbaa5208ea679121cecb5d8fd3e0'
TOPIC_ADMIN_UPDATE_GUARDIANS     = '\x530db3bf9b4b0c4f296fe1d9e21620b91db0a8bdcaca4cf1e6dc9844739405c1'
TOPIC_ADMIN_UPDATE_REVENUE_COLL  = '\xde3dd47a9a762713b4a9813a037ab6f57e36569d8b0ec4ddb285d8a61878b5b4'
TOPIC_ADMIN_CHANGE_STATUS        = '\xb33384c8a450936b9fba178db857f03fb9865a40d166aa2f9d439a9fdddfbe22'
TOPIC_ADMIN_UPDATE_USER_CLASSES  = '\x9ccbc3483d75ae36da94213ac30ac0a047e1226ef3435d004cd501608e5b388b'
TOPIC_ADMIN_UPDATE_TOKEN_CONFIGS = '\xa9d5be7e168dc43b637b924e6cc22c262478dffd9d475fa170b6d4e4ba576460'
TOPIC_ADMIN_UPDATE_SUPPLY_CFG    = '\x614e3525ec8c152da9319cd9038950346a4a042d3c6810a7f3ffddc34347bdb0'
TOPIC_ADMIN_UPDATE_BORROW_CFG    = '\x4a3d512075def8d38b63e79dacfdab217654f641be2b2f7d638b67b2515df7c0'
TOPIC_ADMIN_PAUSE_USER           = '\x6686e5bb0cc56cbc9aa2b434eb18009891bf411d6d3f961fdfe70be336ca4528'
TOPIC_ADMIN_UNPAUSE_USER         = '\xacd30ef49b8fd1b51bbefff95071c5b0257180a7778c9c0fa4eb77a8842e290d'
TOPIC_ADMIN_UPDATE_RATE_DATA_V1  = '\x1f953465aa7f3f2478d38b6c2a9cfcfbda846398254e278f614d586d527d902c'
TOPIC_ADMIN_UPDATE_RATE_DATA_V2  = '\xf96f9120f802331b6220bac68c2ab90cce6c8a8f9fed548d72dd092ad1899bf9'
TOPIC_ADMIN_COLLECT_REVENUE      = '\x7ded56fbc1e1a41c85fd5fb3d0ce91eafc72414b7f06ed356c1d921823d4c37c'
TOPIC_ADMIN_UPDATE_EXCH_PRICES   = '\x96c40bed7fc8d0ac41633a3bd47f254f0b0076e5df70975c51d23514bc49d3b8'
TOPIC_ADMIN_UPDATE_USER_WD_LIMIT = '\xbd618a42c279f25a1d0dd6144f1a1b2ded22549073604bb0774cff6a99ee8428'
-- InfiniteProxy
TOPIC_PROXY_SET_ADMIN            = '\xb2396a4169c0fac3eb0713eb7d54220cbe5e21e585a59578ec4de929657c0733'
TOPIC_PROXY_SET_DUMMY_IMPL       = '\x761380f4203cd2fcc7ee1ae32561463bc08bbf6761cb9d5caa925f99a6d54502'
TOPIC_PROXY_SET_IMPL             = '\xd613a4a18e567ee1f2db4d5b528a5fee09f7dff92d6fb708afd6c095070a9c6d'
TOPIC_PROXY_REMOVE_IMPL          = '\xda53aaefabec4c3f8ba693a2e3c67fa0152fbd71c369d51f669e66b28a4a0864'

-- ===== Selectors =====
SEL_LIQ_OPERATE                  = '\xad967e15'
SEL_PROXY_GET_SIGS_IMPL          = '\xa5fcc8bc'
SEL_PROXY_GET_IMPL_SIGS          = '\x89396dc8'
SEL_PROXY_GET_ADMIN              = '\x6e9960c3'
SEL_PROXY_GET_DUMMY_IMPL         = '\x908bfe5e'
SEL_PROXY_READ_FROM_STORAGE      = '\xb5c736e4'

-- ===== Core addresses (ALL Fluid chains: ETH, Base, Arbitrum, Polygon, BNB) =====
FLUID_LIQUIDITY                  = '\x52aa899454998be5b000ad077a46bbe360f4e497'
FLUID_LIQUIDITY_RESOLVER         = '\xca13a15de31235a37134b4717021c35a3cf25c60'
FLUID_REVENUE_RESOLVER           = '\x0a84741d50b4190b424f57425b09fae60c330f32'
FLUID_RESERVE_CONTRACT_PROXY     = '\x264786ef916af64a1db19f513f24a3681734ce92'
FLUID_VAULT_FACTORY              = '\x324c5dc1fc42c7a4d43d92df1eba58a54d13bf2d'
FLUID_DEX_FACTORY                = '\x91716c4eda1fb55e84bf8b4c7085f84285c19085'
FLUID_LENDING_FACTORY            = '\x54b91a0d94cb471f37f949c60f7fa7935b551d03'
FLUID_DEPLOYER                   = '\x4f6f977acdd1177dcd81ab83074855ecb9c2d49e'
FLUID_TEAM_MULTISIG              = '\xca5e9219e1007931fd5d938c1815a90ef08f1584'

-- ===== FLUID governance token (per chain) =====
FLUID_TOKEN_ETH                  = '\x6f40d4a6237c257fff2db00fa0510deeecd303eb'  -- symbol()=FLUID
FLUID_TOKEN_ARB                  = '\x61e030a56d33e8260fdd81f03b162a79fe3449cd'  -- symbol()=FLUID
-- Polygon: no native FLUID token confirmed. 0xf50d05a1402d0adafa880d36050736f9f6ee7dee is the legacy INST bridge (symbol()=INST, name()="Instadapp (PoS)"), NOT FLUID.

-- ===== InfiniteProxy storage slots =====
SLOT_EIP1967_ADMIN               = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
SLOT_EIP1967_IMPL_DUMMY          = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
SLOT_SIG_BASE                    = '\x000000003ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 8. Verification & sources

How every constant here was verified (2026-05-29):

- **Topic0 / selector hashes:** computed locally as `keccak256(canonical signature)` / `[0:4]`. Canonical signatures taken verbatim from `Instadapp/fluid-contracts-public` (`main`): `contracts/infiniteProxy/events.sol`, `contracts/liquidity/userModule/events.sol`, `contracts/liquidity/adminModule/{events,structs}.sol`. Struct-array event args expanded to tuples before hashing.
- **Address bytecode existence:** `eth_getCode` non-empty on `ethereum-rpc.publicnode.com`, `base-rpc.publicnode.com`, `arbitrum-one-rpc.publicnode.com`, `polygon-bor-rpc.publicnode.com`, `bsc-rpc.publicnode.com` for the Liquidity proxy + resolvers (proxy 4462 B; LiquidityResolver 12803 B). FLUID `symbol()`="FLUID" verified on Ethereum.
- **Live topics:** `eth_getLogs` (address-scoped) confirmed `LogOperate` on the Liquidity proxy (ETH/BNB/Polygon).
- **Proxy slots & dispatch:** `eth_getStorageAt` for the EIP-1967 admin + dummy-impl slots (per-chain values in §4); `getSigsImplementation(0xad967e15)` returned the per-chain UserModule (ETH `0x4bdc88…`, others `0x3c0651…`), confirming the per-selector dispatch model.
- **Not on Optimism/Avalanche:** confirmed by absence of `deployments/optimism|avalanche` in the repo and no bytecode at `0x52Aa…E497` on either chain.

**Authoritative sources:**
- [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) — all source + `deployments/<chain>/v1_0_0/*.json` artifacts.
- [Fluid docs — contract addresses](https://docs.fluid.instadapp.io/contracts/contract-addresses.html).
- Explorers: Etherscan / BaseScan / Arbiscan / PolygonScan / BscScan for spot confirmation.

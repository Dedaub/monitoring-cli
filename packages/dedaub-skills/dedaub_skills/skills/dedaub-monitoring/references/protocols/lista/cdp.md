# Lista CDP (lisUSD) — Topics, Selectors, Addresses (BNB Chain)

**Status:** verified against live RPC on BNB Chain (56) and the canonical `lista-dao/lista-dao-contracts` repo (archived, still the deployed source) on 2026-10-30.
**Scope:** the lisUSD collateralised-debt-position stablecoin system. It is a MakerDAO DSS fork inherited from Helio Money (lisUSD was named HAY): `Interaction` (user entry point), `Vat`, `Spot`, `Jug`, `Dog`, `Clipper`, `Abaci`, `Vow`, `GemJoin`/`HayJoin`, the `lisUSD` token, the `Jar` staking pool, collateral providers (`HelioProvider`, `SlisBNBProvider`, …), the USDT `PSM` and the lisUSD flash minter. Topics and selectors are chain-agnostic. Addresses are network-specific.

Users never call `Vat` directly. Every deposit, borrow, repay and withdraw goes through **`Interaction`**, which calls `GemJoin.join` → `Vat.frob` → `HayJoin.exit`. `Vat` emits **no events**, so `Interaction` events are the position-level source of truth. Collateral types are `ilk`s (`bytes32`). Each ilk has its own `GemJoin`, `Clipper` and oracle.

All core contracts are OZ v4 TransparentUpgradeableProxies (2141 B) behind the shared ProxyAdmin `0x1fa3e4718168077975ff4039304cc2e19ae58c4c`. Newer collateral joins and clippers are OZ v5 Transparent proxies (1159 B), each with its own ProxyAdmin. The ProxyAdmins checked are owned by the 1-day TimelockController `0x07d274a68393e8b8a2ccf19a2ce4ba3518735253`.

The CDP exists on **BNB Chain only**. `lisUSD` and `Interaction` return `0x` on Ethereum, Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc. Lista also runs lisUSD broker markets on Moolah ([lending.md](lending.md) §1.3).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Interaction (user entry point)

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed user, address collateral, uint256 amount, uint256 totalAmount)` — **same topic0 as ERC-4626 `Deposit`**, but only 2 topics |
| `0x10a0132d3bf8c82a7fb93a86160f3074ca5c3e5706fa2bcdf0e2b5fd495af09b` | `Borrow(address indexed user, address collateral, uint256 collateralAmount, uint256 amount, uint256 liquidationPrice)` — lisUSD minted |
| `0xee7777293f0d992d01f7d63f6f0e7762ee0df9d22267140e41090174a70e6f72` | `Payback(address indexed user, address collateral, uint256 amount, uint256 debt, uint256 liquidationPrice)` |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed user, uint256 amount)` — **no collateral field** |
| `0xa39454816a8e1e974f3d7de0cc0ba57840ba7d4cf111f280726b1f687e91d42b` | `AuctionStarted(address indexed token, address user, uint256 amount, uint256 price)` |
| `0x4ecae3269f800df64b16cb9f6f8b0b507018888521d1cff0841823e44bc0b00d` | `Liquidation(address indexed user, address indexed collateral, uint256 amount, uint256 leftover)` — emitted on `buyFromAuction` |
| `0x5d8d8db1d1b082fc4f893dcf587266b61ac1079e3f5e959cd6e76cfe84274f47` | `CollateralEnabled(address token, bytes32 ilk)` |
| `0x9fc793554ab8af2084d6005e4d61d847f73406e2f552476dfb2a0d4987ef4fa0` | `CollateralDisabled(address token, bytes32 ilk)` |

### 1.2 Liquidation engine (Dog, Clipper, Spot)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x85258d09e1e4ef299ff3fc11e74af99563f022d21f3f940db982229dc2a3358c` | `Bark(bytes32 indexed ilk, address indexed urn, uint256 ink, uint256 art, uint256 due, address clip, uint256 indexed id)` | Dog |
| `0x54f095dc7308776bf01e8580e4dd40fd959ea4bf50b069975768320ef8d77d8a` | `Digs(bytes32 indexed ilk, uint256 rad)` | Dog |
| `0x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8` | `Kick(uint256 indexed id, uint256 top, uint256 tab, uint256 lot, address indexed usr, address indexed kpr, uint256 coin)` | Clipper |
| `0x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1` | `Take(uint256 indexed id, uint256 max, uint256 price, uint256 owe, uint256 tab, uint256 lot, address indexed usr)` | Clipper |
| `0x275de7ecdd375b5e8049319f8b350686131c219dd4dc450a08e9cf83b03c865f` | `Redo(uint256 indexed id, uint256 top, uint256 tab, uint256 lot, address indexed usr, address indexed kpr, uint256 coin)` | Clipper |
| `0x2c5d2826eb5903b8fc201cf48094b858f42f61c7eaac9aaf43ebed490138144e` | `Yank(uint256 id)` | Clipper |
| `0xdfd7467e425a8107cfd368d159957692c25085aacbcf5228ce08f10f2146486e` | `Poke(bytes32 ilk, bytes32 val, uint256 spot)` — price update per ilk | Spot |
| `0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7` | `File(bytes32 indexed what, uint256 data)` | Dog, Clipper, Abaci, Flash |
| `0x851aa1caf4888170ad8875449d18f0f512fd6deb2a6571ea1a41fb9f95acbcd1` | `File(bytes32 indexed ilk, bytes32 indexed what, uint256 data)` | Dog |
| `0xdd0e34038ac38b2a1ce960229778ac48a8719bc900b6c4f8d0475c6e8b385a60` | `Rely(address indexed usr)` — ward added (admin) | Dog, Clipper, joins, Flash |
| `0x184450df2e323acec0ed3b5c7531b81f9b4cdef7914dfd4c0a4317416bb5251b` | `Deny(address indexed usr)` | same |
| `0x2308ed18a14e800c39b86eb6ea43270105955ca385b603b64eca89f98ae8fbda` | `Cage()` — emergency shutdown of that module | Dog, Jar, joins |

### 1.3 Joins, Jar, lisUSD, PSM, flash mint

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xb4e09949657f21548b58afe74e7b86cd2295da5ff1598ae1e5faecb1cf19ca95` | `Join(address indexed usr, uint256 wad)` | GemJoin, HayJoin, **and** Jar (`Join(address indexed user, uint indexed amount)`) |
| `0x22d324652c93739755cf4581508b60875ebdd78c20c0cff5cf8e23452b299631` | `Exit(address indexed usr, uint256 wad)` | GemJoin, HayJoin, Jar |
| `0xc38f9a7f7e6a60286c03e404e4a1890a1434a5633900261bf999356064b031da` | `Replenished(uint256 reward)` | Jar |
| `0x6763409c7e3ad1a90337041a3f8ec72290e406af08a63cf3193b3e2b49c7bea6` | `SupplyCapSet(uint256 oldCap, uint256 newCap)` | lisUSD |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — mint/burn by HayJoin | lisUSD |
| `0xf6f342132c7de5e5a1e99c8efae544c94731f3ff093f5c3c97c6973d9415cdfb` | `BuyToken(address account, uint256 realAmount, uint256 fee)` — lisUSD → USDT | PSM |
| `0xa8ff15eb642b39da3ab82bb74a87b76cc3e1aef2b82b70bc2a35458386db29aa` | `SellToken(address account, uint256 realAmount, uint256 fee)` — USDT → lisUSD | PSM |
| `0x4c6fb4d469797cfdfb4ac382c2fe84a494711f5b9676334ff9fac5f7601aef70` | `SetDailyLimit(uint256 dailyLimit)` | PSM |
| `0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0` | `FlashLoan(address indexed receiver, address token, uint256 amount, uint256 fee)` — lisUSD flash mint | FlashMinter |

### 1.4 Collateral providers (HelioProvider, SlisBNBProvider)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed account, uint256 amount)` — **same topic0 and same topic layout as WBNB `Deposit`**; only the emitter tells them apart | HelioProvider (BNB) |
| `0x2717ead6b9200dd235aad468c9809ea400fe33ac69b5bfaa6d3e90fc922b6398` | `Withdrawal(address indexed owner, address indexed recipient, uint256 amount)` | HelioProvider, SlisBNBProvider |
| `0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15` | `Deposit(address indexed account, uint256 amount, uint256 lPAmount)` | SlisBNBProvider (CDP) |
| `0x6dd29d11f8d1bcdbd79da21bf92895417dcc2f8886b3db11c8a4ce00b73de9d0` | `Liquidation(address indexed recipient, uint256 amount)` — collateral paid out on auction | SlisBNBProvider |
| `0x506fb497b203ea0f0b7a82df454f29d95b05b62329e7ad4ba4b93c70762a49d5` | `SyncUserLpWithReserve(address account, uint256 userLp, uint256 reservedLp)` — slisBNBx resync | SlisBNBProvider |
| `0xcc6ecd9a3781d13dd00409111e58b97984469875b6b06f8bff8d1bf8f84450c1` | `ChangeDelegateTo(address account, address oldDelegatee, address newDelegatee)` | providers |

---

## 2. Function signatures (chain-agnostic)

### 2.1 Interaction

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8340f549` | `deposit(address,address,uint256)` | `(participant, token, dink)`. Provider-only for provider-backed ilks. Emits `Deposit`. |
| `0x4b8a3529` | `borrow(address,uint256)` | `(token, lisUSDAmount)`. Emits `Borrow`. |
| `0x35ed8ab8` | `payback(address,uint256)` | Emits `Payback`. |
| `0x3b862af1` | `paybackFor(address,uint256,address)` | Repay for `borrower`. |
| `0xd9caed12` | `withdraw(address,address,uint256)` | `(participant, token, dink)`. Emits `Withdraw`. |
| `0x9f1d9267` | `withdrawFor(address,address,uint256)` | |
| `0x953790b1` | `startAuction(address,address,address)` | `(token, user, keeper)`. Calls `Dog.bark`. Emits `AuctionStarted`. |
| `0xe5ff2f8e` | `buyFromAuction(address,uint256,uint256,uint256,address,bytes)` | Calls `Clipper.take`. Emits `Liquidation`. |
| `0x07251016` | `resetAuction(address,uint256,address)` | Calls `Clipper.redo`. |
| `0x67a5cd06` | `drip(address)` | Accrue stability fee (Jug). |
| `0xb1a997ac` | `poke(address)` | Update price (Spot). |
| `0x2049ad8e` | `setCollateralType(address,address,bytes32,address,uint256)` | Admin. Emits `CollateralEnabled`. |
| `0x06fbed54` | `setCollateralDuty(address,uint256)` | Admin. |
| `0x7b7a4137` | `setHelioProvider(address,address,bool)` | Admin. |

### 2.2 DSS core and helpers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x76088703` | `frob(bytes32,address,address,address,int256,int256)` | Vat. No event. |
| `0x7bab3f40` | `grab(bytes32,address,address,address,int256,int256)` | Vat. Liquidation seizure. |
| `0xed998908` | `bark(bytes32,address,address)` | Dog. Emits `Bark`. |
| `0x81a794cb` | `take(uint256,uint256,uint256,address,bytes)` | Clipper. Emits `Take`. |
| `0xd843416d` | `redo(uint256,address)` | Clipper. |
| `0x44e2a5a8` | `drip(bytes32)` | Jug. |
| `0x1504460f` | `poke(bytes32)` | Spot. Emits `Poke`. |
| `0x3b4da69f` / `0xef693bed` | `join(address,uint256)` / `exit(address,uint256)` | GemJoin / HayJoin. |
| `0x049878f3` / `0x7f8661a1` | `join(uint256)` / `exit(uint256)` | Jar (stake lisUSD). |
| `0x66231cb2` | `replenish(uint256,bool)` | Jar reward top-up. |
| `0xd96a094a` / `0xe4849b32` | `buy(uint256)` / `sell(uint256)` | PSM. |
| `0x5cffe9de` | `flashLoan(address,address,uint256,bytes)` | FlashMinter (ERC-3156). |
| `0xb9472535` | `provide()` | HelioProvider: payable BNB in. |
| `0x2e2ebe06` | `provide(uint256)` | Token providers (slisBNB, etc.). |
| `0x0357371d` | `release(address,uint256)` | Providers: collateral out. |
| `0x40c10f19` / `0x9dc29fac` | `mint(address,uint256)` / `burn(address,uint256)` | lisUSD (wards only). |
| `0xb6a3f59a` | `setSupplyCap(uint256)` | lisUSD. |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)

All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com` on 2026-10-30. "v4 TP" = OZ v4 TransparentUpgradeableProxy behind ProxyAdmin `0x1fa3e471…8c4c`.

| Role | Address | One-liner |
|------|---------|-----------|
| **Interaction** | `0xB68443Ee3e828baD1526b3e0Bdf2Dfc6b1975ec4` | User entry point. v4 TP, impl `0xce338985a4b241605955dd77c917aa040e110ed3`. |
| AuctionProxy (library) | `0x272d6589cecc19165cfcd0466f73a648cb1ea700` | Linked library for auctions (7641 B, not a proxy). |
| **lisUSD** | `0x0782b6d8c4551B9760e74c0545a9bCD90bdc41E5` | Stablecoin (symbol `lisUSD`). v4 TP. |
| Vat | `0x33A34eAB3ee892D40420507B820347b1cA2201c4` | Core accounting. v4 TP. |
| Spot | `0x49bc2c4E5B035341b7d92Da4e6B267F7426F3038` | Price feed per ilk. v4 TP. |
| Jug | `0x787BdEaa29A253e40feB35026c3d05C18CbCA7B3` | Stability fee. v4 TP. |
| Dog | `0xd57E7b53a1572d27A04d9c1De2c4D423f1926d0B` | Liquidation trigger. v4 TP. |
| Vow | `0x2078A1969Ea581D618FDBEa2C0Dc13Fc15CB9fa7` | Surplus/debt. v4 TP. |
| HayJoin | `0x4C798F81de7736620Cd8e6510158b1fE758e22F7` | lisUSD mint/burn adapter. v4 TP. |
| Jar | `0x0a1Fd12F73432928C190CAF0810b3B767A59717e` | lisUSD staking pool. v4 TP. |
| Abaci (current / classic) | `0xc1359eD77E6B0CBF9a8130a4C28FBbB87B9501b7` / `0xbaf8b40a1e2a7b842289778c1c509b6bede3cc03` | Auction price curve. |
| Clip (BNB/ceABNBc) | `0x2dcFb02CE33955b6Cc0aF34033189DE3ac4C0292` | Original clipper. v4 TP. |
| FlashMinter | `0x64d94e715B6c03A5D8ebc6B2144fcef278EC6aAa` | lisUSD flash mint. v4 TP. |
| HelioProvider (BNB) | `0xa835F890Fcde7679e7F7711aBfd515d2A267Ed0B` | BNB → ceToken collateral. v4 TP. |
| MasterVault | `0x986b40c2618ff295a49ac442c5ec40febb26cc54` | BNB strategy vault behind HelioProvider. v4 TP. |
| CeToken (ceABNBc) | `0x563282106A5B0538f8673c787B3A16D3Cc1DbF1a` | Collateral token. v4 TP. |
| slisBNBProvider (CDP) | `0xfD31e1C5e5571f8E7FE318f80888C1e6da97819b` | slisBNB collateral + slisBNBx mint. ERC-1967 (170 B). |
| GemJoin / Clipper (slisBNB) | `0x91e49983598685dd5acac90ceb4061a772f6e5ae` / `0xba92899ea8bebb717cfc60507251acbb79a3b959` | v4 TP. |
| GemJoin / Clipper (BTCB) | `0xad9eAAe95617c39019aCC42301a1dCa4ea5b6f65` / `0xb12fF6FD1885a9Cb2b26302c98092644604B1e92` | OZ v5 TP. |
| GemJoin / Clipper (wBETH) | `0xf45c3b619ee86f653805e007fe211b7e930e0b3b` / `0x96b64bfcdbe658f2792322ac7a9d2dc215eba48f` | v4 TP (same impls as the slisBNB pair). |
| GemJoin / Clipper (USDT) | `0xAd406CcF75f9E6216fA4349635B0cD77D0059b1f` / `0xf6dAdF1210F7C22aD5bCba84b23cFd424a30313C` | OZ v5 TP. |
| GemJoin / Clipper (USD1) | `0x68B9A9eA70f4391c016746BE240037E5d4f63807` / `0xdeB93441fAc0737321199E84a5F0420931A6562e` | OZ v5 TP. |
| PSM (USDT) | `0xaa57F36DD5Ef2aC471863ec46277f976f272eC0c` | lisUSD↔USDT. ERC-1967 (170 B). |
| VaultManager (USDT) / VenusAdapter | `0x5763DDeB60c82684F3D0098aEa5076C0Da972ec7` / `0xf76D9cFD08dF91491680313B1A5b44307129CDa9` | PSM reserve deployment. |
| EarnPool / LisUSDPoolSet | `0x66dE07893Db7492B56bA88503B4cC99bAb1796F3` / `0x37DB1AE9B24055D1F9fE973Aea40B7EB2995D0Bf` | lisUSD earn. |
| cdpLiquidator | `0x556D96dFB7BDcf14B73E663CB46669f7826c7B87` | Lista auction bot. |
| ResilientOracle | `0xf3afD82A4071f272F403dC176916141f44E6c750` | Price oracle. OZ v5 TP. |

About 20 more collateral ilks (ezETH, weETH, STONE, solvBTC, BBTC, wstETH, FDUSD, SolvBTC.BBN, sUSDX, pumpBTC, cemBTC, mCake, mwBETH, USDF, asUSDF, …) each have a GemJoin, Clipper and oracle. The full list is on the docs page "Collateral Debt Position — Smart Contract" and in `lista-dao-contracts/addresses/new_collateral_*_bsc.json`. Discover ilks on-chain with `CollateralEnabled` on Interaction.

## 4. Cross-chain summary

| Chain (ID) | Interaction | lisUSD | Vat | PSM |
|------------|-------------|--------|-----|-----|
| BNB (56) | `0xB68443…5ec4` | `0x0782b6…41E5` | `0x33A34e…01c4` | `0xaa57F3…ec0c` (USDT) |
| Ethereum · Base · Avalanche · Arbitrum · Optimism · Polygon · Robinhood · Arc | — | — | — | — |

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Interaction, Vat, Spot, Jug, Dog, Vow, Jar, HayJoin, lisUSD, Clip, Abaci, HelioProvider, MasterVault, CeToken, slisBNB GemJoin/Clipper, FlashMinter | OZ v4 TransparentUpgradeableProxy | 2141 B; admin slot `0x1fa3e471…8c4c` | ProxyAdmin owner = TimelockController `0x07d274…5253` |
| Newer GemJoins/Clippers (BTCB, USDT, USD1, …), ResilientOracle | OZ v5 TransparentUpgradeableProxy | 1159 B; one ProxyAdmin per proxy | ProxyAdmin owner (timelock for the ones checked) |
| PSM, VaultManager, EarnPool, LisUSDPoolSet, cdpLiquidator, slisBNBProvider | ERC-1967 proxy (UUPS) | 170 B; admin slot `0x0` | `DEFAULT_ADMIN_ROLE` |
| AuctionProxy | linked library | impl slot `0x0` | — |

Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. Also watch `Rely`/`Deny` on Vat-adjacent modules: a new ward can mint lisUSD or move collateral.

## 6. Detection invariants & gotchas

1. **Vat is silent.** `Vat.frob`/`grab`/`suck` emit nothing. Track positions with Interaction `Deposit`/`Borrow`/`Payback`/`Withdraw`, and lisUSD supply with lisUSD `Transfer` from/to `0x0` (minted by HayJoin).
2. **Interaction `Deposit` = ERC-4626 `Deposit` topic0.** Interaction indexes only `user` (2 topics). ERC-4626 vaults index `sender` and `owner` (3 topics). Filter by emitter `0xB68443…5ec4`.
3. **Interaction `Withdraw` has no collateral token.** Join it to the `Exit` log of the GemJoin in the same transaction to learn the ilk.
4. **Provider-backed collateral.** For BNB (HelioProvider) and slisBNB, the user calls the provider (`provide`), and the provider calls `Interaction.deposit`. `Deposit.user` is the end user (`participant`), but `tx.to` is the provider.
5. **Liquidation is three logs.** `Interaction.AuctionStarted` + `Dog.Bark` + `Clipper.Kick` at start. `Clipper.Take` + `Interaction.Liquidation` at settlement. The Clipper `id` is per clipper, so key auctions on `(clipper, id)`.
6. **`Join`/`Exit` topics are shared** by every GemJoin, HayJoin and the Jar. Filter by emitter.
7. **`AuctionFinished`** (`0x88a732d7…`) is declared in `IDao` but is not in the live Interaction bytecode. Do not alert on its absence.
8. **lisUSD legacy name.** Older code and explorers show the token as HAY. The address did not change.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_CDP_DEPOSIT                 = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_CDP_BORROW                  = '\x10a0132d3bf8c82a7fb93a86160f3074ca5c3e5706fa2bcdf0e2b5fd495af09b'
TOPIC_CDP_PAYBACK                 = '\xee7777293f0d992d01f7d63f6f0e7762ee0df9d22267140e41090174a70e6f72'
TOPIC_CDP_WITHDRAW                = '\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'
TOPIC_CDP_AUCTION_STARTED         = '\xa39454816a8e1e974f3d7de0cc0ba57840ba7d4cf111f280726b1f687e91d42b'
TOPIC_CDP_LIQUIDATION             = '\x4ecae3269f800df64b16cb9f6f8b0b507018888521d1cff0841823e44bc0b00d'
TOPIC_CDP_COLLATERAL_ENABLED      = '\x5d8d8db1d1b082fc4f893dcf587266b61ac1079e3f5e959cd6e76cfe84274f47'
TOPIC_DOG_BARK                    = '\x85258d09e1e4ef299ff3fc11e74af99563f022d21f3f940db982229dc2a3358c'
TOPIC_CLIP_KICK                   = '\x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8'
TOPIC_CLIP_TAKE                   = '\x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1'
TOPIC_CLIP_REDO                   = '\x275de7ecdd375b5e8049319f8b350686131c219dd4dc450a08e9cf83b03c865f'
TOPIC_SPOT_POKE                   = '\xdfd7467e425a8107cfd368d159957692c25085aacbcf5228ce08f10f2146486e'
TOPIC_JOIN                        = '\xb4e09949657f21548b58afe74e7b86cd2295da5ff1598ae1e5faecb1cf19ca95'
TOPIC_EXIT                        = '\x22d324652c93739755cf4581508b60875ebdd78c20c0cff5cf8e23452b299631'
TOPIC_RELY                        = '\xdd0e34038ac38b2a1ce960229778ac48a8719bc900b6c4f8d0475c6e8b385a60'
TOPIC_DENY                        = '\x184450df2e323acec0ed3b5c7531b81f9b4cdef7914dfd4c0a4317416bb5251b'
TOPIC_PSM_BUY_TOKEN               = '\xf6f342132c7de5e5a1e99c8efae544c94731f3ff093f5c3c97c6973d9415cdfb'
TOPIC_PSM_SELL_TOKEN              = '\xa8ff15eb642b39da3ab82bb74a87b76cc3e1aef2b82b70bc2a35458386db29aa'
TOPIC_LISUSD_FLASHLOAN            = '\x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0'
TOPIC_LISUSD_SUPPLY_CAP_SET       = '\x6763409c7e3ad1a90337041a3f8ec72290e406af08a63cf3193b3e2b49c7bea6'
-- ===== Selectors (chain-agnostic) =====
SEL_CDP_DEPOSIT                   = '\x8340f549'
SEL_CDP_BORROW                    = '\x4b8a3529'
SEL_CDP_PAYBACK                   = '\x35ed8ab8'
SEL_CDP_WITHDRAW                  = '\xd9caed12'
SEL_CDP_START_AUCTION             = '\x953790b1'
SEL_CDP_BUY_FROM_AUCTION          = '\xe5ff2f8e'
SEL_CLIP_TAKE                     = '\x81a794cb'
SEL_DOG_BARK                      = '\xed998908'
SEL_PSM_BUY                       = '\xd96a094a'
SEL_PSM_SELL                      = '\xe4849b32'
SEL_LISUSD_FLASHLOAN              = '\x5cffe9de'
-- ===== Addresses (network-specific) =====
BSC_INTERACTION                   = '\xb68443ee3e828bad1526b3e0bdf2dfc6b1975ec4'
BSC_LISUSD                        = '\x0782b6d8c4551b9760e74c0545a9bcd90bdc41e5'
BSC_VAT                           = '\x33a34eab3ee892d40420507b820347b1ca2201c4'
BSC_DOG                           = '\xd57e7b53a1572d27a04d9c1de2c4d423f1926d0b'
BSC_SPOT                          = '\x49bc2c4e5b035341b7d92da4e6b267f7426f3038'
BSC_JUG                           = '\x787bdeaa29a253e40feb35026c3d05c18cbca7b3'
BSC_VOW                           = '\x2078a1969ea581d618fdbea2c0dc13fc15cb9fa7'
BSC_HAYJOIN                       = '\x4c798f81de7736620cd8e6510158b1fe758e22f7'
BSC_JAR                           = '\x0a1fd12f73432928c190caf0810b3b767a59717e'
BSC_HELIO_PROVIDER                = '\xa835f890fcde7679e7f7711abfd515d2a267ed0b'
BSC_CDP_SLISBNB_PROVIDER          = '\xfd31e1c5e5571f8e7fe318f80888c1e6da97819b'
BSC_CLIP_SLISBNB                  = '\xba92899ea8bebb717cfc60507251acbb79a3b959'
BSC_PSM_USDT                      = '\xaa57f36dd5ef2ac471863ec46277f976f272ec0c'
BSC_LISUSD_FLASH_MINTER           = '\x64d94e715b6c03a5d8ebc6b2144fcef278ec6aaa'
BSC_CDP_PROXY_ADMIN               = '\x1fa3e4718168077975ff4039304cc2e19ae58c4c'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `lista-dao-contracts/contracts` (`Interaction.sol`, `ceros/interfaces/IDao.sol`, `interfaces/IAuctionProxy.sol`, `dog.sol`, `clip.sol`, `spot.sol`, `join.sol`, `jar.sol`, `LisUSD.sol`, `flash.sol`, `psm/PSM.sol`, provider interfaces). Every listed topic and selector was found as a constant in the live implementation bytecode (Interaction impl `0xce338985…`, Dog, both Clippers, Jar, Spot, GemJoin, HayJoin, lisUSD, FlashMinter, PSM, HelioProvider, slisBNBProvider). Live `eth_getLogs` on Interaction returned `Deposit` 3 and `Withdraw` 19 in a 40k-block window.
- **Addresses:** parsed from the docs page "Collateral Debt Position — Smart Contract" and `lista-dao-contracts/addresses/bsc.json`, then existence-checked with `eth_getCode`. EIP-1967 implementation and admin slots and ProxyAdmin `owner()` were read live.
- **Chain coverage:** Interaction and lisUSD return `0x` on the eight other target chains.
- **Limit:** the public BSC endpoint serves logs for recent blocks only. `Borrow`, `Payback`, `Bark` and `Take` had no logs in the reachable window. They were confirmed by bytecode presence only.

Authoritative sources:
- [lista-dao/lista-dao-contracts](https://github.com/lista-dao/lista-dao-contracts) — source of truth for signatures and `addresses/bsc.json`.
- [Lista docs — CDP smart contracts](https://docs.bsc.lista.org/for-developer/collateral-debt-position/smart-contract) · [Flash loan](https://docs.bsc.lista.org/for-developer/collateral-debt-position/flash-loan)
- Explorer: [BscScan Interaction](https://bscscan.com/address/0xB68443Ee3e828baD1526b3e0Bdf2Dfc6b1975ec4)

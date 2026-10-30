# Sky USDS, Savings, SKY & Staking — Topics, Selectors, Addresses (Ethereum)

**Status:** verified against live Ethereum RPC, the on-chain ChainLog (`0xdA0Ab1e0017DEbCd72Be8599041a2aa3bA7e740F`) and Sourcify-verified ABIs on 2026-10-30.
**Scope:** the Sky-era token and savings layer on Ethereum (chain ID 1): USDS, UsdsJoin, the DAI↔USDS converter, sUSDS (Sky Savings Rate), stUSDS, SKY, MKR and the MKR→SKY converter, the Staking Engine (Lockstake) and its Clipper/oracle/migrator, staking-reward farms, vesting, the LitePSM (USDC) and the rate setters. Topics and selectors are chain-agnostic. Addresses are Ethereum-only. The Vat and liquidation core are in [mcd.md](mcd.md). Bridged USDS / sUSDS / SKY on Base, Arbitrum, Optimism, Avalanche (and Unichain) are in [l2.md](l2.md). **BNB, Polygon, Robinhood Chain and Arc have no USDS, sUSDS or SKY deployment** (`eth_getCode` = `0x` at every Sky token literal, 2026-10-30).

USDS is the Sky-era stablecoin. It is a **UUPS proxy** (ERC-1967) over the `Usds` implementation. It is minted and burned only by `UsdsJoin` (Vat ↔ ERC-20) and by authorised wards. DAI and USDS convert 1:1 in both directions through `DaiUsds`, which routes through the two joins and the Vat. sUSDS and stUSDS are also UUPS proxies. SKY, MKR, `DaiUsds`, `MkrSky`, the LockstakeEngine, the LitePSM and the reward farms are immutable.

The **Staking Engine** (`LockstakeEngine`, ilk `LSEV2-SKY-A`) locks SKY in a per-position `LockstakeUrn` clone, mints `lsSKY` 1:1, stakes the lsSKY in one selected reward farm, delegates the SKY votes, and lets the owner borrow USDS against it. Its positions are liquidated by `LockstakeClipper` with the standard Clipper topics. stUSDS is the "expert" USDS vault whose `ilk` is also `LSEV2-SKY-A`: it supplies the USDS that SKY-backed borrowers draw.

---

## 0. Contract families & versions

| Component | Contracts | Status |
|-----------|-----------|--------|
| USDS | `USDS` (proxy) → `Usds` impl, `UsdsJoin`, `DaiUsds` | Live since 2024-09. UUPS. |
| Savings | `sUSDS` (proxy) → `SUsds` impl; `stUSDS` (proxy) → `StUsds` impl + `StUsdsRateSetter` + `StUsdsMom` | sUSDS live since 2024-09. stUSDS live (2025). |
| Rate control | `SPBEAM` (sets DSR, SSR and ilk duties with bounded steps), `SPBEAM_MOM`, `MCD_SBEBEAM` | SPBEAM is a ward on Jug, Pot and sUSDS. |
| Governance token | `SKY`, legacy `MKR`, `MkrSky` converter | MKR → SKY at 24,000 SKY per MKR, `fee()` = 5 % (read 2026-10-30). |
| Staking Engine | `LockstakeEngine` (V2, SKY), `LockstakeSky` (lsSKY), `LockstakeClipper`, `LockstakeCappedOsmWrapper`, `LockstakeMigrator`, `LockstakeUrn` impl | V2 live. V1 "Seal" engine (MKR) is `*_OLD_V1`. |
| Rewards | `StakingRewards` farms, `VestedRewardsDistribution`, `DssVest*` | Synthetix-style farms with a `uint16 referral`. |
| PSM | `DssLitePsm` (`LITE-PSM-USDC-A`), `UsdsPsmWrapper`, `DssLitePsmMom` | Legacy `DssPsm` USDC/PAX/GUSD are wound down. |
| Helpers | `DsrManager` | Legacy DAI-DSR helper. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 USDS, SKY, lsSKY (ERC-20 + wards)

| topic0 | Event |
|--------|-------|
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |
| `0x184450df2e323acec0ed3b5c7531b81f9b4cdef7914dfd4c0a4317416bb5251b` | `Deny(address indexed usr)` |
| `0xdd0e34038ac38b2a1ce960229778ac48a8719bc900b6c4f8d0475c6e8b385a60` | `Rely(address indexed usr)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |

SKY (`Sky`) and lsSKY (`LockstakeSky`) emit the same `Transfer`/`Approval`/`Rely`/`Deny` topics without `Upgraded`. Mint and burn are `Transfer` from/to `0x0`. Every L2 copy of USDS and sUSDS uses this exact topic set ([l2.md](l2.md)).

### 1.2 MKR (legacy DSToken)

| topic0 | Event |
|--------|-------|
| `0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885` | `Mint(address indexed guy, uint256 wad)` |
| `0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5` | `Burn(address indexed guy, uint256 wad)` |
| `0x1abebea81bfa2637f28358c371278fb15ede7ea8dd28d2e03b112ff6d936ada4` | `LogSetAuthority(address indexed authority)` |
| `0xce241d7ca1f669fee44b6fc00b8eba2df3bb514eed0f6f668f8f89096e81ed94` | `LogSetOwner(address indexed owner)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

MKR `Mint`/`Burn` are separate events. MKR also emits `Transfer`. `MkrSky` burns MKR and mints SKY.

### 1.3 DaiUsds and UsdsJoin

| topic0 | Event |
|--------|-------|
| `0x23889db6b244d239344deac88ec7781d810b3873fe323939d1ce0e8ac9564235` | `DaiToUsds(address indexed caller, address indexed usr, uint256 wad)` |
| `0x9c7bd3b60b7e46fc1d7a38d88b7dd4be0e028b80b706848fc3c065eabc8e6a9b` | `UsdsToDai(address indexed caller, address indexed usr, uint256 wad)` |

| topic0 | Event |
|--------|-------|
| `0xbc2a67d422c268da6fe45f3e7d194e1d98906d221f1cfad62a5c80f2cd209f4c` | `Exit(address indexed caller, address indexed usr, uint256 wad)` |
| `0x0e64978d073561c3dfd4d4e3e4dce066cde2ab246a44f990fabb0a21a4a3bd95` | `Join(address indexed caller, address indexed usr, uint256 wad)` |

`UsdsJoin.Join` = ERC-20 USDS burned into Vat DAI. `UsdsJoin.Exit` = Vat DAI minted out as ERC-20 USDS. A `DaiUsds.DaiToUsds` fires together with DaiJoin `join` + UsdsJoin `Exit`.

### 1.4 sUSDS (ERC-4626, Sky Savings Rate)

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` |
| `0xad1e8a53178522eb68a9d94d862bf30c841f709d2115f743eb6b34528751c79f` | `Drip(uint256 chi, uint256 diff)` |
| `0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7` | `File(bytes32 indexed what, uint256 data)` |
| `0xb30a03a0e2a407f18ae0e83491331dc069d1521e292feffb071e61c8f7f40636` | `Referral(uint16 indexed referral, address indexed owner, uint256 assets, uint256 shares)` |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` |

### 1.5 stUSDS (ERC-4626, expert vault)

| topic0 | Event |
|--------|-------|
| `0xaaa7de6dcd0061e0bcd3a9bb711f1cc6d76b603c4d5cb97901525c7952076406` | `Cut(uint256 assets, uint256 oldChi, uint256 newChi)` |

stUSDS also emits the sUSDS topics `Deposit`, `Withdraw`, `Drip`, `Referral`, `File(bytes32,uint256)` (identical topic0). `Cut` fires when Lockstake liquidation losses reduce the share price.

| topic0 | Event |
|--------|-------|
| `0x80c9bdaa28e2c8c29e1f3d127e3e57466544546d365a0731bb69d8966a0778ec` | `Set(uint256 strBps, uint256 dutyBps, uint256 line, uint256 cap)` |

| topic0 | Event |
|--------|-------|
| `0x10536966b141d1113a9de0047f411034b44b4a35cc0d79f784ee8d87dc49e0a6` | `DissRateSetterBud(address indexed rateSetter, address bud)` |
| `0x63f3ab2c2b56fb9a11906009fb6d4b74ebb49687cab8ec5a0e8456394435fee3` | `HaltRateSetter(address indexed rateSetter)` |
| `0x52e3783bc5403a1f577b11fe9ea8dac09e951687e2729361a75725d45ba688a2` | `ZeroCap(address indexed rateSetter)` |
| `0xe651af4d3da9f1f05ef3d2fb2bc830e78a30258fdf9f8605a518e5ffa8d0a2a6` | `ZeroLine(address indexed rateSetter)` |

### 1.6 MkrSky converter

| topic0 | Event |
|--------|-------|
| `0xb90306ad06b2a6ff86ddc9327db583062895ef6540e62dc50add009db5b356eb` | `Burn(uint256 skyAmt)` |
| `0x4256a058fa2b123d727576d3d31e3a272db98ee5fe264e229610ce43dc849999` | `Collect(address indexed to, uint256 take)` |
| `0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7` | `File(bytes32 indexed what, uint256 data)` |
| `0x0a1dc0eb35e4f1de6bf0a2cbddfee6266b9326ddef41f1761763a0bf039660a8` | `MkrToSky(address indexed caller, address indexed usr, uint256 mkrAmt, uint256 skyAmt, uint256 skyFee)` |

### 1.7 Staking Engine (LockstakeEngine V2)

| topic0 | Event |
|--------|-------|
| `0x169dc17e0067f1d5a355eb6a2ab8d282a8569a96f0f3dc4776e9d62023fe6c36` | `AddFarm(address farm)` |
| `0xfae8feabc29b75519fe202a936053f133aa6ee03453dcb7bbbe544d3b6970616` | `DelFarm(address farm)` |
| `0x970ddd008a8a27402f3bcac48972a48da4954fbd2493769baba2ad596e489566` | `Draw(address indexed owner, uint256 indexed index, address to, uint256 wad)` |
| `0x8fef588b5fc1afbf5b2f06c1a435d513f208da2e6704c3d8f0e0ec91167066ba` | `File(bytes32 indexed what, address data)` |
| `0xde1819362eecc26ff17e717ad1e56b0154734cd5cc609494230256154e6c7ff0` | `Free(address indexed owner, uint256 indexed index, address to, uint256 wad, uint256 freed)` |
| `0xcd6427026c24aea1d465d0e880edc743f7ba98ea5a30a21702762edbb61c148d` | `FreeNoFee(address indexed owner, uint256 indexed index, address to, uint256 wad)` |
| `0xb0787e3944c17543aef2eb910c82d62e9ba80dabf5b15e371b09ac5728839700` | `GetReward(address indexed owner, uint256 indexed index, address indexed farm, address to, uint256 amt)` |
| `0xda1655dfbc632499abfa84202e0f5eda082634c6c927410ed51fc2213c3fb7d8` | `Hope(address indexed owner, uint256 indexed index, address indexed usr)` |
| `0x15a082f86d911273b558eb3797fc962ebe7cb22d787d8d13989e1ff0dc73a607` | `Lock(address indexed owner, uint256 indexed index, uint256 wad, uint16 ref)` |
| `0x81a57ff14cc36197cdb39b8075f925696024dc426d81c0c798dc4632a0eb4eb8` | `Nope(address indexed owner, uint256 indexed index, address indexed usr)` |
| `0xee91ffe09782821749e0fd00ad3d404b7fb3e2e8520e77aa5549c900f696f557` | `OnKick(address indexed urn, uint256 wad)` |
| `0xbb73c7bd9a4eafb9de35122e727b77695cc0d396aedc338b3589407028b568f6` | `OnRemove(address indexed urn, uint256 sold, uint256 burn, uint256 refund)` |
| `0x451bc655099856594a05cf3a385ce798360d63bc64e37b85d96e99a4b988fca6` | `OnTake(address indexed urn, address indexed who, uint256 wad)` |
| `0xdde6dd354074cad07a2dacbb612a6d2bac55ac537264d73250bf5c76bc15d64d` | `Open(address indexed owner, uint256 indexed index, address urn)` |
| `0xd434da22811bf2b5c3a8fc79e3d6644a80549c3159b7b28388eace49036f44c3` | `SelectFarm(address indexed owner, uint256 indexed index, address indexed farm, uint16 ref)` |
| `0x7af85b23b513d22f5f9daec6f2ad07e68c4953757a0d52e2d1013a5cc4995cef` | `SelectVoteDelegate(address indexed owner, uint256 indexed index, address indexed voteDelegate)` |
| `0x7c82d5b45cb4b7df16c473bcd2c3933a1651d1c91b9f17ebb2cccacbf29e03fd` | `Wipe(address indexed owner, uint256 indexed index, uint256 wad)` |

The V1 engine (MKR, `LOCKSTAKE_ENGINE_OLD_V1`) emits the same topics plus:

| topic0 | Event |
|--------|-------|
| `0x856e108038bf5b4b585e134533bf8c4d4bcd0f6f393342d8bd8eeac2360c5f1c` | `FreeSky(address indexed owner, uint256 indexed index, address to, uint256 skyWad, uint256 skyFreed)` |
| `0xdbe1fb728973022399a0db0e7e89f75bc1e84a5c9023b3ea6ecfc12cd7c74816` | `LockSky(address indexed owner, uint256 indexed index, uint256 skyWad, uint16 ref)` |

`LockstakeMigrator` emits an **anonymous** event `Migrate(address indexed oldOwner, uint256 indexed oldIndex, address indexed newOwner, uint256 indexed newIndex, uint256 ink, uint256 debt)`. It has four indexed fields and no topic0: `topic0` is `oldOwner`. Filter it by emitter only.

`LockstakeClipper` emits the standard Clipper topics `Kick`/`Take`/`Redo`/`Yank` ([mcd.md §1.4](mcd.md)).

### 1.8 Reward farms and vesting

| topic0 | Event |
|--------|-------|
| `0x8fb6c181ee25a520cf3dd6565006ef91229fcfe5a989566c2a3b8c115570cec5` | `PauseChanged(bool isPaused)` |
| `0x16902e34d01e8d5f80ce64939920a1390ff67f2546ae43ae72ac482033300968` | `Referral(uint16 indexed referral, address indexed user, uint256 amount)` |
| `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | `RewardAdded(uint256 reward)` |
| `0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486` | `RewardPaid(address indexed user, uint256 reward)` |
| `0x1c794a043683a294127c95bc365bae91b63b651eb9884a2c9120afee2bb690b4` | `RewardsDistributionUpdated(address newRewardsDistribution)` |
| `0xfb46ca5a5e06d4540d6387b930a7c978bce0db5f449ec6b3f5d07c6e1d44f2d3` | `RewardsDurationUpdated(uint256 newDuration)` |
| `0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d` | `Staked(address indexed user, uint256 amount)` |
| `0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5` | `Withdrawn(address indexed user, uint256 amount)` |

| topic0 | Event |
|--------|-------|
| `0x4def474aca53bf221d07d9ab0f675b3f6d8d2494b8427271bcf43c018ef1eead` | `Distribute(uint256 amount)` |

| topic0 | Event |
|--------|-------|
| `0x2e3cc5298d3204a0f0fc2be0f6fdefcef002025f4c75caf950b23e6cfbfb78d0` | `Init(uint256 indexed id, address indexed usr)` |
| `0x8ceddd02f4fb8ef0d5d6212cf4c91d59d366e04b977e8b2b944168d2a6d85081` | `Move(uint256 indexed id, address indexed dst)` |
| `0x9247a2bf1b75bc397d4043d99b9cebce531548a01dbb56a5d4c5f5ca26051e8d` | `Restrict(uint256 indexed id)` |
| `0x3d1b575f06b2d660af77eec35d9b3ffcfa956b6c1fdbc840992d4b03b03e622b` | `Unrestrict(uint256 indexed id)` |
| `0xa2906882572b0e9dfe893158bb064bc308eb1bd87d1da481850f9d17fc293847` | `Vest(uint256 indexed id, uint256 amt)` |
| `0x6f2a3ed78a3066d89360b6c89e52bf3313f52e859401a3ea5fa0f033fd540c3c` | `Yank(uint256 indexed id, uint256 end)` |

`StakingRewards.Referral` and `sUSDS.Referral` have different signatures and different topic0 values.

### 1.9 LitePSM, legacy PSM, rate setter

| topic0 | Event |
|--------|-------|
| `0x085d06ecf4c34b237767a31c0888e121d89546a77f186f1987c6b8715e1a8caa` | `BuyGem(address indexed owner, uint256 value, uint256 fee)` |
| `0xbaf40fa9da797753c7837b8bae01a8ee6009597a3de9665c6fdf70e870664993` | `Chug(uint256 wad)` |
| `0x12fdafd291eb287a54e3416070923d22aa5072f5ee04c4fb8361615e7508a37c` | `Diss(address indexed usr)` |
| `0x1293e04cd381a7d781bab7dbc1f14f587c30b893b53af97e704717cc02a10254` | `Fill(uint256 wad)` |
| `0x6ffc0fabf0709270e42087e84a3bfc36041d3b281266d04ae1962185092fb244` | `Kiss(address indexed usr)` |
| `0xef75f5a47cc9a929968796ceb84f19e7541617b4577f2c228ea95200e1572081` | `SellGem(address indexed owner, uint256 value, uint256 fee)` |
| `0xc73c16902381a37c21b07e127e3d0c092955b9fedb2b23e7e9b91ca527545ae6` | `Trim(uint256 wad)` |

| topic0 | Event |
|--------|-------|
| `0x495feb065552316a79c594a4305afbd632955a68b2c6f65ad8b2f62d150fea92` | `Halt(address indexed psm, uint8 indexed what)` |

| topic0 | Event |
|--------|-------|
| `0x28e3246f80515f5c1ed987b133ef2f193439b25acba6a5e69f219e896fc9d179` | `Set(bytes32 indexed id, uint256 bps)` |

The legacy `DssPsm` (`MCD_PSM_USDC_A` / `_PAX_A` / `_GUSD_A`) emits the same `SellGem`/`BuyGem` topic0 values as the LitePSM. Key on the emitter.

### 1.10 DsrManager (legacy)

| topic0 | Event |
|--------|-------|
| `0x22d324652c93739755cf4581508b60875ebdd78c20c0cff5cf8e23452b299631` | `Exit(address indexed dst, uint256 wad)` |
| `0xb4e09949657f21548b58afe74e7b86cd2295da5ff1598ae1e5faecb1cf19ca95` | `Join(address indexed dst, uint256 wad)` |

`DsrManager.Join` and `ESM.Join` share topic0 `0xb4e09949657f21548b58afe74e7b86cd2295da5ff1598ae1e5faecb1cf19ca95`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 USDS / SKY

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xa9059cbb` | `transfer(address,uint256)` | `(bool)` |
| `0x23b872dd` | `transferFrom(address,address,uint256)` | `(bool)` |
| `0x095ea7b3` | `approve(address,uint256)` | `(bool)` |
| `0x9fd5a6cf` | `permit(address,address,uint256,uint256,bytes)` | two overloads (EIP-2612 v,r,s and ERC-1271 `bytes signature`) |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | two overloads (EIP-2612 v,r,s and ERC-1271 `bytes signature`) |
| `0x40c10f19` | `mint(address,uint256)` | auth (UsdsJoin, bridges on L2) |
| `0x9dc29fac` | `burn(address,uint256)` | auth or allowance |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | auth (PauseProxy). UUPS |
| `0xaaf10f42` | `getImplementation()` | `(address)`. view |

SKY has the same `transfer`/`approve`/`permit`/`mint`/`burn` selectors (`mint` auth = MkrSky, DssVestMintable, governance).

### 2.2 DaiUsds, UsdsJoin, MkrSky

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xf2c07aae` | `daiToUsds(address,uint256)` | permissionless 1:1 |
| `0x68f30150` | `usdsToDai(address,uint256)` | permissionless 1:1 |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x3b4da69f` | `join(address,uint256)` | burn ERC-20 USDS, credit Vat DAI |
| `0xef693bed` | `exit(address,uint256)` | debit Vat DAI, mint ERC-20 USDS |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xab89605a` | `mkrToSky(address,uint256)` | permissionless. Burns MKR, mints SKY minus `fee` |
| `0x06ec16f8` | `collect(address)` | `(uint256)` |
| `0x42966c68` | `burn(uint256)` | — |
| `0x2c4e722e` | `rate()` | `(uint256)`. view |
| `0xddca3f43` | `fee()` | `(uint256)`. view |

### 2.3 sUSDS / stUSDS

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x6e553f65` | `deposit(uint256,address)` | `(uint256)`. overload with `uint16 referral` |
| `0x9b8d6d38` | `deposit(uint256,address,uint16)` | `(uint256)`. overload with `uint16 referral` |
| `0x216740a0` | `mint(uint256,address,uint16)` | `(uint256)` |
| `0x94bf804d` | `mint(uint256,address)` | `(uint256)` |
| `0xb460af94` | `withdraw(uint256,address,address)` | `(uint256)` |
| `0xba087652` | `redeem(uint256,address,address)` | `(uint256)` |
| `0x9f678cca` | `drip()` | `(uint256)`. permissionless. Accrues SSR into `chi` |
| `0x03607ceb` | `ssr()` | `(uint256)`. view. per-second rate (ray) |
| `0xc92aecc4` | `chi()` | `(uint192)`. view |
| `0x20aba08b` | `rho()` | `(uint64)`. view |
| `0x01e1d114` | `totalAssets()` | `(uint256)`. view |
| `0x07a2d13a` | `convertToAssets(uint256)` | `(uint256)`. view |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | auth. UUPS |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x09260db7` | `cut(uint256)` | auth (LockstakeClipper path) |
| `0xc15bae84` | `str()` | `(uint256)`. view. stUSDS rate |
| `0x355274ea` | `cap()` | `(uint256)`. view |
| `0xb56b8353` | `line()` | `(uint256)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x606ce3bf` | `set(uint256,uint256,uint256,uint256)` | whitelisted (`bud`). Sets `str`, ilk `duty`, `line`, `cap` in one call |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x474d857f` | `set((bytes32,uint256)[])` | whitelisted (`bud`). Array of `(id, bps)`: `DSR`, `SSR` or an ilk name |

### 2.4 Staking Engine

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x690e7c09` | `open(uint256)` | `(address)`. creates a new LockstakeUrn for `msg.sender` (index = `ownerUrnsCount`) |
| `0x6c3dead4` | `lock(address,uint256,uint256,uint16)` | lock SKY. `ref` = referral code |
| `0xbf0700fe` | `free(address,uint256,address,uint256)` | `(uint256)`. unlock SKY (fee applies, `fee()` = 0 on 2026-10-30) |
| `0x1c6eb67b` | `freeNoFee(address,uint256,address,uint256)` | auth |
| `0x7abdf250` | `draw(address,uint256,address,uint256)` | borrow USDS |
| `0xc3b6cb4b` | `wipe(address,uint256,uint256)` | repay USDS |
| `0x6ddb4566` | `wipeAll(address,uint256)` | `(uint256)` |
| `0xb5331d5e` | `selectFarm(address,uint256,address,uint16)` | — |
| `0x0adfd1bf` | `selectVoteDelegate(address,uint256,address)` | — |
| `0x58771079` | `getReward(address,uint256,address,address)` | `(uint256)` |
| `0x90a01441` | `hope(address,uint256,address)` | — |
| `0xa496d520` | `nope(address,uint256,address)` | — |
| `0x5c2e41c1` | `onKick(address,uint256)` | auth (Clipper) |
| `0xd0294ea5` | `onTake(address,address,uint256)` | auth (Clipper) |
| `0x2d074bbd` | `onRemove(address,uint256,uint256)` | auth (Clipper) |
| `0xac9650d8` | `multicall(bytes[])` | `(bytes[])` |
| `0xd9f06192` | `ownerUrns(address,uint256)` | `(address)`. view. urn address for `(owner, index)` |
| `0x3d64fc52` | `urnOwners(address)` | `(address)`. view |
| `0x2a95b45d` | `urnFarms(address)` | `(address)`. view |
| `0xd9c415f4` | `urnVoteDelegates(address)` | `(address)`. view |
| `0xfdc56a18` | `urnAuctions(address)` | `(uint256)`. view |

V1 extras: `lockSky` `0x21e2e369`, `freeSky` `0xaad84387`.

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x5ea8d4f3` | `migrate(address,uint256,address,uint256,uint16)` | move a V1 (MKR) position to V2 (SKY) with a Vat-DAI flash loan |

### 2.5 Reward farms and vesting

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x42ea02c1` | `stake(uint256,uint16)` | with referral |
| `0xa694fc3a` | `stake(uint256)` | — |
| `0x2e1a7d4d` | `withdraw(uint256)` | — |
| `0x3d18b912` | `getReward()` | — |
| `0xe9fad8ee` | `exit()` | — |
| `0x3c6b16ab` | `notifyRewardAmount(uint256)` | auth (rewardsDistribution) |
| `0x008cc262` | `earned(address)` | `(uint256)`. view |
| `0x7b0a47ee` | `rewardRate()` | `(uint256)`. view |
| `0xebe2b12b` | `periodFinish()` | `(uint256)`. view |
| `0x72f702f3` | `stakingToken()` | `(address)`. view |
| `0xd1af0c7d` | `rewardsToken()` | `(address)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xe4fc6b6d` | `distribute()` | `(uint256)`. permissionless (cron job). Vests from DssVest and calls `notifyRewardAmount` |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xdb64ff8f` | `create(address,uint256,uint256,uint256,uint256,address)` | `(uint256)`. auth |
| `0x6a760b80` | `vest(uint256)` | — |
| `0xbb7c46f3` | `vest(uint256,uint256)` | — |
| `0x26e027f1` | `yank(uint256)` | — |
| `0xd8a8e03a` | `move(uint256,address)` | — |
| `0xf52981f4` | `accrued(uint256)` | `(uint256)`. view |
| `0x53e8863d` | `unpaid(uint256)` | `(uint256)`. view |

### 2.6 LitePSM and wrapper

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x95991276` | `sellGem(address,uint256)` | `(uint256)`. USDC → DAI, fee `tin` |
| `0x8d7ef9bb` | `buyGem(address,uint256)` | `(uint256)`. DAI → USDC, fee `tout` |
| `0x86c34f42` | `sellGemNoFee(address,uint256)` | `(uint256)`. whitelisted (`bud`) |
| `0x067d9274` | `buyGemNoFee(address,uint256)` | `(uint256)`. whitelisted |
| `0xd9c55ce1` | `fill()` | `(uint256)`. permissionless. Pre-mint DAI up to `buf` |
| `0x40d9c0e3` | `trim()` | `(uint256)`. permissionless. Burn excess pre-minted DAI |
| `0x9b652df6` | `chug()` | `(uint256)`. permissionless. Send fees to Vow |
| `0x568d4b6f` | `tin()` | `(uint256)`. view |
| `0xfae036d5` | `tout()` | `(uint256)`. view |
| `0x15232515` | `buf()` | `(uint256)`. view |
| `0xcccef9e2` | `pocket()` | `(address)`. view |
| `0x7bd2bea7` | `gem()` | `(address)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x95991276` | `sellGem(address,uint256)` | `(uint256)`. USDC → USDS through the LitePSM |
| `0x8d7ef9bb` | `buyGem(address,uint256)` | `(uint256)`. USDS → USDC |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xd42ff876` | `halt(address,uint8)` | emergency halt of buys, sells or both (`what` = 0/1/2) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-10-30 and matched against the ChainLog key.

### 3.1 Tokens and converters

| Role | ChainLog key | Address | One-liner |
|------|--------------|---------|-----------|
| **USDS** (proxy) | `USDS` | `0xdC035D45d973E3EC169d2276DDab16f1e407384F` | Sky Dollar. Impl `USDS_IMP` `0x1923DfeE706A8E78157416C29cBCCFDe7cdF4102`. |
| **UsdsJoin** | `USDS_JOIN` | `0x3C0f895007CA717Aa01c8693e59DF1e8C3777FEB` | Vat DAI ↔ ERC-20 USDS. |
| **DaiUsds** | `DAI_USDS` | `0x3225737a9Bbb6473CB4a45b7244ACa2BeFdB276A` | 1:1 DAI ↔ USDS converter. |
| **sUSDS** (proxy) | `SUSDS` | `0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD` | Savings USDS (ERC-4626). Impl `SUSDS_IMP` `0x4e7991e5C547ce825BdEb665EE14a3274f9F61e0`. |
| **stUSDS** (proxy) | `STUSDS` | `0x99CD4Ec3f88A45940936F469E4bB72A2A701EEB9` | Expert USDS vault (ilk `LSEV2-SKY-A`). Impl `STUSDS_IMP` `0x7A61B7adCFD493f7CF0F86dFCECB94b72c227F22`. |
| StUsdsRateSetter | `STUSDS_RATE_SETTER` | `0x30784615252B13E1DbE2bDf598627eaC297Bf4C5` | Bounded setter for `str`/duty/line/cap. |
| StUsdsMom | `STUSDS_MOM` | `0x99159d0b885CC6633daC7CD4d82e4247A834b89A` | Emergency halts for stUSDS. |
| **SKY** | `SKY` (= `MCD_GOV`) | `0x56072C95FAA701256059aa122697B133aDEd9279` | Governance token. |
| MKR (legacy) | `MKR` | `0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2` | Old governance token (DSToken). |
| **MkrSky** | `MKR_SKY` | `0xA1Ea1bA18E88C381C724a75F23a130420C403f9a` | MKR → SKY converter (24,000:1, 5 % fee). |

### 3.2 Staking Engine

| Role | ChainLog key | Address | One-liner |
|------|--------------|---------|-----------|
| **LockstakeEngine** (V2) | `LOCKSTAKE_ENGINE` | `0xCe01C90dE7FD1bcFa39e237FE6D8D9F569e8A6a3` | SKY staking + borrowing (`LSEV2-SKY-A`). |
| **LockstakeSky** (lsSKY) | `LOCKSTAKE_SKY` | `0xf9A9cfD3229E985B91F99Bc866d42938044FFa1C` | Receipt token staked in farms. |
| **LockstakeClipper** | `LOCKSTAKE_CLIP` | `0x836F56750517b1528B5078Cba4Ac4B94fBE4A399` | Liquidation auctions for staked SKY. |
| Clipper calc | `LOCKSTAKE_CLIP_CALC` | `0xB8f8c7caabFa320717E3e848948450e120F0D9BB` | Price decrease function. |
| LockstakeCappedOsmWrapper | `LOCKSTAKE_ORACLE` | `0x0C13fF3DC02E85aC169c4099C09c9B388f2943Fd` | Capped SKY price (pip of `LSEV2-SKY-A`). Underlying `PIP_SKY` `0x511485bBd96e7e3a056a8D1b84C5071071C52D6F`. |
| LockstakeMigrator | `LOCKSTAKE_MIGRATOR` | `0x473d777f608C3C24B441AB6bD4bBcA6b7F9AF90B` | V1 → V2 position migration. |
| LockstakeUrn impl | — | `0x7b4cb30d13983bf81767531433cebd4214908a99` | Clone template (`urnImplementation()`). Each position is a clone. |
| Old V1 engine (MKR) | `LOCKSTAKE_ENGINE_OLD_V1` | `0x2b16C07D5fD5cC701a0a871eae2aad6DA5fc8f12` | "Seal Engine". Deprecated. |
| Old V1 lsMKR / Clipper | `LOCKSTAKE_MKR_OLD_V1` / `LOCKSTAKE_CLIP_OLD_V1` | `0xb4e0e45e142101dC3Ed768bac219fC35EDBED295` / `0xA85621D35cAf9Cf5C146D2376Ce553D7B78A6239` | Deprecated. |

### 3.3 Reward farms and vesting

| Role | ChainLog key | Address | Stake → reward |
|------|--------------|---------|----------------|
| StakingRewards | `REWARDS_LSSKY_USDS` | `0x38E4254bD82ED5Ee97CD1C4278FAae748d998865` | lsSKY → USDS (Splitter `farm`). |
| StakingRewards | `REWARDS_LSSKY_SKY` | `0xB44C2Fb4181D7Cb06bdFf34A46FdFe4a259B40Fc` | lsSKY → SKY. |
| StakingRewards | `REWARDS_LSSKY_SPK` | `0x99cBC0e4E6427F6939536eD24d1275B95ff77404` | lsSKY → SPK. |
| StakingRewards | `REWARDS_USDS_SKY` | `0x0650CAF159C5A49f711e8169D4336ECB9b950275` | USDS → SKY. |
| StakingRewards | `REWARDS_USDS_SPK` | `0x173e314C7635B45322cd8Cb14f44b312e079F3af` | USDS → SPK. |
| StakingRewards | `REWARDS_USDS_GROVE` | `0x4E41488C19cD35EB4de3083Fc3e204854c75c86a` | USDS → GROVE. |
| StakingRewards | `REWARDS_USDS_01` | `0x10ab606B067C9C461d8893c47C7512472E19e2Ce` | USDS → points only (`rewardsToken()` = `0x0`). |
| StakingRewards (legacy) | `REWARDS_LSMKR_USDS_LEGACY` | `0x92282235a39bE957fF1f37619fD22A9aE5507CB1` | lsMKR → USDS (V1). |
| VestedRewardsDistribution | `REWARDS_DIST_USDS_SKY` / `_LSSKY_SKY` / `_LSSKY_SPK` / `_USDS_SPK` / `_USDS_GROVE` | `0xC8d67Fcf101d3f89D0e1F3a2857485A84072a63F` / `0x675671A8756dDb69F7254AFB030865388Ef699Ee` / `0xa3Ee378BdD0b7DD403cEd3a0A65B2B389A2eaB7e` / `0x3959e23A63CA7ac12D658bb44F90cb1f7Ee4C02c` / `0xAf7a108B4fB0b2F65E1Acc9E1a548abe482559C4` | Feeds each farm from DssVest. |
| DssVestMintable (SKY) | `MCD_VEST_SKY` | `0xB313Eab3FdE99B2bB4bA9750C2DDFBe2729d1cE9` | Mints SKY on vest. |
| DssVestTransferrable | `MCD_VEST_SKY_TREASURY` / `MCD_VEST_USDS` / `MCD_VEST_DAI` | `0x67eaDb3288cceDe034cE95b0511DCc65cf630bB6` / `0xc447a9745aDe9A44Bb9E37B7F6C92f9582544110` / `0xa4c22f0e25C6630B2017979AcF1f865e94695C4b` | Treasury vesting streams. |

### 3.4 PSM, rate control, helpers

| Role | ChainLog key | Address | One-liner |
|------|--------------|---------|-----------|
| **DssLitePsm** | `MCD_LITE_PSM_USDC_A` | `0xf6e72Db5454dd049d0788e411b06CfAF16853042` | USDC ↔ DAI, ilk `LITE-PSM-USDC-A` (≈ 4.48 B debt). |
| LitePSM pocket | `MCD_LITE_PSM_USDC_A_POCKET` | `0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341` | Holds the USDC. No code (an account). |
| **UsdsPsmWrapper** | `WRAPPER_USDS_LITE_PSM_USDC_A` | `0xA188EEC8F81263234dA3622A406892F3D630f98c` | USDC ↔ USDS through the LitePSM. |
| DssLitePsmMom | `LITE_PSM_MOM` | `0x467b32b0407Ad764f56304420Cddaa563bDab425` | Emergency halt. |
| Legacy DssPsm | `MCD_PSM_USDC_A` / `MCD_PSM_PAX_A` / `MCD_PSM_GUSD_A` | `0x89B78CfA322F6C5dE0aBcEecab66Aee45393cC5A` / `0x961Ae24a1Ceba861D1FDf723794f6024Dc5485Cf` / `0x204659B2Fd2aD5723975c362Ce2230Fba11d3900` | Wound down (ceilings 0). |
| **SPBEAM** | `MCD_SPBEAM` | `0x36B072ed8AFE665E3Aa6DaBa79Decbec63752b22` | Sets DSR / SSR / duties. |
| SPBEAM_MOM | `SPBEAM_MOM` | `0xf0C6e6Ec8B367cC483A411e595D3Ba0a816d37D0` | Emergency halt of SPBEAM. |
| SBEBEAM | `MCD_SBEBEAM` | `0xc8b61d211D3D03A630Fb09199E17953a8c9749a9` | Smart Burn Engine parameter setter (ChainLog name). ABI not on Sourcify. Topics not listed (unverified). |
| DsrManager | `DSR_MANAGER` | `0x373238337Bfe1146fb49989fc222523f83081dDb` | Legacy DAI → Pot helper. |

SkyLink contracts on Ethereum (USDS/sUSDS OFT adapters, SkyLink L1 bridges, escrows and governance relays) are in [l2.md](l2.md).

---

## 4. Cross-chain summary

| Chain | ID | USDS | sUSDS | SKY | Engine / PSM / farms |
|-------|----|------|-------|-----|----------------------|
| Ethereum | 1 | `0xdC035D45…384F` | `0xa3931d71…7fbD` | `0x56072C95…9279` | ✅ all of §3 |
| Base | 8453 | bridged ([l2.md](l2.md)) | bridged | contract deployed, zero supply | — |
| Arbitrum One | 42161 | bridged | bridged | — | — |
| Optimism | 10 | bridged | bridged | — | — |
| Avalanche | 43114 | LayerZero OFT | LayerZero OFT | — | — |
| BNB | 56 | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — |
| Robinhood Chain | 4663 | — | — | — | — |
| Arc | 5042 | — | — | — | — |

## 5. Proxies (old & new)

| Contract | Pattern | Current impl (2026-10-30) | Upgrade auth |
|----------|---------|---------------------------|--------------|
| **USDS** `0xdC03…384F` | ERC-1967 UUPS (170-byte proxy) | `0x1923DfeE706A8E78157416C29cBCCFDe7cdF4102` | `wards` (PauseProxy = 1). `upgradeToAndCall`. |
| **sUSDS** `0xa393…7fbD` | ERC-1967 UUPS | `0x4e7991e5C547ce825BdEb665EE14a3274f9F61e0` | `wards` (PauseProxy). |
| **stUSDS** `0x99CD…EEB9` | ERC-1967 UUPS (163-byte proxy) | `0x7A61B7adCFD493f7CF0F86dFCECB94b72c227F22` | `wards` (PauseProxy). |
| Everything else in §3 | Immutable | EIP-1967 slots `0x0` | Replacement via ChainLog. |

Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on the three proxies. The admin slot is empty on all three (UUPS, no ProxyAdmin).

## 6. Detection invariants & gotchas

1. **USDS supply has several mint paths.** `UsdsJoin.Exit` (from Vat DAI: vault draws, allocator draws, LitePSM via wrapper, DaiUsds), plus bridge/OFT unlocks on L1 (escrows release, they do not mint). Track supply with `Transfer` from `0x0`, not with one source.
2. **DAI ↔ USDS conversions are not new money.** `DaiToUsds` burns DAI (DaiJoin `join`) and mints USDS (UsdsJoin `Exit`) in one call. Net out both legs.
3. **sUSDS vs stUSDS share topic0.** Both are ERC-4626 with identical `Deposit`/`Withdraw`/`Drip`/`Referral` topics. Key on the emitter. The ERC-4626 `Deposit`/`Withdraw` topics also match every other ERC-4626 vault.
4. **`Drip(chi, diff)`** gives the SSR accrual. `diff` is USDS minted into sUSDS as yield (via Vat `suck`).
5. **Lockstake position identity is `(owner, index)` and an urn address.** `Open` gives the urn. Vat `frob` notes and Clipper `Kick.usr` show the urn, not the owner. Resolve with `urnOwners(urn)`.
6. **`OnKick` / `OnTake` / `OnRemove`** on the engine are the liquidation side effects. `OnRemove.burn` is SKY burned as the liquidation penalty. `OnRemove.refund` goes back to the owner.
7. **The Migrator event is anonymous with four indexed fields.** `topic0` is the old owner address. A topic0-based filter misses it.
8. **StakingRewards amounts.** `Staked`/`Withdrawn` amounts are lsSKY (engine farms) or USDS (USDS farms). The `user` of an engine farm is the urn, not the person.
9. **LitePSM `SellGem`/`BuyGem` amounts are in USDC units (6 dp) for `value` and DAI (18 dp) for `fee`.** Through the wrapper, `owner` is the **wrapper** (`0xA188…f98c`), not the user. Take the user from the USDC/USDS `Transfer` legs or `tx.from`.
10. **`fill`/`trim`** pre-mint and burn DAI inside the PSM. They change Vat debt without a user swap. Do not count them as flows.
11. **MKR is still live.** `MkrToSky` is one-way. MKR `Burn` + SKY `Transfer` from `0x0` fire together.
12. **SPBEAM `Set(id, bps)`** is the rate-change signal. `id` = `"DSR"`, `"SSR"` or an ilk name (bytes32).

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_ERC20_TRANSFER        = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  -- Transfer(address,address,uint256)
TOPIC_ERC20_APPROVAL        = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'  -- Approval(address,address,uint256)
TOPIC_UPGRADED              = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'  -- Upgraded(address)
TOPIC_DAIUSDS_DAI_TO_USDS   = '\x23889db6b244d239344deac88ec7781d810b3873fe323939d1ce0e8ac9564235'  -- DaiToUsds(address,address,uint256)
TOPIC_DAIUSDS_USDS_TO_DAI   = '\x9c7bd3b60b7e46fc1d7a38d88b7dd4be0e028b80b706848fc3c065eabc8e6a9b'  -- UsdsToDai(address,address,uint256)
TOPIC_USDSJOIN_JOIN         = '\x0e64978d073561c3dfd4d4e3e4dce066cde2ab246a44f990fabb0a21a4a3bd95'  -- Join(address,address,uint256)
TOPIC_USDSJOIN_EXIT         = '\xbc2a67d422c268da6fe45f3e7d194e1d98906d221f1cfad62a5c80f2cd209f4c'  -- Exit(address,address,uint256)
TOPIC_ERC4626_DEPOSIT       = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'  -- Deposit(address,address,uint256,uint256)
TOPIC_ERC4626_WITHDRAW      = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'  -- Withdraw(address,address,address,uint256,uint256)
TOPIC_SUSDS_DRIP            = '\xad1e8a53178522eb68a9d94d862bf30c841f709d2115f743eb6b34528751c79f'  -- Drip(uint256,uint256)
TOPIC_SUSDS_REFERRAL        = '\xb30a03a0e2a407f18ae0e83491331dc069d1521e292feffb071e61c8f7f40636'  -- Referral(uint16,address,uint256,uint256)
TOPIC_STUSDS_CUT            = '\xaaa7de6dcd0061e0bcd3a9bb711f1cc6d76b603c4d5cb97901525c7952076406'  -- Cut(uint256,uint256,uint256)
TOPIC_MKRSKY_CONVERT        = '\x0a1dc0eb35e4f1de6bf0a2cbddfee6266b9326ddef41f1761763a0bf039660a8'  -- MkrToSky(address,address,uint256,uint256,uint256)
TOPIC_LSE_OPEN              = '\xdde6dd354074cad07a2dacbb612a6d2bac55ac537264d73250bf5c76bc15d64d'  -- Open(address,uint256,address)
TOPIC_LSE_LOCK              = '\x15a082f86d911273b558eb3797fc962ebe7cb22d787d8d13989e1ff0dc73a607'  -- Lock(address,uint256,uint256,uint16)
TOPIC_LSE_FREE              = '\xde1819362eecc26ff17e717ad1e56b0154734cd5cc609494230256154e6c7ff0'  -- Free(address,uint256,address,uint256,uint256)
TOPIC_LSE_DRAW              = '\x970ddd008a8a27402f3bcac48972a48da4954fbd2493769baba2ad596e489566'  -- Draw(address,uint256,address,uint256)
TOPIC_LSE_WIPE              = '\x7c82d5b45cb4b7df16c473bcd2c3933a1651d1c91b9f17ebb2cccacbf29e03fd'  -- Wipe(address,uint256,uint256)
TOPIC_LSE_SELECT_FARM       = '\xd434da22811bf2b5c3a8fc79e3d6644a80549c3159b7b28388eace49036f44c3'  -- SelectFarm(address,uint256,address,uint16)
TOPIC_LSE_SELECT_DELEGATE   = '\x7af85b23b513d22f5f9daec6f2ad07e68c4953757a0d52e2d1013a5cc4995cef'  -- SelectVoteDelegate(address,uint256,address)
TOPIC_LSE_ON_KICK           = '\xee91ffe09782821749e0fd00ad3d404b7fb3e2e8520e77aa5549c900f696f557'  -- OnKick(address,uint256)
TOPIC_LSE_ON_TAKE           = '\x451bc655099856594a05cf3a385ce798360d63bc64e37b85d96e99a4b988fca6'  -- OnTake(address,address,uint256)
TOPIC_LSE_ON_REMOVE         = '\xbb73c7bd9a4eafb9de35122e727b77695cc0d396aedc338b3589407028b568f6'  -- OnRemove(address,uint256,uint256,uint256)
TOPIC_FARM_STAKED           = '\x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'  -- Staked(address,uint256)
TOPIC_FARM_WITHDRAWN        = '\x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'  -- Withdrawn(address,uint256)
TOPIC_FARM_REWARD_PAID      = '\xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'  -- RewardPaid(address,uint256)
TOPIC_FARM_REFERRAL         = '\x16902e34d01e8d5f80ce64939920a1390ff67f2546ae43ae72ac482033300968'  -- Referral(uint16,address,uint256)
TOPIC_VRD_DISTRIBUTE        = '\x4def474aca53bf221d07d9ab0f675b3f6d8d2494b8427271bcf43c018ef1eead'  -- Distribute(uint256)
TOPIC_PSM_SELL_GEM          = '\xef75f5a47cc9a929968796ceb84f19e7541617b4577f2c228ea95200e1572081'  -- SellGem(address,uint256,uint256)
TOPIC_PSM_BUY_GEM           = '\x085d06ecf4c34b237767a31c0888e121d89546a77f186f1987c6b8715e1a8caa'  -- BuyGem(address,uint256,uint256)
TOPIC_PSM_FILL              = '\x1293e04cd381a7d781bab7dbc1f14f587c30b893b53af97e704717cc02a10254'  -- Fill(uint256)
TOPIC_PSM_TRIM              = '\xc73c16902381a37c21b07e127e3d0c092955b9fedb2b23e7e9b91ca527545ae6'  -- Trim(uint256)
TOPIC_PSM_CHUG              = '\xbaf40fa9da797753c7837b8bae01a8ee6009597a3de9665c6fdf70e870664993'  -- Chug(uint256)
TOPIC_PSMMOM_HALT           = '\x495feb065552316a79c594a4305afbd632955a68b2c6f65ad8b2f62d150fea92'  -- Halt(address,uint8)
TOPIC_SPBEAM_SET            = '\x28e3246f80515f5c1ed987b133ef2f193439b25acba6a5e69f219e896fc9d179'  -- Set(bytes32,uint256)
TOPIC_STUSDS_RATE_SET       = '\x80c9bdaa28e2c8c29e1f3d127e3e57466544546d365a0731bb69d8966a0778ec'  -- Set(uint256,uint256,uint256,uint256)
-- ===== Selectors (chain-agnostic) =====
SEL_DAI_TO_USDS             = '\xf2c07aae'  -- daiToUsds(address,uint256)
SEL_USDS_TO_DAI             = '\x68f30150'  -- usdsToDai(address,uint256)
SEL_SUSDS_DEPOSIT           = '\x6e553f65'  -- deposit(uint256,address)
SEL_SUSDS_DEPOSIT_REF       = '\x9b8d6d38'  -- deposit(uint256,address,uint16)
SEL_SUSDS_REDEEM            = '\xba087652'  -- redeem(uint256,address,address)
SEL_SUSDS_WITHDRAW          = '\xb460af94'  -- withdraw(uint256,address,address)
SEL_SUSDS_DRIP              = '\x9f678cca'  -- drip()
SEL_MKR_TO_SKY              = '\xab89605a'  -- mkrToSky(address,uint256)
SEL_LSE_OPEN                = '\x690e7c09'  -- open(uint256)
SEL_LSE_LOCK                = '\x6c3dead4'  -- lock(address,uint256,uint256,uint16)
SEL_LSE_FREE                = '\xbf0700fe'  -- free(address,uint256,address,uint256)
SEL_LSE_DRAW                = '\x7abdf250'  -- draw(address,uint256,address,uint256)
SEL_LSE_WIPE                = '\xc3b6cb4b'  -- wipe(address,uint256,uint256)
SEL_PSM_SELL_GEM            = '\x95991276'  -- sellGem(address,uint256)
SEL_PSM_BUY_GEM             = '\x8d7ef9bb'  -- buyGem(address,uint256)
SEL_SPBEAM_SET              = '\x474d857f'  -- set((bytes32,uint256)[])
SEL_UPGRADE_TO_AND_CALL     = '\x4f1ef286'  -- upgradeToAndCall(address,bytes)
-- ===== Addresses (Ethereum, chain 1) =====
ETH_USDS                    = '\xdc035d45d973e3ec169d2276ddab16f1e407384f'
ETH_USDS_IMP                = '\x1923dfee706a8e78157416c29cbccfde7cdf4102'
ETH_USDS_JOIN               = '\x3c0f895007ca717aa01c8693e59df1e8c3777feb'
ETH_DAI_USDS                = '\x3225737a9bbb6473cb4a45b7244aca2befdb276a'
ETH_SUSDS                   = '\xa3931d71877c0e7a3148cb7eb4463524fec27fbd'
ETH_STUSDS                  = '\x99cd4ec3f88a45940936f469e4bb72a2a701eeb9'
ETH_SKY                     = '\x56072c95faa701256059aa122697b133aded9279'
ETH_MKR                     = '\x9f8f72aa9304c8b593d555f12ef6589cc3a579a2'
ETH_MKR_SKY                 = '\xa1ea1ba18e88c381c724a75f23a130420c403f9a'
ETH_LOCKSTAKE_ENGINE        = '\xce01c90de7fd1bcfa39e237fe6d8d9f569e8a6a3'
ETH_LOCKSTAKE_SKY           = '\xf9a9cfd3229e985b91f99bc866d42938044ffa1c'
ETH_LOCKSTAKE_CLIP          = '\x836f56750517b1528b5078cba4ac4b94fbe4a399'
ETH_LOCKSTAKE_ENGINE_V1     = '\x2b16c07d5fd5cc701a0a871eae2aad6da5fc8f12'
ETH_REWARDS_LSSKY_USDS      = '\x38e4254bd82ed5ee97cd1c4278faae748d998865'
ETH_REWARDS_USDS_SKY        = '\x0650caf159c5a49f711e8169d4336ecb9b950275'
ETH_LITE_PSM_USDC_A         = '\xf6e72db5454dd049d0788e411b06cfaf16853042'
ETH_USDS_PSM_WRAPPER        = '\xa188eec8f81263234da3622a406892f3d630f98c'
ETH_SPBEAM                  = '\x36b072ed8afe665e3aa6daba79decbec63752b22'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify-verified ABI of each listed address (implementation ABI for the three proxies). Cross-checked against live `eth_getLogs` in the last 10k blocks: DaiUsds `UsdsToDai` (544) / `DaiToUsds` (300); UsdsJoin `Join` (2,965) / `Exit` (2,604); sUSDS `Drip` (995), `Withdraw` (592), `Deposit` (403), `Referral` (35); stUSDS `Drip`/`Deposit`/`Withdraw`/`Referral`; LitePSM `BuyGem` (4,323), `SellGem` (2,920), `Trim`, `Fill`; LockstakeEngine `GetReward`, `Lock`, `Free`, `SelectFarm`, `Open`; MkrSky `MkrToSky` (23 in 400k blocks). The DaiJoin LibNote layout (`topic1` = caller) was read from a live UsdsPsmWrapper exit.
- **Addresses:** ChainLog keys (on-chain `count()` = 520) and existence-checked via `eth_getCode`. Proxy implementations read from the EIP-1967 slot. `MkrSky.rate()` = 24000, `MkrSky.fee()` = 0.05e18, `LockstakeEngine.ilk()` = `stUSDS.ilk()` = `LSEV2-SKY-A`, `LockstakeEngine.fee()` = 0, `Splitter.farm()` = `REWARDS_LSSKY_USDS` read live.
- **Chain coverage:** `eth_getCode` for USDS, sUSDS and SKY (Ethereum literals and every L2 literal) on all nine chains.
- **Unverified:** `MCD_SBEBEAM` topics and selectors (no published ABI). Not listed.

Authoritative sources:
- [sky-ecosystem/usds](https://github.com/sky-ecosystem/usds) · [sky-ecosystem/sdai (sUSDS)](https://github.com/sky-ecosystem/sdai) · [sky-ecosystem/stusds](https://github.com/sky-ecosystem/stusds)
- [sky-ecosystem/lockstake](https://github.com/sky-ecosystem/lockstake) · [sky-ecosystem/endgame-toolkit](https://github.com/sky-ecosystem/endgame-toolkit) · [sky-ecosystem/dss-lite-psm](https://github.com/sky-ecosystem/dss-lite-psm) · [sky-ecosystem/sp-beam](https://github.com/sky-ecosystem/sp-beam)
- [Sky ChainLog (JSON)](https://chainlog.sky.money/api/mainnet/active.json) · [Sky developer docs](https://developers.skyeco.com/) · [sky-ecosystem/sky-protocol-info](https://github.com/sky-ecosystem/sky-protocol-info)
- Explorer: [Etherscan](https://etherscan.io/token/0xdC035D45d973E3EC169d2276DDab16f1e407384F) · ABIs: [Sourcify](https://sourcify.dev/)

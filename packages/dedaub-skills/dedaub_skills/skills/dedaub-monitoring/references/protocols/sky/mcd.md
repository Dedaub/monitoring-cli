# Sky (formerly MakerDAO) MCD Core — Topics, Selectors, Addresses (Ethereum)

**Status:** verified against live Ethereum RPC, the on-chain ChainLog (`0xdA0Ab1e0017DEbCd72Be8599041a2aa3bA7e740F`, version `1.20.21`, 520 keys) and Sourcify-verified ABIs on 2026-10-30.
**Scope:** the Multi-Collateral Dai (MCD / "dss") engine: Vat, Dai, joins, Jug, Pot, Spotter, OSM, Dog + Clipper liquidations, Vow, the surplus path (Kicker → Splitter → Flapper), Flopper, End/ESM/Cure shutdown, DssFlash, CDP manager, risk automation, allocator vaults and governance. Topics and selectors are chain-agnostic. Addresses are Ethereum-only (chain ID 1). **The MCD core exists on Ethereum only**; it is absent on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc (`eth_getCode` = `0x` for the Vat, ChainLog and Dai literals on all eight). USDS, sUSDS, SKY and the PSM are in [usds.md](usds.md). Bridged tokens are in [l2.md](l2.md).

MCD is a set of **immutable, non-proxy** contracts. Governance changes behaviour by `rely`/`deny` (the `wards` auth pattern) and by `file(...)` parameter writes. All of these go through `DSPause` (`MCD_PAUSE`) and run as `MCD_PAUSE_PROXY` (`0xBE8E3e36…`), which is a ward on every core contract. A new collateral type ("ilk") adds a new GemJoin + Clipper + oracle, never a new Vat.

**The Vat is the ledger.** Every vault change, every DAI/USDS mint, every liquidation and every surplus transfer is a Vat call. The Vat and the older LibNote contracts (Dai, joins, Jug, Pot, Vow, Pause) emit **anonymous** logs: `topic0` is the 4-byte function selector, left-aligned and zero-padded to 32 bytes. Filter these on `(emitter, topic0 = selector‖0…0)`. Newer modules (Dog, Clipper, Spotter, End, Splitter, Flapper, LitePSM, Lockstake) emit normal named events.

---

## 0. Contract families & versions

| Family | Contracts | Notes |
|--------|-----------|-------|
| Accounting core | Vat, Dai, DaiJoin, GemJoin (one per ilk), Jug, Pot, Spotter, OSM (one per price feed) | 2019 deployment. Immutable. Anonymous note logs. |
| Liquidations 2.0 | Dog (one), Clipper (one per ilk), StairstepExponentialDecrease calc (one per ilk), ClipperMom | Replaced Cat/Flipper in 2021. Named events. |
| System balance | Vow, Kicker, Splitter, FlapperUniV2SwapOnly ("Smart Burn Engine"), Flopper | Kicker took over `flap` from the Vow. Surplus buys SKY on Uniswap V2 and pays the staking farm. |
| Shutdown | End, ESM, Cure | Global settlement. Never fired on the 2019 deployment. |
| Liquidity | DssFlash, LitePSM (see [usds.md](usds.md)) | Flash mint of DAI up to `max`. |
| Allocation | AllocatorVault + AllocatorBuffer (one pair per Star / "Prime"), AllocatorRegistry, AllocatorRoles, D3MHub (legacy direct deposits) | Allocator ilks hold most of the debt (Spark, Grove/Bloom, Obex, Prysm…). |
| Risk automation | DssAutoLine (`MCD_IAM_AUTO_LINE`), LineMom, OsmMom, ClipperMom, emergency spells (`EMSP_*`) | Mom contracts bypass the Pause delay for emergency actions. |
| Governance | Chief (SKY), DSPause, DSPauseProxy, ChainLog, IlkRegistry, VoteDelegateFactory, StarGuard (one per Star) | Chief V3 votes with SKY since the 2025 governance upgrade. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Vat (anonymous note — `topic0` = selector left-aligned)

The Vat declares `LogNote(bytes4 indexed sig, bytes32 indexed arg1, bytes32 indexed arg2, bytes32 indexed arg3, bytes data) anonymous`. Its formal hash `0xd3ff30f94bb4ebb4f3d773ea26b6efc7328b9766f99f19dff6f01392138be46d` **never appears** in a log. `topic1..3` are the first three call arguments (addresses left-padded to 32 bytes). `data` holds the full calldata.

| topic0 (selector left-aligned) | Call | Meaning |
|-------------------------------|------|---------|
| `0x7608870300000000000000000000000000000000000000000000000000000000` | `frob(bytes32,address,address,address,int256,int256)` | vault change. topic1 = ilk, topic2 = urn (u), topic3 = gem source (v). `dink`/`dart` are in `data` |
| `0x870c616d00000000000000000000000000000000000000000000000000000000` | `fork(bytes32,address,address,int256,int256)` | move collateral + debt between two urns |
| `0x7bab3f4000000000000000000000000000000000000000000000000000000000` | `grab(bytes32,address,address,address,int256,int256)` | liquidation seizure (called by Dog) or End. topic1 = ilk, topic2 = urn |
| `0xb65337df00000000000000000000000000000000000000000000000000000000` | `fold(bytes32,address,int256)` | rate accrual. Jug.drip calls it |
| `0xf24e23eb00000000000000000000000000000000000000000000000000000000` | `suck(address,address,uint256)` | unbacked mint of internal DAI. topic1 = debit (u, usually Vow), topic2 = credit (v) |
| `0xf37ac61c00000000000000000000000000000000000000000000000000000000` | `heal(uint256)` | Vow cancels surplus against bad debt |
| `0x7cdd3fde00000000000000000000000000000000000000000000000000000000` | `slip(bytes32,address,int256)` | change a user's free gem balance. joins call it |
| `0x6111be2e00000000000000000000000000000000000000000000000000000000` | `flux(bytes32,address,address,uint256)` | move free gem between users |
| `0xbb35783b00000000000000000000000000000000000000000000000000000000` | `move(address,address,uint256)` | move internal DAI (rad). Most frequent Vat log |
| `0xa3b22fc400000000000000000000000000000000000000000000000000000000` | `hope(address)` | grant `can` permission |
| `0xdc4d20fa00000000000000000000000000000000000000000000000000000000` | `nope(address)` | revoke `can` permission |
| `0x1a0b287e00000000000000000000000000000000000000000000000000000000` | `file(bytes32,bytes32,uint256)` | parameter change (`line`, `spot`, `dust`) |
| `0x29ae811400000000000000000000000000000000000000000000000000000000` | `file(bytes32,uint256)` | parameter change (`line`, `spot`, `dust`) |
| `0x3b66319500000000000000000000000000000000000000000000000000000000` | `init(bytes32)` | new ilk |
| `0x6924500900000000000000000000000000000000000000000000000000000000` | `cage()` | shutdown |
| `0x65fae35e00000000000000000000000000000000000000000000000000000000` | `rely(address)` | add ward |
| `0x9c52a7f100000000000000000000000000000000000000000000000000000000` | `deny(address)` | remove ward |

### 1.2 LibNote contracts (Dai, DaiJoin, GemJoin, Jug, Pot, Vow) — anonymous note

These declare `LogNote(bytes4 indexed sig, address indexed usr, bytes32 indexed arg1, bytes32 indexed arg2, bytes data) anonymous` (formal hash `0xd3d8bec38a91a5f4411247483bc030a174e77cda9c0351924c759f41453aa5e8`, never emitted). Here `topic1` = `msg.sender`, `topic2..3` = the first two arguments. The same padded selector means different things on different emitters, so always key on the emitter.

| topic0 (selector left-aligned) | Emitter → call | Meaning |
|-------------------------------|----------------|---------|
| `0x3b4da69f00000000000000000000000000000000000000000000000000000000` | DaiJoin / GemJoin → `join(address,uint256)` | DaiJoin: burn ERC-20 DAI into Vat DAI. GemJoin: lock collateral token into the Vat. |
| `0xef693bed00000000000000000000000000000000000000000000000000000000` | DaiJoin / GemJoin → `exit(address,uint256)` | DaiJoin: mint ERC-20 DAI out of the Vat. GemJoin: release collateral. |
| `0x44e2a5a800000000000000000000000000000000000000000000000000000000` | Jug → `drip(bytes32)` | Accrue stability fee for one ilk. topic3 = ilk. |
| `0x9f678cca00000000000000000000000000000000000000000000000000000000` | Pot → `drip()` | Accrue DSR. |
| `0x049878f300000000000000000000000000000000000000000000000000000000` | Pot → `join(uint256)` | Deposit into DSR (pie units). |
| `0x7f8661a100000000000000000000000000000000000000000000000000000000` | Pot → `exit(uint256)` | Withdraw from DSR (pie units). |
| `0x697efb7800000000000000000000000000000000000000000000000000000000` | Vow → `fess(uint256)` | Queue bad debt (Dog calls it on every `bark`). |
| `0xd7ee674b00000000000000000000000000000000000000000000000000000000` | Vow → `flog(uint256)` | Release queued debt. |
| `0xf37ac61c00000000000000000000000000000000000000000000000000000000` | Vow → `heal(uint256)` | Cancel surplus against debt (Vow also triggers Vat `heal`). |
| `0xbbbb0d7b00000000000000000000000000000000000000000000000000000000` | Vow → `flop()` | Start a debt auction (Flopper). |
| `0x1a0b287e00000000000000000000000000000000000000000000000000000000` | Jug → `file(bytes32,bytes32,uint256)` | Set `duty` (stability fee) for an ilk. |
| `0x29ae811400000000000000000000000000000000000000000000000000000000` | Pot / Jug / Vow → `file(bytes32,uint256)` | Pot: set `dsr`. Jug: set `base`. |
| `0x65fae35e00000000000000000000000000000000000000000000000000000000` | any LibNote contract → `rely(address)` | Add a ward. |
| `0x9c52a7f100000000000000000000000000000000000000000000000000000000` | any LibNote contract → `deny(address)` | Remove a ward. |

`DSPause` uses the older DSNote variant `LogNote(bytes4 indexed sig, address indexed guy, bytes32 indexed foo, bytes32 indexed bar, uint256 wad, bytes fax) anonymous`. Its live topic0 values are also padded selectors: `plot` = `0x46d2fbbb00…`, `exec` = `0x168ccd6700…`, `drop` = `0x162c7de300…` (`foo` = spell `usr`, `bar` = `tag`).

### 1.3 Dai (ERC-20, `0x6B17…1d0F`)

| topic0 | Event |
|--------|-------|
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed src, address indexed guy, uint256 wad)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed src, address indexed dst, uint256 wad)` |

Mint and burn are `Transfer` from/to `0x0`. `rely`/`deny` use the LibNote topics in §1.2.

### 1.4 Liquidations — Dog, Clipper, calc

| topic0 | Event |
|--------|-------|
| `0x85258d09e1e4ef299ff3fc11e74af99563f022d21f3f940db982229dc2a3358c` | `Bark(bytes32 indexed ilk, address indexed urn, uint256 ink, uint256 art, uint256 due, address clip, uint256 indexed id)` |
| `0x2308ed18a14e800c39b86eb6ea43270105955ca385b603b64eca89f98ae8fbda` | `Cage()` |
| `0x54f095dc7308776bf01e8580e4dd40fd959ea4bf50b069975768320ef8d77d8a` | `Digs(bytes32 indexed ilk, uint256 rad)` |
| `0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7` | `File(bytes32 indexed what, uint256 data)` |
| `0x8fef588b5fc1afbf5b2f06c1a435d513f208da2e6704c3d8f0e0ec91167066ba` | `File(bytes32 indexed what, address data)` |
| `0x851aa1caf4888170ad8875449d18f0f512fd6deb2a6571ea1a41fb9f95acbcd1` | `File(bytes32 indexed ilk, bytes32 indexed what, uint256 data)` |
| `0x4ff2caaa972a7c6629ea01fae9c93d73cc307d13ea4c369f9bbbb7f9b7e9461d` | `File(bytes32 indexed ilk, bytes32 indexed what, address clip)` |

| topic0 | Event |
|--------|-------|
| `0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7` | `File(bytes32 indexed what, uint256 data)` |
| `0x8fef588b5fc1afbf5b2f06c1a435d513f208da2e6704c3d8f0e0ec91167066ba` | `File(bytes32 indexed what, address data)` |
| `0x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8` | `Kick(uint256 indexed id, uint256 top, uint256 tab, uint256 lot, address indexed usr, address indexed kpr, uint256 coin)` |
| `0x275de7ecdd375b5e8049319f8b350686131c219dd4dc450a08e9cf83b03c865f` | `Redo(uint256 indexed id, uint256 top, uint256 tab, uint256 lot, address indexed usr, address indexed kpr, uint256 coin)` |
| `0x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1` | `Take(uint256 indexed id, uint256 max, uint256 price, uint256 owe, uint256 tab, uint256 lot, address indexed usr)` |
| `0x2c5d2826eb5903b8fc201cf48094b858f42f61c7eaac9aaf43ebed490138144e` | `Yank(uint256 id)` |

Every per-ilk Clipper and the Lockstake Clipper (see [usds.md](usds.md)) emit the **same** topics. `Kick.usr`/`Take.usr` is the urn owner (Kick) or the collateral receiver (Take). `kpr` gets the keeper incentive. The calc contract only emits `File(bytes32,uint256)` (`0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7`).

### 1.5 Prices — Spotter, OSM

| topic0 | Event |
|--------|-------|
| `0xdfd7467e425a8107cfd368d159957692c25085aacbcf5228ce08f10f2146486e` | `Poke(bytes32 ilk, bytes32 val, uint256 spot)` |

| topic0 | Event |
|--------|-------|
| `0x296ba4ca62c6c21c95e828080cb8aec7481b71390585605300a8a76f9e95b527` | `LogValue(bytes32 val)` |

`Poke.val` is the OSM current price (`bytes32`, wad). `Poke.spot` is the liquidation price (ray) that the Vat stores.

### 1.6 Surplus and debt — Splitter, Flapper, Flopper, Kicker

| topic0 | Event |
|--------|-------|
| `0x8b2f35c645f75532175a00d9b4565154e45c8eb57ee0155e03d0958f3a4d4b89` | `Cage(uint256 rad)` |
| `0xe6dde59cbc017becba89714a037778d234a84ce7f0a137487142a007e580d609` | `Kick(uint256 tot, uint256 lot, uint256 pay)` |

| topic0 | Event |
|--------|-------|
| `0xffacc3c568d281ed9c440365e37ddd4f3cc5ce8e5ccac4b1c3b178f10c5531f3` | `Exec(uint256 lot, uint256 bought)` |

| topic0 | Event |
|--------|-------|
| `0x7e8881001566f9f89aedb9c5dc3d856a2b81e5235a8196413ed484be91cc0df6` | `Kick(uint256 id, uint256 lot, uint256 bid, address indexed gal)` |

The Kicker emits only `Rely`/`Deny`/`File`. Its `flap()` calls `Vat.suck(vow, splitter, …)` and then `Splitter.kick`. `Splitter.Kick.lot` goes to the Flapper (SKY buy-back). `Splitter.Kick.pay` goes to the Splitter `farm` (the staked-SKY USDS reward farm). Flapper and Splitter `Kick` fire in the same transaction. The Flopper `Kick` and the Clipper `Kick` have different signatures and different topic0 values.

### 1.7 Shutdown — End, ESM, Cure

| topic0 | Event |
|--------|-------|
| `0x2308ed18a14e800c39b86eb6ea43270105955ca385b603b64eca89f98ae8fbda` | `Cage()` |
| `0x4a9efa0a0e3f548761a6924fe06ac5cb94ecdbc08b10d855bbcc04e37c4910db` | `Cage(bytes32 indexed ilk)` |
| `0x888c7c01b06fd8004523e2bc9a274be1feaa9f03579ae5f568061dac078793c9` | `Cash(bytes32 indexed ilk, address indexed usr, uint256 wad)` |
| `0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7` | `File(bytes32 indexed what, uint256 data)` |
| `0x8fef588b5fc1afbf5b2f06c1a435d513f208da2e6704c3d8f0e0ec91167066ba` | `File(bytes32 indexed what, address data)` |
| `0x8d1d5ae676a6db1f6f14414f8a6c78941bbfb700fe3f3be6d3245f26c2f2d550` | `Flow(bytes32 indexed ilk)` |
| `0xf26f2b994a5e16f0960958e62541681f9e3e84d4caac2e487d25e0c75243f0d8` | `Free(bytes32 indexed ilk, address indexed usr, uint256 ink)` |
| `0x47a981d8cbc0f6df64c9be4ce0a423071a088bd46c549bbd11a4d566e031fe0c` | `Pack(address indexed usr, uint256 wad)` |
| `0xa05b7b56166c25efbac063da905f9ea6aa1dc5101f95b43c7a838aace979ab59` | `Skim(bytes32 indexed ilk, address indexed urn, uint256 wad, uint256 art)` |
| `0xbfa2310a8897203a59922debd0db38279196d8de5050df84608e2bb3e7790f69` | `Skip(bytes32 indexed ilk, uint256 indexed id, address indexed usr, uint256 tab, uint256 lot, uint256 art)` |
| `0xfc67e20caaffa015d51f696df8ea5c273ba269c69bdc2ec31c1334d01286eaa4` | `Snip(bytes32 indexed ilk, uint256 indexed id, address indexed usr, uint256 tab, uint256 lot, uint256 art)` |
| `0x4df15159e645ba7d02cadde0bc937abef5ad0134623c00de50a31750b85978b9` | `Thaw()` |

| topic0 | Event |
|--------|-------|
| `0x74269424d52f84560e5738dd2769b61b0e04d5c87c87ca043a1e005e0722a678` | `DenyProxy(address indexed base, address indexed pause)` |
| `0x14c539ef1ff6ef515371448cd46419fd75ebb8698b7f6644c4f66b03b0327085` | `Fire()` |
| `0xb4e09949657f21548b58afe74e7b86cd2295da5ff1598ae1e5faecb1cf19ca95` | `Join(address indexed usr, uint256 wad)` |

| topic0 | Event |
|--------|-------|
| `0x2308ed18a14e800c39b86eb6ea43270105955ca385b603b64eca89f98ae8fbda` | `Cage()` |
| `0xdbc628f334a9c7bf46419d864ca89e17415703fa12263f2284d94cc9b75b659e` | `Drop(address indexed src)` |
| `0x2b07094bdf192088dc9d18c2c3a2b11b7f1df5d6f3460343964c059221e3f048` | `Lift(address indexed src)` |
| `0xe90dfdfab1f4f73aeba2ef47b366c3c4118d3c38cab46bb993f7ed257a61c8c0` | `Load(address indexed src)` |

`End.Cage()`, `ESM.Fire()` and `Dog.Cage()` mean global settlement. Treat any of them as a critical alert.

### 1.8 Flash mint — DssFlash

| topic0 | Event |
|--------|-------|
| `0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0` | `FlashLoan(address indexed receiver, address token, uint256 amount, uint256 fee)` |
| `0xbca56acc64a74a4c131755895cf7f72fc3f9e39af64241f7ad0f77e86f41ada9` | `VatDaiFlashLoan(address indexed receiver, uint256 amount, uint256 fee)` |

### 1.9 CDP manager

| topic0 | Event |
|--------|-------|
| `0xd6be0bc178658a382ff4f91c8c68b542aa6b71685b8fe427966b87745c3ea7a2` | `NewCdp(address indexed usr, address indexed own, uint256 indexed cdp)` |

`frob`/`flux`/`move` on the manager produce no manager event. Read the Vat note log instead. The urn address of a manager CDP is the `UrnHandler` returned by `urns(cdp)`.

### 1.10 Risk automation — DssAutoLine, LineMom, ClipperMom

| topic0 | Event |
|--------|-------|
| `0x2696a4655cbecf97fdc3c9c74f3eba424f2e404790389c2b4e31d2e32129c7dc` | `Exec(bytes32 indexed ilk, uint256 line, uint256 lineNew)` |
| `0xa56fb2a6d4126f324526f0668c53927c0cd8e08f41ba0fe0f2d6090a84bc75c8` | `Remove(bytes32 indexed ilk)` |
| `0x1326c8f8fb452b5d26a2406d96790efbb561bf5d2686986a30a5cd847eefc673` | `Setup(bytes32 indexed ilk, uint256 line, uint256 gap, uint256 ttl)` |

| topic0 | Event |
|--------|-------|
| `0x74ceb2982b813d6b690af89638316706e6acb9a48fced388741b61b510f165b7` | `AddIlk(bytes32 indexed ilk)` |
| `0xf6b820341ae6c418a12253ec147337ed8655d2f23fe6f80f725d1011c769e3e8` | `DelIlk(bytes32 indexed ilk)` |
| `0x2f7b3d4e0422d010112e7368dfc4d711470e4452a7120bd8c6264864d4bc0111` | `Wipe(bytes32 indexed ilk, uint256 line)` |

| topic0 | Event |
|--------|-------|
| `0x01a1de957c616c7c99b8f1a1158174e9bd174302795cdbcfbfe0bc760d418c6f` | `SetBreaker(address indexed clip, uint256 level)` |

### 1.11 Allocation — AllocatorVault, AllocatorBuffer, AllocatorRoles, AllocatorRegistry, D3MHub

| topic0 | Event |
|--------|-------|
| `0x7ffa12f2611233f19bb229a71c5d8224cb37373555ab6754b65aef59ea26831d` | `Draw(address indexed sender, uint256 wad)` |
| `0x2d2c7da251295f4d722a8ddaf337627952c957ce21b2757c852e47fe81b3a2af` | `Wipe(address indexed sender, uint256 wad)` |

| topic0 | Event |
|--------|-------|
| `0x6e11fb1b7f119e3f2fa29896ef5fdf8b8a2d0d4df6fe90ba8668e7d8b2ffa25e` | `Approve(address indexed asset, address indexed spender, uint256 amount)` |

| topic0 | Event |
|--------|-------|
| `0x1666ce5bfc515e272162696dc7b908334194bcf1f921f457b5406d2e00ed9e6e` | `SetIlkAdmin(bytes32 indexed ilk, address user)` |
| `0xe459bcd103dbe8b0e6a5d530849ce830cfccf2828693cd58ae90801afd24fab5` | `SetRoleAction(bytes32 indexed ilk, uint8 indexed role, address indexed target, bytes4 sig, bool enabled)` |
| `0x830afcb2e8fda1fe33202a89fe3abf4fc4205f546f29092f144c19e34aab3cea` | `SetUserRole(bytes32 indexed ilk, address indexed who, uint8 indexed role, bool enabled)` |

| topic0 | Event |
|--------|-------|
| `0x4a9efa0a0e3f548761a6924fe06ac5cb94ecdbc08b10d855bbcc04e37c4910db` | `Cage(bytes32 indexed ilk)` |
| `0x4c5fe0002a1fb38c42a2194fead84961e86a4f4602893768507bce8d41914ccd` | `Cull(bytes32 indexed ilk, uint256 ink, uint256 art)` |
| `0xa3ae4ef58d1a6c0820e2b8f53fdf7b8261d36962b6755d261c428ae604a193bf` | `Exit(bytes32 indexed ilk, address indexed usr, uint256 amt)` |
| `0x424e88d5869b9c852dcebad351c9782779b49b6fb722e88c3fbd5568e7ad1e9f` | `Fees(bytes32 indexed ilk, uint256 amt)` |
| `0x2a18a8dfd750909275ab34a50306e60baeb3b7be1cbf6aa09180b38c2a4451f6` | `NoOp(bytes32 indexed ilk)` |
| `0x6ae62e7d79a6ec3ae01d3104d54b52e5412bb468cae3d53be82d0d377b01c9c2` | `Uncull(bytes32 indexed ilk, uint256 wad)` |
| `0x9aad384963fed57d8fdddbe4a5173b7461e48294ce28a638da5af96462504db8` | `Unwind(bytes32 indexed ilk, uint256 amt)` |
| `0xf00f80805ef849c3a6ee6cc8727b4eeddb2efee7e404e4ee96f89dfd076e3693` | `Wind(bytes32 indexed ilk, uint256 amt)` |

`AllocatorVault.Draw` mints USDS debt for a Star into its buffer. `Wipe` repays it. `AllocatorBuffer.Approve` and `Escrow.Approve` (see [l2.md](l2.md)) share topic0 `0x6e11fb1b7f119e3f2fa29896ef5fdf8b8a2d0d4df6fe90ba8668e7d8b2ffa25e`.

### 1.12 Governance and registries — Chief, ChainLog, IlkRegistry, VoteDelegateFactory, StarGuard

| topic0 | Event |
|--------|-------|
| `0xbde4476d3fa00c45be48daa5d230f4dbcd5d571237f236d9e24793a4468edbc7` | `Etch(bytes32 indexed slate, address[] yays)` |
| `0xce6c5af8fd109993cb40da4d5dc9e4dd8e61bc2e48f1e3901472141e4f56f293` | `Free(address indexed usr, uint256 wad)` |
| `0x02ac8168caf2f254b394bd39e19417c5c28124ab89c9bc2d44921b19808e2669` | `Launch()` |
| `0x2b07094bdf192088dc9d18c2c3a2b11b7f1df5d6f3460343964c059221e3f048` | `Lift(address indexed whom)` |
| `0x625fed9875dada8643f2418b838ae0bc78d9a148a18eee4ee1979ff0f3f5d427` | `Lock(address indexed usr, uint256 wad)` |
| `0xc1eff9d9e2ab8a2b29706e0c2818cd78972e60f1ce84c268a77005b0bece97c4` | `Vote(address indexed usr, bytes32 indexed slate)` |

| topic0 | Event |
|--------|-------|
| `0x236084b20b5721ddf3e40ed45b570186612a08edec64abae6894b60f315c54bc` | `RemoveAddress(bytes32 key)` |
| `0xcf0ecd10d1399d98978051da48095f368d6f1fa3292d5fc09135b92aa2a4d733` | `UpdateAddress(bytes32 key, address addr)` |
| `0xc7d51f843aa4e748744967527c18b55884fbbd978794939a53e6de466659169e` | `UpdateIPFS(string ipfs)` |
| `0x6ce764b6ccabce70dd110fb75895ead7988d54d58fef7e8ee13a32d04c21f3b9` | `UpdateSha256sum(string sha256sum)` |
| `0xc96e830455c6cd482ced2b3637de7e7f3c87ed0f17eff0999ba5e262ea44c67b` | `UpdateVersion(string version)` |

| topic0 | Event |
|--------|-------|
| `0x74ceb2982b813d6b690af89638316706e6acb9a48fced388741b61b510f165b7` | `AddIlk(bytes32 ilk)` |
| `0x42f3b824eb9d522b949ff3d8f70db1872c46f3fc68b6df1a4c8d6aaebfcb6796` | `RemoveIlk(bytes32 ilk)` |
| `0x176e1433f84712b82b982cc7a7b738797bd98e17b0882a6edc1a9a89e3dcbdfa` | `UpdateIlk(bytes32 ilk)` |

| topic0 | Event |
|--------|-------|
| `0x2187b96b95fffefab01016c852705bc8ec76d1ea17dd5bffef25fd7136633644` | `CreateVoteDelegate(address indexed usr, address indexed voteDelegate)` |

| topic0 | Event |
|--------|-------|
| `0xdbc628f334a9c7bf46419d864ca89e17415703fa12263f2284d94cc9b75b659e` | `Drop(address indexed addr)` |
| `0xd074dc2801f2a4136a42e9fae80ca2c91228872a7a4996e6b47e10879559c0bf` | `Exec(address indexed addr)` |
| `0x0f870ae93c797c0a219447673e1027ae91aaa67bc1ad8f3951235edfc925f5be` | `Plot(address indexed addr, bytes32 tag, uint256 deadline)` |

`Chief.Lift` and `Cure.Lift` share topic0 `0x2b07094bdf192088dc9d18c2c3a2b11b7f1df5d6f3460343964c059221e3f048`. `IlkRegistry` events have **no indexed** fields. `ChainLog.UpdateAddress` is the cleanest "contract rotated" signal for the whole protocol.

### 1.13 Shared auth and parameter topics (newer modules)

| topic0 | Event | Emitters |
|--------|-------|----------|
| `0xdd0e34038ac38b2a1ce960229778ac48a8719bc900b6c4f8d0475c6e8b385a60` | `Rely(address indexed usr)` | Dog, Clipper, End, Splitter, Flapper, Kicker, Cure, LitePSM, USDS, sUSDS, SKY, Lockstake, bridges… |
| `0x184450df2e323acec0ed3b5c7531b81f9b4cdef7914dfd4c0a4317416bb5251b` | `Deny(address indexed usr)` | same set |
| `0xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7` | `File(bytes32 indexed what, uint256 data)` | Dog, Clipper, calc, End, ESM, Splitter, Flapper, Kicker, LitePSM, sUSDS… |
| `0x8fef588b5fc1afbf5b2f06c1a435d513f208da2e6704c3d8f0e0ec91167066ba` | `File(bytes32 indexed what, address data)` | Dog, Clipper, End, Splitter, Flapper, bridges… |
| `0x851aa1caf4888170ad8875449d18f0f512fd6deb2a6571ea1a41fb9f95acbcd1` | `File(bytes32 indexed ilk, bytes32 indexed what, uint256 data)` | Dog, D3MHub, SPBEAM |
| `0x4ff2caaa972a7c6629ea01fae9c93d73cc307d13ea4c369f9bbbb7f9b7e9461d` | `File(bytes32 indexed ilk, bytes32 indexed what, address data)` | Dog (`clip`), D3MHub, AllocatorRegistry |

A new ward on a core contract is a critical change. Watch `Rely` on every address in §3 and the LibNote `rely` padded selector on the Vat/Dai/Jug/Pot/Vow.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Vat

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x76088703` | `frob(bytes32,address,address,address,int256,int256)` | ward-free. `msg.sender` must be the urn owner or hold `can`. dink/dart are signed |
| `0x870c616d` | `fork(bytes32,address,address,int256,int256)` | — |
| `0x7bab3f40` | `grab(bytes32,address,address,address,int256,int256)` | auth (Dog, End) |
| `0xb65337df` | `fold(bytes32,address,int256)` | auth (Jug) |
| `0xf24e23eb` | `suck(address,address,uint256)` | auth (Vow, Kicker, LitePSM, D3M) |
| `0xf37ac61c` | `heal(uint256)` | — |
| `0x7cdd3fde` | `slip(bytes32,address,int256)` | auth (joins) |
| `0x6111be2e` | `flux(bytes32,address,address,uint256)` | — |
| `0xbb35783b` | `move(address,address,uint256)` | — |
| `0xa3b22fc4` | `hope(address)` | — |
| `0xdc4d20fa` | `nope(address)` | — |
| `0x1a0b287e` | `file(bytes32,bytes32,uint256)` | — |
| `0x29ae8114` | `file(bytes32,uint256)` | — |
| `0x3b663195` | `init(bytes32)` | — |
| `0x69245009` | `cage()` | — |
| `0x65fae35e` | `rely(address)` | — |
| `0x9c52a7f1` | `deny(address)` | — |
| `0xd9638d36` | `ilks(bytes32)` | `(uint256,uint256,uint256,uint256,uint256)`. view. `(Art, rate, spot, line, dust)` |
| `0x2424be5c` | `urns(bytes32,address)` | `(uint256,uint256)`. view. `(ink, art)` |
| `0x214414d5` | `gem(bytes32,address)` | `(uint256)`. view |
| `0x6c25b346` | `dai(address)` | `(uint256)`. view |
| `0xf059212a` | `sin(address)` | `(uint256)`. view |
| `0x0dca59c1` | `debt()` | `(uint256)`. view |
| `0x2d61a355` | `vice()` | `(uint256)`. view |
| `0xbabe8a3f` | `Line()` | `(uint256)`. view |
| `0x957aa58c` | `live()` | `(uint256)`. view |

Normalised debt is `art`. Real debt in rad is `art × rate`. Units: wad = 1e18, ray = 1e27, rad = 1e45.

### 2.2 Dai and joins

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xa9059cbb` | `transfer(address,uint256)` | `(bool)` |
| `0x23b872dd` | `transferFrom(address,address,uint256)` | `(bool)` |
| `0x095ea7b3` | `approve(address,uint256)` | `(bool)` |
| `0x8fcbaf0c` | `permit(address,address,uint256,uint256,bool,uint8,bytes32,bytes32)` | DAI-style permit (`holder, spender, nonce, expiry, allowed, v, r, s`), not EIP-2612 |
| `0x40c10f19` | `mint(address,uint256)` | auth (DaiJoin) |
| `0x9dc29fac` | `burn(address,uint256)` | — |
| `0xb753a98c` | `push(address,uint256)` | — |
| `0xf2d5d56b` | `pull(address,uint256)` | — |
| `0xbb35783b` | `move(address,address,uint256)` | — |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x3b4da69f` | `join(address,uint256)` | burn ERC-20 DAI, credit Vat DAI to `usr` |
| `0xef693bed` | `exit(address,uint256)` | debit Vat DAI, mint ERC-20 DAI |
| `0x69245009` | `cage()` | — |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x3b4da69f` | `join(address,uint256)` | pull collateral, `vat.slip(+)` |
| `0xef693bed` | `exit(address,uint256)` | `vat.slip(-)`, send collateral |

### 2.3 Rates — Jug, Pot

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x44e2a5a8` | `drip(bytes32)` | `(uint256)`. permissionless. Calls `vat.fold` |
| `0x1a0b287e` | `file(bytes32,bytes32,uint256)` | auth. `duty` |
| `0x29ae8114` | `file(bytes32,uint256)` | auth. `base` |
| `0xd9638d36` | `ilks(bytes32)` | `(uint256,uint256)`. view. `(duty, rho)` |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x9f678cca` | `drip()` | `(uint256)`. permissionless |
| `0x049878f3` | `join(uint256)` | — |
| `0x7f8661a1` | `exit(uint256)` | — |
| `0x487bf082` | `dsr()` | `(uint256)`. view |
| `0xc92aecc4` | `chi()` | `(uint256)`. view |
| `0x20aba08b` | `rho()` | `(uint256)`. view |
| `0x0bebac86` | `pie(address)` | `(uint256)`. view |
| `0x2c69ed58` | `Pie()` | `(uint256)`. view |

### 2.4 Prices — Spotter, OSM

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x1504460f` | `poke(bytes32)` | permissionless |
| `0xd9638d36` | `ilks(bytes32)` | `(address,uint256)`. view. `(pip, mat)` |
| `0x495d32cb` | `par()` | `(uint256)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x18178358` | `poke()` | permissionless, once per `hop` |
| `0x59e02dd7` | `peek()` | `(bytes32,bool)`. view. whitelisted (`bud`) |
| `0x0e5a6c70` | `peep()` | `(bytes32,bool)`. view. next price, whitelisted |
| `0x07da68f5` | `stop()` | auth (OsmMom) |
| `0xbe9a6555` | `start()` | — |
| `0xac4c25b2` | `void()` | — |

### 2.5 Liquidations — Dog, Clipper

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xed998908` | `bark(bytes32,address,address)` | `(uint256)`. permissionless. Starts an auction for an unsafe urn |
| `0xc87193f4` | `digs(bytes32,uint256)` | auth (Clipper) |
| `0xd9638d36` | `ilks(bytes32)` | `(address,uint256,uint256,uint256)`. view. `(clip, chop, hole, dirt)` |
| `0xaf7cfeb1` | `Hole()` | `(uint256)`. view |
| `0xeda6e121` | `Dirt()` | `(uint256)`. view |
| `0x69245009` | `cage()` | — |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x898eb267` | `kick(uint256,uint256,address,address)` | `(uint256)`. auth (Dog) |
| `0x81a794cb` | `take(uint256,uint256,uint256,address,bytes)` | permissionless. `(id, amt, max, who, data)`. Non-empty `data` triggers `clipperCall` flash-callback on `who` |
| `0xd843416d` | `redo(uint256,address)` | permissionless reset of a stale auction |
| `0x26e027f1` | `yank(uint256)` | auth (End) |
| `0x0cbb5862` | `upchost()` | — |
| `0x5c622a0e` | `getStatus(uint256)` | `(bool,uint256,uint256,uint256)`. view. `(needsRedo, price, lot, tab)` |
| `0xb5f522f7` | `sales(uint256)` | `(uint256,uint256,uint256,address,uint96,uint256)`. view. `(pos, tab, lot, usr, tic, top)` |
| `0x0f560cd7` | `list()` | `(uint256[])`. view |
| `0x06661abd` | `count()` | `(uint256)`. view |
| `0xcfdd3302` | `kicks()` | `(uint256)`. view |
| `0x75f12b21` | `stopped()` | `(uint256)`. view. circuit-breaker level 0–3 |

### 2.6 Vow, Kicker, Splitter, Flapper, Flopper

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x697efb78` | `fess(uint256)` | auth |
| `0xd7ee674b` | `flog(uint256)` | — |
| `0xf37ac61c` | `heal(uint256)` | — |
| `0x2506855a` | `kiss(uint256)` | — |
| `0x0e01198b` | `flap()` | `(uint256)`. superseded by `Kicker.flap()` |
| `0xbbbb0d7b` | `flop()` | `(uint256)` |
| `0x69245009` | `cage()` | — |
| `0xd0adc35f` | `Sin()` | `(uint256)`. view |
| `0x2a1d2b3c` | `Ash()` | `(uint256)`. view |
| `0xc349d362` | `sump()` | `(uint256)`. view |
| `0xe4330545` | `dump()` | `(uint256)`. view |
| `0x68110b2f` | `bump()` | `(uint256)`. view |
| `0x1b8e8cfa` | `hump()` | `(uint256)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x0e01198b` | `flap()` | `(uint256)`. permissionless. Reverts unless surplus > `khump` |
| `0x581e5d7e` | `kbump()` | `(uint256)`. view |
| `0x20bc1c75` | `khump()` | `(int256)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xca40c419` | `kick(uint256,uint256)` | `(uint256)`. auth (Kicker) |
| `0xa2f91af2` | `cage(uint256)` | — |
| `0x44df8e70` | `burn()` | `(uint256)`. view. share to Flapper (wad) |
| `0xb0b8579b` | `hop()` | `(uint256)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xf873cb91` | `exec(uint256)` | auth (Splitter). Swap USDS → SKY on the Uniswap V2 pair |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xb7e9cd24` | `kick(address,uint256,uint256)` | `(uint256)`. auth (Vow) |
| `0x5ff3a382` | `dent(uint256,uint256,uint256)` | — |
| `0xc959c42b` | `deal(uint256)` | — |
| `0xfc7b6aee` | `tick(uint256)` | — |

### 2.7 Shutdown, flash, CDP manager

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x69245009` | `cage()` | auth (ESM / governance) |
| `0xe2702fdc` | `cage(bytes32)` | — |
| `0x38c6de40` | `snip(bytes32,uint256)` | — |
| `0x503ecf06` | `skip(bytes32,uint256)` | — |
| `0x89ea45d3` | `skim(bytes32,address)` | — |
| `0xc83062c6` | `free(bytes32)` | — |
| `0x5920375c` | `thaw()` | — |
| `0x4a10eaa6` | `flow(bytes32)` | — |
| `0x6ea42555` | `pack(uint256)` | — |
| `0xfe8507c6` | `cash(bytes32,uint256)` | — |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x049878f3` | `join(uint256)` | lock governance token toward `min` |
| `0x457094cc` | `fire()` | trigger shutdown when `Sum >= min` |
| `0x0715940e` | `denyProxy(address)` | — |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x5cffe9de` | `flashLoan(address,address,uint256,bytes)` | `(bool)`. ERC-3156, token = DAI |
| `0x3f03653f` | `vatDaiFlashLoan(address,uint256,bytes)` | `(bool)` |
| `0x6ac5db19` | `max()` | `(uint256)`. view |
| `0xd9d98ce4` | `flashFee(address,uint256)` | `(uint256)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x6090dec5` | `open(bytes32,address)` | `(uint256)` |
| `0xfcafcc68` | `give(uint256,address)` | — |
| `0x45e6bdcd` | `frob(uint256,int256,int256)` | — |
| `0x9bb8f838` | `flux(uint256,address,uint256)` | — |
| `0xf9f30db6` | `move(uint256,address,uint256)` | — |
| `0x7e348b7d` | `enter(address,uint256)` | — |
| `0x1b0dbf72` | `quit(uint256,address)` | — |
| `0xe50322a2` | `shift(uint256,uint256)` | — |
| `0x2726b073` | `urns(uint256)` | `(address)`. view. urn handler for a cdp |
| `0x8161b120` | `owns(uint256)` | `(address)`. view |

### 2.8 Risk automation and allocation

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xb5e98b3b` | `exec(bytes32)` | `(uint256)`. permissionless ceiling update |
| `0x2a48322d` | `setIlk(bytes32,uint256,uint256,uint256)` | auth |
| `0xc465f077` | `remIlk(bytes32)` | auth |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xd771aa58` | `wipe(bytes32)` | `(uint256)`. emergency `line` = 0, no delay |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x2145a7f3` | `setBreaker(address,uint256,uint256)` | auth |
| `0xaa85b638` | `tripBreaker(address)` | permissionless if the price drops more than `tolerance` in one OSM step |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x63c4f031` | `stop(bytes32)` | emergency OSM stop |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x3b304147` | `draw(uint256)` | auth (Star operator). Mint USDS debt into the buffer |
| `0xb38a1620` | `wipe(uint256)` | repay |
| `0xc5ce281e` | `ilk()` | `(bytes32)`. view |
| `0xedaafe20` | `buffer()` | `(address)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xb5e98b3b` | `exec(bytes32)` | permissionless rebalance of a D3M ilk |
| `0x8569cb59` | `exit(bytes32,address,uint256)` | — |
| `0xe2702fdc` | `cage(bytes32)` | — |
| `0xb6c5bb0d` | `cull(bytes32)` | — |
| `0x3d508951` | `uncull(bytes32)` | — |

### 2.9 Governance

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xdd467064` | `lock(uint256)` | — |
| `0xd8ccd0f3` | `free(uint256)` | — |
| `0x5123e1fa` | `etch(address[])` | `(bytes32)` |
| `0xa69beaba` | `vote(bytes32)` | — |
| `0xed081329` | `vote(address[])` | `(bytes32)` |
| `0x3c278bd5` | `lift(address)` | — |
| `0x01339c21` | `launch()` | — |
| `0xfe95a5ce` | `hat()` | `(address)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x46d2fbbb` | `plot(address,bytes32,bytes,uint256)` | auth (Chief `hat`) |
| `0x168ccd67` | `exec(address,bytes32,bytes,uint256)` | `(bytes)`. after `delay` |
| `0x162c7de3` | `drop(address,bytes32,bytes,uint256)` | — |
| `0x6a42b8f8` | `delay()` | `(uint256)`. view |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x21f8a721` | `getAddress(bytes32)` | `(address)`. view. revert if key is missing |
| `0x0f560cd7` | `list()` | `(bytes32[])`. view |
| `0x06661abd` | `count()` | `(uint256)`. view |
| `0x54fd4d50` | `version()` | `(string)`. view |
| `0xca446dd9` | `setAddress(bytes32,address)` | auth |

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x0f560cd7` | `list()` | `(bytes32[])`. view |
| `0xb64a097e` | `info(bytes32)` | `(string,string,uint256,uint256,address,address,address,address)`. view |
| `0xad677d0b` | `join(bytes32)` | `(address)`. view |
| `0x247c803f` | `xlip(bytes32)` | `(address)`. view |
| `0xa4903036` | `pip(bytes32)` | `(address)`. view |
| `0x41f0b723` | `gem(bytes32)` | `(address)`. view |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-10-30, and matched against `ChainLog.getAddress(key)` (key in the second column).

### 3.1 Core accounting

| Role | ChainLog key | Address | One-liner |
|------|--------------|---------|-----------|
| **Vat** | `MCD_VAT` | `0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B` | Core ledger. Total debt ≈ 11.81 B rad-DAI, `Line` ≈ 15.74 B on 2026-10-30. |
| **Dai** | `MCD_DAI` | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | ERC-20 DAI. |
| **DaiJoin** | `MCD_JOIN_DAI` | `0x9759A6Ac90977b93B58547b4A71c78317f391A28` | Vat DAI ↔ ERC-20 DAI. |
| **Jug** | `MCD_JUG` | `0x19c0976f590D67707E62397C87829d896Dc0f1F1` | Stability fees. |
| **Pot** | `MCD_POT` | `0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7` | Dai Savings Rate. |
| **Spotter** | `MCD_SPOT` | `0x65C79fcB50Ca1594B025960e539eD7A9a6D434A3` | Pushes OSM prices into the Vat. |
| **IlkRegistry** | `ILK_REGISTRY` | `0x5a464C28D19848f44199D003BeF5ecc87d090F87` | Ilk → join/clip/pip/gem lookup (35 ilks). |
| **ChainLog** | `CHANGELOG` | `0xdA0Ab1e0017DEbCd72Be8599041a2aa3bA7e740F` | On-chain address registry. Source of truth. |

### 3.2 Liquidations

| Role | ChainLog key | Address | One-liner |
|------|--------------|---------|-----------|
| **Dog** | `MCD_DOG` | `0x135954d155898D42C90D2a57824C690e0c7BEf1B` | Liquidation trigger (`bark`). |
| **ClipperMom** | `CLIPPER_MOM` | `0x79FBDF16b366DFb14F66cE4Ac2815Ca7296405A0` | Clipper circuit breaker. |
| Global clip breaker | `EMSP_GLOBAL_CLIP_BREAKER` | `0x828824dBC62Fba126C76E0Abe79AE28E5393C2cb` | Emergency spell: stop all Clippers. |
| CLIP_FAB / CALC_FAB | `CLIP_FAB` / `CALC_FAB` | `0x0716F25fBaAae9b63803917b6125c10c313dF663` / `0xE1820A2780193d74939CcA104087CADd6c1aA13A` | Factories for new Clippers / calcs. |

### 3.3 Live ilks (debt > 0 or ceiling > 0 on 2026-10-30; read from IlkRegistry + `Vat.ilks`)

| Ilk | Debt (≈ DAI) | Ceiling | GemJoin | Clipper | Oracle (pip) |
|-----|-------------|---------|---------|---------|--------------|
| `ALLOCATOR-SPARK-A` | 3,878 M | 5,361 M | — (no gem) | — | `0xc7B91C401C02B73CBdF424dFaaa60950d5040dB7` |
| `LITE-PSM-USDC-A` | 4,477 M | 5,553 M | — (LitePSM is its own join) | — | `0x77b68899b99b686f415d074278a9a16b336085a0` |
| `ALLOCATOR-BLOOM-A` | 1,558 M | 2,019 M | — | — | `0xc7B91C…0dB7` |
| `ALLOCATOR-OBEX-A` | 406 M | 456 M | — | — | `0xc7B91C…0dB7` |
| `ETH-A` | 180 M | 329 M | `0x2F0b23f53734252Bda2277357e97e1517d6B042A` | `0xc67963a226eddd77B91aD8c421630A1b0AdFF270` | `0x81FE72B5A8d1A857d176C3E7d5Bd2679A9B85763` |
| `ETH-C` | 178 M | 284 M | `0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E` | `0xc2b12567523e3f3CBd9931492b91fe65b240bc47` | `0x81FE72…5763` |
| `LSEV2-SKY-A` | 161 M | 167 M | — (LockstakeEngine) | `0x836F56750517b1528B5078Cba4Ac4B94fBE4A399` | `0x0C13fF3DC02E85aC169c4099C09c9B388f2943Fd` |
| `ALLOCATOR-GROVE-A` | 130 M | 280 M | — | — | `0xc7B91C…0dB7` |
| `RWA009-A` | 50 M | 100 M | `0xEe0FC514280f09083a32AE906cCbD2FAc4c680FA` | — | `0xdc7d370a089797fe9556a2b0400496ebb3a61e44` |
| `WSTETH-A` | 18 M | 60 M | `0x10CD5fbe1b404B7E19Ef964B63939907bdaf42E2` | `0x49A33A28C4C7D9576ab28898F4C9ac7e52EA457A` | `0xFe7a2aC0B945f12089aEEB6eCebf4F384D9f043F` |
| `RWA002-A` | 16 M | 50 M | `0xe72C7e90bc26c11d45dBeE736F0acf57fC5B7152` | — | `0xd2473237e20bd52f8e7ce0fd79403a6a82fbaec8` |
| `ETH-B` | 6 M | 29 M | `0x08638eF1A205bE6762A8b935F5da9b700Cf7322c` | `0x71eb894330e8a4b96b8d6056962e7F116F50e06F` | `0x81FE72…5763` |
| `WSTETH-B` | 5 M | 50 M | `0x248cCBf4864221fC0E840F29BB042ad5bFC89B5c` | `0x3ea60191b7d5990a3544B6Ef79983fD67e85494A` | `0xFe7a2a…043F` |
| `ALLOCATOR-PRYSM-A` | 5 M | 20 M | — | — | `0xc7B91C…0dB7` |
| `RWA005-A` / `RWA004-A` | 2.8 M / 1.5 M | 0 | `0xA4fD373b93aD8e054970A3d6cd4Fd4C31D08192e` / `0xD50a8e9369140539D1c2D113c4dC1e659c6242eB` | — | — |
| `WBTC-A` / `WBTC-B` / `WBTC-C` | 0.6 M / 0.2 M / 1.2 M | 0 (offboarding) | `0xBF72Da2B…5eb5` / `0xfA8c996e…96E0` / `0x7f62f959…9de2` | `0x0227b54A…6e2C` / `0xe30663C6…4a22` / `0x39F29773…161D1` | `0xf185d0682d50819263941e5f4EacC763CC5C6C42` |
| `ALLOCATOR-PATTERN-A` / `ALLOCATOR-INTERVAL-A` | 0 | 50 M / 10 M | — | — | `0xc7B91C…0dB7` |
| `TELEPORT-FW-A` | 0 | 2.1 M | `0x41Ca7a7Aa2Be78Cf7CB80C0F4a9bdfBC96e81815` | — | — |

Other ilks in the registry (BAT, KNC, LINK, YFI, UNI-V2 LP, GUNIV3, RETH, MATIC, PSM-GUSD/PAX, old PSM-USDC-A, other RWAs…) have zero debt and zero ceiling. Their joins and clippers stay in the ChainLog as `MCD_JOIN_<ILK>` / `MCD_CLIP_<ILK>`.

### 3.4 Allocator (Star) vaults

| Star | AllocatorVault (`ALLOCATOR_<X>_A_VAULT`) | AllocatorBuffer (`ALLOCATOR_<X>_A_BUFFER`) |
|------|------------------------------------------|--------------------------------------------|
| Spark | `0x691a6c29e9e96dd897718305427Ad5D534db16BA` | `0xc395D150e71378B47A1b8E9de0c1a83b75a08324` |
| Bloom (Grove) | `0x26512A41C8406800f21094a7a7A0f980f6e25d43` | `0x629aD4D779F46B8A1491D3f76f7E97Cb04D8b1Cd` |
| Grove | `0xf739a30c74927dc6cFA3B67E4933872a1FC5F4EB` | `0x436DABce608f73BeA2b75fba35bffe72739697d5` |
| Obex | `0xF275110dFE7B80df66a762f968f59B70BABE2b29` | `0x51E9681D7a05abFD33EfaFd43e5dd3Afc0093F1D` |
| Prysm | `0x146181Aa9B362EaEC2eC3aDd7429a06D53B43d1a` | `0xD0BB61b34771146e31055f20f329cDf97429F889` |
| Pattern | `0xbd34fc6AAa1d3F52B314CB9D78023dd23eAc3B0E` | `0x823459b55D79F0421f24a4828237F7ecb8D7F1ef` |
| Interval | `0xDD3bE7650589E6A6171d454b026C4AD1a2C02720` | `0x67Ac5c8FbFDAc5265c995e9B2ACd830496438AfD` |
| Nova | `0xe4470DD3158F7A905cDeA07260551F72d4bB0e77` | `0x065E5De3D3A08c9d14BF79Ce5A6d3D0E8794640c` |

Shared: `ALLOCATOR_REGISTRY` `0xCdCFA95343DA7821fdD01dc4d0AeDA958051bB3B`, `ALLOCATOR_ROLES` `0x9A865A710399cea85dbD9144b7a09C889e94E803`, `PIP_ALLOCATOR` `0xc7B91C401C02B73CBdF424dFaaa60950d5040dB7` (fixed $1), `DIRECT_HUB` (D3MHub, legacy) `0x12F36cdEA3A28C35aC8C6Cc71D9265c17C74A27F`. The Spark and Grove protocol contracts behind these vaults are documented in the `spark` docs, not here.

### 3.5 Surplus, debt, shutdown, flash

| Role | ChainLog key | Address | One-liner |
|------|--------------|---------|-----------|
| **Vow** | `MCD_VOW` | `0xA950524441892A31ebddF91d3cEEFa04Bf454466` | System surplus / debt buffer. |
| **Kicker** | `MCD_KICK` | `0xD889477102e8C4A857b78Fcc2f134535176Ec1Fc` | Permissionless `flap()` entry point. |
| **Splitter** | `MCD_SPLIT` | `0xBF7111F13386d23cb2Fba5A538107A73f6872bCF` | Splits surplus: Flapper + `farm` (`REWARDS_LSSKY_USDS` `0x38E4…8865`). |
| **Flapper** (FlapperUniV2SwapOnly) | `MCD_FLAP` | `0x374D9c3d5134052Bc558F432Afa1df6575f07407` | Buys SKY on Uniswap V2 pair `0x2621cc0b3f3c079c1db0e80794aa24976f0b9e3c`. Receiver = PauseProxy. |
| Flapper oracle | `FLAP_SKY_ORACLE` | `0xc2ffbbDCCF1466Eb8968a846179191cb881eCdff` | SKY price guard for the Flapper. |
| **Flopper** | `MCD_FLOP` | `0xA41B6EF151E06da0e34B009B86E828308986736D` | Debt auction (mints governance token). |
| **End** | `MCD_END` | `0x0e2e8F1D1326A4B9633D96222Ce399c708B19c28` | Global settlement. |
| **ESM** | `MCD_ESM` | `0x09e05fF6142F2f9de8B6B65855A1d56B6cfE4c58` | Emergency shutdown module. |
| **Cure** | `MCD_CURE` | `0x0085c9feAb2335447E1F4DC9bf3593a8e28bdfc7` | Shutdown debt accounting for bridges/allocators. |
| **DssFlash** | `MCD_FLASH` | `0x60744434d6339a6B27d73d9Eda62b6F66a0a04FA` | DAI flash mint. |
| CDP manager | `CDP_MANAGER` | `0x5ef30b9986345249bc32d8928B7ee64DE9435E39` | Legacy Oasis-style vault NFTs (`cdp` ids). |
| ProxyRegistry | `PROXY_REGISTRY` | `0x4678f0a6958e4D2Bc4F1BAF7Bc52E8F3564f3fE4` | DSProxy factory registry (legacy UI). |

### 3.6 Governance and risk automation

| Role | ChainLog key | Address | One-liner |
|------|--------------|---------|-----------|
| **Chief** (V3, SKY) | `MCD_ADM` | `0x929d9A1435662357F54AdcF64DcEE4d6b867a6f9` | Executive voting. Old MKR Chief V2: `0x0a3f6849f78076aefadf113f5bed87720274ddc0`. |
| **DSPause** | `MCD_PAUSE` | `0xbE286431454714F511008713973d3B053A2d38f3` | Governance delay. |
| **DSPauseProxy** | `MCD_PAUSE_PROXY` | `0xBE8E3e3618f7474F8cB1d074A26afFef007E98FB` | The protocol owner. Ward on every core contract. |
| DssAutoLine | `MCD_IAM_AUTO_LINE` | `0xC7Bdd1F2B16447dcf3dE045C4a039A60EC2f0ba3` | Automatic debt-ceiling steps. |
| LineMom | `LINE_MOM` | `0x9c257e5Aaf73d964aEBc2140CA38078988fB0C10` | Emergency `line` wipe. |
| OsmMom | `OSM_MOM` | `0x76416A4d5190d071bfed309861527431304aA14f` | Emergency OSM stop. |
| VoteDelegateFactory (V3) | `VOTE_DELEGATE_FACTORY` | `0x4Cf3DaeFA2683Cd18df00f7AFF5169C00a9EccD5` | Delegate contracts for SKY. Legacy V2: `0xC3D809E87A2C9da4F6d98fECea9135d834d6F5A0`. |
| StarGuard (Spark) | `SPARK_STARGUARD` | `0x6605aa120fe8b656482903E7757BaBF56947E45E` | Plot/exec of Star spells. One per Star (`<STAR>_STARGUARD`). |
| Spark SubProxy | `SPARK_SUBPROXY` | `0x3300f198988e4C9C63F75dF86De36421f06af8c4` | Star executor. Others: `GROVE_SUBPROXY`, `KEEL_SUBPROXY`, `OBEX_SUBPROXY`, `PATTERN_SUBPROXY`, … |
| PIP_ETH (OSM) | `PIP_ETH` | `0x81FE72B5A8d1A857d176C3E7d5Bd2679A9B85763` | ETH OSM (1 h delay). `PIP_WSTETH` `0xFe7a2aC0B945f12089aEEB6eCebf4F384D9f043F`, `PIP_WBTC` `0xf185d0682d50819263941e5f4EacC763CC5C6C42`. |

---

## 4. Other chains

The MCD core (Vat, joins, Dog/Clipper, Vow, Pot, Jug, governance) is deployed on **Ethereum only**. `eth_getCode` returns `0x` for `MCD_VAT`, `CHANGELOG` and `MCD_DAI` on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc (checked 2026-10-30). Bridged DAI on Arbitrum and Optimism (`0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1`) is a Maker-built L2 token, documented in [l2.md](l2.md).

## 5. Cross-chain summary

| Chain | ID | MCD core | Notes |
|-------|----|----------|-------|
| Ethereum | 1 | ✅ | Everything in §3. |
| Base | 8453 | — | `0xDA10009c…` has a 1,456-byte non-DAI contract here (decoy). |
| BNB | 56 | — | Same 1,456-byte decoy at `0xDA10009c…`. |
| Avalanche | 43114 | — | Same decoy at `0xDA10009c…`. |
| Arbitrum One | 42161 | — | Maker L2 DAI + gateway only ([l2.md](l2.md)). |
| Optimism | 10 | — | Maker L2 DAI + bridge only ([l2.md](l2.md)). |
| Polygon PoS | 137 | — | Same decoy at `0xDA10009c…`. |
| Robinhood Chain | 4663 | — | No code at any Sky literal. |
| Arc | 5042 | — | No code at any Sky literal. |

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Every contract in §3 | **Immutable** (no proxy) | EIP-1967 implementation and admin slots read `0x0` on all of them (2026-10-30) | Replacement only: governance deploys a new contract, `rely`s it and updates the ChainLog (`UpdateAddress`). |
| Governance path | DSPause + DSPauseProxy | `MCD_PAUSE.delay()` | Chief `hat` → `plot` → wait `delay` → `exec`. PauseProxy runs the spell with `delegatecall`. |

Rotations to watch: `ChainLog.UpdateAddress` / `RemoveAddress`, `Rely`/`Deny` (named and LibNote), `Dog.File(ilk,"clip",…)` (new Clipper), `Vow.file("flapper"/"flopper")` (LibNote `file(bytes32,address)` padded topic `0xd4e8be8300…`). The ETH-A Clipper, the Dog and the Vat were never replaced. Pre-2021 Cat (`0x78F2c2AF65126834c51822F56Be0d7469D7A523E`) and Flippers are retired.

## 7. Detection invariants & gotchas

1. **Anonymous logs.** The Vat, Dai, joins, Jug, Pot, Vow and Pause emit anonymous note logs. `topic0` is `selector‖0x00…`, not a keccak of an event. A topic0 filter for the formal `LogNote` hash finds nothing.
2. **Vat vs LibNote layout differs.** Vat: `topic1..3` = call args 1–3. LibNote: `topic1` = `msg.sender`, `topic2..3` = call args 1–2. Pause (DSNote): `topic1` = sender, `topic2` = `usr`, `topic3` = `tag`.
3. **Signed amounts are in `data`, not topics.** `frob(i,u,v,w,dink,dart)`: `dink`/`dart` are `int256`. Decode the calldata copy in `data` (offset 0x44 onward = raw calldata).
4. **Units.** wad 1e18, ray 1e27, rad 1e45. Vat DAI and `sin` are rad. `art` is normalised; multiply by `ilks(i).rate`.
5. **Two very different `Kick` events.** Clipper `Kick` (7 fields, `id` indexed) ≠ Flopper `Kick` (4 fields) ≠ Splitter `Kick(tot,lot,pay)`. Key on the emitter.
6. **One topic set for all Clippers.** Per-ilk Clippers and the Lockstake Clipper share `Kick`/`Take`/`Redo`/`Yank`. Map the emitter to the ilk with `IlkRegistry.xlip(ilk)` or `Dog.ilks(ilk).clip`.
7. **Liquidation chain.** One `bark` gives: Vat `grab` note + Vow `fess` note + Dog `Bark` + Clipper `Kick` (+ `Digs` later on each take). Count liquidations from `Dog.Bark`, not from Clipper `Kick` (`redo` re-kicks with `Redo`).
8. **`Take` with callback.** `take(..., who, data)` with non-empty `data` calls `who.clipperCall(...)` — flash liquidation. `Take.usr` is the receiver, not the taker. Use `tx.from` for the keeper.
9. **The surplus path moved.** `Vow.flap()` is dead. Surplus flows: `Kicker.flap()` → Vat `suck` (from Vow to Splitter) → `Splitter.Kick` → `Flapper.Exec` (SKY bought, sent to PauseProxy) + USDS to the staking farm. The Flapper uses USDS, not DAI.
10. **Allocator ilks have no GemJoin and no Clipper.** Their debt moves with `AllocatorVault.Draw`/`Wipe` and Vat `frob` notes. They cannot be liquidated. `PIP_ALLOCATOR` is a fixed-price oracle.
11. **LITE-PSM-USDC-A has no GemJoin.** The LitePSM `frob`s the Vat directly. Its USDC sits in the `pocket` (`MCD_LITE_PSM_USDC_A_POCKET` `0x37305B1cD40574E4C5Ce33f8e8306Be057fD7341`, no code — an account, not a contract). See [usds.md](usds.md).
12. **`MCD_GOV` is now SKY.** The ChainLog key `MCD_GOV` and the `SKY` key both point to `0x56072C95FAA701256059aa122697B133aDEd9279`. `MKR` still points to the old MKR token.
13. **Shutdown signals.** `End.Cage()`, `ESM.Fire()`, Vat `cage` note, `Dog.Cage()`, Pot `cage`. Any one is a protocol-wide event.
14. **CDP manager hides the owner.** A Vat `frob` from a manager CDP shows the `UrnHandler`, not the user. Resolve with `CdpManager.owns(cdp)` / `urns(cdp)`.
15. **DAI on other chains is mostly not Sky's.** DAI on Polygon (`0x8f3Cf7ad…`), BNB (Binance-peg) and Base (`0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb`, standard OP bridge) are third-party bridged tokens with no Sky mint authority.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Anonymous note topics (topic0 = selector left-aligned) =====
TOPIC_VAT_FROB              = '\x7608870300000000000000000000000000000000000000000000000000000000'  -- frob(bytes32,address,address,address,int256,int256) (anonymous note, topic0 = selector)
TOPIC_VAT_GRAB              = '\x7bab3f4000000000000000000000000000000000000000000000000000000000'  -- grab(bytes32,address,address,address,int256,int256) (anonymous note, topic0 = selector)
TOPIC_VAT_FORK              = '\x870c616d00000000000000000000000000000000000000000000000000000000'  -- fork(bytes32,address,address,int256,int256) (anonymous note, topic0 = selector)
TOPIC_VAT_FOLD              = '\xb65337df00000000000000000000000000000000000000000000000000000000'  -- fold(bytes32,address,int256) (anonymous note, topic0 = selector)
TOPIC_VAT_SUCK              = '\xf24e23eb00000000000000000000000000000000000000000000000000000000'  -- suck(address,address,uint256) (anonymous note, topic0 = selector)
TOPIC_VAT_HEAL              = '\xf37ac61c00000000000000000000000000000000000000000000000000000000'  -- heal(uint256) (anonymous note, topic0 = selector)
TOPIC_VAT_SLIP              = '\x7cdd3fde00000000000000000000000000000000000000000000000000000000'  -- slip(bytes32,address,int256) (anonymous note, topic0 = selector)
TOPIC_VAT_MOVE              = '\xbb35783b00000000000000000000000000000000000000000000000000000000'  -- move(address,address,uint256) (anonymous note, topic0 = selector)
TOPIC_VAT_FILE_ILK          = '\x1a0b287e00000000000000000000000000000000000000000000000000000000'  -- file(bytes32,bytes32,uint256) (anonymous note, topic0 = selector)
TOPIC_VAT_CAGE              = '\x6924500900000000000000000000000000000000000000000000000000000000'  -- cage() (anonymous note, topic0 = selector)
TOPIC_JOIN_JOIN             = '\x3b4da69f00000000000000000000000000000000000000000000000000000000'  -- join(address,uint256) (anonymous note, topic0 = selector)
TOPIC_JOIN_EXIT             = '\xef693bed00000000000000000000000000000000000000000000000000000000'  -- exit(address,uint256) (anonymous note, topic0 = selector)
TOPIC_JUG_DRIP              = '\x44e2a5a800000000000000000000000000000000000000000000000000000000'  -- drip(bytes32) (anonymous note, topic0 = selector)
TOPIC_POT_DRIP              = '\x9f678cca00000000000000000000000000000000000000000000000000000000'  -- drip() (anonymous note, topic0 = selector)
TOPIC_POT_JOIN              = '\x049878f300000000000000000000000000000000000000000000000000000000'  -- join(uint256) (anonymous note, topic0 = selector)
TOPIC_POT_EXIT              = '\x7f8661a100000000000000000000000000000000000000000000000000000000'  -- exit(uint256) (anonymous note, topic0 = selector)
TOPIC_VOW_FESS              = '\x697efb7800000000000000000000000000000000000000000000000000000000'  -- fess(uint256) (anonymous note, topic0 = selector)
TOPIC_PAUSE_PLOT            = '\x46d2fbbb00000000000000000000000000000000000000000000000000000000'  -- plot(address,bytes32,bytes,uint256) (anonymous note, topic0 = selector)
TOPIC_PAUSE_EXEC            = '\x168ccd6700000000000000000000000000000000000000000000000000000000'  -- exec(address,bytes32,bytes,uint256) (anonymous note, topic0 = selector)
TOPIC_NOTE_RELY             = '\x65fae35e00000000000000000000000000000000000000000000000000000000'  -- rely(address) (anonymous note, topic0 = selector)
TOPIC_NOTE_DENY             = '\x9c52a7f100000000000000000000000000000000000000000000000000000000'  -- deny(address) (anonymous note, topic0 = selector)
-- ===== Named topics (chain-agnostic) =====
TOPIC_DOG_BARK              = '\x85258d09e1e4ef299ff3fc11e74af99563f022d21f3f940db982229dc2a3358c'  -- Bark(bytes32,address,uint256,uint256,uint256,address,uint256)
TOPIC_DOG_DIGS              = '\x54f095dc7308776bf01e8580e4dd40fd959ea4bf50b069975768320ef8d77d8a'  -- Digs(bytes32,uint256)
TOPIC_CLIP_KICK             = '\x7c5bfdc0a5e8192f6cd4972f382cec69116862fb62e6abff8003874c58e064b8'  -- Kick(uint256,uint256,uint256,uint256,address,address,uint256)
TOPIC_CLIP_TAKE             = '\x05e309fd6ce72f2ab888a20056bb4210df08daed86f21f95053deb19964d86b1'  -- Take(uint256,uint256,uint256,uint256,uint256,uint256,address)
TOPIC_CLIP_REDO             = '\x275de7ecdd375b5e8049319f8b350686131c219dd4dc450a08e9cf83b03c865f'  -- Redo(uint256,uint256,uint256,uint256,address,address,uint256)
TOPIC_CLIP_YANK             = '\x2c5d2826eb5903b8fc201cf48094b858f42f61c7eaac9aaf43ebed490138144e'  -- Yank(uint256)
TOPIC_SPOT_POKE             = '\xdfd7467e425a8107cfd368d159957692c25085aacbcf5228ce08f10f2146486e'  -- Poke(bytes32,bytes32,uint256)
TOPIC_OSM_LOGVALUE          = '\x296ba4ca62c6c21c95e828080cb8aec7481b71390585605300a8a76f9e95b527'  -- LogValue(bytes32)
TOPIC_SPLITTER_KICK         = '\xe6dde59cbc017becba89714a037778d234a84ce7f0a137487142a007e580d609'  -- Kick(uint256,uint256,uint256)
TOPIC_FLAPPER_EXEC          = '\xffacc3c568d281ed9c440365e37ddd4f3cc5ce8e5ccac4b1c3b178f10c5531f3'  -- Exec(uint256,uint256)
TOPIC_FLOP_KICK             = '\x7e8881001566f9f89aedb9c5dc3d856a2b81e5235a8196413ed484be91cc0df6'  -- Kick(uint256,uint256,uint256,address)
TOPIC_END_CAGE              = '\x2308ed18a14e800c39b86eb6ea43270105955ca385b603b64eca89f98ae8fbda'  -- Cage()
TOPIC_ESM_FIRE              = '\x14c539ef1ff6ef515371448cd46419fd75ebb8698b7f6644c4f66b03b0327085'  -- Fire()
TOPIC_FLASH_LOAN            = '\x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0'  -- FlashLoan(address,address,uint256,uint256)
TOPIC_FLASH_VATDAI          = '\xbca56acc64a74a4c131755895cf7f72fc3f9e39af64241f7ad0f77e86f41ada9'  -- VatDaiFlashLoan(address,uint256,uint256)
TOPIC_CDP_NEWCDP            = '\xd6be0bc178658a382ff4f91c8c68b542aa6b71685b8fe427966b87745c3ea7a2'  -- NewCdp(address,address,uint256)
TOPIC_AUTOLINE_EXEC         = '\x2696a4655cbecf97fdc3c9c74f3eba424f2e404790389c2b4e31d2e32129c7dc'  -- Exec(bytes32,uint256,uint256)
TOPIC_ALLOC_DRAW            = '\x7ffa12f2611233f19bb229a71c5d8224cb37373555ab6754b65aef59ea26831d'  -- Draw(address,uint256)
TOPIC_ALLOC_WIPE            = '\x2d2c7da251295f4d722a8ddaf337627952c957ce21b2757c852e47fe81b3a2af'  -- Wipe(address,uint256)
TOPIC_CHAINLOG_UPDATE       = '\xcf0ecd10d1399d98978051da48095f368d6f1fa3292d5fc09135b92aa2a4d733'  -- UpdateAddress(bytes32,address)
TOPIC_CHAINLOG_REMOVE       = '\x236084b20b5721ddf3e40ed45b570186612a08edec64abae6894b60f315c54bc'  -- RemoveAddress(bytes32)
TOPIC_CHIEF_LIFT            = '\x2b07094bdf192088dc9d18c2c3a2b11b7f1df5d6f3460343964c059221e3f048'  -- Lift(address)
TOPIC_RELY                  = '\xdd0e34038ac38b2a1ce960229778ac48a8719bc900b6c4f8d0475c6e8b385a60'  -- Rely(address)
TOPIC_DENY                  = '\x184450df2e323acec0ed3b5c7531b81f9b4cdef7914dfd4c0a4317416bb5251b'  -- Deny(address)
TOPIC_FILE_UINT             = '\xe986e40cc8c151830d4f61050f4fb2e4add8567caad2d5f5496f9158e91fe4c7'  -- File(bytes32,uint256)
TOPIC_FILE_ADDR             = '\x8fef588b5fc1afbf5b2f06c1a435d513f208da2e6704c3d8f0e0ec91167066ba'  -- File(bytes32,address)
TOPIC_ERC20_TRANSFER        = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  -- Transfer(address,address,uint256)
-- ===== Selectors (chain-agnostic) =====
SEL_VAT_FROB                = '\x76088703'  -- frob(bytes32,address,address,address,int256,int256)
SEL_VAT_SUCK                = '\xf24e23eb'  -- suck(address,address,uint256)
SEL_DOG_BARK                = '\xed998908'  -- bark(bytes32,address,address)
SEL_CLIP_TAKE               = '\x81a794cb'  -- take(uint256,uint256,uint256,address,bytes)
SEL_CLIP_REDO               = '\xd843416d'  -- redo(uint256,address)
SEL_JUG_DRIP                = '\x44e2a5a8'  -- drip(bytes32)
SEL_POT_DRIP                = '\x9f678cca'  -- drip()
SEL_SPOT_POKE               = '\x1504460f'  -- poke(bytes32)
SEL_OSM_POKE                = '\x18178358'  -- poke()
SEL_KICKER_FLAP             = '\x0e01198b'  -- flap()
SEL_FLASH_LOAN              = '\x5cffe9de'  -- flashLoan(address,address,uint256,bytes)
SEL_PAUSE_PLOT              = '\x46d2fbbb'  -- plot(address,bytes32,bytes,uint256)
SEL_PAUSE_EXEC              = '\x168ccd67'  -- exec(address,bytes32,bytes,uint256)
SEL_END_CAGE                = '\x69245009'  -- cage()
SEL_ESM_FIRE                = '\x457094cc'  -- fire()
SEL_RELY                    = '\x65fae35e'  -- rely(address)
SEL_DENY                    = '\x9c52a7f1'  -- deny(address)
-- ===== Addresses (Ethereum, chain 1) =====
ETH_MCD_VAT                 = '\x35d1b3f3d7966a1dfe207aa4514c12a259a0492b'
ETH_MCD_DAI                 = '\x6b175474e89094c44da98b954eedeac495271d0f'
ETH_MCD_JOIN_DAI            = '\x9759a6ac90977b93b58547b4a71c78317f391a28'
ETH_MCD_JUG                 = '\x19c0976f590d67707e62397c87829d896dc0f1f1'
ETH_MCD_POT                 = '\x197e90f9fad81970ba7976f33cbd77088e5d7cf7'
ETH_MCD_SPOT                = '\x65c79fcb50ca1594b025960e539ed7a9a6d434a3'
ETH_MCD_DOG                 = '\x135954d155898d42c90d2a57824c690e0c7bef1b'
ETH_MCD_VOW                 = '\xa950524441892a31ebddf91d3ceefa04bf454466'
ETH_MCD_KICK                = '\xd889477102e8c4a857b78fcc2f134535176ec1fc'
ETH_MCD_SPLIT               = '\xbf7111f13386d23cb2fba5a538107a73f6872bcf'
ETH_MCD_FLAP                = '\x374d9c3d5134052bc558f432afa1df6575f07407'
ETH_MCD_FLOP                = '\xa41b6ef151e06da0e34b009b86e828308986736d'
ETH_MCD_END                 = '\x0e2e8f1d1326a4b9633d96222ce399c708b19c28'
ETH_MCD_ESM                 = '\x09e05ff6142f2f9de8b6b65855a1d56b6cfe4c58'
ETH_MCD_FLASH               = '\x60744434d6339a6b27d73d9eda62b6f66a0a04fa'
ETH_MCD_PAUSE               = '\xbe286431454714f511008713973d3b053a2d38f3'
ETH_MCD_PAUSE_PROXY         = '\xbe8e3e3618f7474f8cb1d074a26affef007e98fb'
ETH_MCD_ADM                 = '\x929d9a1435662357f54adcf64dcee4d6b867a6f9'
ETH_CHAINLOG                = '\xda0ab1e0017debcd72be8599041a2aa3ba7e740f'
ETH_ILK_REGISTRY            = '\x5a464c28d19848f44199d003bef5ecc87d090f87'
ETH_CDP_MANAGER             = '\x5ef30b9986345249bc32d8928b7ee64de9435e39'
ETH_JOIN_ETH_A              = '\x2f0b23f53734252bda2277357e97e1517d6b042a'
ETH_CLIP_ETH_A              = '\xc67963a226eddd77b91ad8c421630a1b0adff270'
ETH_CLIP_ETH_C              = '\xc2b12567523e3f3cbd9931492b91fe65b240bc47'
ETH_CLIP_WSTETH_A           = '\x49a33a28c4c7d9576ab28898f4c9ac7e52ea457a'
ETH_ALLOC_SPARK_VAULT       = '\x691a6c29e9e96dd897718305427ad5d534db16ba'
ETH_ALLOC_BLOOM_VAULT       = '\x26512a41c8406800f21094a7a7a0f980f6e25d43'
ETH_IAM_AUTO_LINE           = '\xc7bdd1f2b16447dcf3de045c4a039a60ec2f0ba3'
ETH_PIP_ETH                 = '\x81fe72b5a8d1a857d176c3e7d5bd2679a9b85763'
```

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify-verified ABI of each listed address. Cross-checked against live `eth_getLogs`: Vat padded topics `move` (9,980 logs in 10k blocks), `suck`, `frob`, `fold`, `file`, `slip`, `heal`, `flux`, `hope`; Jug `drip(bytes32)`; Pot `drip`/`join`/`exit`; DaiJoin `join`/`exit`; Vow `fess`; Pause `plot`/`exec`; Spotter `Poke`; Splitter `Kick` + Flapper `Exec` (43 each, same transactions); DssFlash `FlashLoan`; Dog `Bark` (216) and `Digs` (388) plus ETH-A Clipper `Take` (217) and `Kick` (71) between blocks 21.0 M and 26.3 M.
- **Addresses:** read from the ChainLog (`count()` = 520, `version()` = `1.20.21`) and its JSON mirror, then existence-checked via `eth_getCode`. Ilk table from `IlkRegistry.list()` + `Vat.ilks(ilk)` + `IlkRegistry.join/xlip/pip/gem` at block ≈ 26,306,300. Flapper/Splitter/Kicker wiring read live (`pair()`, `receiver()`, `farm()`, `splitter()`).
- **Proxies:** EIP-1967 implementation and admin slots read on every §3 address; all `0x0`.
- **Chain coverage:** `eth_getCode` for the Vat, ChainLog, DAI, MKR and USDS literals on all nine chains; the 1,456-byte contract at `0xDA10009c…` on Base, BNB, Avalanche and Polygon answers no `symbol()`, so it is not DAI.

Authoritative sources:
- [sky-ecosystem/dss](https://github.com/sky-ecosystem/dss) — Vat, Dai, joins, Jug, Pot, Spot, Dog, Clipper, Vow, End.
- [sky-ecosystem/dss-flappers](https://github.com/sky-ecosystem/dss-flappers) — Kicker, Splitter, FlapperUniV2SwapOnly.
- [sky-ecosystem/dss-allocator](https://github.com/sky-ecosystem/dss-allocator) · [sky-ecosystem/chainlog-ui](https://github.com/sky-ecosystem/chainlog-ui) · [sky-ecosystem/sky-protocol-info](https://github.com/sky-ecosystem/sky-protocol-info)
- [Sky ChainLog (JSON)](https://chainlog.sky.money/api/mainnet/active.json) · [Sky developer docs](https://developers.skyeco.com/)
- Explorer: [Etherscan](https://etherscan.io/address/0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B) · ABIs: [Sourcify](https://sourcify.dev/)

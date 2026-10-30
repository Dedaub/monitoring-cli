# Topaz Multichain (BNB hub + Robinhood, Base, Ethereum, Arc spokes) — Topics, Selectors, Addresses

**Status:** verified on 2026-10-30 against live RPC on BNB (56), Robinhood Chain (4663), Base (8453), Ethereum (1) and Arc (5042). Every spoke address in §3 returned code (sizes match on all four spokes). Wiring read live: `CLFactory.voter()`, `CLFactory.poolImplementation()`, `PoolFactory.voter()`, `NPM.factory()`, `NPM.WETH9()`, `Voter.factoryRegistry()`, `Voter.governor()`, `XTopazOFT.symbol()`. Topics recomputed locally from the deployed ABIs in the official `topazdex/agent-skill` repository.
**Scope:** the 2026 hub-and-spoke expansion of Topaz. BNB Chain stays the **hub** (TOPAZ, veTOPAZ, Minter — see [`amm.md`](amm.md) and [`slipstream.md`](slipstream.md)). Four **spokes** run the same v2 AMM and Slipstream CL code with a local Voter that is fed by LayerZero messages. Not on Arbitrum, Optimism, Avalanche or Polygon.

The spokes do **not** have TOPAZ, VotingEscrow or Minter. Each spoke has **xTOPAZ** (`XTopazOFT`, a LayerZero OFT), an `XTopazVotingVault` (stake xTOPAZ to vote on the local Voter), and a `SpokeEmissionReceiver` that receives the weekly budget from the BNB `EpochCoordinator`. Pool, gauge and NFPM code is byte-identical to BNB (same ABI variants), so every topic and selector in `amm.md` §1–§2 and `slipstream.md` §1–§2 applies unchanged on the spokes. Only the addresses differ.

> **Address reuse trap.** The spokes were deployed with per-chain nonces. Many spoke addresses are BNB addresses of **different** contracts: `0x268d1C8a…` is the BNB FactoryRegistry but the Robinhood UniversalRouter; `0x7B1d8745…` is the BNB AirdropDistributor but the Arc UniversalRouter; `0x606794d3…` is the BNB Minter but the Ethereum UniversalRouter; `0xe4b23F13…` is the BNB ManagedRewardsFactory but the Base UniversalRouter. Always key on `(chain, address)`.

---

## 1. Topics (new contracts only — pool/gauge/NFPM topics are in amm.md and slipstream.md)

### 1.1 XTopazOFT (spokes) and XTopazOFTAdapter (BNB)

| topic0 | Event |
|--------|-------|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` — trust-root change |
| `0x598f84fcbefcc6e5ff91d667bb1ac552746f1845a057928e4a1832076a28d5c0` / `0x1e863e624abfcced37cd8a56874c5b32fa2608de528bebaeab47a2d021fc45a3` | `InboundLimitSet(uint32,uint192,uint64)` / `OutboundLimitSet(uint32,uint192,uint64)` |
| `0x40db37ff5c0bdc2c427fbb2078c8f24afea940abac0e3c23bb4ea3bf2da2b212` | `PausedSet(bool)` (OFT; also SpokeEmissionReceiver, XTopazVotingVault) |
| `0x24ac3e8a0937219e2f0db7dfaeedca631a5075dd7021394d3e4485a790dfddf9` | `RoutePausedSet(uint32 indexed eid, bool)` (BNB adapter only) |
| `0x241d37767c6ce901198dddf0f5f7dbf7e2bb01f91089c75800fc9a756bbf5891` | `SupplyReconciled(uint32 indexed eid, uint256, uint256)` (BNB adapter only) |

### 1.2 Emission plumbing

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x77360216dafe21aa8d455333608207082f74e837ba9b3ef15d0a73cd22693738` | `Funded(uint256 indexed epoch, uint256 amount, uint256 exchangeRate)` | SpokeEmissionReceiver |
| `0x0fd7bb2818b0aaa42a4064edb68964c3e29810804cf8cce3060a3bac23fb9d79` | `Notified(uint256 indexed epoch, uint256 amount)` | SpokeEmissionReceiver |
| `0x3af790fafda720819b2fc6e15090606e81154e0ac9a92d38ecad006d99d20ecc` | `Rescued(address indexed token, address to, uint256 amount)` | SpokeEmissionReceiver |
| `0x727f577e44d33a6aac3e0af085cf529fa5d72ce53ba93b85fb3c9234cd6a7764` | `BudgetSent(uint256 indexed epoch, uint32 indexed eid, bytes32 indexed guid, uint256,uint256,uint256)` | BNB EpochCoordinator |
| `0xcfd61b9e5d6b3af7ec669e27ffc8bbff368b984d1835e5534c956da012a7e4e0` | `EpochFinalized(uint256 indexed epoch, uint256,uint256,uint256,uint256,uint256)` | BNB EpochCoordinator |

### 1.3 XTopazVotingVault (spokes)

| topic0 | Event |
|--------|-------|
| `0xb629bfc7335323dae55eb109edb9738aef2a9e11b6b07c1a664b7d03de8e8172` | `PositionOpened(uint256 indexed id, address indexed owner, address indexed from, uint256 amount, uint256 unlockAt)` |
| `0x7a7c91da4431183b882c881b099bbdf8b23aa5ccf277a523d67de7555e4d0a83` | `PositionIncreased(uint256 indexed id, uint256, uint256)` |
| `0xffdaf13b1d96bfc2213355f353f84c19493e0681eb0df26f83d862acd266750a` | `Unstaked(uint256 indexed id, address indexed receiver, uint256 amount, uint256 remaining)` |
| `0x5f396e3d707f16567164186d4a7a00562a5d0cb6f24f75f483deedb1f899e207` | `PositionMerged(uint256 indexed fromId, uint256 indexed toId, uint256, uint256)` |

### 1.4 Selectors

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc7c7f5b3` | `send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)` | OFT bridge-out |
| `0x13137d65` | `lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)` | LayerZero endpoint entry |
| `0x3400288b` | `setPeer(uint32,bytes32)` | Owner-only trust change |

---

## 2. Addresses — BNB hub additions (chain ID 56)

The BNB core in `amm.md` / `slipstream.md` is unchanged. These contracts were added for the multichain system:

| Contract | Address | Size |
|----------|---------|------|
| XTopaz (hub xTOPAZ, `symbol()` "xTOPAZ") | `0xf7adffe50d6369ef19df3af8d4ddbc15ace175fd` | 4,784 B |
| XTopazOFTAdapter (lockbox for spokes) | `0x7947b32e4b30413c83ee3602996edf97f6093748` | 14,157 B |
| EpochCoordinator (sends spoke budgets) | `0x7a8f5eedc0136a76dbffa209f00622074e29c01b` | 9,202 B |
| RelayManager | `0x243846421d3c9bf34a3db4982344a23cf171397c` | 14,044 B |
| HubUnwrapComposer | `0x64540da4816abf969e7c5c520924dd3d6a5acb58` | 3,646 B |
| VeTopazVault | `0x875acc3f094f10f9a7a8c32c79d509c13a3de5b8` | 14,237 B |
| XTopazZap / WrapRouter | `0xda75765e4eb2d0ebaba24bbb4a4359c88c8c229b` / `0xb12d10065bcd591d9c9ff2f12b3cbf1d9741d885` | 8,378 B / 6,910 B |
| CLZap / UniversalRouter | `0x475fee1722e7f56a9d341492a67db830d3a3a7de` / `0x691e6171e0a434ffe5c9f1759621d05b9efcf6a6` | 10,016 B / 16,003 B |
| PositionBurnHelper / TopazSlipstreamStateMulticall | `0x2764db7bca0ccf98a1611f36879ebffd06ffc02b` / `0xa1941194be7c2607ffbc27de23b1aca357c45e3d` | |
| System pool set (accounting, not user markets) | SystemPoolFactory `0x0a0483f8623bfee18b7f31fe1ea027367b5cb15e`, SystemPool `0x8b29025838dcbe9098de563c063233a51b3dd5a1`, SystemGaugeFactory `0x36e9c2d819cbefc316c400e74185273308d3273c`, SystemGauge `0xb12a5e332131091a226a23652418b54f80b2cda9` | |

## 3. Addresses — spokes (Robinhood 4663, Base 8453, Ethereum 1, Arc 5042)

| Contract | Address (all four spokes) |
|---|---|
| XTopazOFT | `0x1aa89c4ab9884cb65b759a3cc3a1690744d687a6` |
| FactoryRegistry | `0x6f701f163a7372c27275e76af21b6cf06ca6d498` |
| GaugeFactory | `0x60e60b6d0b77f3af83fd6ed35db6d0664693e39a` |
| ManagedRewardsFactory | `0xab2df5a1c8bb46a28d26a74c64eeaffe89ed3714` |
| Pool | `0x8776be6cd50bb78414c655bc8bf9e86a0989722f` |
| PoolFactory | `0x1e3ac31cf96b20619c913384c9bf6010a824fb95` |
| ProtocolForwarder | `0xcafa164098ce984799413daa2ee7579eb9f471df` |
| Router | `0x18226f64a850163c0f0aba453653cc206eae99f3` |
| SpokeEmissionReceiver | `0xb6286aae59580f504471bf5031a2aa688c5ac140` |
| Voter | `0xb509071a8a33fc2184b169dfc029b3de3cf5172b` |
| VotingRewardsFactory | `0x28e686ffa9caf74411fba0923dc3729cd513e3d4` |
| XTopazVotingVault | `0x35d7ac512f465f48d2bcb4c7322dd34c7bb7c777` |
| CLFactory | `0xaa5865dc3a60b25d305226d66fd573021f0d8ffb` |
| CLGauge | `0xe6ab7aa7cce6c3e11e709408bd985828a98b6553` |
| CLGaugeFactory | `0xc99b3e03e8de70318f705155a3195c18d6344dfe` |
| CLPool | `0x2daa7cf731334b4cd1c2e4e01e97ca67f4b9c6ae` |
| NFTDescriptor | `0xf09d42dbd9f867422339f13f40a936fc54b28133` |
| NFTSVG | `0x1328cfccb9d670fa478f0d5249f41a38f23af592` |
| NonfungiblePositionManager | `0x522bf4b5c9280bb6bb719f2ce7f514dd63c8c0c5` |
| NonfungibleTokenPositionDescriptor | `0xb17cd823450ec44462399ed02f8c72dce1bf1d5f` |

| Contract | Robinhood (4663) | Base (8453) | Ethereum (1) | Arc (5042) |
|---|---|---|---|---|
| CLZap | `0x0b8ad16647d392f5f34a88097cb01d2f074334ae` | `0x8c29f85a151e16c94bc845d14a7a4cd44345f168` | `0x1b4c8adc09d4c2940c0e536ff11266013d15b38a` | `0xa3e7b9a8c3fb6b54381ecefc2c3e1cbe991e9b8b` |
| SpokeBudgetComposer | `0x5da6456fa2560071dd29871ca045908f98932865` | `0xbba1c3b415cf8212cf3ce11e726ab62125bdc6db` | `0x5da6456fa2560071dd29871ca045908f98932865` | `0x5da6456fa2560071dd29871ca045908f98932865` |
| SpokeStakeComposer | `0xbba1c3b415cf8212cf3ce11e726ab62125bdc6db` | `0x2c359c5c680e2b1bca465e63d1904afac6b308f1` | `0xbba1c3b415cf8212cf3ce11e726ab62125bdc6db` | `0xbba1c3b415cf8212cf3ce11e726ab62125bdc6db` |
| CLInterfaceMulticall | `0x1b4c8adc09d4c2940c0e536ff11266013d15b38a` | `0x7f128593d76d9df3a6e6d1aec414602aff11804d` | `0xc2f7f923cad652038dbd5cb8acad60be0b840bf5` | `0xc2f7f923cad652038dbd5cb8acad60be0b840bf5` |
| CustomSwapFeeModule | `0x3ae3642ecebb720e48fe3f8feff5f7b5c50f98f6` | `0xce6be50cf7a6a868e5993aaa505b905b31c011e0` | `0x3ae3642ecebb720e48fe3f8feff5f7b5c50f98f6` | `0x3ae3642ecebb720e48fe3f8feff5f7b5c50f98f6` |
| CustomUnstakedFeeModule | `0xce6be50cf7a6a868e5993aaa505b905b31c011e0` | `0x5e29d449199e1c2e5a5557145075ccbae0be0920` | `0xce6be50cf7a6a868e5993aaa505b905b31c011e0` | `0xce6be50cf7a6a868e5993aaa505b905b31c011e0` |
| DynamicSwapFeeModule | `0x0dca13b1039277d82b27add86d06195b8e9bbfdb` | `0x8bc9b86ebcd30a724bf486536507b7f6bf1a5a46` | `0x8c29f85a151e16c94bc845d14a7a4cd44345f168` | `0x8c29f85a151e16c94bc845d14a7a4cd44345f168` |
| MixedRouteQuoterV1 | `0x39a344d192d1d34a6bee24dcf11093e93fbb3993` | `0xa9cd3ac90513663197e7fd6c932f63f0c40701be` | `0x39a344d192d1d34a6bee24dcf11093e93fbb3993` | `0x39a344d192d1d34a6bee24dcf11093e93fbb3993` |
| PositionBurnHelper | `0xc2f7f923cad652038dbd5cb8acad60be0b840bf5` | `0x1b4c8adc09d4c2940c0e536ff11266013d15b38a` | `0x8bc9b86ebcd30a724bf486536507b7f6bf1a5a46` | `0x8bc9b86ebcd30a724bf486536507b7f6bf1a5a46` |
| QuoterV2 | `0xa9cd3ac90513663197e7fd6c932f63f0c40701be` | `0x2e7395a6e0de6ee1f390bece891069cd18ff8572` | `0xa9cd3ac90513663197e7fd6c932f63f0c40701be` | `0xa9cd3ac90513663197e7fd6c932f63f0c40701be` |
| SugarHelper | `0x8c29f85a151e16c94bc845d14a7a4cd44345f168` | `0x0dca13b1039277d82b27add86d06195b8e9bbfdb` | `0x0b8ad16647d392f5f34a88097cb01d2f074334ae` | `0x0b8ad16647d392f5f34a88097cb01d2f074334ae` |
| SwapRouter | `0x2e7395a6e0de6ee1f390bece891069cd18ff8572` | `0x5da6456fa2560071dd29871ca045908f98932865` | `0x2e7395a6e0de6ee1f390bece891069cd18ff8572` | `0x2e7395a6e0de6ee1f390bece891069cd18ff8572` |
| TopazSlipstreamStateMulticall | `0x8bc9b86ebcd30a724bf486536507b7f6bf1a5a46` | `0xc2f7f923cad652038dbd5cb8acad60be0b840bf5` | `0x0dca13b1039277d82b27add86d06195b8e9bbfdb` | `0x0dca13b1039277d82b27add86d06195b8e9bbfdb` |
| UniversalRouter | `0x268d1c8a538ecf6628838c11d581e1eabd13d6a4` | `0xe4b23f13b24232c1e68ad0575191216152aa9480` | `0x606794d37991a426a189fd9fa8664d339a77f8ae` | `0x7b1d8745079c85af80ff7a7ea7c2c4769eab5348` |
| AutoManageFactory | `0x94765515d5b86fc46585055790ca17cb3252c079` | — | — | `0xd791ed4a795f4a8f774cb42873963dd2906e2591` |
| AutoManageZap | `0x765ac48e102ebb31f33f82cf9b9c660639e54b9f` | — | — | `0xb95caaccb808a4d276c2dc32e8b89cc15a10d703` |
| AutoManageLens | `0x8fa5f9e073daca98b0020fc27e13c7c0f959ffc8` | — | — | `0x92582b0cac1b36a1d6d66b521cf6bc9a827b95ce` |

Wrapped native: Robinhood `0x0bd7d308f8e1639fab988df18a8011f41eacad73`, Base `0x4200000000000000000000000000000000000006`, Ethereum WETH `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` (all read from `NPM.WETH9()`). **Arc has no wrapped native**: `NPM.WETH9()` returns the stub `0x8bceaa40b9acdfaedf85adf4ff01f5ad6517937f`, which reverts on every call; native-token paths fail there.

**Pool counts** (2026-10-30, `allPoolsLength()`): CLFactory — Robinhood 14, Arc 11, Base 3, Ethereum 2; PoolFactory (v2) — Arc 4, others 0. Robinhood CL pool `0x8132252bd65e7c03f7b57739e1db1c58d6ee792f` (45 B EIP-1167 clone of `CLPool`) emitted 979 `Swap` logs in 300,000 blocks.

## 4. Cross-chain summary

| Chain (ID) | Role | TOPAZ / veTOPAZ | xTOPAZ | CLFactory | PoolFactory | Voter |
|------------|------|-----------------|--------|-----------|-------------|-------|
| BNB (56) | hub | ✓ (`amm.md`) | `0xf7ad…75fd` + adapter | `0x73dc…2ed9` | `0x65e6…5784` | `0x2f80…dd67` |
| Robinhood (4663) | spoke | — | `0x1aa8…87a6` | `0xaa58…8ffb` | `0x1e3a…fb95` | `0xb509…172b` |
| Base (8453) | spoke | — | same | same | same | same |
| Ethereum (1) | spoke | — | same | same | same | same |
| Arc (5042) | spoke | — | same | same | same | same |
| Arbitrum, Optimism, Avalanche, Polygon | — | — | — | — | — | — |

## 5. Proxies

None found. The EIP-1967 implementation slot is `0x0` on the BNB `XTopaz`, the spoke `XTopazOFT` and the spoke `Voter`. Pools and CL gauges are EIP-1167 clones (45 B) of `Pool` / `CLPool` / `CLGauge`, as on BNB.

## 6. Detection invariants & gotchas

1. **Same address, different contract, across chains** (see the box at the top). Never reuse a BNB allowlist on a spoke.
2. **Spoke governance = the BNB admin Safe.** `Voter.governor()` returns `0xf407739e81574a3c9a3195bcb85ee694c94e540c` on all four spokes; that Safe has 171 B proxy code on Robinhood and Arc too.
3. **xTOPAZ supply moves by LayerZero.** Spoke mints and burns show as `OFTReceived` / `OFTSent` on `XTopazOFT`; the BNB side locks in `XTopazOFTAdapter`. A `PeerSet` or limit change is a trust-root change.
4. **Emissions arrive per epoch.** `EpochCoordinator.BudgetSent` on BNB pairs with `SpokeEmissionReceiver.Funded` / `Notified` on the spoke (match on `epoch` and the LayerZero `guid`).
5. **Arc gas is USDC.** Do not expect WETH-style wraps on Arc; the WETH9 stub reverts.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (new contracts) =====
TOPIC_OFT_SENT                    = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED                = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_OFT_PEER_SET                = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_TOPAZ_SPOKE_FUNDED          = '\x77360216dafe21aa8d455333608207082f74e837ba9b3ef15d0a73cd22693738'
TOPIC_TOPAZ_SPOKE_NOTIFIED        = '\x0fd7bb2818b0aaa42a4064edb68964c3e29810804cf8cce3060a3bac23fb9d79'
TOPIC_TOPAZ_BUDGET_SENT           = '\x727f577e44d33a6aac3e0af085cf529fa5d72ce53ba93b85fb3c9234cd6a7764'
TOPIC_TOPAZ_VAULT_POSITION_OPENED = '\xb629bfc7335323dae55eb109edb9738aef2a9e11b6b07c1a664b7d03de8e8172'
TOPIC_TOPAZ_VAULT_UNSTAKED        = '\xffdaf13b1d96bfc2213355f353f84c19493e0681eb0df26f83d862acd266750a'
-- pool / CL topics: reuse amm.md and slipstream.md (Swap v2 0xb3e27736..., CL Swap 0xc42079f9..., CL PoolCreated 0xab0d57f0...)
-- ===== Selectors =====
SEL_OFT_SEND                      = '\xc7c7f5b3'
SEL_OFT_SET_PEER                  = '\x3400288b'
-- ===== Addresses: same on ROBIN, BASE, ETH, ARC =====
SPOKE_TOPAZ_CL_FACTORY            = '\xaa5865dc3a60b25d305226d66fd573021f0d8ffb'
SPOKE_TOPAZ_CL_POOL_IMPL          = '\x2daa7cf731334b4cd1c2e4e01e97ca67f4b9c6ae'
SPOKE_TOPAZ_NPM                   = '\x522bf4b5c9280bb6bb719f2ce7f514dd63c8c0c5'
SPOKE_TOPAZ_POOL_FACTORY          = '\x1e3ac31cf96b20619c913384c9bf6010a824fb95'
SPOKE_TOPAZ_POOL_IMPL             = '\x8776be6cd50bb78414c655bc8bf9e86a0989722f'
SPOKE_TOPAZ_ROUTER                = '\x18226f64a850163c0f0aba453653cc206eae99f3'
SPOKE_TOPAZ_VOTER                 = '\xb509071a8a33fc2184b169dfc029b3de3cf5172b'
SPOKE_TOPAZ_FACTORY_REGISTRY      = '\x6f701f163a7372c27275e76af21b6cf06ca6d498'
SPOKE_TOPAZ_XTOPAZ_OFT            = '\x1aa89c4ab9884cb65b759a3cc3a1690744d687a6'
SPOKE_TOPAZ_XTOPAZ_VOTING_VAULT   = '\x35d7ac512f465f48d2bcb4c7322dd34c7bb7c777'
SPOKE_TOPAZ_EMISSION_RECEIVER     = '\xb6286aae59580f504471bf5031a2aa688c5ac140'
-- ===== Per-chain swap routers =====
ROBIN_TOPAZ_SWAP_ROUTER           = '\x2e7395a6e0de6ee1f390bece891069cd18ff8572'
ARC_TOPAZ_SWAP_ROUTER             = '\x2e7395a6e0de6ee1f390bece891069cd18ff8572'
ETH_TOPAZ_SWAP_ROUTER             = '\x2e7395a6e0de6ee1f390bece891069cd18ff8572'
BASE_TOPAZ_SWAP_ROUTER            = '\x5da6456fa2560071dd29871ca045908f98932865'
ROBIN_TOPAZ_UNIVERSAL_ROUTER      = '\x268d1c8a538ecf6628838c11d581e1eabd13d6a4'
ARC_TOPAZ_UNIVERSAL_ROUTER        = '\x7b1d8745079c85af80ff7a7ea7c2c4769eab5348'
ETH_TOPAZ_UNIVERSAL_ROUTER        = '\x606794d37991a426a189fd9fa8664d339a77f8ae'
BASE_TOPAZ_UNIVERSAL_ROUTER       = '\xe4b23f13b24232c1e68ad0575191216152aa9480'
-- ===== BNB hub additions =====
BNB_TOPAZ_XTOPAZ                  = '\xf7adffe50d6369ef19df3af8d4ddbc15ace175fd'
BNB_TOPAZ_XTOPAZ_OFT_ADAPTER      = '\x7947b32e4b30413c83ee3602996edf97f6093748'
BNB_TOPAZ_EPOCH_COORDINATOR       = '\x7a8f5eedc0136a76dbffa209f00622074e29c01b'
ALL_TOPAZ_ADMIN_SAFE              = '\xf407739e81574a3c9a3195bcb85ee694c94e540c'
```

## 8. Verification & sources

- **Addresses:** from the official five-chain catalog (reviewed 2026-09-29) and the DefiLlama registries (`topaz-cl`, `topaz-amm`); every spoke address existence-checked with `eth_getCode` on all four spokes (equal sizes), BNB additions checked on BNB.
- **Wiring:** `CLFactory.voter()` = `PoolFactory.voter()` = Voter; `CLFactory.poolImplementation()` = CLPool; `NPM.factory()` = CLFactory; `Voter.factoryRegistry()` = FactoryRegistry; `Voter.governor()` = admin Safe — on all four spokes. BNB `NPM.tokenDescriptor()` = `0x239B…498A`.
- **Topics:** recomputed locally as `keccak256(signature)` from the deployed ABI files. CL `Swap` / `Burn` / `Collect` / `Mint` seen live on a Robinhood CL pool via `https://rpc.mainnet.chain.robinhood.com`.

Sources:
- [topazdex/agent-skill `references/deployments.md`](https://github.com/topazdex/agent-skill/blob/main/references/deployments.md) and its `abis/deployed/` folder
- [Topaz contracts page](https://www.topazdex.com/docs/contracts)
- [DefiLlama-Adapters `registries/uniswapV3.js` and `registries/uniswapV2.js`](https://github.com/DefiLlama/DefiLlama-Adapters/tree/main/registries)
- Explorers: [BscScan](https://bscscan.com) · [robin.etherscan.io](https://robin.etherscan.io) · [Basescan](https://basescan.org) · [Etherscan](https://etherscan.io) · [arcscan.app](https://arcscan.app)

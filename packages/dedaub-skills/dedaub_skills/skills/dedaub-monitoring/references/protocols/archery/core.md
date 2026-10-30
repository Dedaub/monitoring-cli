# Archery (V2 + V3 / Slipstream CL) — Topics, Selectors, Addresses (Arc)

**Status:** verified against live Arc RPC on 2026-10-30. Addresses come from the official deployment record (archery.wtf/docs/security, address book `arc-mainnet-open-20260924-addresses.json`). Every address returned code. Contract names come from Sourcify full matches (chain 5042). Topics were recomputed locally as `keccak256(signature)`.
**Scope:** Archery on **Arc (5042)**: the ve(3,3) core (ARCHERY, VotingEscrow, Voter), the V2 Solidly AMM and the V3 concentrated-liquidity product ("Archery V3" on DefiLlama). Topics and selectors are chain-agnostic. Addresses are network-specific.

Archery is a USDC-native **Aerodrome-style fork**: "Archery Core" (Velodrome V2 AMM + ve(3,3)) plus "Slipstream" (concentrated liquidity). It is **not** a copy of Topaz. It is an independent deployment of the same upstream code. The CL contracts have the **same function-selector sets as the Topaz Slipstream build on Arc**. The `v3Factory` (4917 B) has the same size as the Topaz CLFactory `0xaa58…8ffb`. The bytecode differs only in 125 bytes of embedded values. So the CL topics and selectors are in [topaz/slipstream.md](../topaz/slipstream.md), and the V2 AMM and ve topics are in [topaz/amm.md](../topaz/amm.md). This file lists only what differs, plus the Arc addresses.

What differs: the **Voter is extended with a gauge-emission cap system** (24,448 B against 13,484 B for the Topaz spoke Voter). The ARCHERY token is **pre-TGE**: `totalSupply()` = 0 and no Minter is deployed ("Not deployed · at TGE" in the deployment record). DefiLlama reported about $0.60M TVL on 2026-10-30.

---

## 1. Topics (chain-agnostic)

### 1.1 Shared with Topaz / Aerodrome (see the linked files for the full lists)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | `Swap(address indexed sender, address indexed recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)` ✓live | CL pool (= Uniswap V3) |
| `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` / `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | `Mint(…)` / `Burn(…)` (Uniswap V3 layout) | CL pool |
| `0xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2` | `PoolCreated(address indexed token0, address indexed token1, int24 indexed tickSpacing, address pool)` | v3Factory |
| `0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f` / `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | `IncreaseLiquidity(…)` / `DecreaseLiquidity(…)` | v3PositionManager |
| `0x1c8ab8c7f45390d58f58f1d655213a82cca5d12179761a87c16f098813b8f211` / `0x8903a5b5d08a841e7f68438387f1da20c84dea756379ed37e633ff3854b99b84` | `Deposit(address indexed user, uint256 indexed tokenId, uint128 indexed liquidityToStake)` / `Withdraw(…)` | CLGauge |
| `0xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b` | `Swap(address indexed sender, address indexed to, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out)` | V2 Pool |
| `0x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e` | `PoolCreated(address indexed token0, address indexed token1, bool indexed stable, address pool, uint256)` | v2PoolFactory |
| `0x8835c22a0c751188de86681e15904223c054bedd5c68ec8858945b7831290273` | `Deposit(address indexed provider, uint256 indexed tokenId, uint8 indexed depositType, uint256 value, uint256 locktime, uint256 ts)` | VotingEscrow |
| `0x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94` | `Withdraw(address indexed provider, uint256 indexed tokenId, uint256 value, uint256 ts)` | VotingEscrow |
| `0x452d440efc30dfa14a0ef803ccb55936af860ec6a6960ed27f129bef913f296a` | `Voted(address indexed voter, address indexed pool, uint256 indexed tokenId, uint256 weight, uint256 totalWeight, uint256 timestamp)` | Voter |
| `0xef9f7d1ffff3b249c6b9bf2528499e935f7d96bb6d6ec4e7da504d1d3c6279e1` | `GaugeCreated(address indexed poolFactory, address indexed votingRewardsFactory, address indexed gaugeFactory, address pool, address bribeVotingReward, address feeVotingReward, address gauge, address creator)` | Voter |
| `0x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17` | `DistributeReward(address indexed sender, address indexed gauge, uint256 amount)` | Voter |
| `0x04a5d3f5d80d22d9345acc80618f4a4e7e663cf9e1aed23b57d975acec002ba7` | `GaugeKilled(address indexed gauge)` | Voter |

### 1.2 Archery-only — Voter gauge-cap events

| topic0 | Event |
|--------|-------|
| `0x38de567d6a1f1332b88b96d2db31d0ecf2e7100adc7157fa6affda356cdc54a0` | `SetGaugeCapController(address indexed oldGaugeCapController, address indexed newGaugeCapController)` |
| `0x34ecd8cb5fc0cf2207f60c0b243bca90771f4b1b8e4b4f8e416c18f1eaf9525a` | `CapModeQueued(uint8 indexed mode, uint256 indexed effectiveEpoch)` |
| `0xf301c3d8d20ef7044510b081447727b7e63c4d8dbfeeefec64d5956f2405c7ca` | `CapModeApplied(uint8 indexed mode, uint256 indexed epoch)` |
| `0xb1f6fb906f48b5a348d078cfeeea6030bb824835ecf194688e73fca10158c0fe` | `DefaultGaugeCapSet(address indexed gauge, uint16 bps, bool active, bytes32 reasonHash)` |
| `0xfbfec4ed2d4161d388dc4f65916834f97acebba5a68e7fc5f9406883c29cf1e4` | `GovernanceGaugeCapSet(address indexed gauge, uint256 indexed epoch, uint16 capBps, bool active, uint256 expiresEpoch, bytes32 reasonHash)` |
| `0xf79a11b3a52e2e409f4ad59d9e166e602b1aaba3e073abbbe7267c0aa6757d3b` | `EmergencyGaugeCapSet(address indexed gauge, uint256 indexed epoch, uint16 capBps, bool active)` |
| `0x032d2720d65f468c702910445eb7e474be6a262e7d82412448d0605d1e8e99eb` | `MaxCouncilEmergencyCapSet(address indexed gauge, uint16 maxBps)` |
| `0x7d7de90a5657c8d5525701c32f11c440c5fd7830a6986a8b81bba554fee3ec94` | `GlobalFallbackCapSet(uint16 bps, bool active, bytes32 reasonHash)` |
| `0x6f7e05b50276939d2211a5d0b0a97d69c5598dfe0613b2f9c082454f410403d9` | `GaugeCapAccounted(uint256 indexed epoch, address indexed gauge, uint256 nominal, uint256 requestedCumulative, uint256 released, uint256 withheld, uint8 status)` |
| `0x0e2798d95f0ab6df7cf108d0da3ee0bc18803d3981c3224afdb9576be3dd7627` | `GaugeCapObserved(uint256 indexed epoch, address indexed gauge, uint256 nominal, uint256 simulatedRelease, uint256 simulatedWithheld, uint256 denominatorWeth, uint256 conservativeUpPriceWeth, uint256 multiplierWad, uint8 status)` |
| `0x002df6c430fe66a0c4f856783d54cb499470d84b6be0ed4c7f365d0d4ea8f1f6` | `GaugeCapFallbackUsed(uint256 indexed epoch, address indexed gauge, uint16 fallbackBps, uint8 quoteStatus, bytes32 reason)` |
| `0x28778cdadbc004b0ef3d115ff7f4034f575f444b2dd83eb2495d9f4d158343b5` | `EpochCapSettled(uint256 indexed epoch, uint256 indexFloor, uint256 burnedAmount, uint256 liveAccountedReserve)` |
| `0x57be457dd27081933117d0aa3aacf8ec41b26821f46a5a1a521afb47aa1b9a25` | `ExpiredGaugeClaimableCleared(uint256 indexed expiredEpoch, address indexed gauge, uint256 amount)` |

## 2. Function signatures (chain-agnostic)

CL selectors equal [topaz/slipstream.md](../topaz/slipstream.md) §2 (for example NPM `mint` `0xb5007d1f`, SwapRouter `exactInputSingle` `0xa026383e`; both confirmed in the Archery bytecode). V2 and ve selectors equal [topaz/amm.md](../topaz/amm.md). Key ones:

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xb5007d1f` | `mint((address,address,int24,int24,int24,uint256,uint256,uint256,uint256,address,uint256,uint160))` | v3PositionManager |
| `0xa026383e` | `exactInputSingle((address,address,int24,address,uint256,uint256,uint256,uint160))` | v3SwapRouter |
| `0xcac88ea9` | `swapExactTokensForTokens(uint256,uint256,(address,address,bool,address)[],address,uint256)` | v2Router |
| `0x5a47ddc3` / `0x0dede6c4` | `addLiquidity(address,address,bool,…)` / `removeLiquidity(address,address,bool,…)` | v2Router |
| `0xb52c05fe` / `0x2e1a7d4d` | `createLock(uint256,uint256)` / `withdraw(uint256)` | VotingEscrow |
| `0x7ac09bf7` / `0x310bd74b` / `0x32145f90` | `vote(uint256,address[],uint256[])` / `reset(uint256)` / `poke(uint256)` | Voter |
| `0x794cea3c` / `0x992a7933` | `createGauge(address,address)` / `killGauge(address)` | Voter |
| `0x6138889b` / `0x7625391a` | `distribute(address[])` / `distribute(uint256,uint256)` | Voter |
| `0x0ad1af32` | `setGaugeCapController(address)` | Voter (Archery-only) |
| `0x36efd16f` | `depositFor(uint256,address)` | CLGauge (Archery-only) |

---

## 3. Addresses — Arc (chain ID 5042)

All verified via `eth_getCode` on `https://arc-rpc.publicnode.com` on 2026-10-30. No contract is a proxy (EIP-1967 impl slot empty). Deployment start block 22,447,642.

| Role | Address | Size | Notes |
|------|---------|------|-------|
| **ARCHERY token** | `0x85799160a8f84a90b41ced026e2873e9025d973c` | 5112 B | `totalSupply()` = 0 (pre-TGE). `minter()` = deployer. |
| **VotingEscrow** | `0x295ee38604abdb6a9aaf4e72eedafaebdd8a74b4` | 24508 B | `token()` = ARCHERY; `supply()` = 0. |
| **Voter** | `0x55e1be3aa0f751661f76669d4b5584175af8a36d` | 24448 B | `length()` = 4 gauges. `gaugeCapController()` = 0 (unset). |
| RewardsDistributor | `0xbe413241b3c783650ba482dd6d69c1c5549a2164` | 5850 B | |
| FactoryRegistry | `0xa180adc9a7ef76399d637ab3d6c58a1fbd57d2cb` | 2608 B | |
| VotingRewardsFactory | `0x5c6cc74382b2c37e2a14740e5c180817d86105b4` | 15068 B | |
| ManagedRewardsFactory | `0x3f344d04899e841bceb01afcf72173cfc6983ece` | 14261 B | |
| veArtProxy | `0xb420ac09bbf8a53784dc613aee02a44f4c077f84` | 15922 B | |
| v2PoolFactory | `0x0769d7d58e064d3dd4c2bb17274506f4824a9657` | 3465 B | `allPoolsLength()` = 0. |
| v2PoolImplementation | `0x02b9abc3717a6c5515ca0990d76ca209a4e552fc` | 21033 B | |
| v2Router | `0xc59a63612535879e71eb055336f4519cd20d5eb9` | 23685 B | `defaultFactory()` = v2PoolFactory. |
| v2GaugeFactory | `0x1f7fdc021f5c8244f09cb2e3ac7c28c48744b4e7` | 7434 B | |
| **v3Factory** (CLFactory) | `0xc481038c013fe96f38ce7a2dc417b2b1b78b16a4` | 4917 B | `allPoolsLength()` = 4. `owner()` = deployer. |
| v3PoolImplementation | `0x80d055bb22a7cd41843c7de0345e345bb9bcc6dd` | 24238 B | Pools are 45 B EIP-1167 clones. |
| **v3PositionManager** (NPM) | `0x3547c1543f5f61dc17094916d0bd0cbb0a837e51` | 24400 B | `factory()` = v3Factory. `WETH9()` = 0. |
| v3PositionDescriptor | `0x2f4281afbf71c93c9a72dac26cd259c69ddf4fe3` | 5946 B | |
| **v3SwapRouter** | `0x3b37e67c973683f7fe8a0f304dedfaf475fec138` | 9987 B | `factory()` = v3Factory. |
| v3Quoter | `0xcf5be05947984a1a577eace213bc50d08e5cc528` | 3768 B | |
| v3QuoterV2 | `0xc6b5c6056c4be2de1c014695a7ccb75087a1c574` | 6893 B | |
| v3TickLens | `0x88aa181eeb8d80e896331ad909431cb3c40e041b` | 2186 B | |
| v3GaugeFactory | `0xd818ead92b634a897cb374abade309d21372f77d` | 1859 B | |
| v3GaugeImplementation (CLGauge) | `0x046542434918cea37c17971210fbfd6f578bca6a` | 12852 B | |
| v3SwapFeeModule | `0x6bfce61498dea65d62ce11c2480d529a1a9325d4` | 10300 B | `v3Factory.swapFeeModule()`. |
| v3UnstakedFeeModule | `0xe563cf4b1cc5f2625cfe29ab1a7607d49df3f0fe` | 860 B | |
| ArcheryUtils | `0x37245a40c14113aaef4a8fc8adda6071768fce12` | 17203 B | |
| Deployer / operator / governance | `0x5a378ff5e4450f8841ded68fcc110cd433f52e97` | EOA | Voter `governor`, `epochGovernor`, `emergencyCouncil`, `minter`; VE `team`; factory owner and fee managers. |

### 3.1 CL pools and gauges (from `v3Factory.allPools(i)` and `Voter.gauges(pool)`)

| Market (tickSpacing) | Pool | Gauge |
|----------------------|------|-------|
| WETH / USDC (50) | `0x072ca55acb3cc90f96b7f7807cf8de2250af4dc7` | `0xf340f4c015a3378a69e4b5cd3bec058b9ead6ae4` |
| cirBTC / USDC (50) | `0x948523143f6610a64ee8f17667818fe1d8c9f562` | `0x2a07eac1c8a838be3bc747175e103dceb09f5d91` |
| WETH / cirBTC (10) | `0x3572897908f2d8d171bf701758f6ddafec5e3637` | `0xaaf8b6760ffd25297c55bb65f34353438e6d946b` |
| USDC / EURC (1) | `0xb88c08e31c1bc7d41f2cfc4fbafad5b3b0a5eae9` | `0x75a80442b81386b017e35ffd746ec8f31c1a5a9c` |

The deployment record also lists Arc **testnet** (5042002) addresses. They are not in this file.

## 4. Cross-chain summary

| Chain | ID | Archery |
|-------|----|---------|
| Arc | 5042 | ✓ all contracts in §3 |
| Ethereum / Base / BNB / Avalanche / Arbitrum / Optimism / Polygon / Robinhood | — | — (v3Factory, Voter, ARCHERY and NPM addresses return `0x` on all eight) |

## 5. Proxies

None. Every contract in §3 is a plain deployment (EIP-1967 impl slot = 0). CL pools and CL gauges are EIP-1167 clones of `v3PoolImplementation` / `v3GaugeImplementation`. Control sits with the deployer EOA `0x5a37…2e97` (no timelock, no multisig).

## 6. Detection invariants & gotchas

1. **Same topics as Topaz and Aerodrome.** Key every event on `(5042, emitter)`. Topaz also runs Slipstream on Arc (CLFactory `0xaa58…8ffb`) with the same `PoolCreated` topic.
2. **One EOA controls everything.** The deployer is Voter governor, emergency council and epoch governor, VE team, factory owner and swap-fee manager. Alert on `SetGaugeCapController`, `GaugeKilled`, `CapModeQueued`, and on fee-module changes on the v3Factory.
3. **V2 has no pools yet.** `v2PoolFactory.allPoolsLength()` = 0. All TVL is in the four CL pools. The WETH/USDC CL pool emitted 263 `Swap` logs in about 12,000 blocks to block 28,668,415.
4. **No emissions yet.** ARCHERY supply is 0 and no Minter exists. Gauges exist but distribute nothing until TGE.
5. **No native wrapper.** Arc gas is USDC. `NPM.WETH9()` returns 0. Native-token paths are not usable.
6. **Arc log cap.** `eth_getLogs` is capped at about 2,000 blocks per call on Arc.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_ARCH_CL_SWAP              = '\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
TOPIC_ARCH_CL_POOL_CREATED      = '\xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2'
TOPIC_ARCH_V2_SWAP              = '\xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b'
TOPIC_ARCH_V2_POOL_CREATED      = '\x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e'
TOPIC_ARCH_VE_DEPOSIT           = '\x8835c22a0c751188de86681e15904223c054bedd5c68ec8858945b7831290273'
TOPIC_ARCH_VE_WITHDRAW          = '\x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94'
TOPIC_ARCH_VOTED                = '\x452d440efc30dfa14a0ef803ccb55936af860ec6a6960ed27f129bef913f296a'
TOPIC_ARCH_GAUGE_CREATED        = '\xef9f7d1ffff3b249c6b9bf2528499e935f7d96bb6d6ec4e7da504d1d3c6279e1'
TOPIC_ARCH_GAUGE_KILLED         = '\x04a5d3f5d80d22d9345acc80618f4a4e7e663cf9e1aed23b57d975acec002ba7'
TOPIC_ARCH_SET_CAP_CONTROLLER   = '\x38de567d6a1f1332b88b96d2db31d0ecf2e7100adc7157fa6affda356cdc54a0'
TOPIC_ARCH_CAP_MODE_QUEUED      = '\x34ecd8cb5fc0cf2207f60c0b243bca90771f4b1b8e4b4f8e416c18f1eaf9525a'
TOPIC_ARCH_EPOCH_CAP_SETTLED    = '\x28778cdadbc004b0ef3d115ff7f4034f575f444b2dd83eb2495d9f4d158343b5'
-- ===== Selectors =====
SEL_ARCH_NPM_MINT               = '\xb5007d1f'
SEL_ARCH_EXACT_INPUT_SINGLE     = '\xa026383e'
SEL_ARCH_V2_SWAP_EXACT_TOKENS   = '\xcac88ea9'
SEL_ARCH_VOTE                   = '\x7ac09bf7'
-- ===== Arc (5042) =====
ARC_ARCH_TOKEN                  = '\x85799160a8f84a90b41ced026e2873e9025d973c'
ARC_ARCH_VOTING_ESCROW          = '\x295ee38604abdb6a9aaf4e72eedafaebdd8a74b4'
ARC_ARCH_VOTER                  = '\x55e1be3aa0f751661f76669d4b5584175af8a36d'
ARC_ARCH_V2_FACTORY             = '\x0769d7d58e064d3dd4c2bb17274506f4824a9657'
ARC_ARCH_V2_ROUTER              = '\xc59a63612535879e71eb055336f4519cd20d5eb9'
ARC_ARCH_V3_FACTORY             = '\xc481038c013fe96f38ce7a2dc417b2b1b78b16a4'
ARC_ARCH_V3_NPM                 = '\x3547c1543f5f61dc17094916d0bd0cbb0a837e51'
ARC_ARCH_V3_SWAP_ROUTER         = '\x3b37e67c973683f7fe8a0f304dedfaf475fec138'
ARC_ARCH_V3_QUOTER_V2           = '\xc6b5c6056c4be2de1c014695a7ccb75087a1c574'
ARC_ARCH_POOL_WETH_USDC         = '\x072ca55acb3cc90f96b7f7807cf8de2250af4dc7'
ARC_ARCH_POOL_CIRBTC_USDC       = '\x948523143f6610a64ee8f17667818fe1d8c9f562'
ARC_ARCH_POOL_WETH_CIRBTC       = '\x3572897908f2d8d171bf701758f6ddafec5e3637'
ARC_ARCH_POOL_USDC_EURC         = '\xb88c08e31c1bc7d41f2cfc4fbafad5b3b0a5eae9'
ARC_ARCH_DEPLOYER               = '\x5a378ff5e4450f8841ded68fcc110cd433f52e97'
```

## 8. Verification & sources

- **Addresses:** the official deployment table (mainnet column), each existence-checked with `eth_getCode`. Wiring read live: `Voter.ve()`, `governor()`, `emergencyCouncil()`, `epochGovernor()`, `minter()`, `length()`, `gauges(pool)`; `VotingEscrow.token()`, `team()`; `v3Factory.owner()`, `voter()`, `poolImplementation()`, `swapFeeModule()`, `unstakedFeeModule()`, `allPools(i)`; `NPM.factory()`; `SwapRouter.factory()`; `v2Router.defaultFactory()`; `v2PoolFactory.voter()`.
- **Fork comparison:** `PUSH4` selector sets compared with the Topaz Arc deployment. v3Factory, CL pool and SwapRouter sets are identical; the NPM differs by one non-selector `PUSH4` constant; the CLGauge adds `depositFor(uint256,address)` (`0x36efd16f`); the Voter has 48 `PUSH4` constants that the Topaz Voter does not have.
- **Topics:** recomputed from the Sourcify ABIs of Voter, VotingEscrow, NPM, CLGauge, v2 Router, v2 Pool, v2 PoolFactory and ARCHERY. The CL `Swap` topic seen live on the WETH/USDC and USDC/EURC pools.
- **Chain coverage:** `eth_getCode` on all nine public RPCs.
- **TVL:** `api.llama.fi/protocol/archery` (Arc 599,477 USD on 2026-10-30).

Sources:
- [Archery security and contracts](https://archery.wtf/docs/security) — deployment record and address book.
- [Sourcify](https://sourcify.dev) — verified sources for chain 5042.
- [DefiLlama adapter `projects/archery/index.js`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/archery/index.js) · [DefiLlama Archery](https://defillama.com/protocol/archery)
- [`aerodrome-finance/contracts`](https://github.com/aerodrome-finance/contracts) · [`aerodrome-finance/slipstream`](https://github.com/aerodrome-finance/slipstream) — upstream signatures.

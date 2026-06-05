# Velodrome Superchain (Root/Leaf cross-chain) — Compressed Reference (Optimism + OP-Stack leaf chains)

**Status:** topic0/selectors via local keccak from `velodrome-finance/superchain-contracts` interface source; addresses from `deployment-addresses/*.json` re-verified on-chain across root + 4 leaf chains (publicnode/drpc, 2026-06) — `leafXVelo.symbol()` = "XVELO" on every leaf; `rootMessageModule` emitted 60 `SentMessage` in the last ~40k OP blocks ✓.
**Scope:** the **cross-chain expansion** that takes Velodrome's ve(3,3) AMM beyond Optimism onto the **Optimism Superchain (OP-Stack)**. Single-chain AMM/gov/CL live in [`v2.md`](v2.md) and [`slipstream.md`](slipstream.md).
**Key architecture:** **Root chain = Optimism** (holds the canonical Voter, VotingEscrow, emissions). **Leaf chains** host vanilla Velodrome pools + leaf gauges; votes/emissions are bridged from root. Root pushes payloads through a **Hyperlane** message module; the bridgeable token is **XVELO** (1:1 redeemable for VELO via a root Lockbox). Leaf chains run **vanilla V2 pools** (not Slipstream unless the superchain-CL stack is also deployed — see [`slipstream.md`](slipstream.md)).

---

## Root / Leaf model (one paragraph)

Every leaf pool has a **RootPool** twin on Optimism. To vote/emit to a leaf gauge, a veVELO holder votes on the **root Voter**; the **RootMessageBridge** encodes a payload, the **RootHLMessageModule** (`0x2BbA…`) verifies the sender against the root Voter/FactoryRegistry and ships it via **Hyperlane** to the leaf's **LeafMessageModule** (same address), which forwards to the **LeafGauge**. VELO emissions cross as **XVELO** (mint/burn-bridged XERC20): root `Lockbox` locks VELO → mints XVELO; leaf burns XVELO on redemption. A **SinkGauge/SinkPool** on root absorbs the emissions earmarked for leaf chains.

---

## Topics (chain-agnostic — superchain-specific events)

### Hyperlane message module (Root + Leaf) — cross-chain payloads
```
0xe8ed70f129c378298b9277a92cb6f0f821d501da841fb5a9f313c645b1da14e3 -> SentMessage(uint32,bytes32,uint256,string,string)   [destinationDomain,recipient,value,message,metadata — emitted by the MessageModule/TokenBridge; VERIFIED LIVE on rootMessageModule ✓]
0x4eab7b127c764308788622363ad3e9532de3dfba7845bd4f84c125a22544255a -> HookSet(address)
0xd9c9e56222fe2b65a0022908f00615ccf568720470e84992da2945e08eae3bd4 -> DomainSet(uint256,uint32)   [chainid → Hyperlane domain mapping]
```
> Inbound delivery is via Hyperlane Mailbox `process` → the module's `handle(uint32,bytes32,bytes)` (IHLHandler) — no dedicated "ReceivedMessage" event; trace inbound by the Mailbox `ProcessId`/`Process` events or by the resulting LeafGauge/XVELO effects.

### XVELO / XERC20 bridgeable token
```
0x7ca16db12dad0e1c536f8062fd9e2e4fbb3d1a503b59df12a0cfa9f96abf1c59 -> CrosschainMint(address,uint256)   [SuperchainERC20-style mint on bridge-in]
0x017c33ab728c93e2be949ec7e4a35b76d607957c5fac4253f5d623b4a3b13036 -> CrosschainBurn(address,uint256)   [burn on bridge-out]
0x95285a889cc4780f8d9cb87aabb3a7f1bf6cf8e14c2549844e611a2811823b95 -> BridgeLimitsSet(address,uint256)   [per-bridge minting buffer cap]
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)   [standard ERC-20]
```

### XERC20Lockbox (root — VELO ⇄ XVELO 1:1)
```
0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c -> Deposit(address,uint256)    [lock VELO → mint XVELO — same topic0 as gauge Deposit, disambiguate by emitter]
0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364 -> Withdraw(address,uint256)   [burn XVELO → release VELO]
```

### LeafGauge (leaf-chain LP staking) — NOTE the 3-arg Deposit
```
0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62 -> Deposit(address,address,uint256)   [sender,to,amount — 3-arg, DISTINCT from V2 gauge's 2-arg Deposit 0xe1fffcc4…]
0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364 -> Withdraw(address,uint256)
0x095667752957714306e1a6ad83495404412df6fdb932fca6dc849a7ee910d4c1 -> NotifyReward(address,uint256)
0x1f89f96333d3133000ee447473151fa9606543368f02271c9d95ae14f13bcc67 -> ClaimRewards(address,uint256)
0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3 -> ClaimFees(address,uint256,uint256)   [LeafGauge fee claim — leaf CL-style]
```

> **Leaf Pool / PoolFactory / Voter / Reward events are byte-identical to V2** ([`v2.md`](v2.md)) — leaf pools run the same `Pool` bytecode (`Swap` `0xb3e27736…`, `PoolCreated` `0x2128d88d…`, etc.).

---

## Function signatures (chain-agnostic)
```
0x587faab6 -> sendToken(address,uint256,uint256)        [TokenBridge: recipient, amount, chainid → bridge XVELO]
0xe289adcd -> sendMessage(uint256,bytes)                [RootMessageBridge: chainid, payload]
0x18bf5077 -> crosschainMint(address,uint256)           [XERC20 SuperchainERC20 mint]
0x2b8c49e3 -> crosschainBurn(address,uint256)           [XERC20 SuperchainERC20 burn]
0x40c10f19 -> mint(address,uint256)                     [XERC20 bridge-gated mint]
0x9dc29fac -> burn(address,uint256)                     [XERC20 bridge-gated burn]
0xb6b55f25 -> deposit(uint256)                          [Lockbox: VELO → XVELO]
0x2e1a7d4d -> withdraw(uint256)                         [Lockbox: XVELO → VELO]
```

---

## Addresses

### Root — Optimism (chain ID 10)
> Source: `superchain-contracts/deployment-addresses/optimism.json`. All on-chain ✓.
```
0xF278761576f45472bdD721EACA19317cE159c011 -> rootMessageBridge (6323B code ✓)
0x2BbA7515F7cF114B45186274981888D8C2fBA15E -> rootMessageModule (Hyperlane; emits SentMessage — 60 in last 40k blk ✓)
0x916e0AD2d7e3f446A26b0333Ca37A9e8972030c5 -> rootModuleVault
0x31832f2a97Fd20664D76Cc421207669b55CE4BC0 -> rootPoolFactory (AMM; 1939B code ✓)
0x10499d88Bd32AF443Fc936F67DE32bE1c8Bb374C -> rootPoolImplementation
0x42e403b73898320f23109708b0ba1Ae85838C445 -> rootGaugeFactory
0x7dc9fd82f91B36F416A89f5478375e4a79f4Fb2F -> rootVotingRewardsFactory
0x7f9AdFbd38b669F03d1d11000Bc76b9AaEA28A81 -> rootXVelo / XVELO token (symbol "XVELO" ✓)
0x12B64dF29590b4F0934070faC96e82e580D60232 -> rootLockbox (VELO ⇄ XVELO; 1444B code ✓)
0x73CaE4450f11f4A33a49C880CE3E8E56a9294B31 -> rootXFactory (XERC20Factory)
0x1A9d17828897d6289C6dff9DC9F5cc3bAEa17814 -> rootTokenBridge (XVELO bridge)
0x479Bec910d4025b4aC440ec27aCf28eac522242B -> rootTokenBridgeVault
0xf7a15F27533c2Db26341220C1e0B939B56dEfeda -> emergencyCouncil (superchain)
# Restricted reward (XOP) leg — used to bridge restricted incentives
0xafcc6AE807187A31E84138F3860D4CE27973e01b -> rootRestrictedRewardToken (XOP)
0xb46cEA3e5839914bCb7622841D6E3dfC1BD92313 -> rootRestrictedRewardLockbox
0xac6A6080E002D2803959242C0FE10050C482D214 -> rootRestrictedTokenBridge
0xb9d32Bf44a71bC0a383Bd2061584e98A1e09C8d2 -> rootRestrictedTokenBridgeVault
0x00a3767687699C65878655B62E565453BDC75Fb1 -> rootRestrictedXFactory
```

### Leaf chains — SHARED addresses (deterministic CreateX deploy; identical on every leaf chain) ✓
> Verified live on Mode, Unichain, Soneium, Lisk (`leafXVelo.symbol()`="XVELO", `leafPoolFactory.allPoolsLength()` > 0). The **only per-chain variation is `leafFeeModule`** (table below).
```
0x31832f2a97Fd20664D76Cc421207669b55CE4BC0 -> leafPoolFactory (vanilla V2 pools)
0x10499d88Bd32AF443Fc936F67DE32bE1c8Bb374C -> leafPoolImplementation
0x3a63171DD9BebF4D07BC782FECC7eb0b890C2A45 -> leafRouter
0x42e403b73898320f23109708b0ba1Ae85838C445 -> leafGaugeFactory
0x7dc9fd82f91B36F416A89f5478375e4a79f4Fb2F -> leafVotingRewardsFactory
0x97cDBCe21B6fd0585d29E539B1B99dAd328a1123 -> leafVoter
0xF278761576f45472bdD721EACA19317cE159c011 -> leafMessageBridge
0x2BbA7515F7cF114B45186274981888D8C2fBA15E -> leafMessageModule (Hyperlane handler)
0x1A9d17828897d6289C6dff9DC9F5cc3bAEa17814 -> leafTokenBridge
0x73CaE4450f11f4A33a49C880CE3E8E56a9294B31 -> leafXFactory
0x7f9AdFbd38b669F03d1d11000Bc76b9AaEA28A81 -> leafXVelo / XVELO (symbol "XVELO" ✓)
# Restricted (XOP) leg — also on Base & Optimism
0xafcc6AE807187A31E84138F3860D4CE27973e01b -> leafRestrictedRewardToken (XOP)
0xac6A6080E002D2803959242C0FE10050C482D214 -> leafRestrictedTokenBridge
0x00a3767687699C65878655B62E565453BDC75Fb1 -> leafRestrictedXFactory
```

### Leaf chain roster + per-chain `leafFeeModule`
| Chain | Chain ID | Velodrome footprint | leafFeeModule |
|---|---|---|---|
| Optimism | 10 | **ROOT** (full AMM+CL+gov, see v2.md/slipstream.md) | — |
| Mode | 34443 | Full leaf AMM+gauges (allPoolsLength 107 ✓) | (not set) |
| Unichain | 130 | Full leaf AMM+gauges (allPoolsLength 16 ✓) | 0x81c5d01Ae474040a59D0092A6973f4621e06B362 |
| Soneium | 1868 | Full leaf AMM+gauges (allPoolsLength 95 ✓) | 0x81c5d01Ae474040a59D0092A6973f4621e06B362 |
| Lisk | 1135 | Full leaf AMM+gauges (allPoolsLength 53 ✓) | 0x44536f7694D2D2F843437AdeD8D95525f797a06B |
| Metal L2 | 1750 | Full leaf AMM+gauges | 0x81c5d01Ae474040a59D0092A6973f4621e06B362 |
| Ink | 57073 | Full leaf AMM+gauges | 0x81c5d01Ae474040a59D0092A6973f4621e06B362 |
| Fraxtal | 252 | Full leaf AMM+gauges | 0xC60A684E00f2aEc11603348A615cb2b454B62e31 |
| Superseed | 5330 | Full leaf AMM+gauges | 0x81c5d01Ae474040a59D0092A6973f4621e06B362 |
| Swell | 1923 | Full leaf AMM+gauges | 0x81c5d01Ae474040a59D0092A6973f4621e06B362 |
| Celo | 42220 | Full leaf AMM+gauges | 0x81c5d01Ae474040a59D0092A6973f4621e06B362 |
| Bob | 60808 | **Standalone V2 pools only** (PoolFactory `0x3183…` + Router `0x3a63…` + StakingRewards `0x8Eb6838B…` / factory; **no ve(3,3) gauges/voter**) | — |
| **Base** | 8453 | **Restricted-bridge only** — no Velodrome AMM (Aerodrome serves Base); only XOP `leafRestricted*` contracts | — |

> Bob extras: `tokenRegistry 0x8d9c67488c154286B9D4ccaC6c4CBF30589107a7`, `universalRouter 0xc3F14F34EA43943e6fd677A2BDceA65882e67783`, `stakingRewardsFactory 0x8Eb6838B4e998DA08aab851F3d42076f21530389`, `stakingRewardsImplementation 0x593D092BB28CCEfe33bFdD3d9457e77Bd3084271`.

---

## Proxies

- **Leaf AMM Pools: NO upgradeable proxy** — CREATE2 from leafPoolFactory, immutable (same as V2).
- **XVELO / XERC20 tokens, bridges, lockboxes, message modules:** deployed via **CreateX deterministic** deployment → identical addresses cross-chain. Treat as immutable per the audited superchain-contracts release; if upgradeable, read the EIP-1967 impl slot per instance.
- **Hyperlane** Mailbox/ISM are external infra (not in this address set); `ism` is `0x0` in the deployment JSON (default/unset ISM).
- ve(3,3) governance lives only on root (Optimism) — see [`v2.md`](v2.md).

---

## Detection invariants & gotchas

1. **Leaf gauge `Deposit` is 3-arg (`0x5548c837…`), not the V2 2-arg `0xe1fffcc4…`.** A monitor reusing the V2 gauge-Deposit constant will MISS all leaf-chain stakes.
2. **Same address ≠ same chain.** Leaf contracts share addresses across ALL leaf chains — always scope queries by chain ID; an address alone is ambiguous.
3. **`SentMessage` (`0xe8ed70f1…`) is the cross-chain payload event** — emitted by the **MessageModule** (`0x2BbA…`), not the bridge facade. Inbound has **no event** (Hyperlane `handle`); detect inbound via resulting XVELO `CrosschainMint`/LeafGauge effects.
4. **Lockbox `Deposit`/`Withdraw` reuse gauge topic0s** (`0xe1fffcc4…`/`0x884edad9…`) — disambiguate by emitter (the rootLockbox `0x12B6…`).
5. **Base = Aerodrome territory.** A `base.json` entry exists but only for the restricted (XOP) reward bridge; there is **no Velodrome pool/gauge on Base**.
6. **Bob has no gauges** — it's a standalone V2-pools + StakingRewards deployment; don't expect ve(3,3) `GaugeCreated`/`Voted` there.
7. **XVELO ≠ VELO.** XVELO (`0x7f9A…`, all chains) is the bridgeable wrapper; the canonical VELO (`0x9560…`) exists only on Optimism. 1:1 via the root Lockbox.

---

## Quick-copy bytea-ready constants (Postgres `'\x…'`)
```
sent_message      = '\xe8ed70f129c378298b9277a92cb6f0f821d501da841fb5a9f313c645b1da14e3'
crosschain_mint   = '\x7ca16db12dad0e1c536f8062fd9e2e4fbb3d1a503b59df12a0cfa9f96abf1c59'
crosschain_burn   = '\x017c33ab728c93e2be949ec7e4a35b76d607957c5fac4253f5d623b4a3b13036'
leaf_gauge_deposit= '\x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62'
bridge_limits_set = '\x95285a889cc4780f8d9cb87aabb3a7f1bf6cf8e14c2549844e611a2811823b95'
xvelo_addr        = '\x7f9adfbd38b669f03d1d11000bc76b9aaea28a81'
leaf_pool_factory = '\x31832f2a97fd20664d76cc421207669b55ce4bc0'
root_msg_module   = '\x2bba7515f7cf114b45186274981888d8c2fba15e'
```

---

## Verification & sources
- topic0/selectors: local keccak this session from `superchain-contracts/src/interfaces/{bridge,xerc20,gauges,root}` (`ITokenBridge`, `IXERC20`, `IXERC20Lockbox`, `ICrosschainERC20`, `ILeafGauge`, `IRootHLMessageModule`). `SentMessage` topic0 confirmed live (60 events on rootMessageModule, last ~40k OP blocks).
- Addresses: `superchain-contracts/deployment-addresses/*.json` for all 13 chain files; re-verified on-chain — root XVELO/Lockbox/MessageBridge/PoolFactory code; leaf XVELO `symbol()` + `leafPoolFactory.allPoolsLength()` on Mode/Unichain/Soneium/Lisk; chain IDs resolved via `eth_chainId`.
- Source: [`velodrome-finance/superchain-contracts`](https://github.com/velodrome-finance/superchain-contracts) (`SPECIFICATION.md`). Single-chain: [`v2.md`](v2.md), [`slipstream.md`](slipstream.md). Cross-chain CL: [`slipstream.md`](slipstream.md) §superchain.

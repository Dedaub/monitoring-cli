# Curve Finance — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Base, BSC, Polygon, Gnosis, Avalanche)

**Status:** verified against live RPC on all eight listed chains and the canonical `curvefi` Vyper source repos on **2026-06-02**. Event topic0 hashes and function selectors were recomputed locally as `keccak256(canonical signature)` (deterministic; 69/69 topics and 56/56 selectors re-checked, cross-checked against live `eth_getLogs`). **Every address was existence-checked with `eth_getCode`** on each chain it is claimed on (all resolve), every listed proxy slot was read live, and the `AddressProvider` id-map was read on-chain. The companion stablecoin/lending file is [crvusd.md](crvusd.md) (crvUSD mint markets + LlamaLend + scrvUSD); see [README.md](README.md). Full method + the independent fact-check are in §14.
**Scope:** the Curve AMM exchange protocol across seven EVM chains, its factories/registries, the Curve DAO/tokenomics stack (Ethereum), and an adjacent crvUSD pointer. Topics + selectors are chain-agnostic; addresses are network-specific.

Curve is **not one ABI** — it is a family of pool implementations deployed over six years, each with its own event and function signatures. The single most important fact for monitoring Curve: **StableSwap pools use `int128` coin indices, CryptoSwap pools (tricrypto/twocrypto) use `uint256` indices**, and the "NG" (new-generation) rewrites changed event field layouts again. The *same* logical event name (`TokenExchange`, `AddLiquidity`, …) therefore hashes to *different* `topic0` values across families — you must match on `(topic0, pool-family)`, never on event name alone.

Unlike Uniswap V2 (one factory, one init-code hash, pools derivable by CREATE2), Curve pools are deployed by **multiple factories** via **EIP-5202 blueprints** (`create_from_blueprint`), are heterogeneous, and number in the tens of thousands. The correct way to enumerate them is to (a) watch each factory's `*Deployed` event, and/or (b) read the on-chain **MetaRegistry**, then classify each pool by which family's `topic0` set its logs match. Pool logic is immutable once deployed; only parameters (A, fees) are mutable by the DAO admin.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

> **Family fingerprint.** `TokenExchange` arg #2/#4 type tells you the family instantly: `int128` → StableSwap (classic or NG); `uint256` → CryptoSwap (old or NG). The NG crypto event carries 7 args (adds `fee` + price), old crypto carries 5.

### 1.1 StableSwap — classic (3pool, lending/meta pools; `curve-contract`)

| topic0 | Event |
|--------|-------|
| `0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140` | `TokenExchange(address indexed buyer, int128 sold_id, uint256 tokens_sold, int128 bought_id, uint256 tokens_bought)` |
| `0xd013ca23e77a65003c2c659c5442c00c805371b7fc1ebd4c206c41d1536bd90b` | `TokenExchangeUnderlying(address indexed buyer, int128 sold_id, uint256 tokens_sold, int128 bought_id, uint256 tokens_bought)` |
| `0x26f55a85081d24974e85c6c00045d0f0453991e95873f52bff0d21af4079a768` | `AddLiquidity(address indexed provider, uint256[2] token_amounts, uint256[2] fees, uint256 invariant, uint256 token_supply)` — **2-coin** |
| `0x423f6495a08fc652425cf4ed0d1f9e37e571d9b9529b1c1c23cce780b2e7df0d` | `AddLiquidity(address indexed provider, uint256[3] token_amounts, uint256[3] fees, uint256 invariant, uint256 token_supply)` — **3-coin** |
| `0x3f1915775e0c9a38a57a7bb7f1f9005f486fb904e1f84aa215364d567319a58d` | `AddLiquidity(address indexed provider, uint256[4] token_amounts, uint256[4] fees, uint256 invariant, uint256 token_supply)` — **4-coin** |
| `0x7c363854ccf79623411f8995b362bce5eddff18c927edc6f5dbbb5e05819a82c` | `RemoveLiquidity(address indexed provider, uint256[2] token_amounts, uint256[2] fees, uint256 token_supply)` — **2-coin** |
| `0xa49d4cf02656aebf8c771f5a8585638a2a15ee6c97cf7205d4208ed7c1df252d` | `RemoveLiquidity(address indexed provider, uint256[3] token_amounts, uint256[3] fees, uint256 token_supply)` — **3-coin** |
| `0x9878ca375e106f2a43c3b599fc624568131c4c9a4ba66a14563715763be9d59d` | `RemoveLiquidity(address indexed provider, uint256[4] token_amounts, uint256[4] fees, uint256 token_supply)` — **4-coin** |
| `0x9e96dd3b997a2a257eec4df9bb6eaf626e206df5f543bd963682d143300be310` | `RemoveLiquidityOne(address indexed provider, uint256 token_amount, uint256 coin_amount)` |
| `0x173599dbf9c6ca6f7c3b590df07ae98a45d74ff54065505141e7de6c46a624c2` | `RemoveLiquidityImbalance(address indexed provider, uint256[3] token_amounts, uint256[3] fees, uint256 invariant, uint256 token_supply)` — **3-coin** |
| `0xa2b71ec6df949300b59aab36b55e189697b750119dd349fcfa8c0f779e83c254` | `RampA(uint256 old_A, uint256 new_A, uint256 initial_time, uint256 future_time)` |
| `0x46e22fb3709ad289f62ce63d469248536dbc78d82b84a3d7e74ad606dc201938` | `StopRampA(uint256 A, uint256 t)` |
| `0x351fc5da2fbf480f2225debf3664a4bc90fa9923743aad58b4603f648e931fe0` | `CommitNewFee(uint256 indexed deadline, uint256 fee, uint256 admin_fee)` — 3pool family |
| `0xbe12859b636aed607d5230b2cc2711f68d70e51060e6cca1f575ef5d2fcc95d1` | `NewFee(uint256 fee, uint256 admin_fee)` — 3pool family |
| `0x6081daa3b61098baf24d9c69bcd53af932e0635c89c6fd0617534b9ba76a7f73` | `CommitNewParameters(uint256 indexed deadline, uint256 A, uint256 fee, uint256 admin_fee)` — lending pools |
| `0x752a27d1853eb7af3ee4ff764f2c4a51619386af721573dd3809e929c39db99e` | `NewParameters(uint256 A, uint256 fee, uint256 admin_fee)` — lending pools |
| `0x181aa3aa17d4cbf99265dd4443eba009433d3cde79d60164fde1d1a192beb935` | `CommitNewAdmin(uint256 indexed deadline, address indexed admin)` |
| `0x71614071b88dee5e0b2ae578a9dd7b2ebbe9ae832ba419dc0242cd065a290b6c` | `NewAdmin(address indexed admin)` |

`token_amounts`/`fees` array width equals `N_COINS`, so add/remove-liquidity events have a **different topic0 per pool size**. `TokenExchangeUnderlying` is emitted only by lending and metapools (the `_underlying` path).

### 1.2 StableSwap-NG (`stableswap-ng`; the pool *is* the LP token)

| topic0 | Event |
|--------|-------|
| `0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140` | `TokenExchange(address indexed buyer, int128 sold_id, uint256 tokens_sold, int128 bought_id, uint256 tokens_bought)` — **same topic0 as classic** |
| `0xd013ca23e77a65003c2c659c5442c00c805371b7fc1ebd4c206c41d1536bd90b` | `TokenExchangeUnderlying(...)` — metapool only, same as classic |
| `0x189c623b666b1b45b83d7178f39b8c087cb09774317ca2f53c2d3c3726f222a2` | `AddLiquidity(address indexed provider, uint256[] token_amounts, uint256[] fees, uint256 invariant, uint256 token_supply)` — **dynamic arrays → new topic0** |
| `0x347ad828e58cbe534d8f6b67985d791360756b18f0d95fd9f197a66cc46480ea` | `RemoveLiquidity(address indexed provider, uint256[] token_amounts, uint256[] fees, uint256 token_supply)` |
| `0x6f48129db1f37ccb9cc5dd7e119cb32750cabdf75b48375d730d26ce3659bbe1` | `RemoveLiquidityOne(address indexed provider, int128 token_id, uint256 token_amount, uint256 coin_amount, uint256 token_supply)` — NG adds `token_id`+`token_supply` |
| `0x3631c28b1f9dd213e0319fb167b554d76b6c283a41143eb400a0d1adb1af1755` | `RemoveLiquidityImbalance(address indexed provider, uint256[] token_amounts, uint256[] fees, uint256 invariant, uint256 token_supply)` |
| `0xa2b71ec6df949300b59aab36b55e189697b750119dd349fcfa8c0f779e83c254` | `RampA(...)` — same as classic |
| `0x46e22fb3709ad289f62ce63d469248536dbc78d82b84a3d7e74ad606dc201938` | `StopRampA(uint256 A, uint256 t)` — same as classic |
| `0x750d10a7f37466ce785ee6bcb604aac543358db42afbcc332a3c12a49c80bf6d` | `ApplyNewFee(uint256 fee, uint256 offpeg_fee_multiplier)` — NG replaces Commit/NewFee |
| `0x68dc4e067dff1862b896b7a0faf55f97df1a60d0aaa79481b69d675f2026a28c` | `SetNewMATime(uint256 ma_exp_time, uint256 D_ma_time)` |

NG pools are ERC-20 themselves, so they also emit standard `Transfer`/`Approval` (§1.7).

### 1.3 CryptoSwap — old tricrypto-2 (`curve-crypto-contract`; 3-coin, separate LP token)

| topic0 | Event |
|--------|-------|
| `0xb2e76ae99761dc136e598d4a629bb347eccb9532a5f8bbd72e18467c3c34cc98` | `TokenExchange(address indexed buyer, uint256 sold_id, uint256 tokens_sold, uint256 bought_id, uint256 tokens_bought)` — **`uint256` indices, 5 args, no fee field** |
| `0x96b486485420b963edd3fdec0b0195730035600feb7de6f544383d7950fa97ee` | `AddLiquidity(address indexed provider, uint256[3] token_amounts, uint256 fee, uint256 token_supply)` |
| `0xd6cc314a0b1e3b2579f8e64248e82434072e8271290eef8ad0886709304195f5` | `RemoveLiquidity(address indexed provider, uint256[3] token_amounts, uint256 token_supply)` |
| `0x5ad056f2e28a8cec232015406b843668c1e36cda598127ec3b8c59b8c72773a0` | `RemoveLiquidityOne(address indexed provider, uint256 token_amount, uint256 coin_index, uint256 coin_amount)` |
| `0x6059a38198b1dc42b3791087d1ff0fbd72b3179553c25f678cd246f52ffaaf59` | `ClaimAdminFee(address indexed admin, uint256 tokens)` |
| `0xe35f0559b0642164e286b30df2077ec3a05426617a25db7578fd20ba39a6cd05` | `RampAgamma(uint256 initial_A, uint256 future_A, uint256 initial_gamma, uint256 future_gamma, uint256 initial_time, uint256 future_time)` |
| `0x5f0e7fba3d100c9e19446e1c92fe436f0a9a22fe99669360e4fdd6d3de2fc284` | `StopRampA(uint256 current_A, uint256 current_gamma, uint256 time)` |
| `0x1c65bbdc939f346e5d6f0bde1f072819947438d4fc7b182cc59c2f6dc5504087` | `NewParameters(uint256 admin_fee, uint256 mid_fee, uint256 out_fee, uint256 fee_gamma, uint256 allowed_extra_profit, uint256 adjustment_step, uint256 ma_half_time)` — **7 args** |
| `0x913fde9a37e1f8ab67876a4d0ce80790d764fcfc5692f4529526df9c6bdde553` | `CommitNewParameters(uint256 indexed deadline, …7 params…)` — **8 args** |

### 1.4 Tricrypto-NG (`tricrypto-ng`; 3-coin, pool *is* LP token)

| topic0 | Event |
|--------|-------|
| `0x143f1f8e861fbdeddd5b46e844b7d3ac7b86a122f36e8c463859ee6811b1f29c` | `TokenExchange(address indexed buyer, uint256 sold_id, uint256 tokens_sold, uint256 bought_id, uint256 tokens_bought, uint256 fee, uint256 packed_price_scale)` — **7 args (adds fee + price)** |
| `0xe1b60455bd9e33720b547f60e4e0cfbf1252d0f2ee0147d53029945f39fe3c1a` | `AddLiquidity(address indexed provider, uint256[3] token_amounts, uint256 fee, uint256 token_supply, uint256 packed_price_scale)` |
| `0xd6cc314a0b1e3b2579f8e64248e82434072e8271290eef8ad0886709304195f5` | `RemoveLiquidity(address indexed provider, uint256[3] token_amounts, uint256 token_supply)` — **same topic0 as old tricrypto-2** |
| `0xe200e24d4a4c7cd367dd9befe394dc8a14e6d58c88ff5e2f512d65a9e0aa9c5c` | `RemoveLiquidityOne(address indexed provider, uint256 token_amount, uint256 coin_index, uint256 coin_amount, uint256 approx_fee, uint256 packed_price_scale)` |
| `0x6059a38198b1dc42b3791087d1ff0fbd72b3179553c25f678cd246f52ffaaf59` | `ClaimAdminFee(address indexed admin, uint256 tokens)` — same as old crypto |
| `0xe35f0559b0642164e286b30df2077ec3a05426617a25db7578fd20ba39a6cd05` | `RampAgamma(...)` — same as old crypto |
| `0x5f0e7fba3d100c9e19446e1c92fe436f0a9a22fe99669360e4fdd6d3de2fc284` | `StopRampA(uint256 current_A, uint256 current_gamma, uint256 time)` |
| `0xa32137411fc7c20db359079cd84af0e2cad58cd7a182a8a5e23e08e554e88bf0` | `NewParameters(uint256 mid_fee, uint256 out_fee, uint256 fee_gamma, uint256 allowed_extra_profit, uint256 adjustment_step, uint256 ma_time)` — **6 args, no admin_fee** |
| `0xec36b92a482408f90e07357ca20c8cfaca85affe765903cb242e377fafb166af` | `CommitNewParameters(uint256 indexed deadline, …6 params…)` — **7 args** |

### 1.5 Twocrypto-NG (`twocrypto-ng`; 2-coin, pool *is* LP token)

| topic0 | Event |
|--------|-------|
| `0x143f1f8e861fbdeddd5b46e844b7d3ac7b86a122f36e8c463859ee6811b1f29c` | `TokenExchange(...)` — **same 7-arg topic0 as tricrypto-NG**; last field is single `price_scale` |
| `0x7196cbf63df1f2ec20638e683ebe51d18260be510592ee1e2efe3f3cfd4c33e9` | `AddLiquidity(address indexed provider, uint256[2] token_amounts, uint256 fee, uint256 token_supply, uint256 price_scale)` |
| `0xdd3c0336a16f1b64f172b7bb0dad5b2b3c7c76f91e8c4aafd6aae60dce800153` | `RemoveLiquidity(address indexed provider, uint256[2] token_amounts, uint256 token_supply)` |
| `0xe200e24d4a4c7cd367dd9befe394dc8a14e6d58c88ff5e2f512d65a9e0aa9c5c` | `RemoveLiquidityOne(...)` — **same topic0 as tricrypto-NG** |
| `0x22f9ea3e7d7b113cb423896d2e121f96a66c17814ac7f63d69096769fa3e2a55` | `RemoveLiquidityImbalance(address indexed provider, uint256 lp_token_amount, uint256[2] token_amounts, uint256 approx_fee, uint256 price_scale)` — twocrypto-NG only |
| `0x3bbd5f2f4711532d6e9ee88dfdf2f1468e9a4c3ae5e14d2e1a67bf4242d008d0` | `ClaimAdminFee(address indexed admin, uint256[2] tokens)` — **tokens is an array here** (differs from tri/old scalar) |
| `0xa32137411fc7c20db359079cd84af0e2cad58cd7a182a8a5e23e08e554e88bf0` | `NewParameters(...)` — same 6-arg topic0 as tricrypto-NG |
| `0xe35f0559b0642164e286b30df2077ec3a05426617a25db7578fd20ba39a6cd05` / `0x5f0e7fba3d100c9e19446e1c92fe436f0a9a22fe99669360e4fdd6d3de2fc284` | `RampAgamma` / `StopRampA(uint256,uint256,uint256)` |

### 1.6 Factories (pool-creation events — watch these to enumerate new pools)

| topic0 | Event | Factory |
|--------|-------|---------|
| `0xd1d60d4611e4091bb2e5f699eeb79136c21ac2305ad609f3de569afc3471eecc` | `PlainPoolDeployed(address[] coins, uint256 A, uint256 fee, address deployer)` | Stableswap-**NG** factory |
| `0x5b4a28c940282b5bf183df6a046b8119cf6edeb62859f75e835eb7ba834cce8d` | `PlainPoolDeployed(address[4] coins, uint256 A, uint256 fee, address deployer)` | **old** metapool factory (fixed `address[4]`) |
| `0x01f31cd2abdeb4e5e10ba500f2db0f937d9e8c735ab04681925441b4ea37eda5` | `MetaPoolDeployed(address coin, address base_pool, uint256 A, uint256 fee, address deployer)` | both stableswap factories |
| `0xa307f5d0802489baddec443058a63ce115756de9020e2b07d3e2cd2f21269e2a` | `TricryptoPoolDeployed(address pool, string name, string symbol, address weth, address[3] coins, address math, bytes32 salt, uint256 packed_precisions, uint256 packed_A_gamma, uint256 packed_fee_params, uint256 packed_rebalancing_params, uint256 packed_prices, address deployer)` | Tricrypto-NG factory |
| `0x1bfca87cdf324c1e496fa70ab97c7d3413172ca3497c3f5cb2098e31f0686bf7` | `TwocryptoPoolDeployed(address pool, string name, string symbol, address[2] coins, address math, bytes32 salt, uint256[2] precisions, uint256 packed_A_gamma, uint256 packed_fee_params, uint256 packed_rebalancing_params, address deployer)` | Twocrypto-NG factory |
| `0x0394cb40d7dbe28dad1d4ee890bdd35bbb0d89e17924a80a542535e83d54ba14` | `CryptoPoolDeployed(address token, address[2] coins, uint256 A, uint256 gamma, uint256 mid_fee, uint256 out_fee, uint256 allowed_extra_profit, uint256 fee_gamma, uint256 adjustment_step, uint256 admin_fee, uint256 ma_half_time, uint256 initial_price, address deployer)` | **old** crypto factory |
| `0x656bb34c20491970a8c163f3bd62ead82022b379c3924960ec60f6dbfc5aab3b` | `LiquidityGaugeDeployed(address pool, address gauge)` | most factories |
| `0x1d6247eae69b5feb96b30be78552f35de45f61fdb6d6d7e1b08aae159b6226af` | `LiquidityGaugeDeployed(address pool, address token, address gauge)` | old crypto factory (3-arg) |
| `0xcc6afdfec79da6be08142ecee25cf14b665961e25d30d8eba45959be9547635f` | `BasePoolAdded(address base_pool)` | stableswap factories |

### 1.7 AddressProvider / MetaRegistry, ERC-20, DAO events

| topic0 | Event | Contract |
|--------|-------|----------|
| `0x5b0f9b31dc08c19adcc0181c1b97ad54a84487faf0a4fdcb88c8681724298af9` | `NewAddressIdentifier(uint256 indexed id, address addr, string description)` | classic AddressProvider |
| `0xe7a6334c4f573efdf292d404d59adacec345f4f7c76495a034008edda0acef47` | `AddressModified(uint256 indexed id, address new_address, uint256 version)` | classic AddressProvider |
| `0x126b1179a2f21d5e130df19f7483a0a854bb662e3c8ce5dc28e4e8e46dd72690` | `NewEntry(uint256 indexed id, address addr, string description)` | AddressProvider-NG |
| `0x4f3b9988fc693b8d0ea535c1d768a3ac2ea49aca0f685397357a6a9b9ad13dce` | `EntryModified(uint256 indexed id, uint256 version)` | AddressProvider-NG |
| `0x21706341bb0a4b16c93763b24238e8737928e6ebd1f83adb7cec56cf3fc184a3` | `EntryRemoved(uint256 indexed id)` | AddressProvider-NG |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | CRV, LP tokens, NG pools, gauges |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | CRV, LP tokens, NG pools |
| `0x4566dfc29f6f11d13a418c26a02bef7c28bae749d4de47e4e6a7cddea6730d59` | `Deposit(address indexed provider, uint256 value, uint256 indexed locktime, int128 type, uint256 ts)` | VotingEscrow (veCRV) |
| `0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568` | `Withdraw(address indexed provider, uint256 value, uint256 ts)` | VotingEscrow (veCRV) |
| `0x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c` | `Supply(uint256 prevSupply, uint256 supply)` | VotingEscrow (veCRV) |
| `0xfd55b3191f9c9dd92f4f134dd700e7d76f6a0c836a08687023d6d38f03ebd877` | `NewGauge(address addr, int128 gauge_type, uint256 weight)` | GaugeController |
| `0x45ca9a4c8d0119eb329e580d28fe689e484e1be230da8037ade9547d2d25cc91` | `VoteForGauge(uint256 time, address user, address gauge_addr, uint256 weight)` | GaugeController |
| `0x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0` | `Minted(address indexed recipient, address gauge, uint256 minted)` | Minter |
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed provider, uint256 value)` | LiquidityGauge |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed provider, uint256 value)` | LiquidityGauge |
| `0x7ecd84343f76a23d2227290e0288da3251b045541698e575a5515af4f04197a3` | `UpdateLiquidityLimit(address user, uint256 original_balance, uint256 original_supply, uint256 working_balance, uint256 working_supply)` | LiquidityGauge |
| `0xce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6` | `CheckpointToken(uint256 time, uint256 tokens)` | FeeDistributor |
| `0x9cdcf2f7714cca3508c7f0110b04a90a80a3a8dd0e35de99689db74d28c5383e` | `Claimed(address indexed recipient, uint256 amount, uint256 claim_epoch, uint256 max_epoch)` | FeeDistributor |

> **`Deposit`/`Withdraw` topic0 collisions.** veCRV `Deposit`(`0x4566dfc2…`) ≠ gauge `Deposit`(`0xe1fffcc4…`) ≠ ERC-4337/other `Deposit`. Always pair the topic0 with the emitting contract address.

---

## 2. Function signatures (chain-agnostic)

Selectors = `keccak256(canonical signature)[0:4]`, computed with `cast sig`. **Vyper default arguments produce one selector per arity** — the most common ones are listed; trailing optional `_receiver`/`use_eth`/`_claim_admin_fees` args yield additional selectors not all enumerated here.

### 2.1 StableSwap (classic + NG) — `int128` indices

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3df02124` | `exchange(int128 i, int128 j, uint256 dx, uint256 min_dy)` | the workhorse swap |
| `0xa6417ed6` | `exchange_underlying(int128 i, int128 j, uint256 dx, uint256 min_dy)` | lending/meta only |
| `0x7e3db030` | `exchange_received(int128 i, int128 j, uint256 dx, uint256 min_dy)` | **NG only** — no token pull-in (caller pre-transfers) |
| `0x0b4c7e4d` | `add_liquidity(uint256[2] amounts, uint256 min_mint_amount)` | 2-coin (classic + NG metapool) |
| `0x4515cef3` | `add_liquidity(uint256[3] amounts, uint256 min_mint_amount)` | 3-coin |
| `0x029b2f34` | `add_liquidity(uint256[4] amounts, uint256 min_mint_amount)` | 4-coin |
| `0xb72df5de` | `add_liquidity(uint256[] amounts, uint256 min_mint_amount)` | **NG plain pool** (dynamic array) |
| `0x5b36389c` | `remove_liquidity(uint256 amount, uint256[2] min_amounts)` | 2-coin |
| `0xecb586a5` | `remove_liquidity(uint256 amount, uint256[3] min_amounts)` | 3-coin |
| `0xd40ddb8c` | `remove_liquidity(uint256 amount, uint256[] min_amounts)` | NG plain pool |
| `0x1a4d01d2` | `remove_liquidity_one_coin(uint256 token_amount, int128 i, uint256 min_amount)` | |
| `0xe3103273` | `remove_liquidity_imbalance(uint256[2] amounts, uint256 max_burn_amount)` | 2-coin |
| `0x9fdaea0c` | `remove_liquidity_imbalance(uint256[3] amounts, uint256 max_burn_amount)` | 3-coin |
| `0x7706db75` | `remove_liquidity_imbalance(uint256[] amounts, uint256 max_burn_amount)` | NG plain pool |
| `0x5e0d443f` | `get_dy(int128 i, int128 j, uint256 dx)` | view |
| `0x07211ef7` | `get_dy_underlying(int128 i, int128 j, uint256 dx)` | view |
| `0x3883e119` | `calc_token_amount(uint256[3] amounts, bool is_deposit)` | width = N_COINS |
| `0xcc2b27d7` | `calc_withdraw_one_coin(uint256 token_amount, int128 i)` | view |
| `0xfd0684b1` | `stored_rates()` | NG: per-coin rate multipliers |

### 2.2 CryptoSwap (old tricrypto-2, tricrypto-NG, twocrypto-NG) — `uint256` indices

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5b41b908` | `exchange(uint256 i, uint256 j, uint256 dx, uint256 min_dy)` | base form (all crypto) |
| `0x394747c5` | `exchange(uint256 i, uint256 j, uint256 dx, uint256 min_dy, bool use_eth)` | old crypto / tricrypto-NG |
| `0x29b244bb` | `exchange_received(uint256 i, uint256 j, uint256 dx, uint256 min_dy)` | twocrypto-NG |
| `0x556d6e9f` | `get_dy(uint256 i, uint256 j, uint256 dx)` | view |
| `0x4515cef3` | `add_liquidity(uint256[3] amounts, uint256 min_mint_amount)` | tricrypto (3-coin) |
| `0x0b4c7e4d` | `add_liquidity(uint256[2] amounts, uint256 min_mint_amount)` | twocrypto (2-coin) |
| `0xf1dc3cc9` | `remove_liquidity_one_coin(uint256 token_amount, uint256 i, uint256 min_amount)` | **`uint256 i`** (vs stableswap `int128`) |
| `0xa3f7cdd5` | `price_scale(uint256 k)` | tricrypto (per-coin) |
| `0xb9e8c9fd` | `price_scale()` | twocrypto (single) |
| `0x68727653` | `price_oracle(uint256 k)` | tricrypto |
| `0x86fc88d3` | `price_oracle()` | twocrypto |
| `0xb1373929` | `gamma()` | crypto-only param |

### 2.3 Common to (almost) all pools

> These selectors are **identical across nearly every Curve pool family** — disambiguate by pool address, not selector.

| Selector | Signature |
|----------|-----------|
| `0xc6610657` | `coins(uint256)` → address |
| `0x4903b0d1` | `balances(uint256)` → uint256 |
| `0xf446c1d0` | `A()` → uint256 |
| `0xbb7b8b80` | `get_virtual_price()` → uint256 |
| `0xddca3f43` | `fee()` → uint256 |
| `0xfc0c546a` | `token()` → address (classic/old crypto: separate LP token) |

### 2.4 Factories / Registry / AddressProvider

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x956aae3a` | `pool_count()` | factories + MetaRegistry |
| `0x3a1d5d8e` | `pool_list(uint256)` | factories |
| `0x9ac90d3d` | `get_coins(address)` | factories + MetaRegistry |
| `0x92e3cc2d` | `get_balances(address)` | factories + MetaRegistry |
| `0xa87df06c` | `find_pool_for_coins(address, address)` | factories |
| `0x493f4f74` | `get_address(uint256 id)` | AddressProvider (both) — **id 7 = MetaRegistry on Ethereum only** (id map is chain-specific) |
| `0xa262904b` | `get_registry()` | classic AddressProvider |
| `0xbdf475c3` | `get_pool_from_lp_token(address)` | MetaRegistry |
| `0x619ea806` | `is_registered(address)` | MetaRegistry |

### 2.5 DAO / tokenomics

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x65fc3873` | `create_lock(uint256 value, uint256 unlock_time)` | VotingEscrow |
| `0x4957677c` | `increase_amount(uint256 value)` | VotingEscrow |
| `0xeff7a612` | `increase_unlock_time(uint256 unlock_time)` | VotingEscrow |
| `0xd7136328` | `vote_for_gauge_weights(address gauge, uint256 weight)` | GaugeController |
| `0x6207d866` | `gauge_relative_weight(address)` | GaugeController |
| `0x6a627842` | `mint(address gauge)` | Minter (note: same selector as Uniswap V2 `mint(address)`) |
| `0xa51e1904` | `mint_many(address[8] gauges)` | Minter |
| `0xb6b55f25` | `deposit(uint256)` / `0x2e1a7d4d` `withdraw(uint256)` | LiquidityGauge |
| `0xe6f1daf2` | `claim_rewards()` | LiquidityGauge |
| `0x33134583` | `claimable_tokens(address)` | LiquidityGauge |
| `0x4e71d92d` | `claim()` | FeeDistributor (default `_addr`) |

---

## 3. Core infrastructure — same address on every chain

Curve deploys its registry stack with a deterministic deployer, so several addresses are **identical across all seven chains**. Always still condition on `(chainId, address)`.

| Role | Address | Notes |
|------|---------|-------|
| **AddressProvider (classic)** | `0x0000000022D53366457F9d5E68Ec105046FC4383` | Same on all 8 chains (code verified on each; Base is a smaller 1546-byte variant). The legacy entry point: `get_address(id)`. |
| **AddressProvider-NG** | `0x5ffe7FB82894076ECB99A30D6A32e969e6e35E98` | The **newer** id-registry — same address on all 8 chains (verified). This, not the classic `0x0000…4383`, is where the NG factories are registered; it has its **own** id-map (Eth, read live: 1=PoolInfo, 2=Exchange Router `0x16c6521d…`, 4=crvUSD FeeDistributor `0xd16d5ec3…`, 7=MetaRegistry, 8=crvUSD Stableswap factory, 11=Tricrypto-NG factory, 12=StableSwap-NG factory `0x6A8c…21bf`, 13=Twocrypto-NG factory, 18=RateProvider). Emits `NewEntry`/`EntryModified` (§1.7). |
| **Gauge factory (Root/Child)** | `0xabC000d88f23Bb45525E447528DBF656A9D55bf5` | Same address on all 8 chains. On **Ethereum** it is the **RootLiquidityGaugeFactory** (deploys L1 root gauges, ~1.75 KB); on **every L2** it is the **ChildLiquidityGaugeFactory** (deploys L2 child gauges, ~3.5 KB) — *different bytecode per role, same address*. Watch its gauge-deploy events (§1.6). |
| **MetaRegistry (Ethereum)** | `0xF98B45FA17DE75FB1aD0e7aFD971b0ca00e379fC` | On **Ethereum** reachable via `AddressProvider.get_address(7)` (verified on-chain). **This does NOT generalize** — on Arbitrum/Optimism/Base/Gnosis/Avalanche `get_address(7)` returns `0x0`, and on Polygon it returns a different contract. The id→contract map is chain-specific; find the L2 MetaRegistry by scanning the AddressProvider's populated ids per chain. |
| **TwoCrypto-NG factory** | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` | Identical on Ethereum, Arbitrum, Optimism, Polygon, Gnosis, Avalanche, **BSC**. **Base is the exception** (`0xc9Fe0C63…b665F`). |
| **Router (CurveRouterNG)** | `0x0DCDED3545D565bA3B19E683431381007245d983` | Live on Optimism, Polygon, Gnosis, Avalanche **and also Ethereum + Arbitrum** (verified, ~20–24 KB), where it **coexists** with the per-chain routers listed in §4–§5. Base (`0x4f37…fc1F`) and BSC (`0xA72C…51CC`) differ. A second, newer Ethereum router — the AP-NG "Exchange Router" `0x16c6521dff6bab339122a0fe25a9116693265353` — is also live. **Multiple router versions coexist per chain; track every router present, not just one.** |
| **Deposit & Stake zap** | `0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD` | Identical on Arbitrum, Optimism, Polygon, Gnosis, Avalanche. |

`AddressProvider` IDs are **chain-specific — read them, don't assume.** On **Ethereum** the *classic* AddressProvider id-map is (all read live 2026-06-02 via `get_address(id)`): `0` = Main Registry `0x90e0…d7f5`, `1` = PoolInfo, `2` = **Exchanges** `0x99a58482bd75cbab83b27ec03ca68ff489b5788f`, `3` = **Metapool Factory** `0xb9fc…90d4`, `4` = **crvUSD FeeDistributor** `0xd16d5ec3…`, `5` = **CryptoSwap Registry** `0x8f942c20d02befc377d41445793068908e2250d0`, `6` = **Cryptopool Factory** `0xf18056bb…`, `7` = MetaRegistry, `8` = crvUSD Stableswap factory `0x4f8846ae…`, `11` = Tricrypto-NG factory. ⚠️ **Earlier drafts of this doc inverted ids 3/5/6** ("3 = crypto Registry, 5 = crypto factory") — that was wrong; the live values above are authoritative. On L2s the same ids map to different contracts (e.g. Polygon `get_address(7)` returns the OldCrypto factory `0xe5de15a9…`, **not** the MetaRegistry) or are unpopulated (`get_address(7)` = `0x0` on Arbitrum/Optimism/Base/Gnosis/Avalanche). The NG factories live under the separate **AddressProvider-NG** `0x5ffe7FB8…` id-map (see the §3 table).

---

## 4. Addresses — Ethereum mainnet (chain ID 1)

### 4.1 Factories & registries

| Role | Address |
|------|---------|
| AddressProvider | `0x0000000022D53366457F9d5E68Ec105046FC4383` |
| MetaRegistry | `0xF98B45FA17DE75FB1aD0e7aFD971b0ca00e379fC` |
| Main StableSwap Registry | `0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d7f5` |
| PoolInfo | `0xe64608E223433E8a03a1DaaeFD8Cb638C14B552C` |
| Stableswap-NG factory | `0x6A8cbed756804B16E05E741eDaBd5cB544AE21bf` |
| Tricrypto-NG factory | `0x0c0e5f2fF0ff18a3be9b835635039256dC4B4963` |
| Twocrypto-NG factory | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` |
| Old metapool/stableswap factory | `0xB9fC157394Af804a3578134A6585C0dc9cc990d4` |
| Old crypto-swap factory | `0xF18056Bbd320E96A48e3Fbf8bC061322531aac99` |
| Router (CurveRouterNG) | `0x45312ea0eFf7E09C83CBE249fa1d7598c4C8cd4e` |
| Exchange Router (newer, AP-NG id2) | `0x16c6521dff6bab339122a0fe25a9116693265353` |
| Deposit & Stake zap | `0x56C526b0159a258887e0d79ec3a80dfb940d0cD7` |
| AddressProvider-NG | `0x5ffe7FB82894076ECB99A30D6A32e969e6e35E98` |
| RootLiquidityGaugeFactory | `0xabC000d88f23Bb45525E447528DBF656A9D55bf5` |
| Exchanges registry (AP id2) | `0x99a58482bd75cbab83b27ec03ca68ff489b5788f` |
| CryptoSwap Registry (AP id5) | `0x8f942c20d02befc377d41445793068908e2250d0` |
| crvUSD Stableswap pool factory (AP id8; `pool_count` 29) | `0x4F8846Ae9380B90d2E71D5e3D042dff3E7ebb40d` |
| crvUSD FeeDistributor (AP id4, veCRV sink) | `0xD16d5eC345Dd86Fb63C6a9C43c517210F1027914` |

### 4.2 DAO / tokenomics

| Role | Address |
|------|---------|
| CRV token (ERC20CRV) | `0xD533a949740bb3306d119CC777fa900bA034cd52` |
| VotingEscrow (veCRV) | `0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2` |
| GaugeController | `0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB` |
| Minter | `0xd061D61a4d941c39E5453435B6345Dc261C2fcE0` |
| FeeDistributor (3CRV, veCRV fees) | `0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc` |
| PoolProxy (fee receiver / admin) | `0xeCb456EA5365865EbAb8a2661B0c503410e9B347` |
| Ownership Agent | `0x40907540d8a6c65c637785e8f8b742ae6b0b9968` |
| Parameter Agent | `0x4eeb3ba4f221ca16ed4a0cc7254e2e32df948c5f` |
| Ownership voting app | `0xE478de485ad2fe566d49342Cbd03E49ed7db3356` |
| Parameter voting app | `0xBCfF8B0b9419b9a88c44546519b1e909cf330399` |

### 4.3 Flagship pools (illustrative — enumerate the rest via factory events / MetaRegistry)

| Pool | Pool address | LP token | Family |
|------|--------------|----------|--------|
| 3pool (DAI/USDC/USDT) | `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7` | `0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490` | StableSwap classic (3-coin) |
| stETH/ETH | `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` | `0x06325440D014e39736583c165C2963BA99fAf14E` | StableSwap classic (2-coin) |
| tricrypto-2 (USDT/WBTC/WETH) | `0xD51a44d3FaE010294C616388b506AcdA1bfAAE46` | `0xc4AD29ba4B3c580e6D59105FFf484999997675Ff` | CryptoSwap old (3-coin) |
| TricryptoUSDC (USDC/WBTC/WETH) | `0x7F86Bf177Dd4F3494b841a37e810A34dD56c829B` | pool = LP | Tricrypto-NG |
| TricryptoUSDT (USDT/WBTC/WETH) | `0xf5f5B97624542D72A9E06f04804Bf81baA15e2B4` | pool = LP | Tricrypto-NG |

### 4.4 NG blueprint/implementation helpers (Ethereum) — referenced in the factory `*Deployed` events

The NG factories delegate heavy math/views to shared **implementation** contracts (recorded in each pool's `*Deployed` event, §1.6) and clone a **gauge implementation**. These are immutable Vyper deployments, all `eth_getCode`-verified on Ethereum (2026-06-02). You rarely key alerts on them, but you need them to decode `*Deployed` events and to recognise the math contract a crypto pool delegates to.

| Role | Address |
|------|---------|
| StableSwap-NG views impl | `0xff53042865df617de4bb871bd0988e7b93439ccf` |
| StableSwap-NG / Twocrypto math impl | `0xc9cbc565a9f4120a2740ec6f64cc24aeb2bb3e5e` |
| StableSwap-NG / Twocrypto gauge impl | `0x38d9bda812da2c68dfc6ade85a7f7a54e77f8325` |
| Tricrypto-NG views impl | `0x064253915b8449fdefac2c4a74aa9fdf56691a31` |
| Tricrypto-NG math impl | `0xcbff3004a20dbfe2731543aa38599a526e0fd6ee` |
| Tricrypto-NG gauge impl | `0x5fc124a161d888893529f67580ef94c2784e9233` |
| Twocrypto-NG math impl | `0x1fd8af16dc4bebd950521308d55d0543b6cdf4a1` |
| Twocrypto-NG views impl | `0x07cdebf81977e111b08c126defa07818d0045b80` |
| FeeCollector (NG `fee_receiver`, Ethereum) | `0xa2bcd1a4efbd04b63cd03f5aff2561106ebcce00` |

On L2s the SSNG/Tricrypto factories return their **own** per-chain math impls (e.g. Arbitrum SSNG math `0xd4a8bd4d…`); `gauge_implementation` is `0x0` on L2 factories because the **ChildLiquidityGaugeFactory** (`0xabC000…55bf5`, §3) deploys L2 gauges instead.

---

## 5–9. Addresses — L2 / sidechains

All from `curvefi/curve-js` `network_constants.ts`, on-chain re-verified. AddressProvider is `0x0000000022D53366457F9d5E68Ec105046FC4383` on every chain (omitted from the rows below). CRV is bridged (a different address per chain). The MetaRegistry is **not** uniformly at `get_address(7)` on L2s — that id is Ethereum-specific (see §3).

### 5. Arbitrum One (chain ID 42161)

| Role | Address |
|------|---------|
| CRV (bridged) | `0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978` |
| crvUSD (bridged) | `0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5` |
| Stableswap-NG factory | `0x9AF14D26075f142eb3F292D5065EB3faa646167b` |
| Tricrypto-NG factory | `0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8` |
| Twocrypto-NG factory | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` |
| Old metapool factory | `0xb17b674D9c5CB2e441F8e196a2f048A81355d031` |
| Router | `0x2191718CD32d02B8E60BAdFFeA33E4B5DD9A0A0D` |
| Deposit & Stake | `0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD` |

### 6. Optimism (chain ID 10)

| Role | Address |
|------|---------|
| CRV (bridged) | `0x0994206dfE8De6Ec6920FF4D779B0d950605Fb53` |
| crvUSD (bridged) | `0xC52D7F23a2e460248Db6eE192Cb23dD12bDDCbf6` |
| Stableswap-NG factory | `0x5eeE3091f747E60a045a2E715a4c71e600e31F6E` |
| Tricrypto-NG factory | `0xc6C09471Ee39C7E30a067952FcC89c8922f9Ab53` |
| Twocrypto-NG factory | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` |
| Old metapool factory | `0x2db0E83599a91b508Ac268a6197b8B14F5e72840` |
| Router | `0x0DCDED3545D565bA3B19E683431381007245d983` |
| Deposit & Stake | `0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD` |

### 7. Base (chain ID 8453)

| Role | Address |
|------|---------|
| CRV (bridged) | `0x8Ee73c484A26e0A5df2Ee2a4960B789967dd0415` |
| Stableswap-NG factory | `0xd2002373543Ce3527023C75e7518C274A51ce712` |
| Tricrypto-NG factory | `0xA5961898870943c68037F6848d2D866Ed2016bcB` |
| Twocrypto-NG factory | `0xc9Fe0C63Af9A39402e8a5514f9c43Af0322b665F` — **chain-specific, not the shared `0x98EE…` address** |
| Old crypto factory | `0x5EF72230578b3e399E6C6F4F6360edF95e83BBfd` |
| Old metapool factory | `0x3093f9B57A428F3EB6285a589cb35bEA6e78c336` |
| Router | `0x4f37A9d177470499A2dD084621020b023fcffc1F` |
| Deposit & Stake | `0x69522fb5337663d3B4dFB0030b881c1A750Adb4f` |

### 8. Polygon PoS (chain ID 137)

| Role | Address |
|------|---------|
| CRV (bridged) | `0x172370d5Cd63279eFa6d502DAB29171933a610AF` |
| Stableswap-NG factory | `0x1764ee18e8B3ccA4787249Ceb249356192594585` |
| Tricrypto-NG factory | `0xC1b393EfEF38140662b91441C6710Aa704973228` |
| Twocrypto-NG factory | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` |
| Old crypto factory | `0xE5De15A9C9bBedb4F5EC13B131E61245f2983A69` |
| Old metapool factory | `0x722272D36ef0Da72FF51c5A65Db7b870E2e8D4ee` |
| Router | `0x0DCDED3545D565bA3B19E683431381007245d983` |
| Deposit & Stake | `0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD` |

### 9. Gnosis (chain ID 100) & Avalanche (chain ID 43114)

| Role | Gnosis | Avalanche |
|------|--------|-----------|
| CRV (bridged) | `0x712b3d230F3C1c19db860d80619288b1f0BDd0BD` | `0x47536F17F4fF30e64A96a7555826b8f9e66ec468` |
| Stableswap-NG factory | `0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8` | `0x1764ee18e8B3ccA4787249Ceb249356192594585` |
| Tricrypto-NG factory | `0xb47988aD49DCE8D909c6f9Cf7B26caF04e1445c8` | `0x3d6cB2F6DcF47CDd9C13E4e3beAe9af041d8796a` |
| Twocrypto-NG factory | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` |
| Old metapool factory | `0xD19Baeadc667Cf2015e395f2B08668Ef120f41F5` | `0xb17b674D9c5CB2e441F8e196a2f048A81355d031` |
| Router | `0x0DCDED3545D565bA3B19E683431381007245d983` | `0x0DCDED3545D565bA3B19E683431381007245d983` |
| Deposit & Stake | `0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD` | `0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD` |

### 9b. BNB Smart Chain (chain ID 56) — factory-only

On-chain verified via `bsc-rpc.publicnode.com`. The classic `AddressProvider` exists (`0x0000…4383`, code present) but its registry ids are **unpopulated** (`get_address()` = `0x0`) — Curve on BSC is purely factory-deployed pools: no MetaRegistry, no native CRV/gauge stack.

| Role | Address |
|------|---------|
| Stableswap-NG factory | `0xd7E72f3615aa65b92A4DBdC211E296a35512988B` (pool_count 168 ✓) |
| Tricrypto-NG factory | `0xc55837710bc500F1E3c7bb9dd1d51F7c5647E657` (pool_count 20 ✓) |
| Twocrypto-NG factory | `0x98EE851a00abeE0d95D08cF4CA2BdCE32aeaAF7F` (pool_count 126 ✓; shared addr) |
| Old crypto factory | `0xBd5fBd2FA58cB15228a9Abdac9ec994f79E3483C` (pool_count 10 ✓) |
| Old metapool factory | `0xEfDE221f306152971D8e9f181bFe998447975810` (pool_count 0 — deployed, empty ✓) |
| Router (CurveRouterNG) | `0xA72C85C258A81761433B4e8da60505Fe3Dd551CC` |
| Deposit & Stake | `0x4f37A9d177470499A2dD084621020b023fcffc1F` |

**CRV: none** — curve-js lists `0x8Ee73c…0415` (a Base address) which has no code on BSC; treat as unset. No MetaRegistry / classic registry on BSC.

---

## 9c. Cross-chain summary (presence matrix)

`✓` = bytecode confirmed via `eth_getCode` on 2026-06-02; `—` = not deployed / not listed (absence not exhaustively probed for the old-crypto factory on chains where Curve never shipped it). **AddressProvider, AddressProvider-NG and the Gauge factory share one address across all 8 chains** (§3); everything else is per-chain.

| Chain (ID) | AP | AP-NG | SSNG fac | TriNG fac | TwoNG fac | OldMeta fac | OldCrypto fac | Gauge fac | Router(s) present |
|---|---|---|---|---|---|---|---|---|---|
| Ethereum (1) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Root | `45312…`, `0DCD…`, `16c6…` |
| Arbitrum (42161) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Child | `2191…`, `0DCD…` |
| Optimism (10) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Child | `0DCD…` |
| Base (8453) | ✓ | ✓ | ✓ | ✓ | ✓ ¹ | ✓ | ✓ | Child | `4f37…` |
| Polygon (137) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Child | `0DCD…` |
| Gnosis (100) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Child | `0DCD…` |
| Avalanche (43114) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | Child | `0DCD…` |
| BSC (56) | ✓ ² | ✓ | ✓ | ✓ | ✓ | ✓ ³ | ✓ | Child | `A72C…` |

¹ Base TwoCrypto-NG factory is the chain-specific `0xc9Fe…b665F`, **not** the shared `0x98EE…AF7F`. ² BSC AddressProvider exists but its classic registry ids are unpopulated (factory-only chain). ³ BSC OldMeta factory is deployed but `pool_count` 0.

### 9c.1 Per-chain fee receiver (PoolProxy / fee-burn destination)

Each chain routes pool admin fees to a fee receiver (read from the SSNG factory `fee_receiver()`; all `eth_getCode`-verified). Ethereum uses the DAO **PoolProxy** (§4.2); each L2 has its own:

| Chain | Fee receiver (PoolProxy) |
|-------|--------------------------|
| Ethereum | `0xeCb456EA5365865EbAb8a2661B0c503410e9B347` (PoolProxy, §4.2) |
| Arbitrum | `0xd4f94d0aaa640bbb72b5eec2d85f6d114d81a88e` |
| Optimism | `0xbf7e49483881c76487b0989cd7d9a8239b20ca41` |
| Base | `0xe8269b33e47761f552e1a3070119560d5fa8bbd6` |
| Polygon | `0x774d1dba98cfbd1f2bc3a1f59c494125e07c48f9` |
| Gnosis | `0xbb7404f9965487a9dde721b3a5f0f3ccfa9aa4c5` |
| Avalanche | `0x06534b0bf7ff378f162d4f348390bda53b15fa35` |
| BSC | `0x98b4029cabef7fd525a36b0bf8555ec1d42ec0b6` |

---

## 10. crvUSD, LlamaLend & scrvUSD → see [crvusd.md](crvusd.md)

Curve's **crvUSD** stablecoin (overcollateralized minting), the **LlamaLend / Curve Lend** lending markets (built on the same LLAMMA soft-liquidation engine), and **scrvUSD** (the ERC-4626 savings wrapper) are a distinct product line with their own event vocabulary (`Borrow`, `Repay`, `Liquidate`, `RemoveCollateral`, `UserState`, ERC-4626 `Deposit`/`Withdraw`, …). They are documented in full — topics, selectors, every address on all 8 chains, proxies — in the sibling file **[crvusd.md](crvusd.md)**. Quick orientation (Ethereum):

| Role | Address | Note |
|------|---------|------|
| crvUSD token | `0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E` | bridged to a *different* address on each L2 (see crvusd.md) |
| ControllerFactory (mint markets) | `0xC9332fdCB1C491Dcc683bAe86Fe3cb70360738BC` | `n_collaterals()` = 9; mint markets are **Ethereum-only** |
| OneWayLendingFactory (LlamaLend) | `0xeA6876DDE9e3467564acBeE1Ed5bac88783205E0` | `market_count()` = 48 |
| scrvUSD (savings) | `0x0655977FEb2f289A4aB78af67BAB0d17aAb84367` | ERC-4626; Yearn-V3 clone |

> ⚠️ **Correction:** earlier drafts listed the LlamaLend factory as `0x4F8846Ae…`. That address is the **crvUSD Stableswap *pool* factory** (`pool_count` = 29, AddressProvider id8 / §4.1) — `market_count()` reverts on it. The real **OneWayLendingFactory** is `0xeA6876DD…` (`market_count()` = 48, verified live).

Mint markets exist **only on Ethereum**; LlamaLend is on **Ethereum + Arbitrum + Optimism** (of the 8 chains); every other chain has only the bridged crvUSD token. Each collateral/market has its own **Controller** + **LLAMMA** AMM — enumerate via the factories, never hard-code. Full detail in [crvusd.md](crvusd.md).

---

## 11. Proxies

Curve does **not** use upgradeable proxies for its pools. Modern (NG) pools are deployed by factories via **EIP-5202 blueprint** contracts (`create_from_blueprint`) — each pool is a full, independent bytecode deployment, **not** an EIP-1167 minimal-proxy clone, and its logic is **immutable** once deployed. The factory can register a new blueprint implementation, but that only affects *future* pools; existing pools never change code.

| Item | Pattern | Why it matters |
|------|---------|----------------|
| NG pool creation | `create_from_blueprint(impl, …)` (EIP-5202) → CREATE/CREATE2 | Pool address is not CREATE2-derivable from coins alone (salt + blueprint vary) — **enumerate via the factory's `*Deployed` event, do not try to derive like Uniswap V2.** |
| Pool logic upgrade | **None** | Existing pools are frozen. No proxy-impl slot to watch. |
| Pool parameters (A, fees) | mutable by admin | Surfaces as `RampA`/`StopRampA`/`NewParameters`/`ApplyNewFee` events, gated behind the Ownership/Parameter Agent timelock. |
| Math contract | external, set at deploy | Crypto pools delegate heavy math to a shared `math` contract (recorded in the `*Deployed` event), not a delegatecall proxy. |

There is no single init-code hash (contrast Uniswap V2 §11). See `references/proxies.md` for general proxy detection if you encounter wrapped/zap contracts around Curve.

---

## 12. Detection invariants & gotchas

1. **`int128` vs `uint256` indices is the family fingerprint.** `TokenExchange` with `int128` sold/bought ids → StableSwap; with `uint256` → CryptoSwap. This is the cleanest way to classify a swap log without first resolving the pool.
2. **`TokenExchange` topic0 is reused within families.** Classic + NG StableSwap share `0x8b3e96f2…`; tricrypto-NG + twocrypto-NG share the 7-arg `0x143f1f8e…`; old tricrypto-2 is unique (`0xb2e76ae9…`, 5-arg). You cannot tell NG-stable from classic-stable by `TokenExchange` topic0 alone — use the `AddLiquidity` topic0 or the pool's factory.
3. **`AddLiquidity`/`RemoveLiquidity` topic0 encodes the coin count and the generation.** Classic uses fixed `uint256[N]` (distinct topic0 per N=2/3/4); NG-stable uses dynamic `uint256[]` (`0x189c623b…`); crypto variants differ again. A single alert that wants "all Curve liquidity adds" must match a *set* of topic0s, not one.
4. **Pools are factory-deployed and numerous — enumerate, don't derive.** Watch each factory's `*Deployed` event (§1.6) to discover new pools, or read MetaRegistry. There is no Uniswap-style CREATE2 init-code-hash shortcut (§11).
5. **The swap fee is not its own event.** Curve fees are taken inside `exchange()`; NG crypto events embed a `fee` field in `TokenExchange`, but classic/stable do not — derive fees from pool params (`fee()`, `mid_fee`/`out_fee` for crypto).
6. **NG `exchange_received` moves tokens before the call.** A swap can happen with **no incoming ERC-20 `Transfer` to the pool inside the same call frame** when `exchange_received` is used (caller pre-funds). Naive "detect swap by Transfer-into-pool" logic misses these.
7. **`TokenExchangeUnderlying` only fires on lending/metapools.** A metapool swap touching the base-pool coins emits `TokenExchangeUnderlying` (`0xd013ca23…`), not `TokenExchange`. Monitor both.
8. **`coins`/`balances`/`A`/`get_virtual_price` selectors are shared across virtually all families** (`0xc6610657`/`0x4903b0d1`/`0xf446c1d0`/`0xbb7b8b80`). Never infer pool type from these — always from the event topic0 or the factory.
9. **NG pools ARE their own LP token; classic + old-crypto pools have a separate LP token.** For NG, the pool address emits ERC-20 `Transfer`/`Approval`. For classic, the LP token is a different contract (see `token()` / the LP column in §4.3). LP-supply accounting must target the right contract.
10. **AddressProvider is the same address on every chain** (`0x0000…fc4383`), but the registries/factories it points to are chain-specific. Resolve infra by `get_address(id)` per chain rather than hard-coding. **`id 7 = MetaRegistry` only on Ethereum** — on L2s that id is `0x0` or points elsewhere (and on BSC the AddressProvider's ids are entirely unpopulated).
11. **Factory addresses cluster across chains.** The TwoCrypto-NG factory is `0x98EE…AF7F` on every chain (ETH/Arbitrum/Optimism/Polygon/Gnosis/Avalanche/BSC) **except Base** (`0xc9Fe…b665F`); the Router `0x0DCD…d983` and Deposit&Stake `0x37c5…14FD` repeat on several L2s. Always condition on `(chainId, address)`.
12. **Parameter changes are timelocked DAO actions.** `RampA`/`NewParameters`/`ApplyNewFee` originate from the Ownership/Parameter Agent (§4.2) via the DAO, not from random EOAs — useful for distinguishing legitimate parameter changes from anomalies.
13. **`mint(address)` selector `0x6a627842` collides with Uniswap V2 `mint(address)`.** On Curve it is the Minter claiming CRV for a gauge; disambiguate by target address (Minter `0xd061…2fcE0`).
14. **The Curve Block Oracle and RateProvider are separate infrastructure, not pool contracts.** The 2025 **Curve Block Oracle** (a cross-chain blockhash / storage-proof messaging primitive deployed on 20+ Curve chains; underpins scrvUSD's cross-chain price) and the per-chain **RateProvider** (AddressProvider-NG id 18) are neither DEX pools nor LP tokens — do not classify their events as swap/liquidity activity. They are noted for completeness; their per-chain addresses are not enumerated here.
15. **Bytea hex literals must have an even digit count:** 40 hex chars for addresses, 64 for 32-byte topic values. Topic0 values above are 64 hex chars (32 bytes); selectors are 8 hex chars (4 bytes).

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Event topic0 (chain-agnostic) =====
-- StableSwap (classic + NG)
TOPIC_SS_TOKEN_EXCHANGE              = '\x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140'
TOPIC_SS_TOKEN_EXCHANGE_UNDERLYING   = '\xd013ca23e77a65003c2c659c5442c00c805371b7fc1ebd4c206c41d1536bd90b'
TOPIC_SS_ADD_LIQ_2COIN               = '\x26f55a85081d24974e85c6c00045d0f0453991e95873f52bff0d21af4079a768'
TOPIC_SS_ADD_LIQ_3COIN               = '\x423f6495a08fc652425cf4ed0d1f9e37e571d9b9529b1c1c23cce780b2e7df0d'
TOPIC_SS_ADD_LIQ_4COIN               = '\x3f1915775e0c9a38a57a7bb7f1f9005f486fb904e1f84aa215364d567319a58d'
TOPIC_SS_REMOVE_LIQ_2COIN            = '\x7c363854ccf79623411f8995b362bce5eddff18c927edc6f5dbbb5e05819a82c'
TOPIC_SS_REMOVE_LIQ_3COIN            = '\xa49d4cf02656aebf8c771f5a8585638a2a15ee6c97cf7205d4208ed7c1df252d'
TOPIC_SS_REMOVE_LIQ_4COIN            = '\x9878ca375e106f2a43c3b599fc624568131c4c9a4ba66a14563715763be9d59d'
TOPIC_SS_REMOVE_LIQ_ONE              = '\x9e96dd3b997a2a257eec4df9bb6eaf626e206df5f543bd963682d143300be310'
TOPIC_SS_REMOVE_LIQ_IMBALANCE_3COIN  = '\x173599dbf9c6ca6f7c3b590df07ae98a45d74ff54065505141e7de6c46a624c2'
-- StableSwap-NG (dynamic arrays)
TOPIC_SSNG_ADD_LIQUIDITY             = '\x189c623b666b1b45b83d7178f39b8c087cb09774317ca2f53c2d3c3726f222a2'
TOPIC_SSNG_REMOVE_LIQUIDITY          = '\x347ad828e58cbe534d8f6b67985d791360756b18f0d95fd9f197a66cc46480ea'
TOPIC_SSNG_REMOVE_LIQ_ONE            = '\x6f48129db1f37ccb9cc5dd7e119cb32750cabdf75b48375d730d26ce3659bbe1'
TOPIC_SSNG_REMOVE_LIQ_IMBALANCE      = '\x3631c28b1f9dd213e0319fb167b554d76b6c283a41143eb400a0d1adb1af1755'
-- CryptoSwap old tricrypto-2
TOPIC_CRYPTO_TOKEN_EXCHANGE          = '\xb2e76ae99761dc136e598d4a629bb347eccb9532a5f8bbd72e18467c3c34cc98'
TOPIC_CRYPTO_ADD_LIQUIDITY           = '\x96b486485420b963edd3fdec0b0195730035600feb7de6f544383d7950fa97ee'
TOPIC_CRYPTO_REMOVE_LIQUIDITY        = '\xd6cc314a0b1e3b2579f8e64248e82434072e8271290eef8ad0886709304195f5'
TOPIC_CRYPTO_REMOVE_LIQ_ONE          = '\x5ad056f2e28a8cec232015406b843668c1e36cda598127ec3b8c59b8c72773a0'
TOPIC_CRYPTO_CLAIM_ADMIN_FEE         = '\x6059a38198b1dc42b3791087d1ff0fbd72b3179553c25f678cd246f52ffaaf59'
-- Tricrypto-NG / Twocrypto-NG (shared 7-arg TokenExchange + RemoveLiqOne)
TOPIC_CRYPTONG_TOKEN_EXCHANGE        = '\x143f1f8e861fbdeddd5b46e844b7d3ac7b86a122f36e8c463859ee6811b1f29c'
TOPIC_TRICRYPTONG_ADD_LIQUIDITY      = '\xe1b60455bd9e33720b547f60e4e0cfbf1252d0f2ee0147d53029945f39fe3c1a'
TOPIC_TWOCRYPTONG_ADD_LIQUIDITY      = '\x7196cbf63df1f2ec20638e683ebe51d18260be510592ee1e2efe3f3cfd4c33e9'
TOPIC_TWOCRYPTONG_REMOVE_LIQUIDITY   = '\xdd3c0336a16f1b64f172b7bb0dad5b2b3c7c76f91e8c4aafd6aae60dce800153'
TOPIC_CRYPTONG_REMOVE_LIQ_ONE        = '\xe200e24d4a4c7cd367dd9befe394dc8a14e6d58c88ff5e2f512d65a9e0aa9c5c'
TOPIC_TWOCRYPTONG_REMOVE_LIQ_IMBAL   = '\x22f9ea3e7d7b113cb423896d2e121f96a66c17814ac7f63d69096769fa3e2a55'
TOPIC_TWOCRYPTONG_CLAIM_ADMIN_FEE    = '\x3bbd5f2f4711532d6e9ee88dfdf2f1468e9a4c3ae5e14d2e1a67bf4242d008d0'
-- Parameter changes (shared)
TOPIC_RAMP_A                         = '\xa2b71ec6df949300b59aab36b55e189697b750119dd349fcfa8c0f779e83c254'
TOPIC_STOP_RAMP_A                    = '\x46e22fb3709ad289f62ce63d469248536dbc78d82b84a3d7e74ad606dc201938'
TOPIC_RAMP_AGAMMA                    = '\xe35f0559b0642164e286b30df2077ec3a05426617a25db7578fd20ba39a6cd05'
TOPIC_SSNG_APPLY_NEW_FEE             = '\x750d10a7f37466ce785ee6bcb604aac543358db42afbcc332a3c12a49c80bf6d'
-- Factory pool-creation events
TOPIC_NG_PLAIN_POOL_DEPLOYED         = '\xd1d60d4611e4091bb2e5f699eeb79136c21ac2305ad609f3de569afc3471eecc'
TOPIC_OLD_PLAIN_POOL_DEPLOYED        = '\x5b4a28c940282b5bf183df6a046b8119cf6edeb62859f75e835eb7ba834cce8d'
TOPIC_META_POOL_DEPLOYED             = '\x01f31cd2abdeb4e5e10ba500f2db0f937d9e8c735ab04681925441b4ea37eda5'
TOPIC_TRICRYPTO_POOL_DEPLOYED        = '\xa307f5d0802489baddec443058a63ce115756de9020e2b07d3e2cd2f21269e2a'
TOPIC_TWOCRYPTO_POOL_DEPLOYED        = '\x1bfca87cdf324c1e496fa70ab97c7d3413172ca3497c3f5cb2098e31f0686bf7'
TOPIC_CRYPTO_POOL_DEPLOYED           = '\x0394cb40d7dbe28dad1d4ee890bdd35bbb0d89e17924a80a542535e83d54ba14'
TOPIC_LIQ_GAUGE_DEPLOYED_2ARG        = '\x656bb34c20491970a8c163f3bd62ead82022b379c3924960ec60f6dbfc5aab3b'
-- DAO / tokenomics
TOPIC_VECRV_DEPOSIT                  = '\x4566dfc29f6f11d13a418c26a02bef7c28bae749d4de47e4e6a7cddea6730d59'
TOPIC_VECRV_WITHDRAW                 = '\xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568'
TOPIC_GC_NEW_GAUGE                   = '\xfd55b3191f9c9dd92f4f134dd700e7d76f6a0c836a08687023d6d38f03ebd877'
TOPIC_GC_VOTE_FOR_GAUGE              = '\x45ca9a4c8d0119eb329e580d28fe689e484e1be230da8037ade9547d2d25cc91'
TOPIC_MINTER_MINTED                  = '\x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0'
TOPIC_GAUGE_DEPOSIT                  = '\xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'
TOPIC_GAUGE_WITHDRAW                 = '\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'
TOPIC_ERC20_TRANSFER                 = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Function selectors =====
SEL_SS_EXCHANGE                      = '\x3df02124'   -- exchange(int128,int128,uint256,uint256)
SEL_SS_EXCHANGE_UNDERLYING           = '\xa6417ed6'
SEL_SS_EXCHANGE_RECEIVED             = '\x7e3db030'   -- NG
SEL_CRYPTO_EXCHANGE                  = '\x5b41b908'   -- exchange(uint256,uint256,uint256,uint256)
SEL_SS_GET_DY                        = '\x5e0d443f'   -- get_dy(int128,int128,uint256)
SEL_CRYPTO_GET_DY                    = '\x556d6e9f'   -- get_dy(uint256,uint256,uint256)
SEL_ADD_LIQ_2COIN                    = '\x0b4c7e4d'
SEL_ADD_LIQ_3COIN                    = '\x4515cef3'
SEL_ADD_LIQ_DYNAMIC                  = '\xb72df5de'   -- NG plain add_liquidity(uint256[],uint256)
SEL_REMOVE_LIQ_ONE_INT128            = '\x1a4d01d2'   -- stableswap
SEL_REMOVE_LIQ_ONE_UINT256           = '\xf1dc3cc9'   -- cryptoswap
SEL_GET_ADDRESS                      = '\x493f4f74'   -- AddressProvider.get_address(uint256)
SEL_POOL_COUNT                       = '\x956aae3a'
SEL_FIND_POOL_FOR_COINS              = '\xa87df06c'

-- ===== Infra (same address on all 8 chains) =====
ADDRESS_PROVIDER                     = '\x0000000022d53366457f9d5e68ec105046fc4383'
ADDRESS_PROVIDER_NG                  = '\x5ffe7fb82894076ecb99a30d6a32e969e6e35e98'  -- NG entry point, all 8 chains
GAUGE_FACTORY_ROOT_CHILD             = '\xabc000d88f23bb45525e447528dbf656a9d55bf5'  -- Root on ETH, Child on every L2
TWOCRYPTO_NG_FACTORY_SHARED          = '\x98ee851a00abee0d95d08cf4ca2bdce32aeaaf7f'  -- NOT Base (Base = 0xc9fe...b665f)
ROUTER_SHARED_L2                     = '\x0dcded3545d565ba3b19e683431381007245d983'  -- OP/Polygon/Gnosis/Avax + ALSO ETH+ARB
DEPOSIT_AND_STAKE_SHARED_L2          = '\x37c5ab57af7100bdc9b668d766e193ccbf6614fd'

-- ===== Ethereum (chain ID 1) =====
ETH_META_REGISTRY                    = '\xf98b45fa17de75fb1ad0e7afd971b0ca00e379fc'
ETH_REGISTRY                         = '\x90e00ace148ca3b23ac1bc8c240c2a7dd9c2d7f5'
ETH_STABLESWAP_NG_FACTORY            = '\x6a8cbed756804b16e05e741edabd5cb544ae21bf'
ETH_TRICRYPTO_NG_FACTORY             = '\x0c0e5f2ff0ff18a3be9b835635039256dc4b4963'
ETH_TWOCRYPTO_NG_FACTORY             = '\x98ee851a00abee0d95d08cf4ca2bdce32aeaaf7f'
ETH_OLD_METAPOOL_FACTORY             = '\xb9fc157394af804a3578134a6585c0dc9cc990d4'
ETH_OLD_CRYPTO_FACTORY               = '\xf18056bbd320e96a48e3fbf8bc061322531aac99'
ETH_CRV                              = '\xd533a949740bb3306d119cc777fa900ba034cd52'
ETH_VECRV                            = '\x5f3b5dfeb7b28cdbd7faba78963ee202a494e2a2'
ETH_GAUGE_CONTROLLER                 = '\x2f50d538606fa9edd2b11e2446beb18c9d5846bb'
ETH_MINTER                           = '\xd061d61a4d941c39e5453435b6345dc261c2fce0'
ETH_FEE_DISTRIBUTOR                  = '\xa464e6dcda8ac41e03616f95f4bc98a13b8922dc'
ETH_3POOL                            = '\xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7'
ETH_STETH_POOL                       = '\xdc24316b9ae028f1497c275eb9192a3ea0f67022'
ETH_TRICRYPTO2                       = '\xd51a44d3fae010294c616388b506acda1bfaae46'
ETH_TRICRYPTO_USDC                   = '\x7f86bf177dd4f3494b841a37e810a34dd56c829b'
ETH_TRICRYPTO_USDT                   = '\xf5f5b97624542d72a9e06f04804bf81baa15e2b4'
ETH_CRVUSD                           = '\xf939e0a03fb07f59a73314e73794be0e57ac1b4e'
ETH_CRVUSD_CONTROLLER_FACTORY        = '\xc9332fdcb1c491dcc683bae86fe3cb70360738bc'
ETH_ONEWAY_LENDING_FACTORY           = '\xea6876dde9e3467564acbee1ed5bac88783205e0'  -- LlamaLend (NOT 0x4f8846ae); see crvusd.md
ETH_CRVUSD_STABLESWAP_FACTORY        = '\x4f8846ae9380b90d2e71d5e3d042dff3e7ebb40d'  -- AP id8, pool_count 29 (NOT lending)
ETH_CRVUSD_FEE_DISTRIBUTOR           = '\xd16d5ec345dd86fb63c6a9c43c517210f1027914'  -- AP id4, veCRV sink
ETH_EXCHANGE_ROUTER_2                = '\x16c6521dff6bab339122a0fe25a9116693265353'  -- AP-NG id2 (newer router)
ETH_EXCHANGES_REGISTRY               = '\x99a58482bd75cbab83b27ec03ca68ff489b5788f'  -- AP id2
ETH_CRYPTOSWAP_REGISTRY              = '\x8f942c20d02befc377d41445793068908e2250d0'  -- AP id5
-- per-chain fee receivers (PoolProxy / fee-burn destination), §9c.1
ETH_POOL_PROXY                       = '\xecb456ea5365865ebab8a2661b0c503410e9b347'
ARB_FEE_RECEIVER                     = '\xd4f94d0aaa640bbb72b5eec2d85f6d114d81a88e'
OP_FEE_RECEIVER                      = '\xbf7e49483881c76487b0989cd7d9a8239b20ca41'
BASE_FEE_RECEIVER                    = '\xe8269b33e47761f552e1a3070119560d5fa8bbd6'
POL_FEE_RECEIVER                     = '\x774d1dba98cfbd1f2bc3a1f59c494125e07c48f9'
GNO_FEE_RECEIVER                     = '\xbb7404f9965487a9dde721b3a5f0f3ccfa9aa4c5'
AVAX_FEE_RECEIVER                    = '\x06534b0bf7ff378f162d4f348390bda53b15fa35'
BSC_FEE_RECEIVER                     = '\x98b4029cabef7fd525a36b0bf8555ec1d42ec0b6'

-- ===== Arbitrum (42161) =====
ARB_CRV                              = '\x11cdb42b0eb46d95f990bedd4695a6e3fa034978'
ARB_CRVUSD                          = '\x498bf2b1e120fed3ad3d42ea2165e9b73f99c1e5'
ARB_STABLESWAP_NG_FACTORY           = '\x9af14d26075f142eb3f292d5065eb3faa646167b'
ARB_TRICRYPTO_NG_FACTORY            = '\xbc0797015fcfc47d9c1856639cae50d0e69fbee8'
ARB_OLD_METAPOOL_FACTORY            = '\xb17b674d9c5cb2e441f8e196a2f048a81355d031'
ARB_ROUTER                          = '\x2191718cd32d02b8e60badffea33e4b5dd9a0a0d'

-- ===== Optimism (10) =====
OP_CRV                              = '\x0994206dfe8de6ec6920ff4d779b0d950605fb53'
OP_CRVUSD                          = '\xc52d7f23a2e460248db6ee192cb23dd12bddcbf6'
OP_STABLESWAP_NG_FACTORY            = '\x5eee3091f747e60a045a2e715a4c71e600e31f6e'
OP_TRICRYPTO_NG_FACTORY             = '\xc6c09471ee39c7e30a067952fcc89c8922f9ab53'
OP_OLD_METAPOOL_FACTORY             = '\x2db0e83599a91b508ac268a6197b8b14f5e72840'

-- ===== Base (8453) =====
BASE_CRV                            = '\x8ee73c484a26e0a5df2ee2a4960b789967dd0415'
BASE_STABLESWAP_NG_FACTORY          = '\xd2002373543ce3527023c75e7518c274a51ce712'
BASE_TRICRYPTO_NG_FACTORY           = '\xa5961898870943c68037f6848d2d866ed2016bcb'
BASE_TWOCRYPTO_NG_FACTORY           = '\xc9fe0c63af9a39402e8a5514f9c43af0322b665f'  -- chain-specific!
BASE_OLD_CRYPTO_FACTORY             = '\x5ef72230578b3e399e6c6f4f6360edf95e83bbfd'
BASE_OLD_METAPOOL_FACTORY           = '\x3093f9b57a428f3eb6285a589cb35bea6e78c336'

-- ===== Polygon (137) =====
POL_CRV                             = '\x172370d5cd63279efa6d502dab29171933a610af'
POL_STABLESWAP_NG_FACTORY           = '\x1764ee18e8b3cca4787249ceb249356192594585'
POL_TRICRYPTO_NG_FACTORY            = '\xc1b393efef38140662b91441c6710aa704973228'
POL_OLD_CRYPTO_FACTORY              = '\xe5de15a9c9bbedb4f5ec13b131e61245f2983a69'
POL_OLD_METAPOOL_FACTORY            = '\x722272d36ef0da72ff51c5a65db7b870e2e8d4ee'

-- ===== Gnosis (100) =====
GNO_CRV                             = '\x712b3d230f3c1c19db860d80619288b1f0bdd0bd'
GNO_STABLESWAP_NG_FACTORY           = '\xbc0797015fcfc47d9c1856639cae50d0e69fbee8'
GNO_TRICRYPTO_NG_FACTORY            = '\xb47988ad49dce8d909c6f9cf7b26caf04e1445c8'
GNO_OLD_METAPOOL_FACTORY            = '\xd19baeadc667cf2015e395f2b08668ef120f41f5'

-- ===== Avalanche (43114) =====
AVAX_CRV                            = '\x47536f17f4ff30e64a96a7555826b8f9e66ec468'
AVAX_STABLESWAP_NG_FACTORY          = '\x1764ee18e8b3cca4787249ceb249356192594585'
AVAX_TRICRYPTO_NG_FACTORY           = '\x3d6cb2f6dcf47cdd9c13e4e3beae9af041d8796a'
AVAX_OLD_METAPOOL_FACTORY           = '\xb17b674d9c5cb2e441f8e196a2f048a81355d031'

-- ===== BNB Smart Chain (56) — factory-only, no CRV/registry =====
BSC_STABLESWAP_NG_FACTORY           = '\xd7e72f3615aa65b92a4dbdc211e296a35512988b'
BSC_TRICRYPTO_NG_FACTORY            = '\xc55837710bc500f1e3c7bb9dd1d51f7c5647e657'
BSC_OLD_CRYPTO_FACTORY              = '\xbd5fbd2fa58cb15228a9abdac9ec994f79e3483c'
BSC_OLD_METAPOOL_FACTORY            = '\xefde221f306152971d8e9f181bfe998447975810'
BSC_ROUTER                          = '\xa72c85c258a81761433b4e8da60505fe3dd551cc'
```

---

## 14. Verification & sources

How the constants in this doc were produced:

- **Event topic0 hashes and function selectors:** computed locally with Foundry `cast keccak` (full keccak256 of the canonical event signature) and `cast sig` (`keccak256(sig)[0:4]`). Canonical signatures were read directly from the `curvefi` Vyper source (see file list below). Every hash/selector in §1, §2, and §13 was machine-computed, not transcribed — these are ground truth.
- **The `int128` vs `uint256` index distinction, NG field layouts, and per-family event differences** were taken from the actual Vyper `event` declarations in source, then confirmed by the hash differing across families.
- **Addresses (§3–§10, §13):** sourced from `curvefi/curve-js` `src/constants/network_constants.ts` (per-chain factories, router, CRV, crvUSD), the Curve readthedocs deployment page, and Etherscan labels — then **independently re-verified on-chain** via `cast` against `publicnode` RPCs on all eight chains incl BSC (originally 2026-05; **fully re-verified 2026-06-02** — every address resolves). Verified: Ethereum `AddressProvider.get_address(7)` = MetaRegistry `0xF98B…79fC` (`pool_count()` = 2272 as of 2026-06-02); CRV `symbol()` = `"CRV"` on every chain that has it; crvUSD `symbol()` = `"crvUSD"`; StableSwap-NG and Tricrypto-NG factories return live `pool_count()` (2026-06-02: Ethereum 906 / 122; Arbitrum 267 / 55; BSC 174 / 28); 3pool `coins(0)` = DAI. **Corrections surfaced by this check:** the `id 7 = MetaRegistry` rule holds **only on Ethereum** — on Arbitrum/Optimism/Base/Gnosis/Avalanche `get_address(7)` = `0x0` and on Polygon it maps elsewhere (§3); **BSC is factory-only** (AddressProvider present but registries unpopulated, and curve-js's BSC `crv` is a Base address with no code on BSC — §9b). Flagship pool addresses (§4.3) are `eth_getCode`-confirmed; the full crvUSD/LlamaLend/scrvUSD address set moved to [crvusd.md](crvusd.md).

- **Re-evaluation pass (2026-06-02) — this revision.** Every address in the doc was `eth_getCode`-checked on each chain it is claimed on (**all resolve**); all 69 topic0 + 56 selectors recomputed (**all match**); proxy slots re-read (**all `0x0` — immutable confirmed**). Corrections folded in: (1) the header Status line (previously "addresses NOT RPC-verified") reconciled — they are verified; (2) the classic AddressProvider id-map read live and **ids 3/5/6 corrected** (3 = Metapool Factory, 5 = CryptoSwap Registry, 6 = Cryptopool Factory; the prior draft inverted 3/5); (3) added **AddressProvider-NG** `0x5ffe7FB8…` (8 chains), the **Root/Child gauge factory** `0xabC000…55bf5` (8 chains), per-chain **PoolProxy fee receivers** (§9c.1), the **NG math/views/gauge impls** + FeeCollector (§4.4), a cross-chain presence matrix (§9c), and a 2nd Ethereum **Exchange Router** `0x16c6521d…`; (4) **corrected the crvUSD lending factory** — the real OneWayLendingFactory is `0xeA6876DD…` (`market_count` 48), while the previously-listed `0x4F8846Ae…` is the crvUSD Stableswap pool factory (`pool_count` 29, AP id8); (5) split the crvUSD/LlamaLend/scrvUSD product line into the sibling [crvusd.md](crvusd.md).

Authoritative source repos / pages:

- Vyper source (signatures): [`curvefi/curve-contract`](https://github.com/curvefi/curve-contract), [`curvefi/stableswap-ng`](https://github.com/curvefi/stableswap-ng), [`curvefi/tricrypto-ng`](https://github.com/curvefi/tricrypto-ng), [`curvefi/twocrypto-ng`](https://github.com/curvefi/twocrypto-ng), [`curvefi/curve-factory`](https://github.com/curvefi/curve-factory), [`curvefi/metaregistry`](https://github.com/curvefi/metaregistry), [`curvefi/curve-dao-contracts`](https://github.com/curvefi/curve-dao-contracts)
- Addresses: [`curvefi/curve-js` network_constants.ts](https://github.com/curvefi/curve-js/blob/master/src/constants/network_constants.ts), [Curve readthedocs deployment addresses](https://curve.readthedocs.io/ref-addresses.html), [Curve Technical Docs — Deployed contracts](https://docs.curve.finance/references/deployed-contracts/)
- Concepts: [Curve Technical Docs — AddressProvider](https://docs.curve.finance/integration/address-provider/), [MetaRegistry](https://docs.curve.finance/integration/metaregistry/)
- [EIP-5202: Blueprint contracts](https://eips.ethereum.org/EIPS/eip-5202)

### 14.1 Independent fact-check (2026-06-02) — verified complete; no refutations, two additive leads

Nine non-obvious claims were cross-checked against the official Curve docs (`docs.curve.finance`), `curvefi/curve-llamalend.js` (`aliases.ts`), the legacy `curve.readthedocs.io` registry, Curve governance/news posts, and block explorers — then re-confirmed on-chain. Verdicts:

1. **AMM generations & core infra complete** (StableSwap classic/NG · old-tricrypto-2 + Tricrypto-NG + Twocrypto-NG · classic AddressProvider + AddressProvider-NG · MetaRegistry · Root/Child gauge factory · CurveRouterNG · DAO stack) — ✅ confirmed; no missing pool *generation* surfaced.
2. **Classic AddressProvider id-map** (0=Main Registry, 2=Exchanges, 3=Metapool Factory, 5=CryptoSwap Registry, 6=Cryptopool Factory, 7=MetaRegistry, 8=crvUSD Stableswap factory, 11=Tricrypto) — ✅ confirmed (read live; docs corroborate).
3. **Pools immutable, EIP-5202 blueprint deploys, no upgradeable proxy** — ✅ confirmed (impl slots `0x0`; documented).
4. **LlamaLend factory = `0xeA6876DD…`; `0x4F8846Ae…` is the crvUSD Stableswap factory, not lending** — ✅ confirmed verbatim by `curve-llamalend.js aliases.ts` (Ethereum `OneWayFactory`) + on-chain `market_count` 48 vs `pool_count` 29.
5. **9 crvUSD mint markets current** — ✅ confirmed: Curve governance/news ("Enhanced crvUSD Markets") confirms cbBTC, weETH, LBTC are the three newest additions atop the existing sfrxETH(×2)/wstETH/WBTC/WETH/tBTC.
6. **LlamaLend on ETH/ARB/OP only (of the 8)** — ✅ confirmed (expanded to Arbitrum/Optimism/Fraxtal by end-2024; Fraxtal + Sonic out of scope).
7. **scrvUSD = `0x0655977F…`, Yearn-V3 ERC-4626, Ethereum-only** — ✅ confirmed (`aliases.ts` `stcrvUSD`).
8. **Deployed Controller `Liquidate` = 5-arg/1-indexed (not the master 7-arg rewrite)** — ✅ confirmed (keccak + deployed-bytecode scan).
9. **PegKeeper v1 (4) / v2 (5) behind regulator `0x36a04CAf…`** — ✅ confirmed (read live from the regulator).

**Two additive leads (noted, not enumerated):** (a) the **Curve Block Oracle / Blockhash Oracle** — new 2025 cross-chain infrastructure on 20+ Curve chains (storage-proof blockhash distribution; underpins scrvUSD's cross-chain oracle) — a messaging primitive, not a DEX/lending alert target (see §12 item 14); (b) the **RateProvider** at AddressProvider-NG **id 18** (per-chain rate helper, added to the §3 id-map note). A **DAO Treasury** contract also launched June 2025 (governance-side). **Net corrections folded into the body: none beyond the re-evaluation pass above — all nine claims confirmed; the leads are recorded as known, intentionally-out-of-primary-scope components.**

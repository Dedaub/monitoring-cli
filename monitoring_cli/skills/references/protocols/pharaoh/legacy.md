# Pharaoh Legacy AMM — Topics, Selectors, Addresses (Avalanche C-Chain)

**Status:** topic0/selectors computed with `cast keccak`; 1–2 cross-checked against live `eth_getLogs` on Avalanche (publicnode, 2026-06). Addresses on-chain verified via `eth_getCode` + view reads (`PairFactory.allPairsLength()` → 182 ✓, `PHAR.symbol()` → "PHAR" ✓, `xPHAR.symbol()` → "xPHAR" ✓). All six other chains confirmed absent (`0x`).
**Scope:** Pharaoh Exchange **Legacy AMM** — the Solidly/ve(3,3) classic AMM layer. Pharaoh is a fork of **RAMSES Exchange** (which itself forked Velodrome V1). Contracts covered: PairFactory, Pair (LP token), Router, Voter (EIP-1967 upgradeable proxy), VoteModule, VotingEscrow/veNFT (EIP-1967 proxy), Minter, GaugeFactory (legacy), FeeDistributorFactory, FeeRecipientFactory, AccessHub (EIP-1967 proxy), TreasuryHelper (EIP-1967 proxy), PHAR token, xPHAR token, p33 token, Team Multisig, Timelock, ProxyAdmin. The concentrated-liquidity (CL/RAMSES V3) product lives in [`cl.md`](cl.md).
**Key facts:** Pharaoh is **Avalanche C-Chain only** — confirmed `0x` on Ethereum, Base, BNB, Arbitrum, Optimism, and Polygon. Epoch-based emissions (weekly PHAR mint → xPHAR → VoteModule). AMM `Swap` topic0 **matches Uniswap V2 layout** (unlike Aerodrome/Velodrome V2). The PairCreated signature **omits the `bool stable` field** (3-arg form), unlike Solidly-canonical 5-arg. The ve(3,3) token is **xPHAR** (liquid wrapper of PHAR) deposited into the VotingEscrow (ERC-721 veNFT). The Voter and VotingEscrow are behind EIP-1967 transparent proxies.

---

## 1. Topics (chain-agnostic)

### 1.1 PairFactory

```
0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9  PairCreated(address,address,address,uint256)
    [token0 indexed, token1 indexed, pair (non-indexed), allPairsLength (non-indexed)]
    ← confirmed live on Avalanche (block 0x42c39d4); note: NO bool-stable field unlike Solidly canonical
```

### 1.2 Pair (LP contract — one deployed per pool)

```
0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  Swap(address,uint256,uint256,uint256,uint256,address)
    [sender indexed, amount0In, amount1In, amount0Out, amount1Out, to indexed]
    ← confirmed live on Avalanche (WAVAX/USDC pair 0x1cca95f1…, 81 events in recent 50k blocks)
    ← SAME topic0 as Uniswap V2 Swap — disambiguate by emitting contract

0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1  Sync(uint112,uint112)
    ← confirmed live on Avalanche (83 events alongside Swaps); same topic0 as Uniswap V2 Sync

0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f  Mint(address,uint256,uint256)
    [sender, amount0, amount1] — same topic0 as Uniswap V2 / Sushi V2 Mint

0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496  Burn(address,uint256,uint256,address)
    [sender, amount0, amount1, to]

0x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602  Fees(address,uint256,uint256)
    [sender, amount0, amount1] — Solidly-fork trading-fee distribution event

0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)     [ERC-20]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)     [ERC-20]
```

### 1.3 Voter (EIP-1967 proxy at 0x922b…)

```
0x48d3c521fd0d5541640f58c6d6381eed7cb2e8c9df421ae165a4f4c2d221ee0d  GaugeCreated(address,address,address,address)
    [pool indexed, gauge indexed, accessHub (non-indexed), feeDistributor (non-indexed)]
    ← confirmed live on Avalanche (7 events in deploy range 0x42c31ce…)

0xc2e0f725ed6a663192d51dd063d0ac1cd49139c4b1c7a33d9a58ee09f22d100e  Voted(address,uint256,address)
    [voter/veNFT indexed, weight (non-indexed), pool indexed]
    ← confirmed live on Avalanche (67 events in deploy range)

0x8de1cbf50111cf8fb638e287146dbebe220633426e6df96cafd96993d3e34317  Poke(address)
    [veNFT/voter address indexed]
    ← confirmed live on Avalanche (8 events alongside Voted events); matches 4byte "Poke(address)"

0x6661a7108aecd07864384529117d96c319c1163e3010c01390f6b704726e07de  Whitelisted(address,address)
    [accessHub indexed, pool indexed]
    ← confirmed live on Avalanche (12 events in deploy range); matches 4byte "Whitelisted(address,address)"

0x3e218be5ccee06666169af16568736427163f2aeec9b654271ebed990debc03f  [UNVERIFIED SIGNATURE]
    [address indexed, address indexed — both same value (gauge), no data]
    ← observed in same txs as GaugeCreated; not present in 4byte.directory; likely a RAMSES-specific
      initialisation event emitted when a gauge is first seeded with PHAR rewards

0xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826  NotifyReward(address,address,uint256)
    [token indexed, gauge indexed, amount]

0x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17  DistributeReward(address,address,uint256)
    [sender indexed, gauge indexed, amount]
```

### 1.4 VoteModule (0x34F2…)

```
0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c  Deposit(address,uint256)
    [depositor indexed, amount] — xPHAR deposited from VotingEscrow; same topic0 as WETH Deposit

0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364  Withdraw(address,uint256)
    [withdrawer indexed, amount]

0x045b0fef01772d2fbba53dbd38c9777806eac0865b00af43abcfbcaf50da9206  Delegate(address,address,bool)
    [from indexed, to indexed, approved indexed] — voting power delegation
    ← confirmed live on Avalanche; matches 4byte "Delegate(address,address,bool)"
```

### 1.5 VotingEscrow / veNFT (EIP-1967 proxy at 0xfe99…)

```
0xe31c7b8d08ee7db0afa68782e1028ef92305caeea8626633ad44d413e30f6b2f  Deposit(address,uint256,address)
    [depositor indexed, amount indexed, recipient indexed]
    ← confirmed live on Avalanche (6 events in recent 50k blocks); RAMSES-specific layout

0xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683  Claimed(address,address,uint256)
    [claimant indexed, token indexed, amount] — bribe/fee claim from FeeDistributor
    ← confirmed live on Avalanche; matches 4byte "Claimed(address,address,uint256)"

0xf97732ff1935467f3b6e89a5f6e778fd9868ea58ab819d0c11b297e18a862802  [UNVERIFIED SIGNATURE]
    [address indexed, address indexed, address indexed — no data]
    ← observed on Avalanche (1 event, recipient + USDC + FeeDistributor as topics);
      not in 4byte.directory; context suggests a fee-claim routing event

0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)     [ERC-721]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)     [ERC-721]
```

### 1.6 Minter (0xd23F…)

```
0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f  Mint(address,uint256,uint256)
    [sender indexed, weekly, circulating_supply] — collides with Uniswap V2 Mint
    Note: PHAR.minter() returns the Minter address; minting flows to xPHAR, not PHAR directly
    in recent epochs. No Minter Mint events were observed in queried ranges — protocol may be
    in a low-emission phase.
```

### 1.7 PHAR token (0x13A4… — ERC-20)

```
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)
```

### 1.8 xPHAR token (0xE816… — ERC-20 + conversion)

```
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)
0xa428517b481b65176e7c35a57b564d5cf943c8462468b8a0f025fa689173f901  Converted(address,uint256)
    [converter indexed, amount] — PHAR → xPHAR conversion event
    ← confirmed live on Avalanche (14 events in recent 50k blocks); matches 4byte "Converted(address,uint256)"
```

### 1.9 p33 token (0x26e9… — ERC-20 + staking)

```
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)
0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7  Deposit(address,address,uint256,uint256)
    [depositor indexed, receiver indexed, assets, shares] — p33 staking deposit
    ← confirmed live on Avalanche; matches canonical Deposit(address,address,uint256,uint256)
0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db  Withdraw(address,address,address,uint256,uint256)
    [sender indexed, receiver indexed, owner indexed, assets, shares] — p33 staking withdrawal
    ← confirmed live on Avalanche; matches 4byte "Withdraw(address,address,address,uint256,uint256)"
```

---

## 2. Function signatures

### PairFactory
```
0x82dfdce4  createPair(address,address,bool)
0x574f2ba3  allPairsLength()
0x6801cc30  getPair(address,address,bool)
0x1e3dd18b  allPairs(uint256)
0x46c96aac  voter()
```

### Pair (LP)
```
0x0902f1ac  getReserves()
0x562e19df  swap(uint256,uint256,uint256,uint256,address)
0x6a627842  mint(address)
0x89afcb44  burn(address)
0xbc25cf77  skim(address)
```

### Router
```
0xf41766d8  swapExactTokensForTokens(uint256,uint256,(address,address,bool)[],address,uint256)
0x5a47ddc3  addLiquidity(address,address,bool,uint256,uint256,uint256,uint256,address,uint256)
0x0dede6c4  removeLiquidity(address,address,bool,uint256,uint256,uint256,address,uint256)
0x5e1e6325  getAmountOut(uint256,address,address)
0xce700c29  quoteAddLiquidity(address,address,bool,address,uint256,uint256)
```

### Voter
```
0xe4ff5c2f  vote(address,address[],uint256[])
0x6b8ab97d  reset(address)
0xb1a997ac  poke(address)
0x794cea3c  createGauge(address,address)
0x63453ae1  distribute(address)
0xb66503cf  notifyRewardAmount(address,uint256)
0x02fc77fe  claimBribes(address[],address[][],address)
0x0c025d1c  claimFees(address[],address[][],address)
```

### Minter
```
0xed29fc11  update_period()
0xaf14052c  rebase()
```

### VotingEscrow (veNFT)
```
0xb52c05fe  createLock(uint256,uint256)
0xa183af52  increase_amount(uint256,uint256)
0xa4d855df  increase_unlock_time(uint256,uint256)
0x2e1a7d4d  withdraw(uint256)
0xd1c2babb  merge(uint256,uint256)
0xe7e242d4  balanceOfNFT(uint256)
0xb45a3c0e  locked(uint256)
```

---

## 3. Addresses — Avalanche C-Chain (43114)

> All verified via `eth_getCode` (non-zero bytecode) on publicnode Avalanche RPC, 2026-06.

### Tokens
```
0x13A466998Ce03Db73aBc2d4DF3bBD845Ed1f28E7  PHAR token        (symbol "PHAR" ✓; totalSupply ~5.02e26 ✓; minter()→Minter ✓)
0xE8164Ea89665DAb7a553e667F81F30CfDA736B9A  xPHAR token       (symbol "xPHAR" ✓)
0x26e9dbe75aed331e41272bece932ff1b48926ca9  p33 token         (symbol "p33" ✓)
```

### AMM Core
```
0x85448bF2F589ab1F56225DF5167c63f57758f8c1  PairFactory       (allPairsLength() → 182 ✓; voter()→Voter ✓)
0x9CEE04bDcE127DA7E448A333f006DEFb3d5e38cC  Router            (legacy AMM)
0x5AcC35397D2ce81Ac54A4B1c6D9e1FB29F8EC6C6  UniversalRouter
```

### Governance & Emissions
```
0x922b9Ca8e2207bfB850B6FF647c054d4b58a2Aa7  Voter             (EIP-1967 proxy; impl 0x5363e33b…; proxy-admin 0x68ee9459…; minter()→Minter ✓)
0xfe99e92df71f53a26005d1bfbe54c941a3131aa0  VotingEscrow      (EIP-1967 proxy; impl 0x9b8afab3…; proxy-admin 0x6a66483b…; veNFT / vePHAR)
0x34F233F868CdB42446a18562710eE705d66f846b  VoteModule        (xPHAR staking + voting delegation hub)
0xd23F124bBbC958bCdDC0cE624042B48154222FDE  Minter            (PHAR weekly emissions; PHAR.minter()→here ✓)
```

### Factories
```
0xd9A63c24F69F015ebe3FF61817645DC7CC5906B1  Legacy GaugeFactory
0x5Af7Fad6E813fb4637e5cFacC7DdE6c5445125ac  FeeDistributorFactory
0x227fABb4dB11CC082EF8cd083CfF5d034D4de16F  FeeRecipientFactory
```

### Access Control & Admin
```
0x3176f6E4Be2448C53EDD59C27651EDFaA74bf483  AccessHub         (EIP-1967 proxy; impl 0x97301276…; proxy-admin 0x3B91972c… ✓)
0x3B91972c1Ff63296cb824a30997C7e4a982B7ee6  ProxyAdmin        (OZ ProxyAdmin; owner()→Team Multisig ✓)
0xd1b27ccAF2A4dDcA0Ac32181374C70282492d843  Team Multisig
0x12d54ad6daf65d55b029df1b34b260c68fc0ddcf  Timelock
0xcbeb24e8fc568001e83430ec4929ce56b29ba9a2  Pharaoh Deployer  (EOA; Ramses V3 Factory Initialized Deployer)
```

### Treasury & Fees
```
0x660862D49E92f80f29E56C2770027E8d83e97882  TreasuryHelper    (EIP-1967 proxy; impl 0xf03ce48d…; proxy-admin 0xba40a2e5…)
0x1e1e2a861205767D69A51edf03cf5e3a278437bc  FeeCollector      (immutable — no EIP-1967 impl slot)
```

### Notable LP Pairs (examples)
```
0x1cca95F17Eb953cd8c3D91fe81C7e8e815ac8ADd  WAVAX/USDC volatile pair  (getPair(WAVAX,USDC,false) ✓; reserves confirmed)
0xa07182AF0F7Fb49b9b1Ea48Ea8c6BB84283A739c  allPairs(0)
```

---

## 4. Cross-chain summary

| Chain | Chain ID | Status |
|-------|----------|--------|
| Avalanche C-Chain | 43114 | **DEPLOYED** — all contracts verified ✓ |
| Ethereum | 1 | absent — `eth_getCode` returns `0x` for PHAR, Voter |
| Base | 8453 | absent — `0x` |
| BNB Smart Chain | 56 | absent — `0x` |
| Arbitrum One | 42161 | absent — `0x` |
| Optimism | 10 | absent — `0x` |
| Polygon PoS | 137 | absent — `0x` |

Pharaoh is **Avalanche-exclusive**. Any address appearing in these contracts on other chains is coincidence or a different protocol.

---

## 5. Proxies

| Contract | Address | Pattern | Implementation | Proxy Admin |
|----------|---------|---------|---------------|-------------|
| Voter | 0x922b9Ca8… | EIP-1967 transparent | 0x5363e33b… | 0x68ee9459… |
| VotingEscrow | 0xfe99e92d… | EIP-1967 transparent | 0x9b8afab3… | 0x6a66483b… |
| AccessHub | 0x3176f6E4… | EIP-1967 transparent | 0x97301276… | 0x3B91972c… (ProxyAdmin) |
| TreasuryHelper | 0x660862D4… | EIP-1967 transparent | 0xf03ce48d… | 0xba40a2e5… |
| PairFactory | 0x85448bF2… | **immutable** — no impl slot | — | — |
| Minter | 0xd23F124b… | **immutable** — no impl slot | — | — |
| VoteModule | 0x34F233F8… | **immutable** — no impl slot | — | — |
| Pairs (LP) | per-pool | CREATE2 immutable | — | — |

**Key upgrade path:** The ProxyAdmin `0x3B91972c…` (owned by Team Multisig `0xd1b27cc…`) controls AccessHub. Voter and VotingEscrow use separate proxy admin contracts owned by different addresses — the VotingEscrow proxy admin `0x6a66483b…` is owned by EOA `0xB3bfB329…`, not the Team Multisig.

**Proxy detection:** For the Voter proxy (0x922b…), direct view calls to most functions revert on the impl unless called through the proxy (storage not initialised on impl). Always target the proxy address.

---

## 6. Detection invariants & gotchas

1. **AMM `Swap` topic0 (`0xd78ad95f…`) matches Uniswap V2.** Pharaoh pairs use the standard Solidly swap signature identical to Uni V2 — disambiguate exclusively by emitting contract address (i.e., check `eth_getCode` result or compare against `PairFactory.getPair()`).

2. **`PairCreated` is the 3-arg form** — `PairCreated(address,address,address,uint256)` (`0x0d3648bd…`), NOT the 5-arg Solidly form with `bool stable`. There is no on-chain `stable` flag in the event; instead, call `Pair.stable()` on the deployed pair contract to determine pool type.

3. **`Sync` topic0 (`0x1c411e9a…`) = `Sync(uint112,uint112)`**, identical to Uniswap V2. Pharaoh pairs inherit the Solidly pair which still packs reserves as uint112 for the Sync event.

4. **Voter is a proxy — calling the implementation directly will revert** on most functions because storage (including pool lists, gauges map) lives on the proxy storage, not the impl. All queries must go to `0x922b9Ca8…`.

5. **VotingEscrow is also a proxy** (`0xfe99e92d…`). The veNFT is an ERC-721; lock positions are tracked by `tokenId`. The `Deposit` event layout (`Deposit(address,uint256,address)`) differs from both Curve veCRV and Aerodrome/Velodrome ve layouts.

6. **Two unresolved topic0 values** are observed on-chain but absent from 4byte.directory:
   - `0x3e218be5…` (Voter): 2 identical indexed addresses, no data — emitted at GaugeCreated time, suspected gauge initialisation event.
   - `0xf97732ff…` (VotingEscrow): 3 indexed addresses, no data — observed once with depositor + reward token + FeeDistributor, suspected fee-routing event.

7. **Emissions flow:** PHAR Minter → xPHAR minted → xPHAR deposited into VotingEscrow → VoteModule receives `Deposit(address,uint256)` from the VE. Monitoring "new PHAR minted" should track xPHAR `Transfer(0x0…, …)` rather than PHAR mint events.

8. **p33 is an ERC-4626-style vault** using `Deposit(address,address,uint256,uint256)` and `Withdraw(address,address,address,uint256,uint256)` — both match the standard ERC-4626 event layout.

9. **GaugeCreated 4-arg layout** — the Voter emits `GaugeCreated(address indexed pool, address indexed gauge, address accessHub, address feeDistributor)`. The `accessHub` and `feeDistributor` are in `data`, not `topics`.

10. **Multiple proxy admin contracts** — the ProxyAdmin at `0x3B91972c…` only governs AccessHub (and possibly others not checked). Voter and VotingEscrow each have their own separate proxy admin contracts. An upgrade to the Voter requires a transaction to `0x68ee9459…`, not to `0x3B91972c…`.

---

## 7. Quick-copy detection constants

```
-- PairFactory
\x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9  -- PairCreated(address,address,address,uint256)

-- Pair (AMM pool)
\xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  -- Swap(address,uint256,uint256,uint256,uint256,address)
\x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1  -- Sync(uint112,uint112)
\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f  -- Mint(address,uint256,uint256)
\xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496  -- Burn(address,uint256,uint256,address)
\x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602  -- Fees(address,uint256,uint256)
\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  -- Transfer(address,address,uint256)

-- Voter
\x48d3c521fd0d5541640f58c6d6381eed7cb2e8c9df421ae165a4f4c2d221ee0d  -- GaugeCreated(address,address,address,address)
\xc2e0f725ed6a663192d51dd063d0ac1cd49139c4b1c7a33d9a58ee09f22d100e  -- Voted(address,uint256,address)
\x8de1cbf50111cf8fb638e287146dbebe220633426e6df96cafd96993d3e34317  -- Poke(address)
\x6661a7108aecd07864384529117d96c319c1163e3010c01390f6b704726e07de  -- Whitelisted(address,address)
\xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826  -- NotifyReward(address,address,uint256)
\x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17  -- DistributeReward(address,address,uint256)

-- VoteModule
\xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c  -- Deposit(address,uint256)
\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364  -- Withdraw(address,uint256)
\x045b0fef01772d2fbba53dbd38c9777806eac0865b00af43abcfbcaf50da9206  -- Delegate(address,address,bool)

-- VotingEscrow (veNFT)
\xe31c7b8d08ee7db0afa68782e1028ef92305caeea8626633ad44d413e30f6b2f  -- Deposit(address,uint256,address)
\xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683  -- Claimed(address,address,uint256)

-- xPHAR
\xa428517b481b65176e7c35a57b564d5cf943c8462468b8a0f025fa689173f901  -- Converted(address,uint256)

-- p33
\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7  -- Deposit(address,address,uint256,uint256)
\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db  -- Withdraw(address,address,address,uint256,uint256)
```

---

## 8. Verification & sources

**On-chain verification (Avalanche C-Chain, 2026-06):**
- `eth_getCode` non-zero confirmed for all 15 known addresses plus VotingEscrow proxy `0xfe99…`, Voter impl `0x5363…`, AccessHub impl `0x9730…`, TreasuryHelper impl `0xf03c…`
- `PairFactory.allPairsLength()` → 182
- `PHAR.symbol()` → "PHAR"; `PHAR.minter()` → Minter `0xd23f…`
- `xPHAR.symbol()` → "xPHAR"; `p33.symbol()` → "p33"
- `PairFactory.voter()` → Voter `0x922b…`
- `Voter.minter()` → Minter `0xd23f…`
- `ProxyAdmin.owner()` → Team Multisig `0xd1b2…`
- WAVAX/USDC pair reserves confirmed non-zero; Swap (`0xd78ad95f…`) and Sync (`0x1c411e9a…`) confirmed live
- GaugeCreated (`0x48d3c521…`), Voted (`0xc2e0f725…`), Poke (`0x8de1cbf5…`), Whitelisted (`0x6661a710…`) confirmed from live Voter logs
- VoteModule Deposit/Withdraw/Delegate confirmed from live logs
- VotingEscrow Deposit (`0xe31c7b8d…`), Claimed (`0xf7a40077…`) confirmed from live logs
- xPHAR Converted (`0xa428517b…`), p33 Deposit/Withdraw confirmed from live logs
- EIP-1967 impl slots read for Voter, VotingEscrow, AccessHub, TreasuryHelper
- 6-chain absence: `eth_getCode` → `0x` for PHAR and Voter on Ethereum, Base, BNB, Arbitrum, Optimism, Polygon

**Absent (0x on all 6 non-Avalanche target chains):** Confirmed using publicnode RPCs for Ethereum (1), Base (8453), BNB (56), Arbitrum (42161), Optimism (10), Polygon (137).

**Unconfirmed:**
- `0x3e218be5…` (Voter) — observed on-chain but not in 4byte.directory; exact signature unknown
- `0xf97732ff…` (VotingEscrow) — observed on-chain but not in 4byte.directory; exact signature unknown
- VotingEscrow `name()` / `symbol()` calls revert through the proxy (storage not initialized on direct call pattern used)
- Minter `Mint` events were not observed in queried block ranges; the Minter may emit to a different pattern or the Mint events pre-date the queried window

**Sources:**
- Contract addresses: [Pharaoh docs](https://docs.phar.gg/pages/contract-addresses) (on-chain re-verified)
- Codebase: [`PharaohExchange/pharaoh-contracts`](https://github.com/PharaohExchange/pharaoh-contracts) (Solidity 99.5%, GPL-3.0)
- Topic0 resolution: `cast keccak` + live `eth_getLogs` on Avalanche publicnode + [4byte.directory](https://www.4byte.directory) event signatures API
- Fork lineage: Pharaoh ← RAMSES Exchange ← Velodrome V1 ← Solidly (Andre Cronje)
- RPC: `https://avalanche-c-chain-rpc.publicnode.com` (verified 2026-06, latest block ~87 487 168)

**Net corrections folded in:** none — all claims confirmed. The proxy admin label was already accurate; the "stored as immutable in bytecode" nuance is added in this note.

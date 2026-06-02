# DeFi Protocol Integration Patterns

Deep reference for integrating with major EVM DeFi protocols. Covers architecture, key contracts, arithmetic systems, and critical gotchas that cause real bugs.

---

## Fixed-Point Arithmetic Systems

DeFi protocols use various precision systems. Mixing them up causes catastrophic bugs.

| System | Decimals | Used By | Example |
|--------|----------|---------|---------|
| wad | 18 | Maker (token amounts), most ERC-20s | `1e18` = 1.0 |
| ray | 27 | Maker (rate accumulators), Aave (indices) | `1e27` = 1.0 |
| rad | 45 | Maker (internal Vat DAI balance) | `1e45` = 1.0 |
| Q64.96 | 96-bit fractional | Uniswap V3 (sqrtPriceX96) | `sqrt(price) * 2^96` |
| 30-decimal USD | 30 | GMX V2 (sizeDeltaUsd) | `1e30` = $1.00 |
| 36-adjusted | 36 + loanDecimals - collateralDecimals | Morpho Blue (oracle prices) | Varies per market |
| basis points | 4 (as /10000) | Fee rates, slippage | `30` = 0.3% |

### Maker Arithmetic Functions
```solidity
// wad math (18 decimals)
function wmul(uint256 x, uint256 y) internal pure returns (uint256) {
    return (x * y + WAD / 2) / WAD; // WAD = 1e18
}

// ray math (27 decimals)
function rmul(uint256 x, uint256 y) internal pure returns (uint256) {
    return (x * y + RAY / 2) / RAY; // RAY = 1e27
}

// CRITICAL: Maker debt = normalized_debt (art) * accumulated_rate (rate)
// rate is a ray, art is a wad, result is a rad
// debt_rad = art_wad * rate_ray
```

### Uniswap V3 Price Conversion
```
sqrtPriceX96 is NOT a direct price. To get actual price:
price = (sqrtPriceX96 / 2^96)^2
     = sqrtPriceX96^2 / 2^192

Adjust for token decimals:
priceToken0InToken1 = price * 10^(decimals0 - decimals1)
```

---

## Rebasing Tokens

Tokens whose `balanceOf()` changes without transfers. Major source of integration bugs.

### stETH (Lido)
- `balanceOf()` changes every oracle report (~daily) as staking rewards accrue
- Internally tracks **shares**: `balance = shares * totalPooledEther / totalShares`
- **1-2 wei rounding loss per transfer** (shares→balance conversion rounds twice)
- Use `wstETH` for any stored accounting (non-rebasing wrapper)
- `transferShares(recipient, sharesAmount)` for exact share transfers
- Addresses: stETH proxy `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84`, wstETH `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0`

### aTokens (Aave)
- Balance increases every block as interest accrues
- Use `scaledBalanceOf()` for stored accounting (returns underlying shares)
- `liquidityIndex` (ray, 27 decimals) converts scaled↔actual: `actualBalance = scaledBalance * liquidityIndex / 1e27`
- DO NOT use `balanceOf()` for equality checks — it changes between blocks

### Rule: Never store rebasing token balances directly. Always use the underlying shares/scaled representation.

---

## Uniswap

### V2 — Constant Product AMM
```
Pair: holds reserves of token0 + token1
Invariant: reserve0 * reserve1 = k (minus 0.3% fee)
swap(uint amount0Out, uint amount1Out, address to, bytes data)
  - Flash swaps: if data.length > 0, calls to.uniswapV2Call(sender, amount0, amount1, data)

Factory: createPair(tokenA, tokenB) → deterministic CREATE2 address
Router: swapExactTokensForTokens, addLiquidity, removeLiquidity
```

### V3 — Concentrated Liquidity
- LPs provide liquidity within price ranges `[tickLower, tickUpper]`
- Ticks: `price = 1.0001^tick` (each tick = 0.01% price movement)
- Fee tiers: 100 (0.01%), 500 (0.05%), 3000 (0.30%), 10000 (1.00%)
- Tick spacing: 1 (1bp), 10 (5bp), 60 (30bp), 200 (100bp)
- `slot0()` returns: sqrtPriceX96, tick, observationIndex, observationCardinality, observationCardinalityNext, feeProtocol, unlocked
- TWAP oracle: `observe(uint32[] secondsAgos)` returns cumulative tick and liquidity values
- Callback pattern: `uniswapV3SwapCallback(int256 amount0Delta, int256 amount1Delta, bytes data)` — must pay tokens in callback
- Multi-hop path encoding: `abi.encodePacked(tokenIn, fee, tokenMid, fee, tokenOut)`

### V4 — Singleton + Hooks
- **All pools in ONE contract** (PoolManager singleton): `0x000000000004444c5dc75cB358380D2e3dE08A90`
- Hooks: custom logic at pool lifecycle points (beforeSwap, afterSwap, beforeAddLiquidity, etc.)
- Hook address encodes enabled callbacks via flag bits in the address
- Flash accounting: net balance changes settled at end of transaction (no intermediate transfers)
- `PoolKey: {currency0, currency1, fee, tickSpacing, hooks}`
- Permit2: `0x000000000022D473030F116dDEE9F6B43aC78BA3` (gasless approvals via EIP-712 signatures)

### Key Addresses (Ethereum, verified Feb 2026)
| Contract | Address |
|----------|---------|
| SwapRouter02 | `0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45` |
| NonfungiblePositionManager | `0xC36442b4a4522E871399CD717aBDD847Ab11FE88` |
| QuoterV2 | `0x61fFE014bA17989E743c5F6cB21bF9697530B21e` |
| UniversalRouter | `0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD` |
| V4 PoolManager | `0x000000000004444c5dc75cB358380D2e3dE08A90` |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` |

---

## Aave V3

### Architecture
- Pool (lending/borrowing): `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2` (Ethereum)
- PoolAddressesProvider: `0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e`
- Oracle: `0x54586bE62E3c3580375aE3723C145253060Ca0C2`
- Deployed on Arbitrum, Optimism, Polygon, Base with identical interfaces

### Critical Patterns
- Health factor: 18-decimal fixed-point (`1e18` = liquidation threshold)
- Interest rates stored as **rays** (27 decimals) for `liquidityIndex` and `variableBorrowIndex`
- `getUserAccountData()` returns: totalCollateralBase, totalDebtBase, availableBorrowsBase, currentLiquidationThreshold, ltv, healthFactor (all in 8-decimal USD except HF which is 18-dec)
- Flash loan fee: 0.05% (configurable per market)
- Variable rate mode = 2, Stable rate (deprecated) = 1
- E-Mode categories override LTV/liquidation thresholds (ID-based)
- Supply/borrow caps enforced before state changes

### Common Error Codes
| Code | Meaning |
|------|---------|
| 26 | Insufficient collateral |
| 27 | Isolation mode conflict |
| 35 | Health factor below threshold |
| 50 | Supply cap exceeded |
| 51 | Borrow cap exceeded |

---

## Curve

### Critical: No Universal ABI
Each pool type (StableSwap, CryptoSwap, Meta, Factory) has **different function signatures**. You MUST identify the pool type first.

### Pool Types
- **StableSwap**: `exchange(int128 i, int128 j, uint256 dx, uint256 min_dy)` — stable pairs (3pool, stETH/ETH)
- **CryptoSwap**: `exchange(uint256 i, uint256 j, uint256 dx, uint256 min_dy)` — volatile pairs (tricrypto)
- **Meta pools**: `exchange_underlying(int128 i, int128 j, uint256 dx, uint256 min_dy)` — pools paired with base pool LP
- Token indices are pool-specific, NOT sorted — verify with `coins(i)` call

### Key Gotchas
- `get_dy()` returns output **BEFORE** fees
- Fee encoding: value in 1e10 precision (e.g., `4000000` = 0.04%)
- Amplification parameter A controls peg tightness (3pool: A=2000)
- Virtual price only increases monotonically (used for LP valuation)
- Many Curve pools are Vyper contracts — use `viem` or `ethers` with correct ABI

### Key Addresses (Ethereum)
| Pool | Address | Coins |
|------|---------|-------|
| 3pool | `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7` | DAI(0), USDC(1), USDT(2) |
| stETH/ETH | `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` | ETH(0), stETH(1) |
| Tricrypto2 | `0xD51a44d3FaE010294C616388b506AcdA1bfAAE46` | USDT, WBTC, WETH |
| Router | `0xF0d4c12A5768D806021F80a262B4d39d26C58b8D` | — |

---

## Compound V3 (Comet)

### Architecture Changes from V2
- **No cTokens** — direct supply/withdraw/borrow/repay on Comet contract
- Single base asset per market (one-asset borrowing model)
- Interest accrues **per-second** (not per-block like V2)
- Collateral is non-yielding; only base asset earns interest

### Key Patterns
- `balanceOf()` returns base asset balance (zero for pure collateral suppliers)
- Account balance can be **NEGATIVE** (borrowed amounts)
- `borrowBalanceOf()` for outstanding debt
- `collateralBalanceOf(user, asset)` for collateral amounts
- Liquidation is two-step: `absorb()` + `buyCollateral()` (not atomic)
- `getAssetInfo(i)` returns: offset, asset, priceFeed, scale, borrowCollateralFactor, liquidateCollateralFactor, liquidationFactor, supplyCap

### Key Addresses (Ethereum)
| Contract | Address |
|----------|---------|
| Comet USDC | `0xc3d688B66703497DAA19211EEdff47f25384cdc3` |
| COMP Token | `0xc00e94Cb662C3520282E6f5717214004A7f26888` |
| Comet Rewards | `0x1B0e765F6224C21223AeA2af16c1C46E38885a40` |

---

## Maker / Sky (MCD)

### Unit System (CRITICAL — most common source of bugs)
- **wad** = 10^18 (token amounts, normalized debt `art`)
- **ray** = 10^27 (rate accumulators, stability fee rate)
- **rad** = 10^45 (internal Vat DAI balance: `art * rate`)
- DAI has dual representation: internal `rad` in Vat vs external `wad` ERC-20

### MUST-Know Rules
1. **MUST call `jug.drip(ilk)` before calculating accurate debt** — rate accumulator only updates on drip
2. Users interact via DSProxy + DssProxyActions, NOT directly with Vat
3. Vault struct: `ilk` (collateral type like `ETH-A`), `art` (normalized debt), `ink` (locked collateral)
4. Ilk parameters: `Art` (total debt), `rate` (fee accumulator), `spot` (price w/ margin), `line` (debt ceiling), `dust` (min debt)
5. Liquidation 2.0 uses Dutch auctions (Clipper), not English (Flipper)
6. DSR uses Pot contract; Sky system uses sUSDS (ERC-4626 vault)

### Key Addresses (Ethereum)
| Contract | Address |
|----------|---------|
| Vat (core accounting) | `0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B` |
| Jug (stability fees) | `0x19c0976f590D67707E62397C87829d896Dc0f1F1` |
| DAI | `0x6B175474E89094C44Da98b954EedeAC495271d0F` |
| MKR | `0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2` |
| CDP Manager | `0x5ef30b9986345249bc32d8928B7ee64DE9435E39` |

---

## Morpho Blue

### Architecture
- **One singleton contract** holds ALL markets: `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb`
- Market ID = `keccak256(abi.encode(loanToken, collateralToken, oracle, irm, lltv))` — NOT numeric, NOT address
- Markets are immutable post-creation (oracle, IRM, LLTV cannot change)
- Permissionless market creation (no governance gates)

### Critical Patterns
- **Oracle price uses 36-decimal scaling**: `36 + loanTokenDecimals - collateralTokenDecimals`
  - WETH/USDC: `36 + 6 - 18 = 24` decimals
- Shares-based accounting (like ERC-4626) — assets/shares conversions change with interest
- LLTV is liquidation threshold, NOT max borrow amount
- `liquidate()` uses `seizedAssets` OR `repaidShares` (not both)
- Authorization is per-address across ALL markets (not per-market)
- MetaMorpho vaults: separate ERC-4626 wrappers that allocate across markets

---

## GMX V2

### Architecture
- Async 2-step execution: create order → keeper executes (NOT atomic)
- **`multicall` is MANDATORY** for order creation (batch sendWnt + sendTokens + createOrder)
- **`sizeDeltaUsd` uses 30 decimals**: `toUsd30(x) = BigInt(x * 1e6) * 10n**24n`
- Execution fee is ETH (wrapped as WETH), paid upfront to keepers
- GM tokens are NOT fungible across markets (separate ERC-20 per market)
- Chainlink Data Streams pricing (not standard feeds)

### Order Types
| Type | Enum | Description |
|------|------|-------------|
| MarketSwap | 0 | Instant swap |
| LimitSwap | 1 | Limit swap order |
| MarketIncrease | 2 | Open/increase position at market |
| LimitIncrease | 3 | Limit order to open/increase |
| MarketDecrease | 4 | Close/decrease at market |
| LimitDecrease | 5 | Limit order to close/decrease |
| StopLossDecrease | 6 | Stop loss |
| Liquidation | 7 | Forced liquidation |

### Key Addresses (Arbitrum)
| Contract | Address |
|----------|---------|
| ExchangeRouter | `0x69C527fC77291722b52649E45c838e41be8Bf5d5` |
| Router (approvals) | `0x7452c558d45f8afC8c83dAe62C3f8A5BE19c71f6` |
| Reader | `0x22199a49A999c351eF7927602CFB187ec3cae489` |
| DataStore | `0xFD70de6b91282D8017aA4E741e9Ae325CAb992d8` |

---

## Pendle

### Yield Tokenization
- **SY** (StandardizedYield, ERC-5115): wraps all yield-bearing tokens
- **PT** (Principal Token): redeems 1:1 with underlying at maturity
- **YT** (Yield Token): represents yield claim until maturity (time-decaying)
- Invariant: `PT + YT = SY` (before maturity)
- Uses logit curve for PT/SY trading (NOT Uniswap x*y=k)
- Time-decay parameter converges PT price to SY as maturity approaches
- Market state: `totalPt, totalSy, totalLp, scalarRoot, expiry, lnFeeRateRoot, lastLnImpliedRate`
- Implied APY: `e^(lnImpliedRate / 1e18) - 1`

### Key Addresses (Ethereum)
| Contract | Address |
|----------|---------|
| PendleRouter | `0x888888888889758F76e7103c6CbF23ABbF58F946` |
| PendleRouterStatic | `0x263833d47eA3fA4a30d59B2E6C1A0e682eF1C078` |
| PtOracle | `0x66a1096C6366b2529274dF4f5D8f56DA60a2CacD` |

---

## Lido

### stETH Mechanics
- `submit(address _referral)` is **payable** (NOT fallback) — sends ETH, receives stETH
- Share rate: `(totalPooledEther * 1e18) / totalShares`
- wstETH conversion: `getStETHByWstETH()`, `getWstETHByStETH()`
- Withdrawal queue: request (min 100 wei, max 1000 stETH) → finalization → claim
- Chainlink wstETH/ETH feed: `0x536218f9E9Eb48863970252233c8F271f554C2d0` (86400s heartbeat)

### Key Addresses (Ethereum)
| Contract | Address |
|----------|---------|
| stETH proxy | `0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84` |
| wstETH | `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` |
| WithdrawalQueue | `0x889edC2eDab5f40e902b864aD4d7AdE8E412F9B1` |

---

## EigenLayer

### Restaking (NOT liquid staking)
- Stake already-staked assets (LSTs or native ETH) for additional security guarantees
- 7-day withdrawal escrow (`minWithdrawalDelayBlocks`) for slashing finality
- Withdrawals are 2-step: `queueWithdrawals()` → wait → `completeQueuedWithdrawals()`
- Delegation is all-or-nothing per operator (cannot split across multiple)
- Native restaking requires EigenPod (validator withdrawal credentials → EigenPod address)
- Rewards via RewardsCoordinator with Merkle proofs
- **Slashing is live** (since SLASHING upgrade via AllocationManager)

### LST Strategy Addresses (Ethereum)
| Strategy | Address | Token |
|----------|---------|-------|
| stETH | `0x93c4b944D05dfe6df7645A86cd2206016c51564D` | stETH |
| rETH | `0x1BeE69b7dFFfA4E2d53C2a2Df135C388AD25dCD2` | rETH |
| cbETH | `0x54945180dB7943c0ed0FEE7EdaB2Bd24620256bc` | cbETH |

### Core Contracts
| Contract | Address |
|----------|---------|
| StrategyManager | `0x858646372CC42E1A627fcE94aa7A7033e7CF075A` |

---

## ERC-4626 Tokenized Vaults

Used by: Morpho MetaMorpho, Maker sUSDS, Pendle SY, Aave wrapped aTokens, Compound V3 wrappers

### Key Interface
```solidity
function deposit(uint256 assets, address receiver) external returns (uint256 shares);
function withdraw(uint256 assets, address receiver, address owner) external returns (uint256 shares);
function convertToShares(uint256 assets) external view returns (uint256);
function convertToAssets(uint256 shares) external view returns (uint256);
```

### Critical: First-Depositor Inflation Attack
- Attacker deposits 1 wei → donates large amount to vault → next depositor gets 0 shares due to rounding
- Mitigation: OpenZeppelin v4.9+ uses virtual offset (add virtual shares/assets to calculations)
- Alternative: require minimum initial deposit, or use `_decimalsOffset()` override

### Rounding Rules
- `deposit/mint`: round UP shares minted (favor vault)
- `withdraw/redeem`: round DOWN assets returned (favor vault)
- Always favor the vault to prevent value extraction

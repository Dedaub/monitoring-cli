# Oracle Integration Patterns

Reference for integrating price oracles and data feeds across EVM chains. Covers Chainlink, Pyth, and Redstone with staleness checks, decimal handling, and L2-specific requirements.

---

## Oracle Comparison

| Feature | Chainlink | Pyth | Redstone |
|---------|-----------|------|----------|
| Model | Push (on-chain feeds) | Pull (update in calldata) | Push + Pull (calldata or feeds) |
| Latency | ~1 heartbeat (varies) | ~400ms | ~10s |
| Decimals | 8 (usually) | Variable (price * 10^expo) | 8 |
| L2 Support | Yes + sequencer feed | Yes (same feed IDs) | Yes |
| Cost | Free to read | Update fee (~1 wei) | Free (push) / calldata cost (pull) |
| Freshness | On-chain, check staleness | Must update before read | On-chain or in-calldata |

---

## Chainlink

### AggregatorV3Interface
```solidity
interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,      // price in feed's decimals (usually 8)
        uint256 startedAt,
        uint256 updatedAt,  // CRITICAL: check this for staleness
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}
```

### Staleness Check (REQUIRED)
```solidity
(, int256 price, , uint256 updatedAt, ) = feed.latestRoundData();
require(price > 0, "Invalid price");
require(block.timestamp - updatedAt <= HEARTBEAT, "Stale price");
```

### Heartbeat Intervals by Chain
| Chain | ETH/USD Heartbeat | Deviation Threshold |
|-------|-------------------|-------------------|
| Ethereum | 3,600s (1hr) | 0.5% |
| Arbitrum | 86,400s (24hr) | 0.5% |
| Base | 86,400s (24hr) | 0.5% |
| Optimism | 86,400s (24hr) | 0.5% |
| Polygon | 27s | 0.5% |

### L2 Sequencer Uptime Feed (CRITICAL for L2s)

On L2s, the sequencer can go down. During downtime, oracle prices become stale but `updatedAt` still looks recent when the sequencer comes back. **You MUST check the sequencer uptime feed.**

```solidity
// Sequencer uptime feed addresses
// Arbitrum: 0xFdB631F5EE196F0ed6FAa767959853A9F217697D
// Optimism: 0x371EAD81c9102C9BF4874A9075FFFf170F2Ee389
// Base:     0xBCF85224fc0756B9Fa45aA7892530B47e10b6433

(, int256 answer, uint256 startedAt, , ) = sequencerFeed.latestRoundData();
bool sequencerUp = answer == 0;
require(sequencerUp, "Sequencer down");
// Grace period after sequencer restart (prevent stale price usage)
require(block.timestamp - startedAt > GRACE_PERIOD, "Grace period");
```

### Common Feed Addresses (Ethereum)
| Pair | Address | Decimals |
|------|---------|----------|
| ETH/USD | `0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419` | 8 |
| BTC/USD | `0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c` | 8 |
| USDC/USD | `0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6` | 8 |
| DAI/USD | `0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9` | 8 |
| LINK/USD | `0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c` | 8 |
| wstETH/ETH | `0x536218f9E9Eb48863970252233c8F271f554C2d0` | 18 |

### VRF v2.5 (Verifiable Random Function)
- Uses `VRFV2PlusClient` struct (v2 is deprecated)
- Supports native token payment (not just LINK)
- Request: `requestRandomWords(VRFV2PlusClient.RandomWordsRequest)` → callback: `fulfillRandomWords(requestId, randomWords)`

### CCIP (Cross-Chain Interoperability Protocol)
- Router addresses per chain with **chain selectors** (not chain IDs)
- Ethereum selector: `5009297550715157269`
- Arbitrum selector: `4949039107694359620`
- Pattern: `router.ccipSend(destinationChainSelector, message)` with fee payment in LINK or native

### Chainlink Automation (formerly Keepers)
```solidity
interface AutomationCompatibleInterface {
    function checkUpkeep(bytes calldata checkData) external returns (bool upkeepNeeded, bytes memory performData);
    function performUpkeep(bytes calldata performData) external;
}
```

---

## Pyth Network

### Pull-Based Model
Unlike Chainlink (push), Pyth requires updating prices in the same transaction before reading them. This prevents sandwich attacks.

### Integration Pattern
```solidity
// 1. Fetch price update from Hermes API (off-chain)
// GET https://hermes.pyth.network/v2/updates/price/latest?ids[]=0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace

// 2. Submit update + read in same tx
IPyth pyth = IPyth(PYTH_ADDRESS);
pyth.updatePriceFeeds{value: updateFee}(priceUpdateData);
PythStructs.Price memory price = pyth.getPriceNoOlderThan(priceFeedId, maxAge);

// 3. Validate confidence
require(price.conf < uint64(abs(price.price) / 100), "Price confidence too wide");
```

### Price Structure
```solidity
struct Price {
    int64 price;      // price in base units
    uint64 conf;      // confidence interval
    int32 expo;       // exponent (e.g., -8 means price * 10^-8)
    uint256 publishTime;
}
// Actual price = price.price * 10^price.expo
```

### Key Feed IDs (same across ALL chains)
| Asset | Feed ID (bytes32) |
|-------|-------------------|
| ETH/USD | `0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace` |
| BTC/USD | `0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43` |
| USDC/USD | `0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a` |

### Contract Addresses
| Chain | Address |
|-------|---------|
| Ethereum | `0x4305FB66699C3B2702D4d05CF36551390A4c69C6` |
| Arbitrum | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` |
| Base | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` |
| Optimism | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` |
| Polygon | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` |

### Express Relay
- MEV protection for liquidation auctions
- Liquidators bid for priority execution
- Protocol receives MEV value instead of losing it to searchers

---

## Redstone

### Dual Model

**Push Model (Chainlink-compatible):**
- Implements `AggregatorV3Interface` — drop-in Chainlink replacement
- 8 decimal prices
- Push feed addresses (Ethereum ETH/USD): `0xdDb6F90fFb6BFc325bf2AacC7263F67aFDe60483`

**Pull Model (Calldata-embedded):**
```solidity
// Contract inherits RedstoneConsumerBase
contract MyContract is RedstoneConsumerBase {
    function getOracleNumericValueFromTxMsg(bytes32 dataFeedId)
        internal view virtual returns (uint256);

    function doSomething() external {
        uint256 ethPrice = getOracleNumericValueFromTxMsg(bytes32("ETH"));
        // Price extracted from calldata (signed by 3+ data providers)
    }
}
```
- Frontend must wrap transactions with `WrapperBuilder` to inject signed price data into calldata
- Prices use 8 decimals (matches Chainlink convention)
- Compatible with ERC-4337 smart accounts

### RedStone X (Two-Phase Protection)
- Delayed execution to prevent frontrunning
- Phase 1: user submits intent, Phase 2: price injected and executed
- Protects against oracle manipulation attacks

---

## Oracle Best Practices

### 1. Always Check Staleness
```solidity
// Chainlink
require(block.timestamp - updatedAt <= HEARTBEAT, "Stale");

// Pyth
Price memory p = pyth.getPriceNoOlderThan(feedId, MAX_AGE);

// Redstone (push)
require(block.timestamp - updatedAt <= HEARTBEAT, "Stale");
```

### 2. Handle Decimal Normalization
```solidity
// Chainlink: usually 8 decimals, but CHECK with feed.decimals()
// Pyth: variable (use expo field)
// Token amounts: varies (USDC=6, WBTC=8, most=18)

// Normalize to 18 decimals:
uint256 normalizedPrice = uint256(chainlinkAnswer) * 10**(18 - feed.decimals());
```

### 3. L2 Sequencer Check (Mandatory on L2s)
Always check sequencer uptime before using oracle prices on Arbitrum, Optimism, Base.

### 4. Multi-Oracle Strategy
```
Primary: Chainlink (most battle-tested)
Fallback: Pyth or Redstone
Validation: cross-check deviation between sources
If deviation > threshold → pause or use TWAP
```

### 5. TWAP as Fallback
- Uniswap V3 `observe()` provides time-weighted average prices
- More manipulation-resistant than spot prices
- Higher latency than Chainlink/Pyth
- Cannot be used for low-liquidity pairs

### 6. Never Use Spot Prices for Lending/Liquidation
- Flash loans can manipulate spot prices within a single transaction
- Always use time-weighted averages or oracle feeds
- Validate that oracle price hasn't moved more than X% in one block

# Solidity, Vyper & Smart Contract Patterns Reference

## Solidity Compiler & Language

### Pragma & Versions
- `pragma solidity ^0.8.20;` — compiler version constraint
- Key version breakpoints:
  - **0.5.0**: explicit `calldata`/`memory` for external params, `address payable`
  - **0.6.0**: `try/catch`, `abstract`, `virtual/override`, `receive()/fallback()`
  - **0.7.0**: removed `now` (use `block.timestamp`), removed string concat with `+`
  - **0.8.0**: built-in overflow checks, `unchecked{}`, custom errors (0.8.4), user-defined value types (0.8.8)
  - **0.8.20+**: default EVM target = Shanghai (PUSH0 opcode); use `--evm-version paris` for older chain compat
  - **0.8.24+**: transient storage (`tload`/`tstore` in assembly)

### Function Visibility & Mutability
| Visibility | Callable from | ABI exposed |
|---|---|---|
| `external` | Other contracts/EOAs only | Yes |
| `public` | Anywhere (internal + external) | Yes |
| `internal` | Current contract + derived | No |
| `private` | Current contract only | No |

| Mutability | State read | State write | ETH receive |
|---|---|---|---|
| (none) | Yes | Yes | Yes (if payable) |
| `view` | Yes | No | No |
| `pure` | No | No | No |
| `payable` | Yes | Yes | Yes |

### Data Locations
- **`storage`**: persistent, on-chain; assignment to local `storage` var creates a reference (not copy)
- **`memory`**: temporary, within function scope; assignment creates a copy from storage
- **`calldata`**: read-only, function input; cheapest for external function params
- **`stack`**: EVM stack, for local value-type variables

### Error Handling
```solidity
// require — input validation (refunds remaining gas)
require(amount > 0, "Amount must be positive");

// Custom errors (0.8.4+) — cheaper than string messages
error InsufficientBalance(uint256 available, uint256 required);
if (balance < amount) revert InsufficientBalance(balance, amount);

// try/catch — for external calls
try token.transfer(to, amount) returns (bool success) {
    require(success, "Transfer failed");
} catch Error(string memory reason) {
    // Catch require/revert with string
} catch (bytes memory lowLevelData) {
    // Catch everything else
}

// assert — invariant checks (consumes all gas in <0.8, Panic(0x01) in >=0.8)
assert(totalSupply == sumOfBalances);
```

### Assembly (Yul)
```solidity
assembly {
    // Load free memory pointer
    let ptr := mload(0x40)

    // Storage operations
    let val := sload(slot)
    sstore(slot, newVal)

    // Call another contract
    let success := call(gas(), target, value, inputOffset, inputSize, outputOffset, outputSize)

    // Return data
    returndatacopy(ptr, 0, returndatasize())

    // Compute storage slot for mapping
    mstore(0x00, key)
    mstore(0x20, mappingSlot)
    let slot := keccak256(0x00, 0x40)
}
```

---

## Common Contract Patterns

### Ownable
```solidity
address public owner;
modifier onlyOwner() {
    require(msg.sender == owner, "Not owner");
    _;
}
function transferOwnership(address newOwner) external onlyOwner {
    owner = newOwner;
}
// Variant: Ownable2Step requires new owner to accept
```

### ReentrancyGuard
```solidity
uint256 private _status = 1; // NOT_ENTERED
modifier nonReentrant() {
    require(_status != 2, "ReentrancyGuard: reentrant call");
    _status = 2; // ENTERED
    _;
    _status = 1; // NOT_ENTERED
}
// Transient storage variant (0.8.24+): uses tstore/tload, cheaper
```

### Pausable
```solidity
bool public paused;
modifier whenNotPaused() { require(!paused, "Paused"); _; }
modifier whenPaused() { require(paused, "Not paused"); _; }
function pause() external onlyOwner { paused = true; }
function unpause() external onlyOwner { paused = false; }
```

### Proxy Patterns

See `references/proxies.md` for the full catalog (EIP-1167/1822/1967/2535/3448/7702,
beacon, Diamond, Safe, DSProxy, ERC-6900/7579, detection cheatsheet, and how to
resolve the current impl for each pattern). Quick reminder of the four most
common shapes:

**Transparent Proxy**:
```
User → Proxy (fallback → delegatecall → Implementation)
Admin → Proxy (admin functions: upgrade, changeAdmin)
```

**UUPS (Universal Upgradeable Proxy Standard)**:
```
User → Proxy (fallback → delegatecall → Implementation)
Admin → Proxy → Implementation.upgradeTo(newImpl)  // upgrade logic lives in impl
```

**Beacon Proxy**:
```
User → Proxy (reads impl from Beacon) → delegatecall → Implementation
Admin → Beacon.upgrade(newImpl)  // all proxies update at once
```

**Minimal Proxy (EIP-1167 Clone)**:
```
45-byte contract that delegatecalls to a fixed implementation
Bytecode: 363d3d373d3d3d363d73<impl-addr>5af43d82803e903d91602b57fd5bf3
```

### Access Control (OpenZeppelin)
```solidity
// Role-based
bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
mapping(bytes32 => mapping(address => bool)) private _roles;

function hasRole(bytes32 role, address account) public view returns (bool);
function grantRole(bytes32 role, address account) external onlyRole(DEFAULT_ADMIN_ROLE);
function revokeRole(bytes32 role, address account) external onlyRole(DEFAULT_ADMIN_ROLE);
```

---

## Token Implementation Patterns

### ERC-20 Core
```solidity
mapping(address => uint256) private _balances;
mapping(address => mapping(address => uint256)) private _allowances;
uint256 private _totalSupply;

function transfer(address to, uint256 amount) external returns (bool) {
    _balances[msg.sender] -= amount;
    _balances[to] += amount;
    emit Transfer(msg.sender, to, amount);
    return true;
}
```

### Fee-on-Transfer (Tax) Tokens
```solidity
function _transfer(address from, address to, uint256 amount) internal {
    uint256 fee = amount * taxRate / 10000;
    uint256 netAmount = amount - fee;
    _balances[from] -= amount;
    _balances[to] += netAmount;
    _balances[feeRecipient] += fee;
    emit Transfer(from, to, netAmount);
}
// Red flags: different buy/sell tax, high max tax, mutable tax rates
```

### Honeypot Patterns
- **Blacklist**: `require(!blacklisted[from] && !blacklisted[to])` in transfer
- **Max transaction**: `require(amount <= maxTxAmount)` — can be set to 0 to block sells
- **Trading enabled flag**: `require(tradingEnabled)` — owner can disable
- **Approve manipulation**: custom approve that doesn't actually set allowance
- **Balance manipulation**: `balanceOf()` returns fake value, actual balance is different
- **External call in transfer**: calls external contract that can revert conditionally

### Reflection Tokens
- Total supply split into `rSupply` (reflected) and `tSupply` (actual)
- `balanceOf` computed dynamically: `rOwned[account] / rate`
- Transfer reduces `rTotal` proportionally → all holders' balances increase
- Complex accounting makes tax calculation non-trivial

---

## DeFi Protocol Patterns

### Uniswap V2
```
Pair contract: holds reserves of token0 + token1
swap(uint amount0Out, uint amount1Out, address to, bytes calldata data)
  - Constant product: (reserve0 * reserve1) = k (minus 0.3% fee)
  - Flash swaps: if data.length > 0, calls to.uniswapV2Call(sender, amount0, amount1, data)

Factory: createPair(tokenA, tokenB) → deterministic CREATE2 address
Router: swapExactTokensForTokens, addLiquidity, removeLiquidity
```

### Uniswap V3
```
Concentrated liquidity: LPs provide liquidity within price ranges [tickLower, tickUpper]
Ticks: price = 1.0001^tick (each tick = 0.01% price movement)
sqrtPriceX96: sqrt(price) * 2^96 (fixed-point representation)
swap(recipient, zeroForOne, amountSpecified, sqrtPriceLimitX96, data)
  - zeroForOne: true = sell token0 for token1
  - Crosses ticks as price moves
  - Callback: uniswapV3SwapCallback(amount0Delta, amount1Delta, data)
```

### Uniswap V4
```
Singleton contract: all pools in one contract (no per-pair deployments)
Hooks: custom logic at pool lifecycle points (beforeSwap, afterSwap, etc.)
Flash accounting: net balance changes settled at end of transaction
PoolKey: {currency0, currency1, fee, tickSpacing, hooks}
```

### Common DeFi Integrations
- **Flash loans** (Aave/dYdX): borrow → use → repay + fee in single tx
- **Oracles**: Chainlink (latestRoundData), Uniswap TWAP (observe), Band Protocol
- **Lending**: deposit collateral → borrow → liquidation if health factor < 1
- **Yield farming**: stake LP tokens → earn reward tokens → compound

---

## Vyper Quick Reference

### Contract Structure
```vyper
# @version ^0.3.10

# State variables
owner: public(address)
balances: HashMap[address, uint256]
totalSupply: public(uint256)

# Events
event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    amount: uint256

# Constructor
@deploy
def __init__(_supply: uint256):
    self.owner = msg.sender
    self.totalSupply = _supply
    self.balances[msg.sender] = _supply

# External function
@external
def transfer(to: address, amount: uint256) -> bool:
    assert self.balances[msg.sender] >= amount, "Insufficient balance"
    self.balances[msg.sender] -= amount
    self.balances[to] += amount
    log Transfer(msg.sender, to, amount)
    return True

# View function
@external
@view
def balanceOf(account: address) -> uint256:
    return self.balances[account]
```

### Key Vyper Differences from Solidity
| Feature | Solidity | Vyper |
|---|---|---|
| Overflow protection | Built-in (0.8+) | Always built-in |
| Inheritance | Multiple (C3 linearization) | None (by design) |
| Inline assembly | `assembly { ... }` | Not allowed |
| Modifiers | `modifier onlyOwner` | Not supported; use internal functions |
| Reentrancy guard | Manual / OZ library | `@nonreentrant("lock")` decorator |
| String concat | `string.concat(a, b)` | `concat(a, b)` built-in |
| Max values | `type(uint256).max` | `max_value(uint256)` |
| Logging | `emit Event(...)` | `log Event(...)` |
| Constructor | `constructor()` | `@deploy def __init__()` |

---

## Bytecode Analysis

### Identifying Contract Type from Bytecode
- **Proxy (EIP-1167)**: starts with `363d3d373d3d3d363d73` → clone
- **Proxy (transparent/UUPS)**: has DELEGATECALL, reads from EIP-1967 slot
- **ERC-20**: has selectors `0x70a08231`, `0xa9059cbb`, `0x095ea7b3`, `0x18160ddd`
- **ERC-721**: has `0x6352211e` (ownerOf), `0x42842e0e` (safeTransferFrom), supports ERC-165
- **Vyper contract**: starts with different preamble, no PUSH0 until recent versions
- **Unverified**: no source available, use decompilers (Dedaub, Panoramix, Heimdall)

### Function Selector Dispatch
Most Solidity compilers emit a dispatcher at the start of runtime bytecode:
```
CALLDATALOAD(0) → SHR(224) → selector
If selector == 0xa9059cbb → JUMP to transfer implementation
If selector == 0x70a08231 → JUMP to balanceOf implementation
...
Else → JUMP to fallback/receive or REVERT
```

### Constructor vs Runtime Bytecode
- **Init code** (constructor): runs once during deployment, returns runtime code
- **Runtime code**: stored on-chain, executed on every call
- Constructor args are ABI-encoded at the end of the deploy transaction's data
- `CODECOPY` + `RETURN` in init code copies runtime portion and returns it

---

## OpenZeppelin v5 Breaking Changes

| v4 | v5 | Impact |
|----|-----|--------|
| `Ownable()` auto-sets msg.sender | `Ownable(initialOwner)` requires arg | Constructor change |
| `_setupRole()` | Removed — use `_grantRole()` | Access control |
| `_beforeTokenTransfer` / `_afterTokenTransfer` hooks | `_update()` single hook | Token customization |
| `uint256[50] __gap` arrays | ERC-7201 namespaced storage | Upgradeable storage |
| Per-contract role management | `AccessManager` centralized hub | Architecture |
| `SafeERC20.safeApprove()` | `forceApprove()` (renamed) | API change |

### ERC-7201 Namespaced Storage
```solidity
// Replaces __gap arrays for upgradeable contracts
/// @custom:storage-location erc7201:myprotocol.storage.main
struct MainStorage {
    uint256 value;
    mapping(address => uint256) balances;
}

bytes32 private constant MAIN_STORAGE_LOCATION =
    keccak256(abi.encode(uint256(keccak256("myprotocol.storage.main")) - 1)) & ~bytes32(uint256(0xff));

function _getMainStorage() private pure returns (MainStorage storage $) {
    assembly { $.slot := MAIN_STORAGE_LOCATION }
}
```

---

## Advanced DeFi Patterns

### Shares-Based Accounting (ERC-4626)
Used by: Morpho, Aave (scaled balances), Compound V3, Pendle SY, Maker sUSDS
```solidity
// Deposit: assets → shares (round DOWN to favor vault)
shares = assets * totalShares / totalAssets;

// Withdraw: shares → assets (round DOWN to favor vault)
assets = shares * totalAssets / totalShares;

// CRITICAL: First-depositor inflation attack
// Attacker: deposit 1 wei → donate large amount → next depositor gets 0 shares
// Mitigation: virtual offset (OZ v4.9+), or minimum initial deposit
```

### Rebasing Token Patterns
```solidity
// stETH: balance = shares * totalPooledEther / totalShares
// Problem: 1-2 wei rounding loss per transfer
// Solution: Use wstETH for stored accounting

// aToken: balance changes every block (interest accrual)
// Problem: balanceOf() is non-deterministic between blocks
// Solution: Use scaledBalanceOf() for stored accounting
```

### Flash Loan Pattern (ERC-3156)
```solidity
interface IERC3156FlashBorrower {
    function onFlashLoan(
        address initiator,
        address token,
        uint256 amount,
        uint256 fee,
        bytes calldata data
    ) external returns (bytes32);
}
// Return value MUST be keccak256("ERC3156FlashBorrower.onFlashLoan")
// Aave: 0.05% fee, Uniswap V3: 0.01% fee (flash swaps)
```

### Commit-Reveal Pattern
```solidity
// Phase 1: Commit (hide action)
bytes32 commitment = keccak256(abi.encodePacked(value, salt, msg.sender));
commitments[msg.sender] = commitment;

// Phase 2: Reveal (after delay)
require(block.timestamp >= commitTime + MIN_DELAY, "Too early");
require(keccak256(abi.encodePacked(value, salt, msg.sender)) == commitments[msg.sender], "Invalid");
// Execute action
```

### Merkle Proof Validation (Allowlists)
```solidity
function claim(bytes32[] calldata proof, uint256 amount) external {
    bytes32 leaf = keccak256(abi.encodePacked(msg.sender, amount));
    require(MerkleProof.verify(proof, merkleRoot, leaf), "Invalid proof");
    // Process claim
}
```

---

## Non-Standard Token Behaviors

| Token | Quirk | Mitigation |
|-------|-------|------------|
| USDT | `approve()` requires setting to 0 first | Use `SafeERC20.forceApprove()` |
| USDT | `transfer()` doesn't return bool | Use `SafeERC20.safeTransfer()` |
| BNB (ERC-20) | `transfer()` edge cases | Use SafeERC20 |
| Fee-on-transfer tokens | Received amount < sent amount | Check balance before/after |
| Rebasing tokens (stETH) | Balance changes without transfer | Use wrapped version |
| Double-entry tokens (TUSD) | Two addresses, same balance | Check both addresses |
| Upgradeable tokens | Behavior can change post-deployment | Monitor for upgrades |
| Pausable tokens | Transfers can be blocked | Handle revert gracefully |

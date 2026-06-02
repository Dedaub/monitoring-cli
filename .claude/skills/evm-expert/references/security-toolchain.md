# Security Analysis Toolchain

Layered security analysis workflow for EVM smart contracts. From fast static analysis to formal verification, covering tools, invariant design patterns, and a recommended audit pipeline.

---

## Analysis Workflow (Fast → Deep)

```
1. Code-Recon    → Understand architecture, trust boundaries, entry points
2. Slither       → Fast static analysis (seconds, 95+ detectors)
3. Semgrep       → Custom pattern + taint tracking rules
4. Echidna       → Property-based fuzzing (multi-tx sequences)
5. Halmos        → Local symbolic verification (bounded)
6. Mythril       → Symbolic execution (state-dependent, multi-tx)
7. Certora       → Formal verification (unbounded proofs)
8. VulnHunter    → Variant analysis (scale discovered bugs)
9. Solidity-Auditor → Orchestrated multi-agent report
```

---

## 1. Slither — Static Analysis

**What:** Pattern-based vulnerability detection with 95+ built-in detectors.
**Speed:** Seconds. Run on every PR.

### Key Commands
```bash
# Basic run
slither . --foundry-out-directory out

# Filter by severity
slither . --detect reentrancy-eth,arbitrary-send-erc20,controlled-delegatecall

# Print storage layout
slither . --print storage-layout

# Print call graph
slither . --print call-graph

# Exclude test files
slither . --filter-paths "test/|script/|lib/"

# SARIF output for GitHub Code Scanning
slither . --sarif output.sarif
```

### High-Impact Detectors
| Detector | Impact | What It Finds |
|----------|--------|--------------|
| `reentrancy-eth` | High | CEI violation with ETH transfer |
| `reentrancy-no-eth` | Medium | CEI violation without ETH |
| `arbitrary-send-erc20` | High | Uncontrolled token transfer |
| `controlled-delegatecall` | High | User-controlled delegatecall target |
| `suicidal` | High | Unprotected selfdestruct |
| `unprotected-upgrade` | High | Missing access control on upgrade |
| `unchecked-transfer` | Medium | ERC-20 transfer return not checked |
| `weak-prng` | High | Block-based randomness |
| `msg-value-loop` | High | msg.value reuse in loop |
| `domain-separator-collision` | Medium | EIP-712 domain separator conflicts |
| `shadowing-state` | High | Child overrides parent state variable |

### Triage Tips
- Filter false positives with `--exclude-informational --exclude-low`
- Use `// slither-disable-next-line detector-name` for known-safe patterns
- Run printers (`--print human-summary`) before detectors for context

---

## 2. Semgrep — Custom Pattern + Taint Tracking

**What:** YAML-based AST pattern matching with taint analysis.
**Speed:** Seconds. Good for org-wide custom rules.

### Setup
```bash
# Community rules (best starting point)
semgrep --config "p/smart-contracts"

# Decurity ruleset (Solidity-specific)
semgrep --config "https://semgrep.dev/p/decurity-audit"

# Custom rules
semgrep --config ./semgrep-rules/
```

### Custom Rule Example (CEI Violation)
```yaml
rules:
  - id: state-change-after-external-call
    patterns:
      - pattern: |
          $ADDR.call{...}(...);
          ...
          $STATE_VAR = ...;
    message: "State change after external call (reentrancy risk)"
    severity: ERROR
    languages: [solidity]
```

### Taint Tracking Example
```yaml
rules:
  - id: user-input-to-delegatecall
    mode: taint
    pattern-sources:
      - pattern: function $F(..., address $ADDR, ...) external { ... }
    pattern-sinks:
      - pattern: $TARGET.delegatecall(...)
    pattern-sanitizers:
      - pattern: require($ADDR == $TRUSTED, ...)
    message: "User-controlled address reaches delegatecall"
    severity: ERROR
    languages: [solidity]
```

---

## 3. Echidna — Property-Based Fuzzing

**What:** Coverage-guided fuzzer generating multi-transaction sequences.
**Speed:** Minutes to hours. Best for invariant testing.

### Testing Modes
- **Property mode:** Functions prefixed `echidna_` must return true
- **Assertion mode:** Uses Solidity `assert()` statements
- **Optimization mode:** Finds inputs that maximize/minimize a value

### DeFi Invariant Templates

**Conservation (ERC-20):**
```solidity
function echidna_supply_bounded() public view returns (bool) {
    return token.totalSupply() <= INITIAL_SUPPLY;
}

function echidna_no_token_creation() public view returns (bool) {
    return token.totalSupply() == sumOfAllBalances();
}
```

**Solvency (Vault/Lending):**
```solidity
function echidna_solvency() public view returns (bool) {
    return vault.totalAssets() >= vault.totalDebt();
}

function echidna_share_price_monotonic() public view returns (bool) {
    uint256 currentPrice = vault.convertToAssets(1e18);
    return currentPrice >= lastSharePrice;
}
```

**Access Control:**
```solidity
function echidna_roles_monotonic() public view returns (bool) {
    // Roles should never be silently revoked
    return !hadRole || contract.hasRole(ROLE, account);
}
```

### Configuration
```yaml
# echidna.yaml
testMode: "property"
testLimit: 50000
seqLen: 100          # max transaction sequence length
shrinkLimit: 5000    # shrinking iterations
sender: ["0x10000", "0x20000", "0x30000"]  # fuzzer addresses
deployer: "0x30000"
balanceAddr: 0xffffffff
balanceContract: 0xffffffff
```

### Key Feature: Corpus Shrinking
Echidna reduces a 50-transaction failing sequence to minimal 2-3 call reproducer. Save corpus for regression testing.

---

## 4. Halmos — Bounded Model Checking

**What:** Symbolic testing using Z3 solver. Foundry-native (`check_` prefix).
**Speed:** Minutes. Completely local, no API key needed.

### Usage
```bash
# Run all symbolic tests
halmos --contract MyTest

# With specific loop bound
halmos --contract MyTest --loop 5

# With solver timeout
halmos --contract MyTest --solver-timeout-branching 10000
```

### Writing Symbolic Tests
```solidity
function check_transferConservation(address from, address to, uint256 amount) public {
    // Setup: constrain inputs
    vm.assume(from != to);
    vm.assume(from != address(0) && to != address(0));
    vm.assume(amount <= token.balanceOf(from));

    uint256 totalBefore = token.balanceOf(from) + token.balanceOf(to);

    vm.prank(from);
    token.transfer(to, amount);

    uint256 totalAfter = token.balanceOf(from) + token.balanceOf(to);

    // Use raw assert, not assertEq (reverts are acceptable paths)
    assert(totalBefore == totalAfter);
}
```

### Key Differences from Foundry Fuzz
- Explores ALL paths (up to bound), not random samples
- Uses `assert()` not `assertEq()` — reverts are acceptable paths
- `vm.assume()` prunes search space
- `svm.createUint256()` for symbolic storage values
- Path count in output shows if assumptions are vacuous (0 paths = vacuous)

---

## 5. Mythril — Symbolic Execution

**What:** State-dependent vulnerability detection via Z3 SMT solver on bytecode.
**Speed:** Minutes to hours. Best for multi-transaction exploits.

### Key Commands
```bash
# Analyze source
myth analyze contracts/Token.sol --solc-json config.json

# Analyze deployed contract (pulls bytecode)
myth analyze --address 0x... --rpc infura-url

# Control depth
myth analyze contracts/Token.sol -t 3   # 3 transaction depth

# Specific modules
myth analyze contracts/Token.sol --modules ether_thief,suicide,reentrancy
```

### SWC Mappings
| Module | SWC | Vulnerability |
|--------|-----|--------------|
| `ether_thief` | SWC-105 | Unauthorized ETH withdrawal |
| `suicide` | SWC-106 | Unprotected selfdestruct |
| `delegatecall` | SWC-112 | Delegatecall to untrusted |
| `reentrancy` | SWC-107 | Reentrancy |
| `integer` | SWC-101 | Integer overflow/underflow |
| `unchecked_retval` | SWC-104 | Unchecked return values |
| `tx_origin` | SWC-115 | tx.origin authentication |
| `assertions` | SWC-110 | Reachable assert violations |

### Strength: Counter-Example Generation
Mythril produces concrete transaction sequences proving a vulnerability. Example output:
```
Reentrancy detected:
  TX 1: attacker.deposit{value: 1 ether}()
  TX 2: attacker.withdraw(1 ether) → re-enters via fallback
```

---

## 6. Certora — Formal Verification

**What:** Unbounded mathematical proofs using CVL (Certora Verification Language).
**Speed:** Minutes to hours. Requires cloud API (paid). Most thorough.

### CVL Basics
```cvl
// Rule: transfer preserves total supply
rule transferPreservesTotalSupply(address from, address to, uint256 amount) {
    uint256 supplyBefore = totalSupply();

    env e;
    transfer(e, to, amount);

    assert totalSupply() == supplyBefore;
}

// Invariant with ghost variable
ghost mathint sumOfBalances {
    init_state axiom sumOfBalances == 0;
}

hook Sstore balances[KEY address a] uint256 newBalance (uint256 oldBalance) {
    sumOfBalances = sumOfBalances + newBalance - oldBalance;
}

invariant totalSupplyIsSumOfBalances()
    to_mathint(totalSupply()) == sumOfBalances;
```

### Key CVL Patterns
- **Ghost variables:** Track derived state (sum of balances, call counts)
- **Hooks:** Update ghosts on storage writes
- **Parametric rules:** `rule noRevertExcept(method f)` — quantify over ALL functions
- **`@withrevert`:** Check that specific conditions cause reverts
- **`mathint`:** Unbounded integer (spec-side only, no overflow)
- **Dispatchers:** Handle dynamic dispatch to unknown external contracts

### What It Proves That Others Can't
- `totalSupply() == sum(balances[])` for ANY number of transactions
- Solvency: collateral always covers borrows across arbitrary sequences
- Access control monotonicity: roles never silently revoked
- Round-trip: deposit then withdraw ≥ original amount

---

## Common Vulnerability Patterns & Detection

| Vulnerability | Slither | Echidna | Halmos | Mythril | Certora |
|--------------|---------|---------|--------|---------|---------|
| Reentrancy | `reentrancy-eth` | CEI invariant | - | `reentrancy` | Parametric rule |
| Integer overflow | `unchecked-*` | Assertion | Symbolic check | `integer` | mathint proof |
| Access control | `unprotected-upgrade` | Role invariant | - | - | Permission ghost |
| Oracle manipulation | - | Price bound invariant | - | - | TWAP proof |
| First-depositor attack | - | Share price invariant | Symbolic | - | Rounding proof |
| Flash loan exploit | - | Conservation invariant | - | `ether_thief` | Solvency invariant |
| Storage collision | `storage-layout` | - | - | - | Ghost + hook |
| Signature replay | - | Nonce invariant | Symbolic | - | Replay rule |

---

## Pre-Audit Reconnaissance (code-recon)

Before running any tools, build architectural understanding:

### 1. Entry Point Mapping
- All `external` and `public` functions
- Fallback/receive handlers
- Callback functions (flash loan, swap callbacks)
- Admin/governance functions

### 2. Trust Boundary Identification
- Which addresses can call what (roles, owners, governance)
- External protocol dependencies (oracles, DEXes, bridges)
- Upgradeable components (proxy patterns, implementation slots)
- Token interactions (approve, transfer, permit)

### 3. Data Flow Tracing
- Token flow: where do tokens enter, move, and exit?
- State mutations: which storage slots change and when?
- External calls: who calls whom with what data?

### 4. Critical Function Categories
- **Value transfer:** withdraw, swap, liquidate, bridge
- **Access control:** grantRole, transferOwnership, upgrade
- **State transitions:** pause, unpause, migrate, emergency
- **Oracle-dependent:** price reads, liquidation triggers

---

## Defense Patterns Quick Reference

### Checks-Effects-Interactions (CEI)
```solidity
// WRONG
function withdraw(uint256 amount) external {
    (bool ok, ) = msg.sender.call{value: amount}("");  // interaction FIRST
    balances[msg.sender] -= amount;  // effect AFTER
}

// CORRECT
function withdraw(uint256 amount) external nonReentrant {
    balances[msg.sender] -= amount;  // effect FIRST
    (bool ok, ) = msg.sender.call{value: amount}("");  // interaction AFTER
    require(ok, "Transfer failed");
}
```

### SafeERC20 (USDT Quirks)
```solidity
// USDT approve() requires setting to 0 first
// SafeERC20 handles this + tokens that don't return bool
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
using SafeERC20 for IERC20;
token.safeTransfer(to, amount);
token.safeApprove(spender, amount);  // handles USDT
```

### EIP-712 Signature Replay Prevention
```solidity
// MUST include: chain ID, contract address, nonce, deadline
bytes32 DOMAIN_SEPARATOR = keccak256(abi.encode(
    keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
    keccak256("MyProtocol"),
    keccak256("1"),
    block.chainid,
    address(this)
));
// Increment nonce per signer after each use
// Check deadline: require(block.timestamp <= deadline)
```

### Proxy Storage Safety
```solidity
// OpenZeppelin v5: ERC-7201 namespaced storage (replaces __gap arrays)
// Storage location = keccak256(abi.encode(uint256(keccak256("myprotocol.storage.main")) - 1)) & ~bytes32(uint256(0xff))
// NEVER reorder or remove storage variables in upgradeable contracts
// ALWAYS add new variables at the END
```

### MEV Protection
- Set slippage limits (never 100% slippage)
- Include deadline parameter: `require(block.timestamp <= deadline)`
- Use Flashbots Protect RPC for private transactions
- Consider commit-reveal for high-value operations

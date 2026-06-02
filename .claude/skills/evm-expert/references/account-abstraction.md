# Account Abstraction & Smart Accounts

Reference for ERC-4337, EIP-7702, Safe multisig, and smart account patterns on EVM chains.

---

## ERC-4337 Account Abstraction

### Architecture
```
User → Bundler (off-chain) → EntryPoint (on-chain) → Smart Account → Target Contract
                                    ↓
                              Paymaster (optional, sponsors gas)
```

### EntryPoint v0.7 (ALL EVM chains)
`0x0000000071727De22E5E9d8BAf0edAc6f37da032`

### UserOperation Structure (v0.7)
```solidity
struct PackedUserOperation {
    address sender;              // smart account address
    uint256 nonce;               // 2D: upper 192 bits = key, lower 64 = sequence
    bytes initCode;              // factory + createAccount calldata (empty if account exists)
    bytes callData;              // actual operation to execute
    bytes32 accountGasLimits;    // packed: verificationGasLimit (16 bytes) + callGasLimit (16 bytes)
    uint256 preVerificationGas;  // overhead gas
    bytes32 gasFees;             // packed: maxPriorityFeePerGas (16 bytes) + maxFeePerGas (16 bytes)
    bytes paymasterAndData;      // paymaster address + verification/postOp gas + paymaster data
    bytes signature;             // validation signature
}
```

### 2D Nonces
- Upper 192 bits = **key** (allows parallel execution lanes)
- Lower 64 bits = **sequence** (must be sequential within each key)
- Key 0 is the default sequential nonce
- Different keys enable parallel UserOps without nonce conflicts

### Bundler RPC Methods
| Method | Purpose |
|--------|---------|
| `eth_sendUserOperation` | Submit UserOp to bundler mempool |
| `eth_estimateUserOperationGas` | Estimate gas for UserOp |
| `eth_getUserOperationByHash` | Get UserOp by hash |
| `eth_getUserOperationReceipt` | Get receipt after inclusion |
| `eth_supportedEntryPoints` | List supported EntryPoints |

### Paymaster Patterns

**Verifying Paymaster (signature-based):**
```solidity
// Off-chain: backend signs approval for specific UserOps
// On-chain: paymaster verifies signature in validatePaymasterUserOp
function _validatePaymasterUserOp(PackedUserOperation calldata userOp, bytes32 userOpHash, uint256 maxCost)
    internal override returns (bytes memory context, uint256 validationData)
{
    // Verify backend signature over (userOpHash, validUntil, validAfter)
    // Return context for postOp accounting
}
```

**ERC-20 Paymaster (token payment):**
```solidity
// User pays gas in ERC-20 tokens instead of ETH
// Paymaster: reads token price, transfers tokens from user, pays ETH to EntryPoint
// Requires user to approve paymaster for the ERC-20 token
```

**Sponsoring Paymaster (free gas):**
```solidity
// Protocol deposits ETH into EntryPoint
// Paymaster sponsors all UserOps matching criteria (whitelist, rate limit)
// Used for onboarding (first N transactions free)
```

---

## EIP-7702 — EOA Code Delegation

### What It Does
Allows EOAs to temporarily delegate to a smart contract implementation. The EOA gets smart account capabilities (batching, session keys) while remaining an EOA.

### Transaction Format
```
Type 0x04 transaction with authorization list:
{
    chainId,
    address,      // implementation contract to delegate to
    nonce,        // EOA nonce at time of signing
    v, r, s       // EOA signature
}
```

### Key Properties
- EOA's code is set to a delegation designator: `0xef0100 ++ address`
- Calls to the EOA execute the delegated code in the EOA's context
- Authorization can be revoked by sending another 7702 tx with `address(0)`
- Multiple authorizations can be batched in one transaction
- **Nonce check prevents replay** — authorization is bound to specific nonce

### Monad-Specific 7702 Restrictions
- Minimum 10 MON balance required
- CREATE/CREATE2 banned for delegated EOAs
- Gas limit charging still applies

---

## Safe (Gnosis Safe)

### Architecture
- **Singleton** (implementation): `0x41675C099F32341bf84BFc5382aF534df5C7461a` (v1.4.1, all chains)
- **ProxyFactory**: `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67`
- Each Safe is a proxy pointing to the singleton
- Deterministic address across chains (same salt → same address)

### Key Features
- **Threshold-based multisig**: M-of-N owners must sign
- **Modules**: bypass threshold, add custom logic (spending limits, recovery)
- **Guards**: pre/post-execution hooks (transaction validation)
- **Delegates**: non-owner addresses that can propose transactions
- **EIP-1271**: `isValidSignature(bytes32, bytes)` for smart contract signature verification

### Transaction Service API
```
Ethereum:  https://safe-transaction-mainnet.safe.global
Arbitrum:  https://safe-transaction-arbitrum.safe.global
Base:      https://safe-transaction-base.safe.global
Optimism:  https://safe-transaction-optimism.safe.global
Polygon:   https://safe-transaction-polygon.safe.global
Avalanche: https://safe-transaction-avalanche.safe.global
BSC:       https://safe-transaction-bsc.safe.global
```

### ERC-7579 Module Standard
| Module Type | Purpose |
|-------------|---------|
| Validator | Custom signature validation (passkeys, social recovery) |
| Executor | Execute transactions (automation, scheduled ops) |
| Hook | Pre/post execution checks (spending limits, allowlists) |
| Fallback | Handle unknown function calls |

---

## OpenZeppelin Smart Account Patterns

### Ownable (v5 Breaking Change)
```solidity
// v4: constructor sets msg.sender as owner automatically
// v5: MUST pass initial owner to constructor
constructor(address initialOwner) Ownable(initialOwner) {}
```

### AccessControl
```solidity
bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
// grantRole(role, account) — requires DEFAULT_ADMIN_ROLE
// revokeRole(role, account) — requires DEFAULT_ADMIN_ROLE
// renounceRole(role, account) — only for self
```

### AccessManager (New in v5)
- Centralized permission hub (replaces per-contract role management)
- Time-delayed operations for sensitive functions
- Role → function mapping across multiple contracts
- Single point of administration for entire protocol

### ERC-7201 Namespaced Storage (Replaces `__gap`)
```solidity
// v4: uint256[50] private __gap; // manual gap management
// v5: ERC-7201 namespaced storage
// Location = keccak256(abi.encode(uint256(keccak256("myprotocol.storage.main")) - 1)) & ~bytes32(uint256(0xff))

/// @custom:storage-location erc7201:myprotocol.storage.main
struct MainStorage {
    uint256 value;
    mapping(address => uint256) balances;
}

function _getMainStorage() private pure returns (MainStorage storage $) {
    assembly { $.slot := MAIN_STORAGE_LOCATION }
}
```

---

## Permit2 (Gasless Approvals)

### Address (ALL EVM chains)
`0x000000000022D473030F116dDEE9F6B43aC78BA3`

### How It Works
1. User approves Permit2 contract once (max allowance)
2. For each operation, user signs an off-chain EIP-712 message
3. Protocol calls `permit2.permitTransferFrom()` with the signature
4. Permit2 transfers tokens from user to protocol

### Benefits
- One-time approval instead of per-protocol approvals
- Expiring permits (time-bounded)
- Batch permits (multiple tokens in one signature)
- Signature-based (no on-chain transaction for approval)

### Integration
```solidity
// Protocol contract
function swapWithPermit(
    ISignatureTransfer.PermitTransferFrom calldata permit,
    ISignatureTransfer.SignatureTransferDetails calldata transferDetails,
    bytes calldata signature
) external {
    PERMIT2.permitTransferFrom(permit, transferDetails, msg.sender, signature);
    // ... execute swap with transferred tokens
}
```

---

## ENS (Ethereum Name Service)

### Core Contracts
| Contract | Address | Purpose |
|----------|---------|---------|
| Registry | `0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e` | Ownership records |
| Public Resolver | `0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63` | Name → address/content |
| Registrar Controller | `0x253553366Da8546fC250F225fe3d25d0C782303b` | .eth registration |
| Reverse Registrar | `0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb` | Address → name |

### namehash Algorithm
```
namehash("") = 0x0000...0000
namehash("eth") = keccak256(namehash("") + keccak256("eth"))
namehash("alice.eth") = keccak256(namehash("eth") + keccak256("alice"))
```

### Registration (Commit-Reveal)
1. `commit(keccak256(name, owner, secret))` — submit hash
2. Wait 60 seconds (minimum)
3. `register(name, owner, duration, secret, ...)` — reveal and register
- Names expire with 90-day grace period, then 21-day auction

### CCIP-Read (ERC-3668)
- Enables offchain subdomains (cb.id, lens.xyz)
- Resolver returns `OffchainLookup` error with gateway URL
- Client fetches from gateway, submits response back to resolver
- Resolver verifies gateway response on-chain

---

## Smart Account Design Considerations

### msg.sender Assumptions
- With AA, `msg.sender` may be a smart contract, not an EOA
- `tx.origin == msg.sender` check fails for smart accounts
- Use `EIP-1271` for signature verification (not just `ecrecover`)

### Gas Considerations
- Smart accounts have higher deployment cost (proxy creation)
- Each UserOp has overhead: verification gas + calldata gas
- Paymasters add validation overhead
- On L2s, smart account deployment may hit different gas costs

### Multi-Chain Account Sync
- Safe: deterministic addresses via CREATE2 (same salt = same address across chains)
- ERC-4337: factory address + salt determines counterfactual address
- EIP-7702: delegation is per-chain (must authorize on each chain separately)

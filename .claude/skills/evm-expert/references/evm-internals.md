# EVM Internals Reference

## Opcode Categories

### Stack Operations
| Opcode | Hex | Gas | Description |
|---|---|---|---|
| STOP | 0x00 | 0 | Halt execution |
| POP | 0x50 | 2 | Remove top stack item |
| PUSH1–PUSH32 | 0x60–0x7F | 3 | Push 1–32 bytes onto stack |
| DUP1–DUP16 | 0x80–0x8F | 3 | Duplicate 1st–16th stack item |
| SWAP1–SWAP16 | 0x90–0x9F | 3 | Swap top with 2nd–17th item |

### Arithmetic
| Opcode | Hex | Gas | Description |
|---|---|---|---|
| ADD | 0x01 | 3 | a + b |
| MUL | 0x02 | 5 | a * b |
| SUB | 0x03 | 3 | a - b |
| DIV | 0x04 | 5 | a / b (unsigned) |
| SDIV | 0x05 | 5 | a / b (signed) |
| MOD | 0x06 | 5 | a % b |
| SMOD | 0x07 | 5 | a % b (signed) |
| ADDMOD | 0x08 | 8 | (a + b) % N |
| MULMOD | 0x09 | 8 | (a * b) % N |
| EXP | 0x0A | 10* | a ** b (*+50 per byte of exponent) |
| SIGNEXTEND | 0x0B | 5 | Sign extend from bit position |

### Comparison & Bitwise
| Opcode | Hex | Gas | Description |
|---|---|---|---|
| LT/GT/SLT/SGT | 0x10–0x13 | 3 | Less/greater than (unsigned/signed) |
| EQ | 0x14 | 3 | Equality |
| ISZERO | 0x15 | 3 | a == 0 |
| AND/OR/XOR | 0x16–0x18 | 3 | Bitwise ops |
| NOT | 0x19 | 3 | Bitwise NOT |
| BYTE | 0x1A | 3 | Extract byte from word |
| SHL/SHR/SAR | 0x1B–0x1D | 3 | Shift left/right/arithmetic right (EIP-145) |

### Memory Operations
| Opcode | Hex | Gas | Description |
|---|---|---|---|
| MLOAD | 0x51 | 3* | Load 32 bytes from memory (*+expansion cost) |
| MSTORE | 0x52 | 3* | Store 32 bytes to memory |
| MSTORE8 | 0x53 | 3* | Store 1 byte to memory |
| MSIZE | 0x59 | 2 | Current memory size in bytes |
| MCOPY | 0x5E | 3* | Copy memory regions (EIP-5656, Cancun) |

### Storage Operations
| Opcode | Hex | Gas | Description |
|---|---|---|---|
| SLOAD | 0x54 | 2100/100 | Load from storage (cold/warm, EIP-2929) |
| SSTORE | 0x55 | varies | Store to storage (see EIP-2200 gas schedule) |
| TLOAD | 0x5C | 100 | Load from transient storage (EIP-1153, Cancun) |
| TSTORE | 0x5D | 100 | Store to transient storage (EIP-1153, Cancun) |

### SSTORE Gas Schedule (EIP-2200 + EIP-3529)
- **Cold access surcharge**: 2100 gas (first access in tx, EIP-2929)
- **No-op** (value unchanged): 100 gas (warm)
- **Clean → non-zero**: 20,000 gas
- **Non-zero → different non-zero**: 2,900 gas (warm)
- **Non-zero → zero**: 2,900 gas + 4,800 gas refund
- **Dirty slot re-set**: 100 gas (warm) with possible refund adjustments

### Call Operations
| Opcode | Hex | Description |
|---|---|---|
| CALL | 0xF1 | Standard call: new context, new storage, new msg.sender |
| CALLCODE | 0xF2 | **Deprecated** — like DELEGATECALL but with caller's msg.sender |
| DELEGATECALL | 0xF4 | Execute target code in caller's context (storage, msg.sender, msg.value preserved) |
| STATICCALL | 0xFA | Read-only call; reverts on state-changing opcodes |
| CREATE | 0xF0 | Deploy contract, address = keccak256(rlp([sender, nonce]))[12:] |
| CREATE2 | 0xF5 | Deploy at deterministic address = keccak256(0xff ++ sender ++ salt ++ keccak256(initcode))[12:] |
| RETURN | 0xF3 | Return data from memory |
| REVERT | 0xFD | Revert with data from memory (refunds remaining gas) |
| SELFDESTRUCT | 0xFF | **Deprecated (EIP-6780)** — only works in same-tx creation since Dencun |

### Environment
| Opcode | Hex | Description |
|---|---|---|
| ADDRESS | 0x30 | Current contract address |
| BALANCE | 0x31 | ETH balance of address |
| ORIGIN | 0x32 | tx.origin (original EOA sender) |
| CALLER | 0x33 | msg.sender |
| CALLVALUE | 0x34 | msg.value in wei |
| CALLDATALOAD | 0x35 | Load 32 bytes from calldata |
| CALLDATASIZE | 0x36 | Size of calldata |
| CALLDATACOPY | 0x37 | Copy calldata to memory |
| CODESIZE | 0x38 | Size of running contract code |
| CODECOPY | 0x39 | Copy code to memory |
| GASPRICE | 0x3A | tx.gasprice |
| EXTCODESIZE | 0x3B | Size of external account code |
| EXTCODECOPY | 0x3C | Copy external code to memory |
| RETURNDATASIZE | 0x3D | Size of last return data |
| RETURNDATACOPY | 0x3E | Copy return data to memory |
| EXTCODEHASH | 0x3F | keccak256 of external code |
| SELFBALANCE | 0x47 | Current contract ETH balance (cheaper than BALANCE(ADDRESS)) |

### Block Information
| Opcode | Hex | Description |
|---|---|---|
| BLOCKHASH | 0x40 | Hash of given block (last 256 only) |
| COINBASE | 0x41 | Block beneficiary (miner/validator) |
| TIMESTAMP | 0x42 | Block timestamp |
| NUMBER | 0x43 | Block number |
| PREVRANDAO | 0x44 | Beacon chain randomness (was DIFFICULTY pre-merge) |
| GASLIMIT | 0x45 | Block gas limit |
| CHAINID | 0x46 | Chain ID (EIP-1344) |
| BASEFEE | 0x48 | Block base fee (EIP-3198) |
| BLOBHASH | 0x49 | Hash of blob at index (EIP-4844) |
| BLOBBASEFEE | 0x4A | Blob base fee (EIP-7516) |

### Logging
| Opcode | Hex | Description |
|---|---|---|
| LOG0 | 0xA0 | Log with 0 topics |
| LOG1 | 0xA1 | Log with 1 topic (typically event signature) |
| LOG2 | 0xA2 | Log with 2 topics |
| LOG3 | 0xA3 | Log with 3 topics (most ERC-20 events) |
| LOG4 | 0xA4 | Log with 4 topics (max) |

---

## Memory Layout Conventions (Solidity)
- `0x00–0x3F` (64 bytes): scratch space for hashing
- `0x40–0x5F` (32 bytes): free memory pointer (points to next available memory)
- `0x60–0x7F` (32 bytes): zero slot (used as initial value for dynamic memory arrays)
- `0x80+`: free memory starts here

## Calldata Layout
```
| 4 bytes   | 32 bytes     | 32 bytes     | ...          |
| selector  | arg0 (padded)| arg1 (padded)| argN (padded)|
```
- Dynamic types (bytes, string, arrays): offset pointer at the argument position → length + data at the end

---

## Contract Creation
1. **Init code** runs: constructor logic + returns the **runtime bytecode**
2. Runtime bytecode is stored on-chain as the contract's code
3. Constructor args are ABI-encoded and appended after the init code in the creation tx data
4. `CREATE` address: `keccak256(rlp([sender, nonce]))[12:]`
5. `CREATE2` address: `keccak256(0xff ++ sender ++ salt ++ keccak256(initcode))[12:]` — deterministic, independent of nonce

---

## Key EIPs for EVM Developers
| EIP | Name | Impact |
|---|---|---|
| EIP-20 | ERC-20 Token Standard | Fungible token interface |
| EIP-721 | ERC-721 NFT Standard | Non-fungible token interface |
| EIP-1155 | Multi Token Standard | Batch-capable multi-token |
| EIP-1167 | Minimal Proxy (Clone) | Cheap contract cloning |
| EIP-1559 | Fee market change | Base fee + priority fee |
| EIP-1967 | Proxy Storage Slots | Standard proxy implementation slots |
| EIP-2612 | Permit | Gasless ERC-20 approvals |
| EIP-2929 | Gas cost increases | Cold/warm access lists |
| EIP-2930 | Access lists | Optional tx access list |
| EIP-3156 | Flash Loans | Standard flash loan interface |
| EIP-4337 | Account Abstraction | UserOperations, bundlers, paymasters |
| EIP-4626 | Tokenized Vaults | Standard yield vault interface |
| EIP-4844 | Proto-Danksharding | Blob transactions for L2 data |
| EIP-5656 | MCOPY | Memory copy opcode |
| EIP-6780 | SELFDESTRUCT restriction | Only works in creation tx |
| EIP-1153 | Transient storage | TLOAD/TSTORE (cleared after tx) |
| EIP-7702 | Set EOA code | Allow EOAs to temporarily act as contracts |
| EIP-7951 | secp256r1 precompile | Native passkey/WebAuthn signature verification |
| EIP-3156 | Flash Loans | Standard flash loan interface |
| EIP-2535 | Diamond Standard | Multi-facet proxy with function routing |
| EIP-5115 | Standardized Yield | Pendle SY token standard |
| EIP-7579 | Smart Account Modules | Validator, executor, hook, fallback modules |
| EIP-6963 | Multi-Provider Discovery | Replace window.ethereum race condition |
| EIP-3668 | CCIP-Read (OffchainLookup) | Off-chain data resolution (ENS subdomains) |
| EIP-7966 | Synchronous Receipts | Real-time tx receipts (MegaETH) |

---

## EVM Differences Across Chains

Not all EVM chains behave identically. Key differences:

| Feature | Ethereum | zkSync | Monad | MegaETH | Sei |
|---------|----------|--------|-------|---------|-----|
| EVM Version | cancun | paris (no PUSH0) | cancun | custom | paris (no PUSH0) |
| CREATE2 | Standard | Includes constructorInput | Standard | Standard | Standard |
| Intrinsic gas | 21,000 | varies | 21,000 | 60,000 | varies |
| Cold SLOAD | 2,100 | 2,100 | 8,100 (4x) | varies | 2,100 |
| Contract limit | 24.5 KB | varies | 128 KB | 512 KB | 24.5 KB |
| Account model | EOA + Contract | All smart accounts | EOA + Contract | EOA + Contract | EOA + Contract |

See `multi-chain.md` for complete chain-specific reference.

# EVM Development & Research Tooling

Comprehensive reference for development frameworks, client libraries, simulation tools, indexing, and research utilities for EVM development.

---

## Development Frameworks

### Foundry (Solidity-Native)

**Components:**
- `forge` — build, test, deploy, verify
- `cast` — CLI for chain interaction
- `anvil` — local EVM node (fork support)
- `chisel` — interactive Solidity REPL

**Key Commands:**
```bash
# Build & test
forge build
forge test -vvvv                    # full trace on failure
forge test --match-test testSwap    # run specific test
forge test --fork-url $RPC_URL      # fork mainnet

# Gas analysis
forge test --gas-report
forge snapshot                      # gas snapshot for regression

# Coverage
forge coverage --report lcov

# Inspect contract
forge inspect MyContract storage-layout
forge inspect MyContract abi
forge inspect MyContract ir          # Yul IR

# Deploy
forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast --verify

# Verify
forge verify-contract 0xAddr MyContract --chain-id 1 --etherscan-api-key $KEY
```

**Testing Patterns:**
```solidity
// Fork test at specific block
function setUp() public {
    vm.createSelectFork("mainnet", 19_000_000);
}

// Fuzz test with input bounding
function testFuzz_transfer(address to, uint256 amount) public {
    amount = bound(amount, 1, token.balanceOf(address(this)));
    vm.assume(to != address(0));
    token.transfer(to, amount);
}

// Invariant test with handler
function invariant_solvency() public {
    assertGe(vault.totalAssets(), vault.totalDebt());
}
```

**Cheatcodes:**
| Cheatcode | Purpose |
|-----------|---------|
| `vm.prank(addr)` | Next call from addr |
| `vm.startPrank(addr)` | All calls from addr until stopPrank |
| `vm.deal(addr, amount)` | Set ETH balance |
| `deal(token, addr, amount)` | Set ERC-20 balance |
| `vm.warp(timestamp)` | Set block.timestamp |
| `vm.roll(blockNumber)` | Set block.number |
| `vm.expectRevert(selector)` | Expect next call reverts |
| `vm.expectEmit(t1,t2,t3,data)` | Expect specific event |
| `vm.store(addr, slot, value)` | Write storage slot |
| `vm.load(addr, slot)` | Read storage slot |
| `vm.assume(condition)` | Skip fuzz input if false |
| `bound(x, min, max)` | Clamp fuzz input (preferred over assume) |

### Hardhat (TypeScript-Native)

**Key Commands:**
```bash
npx hardhat compile
npx hardhat test
npx hardhat node                    # local node
npx hardhat ignition deploy ./ignition/modules/MyModule.ts --network mainnet
```

**Custom Network Methods:**
```typescript
// Manipulate state in tests
await network.provider.send("hardhat_setBalance", [addr, "0xDE0B6B3A7640000"]);
await network.provider.send("hardhat_setStorageAt", [addr, slot, value]);
await network.provider.send("hardhat_impersonateAccount", [addr]);
await network.provider.send("hardhat_reset", [{ forking: { jsonRpcUrl: url, blockNumber: n } }]);
await network.provider.send("evm_increaseTime", [3600]);
await network.provider.send("evm_mine");
```

---

## Client Libraries

### viem (TypeScript, Tree-Shakeable)

```typescript
import { createPublicClient, createWalletClient, http, parseAbi } from 'viem';
import { mainnet } from 'viem/chains';

// Read
const client = createPublicClient({ chain: mainnet, transport: http() });
const balance = await client.readContract({
    address: '0x...', abi: parseAbi(['function balanceOf(address) view returns (uint256)']),
    functionName: 'balanceOf', args: ['0x...']
});

// Simulate-then-execute (catch reverts before gas spend)
const { request } = await client.simulateContract({ ... });
const hash = await walletClient.writeContract(request);

// Batch JSON-RPC
const client = createPublicClient({ chain: mainnet, transport: http(), batch: { multicall: true } });

// Multicall (batch reads)
const results = await client.multicall({ contracts: [
    { address: tokenA, abi, functionName: 'balanceOf', args: [user] },
    { address: tokenB, abi, functionName: 'balanceOf', args: [user] },
]});
```

**Key Pattern:** Always use `as const` on ABI arrays for full type inference.

### ethers.js v6

```typescript
import { JsonRpcProvider, Wallet, Contract, parseEther, formatUnits } from 'ethers';

const provider = new JsonRpcProvider(rpcUrl);
const wallet = new Wallet(privateKey, provider);
const contract = new Contract(address, abi, wallet);

// Read
const balance = await contract.balanceOf(userAddress);

// Write
const tx = await contract.transfer(to, amount);
const receipt = await tx.wait();
console.log(receipt.status); // 1 = success, 0 = revert

// Events
const filter = contract.filters.Transfer(from, null); // from=specific, to=any
const events = await contract.queryFilter(filter, fromBlock, toBlock);

// EIP-712 signing
const signature = await wallet.signTypedData(domain, types, value);
```

**v6 Changes:** Native `bigint` (no BigNumber), `parseEther`/`formatEther` are standalone functions.

### wagmi (React Hooks)

```typescript
import { useReadContract, useWriteContract, useSimulateContract } from 'wagmi';

// Read with Multicall batching
const { data } = useReadContract({ address, abi, functionName: 'balanceOf', args: [user] });

// Simulate → Write pattern
const { data: sim } = useSimulateContract({ address, abi, functionName: 'transfer', args: [to, amount] });
const { writeContract } = useWriteContract();
writeContract(sim!.request);

// Batch reads (uses Multicall3 automatically)
const { data } = useReadContracts({ contracts: [
    { address: tokenA, abi, functionName: 'symbol' },
    { address: tokenA, abi, functionName: 'decimals' },
]});
```

---

## cast (Foundry CLI — Chain Interaction)

Essential `cast` commands for research and debugging:

```bash
# Read contract state
cast call 0xAddr "balanceOf(address)(uint256)" 0xUser --rpc-url $RPC
cast storage 0xAddr 0 --rpc-url $RPC          # read slot 0
cast code 0xAddr --rpc-url $RPC                # get bytecode

# Decode data
cast sig "transfer(address,uint256)"           # → 0xa9059cbb
cast 4byte 0xa9059cbb                          # → transfer(address,uint256)
cast abi-decode "transfer(address,uint256)" 0x... # decode calldata
cast calldata-decode "transfer(address,uint256)" 0xa9059cbb... # full calldata decode

# Transaction analysis
cast tx 0xTxHash --rpc-url $RPC                # get tx details
cast receipt 0xTxHash --rpc-url $RPC           # get receipt
cast run 0xTxHash --rpc-url $RPC               # replay tx locally

# Log filtering
cast logs --address 0xAddr --topic0 "Transfer(address,address,uint256)" --from-block 19000000 --rpc-url $RPC

# Block info
cast block latest --rpc-url $RPC
cast block-number --rpc-url $RPC
cast base-fee --rpc-url $RPC
cast gas-price --rpc-url $RPC

# Encoding
cast keccak "Transfer(address,address,uint256)" # event topic0
cast abi-encode "f(address,uint256)" 0xAddr 1000
cast --to-wei 1.5 ether                        # → 1500000000000000000
cast --from-wei 1500000000000000000             # → 1.5

# ENS
cast resolve-name vitalik.eth --rpc-url $RPC
cast lookup-address 0xd8dA... --rpc-url $RPC

# Storage layout exploration
cast storage 0xAddr --rpc-url $RPC              # dump all non-zero slots
```

---

## Simulation & Debugging

### Tenderly

**Simulation API v2:**
```bash
# Single transaction simulation
curl -X POST "https://api.tenderly.co/api/v1/account/$ACCOUNT/project/$PROJECT/simulate" \
  -H "X-Access-Key: $KEY" \
  -d '{
    "network_id": "1",
    "from": "0x...",
    "to": "0x...",
    "input": "0x...",
    "value": "0",
    "save": true,
    "state_objects": {
      "0xAddr": { "balance": "1000000000000000000" }
    }
  }'
```

**Bundle Simulation (sequential state carry-over):**
```bash
# Simulate multiple txs in sequence (e.g., approve → swap)
curl -X POST ".../simulate-bundle" \
  -d '{ "simulations": [
    { "from": "0x...", "to": "0xToken", "input": "0x095ea7b3..." },
    { "from": "0x...", "to": "0xRouter", "input": "0x38ed1739..." }
  ]}'
```

**Virtual TestNets (fork + persist):**
```bash
# Custom RPC methods on Virtual TestNets
tenderly_setBalance(address, "0xDE0B6B3A7640000")
tenderly_setErc20Balance(tokenAddr, walletAddr, "0x...")
```

### Anvil (Foundry Local Node)

```bash
# Fork mainnet at specific block
anvil --fork-url $RPC_URL --fork-block-number 19000000

# With auto-impersonation
anvil --fork-url $RPC_URL --auto-impersonate

# Custom chain ID
anvil --chain-id 31337

# Unlimited balance accounts
anvil --balance 10000
```

**Anvil RPC Methods:**
```bash
anvil_setBalance(addr, amount)
anvil_setCode(addr, bytecode)
anvil_setStorageAt(addr, slot, value)
anvil_impersonateAccount(addr)
anvil_mine(numBlocks, interval)
evm_snapshot()                    # save state
evm_revert(snapshotId)           # restore state
```

---

## Indexing & Data

### The Graph

**What:** Decentralized indexing protocol. Define event handlers in AssemblyScript, query via GraphQL.

**Key Patterns:**
```typescript
// subgraph.yaml — data source definition
dataSources:
  - kind: ethereum
    name: Uniswap
    source:
      address: "0x..."
      abi: Factory
      startBlock: 12369621
    mapping:
      eventHandlers:
        - event: PairCreated(indexed address,indexed address,address,uint256)
          handler: handlePairCreated

// Factory pattern (dynamic data sources)
// When a new contract is deployed, create a new data source
PairTemplate.create(pairAddress);
```

**Graph-ts Types:** `BigInt`, `BigDecimal`, `Bytes`, `Address` — NOT native JavaScript types.

### Dune Analytics
- SQL queries on decoded blockchain data
- Supports Ethereum, Arbitrum, Optimism, Base, Polygon, BSC, Avalanche
- Tables: `ethereum.transactions`, `ethereum.logs`, `ethereum.traces`
- Decoded tables: `uniswap_v3_ethereum.Pair_evt_Swap`
- Spellbook for curated data models

---

## Research & Exploration Tools

### Block Explorers
| Chain | Explorer | API Base URL |
|-------|----------|-------------|
| Ethereum | Etherscan | `https://api.etherscan.io/api` |
| Arbitrum | Arbiscan | `https://api.arbiscan.io/api` |
| Base | Basescan | `https://api.basescan.org/api` |
| Optimism | Optimistic Etherscan | `https://api-optimistic.etherscan.io/api` |
| Polygon | Polygonscan | `https://api.polygonscan.com/api` |
| BSC | BscScan | `https://api.bscscan.com/api` |
| Avalanche | SnowTrace | `https://api.snowtrace.io/api` |

All use the same API format:
```
GET {base}?module=contract&action=getabi&address=0x...&apikey=KEY
GET {base}?module=contract&action=getsourcecode&address=0x...&apikey=KEY
```

### Signature & ABI Lookup
| Service | URL | Purpose |
|---------|-----|---------|
| 4byte.directory | `https://www.4byte.directory/api/v1/signatures/?hex_signature=0x...` | Function selectors |
| 4byte.directory | `https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0x...` | Event signatures |
| OpenChain | `https://api.openchain.xyz/signature-database/v1/lookup?function=0x...` | Selectors + events |
| Sourcify | `https://sourcify.dev/server/files/any/{chainId}/0x{addr}` | Verified source + ABI |

### Decompilers & Bytecode Analysis
| Tool | URL | Purpose |
|------|-----|---------|
| Dedaub | `https://app.dedaub.com/` | Bytecode decompiler + storage analysis |
| Heimdall | CLI tool (`heimdall decompile`) | Fast bytecode decompilation |
| EVM Diff | `https://evmdiff.com/` | Compare EVM implementations across chains |
| OpenZeppelin Diff | Compare OZ versions | Storage layout diff |

### On-Chain Data APIs
| Service | Purpose | Free Tier |
|---------|---------|-----------|
| Alchemy | RPC + enhanced APIs (getNFTs, getTokenBalances) | Yes |
| QuickNode | RPC + add-ons (trace, debug) | Yes |
| Infura | RPC (Ethereum, L2s) | Yes |
| Ankr | Multi-chain RPC | Yes |
| CoinGecko | Token prices, market data | Yes |
| DeFi Llama | TVL, yields, protocol data | Yes (no key) |
| Dune | Historical decoded data via SQL | Free queries |

### Token & Protocol Research
```bash
# Get token info quickly
cast call 0xToken "name()" --rpc-url $RPC | cast --to-ascii
cast call 0xToken "symbol()" --rpc-url $RPC | cast --to-ascii
cast call 0xToken "decimals()" --rpc-url $RPC | cast --to-dec
cast call 0xToken "totalSupply()" --rpc-url $RPC | cast --to-dec

# Check if address is contract or EOA
cast code 0xAddr --rpc-url $RPC   # empty = EOA, non-empty = contract

# Check proxy implementation
cast storage 0xProxy 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc --rpc-url $RPC

# Trace a transaction
cast run 0xTxHash --rpc-url $RPC   # full trace
cast receipt 0xTxHash --rpc-url $RPC  # receipt with logs
```

---

## Scaffold-ETH 2 (Full-Stack Prototyping)

**What:** Foundry + Next.js starter kit with auto-generated debug pages.

```bash
npx create-eth@latest
# Generates: packages/foundry/ + packages/nextjs/

# Custom hooks
useScaffoldReadContract({ contractName: "MyToken", functionName: "balanceOf", args: [address] });
useScaffoldWriteContract({ contractName: "MyToken", functionName: "transfer", args: [to, amount] });
useScaffoldEventHistory({ contractName: "MyToken", eventName: "Transfer", fromBlock: 0n });
```

**Best for:** Rapid prototyping, hackathons, debug-first development.

---

## Frontend Integration Patterns

### Wallet Connection State Machine
```
disconnected → connecting → connected → wrong-network
     ↑              ↓            ↓
     └──────────────┘     (chain switch)
```

### Transaction Lifecycle
```
idle → awaiting-signature → pending → confirmed/failed
                ↓ (user rejects: error 4001 — do NOT show error toast)
              idle
```

### Key Frontend Libraries
| Library | Purpose |
|---------|---------|
| wagmi | React hooks for Ethereum |
| viem | Low-level EVM client |
| RainbowKit | Wallet connection UI (30+ wallets) |
| ConnectKit | Alternative wallet UI |
| Privy | Embedded wallets (email/social login) |

### EIP-6963 (Multi-Injected Provider Discovery)
Replaces `window.ethereum` race condition. Wallets announce themselves via events:
```typescript
window.addEventListener("eip6963:announceProvider", (event) => {
    const { info, provider } = event.detail;
    // info.name, info.icon, info.rdns, info.uuid
});
window.dispatchEvent(new Event("eip6963:requestProvider"));
```

---

## Gas Optimization Tools

```bash
# Gas report per function
forge test --gas-report

# Gas snapshot for regression
forge snapshot
forge snapshot --diff   # compare against previous

# Inspect storage layout (find packing opportunities)
forge inspect MyContract storage-layout

# Check contract size
forge build --sizes
```

### Common Gas Savings
- Pack storage variables (group smaller types together)
- Use `calldata` instead of `memory` for external function params
- Use custom errors instead of require strings
- Use `unchecked{}` for math that can't overflow
- Batch operations with Multicall
- Use `immutable` and `constant` for values set once
- Cache storage reads in local variables

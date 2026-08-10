# Angstrom (Sorella Labs) — Topics, Selectors, Addresses

**Status:** verified against live Ethereum RPC (publicnode) and the canonical `SorellaLabs/angstrom` repo on 2026-06-09. Confirmed absent on Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon.
**Scope:** Angstrom hook, ControllerV1, AngstromAdapter on Ethereum mainnet (chain ID 1). EventEmitter contract is defined in the repo but shows **no evidence of mainnet deployment** as of verification date — flagged throughout.

---

## Architecture orientation

Angstrom is **not a traditional AMM**. It is a Uniswap V4 hook that implements an off-chain order-routing and MEV-protection layer:

- Off-chain **"leader" nodes** collect user limit orders and top-of-block (ToB) arbitrage orders each block.
- The leader calls `execute(bytes)` on the Angstrom hook once per block, submitting an opaque PADE-encoded bundle containing all settled user orders, LP reward updates, and ToB arb.
- **Users do not call `swap()`** — they sign orders off-chain; execution is batched by the leader.
- The hook controls which Uniswap V4 pools it manages by registering pools through `ControllerV1.configurePool`. Every Angstrom pool lives inside the UniV4 `PoolManager` singleton with Angstrom as the hook address.
- **Monitoring primary signal**: calls to `execute(bytes)` on the hook. Calldata is PADE-encoded; to decode order details, parse per the PADE encoding spec in `contracts/docs/pade-encoding-format.md` and `payload-types.md`.
- **Events are sparse**: the hook emits only one anonymous `log0` per `execute` call (a 32-byte keccak of the fee summary buffer, used for integrity checking). All trade details live in calldata.

Hook address vanity encoding: the low 2 bytes of `0x0000000aa232009084bd71a5797d089aa4edfad4` are `0xfad4`, which encodes the UniV4 hook callback flags. Active callbacks:
`BEFORE_INITIALIZE`, `AFTER_INITIALIZE`, `BEFORE_ADD_LIQUIDITY`, `BEFORE_REMOVE_LIQUIDITY`, `BEFORE_SWAP`, `AFTER_SWAP`, `AFTER_DONATE`, `AFTER_SWAP_RETURNS_DELTA`.
`AFTER_ADD_LIQUIDITY` and `AFTER_REMOVE_LIQUIDITY` are **not** set.

---

## 1. Topics (chain-agnostic)

### 1.1 EventEmitter — fee governance events

> **UNVERIFIED — no on-chain deployment found.** The `EventEmitter.s.sol` deploy script exists in the repo and defines the contract; exhaustive search of all deployer EOA transactions, multisig transactions, and TimelockController history found no EventEmitter deployment on Ethereum mainnet as of block 25280064 (2026-06-09). Topics are computed from source; the contract **address is unknown**.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x926949e7d95e19ed1a0e515ff8f86f10f48ddd8971ca26693a407042147c5c47` | `FeeClaimQueued(address indexed asset, uint8 indexed claimType, uint256 amount, uint256 startBlock, uint256 endBlock)` | `claimType`: GAS=0, PROTOCOL=1, BOTH=2. Emitted by `DEFAULT_ADMIN_ROLE` callers (timelock + multisig). |
| `0x4d8ad161753ade162feebb7c6d7a393c6e5a9ce74754f3859d4e47abe20e9aeb` | `FeeClaimExecuted(address indexed asset, uint8 indexed claimType, uint256 amount, uint256 startBlock, uint256 endBlock)` | Same `claimType` enum. Signals fee payout execution. |

The EventEmitter also exposes `emitGenericEvent(bytes32[] topics, bytes logData)` which can emit arbitrary logs; filter carefully by address when monitoring.

### 1.2 ControllerV1 — governance and node management

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xb25d03aaf308d7291709be1ea28b800463cf3a9a4c4a5555d7333a964c1dfebd` | `NodeAdded(address indexed node)` | New leader node approved. |
| `0xcfc24166db4bb677e857cacabd1541fb2b30645021b27c5130419589b84db52b` | `NodeRemoved(address indexed node)` | Leader node revoked. |
| `0xf325a037d71efc98bc41dc5257edefd43a1d1162e206373e53af271a7a3224e9` | `PoolConfigured(address indexed asset0, address indexed asset1, uint16 tickSpacing, uint24 bundleFee, uint24 unlockedFee, uint24 protocolUnlockedFee)` | New Angstrom-managed pool registered. |
| `0x79f612570217c00df128c1b828dd6b321b3a70ae4c61b7a97fe4a71fc19df9ba` | `PoolRemoved(address indexed asset0, address indexed asset1, int24 tickSpacing, uint24 feeInE6)` | Pool de-listed. |
| `0xc93f1add41c218fa7665c10617033f441f8e3c16fa372796265445d7a1497c23` | `OpaqueBatchPoolUpdate()` | Emitted on every `batchUpdatePools` call; fee params changed but not decoded in event. |
| `0xcbcf384e26c16836177d0b6d8ce70541a86ff3091deecaf5b6e0fa5564c78250` | `NewControllerSet(address indexed newController)` | Pending controller change queued. |
| `0xab258afbe9ebb963a1baeadbb7265f37c95f67b6ca707ab7f56268bcb7d291c8` | `NewControllerAccepted(address indexed newController)` | Controller migration complete. |

### 1.3 Angstrom hook — anonymous log (no topics)

The hook emits **one anonymous `log0`** per `execute` call via inline assembly in `Settlement._saveAndSettle`. No topic — only 32 bytes of data containing `keccak256(fee_summary_buffer)`. This can be detected by filtering `log0` events from the hook address with no topics.

### 1.4 UniV4 PoolManager — pool activity (Angstrom pools)

Angstrom pools emit standard UniV4 `PoolManager` events; filter by the `PoolId` (topic1) for pools where `hooks == 0x0000000aa232009084bd71a5797d089aa4edfad4`. Current active pools:

| PoolId component | Pool 0 | Pool 1 |
|---|---|---|
| token0 | USDC `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` | WETH `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` |
| token1 | WETH `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | USDT `0xdac17f958d2ee523a2206206994597c13d831ec7` |

PoolManager topic0s for Angstrom activity:

| topic0 | Event |
|--------|-------|
| `0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f` | `Swap(PoolId indexed id, address indexed sender, int128 amount0, int128 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick, uint24 fee)` |
| `0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec` | `ModifyLiquidity(PoolId indexed id, address indexed sender, int24 tickLower, int24 tickUpper, int256 liquidityDelta, bytes32 salt)` |
| `0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438` | `Initialize(PoolId indexed id, Currency indexed currency0, Currency indexed currency1, uint24 fee, int24 tickSpacing, IHooks hooks, uint160 sqrtPriceX96, int24 tick)` |

For Angstrom `Swap` events: `sender` will be the Angstrom hook address (the hook calls `poolManager.swap` internally inside the `execute` callback). Filter `PoolManager.Swap` with `topic1 = <angstrom PoolId>`.

---

## 2. Function selectors (chain-agnostic)

### 2.1 Angstrom hook (`0x0000000aa232009084bd71a5797d089aa4edfad4`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x09c5eabe` | `execute(bytes encoded)` | **Primary monitoring target.** Called once per block by the winning leader node. Decoding requires PADE format parser. Access-gated: caller must be an approved node. |
| `0x7407905c` | `compose(address target, bytes calldata data)` | Composability entry point: called from within an existing `execute` to invoke `target` with `data`. |
| `0x47e7ef24` | `deposit(address asset, uint256 amount)` | Pull `asset` from caller into their Angstrom balance. |
| `0x8340f549` | `deposit(address asset, address to, uint256 amount)` | Pull `asset` from caller and credit `to`. |
| `0xf3fef3a3` | `withdraw(address asset, uint256 amount)` | Withdraw `amount` of `asset` from caller's balance. |
| `0xd9caed12` | `withdraw(address asset, address to, uint256 amount)` | Withdraw `amount` to `to`. |

UniV4 hook callbacks (called by PoolManager — selectors are the UniV4 standard for each callback):

| Callback | Notes |
|----------|-------|
| `beforeInitialize` | Validates hook flags match expected Angstrom permissions. |
| `afterInitialize` | Pool state initialization. |
| `beforeAddLiquidity` | Validates liquidity actions (only via hook-controlled paths). |
| `beforeRemoveLiquidity` | Same. |
| `beforeSwap` | Blocks direct external swaps — reverts unless caller is the hook itself (MEV protection). |
| `afterSwap` + `afterSwapReturnsDelta` | Applies Angstrom pool AMM logic and reward accounting post-swap. |

### 2.2 ControllerV1 (`0x1746484ea5e11c75e009252c102c8c33e0315fd4`)

| Selector | Signature | Role required | Notes |
|----------|-----------|---------------|-------|
| `0x5c1b182d` | `initStartNodes(address[] initNodes)` | owner | One-time node initialization. |
| `0x9d95f1cc` | `addNode(address node)` | owner | Approve a new leader node. |
| `0xb2b99ec9` | `removeNode(address node)` | fastOwner | Revoke a leader node. |
| `0x13871465` | `configurePool(address asset0, address asset1, uint16 tickSpacing, uint24 bundleFee, uint24 unlockedFee, uint24 protocolUnlockedFee)` | fastOwner | Register / update an Angstrom pool. |
| `0x744b92e2` | `removePool(address asset0, address asset1)` | owner | De-list a pool. |
| `0x4d2bf47c` | `batchUpdatePools((address,address,uint24,uint24,uint24)[] updates)` | node / fastOwner / owner | Batch fee updates. Emits `OpaqueBatchPoolUpdate`. |
| `0x182e6f39` | `distributeFees((address,uint256,(address,uint256)[])[] assets)` | owner | Distribute collected protocol fees. |
| `0x33830e48` | `collect_unlock_swap_fees(address to, bytes packed_assets)` | fastOwner | Collect swap fees via PoolManager unlock. |
| `0x59baef40` | `setNewController(address newController)` | owner | Stage controller migration. |
| `0xf86ad98a` | `acceptNewController()` | pending controller | Complete migration. |

### 2.3 AngstromAdapter (`0xb535aeb27335b91e1b5bccbd64888ba7574efbf8`)

Convenience swap adapter that wraps UniV4 pool access for external callers; applies attestation-based bundle validation before allowing a swap.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa88f90c1` | `swap((address,address,uint24,int24,address) key, bool zeroForOne, uint128 amountIn, uint128 minAmountOut, (uint64 blockNumber, bytes unlockData)[] bundle, address recipient, uint256 deadline) returns (uint256 amountOut)` | `bundle` is the attestation array: the adapter picks the entry matching the current block. |
| `0x91dd7346` | `unlockCallback(bytes data)` | Called by UniV4 PoolManager during the unlock flow. |

---

## 3. Addresses

### 3.1 Ethereum mainnet (chain ID 1) — all verified on-chain

| Contract | Address | Bytecode size | Proxy |
|----------|---------|---------------|-------|
| Angstrom hook (v1) | `0x0000000aa232009084bd71a5797d089aa4edfad4` | 23 569 B | No (EIP-1967 slot = zero) |
| ControllerV1 | `0x1746484ea5e11c75e009252c102c8c33e0315fd4` | 10 552 B | No (EIP-1967 slot = zero) |
| AngstromAdapter | `0xb535aeb27335b91e1b5bccbd64888ba7574efbf8` | 5 347 B | No (EIP-1967 slot = zero) |
| TimelockController (governance) | `0x60d41d9708bbefd29000d1486c6406ef23526c01` | 7 845 B | No |
| Multisig (Safe 1.3.0) | `0xd31c82069da3013fdb16b731ad19076af9b93105` | 171 B (Safe 1.3.0 proxy) | Yes → Safe singleton |
| UniV4 PoolManager | `0x000000000004444c5dc75cb358380d2e3de08a90` | 24 009 B | No |
| EventEmitter | **NOT DEPLOYED** | — | — |

Governance hierarchy: `owner` of ControllerV1 = TimelockController (5-day min delay); `fastOwner` = Multisig (immediate ops); nodes = 3 approved leader EOAs (as of block 25280064).

Deployer EOA: `0x6480c1af044ccda534998232428fa5a144127ece`
Deployment tx (Angstrom hook + ControllerV1): `0x35cd06f2d4c1455ea7e1796355632b30a8ac9cf78ba100998c1ef837b078a12c` (block 22971782, 2025-07-22)
TimelockController deployment tx: `0xc1d02a1e086c3f64e280ae8386b9d79bbca37e2a8e33a1d3b0c14dea4a8d09ce` (block 22971781)
AngstromAdapter deployment tx: `0xe7372593f0d48ad9d6bb14842813dedb2db1d0f9f86c928b52d8257531953a64` (block 23447819, 2025-09-26)

### 3.2 All other chains — confirmed absent

| Chain | Chain ID | Angstrom hook |
|-------|----------|--------------|
| Base | 8453 | `0x` (no code) |
| BNB Smart Chain | 56 | `0x` (no code) |
| Avalanche C-Chain | 43114 | `0x` (no code) |
| Arbitrum One | 42161 | `0x` (no code) |
| Optimism | 10 | `0x` (no code) |
| Polygon PoS | 137 | `0x` (no code) |

---

## 4. Active state (as of block 25280064)

**Active leader nodes (3):**
- `0x5875db54cd9ae2b2a875e09bb731772297ae9d92`
- `0x2252f216f4a494a87025123425181ca1bb754fb8`
- `0xc917c3fa468f2c4b9c84c72caa46420eb9825249`

**Active pools (2):**
- Pool 0: USDC / WETH (`0xa0b86991…` / `0xc02aaa39…`)
- Pool 1: WETH / USDT (`0xc02aaa39…` / `0xdac17f95…`)

**Token holdings in hook (approx.):** ~$484k across 97 tokens; largest: USDC ~$334k, WETH ~$120k, USDT ~$29k.

---

## 5. Monitoring notes

1. **Primary signal — `execute(bytes)` calls.** Filter Ethereum transactions `to = 0x0000000aa232009084bd71a5797d089aa4edfad4` with selector `0x09c5eabe`. These happen approximately once per block when Angstrom is active. Large or missing calls indicate protocol health changes.

2. **Node roster changes.** Watch `NodeAdded` / `NodeRemoved` from ControllerV1. A node removal mid-block may signal slashing or a key rotation.

3. **Pool configuration.** `PoolConfigured` and `PoolRemoved` on ControllerV1 change which UniV4 pools Angstrom manages — important context for the `execute` calldata scope.

4. **No fee events yet.** `FeeClaimQueued` / `FeeClaimExecuted` cannot be monitored until EventEmitter is deployed. Check periodically for new contracts deployed by the deployer EOA (`0x6480c1af…`) or the multisig.

5. **Deposits/withdrawals.** `deposit` and `withdraw` calls on the hook indicate LP activity. No events — monitor by function selector on the hook address.

6. **Governance lag.** Any `owner`-level changes (node adds, pool removes, fee distribution, controller migration) pass through the TimelockController with a minimum 5-day delay. The `scheduleBatch` / `executeBatch` pattern on the timelock is the governance mechanism; monitor `CallScheduled` / `CallExecuted` events on `0x60d41d97…`.

7. **Anonymous log0.** Each `execute` emits one anonymous log (no topics) from the hook with 32 bytes of fee-summary hash data. Useful for confirming execution happened without decoding calldata.

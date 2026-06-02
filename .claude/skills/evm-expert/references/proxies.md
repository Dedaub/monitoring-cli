# Proxy Patterns Reference

High-level mechanics for every proxy / delegate / upgradeable pattern an EVM
analyst is likely to encounter. Pure how-it-works — no project-specific
implementation notes. Use this when you need to identify a proxy from bytecode,
storage, or logs, or when reasoning about an upgrade path.

---

## What "proxy" means in EVM

A proxy is any contract whose runtime behavior is **dispatched to another
contract's code via `DELEGATECALL`**. `DELEGATECALL` executes the callee's
bytecode in the caller's storage / msg.sender / msg.value context. The callee
is the "implementation" (also: logic, master copy, facet, target, module).
Variants differ in:

1. **Where the implementation address lives** (storage slot? immutable? code?
   computed?).
2. **Who can change it** (admin EOA? governance? immutable?).
3. **How it announces changes** (which events).
4. **What it dispatches** (single impl for all calls? per-selector facet?).

Anything else attached to that core (initializers, admins, beacons, modules,
factories) is variation around those four axes.

---

## Common storage slot constants

All major slot constants follow the pattern `keccak256("<namespace>") - 1` to
avoid collision with the implementation's own storage layout (Solidity's
default packing starts at slot 0 and walks up; random keccak slots cannot
collide unless deliberately attacked).

### EIP-1967 (the most prevalent)

| Slot | Value | Stores |
|---|---|---|
| impl | `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` | implementation address |
| beacon | `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50` | beacon address (BeaconProxy) |
| admin | `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` | admin address (transparent proxy / ProxyAdmin) |
| rollback | `0x4910fdfa16fed3260ed0e7147f7cc6da11a60208b5b9406d12a635614ffd9143` | rollback impl (UUPS safety) |

### EIP-1822 (UUPS, historic)

| Slot | Value | Stores |
|---|---|---|
| proxiable | `0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7` | implementation address (UUPS-original) |

Modern UUPS impls reuse the EIP-1967 impl slot; this slot only matters for
contracts that pre-date the unification.

### Legacy ZeppelinOS (pre-EIP-1967 OpenZeppelin, ~2018-2020)

| Slot | Value | Stores |
|---|---|---|
| impl | `0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3` | implementation address (`keccak256("org.zeppelinos.proxy.implementation")` — no `- 1`) |
| admin | `0x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b` | admin address (`keccak256("org.zeppelinos.proxy.admin")`) |

OpenZeppelin Upgrades / ZeppelinOS proxies deployed before the EIP-1967
unification use these slots. Modern OZ contracts switched to the EIP-1967
layout. Note these slots do **not** subtract 1 from the keccak — that quirk
was introduced by EIP-1967 specifically to avoid Solidity-compiler-emitted
slots (Solidity 0.8+ refuses to emit `keccak256(x) - 1` as a constant).

### EIP-2535 (Diamond)

| Slot | Value | Stores |
|---|---|---|
| diamond storage | `0xc8fcad8db84d3cc18b4c41d551ea0ee66dd599cde068d998e57d5e09332c131c` | start of `DiamondStorage` struct (selector → facet map base) |

(The exact slot is reference-implementation-dependent; many diamonds use
arbitrary namespaced storage instead, see ERC-7201 below.)

### ERC-7201 namespaced storage

Formula: `slot = keccak256(abi.encode(uint256(keccak256(formula_id)) - 1)) & ~bytes32(uint256(0xff))`

Used by OpenZeppelin 5.x upgradeable contracts (replaces `__gap[]` arrays) and
modern diamond implementations. Each struct gets its own random-looking slot;
no bytecode constant matches the impl slot in the traditional sense.

---

## Pattern catalog

### 1. EIP-1167 — Minimal Proxy / Clone

- **Idea**: a 45-byte runtime that immutably `DELEGATECALL`s a hardcoded
  implementation. Cheapest possible proxy; perfect for factory-deployed
  per-user contracts.
- **Bytecode** (45 bytes):
  `0x363d3d373d3d3d363d73<20-byte impl>5af43d82803e903d91602b57fd5bf3`
- **Mutability**: none. Cannot be upgraded.
- **No events** on creation other than what the factory itself emits (no
  upgrade events because it cannot upgrade).
- **Detection**: bytecode pattern match. The impl address is at bytes 10..30.

### 2. EIP-3448 — MetaProxy

- **Idea**: EIP-1167 + appended **immutable metadata bytes**. The proxy is a
  fixed clone but reads constructor-style args from its own code via
  `CODECOPY`. Used when many proxies need the same logic but per-instance
  data (e.g., Yearn V3 vaults, Pendle markets).
- **Bytecode**: minimal-proxy preamble + impl address + metadata bytes +
  trailer length suffix. The convention is that `getMetadata()` reads from the
  trailer.
- **Mutability**: none (immutable impl, immutable args).
- **Detection**: bytecode starts like EIP-1167 but with extra bytes after the
  trailer.

### 3. ClonesWithImmutableArgs (de facto, not a formal EIP)

- **Idea**: clones with **append-to-calldata** immutable args. Each delegatecall
  forwards both the original calldata and the appended immutables, so the
  implementation can read its per-clone parameters via `calldatasize` math.
  Popularized by 0xSplits / Solady. Used by Splits, Liquity V2 troves, etc.
- **Bytecode**: 47–62-byte variant of minimal proxy that appends `n` bytes of
  immutable args to every delegatecall's calldata.
- **Mutability**: none.
- **Detection**: bytecode shape similar to EIP-1167 with a different trailer
  that performs `CALLDATACOPY` + immutable-append logic.

### 4. EIP-1967 Transparent Upgradeable Proxy

- **Idea**: proxy fallback `DELEGATECALL`s the impl at the EIP-1967 impl slot.
  Calls from the admin EOA take the admin-only path (`upgradeTo`,
  `changeAdmin`) and never reach the impl. Calls from anyone else delegatecall
  through.
- **Storage**: EIP-1967 impl + admin slots.
- **Events**:
  - `Upgraded(address indexed implementation)`
    — `topic0 = 0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`
  - `AdminChanged(address previousAdmin, address newAdmin)`
    — `topic0 = 0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f`
- **Upgrade authority**: the admin address in the admin slot. In OZ 5.x the
  admin is itself a `ProxyAdmin` contract owned by an EOA / multisig /
  governance.
- **Selector clash protection**: the proxy's own `upgradeTo` / `admin` /
  `implementation` functions are gated by `if (msg.sender == admin)`. Non-admin
  calls fall through unconditionally, so the impl can safely define functions
  with the same names.

### 5. EIP-1822 + EIP-1967 — UUPS

- **Idea**: upgrade logic lives **in the implementation** (`upgradeTo` /
  `upgradeToAndCall`), not in the proxy. The proxy is a minimal forwarder.
  Cheaper deploys, but a buggy new impl can brick upgrades forever (no
  fall-back if `upgradeTo` is missing).
- **Storage**: EIP-1967 impl slot (modern); EIP-1822 proxiable slot (legacy).
- **Events**: same `Upgraded(address)` as EIP-1967. The proxiable check
  (`proxiableUUID()`) is read off the new impl during upgrade to confirm it's
  upgrade-aware.
- **Detection**: bytecode contains the EIP-1967 impl slot constant; impl
  exposes `upgradeTo(address)` / `upgradeToAndCall(address,bytes)` /
  `proxiableUUID()`.

### 6. Beacon Proxy (OpenZeppelin)

- **Idea**: the proxy stores a **beacon address** (not the impl). On every
  call, it reads `IBeacon(beacon).implementation()` and delegatecalls there.
  Many proxies can share one beacon → upgrading the beacon upgrades the whole
  family atomically.
- **Storage**: EIP-1967 beacon slot on the proxy. The beacon contract holds
  the impl in its own state.
- **Events**:
  - On the proxy: `BeaconUpgraded(address indexed beacon)`
    — `topic0 = 0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e`
    (typically emitted only at deploy time).
  - On the beacon: `Upgraded(address indexed implementation)` — same topic0
    as the proxy `Upgraded` event. Fires on every beacon swap.
- **Detection**: bytecode contains the EIP-1967 beacon slot constant; beacon
  implements `implementation() returns (address)`.

### 7. EIP-2535 — Diamond (Multi-Facet) Proxy

- **Idea**: one proxy dispatches to **many facets**, one per selector. The
  proxy's fallback looks up `selectorToFacet[msg.sig]` and delegatecalls there.
  Allows arbitrarily large contracts past the 24KB EIP-170 limit.
- **Storage**: a `DiamondStorage` struct (selector → facet, facet → selectors,
  facet list). Either at a fixed slot or via ERC-7201 namespace.
- **Loupe** (optional sub-interface, EIP-2535):
  - `facets()` → list of `(facet, selectors[])`
  - `facetFunctionSelectors(address)` → selectors for one facet
  - `facetAddresses()` → all facet addresses
  - `facetAddress(bytes4)` → facet for one selector
- **Events**:
  - `DiamondCut(FacetCut[] _diamondCut, address _init, bytes _calldata)`
    — `topic0 = 0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673`
  - `FacetCut = (address facetAddress, uint8 action, bytes4[] functionSelectors)`
    with `action ∈ {0=Add, 1=Replace, 2=Remove}`.
- **Detection**: bytecode contains diamond storage slot; emits `DiamondCut`.
  Loupe presence is not required.

### 8. EIP-1538 — Transparent Contract Standard (historical)

- **Idea**: Diamond's predecessor. Same selector-to-impl idea but with a
  different event and no loupe spec. Largely superseded by EIP-2535; some
  pre-2020 contracts (Mosendo, some early DAOs) still use it.
- **Events**: `CommitMessage(string)` and a per-function `FunctionUpdate(...)`
  — non-standard signatures across implementations.

### 9. EIP-897 — Legacy DelegateProxy interface

- **Idea**: original (pre-1967) standardization attempt. Proxies expose:
  - `proxyType() returns (uint256)` — `1` = forwarding (immutable), `2` =
    upgradeable.
  - `implementation() returns (address)` — current impl.
- Storage layout is **not** standardized; only the interface is. Many old
  contracts (Augur, early Compound, Aragon AppProxy) implement this.
- **Detection**: bytecode contains the `implementation()` selector
  (`0x5c60da1b`) and/or `proxyType()` (`0x4555d5c9`).

### 10. EIP-7702 — EOA delegation (set-code transactions)

- **Idea**: an EOA can attach a delegation that says "execute as if I were
  code X". A Type-4 transaction carries an authorization list that writes a
  3-byte marker + 20-byte address into the EOA's code: `0xef0100<address>`.
- **Storage**: the EOA's own storage (not the delegate's).
- **Detection**: `eth_getCode(eoa)` returns `0xef0100<addr>`. The delegate is
  the 20 bytes after the prefix. No standard event; the auth tuple is on the
  transaction itself.
- **Mutability**: another Type-4 tx replaces the delegate; passing `addr = 0`
  clears it.

### 11. Gnosis Safe / SafeProxy

- **Idea**: lightweight proxy delegating to a `Singleton` (formerly
  "masterCopy") Safe contract. The singleton holds the multisig + module
  logic. Per-safe state (owners, threshold, modules) lives in the proxy's
  storage.
- **Storage**: singleton address is at **slot 0** (not EIP-1967). Unusual.
- **Functions**:
  - `masterCopy() returns (address)` — current singleton (Safe < v1.3).
  - Newer Safes use `VERSION()` / a fixed singleton per major version.
- **Events**:
  - `ChangedMasterCopy(address)` (old) — `topic0 = 0x99d6b9b67d9b...` (varies)
  - `SafeSetup(...)` at initialization
  - `EnabledModule(address)` / `DisabledModule(address)` for module changes —
    these aren't impl swaps, but they change the call-routing surface in a
    similar way (modules can be called as proxies on behalf of the safe).
- **Detection**: contract name `GnosisSafeProxy` / `SafeProxy`; tiny bytecode
  that delegatecalls to slot-0.

### 12. DSProxy (DappHub)

- **Idea**: user-deployed personal proxy. Owner calls `execute(address target,
  bytes data)` which `DELEGATECALL`s into `target`. Not upgradeable; the
  "implementation" varies per call. Used heavily by MakerDAO frontends,
  InstaDapp v1, Oasis.
- **Detection**: `DSProxyCache` deployed alongside; factory emits
  `Created(address indexed sender, address indexed owner, address proxy, address cache)`.
- **No persistent impl** — each call brings its own delegatecall target via
  calldata.

### 13. InstaDapp DSA (DeFi Smart Account)

- **Idea**: like DSProxy but with a registry of "Connectors" (pre-approved
  delegate targets). `cast(string[] connectors, bytes[] datas, address origin)`
  loops and delegatecalls each connector in order.
- **Events**: `LogCast`, `LogEnableUser`, `LogDisableUser`, `LogSwitchShield`.
- **Detection**: typical pattern is account contracts deployed by InstaIndex
  factory.

### 14. Aragon AppProxy (Kernel-based)

- **Idea**: each Aragon DAO has a `Kernel` (root proxy) that maps `(namespace,
  appId)` → impl address. App proxies query the kernel for their impl on every
  call. Effectively a beacon pattern keyed by `(namespace, appId)` instead of a
  single beacon address.
- **Storage**: kernel address at fixed slot; app id at fixed slot.
- **Events**:
  - On the kernel: `SetApp(bytes32 indexed namespaces, bytes32 indexed appId, address app)`
- **Detection**: bytecode references `getApp(bytes32,bytes32)` (selector
  `0xb6c0d5fc` on the kernel).

### 15. Synthetix `Proxy` / `Proxyable`

- **Idea**: Synthetix-style proxy with a `target` address (their term for
  impl) and explicit two-step swap (`setTarget`).
- **Events**:
  - `TargetUpdated(address newTarget)` — `topic0 = 0x814250a3b8c79fcbe2ead2c131c952a278491c8f4322a79fe84b5040a810373e` (non-EIP-1967, verified via keccak).
- **Storage**: non-standard slots.

### 16. Compound Comptroller / cToken upgrade pattern

- **Idea**: two-step upgrade via `_setPendingImplementation(address)` then the
  pending impl calls `_become(comptroller)` to accept. Used by cTokens and
  Comptroller.
- **Events**:
  - `NewImplementation(address oldImplementation, address newImplementation)`
    — `topic0 = 0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a`
  - `NewPendingImplementation(address oldPending, address newPending)`
- **Storage**: non-standard slots (`implementation`, `pendingImplementation`).

### 17. USDT (Tether) "fallback to upgraded" pattern

- **Idea**: not a true proxy. `TetherToken` stores `address upgradedAddress`
  and `bool deprecated`. When `deprecated == true`, every external function
  forwards (CALL, not DELEGATECALL) to `upgradedAddress`. Once deprecated, the
  original is frozen.
- **Events**: `Deprecate(address newAddress)`.
- **Detection**: `deprecated()` and `upgradedAddress()` selectors;
  `Deprecate(address)` log.

### 18. Aave V2/V3 `InitializableImmutableAdminUpgradeabilityProxy`

- **Idea**: EIP-1967-style proxy with the admin baked in as **immutable** at
  construction. The impl is upgradeable; the admin is not. Aave uses one
  proxy per lending market.
- **Storage**: EIP-1967 impl slot. Admin is in immutables (in code, not
  storage).
- **Events**: standard `Upgraded(address)`.
- **Detection**: bytecode contains the EIP-1967 impl slot constant but no
  admin slot constant.

### 19. Wormhole `ImplementationContract`

- **Idea**: bespoke proxy with `upgrade(bytes encodedVm)` triggered by signed
  guardian VAA. After verification, calls `setImplementation` and emits
  `ContractUpgraded(address indexed oldContract, address indexed newContract)`.
- **Events**:
  - `ContractUpgraded(address,address)` — bespoke topic0.
  - `Initialized(uint8)` from OZ's `Initializable`.
- **Storage**: EIP-1967 impl slot.

### 20. ERC-6900 — Modular Smart Account

- **Idea**: smart-account standard where "plugins" (modules) provide
  validation, execution, and hook logic. Plugins are installed/uninstalled
  similar to Diamond facets but with stricter manifests describing their
  interfaces and dependencies.
- **Events**:
  - `PluginInstalled(address indexed plugin, bytes32 manifestHash, FunctionReference[] dependencies)`
  - `PluginUninstalled(address indexed plugin, bool onUninstallSucceeded)`
- **Detection**: account exposes `installPlugin` / `uninstallPlugin` /
  `getInstalledPlugins`.

### 21. ERC-7579 — Minimal Modular Smart Account

- **Idea**: more minimal alternative to ERC-6900. Modules typed by purpose
  (validator, executor, fallback, hook). Lower-overhead, broader adoption
  among ERC-4337 stacks (ZeroDev Kernel, Biconomy Nexus, Rhinestone).
- **Events**:
  - `ModuleInstalled(uint256 moduleTypeId, address module)`
  - `ModuleUninstalled(uint256 moduleTypeId, address module)`
- **Detection**: account exposes `installModule(uint256,address,bytes)` /
  `isModuleInstalled(uint256,address,bytes)`.

### 22. OpenZeppelin `Initializable` event (any modern proxy)

- **Idea**: not a proxy itself, but a signal. Every OZ-upgradeable impl emits
  `Initialized(uint64 version)` (post-5.x) or `Initialized(uint8 version)`
  (pre-5.x) the first time it's initialized on the proxy. Also fires on
  `reinitializer(N)` upgrades.
- **Use**: a cheap heartbeat that "something proxied just upgraded to version
  N" — useful as a secondary signal to confirm an `Upgraded` event corresponds
  to a real impl swap.

### 23. Chainlink `AggregatorProxy` (price-feed proxy)

- **Idea**: every Chainlink price feed (`ETH/USD`, `BTC/USD`, …) is actually a
  proxy contract that points at the current `AccessControlledOffchainAggregator`.
  When Chainlink rotates aggregators (key rotation, contract upgrade), the
  proxy's `aggregator` slot is swapped via a two-step
  `proposeAggregator(address)` → `confirmAggregator(address)` flow.
- **Storage**: non-standard. `AggregatorProxy` extends `ConfirmedOwner`
  (slots 0-1 = `s_owner`, `s_pendingOwner`), so the `currentPhase` struct
  (`{uint16 id, address aggregator}`, packed) lives at slot 2 and
  `proposedAggregator` at slot 3. Raw-storage reads are fragile across feed
  versions — prefer `proxy.aggregator()` (selector `0x245a7bfc`).
- **Events**: no widely-standardized upgrade event — many feeds emit only the
  data event `AnswerUpdated(int256 current, uint256 roundId, uint256 updatedAt)`.
  The `OwnershipTransferred` event signals the proxy ownership, not the
  aggregator swap. Some feed versions emit `AggregatorConfirmed(address,address)`
  (non-standard topic0).
- **Detection**: call `proxy.aggregator()` (selector `0x245a7bfc`). The result
  is the current backing aggregator. To detect swaps, poll periodically — or
  watch for `OwnershipTransferred` as a weak hint.

### 24. EIP-6551 — Token-Bound Accounts (TBA)

- **Idea**: every ERC-721 token can own a smart contract at a deterministic
  address. The TBA is deployed by the `ERC6551Registry` at
  `0x000000006551c19487814612e58FE06813775758` (same on every chain) via
  `createAccount(impl, salt, chainId, tokenContract, tokenId)`. The TBA is
  typically itself a proxy (EIP-1167 clone) of a TBA implementation
  (TokenBound's `AccountV3`, Cre8ors, etc.).
- **Detection**: registry emits
  `ERC6551AccountCreated(address account, address indexed implementation, bytes32 salt, uint256 chainId, address indexed tokenContract, uint256 indexed tokenId)`.
  Watching this event gives instant TBA discovery.
- **Mutability**: the TBA itself is immutable (1167); ownership follows the NFT.
  Some TBA implementations expose `upgrade(address)` if they're UUPS, in which
  case standard EIP-1967 detection applies.

### 25. OP Stack proxies

OP Stack chains (Optimism, Base, Mode, Mantle, Zora, Lisk, World, etc.) use
three proxy variants depending on contract age:

- **`Proxy.sol`** — modern OP Stack proxy. EIP-1967 storage. Emits the
  standard `Upgraded(address)` and `AdminChanged(address,address)`. The admin
  is managed by an `OptimismPortal` `ProxyAdmin` predeploy at
  `0x4200000000000000000000000000000000000018`.
- **`L1ChugSplashProxy`** — historical proxy with **mode switching**. Has two
  modes: "deployment" (calls go to a code dictionary) and "proxy" (delegatecall
  to the impl). Mode is determined by whether the admin is calling. Used for
  initial bedrock migrations; rarely seen post-2023.
- **`ResolvedDelegateProxy`** — historical. The impl is resolved at runtime
  from `Lib_AddressManager.getAddress(string name)`. A per-proxy `name`
  string is stored at deploy time; on each call, the proxy queries the
  `AddressManager` for the current contract registered under that name.
- **Events**:
  - Modern: standard EIP-1967.
  - `Lib_AddressManager`: `AddressSet(string indexed _name, address _newAddress, address _oldAddress)` — fires when the resolved-delegate impl changes.

### 26. Arbitrum `AdminFallbackProxy`

- **Idea**: EIP-1967 variant with **two impls**: `userImpl` and `adminImpl`.
  Admin calls route to the admin impl (which can also `upgradeTo`); non-admin
  calls route to the user impl. Used by Arbitrum's L1/L2 gateway contracts
  (`L1ERC20Gateway`, `L2ERC20Gateway`, `Inbox`, `Outbox`, etc.).
- **Storage**: two impl slots — the standard EIP-1967 impl slot plus an
  Arbitrum-specific admin-impl slot
  (`keccak256("eip1967.proxy.implementation.secondary") - 1`).
- **Events**: standard `Upgraded(address)` plus a secondary
  `UpgradedSecondary(address)` (signature varies by deploy).
- **Detection**: bytecode contains both 1967 slot constants plus the secondary
  slot constant.

### 27. 0x ZeroEx Exchange Proxy ("Feature Migration")

- **Idea**: Diamond-inspired but pre-dates EIP-2535. The proxy has a
  `selector → impl` map; new features are added via a `Migrate` call that
  delegatecalls a migration script.
- **Events**:
  - `ProxyFunctionUpdated(bytes4 indexed selector, address oldImpl, address newImpl)` —
    fires per-selector change.
  - `Migrated(address caller, address oldImpl, address newImpl)` — fires once
    per migration call.
- **Detection**: the 0x ZeroEx proxy lives at a well-known address on each
  chain (e.g., `0xDef1C0ded9bec7F1a1670819833240f027b25EfF` on Ethereum). Track
  by address.

### 28. OpenSea Wyvern `OwnableDelegateProxy` (historical)

- **Idea**: per-user proxy registered in `WyvernProxyRegistry`. Each user
  deploys their own `OwnableDelegateProxy` that delegates to a shared
  "exchange" impl. Replaced by Seaport (which has no per-user proxy), but
  millions of these exist on mainnet from the 2018-2022 NFT era.
- **Detection**: `WyvernProxyRegistry` at
  `0xa5409ec958c83c3f309868babaca7c86dcb077c1` emits proxy-registration logs.
  Per-instance bytecode is a fixed pattern (the OZ `OwnableDelegateProxy`
  contract code).

### 29. Argent `BaseWallet` / `ArgentAccount`

- **Idea**: pre-AA smart wallet with module system. The wallet delegates
  function calls to authorized modules (recovery, guardians, sessions).
- **Events**:
  - `ModuleAdded(address module)`
  - `ModuleRemoved(address module)`
- **Detection**: deployed by Argent's wallet factories on Ethereum and zkSync.
  Tens of thousands of instances.

### 30. EigenLayer EigenPods (EIP-1167 at scale)

- **Idea**: every EigenLayer beacon-chain staker has a personal `EigenPod`
  deployed by `EigenPodManager.createPod()`. Each pod is an EIP-1167 clone of
  the canonical `EigenPodImplementation`. There are hundreds of thousands of
  these on Ethereum.
- **Detection**: factory event `PodDeployed(address indexed eigenPod, address indexed podOwner)`
  on the `EigenPodManager`. Bytecode is standard EIP-1167.
- **Why it matters**: noteworthy because the volume can dominate any
  per-instance "scan for new clones" approach — use the factory event instead.

### 31. RocketPool minipools (EIP-1167 at scale)

- **Idea**: RocketPool's node operators each deploy minipool contracts via
  `RocketMinipoolFactory.createMinipool()`. Each minipool is an EIP-1167 clone
  of `RocketMinipoolDelegate`. ~50k+ on mainnet.
- **Detection**: `MinipoolCreated(address indexed minipool, address indexed node, uint256 time)`.

### 32. Vyper `create_forwarder_to` / `create_minimal_proxy_to`

- **Idea**: Vyper's native EIP-1167 deploy primitive. The deployer code differs
  slightly from Solidity's `Clones.clone()`, but the **runtime bytecode is
  identical EIP-1167**. Used by Curve LP pool factories, Yearn V3, etc.
- **Detection**: same as EIP-1167 — no special handling needed once deployed.
- **Constructor variant**: `create_forwarder_to(impl, value=, salt=)` emits no
  standard creation event; discover via factory event or `contract_creation`.

### 33. Custom Yul-only proxies

- **Idea**: hand-written assembly proxies that delegate to a stored impl but
  use neither EIP-1167 bytecode nor the EIP-1967 storage slot constant. Used
  by a handful of mature protocols (some Frax, some Convex, some custom AMMs)
  for gas optimization or pre-EIP standardization.
- **Detection**: only reliable via **DELEGATECALL trace analysis**. Group
  `transaction_detail` rows by `(from_a, call_opcode='DELEGATECALL')`: any
  address whose runtime behavior is "DELEGATECALL to a small set of targets"
  is a proxy, regardless of bytecode.
- **Heuristic**: if 90%+ of an address's outbound calls are DELEGATECALL and
  go to ≤ 3 distinct targets, treat it as a proxy. The dominant target is
  the impl.

---

## Trace-based proxy discovery (catch-all)

When neither bytecode patterns nor known events fit, the runtime-level
signal is universal: **the contract DELEGATECALLs somewhere**. Group call
traces by emitter and ratio:

```sql
SELECT from_a AS proxy,
       to_a AS impl,
       COUNT(*) AS calls
FROM transaction_detail
WHERE call_opcode = 'DELEGATECALL'
  AND block_number > <recent>
GROUP BY from_a, to_a;
```

This catches:

- Yul-only and other custom proxies that no static scan can detect.
- Proxies whose impl is computed dynamically (e.g., Aragon AppProxy querying
  the kernel — the resolved target shows up as the DELEGATECALL `to_a`).
- ERC-1167 clones whose factory event you missed.
- Any pattern not yet known — useful as a backfill / safety net.

Tradeoffs:

- Will pick up `DSProxy.execute()` calls (one delegatecall per call, target
  varies) — filter by "dominant target ≥ 80% of delegatecalls" to reject
  these.
- Will pick up Diamond facets — but the impl will look like a different
  facet on every call. Filter by "single dominant target" too.
- Heavier than slot/event-driven scan, so run periodically rather than per
  block.

---

### 34. SELFDESTRUCT-redeploy pattern (historical / mostly dead)

- **Idea**: pre-Cancun, a contract could `SELFDESTRUCT` and CREATE2 redeploy
  to the same address with new bytecode. EIP-6780 (Cancun, Mar 2024) restricts
  SELFDESTRUCT to only delete state when called in the same tx as creation —
  so this pattern no longer works for existing contracts.
- **Where you'll still see it**: pre-Cancun on-chain history, and on chains
  that haven't shipped EIP-6780.

### 35. Factory-clone discovery (any pattern)

- **Idea**: many proxies are created in bulk by a single factory contract
  (Uniswap V2 pairs, Yearn vaults, Safe accounts, Compound markets, EigenPods,
  RocketPool minipools, TBAs). The factory typically emits a
  `PairCreated`/`VaultDeployed`/`ProxyCreation`/`AccountCreated` log carrying
  the new proxy address — easier to discover proxies via factory logs than via
  bytecode scans. For very high-volume families (EigenPods, RocketPool
  minipools, TBAs) the factory-event path is the only one that scales.

---

## Detection cheatsheet

| Signal | Implies |
|---|---|
| Bytecode = exact 45 bytes starting `0x363d3d37…` | EIP-1167 clone |
| Bytecode starts like EIP-1167 + extra trailer bytes | EIP-3448 / ClonesWithImmutableArgs |
| `eth_getCode` returns `0xef0100…` | EIP-7702 delegated EOA |
| Storage slot `0x3608…` non-zero | EIP-1967 / UUPS / transparent / Aave / OP Stack `Proxy` |
| Storage slot `0xa3f0…` non-zero | Beacon proxy (slot value is the beacon) |
| Storage slot `0xc8fc…` non-zero | EIP-2535 Diamond |
| Storage slot `0xc5f1…` non-zero | EIP-1822 (legacy UUPS) |
| Two impl slots (1967 + secondary) | Arbitrum `AdminFallbackProxy` |
| `Upgraded(address)` event | EIP-1967 / UUPS / transparent / Beacon (on beacon contract) |
| `BeaconUpgraded(address)` event | Beacon proxy (initial wiring) |
| `AdminChanged(address,address)` event | Transparent proxy admin swap |
| `DiamondCut(...)` event | EIP-2535 Diamond facet mutation |
| `ProxyFunctionUpdated(bytes4,...)` event | 0x ZeroEx Feature migration |
| `TargetUpdated(address)` event | Synthetix Proxyable |
| `NewImplementation(address,address)` event | Compound-style two-step upgrade |
| `Deprecate(address)` event | USDT fallback-to-upgraded |
| `ContractUpgraded(address,address)` event | Wormhole impl swap |
| `AddressSet(string,address,address)` event | OP Stack `AddressManager` / `ResolvedDelegateProxy` |
| `ERC6551AccountCreated(...)` event | EIP-6551 TBA deployment |
| `PluginInstalled / PluginUninstalled` | ERC-6900 modular account |
| `ModuleInstalled / ModuleUninstalled` | ERC-7579 modular account |
| `ModuleAdded / ModuleRemoved` (Argent flavor) | Argent wallet |
| `Initialized(uint64)` event | OZ Initializable — secondary upgrade signal |
| `SafeSetup` / `ChangedMasterCopy` | Gnosis Safe family |
| `SetApp(bytes32,bytes32,address)` | Aragon Kernel app registration |
| `PodDeployed(...)` / `MinipoolCreated(...)` | EigenPod / RocketPool minipool (mass EIP-1167) |
| Tiny bytecode + delegatecalls to slot-0 | Gnosis Safe / SafeProxy |
| `proxy.aggregator()` returns address | Chainlink `AggregatorProxy` (price feed) |
| `implementation()` returns address, no upgrade slot | EIP-897 legacy / DSProxy / custom |
| Address mostly DELEGATECALLs to a single target | Custom Yul-only proxy (trace-discovered) |

---

## How to resolve a proxy's current impl

1. **EIP-1967**: `eth_getStorageAt(proxy, 0x3608…)` → bottom 20 bytes are the
   impl. Cheapest path; works for ~70%+ of upgradeable contracts.
2. **Beacon**: `eth_getStorageAt(proxy, 0xa3f0…)` → bottom 20 bytes are the
   beacon. Then `IBeacon(beacon).implementation()` → impl.
3. **Diamond**: per-selector. `IDiamondLoupe(proxy).facetAddress(selector)`.
   For the full map, `facets()` (returns the full `(facet, selectors[])`
   list).
4. **EIP-1822**: `eth_getStorageAt(proxy, 0xc5f1…)`.
5. **EIP-897**: `proxy.implementation()` via eth_call.
6. **Safe**: `eth_getStorageAt(proxy, 0)` or `proxy.masterCopy()`.
7. **EIP-7702 EOA**: bytes 3..23 of `eth_getCode(eoa)`.
8. **Chainlink `AggregatorProxy`**: `proxy.aggregator()` (selector `0x245a7bfc`).
9. **OP Stack `ResolvedDelegateProxy`**: read the proxy's stored `name`, then
   `AddressManager.getAddress(name)`.
10. **Arbitrum `AdminFallbackProxy`**: read both `0x3608…` (user impl) and the
    Arbitrum secondary slot (admin impl). The "current impl" depends on who's
    calling.
11. **Custom / Yul-only**: read source / decompile. As a fallback, run
    `debug_traceCall` on a known function and check the `to` of the first
    `DELEGATECALL`, or query the runtime trace table for the dominant
    DELEGATECALL target from this address.

---

## Things that are easy to get wrong

- **Beacon slot stores the beacon, not the impl.** Many trackers record the
  slot value as the implementation; that's wrong. The real impl is one extra
  hop away on the beacon contract, and the beacon — not the proxy — is what
  emits future `Upgraded` events.
- **`Upgraded(address)` topic0 is the same on proxy and beacon.** When you see
  this event, you have to know whether the emitter is a proxy or a beacon to
  know what to update.
- **UUPS rollback slot can briefly hold the old impl during upgrades.** Don't
  treat it as the live impl.
- **Diamonds without loupe exist.** Don't assume `facets()` is callable. Fall
  back to applying `DiamondCut` deltas, or reading the diamond's facet-map
  storage directly if the layout is known.
- **`Upgraded(address)` can be emitted by non-proxies.** Always verify by
  reading the EIP-1967 impl slot at the event's block — some contracts just
  reuse the event signature.
- **EIP-1167 clones cannot upgrade**, so seeing one with a stored
  "implementation" record means that record is permanent — never expect an
  upgrade event.
- **EIP-7702 delegates aren't visible in the standard bytecode scan.** The
  EOA's code is the 23-byte `0xef0100<addr>` blob, not anything resembling a
  typical proxy.
- **Safe stores singleton at slot 0**, not at any EIP-1967 slot. Easy to miss
  with bytecode-constant scans.
- **ERC-7201 namespaced storage** means modern proxies/diamonds may not
  contain *any* of the well-known slot constants in their bytecode — their
  storage layout is computed at compile time from a string namespace.
- **Chainlink feed "impl" rotates silently.** Aggregator swaps don't emit a
  widely-standardized event — polling `proxy.aggregator()` is the only
  reliable signal for most feeds.
- **OP Stack `ResolvedDelegateProxy` impl can change without the proxy
  emitting anything.** The signal lives on the `AddressManager` contract,
  not on the proxy itself.
- **Arbitrum `AdminFallbackProxy` has two impls.** Don't pick one — record
  both, and resolve at query time based on caller-context.
- **Mass-deployed clones (EigenPods, minipools, TBAs) will dominate any
  per-instance scan.** Use factory events, not bytecode scans, for these
  families.
- **DSProxy and InstaDapp DSA don't have a "current impl".** Their target
  varies per call. Treat them as a separate category, not as upgradeable
  proxies.
- **Aragon AppProxy resolves impl per call via the kernel.** Read the kernel,
  not the proxy. Two proxies pointing at the same `(namespace, appId)` share
  one impl.

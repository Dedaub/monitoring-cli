# Train Protocol — Topics, Selectors, Addresses (v3: Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Robinhood; legacy HTLC: Ethereum + Base + Arbitrum + Optimism; NOT Avalanche)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the official `TrainProtocol/contracts` repository (`chains/evm/solidity/src/Train.sol`, `chains/evm/solidity/DEPLOYMENTS.md`), the official docs repository (`TrainProtocol/docs`, `deployments.mdx`), and the Sourcify-verified sources of the v3 `Train` (Ethereum, solc 0.8.34) and of the legacy `Train` contracts (Ethereum, Base, Arbitrum; solc 0.8.23).
**Scope:** the two generations of Train's EVM HTLC contract: **v3** (current, one CreateX address on every chain, events `UserLocked` / `SolverLocked` / `…Redeemed` / `…Refunded`) and the **legacy native-ETH HTLC** of 2025 (events `TokenCommitted` / `TokenLocked` / `TokenLockAdded` / `TokenRedeemed` / `TokenRefunded`). Topics and selectors are chain-agnostic. Addresses are network-specific.

Train is a trust-minimized intent bridge built on hashed time-locked contracts (HTLC). The user locks funds on the source chain; a solver locks funds for the user on the destination chain under the **same hashlock** (`sha256(secret)`, not keccak). Revealing the secret on the destination pays the user, and the same revealed secret then lets the solver take the user's lock on the source. If the secret is never revealed, both sides refund after their timelocks.

**The link key is the hashlock.** In v3 it is `topic1` of every event on both chains. In the legacy contract the key is the user-chosen `Id` (`topic1` on both chains), and the hashlock and the secret are in the data. The secret appears in the redeem events, so both redeems of one swap carry the same secret.

v3 is **immutable and permissionless**: no owner, no proxy, no pause. It was deployed on 2026-07-30/31. In the windows measured below it had **no activity** on any chain.

---

## 0. Contract families & flow

| Generation | Contract | Chains | Assets | Status |
|-----------|----------|--------|--------|--------|
| **v3** (current) | `Train` `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | ETH, Base, ARB, OP, POLY, BNB, Robinhood (+ Starknet, Fuel, Tempo off-target) | native ETH (`token = 0x0`) and any ERC-20 | Immutable, no events yet |
| v3 helpers | `TrainRouter`, `ConstantPayoutCurve` | testnets only | — | Not deployed on mainnets (locks use `payoutCurve = 0x0`) |
| **Legacy HTLC** (2025) | `Train` (native ETH only) | ETH `0x7E6f983f93fd12114DaFE0C69d1e55023EE0abCB`, Base `0xAE90b87324DA77113075E149455C53a88F6a01fb`, ARB and OP `0x126Fc543AA75D1D8511390aEb0a5E49Ad8a245BC` | native ETH only | Immutable; last activity seen in 2026 was refunds |

**v3 flow (one swap, source S → destination D):**

1. S: user `userLock(params, dst, userData, solverData)` → funds escrowed in `Train` (`msg.value` or ERC-20 `Transfer(user → Train)`) → `UserLocked(hashlock, sender = user, recipient = solver, …, dstChain, dstAddress, dstAmount, dstToken, …)`.
2. D: solver `solverLock(params, dst, data)` → solver funds escrowed → `SolverLocked(hashlock, sender = solver, recipient = user, …)`.
3. D: anyone with the secret calls `redeemSolver(hashlock, solver, secret)` → payout to the user (native or ERC-20 `Transfer(Train → user)`) → `SolverRedeemed(hashlock, solver, redeemer, secret, payout, excess, rewardTo, reward)`. **This is the destination payout.**
4. S: `redeemUser(hashlock, secret)` → the user's escrow goes to the solver → `UserRedeemed(hashlock, redeemer, secret, payout, excess)`. **This is the solver settlement on the source.**
5. Refunds: `refundUser(hashlock)` → `UserRefunded` (to `refundTo`; the recipient can refund at any time, others after the timelock). `refundSolver(hashlock, solver)` → `SolverRefunded` after the timelock.

**Legacy flow:** S: user `commit(...)` with `msg.value` → `TokenCommitted(Id, …, sender = user, srcReceiver = solver, amount, timelock)`. D: solver `lock(Id, hashlock, reward, …)` with `msg.value` → `TokenLocked(Id, hashlock, …, sender = solver, srcReceiver = user, …)`. S: user `addLock` / `addLockSig` → `TokenLockAdded(Id, hashlock, timelock)`. D then S: `redeem(Id, secret)` → `TokenRedeemed(Id, redeemAddress, secret, hashlock)`, native ETH to `srcReceiver`. Refund: `refund(Id)` → `TokenRefunded(Id)`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 v3 `Train`

| topic0 | Event |
|--------|-------|
| `0xdfe05ae9bd15ce03de0e90eed9af6c6236334156b2e881541a002e834b5d1aec` | `UserLocked(bytes32 indexed hashlock, address indexed sender, address indexed recipient, string srcChain, address token, uint256 amount, uint48 timelock, address payoutCurve, string dstChain, string dstAddress, uint256 dstAmount, string dstToken, uint256 rewardAmount, string rewardToken, string rewardRecipient, uint48 rewardTimelockDelta, uint48 quoteExpiry, bytes userData, bytes solverData)` |
| `0x998c258d5b8240adc4f2622f59a44f010a931c7b9a81e000a45cc958d9f576fc` | `SolverLocked(bytes32 indexed hashlock, address indexed sender, address indexed recipient, string srcChain, address token, uint256 amount, uint256 reward, address rewardToken, address rewardRecipient, uint48 timelock, uint48 rewardTimelock, address payoutCurve, string dstChain, string dstAddress, uint256 dstAmount, string dstToken, bytes data)` |
| `0xd7c5c3b4e95bd2bfba9028936094242e86e7bc13eb69e6e6def7d1764493efdb` | `SolverRedeemed(bytes32 indexed hashlock, address indexed solver, address redeemer, uint256 secret, uint256 payout, uint256 excess, address rewardTo, uint256 reward)` |
| `0x082f4ca370b708ef8fd80a3abd8ee11268a320651b8fc07f9c3276f76bd20477` | `UserRedeemed(bytes32 indexed hashlock, address redeemer, uint256 secret, uint256 payout, uint256 excess)` |
| `0xe9f985edb090d17cd6c46958be5e76611b58bfa3c82977f29971d50a51747a3d` | `UserRefunded(bytes32 indexed hashlock, address refundTo, uint256 amount)` |
| `0xffd56cae09d1117b2c3e9bc79e51ad41b728e462b300e664c5eb442cff453b46` | `SolverRefunded(bytes32 indexed hashlock, address indexed solver, address refundTo, uint256 amount, uint256 reward)` |

Side: `UserLocked` = source deposit. `SolverLocked` = destination escrow by the solver (funds not yet with the user). `SolverRedeemed` = destination payout to the user. `UserRedeemed` = source settlement to the solver. `UserRefunded` / `SolverRefunded` = refunds. `amount` fields are the measured received amounts (fee-on-transfer safe). `dstChain`, `dstAddress`, `dstAmount`, `dstToken` are strings and numbers logged only (not enforced on chain).

### 1.2 Legacy HTLC `Train` (native ETH)

| topic0 | Event |
|--------|-------|
| `0x48d52ce986069817751aa9893c41f6743eef33f5468ba8d638818a793fec500e` | `TokenCommitted(bytes32 indexed Id, string[] hopChains, string[] hopAssets, string[] hopAddresses, string dstChain, string dstAddress, string dstAsset, address indexed sender, address indexed srcReceiver, string srcAsset, uint256 amount, uint48 timelock)` |
| `0x4ceab1c2914b95780a2f8f611de30f855494a303ba92b618f434814a617637c7` | `TokenLockAdded(bytes32 indexed Id, bytes32 hashlock, uint48 timelock)` |
| `0xd9bb64008dc2709fe211e8b5bbcf1671389cc4f5a4ffd295891f17c759a1817a` | `TokenLocked(bytes32 indexed Id, bytes32 hashlock, string dstChain, string dstAddress, string dstAsset, address indexed sender, address indexed srcReceiver, string srcAsset, uint256 amount, uint256 reward, uint48 rewardTimelock, uint48 timelock)` |
| `0x7cbd5a76f728157ea921886950b9fb8dbf8f7c21b4d81b7ad97dd405e07a77a3` | `TokenRedeemed(bytes32 indexed Id, address redeemAddress, uint256 secret, bytes32 hashlock)` |
| `0x92b8d387b3b4732fb701784c5e553091c36997ec127e0865a7c990bc62cc7382` | `TokenRefunded(bytes32 indexed Id)` |

Side: `TokenCommitted` = source deposit (no hashlock yet). `TokenLocked` = destination solver escrow. `TokenLockAdded` = status only (adds the hashlock to the source commit). `TokenRedeemed` = payout on the chain where it is emitted (to `srcReceiver`). `TokenRefunded` = refund to the locker.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 v3 `Train`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2bc6673c` | `userLock((bytes32 hashlock, uint256 amount, uint256 rewardAmount, uint48 timelockDelta, uint48 rewardTimelockDelta, uint48 quoteExpiry, address recipient, address refundTo, address token, address payoutCurve, bytes payoutCurveData, string rewardToken, string rewardRecipient, string srcChain) params, (string dstChain, string dstAddress, uint256 dstAmount, string dstToken) dst, bytes userData, bytes solverData)` | Payable. Source deposit. Emits `UserLocked`. |
| `0xc672f103` | `userLockFor(address user, (bytes32 hashlock, uint256 amount, uint256 rewardAmount, uint48 timelockDelta, uint48 rewardTimelockDelta, uint48 quoteExpiry, address recipient, address refundTo, address token, address payoutCurve, bytes payoutCurveData, string rewardToken, string rewardRecipient, string srcChain) params, (string dstChain, string dstAddress, uint256 dstAmount, string dstToken) dst, bytes userData, bytes solverData)` | ERC-20 only. Caller funds the lock for `user` (gasless router path). Emits `UserLocked` with `sender = user`. |
| `0xebfd147d` | `solverLock((bytes32 hashlock, uint256 amount, uint256 reward, uint48 timelockDelta, uint48 rewardTimelockDelta, address recipient, address rewardRecipient, address refundTo, address token, address rewardToken, address payoutCurve, bytes payoutCurveData, string srcChain) params, (string dstChain, string dstAddress, uint256 dstAmount, string dstToken) dst, bytes data)` | Payable. One lock per `(hashlock, solver)`. Emits `SolverLocked`. |
| `0x51c1ffe4` | `redeemSolver(bytes32 hashlock, address solver, uint256 secret)` | Permissionless. Pays the solver lock's recipient (the user). Emits `SolverRedeemed`. |
| `0x22b4ea84` | `redeemUser(bytes32 hashlock, uint256 secret)` | Permissionless. Pays the user lock's recipient (the solver). Emits `UserRedeemed`. |
| `0x7f5eedae` | `refundUser(bytes32 hashlock)` | Emits `UserRefunded`. |
| `0x1feb2dab` | `refundSolver(bytes32 hashlock, address solver)` | After the timelock. Emits `SolverRefunded`. |
| `0x36c24998` | `getUserLock(bytes32 hashlock)` | View. |
| `0x93ba49fc` | `getSolverLock(bytes32 hashlock, address solver)` | View. |

### 2.2 Legacy HTLC `Train`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf30ce07a` | `commit(string[] hopChains, string[] hopAssets, string[] hopAddresses, string dstChain, string dstAsset, string dstAddress, string srcAsset, bytes32 Id, address srcReceiver, uint48 timelock)` | Payable. Source deposit. Emits `TokenCommitted`. |
| `0xdaebb789` | `lock(bytes32 Id, bytes32 hashlock, uint256 reward, uint48 rewardTimelock, uint48 timelock, address srcReceiver, string srcAsset, string dstChain, string dstAddress, string dstAsset)` | Payable. Solver escrow. Emits `TokenLocked`. |
| `0xa9e0c1a5` | `addLock(bytes32 Id, bytes32 hashlock, uint48 timelock)` | Original sender only. Emits `TokenLockAdded`. |
| `0x35be7d8b` | `addLockSig((bytes32 Id, bytes32 hashlock, uint48 timelock) message, bytes32 r, bytes32 s, uint8 v)` | EIP-712 signed variant. Emits `TokenLockAdded`. |
| `0x673da154` | `redeem(bytes32 Id, uint256 secret)` | Emits `TokenRedeemed`. Native ETH to `srcReceiver`. |
| `0x7249fbb6` | `refund(bytes32 Id)` | After the timelock. Emits `TokenRefunded`. |
| `0x8928777e` | `getHTLCDetails(bytes32 Id)` | View. |

---

## 3. Addresses — v3 `Train` (one address, CreateX)

`0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8`, deployed with CreateX `0xba5Ed099633D3B313e4D5F7bdc1305d3c28ba5Ed` and salt `keccak256('train.protocol.v3')` (`0x6ea79710b625701a4e948a261916507183bbcdc2bf17c7d633ac10d102f42125`). Existence-checked with `eth_getCode` on 2026-09-29:

| Chain | ID | v3 `Train` | Code |
|-------|----|-----------|------|
| Ethereum | 1 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | 15108 B (deploy tx `0xe64c8d9997ab40bb8def607c2a4540066b5228503b06ab826f823866985d4d60`, block 25,648,174) |
| Base | 8453 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | 15108 B |
| Arbitrum One | 42161 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | 15108 B |
| Optimism | 10 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | 15108 B |
| Polygon PoS | 137 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | 15108 B |
| BNB Smart Chain | 56 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | 15108 B |
| Robinhood Chain | 4663 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | 15108 B (deploy tx `0x4e2f6a26ec2a3013f521a3567b3588d293b0099375d79b93ed708428058d1a95`) |
| Avalanche C-Chain | 43114 | — | `0x`: not deployed, not in the official list |

The runtime code is byte-identical on the seven chains (no immutables). The official deployment file reserves `TrainRouter` `0xF406475230bE1A65d06bd87A2724F78F4b6A2928` and `ConstantPayoutCurve` `0xf5522F01B44D95f3A8d8be5d78F3eee91d26543C` and states they are not deployed on mainnets (not existence-checked here). Off-target v3: Starknet `0x0397630513a04161f0f73bc1aaf76c6e10f85d8b17b42d00d11e8767a1cf5255` (zero-padded felt), Fuel `0x445464bf4d8f2ad1cdffefa8345438f6769c44fc4aedf0eb9c2e34f5756f5750`, Tempo `0xCb74407724c463EAA9bC661818364b532F8B5Cb5`.

## 4. Addresses — legacy HTLC `Train`

| Chain | ID | Legacy `Train` | Code | Notes |
|-------|----|----------------|------|-------|
| Ethereum | 1 | `0x7E6f983f93fd12114DaFE0C69d1e55023EE0abCB` | 6472 B | Sourcify-verified, block 21,886,781 |
| Base | 8453 | `0xAE90b87324DA77113075E149455C53a88F6a01fb` | 6472 B | Sourcify-verified, block 26,627,704 |
| Arbitrum One | 42161 | `0x126Fc543AA75D1D8511390aEb0a5E49Ad8a245BC` | 6472 B | Sourcify-verified, block 307,992,760 |
| Optimism | 10 | `0x126Fc543AA75D1D8511390aEb0a5E49Ad8a245BC` | 6472 B | listed by a third-party bridge indexer; same size as the verified copies |
| Polygon, BNB, Avalanche, Robinhood | — | — | — | no legacy deployment found (`0x` at the three addresses, except the decoys below) |

All legacy contracts were deployed by `0x0D424e1a805C4c5fe8a276E986031860421141D1`. **Decoys:** `0xAE90b87324DA77113075E149455C53a88F6a01fb` holds unrelated code on Ethereum (428 B), Arbitrum (429 B) and BNB (7757 B).

---

## 5. Cross-chain summary

| Chain | ID | v3 `Train` | Legacy HTLC |
|-------|----|-----------|-------------|
| Ethereum | 1 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | `0x7E6f983f93fd12114DaFE0C69d1e55023EE0abCB` |
| Base | 8453 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | `0xAE90b87324DA77113075E149455C53a88F6a01fb` |
| Arbitrum One | 42161 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | `0x126Fc543AA75D1D8511390aEb0a5E49Ad8a245BC` |
| Optimism | 10 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | `0x126Fc543AA75D1D8511390aEb0a5E49Ad8a245BC` |
| Polygon PoS | 137 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | — |
| BNB Smart Chain | 56 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | — |
| Avalanche C-Chain | 43114 | — | — |
| Robinhood Chain | 4663 | `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8` | — |

Off-target legacy deployments named by a third-party indexer: zkSync Era `0xB4863f53332C89078575320C01E270032f71e486`, Linea `0x320818EEFCF46ED1ec722f3bbC5B463EA1F5B619` (not checked).

---

## 6. Proxies

None. v3 `Train` is a plain `ReentrancyGuardTransient` contract with no owner, no admin and no pause (source and 15108-byte full runtime, no EIP-1967 implementation). The legacy contracts are plain `EIP712` + `ReentrancyGuard` contracts with no owner. There is no `Upgraded` or admin event to watch. Redeploys use a new CreateX salt and a new address (v1 and v2 were testnet-only releases at other addresses).

---

## 7. Detection invariants & gotchas

1. **Link key: the hashlock (v3) or the `Id` (legacy), `topic1` on both chains.** The hashlock is `sha256(secret)`: compute it with SHA-256, not keccak, when you check a revealed secret.
2. **The secret is public after the first redeem.** `SolverRedeemed.secret` on the destination and `UserRedeemed.secret` on the source are equal for one swap: a second, exact join key.
3. **Who gets paid.** In `UserLocked` the `recipient` is the solver; in `SolverLocked` the `recipient` is the user. The user's payout is `SolverRedeemed` on the destination, not `UserRedeemed`.
4. **`redeemer` is not the payee.** Anyone holding the secret can redeem. Funds always go to the lock's `recipient`; `excess` goes to `refundTo`; the solver reward goes to `rewardTo`.
5. **Native ETH has no ERC-20 row.** v3 native locks use `msg.value` and pay out with a 10,000-gas native call. The legacy contract is native-ETH only.
6. **Destination fields are free-form strings.** `dstChain`, `dstAddress`, `dstToken` are logged only and are not validated on chain.
7. **Only `(hashlock, solver)` is unique in v3.** Several solvers can lock the same hashlock on the destination. Match the `SolverRedeemed.solver` to the lock you follow.
8. **No activity yet on v3.** All Train topics were 0 in the pinned window on all eight chains, and the explorer log API returned no v3 log at all on Ethereum, Base, Arbitrum and Polygon. A first `UserLocked` on mainnet is itself notable.
9. **Large-transfer trigger:** `UserLocked.amount` and `SolverLocked.amount` (with `token`), and `SolverRedeemed.payout`. There are no admin triggers.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== v3 topics (chain-agnostic) =====
TOPIC_TRAIN_USER_LOCKED          = '\xdfe05ae9bd15ce03de0e90eed9af6c6236334156b2e881541a002e834b5d1aec'
TOPIC_TRAIN_SOLVER_LOCKED        = '\x998c258d5b8240adc4f2622f59a44f010a931c7b9a81e000a45cc958d9f576fc'
TOPIC_TRAIN_SOLVER_REDEEMED      = '\xd7c5c3b4e95bd2bfba9028936094242e86e7bc13eb69e6e6def7d1764493efdb'
TOPIC_TRAIN_USER_REDEEMED        = '\x082f4ca370b708ef8fd80a3abd8ee11268a320651b8fc07f9c3276f76bd20477'
TOPIC_TRAIN_USER_REFUNDED        = '\xe9f985edb090d17cd6c46958be5e76611b58bfa3c82977f29971d50a51747a3d'
TOPIC_TRAIN_SOLVER_REFUNDED      = '\xffd56cae09d1117b2c3e9bc79e51ad41b728e462b300e664c5eb442cff453b46'
-- ===== legacy topics =====
TOPIC_TRAIN_TOKEN_COMMITTED      = '\x48d52ce986069817751aa9893c41f6743eef33f5468ba8d638818a793fec500e'
TOPIC_TRAIN_TOKEN_LOCK_ADDED     = '\x4ceab1c2914b95780a2f8f611de30f855494a303ba92b618f434814a617637c7'
TOPIC_TRAIN_TOKEN_LOCKED         = '\xd9bb64008dc2709fe211e8b5bbcf1671389cc4f5a4ffd295891f17c759a1817a'
TOPIC_TRAIN_TOKEN_REDEEMED       = '\x7cbd5a76f728157ea921886950b9fb8dbf8f7c21b4d81b7ad97dd405e07a77a3'
TOPIC_TRAIN_TOKEN_REFUNDED       = '\x92b8d387b3b4732fb701784c5e553091c36997ec127e0865a7c990bc62cc7382'

-- ===== Selectors =====
SEL_TRAIN_USER_LOCK              = '\x2bc6673c'
SEL_TRAIN_USER_LOCK_FOR          = '\xc672f103'
SEL_TRAIN_SOLVER_LOCK            = '\xebfd147d'
SEL_TRAIN_REDEEM_SOLVER          = '\x51c1ffe4'
SEL_TRAIN_REDEEM_USER            = '\x22b4ea84'
SEL_TRAIN_REFUND_USER            = '\x7f5eedae'
SEL_TRAIN_REFUND_SOLVER          = '\x1feb2dab'
SEL_TRAIN_LEGACY_COMMIT          = '\xf30ce07a'
SEL_TRAIN_LEGACY_LOCK            = '\xdaebb789'
SEL_TRAIN_LEGACY_ADD_LOCK        = '\xa9e0c1a5'
SEL_TRAIN_LEGACY_ADD_LOCK_SIG    = '\x35be7d8b'
SEL_TRAIN_LEGACY_REDEEM          = '\x673da154'
SEL_TRAIN_LEGACY_REFUND          = '\x7249fbb6'

-- ===== v3 Train (same address on seven chains; not on Avalanche) =====
ETH_TRAIN_V3                     = '\x265978c3e2e5db9c3ea665cc40c5925a5fc13ee8'
BASE_TRAIN_V3                    = '\x265978c3e2e5db9c3ea665cc40c5925a5fc13ee8'
ARB_TRAIN_V3                     = '\x265978c3e2e5db9c3ea665cc40c5925a5fc13ee8'
OP_TRAIN_V3                      = '\x265978c3e2e5db9c3ea665cc40c5925a5fc13ee8'
POLY_TRAIN_V3                    = '\x265978c3e2e5db9c3ea665cc40c5925a5fc13ee8'
BNB_TRAIN_V3                     = '\x265978c3e2e5db9c3ea665cc40c5925a5fc13ee8'
RH_TRAIN_V3                      = '\x265978c3e2e5db9c3ea665cc40c5925a5fc13ee8'

-- ===== Legacy HTLC Train =====
ETH_TRAIN_LEGACY                 = '\x7e6f983f93fd12114dafe0c69d1e55023ee0abcb'
BASE_TRAIN_LEGACY                = '\xae90b87324da77113075e149455c53a88f6a01fb'
ARB_TRAIN_LEGACY                 = '\x126fc543aa75d1d8511390aeb0a5e49ad8a245bc'
OP_TRAIN_LEGACY                  = '\x126fc543aa75d1d8511390aeb0a5e49ad8a245bc'
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(sig)` from `chains/evm/solidity/src/Train.sol` of the official repository (identical to the Sourcify-verified v3 `Train` on Ethereum) and from the Sourcify-verified legacy `contracts/Train.sol` (Ethereum, Base, Arbitrum copies have the same ABI).
- **Addresses:** v3 from the official `deployments.mdx` and `DEPLOYMENTS.md` (seven mainnets, deploy transactions). Legacy from Sourcify metadata and a third-party bridge indexer. All existence-checked with `eth_getCode` on the eight chains.
- **Activity:** pinned 12-hour window 2026-09-28 00:00–12:00 UTC, every Train topic counted from every emitter on every chain: 0 on all eight chains (v3 and legacy). Explorer log API (all blocks) at the v3 address: no logs on Ethereum, Base, Arbitrum and Polygon; Optimism and Robinhood could not be read through the API. Legacy Base: the latest logs (from block 45,000,000) are `TokenRefunded`, the last at block 45,598,519. Legacy Ethereum (from block 25,000,000) and legacy Arbitrum (from block 450,000,000): no logs. No main event exists in the measured ranges, so no sample receipt could be read.

Authoritative sources:
- Repository — [TrainProtocol/contracts](https://github.com/TrainProtocol/contracts) (`chains/evm/solidity/src/Train.sol`, `chains/evm/solidity/DEPLOYMENTS.md`) · [TrainProtocol/docs](https://github.com/TrainProtocol/docs) (`deployments.mdx`)
- Verified source — Sourcify v3 `Train` (chain 1, `0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8`); legacy `Train` (chain 1 `0x7E6f983f93fd12114DaFE0C69d1e55023EE0abCB`, chain 8453 `0xAE90b87324DA77113075E149455C53a88F6a01fb`, chain 42161 `0x126Fc543AA75D1D8511390aEb0a5E49Ad8a245BC`)
- Third-party cross-check — [DefiLlama bridges-server Train adapter](https://github.com/DefiLlama/bridges-server/blob/master/src/adapters/train/index.ts)
- Explorers — [Etherscan v3](https://etherscan.io/address/0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8) · [Robinhood Blockscout v3](https://robinhoodchain.blockscout.com/address/0x265978c3e2E5dB9C3Ea665cC40C5925A5fc13Ee8) · [Basescan legacy](https://basescan.org/address/0xAE90b87324DA77113075E149455C53a88F6a01fb)

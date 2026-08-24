# Hop Protocol v1 — Topics, Selectors, Addresses (Ethereum + Optimism + Arbitrum + Polygon + Base; not on BNB/Avalanche)

**Status:** verified against live RPC on every listed chain and the canonical `hop-protocol/contracts` (branch `v1`) + `hop-protocol/hop` SDK address registry on 2026-06-09.
**Scope:** the Hop v1 token bridge — `L1_Bridge` (per token, on Ethereum), `L2_Bridge` + `L2_AmmWrapper` + Saddle `Swap` (per token, on each rollup), the `HopBridgeToken` (hToken) and the LP token. Topics/selectors are **chain-agnostic** (`keccak256` of the canonical signature); addresses are **network-specific and per-token** (every token has its *own* bridge instance). Of the seven requested chains, Hop has bridges on **Ethereum, Optimism, Arbitrum, Polygon, Base**; it is **NOT deployed on BNB Smart Chain or Avalanche C-Chain** (`eth_getCode` = `0x` for every Hop address there).

Hop is a **bonder-based ("fast") bridge** that mints a synthetic **hToken** (e.g. `hUSDC`, `hETH`) on each L2 and swaps it 1:1-ish against the canonical token through a per-token **Saddle (StableSwap) AMM pool**. A user "sends" on the source chain; an off-chain **Bonder** front-runs canonical L2→L1 (or L2→L2) finality by posting a `WithdrawalBonded` against the destination bridge and is later reimbursed when the Merkle **TransferRoot** propagates and is `settle`d. The whole flow is **non-upgradeable**: every `L1_Bridge`, `L2_Bridge`, `L2_AmmWrapper`, Saddle `Swap`, hToken and LP token is a **plain, directly-deployed contract** (EIP-1967 impl slot reads `0x0` — confirmed on ETH/ARB/OP/Base). There are no proxies anywhere in the v1 system, so there is no `Upgraded` event to watch and an impl can never silently change; the only "admin" surface is the governance multisig (`governance()` = `0x22e3f828b3f47dacfacd875d20bd5cc0879c96e7`, identical across every L1 bridge) that can swap the cross-domain messenger wrapper, pause deposits, set the AMM wrapper, and add/remove bonders.

**The single most important indexing fact:** the live production deployment is the **`v1` branch**, whose event signatures differ from the repo's `master`/next-gen branch. In particular `WithdrawalBonded` is **2-field** (`(bytes32,uint256)`, no `bonder`), `TransferSent` (L2) is the **9-field** variant (`...,uint256 amountOutMin,uint256 deadline`, no `rootIndex`/`tokenIndex`/`bonder`), and `TransfersCommitted` is **4-field** (no `bonder`/`rootIndex`). If you compute topics from `master` you will silently miss every real log. All topics below are the v1 forms and were cross-checked against live logs (§9).

---

## 0. Contract families & versions

| Contract | Role | Where | Proxy? |
|----------|------|-------|--------|
| **L1_Bridge** (`L1_ERC20_Bridge` / `L1_ETH_Bridge`) | Canonical lockbox on Ethereum; users `sendToL2`, bonders `bondTransferRoot`/`confirmTransferRoot`; settles roots. **One instance per token.** | Ethereum only | No (direct) |
| **L2_Bridge** (`L2_OptimismBridge`, `L2_ArbitrumBridge`, `L2_PolygonBridge`, …) | Mints/burns hToken; users `send`, bonders `bondWithdrawalAndDistribute`; commits TransferRoots back to L1. **One per token per L2.** | Optimism, Arbitrum, Polygon, Base (Gnosis/Nova/Linea/PolygonZkEvm out of the 7) | No (direct) |
| **L2_AmmWrapper** | Convenience router: swaps canonical↔hToken on the Saddle pool then calls `L2_Bridge.send`. **One per token per L2** (zero-address for HOP-token bridges — no AMM). | same as L2_Bridge | No (direct) |
| **Saddle `Swap`** | StableSwap AMM pool holding {canonical, hToken}; emits `TokenSwap`/`AddLiquidity`/… **One per token per L2.** | same as L2_Bridge | No (direct) |
| **HopBridgeToken** (hToken) | ERC-20 synthetic (`hUSDC`, `hETH`, …); `mint`/`burn` are bridge-only (`onlyOwner`). | each L2 | No |
| **Saddle LP token** (`l2SaddleLpToken`) | ERC-20 LP share of the Saddle pool. | each L2 | No |
| **Bonder** | Off-chain relayer EOA (`0xa6a688F1…`, code len 0). Posts bonds; not a contract. | — | n/a (EOA) |

The HOP-governance-token bridges (HOP, and the HOP token itself `0xc5102fE9…`) ship a `L2_Bridge` **with `l2AmmWrapper = 0x0` and `l2SaddleSwap = 0x0`** — they have no AMM because the hToken *is* the canonical token. Don't expect `TokenSwap`/AmmWrapper events on HOP-token routes.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak on 2026-06-09. The ones marked ✓live were confirmed against real `eth_getLogs` (§9).

### 1.1 L1_Bridge (Ethereum) — emits source-side deposits + root lifecycle

| topic0 | Event |
|--------|-------|
| `0x0a0607688c86ec1775abcdbab7b33a3a35a6c9cde677c9be880150c231cc6b0b` | `TransferSentToL2(uint256 indexed chainId, address indexed recipient, uint256 amount, uint256 amountOutMin, uint256 deadline, address indexed relayer, uint256 relayerFee)` ✓live |
| `0xa57b3e1f3af9eca02201028629700658608222c365064584cfe65d9630ef4f7b` | `TransferRootBonded(bytes32 indexed root, uint256 amount)` |
| `0xfdfb0eefa96935b8a8c0edf528e125dc6f3934fdbbfce31b38967e8ff413dccd` | `TransferRootConfirmed(uint256 indexed originChainId, uint256 indexed destinationChainId, bytes32 indexed rootHash, uint256 totalAmount)` ✓live |
| `0xec2697dcba539a0ac947cdf1f6d0b6314c065429eca8be2435859b10209d4c27` | `TransferBondChallenged(bytes32 indexed transferRootId, bytes32 indexed rootHash, uint256 originalAmount)` |
| `0x4a99228a8a6d774d261be57ab0ed833bb1bae1f22bbbd3d4767b75ad03fdddf7` | `ChallengeResolved(bytes32 indexed transferRootId, bytes32 indexed rootHash, uint256 originalAmount)` |

### 1.2 L2_Bridge (Optimism/Arbitrum/Polygon/Base) — emits destination-side sends + commits

| topic0 | Event |
|--------|-------|
| `0xe35dddd4ea75d7e9b3fe93af4f4e40e778c3da4074c9d93e7c6536f1e803c1eb` | `TransferSent(bytes32 indexed transferId, uint256 indexed chainId, address indexed recipient, uint256 amount, bytes32 transferNonce, uint256 bonderFee, uint256 index, uint256 amountOutMin, uint256 deadline)` ✓live |
| `0xf52ad20d3b4f50d1c40901dfb95a9ce5270b2fc32694e5c668354721cd87aa74` | `TransfersCommitted(uint256 indexed destinationChainId, bytes32 indexed rootHash, uint256 totalAmount, uint256 rootCommittedAt)` |
| `0x320958176930804eb66c2343c7343fc0367dc16249590c0f195783bee199d094` | `TransferFromL1Completed(address indexed recipient, uint256 amount, uint256 amountOutMin, uint256 deadline, address indexed relayer, uint256 relayerFee)` |

### 1.3 Bridge (shared base — emitted by BOTH L1_Bridge and L2_Bridge)

| topic0 | Event |
|--------|-------|
| `0x9475cdbde5fc71fe2ccd413c82878ee54d061b9f74f9e2e1a03ff1178821502c` | `Withdrew(bytes32 indexed transferId, address indexed recipient, uint256 amount, bytes32 transferNonce)` |
| `0x0c3d250c7831051e78aa6a56679e590374c7c424415ffe4aa474491def2fe705` | `WithdrawalBonded(bytes32 indexed transferId, uint256 amount)` ✓live — **v1 2-field form (no `bonder`)** |
| `0x84eb21b24c31b27a3bc67dde4a598aad06db6e9415cd66544492b9616996143c` | `WithdrawalBondSettled(address indexed bonder, bytes32 indexed transferId, bytes32 indexed rootHash)` |
| `0x78e830d08be9d5f957414c84d685c061ecbd8467be98b42ebb64f0118b57d2ff` | `MultipleWithdrawalsSettled(address indexed bonder, bytes32 indexed rootHash, uint256 totalBondsSettled)` ✓live |
| `0xb33d2162aead99dab59e77a7a67ea025b776bf8ca8079e132afdf9b23e03bd42` | `TransferRootSet(bytes32 indexed rootHash, uint256 totalAmount)` ✓live |

### 1.4 Accounting (shared base — bonder stake/registry; on BOTH L1 and L2 bridges)

| topic0 | Event |
|--------|-------|
| `0xebedb8b3c678666e7f36970bc8f57abf6d8fa2e828c0da91ea5b75bf68ed101a` | `Stake(address indexed account, uint256 amount)` ✓live |
| `0x85082129d87b2fe11527cb1b3b7a520aeb5aa6913f88a3d8757fe40d1db02fdd` | `Unstake(address indexed account, uint256 amount)` |
| `0x2cec73b7434d3b91198ad1a618f63e6a0761ce281af5ec9ec76606d948d03e23` | `BonderAdded(address indexed newBonder)` ✓live |
| `0x4234ba611d325b3ba434c4e1b037967b955b1274d4185ee9847b7491111a48ff` | `BonderRemoved(address indexed previousBonder)` |

### 1.5 Saddle `Swap` (per-token AMM pool on each L2)

| topic0 | Event |
|--------|-------|
| `0xc6c1e0630dbe9130cc068028486c0d118ddcea348550819defd5cb8c257f8a38` | `TokenSwap(address indexed buyer, uint256 tokensSold, uint256 tokensBought, uint128 soldId, uint128 boughtId)` |
| `0x189c623b666b1b45b83d7178f39b8c087cb09774317ca2f53c2d3c3726f222a2` | `AddLiquidity(address indexed provider, uint256[] tokenAmounts, uint256[] fees, uint256 invariant, uint256 lpTokenSupply)` |
| `0x88d38ed598fdd809c2bf01ee49cd24b7fdabf379a83d29567952b60324d58cef` | `RemoveLiquidity(address indexed provider, uint256[] tokenAmounts, uint256 lpTokenSupply)` |
| `0x43fb02998f4e03da2e0e6fff53fdbf0c40a9f45f145dc377fc30615d7d7a8a64` | `RemoveLiquidityOne(address indexed provider, uint256 lpTokenAmount, uint256 lpTokenSupply, uint256 boughtId, uint256 tokensBought)` |
| `0x3631c28b1f9dd213e0319fb167b554d76b6c283a41143eb400a0d1adb1af1755` | `RemoveLiquidityImbalance(address indexed provider, uint256[] tokenAmounts, uint256[] fees, uint256 invariant, uint256 lpTokenSupply)` |
| `0xab599d640ca80cde2b09b128a4154a8dfe608cb80f4c9399c8b954b01fd35f38` | `NewAdminFee(uint256 newAdminFee)` |
| `0xd88ea5155021c6f8dafa1a741e173f595cdf77ce7c17d43342131d7f06afdfe5` | `NewSwapFee(uint256 newSwapFee)` |
| `0xd5fe46099fa396290a7f57e36c3c3c8774e2562c18ed5d1dcc0fa75071e03f1d` | `NewWithdrawFee(uint256 newWithdrawFee)` |
| `0xa2b71ec6df949300b59aab36b55e189697b750119dd349fcfa8c0f779e83c254` | `RampA(uint256 oldA, uint256 newA, uint256 initialTime, uint256 futureTime)` |
| `0x46e22fb3709ad289f62ce63d469248536dbc78d82b84a3d7e74ad606dc201938` | `StopRampA(uint256 currentA, uint256 time)` |

### 1.6 ERC-20 (hToken + LP token + canonical token)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — hToken mint = `Transfer(0x0,bonder/recipient,…)`, burn = `Transfer(user,0x0,…)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

**No topic0 collisions inside the Hop set.** The only generic ones are ERC-20 `Transfer`/`Approval` (§1.6). `TransferSent` (L2) and `TransferSentToL2` (L1) are distinct topics — never conflate them. `Withdrew`/`WithdrawalBonded`/`WithdrawalBondSettled`/`TransferRootSet`/`Stake`/`BonderAdded` come from the shared base and therefore fire on **both** the L1 and the L2 bridge of a token — disambiguate by `(chainId, emitter address)`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 L1_Bridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xdeace8f5` | `sendToL2(uint256 chainId, address recipient, uint256 amount, uint256 amountOutMin, uint256 deadline, address relayer, uint256 relayerFee)` | `payable`. User deposit L1→L2. Emits `TransferSentToL2`. |
| `0x8d8798bf` | `bondTransferRoot(bytes32 rootHash, uint256 destinationChainId, uint256 totalAmount)` | Bonder-only. Emits `TransferRootBonded`. |
| `0xef6ebe5e` | `confirmTransferRoot(uint256 originChainId, bytes32 rootHash, uint256 destinationChainId, uint256 totalAmount, uint256 rootCommittedAt)` | Only callable via the L2 messenger wrapper. Emits `TransferRootConfirmed`. |
| `0x1bbe15ea` | `challengeTransferBond(bytes32 rootHash, uint256 originalAmount, uint256 destinationChainId)` | `payable`. Emits `TransferBondChallenged`. |
| `0x81707b80` | `resolveChallenge(bytes32 rootHash, uint256 originalAmount, uint256 destinationChainId)` | Emits `ChallengeResolved`. |
| `0xd4448163` | `setCrossDomainMessengerWrapper(uint256 chainId, address _crossDomainMessengerWrapper)` | governance-only (rewires the messenger). |
| `0x14942024` | `setChainIdDepositsPaused(uint256 chainId, bool isPaused)` | governance-only — **pause/halt signal.** |

### 2.2 L2_Bridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa6bd1b33` | `send(uint256 chainId, address recipient, uint256 amount, uint256 bonderFee, uint256 amountOutMin, uint256 deadline)` | User send L2→{L1,L2}. Burns hToken. Emits `TransferSent`. Usually reached via `L2_AmmWrapper.swapAndSend`, not directly. |
| `0x32b949a2` | `commitTransfers(uint256 destinationChainId)` | Bundles pending transfers into a root → emits `TransfersCommitted`; bonder-gated before min delay. |
| `0xcc29a306` | `distribute(address recipient, uint256 amount, uint256 amountOutMin, uint256 deadline, address relayer, uint256 relayerFee)` | L1→L2 fulfillment (only L1 bridge via messenger). Emits `TransferFromL1Completed`. |
| `0x3d12a85a` | `bondWithdrawalAndDistribute(address recipient, uint256 amount, bytes32 transferNonce, uint256 bonderFee, uint256 amountOutMin, uint256 deadline)` | **The fast-path: bonder fronts a destination L2→L2 transfer.** Emits `WithdrawalBonded` (+ a Saddle `TokenSwap` if AMM-routed). |
| `0xfd31c5ba` | `setTransferRoot(bytes32 rootHash, uint256 totalAmount)` | Only L1 bridge via messenger. Emits `TransferRootSet`. |
| `0x051e7216` | `getNextTransferNonce()` → `bytes32` | view. |
| `0x64c6fdb4` | `setAmmWrapper(address _ammWrapper)` | governance-only. |

### 2.3 Bridge (shared — present on L1 and L2 bridges)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0f7aadb7` | `withdraw(address recipient, uint256 amount, bytes32 transferNonce, uint256 bonderFee, uint256 amountOutMin, uint256 deadline, bytes32 rootHash, uint256 transferRootTotalAmount, uint256 transferIdTreeIndex, bytes32[] siblings, uint256 totalLeaves)` | Permissionless claim with Merkle proof. Emits `Withdrew`. |
| `0x23c452cd` | `bondWithdrawal(address recipient, uint256 amount, bytes32 transferNonce, uint256 bonderFee)` | Bonder-only. Emits `WithdrawalBonded`. |
| `0xc7525dd3` | `settleBondedWithdrawal(address bonder, bytes32 transferId, bytes32 rootHash, uint256 transferRootTotalAmount, uint256 transferIdTreeIndex, bytes32[] siblings, uint256 totalLeaves)` | Emits `WithdrawalBondSettled`. |
| `0xb162717e` | `settleBondedWithdrawals(address bonder, bytes32[] transferIds, uint256 totalAmount)` | Batch settle. Emits `MultipleWithdrawalsSettled`. |
| `0xcbd1642e` | `rescueTransferRoot(bytes32 rootHash, uint256 originalAmount, address recipient)` | governance-only (8-week rescue delay). |
| `0xaf215f94` | `getTransferId(uint256 chainId, address recipient, uint256 amount, bytes32 transferNonce, uint256 bonderFee, uint256 amountOutMin, uint256 deadline)` → `bytes32` | view — the canonical transferId hash (the key everything is indexed by). |
| `0x960a7afa` | `getTransferRootId(bytes32 rootHash, uint256 totalAmount)` → `bytes32` | view. |
| `0x3a7af631` | `isTransferIdSpent(bytes32 transferId)` → `bool` | view. |
| `0x302830ab` | `getBondedWithdrawalAmount(address bonder, bytes32 transferId)` → `uint256` | view. |
| `0x3408e470` | `getChainId()` → `uint256` | view — returns the chain's own id (e.g. 42161). |
| `0x5aa6e675` | `governance()` → `address` | view — the governance multisig. |

### 2.4 L2_AmmWrapper

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xeea0d7b2` | `swapAndSend(uint256 chainId, address recipient, uint256 amount, uint256 bonderFee, uint256 amountOutMin, uint256 deadline, uint256 destinationAmountOutMin, uint256 destinationDeadline)` | `payable`. **The user entrypoint on L2.** Swaps canonical→hToken on Saddle then `L2_Bridge.send`. |
| `0xe5c7a632` | `swap(uint256 chainId, address recipient, uint256 amount, uint256 bonderFee, uint256 amountOutMin, uint256 deadline)` | direct hToken send wrapper. |
| `0x676c5ef6` | `attemptSwap(address recipient, uint256 amount, uint256 amountOutMin, uint256 deadline)` | internal swap helper (also a selector on L2_Bridge). |
| `0xe78cea92` | `bridge()` → `address` | view — the owning L2_Bridge. |
| `0x1ee1bf67` | `l2CanonicalToken()` → `address` | view. |
| `0xfc6e3b3b` | `hToken()` → `address` | view. |
| `0x9cd01605` | `exchangeAddress()` → `address` | view — the Saddle `Swap` pool. |
| `0x28555125` | `l2CanonicalTokenIsEth()` → `bool` | view — `true` ⇒ canonical token is WETH and ETH is handled natively. |

### 2.5 Saddle `Swap` (AMM)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x91695586` | `swap(uint8 tokenIndexFrom, uint8 tokenIndexTo, uint256 dx, uint256 minDy, uint256 deadline)` → `uint256` | Emits `TokenSwap`. **Note `uint8` indices** — distinct from the bridge `send`/AmmWrapper `swap`. |
| `0x4d49e87d` | `addLiquidity(uint256[] amounts, uint256 minToMint, uint256 deadline)` → `uint256` | Emits `AddLiquidity`. |
| `0x31cd52b0` | `removeLiquidity(uint256 amount, uint256[] minAmounts, uint256 deadline)` → `uint256[]` | Emits `RemoveLiquidity`. |
| `0x3e3a1560` | `removeLiquidityOneToken(uint256 tokenAmount, uint8 tokenIndex, uint256 minAmount, uint256 deadline)` → `uint256` | Emits `RemoveLiquidityOne`. |
| `0x84cdd9bc` | `removeLiquidityImbalance(uint256[] amounts, uint256 maxBurnAmount, uint256 deadline)` → `uint256` | Emits `RemoveLiquidityImbalance`. |
| `0xa95b089f` | `calculateSwap(uint8 tokenIndexFrom, uint8 tokenIndexTo, uint256 dx)` → `uint256` | view. |
| `0x82b86600` | `getToken(uint8 index)` → `address` | view — index 0 = canonical, index 1 = hToken. |
| `0x66c0bd24` | `getTokenIndex(address tokenAddress)` → `uint8` | view. |
| `0xe25aa5fa` | `getVirtualPrice()` → `uint256` | view (1e18). |

### 2.6 HopBridgeToken (hToken)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address account, uint256 amount)` | `onlyOwner` (= the L2_Bridge). Emits ERC-20 `Transfer(0x0,…)`. |
| `0x9dc29fac` | `burn(address account, uint256 amount)` | `onlyOwner`. Emits `Transfer(…,0x0)`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. **One L1_Bridge per token** (there is no shared singleton). Each is a non-proxy ~18.4–19.4 KB contract. `governance()` on every one = `0x22e3f828b3f47dacfacd875d20bd5cc0879c96e7`.

| Token (role) | L1_Bridge address | One-liner |
|------|---------|-----------|
| **USDC** | `0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a` | USDC lockbox; emits `TransferSentToL2`. |
| **USDT** | `0x3E4a3a4796d16c0Cd582C382691998f7c06420B6` | |
| **DAI** | `0x3d4Cc8A61c7528Fd86C55cfe061a78dCBA48EDd1` | |
| **ETH** | `0xb8901acB165ed027E32754E0FFe830802919727f` | native-ETH bridge (`L1_ETH_Bridge`). |
| **MATIC** | `0x22B1Cbb8D98a01a3B71D034BB899775A76Eb1cc2` | |
| **HOP** | `0x914f986a44AcB623A277d6Bd17368171FCbe4273` | HOP-token bridge (no AMM on L2). |
| **SNX** | `0x893246FACF345c99e4235E5A7bbEE7404c988b96` | Optimism-only route. |
| **sUSD** | `0x36443fC70E073fe9D50425f82a3eE19feF697d62` | Optimism-only route. |
| **rETH** | `0x87269B23e73305117D0404557bAdc459CEd0dbEc` | Optimism + Arbitrum routes. |
| **MAGIC** | `0xf074540eb83c86211F305E145eB31743E228E57d` | Arbitrum + Nova routes (Nova ∉ the 7). |

Other canonical Ethereum-side addresses: the L1 token contracts themselves are the well-known mainnet tokens (USDC `0xA0b8…eB48`, WETH-as-ETH handled natively, HOP token `0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC`). Each token also has a per-destination **L1 MessengerWrapper** (see §4–§7, the `l1MessengerWrapper` rows) deployed on Ethereum that bridges governance/root messages to a specific L2 — these live on chain 1 but are keyed by destination.

---

## 4. Addresses — Optimism (chain ID 10)

All verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`. L2_Bridge ~14.7 KB, non-proxy. `getChainId()` returns 10. Optimism has the **widest token set** (it was Hop's first L2).

| Token | L2_Bridge | L2_AmmWrapper | Saddle Swap | hToken | LP token |
|-------|-----------|---------------|-------------|--------|----------|
| USDC | `0xa81D244A1814468C734E5b4101F7b9c0c577a8fC` | `0x2ad09850b0CA4c7c1B33f5AcD6cBAbCaB5d6e796` | `0x3c0FFAca566fCcfD9Cc95139FEF6CBA143795963` | `0x25D8039bB044dC227f741a9e381CA4cEAE2E6aE8` | `0x2e17b8193566345a2Dd467183526dEdc42d2d5A8` |
| USDT | `0x46ae9BaB8CEA96610807a275EBD36f8e916b5C61` | `0x7D269D3E0d61A05a0bA976b7DBF8805bF844AF3F` | `0xeC4B41Af04cF917b54AEb6Df58c0f8D78895b5Ef` | `0x2057C8ECB70Afd7Bee667d76B4CD373A325b1a20` | `0xF753A50fc755c6622BBCAa0f59F0522f264F006e` |
| DAI | `0x7191061D5d4C60f598214cC6913502184BAddf18` | `0xb3C68a491608952Cb1257FC9909a537a0173b63B` | `0xF181eD90D6CfaC84B8073FdEA6D34Aa744B41810` | `0x56900d66D74Cb14E3c86895789901C9135c95b16` | `0x22D63A26c730d49e5Eab461E4f5De1D8BdF89C92` |
| ETH | `0x83f6244Bd87662118d96D9a6D44f09dffF14b30E` | `0x86cA30bEF97fB651b8d866D45503684b90cb3312` | `0xaa30D6bba6285d0585722e2440Ff89E23EF68864` | `0xE38faf9040c7F09958c638bBDB977083722c5156` | `0x5C2048094bAaDe483D0b1DA85c3Da6200A88a849` |
| HOP | `0x03D7f750777eC48d39D080b020D83Eb2CB4e3547` | *(none — `0x0`)* | *(none — `0x0`)* | `0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC` | *(none)* |
| SNX | `0x16284c7323c35F4960540583998C98B1CfC581a7` | `0xf11EBB94EC986EA891Aec29cfF151345C83b33Ec` | `0x1990BC6dfe2ef605Bfc08f5A23564dB75642Ad73` | `0x13B7F51BD865410c3AcC4d56083C5B56aB38D203` | `0xe63337211DdE2569C348D9B3A0acb5637CFa8aB3` |
| sUSD | `0x33Fe5bB8DA466dA55a8A32D6ADE2BB104E2C5201` | `0x29Fba7d2A6C95DB162ee09C6250e912D6893DCa6` | `0x8d4063E82A4Db8CdAed46932E1c71e03CA69Bede` | `0x6F03052743CD99ce1b29265E377e320CD24Eb632` | `0xBD08972Cef7C9a5A046C9Ef13C9c3CE13739B8d6` |
| rETH | `0xA0075E8cE43dcB9970cB7709b9526c1232cc39c2` | `0x19B2162CA4C2C6F08C6942bFB846ce5C396aCB75` | `0x9Dd8685463285aD5a94D2c128bda3c5e8a6173c8` | `0x755569159598f3702bdD7DFF6233A317C156d3Dd` | `0x0699BC1Ca03761110929b2B56BcCBeb691fa9ca6` |

Note USDT and ETH/HOP reuse some addresses with Base/Polygon — **always key on `(chainId, address)`** (e.g. `0x46ae9BaB…` = USDT-L2Bridge on OP **and** USDC-L2Bridge on Base; `0x86cA30bE…` = ETH-AmmWrapper on OP **and** MATIC-AmmWrapper on Gnosis).

---

## 5. Addresses — Arbitrum One (chain ID 42161)

All verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`. L2_Bridge ~17.2 KB, non-proxy. `getChainId()` returns 42161 (confirmed via `eth_call`).

| Token | L2_Bridge | L2_AmmWrapper | Saddle Swap | hToken | LP token |
|-------|-----------|---------------|-------------|--------|----------|
| USDC | `0x0e0E3d2C5c292161999474247956EF542caBF8dd` | `0xe22D2beDb3Eca35E6397e0C6D62857094aA26F52` | `0x10541b07d8Ad2647Dc6cD67abd4c03575dade261` | `0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d` | `0xB67c014FA700E69681a673876eb8BAFAA36BFf71` |
| USDT | `0x72209Fe68386b37A40d6bCA04f78356fd342491f` | `0xCB0a4177E0A60247C0ad18Be87f8eDfF6DD30283` | `0x18f7402B673Ba6Fb5EA4B95768aABb8aaD7ef18a` | `0x12e59C59D282D2C00f3166915BED6DC2F5e2B5C7` | `0xCe3B19D820CB8B9ae370E423B0a329c4314335fE` |
| DAI | `0x7aC115536FE3A185100B2c4DE4cb328bf3A58Ba6` | `0xe7F40BF16AB09f4a6906Ac2CAA4094aD2dA48Cc2` | `0xa5A33aB9063395A90CCbEa2D86a62EcCf27B5742` | `0x46ae9BaB8CEA96610807a275EBD36f8e916b5C61` | `0x68f5d998F00bB2460511021741D098c05721d8fF` |
| ETH | `0x3749C4f034022c39ecafFaBA182555d4508caCCC` | `0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417` | `0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97` | `0xDa7c0de432a9346bB6e96aC74e3B61A36d8a77eB` | `0x59745774Ed5EfF903e615F5A2282Cae03484985a` |
| HOP | `0x25FB92E505F752F730cAD0Bd4fa17ecE4A384266` | *(none — `0x0`)* | *(none — `0x0`)* | `0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC` | *(none)* |
| rETH | `0xc315239cFb05F1E130E7E28E603CEa4C014c57f0` | `0x16e08C02e4B78B0a5b3A917FF5FeaeDd349a5a95` | `0x0Ded0d521AC7B0d312871D18EA4FDE79f03Ee7CA` | `0x588Bae9C85a605a7F14E551d144279984469423B` | `0xbBA837dFFB3eCf4638D200F11B8c691eA641AdCb` |
| MAGIC | `0xEa5abf2C909169823d939de377Ef2Bf897A6CE98` | `0x50a3a623d00fd8b8a4F3CbC5aa53D0Bc6FA912DD` | `0xFFe42d3Ba79Ee5Ee74a999CAd0c60EF1153F0b82` | `0xB76e673EBC922b1E8f10303D0d513a9E710f5c4c` | `0x163A9E12787dBFa2836caa549aE02ed67F73e7C2` |

---

## 6. Addresses — Polygon PoS (chain ID 137)

All verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`. L2_Bridge ~17.6 KB, non-proxy.

| Token | L2_Bridge | L2_AmmWrapper | Saddle Swap | hToken | LP token |
|-------|-----------|---------------|-------------|--------|----------|
| USDC (USDC.e) | `0x25D8039bB044dC227f741a9e381CA4cEAE2E6aE8` | `0x76b22b8C1079A44F1211D867D68b1eda76a635A7` | `0x5C32143C8B198F392d01f8446b754c181224ac26` | `0x9ec9551d4A1a1593b0ee8124D98590CC71b3B09D` | *(in registry)* |
| USDT | `0x6c9a1ACF73bd85463A46B0AFc076FBdf602b690B` | `0x8741Ba6225A6BF91f9D73531A98A89807857a2B3` | `0xB2f7d27B21a69a033f85C42d5EB079043BAadC81` | `0x9F93ACA246F457916E49Ec923B8ed099e313f763` | `0x3cA3218D6c52B640B0857cc19b69Aa9427BC842C` |
| DAI | `0xEcf268Be00308980B5b3fcd0975D47C4C8e1382a` | `0x28529fec439cfF6d7D1D5917e956dEE62Cd3BE5c` | `0x25FB92E505F752F730cAD0Bd4fa17ecE4A384266` | `0xb8901acB165ed027E32754E0FFe830802919727f` | `0x8b7aA8f5cc9996216A88D900df8B8a0a3905939A` |
| ETH | `0xb98454270065A31D71Bf635F6F7Ee6A518dFb849` | `0xc315239cFb05F1E130E7E28E603CEa4C014c57f0` | `0x266e2dc3C4c59E42AA07afeE5B09E964cFFe6778` | `0x1fDeAF938267ca43388eD1FdB879eaF91e920c7A` | `0x971039bF0A49c8d8A675f839739eE7a42511eC91` |
| MATIC | `0x553bC791D746767166fA3888432038193cEED5E2` | `0x884d1Aa15F9957E1aEAA86a82a72e49Bc2bfCbe3` | `0x3d4Cc8A61c7528Fd86C55cfe061a78dCBA48EDd1` | `0x712F0cf37Bdb8299D0666727F73a5cAbA7c1c24c` | `0xbc4FB4ED825C65fF48163AF7E59d49e32edb5269` |
| HOP | `0x58c61AeE5eD3D748a1467085ED2650B697A66234` | *(none — `0x0`)* | *(none — `0x0`)* | `0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC` | *(none)* |

Polygon-USDC `l2CanonicalToken` in the registry is `0x3c499c54…` (native USDC) but the live Saddle pool token is the bridged USDC.e — verify per-pool with `getToken(0)`. The MATIC-DAI Saddle pool (`0x3d4Cc8A6…`) shares its literal with the **Ethereum DAI L1_Bridge** — `(chainId,address)` keying again.

---

## 7. Addresses — Base (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com`. L2_Bridge ~18.0 KB, non-proxy. Base carries **USDC, ETH, and HOP only** (no USDT/DAI/MATIC routes).

| Token | L2_Bridge | L2_AmmWrapper | Saddle Swap | hToken | LP token |
|-------|-----------|---------------|-------------|--------|----------|
| USDC | `0x46ae9BaB8CEA96610807a275EBD36f8e916b5C61` | `0x7D269D3E0d61A05a0bA976b7DBF8805bF844AF3F` | `0x022C5cE6F1Add7423268D41e08Df521D5527C2A0` | `0x74fa978EaFFa312bC92e76dF40FcC1bFE7637Aeb` | `0x3b507422EBe64440f03BCbE5EEe4bdF76517f320` |
| ETH | `0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a` | `0x10541b07d8Ad2647Dc6cD67abd4c03575dade261` | `0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d` | `0xC1985d7a3429cDC85E59E2E4Fcc805b857e6Ee2E` | `0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D` |
| HOP | `0xe22D2beDb3Eca35E6397e0C6D62857094aA26F52` | *(none — `0x0`)* | *(none — `0x0`)* | `0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC` | *(none)* |

**Collision tell on Base:** `0x46ae9BaB…` is the Base **USDC** L2_Bridge but the OP **USDT** L2_Bridge; `0x3666f603…` is the Base **ETH** L2_Bridge but the Ethereum **USDC** L1_Bridge; `0x10541b07…` is the Base **ETH** AmmWrapper but the Arbitrum **USDC** Saddle Swap. These are deterministic-deploy / nonce-aligned coincidences, not the same contract — never resolve a Hop address without its chainId.

---

## 8. Chains NOT in the seven (recorded findings)

Hop's primary counterparties span more chains than the seven requested. From the canonical registry, also live but **outside the 7 target chains**:

- **Gnosis Chain (100)** — full set for USDC/USDT/DAI/ETH/MATIC/HOP (`l2Bridge` e.g. USDC `0x25D8039b…`). Gnosis was one of Hop's earliest L2s.
- **Arbitrum Nova (42170)** — ETH/HOP/MAGIC (`l2Bridge` ETH `0x8796860c…`).
- **Linea (59144)** — ETH/HOP (`l2Bridge` ETH `0xCbb852A6…`).
- **Polygon zkEVM (1101)** — ETH/HOP (`l2Bridge` ETH `0x0ce6c85c…`).

Each of these has its own `l1MessengerWrapper` deployed on Ethereum (chain 1). **BNB Smart Chain (56) and Avalanche C-Chain (43114) have no Hop deployment of any kind** — confirmed by `eth_getCode = 0x` for the USDC/ETH L2_Bridge addresses and for the HOP token `0xc5102fE9…` on both. Hop is an optimistic/canonical-rollup bridge and never expanded to those non-rollup L1s.

---

## 9. Cross-chain summary

Presence matrix (✓ = `eth_getCode` non-empty on 2026-06-09; — = not deployed / not in registry).

| Chain | ID | Bridge contract | USDC | USDT | DAI | ETH | MATIC | HOP | SNX | sUSD | rETH | MAGIC |
|-------|----|------------------|------|------|-----|-----|-------|-----|-----|------|------|-------|
| **Ethereum** | 1 | L1_Bridge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Optimism** | 10 | L2_Bridge | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | — |
| **Arbitrum** | 42161 | L2_Bridge | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — | ✓ | ✓ |
| **Polygon** | 137 | L2_Bridge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — | — | — |
| **Base** | 8453 | L2_Bridge | ✓ | — | — | ✓ | — | ✓ | — | — | — | — |
| **BNB** | 56 | — | — | — | — | — | — | — | — | — | — | — |
| **Avalanche** | 43114 | — | — | — | — | — | — | — | — | — | — | — |

**Vanity / collision tells:** Hop uses **no vanity prefix**; bridges are nonce-deployed and addresses collide across chains by coincidence (see §4/§6/§7). The recurring tells are (a) the HOP token `0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC` reused as the hToken on every L2 HOP bridge, and (b) the governance multisig `0x22e3f828b3f47dacfacd875d20bd5cc0879c96e7` returned by `governance()` on every L1_Bridge. The bonder EOA `0xa6a688F107851131F0E1dce493EbBebFAf99203e` is the same across all routes for USDC (and most others).

---

## 10. Proxies (old & new)

**There are no proxies in Hop v1.** Every contract is directly deployed and immutable code. Verified by reading the EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` via `eth_getStorageAt` — it returns `0x000…0` on the ETH USDC L1_Bridge, ARB USDC L2_Bridge, OP USDC L2_AmmWrapper, and ARB USDC Saddle Swap (all sampled on 2026-06-09).

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| L1_Bridge / L2_Bridge | **Immutable (no proxy)** | EIP-1967 impl slot = `0x0`; 14–19 KB full bytecode; `getChainId()`/`governance()` present | none — code is fixed. Governance can only rewire messenger wrappers, pause deposits, set AMM wrapper, add/remove bonders. |
| L2_AmmWrapper | **Immutable** | impl slot `0x0`; ~4.4 KB; `bridge()`/`hToken()`/`exchangeAddress()` present | none. |
| Saddle `Swap` | **Immutable** | impl slot `0x0`; ~17.7 KB; `getToken(uint8)` present | pool owner (Hop gov) can set fees / ramp A, not replace code. |
| HopBridgeToken / LP token | **Immutable** | standard ERC-20 bytecode | `mint`/`burn` are owner-gated (owner = L2_Bridge). |

There is **no `Upgraded(address)` event** to watch in the Hop set. The closest "code/wiring change" signals are `setCrossDomainMessengerWrapper` (`0xd4448163`) and `setChainIdDepositsPaused` (`0x14942024`) on the L1 bridges, and `setAmmWrapper` (`0x64c6fdb4`) on the L2 bridges — monitor those calls as governance/risk events.

---

## 11. Detection invariants & gotchas

1. **Use the `v1`-branch signatures, not `master`.** Production is v1: `WithdrawalBonded(bytes32,uint256)` (no `bonder`), `TransferSent(...,uint256 amountOutMin,uint256 deadline)` (9 fields, no `rootIndex`/`tokenIndex`/`bonder`), `TransfersCommitted(uint256,bytes32,uint256,uint256)` (4 fields). The `master` branch's wider events compute to *different* topic0s that never appear on-chain.
2. **Per-token, per-chain instances — there is no singleton.** Each token has its own L1_Bridge on Ethereum and its own {L2_Bridge, L2_AmmWrapper, Saddle Swap, hToken, LP} tuple per L2. Always key everything on `(chainId, contract address, token)`.
3. **Massive cross-chain address collisions, zero vanity.** The same 40-hex string is reused for unrelated roles on different chains (e.g. `0x46ae9BaB…` = OP-USDT-L2Bridge **and** Base-USDC-L2Bridge; `0x3666f603…` = ETH-USDC-L1Bridge **and** Base-ETH-L2Bridge; `0x25FB92E5…` = ARB-HOP-L2Bridge, ETH-Polygon-DAI-Saddle, and Optimism-Polygon-DAI-Saddle). **Never resolve a Hop address without its chainId.**
4. **`transferId` is the join key**, computed as `getTransferId(chainId,recipient,amount,transferNonce,bonderFee,amountOutMin,deadline)` (selector `0xaf215f94`). It links the source `TransferSent`/`TransferSentToL2`, the destination `WithdrawalBonded`/`Withdrew`, and the settlement `WithdrawalBondSettled`. `rootHash`/`transferRootId` join the root lifecycle (`TransfersCommitted`→`TransferRootBonded`→`TransferRootConfirmed`→`TransferRootSet`→`MultipleWithdrawalsSettled`).
5. **The bonder fast-path leaves the recipient's funds with no canonical-bridge event.** `bondWithdrawalAndDistribute` (`0x3d12a85a`) → `WithdrawalBonded` + (often) a Saddle `TokenSwap` is what the user actually sees on the destination; the slow canonical settlement (`Withdrew`/`settleBondedWithdrawals`) happens later and reimburses the bonder, not the user. Don't double-count.
6. **`TransferSent` (L2) ≠ `TransferSentToL2` (L1).** They are different events on different contracts (and the L1 one indexes `chainId`/`recipient`/`relayer`, the L2 one indexes `transferId`/`chainId`/`recipient`). Index both as "a transfer was initiated," but from opposite legs.
7. **`recipient` in the event is the real destination user**; `tx.from` is usually the bonder or the AmmWrapper, not the user. The L1→L2 `relayer` field (and `relayerFee`) is the auto-forwarder, not the user either.
8. **HOP-token bridges have no AMM.** `l2AmmWrapper = 0x0` and `l2SaddleSwap = 0x0` for HOP routes (and the hToken *is* the canonical HOP token `0xc5102fE9…`). Expect `TransferSent`/`WithdrawalBonded` but never `TokenSwap` on those.
9. **ETH bridges set `l2CanonicalTokenIsEth() = true`** (confirmed on OP ETH AmmWrapper). Canonical token is the chain's WETH (`0x4200…06` on OP/Base, `0x82aF…ab1` on Arbitrum, `0x7ceB…619` on Polygon), and ETH moves natively — `amount` is in wei, not via an ERC-20 `Transfer` from the user.
10. **Shared base events fire on both L1 and L2 bridges.** `Withdrew`, `WithdrawalBonded`, `WithdrawalBondSettled`, `MultipleWithdrawalsSettled`, `TransferRootSet`, `Stake`/`Unstake`/`BonderAdded`/`BonderRemoved` all come from `Bridge`/`Accounting` and appear on the L1_Bridge *and* the L2_Bridge of the same token. Disambiguate by emitter chain/address.
11. **Saddle `swap` uses `uint8` token indices** (`0x91695586`) — token 0 = canonical, token 1 = hToken (verify with `getToken(0)`/`getTokenIndex`). This is a different function from the bridge `send`/AmmWrapper `swap` even though all are named "swap."
12. **Not on BNB or Avalanche.** Every Hop address returns `0x` there. A "Hop on BNB/Avax" claim is wrong; treat as absence.
13. **Counterparty chains outside the seven exist** (Gnosis, Nova, Linea, Polygon zkEVM — §8). A `TransferSentToL2`/`TransferSent` whose `chainId` ∉ {1,10,137,8453,42161} is targeting one of those — record the chainId, don't drop the event.
14. **No proxies ⇒ no `Upgraded` topic.** Code is immutable; the only governance "change" signals are `setCrossDomainMessengerWrapper`, `setChainIdDepositsPaused`, `setAmmWrapper`, and `BonderAdded`/`BonderRemoved`. Monitor those as admin/risk events.

---

## 12. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; Hop v1) =====
-- L1_Bridge
TOPIC_TRANSFER_SENT_TO_L2        = '\x0a0607688c86ec1775abcdbab7b33a3a35a6c9cde677c9be880150c231cc6b0b'
TOPIC_TRANSFER_ROOT_BONDED       = '\xa57b3e1f3af9eca02201028629700658608222c365064584cfe65d9630ef4f7b'
TOPIC_TRANSFER_ROOT_CONFIRMED    = '\xfdfb0eefa96935b8a8c0edf528e125dc6f3934fdbbfce31b38967e8ff413dccd'
TOPIC_TRANSFER_BOND_CHALLENGED   = '\xec2697dcba539a0ac947cdf1f6d0b6314c065429eca8be2435859b10209d4c27'
TOPIC_CHALLENGE_RESOLVED         = '\x4a99228a8a6d774d261be57ab0ed833bb1bae1f22bbbd3d4767b75ad03fdddf7'
-- L2_Bridge
TOPIC_TRANSFER_SENT              = '\xe35dddd4ea75d7e9b3fe93af4f4e40e778c3da4074c9d93e7c6536f1e803c1eb'
TOPIC_TRANSFERS_COMMITTED        = '\xf52ad20d3b4f50d1c40901dfb95a9ce5270b2fc32694e5c668354721cd87aa74'
TOPIC_TRANSFER_FROM_L1_COMPLETED = '\x320958176930804eb66c2343c7343fc0367dc16249590c0f195783bee199d094'
-- Bridge (shared L1+L2)
TOPIC_WITHDREW                   = '\x9475cdbde5fc71fe2ccd413c82878ee54d061b9f74f9e2e1a03ff1178821502c'
TOPIC_WITHDRAWAL_BONDED          = '\x0c3d250c7831051e78aa6a56679e590374c7c424415ffe4aa474491def2fe705'
TOPIC_WITHDRAWAL_BOND_SETTLED    = '\x84eb21b24c31b27a3bc67dde4a598aad06db6e9415cd66544492b9616996143c'
TOPIC_MULTIPLE_WITHDRAWALS_SETTLED = '\x78e830d08be9d5f957414c84d685c061ecbd8467be98b42ebb64f0118b57d2ff'
TOPIC_TRANSFER_ROOT_SET          = '\xb33d2162aead99dab59e77a7a67ea025b776bf8ca8079e132afdf9b23e03bd42'
-- Accounting (bonder)
TOPIC_STAKE                      = '\xebedb8b3c678666e7f36970bc8f57abf6d8fa2e828c0da91ea5b75bf68ed101a'
TOPIC_UNSTAKE                    = '\x85082129d87b2fe11527cb1b3b7a520aeb5aa6913f88a3d8757fe40d1db02fdd'
TOPIC_BONDER_ADDED               = '\x2cec73b7434d3b91198ad1a618f63e6a0761ce281af5ec9ec76606d948d03e23'
TOPIC_BONDER_REMOVED             = '\x4234ba611d325b3ba434c4e1b037967b955b1274d4185ee9847b7491111a48ff'
-- Saddle Swap (AMM)
TOPIC_TOKEN_SWAP                 = '\xc6c1e0630dbe9130cc068028486c0d118ddcea348550819defd5cb8c257f8a38'
TOPIC_ADD_LIQUIDITY              = '\x189c623b666b1b45b83d7178f39b8c087cb09774317ca2f53c2d3c3726f222a2'
TOPIC_REMOVE_LIQUIDITY           = '\x88d38ed598fdd809c2bf01ee49cd24b7fdabf379a83d29567952b60324d58cef'
TOPIC_REMOVE_LIQUIDITY_ONE       = '\x43fb02998f4e03da2e0e6fff53fdbf0c40a9f45f145dc377fc30615d7d7a8a64'
TOPIC_REMOVE_LIQUIDITY_IMBALANCE = '\x3631c28b1f9dd213e0319fb167b554d76b6c283a41143eb400a0d1adb1af1755'
-- ERC-20 (hToken / LP / canonical)
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
-- L1_Bridge
SEL_SEND_TO_L2                   = '\xdeace8f5'
SEL_BOND_TRANSFER_ROOT           = '\x8d8798bf'
SEL_CONFIRM_TRANSFER_ROOT        = '\xef6ebe5e'
SEL_CHALLENGE_TRANSFER_BOND      = '\x1bbe15ea'
SEL_RESOLVE_CHALLENGE            = '\x81707b80'
SEL_SET_MESSENGER_WRAPPER        = '\xd4448163'
SEL_SET_DEPOSITS_PAUSED          = '\x14942024'
-- L2_Bridge
SEL_SEND                         = '\xa6bd1b33'
SEL_COMMIT_TRANSFERS             = '\x32b949a2'
SEL_DISTRIBUTE                   = '\xcc29a306'
SEL_BOND_WITHDRAWAL_AND_DISTRIBUTE = '\x3d12a85a'
SEL_SET_TRANSFER_ROOT            = '\xfd31c5ba'
SEL_SET_AMM_WRAPPER              = '\x64c6fdb4'
-- Bridge (shared)
SEL_WITHDRAW                     = '\x0f7aadb7'
SEL_BOND_WITHDRAWAL              = '\x23c452cd'
SEL_SETTLE_BONDED_WITHDRAWAL     = '\xc7525dd3'
SEL_SETTLE_BONDED_WITHDRAWALS    = '\xb162717e'
SEL_RESCUE_TRANSFER_ROOT         = '\xcbd1642e'
SEL_GET_TRANSFER_ID              = '\xaf215f94'
SEL_GET_TRANSFER_ROOT_ID         = '\x960a7afa'
SEL_IS_TRANSFER_ID_SPENT         = '\x3a7af631'
SEL_GET_CHAIN_ID                 = '\x3408e470'
SEL_GOVERNANCE                   = '\x5aa6e675'
-- L2_AmmWrapper
SEL_SWAP_AND_SEND                = '\xeea0d7b2'
SEL_AMMWRAP_SWAP                 = '\xe5c7a632'
SEL_ATTEMPT_SWAP                 = '\x676c5ef6'
SEL_AMMWRAP_BRIDGE               = '\xe78cea92'
SEL_AMMWRAP_EXCHANGE_ADDRESS     = '\x9cd01605'
SEL_AMMWRAP_HTOKEN               = '\xfc6e3b3b'
SEL_AMMWRAP_CANONICAL_IS_ETH     = '\x28555125'
-- Saddle Swap
SEL_SADDLE_SWAP                  = '\x91695586'
SEL_ADD_LIQUIDITY                = '\x4d49e87d'
SEL_REMOVE_LIQUIDITY             = '\x31cd52b0'
SEL_GET_TOKEN                    = '\x82b86600'
SEL_GET_TOKEN_INDEX              = '\x66c0bd24'
-- HopBridgeToken
SEL_MINT                         = '\x40c10f19'
SEL_BURN                         = '\x9dc29fac'

-- ===== Proxy slot (reads 0x0 everywhere — Hop has NO proxies) =====
EIP1967_IMPL_SLOT                = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'

-- ===== Shared constants =====
HOP_GOVERNANCE                   = '\x22e3f828b3f47dacfacd875d20bd5cc0879c96e7'   -- governance() on every L1_Bridge
HOP_TOKEN                        = '\xc5102fe9359fd9a28f877a67e36b0f050d81a3cc'   -- HOP ERC-20 = hToken on every HOP L2 bridge
USDC_BONDER                      = '\xa6a688f107851131f0e1dce493ebbebfaf99203e'   -- bonder EOA (USDC + most routes)

-- ===== Ethereum (chain 1) L1_Bridge per token =====
ETH_L1BRIDGE_USDC                = '\x3666f603cc164936c1b87e207f36beba4ac5f18a'
ETH_L1BRIDGE_USDT                = '\x3e4a3a4796d16c0cd582c382691998f7c06420b6'
ETH_L1BRIDGE_DAI                 = '\x3d4cc8a61c7528fd86c55cfe061a78dcba48edd1'
ETH_L1BRIDGE_ETH                 = '\xb8901acb165ed027e32754e0ffe830802919727f'
ETH_L1BRIDGE_MATIC               = '\x22b1cbb8d98a01a3b71d034bb899775a76eb1cc2'
ETH_L1BRIDGE_HOP                 = '\x914f986a44acb623a277d6bd17368171fcbe4273'
ETH_L1BRIDGE_SNX                 = '\x893246facf345c99e4235e5a7bbee7404c988b96'
ETH_L1BRIDGE_SUSD                = '\x36443fc70e073fe9d50425f82a3ee19fef697d62'
ETH_L1BRIDGE_RETH                = '\x87269b23e73305117d0404557badc459ced0dbec'
ETH_L1BRIDGE_MAGIC               = '\xf074540eb83c86211f305e145eb31743e228e57d'

-- ===== Optimism (chain 10) L2_Bridge per token =====
OP_L2BRIDGE_USDC                 = '\xa81d244a1814468c734e5b4101f7b9c0c577a8fc'
OP_L2BRIDGE_USDT                 = '\x46ae9bab8cea96610807a275ebd36f8e916b5c61'
OP_L2BRIDGE_DAI                  = '\x7191061d5d4c60f598214cc6913502184baddf18'
OP_L2BRIDGE_ETH                  = '\x83f6244bd87662118d96d9a6d44f09dfff14b30e'
OP_L2BRIDGE_HOP                  = '\x03d7f750777ec48d39d080b020d83eb2cb4e3547'
OP_L2BRIDGE_SNX                  = '\x16284c7323c35f4960540583998c98b1cfc581a7'
OP_L2BRIDGE_SUSD                 = '\x33fe5bb8da466da55a8a32d6ade2bb104e2c5201'
OP_L2BRIDGE_RETH                 = '\xa0075e8ce43dcb9970cb7709b9526c1232cc39c2'
OP_AMMWRAPPER_USDC               = '\x2ad09850b0ca4c7c1b33f5acd6cbabcab5d6e796'
OP_SADDLESWAP_USDC               = '\x3c0ffaca566fccfd9cc95139fef6cba143795963'

-- ===== Arbitrum One (chain 42161) L2_Bridge per token =====
ARB_L2BRIDGE_USDC                = '\x0e0e3d2c5c292161999474247956ef542cabf8dd'
ARB_L2BRIDGE_USDT                = '\x72209fe68386b37a40d6bca04f78356fd342491f'
ARB_L2BRIDGE_DAI                 = '\x7ac115536fe3a185100b2c4de4cb328bf3a58ba6'
ARB_L2BRIDGE_ETH                 = '\x3749c4f034022c39ecaffaba182555d4508caccc'
ARB_L2BRIDGE_HOP                 = '\x25fb92e505f752f730cad0bd4fa17ece4a384266'
ARB_L2BRIDGE_RETH                = '\xc315239cfb05f1e130e7e28e603cea4c014c57f0'
ARB_L2BRIDGE_MAGIC               = '\xea5abf2c909169823d939de377ef2bf897a6ce98'
ARB_AMMWRAPPER_USDC              = '\xe22d2bedb3eca35e6397e0c6d62857094aa26f52'
ARB_SADDLESWAP_USDC              = '\x10541b07d8ad2647dc6cd67abd4c03575dade261'

-- ===== Polygon PoS (chain 137) L2_Bridge per token =====
POLY_L2BRIDGE_USDC               = '\x25d8039bb044dc227f741a9e381ca4ceae2e6ae8'
POLY_L2BRIDGE_USDT               = '\x6c9a1acf73bd85463a46b0afc076fbdf602b690b'
POLY_L2BRIDGE_DAI                = '\xecf268be00308980b5b3fcd0975d47c4c8e1382a'
POLY_L2BRIDGE_ETH                = '\xb98454270065a31d71bf635f6f7ee6a518dfb849'
POLY_L2BRIDGE_MATIC              = '\x553bc791d746767166fa3888432038193ceed5e2'
POLY_L2BRIDGE_HOP                = '\x58c61aee5ed3d748a1467085ed2650b697a66234'
POLY_AMMWRAPPER_USDC             = '\x76b22b8c1079a44f1211d867d68b1eda76a635a7'
POLY_SADDLESWAP_USDC             = '\x5c32143c8b198f392d01f8446b754c181224ac26'

-- ===== Base (chain 8453) L2_Bridge per token =====
BASE_L2BRIDGE_USDC               = '\x46ae9bab8cea96610807a275ebd36f8e916b5c61'
BASE_L2BRIDGE_ETH                = '\x3666f603cc164936c1b87e207f36beba4ac5f18a'
BASE_L2BRIDGE_HOP                = '\xe22d2bedb3eca35e6397e0c6d62857094aa26f52'
BASE_AMMWRAPPER_USDC             = '\x7d269d3e0d61a05a0ba976b7dbf8805bf844af3f'
BASE_SADDLESWAP_USDC             = '\x022c5ce6f1add7423268d41e08df521d5527c2a0'
```

---

## 13. Verification & sources

How every constant was verified (2026-06-09):

- **Event topic0 / function selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome) from the canonical Solidity source on the `hop-protocol/contracts` **`v1`** branch (`bridges/Bridge.sol`, `L1_Bridge.sol`, `L2_Bridge.sol`, `L2_AmmWrapper.sol`, `Accounting.sol`, `HopBridgeToken.sol`, `saddle/Swap.sol`). The v1 vs. `master` divergence (2-field `WithdrawalBonded`, 9-field `TransferSent`, 4-field `TransfersCommitted`) was resolved by diffing both branches and confirming against live logs.
- **Live-log cross-check:** `eth_getLogs` on the Ethereum USDC L1_Bridge (`0x3666f603…`, blocks 12 650 032–12 700 032) confirmed `TransferSentToL2` `0x0a060768`, `TransferRootConfirmed` `0xfdfb0eef`, `WithdrawalBonded` `0x0c3d250c`, `TransferRootSet` `0xb33d2162`, `MultipleWithdrawalsSettled` `0x78e830d0`, `Stake` `0xebedb8b3`, `BonderAdded` `0x2cec73b7`. The L2 9-field `TransferSent` `0xe35dddd4` was confirmed live on the Optimism ETH L2_Bridge (`0x83f6244B…`, recent block window).
- **Addresses:** parsed from the canonical SDK registry `hop-protocol/hop` `packages/sdk/src/addresses/mainnet.ts` (the `bridges` map: `l1Bridge`, `l2Bridge`, `l2AmmWrapper`, `l2SaddleSwap`, `l2HopBridgeToken`, `l2SaddleLpToken`), then existence-checked via `eth_getCode` on each chain's publicnode RPC. All Ethereum L1 bridges (10 tokens) and all L2 bridges/wrappers/swaps on Optimism/Arbitrum/Polygon/Base returned non-empty bytecode; **BNB and Avalanche returned `0x` for every probe.**
- **Wiring confirmation (`eth_call`):** `getChainId()` = 42161 on the ARB USDC L2_Bridge; `governance()` = `0x22e3f828…` identical on the USDC and HOP L1 bridges; OP USDC AmmWrapper `bridge()` = the USDC L2_Bridge; OP ETH AmmWrapper `l2CanonicalTokenIsEth()` = 1, `hToken()`/`exchangeAddress()`/`l2CanonicalToken()` match the registry; the bonder `0xa6a688F1…` and HOP token on BNB/Avax have code length 0.
- **Proxy classification:** EIP-1967 impl slot `0x360894…bbc` read via `eth_getStorageAt` returns `0x0` on the ETH USDC L1_Bridge, ARB USDC L2_Bridge, OP USDC L2_AmmWrapper, and ARB USDC Saddle Swap ⇒ **no proxies; immutable code; no `Upgraded` event.**
- **Chain coverage:** the seven requested chains were each probed with the USDC and ETH bridge addresses; counterparty chains outside the seven (Gnosis, Arbitrum Nova, Linea, Polygon zkEVM) are present in the registry and recorded in §8.

**Authoritative sources:**
- Canonical contracts (production): https://github.com/hop-protocol/contracts/tree/v1/contracts/bridges and `.../saddle/Swap.sol`
- Address registry (SDK): https://github.com/hop-protocol/hop/blob/develop/packages/sdk/src/addresses/mainnet.ts
- Official docs: https://docs.hop.exchange/ (Smart Contracts / Contract Addresses)
- Explorers: https://etherscan.io/address/0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a · https://arbiscan.io/address/0x0e0E3d2C5c292161999474247956EF542caBF8dd · https://optimistic.etherscan.io/address/0x83f6244Bd87662118d96D9a6D44f09dffF14b30E · https://basescan.org/address/0x46ae9BaB8CEA96610807a275EBD36f8e916b5C61

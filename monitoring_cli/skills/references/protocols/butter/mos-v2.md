# Butter Network — MAP Omnichain Service V2 (MOS V2, LEGACY) — Topics, Selectors, Addresses (Ethereum, Base, BNB, Arbitrum, Optimism, Polygon + MAP relay)

**Status:** verified against live RPC on Ethereum (1), Base (8453), BNB (56), Arbitrum One (42161), Optimism (10), Polygon PoS (137), and the canonical `butternetwork/butter-mos-contracts` (`evmv2/`) repo on 2026-06-09. **Avalanche (43114): not deployed** (`eth_getCode` = `0x`).
**Scope:** the **legacy, superseded** MAP Omnichain Service bridge — `MAPOmnichainServiceV2` on spoke chains, `MAPOmnichainServiceRelayV2` on the MAP relay, plus `TokenRegisterV2`. **MOS V2 is fully replaced by MOS V3** ([mos-v3.md](mos-v3.md)); the V2 proxy still has bytecode on most chains but shows **~0 recent on-chain activity** (0 logs in a 49k-block window on Ethereum). Documented for completeness / historical indexing. Topics + selectors are chain-agnostic; addresses are network-specific.

MOS V2 used the same hub-and-spoke design as V3 (every transfer routes through the MAP relay, chainId 22776), but with an older event vocabulary: outbound transfers emit **`mapSwapOut`** / `mapTransferOut` / `mapDepositOut`, inbound emit **`mapSwapIn`** / `mapDepositIn`. The V3 redesign collapsed these into the generic `MessageOut`/`MessageIn`/`MessageRelay` triplet.

**Single shared spoke address `0xfeB2b97e4Efce787c08086dC16Ab69E063911380` on most EVM chains** (deterministic deploy), behind an **EIP-1967 Transparent proxy** (not UUPS) with a populated admin slot. On **Arbitrum and Optimism the same literal is a smaller, distinct deployment** (177 B proxy vs 680 B). zkSync uses a different literal entirely.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally on 2026-06-09 from `evmv2/contracts/`.

### 1.1 MAPOmnichainServiceV2 (spoke) — emitter = `0xfeB2b97e…`

| topic0 | Event |
|--------|-------|
| `0xca1cf8cebf88499429cca8f87cbca15ab8dafd06702259a5344ddce89ef3f3a5` | `mapSwapOut(uint256 indexed fromChain, uint256 indexed toChain, bytes32 orderId, bytes token, bytes from, bytes to, uint256 amount, bytes swapData)` — outbound swap-and-bridge. |
| `0x2a945137b011d4aadec6425788c652197d107fc33f6cdccbb0c269273be9c1c9` | `mapSwapIn(uint256 indexed fromChain, uint256 indexed toChain, bytes32 indexed orderId, address token, bytes from, address toAddress, uint256 amountOut)` — inbound delivery. |
| `0x44ff77018688dad4b245e8ab97358ed57ed92269952ece7ffd321366ce078622` | `mapTransferOut(uint256 indexed fromChain, uint256 indexed toChain, bytes32 orderId, bytes token, bytes from, bytes to, uint256 amount, bytes toChainToken)` — plain transfer-out (no swap). |
| `0xb7100086a8e13ebae772a0f09b07046e389a6b036406d22b86f2d2e5b860a8d9` | `mapDepositOut(uint256 indexed fromChain, uint256 indexed toChain, bytes32 orderId, address token, bytes from, address to, uint256 amount)` — vault liquidity deposit-out. |

### 1.2 MAPOmnichainServiceRelayV2 (MAP relay, 22776) — emitter = `0xfeB2b97e…` on MAPO

| topic0 | Event |
|--------|-------|
| `0x5bf7c8229e485fc1aa764dc0e95bb88be5d3589f08d0fb5fca73bd195aecde0e` | `mapDepositIn(uint256 indexed fromChain, uint256 indexed toChain, address indexed token, bytes32 orderId, bytes from, address to, uint256 amount)` |
| `0x8131e5b107f7021b0773c1108755872d7b94bb31532fdf2256e0a3ef2c890a3d` | `mapSwapExecute(uint256 indexed fromChain, uint256 indexed toChain, address indexed from)` |
| `0x70813c9dca7020458095d8251d2a1268cfadf7eb8a1fd2054c571fca46fea906` | `CollectFee(bytes32 indexed orderId, address indexed token, uint256 value)` |
| `0xbaf2d9d2bcb4b0053b367b5cf2602bbe430a111af7a354b557f102a9711a8b35` | `CollectFeeV2(bytes32 indexed orderId, address indexed token, uint256 baseFee, uint256 bridgeFee, uint256 messageFee, uint256 vaultFee, uint256 protocolFee)` |

### 1.3 Admin / proxy

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address implementation)` — watch on the proxy. |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` (Transparent proxy admin). |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (bridged token lock/mint/burn). |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb899f904` | `swapOutToken(address _initiator, address _token, bytes _to, uint256 _amount, uint256 _toChain, bytes _swapData)` → `bytes32 orderId` | **outbound entrypoint.** *(Same selector as the MOS V3 `swapOutToken` — disambiguate by contract address/generation.)* Emits `mapSwapOut`. |
| `0xfb0f97a8` | `depositToken(address _token, address _to, uint256 _amount)` | vault liquidity deposit. *(Same selector as MOS V3 `depositToken`.)* |
| `0xea618b87` | `swapIn(uint256 _chainId, uint256 _logIndex, bytes32 _orderId, bytes _receiptProof)` | verify relay proof + deliver. Emits `mapSwapIn`. |
| `0x504420c8` | `swapInVerified(bytes _logArray, uint256 _logIndex, bytes32 _orderId)` | execute a previously-verified inbound log. |
| `0xd962e33b` | `setButterRouter(address)` | admin: set the trusted router. |
| `0xbf7e214f` | `authority()` | — |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

Verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Source: `evmv2/deployments/mos.json`.

| Role | Address | Bytecode | One-liner |
|------|---------|----------|-----------|
| **MOS V2** (`MAPOmnichainServiceV2`, Transparent proxy) | `0xfeB2b97e4Efce787c08086dC16Ab69E063911380` | 680 B | Legacy spoke bridge. Live impl `0x2787bfc68c2d004bef91e486b086a297ae31dd3d`; proxy admin `0xaaaaa8a316ab372af9bc4cdd2ae040b03f9d4d88`. **~0 recent activity.** |
| AuthorityManager (V2-era) | `0xAaaAa8a316ab372Af9BC4cDD2ae040b03f9D4d88` | 4609 B | V2 access-control admin (= the proxy admin above). |

## 4. Addresses — Base / BNB / Arbitrum / Optimism / Polygon + Avalanche

Verified via `eth_getCode` on each chain. The **spoke proxy literal `0xfeB2b97e…` is shared on ETH/Base/BNB/Polygon** (680/708 B Transparent proxy) but is a **distinct, smaller deployment (177 B) on Arbitrum & Optimism**, and **absent on Avalanche**:

| Chain | ID | MOS V2 `0xfeB2b97e…` | Live impl | Proxy admin |
|---|---|---|---|---|
| Ethereum | 1 | ✓ (680 B) | `0x2787bfc68c2d004bef91e486b086a297ae31dd3d` | `0xaaaaa8a3…` (AuthorityManager) |
| Base | 8453 | ✓ (708 B) | `0x3377687e43a92e8d973801852216b99d60049ccf` | `0xbbcfbbec…` (ProxyAdmin) |
| BNB | 56 | ✓ (680 B) | `0x257afb93a59dc2ff522da10f9f428b414ab4b550` | `0xaaaaa8a3…` |
| Arbitrum | 42161 | ✓ (**177 B**, distinct deploy) | `0x8a452d3f4fc3a478dbbafc0aedabd096968ea304` | `0xbbcfbbec…` |
| Optimism | 10 | ✓ (**177 B**, distinct deploy) | `0xdfad86ba2d2d6580b534f447b54798a968da6a00` | `0xbbcfbbec…` |
| Polygon | 137 | ✓ (680 B) | `0x6f41c425f1bd258a12ee2850467683b1a3462e14` | `0xbbcfbbec…` |
| **Avalanche** | 43114 | **✗ (0x — never deployed)** | — | — |

AuthorityManager `0xAaaAa8a3…` (4609 B) is present on ETH/Base/BNB/Arb/OP/Polygon, **absent on Avalanche**.

## 5. Cross-chain summary

| Chain | ID | MOS V2 spoke | Notes |
|---|---|---|---|
| Ethereum | 1 | ✓ 680 B | impl `0x2787bfc6…` |
| Base | 8453 | ✓ 708 B | impl `0x3377687e…` |
| BNB | 56 | ✓ 680 B | impl `0x257afb93…` |
| Arbitrum | 42161 | ✓ 177 B | distinct smaller proxy |
| Optimism | 10 | ✓ 177 B | distinct smaller proxy |
| Polygon | 137 | ✓ 680 B | impl `0x6f41c425…` |
| **Avalanche** | 43114 | **✗** | MOS V3 only there |
| **MAP relay (MAPO)** | **22776** | ✓ (`MAPOmnichainServiceRelayV2`) + TokenRegisterV2 `0xE00219ec…` | not a target chain |

**Counterparty chains outside the seven:** MAP relay (22776), zkSync Era (324, different literal `0xBEf06a32…`), Linea, Mantle, Scroll, zkLink (`0xB666A84a…`), Merlin, Bevm, AINN, B2, Conflux, Klaytn, plus **Tron** (`TYMpgB8Q9vSoGtkyE3hXsvUrpte3KCDGj6`).

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **MOS V2** (`0xfeB2b97e…`) | **EIP-1967 Transparent** (not UUPS) | impl slot `0x360894…` populated; **admin slot `0xb53127…` populated** (= AuthorityManager `0xaaaaa8a3…` on ETH/BSC, ProxyAdmin `0xbbcfbbec…` elsewhere); per-chain impl (§4). | Transparent proxy admin / AuthorityManager. |
| AuthorityManager (`0xAaaAa8a3…`) | NOT a proxy | 4609 B full contract; impl slot `0x0`. | self. |
| TokenRegisterV2 (MAPO `0xE00219ec…`) | proxy (relay) | — | AuthorityManager. |

Watch `Upgraded(address)` (`0xbc7cd75a…`) + `AdminChanged` (`0x7e644d79…`) on `0xfeB2b97e…` per chain.

## 7. Detection invariants & gotchas

1. **MOS V2 is deprecated — V3 carries all current traffic.** A V2 proxy with code but no `mapSwapOut`/`mapSwapIn` logs is expected, not a bug. (Live: 0 logs in a 49k-block window on the ETH V2 proxy.) Only index V2 for historical backfill.
2. **`swapOutToken` and `depositToken` selectors (`0xb899f904`, `0xfb0f97a8`) are IDENTICAL between MOS V2 and MOS V3** (same canonical signatures). Disambiguate by the **contract address/generation** (`0xfeB2b97e…` = V2, `0x0000317Bec…` = V3), never by selector alone.
3. **V2 event vocabulary differs from V3.** V2 = `mapSwapOut`/`mapSwapIn`/`mapTransferOut`/`mapDepositOut`/`mapDepositIn`; V3 = `MessageOut`/`MessageIn`/`MessageRelay`/`DepositIn`. They do not share topic0s.
4. **The spoke literal `0xfeB2b97e…` is a SMALLER, distinct deployment on Arbitrum & Optimism (177 B)** vs the 680 B proxy on ETH/BSC/Base/Polygon, and **does not exist on Avalanche**. Key on `(chainId, address)` and read the impl per chain.
5. **Two different proxy admins** appear: AuthorityManager `0xaaaaa8a3…` (ETH/BSC) vs a plain ProxyAdmin `0xbbcfbbec…` (Base/Arb/OP/Polygon). Both can fire `AdminChanged`/`Upgraded`.
6. **The real user is `from`/`to` in the events, not `msg.sender`** (router/relayer is the caller).

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; LEGACY V2) =====
TOPIC_V2_MAP_SWAP_OUT      = '\xca1cf8cebf88499429cca8f87cbca15ab8dafd06702259a5344ddce89ef3f3a5'
TOPIC_V2_MAP_SWAP_IN       = '\x2a945137b011d4aadec6425788c652197d107fc33f6cdccbb0c269273be9c1c9'
TOPIC_V2_MAP_TRANSFER_OUT  = '\x44ff77018688dad4b245e8ab97358ed57ed92269952ece7ffd321366ce078622'
TOPIC_V2_MAP_DEPOSIT_OUT   = '\xb7100086a8e13ebae772a0f09b07046e389a6b036406d22b86f2d2e5b860a8d9'
TOPIC_V2_MAP_DEPOSIT_IN    = '\x5bf7c8229e485fc1aa764dc0e95bb88be5d3589f08d0fb5fca73bd195aecde0e'
TOPIC_V2_MAP_SWAP_EXECUTE  = '\x8131e5b107f7021b0773c1108755872d7b94bb31532fdf2256e0a3ef2c890a3d'
TOPIC_V2_COLLECT_FEE       = '\x70813c9dca7020458095d8251d2a1268cfadf7eb8a1fd2054c571fca46fea906'
TOPIC_V2_COLLECT_FEE_V2    = '\xbaf2d9d2bcb4b0053b367b5cf2602bbe430a111af7a354b557f102a9711a8b35'
TOPIC_UPGRADED             = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED        = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors =====
SEL_V2_SWAP_OUT_TOKEN      = '\xb899f904'   -- shared with MOS V3
SEL_V2_DEPOSIT_TOKEN       = '\xfb0f97a8'   -- shared with MOS V3
SEL_V2_SWAP_IN             = '\xea618b87'
SEL_V2_SWAP_IN_VERIFIED    = '\x504420c8'

-- ===== Addresses (key on (chainId,addr)) =====
BUTTER_MOSV2_SPOKE         = '\xfeb2b97e4efce787c08086dc16ab69e063911380'  -- ETH/Base/BSC/Polygon 680B; Arb/OP 177B; Avax ABSENT
BUTTER_MOSV2_AUTHORITY     = '\xaaaaa8a316ab372af9bc4cdd2ae040b03f9d4d88'
MAPO_TOKEN_REGISTER_V2     = '\xe00219ecdbd02e102998ff208724671c4709e188'  -- MAP relay only
-- per-chain V2 impls:
ETH_MOSV2_IMPL             = '\x2787bfc68c2d004bef91e486b086a297ae31dd3d'
BASE_MOSV2_IMPL            = '\x3377687e43a92e8d973801852216b99d60049ccf'
BSC_MOSV2_IMPL             = '\x257afb93a59dc2ff522da10f9f428b414ab4b550'
ARB_MOSV2_IMPL             = '\x8a452d3f4fc3a478dbbafc0aedabd096968ea304'
OP_MOSV2_IMPL              = '\xdfad86ba2d2d6580b534f447b54798a968da6a00'
POLY_MOSV2_IMPL            = '\x6f41c425f1bd258a12ee2850467683b1a3462e14'
```

## 9. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from `butternetwork/butter-mos-contracts/evmv2/contracts/` (`MAPOmnichainServiceV2.sol`, `MAPOmnichainServiceRelayV2.sol`, `interface/IButterMosV2.sol`).
- **Addresses:** parsed from `evmv2/deployments/mos.json` and existence-checked via `eth_getCode` on all seven target RPCs — present on ETH/Base/BNB/Arb/OP/Polygon, `0x` (absent) on Avalanche. Bytecode sizes recorded (680 B vs 177 B variants).
- **Proxy classification + deprecation:** EIP-1967 impl **and** admin slots read live via `eth_getStorageAt` on `0xfeB2b97e…` per chain — both populated ⇒ Transparent proxy (per-chain impls in §4). Deprecation confirmed by `eth_getLogs` returning **0 logs** for the V2 proxy on Ethereum across a 49k-block window (all current traffic is on MOS V3, mos-v3.md).

**Authoritative sources:**
- Bridge repo: <https://github.com/butternetwork/butter-mos-contracts> (`evmv2/`)
- Docs: <https://docs.butternetwork.io> · MAP Protocol: <https://docs.mapprotocol.io>
- Explorers: Etherscan / Basescan / BscScan / Arbiscan / Optimistic Etherscan / Polygonscan; MAP relay <https://maposcan.io>

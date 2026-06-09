# Coinbase Wrapped Staked ETH (cbETH) — Topics, Selectors, Addresses (Ethereum + Base/Arbitrum/Optimism/Polygon bridged)

**Status:** verified against live RPC on every listed chain on 2026-06-09 via `eth_getCode` / `eth_getStorageAt` / `eth_call` / `eth_getLogs`, the verified implementation source on Etherscan/Basescan, and keccak-256 recomputed locally + cross-checked against live logs.
**Scope:** cbETH is a **single-token liquid-staking product**, not an on-chain staking system. The canonical token + all mint/burn/rate logic live **only on Ethereum mainnet (chain ID 1)** at `0xBe9895146f7AF43049ca1c1AE358B0541Ea49704`. Every other chain holds a **bridged representation** of that ERC-20 (different address per chain, different bridge tech, no exchange-rate logic). Event `topic0` and function `selector` values are **chain-agnostic** (identical wherever the same implementation is deployed); addresses are network-specific. **(This doc covers cbETH only — cbBTC is a separate, non-staking product and is out of scope.)**

**What cbETH is.** cbETH is the **liquid wrapper for ETH staked through Coinbase**. Coinbase runs the validators off-chain; the token is a permissioned, upgradeable ERC-20 that Coinbase mints/burns and whose **ETH→cbETH exchange rate is pushed on-chain by an off-chain oracle** (cbETH is value-accruing / non-rebasing — supply does **not** change on yield, the *rate* rises). The Ethereum contract is a **fork of Circle/Centre's `FiatToken`** (the USDC code): same master-minter/minter, pauser, and blacklister admin surface, behind the same legacy **unstructured-storage upgradeable proxy** (`FiatTokenProxy`) — **plus** two cbETH-specific additions: `exchangeRate()` and `updateExchangeRate(uint256)` and an `ExchangeRateUpdated` event. The off-chain rate push is the **key protocol invariant** an indexer must track: there is no on-chain staking, no validators, no withdrawal queue here — just `mint`, `burn`, and the periodic rate update.

---

## 0. Contract families & versions

| Component | Where | Notes |
|-----------|-------|-------|
| **cbETH token (canonical)** | Ethereum only | FiatToken fork + `exchangeRate`/`updateExchangeRate`; behind a legacy unstructured-storage proxy. The only place mint/burn/rate happen. |
| **Bridged cbETH** | Base, Arbitrum, Optimism, Polygon | Per-chain ERC-20 mirrors of the Ethereum token. **No `exchangeRate()`**, no minting except by the bridge. Three different bridge technologies (OP Standard Bridge, an OZ BeaconProxy, Frax fxPortal). |
| **Exchange-rate oracle** | off-chain → Ethereum | A Coinbase-operated EOA (`0x9b37180d847b27adc13c2277299045c1237ae281`, observed) calls `updateExchangeRate` → `ExchangeRateUpdated`. This is the *only* yield signal — cbETH never rebases. |

There is **one** Ethereum version (the contract has been upgraded in place via the proxy, but the implementation ABI below is the live one). Bridged tokens are independent deployments and may upgrade on their own schedules.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

`topic0` is unaffected by `indexed`; signatures are canonical (no names/spaces, `indexed` removed). **✓** = observed verbatim in live mainnet logs this session; **src** = keccak of the verified-source signature (FiatToken / cbETH), high confidence, not log-confirmed in sampled windows.

### 1.1 cbETH token (Ethereum) — ERC-20 + FiatToken admin + exchange rate

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ✓ |
| `0x0b4e9390054347e2a16d95fd8376311b0d2deedecba526e9742bcaa40b059f0b` | `ExchangeRateUpdated(address indexed oracle, uint256 newExchangeRate)` | ✓ |
| `0xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8` | `Mint(address indexed minter, address indexed to, uint256 amount)` | ✓ |
| `0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5` | `Burn(address indexed burner, uint256 amount)` | ✓ |
| `0x46980fca912ef9bcdbd36877427b6b90e860769f604e89c0e67720cece530d20` | `MinterConfigured(address indexed minter, uint256 minterAllowedAmount)` | src |
| `0xe94479a9f7e1952cc78f2d6baab678adc1b772d936c6583def489e524cb66692` | `MinterRemoved(address indexed oldMinter)` | src |
| `0xdb66dfa9c6b8f5226fe9aac7e51897ae8ee94ac31dc70bb6c9900b2574b707e6` | `MasterMinterChanged(address indexed newMasterMinter)` | src |
| `0x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625` | `Pause()` | src |
| `0x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33` | `Unpause()` | src |
| `0xb80482a293ca2e013eda8683c9bd7fc8347cfdaeea5ede58cba46df502c2a604` | `PauserChanged(address indexed newAddress)` | src |
| `0xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855` | `Blacklisted(address indexed _account)` | src |
| `0x117e3210bb9aa7d9baff172026820255c6f6c30ba8999d1c2fd88e2848137c4e` | `UnBlacklisted(address indexed _account)` | src |
| `0xc67398012c111ce95ecb7429b933096c977380ee6c421175a71a4a4c6c88c06e` | `BlacklisterChanged(address indexed newBlacklister)` | src |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | src |

> **`ExchangeRateUpdated` is the yield signal.** topic1 = the indexed **oracle EOA** that pushed the rate; `data` = the new rate (1e18 ETH per cbETH, monotonically increasing — live ≈ `1.1321e18`). **cbETH never rebases**: balances/supply are unaffected by yield, only this number moves. There is one push roughly daily.
> **Mint/Burn carry the supply changes.** `Mint` (3 topics: minter, to) and `Burn` (2 topics: burner) come *with* `Transfer` from/to `0x0`. Index `Mint`/`Burn` to separate Coinbase issuance/redemption from secondary-market `Transfer`s.

### 1.2 FiatTokenProxy (Ethereum) — EIP-1967-style admin events on the proxy address

The proxy is the **legacy OpenZeppelin `AdminUpgradeabilityProxy`** (zos/unstructured storage, predates EIP-1967), but it emits the **same** two admin events as EIP-1967 proxies:

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

> **Watch `Upgraded` on the cbETH proxy.** A new implementation can change mint/burn/rate semantics or the entire admin surface — it is the single highest-severity event for this token.

### 1.3 Bridged tokens (Base / Arbitrum / Optimism / Polygon)

All bridged cbETH emit the standard ERC-20 `Transfer`/`Approval` (same topic0s as §1.1). Mint/burn shape differs by bridge:

| Chain / bridge | Mint/burn surface |
|---|---|
| **Base** — OptimismMintableERC20 (proxied) | `Mint(address indexed account, uint256 amount)` `0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885` + `Burn(address indexed account, uint256 amount)` `0xcc16f5dbb4...` *(2-arg Burn — same topic0 as the FiatToken `Burn`; disambiguate by chain+emitter)* — minted/burned by the L2 Standard Bridge (`0x4200…0010`). |
| **Optimism** — OptimismMintableERC20 | same OP-mintable `Mint`/`Burn` pair as Base. |
| **Arbitrum** — OZ BeaconProxy custom token | ERC-20 only in sampled use; mint/burn is bridge-gated (not the OP-mintable ABI). |
| **Polygon** — Frax fxPortal `FXERC20` (`fxcbETH`) | fxPortal deposit/withdraw mint/burn; ERC-20 `Transfer` from/to `0x0`. |

> None of the bridged tokens emit `ExchangeRateUpdated` — the rate lives only on Ethereum. Cross-chain consumers must read the Ethereum `exchangeRate()` (or a Chainlink feed), never a local one.

---

## 2. Function signatures (chain-agnostic — `selector = keccak256(signature)[0:4]`)

**bytecode** = confirmed present in the live Ethereum implementation (`0x31724Ca0…`, PUSH4-dispatcher scan; proxy resolved to impl first). All selectors below were found in that implementation.

### 2.1 cbETH token (Ethereum implementation)

| Selector | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `0x3ba0b9a9` | `exchangeRate()` | `uint256` | **ETH per 1 cbETH (1e18).** The value-accrual anchor. ✓ live ≈ `1.1321e18`. |
| `0xb9e205ae` | `updateExchangeRate(uint256 newExchangeRate)` | — | **Oracle-only.** Pushes the off-chain rate → emits `ExchangeRateUpdated`. The key write to monitor. |
| `0x40c10f19` | `mint(address _to, uint256 _amount)` | `bool` | Minter-only; emits `Mint` + `Transfer` from `0x0`. |
| `0x42966c68` | `burn(uint256 _amount)` | — | Minter burns own balance; emits `Burn` + `Transfer` to `0x0`. |
| `0x4e44d956` | `configureMinter(address minter, uint256 minterAllowedAmount)` | `bool` | Master-minter sets a minter's allowance; emits `MinterConfigured`. |
| `0x3092afd5` | `removeMinter(address minter)` | `bool` | emits `MinterRemoved`. |
| `0xaa271e1a` | `isMinter(address account)` | `bool` | |
| `0x8a6db9c3` | `minterAllowance(address minter)` | `uint256` | |
| `0xaa20e1e4` | `updateMasterMinter(address _newMasterMinter)` | — | emits `MasterMinterChanged`. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | — | Pauser-only; emit `Pause`/`Unpause`. |
| `0x554bab3c` | `updatePauser(address _newPauser)` | — | emits `PauserChanged`. |
| `0xf9f92be4` / `0x1a895266` | `blacklist(address _account)` / `unBlacklist(address _account)` | — | Blacklister-only; emit `Blacklisted`/`UnBlacklisted`. |
| `0xad38bf22` | `updateBlacklister(address _newBlacklister)` | — | emits `BlacklisterChanged`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | — | emits `OwnershipTransferred`. |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | — | EIP-2612 gasless approval. |
| `0x70a08231` / `0x18160ddd` | `balanceOf(address)` / `totalSupply()` | `uint256` | **Non-rebasing** — unaffected by yield. |
| `0x095ea7b3` / `0xa9059cbb` / `0x23b872dd` | `approve` / `transfer` / `transferFrom` | `bool` | ERC-20. |
| `0x35d99f35` | `masterMinter()` | `address` | |

### 2.2 FiatTokenProxy (Ethereum) — admin-only proxy methods

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | proxy-admin-only; emits `Upgraded`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | proxy-admin-only. |
| `0x5c60da1b` | `implementation()` | returns the current impl (callable on the proxy; ✓ returns `0x31724Ca0…`). |
| `0xf851a440` | `admin()` | proxy admin (admin-context only). |
| `0x8f283970` | `changeAdmin(address newAdmin)` | emits `AdminChanged`. |

> **Selector clash with the impl is resolved by the admin gate.** On a `FiatTokenProxy`, the *proxy admin* address hits the proxy's own `upgradeTo`/`admin`/`changeAdmin`; everyone else falls through to the implementation. The token's `implementation()` (`0x5c60da1b`) is readable by anyone.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

Every address has on-chain code (verified `eth_getCode`). The proxy uses the **legacy zos unstructured-storage** slots, **not** standard EIP-1967 (the EIP-1967 impl/admin slots read **zero** on this contract — confirmed live).

| Role | Address | One-liner |
|------|---------|-----------|
| **cbETH (FiatTokenProxy)** | `0xBe9895146f7AF43049ca1c1AE358B0541Ea49704` | The canonical token; everything in §1–§2 is emitted/called here. |
| cbETH implementation (live) | `0x31724Ca0C982a31fbb5C57f4217AB585271fC9a5` | FiatToken fork + exchangeRate logic. Resolve via `implementation()` — **read live, it changes on `Upgraded`.** |
| Proxy admin (upgrade authority) | `0xDeD1F5e7FB71c1740AebC09b6B0a5e24B0Cb71D1` | Holds **no code** (Coinbase-controlled admin key); sole `upgradeTo`/`changeAdmin` caller. Read from the zos admin slot. |
| Exchange-rate oracle (observed) | `0x9b37180d847B27ADC13C2277299045C1237Ae281` | Coinbase EOA seen calling `updateExchangeRate` / indexed in `ExchangeRateUpdated`. Off-chain-operated; may rotate — verify live. |

**Storage slots for this proxy** (legacy zeppelinos, recomputed locally):
- impl slot `0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3` = `keccak256("org.zeppelinos.proxy.implementation")` → currently `0x31724Ca0…`
- admin slot `0x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b` = `keccak256("org.zeppelinos.proxy.admin")` → currently `0xDeD1F5e7…`

---

## 4. Addresses — bridged cbETH (per-chain mirrors)

Each bridged token has a **different address and a different bridge mechanism**; the Ethereum address holds **no code** on any L2 (verified `0x` on all six). All are 18-decimal ERC-20s; none carries `exchangeRate()`.

### 4.1 Base (chain ID 8453)
| Role | Address | One-liner |
|------|---------|-----------|
| **cbETH** | `0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22` | **Coinbase-native bridged token** via the Base **L2 Standard Bridge** (`0x4200…0010` = `bridge()`); `l1Token()` = the Ethereum cbETH. **Behind an EIP-1967 proxy** (impl `0x07a71b9b835c9EBa242836704D17DA0953324E1f`, admin `0xd94e416cF2c7167608B2515B7e4102B41efff94f`). Largest L2 supply (~44.6k). |

### 4.2 Arbitrum One (chain ID 42161)
| Role | Address | One-liner |
|------|---------|-----------|
| **cbETH** | `0x1DEBd73E752bEaF79865Fd6446b0c970eAE7732f` | Bridged token behind an **OpenZeppelin BeaconProxy** (beacon `0xe72bA9418B5f2cE0A6a40501Fe77C6839aa37333`, beacon impl `0x3f770aC673856f105b586bB393D122721265Ad46`, beacon owner `0xCF57572261C7c2bcf21FfD220eA7d1a27D40a827`). **Not** the Arbitrum standard-gateway token (no `l1Token()`/`l2Gateway()`). Supply ~229. |

### 4.3 Optimism (chain ID 10)
| Role | Address | One-liner |
|------|---------|-----------|
| **cbETH** | `0xadDb6A0412DE1BA0F936DCaeb8Aaa24578dcF3B2` | **OptimismMintableERC20**, **non-proxy** (EIP-1967 slot zero); `l1Token()` = the Ethereum cbETH. OP Standard Bridge native rep. Supply ~23. |

### 4.4 Polygon PoS (chain ID 137)
| Role | Address | One-liner |
|------|---------|-----------|
| **fxcbETH** | `0x4b4327dB1600B8B1440163F667e199CEf35385f5` | **Frax fxPortal `FXERC20`** (symbol `fxcbETH`, name "Coinbase Wrapped Staked ETH (FXERC20)"), **EIP-1167 minimal-proxy clone** of `0xad87E3B217c66B0d45deafBC540330D300811b94`. **Third-party (Frax) bridge, not Coinbase-native** — the only Polygon representation found; no first-party PoS-bridged cbETH. Supply ~19. |

### 4.5 NOT deployed / decoys
| Chain | Finding |
|-------|---------|
| **BNB Smart Chain (56)** | **No canonical cbETH.** A look-alike at `0x691b302b4f2030c53773C7436Ad8C9bc6035f341` reports name "Coinbase Wrapped Staked ETH" / symbol `CBETH` but has **decimals = 9** (real cbETH is 18), a fixed round supply (100,001), **no standard bridge/mint interface, and no recent Transfer activity** → treat as a **dormant decoy**, not the protocol token. |
| **Avalanche C-Chain (43114)** | **Absent.** No cbETH deployment found (the Ethereum/BNB candidate addresses return `0x` here). |

---

## 5. Cross-chain summary

| Chain (ID) | cbETH address | Bridge / kind | Proxy | exchangeRate? |
|---|---|---|---|---|
| Ethereum (1) | `0xBe9895146f7AF43049ca1c1AE358B0541Ea49704` | **canonical** (FiatToken fork) | zos unstructured-storage proxy | **yes** |
| Base (8453) | `0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22` | Coinbase L2 Standard Bridge (OP-mintable) | EIP-1967 proxy | no |
| Arbitrum (42161) | `0x1DEBd73E752bEaF79865Fd6446b0c970eAE7732f` | Coinbase BeaconProxy token | OZ BeaconProxy | no |
| Optimism (10) | `0xadDb6A0412DE1BA0F936DCaeb8Aaa24578dcF3B2` | OP Standard Bridge (OP-mintable) | — (non-proxy) | no |
| Polygon (137) | `0x4b4327dB1600B8B1440163F667e199CEf35385f5` | **Frax fxPortal** (`fxcbETH`, 3rd-party) | EIP-1167 clone | no |
| BNB (56) | *(decoy `0x691b…f341`, decimals=9)* | — | — | no |
| Avalanche (43114) | — (absent) | — | — | — |

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority |
|----------|---------|-----------|-------------------|
| **Ethereum cbETH** | **Legacy OZ `AdminUpgradeabilityProxy` (zos unstructured storage)** | EIP-1967 slots read **zero**; read impl at zos slot `0x7050c9e0…f8c3`, admin at `0x10d6a54a…390b`. `implementation()` (`0x5c60da1b`) is public. Emits `Upgraded`/`AdminChanged`. | Proxy admin key `0xDeD1F5e7…` (Coinbase-controlled, an EOA — no code). |
| **Base cbETH** | **EIP-1967 proxy** | impl slot `0x3608…2bbc` = `0x07a71b9b835c9EBa242836704D17DA0953324E1f`; admin slot = `0xd94e416cF2c7167608B2515B7e4102B41efff94f`. | Base ProxyAdmin `0xd94e416c…`. |
| **Arbitrum cbETH** | **OZ BeaconProxy** | EIP-1967 impl slot zero; **beacon** slot `0xa3f0…3d50` = `0xe72bA9418B5f2cE0A6a40501Fe77C6839aa37333`; `UpgradeableBeacon.implementation()` = `0x3f770aC6…`. | Beacon owner `0xCF575722…`. |
| **Optimism cbETH** | **non-proxy** (immutable logic) | EIP-1967 impl slot zero; no beacon; standard OptimismMintableERC20 bytecode. | n/a (bridge-controlled mint/burn). |
| **Polygon fxcbETH** | **EIP-1167 minimal-proxy clone** | runtime `363d3d373d3d3d363d73 ad87e3b217c66b0d45deafbc540330d300811b94 5af43d82803e903d91602b57fd5bf3`. | Frax fxPortal governance (third-party). |

> **No single canonical cross-chain address and no single proxy pattern** — every chain differs. Always resolve the live implementation on the chain you're indexing (impl slot / beacon / clone target) and never assume the Ethereum admin surface applies to a bridged token.

---

## 7. Detection invariants & gotchas

1. **cbETH never rebases — track the rate, not balances.** Yield accrues by `exchangeRate()` rising; `balanceOf`/`totalSupply` are unaffected. The only yield event is **`ExchangeRateUpdated(address indexed oracle, uint256 newExchangeRate)`** (`0x0b4e9390…`, ✓), Ethereum-only, ~daily. A *falling* or *frozen* rate is the protocol-health red flag.
2. **The exchange rate is off-chain-pushed — that's the key trust assumption.** A single Coinbase oracle EOA (observed `0x9b37…Ae281`) calls `updateExchangeRate`. Watch for: rate pushes from an **unexpected sender**, an **abnormal jump**, or a **long gap** between pushes. There is no on-chain validator/withdrawal machinery to cross-check against.
3. **`Upgraded` on the Ethereum proxy is the top alert.** Legacy zos proxy → a new impl can rewrite mint/burn/rate/admin. Also watch `AdminChanged`, `MasterMinterChanged`, `PauserChanged`, `BlacklisterChanged`, and `MinterConfigured`/`MinterRemoved` — this is a fully-permissioned token.
4. **It's a USDC/FiatToken fork.** Expect `Pause`/`Unpause` (whole-token freeze), `Blacklisted`/`UnBlacklisted` (per-address freeze + balance-wipe-on-blacklist semantics), and the master-minter/minter two-tier issuance. These admin powers are live and real.
5. **`Mint`/`Burn` vs `Transfer`.** Coinbase issuance/redemption = `Mint`(minter,to)/`Burn`(burner) **plus** a `Transfer` from/to `0x0`. To isolate primary issuance from secondary trading, key on `Mint`/`Burn`, not on zero-address `Transfer`s alone.
6. **`Burn` topic0 collision across chains.** The FiatToken `Burn(address,uint256)` (`0xcc16f5db…`) and the OptimismMintableERC20 `Burn(address,uint256)` on Base/Optimism share **the same topic0** — disambiguate by chain + emitting contract. Base/OP `Mint(address,uint256)` (`0x0f6798a5…`) is a **different** 2-arg event from Ethereum's 3-arg `Mint(address,address,uint256)` (`0xab8530f8…`).
7. **No standard EIP-1967 on Ethereum.** Reading slot `0x3608…2bbc` on the Ethereum cbETH returns zero — you'll wrongly conclude "not a proxy". Use the **zos** slots (`0x7050c9e0…` / `0x10d6a54a…`) or `implementation()`.
8. **Bridged tokens are address- and bridge-specific.** Base = OP Standard Bridge (proxied), Optimism = OP Standard Bridge (non-proxy), Arbitrum = a Coinbase BeaconProxy token, Polygon = a **third-party Frax fxPortal** `fxcbETH`. None has `exchangeRate()`; read the Ethereum rate (or a Chainlink feed) for cross-chain pricing.
9. **BNB look-alike is a decoy.** `0x691b…f341` carries the cbETH name/symbol but is **9-decimal**, fixed-supply, inert — do **not** index it as cbETH. **No canonical cbETH on BNB or Avalanche.**
10. **Polygon is `fxcbETH`, not first-party cbETH.** The Polygon representation is a Frax-bridged FXERC20 minimal-proxy clone — fine to track as the on-chain Polygon cbETH, but understand its mint/burn and risk are governed by Frax's fxPortal, not Coinbase.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TRANSFER               = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL               = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_EXCHANGE_RATE_UPDATED  = '\x0b4e9390054347e2a16d95fd8376311b0d2deedecba526e9742bcaa40b059f0b'  -- (oracle, newRate) ETH-only
TOPIC_MINT                   = '\xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8'  -- Mint(address,address,uint256) ETH
TOPIC_BURN                   = '\xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'  -- Burn(address,uint256); also OP-mintable burn
TOPIC_MINTER_CONFIGURED      = '\x46980fca912ef9bcdbd36877427b6b90e860769f604e89c0e67720cece530d20'
TOPIC_MINTER_REMOVED         = '\xe94479a9f7e1952cc78f2d6baab678adc1b772d936c6583def489e524cb66692'
TOPIC_MASTER_MINTER_CHANGED  = '\xdb66dfa9c6b8f5226fe9aac7e51897ae8ee94ac31dc70bb6c9900b2574b707e6'
TOPIC_PAUSE                  = '\x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625'
TOPIC_UNPAUSE                = '\x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33'
TOPIC_PAUSER_CHANGED         = '\xb80482a293ca2e013eda8683c9bd7fc8347cfdaeea5ede58cba46df502c2a604'
TOPIC_BLACKLISTED            = '\xffa4e6181777692565cf28528fc88fd1516ea86b56da075235fa575af6a4b855'
TOPIC_UNBLACKLISTED          = '\x117e3210bb9aa7d9baff172026820255c6f6c30ba8999d1c2fd88e2848137c4e'
TOPIC_BLACKLISTER_CHANGED    = '\xc67398012c111ce95ecb7429b933096c977380ee6c421175a71a4a4c6c88c06e'
TOPIC_OWNERSHIP_TRANSFERRED  = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- proxy (Ethereum)
TOPIC_UPGRADED               = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED          = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
-- bridged OP-mintable Mint (Base/Optimism), 2-arg
TOPIC_OP_MINT                = '\x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'

-- ===== Selectors =====
SEL_EXCHANGE_RATE            = '\x3ba0b9a9'   -- exchangeRate()
SEL_UPDATE_EXCHANGE_RATE     = '\xb9e205ae'   -- updateExchangeRate(uint256)  (oracle-only write)
SEL_MINT                     = '\x40c10f19'   -- mint(address,uint256)
SEL_BURN                     = '\x42966c68'   -- burn(uint256)
SEL_CONFIGURE_MINTER         = '\x4e44d956'   -- configureMinter(address,uint256)
SEL_REMOVE_MINTER            = '\x3092afd5'   -- removeMinter(address)
SEL_PAUSE                    = '\x8456cb59'   -- pause()
SEL_UNPAUSE                  = '\x3f4ba83a'   -- unpause()
SEL_BLACKLIST                = '\xf9f92be4'   -- blacklist(address)
SEL_UNBLACKLIST              = '\x1a895266'   -- unBlacklist(address)
SEL_PERMIT                   = '\xd505accf'   -- permit(...)
SEL_UPGRADE_TO               = '\x3659cfe6'   -- upgradeTo(address)
SEL_UPGRADE_TO_AND_CALL      = '\x4f1ef286'   -- upgradeToAndCall(address,bytes)
SEL_IMPLEMENTATION           = '\x5c60da1b'   -- implementation()

-- ===== Addresses =====
-- Ethereum (chain ID 1)
ETH_CBETH                    = '\xbe9895146f7af43049ca1c1ae358b0541ea49704'  -- FiatTokenProxy (the token)
ETH_CBETH_IMPL               = '\x31724ca0c982a31fbb5c57f4217ab585271fc9a5'  -- live impl (read implementation())
ETH_CBETH_PROXY_ADMIN        = '\xded1f5e7fb71c1740aebc09b6b0a5e24b0cb71d1'  -- upgrade authority (EOA)
ETH_CBETH_RATE_ORACLE        = '\x9b37180d847b27adc13c2277299045c1237ae281'  -- observed exchange-rate pusher
-- Bridged
BASE_CBETH                   = '\x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22'  -- 8453, EIP-1967 proxy, OP-mintable
BASE_CBETH_IMPL              = '\x07a71b9b835c9eba242836704d17da0953324e1f'
ARB_CBETH                    = '\x1debd73e752beaf79865fd6446b0c970eae7732f'  -- 42161, BeaconProxy
ARB_CBETH_BEACON             = '\xe72ba9418b5f2ce0a6a40501fe77c6839aa37333'
OP_CBETH                     = '\xaddb6a0412de1ba0f936dcaeb8aaa24578dcf3b2'  -- 10, OptimismMintableERC20 (non-proxy)
POLY_FXCBETH                 = '\x4b4327db1600b8b1440163f667e199cef35385f5'  -- 137, Frax fxPortal clone (3rd-party)
-- BNB look-alike DECOY (decimals=9, dormant — NOT the protocol token)
BNB_CBETH_DECOY              = '\x691b302b4f2030c53773c7436ad8c9bc6035f341'

-- ===== Storage slots =====
ZOS_IMPL_SLOT                = '\x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3'  -- Ethereum cbETH proxy impl
ZOS_ADMIN_SLOT               = '\x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b'  -- Ethereum cbETH proxy admin
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'  -- Base proxy
EIP1967_BEACON_SLOT          = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'  -- Arbitrum proxy
```

---

## 9. Verification & sources

- **keccak-256:** every topic0 and selector recomputed locally from the canonical signature and cross-checked against known ERC-20 `Transfer`/`Approval` constants before use. The zos proxy slots were recomputed as `keccak256("org.zeppelinos.proxy.implementation"/".admin")`.
- **Topics (✓):** `Transfer`, `Approval`, `ExchangeRateUpdated`, `Mint`, `Burn` observed verbatim in live `eth_getLogs` on `https://ethereum-rpc.publicnode.com` (deployment-era and recent windows) — `ExchangeRateUpdated` topic1 = the oracle EOA, `Mint` = 3 topics, `Burn` = 2 topics. Admin/blacklist/pause events marked `src` (verified-source signature; rare/not in sampled windows).
- **Selectors (bytecode):** PUSH4-dispatcher scan of the live Ethereum implementation `0x31724Ca0…` (resolved from the proxy's zos impl slot) — all listed selectors present. `exchangeRate()` returned `≈1.1321e18` via live `eth_call`.
- **Addresses & proxies:** every address existence-checked with `eth_getCode`; proxy types confirmed by live slot reads — Ethereum = zos slots (EIP-1967 zero), Base = EIP-1967 impl/admin, Arbitrum = EIP-1967 beacon slot + `UpgradeableBeacon.implementation()`, Optimism = no proxy slot (`l1Token()` = Ethereum cbETH), Polygon = EIP-1167 clone runtime decoded. Bridged decimals/totalSupply read live (all 18-dec except the BNB decoy = 9).
- **Absences:** the Ethereum address holds `0x` code on all six other chains; BNB candidate is a 9-decimal dormant decoy; no Avalanche deployment found.

Authoritative sources:

- Coinbase official — [cbETH product page](https://www.coinbase.com/cbeth) · [cbETH help / intro](https://help.coinbase.com/en/coinbase/coinbase-staking/staking/cbeth-intro).
- Verified implementation source / token pages — [Etherscan cbETH](https://etherscan.io/token/0xbe9895146f7af43049ca1c1ae358b0541ea49704) · [Basescan cbETH](https://basescan.org/token/0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22) · [Arbiscan cbETH](https://arbiscan.io/token/0x1debd73e752beaf79865fd6446b0c970eae7732f) · [Optimistic Etherscan cbETH](https://optimistic.etherscan.io/token/0xaddb6a0412de1ba0f936dcaeb8aaa24578dcf3b2) · [PolygonScan fxcbETH](https://polygonscan.com/token/0x4b4327db1600b8b1440163f667e199cef35385f5).
- Code lineage — Circle/Centre `FiatToken` (USDC) reference implementation that cbETH forks.

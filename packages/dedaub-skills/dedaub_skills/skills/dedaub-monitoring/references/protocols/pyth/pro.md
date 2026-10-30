# Pyth Pro (Lazer verifier) — Topics, Selectors, Addresses (Ethereum, Base, BNB, Arbitrum, Polygon, Robinhood Chain, Arc)

**Status:** verified against live RPC on all nine target chains and the canonical `pyth-network/pyth-crosschain` repo on 2026-10-30.
**Scope:** the Pyth Pro on-chain verifier (`PythLazer`, source in `lazer/contracts/evm/src/`). Chains with the canonical contract: Ethereum (1), Base (8453), BNB (56), Arbitrum (42161), Polygon (137), Robinhood Chain (4663), Arc (5042). Not on Avalanche (43114). Optimism (10) has a different, older build at the same literal. Topics and selectors are chain-agnostic. Addresses are network-specific.

Pyth Pro (formerly "Pyth Lazer") delivers low-latency prices signed by a Pyth signer key, not by Wormhole guardians. The contract **stores no price**. A consumer calls `verifyUpdate(bytes)` with a fee inside its own transaction. The function checks the ECDSA signature against the trusted-signer list and returns the payload. **A successful verification emits no event.** Monitor the call, not a log.

The contract has one canonical address on all seven chains, `0xACeA761c27A909d4D3895128EBe6370FDE2dF481`. It is an EIP-1967 UUPS proxy (OpenZeppelin v5). The owner on each chain is that chain's Pyth governance Executor (see [core.md](core.md) §3.4).

---

## 1. Topics (chain-agnostic)

| topic0 | Event |
|--------|-------|
| `0xaa8526c81766fdf5a7d35d60b700ee7d06af554b023ff0946db07c0bae8f7902` | `VerificationFeeSet(uint256 oldFee, uint256 newFee)` — owner only |
| `0xc0819c13be868895eb93e40eaceb96de976442fa1d404e5c55f14bb65a8c489a` | `FeesWithdrawn(address recipient, uint256 amount)` — owner only |
| `0xaf73b0b217208b61be286bbc37095bce7eb8b9ccf617244c2f0f154e8e04e3ff` | `RefundFailed(address indexed payee, uint256 amount)` — overpaid fee could not be returned |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed, address indexed)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64)` (OpenZeppelin v5) |

`updateTrustedSigner` emits **no event**. A signer-key change is visible only as a call.

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x197e1a5a` | `verifyUpdate(bytes)` | payable → `(bytes payload, address signer)`; the consumer path; no event |
| `0x9feb088c` | `updateTrustedSigner(address,uint256)` | **owner only**; adds, extends or removes (`expiresAt = 0`) a signer key — critical |
| `0xaae9d5f2` | `setVerificationFee(uint256)` | owner only |
| `0x164e68de` | `withdrawFees(address)` | owner only |
| `0xd5f50582` | `isValidSigner(address)` | view |
| `0x1d9c68c3` | `getTrustedSigners()` | view → `(address pubkey, uint256 expiresAt)[]` |
| `0xbac12f87` | `verification_fee()` | view |
| `0x54fd4d50` | `version()` | view (`0.3.0`) |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | owner only (UUPS) |
| `0xf2fde38b` | `transferOwnership(address)` | owner only |

## 3. Addresses

All checked with `eth_getCode` on 2026-10-30.

| Chain | ID | Pyth Pro | Code | Implementation | `version()` | `owner()` (= Executor) |
|-------|----|----------|------|----------------|-------------|------------------------|
| Ethereum | 1 | `0xACeA761c27A909d4D3895128EBe6370FDE2dF481` | 183 B | `0xa089a10d05ce37f4b99dc4f1824ba253434a779e` | 0.3.0 | `0xCcD7e24e71ba746CBc758C39CBAb11f4E0dfc46F` |
| Base | 8453 | same | 183 B | same | 0.3.0 | `0xf0a1b566B55e0A0CB5BeF52Eb2a57142617Bee67` |
| BNB | 56 | same | 183 B | same | 0.3.0 | `0x26DD80569a8B23768A1d80869Ed7339e07595E85` |
| Arbitrum | 42161 | same | 176 B | same | 0.3.0 | `0x24654078A8E043e8985D962a5100CDfA2026f92C` |
| Polygon | 137 | same | 183 B | same | 0.3.0 | `0xEbe57e8045F2F230872523bbff7374986E45C486` |
| Robinhood | 4663 | same | 183 B | same | 0.3.0 | `0x0708325268dF9F66270F1401206434524814508b` |
| Arc | 5042 | same | 183 B | same | 0.3.0 | `0x0708325268dF9F66270F1401206434524814508b` |

- **Avalanche:** `eth_getCode` returns `0x`. Not deployed.
- **Optimism:** the literal holds a 176 B proxy with implementation `0x486908b534e34d1ca04d12f01b5bf47ac62a68f5`, `version() = 0.1.1` and `owner() = 0x78357316239040e19fc823372cc179ca75e64b81` (not the Optimism Executor). The docs page says Optimism has **no** Pyth Pro contract. Treat it as an old, unlisted build.

## 4. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Pyth Pro** | EIP-1967 UUPS (OpenZeppelin v5) | impl slot non-zero; admin slot empty; one implementation `0xa089…779e` (8,010 B) on all seven canonical chains | `owner()` = the chain's Executor, which acts only on Pyth governance VAAs |

## 5. Detection invariants & gotchas

1. **No consumption log.** `verifyUpdate` returns data and emits nothing. Use traces or call data (selector `0x197e1a5a`, `to = 0xACeA…F481`) to count use.
2. **Signer rotation is silent.** `updateTrustedSigner` emits nothing. Alert on the call, or poll `getTrustedSigners()`.
3. **Same address, same implementation on seven chains.** Optimism is the exception (older build, different owner).
4. **Owner = Executor.** A governance change reaches Pyth Pro as an `execute(bytes)` call on the Executor that calls into this contract.
5. **Live evidence:** `VerificationFeeSet` was logged on Ethereum at block 26,306,172 (tx `0x960a2d4c8764a5e691234bf07c80cb22f6a9b88044a0319d189f0e1acfed90c6`).

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics =====
TOPIC_PRO_VERIFICATION_FEE_SET = '\xaa8526c81766fdf5a7d35d60b700ee7d06af554b023ff0946db07c0bae8f7902'
TOPIC_PRO_FEES_WITHDRAWN       = '\xc0819c13be868895eb93e40eaceb96de976442fa1d404e5c55f14bb65a8c489a'
TOPIC_PRO_REFUND_FAILED        = '\xaf73b0b217208b61be286bbc37095bce7eb8b9ccf617244c2f0f154e8e04e3ff'
TOPIC_UPGRADED                 = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors =====
SEL_PRO_VERIFY_UPDATE          = '\x197e1a5a'
SEL_PRO_UPDATE_TRUSTED_SIGNER  = '\x9feb088c'
SEL_PRO_SET_VERIFICATION_FEE   = '\xaae9d5f2'
SEL_PRO_WITHDRAW_FEES          = '\x164e68de'
-- ===== Address (ETH, Base, BNB, Arb, Poly, Robin, Arc) =====
PYTH_PRO = '\xacea761c27a909d4d3895128ebe6370fde2df481'
```

## 7. Verification & sources

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `PythLazer.sol`. Every selector and topic above was found as a constant in the live implementation `0xa089…779e`.
- **Addresses:** from `contract_manager/src/store/contracts/EvmLazerContracts.json` and the docs "Pyth Pro" column. Checked with `eth_getCode`, the EIP-1967 slot, `version()` and `owner()` on all nine chains.

Sources:
- [pyth-network/pyth-crosschain — lazer/contracts/evm/src/PythLazer.sol](https://github.com/pyth-network/pyth-crosschain/tree/main/lazer/contracts/evm/src)
- [Pyth docs — EVM contract addresses](https://docs.pyth.network/price-feeds/contract-addresses/evm)
- [Etherscan](https://etherscan.io/address/0xACeA761c27A909d4D3895128EBe6370FDE2dF481)

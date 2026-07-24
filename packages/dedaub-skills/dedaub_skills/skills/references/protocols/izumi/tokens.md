# iZUMi tokens & governance — iZi, veiZi, iUSD (Compressed Reference)

**Status:** topic0/selectors computed locally with keccak from `izumiFinance/veiZi` source; token + veiZi addresses **on-chain verified** (`symbol()`/`name()`/`token()`, publicnode 2026-06). veiZi function selectors confirmed present in deployed bytecode.
**Scope:** the iZUMi token layer — **`iZi`** ERC-20 governance/reward token, **`veiZi`** interest-bearing **ERC-721 vote-escrow veNFT** (Ethereum-only), **`iUSD`** = **iZUMi Bond USD**, a treasury-backed bond-issued 18-dec stablecoin. DEX = [`iziswap.md`](iziswap.md); mining = [`liquidbox.md`](liquidbox.md); index = [`README.md`](README.md).

---

## Topics (chain-agnostic) — `topic0 -> Event(types)`

### veiZi (ERC-721 vote-escrow; lock iZi → boosting + monthly staking rewards)
```
0x621b671f614e8ed2023af3e491b3d2d895533d7d964005535af4c018d2089674 -> Deposit(uint256,uint256,uint256,int128,uint256)   [nftId(indexed),value,lockBlk(indexed),depositType,timestamp]  (NOT the Curve/Velodrome veNFT layout)
0xa01a72713bf837059e3a668d28f0de277fb7f24f2a4e95bf926703c95b5f12b2 -> Withdraw(uint256,uint256,uint256)                [nftId(indexed),value,timestamp]
0x2bccdce62e5aec7ee273161a374088a6da4311d0e688784bde3c1cec8a3c003a -> Stake(uint256,address)                          [nftId(indexed),owner(indexed) — stake veNFT for rewards]
0x4ac743692c9ced0a3f0052fb9917c0856b6b12671016afe41b649643a89b1ad5 -> Unstake(uint256,address)                        [nftId(indexed),owner(indexed)]
0x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c -> Supply(uint256,uint256)                         [preSupply,supply]  ⚠ COLLIDES with Velodrome/Curve/Balancer veToken Supply
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)               [ERC-721 — veNFT mint/move/burn]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 -> Approval(address,address,uint256)
0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31 -> ApprovalForAll(address,address,bool)
```

### iZi / iUSD (standard ERC-20)
```
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 -> Approval(address,address,uint256)
```

---

## Function signatures (veiZi — all confirmed present in deployed bytecode)
```
0xb52c05fe -> createLock(uint256,uint256) -> uint256          [value,unlockTime → nftId]   (same selector as Velodrome VotingEscrow.createLock — disambiguate by chain/contract)
0xb2383e55 -> increaseAmount(uint256,uint256)                 [nftId,value]
0x9d507b8b -> increaseUnlockTime(uint256,uint256)             [nftId,unlockTime]
0x2e1a7d4d -> withdraw(uint256)                               [nftId — after lock expiry]
0xd1c2babb -> merge(uint256,uint256)                          [nftFrom,nftTo]
0xa694fc3a -> stake(uint256)                                  [nftId — stake veNFT to earn rewards]
0xf7f0b4d6 -> nftLocked(uint256) -> (int128,uint256)          [view: locked amount + end]
            -> stakingInfo(address) -> (uint256,uint256,uint256)   [view: nftId,stakingId,amount — note arg is ADDRESS not uint256]
0xfc0c546a -> token() -> address                              [→ iZi 0x9ad37205…]
```
*(Unstaking emits `Unstake`; staked veNFTs accrue a share of protocol rewards — veiZi is "interest-bearing".)*

---

## Addresses (network-specific)

### iZi — ERC-20 governance/reward token (symbol `iZi`, name `izumi Token`, 18 dec)
```
0x9ad37205d608B8b219e6a2573f922094CEc5c200 -> iZi on ETHEREUM (1)        (original; 9,233 B ✓ symbol "iZi" / name "izumi Token")
0x60D01EC2D5E98Ac51C8B4cF84DfCCE98D527c747 -> iZi (multichain address)   ✓ on BNB (56), Polygon (137), Arbitrum (42161), Base (8453) — same address, symbol "iZi" on all
```
- **Not at `0x60D01EC2…` on Optimism** (code 0 — iZi token absent there despite the DEX being deployed). Also present (same `0x60D01EC2…`) on many non-requested iZiSwap chains (Linea, Mantle, Scroll, Zeta, …); Taiko uses `0xa2FbA3fDe6c9E7386716B577e1258577CB9b5Bf7`, Manta `0x91647632245caBf3d66121F86C387aE0ad295F9A`.

### veiZi — vote-escrow veNFT (**Ethereum mainnet only**)
```
0xB56A454d8DaC2AD4cB82337887717a2a427Fcd00 -> veiZi on ETHEREUM (1)      (20,080 B ✓ symbol "veiZi" / name "iZUMi DAO veNFT" / token()→iZi ✓)
0xfa0ad5F78D1fc96DEF92ef7252b8a548edF6d131 -> veiZi iZi reward provider  (EOA/funder, code 0)
```
- veiZi is **not deployed on BNB/Arbitrum/Polygon/Base/Optimism/Avalanche mainnet** (only Ethereum; a separate `veiZi` exists on BNB **testnet** `0x455562Bf…`). Governance/boost is therefore Ethereum-centric.

### iUSD — **iZUMi Bond USD** (symbol `iUSD`, 18 dec; treasury-backed bond-issued stablecoin)
```
0x0a3bb08b3a15a19b4de82f8acfc862606fb69a2d -> iUSD   ✓ on ETHEREUM (1, 9,233 B), BNB (56), Arbitrum (42161) — same address
```
iUSD is issued via the **iZUMi Bond** product (sold to investors as a bond; "Bond Farming" fixed income). Peg defense: iZUMi commits treasury funds to **buy back & burn iUSD if price < 0.996 USDT for 4 consecutive weeks**. No on-chain depeg/exploit found (2023–2026).

---

## Proxies
- **iZi, iUSD, veiZi are all plain immutable contracts** — no EIP-1967 proxy, no `Upgraded`. veiZi is a standard (non-upgradeable) ERC-721 with vote-escrow + staking logic baked in.

## Detection invariants & gotchas
1. **veiZi `Supply` topic0 `0x5e2aa66e…` is shared** with Velodrome / Curve / Balancer veToken `Supply(uint256,uint256)` — **disambiguate by emitter** (only `0xB56A454d…` on Ethereum is veiZi).
2. **veiZi `Deposit` layout differs from the Curve/Velodrome veNFT** `Deposit`: here it's `(nftId, value, lockBlk, depositType(int128), timestamp)` topic0 `0x621b671f…` — a distinct topic0, do not reuse the Velodrome `0x8835c22a…` constant.
3. **veiZi is keyed by `tokenId` (ERC-721)**, not an ERC-20 balance; locks/stakes reference the NFT. It emits ERC-721 `Transfer`.
4. **`createLock(uint256,uint256)` selector `0xb52c05fe` collides with Velodrome `VotingEscrow.createLock`** — same arg shape; disambiguate by chain/contract.
5. **iZi has two canonical addresses** (`0x9ad37205…` ETH original vs `0x60D01EC2…` multichain) — both report symbol "iZi"; key on `(chainId, address)`.

## Quick-copy bytea-ready constants (Postgres `'\x…'`)
```
veizi_deposit   = '\x621b671f614e8ed2023af3e491b3d2d895533d7d964005535af4c018d2089674'
veizi_withdraw  = '\xa01a72713bf837059e3a668d28f0de277fb7f24f2a4e95bf926703c95b5f12b2'
veizi_stake     = '\x2bccdce62e5aec7ee273161a374088a6da4311d0e688784bde3c1cec8a3c003a'
veizi_unstake   = '\x4ac743692c9ced0a3f0052fb9917c0856b6b12671016afe41b649643a89b1ad5'
veizi_supply    = '\x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c'   # COLLIDES w/ Velodrome/Curve veToken Supply
```

## Verification & sources
- topic0/selectors: local keccak from `izumiFinance/veiZi` `contracts/veiZi.sol`; veiZi function selectors confirmed present in deployed bytecode of `0xB56A454d…`.
- Addresses: `eth_call`/`eth_getCode` vs publicnode — iZi `symbol()`="iZi"/`name()`="izumi Token" on ETH + BNB/Polygon/Arb/Base; veiZi `symbol()`="veiZi"/`name()`="iZUMi DAO veNFT"/`token()`→iZi; iUSD `symbol()`="iUSD"/decimals 18. iZi confirmed **absent** at `0x60D01EC2…` on Optimism.
- Source: [`izumiFinance/veiZi`](https://github.com/izumiFinance/veiZi). DEX = [`iziswap.md`](iziswap.md); mining = [`liquidbox.md`](liquidbox.md); index = [`README.md`](README.md).

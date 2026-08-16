"""
Phase 3: User-Side Trapdoor Generation (Eq. 27-30)

Supports:
  - Single-dimension: Q = (D, [a, b])
  - Conjunctive multi-range: Q = Q_1 ∧ Q_2 ∧ ... ∧ Q_d

Real crypto: ABSE.TokenGen with bilinear pairings (Eq. 30) -- BLS12-381
             via abse_fast if installed, else BN128 via abse_real --
             PRF tags with SHA-256 (Eq. 15-17).
"""

import hashlib

from utils import gen_tag, gen_query_bitmap
from merkle_tree import MerkleTree


class UserClient:
    def __init__(self, secrets):
        self.Ks = secrets["Ks"]
        self.SK_A = secrets["SK_A"]
        self.abse = secrets["abse"]
        self.ec_privkey = secrets.get("ec_privkey")

    def _canonical_cover(self, a, b):
        """Eq. 28: Minimal canonical range-cover set at decile granularity."""
        nodes = []
        for i in range((a // 10) * 10, (b // 10) * 10 + 10, 10):
            nodes.append({"l": i, "r": min(i + 9, 100)})
        return nodes

    def generate_trapdoor(self, m, k, t_slot, a, b):
        """Phase 3: Single-dimension trapdoor (Eq. 27-30).

        Real crypto: ABSE.TokenGen (BN128 pairings), SHA-256 PRF tags.
        """
        cover = self._canonical_cover(a, b)
        tokens, search_tags, auth_token = [], [], None

        for node in cover:
            tag = gen_tag(self.Ks, m, k, t_slot, node)
            search_tags.append(tag)
            tok = self.abse.token_gen(self.SK_A, tag)
            eBQ = gen_query_bitmap(self.Ks, m, k, t_slot, a, b)
            tokens.append({
                "T1": tok["T1"], "T2": tok["T2"],
                "attrs": tok["attrs"], "eBQ": eBQ,
                "l": node["l"], "r": node["r"],
            })
            if auth_token is None:
                auth_token = {"T1": tok["T1"], "T2": tok["T2"], "attrs": tok["attrs"]}

        return {
            "m": m, "k": k, "t_slot": t_slot,
            "range": [a, b], "tokens": tokens,
            "search_tags": search_tags, "auth_token": auth_token,
        }

    def generate_conjunctive_trapdoor(self, m, t_slot, dimensions):
        """Phase 3: Conjunctive multi-range trapdoor (Eq. 27).

        Q = Q_1 ∧ Q_2 ∧ ... ∧ Q_d,  Q_j = (D_j, [a_j, b_j])

        Args:
            m: Machine ID
            t_slot: Time slot
            dimensions: List of {"k": keyword, "a": lo, "b": hi}
                e.g. [{"k":"Temp","a":20,"b":50}, {"k":"Humidity","a":60,"b":80}]

        Returns:
            Conjunctive trapdoor with per-dimension tokens.
        """
        dim_trapdoors = []
        for dim in dimensions:
            td = self.generate_trapdoor(m, dim["k"], t_slot, dim["a"], dim["b"])
            dim_trapdoors.append(td)

        return {
            "m": m, "t_slot": t_slot,
            "type": "conjunctive",
            "d": len(dimensions),
            "dimensions": dim_trapdoors,
        }

    def verify_matched_nodes(self, nodes):
        """Phase 5 Step 1 (Theorem 6/7): verify that every returned
        aggregation-bearing node is included under its claimed index
        root before its ciphertext is trusted/aggregated.

        Each node must carry the fields blockchain_edge.py attaches:
        search_tag, sigma, CT_v, Cnt_u, pi_u, root (Eq. 22-23). Uses a
        single shared Merkle multi-proof across all nodes when every
        node reports the same root (the common case: one query epoch),
        falling back to per-node verify_proof otherwise.

        Raises ValueError naming the first node that fails verification
        (omitted, substituted, or tampered aggregation ciphertext).
        Returns True if every node verifies.
        """
        if not nodes:
            return True

        required = ("search_tag", "sigma", "CT_v", "Cnt_u", "pi_u",
                    "root_idx", "root_agg", "epoch", "root")
        for n in nodes:
            missing = [f for f in required if f not in n]
            if missing:
                raise ValueError(
                    f"Node {n.get('l')}-{n.get('r')} missing verification "
                    f"field(s) {missing}; cannot check integrity"
                )

        def leaf_str(n):
            return f"{n['search_tag']}|{n['sigma']}|{n['CT_v']}|{n['Cnt_u']}"

        def check_epoch_binding(n):
            """Bind the index root to the blockchain-anchored epoch commitment.

            Eq. (p2-epoch-commitment): Root_e = H(Root_idx || Root_agg || e).
            Verifying the Merkle path alone only proves the leaf is in SOME
            tree; this step proves that tree is the one anchored on-chain.
            """
            recomputed = hashlib.sha256(
                f"{n['root_idx']}|{n['root_agg']}|{n['epoch']}".encode()
            ).hexdigest()
            if recomputed != n["root"]:
                raise ValueError(
                    f"Epoch commitment mismatch for node "
                    f"[{n.get('l')},{n.get('r')}] -- the index root does not "
                    f"bind to the anchored epoch root (stale or forged epoch)"
                )

        roots = {n["root_idx"] for n in nodes}
        if len(roots) == 1 and "multi_proof" in nodes[0]:
            # Single shared multi-proof covering every returned node.
            root_idx = roots.pop()
            leaves = {n["multi_proof_index"]: leaf_str(n) for n in nodes}
            if not MerkleTree.verify_multi_proof(leaves, nodes[0]["multi_proof"], root_idx):
                raise ValueError("Merkle multi-proof verification failed "
                                  "for returned node set")
            check_epoch_binding(nodes[0])
            return True

        for n in nodes:
            if not MerkleTree.verify_proof(leaf_str(n), n["pi_u"], n["root_idx"]):
                raise ValueError(
                    f"Merkle proof verification failed for node "
                    f"[{n.get('l')},{n.get('r')}] -- omitted, substituted, "
                    f"or tampered aggregation ciphertext"
                )
            check_epoch_binding(n)
        return True

    def decrypt_aggregate(self, ct_sum_str, ct_cnt_str):
        """Phase 5 Step 4: Decrypt aggregate with sk_AHE (EC-ElGamal BSGS)."""
        if not self.ec_privkey or ct_sum_str == "0":
            return None, None
        from ec_elgamal import ECEncryptedNumber
        ct_sum = ECEncryptedNumber.from_string(self.ec_privkey.public_key, ct_sum_str)
        ct_cnt = ECEncryptedNumber.from_string(self.ec_privkey.public_key, ct_cnt_str)
        return self.ec_privkey.decrypt(ct_sum), self.ec_privkey.decrypt(ct_cnt)

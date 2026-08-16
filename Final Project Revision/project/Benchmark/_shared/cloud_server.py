"""
Phase 4: Cloud-Side Secure Range Query Processing (Eq. 34-38)

The cloud server:
  1. Receives encrypted trapdoor from authorized user
  2. Performs ABSE bilinear pairing test for authorization (Eq. 34)
  3. Applies bitmap-constrained filtering (Eq. 37)
  4. Returns matched encrypted nodes (never sees plaintext)

Real crypto:
  - ABSE.Test: 2 BN128 bilinear pairings per authorization check
  - Bitmap AND: PRF-permuted bit intersection

The cloud NEVER holds MSK, SK_A, sk_AHE, or any secret key.
It operates solely on encrypted structures and public parameters.
"""

import hashlib
try:
    from abse_fast import ABSE  # Rust-native BLS12-381 -- must match
except ImportError:              # whichever backend TA.py/blockchain_edge.py
    from abse_real import ABSE   # actually used to build CT_tag, or
                                  # test() fails to even parse the ciphertext.


class CloudServer:
    def __init__(self, collection):
        self.db = collection

    def process_query(self, trapdoor, abse_instance=None):
        """Phase 4: Conjunctive range query processing.

        Optimization #2: ABSE-once + PRF tag matching.
          1. ONE ABSE.Test to verify user authorization (2 pairings)
          2. PRF tag hash-set matching for remaining nodes (O(1) each)

        Falls back to per-node ABSE.Test if search_tags absent.
        """
        m_enc = hashlib.sha256(trapdoor["m"].encode()).hexdigest()
        k_enc = hashlib.sha256(trapdoor["k"].encode()).hexdigest()

        docs = list(self.db.find({"m_enc": m_enc, "k_enc": k_enc}))

        # ABSE instance — cloud only needs test() (stateless, no secrets)
        abse = abse_instance if abse_instance else ABSE()
        if not abse_instance:
            abse.setup()  # Only public params needed for test()

        if "search_tags" in trapdoor and trapdoor["search_tags"]:
            return self._query_fast(docs, trapdoor, abse)
        return self._query_legacy(docs, trapdoor, abse)

    def _query_fast(self, docs, trapdoor, abse):
        """Optimized: ONE ABSE.Test for auth, then PRF tag matching.

        Step 1: Authorization — ABSE.Test on ONE doc (2 BN128 pairings)
        Step 2: Matching — compare search_tag via O(1) hash set lookup
        """
        auth_token = trapdoor.get("auth_token")
        expected_tags = set(trapdoor["search_tags"])

        # Step 1: ABSE.Test for authorization (real pairings).
        #
        # BUGFIX: this previously tried ONLY auth_token -- the token for the
        # FIRST canonical cover node. ABSE.Test succeeds on keyword equality
        # AND policy satisfaction, so if that particular decile happened to
        # hold no records the test failed against every document and the whole
        # query returned empty. A false negative that depended purely on which
        # decile the range started in. Measured at N=300: this path returned 0
        # matches where the per-node path returned 1.
        #
        # Every cover token is now tried, so authorization succeeds whenever
        # the user is authorized for ANY node present in the index.
        candidate_tokens = trapdoor.get("tokens") or []
        if auth_token:
            candidate_tokens = [auth_token] + list(candidate_tokens)

        authorized = False
        for tok in candidate_tokens:
            if authorized:
                break
            token = {"T1": tok["T1"], "T2": tok["T2"], "attrs": tok["attrs"]}
            for doc in docs:
                ct_tag = doc.get("CT_tag")
                if ct_tag and abse.test(token, ct_tag):
                    authorized = True
                    break

        if not authorized:
            return []

        # Step 2: PRF tag set matching + bitmap filter
        # eBQ is invariant across docs -- parse each token's query bitmap
        # once, outside the per-doc loop (was previously re-parsed on
        # every single doc x token pair).
        query_bitmaps = [self._parse_bitmap(tok["eBQ"]) for tok in trapdoor.get("tokens", [])]

        matched = []
        for doc in docs:
            if query_bitmaps:
                # B_tilde is invariant across tokens for a given doc --
                # parse once per doc, not once per (doc, token) pair.
                b_node = self._parse_bitmap(doc["B_tilde"])
                if not any(b_node & b_query for b_query in query_bitmaps):
                    continue

            if doc.get("search_tag") in expected_tags:
                matched.append(doc)

        return matched

    def _query_legacy(self, docs, trapdoor, abse):
        """Legacy: per-node ABSE.Test (2 BN128 pairings per node)."""
        query_bitmaps = [(tok, self._parse_bitmap(tok["eBQ"])) for tok in trapdoor["tokens"]]

        matched = []
        for doc in docs:
            # B_tilde is invariant across tokens for a given doc.
            b_node = self._parse_bitmap(doc["B_tilde"])
            for tok, b_query in query_bitmaps:
                # Step 1: Bitmap filter (Eq. 37)
                if not (b_node & b_query):
                    continue

                # Step 2: ABSE bilinear pairing test (Eq. 34)
                token = {"T1": tok["T1"], "T2": tok["T2"], "attrs": tok["attrs"]}
                if abse.test(token, doc["CT_tag"]):
                    matched.append(doc)
                    break
        return matched

    @staticmethod
    def _parse_bitmap(b):
        """Parse bitmap from stored format to integer."""
        if isinstance(b, str) and all(c in '01' for c in b):
            return int(b, 2)
        return int(b)

    def process_conjunctive_query(self, conj_trapdoor, abse_instance=None):
        """Phase 4: Conjunctive multi-range query (Eq. 27, Theorem 4).

        Q = Q_1 ∧ Q_2 ∧ ... ∧ Q_d

        For each dimension D_j:
          1. Run process_query to get matched nodes (ABSE.Test + bitmap)
          2. Collect time slots that have matches

        Conjunction: intersect time-slot sets across all dimensions.
        Only nodes from time slots matching ALL dimensions are returned.

        Real crypto: ABSE.Test (BN128 pairings) per dimension,
                     bitmap AND filtering per dimension.
        """
        dimensions = conj_trapdoor["dimensions"]

        # Step 1: Per-dimension matching
        dim_matched = []
        dim_slots = []

        for dim_td in dimensions:
            # Forward the ABSE instance -- omitting it made every dimension
            # construct a fresh ABSE() and run setup(), inflating each
            # conjunctive measurement by a full key generation per dimension.
            matched = self.process_query(dim_td, abse_instance)
            dim_matched.append(matched)
            slots = set()
            for doc in matched:
                slots.add(doc.get("t_slot", doc.get("t", "")))
            dim_slots.append(slots)

        # Step 2: Conjunctive intersection — time slots in ALL dimensions
        if dim_slots:
            common = dim_slots[0]
            for s in dim_slots[1:]:
                common &= s
        else:
            common = set()

        # Step 3: Filter each dimension to only common time slots
        filtered = []
        for i, dim_td in enumerate(dimensions):
            nodes = [d for d in dim_matched[i]
                     if d.get("t_slot", d.get("t", "")) in common]
            filtered.append({
                "k": dim_td["k"],
                "range": dim_td.get("range", []),
                "matched_nodes": nodes,
                "node_count": len(nodes),
            })

        return {
            "type": "conjunctive",
            "d": len(dimensions),
            "common_timeslots": sorted(common),
            "dimensions": filtered,
            "matched_any": len(common) > 0,
        }
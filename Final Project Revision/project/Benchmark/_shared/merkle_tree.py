import hashlib

def _hash(data):
    if isinstance(data, str): data = data.encode()
    return hashlib.sha256(data).hexdigest()

class MerkleTree:
    def __init__(self, leaves):
        # Allow leaves to be pre-hashed or strings
        self.leaves = [_hash(l) for l in leaves]
        self.tree = [self.leaves]
        if self.leaves:
            self._build()

    def _build(self):
        current_level = self.leaves
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                h1 = current_level[i]
                if i + 1 < len(current_level):
                    h2 = current_level[i+1]
                    next_level.append(_hash(f"{h1}{h2}"))
                else:
                    next_level.append(h1)
            self.tree.append(next_level)
            current_level = next_level

    def get_root(self):
        return self.tree[-1][0] if self.tree else ""

    def get_proof(self, index):
        proof = []
        curr_idx = index
        for level in range(len(self.tree) - 1):
            is_right = curr_idx % 2 != 0
            sibling_idx = curr_idx - 1 if is_right else curr_idx + 1
            if sibling_idx < len(self.tree[level]):
                proof.append({"hash": self.tree[level][sibling_idx], "pos": "L" if is_right else "R"})
            curr_idx //= 2
        return proof

    @staticmethod
    def verify_proof(leaf_str, proof, root):
        curr_hash = _hash(leaf_str)
        for sib in proof:
            if sib["pos"] == "L":
                curr_hash = _hash(f"{sib['hash']}{curr_hash}")
            else:
                curr_hash = _hash(f"{curr_hash}{sib['hash']}")
        return curr_hash == root

    def get_multi_proof(self, indices):
        """Batched proof for several leaves at once (paper's
        MerkleMultiProof, Eq. p4-aggregation-proof): internal nodes
        shared by multiple selected leaves are hashed once by the
        verifier and reused, instead of shipping/recomputing an
        independent get_proof() path per leaf.

        Returns the minimal set of sibling hashes, per level, that a
        verifier needs to recompute the root from just these leaves.
        Mirrors _build()'s odd-node-carries-forward convention.
        """
        num_levels = len(self.tree) - 1
        known = {0: set(indices)}
        siblings = {}
        for level in range(num_levels):
            cur = known[level]
            nxt = set()
            for idx in cur:
                parent = idx // 2
                left_idx, right_idx = 2 * parent, 2 * parent + 1
                if right_idx < len(self.tree[level]):
                    other_idx = right_idx if idx == left_idx else left_idx
                    if other_idx not in cur:
                        siblings[(level, other_idx)] = self.tree[level][other_idx]
                nxt.add(parent)
            known[level + 1] = nxt
        return {"indices": list(indices), "siblings": siblings, "num_levels": num_levels}

    @staticmethod
    def verify_multi_proof(leaves, multi_proof, root):
        """Verify several (index, leaf_str) pairs against one root
        using a single shared multi-proof, re-hashing each internal
        node at most once regardless of how many leaves it covers.

        Args:
            leaves: {index: leaf_str} for every leaf being verified.
            multi_proof: output of get_multi_proof() for the same indices.
            root: the claimed Merkle root.
        """
        siblings = multi_proof["siblings"]
        level_hashes = {i: _hash(s) for i, s in leaves.items()}
        # Must climb the tree's FULL height, not stop once only one
        # index remains -- a lone verified leaf still needs num_levels
        # sibling-combines (from the proof) to reach the root.
        for level in range(multi_proof["num_levels"]):
            next_hashes = {}
            for idx in sorted(level_hashes):
                parent = idx // 2
                if parent in next_hashes:
                    continue
                left_idx, right_idx = 2 * parent, 2 * parent + 1
                left = level_hashes.get(left_idx, siblings.get((level, left_idx)))
                right = level_hashes.get(right_idx, siblings.get((level, right_idx)))
                if left is None:
                    return False
                next_hashes[parent] = _hash(f"{left}{right}") if right is not None else left
            level_hashes = next_hashes
        if 0 not in level_hashes or len(level_hashes) != 1:
            return False
        return level_hashes[0] == root

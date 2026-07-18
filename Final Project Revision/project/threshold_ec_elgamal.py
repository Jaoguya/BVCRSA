"""
Threshold EC-ElGamal Decryption over NIST P-256
=================================================
Extends ec_elgamal.py with (t, n) threshold decryption:

  KeyGen:  x <- Z_p             (as in ec_elgamal.py)
  Share:   Shamir-split x into n shares x_1..x_n with a degree-(t-1)
           random polynomial f, x_l = f(l), P_l = x_l * G published.
  PartialDecrypt(TDA_l, ct):
           D_l = x_l * C1
           Chaum-Pedersen NIZK proof that log_G(P_l) == log_C1(D_l)
  Verify:  standard Chaum-Pedersen DLEQ verification of the proof
  Combine: Lagrange-interpolate in the exponent over any t of the
           D_l's to recover x*C1 = sum_l lambda_l * D_l
  Recover: vG = C2 - x*C1, then BSGS lookup (reuses ec_elgamal's table)

This models the BVCRSA threshold-decryption-authority (TDA) network used
in the aggregation experiments: t-of-n authorities must cooperate to
decrypt any ciphertext, and each partial decryption is individually
verifiable via its DLEQ proof before being combined.
"""

import os
import hashlib
from ecdsa import NIST256p

from ec_elgamal import ECEncryptedNumber

_G = NIST256p.generator
_ORDER = NIST256p.order


def _rand_scalar():
    while True:
        r = int.from_bytes(os.urandom(32), "big") % _ORDER
        if r != 0:
            return r


def _point_bytes(P):
    """Serialize an EC point (or None/infinity) for hashing."""
    if P is None:
        return b"INF"
    try:
        return int(P.x()).to_bytes(32, "big") + int(P.y()).to_bytes(32, "big")
    except (AttributeError, TypeError):
        return b"INF"


def _fiat_shamir_challenge(*points):
    h = hashlib.sha256()
    for P in points:
        h.update(_point_bytes(P))
    return int.from_bytes(h.digest(), "big") % _ORDER


class ThresholdKeyShares:
    """Shamir-splits an EC-ElGamal private scalar x into n shares, threshold t."""

    def __init__(self, x, t, n):
        if not (1 <= t <= n):
            raise ValueError("require 1 <= t <= n")
        self.t = t
        self.n = n
        # f(z) = x + a1*z + ... + a_{t-1}*z^{t-1}  (f(0) = x)
        self.coeffs = [x % _ORDER] + [_rand_scalar() for _ in range(t - 1)]
        self.shares = {}         # l -> x_l  (kept only for constructing authorities)
        self.public_shares = {}  # l -> P_l = x_l * G  (public verification key)
        for l in range(1, n + 1):
            xl = self._eval(l)
            self.shares[l] = xl
            self.public_shares[l] = _G * xl

    def _eval(self, z):
        result = 0
        power = 1
        for c in self.coeffs:
            result = (result + c * power) % _ORDER
            power = (power * z) % _ORDER
        return result

    def make_authorities(self):
        return {
            l: ThresholdDecryptionAuthority(l, self.shares[l], self.public_shares[l])
            for l in range(1, self.n + 1)
        }


class ThresholdDecryptionAuthority:
    """One of the n authorities (TDA_l), holding share x_l and public P_l = x_l*G."""

    def __init__(self, index, x_l, P_l):
        self.index = index
        self.x_l = x_l
        self.P_l = P_l

    def decrypt(self, ct: ECEncryptedNumber):
        """Partial decryption D_l = x_l * C1, with a Chaum-Pedersen DLEQ proof
        that log_G(P_l) == log_C1(D_l) == x_l."""
        C1 = ct.C1
        D_l = C1 * self.x_l

        k = _rand_scalar()
        t1 = _G * k
        t2 = C1 * k
        c = _fiat_shamir_challenge(_G, self.P_l, C1, D_l, t1, t2)
        s = (k + c * self.x_l) % _ORDER

        return D_l, (c, s)


def verify_dleq(C1, P_l, D_l, proof):
    """Verify a Chaum-Pedersen DLEQ proof for (G, P_l) vs (C1, D_l)."""
    c, s = proof
    neg_c = (_ORDER - c) % _ORDER
    t1p = _G * s + P_l * neg_c
    t2p = C1 * s + D_l * neg_c
    c2 = _fiat_shamir_challenge(_G, P_l, C1, D_l, t1p, t2p)
    return c2 == c


def _lagrange_coeff(indices, j):
    """Lagrange coefficient lambda_j for interpolating f(0) from points `indices`."""
    num, den = 1, 1
    for m in indices:
        if m == j:
            continue
        num = (num * ((-m) % _ORDER)) % _ORDER
        den = (den * ((j - m) % _ORDER)) % _ORDER
    return (num * pow(den, -1, _ORDER)) % _ORDER


def combine_partial_decryptions(partials):
    """partials: list of (index, D_l). Returns x*C1 via exponent-Lagrange interpolation."""
    indices = [idx for idx, _ in partials]
    combined = None
    for idx, D_l in partials:
        lam = _lagrange_coeff(indices, idx)
        term = D_l * lam
        combined = term if combined is None else combined + term
    return combined


def threshold_decrypt(ct, authorities, chosen_indices, bsgs_privkey):
    """Full (t,n) threshold decryption of `ct` using the authorities at
    `chosen_indices`, verifying each partial decryption's DLEQ proof before
    combining, then recovering the plaintext via `bsgs_privkey`'s BSGS table.

    Returns (plaintext, partials) where partials is the list of (index, D_l)
    used, so callers can separately time each phase if desired.
    """
    partials = []
    for idx in chosen_indices:
        auth = authorities[idx]
        D_l, proof = auth.decrypt(ct)
        if not verify_dleq(ct.C1, auth.P_l, D_l, proof):
            raise ValueError(f"DLEQ verification failed for authority {idx}")
        partials.append((idx, D_l))

    xC1 = combine_partial_decryptions(partials)
    neg_xC1 = xC1 * ((_ORDER - 1) % _ORDER)
    vG = ct.C2 + neg_xC1

    plaintext = bsgs_privkey.recover_from_point(vG)
    return plaintext, partials

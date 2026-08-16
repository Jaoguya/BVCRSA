"""Constants for ECGRQ-LI (ref15, Li et al., IEEE ToC 2025).

Salvaged from the standalone ECGRQ folder. MongoDB settings and the live
Atlas credential string have been REMOVED -- the pipeline is CSV-only now.

Status: ECGRQ-LI is cited in Related Work but is NOT one of the four
benchmarked baselines (Trinity/ref26, ABSE-Range/ref27, Latt-IBEKS/ref28,
VC-KASE/ref16). This file exists so the learned index can be promoted to a
baseline if reviewers ask for one; nothing currently imports it.
"""

# Learned index
TRAINING_ROUNDS = 50
HIDDEN_NEURONS = 128
LR = 0.0001
BATCH_SIZE = 1000
EPSILON_VALUES = [0.2, 0.4, 0.6, 0.8, 1.0]

# Query / dataset shape
DATASET_SIZES = [200_000, 400_000, 600_000, 800_000, 1_000_000]
ATTRIBUTE_SIZES = [2, 3, 4, 5, 6]
QUERY_REGION = 64
NUM_ATTRS = 3

# Spatial domain (Geolife / Beijing)
LAT_MIN, LAT_MAX = 39.0, 41.0
LON_MIN, LON_MAX = 115.0, 117.5
Z_BITS = 16

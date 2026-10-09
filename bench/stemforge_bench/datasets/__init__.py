from . import procedural, slakh, vocalmix

DATASETS = {"procedural": procedural.load, "babyslakh": slakh.load, "vocalmix": vocalmix.load}

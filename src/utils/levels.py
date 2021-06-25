import math

from utils.translations import fake_translation as _


LEVELS = [
    {"level": -3, "expMin": -999999,  "name": _("Negative cheater ?"), "accuracy": 95, "reliability": 85, "bullets": 6, "magazines": 1}, # Beginner's luck
    {"level": -2, "expMin": -99999,  "name": _("Duck Hugger ?"), "accuracy": 95, "reliability": 85, "bullets": 6, "magazines": 1}, # Beginner's luck
    {"level": -1, "expMin": -9999,  "name": _("What are you doing ?"), "accuracy": 95, "reliability": 85, "bullets": 6, "magazines": 1}, # Beginner's luck
    {"level": 0, "expMin": -999,  "name": _("public danger"), "accuracy": 95, "reliability": 85, "bullets": 6, "magazines": 1}, # Beginner's luck
    {"level": 1, "expMin": -6,    "name": _("tourist"), "accuracy": 90, "reliability": 85, "bullets": 6, "magazines": 2},  # Beginner's luck
    {"level": 2, "expMin": 20,    "name": _("noob"), "accuracy": 70, "reliability": 86, "bullets": 6, "magazines": 2},     # Beginner's luck
    {"level": 3, "expMin": 50,    "name": _("trainee"), "accuracy": 54, "reliability": 87, "bullets": 6, "magazines": 2},  # Beginner's luck
    {"level": 4, "expMin": 90,    "name": _("duck misser"), "accuracy": 58, "reliability": 88, "bullets": 8, "magazines": 2},
    {"level": 5, "expMin": 140,   "name": _("member of the Committee Against Ducks"), "accuracy": 59, "reliability": 89, "bullets": 8, "magazines": 2},
    {"level": 6, "expMin": 200,   "name": _("duck hater"), "accuracy": 60, "reliability": 90, "bullets": 8, "magazines": 2},
    {"level": 7, "expMin": 270,   "name": _("duck pest"), "accuracy": 65, "reliability": 93, "bullets": 4, "magazines": 3},
    {"level": 8, "expMin": 350,   "name": _("duck hassler"), "accuracy": 67, "reliability": 93, "bullets": 4, "magazines": 3},
    {"level": 9, "expMin": 440,   "name": _("duck plucker"), "accuracy": 69, "reliability": 93, "bullets": 4, "magazines": 3},
    {"level": 10, "expMin": 540,  "name": _("hunter"), "accuracy": 71, "reliability": 94, "bullets": 4, "magazines": 3},
    {"level": 11, "expMin": 650,  "name": _("duck inside out turner"), "accuracy": 73, "reliability": 94, "bullets": 4, "magazines": 3},
    {"level": 12, "expMin": 770,  "name": _("duck clobber"), "accuracy": 73, "reliability": 94, "bullets": 4, "magazines": 3},
    {"level": 13, "expMin": 900,  "name": _("duck chewer"), "accuracy": 74, "reliability": 95, "bullets": 4, "magazines": 3},
    {"level": 14, "expMin": 1040, "name": _("duck eater"), "accuracy": 74, "reliability": 95, "bullets": 4, "magazines": 3},
    {"level": 15, "expMin": 1190, "name": _("duck flattener"), "accuracy": 75, "reliability": 95, "bullets": 4, "magazines": 3},
    {"level": 16, "expMin": 1350, "name": _("duck disassembler"), "accuracy": 80, "reliability": 97, "bullets": 2, "magazines": 4},
    {"level": 17, "expMin": 1520, "name": _("duck demolisher"), "accuracy": 81, "reliability": 97, "bullets": 2, "magazines": 4},
    {"level": 18, "expMin": 1700, "name": _("duck killer"), "accuracy": 81, "reliability": 97, "bullets": 2, "magazines": 4},
    {"level": 19, "expMin": 1890, "name": _("duck skinner"), "accuracy": 82, "reliability": 97, "bullets": 2, "magazines": 4},
    {"level": 20, "expMin": 2090, "name": _("duck predator"), "accuracy": 82, "reliability": 97, "bullets": 2, "magazines": 4},
    {"level": 21, "expMin": 2300, "name": _("duck chopper"), "accuracy": 83, "reliability": 98, "bullets": 2, "magazines": 4},
    {"level": 22, "expMin": 2520, "name": _("duck decorticator"), "accuracy": 83, "reliability": 98, "bullets": 2, "magazines": 4},
    {"level": 23, "expMin": 2750, "name": _("duck fragger"), "accuracy": 84, "reliability": 98, "bullets": 2, "magazines": 4},
    {"level": 24, "expMin": 2990, "name": _("duck shatterer"), "accuracy": 84, "reliability": 98, "bullets": 2, "magazines": 4},
    {"level": 25, "expMin": 3240, "name": _("duck smasher"), "accuracy": 85, "reliability": 98, "bullets": 2, "magazines": 4},
    {"level": 26, "expMin": 3500, "name": _("duck breaker"), "accuracy": 90, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 27, "expMin": 3770, "name": _("duck wrecker"), "accuracy": 91, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 28, "expMin": 4050, "name": _("duck impaler"), "accuracy": 91, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 29, "expMin": 4340, "name": _("duck eviscerator"), "accuracy": 92, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 30, "expMin": 4640, "name": _("ducks terror"), "accuracy": 92, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 31, "expMin": 4950, "name": _("duck exploder"), "accuracy": 93, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 32, "expMin": 5270, "name": _("duck destructor"), "accuracy": 93, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 33, "expMin": 5600, "name": _("duck blaster"), "accuracy": 94, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 34, "expMin": 5940, "name": _("duck pulverizer"), "accuracy": 94, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 35, "expMin": 6290, "name": _("duck disintegrator"), "accuracy": 95, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 36, "expMin": 6650, "name": _("duck atomizer"), "accuracy": 95, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 37, "expMin": 7020, "name": _("duck annihilator"), "accuracy": 96, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 38, "expMin": 7400, "name": _("serial duck killer"), "accuracy": 96, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 39, "expMin": 7790, "name": _("duck genocider"), "accuracy": 97, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 40, "expMin": 8200, "name": _("old noob"), "accuracy": 97, "reliability": 99, "bullets": 1, "magazines": 5},
    {"level": 41, "expMin": 9999, "name": _("duck toaster"), "accuracy": 98, "reliability": 99, "bullets": 1, "magazines": 6},
    {"level": 42, "expMin": 11111, "name": _("unemployed due to extinction of the duck species"), "accuracy": 99, "reliability": 99, "bullets": 1, "magazines": 7}
]


def get_level_info(experience):
    return next((level for level in reversed(LEVELS) if level["expMin"] <= experience), LEVELS[0])


def get_level_info_from_id(level_id):
    return next((level for level in LEVELS if level["level"] == level_id), None)


def get_higher_level():
    return get_level_info(math.inf)


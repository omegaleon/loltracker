"""Champion ID -> role probability mapping.

Generated from 1,721 stored ranked matches in the production database.
Each champion maps to a dict of {role: probability} where roles use
Riot's teamPosition values: TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY.
Only roles with >0 play rate are included.

Used by _assign_team_roles() with the Hungarian algorithm to find the
optimal role assignment for live game participants.
"""

# {champion_id: {role: probability, ...}}
# Roles: TOP, JUNGLE, MIDDLE, BOTTOM, UTILITY
CHAMPION_ROLE_RATES = {
    1: {"TOP": 0.018, "MIDDLE": 0.895, "UTILITY": 0.088},  # Annie
    2: {"TOP": 0.795, "JUNGLE": 0.205},  # Olaf
    3: {"TOP": 0.059, "JUNGLE": 0.012, "MIDDLE": 0.741, "UTILITY": 0.188},  # Galio
    4: {"TOP": 0.097, "MIDDLE": 0.847, "BOTTOM": 0.042, "UTILITY": 0.014},  # TwistedFate
    5: {"TOP": 0.032, "JUNGLE": 0.923, "MIDDLE": 0.038, "UTILITY": 0.006},  # XinZhao
    6: {"TOP": 0.963, "JUNGLE": 0.012, "BOTTOM": 0.012, "UTILITY": 0.012},  # Urgot
    7: {"TOP": 0.015, "MIDDLE": 0.833, "UTILITY": 0.152},  # Leblanc
    8: {"TOP": 0.289, "MIDDLE": 0.697, "BOTTOM": 0.013},  # Vladimir
    9: {"TOP": 0.045, "JUNGLE": 0.627, "MIDDLE": 0.03, "UTILITY": 0.299},  # FiddleSticks
    10: {"TOP": 0.857, "MIDDLE": 0.133, "UTILITY": 0.01},  # Kayle
    11: {"TOP": 0.102, "JUNGLE": 0.82, "MIDDLE": 0.066, "BOTTOM": 0.006, "UTILITY": 0.006},  # MasterYi
    12: {"JUNGLE": 0.017, "MIDDLE": 0.017, "UTILITY": 0.967},  # Alistar
    13: {"TOP": 0.211, "JUNGLE": 0.018, "MIDDLE": 0.772},  # Ryze
    14: {"TOP": 0.77, "JUNGLE": 0.016, "MIDDLE": 0.111, "UTILITY": 0.103},  # Sion
    15: {"JUNGLE": 0.014, "BOTTOM": 0.972, "UTILITY": 0.014},  # Sivir
    16: {"UTILITY": 1.0},  # Soraka
    17: {"TOP": 0.563, "JUNGLE": 0.263, "MIDDLE": 0.03, "BOTTOM": 0.006, "UTILITY": 0.138},  # Teemo
    18: {"MIDDLE": 0.128, "BOTTOM": 0.872},  # Tristana
    19: {"TOP": 0.21, "JUNGLE": 0.77, "MIDDLE": 0.02},  # Warwick
    20: {"JUNGLE": 0.978, "UTILITY": 0.022},  # Nunu
    21: {"MIDDLE": 0.01, "BOTTOM": 0.969, "UTILITY": 0.021},  # MissFortune
    22: {"TOP": 0.009, "MIDDLE": 0.009, "BOTTOM": 0.898, "UTILITY": 0.083},  # Ashe
    23: {"TOP": 0.839, "JUNGLE": 0.08, "MIDDLE": 0.08},  # Tryndamere
    24: {"TOP": 0.61, "JUNGLE": 0.373, "MIDDLE": 0.017},  # Jax
    25: {"TOP": 0.012, "JUNGLE": 0.091, "MIDDLE": 0.188, "UTILITY": 0.709},  # Morgana
    26: {"TOP": 0.016, "MIDDLE": 0.129, "BOTTOM": 0.016, "UTILITY": 0.839},  # Zilean
    27: {"TOP": 0.949, "JUNGLE": 0.017, "MIDDLE": 0.034},  # Singed
    28: {"JUNGLE": 0.925, "UTILITY": 0.075},  # Evelynn
    29: {"TOP": 0.008, "JUNGLE": 0.074, "MIDDLE": 0.025, "BOTTOM": 0.82, "UTILITY": 0.074},  # Twitch
    30: {"JUNGLE": 0.744, "MIDDLE": 0.051, "BOTTOM": 0.179, "UTILITY": 0.026},  # Karthus
    31: {"TOP": 0.69, "JUNGLE": 0.048, "MIDDLE": 0.202, "UTILITY": 0.06},  # Chogath
    32: {"JUNGLE": 0.943, "UTILITY": 0.057},  # Amumu
    33: {"TOP": 0.132, "JUNGLE": 0.816, "UTILITY": 0.053},  # Rammus
    34: {"TOP": 0.071, "MIDDLE": 0.743, "BOTTOM": 0.014, "UTILITY": 0.171},  # Anivia
    35: {"TOP": 0.014, "JUNGLE": 0.801, "UTILITY": 0.185},  # Shaco
    36: {"TOP": 0.642, "JUNGLE": 0.333, "MIDDLE": 0.019, "UTILITY": 0.006},  # DrMundo
    37: {"MIDDLE": 0.009, "UTILITY": 0.991},  # Sona
    38: {"TOP": 0.074, "MIDDLE": 0.926},  # Kassadin
    39: {"TOP": 0.493, "MIDDLE": 0.507},  # Irelia
    40: {"UTILITY": 1.0},  # Janna
    41: {"TOP": 0.972, "MIDDLE": 0.028},  # Gangplank
    42: {"MIDDLE": 0.164, "BOTTOM": 0.836},  # Corki
    43: {"TOP": 0.027, "MIDDLE": 0.027, "UTILITY": 0.947},  # Karma
    44: {"JUNGLE": 0.04, "UTILITY": 0.96},  # Taric
    45: {"TOP": 0.007, "MIDDLE": 0.73, "BOTTOM": 0.162, "UTILITY": 0.101},  # Veigar
    48: {"TOP": 0.566, "JUNGLE": 0.408, "UTILITY": 0.026},  # Trundle
    50: {"TOP": 0.165, "MIDDLE": 0.187, "BOTTOM": 0.165, "UTILITY": 0.482},  # Swain
    51: {"TOP": 0.006, "MIDDLE": 0.006, "BOTTOM": 0.988},  # Caitlyn
    53: {"UTILITY": 1.0},  # Blitzcrank
    54: {"TOP": 0.618, "JUNGLE": 0.171, "MIDDLE": 0.125, "UTILITY": 0.086},  # Malphite
    55: {"MIDDLE": 0.965, "BOTTOM": 0.035},  # Katarina
    56: {"TOP": 0.006, "JUNGLE": 0.994},  # Nocturne
    57: {"TOP": 0.272, "JUNGLE": 0.136, "MIDDLE": 0.012, "UTILITY": 0.58},  # Maokai
    58: {"TOP": 0.978, "MIDDLE": 0.022},  # Renekton
    59: {"TOP": 0.02, "JUNGLE": 0.919, "MIDDLE": 0.01, "UTILITY": 0.051},  # JarvanIV
    60: {"TOP": 0.057, "JUNGLE": 0.771, "UTILITY": 0.171},  # Elise
    61: {"MIDDLE": 0.97, "UTILITY": 0.03},  # Orianna
    62: {"TOP": 0.274, "JUNGLE": 0.661, "MIDDLE": 0.032, "BOTTOM": 0.016, "UTILITY": 0.016},  # MonkeyKing
    63: {"TOP": 0.025, "JUNGLE": 0.068, "MIDDLE": 0.161, "BOTTOM": 0.149, "UTILITY": 0.596},  # Brand
    64: {"TOP": 0.016, "JUNGLE": 0.918, "MIDDLE": 0.049, "UTILITY": 0.016},  # LeeSin
    67: {"TOP": 0.281, "MIDDLE": 0.021, "BOTTOM": 0.699},  # Vayne
    68: {"TOP": 0.893, "MIDDLE": 0.107},  # Rumble
    69: {"TOP": 0.212, "MIDDLE": 0.667, "BOTTOM": 0.121},  # Cassiopeia
    72: {"TOP": 0.25, "JUNGLE": 0.667, "UTILITY": 0.083},  # Skarner
    74: {"TOP": 0.579, "MIDDLE": 0.289, "BOTTOM": 0.026, "UTILITY": 0.105},  # Heimerdinger
    75: {"TOP": 0.86, "JUNGLE": 0.085, "MIDDLE": 0.054},  # Nasus
    76: {"TOP": 0.016, "JUNGLE": 0.164, "MIDDLE": 0.008, "UTILITY": 0.812},  # Nidalee
    77: {"TOP": 0.228, "JUNGLE": 0.772},  # Udyr
    78: {"TOP": 0.217, "JUNGLE": 0.217, "MIDDLE": 0.017, "BOTTOM": 0.017, "UTILITY": 0.533},  # Poppy
    79: {"TOP": 0.558, "JUNGLE": 0.231, "MIDDLE": 0.135, "UTILITY": 0.077},  # Gragas
    80: {"TOP": 0.344, "JUNGLE": 0.153, "MIDDLE": 0.137, "UTILITY": 0.366},  # Pantheon
    81: {"MIDDLE": 0.044, "BOTTOM": 0.956},  # Ezreal
    82: {"TOP": 0.827, "JUNGLE": 0.128, "MIDDLE": 0.026, "BOTTOM": 0.013, "UTILITY": 0.006},  # Mordekaiser
    83: {"TOP": 0.82, "JUNGLE": 0.079, "MIDDLE": 0.09, "UTILITY": 0.011},  # Yorick
    84: {"TOP": 0.232, "MIDDLE": 0.76, "UTILITY": 0.008},  # Akali
    85: {"TOP": 0.575, "JUNGLE": 0.025, "MIDDLE": 0.275, "UTILITY": 0.125},  # Kennen
    86: {"TOP": 0.902, "JUNGLE": 0.005, "MIDDLE": 0.082, "BOTTOM": 0.005, "UTILITY": 0.005},  # Garen
    89: {"UTILITY": 1.0},  # Leona
    90: {"MIDDLE": 0.96, "BOTTOM": 0.013, "UTILITY": 0.027},  # Malzahar
    91: {"TOP": 0.016, "JUNGLE": 0.492, "MIDDLE": 0.492},  # Talon
    92: {"TOP": 0.929, "JUNGLE": 0.036, "MIDDLE": 0.036},  # Riven
    96: {"TOP": 0.024, "MIDDLE": 0.143, "BOTTOM": 0.762, "UTILITY": 0.071},  # KogMaw
    98: {"TOP": 0.506, "JUNGLE": 0.325, "MIDDLE": 0.031, "UTILITY": 0.138},  # Shen
    99: {"TOP": 0.011, "MIDDLE": 0.37, "BOTTOM": 0.04, "UTILITY": 0.579},  # Lux
    101: {"TOP": 0.009, "MIDDLE": 0.564, "BOTTOM": 0.027, "UTILITY": 0.4},  # Xerath
    102: {"TOP": 0.017, "JUNGLE": 0.983},  # Shyvana
    103: {"MIDDLE": 0.977, "UTILITY": 0.023},  # Ahri
    104: {"TOP": 0.06, "JUNGLE": 0.915, "MIDDLE": 0.026},  # Graves
    105: {"TOP": 0.01, "JUNGLE": 0.059, "MIDDLE": 0.931},  # Fizz
    106: {"TOP": 0.345, "JUNGLE": 0.638, "MIDDLE": 0.011, "UTILITY": 0.006},  # Volibear
    107: {"TOP": 0.088, "JUNGLE": 0.86, "BOTTOM": 0.035, "UTILITY": 0.018},  # Rengar
    110: {"TOP": 0.294, "MIDDLE": 0.059, "BOTTOM": 0.632, "UTILITY": 0.015},  # Varus
    111: {"TOP": 0.017, "JUNGLE": 0.023, "MIDDLE": 0.012, "BOTTOM": 0.006, "UTILITY": 0.942},  # Nautilus
    112: {"TOP": 0.019, "MIDDLE": 0.972, "BOTTOM": 0.009},  # Viktor
    113: {"TOP": 0.105, "JUNGLE": 0.816, "MIDDLE": 0.053, "UTILITY": 0.026},  # Sejuani
    114: {"TOP": 1.0},  # Fiora
    115: {"MIDDLE": 0.361, "BOTTOM": 0.611, "UTILITY": 0.028},  # Ziggs
    117: {"MIDDLE": 0.028, "BOTTOM": 0.009, "UTILITY": 0.963},  # Lulu
    119: {"TOP": 0.015, "MIDDLE": 0.015, "BOTTOM": 0.97},  # Draven
    120: {"JUNGLE": 1.0},  # Hecarim
    121: {"JUNGLE": 1.0},  # Khazix
    122: {"TOP": 0.868, "JUNGLE": 0.107, "MIDDLE": 0.019, "BOTTOM": 0.006},  # Darius
    126: {"TOP": 0.559, "JUNGLE": 0.237, "MIDDLE": 0.203},  # Jayce
    127: {"MIDDLE": 0.907, "UTILITY": 0.093},  # Lissandra
    131: {"TOP": 0.007, "JUNGLE": 0.521, "MIDDLE": 0.472},  # Diana
    133: {"TOP": 0.756, "MIDDLE": 0.171, "BOTTOM": 0.049, "UTILITY": 0.024},  # Quinn
    134: {"TOP": 0.02, "MIDDLE": 0.949, "BOTTOM": 0.03},  # Syndra
    136: {"TOP": 0.045, "MIDDLE": 0.818, "BOTTOM": 0.114, "UTILITY": 0.023},  # AurelionSol
    141: {"TOP": 0.057, "JUNGLE": 0.93, "MIDDLE": 0.006, "UTILITY": 0.006},  # Kayn
    142: {"MIDDLE": 0.684, "UTILITY": 0.316},  # Zoe
    143: {"TOP": 0.009, "JUNGLE": 0.181, "MIDDLE": 0.043, "BOTTOM": 0.009, "UTILITY": 0.759},  # Zyra
    145: {"TOP": 0.012, "MIDDLE": 0.012, "BOTTOM": 0.976},  # Kaisa
    147: {"MIDDLE": 0.038, "BOTTOM": 0.314, "UTILITY": 0.648},  # Seraphine
    150: {"TOP": 0.97, "MIDDLE": 0.03},  # Gnar
    154: {"TOP": 0.1, "JUNGLE": 0.771, "MIDDLE": 0.029, "UTILITY": 0.1},  # Zac
    157: {"TOP": 0.134, "MIDDLE": 0.745, "BOTTOM": 0.116, "UTILITY": 0.005},  # Yasuo
    161: {"JUNGLE": 0.01, "MIDDLE": 0.317, "BOTTOM": 0.079, "UTILITY": 0.594},  # Velkoz
    163: {"JUNGLE": 0.186, "MIDDLE": 0.767, "UTILITY": 0.047},  # Taliyah
    164: {"TOP": 0.85, "JUNGLE": 0.025, "MIDDLE": 0.075, "UTILITY": 0.05},  # Camille
    166: {"TOP": 0.034, "MIDDLE": 0.879, "BOTTOM": 0.069, "UTILITY": 0.017},  # Akshan
    200: {"JUNGLE": 0.972, "UTILITY": 0.028},  # Belveth
    201: {"JUNGLE": 0.011, "UTILITY": 0.989},  # Braum
    202: {"TOP": 0.009, "JUNGLE": 0.004, "BOTTOM": 0.987},  # Jhin
    203: {"JUNGLE": 1.0},  # Kindred
    221: {"MIDDLE": 0.032, "BOTTOM": 0.968},  # Zeri
    222: {"MIDDLE": 0.004, "BOTTOM": 0.996},  # Jinx
    223: {"TOP": 0.495, "JUNGLE": 0.01, "MIDDLE": 0.019, "BOTTOM": 0.029, "UTILITY": 0.448},  # TahmKench
    233: {"TOP": 0.041, "JUNGLE": 0.871, "MIDDLE": 0.068, "BOTTOM": 0.007, "UTILITY": 0.014},  # Briar
    234: {"JUNGLE": 0.962, "MIDDLE": 0.038},  # Viego
    235: {"TOP": 0.015, "MIDDLE": 0.008, "BOTTOM": 0.256, "UTILITY": 0.722},  # Senna
    236: {"TOP": 0.01, "MIDDLE": 0.039, "BOTTOM": 0.951},  # Lucian
    238: {"TOP": 0.042, "JUNGLE": 0.142, "MIDDLE": 0.817},  # Zed
    240: {"TOP": 0.818, "JUNGLE": 0.023, "MIDDLE": 0.136, "UTILITY": 0.023},  # Kled
    245: {"TOP": 0.019, "JUNGLE": 0.547, "MIDDLE": 0.428, "BOTTOM": 0.006},  # Ekko
    246: {"JUNGLE": 0.194, "MIDDLE": 0.75, "BOTTOM": 0.028, "UTILITY": 0.028},  # Qiyana
    254: {"TOP": 0.028, "JUNGLE": 0.917, "MIDDLE": 0.028, "UTILITY": 0.028},  # Vi
    266: {"TOP": 0.914, "JUNGLE": 0.075, "MIDDLE": 0.011},  # Aatrox
    267: {"UTILITY": 1.0},  # Nami
    268: {"TOP": 0.07, "MIDDLE": 0.93},  # Azir
    350: {"MIDDLE": 0.015, "UTILITY": 0.985},  # Yuumi
    360: {"MIDDLE": 0.009, "BOTTOM": 0.991},  # Samira
    412: {"TOP": 0.017, "BOTTOM": 0.006, "UTILITY": 0.978},  # Thresh
    420: {"TOP": 0.911, "MIDDLE": 0.089},  # Illaoi
    421: {"TOP": 0.036, "JUNGLE": 0.893, "UTILITY": 0.071},  # RekSai
    427: {"TOP": 0.081, "JUNGLE": 0.811, "UTILITY": 0.108},  # Ivern
    429: {"MIDDLE": 0.125, "BOTTOM": 0.812, "UTILITY": 0.062},  # Kalista
    432: {"TOP": 0.038, "UTILITY": 0.962},  # Bard
    497: {"MIDDLE": 0.082, "UTILITY": 0.918},  # Rakan
    498: {"MIDDLE": 0.022, "BOTTOM": 0.978},  # Xayah
    516: {"TOP": 0.889, "JUNGLE": 0.016, "MIDDLE": 0.032, "BOTTOM": 0.016, "UTILITY": 0.048},  # Ornn
    517: {"TOP": 0.04, "JUNGLE": 0.226, "MIDDLE": 0.677, "UTILITY": 0.056},  # Sylas
    518: {"TOP": 0.065, "MIDDLE": 0.217, "UTILITY": 0.717},  # Neeko
    523: {"TOP": 0.014, "BOTTOM": 0.986},  # Aphelios
    526: {"UTILITY": 1.0},  # Rell
    555: {"MIDDLE": 0.032, "UTILITY": 0.968},  # Pyke
    711: {"MIDDLE": 0.982, "UTILITY": 0.018},  # Vex
    777: {"TOP": 0.409, "JUNGLE": 0.006, "MIDDLE": 0.578, "BOTTOM": 0.006},  # Yone
    799: {"TOP": 0.471, "JUNGLE": 0.429, "MIDDLE": 0.086, "UTILITY": 0.014},  # Ambessa
    800: {"TOP": 0.017, "MIDDLE": 0.647, "BOTTOM": 0.126, "UTILITY": 0.21},  # Mel
    804: {"MIDDLE": 0.011, "BOTTOM": 0.989},  # Yunara
    875: {"TOP": 0.935, "JUNGLE": 0.009, "MIDDLE": 0.056},  # Sett
    876: {"TOP": 0.041, "JUNGLE": 0.959},  # Lillia
    887: {"TOP": 0.587, "JUNGLE": 0.376, "MIDDLE": 0.037},  # Gwen
    888: {"UTILITY": 1.0},  # Renata
    893: {"TOP": 0.037, "MIDDLE": 0.944, "UTILITY": 0.019},  # Aurora
    895: {"MIDDLE": 0.031, "BOTTOM": 0.969},  # Nilah
    897: {"TOP": 0.973, "UTILITY": 0.027},  # KSante
    901: {"TOP": 0.06, "JUNGLE": 0.007, "MIDDLE": 0.128, "BOTTOM": 0.805},  # Smolder
    902: {"UTILITY": 1.0},  # Milio
    904: {"TOP": 0.495, "JUNGLE": 0.459, "MIDDLE": 0.027, "UTILITY": 0.018},  # Zaahen
    910: {"TOP": 0.011, "MIDDLE": 0.723, "BOTTOM": 0.149, "UTILITY": 0.117},  # Hwei
    950: {"TOP": 0.174, "JUNGLE": 0.349, "MIDDLE": 0.477},  # Naafiri
}

# Default role rates for unknown champions (equal probability)
DEFAULT_ROLE_RATES = {
    "TOP": 0.2,
    "JUNGLE": 0.2,
    "MIDDLE": 0.2,
    "BOTTOM": 0.2,
    "UTILITY": 0.2,
}


def get_role_rates(champion_id):
    """Get role probability distribution for a champion.

    Returns dict of {role: probability} for all 5 roles.
    Missing roles get 0.0 probability.
    Unknown champions get equal probability across all roles.
    """
    rates = CHAMPION_ROLE_RATES.get(champion_id)
    if rates is None:
        return dict(DEFAULT_ROLE_RATES)
    # Fill in missing roles with 0.0
    result = {}
    for role in ("TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"):
        result[role] = rates.get(role, 0.0)
    return result

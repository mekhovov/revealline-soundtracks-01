"""Exact free uploads for the repaired second September 25 audition.

The first hosted attempt proved that album-length references do not establish
the duration of itch's separately downloadable loop assets. This revision
selects explicit ``-full`` synth files and complete album uploads from packs
whose free files correspond to documented 3+ minute tracks. These pins
authorize hosted technical preparation only; they grant no listening,
publication, Recording-mode, default or game-admission approval.
"""

CC_BY_BADGE = 'https://itch.io/game-assets/assets-cc4-by'
SOURCE_PINS = {
    'davidkbd-electric-pulse': (
        'https://davidkbd.itch.io/electric-pulse-synthwave-retro-futuristic-music-pack',
        2187961, CC_BY_BADGE),
    'davidkbd-interstellar2': (
        'https://davidkbd.itch.io/interstellar-vol2-edm-metal-music-pack',
        2445174, CC_BY_BADGE),
    'davidkbd-purgatory2': (
        'https://davidkbd.itch.io/purgatory-vol-2-extreme-metal-music-pack',
        2246806, CC_BY_BADGE),
}

UPLOAD_PINS = {
    'davidkbd.cyber-lights': ('davidkbd-electric-pulse', 8382058,
        'DavidKBD - Electric Pulse - 03 - Cyber Lights-full.ogg', 'Cyber Lights'),
    'davidkbd.neon-arcadia-awakening': ('davidkbd-electric-pulse', 8382061,
        'DavidKBD - Electric Pulse - 05 - Neon Arcadia Awakening-full.ogg',
        'Neon Arcadia Awakening'),
    'davidkbd.time-warp': ('davidkbd-electric-pulse', 8382063,
        'DavidKBD - Electric Pulse - 06 - Time Warp-full.ogg', 'Time Warp'),
    'davidkbd.quantum-ripples-of-sound': ('davidkbd-electric-pulse', 8382067,
        'DavidKBD - Electric Pulse - 08 - Quantum Ripples of Sound-full.ogg',
        'Quantum Ripples of Sound'),
    'davidkbd.synthetic-power-surge': ('davidkbd-electric-pulse', 8382551,
        'DavidKBD - Electric Pulse - 10 - Synthetic Power Surge-full.ogg',
        'Synthetic Power Surge'),
    'davidkbd.solar-storm': ('davidkbd-interstellar2', 13507642,
        'DavidKBD - Interstellar vol2 02 - Solar Storm.ogg', 'Solar Storm'),
    'davidkbd.galactic-battle': ('davidkbd-interstellar2', 13507638,
        'DavidKBD - Interstellar vol2 04 - Galactic Battle.ogg', 'Galactic Battle'),
    'davidkbd.orbital-assault': ('davidkbd-interstellar2', 13507646,
        'DavidKBD - Interstellar vol2 09 - Orbital Assault.ogg', 'Orbital Assault'),
    'davidkbd.they-want-death': ('davidkbd-purgatory2', 12451195,
        'DavidKBD - Purgatory Pack vol2 - 02 - They want death.ogg', 'They want death'),
    'davidkbd.insanity-is-your-flame': ('davidkbd-purgatory2', 12451193,
        'DavidKBD - Purgatory Pack vol2 - 04 - Insanity is your flame.ogg',
        'Insanity is your flame'),
    'davidkbd.sin-their-pity-their-agony': ('davidkbd-purgatory2', 12451194,
        'DavidKBD - Purgatory Pack vol2 - 05 - Sin, their pity, their agony.ogg',
        'Sin, their pity, their agony'),
}

# These source pages are also used by the independently reviewed first slate.
# Duplicate keys retain the same normalized description hashes; any source-text
# or licence change stops both hosted entry points.
DESCRIPTION_HASHES = {
    'davidkbd-electric-pulse': 'e5f046ff6701a9642cc1d53467b89e15acf1c4ba62e5efad16bba6f3c87e2d4f',
    'davidkbd-interstellar2': '480e1b406343130318da6b0b2e961d84494b685c1b9126206349a2a824d976fb',
    'davidkbd-purgatory2': '511fd39f74a9f243b56fc1c6e0d62a2178e55febbfec2964b4c0986d97572b70',
}

REFERENCE_DURATIONS = {
    'davidkbd.cyber-lights': 251,
    'davidkbd.neon-arcadia-awakening': 232,
    'davidkbd.time-warp': 236,
    'davidkbd.quantum-ripples-of-sound': 302,
    'davidkbd.synthetic-power-surge': 251,
    'davidkbd.solar-storm': 243,
    'davidkbd.galactic-battle': 253,
    'davidkbd.orbital-assault': 203,
    'davidkbd.they-want-death': 251,
    'davidkbd.insanity-is-your-flame': 192,
    'davidkbd.sin-their-pity-their-agony': 235,
}

REFERENCE_DURATION_SOURCES = {
    'davidkbd-electric-pulse':
        'https://davidkbd.bandcamp.com/album/electric-pulse-synthwave-retro-futuristic-music-pack-original-game-soundtrack',
    'davidkbd-interstellar2':
        'https://davidkbd.bandcamp.com/album/interstellar-vol-2-edm-metal-music-pack-original-game-soundtrack',
    'davidkbd-purgatory2':
        'https://davidkbd.bandcamp.com/album/purgatory-vol-2-extreme-metal-music-pack-original-game-soundtrack',
}


def details(track_id):
    creator = UPLOAD_PINS[track_id][0]
    synth = creator == 'davidkbd-electric-pulse'
    return {
        'family': 'synth90s' if synth else 'metal',
        'role': 'gameplay',
        'energy': 'medium-high' if synth else 'high',
        'metadataReview': 'source-described-listening-pending',
        'fullTrackListening': False,
        'gameplayReview': 'pending',
        'vocalContent': 'creator-described-vocals' if creator == 'davidkbd-purgatory2' else 'unverified',
        'explicitContentReview': 'pending',
        'referenceDurationSeconds': REFERENCE_DURATIONS[track_id],
        'referenceDurationSource': REFERENCE_DURATION_SOURCES[creator],
        'exactNativeDurationReview': 'pending-hosted-decode',
        'minimumDurationSeconds': 180,
    }

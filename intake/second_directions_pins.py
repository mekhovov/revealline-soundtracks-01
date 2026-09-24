"""Exact anonymous source/upload observations for the second September 25 audition.

These pins authorize bounded hosted acquisition only. They confer no listening,
publication, Recording-mode or game-admission approval.
"""

CC_BY_BADGE = 'https://itch.io/game-assets/assets-cc4-by'
SOURCE_PINS = {
    'davidkbd-pink-bloom': (
        'https://davidkbd.itch.io/pink-bloom-synthwave-music-pack',
        1635239, CC_BY_BADGE),
    'davidkbd-hexapuppies': (
        'https://davidkbd.itch.io/hexapuppies-synthwave-music-pack',
        1020992, CC_BY_BADGE),
    'davidkbd-reckless': (
        'https://davidkbd.itch.io/reckless-punk-metal-music-pack',
        974022, CC_BY_BADGE),
    'davidkbd-purgatory': (
        'https://davidkbd.itch.io/purgatory-extreme-metal-music-pack',
        1498789, CC_BY_BADGE),
}

UPLOAD_PINS = {
    'davidkbd.pink-bloom': ('davidkbd-pink-bloom', 6233745,
        'DavidKBD - Pink Bloom Pack - 01 - Pink Bloom.ogg', 'Pink Bloom'),
    'davidkbd.to-the-unknown': ('davidkbd-pink-bloom', 6233747,
        'DavidKBD - Pink Bloom Pack - 03 - To the Unknown.ogg', 'To the Unknown'),
    'davidkbd.lightyear-city': ('davidkbd-pink-bloom', 6233753,
        'DavidKBD - Pink Bloom Pack - 09 - Lightyear City.ogg', 'Lightyear City'),
    'davidkbd.hexapuppies': ('davidkbd-hexapuppies', 3749483,
        'DavidKBD - HexaPuppies Pack - 01 - HexaPuppies.ogg', 'HexaPuppies'),
    'davidkbd.the-great-machine': ('davidkbd-hexapuppies', 3749499,
        'DavidKBD - HexaPuppies Pack - 07 - The Great Machine - variation1.ogg',
        'The Great Machine'),
    'davidkbd.disaster': ('davidkbd-hexapuppies', 3749505,
        'DavidKBD - HexaPuppies Pack - 09 - Disaster - variation1.ogg', 'Disaster'),
    'davidkbd.keep-my-rhythm-if-you-can': ('davidkbd-reckless', 12030737,
        'DavidKBD - Reckless Punk-Metal Pack - 03 - Keep My Rhythm, If You Can.ogg',
        'Keep My Rhythm, If You Can'),
    'davidkbd.dangerous-and-bored': ('davidkbd-reckless', 12030736,
        'DavidKBD - Reckless Punk-Metal Pack - 05 - Dangerous and Bored.ogg',
        'Dangerous and Bored'),
    'davidkbd.speedy-and-hostile': ('davidkbd-reckless', 12030742,
        'DavidKBD - Reckless Punk-Metal Pack - 10 - Speedy and Hostile.ogg',
        'Speedy and Hostile'),
    'davidkbd.purgatory': ('davidkbd-purgatory', 11733688,
        '01 - DavidKBD - Purgatory Pack - Purgatory.ogg', 'Purgatory'),
    'davidkbd.on-fire': ('davidkbd-purgatory', 11733968,
        '06 - DavidKBD - Purgatory Pack - On Fire.ogg', 'On Fire'),
    'davidkbd.hades': ('davidkbd-purgatory', 11733694,
        '07 - DavidKBD - Purgatory Pack - Hades.ogg', 'Hades'),
}

# SHA-256 of SourceDescription's normalized visible text and ordered link targets.
# A change requires source review; never replace a pin automatically on failure.
DESCRIPTION_HASHES = {
    'davidkbd-pink-bloom': '20bce3bda55f556e6259fb64779ef25548945aafddd5bdeee78efb5b8cb6349e',
    'davidkbd-hexapuppies': '95ea537a06ef1fbc155011bf581f602a3ffdc090ba3a25890efbc89b9c4c5fe4',
    'davidkbd-reckless': 'a60256ff1f623e6e9e9d652bb0db1034a46fa8272cf9c6dfa31d7e27731da91a',
    'davidkbd-purgatory': '939bfc4dcf017b27a6ab6d17548bf1f472babb0161fe54f385fc4d5524b4f9f3',
}

REFERENCE_DURATIONS = {
    'davidkbd.pink-bloom': 286,
    'davidkbd.to-the-unknown': 329,
    'davidkbd.lightyear-city': 291,
    'davidkbd.hexapuppies': 270,
    'davidkbd.the-great-machine': 258,
    'davidkbd.disaster': 282,
    'davidkbd.keep-my-rhythm-if-you-can': 241,
    'davidkbd.dangerous-and-bored': 323,
    'davidkbd.speedy-and-hostile': 227,
    'davidkbd.purgatory': 189,
    'davidkbd.on-fire': 185,
    'davidkbd.hades': 207,
}

REFERENCE_DURATION_SOURCES = {
    'davidkbd-pink-bloom':
        'https://davidkbd.bandcamp.com/album/pink-bloom-synthwave-music-pack-original-game-soundtrack',
    'davidkbd-hexapuppies': 'https://music.amazon.com/albums/B08VW2FWP4',
    'davidkbd-reckless':
        'https://davidkbd.bandcamp.com/album/reckless-punk-metal-pack-original-game-soundtrack',
    'davidkbd-purgatory':
        'https://davidkbd.bandcamp.com/album/purgatory-extreme-metal-music-pack-original-game-soundtrack',
}


def details(track_id):
    creator = UPLOAD_PINS[track_id][0]
    synth = creator in {'davidkbd-pink-bloom', 'davidkbd-hexapuppies'}
    return {
        'family': 'synth90s' if synth else 'metal',
        'role': 'gameplay',
        'energy': 'medium-high' if synth else 'high',
        'metadataReview': 'source-described-listening-pending',
        'fullTrackListening': False,
        'gameplayReview': 'pending',
        'vocalContent': 'unverified',
        'explicitContentReview': 'pending',
        'referenceDurationSeconds': REFERENCE_DURATIONS[track_id],
        'referenceDurationSource': REFERENCE_DURATION_SOURCES[creator],
        'exactNativeDurationReview': 'pending-hosted-decode',
        'minimumDurationSeconds': 180,
    }

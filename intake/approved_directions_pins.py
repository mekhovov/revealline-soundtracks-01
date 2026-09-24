"""Exact anonymous source/upload observations for the September 25 audition.

These pins authorize bounded hosted acquisition only. They confer no listening,
publication, Recording-mode or game-admission approval.
"""

CC_BY_BADGE = 'https://itch.io/game-assets/assets-cc4-by'
SOURCE_PINS = {
    'davidkbd-electric-pulse': (
        'https://davidkbd.itch.io/electric-pulse-synthwave-retro-futuristic-music-pack',
        2187961, CC_BY_BADGE),
    'davidkbd-interstellar': (
        'https://davidkbd.itch.io/interstellar-edm-metal-music-pack', 1704727, CC_BY_BADGE),
    'davidkbd-interstellar2': (
        'https://davidkbd.itch.io/interstellar-vol2-edm-metal-music-pack', 2445174, CC_BY_BADGE),
    'davidkbd-hair-knuckles': (
        'https://davidkbd.itch.io/hair-and-kuckles-technometal-music-pack', 1182848, CC_BY_BADGE),
    'davidkbd-purgatory3': (
        'https://davidkbd.itch.io/purgatory-vol-3-extreme-metal-music-pack', 3755088, CC_BY_BADGE),
    'davidkbd-purgatory2': (
        'https://davidkbd.itch.io/purgatory-vol-2-extreme-metal-music-pack', 2246806, CC_BY_BADGE),
}

UPLOAD_PINS = {
    'davidkbd.electric-pulse': ('davidkbd-electric-pulse', 8382056,
        'DavidKBD - Electric Pulse - 01 - Electric Pulse-full.ogg', 'Electric Pulse'),
    'davidkbd.retrochrome-nights': ('davidkbd-electric-pulse', 8382060,
        'DavidKBD - Electric Pulse - 04 - Retrochrome Nights-full.ogg', 'Retrochrome Nights'),
    'davidkbd.vapor-trails-pursuit': ('davidkbd-electric-pulse', 8382528,
        'DavidKBD - Electric Pulse - 09 - Vapor Trails Pursuit-full.ogg', 'Vapor Trails Pursuit'),
    'davidkbd.electric-dreams-of-infinity': ('davidkbd-electric-pulse', 8382065,
        'DavidKBD - Electric Pulse - 07 - Electric Dreams of Infinity-full.ogg',
        'Electric Dreams of Infinity'),
    'davidkbd.digital-horizon': ('davidkbd-electric-pulse', 8382053,
        'DavidKBD - Electric Pulse - 02 - Digital Horizon-full.ogg', 'Digital Horizon'),
    'davidkbd.plasma-storm': ('davidkbd-interstellar', 6501647,
        'DavidKBD - InterstellarPack - 02 - Plasma Storm.ogg', 'Plasma Storm'),
    'davidkbd.meteor-shower': ('davidkbd-interstellar2', 13507636,
        'DavidKBD - Interstellar vol2 01 - Meteor Shower.ogg', 'Meteor Shower'),
    'davidkbd.urban-hairbanger': ('davidkbd-hair-knuckles', 4397475,
        'DavidKBD - Hair And Knuckles Pack - 03 - Urban Hairbanger.ogg', 'Urban Hairbanger'),
    'davidkbd.grave-rot-requiem': ('davidkbd-purgatory3', 14549171,
        'DavidKBD-01 - Grave Rot Requiem.ogg', 'Grave Rot Requiem'),
    'davidkbd.devoured-by-darkness': ('davidkbd-purgatory3', 14549176,
        'DavidKBD-04 - Devoured by Darkness.ogg', 'Devoured by Darkness'),
    'davidkbd.tear-their-fate': ('davidkbd-purgatory2', 12451192,
        'DavidKBD - Purgatory Pack vol2 - 01 - Tear their fate.ogg', 'Tear their fate'),
}

# SHA-256 of SourceDescription's normalized visible text and ordered link targets.
# A change requires source review; never replace a pin automatically on failure.
DESCRIPTION_HASHES = {
    'davidkbd-electric-pulse': 'e5f046ff6701a9642cc1d53467b89e15acf1c4ba62e5efad16bba6f3c87e2d4f',
    'davidkbd-interstellar': '9a5fff99c09da4f9f0c49859f473ac641f465b060e425413a3f6f0f8d47dfa0b',
    'davidkbd-interstellar2': '480e1b406343130318da6b0b2e961d84494b685c1b9126206349a2a824d976fb',
    'davidkbd-hair-knuckles': '4b16d4b0833b64eb8f113a0dd48216b87b3c9e70376e434187e3d7a1dd5155c1',
    'davidkbd-purgatory3': 'fcab6f9052b1cc95f341fa5ccfdf1ea7c0275ce0bcf885559989ecd21137bd73',
    'davidkbd-purgatory2': '511fd39f74a9f243b56fc1c6e0d62a2178e55febbfec2964b4c0986d97572b70',
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
    }

"""Exact free uploads for the Purgatory vol. 3 metal audition.

These pins authorize hosted technical preparation only. They grant no
listening, publication, Recording-mode, default or game-admission approval.
"""

SOURCE = 'https://davidkbd.itch.io/purgatory-vol-3-extreme-metal-music-pack'
SOURCE_KEY = 'davidkbd-purgatory3'
CC_BY_BADGE = 'https://itch.io/game-assets/assets-cc4-by'

SOURCE_PINS = {
    SOURCE_KEY: (SOURCE, 3755088, CC_BY_BADGE),
}

UPLOAD_PINS = {
    'davidkbd.mutilations-melody': (
        SOURCE_KEY,
        14549174,
        "DavidKBD-03 - Mutilation's Melody.ogg",
        "Mutilation's Melody",
    ),
    'davidkbd.bone-grinders-ballad': (
        SOURCE_KEY,
        14549173,
        "DavidKBD-05 - Bone Grinder's Ballad.ogg",
        "Bone Grinder's Ballad",
    ),
    'davidkbd.the-slicing-strain': (
        SOURCE_KEY,
        14549177,
        'DavidKBD-06 - The Slicing Strain.ogg',
        'The Slicing Strain',
    ),
    'davidkbd.visceral-vengeance': (
        SOURCE_KEY,
        14549172,
        'DavidKBD-07 - Visceral Vengeance.ogg',
        'Visceral Vengeance',
    ),
}

# Normalized creator-description facts, including their exact link order.
# Any source-text or licence change stops acquisition before media is fetched.
DESCRIPTION_HASHES = {
    SOURCE_KEY: 'fcab6f9052b1cc95f341fa5ccfdf1ea7c0275ce0bcf885559989ecd21137bd73',
}

REFERENCE_DURATIONS = {
    'davidkbd.mutilations-melody': 133,
    'davidkbd.bone-grinders-ballad': 125,
    'davidkbd.the-slicing-strain': 132,
    'davidkbd.visceral-vengeance': 115,
}


def details(track_id):
    """Return fail-closed catalogue metadata for one exact candidate."""
    return {
        'family': 'metal',
        'role': 'gameplay',
        'energy': 'high',
        'metadataReview': 'source-described-listening-pending',
        'fullTrackListening': False,
        'gameplayReview': 'pending',
        'vocalContent': 'unverified',
        'explicitContentReview': 'pending',
        'referenceDurationSeconds': REFERENCE_DURATIONS[track_id],
        'referenceDurationSource': SOURCE,
        'exactNativeDurationReview': 'pending-hosted-decode',
        'minimumDurationSeconds': 100,
    }

"""Exact free uploads for the Reckless vol. 2 punk-metal audition.

These pins authorize hosted technical preparation only. They grant no
listening, publication, Recording-mode, default or game-admission approval.
"""

SOURCE = 'https://davidkbd.itch.io/reckless-vol-2-punk-metal-music-pack'
SOURCE_KEY = 'davidkbd-reckless2'
CC_BY_LINK = 'https://creativecommons.org/licenses/by/4.0/'

SOURCE_PINS = {
    SOURCE_KEY: (SOURCE, 3681796, CC_BY_LINK),
}

UPLOAD_PINS = {
    'davidkbd.city-limits-crash': (
        SOURCE_KEY, 14147896, 'DavidKBD-01 - City Limits Crash.ogg', 'City Limits Crash'),
    'davidkbd.edge-of-the-city': (
        SOURCE_KEY, 14147899, 'DavidKBD-02 - Edge of the City.ogg', 'Edge of the City'),
    'davidkbd.defiant-descent': (
        SOURCE_KEY, 14147898, 'DavidKBD-03 - Defiant Descent.ogg', 'Defiant Descent'),
    'davidkbd.airborne-anarchy': (
        SOURCE_KEY, 14147903, 'DavidKBD-05 - Airborne Anarchy.ogg', 'Airborne Anarchy'),
}

# Normalized creator-description facts, including their exact link order.
# Any source-text or licence change stops acquisition before media is fetched.
DESCRIPTION_HASHES = {
    SOURCE_KEY: '29f7786b366726e296cb8b36841897e8bdbc3be9b4561cf95c514cbc9facba0b',
}

REFERENCE_LOOP_END_SECONDS = {
    'davidkbd.city-limits-crash': 101,
    'davidkbd.edge-of-the-city': 97,
    'davidkbd.defiant-descent': 106,
    'davidkbd.airborne-anarchy': 84,
}

TEMPOS = {
    'davidkbd.city-limits-crash': 180,
    'davidkbd.edge-of-the-city': 170,
    'davidkbd.defiant-descent': 166,
    'davidkbd.airborne-anarchy': 170,
}


def details(track_id):
    """Return fail-closed catalogue metadata for one exact candidate."""
    return {
        'family': 'metal',
        'role': 'gameplay',
        'energy': 'high',
        'tempoBpm': TEMPOS[track_id],
        'metadataReview': 'source-described-listening-pending',
        'fullTrackListening': False,
        'gameplayReview': 'pending',
        'vocalContent': 'unverified',
        'explicitContentReview': 'pending',
        # These are the source table's loop-end sample positions converted to
        # seconds, not complete-file durations. Hosted decoding records the
        # authoritative duration separately in the candidate receipt.
        'referenceLoopEndSeconds': REFERENCE_LOOP_END_SECONDS[track_id],
        'referenceLoopSource': SOURCE,
        'exactNativeDurationReview': 'pending-hosted-decode',
        'minimumDurationSeconds': 75,
    }

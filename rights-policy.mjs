const DEFINITIONS = Object.freeze({
  "https://creativecommons.org/publicdomain/zero/1.0/": Object.freeze({
    key: "cc0",
    id: "CC0",
    version: "1.0",
    label: "CC0 1.0 Universal",
    shareAlike: false,
  }),
  "https://creativecommons.org/licenses/by/3.0/": Object.freeze({
    key: "cc-by-3.0",
    id: "CC-BY",
    version: "3.0",
    label: "CC BY 3.0 Unported",
    shareAlike: false,
  }),
  "https://creativecommons.org/licenses/by/4.0/": Object.freeze({
    key: "cc-by-4.0",
    id: "CC-BY",
    version: "4.0",
    label: "CC BY 4.0 International",
    shareAlike: false,
  }),
  "https://creativecommons.org/licenses/by-sa/3.0/": Object.freeze({
    key: "cc-by-sa-3.0",
    id: "CC-BY-SA",
    version: "3.0",
    label: "CC BY-SA 3.0 Unported",
    shareAlike: true,
  }),
  "https://creativecommons.org/licenses/by-sa/4.0/": Object.freeze({
    key: "cc-by-sa-4.0",
    id: "CC-BY-SA",
    version: "4.0",
    label: "CC BY-SA 4.0 International",
    shareAlike: true,
  }),
});

export const LICENSES_BY_URL = new Map(Object.entries(DEFINITIONS));
export const LICENSES_BY_KEY = new Map(
  [...LICENSES_BY_URL.entries()].map(([url, definition]) => [
    definition.key,
    Object.freeze({ ...definition, url }),
  ]),
);

const LEGACY_RIGHTS_ARCHIVE_IDS = new Set([
  "licensed-preview-01",
  "core-20260924",
  "metal-approved-directions-audition-20260925",
  "metal-eternity-audition-20260924",
  "metal-groove-audition-20260924",
  "metal-groove-yannz-audition-20260924",
  "metal-nakarada-audition-20260924",
  "metal-second-directions-audition-20260925",
  "synth-approved-directions-audition-20260925",
  "synth-audition-20260924",
  "synth-second-directions-audition-20260925",
  "ukrainian-shchedryk-20260924",
]);

export function allowsLegacyRightsArchive(archiveId) {
  return LEGACY_RIGHTS_ARCHIVE_IDS.has(archiveId);
}

const RIGHTS_KEYS = Object.freeze([
  "licenseId",
  "licenseVersion",
  "licenseURL",
  "rightsEvidenceURL",
  "attribution",
  "derivativeChangeNotice",
  "shareAlike",
]);
const SHARE_ALIKE_KEYS = Object.freeze([
  "required",
  "deliveryLicenseId",
  "deliveryLicenseVersion",
  "deliveryLicenseURL",
]);

function demand(value, message) {
  if (!value) throw new Error(message);
}
function exactKeys(value, keys, label) {
  demand(
    value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value).every((key) => keys.includes(key)) &&
      keys.every((key) => Object.hasOwn(value, key)),
    `Invalid ${label} fields.`,
  );
}
function safeHTTPS(value) {
  try {
    const url = new URL(value);
    return (
      typeof value === "string" &&
      value.length <= 2048 &&
      url.protocol === "https:" &&
      !url.username &&
      !url.password
    );
  } catch {
    return false;
  }
}
function text(value, label, maximum = 2048) {
  demand(
    typeof value === "string" &&
      value.trim().length > 0 &&
      value.length <= maximum,
    `${label} is required.`,
  );
  return value.trim();
}

export function createRightsMetadata({
  licenseURL,
  rightsEvidenceURL,
  attribution,
  derivativeChangeNotice,
}) {
  const definition = LICENSES_BY_URL.get(licenseURL);
  demand(definition, "Unsupported Creative Commons licence.");
  demand(
    safeHTTPS(rightsEvidenceURL),
    "A secure exact rights-evidence URL is required.",
  );
  return {
    licenseId: definition.id,
    licenseVersion: definition.version,
    licenseURL,
    rightsEvidenceURL,
    attribution: text(attribution, "Attribution"),
    derivativeChangeNotice: text(
      derivativeChangeNotice,
      "Derivative change notice",
    ),
    shareAlike: {
      required: definition.shareAlike,
      deliveryLicenseId: definition.shareAlike ? definition.id : null,
      deliveryLicenseVersion: definition.shareAlike ? definition.version : null,
      deliveryLicenseURL: definition.shareAlike ? licenseURL : null,
    },
  };
}

export function validateRecordingRights(track, { allowLegacy = false } = {}) {
  const definition = LICENSES_BY_URL.get(track?.licenseURL);
  demand(definition, "Recording has an unsupported redistribution licence.");
  demand(
    track.license === definition.label,
    "Recording licence label and URL differ.",
  );
  if (!track.rights) {
    demand(
      allowLegacy && !definition.shareAlike,
      definition.shareAlike
        ? "CC BY-SA recordings require explicit rights and delivery terms."
        : "Recording requires explicit rights metadata.",
    );
    return null;
  }

  const rights = track.rights;
  exactKeys(rights, RIGHTS_KEYS, "recording rights");
  exactKeys(rights.shareAlike, SHARE_ALIKE_KEYS, "ShareAlike delivery");
  demand(
    rights.licenseId === definition.id &&
      rights.licenseVersion === definition.version &&
      rights.licenseURL === track.licenseURL,
    "Recording rights identity differs from its licence.",
  );
  demand(
    safeHTTPS(rights.rightsEvidenceURL),
    "Recording rights evidence must be an exact HTTPS URL.",
  );
  demand(
    text(rights.attribution, "Rights attribution") ===
      text(track.credit, "Recording credit"),
    "Recording rights attribution differs from its public credit.",
  );
  text(rights.derivativeChangeNotice, "Derivative change notice");
  demand(
    rights.shareAlike.required === definition.shareAlike,
    "ShareAlike requirement differs from the recording licence.",
  );
  if (definition.shareAlike) {
    demand(
      rights.shareAlike.deliveryLicenseId === definition.id &&
        rights.shareAlike.deliveryLicenseVersion === definition.version &&
        rights.shareAlike.deliveryLicenseURL === track.licenseURL,
      "CC BY-SA delivery must retain the reviewed compatible ShareAlike licence.",
    );
    demand(
      track.recordingModeEligible === false,
      "CC BY-SA recordings cannot be marked Recording-mode-safe.",
    );
  } else {
    demand(
      rights.shareAlike.deliveryLicenseId === null &&
        rights.shareAlike.deliveryLicenseVersion === null &&
        rights.shareAlike.deliveryLicenseURL === null,
      "A non-ShareAlike licence cannot invent ShareAlike delivery terms.",
    );
  }
  return rights;
}

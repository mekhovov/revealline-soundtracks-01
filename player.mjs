const audio = document.querySelector("#audio");
const now = document.querySelector("#now-playing");
const nowSource = document.querySelector("#now-source");
const status = document.querySelector("#playback-status");
const search = document.querySelector("#search");
const genre = document.querySelector("#genre");
const collection = document.querySelector("#collection");
const shuffle = document.querySelector("#shuffle");
const pause = document.querySelector("#pause");
const nextButton = document.querySelector("#next");
const playResults = document.querySelector("#play-results");
const tracksHost = document.querySelector("#tracks");
const count = document.querySelector("#count");
const empty = document.querySelector("#empty");
const summary = document.querySelector("#catalogue-summary");

let catalogue;
let rows = [];
let current = null;
let queue = [];
let generation = 0;

const text = (node, value) => {
  node.textContent = value ?? "";
  return node;
};
const element = (name, className, value) => {
  const node = document.createElement(name);
  if (className) node.className = className;
  if (value !== undefined) text(node, value);
  return node;
};
const formatDuration = (seconds) => {
  if (!Number.isFinite(seconds)) return null;
  const rounded = Math.round(seconds);
  return `${Math.floor(rounded / 60)}:${String(rounded % 60).padStart(2, "0")}`;
};
const formatBytes = (bytes) => `${(bytes / 1024 / 1024).toFixed(2)} MiB`;
const stylesOf = (track) => {
  const value = track.tags.join(" ").toLowerCase();
  const styles = [];
  if (value.includes("ukrain")) styles.push("ukrainian");
  if (value.includes("metal")) styles.push("metal");
  if (/synth|electro|tracker|fm|dance|techno/.test(value)) styles.push("synth");
  if (/chiptune|8-bit|fakebit/.test(value)) styles.push("chiptune");
  if (/rock|punk/.test(value)) styles.push("rock");
  if (/ambient|atmospher/.test(value)) styles.push("ambient");
  return styles.length ? [...new Set(styles)] : ["other"];
};
const searchable = (track) =>
  [track.title, track.artist, track.collection, track.license, ...track.tags]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase();
const visible = () => rows.filter((row) => !row.hidden);

function refresh() {
  const term = search.value.trim().toLocaleLowerCase();
  for (const row of rows) {
    row.hidden =
      !row.dataset.search.includes(term) ||
      (genre.value && !row.trackStyles.includes(genre.value)) ||
      (collection.value && row.dataset.collection !== collection.value);
  }
  const found = visible().length;
  count.textContent = `${found} recording${found === 1 ? "" : "s"}`;
  empty.hidden = found > 0;
  playResults.disabled = found === 0;
  queue = [];
}

function refill() {
  queue = visible();
  if (shuffle.checked) {
    for (let index = queue.length - 1; index > 0; index--) {
      const swap = Math.floor(Math.random() * (index + 1));
      [queue[index], queue[swap]] = [queue[swap], queue[index]];
    }
    if (queue.length > 1 && queue[0] === current)
      [queue[0], queue[1]] = [queue[1], queue[0]];
  } else if (current && queue.includes(current)) {
    const offset = queue.indexOf(current) + 1;
    queue = [...queue.slice(offset), ...queue.slice(0, offset)];
  }
}

function updateMediaSession(track) {
  if (!("mediaSession" in navigator) || !("MediaMetadata" in globalThis))
    return;
  navigator.mediaSession.metadata = new MediaMetadata({
    title: track.title,
    artist: track.artist,
    album: `RevealLine · ${track.collection}`,
  });
}

async function play(row) {
  const request = ++generation;
  if (current) current.removeAttribute("data-active");
  current = row;
  const track = row.track;
  row.dataset.active = "true";
  pause.disabled = false;
  nextButton.disabled = false;
  queue = queue.filter((candidate) => candidate !== row);
  audio.pause();
  audio.src = new URL(track.audio.path, catalogue.archive.baseURL).href;
  now.textContent = `${track.title} · ${track.artist}`;
  nowSource.replaceChildren();
  const source = element("a", "", `Source: ${track.collection}`);
  source.href = track.source;
  source.rel = "noopener noreferrer";
  nowSource.append(source);
  status.textContent = "Loading selected recording…";
  updateMediaSession(track);
  history.replaceState(
    null,
    "",
    `?track=${encodeURIComponent(track.id)}#recordings`,
  );
  try {
    await audio.play();
  } catch {
    if (request === generation)
      status.textContent =
        "Press Play in the audio controls to start. Your browser may require a gesture.";
  }
}

function next() {
  if (!queue.length) refill();
  const row = queue.shift();
  if (row) void play(row);
  else status.textContent = "No recordings match the current filters.";
}

function renderTrack(track, index) {
  const row = element("article", "track");
  row.id = `track-${index}`;
  row.track = track;
  row.dataset.search = searchable(track);
  row.trackStyles = stylesOf(track);
  row.dataset.genres = row.trackStyles.join(" ");
  row.dataset.collection = track.archiveId;

  const playButton = element("button", "play-track", "▶");
  playButton.type = "button";
  playButton.setAttribute(
    "aria-label",
    `Play ${track.title} by ${track.artist}`,
  );
  playButton.addEventListener("click", () => {
    queue = [];
    void play(row);
    refill();
    queue = queue.filter((candidate) => candidate !== row);
  });

  const main = element("div", "track-main");
  main.append(
    element("h2", "", track.title),
    element("p", "artist", track.artist),
  );
  const labels = [...track.tags];
  const duration = formatDuration(track.durationSeconds);
  if (duration) labels.push(duration);
  labels.push(
    track.gameCatalogueAdmission ? "Game playlist" : "Published audition",
  );
  main.append(element("p", "tags", labels.join(" · ")));
  const details = element("details");
  details.append(element("summary", "", "Credits & file details"));
  details.append(
    element("p", "", track.credit),
    element("p", "", `Collection: ${track.collection}`),
    element(
      "p",
      "",
      `File: ${track.fileName} · ${formatBytes(track.audio.bytes)}`,
    ),
    element("p", "", `SHA-256: ${track.audio.sha256}`),
  );
  main.append(details);

  const links = element("div", "links");
  const download = element("a", "", "MP3 ↓");
  download.href = new URL(track.audio.path, catalogue.archive.baseURL).href;
  download.download = track.fileName;
  const creator = element("a", "", "Creator source ↗");
  creator.href = track.source;
  creator.rel = "noopener noreferrer";
  const license = element("a", "", track.license ?? "Licence");
  license.href = track.licenseURL;
  license.rel = "license";
  links.append(download, creator, license);
  row.append(playButton, main, links);
  return row;
}

async function loadCatalogue() {
  try {
    const response = await fetch("catalogue.json", { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    catalogue = await response.json();
    if (catalogue.format !== "revealline-public-soundtrack-catalogue.v1")
      throw new Error("Unsupported catalogue");
    const fragment = document.createDocumentFragment();
    rows = catalogue.tracks.map((track, index) => {
      const row = renderTrack(track, index);
      fragment.append(row);
      return row;
    });
    tracksHost.replaceChildren(fragment);
    tracksHost.setAttribute("aria-busy", "false");
    const sourceCounts = new Map();
    for (const track of catalogue.tracks)
      sourceCounts.set(
        track.archiveId,
        (sourceCounts.get(track.archiveId) ?? 0) + 1,
      );
    for (const source of catalogue.sources) {
      const option = element(
        "option",
        "",
        `${source.id === "foundation-70" ? "Foundation collection" : source.id} (${sourceCounts.get(source.id) ?? 0})`,
      );
      option.value = source.id;
      collection.append(option);
    }
    summary.textContent = `${catalogue.counts.uniqueRecordings} unique recordings across ${catalogue.sources.length} collections. Search, filter and keep them playing in one endless queue.`;
    refresh();
    const requested = new URL(location.href).searchParams.get("track");
    const requestedRow = rows.find((row) => row.track.id === requested);
    if (requestedRow) {
      requestedRow.scrollIntoView({ block: "center" });
      requestedRow.querySelector("button").focus({ preventScroll: true });
      status.textContent = `Ready to play ${requestedRow.track.title}.`;
    }
  } catch (error) {
    tracksHost.setAttribute("aria-busy", "false");
    summary.textContent = "The public catalogue could not be loaded.";
    status.textContent = `Catalogue unavailable: ${error.message}`;
    playResults.disabled = true;
  }
}

search.addEventListener("input", refresh);
genre.addEventListener("change", refresh);
collection.addEventListener("change", refresh);
shuffle.addEventListener("change", () => {
  queue = [];
});
playResults.addEventListener("click", () => {
  queue = [];
  next();
});
nextButton.addEventListener("click", next);
pause.addEventListener("click", () => {
  if (!audio.paused) audio.pause();
  else
    void audio.play().catch(() => {
      status.textContent = "Playback could not resume. Choose the song again.";
    });
});
audio.addEventListener("play", () => {
  pause.textContent = "Pause";
  status.textContent = "";
});
audio.addEventListener("pause", () => {
  pause.textContent = "Resume";
});
audio.addEventListener("ended", next);
audio.addEventListener("error", () => {
  status.textContent =
    "This recording could not load. Try Next or download its MP3.";
});
if ("mediaSession" in navigator) {
  navigator.mediaSession.setActionHandler("play", () => void audio.play());
  navigator.mediaSession.setActionHandler("pause", () => audio.pause());
  navigator.mediaSession.setActionHandler("nexttrack", next);
}

void loadCatalogue();

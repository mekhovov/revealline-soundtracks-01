const audio = document.querySelector('#audio');
const now = document.querySelector('#now-playing');
const status = document.querySelector('#playback-status');
const rows = [...document.querySelectorAll('.track')];
const search = document.querySelector('#search');
const genre = document.querySelector('#genre');
const shuffle = document.querySelector('#shuffle');
const pause = document.querySelector('#pause');
let current = null;
let queue = [];
let generation = 0;
const visible = () => rows.filter((row) => !row.hidden);
function refresh() {
  const term = search.value.trim().toLowerCase();
  for (const row of rows) {
    row.hidden =
      !row.dataset.search.includes(term) ||
      (genre.value && !row.dataset.genres.split(' ').includes(genre.value));
  }
  const count = visible().length;
  document.querySelector('#count').textContent = `${count} recording${count === 1 ? '' : 's'}`;
  document.querySelector('#empty').hidden = count > 0;
  queue = [];
}
function refill() {
  queue = visible();
  if (shuffle.checked) {
    for (let i = queue.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [queue[i], queue[j]] = [queue[j], queue[i]];
    }
    if (queue.length > 1 && queue[0] === current) [queue[0], queue[1]] = [queue[1], queue[0]];
  } else if (current && queue.includes(current)) {
    const offset = queue.indexOf(current) + 1;
    queue = [...queue.slice(offset), ...queue.slice(0, offset)];
  }
}
async function play(row) {
  const request = ++generation;
  if (current) current.removeAttribute('data-active');
  current = row;
  pause.disabled = false;
  current.dataset.active = 'true';
  queue = queue.filter((candidate) => candidate !== row);
  audio.pause();
  audio.src = row.querySelector('a[download]').href;
  now.textContent = `${row.querySelector('h2').textContent} · ${row.querySelector('.artist').textContent}`;
  status.textContent = '';
  try {
    await audio.play();
  } catch {
    if (request === generation)
      status.textContent =
        'Press Play in the audio controls to start, or choose another recording.';
  }
}
function next() {
  if (!queue.length) refill();
  const row = queue.shift();
  if (row) void play(row);
  else status.textContent = 'No recordings match the current filters.';
}
for (const row of rows)
  row.querySelector('button').addEventListener('click', () => {
    queue = [];
    void play(row);
    refill();
    queue = queue.filter((candidate) => candidate !== row);
  });
search.addEventListener('input', refresh);
genre.addEventListener('change', refresh);
shuffle.addEventListener('change', () => {
  queue = [];
});
document.querySelector('#next').addEventListener('click', next);
pause.addEventListener('click', () => {
  if (!audio.paused) audio.pause();
  else {
    const request = generation;
    void audio.play().catch(() => {
      if (request === generation)
        status.textContent =
          'Playback could not start. Choose another recording or its MP3 download link.';
    });
  }
});
audio.addEventListener('play', () => {
  pause.textContent = 'Pause music';
  status.textContent = '';
});
audio.addEventListener('pause', () => {
  pause.textContent = 'Resume music';
});
audio.addEventListener('ended', next);
audio.addEventListener('error', () => {
  status.textContent = 'This recording could not load. Try Next or its MP3 download link.';
});

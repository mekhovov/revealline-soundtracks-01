export const STYLE_GROUPS = Object.freeze([
  ['metal', 'Metal'],
  ['synth', 'Synth & electronic'],
  ['ukrainian', 'Ukrainian'],
  ['chiptune', 'Chiptune'],
  ['rock', 'Rock'],
  ['ambient', 'Ambient'],
  ['other', 'Other'],
]);

export function stylesOf(track) {
  const value = (track?.tags ?? []).join(' ').toLowerCase();
  const styles = [];
  if (value.includes('ukrain')) styles.push('ukrainian');
  if (value.includes('metal')) styles.push('metal');
  if (/synth|electro|tracker|fm|dance|techno/.test(value)) styles.push('synth');
  if (/chiptune|8-bit|fakebit/.test(value)) styles.push('chiptune');
  if (/rock|punk/.test(value)) styles.push('rock');
  if (/ambient|atmospher/.test(value)) styles.push('ambient');
  return styles.length ? [...new Set(styles)] : ['other'];
}

export function matchesStyles(trackStyles, selectedStyles) {
  const selected = new Set(selectedStyles);
  return selected.size > 0 && trackStyles.some((style) => selected.has(style));
}

export function buildPlaybackQueue(
  candidates,
  { order = 'shuffle', current = null, wrap = true, random = Math.random } = {},
) {
  if (!['ordered', 'shuffle'].includes(order)) throw new Error('Unsupported playback order.');
  const queue = [...candidates];
  if (order === 'shuffle') {
    for (let index = queue.length - 1; index > 0; index--) {
      const swap = Math.floor(random() * (index + 1));
      [queue[index], queue[swap]] = [queue[swap], queue[index]];
    }
    if (queue.length > 1 && queue[0] === current)
      [queue[0], queue[1]] = [queue[1], queue[0]];
    return queue;
  }
  if (!current || !queue.includes(current)) return queue;
  const offset = queue.indexOf(current) + 1;
  return wrap ? [...queue.slice(offset), ...queue.slice(0, offset)] : queue.slice(offset);
}

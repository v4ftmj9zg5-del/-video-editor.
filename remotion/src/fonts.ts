import {continueRender, delayRender, staticFile} from 'remotion';

// Bundled OFL fonts (public/fonts) so renders look the same on every machine.
const FONTS: [string, string][] = [
  ['Rubik', 'fonts/Rubik.ttf'],
  ['Heebo', 'fonts/Heebo.ttf'],
  ['Frank Ruhl Libre', 'fonts/FrankRuhlLibre.ttf'],
];

let loaded = false;

export const loadFonts = () => {
  if (loaded || typeof document === 'undefined') return;
  loaded = true;
  const handle = delayRender('fonts');
  Promise.all(
    FONTS.map(([family, file]) => {
      const f = new FontFace(family, `url(${staticFile(file)})`, {weight: '100 900'});
      document.fonts.add(f);
      return f.load();
    })
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error('font load failed', e);
      continueRender(handle);
    });
};

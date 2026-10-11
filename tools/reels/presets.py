"""The two editing styles. Everything a style changes lives here, so a preset
is tuned by editing one dict, not the pipeline code.

Both styles share the same pipeline: silence/retake removal, Hebrew captions,
voice enhancement (natural, no pitch/voice effects), B-roll and 1080x1920 export.
"""

DYNAMIC = dict(
    name="dynamic",
    label="Dynamic Reels",
    # --- cutting: tight, keeps the pace up
    pad_before=0.06,      # s of audio kept before each spoken phrase
    pad_after=0.10,       # s kept after it
    merge_gap=0.12,       # phrases closer than this are joined (no cut)
    # --- camera: alternating punch-in on every jump cut, with an eased "pop"
    zoom_levels=(1.0, 1.14),
    punch=0.07,           # extra zoom at the start of a clip, eased away
    punch_dur=0.28,
    drift=0.0,            # no slow push
    cut="hard",           # hard jump cuts
    cut_frames=0,
    # --- grade
    grade="punchy",
    # --- captions: big bold, 1-3 words, active word highlighted, pop-in
    caption_font="Rubik",
    caption_size=86,
    caption_bold=True,
    caption_y=1180,
    caption_max_words=3,
    caption_max_chars=16,
    caption_mode="pop",
    caption_colour="&H00FFFFFF",
    caption_accent="&H0047D9FF",   # warm yellow (ASS is BGR)
    # --- title / motion graphics
    title_mode="box",
    progress_bar=True,
    # --- B-roll: short, hard cut in with a fast zoom
    broll_dur=1.7,
    broll_min_gap=3.0,
    broll_in="hard",
    broll_zoom=(1.0, 1.12),
    broll_fade_frames=0,
    # --- sound
    sfx="dynamic",        # whoosh on B-roll, tick on punch-ins, hit under title
    music_auto=False,     # trending audio is usually added inside Instagram
    music_lufs=-22,       # music loudness before ducking (voice is -14)
    loudness=-14,         # LUFS target (Instagram)
)

ELEGANT = dict(
    name="elegant",
    label="Elegant Editorial",
    pad_before=0.18,
    pad_after=0.32,
    merge_gap=0.35,
    zoom_levels=(1.0, 1.0),
    punch=0.0,
    punch_dur=0.0,
    drift=0.06,           # slow continuous push-in across the whole video
    cut="dissolve",       # short soft dissolves hide the jump cuts
    cut_frames=7,
    grade="editorial",
    caption_font="Heebo Light",
    caption_size=58,
    caption_bold=False,
    caption_y=1430,
    caption_max_words=6,
    caption_max_chars=30,
    caption_mode="fade",
    caption_colour="&H00F0F4F7",
    caption_accent="&H00F0F4F7",
    title_mode="serif",
    progress_bar=False,
    broll_dur=2.8,
    broll_min_gap=4.0,
    broll_in="dissolve",
    broll_zoom=(1.0, 1.06),
    broll_fade_frames=12,
    sfx="elegant",        # only a soft air swell under B-roll dissolves
    music_auto=True,      # soft generated piano/pad bed if no music file given
    music_lufs=-25,
    loudness=-14,
)

PRESETS = {"dynamic": DYNAMIC, "elegant": ELEGANT}

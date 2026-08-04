# 3xn Frontier Certificate Verification

- Certificates: `44,266`
- Replayed transitions: `230,632`
- Invalid records: `0`
- Exact whole-state family size: `44,266`
- Radius-2 frontier family size: `601`
- Frontier transition closure: `230,632/230,632` (`100.00%`)
- Width coverage: `{5: 204, 7: 3279, 9: 40783}`

## Held-out widest strip

`{'width': 9, 'frontiers': 471, 'seen_at_smaller_width': 394, 'novel_count': 77, 'novel_examples': ['../../.b|*|../o./b.', '../../.b|*|b./.b/b.', '../../.b|*|b./o./..', '../../.w|*|../w./w.', '../../.w|*|w./b./b.', '../../.w|*|w./o./..', '../../.w|*|w./w./..', '../.b/..|*|../b./..', '../.b/..|*|../o./b.', '../.b/..|*|b./.b/b.', '../.b/.b|*|../b./w.', '../.b/.b|*|../o./..', '../.b/.b|*|../o./b.', '../.b/.b|*|b./.b/b.', '../.b/.b|*|b./b./..', '../.b/.b|*|b./o./..', '../.b/.b|*|b./ob/b.', '../.b/.b|*|w./b./..', '../.b/.b|*|w./o./..', '../.b/.w|*|w./o./b.']}`

A finite induction is established only when replay errors, open frontier transitions, and held-out novel signatures are all zero. Nonzero values are concrete closure gaps, not proof failures hidden by frequency ranking.

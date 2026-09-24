# Odd-board Invariant Search

| Board | States | Naive candidates | Naive counterexamples | Component-sum candidates | Component-sum counterexamples | Status |
|---|---:|---:|---:|---:|---:|---|
| 3x3 | 37 | 5 | 1 | 7 | 0 | scanned |
| 3x5 | 565 | 15 | 1 | 75 | 0 | scanned |
| 3x7 | 15,608 | 38 | 7 | 1,893 | 0 | scanned |
| 5x5 | 94,228 | 77 | 9 | 8,367 | 0 | scanned |
| 3x9 | 135,636 | 96 | 11 | 8,932 | 0 | scanned |
| 3x11 | 3,870,038 | 1,033 | 127 | 0 | 0 | Rust full-memo naive scan; component cancellation not scanned |
| 5x7 | 11,442,573 | 689 | 45 | 0 | 0 | Rust full-memo naive scan; component cancellation not scanned |
| 3x13 | 71,877,361 | 318 | 79 | 0 | 0 | Rust full-memo naive scan; component cancellation not scanned |

The naive invariant deliberately ignores attachments between the middle column and wings; any listed counterexample rules out that formulation. The component-sum invariant uses actual disconnected components and exact local values, so a replay counterexample would indicate an implementation defect.

- Saved counterexamples: `100`

# Col tile catalog

Date: September 5, 2026.

`o` means available to either player; `b` means Blue-only permission, not a placed stone. Every root in this table lets Blue use every cell. The table classifies ALL permanent White permission subsets on each listed shape. “Safe” means exact value zero. Counts distinguish labeled masks, not symmetry or CGT equivalence classes.

| Shape | White masks classified | Safe zero masks | Minimal zero supports | Can some safe copy repeat horizontally? |
|---|---:|---:|---:|---|
| 1x2 | 4 | 1 | 1 | No |
| 1x3 | 8 | 2 | 1 | No |
| 1x4 | 16 | 1 | 1 | No |
| 1x5 | 32 | 2 | 1 | No |
| 1x6 | 64 | 1 | 1 | No |
| 1x7 | 128 | 2 | 1 | No |
| 1x8 | 256 | 3 | 2 | No |
| 2x2 | 16 | 7 | 2 | Yes |
| 2x3 | 64 | 4 | 1 | No |
| 2x4 | 256 | 31 | 2 | Yes |
| 2x5 | 1,024 | 5 | 4 | No |
| 2x6 | 4,096 | 127 | 2 | Yes |
| 2x7 | 16,384 | 9 | 4 | No |
| 2x8 | 65,536 | 511 | 2 | Yes |
| 3x3 | 512 | 2 | 1 | No |
| 3x4 | 4,096 | 32 | 3 | Yes |
| 3x5 | 32,768 | 128 | 1 | No |
| 3x6 | 262,144 | 124 | 2 | No |
| 3x7 | 2,097,152 | 4 | 1 | No |
| 4x4 | 65,536 | 511 | 2 | Yes |
| 5x4 | 1,048,576 | 175 | 14 | No |

Total: **3,598,668 masks, 1,682 zero roots, 49 primitive zero supports.** Transpose or rotate a tile to obtain the corresponding orientation. No all-dimensions or all-Col-states claim is implied.

## The four minimal-support 5x4 reflection types

The following four patterns generate all 14 minimal supports under horizontal/vertical reflection. White may be given extra cells, generating exactly the 175 safe masks.

### Type 1: White mask 501695 (15 White-permitted cells)

```
oooo
oobo
ooob
bobo
ooob
```

White ports: `{'west': 23, 'east': 11, 'north': 15, 'south': 7}`. Exact value: **0**.

### Type 2: White mask 503735 (15 White-permitted cells)

```
ooob
oobo
oooo
bobo
ooob
```

White ports: `{'west': 23, 'east': 14, 'north': 7, 'south': 7}`. Exact value: **0**.

### Type 3: White mask 1006591 (17 White-permitted cells)

```
oooo
oooo
oobo
obob
oooo
```

White ports: `{'west': 31, 'east': 23, 'north': 15, 'south': 15}`. Exact value: **0**.

### Type 4: White mask 1029567 (16 White-permitted cells)

```
oooo
oobo
obob
oobo
oooo
```

White ports: `{'west': 31, 'east': 27, 'north': 15, 'south': 15}`. Exact value: **0**.

## Selected compact blocks

### 2x2

Mask 6; White ports `{'west': 2, 'east': 1, 'north': 2, 'south': 1}`; value 0.

```
bo
ob
```

Mask 9; White ports `{'west': 1, 'east': 2, 'north': 1, 'south': 2}`; value 0.

```
ob
bo
```

### 3x4

Mask 1959; White ports `{'west': 5, 'east': 2, 'north': 7, 'south': 7}`; value 0.

```
ooob
bobo
ooob
```

Mask 3678; White ports `{'west': 2, 'east': 5, 'north': 14, 'south': 14}`; value 0.

```
booo
obob
booo
```

Mask 3951; White ports `{'west': 5, 'east': 5, 'north': 15, 'south': 15}`; value 0.

```
oooo
boob
oooo
```

### 3x5

Mask 21845; White ports `{'west': 5, 'east': 5, 'north': 21, 'south': 21}`; value 0.

```
obobo
bobob
obobo
```

### 3x6

Mask 225975; White ports `{'west': 5, 'east': 5, 'north': 55, 'south': 55}`; value 0.

```
oooboo
bobobb
oooboo
```

Mask 243003; White ports `{'west': 5, 'east': 5, 'north': 59, 'south': 59}`; value 0.

```
oobooo
bbobob
oobooo
```

### 3x7

Mask 1966071; White ports `{'west': 7, 'east': 7, 'north': 119, 'south': 119}`; value 0.

```
ooobooo
ooooooo
ooobooo
```

### 4x4

Mask 23130; White ports `{'west': 10, 'east': 5, 'north': 10, 'south': 5}`; value 0.

```
bobo
obob
bobo
obob
```

Mask 42405; White ports `{'west': 5, 'east': 10, 'north': 5, 'south': 10}`; value 0.

```
obob
bobo
obob
bobo
```

## Numerical five-row tile and its opening table

```
ooob
booo
ooob
booo
ooob
```

Exact value **+3/4**. After one Blue opening, the checked local values/outcomes are:

| Row / column | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| 0 | N | -1 | N | -1 |
| 1 | -1 | N | -1 | N |
| 2 | +1/2 | -1 | N | -1 |
| 3 | -1 | N | -1 | N |
| 4 | N | -1 | N | -1 |

**N is an outcome, not a number and not a claim of value star.** Both actors can win when moving first in those cells’ successor games.

## Derived infinite families

The proofs in THEOREMS.md give:

- `E_(4k)=0` on three rows with the usual E4 exterior permissions, for k>=1.
- `J_n=0` on three rows, forbidding only the middle-left and middle-right cells, for n mod4 in {0,1,2}.
- Every even-by-even checkerboard-support tile is zero (White confined to one color class).
- Every one-Blue-stone position on empty 5x8 has certified upper bound -1/4, using two signed five-row tiles and an orientation chosen for the opening.

These are constructive deductions from finite certificates, not extrapolation from a table.

## Partial-state data

`certified_partial_tiles.jsonl.gz` contains **152,473 distinct certified upper-bound-zero checkpoints** with at least four live cells and at least one first-player move. The source certificate and node index are retained. They are NOT all exact zero games.

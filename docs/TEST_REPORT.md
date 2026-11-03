# Test report: 4x4 BF16 systolic array

Commit `2c44c72` (2026-10-27). Reproduce with `test/report/run_report.sh`. Icarus 12.0, cocotb 2.1.0, Python 3.13.18.

## Summary

| Bench | Result |
| --- | --- |
| Full chip, RTL (`test/test.py`) | 14/14 pass |
| BF16 MAC unit (`test/mac`) | 2/2 pass, 22,800 vectors |
| Data prep unit (`test/prep/tb_data_prep_unit.sv`) | does not compile: Wildcard named port connection (.*) did not find a matching identifier for port 8 (step). |

The data-prep testbench predates the `step` port of `data_prep_unit` and the one-cycle start latency, and CI does not run it. With `logic step = 1;` declared and one extra cycle after the `start` pulse, it passes at N,K = 4,4 · 2,2 · 8,8 · 4,8 · 8,4.

Gate-level and implementation results are not produced by this script. They come from the `gds` workflow (`gl_test`, `precheck` jobs) and are recorded in [`VALIDATION.md`](VALIDATION.md). As of 2026-11-03, the latest run is [40569980439](https://github.com/Nilovski/tt_bf16_systolic/actions/runs/40569980439): gate-level 14/14 pass, precheck pass, 0 DRC/LVS/antenna errors. Setup slack is −0.695 ns at `max_ss_100C_1v60` and −0.301 ns at `nom_ss_100C_1v60`, and positive at every tt and ff corner.

Matrices are row-major. Values are BF16, shown as exact decimals and as the 16-bit hex pattern the chip returned.

## Full-chip tests

| # | Test | Sim time (ns) | Result |
| --- | --- | --- | --- |
| 1 | `test_id` | 120 | Pass |
| 2 | `test_identity` | 15,610 | Pass |
| 3 | `test_random` | 310,870 | Pass |
| 4 | `test_accumulate` | 29,850 | Pass |
| 5 | `test_rerun_without_reload` | 44,050 | Pass |
| 6 | `test_read_element` | 14,790 | Pass |
| 7 | `test_unknown_opcode_sets_error` | 210 | Pass |
| 8 | `test_plan_cases` | 46,690 | Pass |
| 9 | `test_specials` | 15,610 | Pass |
| 10 | `test_cancellation` | 15,610 | Pass |
| 11 | `test_status_bits_and_busy` | 30,030 | Pass |
| 12 | `test_ena_low_ignores_input` | 250 | Pass |
| 13 | `test_read_c_slow_host` | 17,850 | Pass |
| 14 | `test_tiled_matmul` | 295,270 | Pass |

### 1. `test_id`: Pass

Sends `OP_ID` (0x41) and reads one byte back.

| Sent | Expected | Got | Result |
| --- | --- | --- | --- |
| `0x41` | `0xA8` | `0xA8` | Pass |

### 2. `test_identity`: Pass

C = I × B for a hand-picked B. STATUS after the run must show DONE, A_LOADED, B_LOADED and RESULT_VALID.

Final STATUS: `0x1e` (DONE + A_LOADED + B_LOADED + RESULT_VALID).

DUT = reference, 16/16 elements bit-exact.

```
A                     B                         C (DUT)                   C hex
   1    0    0    0     1.5    -2  3.25   0.5     1.5    -2  3.25   0.5   3fc0 c000 4050 3f00
   0    1    0    0       4     5    -6     7       4     5    -6     7   4080 40a0 c0c0 40e0
   0    0    1    0   0.125     8     9   -10   0.125     8     9   -10   3e00 4100 4110 c120
   0    0    0    1      11    12    13    14      11    12    13    14   4130 4140 4150 4160
```

### 3. `test_random`: Pass

Random 4×4 × 4×4 products.

Seed 1. 20 independent CLEAR_GEMM runs, every element uniform in [-8, 8] and rounded to BF16. 20/20 runs bit-exact. Hex for every run is in `test_vectors/fullchip_vectors.csv`.

**Run 1**: DUT = reference, 16/16 elements bit-exact.

```
A                                             B                                             C (DUT)
  -5.84375     5.5625    4.21875   -3.92188     -4.34375      7.125     6.4375       -7.5        -32      -43    -13.5   31.375
-0.0732422  -0.808594    2.42188      4.625     -7.59375   0.664062    7.03125   -1.89844     -9.125 -4.40625      -44   -28.75
      -6.5   -7.53125      5.375   -1.07812     -4.53125      -1.25   -7.53125    -4.4375         62      -58     -131    43.75
    4.1875   -7.96875     -0.875    3.54688    -0.992188 -0.0668945   -4.28125    -4.3125      42.75     25.5    -37.5   -27.75
```

**Run 2**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                         C (DUT)
     -4.5 -0.644531  -3.35938  -7.65625     5.28125   2.71875  -3.14062   1.39844      37.25 -7.90625   -26.75      -24
  5.40625  0.902344   2.28125  -5.03125       6.125   5.53125 0.0844727   1.42188      43.25    6.375    -22.5  -8.3125
    7.875      5.75   -6.0625  -2.67188     -7.4375    -4.125      4.75  -1.36719        136       76   -61.75       20
  3.54688     3.375   6.96875     -1.25    -5.21875   0.78125      3.25   2.79688   -5.71875 -1.47656    18.25    -3.25
```

**Run 3**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                         C (DUT)
       -2 -0.976562  0.134766   4.46875     4.34375  0.632812      5.75  -4.28125    10.875  14.625 15.9375   25.25
 0.335938  -1.71094 -0.165039  -7.53125    0.220703      7.25   1.24219 -0.652344     -32.5  -50.75     -48     -28
  -7.3125      3.25   7.71875   1.49219     -3.6875  0.769531    7.3125  -7.90625    -52.75    32.5   27.75 -26.125
 -1.70312  -5.28125 0.0358887   7.71875     4.53125     5.125    6.1875   3.84375     26.25    0.25  31.625      40
```

**Run 4**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                     C (DUT)
   4.9375  0.298828  0.980469  -1.17969    -7.5625  -4.3125 -5.15625  1.35156   -30.125 -5.3125  -26.25   6.375
 -7.09375   5.90625   1.11719   -4.8125    5.78125  4.78125     4.75   5.0625       121   102.5   47.75      32
0.0756836 -0.241211  -2.29688  -2.46875   -3.92188  5.46875  2.76562 -6.65625        26  5.1875     -18      24
 0.617188   1.97656   1.79688 -0.667969   -7.71875 -7.78125  4.09375       -4     4.875   21.75   8.375 1.54688
```

**Run 5**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                     C (DUT)
    -6.25         2  -2.48438    -6.875      -6.25  6.40625 0.162109 -4.65625        37   -43.5  27.875     -47
  -5.4375    0.4375   -5.3125  -3.64062     1.6875   5.0625 -7.65625 -7.71875      54.5   -53.5      41 -23.125
  3.39062 -0.726562  -2.84375 -0.419922   -5.65625      3.5  -5.4375  3.28125   -7.5625   7.875  23.375  -22.75
   -7.625   -1.8125  -1.26562        -5    2.84375 0.714844 -4.46875    7.625     37.75     -66      42    7.25
```

**Run 6**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                     C (DUT)
    4.75 0.265625  -4.4375    2.375    3.90625 -1.34375 -3.96875   -7.875     22.875  15.1875      -48      -75
-1.67969  1.21094 -2.85938  2.09375     6.0625 -7.40625    5.125  7.40625    4.40625    8.625 -7.96875   -4.625
 -7.0625 -3.21875      7.5        6      1.125    -5.25    5.875  7.59375    -18.875 -5.15625    43.75       74
-3.09375     5.75 -3.03125  7.03125    3.26562 0.141602 -1.95312 -2.45312       42.5   -21.25    10.25    26.75
```

**Run 7**: DUT = reference, 16/16 elements bit-exact.

```
A                                                 B                                         C (DUT)
   -4.71875     2.78125    -1.07031    -4.90625    -2.57812  -4.59375   2.79688   5.40625       64.5    32.25  -23.875      1.5
   -6.34375     2.65625    -3.26562 -0.00320435     6.90625      -2.5     6.125         3       35.5 -2.85938   12.375      -38
   -2.79688      5.9375     6.40625    -7.71875   -0.248047   7.78125     -4.25   3.60938         98     88.5    -49.5    61.25
   -4.78125       -2.75     7.78125     4.53125    -6.65625  -5.28125    6.5625  -4.59375     -38.75     65.5    -33.5   -26.75
```

**Run 8**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                         C (DUT)
 4.15625  1.60156  5.46875 -2.10938       4.625      5.25  -2.54688   1.84375     -24.375 -0.203125        33  -3.46875
 -2.5625 -3.34375    5.875  1.66406         4.5  -1.95312   1.13281  -4.40625      -54.75       -30      33.5    23.625
 7.28125   6.1875 -5.84375 0.820312     -6.6875  -3.73438      6.25   1.03125         106      47.5       -51   -16.125
-6.34375   -7.375 -6.84375  5.84375      6.8125 -0.675781   -3.5625   4.59375          23   2.67188       -56      40.5
```

**Run 9**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                         C (DUT)
    5.25  -7.8125  2.73438 -6.53125    -1.94531   7.53125    6.5625  -3.29688      -9.5   26.25     125     0.5
-6.15625  6.15625   -7.375 -4.15625    -3.95312 -0.367188  -6.40625    2.4375      35.5 12.5625  -124.5    88.5
  7.8125 -1.26562 -6.15625  -5.3125      -7.375  -7.84375   7.71875  -3.26562        27     112  27.875    28.5
  -4.125  3.90625 -6.34375   6.5625     1.54688 -0.800781  -2.98438        -7      49.5      12  -120.5      -2
```

**Run 10**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                         C (DUT)
   6.625  7.53125  7.53125 -6.21875     7.71875 -0.832031    2.4375   2.29688        99  18.875      32     -39
 -4.5625  1.88281   7.6875   0.6875      7.0625     -1.75  -3.09375  -2.76562    -46.25   43.75      32     -39
 3.01562  2.59375 -3.85938 0.664062     -2.9375    5.5625   6.28125  -3.15625        51     -28     -24 12.9375
-3.07812  -4.0625  -6.6875     -3.5    -2.65625  0.707031   1.26562   1.53906    -23.75     -30   -41.5  19.875
```

**Run 11**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                     C (DUT)
 -4.09375   -7.6875  -4.09375  -6.84375     7.1875 -5.21875  4.40625     7.75     -142    108   24.5    -54
 0.820312    -6.875   -6.8125   2.17188    5.15625 -2.89062 -6.28125 0.229492   -61.25  21.75 -2.625  57.75
 -3.34375    4.6875  -0.10791    5.8125    6.71875 -3.29688   6.3125 -5.71875    37.75 -39.25    -62 13.375
 -5.53125 0.0228271   4.71875  -6.78125     6.5625     -7.5  -2.9375   6.4375    -52.5     64 25.125   -114
```

**Run 12**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                         C (DUT)
   4.875      6.5   5.4375   3.9375       5.625 -0.746094  -1.67188  -2.57812   -15.375    -106 15.0625     -59
 3.03125 -5.15625 -1.07812 -5.46875      -3.875    -7.625   2.34375  -1.33594      68.5    65.5   -43.5   14.25
  3.4375   2.6875 -3.95312 -6.96875     1.13281        -7  -2.32812  -5.78125     46.25    31.5  -26.75   21.75
 7.40625   4.9375 0.789062 0.660156          -6  -3.85938      5.25  -1.63281      19.5  -51.25  0.8125 -31.375
```

**Run 13**: DUT = reference, 16/16 elements bit-exact.

```
A                                             B                                     C (DUT)
  -1.58594    1.79688      -4.25     -7.875        6.5   6.6875 -3.59375  2.34375   -24.375     -85  -3.875    -5.5
  0.458984  0.0144043      2.375  -0.988281   -7.21875 -6.84375   0.1875  6.03125   -13.125 7.59375 14.9375 -9.1875
   2.98438    3.70312    -4.1875 -0.0786133    -5.4375     4.25    6.125 -3.01562    15.125 -23.625   -35.5   41.75
 -0.337891   -4.40625   -1.40625   0.964844    3.07812  5.59375 -2.04688  3.21875     40.25   27.25  -10.25     -20
```

**Run 14**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                         C (DUT)
 3.78125  1.51562   5.6875  6.34375      -5.375   3.67188  -7.34375    7.6875         45    4.375 -14.0625      113
   7.375  1.14062  -5.1875 -3.98438      4.9375    2.0625  -3.71875   6.59375        -82    46.75      -78        9
-4.53125  1.10938    4.125 -7.15625     7.34375  -5.78125   4.40625   5.46875       41.5      -61     53.5    -53.5
 2.90625  3.46875  -2.4375 0.241211      2.5625   3.20312 -0.878906   6.78125     -15.75    32.75   -45.25    33.75
```

**Run 15**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                         C (DUT)
 7.53125 -1.88281  4.84375 -1.07031     -7.9375  -4.96875 -0.980469  -7.65625      -76 -40.75    -40  -47.5
  -5.375 -2.79688 -5.96875  6.53125     2.04688    1.6875     5.375   -4.6875     31.5     37  42.25   78.5
 7.34375 -6.09375  1.60938 -1.46875     -3.4375  0.675781    -3.625     1.375    -70.5    -50  -52.5  -32.5
  -6.125 -3.26562 -4.03125        4    -3.98438    2.9375   4.65625    4.9375     39.5     34  21.75   76.5
```

**Run 16**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                             C (DUT)
   7.5625  0.726562 -0.147461    5.6875      -5.8125 0.00595093    1.16406   -3.01562        -18    15.25    8.875 -14.8125
   4.3125     1.125  -1.86719  -3.45312     0.048584   -2.29688   0.455078         -8        -39 -11.1875  11.8125  -27.125
 -6.28125   4.90625    -6.125   3.95312    -0.921875  -0.808594     -3.125   -1.60938       60.5     5.25  13.5625  -1.0625
 0.722656    7.4375    4.1875    7.5625      4.53125     2.9375  -0.123047    2.35938       26.5     1.75  -9.8125    -50.5
```

**Run 17**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                         C (DUT)
 -1.96094     -4.75   -7.9375   -3.5625     1.92188  0.496094     -2.25   -7.9375    -5.65625       -39       -47       -52
  1.57031   6.09375   5.28125  0.175781    -1.77344   -1.1875  -1.51562   5.78125   -0.707031   13.9375    21.375     44.25
  7.78125 -0.613281   5.34375  -1.45312     1.35156   3.73438     6.375   3.98438      23.375    18.875    14.125    -47.75
  3.92188    7.8125  -3.10938  -5.28125   -0.116699    3.9375      2.25     2.375      -9.875    -39.75     -52.5  -10.8125
```

**Run 18**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                         C (DUT)
 2.07812 -1.48438   2.0625  2.14062      5.3125  -0.24707 -0.527344  -7.28125       22.5  -25.625   7.4375  6.59375
       7  4.53125  5.53125  4.28125    0.164062   3.92188  -1.24219   -2.3125         65   -33.25     4.25 -14.8125
 5.03125   1.6875 -2.40625 -3.76562     2.51562   -7.6875  0.114746     7.125        9.5    29.75  -16.375    -64.5
 3.32812  5.96875 0.707031  -5.5625     3.04688  -1.57031   3.01562   1.67969      3.375    25.75  -25.875   -42.25
```

**Run 19**: DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                     C (DUT)
-4.65625  -4.6875   6.1875  -3.6875   -4.28125 0.976562    -5.25    4.625    5.65625       53  2.78125   -32.25
 -6.8125  5.28125 0.371094 -2.10938      5.875 -2.71875  -4.4375  7.40625         57 -12.8125  11.9375   1.0625
 0.18457  3.78125  -5.3125  2.45312     3.3125      5.5     -7.5    6.375     8.6875    -46.5    19.25    5.375
 3.42188  5.03125  -3.6875  1.75781    1.96094  -2.9375 -1.09375   4.1875      6.125   -35.75 -14.8125       37
```

**Run 20**: DUT = reference, 16/16 elements bit-exact.

```
A                                         B                                     C (DUT)
   4.5625  -4.96875   2.01562  -5.34375   -4.15625  3.48438      3.5 -3.10938       26.5     49.5     2.25    3.375
   7.5625 -0.902344     6.625   3.65625    -6.3125 -1.64844 -0.12207 -6.40625      -75.5    -46.5       49       42
  1.70312   -3.8125  0.425781  -5.78125         -5   -7.125   1.5625  6.21875         41    52.25   -11.75   -7.375
 -5.78125   3.45312  -2.21875   4.03125   -4.53125  -7.4375  3.26562  5.03125     -4.875      -40 -10.9375     2.25
```

### 4. `test_accumulate`: Pass

GEMM adds into the accumulators instead of clearing them.

Seed 2. CLEAR_GEMM with (A1, B1), then GEMM (accumulate) with (A2, B2). Expected: the model's K = 8 chain over [A1 | A2] × [B1 ; B2].

```
A1                                    B1
 7.28125  7.15625 -7.09375 -6.65625      7.1875  0.707031 -0.882812  -3.70312
   5.375  3.78125  2.71875  -3.0625     -7.4375   -7.5625   -0.5625  -2.90625
 1.69531  1.71094  1.29688 -5.46875    -1.92188   6.28125  0.412109   0.96875
-1.10938 -1.70312   3.5625  7.90625    -4.21875    -7.625  -2.79688   -5.8125
```

```
A2                                    B2
0.164062  7.96875  2.79688 -5.09375   -0.617188  0.486328 -0.160156    6.8125
  6.3125     4.75     3.75      6.5   0.0134277    5.3125  -2.34375     6.125
 4.21875    4.625 -2.34375   7.6875     6.40625    -0.625   1.08594   6.71875
   7.375 -5.40625   4.0625   3.4375     3.57812 -0.213867   -4.4375   -2.8125
```

C after accumulate: 16/16 bit-exact.

```
C (DUT)                                   C hex
    40.25 -0.664062    12.125        67   4221 bf2a 4142 4286
    61.75     40.25       -34        69   4277 4221 c208 428a
   29.875      64.5    -34.75      41.5   41ef 4281 c20b 4226
  -1.6875    -54.25       -18    1.3125   bfd8 c259 c190 3fa8
```

### 5. `test_rerun_without_reload`: Pass

The operand lanes return to order after a feed, so a GEMM can rerun without reloading.

Seed 4. Load once and run CLEAR_GEMM. Run CLEAR_GEMM again with no reload, which must give the same C. Then run GEMM with no reload, which must give A·B + A·B as a K = 8 chain.

```
A                                     B
-4.21875 -6.34375 -1.66406 -5.53125        5.25   4.90625    4.8125  -4.90625
 -6.9375 -1.57812   6.6875   4.8125    -3.04688   2.03125   3.70312    5.6875
    4.25  -4.4375 0.585938 -3.57812     6.09375    -6.625   1.69531      2.75
   -5.25  -6.3125  -4.5625  6.84375   0.0952148  -5.15625 -0.421875   -6.5625
```

| Step | Check | Result |
| --- | --- | --- |
| 1. CLEAR_GEMM | first result | recorded |
| 2. CLEAR_GEMM, no reload | equals step 1 | Pass |
| 3. GEMM, no reload | equals the K = 8 chain | Pass |

```
C step 1                          C step 3                      step 3 hex
-13.375       6  -44.25    16.5   -26.75 11.875  -88.5     33   c1d6 413e c2b1 4204
 9.4375  -106.5     -30  11.875       19   -212 -60.25 23.875   4198 c354 c271 41bf
     39    26.5   6.625     -21       78     53  13.25    -42   429c 4254 4154 c228
 -35.25   -43.5  -59.25     -68    -70.5    -87   -119   -136   c28d c2ae c2ee c308
```

### 6. `test_read_element`: Pass

Single-element reads return the right 16-bit value, low byte first.

Seed 3. One CLEAR_GEMM, then `READ_C_ELEMENT` (0x31) for indices 0, 5, 10, 15.

```
A                                         B
  -4.1875  0.707031  -2.07812   1.66406     2.15625     5.875  0.371094   3.85938
  2.01562   -6.9375  -7.78125   5.40625        2.75  -6.96875     4.125   1.46094
 -3.84375     -4.25    7.9375 -0.476562     -3.1875      -7.5   5.84375 -0.435547
    5.375 -0.378906   2.21875  -5.59375         3.5    6.0625   3.42188      6.75
```

| Index (row, col) | Low byte | High byte | Got | Expected | Value | Result |
| --- | --- | --- | --- | --- | --- | --- |
| 0 (0, 0) | `0xac` | `0x40` | `40ac` | `40ac` | 5.375 | Pass |
| 5 (1, 1) | `0x17` | `0x43` | `4317` | `4317` | 151 | Pass |
| 10 (2, 2) | `0xd0` | `0x41` | `41d0` | `41d0` | 26 | Pass |
| 15 (3, 3) | `0x94` | `0xc1` | `c194` | `c194` | -18.5 | Pass |

### 7. `test_unknown_opcode_sets_error`: Pass

An undefined opcode sets ERROR, and a STATUS read clears it.

| Step | Sent | STATUS | Check | Result |
| --- | --- | --- | --- | --- |
| 1 | `0x7F`, then STATUS | `0x20` (ERROR) | ERROR set | Pass |
| 2 | STATUS again | `0x00` (none) | ERROR cleared | Pass |

### 8. `test_plan_cases`: Pass

Identity on both sides and all ones, checked against exact expected values.

**A × I = A (seed 5)**: Pass.

```
A                                         B                     C (DUT)                                   C hex
  1.96875     3.875   4.71875   7.09375      1    0    0    0     1.96875     3.875   4.71875   7.09375   3ffc 4078 4097 40e3
  3.84375      6.75  -7.53125 -0.550781      0    1    0    0     3.84375      6.75  -7.53125 -0.550781   4076 40d8 c0f1 bf0d
  7.09375   2.39062   6.40625   -6.1875      0    0    1    0     7.09375   2.39062   6.40625   -6.1875   40e3 4019 40cd c0c6
-0.494141   -4.0625  0.699219   1.17969      0    0    0    1   -0.494141   -4.0625  0.699219   1.17969   befd c082 3f33 3f97
```

**I × A = A**: Pass.

```
A                     B                                         C (DUT)                                   C hex
   1    0    0    0     1.96875     3.875   4.71875   7.09375     1.96875     3.875   4.71875   7.09375   3ffc 4078 4097 40e3
   0    1    0    0     3.84375      6.75  -7.53125 -0.550781     3.84375      6.75  -7.53125 -0.550781   4076 40d8 c0f1 bf0d
   0    0    1    0     7.09375   2.39062   6.40625   -6.1875     7.09375   2.39062   6.40625   -6.1875   40e3 4019 40cd c0c6
   0    0    0    1   -0.494141   -4.0625  0.699219   1.17969   -0.494141   -4.0625  0.699219   1.17969   befd c082 3f33 3f97
```

**All ones × all ones = all 4.0**: Pass.

```
A                     B                     C (DUT)               C hex
   1    1    1    1      1    1    1    1      4    4    4    4   4080 4080 4080 4080
   1    1    1    1      1    1    1    1      4    4    4    4   4080 4080 4080 4080
   1    1    1    1      1    1    1    1      4    4    4    4   4080 4080 4080 4080
   1    1    1    1      1    1    1    1      4    4    4    4   4080 4080 4080 4080
```

### 9. `test_specials`: Pass

IEEE special values: inf, NaN, inf × 0, inf − inf, signed zeros, subnormal flush-to-zero and overflow.

Inputs: +inf `7f80`, -inf `ff80`, NaN `7fc0`, 3.0e38, the subnormal `0001` (flushed to zero) and -0 `8000`.

```
A                                     B
    +inf        0        0        0      2    0    0    0
     NaN        0        0        0      2 -inf    0    0
   3e+38    3e+38        0        0      0    0    0    0
9.18e-41       -0        0        0      0    0    0    0
```

```
A hex                 B hex
7f80 0000 0000 0000   4000 0000 0000 0000
7fc0 0000 0000 0000   4000 ff80 0000 0000
7f62 7f62 0000 0000   0000 0000 0000 0000
0001 8000 0000 0000   0000 0000 0000 0000
```

16/16 bit-exact.

```
C (DUT)               C hex
+inf  NaN  NaN  NaN   7f80 7fc0 7fc0 7fc0
 NaN  NaN  NaN  NaN   7fc0 7fc0 7fc0 7fc0
+inf -inf    0    0   7f80 ff80 0000 0000
   0  NaN    0    0   0000 7fc0 0000 0000
```

| Element | Exercises | Got | Result |
| --- | --- | --- | --- |
| C[0][0] | inf × 2 = inf | +inf | Pass |
| C[0][1] | inf × 0 = NaN | NaN | Pass |
| C[2][0] | 3e38·2 + 3e38·2 overflows | +inf | Pass |

### 10. `test_cancellation`: Pass

x + (−x) = +0, and near-cancellation (a 2⁻⁷ residue that needs a long normalize shift).

DUT = reference, 16/16 elements bit-exact.

```
A                     B                                 C (DUT)                                       C hex
   1   -1    1   -1       1.5     1.5     1.5     1.5    0.0078125 -0.0078125          0          0   3c00 bc00 0000 0000
   1   -1    1   -1       1.5     1.5     1.5     1.5    0.0078125 -0.0078125          0          0   3c00 bc00 0000 0000
   1   -1    1   -1   1.00781       1       1       1    0.0078125 -0.0078125          0          0   3c00 bc00 0000 0000
   1   -1    1   -1         1 1.00781       1       1    0.0078125 -0.0078125          0          0   3c00 bc00 0000 0000
```

### 11. `test_status_bits_and_busy`: Pass

STATUS bits across a run; a LOAD sent while busy is dropped and flags ERROR.

Seed 6.

| Step | Action | Observed | Check |
| --- | --- | --- | --- |
| 1 | STATUS after reset | `0x00` (none) | = 0 |
| 2 | LOAD_A, STATUS | `0x04` (A_LOADED) | = A_LOADED |
| 3 | LOAD_B, STATUS | `0x0c` (A_LOADED + B_LOADED) | = A_LOADED + B_LOADED |
| 4 | CLEAR_GEMM, wait 2 cycles | uio[4] BUSY high | BUSY pin = 1 |
| 5 | LOAD_A of all 1.0 while busy, STATUS | `0x2d` (BUSY + A_LOADED + B_LOADED + ERROR) | BUSY + ERROR, not DONE |
| 6 | Poll until idle | `0x1e` (DONE + A_LOADED + B_LOADED + RESULT_VALID) | DONE + RESULT_VALID; uio[5] DONE high |
| 7 | READ_C | Pass | = A·B (busy LOAD dropped) |
| 8 | CLEAR_GEMM, READ_C | Pass | = A·B (stored A unchanged) |

```
A                                         B                                     C (DUT)                               C hex
   4.6875   5.15625 -0.239258   -3.8125   -4.90625 0.859375    4.875    -3.75      28.25    36.75    41.75   -18.25   41e2 4213 4227 c192
       -8   2.60938 -0.476562   4.15625    4.84375  2.96875      5.5   -2.625         28    -21.5      -18    9.625   41e0 c1ac c190 411a
 -2.03125    4.3125  -3.64062   4.84375       -6.5   4.8125    4.875   -0.875         23      -30   6.5625   -16.75   41b8 c1f0 40d2 c186
  3.67188    -1.375  0.613281   2.90625       -6.5 -4.84375  2.15625 -3.34375      -47.5 -12.0625   19.625  -20.375   c23e c141 419d c1a3
```

### 12. `test_ena_low_ignores_input`: Pass

With `ena` low the chip ignores input; `uio_oe` is correct.

| Step | Action | Observed |
| --- | --- | --- |
| 1 | `ena` = 0, send OP_ID | TX_VALID stayed low for 10 cycles |
| 2 | `ena` = 1, send OP_ID | reply `0xA8` |
| 3 | read `uio_oe` | `0b0011_1010` |

### 13. `test_read_c_slow_host`: Pass

READ_C holds each byte until the host raises TX_READY.

Seed 7. Drained with a 9-cycle stall before each of the 32 byte reads.

DUT = reference, 16/16 elements bit-exact.

```
A                                     B                                     C (DUT)                               C hex
 -2.8125 -5.59375  2.42188 -6.84375    2.03125  7.15625  1.23438 -1.65625      -27.5   -3.375    -58.5     49.5   c1dc c058 c26a 4246
0.574219 -2.15625  -7.0625 0.119141      7.625    -7.25     5.75 -3.35938     24.375    63.25  10.1875   -29.75   41c3 427d 4123 c1ee
-7.40625  -1.0625   -6.875  -6.5625    -5.6875   -6.125  -3.0625   5.0625      49.25 -11.8125  -8.8125  -5.5625   4245 c13d c10d c0b2
-1.21094  5.21875 -6.03125  -4.4375   -5.09375  1.30469  2.21875 -2.04688         94   -15.25       37      -37   42bc c174 4214 c214
```

### 14. `test_tiled_matmul`: Pass

Host tiling beyond the array size: 8×8 × 8×8 and a ragged 5×9 × 9×6.

Seed 8, elements uniform in [−4, 4]. `gemm_protocol.matmul` splits the product into 4×4×4 runs, zero-padding the ragged edges. Each output tile gets CLEAR_GEMM for its first K block and GEMM for the rest.

**8×8 @ 8×8** (8 on-chip runs): 64/64 bit-exact.

```
A
   -2.1875    3.70312   -2.98438    1.64062    -3.3125   -2.01562          4   -2.32812
   1.13281  -0.326172     -0.375 -0.0400391   -2.46875    2.64062   -3.28125     -2.125
  -3.84375   -1.86719  -0.738281    3.21875   -0.96875   -3.09375   -1.92969     3.9375
      -3.5   0.960938  -0.980469    1.28906   -1.28906    1.53125 -0.0194092    1.19531
   3.21875   0.652344   -2.85938   -3.48438     3.5625 -0.0908203   -2.45312     3.5625
  0.632812    1.82812    3.04688   -1.71094   -1.14844    3.03125   -2.92188    2.10938
  -3.21875    1.52344    1.61719    3.59375       2.75  0.0289307   -2.42188   -2.79688
  0.229492   0.078125   -3.42188    3.21875  0.0593262    1.60938   -2.23438   -2.04688
```

```
B
  -3.90625   -1.25781   -1.86719  -0.613281  -0.984375    2.67188      3.125   -2.59375
 -0.828125   -2.67188    1.30469    3.79688   -2.39062      2.125   -1.60156   -3.89062
   2.10938   -1.26562   -2.64062  -0.515625   -2.14062   -0.71875  -0.431641   -0.65625
  0.707031    -1.6875   -3.23438    -3.3125   -3.14062   0.167969   -1.11719    2.46875
 0.0393066    1.66406    3.84375       -3.5   -3.85938     -2.875  -0.910156   0.589844
   1.95312    -1.1875    3.71875   -3.96875     2.6875    -2.3125          3   -3.73438
   3.71875    2.07812    3.92188   0.640625   -2.57812    3.76562   -0.46875   -3.32812
   0.84375 -0.0223389  -0.214844   -2.76562   -3.03125   0.644531  -0.378906   -2.98438
```

```
C (DUT)
     9.25 -0.886719     7.375        40   -1.3125     32.25    -17.25   -3.5625
 -13.9375       -14     -13.5      0.25     32.25   -10.125     16.75   4.40625
    7.375   3.34375   -27.375  -11.5625   -11.875  -7.96875    -21.25      31.5
   15.625  -3.10938     6.625  -2.85938    4.6875  -5.53125   -8.1875  -0.84375
   -27.75    4.5625      16.5       -10   -6.1875      -5.5    10.375   -17.625
       -2    -18.25    -6.375  -5.09375   7.59375    -10.25    10.375     -23.5
        6   -8.5625  -6.15625      -8.5       -11    -24.75     -17.5    28.125
 -12.8125        -8  -3.78125   -11.125    12.875    -9.875   5.03125    16.875
```

```
C hex
4114 bf63 40ec 4220 bfa8 4201 c18a c064
c15f c160 c158 3e80 4201 c122 4186 408d
40ec 4056 c1db c139 c13e c0ff c1aa 41fc
417a c047 40d4 c037 4096 c0b1 c103 bf58
c1de 4092 4184 c120 c0c6 c0b0 4126 c18d
c000 c192 c0cc c0a3 40f3 c124 4126 c1bc
40c0 c109 c0c5 c108 c130 c1c6 c18c 41e1
c14d c100 c072 c132 414e c11e 40a1 4187
```

**5×9 @ 9×6** (12 on-chip runs): 30/30 bit-exact.

```
A
-0.484375   1.80469   1.72656 -0.229492 -0.851562  -1.11719  -2.20312  -2.42188 -0.429688
 -3.14062   1.80469   1.66406  0.890625   -3.8125  -1.08594 -0.539062     -3.25      3.75
  2.04688 0.0206299   1.64062  -2.39062  -2.17188  0.206055   1.95312   1.17969  -3.95312
  0.90625   3.26562   1.94531   3.42188   3.85938  -2.20312    -1.625  0.378906    3.8125
 -1.04688   3.53125   2.79688  0.129883         1   3.65625   2.26562  -1.63281   2.76562
```

```
B
   -2.4375   -1.03906    3.67188    2.78125   -1.50781   -1.67969
  0.902344    2.73438    1.47656    3.48438    1.82812     2.5625
  0.839844   -1.10156  -0.578125 -0.0805664   0.231445    2.70312
  -1.85156   -3.45312    1.86719   -1.83594  -0.640625    -3.0625
   2.64062   -1.80469   -1.66406     2.4375  0.0339355   -1.78125
   3.10938  -0.707031   -1.10938    3.71875    2.32812    1.97656
        -2        2.5   0.773438    2.64062   -1.05469       2.25
   2.34375  -0.894531    1.23438    2.23438     3.9375    3.35938
   2.29688   -2.90625   0.882812    1.47656   -3.29688  -0.298828
```

```
C (DUT)
-3.29688   4.5625  -2.9375  -12.875 -3.84375 -2.84375
  -2.375      1.5  -1.6875   -20.75  -19.375        3
-14.4375     23.5        5  7.40625   14.875    22.25
   12.25   -26.75  11.9375   10.875    -11.5  -13.125
  19.875   1.8125  -3.5625     31.5  -0.6875    22.25
```

```
C hex
c053 4092 c03c c14e c076 c036
c018 3fc0 bfd8 c1a6 c19b 4040
c167 41bc 40a0 40ed 416e 41b2
4144 c1d6 413f 412e c138 c152
419f 3fe8 c064 41fc bf30 41b2
```

## BF16 MAC unit (`bf16_mac_seq`)

22,800 vectors, 0 mismatches, worst-case latency 27 cycles.

| Test | Vectors | Inputs | Result |
| --- | --- | --- | --- |
| `test_specials` | 2,800 | every acc × every a of 20 special patterns, b from every third pattern | Pass |
| `test_random` | 20,000 | seed 1: 10 % specials, 30 % exponents 120–134, 60 % any bit pattern | Pass |

Latency distribution (cycles: vectors): 2: 3,805, 12: 3,571, 13: 7, 15: 68, 16: 187, 17: 220, 18: 225, 19: 191, 20: 195, 21: 188, 22: 167, 23: 146, 24: 140, 25: 160, 26: 13,353, 27: 177.

Representative special-grid vectors (all vectors are in `test_vectors/mac_vectors.csv`):

| acc | a | b | Expected | Got | Cycles | Result |
| --- | --- | --- | --- | --- | --- | --- |
| `0000` (0) | `7f80` (+inf) | `0000` (0) | `7fc0` | `7fc0` (NaN) | 2 | Pass |
| `3f80` (1) | `7f80` (+inf) | `4000` (2) | `7f80` | `7f80` (+inf) | 2 | Pass |
| `ff80` (-inf) | `7f80` (+inf) | `4000` (2) | `7fc0` | `7fc0` (NaN) | 2 | Pass |
| `3f80` (1) | `7fc0` (NaN) | `4000` (2) | `7fc0` | `7fc0` (NaN) | 2 | Pass |
| `3f80` (1) | `3f80` (1) | `7f81` (NaN) | `7fc0` | `7fc0` (NaN) | 2 | Pass |
| `7f7f` (3.39e+38) | `7f7f` (3.39e+38) | `4000` (2) | `7f80` | `7f80` (+inf) | 12 | Pass |
| `ff7f` (-3.39e+38) | `7f7f` (3.39e+38) | `4000` (2) | `7f80` | `7f80` (+inf) | 12 | Pass |
| `0000` (0) | `7f7f` (3.39e+38) | `7f00` (1.7e+38) | `7f80` | `7f80` (+inf) | 12 | Pass |
| `0000` (0) | `0001` (9.18e-41) | `4000` (2) | `0000` | `0000` (0) | 2 | Pass |
| `0001` (9.18e-41) | `3f80` (1) | `807f` (-1.17e-38) | `0000` | `0000` (0) | 2 | Pass |
| `0000` (0) | `0080` (1.18e-38) | `0080` (1.18e-38) | `0000` | `0000` (0) | 12 | Pass |
| `8000` (-0) | `8000` (-0) | `4000` (2) | `8000` | `8000` (-0) | 2 | Pass |
| `8000` (-0) | `3f80` (1) | `0000` (0) | `0000` | `0000` (0) | 2 | Pass |
| `bf80` (-1) | `3f80` (1) | `4000` (2) | `3f80` | `3f80` (1) | 17 | Pass |
| `3f81` (1.00781) | `3f80` (1) | `4000` (2) | `4040` | `4040` (3) | 16 | Pass |
| `3fff` (1.99219) | `3f81` (1.00781) | `4000` (2) | `4080` | `4080` (4) | 16 | Pass |

## Calculation logic

Every expected value in this report comes from `test/bf16_model.py`, an integer-only model of the chip's arithmetic. A test passes when the chip's 16-bit result is identical to the model's, bit for bit.

### BF16 encoding

A BF16 value is 16 bits: sign (bit 15), exponent (bits 14–7, bias 127) and mantissa (bits 6–0) with a hidden leading 1. The value is (−1)^s × 1.m × 2^(e−127).

| Exponent field | Mantissa | Meaning in this design |
| --- | --- | --- |
| 0 | any | zero; subnormals are read as zero (DAZ) |
| 1–254 | any | normal number |
| 255 | 0 | ±inf |
| 255 | ≠ 0 | NaN; every NaN result is the single quiet NaN `7fc0` |

Host-side conversion (`from_float`) rounds a float32 to BF16 with round-to-nearest-even, flushing subnormals to zero. The decimals shown in this report are the exact values of the bit patterns (`to_float`).

### Multiply, `mul(a, b)`

1. **Specials first.** Any NaN input gives `7fc0`. inf × 0 gives `7fc0`. inf × nonzero gives ±inf. Any zero or subnormal input gives a zero with sign sa ⊕ sb.
2. **Significands.** (0x80 | ma) × (0x80 | mb) is a 16-bit integer, because each operand is 1.m scaled by 2⁷.
3. **Exponent.** e = ea + eb − 127. If product bit 15 is set, the top 8 bits are kept and e increases by 1; otherwise bits 14–7 are kept.
4. **Round to nearest, ties to even.** The bit just below the kept 8 is the guard bit g, and the OR of every lower bit is the sticky bit. The result rounds up when g = 1 and (sticky = 1 or the kept LSB = 1). A carry out of the mantissa renormalizes it.
5. **Range.** e ≥ 255 gives ±inf (overflow). e ≤ 0 gives ±0 (flush to zero).

### Add, `add(a, b)`

1. **Specials.** NaN gives `7fc0`. inf + inf of the same sign gives inf; inf − inf gives `7fc0`. inf + finite gives inf. Zeros pass the other operand through, and 0 + 0 keeps the sign only when both are −0.
2. **Order and align.** Swap so that |a| ≥ |b|. Both significands get three extra low bits (guard, round, sticky). The smaller one shifts right by d = ea − eb, and every bit shifted out is ORed into sticky. If d ≥ 11, the smaller operand becomes sticky only.
3. **Add or subtract** by sign. A carry renormalizes right by one. For a subtraction, an exact zero gives +0; otherwise the result shifts left until the hidden bit is back, lowering e by one per step. This is the long normalize that `test_cancellation` exercises.
4. **Round** with RNE on the guard bit and the round|sticky bits, then apply the same range handling as multiply.

### Multiply-accumulate and matrix product

- `mac(acc, a, b) = add(acc, mul(a, b))`. It is **not fused**: the product is rounded to BF16 before the add, exactly as `bf16_mac_seq` does it.
- `matmul_ref(A, B, n, k, m)` computes each C[i][j] as a chain starting from acc = +0, applying acc = mac(acc, A[i][t], B[t][j]) for t = 0, 1, …, k−1, in the same order the array accumulates. Floating-point addition is not associative, so the order matters for bit-exactness.
- The inner dimension is zero-padded up to a multiple of 4, exactly as the host tiles it. Adding +0 × x leaves a nonzero accumulator unchanged.
- CLEAR_GEMM starts each PE's accumulator from +0. GEMM continues from the current C. So CLEAR_GEMM(A1, B1) followed by GEMM(A2, B2) equals a single K = 8 chain over [A1 | A2] × [B1 ; B2]. `test_accumulate`, `test_rerun_without_reload` and the tiled test check exactly this.
- **Tiling.** For an n×k by k×m product, the host computes each 4×4 output tile as one CLEAR_GEMM on the first 4-wide K block, then one GEMM per remaining block, then a READ_C. That is ⌈n/4⌉·⌈m/4⌉·⌈k/4⌉ runs: 8 runs for 8×8×8 and 12 runs for 5×9×6.

### Worked example: `test_random`, run 1, C[0][0]

| k | a[0][k] | b[k][0] | product = mul(a, b) | acc = add(acc, product) |
| --- | --- | --- | --- | --- |
| start | | | | `0000` (0) |
| 0 | `c0bb` (-5.84375) | `c08b` (-4.34375) | `41cb` (25.375) | `41cb` (25.375) |
| 1 | `40b2` (5.5625) | `c0f3` (-7.59375) | `c229` (-42.25) | `c187` (-16.875) |
| 2 | `4087` (4.21875) | `c091` (-4.53125) | `c199` (-19.125) | `c210` (-36) |
| 3 | `c07b` (-3.92188) | `bf7e` (-0.992188) | `4079` (3.89062) | `c200` (-32) |

The chip returned `c200` (-32) for C[0][0]; the model gives `c200`, an exact match. The exact real-number dot product is -32.0814. The difference comes from the eight BF16 roundings (one after each multiply, one after each add), which the hardware performs identically. This is why the tests compare bit patterns, not values within a tolerance.

### MAC unit check and latency

`test_mac` drives `bf16_mac_seq` directly with (acc, a, b) and compares `result` with `mac(acc, a, b)`. Latency is the number of clock edges from the `go` pulse to `done`. One row engine serves its 4 PEs in turn every 128-cycle beat, and at most 4 × (27 + 2) + 1 = 117 cycles of each beat are used. A simulation-only assertion in `gemm_controller` fires if any row is still busy at the next beat.

### How the counts in this report are made

- **Pass/fail** per test comes from cocotb's `results.xml`.
- **Bit-exact** counts compare each READ_C value with the `matmul_ref` value the test itself asserted against. Both are captured by `test/report/test_report.py`, which wraps the test helpers without changing what is sent or checked.
- **MAC vectors** and latencies are captured by `test/report/test_mac_report.py`, which uses the same `go`/`done` loop as `test_mac.run`.
- **On-chip run counts:** 1 + 20 + 2 + 3 + 1 + 3 + 1 + 1 + 2 + 1 + (8 + 12) = 55 GEMM runs.

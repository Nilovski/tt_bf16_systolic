# Validation and reproducibility

This record covers the 4x4 BF16 output-stationary systolic array
`tt_um_apex_bf16_systolic`. It separates implementation-flow results,
functional checks of the RTL and of the routed gate-level netlist, and the
design history that led to the current architecture. It does not report
fabricated-silicon measurements, and the gate-level simulation is not a
timing (SDF) simulation.

## Fixed hardware and build record

The reference implementation for this document is repository commit
[`4fde7273d2e640b1a9c47e6451c3d0960c266588`](https://github.com/Nilovski/tt_bf16_systolic/tree/4fde7273d2e640b1a9c47e6451c3d0960c266588).
The commit that adds this document changes only documentation.

Source hashes (SHA-256), as printed by the GDS run below:

```text
dd11a0ada2bd0664f8dd588818d4d0535c8f560f700568961f9811c67499d4ed  info.yaml
4238ab84d75eaf3b0e7935a150dc11bc7dae552dc5a6d34fd3016dd8ecea53f7  src/compute/bf16_adder.sv   (reference only, not in the build)
3909577c8201b6c37604f4144f982a388e6da65014d13b82cd1a5b9aae372ec1  src/compute/bf16_mac_seq.sv
622860015de4682bf4235192d567b5cc874e52a75f62761c5afea4e7a0046172  src/compute/bf16_multiplier.sv   (reference only, not in the build)
86f79c8e6712a47821cfbd553c6dd471786b629d2137b0db51e0d2be26f30c02  src/compute/pe_row_engine.sv
2b4717201276e67704bb3b1e815dccab5a849bbe0e38d4cf0abab307bd195ce3  src/compute/systolic_array.sv
2afcec48160530ac00735419ab2dfb4f2a46b1ca8a45d42512fa11d38658260f  src/compute/systolic_pe.sv
8dfa9d29537da2a16c748f8264b2839d4af84250b7c043174041ef154bfda2cc  src/config.json
addc508b627cf289afa0e02b142be847553f5c8a42e558e9ab6dc944b6348f0e  src/control/gemm_controller.sv
a9b3d4d0aa4a8f3cc19c0f3d24a1a176f1b267cc4d7bfbc49d2ff88b0249ef92  src/interface/command_decoder.sv
06dff5e2be0d49046fd5e511f7b33996400b67cd9fa19267f9a67a97e3734213  src/interface/rx_byte_interface.sv
32f23b71e07369b6e38e8a9bed2063cae24c398089af0a6f2943f09fa5876984  src/interface/status_register.sv
9454de7ce174da598012a5c5041aafab5e1c5b53fa3e284be7e995eef9e95584  src/interface/tx_byte_interface.sv
1818cbed3c8d7f1536672701a56bd4fea76ff6c4d6eae114799f4d2e267eac04  src/output/result_mux.sv
3ed0747c58b6b91d2d12cc529da92ce918498935ff9274af041356dfcb82951a  src/prep/data_prep_unit.sv
8f56dee0a98ce47c416b3463db836839530dbdf69a7f24df1e186ff8964801fb  src/tt_um_apex_bf16_systolic.sv
```

| Check | Recorded result | Evidence |
| --- | --- | --- |
| GDS implementation | Passed | [GDS run 40565085292](https://github.com/Nilovski/tt_bf16_systolic/actions/runs/40565085292) |
| Tiny Tapeout precheck (DRC and layout checks) | Passed | same run, `precheck` job |
| Gate-level regression (14 full-chip tests on the routed netlist) | 14 of 14 passed | same run, `gl_test` job |
| 3D viewer (GitHub Pages) | Passed | same run, `viewer` job |
| RTL full-chip regression (14 tests) | 14 of 14 passed | [Test run 40565085312](https://github.com/Nilovski/tt_bf16_systolic/actions/runs/40565085312) |
| BF16 MAC unit regression (2 tests, about 28,000 vectors) | 2 of 2 passed | same test run |

The RTL and gate-level jobs run the same pin-level cocotb suite
(`test/test.py`). The gate-level job uses functional standard-cell models
with unit delays; it checks the netlist's logic, not its timing. The
CI test and build summaries above are printed as run notices by
`scripts/ci_summary.py`.

Tools: Icarus Verilog (Ubuntu 24.04 package), cocotb 2.1.0, pytest 8.4.2,
Python 3.11 in CI; LibreLane through `TinyTapeout/tt-gds-action@ttsky26d`,
PDK sky130A.

### Implementation metrics and limits

Values below are taken from the final `metrics.json` of that GDS run.

| Metric | Recorded value |
| --- | ---: |
| Clock-period constraint | 20 ns (50 MHz target) |
| Die (6x2 tiles) | 1030.40 x 225.76 um |
| Standard-cell area (excluding fill) | 130,768 um^2 |
| Placement utilization | 57.9 % |
| Standard cells (excluding fill) | 14,307, of which 1,741 flip-flops, 2,946 timing-repair buffers (2,040 for hold) |
| Worst setup slack, typical corner (`nom_tt_025C_1v80`) | +8.20 ns |
| Worst setup slack, all nine corners | -0.695 ns at `max_ss_100C_1v60` (2 paths); -0.301 ns at `nom_ss_100C_1v60` (2 paths); all tt and ff corners positive |
| Setup total negative slack | -1.27 ns |
| Worst hold slack, all nine corners | +0.109 ns at `min_ff_n40C_1v95`; 0 hold violations at every corner |
| Worst clock skew (setup / hold) | 0.324 ns / -0.408 ns |
| Max slew violations | 3,633 at `max_ss_100C_1v60`; 157 to 308 at the tt corners; 39 to 83 at the ff corners |
| Max capacitance violations | 13 at `max_ss_100C_1v60`, 9 at `nom_ss`, 4 at `min_ss`, 0 at tt and ff corners |
| Max fanout violations | 146 at every corner |
| Routing DRC errors | 0 after 8 detailed-routing iterations (257 at the first) |
| Magic DRC, LVS, antenna, power-grid errors | 0 each |
| Flow errors | 0 |
| Routed wirelength | 381,128 um |
| Reported total power estimate | 7.31 mW |

The setup violations are confined to the slow-slow 100 C, 1.60 V corners:
at the worst of them the design would need about 20.7 ns (48 MHz) instead of
20 ns. At the typical corner the slack of 8.20 ns implies about 11.8 ns
(85 MHz) of internal logic delay, well above what the pads allow. The
build passed with them, so the flow's timing acceptance does not cover the
slow corners; they are listed so that the build is not mistaken for
all-corner closure.

The area synthesised before place and route (about 83,000 um^2, area-only
mapping) grows to 130,768 um^2 after placement, mostly through timing-repair
and hold buffers (29,023 um^2) and the clock tree (3,533 um^2).

Standard-cell area is not the allocated tile area (6x2 tiles). A
successful workflow means the Tiny Tapeout acceptance checks passed; it
does not mean zero violations at every reported corner, so the per-corner
counts are listed rather than summarised as "clean".

The design is constrained at a 20 ns clock period (50 MHz). The
[Tiny Tapeout GPIO specification](https://tinytapeout.com/specs/gpio/)
rates the pads at 66 MHz input and 33 MHz output, and notes that a
project's own f_max comes from its static timing analysis, not the pads.
The protocol is fully handshaked, so the host may run the chip at any
clock up to those limits; the demo-board runner uses 10 MHz or less.

## Functional verification

### Reference model

`test/bf16_model.py` is an integer-only, bit-exact model of the chip's
arithmetic. Format: 1 sign, 8 exponent (bias 127), 7 mantissa bits.

- Subnormal inputs read as zero; results below the normal range flush to
  signed zero.
- Round to nearest, ties to even, after the multiply and again after the add.
- Any NaN input, inf x 0 and inf - inf give the quiet NaN `0x7FC0`.
- Overflow gives signed infinity; x + (-x) = +0.
- A matrix element is the chain `acc = add(acc, mul(a, b))` over k = 0..K-1,
  starting from +0, in the order the array accumulates.

Every functional check below compares the hardware against this model
bit for bit, not within a tolerance.

### BF16 MAC unit (`test/mac`)

`bf16_mac_seq` is the multi-cycle multiply-accumulate shared by each row of
PEs. It is tested on its own against `mac()` in the model.

| Test | Stimulus | Result |
| --- | --- | --- |
| `test_specials` | 20 special values (+-0, subnormals, +-1, 2, values just above 1 and below 2, +-largest and +-smallest normal, +-inf, quiet and signalling NaN) for acc and a, every third of them for b: 2,800 cases | pass (RTL) |
| `test_random` | 20,000 random (acc, a, b): 10 % special values, 30 % exponents in 120..134 (many ties and near-cancellations), 60 % uniform bit patterns | pass (RTL) |

Measured worst-case latency over all vectors: **27 clock cycles** from
`go` to `done`. This sets the beat length (below).

### Full-chip regression (`test/test.py`)

All tests drive the chip only through its pins, with the same byte
protocol a real host uses (`test/gemm_protocol.py`).

| Test | What it checks | RTL | Gate-level |
| --- | --- | --- | --- |
| `test_id` | ID reply 0xA8 | pass | pass |
| `test_identity` | I x B = B, and STATUS done, A_loaded, B_loaded and result_valid after the run | pass | pass |
| `test_plan_cases` | A x I = A, I x B = B, and all ones gives all 4.0 | pass | pass |
| `test_random` | 20 random 4x4 products, values uniform in +-8 | pass | pass |
| `test_accumulate` | CLEAR_GEMM then GEMM equals one product with K = 8 | pass | pass |
| `test_rerun_without_reload` | A second CLEAR_GEMM without reloading gives the same C; GEMM doubles it | pass | pass |
| `test_read_element` | READ_C_ELEMENT for indices 0, 5, 10, 15 | pass | pass |
| `test_unknown_opcode_sets_error` | An unknown byte sets STATUS error; reading STATUS clears it | pass | pass |
| `test_specials` | inf x 2 = inf, inf x 0 = NaN, NaN input, overflow to inf (3e38 x 2 + 3e38 x 2), subnormal input read as 0 | pass | pass |
| `test_cancellation` | x + (-x) = +0, and sums that cancel to a few low bits (several normalize steps) | pass | pass |
| `test_status_bits_and_busy` | STATUS after reset, after each load, mid-run and after the run; a LOAD during a run is swallowed, sets error and leaves A intact; BUSY and DONE pins | pass | pass |
| `test_ena_low_ignores_input` | No reply while `ena` is low; `uio_oe` = 0b00111010 | pass | pass |
| `test_read_c_slow_host` | READ_C with a host that waits 9 cycles before taking each of the 32 bytes | pass | pass |
| `test_tiled_matmul` | Host-tiled 8x8 x 8x8 and 5x9 x 9x6 products, bit-exact with the model | pass | pass |

### Beat timing check

The array advances one systolic step per 128-cycle beat. In each beat a
row's MAC visits its 4 PEs: at most 4 x (27 + 2) + 1 = 117 cycles, so the
beat leaves 11 cycles of margin. `gemm_controller` contains a
simulation-only assertion that fails if any row engine is still busy when
the next beat (or the end of the run) arrives. It did not fire in any
RTL run. A 4x4 run is 10 beats, about 1,283 cycles (128 us at 10 MHz).

## Design history

The first BF16 version (branch `bf16-full-plan` of
[Nilovski/4x4_test](https://github.com/Nilovski/4x4_test)) placed a
combinational BF16 multiplier and adder in every PE. It passed its RTL
tests but did not complete implementation:

| Attempt | Tiles | Outcome |
| --- | --- | --- |
| Combinational BF16 PEs | 6x2 | Placement utilization 95 %, did not fit |
| Combinational BF16 PEs, density 70, 50 ns clock | 8x2 | Detailed routing ended at 110,281 violations after about 5 h ([run 40406305890](https://github.com/Nilovski/4x4_test/actions/runs/40406305890)) |
| Shared multi-cycle MAC per row (this design) | 6x2 | Passed GDS, precheck and gate-level tests |

Synthesised with the same SKY130 HD cells (area-only mapping, typical
corner), the combinational version is about 140,000 um^2 and this design
about 83,000 um^2. A multi-cycle MAC in every PE would save little,
because its registers and steering logic cost about as much as the
combinational datapath; sharing one MAC per row is what reduced the area.

## Known limits

- 4x4, not 8x8: an 8x8 BF16 array with 64-entry operand buffers would need
  roughly the full 8x2 area before routing. Larger products are tiled by the
  host (`gemm_protocol.matmul`), and the tiled result is still bit-exact
  with the model because the K-blocks accumulate on chip.
- No subnormal support (flush to zero), one NaN encoding, no exception flags.
- About 128 us per 4x4 product at 10 MHz.
- No silicon measurement, no SDF-annotated timing simulation, no formal
  proof.

## Reproducing the repository checks

Use a fixed checkout and record `git rev-parse HEAD`. With Python 3.11,
Icarus Verilog and GNU Make:

```sh
python -m pip install -r test/requirements.txt
cd test
make clean && make
python -m cocotb_tools.check_results results.xml
cd mac
make clean && make
python -m cocotb_tools.check_results results.xml
```

For implementation results, keep the GDS workflow URL, the commit and the
`GDS_logs` artifact of that run; Actions artifacts expire. Rebuilding the
same RTL does not guarantee identical placement, routing or timing numbers.

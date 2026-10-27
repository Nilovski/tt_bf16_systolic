# Testbench

cocotb tests for `tt_um_apex_bf16_systolic`. `tb.v` wraps the design,
`test.py` holds the full-chip tests, `gemm_protocol.py` is the host protocol
and tiling library shared with the demo-board runner in `../host`, and
`bf16_model.py` is the bit-exact BF16 reference every result is checked
against. `mac/` is a standalone test of the BF16 MAC unit (`bf16_mac_seq`).

## Running

RTL simulation (full chip):

```sh
make -B
```

MAC unit (~28k vectors, including NaN, inf and subnormals):

```sh
cd mac && make -B
```

Gate-level simulation: harden the project, copy the netlist from
`../runs/wokwi/final/pnl/tt_um_apex_bf16_systolic.pnl.v` to
`gate_level_netlist.v`, then run:

```sh
make -B GATES=yes
```

## Viewing waveforms

```sh
gtkwave tb.fst tb.gtkw
```

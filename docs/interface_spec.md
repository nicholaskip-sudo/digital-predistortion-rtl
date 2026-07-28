# Streaming Interface Specification

The RTL will use separate signed I and Q ports with ready/valid flow control.

## systemverilog

input  logic                clk;
input  logic                rst_n;
input  logic                in_valid;
output logic                in_ready;
input  logic signed [15:0]  in_i;
input  logic signed [15:0]  in_q;
output logic                out_valid;
input  logic                out_ready;
output logic signed [15:0]  out_i;
output logic signed [15:0]  out_q;


An input transfers when 'in_valid && in_ready'.

An output transfers when 'out_valid && out_ready'.

Reset is active-low and asynchronously asserted. The MVP throughput target is one
complex sample per clock after pipeline fill.

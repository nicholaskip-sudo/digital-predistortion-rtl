`default_nettype none

interface dpd_stress_if (
    input wire clk
);

    timeunit 1ns;
    timeprecision 1ps;

    import dpd_pkg::*;

    localparam logic [1:0] DPD_COEFF_MODE_UNKNOWN  = 2'd0;
    localparam logic [1:0] DPD_COEFF_MODE_IDENTITY = 2'd1;
    localparam logic [1:0] DPD_COEFF_MODE_ZERO     = 2'd2;

    logic rst_n;

    logic in_valid;
    logic in_ready;
    dpd_sample_t in_i;
    dpd_sample_t in_q;

    logic out_valid;
    logic out_ready;
    dpd_sample_t out_i;
    dpd_sample_t out_q;

    dpd_coefficient_t coefficient_i [0:DPD_NUM_COEFFICIENTS-1];
    dpd_coefficient_t coefficient_q [0:DPD_NUM_COEFFICIENTS-1];
    logic [1:0] coefficient_mode;

    clocking driver_cb @(negedge clk);
        default input #1step output #0;

        input in_ready;

        output rst_n;
        output in_valid;
        output in_i;
        output in_q;
        output out_ready;
    endclocking

    clocking monitor_cb @(posedge clk);
        default input #1step output #0;

        input rst_n;
        input in_valid;
        input in_ready;
        input in_i;
        input in_q;
        input out_valid;
        input out_ready;
        input out_i;
        input out_q;
        input coefficient_mode;
    endclocking

    property p_output_stable_when_stalled;
        @(posedge clk) disable iff (!rst_n)
            out_valid && !out_ready
            |=> out_valid && $stable(out_i) && $stable(out_q);
    endproperty

    property p_input_stable_until_accepted;
        @(posedge clk) disable iff (!rst_n)
            in_valid && !in_ready
            |=> in_valid && $stable(in_i) && $stable(in_q);
    endproperty

    property p_no_output_valid_during_reset;
        @(posedge clk)
            !rst_n |-> !out_valid;
    endproperty

    assert property (p_output_stable_when_stalled)
        else $fatal(
            1,
            "DPD stress interface: output changed while backpressured."
        );

    assert property (p_input_stable_until_accepted)
        else $fatal(
            1,
            "DPD stress interface: input changed before acceptance."
        );

    assert property (p_no_output_valid_during_reset)
        else $fatal(
            1,
            "DPD stress interface: out_valid asserted during reset."
        );

endinterface

`default_nettype wire

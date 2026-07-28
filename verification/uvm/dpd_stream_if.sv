'default_nettype none

interface dpd_stream_if (
    input wire clk
);

    timeunit 1ns;
    timeprecision 1ps;

    import dpd_pkg::*;

    logic rst_n;

    logic in_valid;
    logic in_ready;
    dpd_sample_t in_i;
    dpd_sample_t in_q;

    logic out_valid;
    logic out_ready;
    dpd_sample_t out_i;
    dpd_sample_t out_q;

    clocking driver_cb @(negedge clk);
        default input #1step output #0;

        input rst_n;

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

    assert property (p_output_stable_when_stalled)
        else $fatal(
            1,
            "UVM interface: output changed while backpressured."
        );

    assert property (p_input_stable_until_accepted)
        else $fatal(
            1,
            "UVM interface: input changed before acceptance."
        );

endinterface

'default_nettype wire

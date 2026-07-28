'default_nettype none

module dpd_protocol_negative_tb;

    timeunit 1ns;
    timeprecision 1ps;

    import dpd_pkg::*;

    logic clk;
    string negative_test;

    dpd_stream_if stream_if (
        .clk (clk)
    );

    initial begin : clock_generator
        clk = 1'b0;
        forever #5ns clk = ~clk;
    end

    initial begin : negative_stimulus
        negative_test = "input_stability";
        void'($value$plusargs(
            "NEGATIVE_TEST=%s",
            negative_test
        ));

        stream_if.rst_n = 1'b0;
        stream_if.in_valid = 1'b0;
        stream_if.in_ready = 1'b0;
        stream_if.in_i = '0;
        stream_if.in_q = '0;
        stream_if.out_valid = 1'b0;
        stream_if.out_ready = 1'b0;
        stream_if.out_i = '0;
        stream_if.out_q = '0;

        repeat (3) @(negedge clk);
        stream_if.rst_n = 1'b1;

        if (negative_test == "input_stability") begin
            @(negedge clk);
            stream_if.in_valid = 1'b1;
            stream_if.in_ready = 1'b0;
            stream_if.in_i = dpd_sample_t'(16'sd100);
            stream_if.in_q = dpd_sample_t'(16'shFF38);

            @(negedge clk);
            stream_if.in_i = dpd_sample_t'(16'sd101);

            repeat (3) @(posedge clk);
        end
        else if (negative_test == "output_stability") begin
            @(negedge clk);
            stream_if.out_valid = 1'b1;
            stream_if.out_ready = 1'b0;
            stream_if.out_i = dpd_sample_t'(16'sd300);
            stream_if.out_q = dpd_sample_t'(16'sd400);

            @(negedge clk);
            stream_if.out_q = dpd_sample_t'(16'sd401);

            repeat (3) @(posedge clk);
        end
        else begin
            $fatal(
                1,
                "Unknown NEGATIVE_TEST value: %s",
                negative_test
            );
        end

        $display(
            "NEGATIVE_PROTOCOL_TEST_UNEXPECTED_PASS test=%s",
            negative_test
        );
        $finish;
    end

endmodule

'default_nettype wire

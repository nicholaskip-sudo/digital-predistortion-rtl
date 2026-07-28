'default_nettype none

module dpd_uvm_tb;

    timeunit 1ns;
    timeprecision 1ps;

    import uvm_pkg::*;
    import dpd_pkg::*;
    import dpd_uvm_pkg::*;

    logic clk;

    dpd_coefficient_t coefficient_i [0:DPD_NUM_COEFFICIENTS-1];
    dpd_coefficient_t coefficient_q [0:DPD_NUM_COEFFICIENTS-1];

    dpd_stream_if stream_if (
        .clk (clk)
    );

    dpd_core dut (
        .clk           (clk),
        .rst_n         (stream_if.rst_n),

        .in_valid      (stream_if.in_valid),
        .in_ready      (stream_if.in_ready),
        .in_i          (stream_if.in_i),
        .in_q          (stream_if.in_q),

        .out_valid     (stream_if.out_valid),
        .out_ready     (stream_if.out_ready),
        .out_i         (stream_if.out_i),
        .out_q         (stream_if.out_q),

        .coefficient_i (coefficient_i),
        .coefficient_q (coefficient_q)
    );

    initial begin : clock_generator
        clk = 1'b0;
        forever #5ns clk = ~clk;
    end

    initial begin : reset_generator
        stream_if.rst_n = 1'b0;
        repeat (4) @(negedge clk);
        stream_if.rst_n = 1'b1;
    end

    initial begin : configure_and_run_uvm
        string test_name;
        string vector_directory;
        string filename;
        int sample_count;

        test_name = "dpd_short_uvm_test";
        void'($value$plusargs(
            "UVM_TESTNAME=%s",
            test_name
        ));

        if (test_name == "dpd_full_uvm_test") begin
            vector_directory = "vectors/rtl/ofdm_nominal";
            sample_count = 36864;
        end
        else begin
            vector_directory = "vectors/rtl/ofdm_short";
            sample_count = 512;
        end

        void'($value$plusargs(
            "VECTOR_DIR=%s",
            vector_directory
        ));
        void'($value$plusargs(
            "SAMPLE_COUNT=%d",
            sample_count
        ));

        if (
            sample_count <= 0
            || sample_count > DPD_UVM_MAX_SAMPLE_COUNT
        ) begin
            $fatal(
                1,
                "Invalid UVM sample count: %0d.",
                sample_count
            );
        end

        filename = $sformatf(
            "%s/coefficients_i.hex",
            vector_directory
        );
        $readmemh(filename, coefficient_i);

        filename = $sformatf(
            "%s/coefficients_q.hex",
            vector_directory
        );
        $readmemh(filename, coefficient_q);

        uvm_config_db#(
            virtual dpd_stream_if
        )::set(
            null,
            "*",
            "vif",
            stream_if
        );

        uvm_config_db#(string)::set(
            null,
            "*",
            "vector_directory",
            vector_directory
        );

        uvm_config_db#(int)::set(
            null,
            "*",
            "sample_count",
            sample_count
        );

        $display(
            "DPD_UVM_CONFIG test=%s directory=%s samples=%0d coefficients=%0d",
            test_name,
            vector_directory,
            sample_count,
            DPD_NUM_COEFFICIENTS
        );

        run_test();
    end

    initial begin : timeout
        #5ms;
        $fatal(1, "DPD UVM regression timed out.");
    end

endmodule

'default_nettype wire

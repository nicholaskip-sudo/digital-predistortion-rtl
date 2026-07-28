`default_nettype none

module dpd_stress_tb;

    timeunit 1ns;
    timeprecision 1ps;

    import uvm_pkg::*;
    import dpd_pkg::*;
    import dpd_stress_pkg::*;

    logic clk;

    dpd_stress_if stress_if (
        .clk (clk)
    );

    dpd_core dut (
        .clk           (clk),
        .rst_n         (stress_if.rst_n),

        .in_valid      (stress_if.in_valid),
        .in_ready      (stress_if.in_ready),
        .in_i          (stress_if.in_i),
        .in_q          (stress_if.in_q),

        .out_valid     (stress_if.out_valid),
        .out_ready     (stress_if.out_ready),
        .out_i         (stress_if.out_i),
        .out_q         (stress_if.out_q),

        .coefficient_i (stress_if.coefficient_i),
        .coefficient_q (stress_if.coefficient_q)
    );

    initial begin : clock_generator
        clk = 1'b0;
        forever #5ns clk = ~clk;
    end

    initial begin : configure_and_run_uvm
        int stress_seed;

        stress_seed = 13013;
        void'($value$plusargs(
            "STRESS_SEED=%d",
            stress_seed
        ));

        uvm_config_db#(
            virtual dpd_stress_if
        )::set(
            null,
            "*",
            "vif",
            stress_if
        );

        uvm_config_db#(int)::set(
            null,
            "*",
            "stress_seed",
            stress_seed
        );

        $display(
            "DPD_STRESS_CONFIG seed=%0d identity_samples=%0d zero_samples=%0d recovery_samples=%0d",
            stress_seed,
            DPD_STRESS_IDENTITY_SAMPLE_COUNT,
            DPD_STRESS_ZERO_SAMPLE_COUNT,
            DPD_STRESS_RECOVERY_SAMPLE_COUNT
        );

        run_test();
    end

    initial begin : timeout
        #2ms;
        $fatal(1, "DPD randomized UVM stress regression timed out.");
    end

endmodule

`default_nettype wire

'default_nettype none

module dpd_core_tb;

    timeunit 1ns;
    timeprecision 1ps;

    import dpd_pkg::*;

    localparam int unsigned MAX_SAMPLE_COUNT = 36864;

    logic clk;
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

    dpd_sample_t input_i_memory [0:MAX_SAMPLE_COUNT-1];
    dpd_sample_t input_q_memory [0:MAX_SAMPLE_COUNT-1];
    dpd_sample_t expected_i_memory [0:MAX_SAMPLE_COUNT-1];
    dpd_sample_t expected_q_memory [0:MAX_SAMPLE_COUNT-1];

    string vector_directory;
    string test_name;
    string filename;

    int unsigned sample_count;
    int unsigned sent_count;
    int unsigned received_count;
    int unsigned cycle_count;
    int unsigned first_input_cycle;
    int unsigned first_output_cycle;

    logic first_input_seen;
    logic first_output_seen;

    dpd_core dut (
        .clk           (clk),
        .rst_n         (rst_n),
        .in_valid      (in_valid),
        .in_ready      (in_ready),
        .in_i          (in_i),
        .in_q          (in_q),
        .out_valid     (out_valid),
        .out_ready     (out_ready),
        .out_i         (out_i),
        .out_q         (out_q),
        .coefficient_i (coefficient_i),
        .coefficient_q (coefficient_q)
    );

    initial begin : clock_generator
        clk = 1'b0;
        forever #5ns clk = ~clk;
    end

    initial begin : vector_configuration
        vector_directory = "vectors/rtl/ofdm_short";
        test_name = "ofdm_short";
        sample_count = 512;

        void'($value$plusargs("VECTOR_DIR=%s", vector_directory));
        void'($value$plusargs("TEST_NAME=%s", test_name));
        void'($value$plusargs("SAMPLE_COUNT=%d", sample_count));

        if (sample_count == 0) begin
            $fatal(1, "SAMPLE_COUNT must be greater than zero.");
        end

        if (sample_count > MAX_SAMPLE_COUNT) begin
            $fatal(
                1,
                "SAMPLE_COUNT=%0d exceeds MAX_SAMPLE_COUNT=%0d.",
                sample_count,
                MAX_SAMPLE_COUNT
            );
        end

        filename = $sformatf("%s/input_i.hex", vector_directory);
        $readmemh(filename, input_i_memory, 0, sample_count - 1);

        filename = $sformatf("%s/input_q.hex", vector_directory);
        $readmemh(filename, input_q_memory, 0, sample_count - 1);

        filename = $sformatf("%s/expected_i.hex", vector_directory);
        $readmemh(filename, expected_i_memory, 0, sample_count - 1);

        filename = $sformatf("%s/expected_q.hex", vector_directory);
        $readmemh(filename, expected_q_memory, 0, sample_count - 1);

        filename = $sformatf("%s/coefficients_i.hex", vector_directory);
        $readmemh(filename, coefficient_i);

        filename = $sformatf("%s/coefficients_q.hex", vector_directory);
        $readmemh(filename, coefficient_q);

        $display(
            "DPD_VECTOR_CONFIG test=%s directory=%s samples=%0d coefficients=%0d",
            test_name,
            vector_directory,
            sample_count,
            DPD_NUM_COEFFICIENTS
        );
    end

    initial begin : reset_generator
        rst_n = 1'b0;
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
    end

    always_comb begin : input_driver
        if (sent_count < sample_count) begin
            in_valid = 1'b1;
            in_i = input_i_memory[sent_count];
            in_q = input_q_memory[sent_count];
        end
        else begin
            in_valid = 1'b0;
            in_i = '0;
            in_q = '0;
        end
    end

    always_comb begin : output_backpressure
        out_ready = !(
            ((cycle_count % 11) == 5)
            || ((cycle_count % 17) == 9)
        );
    end

    always_ff @(posedge clk or negedge rst_n) begin : counters_and_scoreboard
        if (!rst_n) begin
            sent_count <= 0;
            received_count <= 0;
            cycle_count <= 0;
            first_input_cycle <= 0;
            first_output_cycle <= 0;
            first_input_seen <= 1'b0;
            first_output_seen <= 1'b0;
        end
        else begin
            cycle_count <= cycle_count + 1;

            if (in_valid && in_ready) begin
                if (!first_input_seen) begin
                    first_input_cycle <= cycle_count + 1;
                    first_input_seen <= 1'b1;
                end
                sent_count <= sent_count + 1;
            end

            if (out_valid && out_ready) begin
                if (!first_output_seen) begin
                    first_output_cycle <= cycle_count + 1;
                    first_output_seen <= 1'b1;
                end

                if (received_count >= sample_count) begin
                    $fatal(
                        1,
                        "Received more than %0d output samples.",
                        sample_count
                    );
                end

                if (
                    (out_i !== expected_i_memory[received_count])
                    || (out_q !== expected_q_memory[received_count])
                ) begin
                    $fatal(
                        1,
                        "DPD mismatch test=%s sample=%0d actual=(%0d,%0d) expected=(%0d,%0d)",
                        test_name,
                        received_count,
                        $signed(out_i),
                        $signed(out_q),
                        $signed(expected_i_memory[received_count]),
                        $signed(expected_q_memory[received_count])
                    );
                end

                if ((received_count + 1) == sample_count) begin
                    assert (sent_count == sample_count)
                        else $fatal(
                            1,
                            "Output completed before all inputs were accepted: sent=%0d expected=%0d.",
                            sent_count,
                            sample_count
                        );

                    $display(
                        "DPD_CORE_REGRESSION_PASS test=%s samples=%0d cycles=%0d latency_cycles=%0d",
                        test_name,
                        sample_count,
                        cycle_count + 1,
                        first_output_seen
                            ? (first_output_cycle - first_input_cycle)
                            : ((cycle_count + 1) - first_input_cycle)
                    );
                    $finish;
                end

                received_count <= received_count + 1;
            end
        end
    end

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

    property p_output_requires_prior_input;
        @(posedge clk) disable iff (!rst_n)
            out_valid |-> (sent_count > received_count);
    endproperty

    assert property (p_output_stable_when_stalled)
        else $fatal(1, "Output changed while backpressured.");

    assert property (p_input_stable_until_accepted)
        else $fatal(1, "Input changed before it was accepted.");

    assert property (p_output_requires_prior_input)
        else $fatal(1, "Output valid asserted without a prior accepted input.");

    initial begin : timeout
        #1ms;
        $fatal(
            1,
            "DPD core simulation timed out: test=%s sent=%0d received=%0d cycles=%0d",
            test_name,
            sent_count,
            received_count,
            cycle_count
        );
    end

endmodule

'default_nettype wire

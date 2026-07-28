`default_nettype none

package dpd_stress_pkg;

    timeunit 1ns;
    timeprecision 1ps;

    import uvm_pkg::*;
    import dpd_pkg::*;

    `include "uvm_macros.svh"

    localparam int unsigned DPD_STRESS_IDENTITY_SAMPLE_COUNT = 1024;
    localparam int unsigned DPD_STRESS_ZERO_SAMPLE_COUNT = 512;
    localparam int unsigned DPD_STRESS_RECOVERY_SAMPLE_COUNT = 512;
    localparam int unsigned DPD_STRESS_TOTAL_SAMPLE_COUNT =
        DPD_STRESS_IDENTITY_SAMPLE_COUNT
        + DPD_STRESS_ZERO_SAMPLE_COUNT
        + DPD_STRESS_RECOVERY_SAMPLE_COUNT;

    localparam int unsigned DPD_STRESS_RESET_AFTER_INPUTS = 257;
    localparam int unsigned DPD_STRESS_RESET_CYCLES = 3;

    localparam logic [1:0] DPD_COEFF_MODE_UNKNOWN  = 2'd0;
    localparam logic [1:0] DPD_COEFF_MODE_IDENTITY = 2'd1;
    localparam logic [1:0] DPD_COEFF_MODE_ZERO     = 2'd2;


    class dpd_stress_item extends uvm_sequence_item;

        dpd_sample_t sample_i;
        dpd_sample_t sample_q;
        int unsigned sample_index;
        int unsigned gap_cycles;

        `uvm_object_utils(dpd_stress_item)

        function new(string name = "dpd_stress_item");
            super.new(name);
        endfunction

        function string convert2string();
            return $sformatf(
                "index=%0d sample=(%0d,%0d) gap=%0d",
                sample_index,
                $signed(sample_i),
                $signed(sample_q),
                gap_cycles
            );
        endfunction

    endclass


    class dpd_stress_sequence extends uvm_sequence #(dpd_stress_item);

        int unsigned sample_count;
        int unsigned first_sample_index;
        int unsigned sequence_seed;
        int unsigned maximum_gap_cycles;

        `uvm_object_utils(dpd_stress_sequence)

        function new(string name = "dpd_stress_sequence");
            super.new(name);
            sample_count = 512;
            first_sample_index = 0;
            sequence_seed = 32'h1;
            maximum_gap_cycles = 3;
        endfunction

        function automatic int unsigned next_lfsr(
            input int unsigned current_value
        );
            int unsigned next_value;
            bit feedback;

            feedback = current_value[31]
                ^ current_value[21]
                ^ current_value[1]
                ^ current_value[0];

            next_value = {
                current_value[30:0],
                feedback
            };

            if (next_value == 0) begin
                next_value = 32'h1;
            end

            return next_value;
        endfunction

        task body();
            int unsigned lfsr_state;
            dpd_stress_item request;

            if (sample_count == 0) begin
                `uvm_fatal(
                    "DPD_STRESS_SEQUENCE_CONFIG",
                    "sample_count must be greater than zero."
                )
            end

            lfsr_state = sequence_seed;
            if (lfsr_state == 0) begin
                lfsr_state = 32'h1;
            end

            for (int unsigned offset = 0;
                 offset < sample_count;
                 offset++) begin

                request = dpd_stress_item::type_id::create(
                    $sformatf("stress_request_%0d", offset)
                );

                start_item(request);

                lfsr_state = next_lfsr(lfsr_state);
                request.sample_i = dpd_sample_t'(
                    lfsr_state[15:0]
                );

                lfsr_state = next_lfsr(lfsr_state);
                request.sample_q = dpd_sample_t'(
                    lfsr_state[15:0]
                );

                // Periodic directed edge values complement the random stream.
                case (offset % 64)
                    0: begin
                        request.sample_i = dpd_sample_t'(16'sh7FFF);
                        request.sample_q = dpd_sample_t'(16'sh0000);
                    end
                    1: begin
                        request.sample_i = dpd_sample_t'(16'sh8000);
                        request.sample_q = dpd_sample_t'(16'sh0001);
                    end
                    2: begin
                        request.sample_i = dpd_sample_t'(16'sh0000);
                        request.sample_q = dpd_sample_t'(16'sh7FFF);
                    end
                    3: begin
                        request.sample_i = dpd_sample_t'(16'shFFFF);
                        request.sample_q = dpd_sample_t'(16'sh8000);
                    end
                    default: begin
                    end
                endcase

                lfsr_state = next_lfsr(lfsr_state);
                request.gap_cycles = (
                    maximum_gap_cycles == 0
                ) ? 0 : (
                    lfsr_state % (maximum_gap_cycles + 1)
                );

                request.sample_index = first_sample_index + offset;

                finish_item(request);
            end

            `uvm_info(
                "DPD_STRESS_SEQUENCE",
                $sformatf(
                    "Completed %0d randomized items beginning at index %0d.",
                    sample_count,
                    first_sample_index
                ),
                UVM_LOW
            )
        endtask

    endclass


    class dpd_stress_sequencer extends uvm_sequencer #(dpd_stress_item);

        `uvm_component_utils(dpd_stress_sequencer)

        function new(
            string name = "dpd_stress_sequencer",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

    endclass


    class dpd_stress_driver extends uvm_driver #(dpd_stress_item);

        `uvm_component_utils(dpd_stress_driver)

        virtual dpd_stress_if vif;

        int stress_seed;
        int unsigned ready_lfsr_state;
        int unsigned coefficient_update_count;
        int unsigned reset_pulse_count;
        int unsigned driven_item_count;

        semaphore reset_lock;

        function new(
            string name = "dpd_stress_driver",
            uvm_component parent = null
        );
            super.new(name, parent);

            stress_seed = 13013;
            ready_lfsr_state = 32'h1;
            coefficient_update_count = 0;
            reset_pulse_count = 0;
            driven_item_count = 0;
            reset_lock = new(1);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            if (!uvm_config_db#(
                virtual dpd_stress_if
            )::get(this, "", "vif", vif)) begin
                `uvm_fatal(
                    "DPD_STRESS_NO_VIF",
                    "dpd_stress_driver could not obtain the virtual interface."
                )
            end

            void'(uvm_config_db#(int)::get(
                this,
                "",
                "stress_seed",
                stress_seed
            ));

            ready_lfsr_state = stress_seed;
            if (ready_lfsr_state == 0) begin
                ready_lfsr_state = 32'h1;
            end
        endfunction

        function automatic int unsigned next_lfsr(
            input int unsigned current_value
        );
            int unsigned next_value;
            bit feedback;

            feedback = current_value[31]
                ^ current_value[21]
                ^ current_value[1]
                ^ current_value[0];

            next_value = {
                current_value[30:0],
                feedback
            };

            if (next_value == 0) begin
                next_value = 32'h1;
            end

            return next_value;
        endfunction

        task initialize_signals();
            vif.rst_n = 1'b0;
            vif.in_valid = 1'b0;
            vif.in_i = '0;
            vif.in_q = '0;
            vif.out_ready = 1'b0;
            vif.coefficient_mode = DPD_COEFF_MODE_UNKNOWN;

            for (int unsigned index = 0;
                 index < DPD_NUM_COEFFICIENTS;
                 index++) begin
                vif.coefficient_i[index] = '0;
                vif.coefficient_q[index] = '0;
            end

            repeat (4) @(vif.driver_cb);
            vif.driver_cb.rst_n <= 1'b1;
        endtask

        task drive_output_ready();
            forever begin
                @(vif.driver_cb);

                if (!vif.rst_n) begin
                    vif.driver_cb.out_ready <= 1'b0;
                end
                else begin
                    ready_lfsr_state = next_lfsr(
                        ready_lfsr_state
                    );

                    // Roughly 75 percent ready with naturally varying stalls.
                    vif.driver_cb.out_ready <= (
                        ready_lfsr_state[1:0] != 2'b00
                    );
                end
            end
        endtask

        task drive_input_items();
            dpd_stress_item request;

            wait (vif.rst_n === 1'b1);

            forever begin
                seq_item_port.get_next_item(request);

                repeat (request.gap_cycles) begin
                    @(vif.driver_cb);
                    vif.driver_cb.in_valid <= 1'b0;
                    vif.driver_cb.in_i <= '0;
                    vif.driver_cb.in_q <= '0;
                end

                @(vif.driver_cb);
                vif.driver_cb.in_valid <= 1'b1;
                vif.driver_cb.in_i <= request.sample_i;
                vif.driver_cb.in_q <= request.sample_q;

                do begin
                    @(vif.monitor_cb);
                end
                while (!(
                    vif.monitor_cb.rst_n
                    && vif.monitor_cb.in_valid
                    && vif.monitor_cb.in_ready
                ));

                @(vif.driver_cb);
                vif.driver_cb.in_valid <= 1'b0;
                vif.driver_cb.in_i <= '0;
                vif.driver_cb.in_q <= '0;

                driven_item_count++;
                seq_item_port.item_done();
            end
        endtask

        task pulse_reset(input int unsigned reset_cycles);
            reset_lock.get();

            @(vif.driver_cb);
            vif.driver_cb.rst_n <= 1'b0;
            reset_pulse_count++;

            repeat (reset_cycles) begin
                @(vif.driver_cb);
            end

            vif.driver_cb.rst_n <= 1'b1;
            reset_lock.put();
        endtask

        task set_identity_coefficients();
            @(vif.driver_cb);

            for (int unsigned index = 0;
                 index < DPD_NUM_COEFFICIENTS;
                 index++) begin
                vif.coefficient_i[index] = '0;
                vif.coefficient_q[index] = '0;
            end

            // Q8.16 representation of +1.0 for memory zero, order one.
            vif.coefficient_i[0] = dpd_coefficient_t'(24'sd65536);
            vif.coefficient_mode = DPD_COEFF_MODE_IDENTITY;
            coefficient_update_count++;
        endtask

        task set_zero_coefficients();
            @(vif.driver_cb);

            for (int unsigned index = 0;
                 index < DPD_NUM_COEFFICIENTS;
                 index++) begin
                vif.coefficient_i[index] = '0;
                vif.coefficient_q[index] = '0;
            end

            vif.coefficient_mode = DPD_COEFF_MODE_ZERO;
            coefficient_update_count++;
        endtask

        task run_phase(uvm_phase phase);
            initialize_signals();

            fork
                drive_output_ready();
                drive_input_items();
            join
        endtask

    endclass


    class dpd_expected_item extends uvm_object;

        dpd_sample_t expected_i;
        dpd_sample_t expected_q;
        int unsigned source_index;
        logic [1:0] coefficient_mode;

        `uvm_object_utils(dpd_expected_item)

        function new(string name = "dpd_expected_item");
            super.new(name);
        endfunction

    endclass


    class dpd_stress_scoreboard extends uvm_scoreboard;

        `uvm_component_utils(dpd_stress_scoreboard)

        virtual dpd_stress_if vif;

        dpd_expected_item expected_queue[$];
        uvm_event done_event;

        bit input_done;
        bit previous_rst_n;

        int unsigned accepted_input_count;
        int unsigned checked_output_count;
        int unsigned mismatch_count;
        int unsigned unexpected_output_count;
        int unsigned reset_count;
        int unsigned dropped_expected_count;
        int unsigned identity_input_count;
        int unsigned zero_input_count;
        int unsigned input_idle_cycle_count;
        int unsigned output_stall_cycle_count;
        int unsigned current_output_stall_length;
        int unsigned max_output_stall_length;

        function new(
            string name = "dpd_stress_scoreboard",
            uvm_component parent = null
        );
            super.new(name, parent);

            done_event = new("done_event");
            input_done = 1'b0;
            previous_rst_n = 1'b0;

            accepted_input_count = 0;
            checked_output_count = 0;
            mismatch_count = 0;
            unexpected_output_count = 0;
            reset_count = 0;
            dropped_expected_count = 0;
            identity_input_count = 0;
            zero_input_count = 0;
            input_idle_cycle_count = 0;
            output_stall_cycle_count = 0;
            current_output_stall_length = 0;
            max_output_stall_length = 0;
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            if (!uvm_config_db#(
                virtual dpd_stress_if
            )::get(this, "", "vif", vif)) begin
                `uvm_fatal(
                    "DPD_STRESS_NO_VIF",
                    "dpd_stress_scoreboard could not obtain the virtual interface."
                )
            end
        endfunction

        function void mark_input_done();
            input_done = 1'b1;
            check_done();
        endfunction

        function int unsigned pending_count();
            return expected_queue.size();
        endfunction

        function void check_done();
            if (input_done && expected_queue.size() == 0) begin
                done_event.trigger();
            end
        endfunction

        function void enqueue_prediction();
            dpd_expected_item expected;

            expected = dpd_expected_item::type_id::create(
                $sformatf(
                    "expected_%0d",
                    accepted_input_count
                )
            );

            expected.source_index = accepted_input_count;
            expected.coefficient_mode = vif.monitor_cb.coefficient_mode;

            case (vif.monitor_cb.coefficient_mode)
                DPD_COEFF_MODE_IDENTITY: begin
                    expected.expected_i = vif.monitor_cb.in_i;
                    expected.expected_q = vif.monitor_cb.in_q;
                    identity_input_count++;
                end

                DPD_COEFF_MODE_ZERO: begin
                    expected.expected_i = '0;
                    expected.expected_q = '0;
                    zero_input_count++;
                end

                default: begin
                    `uvm_fatal(
                        "DPD_STRESS_UNKNOWN_COEFFICIENT_MODE",
                        $sformatf(
                            "Input %0d was accepted with coefficient mode %0d.",
                            accepted_input_count,
                            vif.monitor_cb.coefficient_mode
                        )
                    )
                end
            endcase

            expected_queue.push_back(expected);
            accepted_input_count++;
        endfunction

        function void compare_output();
            dpd_expected_item expected;

            if (expected_queue.size() == 0) begin
                unexpected_output_count++;

                `uvm_error(
                    "DPD_STRESS_UNEXPECTED_OUTPUT",
                    $sformatf(
                        "Unexpected output %0d actual=(%0d,%0d).",
                        checked_output_count,
                        $signed(vif.monitor_cb.out_i),
                        $signed(vif.monitor_cb.out_q)
                    )
                )

                return;
            end

            expected = expected_queue.pop_front();

            if (
                (vif.monitor_cb.out_i !== expected.expected_i)
                || (vif.monitor_cb.out_q !== expected.expected_q)
            ) begin
                mismatch_count++;

                `uvm_error(
                    "DPD_STRESS_MISMATCH",
                    $sformatf(
                        "source=%0d mode=%0d actual=(%0d,%0d) expected=(%0d,%0d)",
                        expected.source_index,
                        expected.coefficient_mode,
                        $signed(vif.monitor_cb.out_i),
                        $signed(vif.monitor_cb.out_q),
                        $signed(expected.expected_i),
                        $signed(expected.expected_q)
                    )
                )
            end

            checked_output_count++;
            check_done();
        endfunction

        task run_phase(uvm_phase phase);
            forever begin
                @(vif.monitor_cb);

                if (!vif.monitor_cb.rst_n) begin
                    if (previous_rst_n) begin
                        reset_count++;
                        dropped_expected_count += expected_queue.size();
                        expected_queue.delete();
                        current_output_stall_length = 0;
                    end
                end
                else begin
                    if (!vif.monitor_cb.in_valid) begin
                        input_idle_cycle_count++;
                    end

                    if (
                        vif.monitor_cb.out_valid
                        && !vif.monitor_cb.out_ready
                    ) begin
                        output_stall_cycle_count++;
                        current_output_stall_length++;
                    end
                    else if (current_output_stall_length != 0) begin
                        if (
                            current_output_stall_length
                            > max_output_stall_length
                        ) begin
                            max_output_stall_length =
                                current_output_stall_length;
                        end
                        current_output_stall_length = 0;
                    end

                    // The output represents a previously accepted input, so
                    // consume it before adding a same-cycle new input.
                    if (
                        vif.monitor_cb.out_valid
                        && vif.monitor_cb.out_ready
                    ) begin
                        compare_output();
                    end

                    if (
                        vif.monitor_cb.in_valid
                        && vif.monitor_cb.in_ready
                    ) begin
                        enqueue_prediction();
                    end
                end

                previous_rst_n = vif.monitor_cb.rst_n;
            end
        endtask

        function bit stress_complete();
            return (
                input_done
                && (accepted_input_count == DPD_STRESS_TOTAL_SAMPLE_COUNT)
                && (
                    checked_output_count + dropped_expected_count
                    == accepted_input_count
                )
                && (mismatch_count == 0)
                && (unexpected_output_count == 0)
                && (reset_count >= 1)
                && (dropped_expected_count >= 1)
                && (identity_input_count > 0)
                && (zero_input_count > 0)
                && (input_idle_cycle_count > 0)
                && (output_stall_cycle_count > 0)
                && (max_output_stall_length > 0)
                && (expected_queue.size() == 0)
            );
        endfunction

        function string summary();
            return $sformatf(
                "DPD_STRESS_SUMMARY inputs=%0d outputs=%0d dropped_on_reset=%0d mismatches=%0d unexpected=%0d resets=%0d identity_inputs=%0d zero_inputs=%0d input_idle_cycles=%0d output_stall_cycles=%0d max_output_stall=%0d",
                accepted_input_count,
                checked_output_count,
                dropped_expected_count,
                mismatch_count,
                unexpected_output_count,
                reset_count,
                identity_input_count,
                zero_input_count,
                input_idle_cycle_count,
                output_stall_cycle_count,
                max_output_stall_length
            );
        endfunction

    endclass


    class dpd_stress_agent extends uvm_agent;

        `uvm_component_utils(dpd_stress_agent)

        dpd_stress_sequencer sequencer;
        dpd_stress_driver driver;

        function new(
            string name = "dpd_stress_agent",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            sequencer = dpd_stress_sequencer::type_id::create(
                "sequencer",
                this
            );
            driver = dpd_stress_driver::type_id::create(
                "driver",
                this
            );
        endfunction

        function void connect_phase(uvm_phase phase);
            super.connect_phase(phase);

            driver.seq_item_port.connect(
                sequencer.seq_item_export
            );
        endfunction

    endclass


    class dpd_stress_env extends uvm_env;

        `uvm_component_utils(dpd_stress_env)

        dpd_stress_agent agent;
        dpd_stress_scoreboard scoreboard;

        function new(
            string name = "dpd_stress_env",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            agent = dpd_stress_agent::type_id::create(
                "agent",
                this
            );
            scoreboard = dpd_stress_scoreboard::type_id::create(
                "scoreboard",
                this
            );
        endfunction

    endclass


    class dpd_m13_stress_uvm_test extends uvm_test;

        `uvm_component_utils(dpd_m13_stress_uvm_test)

        virtual dpd_stress_if vif;
        dpd_stress_env env;
        int stress_seed;

        function new(
            string name = "dpd_m13_stress_uvm_test",
            uvm_component parent = null
        );
            super.new(name, parent);
            stress_seed = 13013;
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            if (!uvm_config_db#(
                virtual dpd_stress_if
            )::get(this, "", "vif", vif)) begin
                `uvm_fatal(
                    "DPD_STRESS_NO_VIF",
                    "dpd_m13_stress_uvm_test could not obtain the virtual interface."
                )
            end

            void'(uvm_config_db#(int)::get(
                this,
                "",
                "stress_seed",
                stress_seed
            ));

            env = dpd_stress_env::type_id::create(
                "env",
                this
            );
        endfunction

        task wait_until_scoreboard_empty();
            do begin
                @(vif.monitor_cb);
            end
            while (env.scoreboard.pending_count() != 0);
        endtask

        task wait_for_stalled_output();
            int unsigned timeout_cycles;

            timeout_cycles = 0;

            do begin
                @(vif.monitor_cb);
                timeout_cycles++;

                if (timeout_cycles > 4096) begin
                    `uvm_fatal(
                        "DPD_STRESS_STALL_TIMEOUT",
                        "Could not find a backpressured output for reset interruption."
                    )
                end
            end
            while (!(
                vif.monitor_cb.rst_n
                && vif.monitor_cb.out_valid
                && !vif.monitor_cb.out_ready
            ));
        endtask

        function dpd_stress_sequence make_sequence(
            input string name,
            input int unsigned sample_count,
            input int unsigned first_sample_index,
            input int unsigned sequence_seed
        );
            dpd_stress_sequence created_sequence;

            created_sequence = dpd_stress_sequence::type_id::create(
                name
            );
            created_sequence.sample_count = sample_count;
            created_sequence.first_sample_index = first_sample_index;
            created_sequence.sequence_seed = sequence_seed;
            created_sequence.maximum_gap_cycles = 3;

            return created_sequence;
        endfunction

        task run_phase(uvm_phase phase);
            dpd_stress_sequence identity_sequence;
            dpd_stress_sequence zero_sequence;
            dpd_stress_sequence recovery_sequence;

            phase.raise_objection(this);

            wait (vif.rst_n === 1'b1);

            env.agent.driver.set_identity_coefficients();

            identity_sequence = make_sequence(
                "identity_sequence",
                DPD_STRESS_IDENTITY_SAMPLE_COUNT,
                0,
                stress_seed ^ 32'h1357_9BDF
            );

            fork
                begin
                    identity_sequence.start(
                        env.agent.sequencer
                    );
                end

                begin
                    wait (
                        env.scoreboard.accepted_input_count
                        >= DPD_STRESS_RESET_AFTER_INPUTS
                    );
                    wait_for_stalled_output();
                    env.agent.driver.pulse_reset(
                        DPD_STRESS_RESET_CYCLES
                    );
                end
            join

            wait_until_scoreboard_empty();

            env.agent.driver.set_zero_coefficients();

            zero_sequence = make_sequence(
                "zero_sequence",
                DPD_STRESS_ZERO_SAMPLE_COUNT,
                DPD_STRESS_IDENTITY_SAMPLE_COUNT,
                stress_seed ^ 32'h2468_ACE1
            );
            zero_sequence.start(env.agent.sequencer);

            wait_until_scoreboard_empty();

            env.agent.driver.set_identity_coefficients();

            recovery_sequence = make_sequence(
                "recovery_sequence",
                DPD_STRESS_RECOVERY_SAMPLE_COUNT,
                DPD_STRESS_IDENTITY_SAMPLE_COUNT
                    + DPD_STRESS_ZERO_SAMPLE_COUNT,
                stress_seed ^ 32'h55AA_0F0F
            );
            recovery_sequence.start(env.agent.sequencer);

            wait_until_scoreboard_empty();

            env.scoreboard.mark_input_done();
            env.scoreboard.done_event.wait_on();

            #20ns;

            `uvm_info(
                "DPD_STRESS_RESULTS",
                env.scoreboard.summary(),
                UVM_NONE
            )

            if (env.agent.driver.coefficient_update_count < 3) begin
                `uvm_fatal(
                    "DPD_STRESS_COEFFICIENT_UPDATE_FAILURE",
                    $sformatf(
                        "Expected at least 3 coefficient updates, observed %0d.",
                        env.agent.driver.coefficient_update_count
                    )
                )
            end

            if (env.agent.driver.reset_pulse_count < 1) begin
                `uvm_fatal(
                    "DPD_STRESS_RESET_FAILURE",
                    "The reset interruption was not issued."
                )
            end

            if (!env.scoreboard.stress_complete()) begin
                `uvm_fatal(
                    "DPD_STRESS_FAILURE",
                    env.scoreboard.summary()
                )
            end

            `uvm_info(
                "DPD_STRESS_PASS",
                $sformatf(
                    "DPD_UVM_STRESS_PASS seed=%0d inputs=%0d outputs=%0d dropped=%0d mismatches=%0d coefficient_updates=%0d",
                    stress_seed,
                    env.scoreboard.accepted_input_count,
                    env.scoreboard.checked_output_count,
                    env.scoreboard.dropped_expected_count,
                    env.scoreboard.mismatch_count,
                    env.agent.driver.coefficient_update_count
                ),
                UVM_NONE
            )

            phase.drop_objection(this);
        endtask

    endclass

endpackage

`default_nettype wire

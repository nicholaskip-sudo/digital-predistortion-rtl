'default_nettype none

package dpd_uvm_pkg;

    timeunit 1ns;
    timeprecision 1ps;

    import uvm_pkg::*;
    import dpd_pkg::*;

    'include "uvm_macros.svh"

    localparam int unsigned DPD_UVM_MAX_SAMPLE_COUNT = 36864;

    localparam dpd_sample_t DPD_UVM_OUTPUT_MAX = {
        1'b0,
        {(DPD_OUTPUT_WIDTH-1){1'b1}}
    };

    localparam dpd_sample_t DPD_UVM_OUTPUT_MIN = {
        1'b1,
        {(DPD_OUTPUT_WIDTH-1){1'b0}}
    };


    class dpd_input_item extends uvm_sequence_item;

        logic signed [DPD_SAMPLE_WIDTH-1:0] sample_i;
        logic signed [DPD_SAMPLE_WIDTH-1:0] sample_q;
        int unsigned sample_index;

        'uvm_object_utils(dpd_input_item)

        function new(string name = "dpd_input_item");
            super.new(name);
        endfunction

        function string convert2string();
            return $sformatf(
                "index=%0d sample=(%0d,%0d)",
                sample_index,
                $signed(sample_i),
                $signed(sample_q)
            );
        endfunction

    endclass


    class dpd_output_item extends uvm_sequence_item;

        logic signed [DPD_OUTPUT_WIDTH-1:0] sample_i;
        logic signed [DPD_OUTPUT_WIDTH-1:0] sample_q;
        int unsigned sample_index;

        'uvm_object_utils(dpd_output_item)

        function new(string name = "dpd_output_item");
            super.new(name);
        endfunction

        function string convert2string();
            return $sformatf(
                "index=%0d sample=(%0d,%0d)",
                sample_index,
                $signed(sample_i),
                $signed(sample_q)
            );
        endfunction

    endclass


    class dpd_input_sequence extends uvm_sequence #(dpd_input_item);

        string vector_directory;
        int sample_count;

        dpd_sample_t input_i_memory [0:DPD_UVM_MAX_SAMPLE_COUNT-1];
        dpd_sample_t input_q_memory [0:DPD_UVM_MAX_SAMPLE_COUNT-1];

        'uvm_object_utils(dpd_input_sequence)

        function new(string name = "dpd_input_sequence");
            super.new(name);
            vector_directory = "vectors/rtl/ofdm_short";
            sample_count = 512;
        endfunction

        task body();
            string filename;
            dpd_input_item request;

            if (sample_count <= 0) begin
                'uvm_fatal(
                    "DPD_SEQUENCE_CONFIG",
                    "sample_count must be greater than zero."
                )
            end

            if (sample_count > DPD_UVM_MAX_SAMPLE_COUNT) begin
                'uvm_fatal(
                    "DPD_SEQUENCE_CONFIG",
                    $sformatf(
                        "sample_count=%0d exceeds maximum=%0d.",
                        sample_count,
                        DPD_UVM_MAX_SAMPLE_COUNT
                    )
                )
            end

            filename = $sformatf(
                "%s/input_i.hex",
                vector_directory
            );
            $readmemh(
                filename,
                input_i_memory,
                0,
                sample_count - 1
            );

            filename = $sformatf(
                "%s/input_q.hex",
                vector_directory
            );
            $readmemh(
                filename,
                input_q_memory,
                0,
                sample_count - 1
            );

            for (int unsigned index = 0;
                 index < sample_count;
                 index++) begin

                request = dpd_input_item::type_id::create(
                    $sformatf("request_%0d", index)
                );

                start_item(request);
                request.sample_i = input_i_memory[index];
                request.sample_q = input_q_memory[index];
                request.sample_index = index;
                finish_item(request);
            end

            'uvm_info(
                "DPD_SEQUENCE",
                $sformatf(
                    "Completed %0d input sequence items.",
                    sample_count
                ),
                UVM_LOW
            )
        endtask

    endclass


    class dpd_sequencer extends uvm_sequencer #(dpd_input_item);

        'uvm_component_utils(dpd_sequencer)

        function new(
            string name = "dpd_sequencer",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

    endclass


    class dpd_driver extends uvm_driver #(dpd_input_item);

        'uvm_component_utils(dpd_driver)

        virtual dpd_stream_if vif;

        function new(
            string name = "dpd_driver",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            if (!uvm_config_db#(
                virtual dpd_stream_if
            )::get(this, "", "vif", vif)) begin
                'uvm_fatal(
                    "DPD_NO_VIF",
                    "dpd_driver could not obtain the virtual interface."
                )
            end
        endfunction

        task drive_output_ready();
            int unsigned ready_cycle;

            ready_cycle = 0;
            vif.out_ready = 1'b0;

            forever begin
                @(vif.driver_cb);

                if (!vif.driver_cb.rst_n) begin
                    ready_cycle = 0;
                    vif.driver_cb.out_ready <= 1'b0;
                end
                else begin
                    ready_cycle++;

                    vif.driver_cb.out_ready <= !(
                        ((ready_cycle % 11) == 5)
                        || ((ready_cycle % 17) == 9)
                    );
                end
            end
        endtask

        task drive_input_items();
            dpd_input_item request;

            vif.in_valid = 1'b0;
            vif.in_i = '0;
            vif.in_q = '0;

            wait (vif.rst_n === 1'b1);

            forever begin
                seq_item_port.get_next_item(request);

                // Drive at the falling edge so data is stable before the DUT
                // evaluates the ready/valid transfer at the next rising edge.
                @(vif.driver_cb);
                vif.driver_cb.in_valid <= 1'b1;
                vif.driver_cb.in_i <= request.sample_i;
                vif.driver_cb.in_q <= request.sample_q;

                // Retire the item only after the actual posedge handshake.
                do begin
                    @(vif.monitor_cb);
                end
                while (!(
                    vif.monitor_cb.rst_n
                    && vif.monitor_cb.in_valid
                    && vif.monitor_cb.in_ready
                ));

                // Remove valid before another rising edge can accept this item.
                @(vif.driver_cb);
                vif.driver_cb.in_valid <= 1'b0;
                vif.driver_cb.in_i <= '0;
                vif.driver_cb.in_q <= '0;

                seq_item_port.item_done();
            end
        endtask

        task run_phase(uvm_phase phase);
            fork
                drive_output_ready();
                drive_input_items();
            join
        endtask

    endclass


    class dpd_output_monitor extends uvm_monitor;

        'uvm_component_utils(dpd_output_monitor)

        virtual dpd_stream_if vif;
        uvm_analysis_port #(dpd_output_item) analysis_port;

        int unsigned output_index;

        function new(
            string name = "dpd_output_monitor",
            uvm_component parent = null
        );
            super.new(name, parent);
            analysis_port = new("analysis_port", this);
            output_index = 0;
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            if (!uvm_config_db#(
                virtual dpd_stream_if
            )::get(this, "", "vif", vif)) begin
                'uvm_fatal(
                    "DPD_NO_VIF",
                    "dpd_output_monitor could not obtain the virtual interface."
                )
            end
        endfunction

        task run_phase(uvm_phase phase);
            dpd_output_item item;

            forever begin
                @(vif.monitor_cb);

                if (
                    vif.monitor_cb.rst_n
                    && vif.monitor_cb.out_valid
                    && vif.monitor_cb.out_ready
                ) begin
                    item = dpd_output_item::type_id::create(
                        $sformatf("output_%0d", output_index),
                        this
                    );

                    item.sample_i = vif.monitor_cb.out_i;
                    item.sample_q = vif.monitor_cb.out_q;
                    item.sample_index = output_index;

                    analysis_port.write(item);
                    output_index++;
                end
            end
        endtask

    endclass


    class dpd_agent extends uvm_agent;

        'uvm_component_utils(dpd_agent)

        dpd_sequencer sequencer;
        dpd_driver driver;
        dpd_output_monitor monitor;

        function new(
            string name = "dpd_agent",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            sequencer = dpd_sequencer::type_id::create(
                "sequencer",
                this
            );
            driver = dpd_driver::type_id::create(
                "driver",
                this
            );
            monitor = dpd_output_monitor::type_id::create(
                "monitor",
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


    class dpd_scoreboard extends uvm_scoreboard;

        'uvm_component_utils(dpd_scoreboard)

        uvm_analysis_imp #(
            dpd_output_item,
            dpd_scoreboard
        ) analysis_export;

        string vector_directory;
        int sample_count;

        dpd_sample_t expected_i_memory [0:DPD_UVM_MAX_SAMPLE_COUNT-1];
        dpd_sample_t expected_q_memory [0:DPD_UVM_MAX_SAMPLE_COUNT-1];

        int unsigned actual_count;
        int unsigned mismatch_count;

        uvm_event done_event;

        function new(
            string name = "dpd_scoreboard",
            uvm_component parent = null
        );
            super.new(name, parent);

            analysis_export = new("analysis_export", this);
            done_event = new("done_event");

            actual_count = 0;
            mismatch_count = 0;
        endfunction

        function void build_phase(uvm_phase phase);
            string filename;

            super.build_phase(phase);

            if (!uvm_config_db#(string)::get(
                this,
                "",
                "vector_directory",
                vector_directory
            )) begin
                'uvm_fatal(
                    "DPD_SCOREBOARD_CONFIG",
                    "Missing vector_directory configuration."
                )
            end

            if (!uvm_config_db#(int)::get(
                this,
                "",
                "sample_count",
                sample_count
            )) begin
                'uvm_fatal(
                    "DPD_SCOREBOARD_CONFIG",
                    "Missing sample_count configuration."
                )
            end

            if (
                sample_count <= 0
                || sample_count > DPD_UVM_MAX_SAMPLE_COUNT
            ) begin
                'uvm_fatal(
                    "DPD_SCOREBOARD_CONFIG",
                    $sformatf(
                        "Invalid sample_count=%0d.",
                        sample_count
                    )
                )
            end

            filename = $sformatf(
                "%s/expected_i.hex",
                vector_directory
            );
            $readmemh(
                filename,
                expected_i_memory,
                0,
                sample_count - 1
            );

            filename = $sformatf(
                "%s/expected_q.hex",
                vector_directory
            );
            $readmemh(
                filename,
                expected_q_memory,
                0,
                sample_count - 1
            );
        endfunction

        function void write(dpd_output_item item);
            if (actual_count >= sample_count) begin
                'uvm_fatal(
                    "DPD_EXTRA_OUTPUT",
                    $sformatf(
                        "Received unexpected output index %0d.",
                        actual_count
                    )
                )
            end

            if (
                (item.sample_i !== expected_i_memory[actual_count])
                || (item.sample_q !== expected_q_memory[actual_count])
            ) begin
                mismatch_count++;

                'uvm_error(
                    "DPD_MISMATCH",
                    $sformatf(
                        "sample=%0d actual=(%0d,%0d) expected=(%0d,%0d)",
                        actual_count,
                        $signed(item.sample_i),
                        $signed(item.sample_q),
                        $signed(expected_i_memory[actual_count]),
                        $signed(expected_q_memory[actual_count])
                    )
                )
            end

            actual_count++;

            if (actual_count == sample_count) begin
                'uvm_info(
                    "DPD_SCOREBOARD",
                    $sformatf(
                        "Compared %0d outputs with %0d mismatches.",
                        actual_count,
                        mismatch_count
                    ),
                    UVM_LOW
                )

                done_event.trigger();
            end
        endfunction

    endclass


    class dpd_functional_coverage extends uvm_component;

        'uvm_component_utils(dpd_functional_coverage)

        virtual dpd_stream_if vif;
        int sample_count;

        bit input_transfer_sample;
        bit output_transfer_sample;

        int unsigned input_quadrant;
        int unsigned output_quadrant;
        int unsigned input_magnitude_class;
        int unsigned output_magnitude_class;
        int unsigned input_state;
        int unsigned output_state;
        int unsigned output_ready_state;
        int unsigned output_saturation_state;
        int unsigned completed_output_stall_length;

        int unsigned accepted_input_count;
        int unsigned accepted_output_count;
        int unsigned saturated_output_count;
        int unsigned current_output_stall_length;
        int unsigned max_output_stall_length;

        int unsigned input_quadrant_hits [0:3];
        int unsigned output_quadrant_hits [0:3];
        int unsigned input_magnitude_hits [0:3];
        int unsigned output_magnitude_hits [0:3];
        int unsigned input_state_hits [0:2];
        int unsigned output_state_hits [0:2];
        int unsigned ready_state_hits [0:1];
        int unsigned saturation_state_hits [0:1];

        covergroup stream_coverage_group;
            option.per_instance = 1;

            cp_input_quadrant: coverpoint input_quadrant
                iff (input_transfer_sample) {
                bins i_pos_q_pos = {0};
                bins i_pos_q_neg = {1};
                bins i_neg_q_pos = {2};
                bins i_neg_q_neg = {3};
            }

            cp_output_quadrant: coverpoint output_quadrant
                iff (output_transfer_sample) {
                bins i_pos_q_pos = {0};
                bins i_pos_q_neg = {1};
                bins i_neg_q_pos = {2};
                bins i_neg_q_neg = {3};
            }

            cp_input_magnitude: coverpoint input_magnitude_class
                iff (input_transfer_sample) {
                bins low = {0};
                bins mid_range = {1};
                bins high = {2};
                bins peak = {3};
            }

            cp_output_magnitude: coverpoint output_magnitude_class
                iff (output_transfer_sample) {
                bins low = {0};
                bins mid_range = {1};
                bins high = {2};
                bins peak = {3};
            }

            cp_input_state: coverpoint input_state {
                bins idle = {0};
                bins stalled = {1};
                bins transferred = {2};
            }

            cp_output_state: coverpoint output_state {
                bins idle = {0};
                bins stalled = {1};
                bins transferred = {2};
            }

            cp_output_ready: coverpoint output_ready_state {
                bins backpressured = {0};
                bins ready = {1};
            }

            cp_output_saturation: coverpoint output_saturation_state
                iff (output_transfer_sample) {
                bins not_saturated = {0};
                bins saturated = {1};
            }

            input_quadrant_x_magnitude: cross
                cp_input_quadrant,
                cp_input_magnitude;

            output_quadrant_x_magnitude: cross
                cp_output_quadrant,
                cp_output_magnitude;

            protocol_state_cross: cross
                cp_input_state,
                cp_output_state;
        endgroup

        covergroup stall_coverage_group;
            option.per_instance = 1;

            cp_output_stall_length:
                coverpoint completed_output_stall_length {
                    bins one_cycle = {1};
                    bins two_cycles = {2};
                    bins three_to_four_cycles = {[3:4]};
                    bins five_or_more_cycles = {[5:1024]};
                }
        endgroup

        function new(
            string name = "dpd_functional_coverage",
            uvm_component parent = null
        );
            super.new(name, parent);

            stream_coverage_group = new();
            stall_coverage_group = new();

            input_transfer_sample = 1'b0;
            output_transfer_sample = 1'b0;

            input_quadrant = 0;
            output_quadrant = 0;
            input_magnitude_class = 0;
            output_magnitude_class = 0;
            input_state = 0;
            output_state = 0;
            output_ready_state = 0;
            output_saturation_state = 0;
            completed_output_stall_length = 0;

            accepted_input_count = 0;
            accepted_output_count = 0;
            saturated_output_count = 0;
            current_output_stall_length = 0;
            max_output_stall_length = 0;

            for (int unsigned index = 0; index < 4; index++) begin
                input_quadrant_hits[index] = 0;
                output_quadrant_hits[index] = 0;
                input_magnitude_hits[index] = 0;
                output_magnitude_hits[index] = 0;
            end

            for (int unsigned index = 0; index < 3; index++) begin
                input_state_hits[index] = 0;
                output_state_hits[index] = 0;
            end

            for (int unsigned index = 0; index < 2; index++) begin
                ready_state_hits[index] = 0;
                saturation_state_hits[index] = 0;
            end
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            if (!uvm_config_db#(
                virtual dpd_stream_if
            )::get(this, "", "vif", vif)) begin
                'uvm_fatal(
                    "DPD_NO_VIF",
                    "dpd_functional_coverage could not obtain the virtual interface."
                )
            end

            if (!uvm_config_db#(int)::get(
                this,
                "",
                "sample_count",
                sample_count
            )) begin
                'uvm_fatal(
                    "DPD_COVERAGE_CONFIG",
                    "Missing sample_count configuration."
                )
            end
        endfunction

        function automatic int unsigned absolute_sample(
            input dpd_sample_t value
        );
            int signed extended_value;

            extended_value = $signed(value);

            if (extended_value < 0) begin
                return -extended_value;
            end

            return extended_value;
        endfunction

        function automatic int unsigned classify_quadrant(
            input dpd_sample_t sample_i,
            input dpd_sample_t sample_q
        );
            int unsigned classification;

            classification = 0;

            if ($signed(sample_i) < 0) begin
                classification |= 2;
            end

            if ($signed(sample_q) < 0) begin
                classification |= 1;
            end

            return classification;
        endfunction

        function automatic int unsigned classify_magnitude(
            input dpd_sample_t sample_i,
            input dpd_sample_t sample_q
        );
            int unsigned magnitude_i;
            int unsigned magnitude_q;
            int unsigned maximum_magnitude;

            magnitude_i = absolute_sample(sample_i);
            magnitude_q = absolute_sample(sample_q);
            maximum_magnitude = (
                magnitude_i > magnitude_q
            ) ? magnitude_i : magnitude_q;

            if (maximum_magnitude <= 2047) begin
                return 0;
            end

            if (maximum_magnitude <= 8191) begin
                return 1;
            end

            if (maximum_magnitude <= 16383) begin
                return 2;
            end

            return 3;
        endfunction

        function automatic bit is_output_saturated(
            input dpd_sample_t sample_i,
            input dpd_sample_t sample_q
        );
            return (
                (sample_i == DPD_UVM_OUTPUT_MAX)
                || (sample_i == DPD_UVM_OUTPUT_MIN)
                || (sample_q == DPD_UVM_OUTPUT_MAX)
                || (sample_q == DPD_UVM_OUTPUT_MIN)
            );
        endfunction

        task run_phase(uvm_phase phase);
            forever begin
                @(vif.monitor_cb);

                if (!vif.monitor_cb.rst_n) begin
                    current_output_stall_length = 0;
                end
                else begin
                    input_transfer_sample = (
                        vif.monitor_cb.in_valid
                        && vif.monitor_cb.in_ready
                    );

                    output_transfer_sample = (
                        vif.monitor_cb.out_valid
                        && vif.monitor_cb.out_ready
                    );

                    if (!vif.monitor_cb.in_valid) begin
                        input_state = 0;
                    end
                    else if (!vif.monitor_cb.in_ready) begin
                        input_state = 1;
                    end
                    else begin
                        input_state = 2;
                    end

                    if (!vif.monitor_cb.out_valid) begin
                        output_state = 0;
                    end
                    else if (!vif.monitor_cb.out_ready) begin
                        output_state = 1;
                    end
                    else begin
                        output_state = 2;
                    end

                    output_ready_state = vif.monitor_cb.out_ready;

                    input_state_hits[input_state]++;
                    output_state_hits[output_state]++;
                    ready_state_hits[output_ready_state]++;

                    if (input_transfer_sample) begin
                        input_quadrant = classify_quadrant(
                            vif.monitor_cb.in_i,
                            vif.monitor_cb.in_q
                        );
                        input_magnitude_class = classify_magnitude(
                            vif.monitor_cb.in_i,
                            vif.monitor_cb.in_q
                        );

                        input_quadrant_hits[input_quadrant]++;
                        input_magnitude_hits[input_magnitude_class]++;
                        accepted_input_count++;
                    end

                    if (output_transfer_sample) begin
                        output_quadrant = classify_quadrant(
                            vif.monitor_cb.out_i,
                            vif.monitor_cb.out_q
                        );
                        output_magnitude_class = classify_magnitude(
                            vif.monitor_cb.out_i,
                            vif.monitor_cb.out_q
                        );
                        output_saturation_state = is_output_saturated(
                            vif.monitor_cb.out_i,
                            vif.monitor_cb.out_q
                        );

                        output_quadrant_hits[output_quadrant]++;
                        output_magnitude_hits[output_magnitude_class]++;
                        saturation_state_hits[output_saturation_state]++;

                        if (output_saturation_state) begin
                            saturated_output_count++;
                        end

                        accepted_output_count++;
                    end

                    if (
                        vif.monitor_cb.out_valid
                        && !vif.monitor_cb.out_ready
                    ) begin
                        current_output_stall_length++;
                    end
                    else if (current_output_stall_length != 0) begin
                        completed_output_stall_length =
                            current_output_stall_length;

                        stall_coverage_group.sample();

                        if (
                            current_output_stall_length
                            > max_output_stall_length
                        ) begin
                            max_output_stall_length =
                                current_output_stall_length;
                        end

                        current_output_stall_length = 0;
                    end

                    stream_coverage_group.sample();
                end
            end
        endtask

        function automatic int unsigned populated_input_quadrants();
            int unsigned count;
            count = 0;

            for (int unsigned index = 0; index < 4; index++) begin
                if (input_quadrant_hits[index] != 0) begin
                    count++;
                end
            end

            return count;
        endfunction

        function automatic int unsigned populated_output_quadrants();
            int unsigned count;
            count = 0;

            for (int unsigned index = 0; index < 4; index++) begin
                if (output_quadrant_hits[index] != 0) begin
                    count++;
                end
            end

            return count;
        endfunction

        function automatic int unsigned populated_input_magnitudes();
            int unsigned count;
            count = 0;

            for (int unsigned index = 0; index < 4; index++) begin
                if (input_magnitude_hits[index] != 0) begin
                    count++;
                end
            end

            return count;
        endfunction

        function automatic int unsigned populated_output_magnitudes();
            int unsigned count;
            count = 0;

            for (int unsigned index = 0; index < 4; index++) begin
                if (output_magnitude_hits[index] != 0) begin
                    count++;
                end
            end

            return count;
        endfunction

        function automatic int unsigned populated_protocol_states();
            int unsigned count;
            count = 0;

            for (int unsigned index = 0; index < 3; index++) begin
                if (input_state_hits[index] != 0) begin
                    count++;
                end

                if (output_state_hits[index] != 0) begin
                    count++;
                end
            end

            return count;
        endfunction

        function automatic int unsigned populated_ready_states();
            int unsigned count;
            count = 0;

            for (int unsigned index = 0; index < 2; index++) begin
                if (ready_state_hits[index] != 0) begin
                    count++;
                end
            end

            return count;
        endfunction

        function automatic int unsigned populated_saturation_states();
            int unsigned count;
            count = 0;

            for (int unsigned index = 0; index < 2; index++) begin
                if (saturation_state_hits[index] != 0) begin
                    count++;
                end
            end

            return count;
        endfunction

        function automatic bit mandatory_coverage_complete();
            return (
                (accepted_input_count == sample_count)
                && (accepted_output_count == sample_count)
                && (populated_input_quadrants() == 4)
                && (populated_output_quadrants() == 4)
                && (populated_input_magnitudes() == 4)
                && (populated_output_magnitudes() == 4)
                && (populated_protocol_states() == 6)
                && (populated_ready_states() == 2)
                && (populated_saturation_states() == 2)
                && (max_output_stall_length > 0)
            );
        endfunction

        function real stream_coverage_percent();
            return stream_coverage_group.get_inst_coverage();
        endfunction

        function real stall_coverage_percent();
            return stall_coverage_group.get_inst_coverage();
        endfunction

        function string coverage_summary();
            return $sformatf(
                "DPD_COVERAGE_SUMMARY stream=%0.2f stall=%0.2f input_transfers=%0d output_transfers=%0d saturated_outputs=%0d max_output_stall=%0d",
                stream_coverage_percent(),
                stall_coverage_percent(),
                accepted_input_count,
                accepted_output_count,
                saturated_output_count,
                max_output_stall_length
            );
        endfunction

        function string mandatory_coverage_summary();
            return $sformatf(
                "input_quadrants=%0d/4 output_quadrants=%0d/4 input_magnitude=%0d/4 output_magnitude=%0d/4 protocol_states=%0d/6 ready_states=%0d/2 saturation_states=%0d/2",
                populated_input_quadrants(),
                populated_output_quadrants(),
                populated_input_magnitudes(),
                populated_output_magnitudes(),
                populated_protocol_states(),
                populated_ready_states(),
                populated_saturation_states()
            );
        endfunction

    endclass


    class dpd_env extends uvm_env;

        'uvm_component_utils(dpd_env)

        dpd_agent agent;
        dpd_scoreboard scoreboard;
        dpd_functional_coverage coverage;

        function new(
            string name = "dpd_env",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            agent = dpd_agent::type_id::create(
                "agent",
                this
            );
            scoreboard = dpd_scoreboard::type_id::create(
                "scoreboard",
                this
            );
            coverage = dpd_functional_coverage::type_id::create(
                "coverage",
                this
            );
        endfunction

        function void connect_phase(uvm_phase phase);
            super.connect_phase(phase);

            agent.monitor.analysis_port.connect(
                scoreboard.analysis_export
            );
        endfunction

    endclass


    class dpd_base_uvm_test extends uvm_test;

        'uvm_component_utils(dpd_base_uvm_test)

        dpd_env env;

        string vector_directory;
        int sample_count;

        function new(
            string name = "dpd_base_uvm_test",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        virtual function string default_vector_directory();
            return "vectors/rtl/ofdm_short";
        endfunction

        virtual function int default_sample_count();
            return 512;
        endfunction

        virtual function string pass_marker();
            return "DPD_UVM_BASE_PASS";
        endfunction

        virtual function bit require_mandatory_coverage();
            return 1'b0;
        endfunction

        function void build_phase(uvm_phase phase);
            super.build_phase(phase);

            if (!uvm_config_db#(string)::get(
                this,
                "",
                "vector_directory",
                vector_directory
            )) begin
                vector_directory = default_vector_directory();
            end

            if (!uvm_config_db#(int)::get(
                this,
                "",
                "sample_count",
                sample_count
            )) begin
                sample_count = default_sample_count();
            end

            env = dpd_env::type_id::create(
                "env",
                this
            );
        endfunction

        task run_phase(uvm_phase phase);
            dpd_input_sequence input_sequence;

            phase.raise_objection(this);

            input_sequence = dpd_input_sequence::type_id::create(
                "input_sequence"
            );
            input_sequence.vector_directory = vector_directory;
            input_sequence.sample_count = sample_count;

            input_sequence.start(env.agent.sequencer);

            env.scoreboard.done_event.wait_on();

            #20ns;

            if (env.scoreboard.mismatch_count != 0) begin
                'uvm_fatal(
                    "DPD_UVM_FAILURE",
                    $sformatf(
                        "DPD UVM test completed with %0d mismatches.",
                        env.scoreboard.mismatch_count
                    )
                )
            end

            'uvm_info(
                "DPD_COVERAGE",
                env.coverage.coverage_summary(),
                UVM_NONE
            )

            if (require_mandatory_coverage()) begin
                if (!env.coverage.mandatory_coverage_complete()) begin
                    'uvm_fatal(
                        "DPD_COVERAGE_FAILURE",
                        $sformatf(
                            "Mandatory functional coverage is incomplete: %s",
                            env.coverage.mandatory_coverage_summary()
                        )
                    )
                end

                'uvm_info(
                    "DPD_COVERAGE_PASS",
                    $sformatf(
                        "DPD_FUNCTIONAL_COVERAGE_PASS %s",
                        env.coverage.mandatory_coverage_summary()
                    ),
                    UVM_NONE
                )
            end

            'uvm_info(
                "DPD_UVM_PASS",
                $sformatf(
                    "%s samples=%0d mismatches=%0d",
                    pass_marker(),
                    env.scoreboard.actual_count,
                    env.scoreboard.mismatch_count
                ),
                UVM_NONE
            )

            phase.drop_objection(this);
        endtask

    endclass


    class dpd_short_uvm_test extends dpd_base_uvm_test;

        'uvm_component_utils(dpd_short_uvm_test)

        function new(
            string name = "dpd_short_uvm_test",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        virtual function string pass_marker();
            return "DPD_UVM_SHORT_PASS";
        endfunction

    endclass


    class dpd_full_uvm_test extends dpd_base_uvm_test;

        'uvm_component_utils(dpd_full_uvm_test)

        function new(
            string name = "dpd_full_uvm_test",
            uvm_component parent = null
        );
            super.new(name, parent);
        endfunction

        virtual function string default_vector_directory();
            return "vectors/rtl/ofdm_nominal";
        endfunction

        virtual function int default_sample_count();
            return 36864;
        endfunction

        virtual function string pass_marker();
            return "DPD_UVM_FULL_PASS";
        endfunction

        virtual function bit require_mandatory_coverage();
            return 1'b1;
        endfunction

    endclass

endpackage

'default_nettype wire

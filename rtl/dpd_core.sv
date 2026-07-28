'default_nettype none

module dpd_core (
    input  wire clk,
    input  wire rst_n,

    input  wire in_valid,
    output wire in_ready,
    input  wire signed [dpd_pkg::DPD_SAMPLE_WIDTH-1:0] in_i,
    input  wire signed [dpd_pkg::DPD_SAMPLE_WIDTH-1:0] in_q,

    output logic out_valid,
    input  wire out_ready,
    output logic signed [dpd_pkg::DPD_OUTPUT_WIDTH-1:0] out_i,
    output logic signed [dpd_pkg::DPD_OUTPUT_WIDTH-1:0] out_q,

    input  wire signed [dpd_pkg::DPD_COEFFICIENT_WIDTH-1:0]
        coefficient_i [0:dpd_pkg::DPD_NUM_COEFFICIENTS-1],
    input  wire signed [dpd_pkg::DPD_COEFFICIENT_WIDTH-1:0]
        coefficient_q [0:dpd_pkg::DPD_NUM_COEFFICIENTS-1]
);

    timeunit 1ns;
    timeprecision 1ps;

    import dpd_pkg::*;

    dpd_sample_t delay_i [0:DPD_MEMORY_DEPTH-2];
    dpd_sample_t delay_q [0:DPD_MEMORY_DEPTH-2];

    wire signed [DPD_SAMPLE_WIDTH-1:0]
        selected_i [0:DPD_MEMORY_DEPTH-1];
    wire signed [DPD_SAMPLE_WIDTH-1:0]
        selected_q [0:DPD_MEMORY_DEPTH-1];

    wire [DPD_MAG_SQ_WIDTH-1:0]
        magnitude_squared [0:DPD_MEMORY_DEPTH-1];
    wire [DPD_MAG_FOURTH_WIDTH-1:0]
        magnitude_fourth [0:DPD_MEMORY_DEPTH-1];

    wire signed [DPD_BASIS_WIDTH-1:0]
        basis_i [0:DPD_NUM_COEFFICIENTS-1];
    wire signed [DPD_BASIS_WIDTH-1:0]
        basis_q [0:DPD_NUM_COEFFICIENTS-1];

    wire signed [DPD_COMPLEX_TERM_WIDTH-1:0]
        term_i [0:DPD_NUM_COEFFICIENTS-1];
    wire signed [DPD_COMPLEX_TERM_WIDTH-1:0]
        term_q [0:DPD_NUM_COEFFICIENTS-1];

    wire signed [DPD_ACCUMULATOR_WIDTH-1:0] accumulator_i_comb;
    wire signed [DPD_ACCUMULATOR_WIDTH-1:0] accumulator_q_comb;

    wire signed [DPD_ROUND_WORK_WIDTH-1:0] accumulator_work_i;
    wire signed [DPD_ROUND_WORK_WIDTH-1:0] accumulator_work_q;

    wire signed [DPD_OUTPUT_WIDTH-1:0] result_i_comb;
    wire signed [DPD_OUTPUT_WIDTH-1:0] result_q_comb;

    function automatic logic [DPD_MAG_SQ_WIDTH-1:0]
        calculate_magnitude_squared(
            input dpd_sample_t sample_i,
            input dpd_sample_t sample_q
        );

        logic signed [31:0] sample_i_extended;
        logic signed [31:0] sample_q_extended;
        logic signed [31:0] square_i_value;
        logic signed [31:0] square_q_value;
        logic [32:0] sum_value;

        begin
            sample_i_extended = {
                {(32-DPD_SAMPLE_WIDTH){
                    sample_i[DPD_SAMPLE_WIDTH-1]
                }},
                sample_i
            };

            sample_q_extended = {
                {(32-DPD_SAMPLE_WIDTH){
                    sample_q[DPD_SAMPLE_WIDTH-1]
                }},
                sample_q
            };

            square_i_value =
                sample_i_extended * sample_i_extended;
            square_q_value =
                sample_q_extended * sample_q_extended;

            sum_value =
                {1'b0, square_i_value}
                + {1'b0, square_q_value};

            calculate_magnitude_squared =
                sum_value[DPD_MAG_SQ_WIDTH-1:0];
        end
    endfunction

    function automatic logic [DPD_MAG_FOURTH_WIDTH-1:0]
        calculate_magnitude_fourth(
            input logic [DPD_MAG_SQ_WIDTH-1:0] magnitude_squared_value
        );

        logic [63:0] magnitude_squared_extended;

        begin
            magnitude_squared_extended = {
                32'b0,
                magnitude_squared_value
            };

            calculate_magnitude_fourth =
                magnitude_squared_extended
                * magnitude_squared_extended;
        end
    endfunction

    function automatic dpd_basis_t calculate_basis_component(
        input dpd_sample_t sample,
        input logic [DPD_MAG_SQ_WIDTH-1:0]
            magnitude_squared_value,
        input logic [DPD_MAG_FOURTH_WIDTH-1:0]
            magnitude_fourth_value,
        input int unsigned order_slot
    );

        dpd_round_work_t sample_work;
        dpd_round_work_t magnitude_work;
        dpd_round_work_t raw_value;
        dpd_round_work_t rounded_value;

        begin
            sample_work = {
                {(DPD_ROUND_WORK_WIDTH-DPD_SAMPLE_WIDTH){
                    sample[DPD_SAMPLE_WIDTH-1]
                }},
                sample
            };

            magnitude_work = '0;
            raw_value = '0;
            rounded_value = '0;

            case (order_slot)
                0: begin
                    rounded_value =
                        sample_work
                        <<< DPD_ORDER1_BASIS_LEFT_SHIFT;
                end

                1: begin
                    magnitude_work[DPD_MAG_SQ_WIDTH-1:0] =
                        magnitude_squared_value;

                    raw_value = sample_work * magnitude_work;

                    rounded_value = dpd_round_shift_away(
                        raw_value,
                        DPD_ORDER3_BASIS_RIGHT_SHIFT
                    );
                end

                2: begin
                    magnitude_work[DPD_MAG_FOURTH_WIDTH-1:0] =
                        magnitude_fourth_value;

                    raw_value = sample_work * magnitude_work;

                    rounded_value = dpd_round_shift_away(
                        raw_value,
                        DPD_ORDER5_BASIS_RIGHT_SHIFT
                    );
                end

                default: begin
                    rounded_value = '0;
                end
            endcase

            calculate_basis_component =
                dpd_saturate_basis(rounded_value);
        end
    endfunction

    function automatic dpd_complex_term_t calculate_term_i(
        input dpd_basis_t basis_i_value,
        input dpd_basis_t basis_q_value,
        input dpd_coefficient_t coefficient_i_value,
        input dpd_coefficient_t coefficient_q_value
    );

        logic signed [47:0] basis_i_extended;
        logic signed [47:0] basis_q_extended;
        logic signed [47:0] coefficient_i_extended;
        logic signed [47:0] coefficient_q_extended;
        dpd_real_product_t product_rr_value;
        dpd_real_product_t product_ii_value;

        begin
            basis_i_extended = {
                {(48-DPD_BASIS_WIDTH){
                    basis_i_value[DPD_BASIS_WIDTH-1]
                }},
                basis_i_value
            };

            basis_q_extended = {
                {(48-DPD_BASIS_WIDTH){
                    basis_q_value[DPD_BASIS_WIDTH-1]
                }},
                basis_q_value
            };

            coefficient_i_extended = {
                {(48-DPD_COEFFICIENT_WIDTH){
                    coefficient_i_value[DPD_COEFFICIENT_WIDTH-1]
                }},
                coefficient_i_value
            };

            coefficient_q_extended = {
                {(48-DPD_COEFFICIENT_WIDTH){
                    coefficient_q_value[DPD_COEFFICIENT_WIDTH-1]
                }},
                coefficient_q_value
            };

            product_rr_value =
                basis_i_extended * coefficient_i_extended;
            product_ii_value =
                basis_q_extended * coefficient_q_extended;

            calculate_term_i =
                $signed({
                    product_rr_value[DPD_REAL_PRODUCT_WIDTH-1],
                    product_rr_value
                })
                - $signed({
                    product_ii_value[DPD_REAL_PRODUCT_WIDTH-1],
                    product_ii_value
                });
        end
    endfunction

    function automatic dpd_complex_term_t calculate_term_q(
        input dpd_basis_t basis_i_value,
        input dpd_basis_t basis_q_value,
        input dpd_coefficient_t coefficient_i_value,
        input dpd_coefficient_t coefficient_q_value
    );

        logic signed [47:0] basis_i_extended;
        logic signed [47:0] basis_q_extended;
        logic signed [47:0] coefficient_i_extended;
        logic signed [47:0] coefficient_q_extended;
        dpd_real_product_t product_ri_value;
        dpd_real_product_t product_ir_value;

        begin
            basis_i_extended = {
                {(48-DPD_BASIS_WIDTH){
                    basis_i_value[DPD_BASIS_WIDTH-1]
                }},
                basis_i_value
            };

            basis_q_extended = {
                {(48-DPD_BASIS_WIDTH){
                    basis_q_value[DPD_BASIS_WIDTH-1]
                }},
                basis_q_value
            };

            coefficient_i_extended = {
                {(48-DPD_COEFFICIENT_WIDTH){
                    coefficient_i_value[DPD_COEFFICIENT_WIDTH-1]
                }},
                coefficient_i_value
            };

            coefficient_q_extended = {
                {(48-DPD_COEFFICIENT_WIDTH){
                    coefficient_q_value[DPD_COEFFICIENT_WIDTH-1]
                }},
                coefficient_q_value
            };

            product_ri_value =
                basis_i_extended * coefficient_q_extended;
            product_ir_value =
                basis_q_extended * coefficient_i_extended;

            calculate_term_q =
                $signed({
                    product_ri_value[DPD_REAL_PRODUCT_WIDTH-1],
                    product_ri_value
                })
                + $signed({
                    product_ir_value[DPD_REAL_PRODUCT_WIDTH-1],
                    product_ir_value
                });
        end
    endfunction

    function automatic dpd_accumulator_t extend_complex_term(
        input dpd_complex_term_t value
    );
        begin
            extend_complex_term = {
                {(DPD_ACCUMULATOR_WIDTH-DPD_COMPLEX_TERM_WIDTH){
                    value[DPD_COMPLEX_TERM_WIDTH-1]
                }},
                value
            };
        end
    endfunction

    assign selected_i[0] = in_i;
    assign selected_q[0] = in_q;

    assign selected_i[1] = delay_i[0];
    assign selected_q[1] = delay_q[0];

    assign selected_i[2] = delay_i[1];
    assign selected_q[2] = delay_q[1];

    assign magnitude_squared[0] =
        calculate_magnitude_squared(selected_i[0], selected_q[0]);
    assign magnitude_squared[1] =
        calculate_magnitude_squared(selected_i[1], selected_q[1]);
    assign magnitude_squared[2] =
        calculate_magnitude_squared(selected_i[2], selected_q[2]);

    assign magnitude_fourth[0] =
        calculate_magnitude_fourth(magnitude_squared[0]);
    assign magnitude_fourth[1] =
        calculate_magnitude_fourth(magnitude_squared[1]);
    assign magnitude_fourth[2] =
        calculate_magnitude_fourth(magnitude_squared[2]);

    assign basis_i[0] = calculate_basis_component(
        selected_i[0],
        magnitude_squared[0],
        magnitude_fourth[0],
        0
    );
    assign basis_i[1] = calculate_basis_component(
        selected_i[0],
        magnitude_squared[0],
        magnitude_fourth[0],
        1
    );
    assign basis_i[2] = calculate_basis_component(
        selected_i[0],
        magnitude_squared[0],
        magnitude_fourth[0],
        2
    );

    assign basis_i[3] = calculate_basis_component(
        selected_i[1],
        magnitude_squared[1],
        magnitude_fourth[1],
        0
    );
    assign basis_i[4] = calculate_basis_component(
        selected_i[1],
        magnitude_squared[1],
        magnitude_fourth[1],
        1
    );
    assign basis_i[5] = calculate_basis_component(
        selected_i[1],
        magnitude_squared[1],
        magnitude_fourth[1],
        2
    );

    assign basis_i[6] = calculate_basis_component(
        selected_i[2],
        magnitude_squared[2],
        magnitude_fourth[2],
        0
    );
    assign basis_i[7] = calculate_basis_component(
        selected_i[2],
        magnitude_squared[2],
        magnitude_fourth[2],
        1
    );
    assign basis_i[8] = calculate_basis_component(
        selected_i[2],
        magnitude_squared[2],
        magnitude_fourth[2],
        2
    );

    assign basis_q[0] = calculate_basis_component(
        selected_q[0],
        magnitude_squared[0],
        magnitude_fourth[0],
        0
    );
    assign basis_q[1] = calculate_basis_component(
        selected_q[0],
        magnitude_squared[0],
        magnitude_fourth[0],
        1
    );
    assign basis_q[2] = calculate_basis_component(
        selected_q[0],
        magnitude_squared[0],
        magnitude_fourth[0],
        2
    );

    assign basis_q[3] = calculate_basis_component(
        selected_q[1],
        magnitude_squared[1],
        magnitude_fourth[1],
        0
    );
    assign basis_q[4] = calculate_basis_component(
        selected_q[1],
        magnitude_squared[1],
        magnitude_fourth[1],
        1
    );
    assign basis_q[5] = calculate_basis_component(
        selected_q[1],
        magnitude_squared[1],
        magnitude_fourth[1],
        2
    );

    assign basis_q[6] = calculate_basis_component(
        selected_q[2],
        magnitude_squared[2],
        magnitude_fourth[2],
        0
    );
    assign basis_q[7] = calculate_basis_component(
        selected_q[2],
        magnitude_squared[2],
        magnitude_fourth[2],
        1
    );
    assign basis_q[8] = calculate_basis_component(
        selected_q[2],
        magnitude_squared[2],
        magnitude_fourth[2],
        2
    );

    genvar term_index;
    generate
        for (term_index = 0;
             term_index < DPD_NUM_COEFFICIENTS;
             term_index++) begin : generate_complex_terms

            assign term_i[term_index] = calculate_term_i(
                basis_i[term_index],
                basis_q[term_index],
                coefficient_i[term_index],
                coefficient_q[term_index]
            );

            assign term_q[term_index] = calculate_term_q(
                basis_i[term_index],
                basis_q[term_index],
                coefficient_i[term_index],
                coefficient_q[term_index]
            );
        end
    endgenerate

    assign accumulator_i_comb =
        extend_complex_term(term_i[0])
        + extend_complex_term(term_i[1])
        + extend_complex_term(term_i[2])
        + extend_complex_term(term_i[3])
        + extend_complex_term(term_i[4])
        + extend_complex_term(term_i[5])
        + extend_complex_term(term_i[6])
        + extend_complex_term(term_i[7])
        + extend_complex_term(term_i[8]);

    assign accumulator_q_comb =
        extend_complex_term(term_q[0])
        + extend_complex_term(term_q[1])
        + extend_complex_term(term_q[2])
        + extend_complex_term(term_q[3])
        + extend_complex_term(term_q[4])
        + extend_complex_term(term_q[5])
        + extend_complex_term(term_q[6])
        + extend_complex_term(term_q[7])
        + extend_complex_term(term_q[8]);

    assign accumulator_work_i = {
        {(DPD_ROUND_WORK_WIDTH-DPD_ACCUMULATOR_WIDTH){
            accumulator_i_comb[DPD_ACCUMULATOR_WIDTH-1]
        }},
        accumulator_i_comb
    };

    assign accumulator_work_q = {
        {(DPD_ROUND_WORK_WIDTH-DPD_ACCUMULATOR_WIDTH){
            accumulator_q_comb[DPD_ACCUMULATOR_WIDTH-1]
        }},
        accumulator_q_comb
    };

    assign result_i_comb = dpd_saturate_sample(
        dpd_round_shift_away(
            accumulator_work_i,
            DPD_OUTPUT_RIGHT_SHIFT
        )
    );

    assign result_q_comb = dpd_saturate_sample(
        dpd_round_shift_away(
            accumulator_work_q,
            DPD_OUTPUT_RIGHT_SHIFT
        )
    );

    assign in_ready = !out_valid || out_ready;

    always_ff @(posedge clk or negedge rst_n) begin : state_registers
        if (!rst_n) begin
            delay_i[0] <= '0;
            delay_i[1] <= '0;
            delay_q[0] <= '0;
            delay_q[1] <= '0;

            out_valid <= 1'b0;
            out_i <= '0;
            out_q <= '0;
        end
        else if (in_ready) begin
            if (in_valid) begin
                delay_i[1] <= delay_i[0];
                delay_i[0] <= in_i;
                delay_q[1] <= delay_q[0];
                delay_q[0] <= in_q;

                out_valid <= 1'b1;
                out_i <= result_i_comb;
                out_q <= result_q_comb;
            end
            else begin
                out_valid <= 1'b0;
            end
        end
    end

endmodule

'default_nettype wire

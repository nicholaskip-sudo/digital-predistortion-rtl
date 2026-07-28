'default_nettype none

package dpd_pkg;

    timeunit 1ns;
    timeprecision 1ps;

    parameter int unsigned DPD_MEMORY_DEPTH = 3;
    parameter int unsigned DPD_NUM_ORDERS = 3;
    parameter int unsigned DPD_NUM_COEFFICIENTS =   DPD_MEMORY_DEPTH * DPD_NUM_ORDERS;

    parameter int unsigned DPD_ORDER_SLOT_0 = 1;
    parameter int unsigned DPD_ORDER_SLOT_1 = 3;
    parameter int unsigned DPD_ORDER_SLOT_2 = 5;

    parameter int unsigned DPD_SAMPLE_WIDTH = 16;
    parameter int unsigned DPD_SAMPLE_FRAC_BITS = 15;

    parameter int unsigned DPD_MAG_SQ_WIDTH = 32;
    parameter int unsigned DPD_MAG_SQ_FRAC_BITS = 30;

    parameter int unsigned DPD_MAG_FOURTH_WIDTH = 64;
    parameter int unsigned DPD_MAG_FOURTH_FRAC_BITS = 60;

    parameter int unsigned DPD_BASIS_WIDTH = 24;
    parameter int unsigned DPD_BASIS_FRAC_BITS = 20;

    parameter int unsigned DPD_COEFFICIENT_WIDTH = 24;
    parameter int unsigned DPD_COEFFICIENT_FRAC_BITS = 16;

    parameter int unsigned DPD_REAL_PRODUCT_WIDTH = 48;
    parameter int unsigned DPD_REAL_PRODUCT_FRAC_BITS = 36;

    parameter int unsigned DPD_COMPLEX_TERM_WIDTH = 49;
    parameter int unsigned DPD_COMPLEX_TERM_FRAC_BITS = 36;

    parameter int unsigned DPD_ACCUMULATOR_WIDTH = 54;
    parameter int unsigned DPD_ACCUMULATOR_FRAC_BITS = 36;

    parameter int unsigned DPD_OUTPUT_WIDTH = 16;
    parameter int unsigned DPD_OUTPUT_FRAC_BITS = 15;

    parameter int unsigned DPD_ORDER1_BASIS_LEFT_SHIFT =
        DPD_BASIS_FRAC_BITS - DPD_SAMPLE_FRAC_BITS;

    parameter int unsigned DPD_ORDER3_BASIS_RIGHT_SHIFT =
        DPD_SAMPLE_FRAC_BITS
        + DPD_MAG_SQ_FRAC_BITS
        - DPD_BASIS_FRAC_BITS;

    parameter int unsigned DPD_ORDER5_BASIS_RIGHT_SHIFT =
        DPD_SAMPLE_FRAC_BITS
        + DPD_MAG_FOURTH_FRAC_BITS
        - DPD_BASIS_FRAC_BITS;

    parameter int unsigned DPD_OUTPUT_RIGHT_SHIFT =     DPD_ACCUMULATOR_FRAC_BITS - DPD_OUTPUT_FRAC_BITS;

    // Large enough for the signed order-5 raw product:
    // Q1.15 sample multiplied by unsigned Q4.60 magnitude fourth.
    parameter int unsigned DPD_ROUND_WORK_WIDTH = 81;

    typedef logic signed [DPD_SAMPLE_WIDTH-1:0] dpd_sample_t;
    typedef logic signed [DPD_BASIS_WIDTH-1:0] dpd_basis_t;
    typedef logic signed [DPD_COEFFICIENT_WIDTH-1:0] dpd_coefficient_t;
    typedef logic signed [DPD_REAL_PRODUCT_WIDTH-1:0] dpd_real_product_t;
    typedef logic signed [DPD_COMPLEX_TERM_WIDTH-1:0] dpd_complex_term_t;
    typedef logic signed [DPD_ACCUMULATOR_WIDTH-1:0] dpd_accumulator_t;
    typedef logic signed [DPD_ROUND_WORK_WIDTH-1:0] dpd_round_work_t;

    localparam dpd_round_work_t DPD_BASIS_MAX_EXT = {
        {(DPD_ROUND_WORK_WIDTH-DPD_BASIS_WIDTH){1'b0}},
        1'b0,
        {(DPD_BASIS_WIDTH-1){1'b1}}
    };

    localparam dpd_round_work_t DPD_BASIS_MIN_EXT = {
        {(DPD_ROUND_WORK_WIDTH-DPD_BASIS_WIDTH){1'b1}},
        1'b1,
        {(DPD_BASIS_WIDTH-1){1'b0}}
    };

    localparam dpd_round_work_t DPD_SAMPLE_MAX_EXT = {
        {(DPD_ROUND_WORK_WIDTH-DPD_SAMPLE_WIDTH){1'b0}},
        1'b0,
        {(DPD_SAMPLE_WIDTH-1){1'b1}}
    };

    localparam dpd_round_work_t DPD_SAMPLE_MIN_EXT = {
        {(DPD_ROUND_WORK_WIDTH-DPD_SAMPLE_WIDTH){1'b1}},
        1'b1,
        {(DPD_SAMPLE_WIDTH-1){1'b0}}
    };

    function automatic int unsigned dpd_polynomial_order(
        input int unsigned order_slot
    );
        case (order_slot)
            0: return DPD_ORDER_SLOT_0;
            1: return DPD_ORDER_SLOT_1;
            2: return DPD_ORDER_SLOT_2;
            default: return 0;
        endcase
    endfunction

    function automatic int unsigned dpd_coefficient_index(
        input int unsigned memory_index,
        input int unsigned order_slot
    );
        return memory_index * DPD_NUM_ORDERS + order_slot;
    endfunction

    function automatic dpd_round_work_t dpd_round_shift_away(
        input dpd_round_work_t value,
        input int unsigned shift
    );
        logic signed [DPD_ROUND_WORK_WIDTH:0] extended_value;
        logic signed [DPD_ROUND_WORK_WIDTH:0] magnitude;
        logic signed [DPD_ROUND_WORK_WIDTH:0] offset;
        logic signed [DPD_ROUND_WORK_WIDTH:0] rounded_magnitude;

        begin
            if (shift == 0) begin
                return value;
            end

            extended_value = {value[DPD_ROUND_WORK_WIDTH-1], value};
            offset = '0;
            offset[shift-1] = 1'b1;

            if (value >= 0) begin
                return (extended_value + offset) >>> shift;
            end

            magnitude = -extended_value;
            rounded_magnitude = (magnitude + offset) >>> shift;
            return -rounded_magnitude;
        end
    endfunction

    function automatic dpd_basis_t dpd_saturate_basis(
        input dpd_round_work_t value
    );
        if (value > DPD_BASIS_MAX_EXT) begin
            return DPD_BASIS_MAX_EXT[DPD_BASIS_WIDTH-1:0];
        end

        if (value < DPD_BASIS_MIN_EXT) begin
            return DPD_BASIS_MIN_EXT[DPD_BASIS_WIDTH-1:0];
        end

        return value[DPD_BASIS_WIDTH-1:0];
    endfunction

    function automatic dpd_sample_t dpd_saturate_sample(
        input dpd_round_work_t value
    );
        if (value > DPD_SAMPLE_MAX_EXT) begin
            return DPD_SAMPLE_MAX_EXT[DPD_SAMPLE_WIDTH-1:0];
        end

        if (value < DPD_SAMPLE_MIN_EXT) begin
            return DPD_SAMPLE_MIN_EXT[DPD_SAMPLE_WIDTH-1:0];
        end

        return value[DPD_SAMPLE_WIDTH-1:0];
    endfunction

endpackage

'default_nettype wire

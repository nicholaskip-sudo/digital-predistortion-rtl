'default_nettype none

module dpd_fixed_spec_tb;

    timeunit 1ns;
    timeprecision 1ps;

    import dpd_pkg::*;

    initial begin : fixed_point_checks
        assert (DPD_SAMPLE_WIDTH == 16);
        assert (DPD_SAMPLE_FRAC_BITS == 15);

        assert (DPD_MAG_SQ_WIDTH == 32);
        assert (DPD_MAG_SQ_FRAC_BITS == 30);

        assert (DPD_MAG_FOURTH_WIDTH == 64);
        assert (DPD_MAG_FOURTH_FRAC_BITS == 60);

        assert (DPD_BASIS_WIDTH == 24);
        assert (DPD_BASIS_FRAC_BITS == 20);

        assert (DPD_COEFFICIENT_WIDTH == 24);
        assert (DPD_COEFFICIENT_FRAC_BITS == 16);

        assert (DPD_REAL_PRODUCT_WIDTH == 48);
        assert (DPD_REAL_PRODUCT_FRAC_BITS == 36);

        assert (DPD_COMPLEX_TERM_WIDTH == 49);
        assert (DPD_COMPLEX_TERM_FRAC_BITS == 36);

        assert (DPD_ACCUMULATOR_WIDTH == 54);
        assert (DPD_ACCUMULATOR_FRAC_BITS == 36);

        assert (DPD_OUTPUT_WIDTH == 16);
        assert (DPD_OUTPUT_FRAC_BITS == 15);

        assert (DPD_ORDER1_BASIS_LEFT_SHIFT == 5);
        assert (DPD_ORDER3_BASIS_RIGHT_SHIFT == 25);
        assert (DPD_ORDER5_BASIS_RIGHT_SHIFT == 55);
        assert (DPD_OUTPUT_RIGHT_SHIFT == 21);

        assert (
            DPD_COMPLEX_TERM_WIDTH >= DPD_REAL_PRODUCT_WIDTH + 1
        ) else $fatal(1, "Complex term lacks add/subtract growth bit.");

        assert (
            DPD_ACCUMULATOR_WIDTH >= DPD_COMPLEX_TERM_WIDTH + 4
        ) else $fatal(1, "Accumulator lacks nine-term growth bits.");

        $display(
            "FIXED_FORMAT sample=Q%0d.%0d basis=Q%0d.%0d coefficient=Q%0d.%0d",
            DPD_SAMPLE_WIDTH - DPD_SAMPLE_FRAC_BITS,
            DPD_SAMPLE_FRAC_BITS,
            DPD_BASIS_WIDTH - DPD_BASIS_FRAC_BITS,
            DPD_BASIS_FRAC_BITS,
            DPD_COEFFICIENT_WIDTH - DPD_COEFFICIENT_FRAC_BITS,
            DPD_COEFFICIENT_FRAC_BITS
        );

        $display(
            "FIXED_SHIFTS order1_left=%0d order3_right=%0d order5_right=%0d output_right=%0d",
            DPD_ORDER1_BASIS_LEFT_SHIFT,
            DPD_ORDER3_BASIS_RIGHT_SHIFT,
            DPD_ORDER5_BASIS_RIGHT_SHIFT,
            DPD_OUTPUT_RIGHT_SHIFT
        );

        $display("DPD_FIXED_SPEC_PASS");
        $finish;
    end

endmodule

'default_nettype wire

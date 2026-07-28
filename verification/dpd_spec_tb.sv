'default_nettype none

module dpd_spec_tb;

    timeunit 1ns;
    timeprecision 1ps;

    import dpd_pkg::*;

    initial begin : specification_checks
        assert (DPD_MEMORY_DEPTH == 3)
            else $fatal(1, "Unexpected memory depth.");
        assert (DPD_NUM_ORDERS == 3)
            else $fatal(1, "Unexpected number of polynomial orders.");
        assert (DPD_NUM_COEFFICIENTS == 9)
            else $fatal(1, "Unexpected coefficient count.");
        assert (DPD_SAMPLE_WIDTH == 16)
            else $fatal(1, "Unexpected sample width.");
        assert (DPD_SAMPLE_FRAC_BITS == 15)
            else $fatal(1, "Unexpected sample fractional bits.");
        assert (DPD_COEFFICIENT_WIDTH == 24)
            else $fatal(1, "Unexpected coefficient width.");
        assert (DPD_COEFFICIENT_FRAC_BITS == 16)
            else $fatal(1, "Unexpected coefficient fractional bits.");

        assert (dpd_polynomial_order(0) == 1)
            else $fatal(1, "Order slot 0 mismatch.");
        assert (dpd_polynomial_order(1) == 3)
            else $fatal(1, "Order slot 1 mismatch.");
        assert (dpd_polynomial_order(2) == 5)
            else $fatal(1, "Order slot 2 mismatch.");

        for (int unsigned memory_index = 0;
             memory_index < DPD_MEMORY_DEPTH;
             memory_index++) begin

            for (int unsigned order_slot = 0;
                 order_slot < DPD_NUM_ORDERS;
                 order_slot++) begin

                int unsigned index;
                index = dpd_coefficient_index(memory_index, order_slot);

                assert (
                    index ==
                    memory_index * DPD_NUM_ORDERS + order_slot
                )
                    else $fatal(1, "Coefficient index mismatch.");

                $display(
                    "COEFFICIENT_MAP index=%0d memory=%0d order=%0d",
                    index,
                    memory_index,
                    dpd_polynomial_order(order_slot)
                );
            end
        end

        $display("DPD_SPEC_PASS");
        $finish;
    end

endmodule

'default_nettype wire

'default_nettype none

module vector_io_smoke_tb;

    timeunit 1ns;
    timeprecision 1ps;

    logic signed [15:0] signed16 [0:7];
    logic signed [23:0] signed24 [0:7];

    initial begin : vector_io_checks
        $readmemh(
            "vectors/rtl/vector_io_smoke/signed16.hex",
            signed16
        );
        $readmemh(
            "vectors/rtl/vector_io_smoke/signed24.hex",
            signed24
        );

        assert (signed16[0] === 16'h0000);
        assert (signed16[1] === 16'h0001);
        assert (signed16[2] === 16'hFFFF);
        assert (signed16[3] === 16'h7FFF);
        assert (signed16[4] === 16'h8000);
        assert (signed16[5] === 16'h1234);
        assert (signed16[6] === 16'hEDCC);
        assert (signed16[7] === 16'h007B);

        assert (signed24[0] === 24'h000000);
        assert (signed24[1] === 24'h000001);
        assert (signed24[2] === 24'hFFFFFF);
        assert (signed24[3] === 24'h7FFFFF);
        assert (signed24[4] === 24'h800000);
        assert (signed24[5] === 24'h123456);
        assert (signed24[6] === 24'hEDCBAA);
        assert (signed24[7] === 24'h010000);

        assert ($signed(signed16[2]) == -1);
        assert ($signed(signed16[4]) == -32768);
        assert ($signed(signed16[6]) == -4660);

        assert ($signed(signed24[2]) == -1);
        assert ($signed(signed24[4]) == -8388608);
        assert ($signed(signed24[6]) == -1193046);

        $display(
            "VECTOR_IO_SIGNED_VALUES s16_neg1=%0d s16_min=%0d s24_neg1=%0d s24_min=%0d",
            $signed(signed16[2]),
            $signed(signed16[4]),
            $signed(signed24[2]),
            $signed(signed24[4])
        );

        $display("VECTOR_IO_SMOKE_PASS");
        $finish;
    end

endmodule

'default_nettype wire

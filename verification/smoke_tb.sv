'default_nettype none

module smoke_tb;

    timeunit 1ns;
    timeprecision 1ps;

    localparam int unsigned WIDTH = 8;

    logic             clk;
    logic             rst_n;
    logic             enable;
    logic [WIDTH-1:0] count;
    logic [WIDTH-1:0] held_count;

    smoke_counter #(
        .WIDTH(WIDTH)
    ) dut (
        .clk    (clk),
        .rst_n  (rst_n),
        .enable (enable),
        .count  (count)
    );

    initial begin
        clk = 1'b0;
        forever #5ns clk = ~clk;
    end

    property p_increment_when_enabled;
        @(posedge clk) disable iff (!rst_n)
            enable |=> count == ($past(count) + 1'b1);
    endproperty

    property p_hold_when_disabled;
        @(posedge clk) disable iff (!rst_n)
            !enable |=> count == $past(count);
    endproperty

    assert property (p_increment_when_enabled)
        else $fatal(1, "Counter failed to increment while enable was asserted.");

    assert property (p_hold_when_disabled)
        else $fatal(1, "Counter changed while enable was deasserted.");

    initial begin : stimulus
        rst_n      = 1'b0;
        enable     = 1'b0;
        held_count = '0;

        repeat (3) @(negedge clk);

        assert (count == '0)
            else $fatal(1, "Counter was not zero during reset. count=%0d", count);

        rst_n  = 1'b1;
        enable = 1'b1;

        repeat (10) @(negedge clk);

        assert (count == WIDTH'(10))
            else $fatal(1, "Expected count=10, actual count=%0d", count);

        enable     = 1'b0;
        held_count = count;

        repeat (3) @(negedge clk);

        assert (count == held_count)
            else $fatal(
                1,
                "Counter did not hold. expected=%0d actual=%0d",
                held_count,
                count
            );

        $display("DSIM_SMOKE_PASS: count=%0d", count);
        $finish;
    end

    initial begin : timeout
        #1us;
        $fatal(1, "Smoke simulation timed out.");
    end

endmodule

'default_nettype wire

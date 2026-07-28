`default_nettype none
module smoke_counter #(parameter int unsigned WIDTH = 8) (
    input wire clk,
    input wire rst_n,
    input wire enable,
    output logic [WIDTH-1:0] count
);
    timeunit 1ns;
    timeprecision 1ps;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= '0;
        else if (enable)
            count <= count + 1'b1;
    end
endmodule
`default_nettype wire

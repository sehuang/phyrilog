module TestNewlinePorts(
    input clock,
    input [3:0] A,
    input [3:0] B,
    output carry,
    output [3:0] sum
);
endmodule
module TestInlinePorts(input clock, input [3:0] A, input [3:0] B, output carry, output [3:0] sum);
endmodule : TestInlinePorts
module TestHybridPorts(input clock, input [3:0] A, input [3:0] B,
    output carry, output [3:0] sum);
endmodule : TestHybridPorts
module TestParamsAndPorts#(
    parameter BITS = 3
)(
    input clock,
    input [BITS-1:0] A,
    input [BITS-1:0] B,
    output carry,
    output [BITS-1:0] sum
);
endmodule : TestParamsAndPorts
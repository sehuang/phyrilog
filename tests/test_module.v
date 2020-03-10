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
    parameter BITS = 8
)(
    input clock,
    input [BITS-1:0] A,
    input [BITS-1:0] B,
    output carry,
    output [BITS-1:0] sum
);
endmodule : TestParamsAndPorts
module TestDummifier(
    input a,
    input b,
    input c,
    output d,
    output e,
    output f
);
    wire A;
    wire B;
    wire C;
    wire D;
    wire E;

    assign d = D;
    assign f = c | E;

    random_gate dim1 (
        .ina(A),
        .inb(B),
        .inc(C),
        .outd(D)
    );

    dummya da (
        .wow(A),
        .thi(B),
        .actually(C),
        .works(D),
        .somehow(E)
    );

    dummyb Db (
        .awow(a),
        .athi(b),
        .aactually(c),
        .aworks(D),
        .asomehow(E)
    );
endmodule : TestDummifier

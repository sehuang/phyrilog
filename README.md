# phyrilog
Verilog-to-physical conversion scripts

## TODO:
* Pin placement is currently dumb and just places all 
the pins on one side iteratively without trying to
first place pre-determined pin locations and then 
auto-determining the remainder. This need to be
implemented.
* ~~Might make more sense to make the rectangles 
themselves objects and work with that.~~ This has 
been implemented in the `rectangle_object_refactor`
branch
* Some information is gotten from inconsistent sources.
This need refactoring.
* The only port definition schema supported is as follows:
>```systemverilog
>module #(
>    parameter N = 3
>)(
>    input [N - 1:0] A,
>    input [N - 1:0] B,
>    output [N - 1:0] C
>);
>```
Support for this schema needs to be added:
>```systemverilog
>module #(parameter N = 3)(A,B,C);
>
>    input [N - 1:0] A,
>    input [N - 1:0] B,
>    output [N - 1:0] C  
>```

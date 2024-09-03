#include "francis_clock_ingress.p4"
#include "francis_clock_egress.p4"
#include "header_parser.p4"
#if __TARGET_TOFINO__ == 3
#include <t3na.p4>
#elif __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif
/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

//switch architecture

Pipeline(SwitchIngressParser(),
         SwitchIngress(),
         SwitchIngressDeparser(),
         SwitchEgressParser(),
         SwitchEgress(),
         SwitchEgressDeparser()) pipe;

Switch(pipe) main;

// Pipeline(SwitchIngressParser(),
//          SwitchIngress(),
//          SwitchIngressDeparser(),
//          EmptyEgressParser(),
//          EmptyEgress(),
//          EmptyEgressDeparser()) pipe1;

// Pipeline(EmptyIngressParser(),
//          EmptyIngress(),
//          EmptyIngressDeparser(),
//          SwitchEgressParser(),
//          SwitchEgress(),
//          SwitchEgressDeparser()) pipe2;

// Switch(pipe1, pipe2) main;


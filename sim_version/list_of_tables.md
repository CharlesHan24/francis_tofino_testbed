1. Packet generation tables.
- two applications: TYPE_ALGO_SLOW_RECONS and TYPE_PING_DETECTION.
- For the emulated version, we generate one batch of packets each delivered to a different logical switch. 
- The period of checking for TYPE_PING_DETECTION is 50000ns, and the period of checking for TYPE_ALGO_SLOW_RECONS is 1260ns. 
- PING PORT = 6


2. Initializing the original table
- depth for roots is set to be 1.

3. Configure other register arrays used for the spanning tree algorithm
- phase_12_launch_next_round_tab. round id counts from 1 to 8 inclusively

4. multicast group rules
    if unicast_ports != -1:
        prioritize unicast ports

5. For recirculation packets: we define port 54 to be the egress port and port 55 to be the ingress port to be recirculated. Ports 54 and 55 are connected.

6. Depth, max_depth, and min_global_depth
- rules for updating max_depth. If (12 == depth + current_round){
    update max_depth of its parent.
    If ((current_round == 10) && (pkt.tree_id == this.tree_id (is root))){
        update min_global_depth
    }
  }

TODO: 1. forward to CPU as CPU cannot listen data plane ports.
2. Set ports to loopback mode. Instead of forwarding a packet to the logical switch's egress port, we directly forward it to the peer logical switch's egress port!

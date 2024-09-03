slow = 39.45885109901428 + 2, fast = 4.38650107383728 + 2
Config: 2s SYNC interval (does not count for the first SYNC 1 interval since the first SYNC_ping message occurs at 0s but annotates that the first packet loss happens which should happens at 2s), 1s algo ping interval for rate-limiting.


correct version, without extra ack messages. same setting 2s sync interval, 1s algo ping interval
time elapsed for slow_recons = 42.56364989280701, fast = 4.44517707824707


Tested on a more complicated/difficult test case, failing a link that causes the deoth of the fast recovery tree == maximum distance between any two pair of switches to be 7; also triggers algo_ping message since the failed link would lead to a whole subtree to be failed. This is actually an adverserial case for PTP where it converges slow enough.
10Mbps time elapsed for slow recons = 47.374167919158936, fast = 4.394640922546387
100Mbps time elapsed for slow_recons = 47.42334198951721, fast = 4.4679529666900635

slow = 39.45885109901428 + 2, fast = 4.38650107383728 + 2
Config: 2s SYNC interval (does not count for the first SYNC 1 interval since the first SYNC_ping message occurs at 0s but annotates that the first packet loss happens which should happens at 2s), 1s algo ping interval for rate-limiting.


correct version, without extra ack messages. same setting 2s sync interval, 1s algo ping interval
time elapsed for slow_recons = 42.56364989280701, fast = 4.44517707824707
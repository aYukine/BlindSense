#!/usr/bin/env python3
import time, csv, os
with open('power_metrics.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'power_w_estimated'])
    while True:
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq') as cf:
                freq_mhz = int(cf.read().strip()) / 1000
            est_power = 5.0 + max(0, (freq_mhz - 800) * 0.1)  # Simplified
        except:
            est_power = 8.0  # Default estimate
        writer.writerow([time.strftime('%Y-%m-%d %H:%M:%S'), f"{est_power:.1f}"])
        f.flush()
        time.sleep(1.0)
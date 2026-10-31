export const checks={
 congestion:{label:"Slow / congested network",description:"Look for simultaneous high utilization, latency, drops and packet loss.",fields:[["link_utilization_pct","Link utilization (%)"],["latency_ms","Round-trip latency (ms)"],["packet_loss_pct","Packet loss (%)"],["queue_drops","Queue drops (count)"],["jitter_ms","Jitter (ms)"]]},
 wifi:{label:"Weak or intermittent Wi-Fi",description:"Signal quality and retries distinguish poor wireless conditions.",fields:[["rssi_dbm","RSSI (dBm)"],["snr_db","Signal-to-noise (dB)"],["retransmissions_pct","Retransmissions (%)"]]},
 dhcp:{label:"Unable to obtain an IP address",description:"Check DHCP failures alongside reachability of the gateway.",fields:[["dhcp_timeout_pct","DHCP timeout (%)"],["gateway_ping_ms","Gateway latency (ms)"]]},
 dns:{label:"Name resolution delays",description:"Compare DNS lookup time with gateway response.",fields:[["dns_latency_ms","DNS lookup latency (ms)"],["gateway_ping_ms","Gateway latency (ms)"]]},
 hardware:{label:"Possible switch overload / interface error",description:"Examine CPU, memory, interface errors and link behavior.",fields:[["cpu_utilization_pct","CPU utilization (%)"],["memory_pct","Memory utilization (%)"],["crc_errors","CRC errors (count)"],["link_utilization_pct","Link utilization (%)"],["latency_ms","Latency (ms)"]]}
} as const;
export type CheckKey=keyof typeof checks;
export const fieldSet=[...new Set(Object.values(checks).flatMap(c=>c.fields.map(f=>f[0])))];
export function missingFor(key:CheckKey,metrics:Record<string,number>){return checks[key].fields.filter(([id])=>!Number.isFinite(metrics[id]));}

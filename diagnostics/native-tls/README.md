# Native TLS trust-replacement reproducer

Status: **unresolved native TLS behavior in Designer 10.5.0 and an experimental
Linux Core VM running 10.5.0-2609.007; not a plugin fix**.
Tracked in [issue 1](https://github.com/joshua-small/qsys-mqtt/issues/1).
This diagnostic uses `TcpSocket.NewTls()` directly. It contains no MQTT engine,
reconnect manager, certificate-file adapter, or MQTT UI state.

## Reproduce locally

Use a separate test design and disposable output directory. The generated Lua
contains synthetic private keys, which must never be used for real services.

```sh
uv run --no-project --with cryptography python diagnostics/native-tls/make_probe.py .local/native-tls
python3 diagnostics/native-tls/server.py .local/native-tls
```

The server binds only `127.0.0.1`, ports 18990-18994. Port 18990 receives diagnostic
messages; 18991 and 18992 have separate TLS contexts for the same test server;
18994 requires a client certificate. The reserved 18993 listener is unused by
this sequence. TLS tickets are disabled and each accepted handshake records its
TLS version and `session_reused`. If running Python under WSL, localhost forwarding
must make those listeners reachable from Windows Designer.

In a fresh Designer 10.5.0 process, put the generated `probe.lua` into a separate
Control Script and emulate. The tests run automatically. Keep the script's global
`ProbeSocket`, `ProbeReporter` and `ProbeTimer` references intact. The source was
actually exercised in a separate diagnostic plugin fixture with the same runtime
body; pasting it into a Control Script is the simplified reproduction procedure,
not an additional application test already performed.

The script sends a case label over TLS and requires the server's acknowledgement
before reporting `ACCEPTED`. A TLS `Connected` event alone is insufficient to
establish that a TLS 1.3 server accepted a client certificate. Native errors here
are from disposable local test identities, never production credentials.

Stop and restart emulation in that same process, then compare the first wrong-CA
case. Finish by stopping emulation and the Python server. Restart Designer before
repeating a fresh-process comparison. Do not copy these diagnostic files into the
installed Plugins catalog or deploy them to a production Core.

## Designer emulation results, 2026-10-16

[Recorded events](designer-10.5.0.jsonl) contain two complete runs: a fresh Designer
process, then emulation restarted in that same process. The test server was not
restarted between those two runs.

| Case | Fresh process result | Interpretation |
| --- | --- | --- |
| Unrelated CA before any successful connection | Rejected: unable to get local issuer certificate | Negative control worked |
| Correct CA | Accepted with server acknowledgement | Positive control worked |
| Unrelated CA after correct CA, new socket | Accepted incorrectly | Trust replacement failed |
| Unrelated CA, different port and separate server TLS context | Accepted incorrectly | Failure was not tied to the first listener |
| Empty `CACertData`, then unrelated CA | Accepted incorrectly | Empty assignment did not reset trust |
| Untrusted client certificate before/after a trusted identity | Rejected before acknowledgement | No accepted stale client identity observed |
| Trusted and renewed client identities | Accepted; server recorded their distinct subjects | Identity replacement worked in these cases |
| No client identity after a trusted identity | Rejected before acknowledgement | No inherited client identity observed |

All server-accepted connections used TLS 1.3 with `session_reused=false`. Every
case set `ValidateCertificate=true`; the CA readback matched the supplied value.
The wrong-CA failures therefore occur without the MQTT engine and without TLS
session resumption in these recorded handshakes. Stopping/restarting emulation
did not clear the trust: the first wrong-CA case in the second run was accepted.
The exact native internal mechanism and its scope across other scripts,
plugin instances and physical Cores have not been established.

## Linux Core VM results, 2026-10-16

The same twelve-case sequence was deployed with **Save to Core & Run** to an
existing experimental Hyper-V lab VM running firmware `10.5.0-2609.007`. These
were native Linux `runtime_engine` runs, not Designer emulation. The VM has
existing platform shims and a model alias; their hashes matched in the captures
before and after redeployment. The running native executable matched the retained
original firmware binary. This is evidence from a modified lab environment, not
acceptance on a supported or physical Core.

The probe's only runtime changes were its two destination addresses. The Python
server bound directly to the host-only interface, and the synthetic server
certificate included that interface's IP SAN. There was no TLS relay. Python TLS
positive/negative controls against the same listener and certificates passed.
Raw VM captures, design files and generated private keys remain local; this is a
sanitized result summary.

Two complete native runs produced the same results:

| Case | Both VM runs |
| --- | --- |
| Unrelated CA first | Rejected: unable to get local issuer certificate |
| Correct CA | Accepted with server acknowledgement |
| Unrelated CA after correct CA, new socket | Accepted incorrectly |
| Unrelated CA, different port and separate server TLS context | Accepted incorrectly |
| Correct CA on the new port, then correct CA again | Accepted |
| Empty `CACertData`, then unrelated CA | Accepted incorrectly |
| Untrusted client certificate before/after trusted identity | Rejected before acknowledgement |
| Trusted and renewed client identities | Accepted with distinct subjects recorded by server |
| No client identity after trusted identity | Rejected before acknowledgement |

Every case read back the assigned CA and used `ValidateCertificate=true`. All
sixteen accepted connections across the two runs used TLS 1.3 and
`session_reused=false`, and each required its matching server acknowledgement.
This reproduces the trust-replacement failure outside Designer emulation.

Between runs, **Save to Core & Run** changed the native runtime PID. The first
unrelated-CA case rejected again in the new process, unlike stopping/restarting
emulation within one Designer process. The within-process failure then recurred.
Process replacement cleared the tested state; this is not a supported MQTT
reconnect or CA-rotation fix. The exact native cause remains unresolved.

## Implementation and acceptance boundary

The MQTT source already releases the old socket, reloads current credentials,
creates a new TLS socket and follows the certificate/key/CA/validation sequence
shown in the current [Q-SYS TcpSocket example](https://help.qsys.com/Content/Control_Scripting/Using_Lua_in_Q-Sys/TcpSocket.htm).
That ordering is an example, not a documented trust-reset contract. Earlier
observations should not be read as establishing setter ordering as the root cause.

Independent SDK review found no plugin-side stale-CA path and no documented
trust-store reset, explicit TLS-context isolation or peer-certificate inspection
API in the reviewed current Help. The reviewer independently passed the existing
13 TLS test groups, 47 regression groups including 52 layouts, and generated-build
consistency on source commit `f7e0bc24ae0fa47e391c3fb4c43b9d4e0f3b18ad`.
Those offline checks do not resolve the native failure.

A per-client rotation guard would not establish native isolation from other
scripts or plugin instances, and disabling certificate validation is not a fix.
The package therefore retains its TLS warning and version 0.3.0.1. No production
source, installed plugin or Core Manager certificate configuration was changed
by this diagnosis.
The lab VM temporarily ran a separate diagnostic design for the native test;
its backed-up design was restored afterward. The test server was stopped and
the temporary scoped firewall rule was removed.

Next acceptance requires a supported Q-SYS trust replacement/isolation mechanism
or runtime correction, followed by the issue's Designer/Core test matrix. File
loading, hostname/SNI/chain behavior and physical Core acceptance remain open.
No Q-SYS support case has been sent by this investigation.

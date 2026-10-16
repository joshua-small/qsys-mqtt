# QSC report draft: Lua TLS retains CA trust across new sockets

Prepared October 16, 2026. Draft for owner review; not submitted to QSC.

## Problem and expected behavior

With `TcpSocket.NewTls()`, an unrelated CA is rejected in a fresh process, but
the same unrelated CA can succeed after an earlier socket used the server's
correct CA. Each socket reports the newly assigned `CACertData` and
`ValidateCertificate=true`. Disconnecting, retiring callbacks and creating a
new socket does not restrict trust to that socket's supplied CA.

Expected: a validating socket explicitly configured with CA B must reject a
server whose certificate chains only to unrelated CA A. If this API intentionally
adds trust globally, please document that contract and provide an isolated
per-connection trust store with effective removal/replacement semantics.

Potential impact: an application can continue accepting a peer after its configured
CA is changed. Static evidence indicates a process-wide context, so independent
scripts may affect each other's trust. Cross-script exploitation was not tested;
this report makes no claim of arbitrary code execution or remote compromise.

## Environments and limits

- Windows Q-SYS Designer 10.5.0 native emulation: reproduced with bare TLS,
  without the MQTT module. Restarting emulation within the same Designer process
  did not reset observed trust; exiting and relaunching Designer did.
- Linux Core runtime 10.5.0, build 2609.007, in an owner-controlled Hyper-V lab.
  This is an experimental, unlicensed VM with existing platform compatibility
  shims and a Core 24f model alias, not a supported or commissioned physical Core.
  No vendor binary or platform shim was changed for these tests.
- Retained original runtime SHA-256:
  `b3aa9ebcd86eb2cae82aed65740d50477dd64ddc85085d35b3c7662fa01bb114`.
  The live executable hash matched. Physical Core reproduction remains requested.
- Disposable certificate authorities and a host-only TLS endpoint; no production
  broker, customer credentials or customer design is needed to reproduce.

## Minimal reproduction

1. Create unrelated CA A and CA B. Give a local TLS server a certificate signed
   only by A. Disable TLS session tickets and log session reuse.
2. Start a fresh Designer process or Save to Core & Run to start a new runtime.
3. For each case create a new globally retained `TcpSocket.NewTls()`. Disable
   native auto-reconnect. Assign the case's PEM to `CACertData`, then set
   `ValidateCertificate=true`. Connect to the same server, send a distinct label
   only after Connected, and require the server to echo an exact ACK before
   recording acceptance. Retire handlers and disconnect after each case.
4. Run cases in order: B, A, B. Also repeat B against a different server port.
5. Repeat after setting `CACertData=""` before B, and after Save to Core & Run.

Core sequence used:

```lua
Socket = TcpSocket.NewTls()
Socket.ReconnectTimeout = 0
Socket.CACertData = CaseCaPem
Socket.ValidateCertificate = true
-- Install Connected/Data/Error/Closed/Timeout handlers and an independent timer.
-- Count success only after the exact application ACK.
Socket:Connect(TestHost, TestPort)
```

| Case | Result |
|---|---|
| Unrelated B in fresh process | Certificate verification error |
| Correct A | Exact ACK accepted |
| B after successful A, new socket | Exact ACK accepted unexpectedly |
| B after A, different port | Exact ACK accepted unexpectedly |
| Empty CA assignment followed by B | Exact ACK accepted unexpectedly |
| B after Save to Core & Run | Certificate verification error again |

All accepted Linux test connections reported TLS 1.3 and `session_reused=false`.
Server tickets were disabled. Separate mTLS tests rejected an unrelated client
identity before and after a trusted client identity, accepted a renewed trusted
client identity, and rejected a missing client certificate. Thus the observed
CA retention is not a claim that all TLS checks are disabled.

Save to Core & Run changed the measured runtime PID (one captured comparison:
25801 to 26066) and restored the fresh-process wrong-CA rejection. This is an
observed workaround on the experimental VM, not a QSC-supported remediation.

## Access Control and Core Manager comparisons

The same CA retention reproduced with Access Control enabled. Enabling Secure
Communication restarted the design but the new run still retained CA A after
replacement. It also reproduced with Trust On First Use off, certificate validity
verification on, rollover off, and Control Server Authentication off.

Next, a fresh runtime compared three Core Manager states: an empty trusted list,
CA A in Trusted Certificates, and CA A in Declined Certificates. Each state used
the same strict options above and a fresh Save to Core & Run.

| Lua configuration | Empty list | A trusted | A declined |
|---|---|---|---|
| Validation enabled, no `CACertData` | Native error, no ACK | Same | Same |
| Explicit unrelated CA B, first supplied CA | Verification error | Same | Same |
| Explicit correct CA A | Exact ACK accepted | Same | Same |
| No `CACertData` after explicit A | Native error, no ACK | Same | Same |

The native empty-CA error was: `Certificate validation enabled but no CA certificate provided`.
The probe deadline records that the attempt did not complete; the accompanying
Designer debug screenshot identifies the native error rather than a network timeout.

Core Manager imported the public CA with fingerprint
`B6:03:25:CE:F0:E6:2F:6D:4B:D3:ED:1C:93:68:A1:F2:89:B7:6D:84:59:7E:5F:87:2D:DD:44:41:6B:C3:D0:BC`.
Read-only guest inspection showed it under `/var/rwfs2/certificates/trusted/`.
`/var/tmp/cert/trusted_combined.pem` changed from an empty file to a 1164-byte
bundle whose SHA-256 exactly matched the supplied public CA:
`c4fbc0fa50a056ed7c0a83aed256cea307e3463e6939698a9d55700b6e1e270a`.
The temporary entry was subsequently removed; trusted/pending/declined counts
returned to zero. The Core's own device certificate was not replaced.

These results show that the tested Lua socket path does not inherit or enforce
those Core Manager trust lists. They do not establish that every Q-SYS TLS client
uses the same behavior.

## Candidate guard and file-access test, October 16

The exact generated module 0.3.1 engine was embedded in a separate diagnostic
fixture, with the production credential loader and native TcpSocket/Timer APIs.
No file adapter or private key was embedded. A disposable public CA file under
`media/` loaded successfully and completed MQTT 5 CONNECT/CONNACK over one full
TLS 1.3 handshake (`session_reused=false`).

After disposal, replacing that file with unrelated CA bytes made a new client
report `Disconnected: ca-change-requires-runtime-restart`, with no socket created.
Reverting the file and replacing the client remained blocked. The probe left
the unrelated CA on disk, then Save to Core & Run replaced native PID 22547 with
22785. In the new process the unrelated CA reached the native transport and was
rejected with `socket-error`; no further completed TLS handshake or MQTT CONNECT
was recorded. This verifies the engine's real Core-VM file path and guard/restart
sequence, not the normal plugin UI or physical Core hardware.

Direct Lua `io.open` attempts for both `/var/tmp/cert/trusted_combined.pem` and
`var/tmp/cert/trusted_combined.pem` returned `invalid path` in both runs. Guest
inspection confirmed the real public bundle existed. Ordinary Lua file access
therefore cannot access this internal store in the tested sandbox.

The original VM design was restored through Designer and Core Manager reported
`VM-Before-TLS-Test`, running with its expected nine missing-peripheral faults.
Its preserved file hash remained unchanged. The disposable public CA file and
temporary scoped Hyper-V firewall rule were removed, and the host test server
was stopped. Access Control and Secure Communication remain enabled; TOFU and
rollover are off, validity-period checking is on, and control-server client
authentication is off. Trusted, pending and declined counts returned to zero.
The Core device certificate and vendor binaries were not replaced.

## Read-only implementation evidence

Static inspection of the retained Linux executable, without executing or patching
it, found this call chain (addresses apply only to the hash above):

- `control_lib::lua2::lua_socket_t` constructs `qsc::tcp_socket_t` (call at
  `0x1df2f31`) and its Connect path calls `qsc::tcp_socket_t::connect`
  (`0x1df7012`).
- `qsc::tcp_socket_t::configure` calls `qsc::ssl::ssl_context()` at `0x3482a1f`,
  obtains that context's store with `SSL_CTX_get_cert_store` at `0x3482ab6`, and
  adds the parsed certificate using `X509_STORE_add_cert` at `0x3482ac4`.
- `qsc::ssl::ssl_context()` at `0x347c090` uses a C++ guarded static, creates the
  context once with `SSL_CTX_new`, and registers its destruction with `__cxa_atexit`.
  This strongly supports process-lifetime additive trust as the mechanism.
- Separate Q-SYS control-communication socket constructors call
  `qsec::tls_context()`. The runtime links `qsec.so` and its trusted-certificate
  database. Presence of that library does not mean Lua sockets use its context.

This is version-specific internal evidence, not a supported API, source-code
claim or vendor-confirmed root cause. Disassembly and vendor binaries remain
local; they are not included in the public plugin package.

## Documentation and questions for QSC

The [TcpSocket TLS example](https://help.qsys.com/Content/Control_Scripting/Using_Lua_in_Q-Sys/TcpSocket.htm)
supplies PEM data explicitly. [Secure Communication](https://help.qsys.com/Content/Core_Manager/Core_Management/Secure_Communication.htm)
describes Q-SYS control/device communication, and [Certificates](https://help.qsys.com/Content/Core_Manager/Core_Management/Certificates.htm)
describes certificate management. The reviewed pages do not document a Lua
selector for Core Manager trust. [System Overview](https://help.qsys.com/Content/Security/Scope_Protocols.htm)
limits scripting filesystem access to media/design roots. Internal store paths
therefore are not a supported direct file-loading solution.

Please confirm:

1. Is additive process-wide CA trust intended for `TcpSocket.NewTls()`? Can QSC
   provide isolated trust per socket and effective CA replacement/removal?
2. Is there a supported Lua interface to Core Manager's trusted/declined lists,
   including updates and revocation, without embedding administrator credentials?
3. Which versions/platforms are affected, and is Save to Core & Run an approved
   temporary method to reset this TLS context?
4. What certificate-chain, hostname and SNI guarantees does this API provide?

The MQTT candidate's interim guard rejects changed CA bytes within a module
lifetime and instructs Save to Core & Run. It cannot enforce isolation between
scripts or prevent a Lua-only restart from losing its guard while native trust
remains. A runtime fix is still needed for robust per-socket trust semantics.

## Retained evidence

Local evidence folders: `.local/mqtt-tls-vm-20261016/` (original twelve-case runs,
hash/PID receipts) and `.local/mqtt-tls-security-20261016/` (Access Control,
Secure Communication, managed CA comparisons and static call-site notes).
The latter contains `manager-empty`, `manager-trusted`, and `manager-declined`
JSONL logs, public-CA metadata, and matching UI screenshots. Submission should
use sanitized logs, a minimal Lua reproduction and freshly generated disposable
PKI. Do not attach full firmware, credentials, raw VM captures or client designs.

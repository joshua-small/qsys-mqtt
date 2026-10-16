# MQTT candidate: requirements and acceptance boundary

## Current candidate: CA-change guard, October 16, 2026

Module 0.3.1 / plugin 0.3.1.0. Earlier sections below retain the evidence for their
named versions; they do not override this candidate's restart requirement.

- `src/tls.lua` keeps private module state as permitted by [Lua Scopes](https://help.qsys.com/DeveloperHelp/Content/Recommended_Practices/LuaScoping.htm).
  Initial CA bytes and a sticky changed-CA latch survive `Mqtt.New`, Dispose and
  plugin Apply/enable events within that module. No additional host objects exist.
- `src/client.lua` stops the tick timer, fails pending operations and reports
  Disconnected with a fixed error before creating a socket on changed CA bytes.
  Existing socket/callback retirement and protected transport calls remain intact;
  see [TCP](https://help.qsys.com/DeveloperHelp/Content/Recommended_Practices/TCP.htm)
  and [Pcall](https://help.qsys.com/DeveloperHelp/Content/Recommended_Practices/Pcall.htm).
- `src/plugin.lua` retains all design-time identity/control/layout contracts and
  presents this condition as Fault (2) with Save to Core & Run instructions.
- TLS validation stays enabled and credentials follow the [TcpSocket example](https://help.qsys.com/Content/Control_Scripting/Using_Lua_in_Q-Sys/TcpSocket.htm).
  The guard is an owner-selected mitigation, not an SDK requirement or native fix.
- Initial offline check: 15 TLS source/lifecycle/plugin groups passed, including
  file rotation, failed initial connection, replacing a client, file reversion,
  enable toggles, stopped retries and unchanged-CA client-key renewal.
- Independent fresh-context SDK review completed against the source hashes below.
  The reviewer independently retrieved applicable official documentation on
  October 16 (Developer Help unversioned; current runtime references 10.5.0).
  No blocking source/SDK finding remains. Required API contracts, recommended
  practices and example-derived TLS setter ordering were distinguished.
- The reviewer passed 47 regression groups/all 52 layouts, 19 MQTT 5 groups,
  15 TLS groups, generated-artifact consistency and six additional lifecycle
  probes: constructor failure after credential loading, throwing callbacks,
  callback-driven client replacement, stale callbacks, plaintext interlude and
  multiple clients. The first complete credential load pins the CA; failed
  credential loading before that point does not. Later native setup failure
  retains the pin. No additional socket was created on latched attempts.
- Review confirmed retained host objects, disabled native reconnect, retired
  callbacks, fixed/redacted errors, Fault 2 status, unchanged plugin identity,
  controls and geometry, and correct generated module/report packaging.
  Layout remains 400px wide, 400x100 header, 375x95.455 logo, page heights
  755/640/475. No new rendered-layout claim is made.
- StyLua 2.5.2 `--check --verify --syntax Lua53` passed for tls.lua,
  client.lua and plugin.lua with the existing 2-space/100-column/Unix settings.
  LuaLS 3.19.1 Information-level analysis loaded all four authored Lua files
  with the existing MQTT configuration/Q-SYS declarations: exit 0, diagnostics
  `[]`. Existing Linux binaries were reused; no source edits or installs.
- Builder VM acceptance passed with the exact generated module 0.3.1 engine
  in a separate diagnostic fixture: real `media/` CA file loading, native TLS 1.3
  MQTT 5 CONNECT/CONNACK, changed-CA and reverted-file latch, and wrong-CA
  rejection after Save to Core & Run replaced PID 22547 with 22785. Only one
  completed handshake occurred across both runs; the rotated/reverted attempts
  created no socket. No credential-file adapter was used.
- Direct Lua reads of both absolute and relative internal trust-bundle paths
  returned `invalid path`. The tested bundle existed outside the media/design
  sandbox. See the report for scope, observations and native-context evidence.
- Original VM design restored; disposable public CA, test server and temporary
  firewall rule removed. This is experimental modified-VM acceptance, not a
  physical Core or complete production-plugin UI test. Reviewer performed no
  GUI/Core actions. Longer restart-status text readability remains unverified.

| Reviewed candidate artifact | SHA-256 |
| --- | --- |
| Plugin 0.3.1.0 | `79607c6170dd9c8a55ab8e1e9c209d74b1701f27526d40431bafccc3b58aeca2` |
| Module 0.3.1 | `afffc3d4e8ed0403e5ae3701f21859ea13c44b03c4771a0fb8c6550308f4eab0` |

Native CA retention, Core Manager comparisons, static implementation evidence,
process restart observations and limitations are in [NATIVE-TLS-REPORT.md](NATIVE-TLS-REPORT.md).
This remains a development candidate: the per-module guard cannot prevent another
Lua environment from expanding the process-wide native trust store.


Target: Q-SYS 10.5.0. Developer Help is not version-pinned; retrieved 2026-10-11.
Requirement mapping, independent review and application observations are separated below.
The 0.3.0 TLS/file references were retrieved again on 2026-10-12.
Current house-style guidance was read from the owner's active checkout at
`docs/PLUGIN-STYLE-GUIDE.md`, including the Q-SYS status-color convention.
The supplied MQTT style derives from commit 8a98433; no unrelated plugin changes
were imported. The primary Generic Display source remains
a local reference, not a redistributable dependency of this plugin.

| Source and classification | Implementation | Verification / limit |
| --- | --- | --- |
| [External Lua Modules](https://help.qsys.com/Content/Control_Scripting/External_Lua_Modules.htm), packaging contract | `build.py`: `init.lua` returning one table, `info.json`, pure Lua closure | Generated module loads without LuaSocket, LuaSec or coroutine; Designer import and saved-design resource persistence passed; native require/traffic probe passed |
| [Basic Plugin Framework](https://help.qsys.com/DeveloperHelp/Content/Code_Examples/Basic_Plugin_Framework.htm), example plus metadata contract | `src/plugin.lua`: unique PluginInfo ID, runtime `if Controls then` | Offline design-time loading and runtime host doubles; Designer 10.5.0 compile/emulation passed |
| [Reserved Functions](https://help.qsys.com/DeveloperHelp/Content/Standards_Definitions/Reserved_Functions.htm), API contracts | GetProperties, GetPages, GetControls, GetComponents, GetControlLayout | Test all channel counts and pages, control types, bindings, unique order and geometry; no audio/serial pins or wiring required |
| [Reserved Control Names](https://help.qsys.com/DeveloperHelp/Content/Standards_Definitions/Reserved_Control_Names.htm), naming contract | Status, IPAddress, Username, Password | Source and layout checks |
| [TCP](https://help.qsys.com/DeveloperHelp/Content/Recommended_Practices/TCP.htm), recommended lifecycle handling | client `_Open`, `_Release`, `_Pump`, `_Lost`; same cleanup for Closed/Error/Timeout | Fragmentation, multi-packet bursts, connection timing and stale callbacks in fake transport |
| [TcpSocket](https://help.qsys.com/Content/Control_Scripting/Using_Lua_in_Q-Sys/TcpSocket.htm), transport API | Wait Connected before CONNECT; native Read/Write; NewTls with CA and ValidateCertificate=true | No LuaSocket adapter assumptions; Designer native TCP passed and native TLS connection observed; CA replacement fails the rejection check (see final section); Core files/TLS and native hostname behavior pending |
| [Timer](https://help.qsys.com/Content/Control_Scripting/Using_Lua_in_Q-Sys/Timer.htm), API | Tick/Work timers with Timer.Now | No sleep/run loop; bounded work and explicit timer shutdown; native Designer backoff observed; clock discontinuities and Core behavior pending |
| [Lua Scopes](https://help.qsys.com/DeveloperHelp/Content/Recommended_Practices/LuaScoping.htm), recommended lifetime | Plugin MqttClient global; client retains socket/timers; module locals private | _Release stops receive work and replaces retired socket handlers with stateless no-op functions; Dispose stops both timers; callers must retain client globally |
| [Pcall](https://help.qsys.com/DeveloperHelp/Content/Recommended_Practices/Pcall.htm), recommended error handling | Validated inputs, protected codec/transport/callback boundaries | Malformed frames and failing user callbacks exercised; errors avoid copying sensitive data |
| [Storing Secrets](https://help.qsys.com/DeveloperHelp/Content/Code_Examples/Storing_Secrets_in_Plugins.htm), example-derived pattern; [Embedded Components](https://help.qsys.com/DeveloperHelp/Content/Standards_Definitions/Embedded_Components.htm), API | SecretStorage custom_controls text.1, masked Password UI | Offline storage/masking test; synthetic password survived Designer save/reopen with masking; not encryption |
| [Plugin Debug](https://help.qsys.com/DeveloperHelp/Content/Recommended_Practices/Plugin_Debug.htm), recommendation | Standard Debug Print choices; metadata-only tracing | No raw credentials/payloads logged |
| [Code Style](https://help.qsys.com/DeveloperHelp/Content/Standards_Definitions/Style_Guide.htm), recommendation + house style | PascalCase public/state names, module-local helpers; design/runtime sections | Upstream MIT codec style intentionally unchanged for provenance |
| House style, owner convention | 400px white canvas, centered MQTT logo, gray panels, Setup then Channel tabs, explicit green confirmation LEDs, native buttons, right-aligned labels and footer; unique ZOrders | All 52 geometry/source combinations and negative mutations; combined 0.3.0.1 Setup, two Channel pages and Certificates rendered in Designer; full channel-count and dark-background extraction checks remain pending |
| [MQTT 3.1.1](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/errata01/os/mqtt-v3.1.1-errata01-os-complete.html), selected protocol contracts | UTF-8 topic validation, clean-session CONNECT, QoS0/1, acknowledgements and deadlines | Targeted wire vectors and lifecycle checks, not full MQTT conformance certification |

Layout retained from plugin 0.3.0.1: the supplied MQTT logo is centered in a 400x100
gray panel, using the complete 1100x280 viewBox at 375x95.455. Page titles sit on
white at (7,106), with content starting at y=130. Field width is 200px and external
label width 155px to accommodate broker addresses and payloads. Setup height is
755px; each paired channel uses a 640px page; Certificates uses 475px.
Tabs and headings match: Setup, Channel 1 through Channel N, Certificates. The earlier 36px text header and 670/555px layouts
belong to the historical Designer observations below, not this new candidate.
Optional native text/off-color overrides are omitted. No extra diagnostics page.

## Status/style update, plugin 0.2.0.1 (October 11, 2026)

The owner supplied mqtt-hor.svg and confirmed #660066. The embedded SVG preserves
the exact supplied asset, including its #606 shorthand and white areas. GetColor
uses named MqttPurple; Boolean Connected, Subscribed and ReceivedValid LEDs use
named IndicatorGreen. Brand color is not used for health indicators.

[Q-SYS Status Controls](https://help.qsys.com/Content/Control_Scripting/status_overview.htm)
provides the status semantics. Aggregate connection status now uses 5 while
connecting, 0 when accepted, and 2 on failure/retry wait or configuration error.
Deliberately disabled/requested-disconnect operation uses gray 3 with explicit
inactive text; this is our inactive presentation, not a claim of native component
Is Required/dynamic-pairing behavior. Focused regression assertions cover initial
connection, failure, retry, recovery, requested disconnect, disable and invalid
configuration. The MQTT engine, control definitions and saved bindings are unchanged.

House-style checks cover the logo, purple block, green LEDs, title/tab agreement,
all 44 page/channel combinations, bounds, overlap and unique shared stacking;
negative mutations retain coverage for missing captions and duplicate orders.
Native Designer rendering, dark-background extraction and hardware acceptance for
this new presentation remain pending. Earlier versioned acceptance is retained
below and must not be presented as a rendering check of 0.2.0.1.

Validation: 47 regression groups including all 44 layouts and the status lifecycle
assertions passed; LuaLS 3.19.1 Information-level diagnostics found no problems;
StyLua 2.5.2 Lua 5.3 formatting/syntax check passed. Independent fresh-context
SDK/style review retrieved Status, Reserved Functions, Code Style and Plugin Debug
requirements. It verified asset identity, geometry, control contracts, stacking
and LED meaning, identified the old all-disconnected-gray mapping, and re-reviewed
the final correction with no blocking finding. This is source/offline evidence.

Remaining acceptance before a production claim: all channel-count layouts in
Designer, selected/deselected and dragged controls over a dark background,
module use from a separate Control Script and shared design on another computer,
Core networking/TLS with valid and invalid certificates, authenticated-broker
refusal, sustained traffic, concurrent instances with unique client IDs,
native Last Will delivery and downstream output-event wiring.

## Initial source milestone, 2026-10-11

- 44 deterministic test groups passed under Lupa 2.8 / Lua 5.3, including all
  44 page/channel-count combinations and negative mutations for duplicate
  stacking order, missing heading and missing individual control label.
- aMQTT 0.12.1 bound only to localhost: actual TCP CONNECT, QoS 1 PUBACK,
  wildcard subscriptions, retained binary data, empty/repeated messages,
  Last Will and UNSUBACK passed through a simulated Q-SYS transport boundary.
- LuaLS 3.19.1 at Information level: zero diagnostics for both authored source
  files. Host declarations are intentionally loose, so this does not establish
  correctness of Q-SYS API calls. Luacheck was not run.
- StyLua 2.6.0 performed formatting with AST verification; the unmodified
  upstream codec files retain their own style. The build verifies their pinned
  normalized SHA-256 hashes and checks generated-artifact consistency.
- Independent fresh-context SDK and house-style review retrieved official
  sources and examined the full candidate. It identified and then independently
  verified corrections for reserved CONNACK flags, disposal/replacement during
  callbacks, a partial-header receive boundary, and cancellation during failure
  callbacks. All 44 test groups and five additional reviewer probes passed;
  no unresolved source findings remained. The exact reviewed identities and
  final delivery commit are recorded in issue 35.

No Designer, Viewer, Core or physical-device session was used for the initial
source milestone. The later Designer acceptance below supersedes its application gaps.

## Designer acceptance and version 0.1.1, 2026-10-11

The owner authorized installation, local broker testing and Computer Use, then
requested offline insertion into an empty schematic fixture. A separate candidate
was created from a small empty baseline; original inputs were hash-preserved.
The exploratory insertion did not change the production writer or its guards.
The plugin and module were installed under the user's Documents/QSC directories.

Observed in Q-SYS Designer **10.5.0**, using its native Lua/TcpSocket/Timer runtime
in emulation against **aMQTT 0.12.1 at 127.0.0.1:18884**:

- The fixture opened and compiled/emulated. Setup, Controls and Channel 2 rendered.
  Labels, hidden-control behavior and the two-line reconnect status were inspected.
- UI publish delivered `hello-from-designer` to `qsys/test/outgoing` with QoS 1
  broker acknowledgement. Wildcard subscription received retained data, repeated
  identical messages (count increased twice), an empty payload and binary bytes
  `00ff410a` displayed as `00FF410A` with Hex format.
- Apply/reconnect and broker stop/restart completed without a Lua error. Backoff,
  automatic reconnection and subscription restoration were observed. A message
  sent after restoration appeared in the UI. No publish was replayed automatically.
- Designer Save As followed by opening the saved file in a new Designer process
  preserved broker address, port, client ID, subscription, Enable and the masked
  synthetic password. The reopened design automatically connected/subscribed and
  received `received-after-save-reopen`. Startup did not publish a message.
  The broker allowed anonymous connections: this verifies storage, not password
  authentication or encryption.
- `qsys_mqtt` 0.1.1 was installed through Design Resources and embedded in the saved
  design. In a separate diagnostic fixture, `require("qsys_mqtt")`, client creation,
  connect, subscribe, QoS 1 publish, receive and Dispose passed. Designer printed
  `MODULE PROBE PASS`; the broker recorded `external-module-ok` on
  `qsys/test/module/echo`. This probe ran in a plugin Lua host; separate Control
  Script and cross-computer module acceptance remain pending. Probe instrumentation
  is local only and absent from the distributed plugin.

Application testing exposed and corrected three issues:

1. Hidden controls retained button styling and lacked distinct stacking order.
   Hidden layouts now use the minimal Style=None contract, and every control and
   graphic has a unique ZOrder. Visible labels and hidden buttons were rechecked.
2. Assigning nil to a native TcpSocket callback raised `function expected` during
   cleanup. Retired handlers now use a shared stateless no-op. Timer disposal uses
   the same function contract. Callback epochs still reject stale work. Fake-host
   setters now reject nil even after a function assignment, and regression tests
   exercise retirement and disposal. Native reconnect passed after this fix.
3. The reconnect status wrapped beyond the original 20px field. Its height is now
   30px; both lines fit during the final observed broker outage.

Final source checks: **47 deterministic groups**, all **44 page/channel-count
combinations**, broker integration, StyLua AST/format verification and LuaLS 3.19.1
Information-level diagnostics (zero with the absolute Q-SYS config path) passed.
A fresh-context SDK reviewer reviewed the callback and hidden-layout fixes
against official Help and independently reran 47 groups on callback-fix build
`5888b82752628db6f692b4e8cbf015c8ca8ab4e2b002a933920026f97310d2eb`.
The reviewer then inspected the final status-height-only change without rerunning
tests; the builder reran 47 groups on the final `c950a63e...` artifact. No unresolved
source findings remained. This is source review plus the specific application observations above,
not Core, TLS, physical-device or complete protocol certification.

Accepted artifact SHA-256 identities:

| Artifact | SHA-256 |
| --- | --- |
| `plugin/MqttClient.qplug` 0.1.1.0 | `c950a63efcb450bf67aff202d504db9ba0415d87dda9d1ca7caf25f2d35f12f5` |
| `module/qsys_mqtt/init.lua` 0.1.1 | `724d768679f25f75b7c48cbc91973d129e0f9602c2012ca6edcf04c454ff609a` |
| Designer-saved `MQTT-Designer-Acceptance.qsys` | `894a907071268e0d2eb18b3daa807d08bb859e6d6556e8af4aa3bd1b6deb0303` |

Local designs, insertion/hash receipts, test reports, broker log and synthetic
credential inspection are retained under
`.local/mqtt-designer-validation-20261011/` and excluded from Git. The fixture's
cached component caption still names an earlier build; the embedded source hash,
runtime banner and footer identify the accepted 0.1.1.0 build. No client or official
design was changed. Delivery and remaining scope are tracked in issue 35 / PR 36.


## MQTT 5 extension, version 0.2.0

The new design-time `MQTT Version` enum uses the Reserved Functions property
contract (Name, Type=enum, Choices, Value). Its default and missing-property
fallback are 3.1.1. Plugin identity, existing control names, layouts, native
hidden-control treatment and secret-storage binding remain unchanged.

| Official contract | Implementation | Verification |
| --- | --- | --- |
| [OASIS MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html), CONNECT/CONNACK sections 3.1–3.2 | Protocol level 5; clean start, zero session expiry, bounded maximum packet size, no topic aliases; honors broker limits and keepalive | Independent wire vectors; a nonzero server session-expiry override is valid but outside this implementation's capability, declined with a best-effort expiry-zero DISCONNECT |
| OASIS sections 3.4, 3.9, 3.11, 3.14 | Short/reason-bearing PUBACK; SUBACK/UNSUBACK per-filter results; server DISCONNECT | Negative acknowledgements fail only the operation; malformed reason codes/counts close transport; metadata-only errors |
| OASIS sections 1.5, 2.2 and packet-specific property rules | `src/mqtt5.lua` guards around unchanged upstream `protocol5.lua` | Bounded property reads, canonical variable integers, UTF-8, duplicate singleton rejection, permitted property types, no unrequested aliases/identifiers |
| OASIS sections 3.2.2 and 4.9 | Receive Maximum counts outgoing unacknowledged QoS1 publishes, independent of subscription requests and inbound ACKs | Broker limits, reset on reconnect, rejected wildcard restoration, server keepalive tests |
| Q-SYS TcpSocket and Core Manager Certificates, documented APIs | Explicit per-socket CA path, unchanged from 0.1.1 | No Core Manager store access or certificate synchronization implemented; native TLS, hostname validation and mutual TLS remain unaccepted |

Validation completed before application testing: 47 existing test groups and all
44 channel/page combinations; 19 new MQTT 5 groups; real localhost TCP with aMQTT
3.1.1 and Mosquitto 5.0. Mosquitto tests include an independent Paho MQTT 5
publisher with content type, response topic, binary correlation data, user
properties and binary payload. QoS1, retained/empty/repeated data, wildcard
subscriptions, Last Will and unsubscribe also passed. StyLua AST verification
and LuaLS Information-level checks passed with zero diagnostics on all three
authored Lua files. These are scoped checks, not full protocol certification.

Independent fresh-context SDK and house-style review completed with no
unresolved source findings. The reviewer retrieved the applicable official Q-SYS
contracts and OASIS protocol requirements, independently reran the regression,
layout, broker and MQTT 5 checks, and added probes for broker capabilities,
malformed properties, bounded/coalesced receive work, disposal, broker restart,
all 44 layouts with MQTT 5 selected, and the full plugin runtime lifecycle.
The final acknowledgement-display correction was independently rechecked with
all 19 MQTT 5 groups and generated-build consistency. This is source review,
not a reviewer-performed GUI session or full MQTT conformance certification.

### Designer MQTT 5 acceptance, 2026-10-11

The builder tested a separate two-channel fixture in Q-SYS Designer **10.5.0**
using native Lua/TcpSocket/Timer emulation and **Mosquitto 2.0.22 at
127.0.0.1:18885**. The original 0.1.1 accepted design hash remained unchanged.
The offline insertion/update experiment did not change production writer guards.

- The new property defaulted to 3.1.1 on the earlier design, and could be changed
  to 5.0. Setup and Controls rendered with the 0.2.0.0 runtime banner/footer.
- Compile/emulation connected, and Mosquitto explicitly recorded protocol level
  5, clean start and the expected client ID. Wildcard QoS1 subscription succeeded.
- An independent Paho MQTT 5 producer's retained `mqtt5-native-receive` message
  appeared under `qsys/test/incoming/v5` with Text format and count 1. The broker
  recorded the native client's PUBACK.
- UI publish sent `hello-from-designer` to `qsys/test/outgoing` at QoS1. Mosquitto
  returned reason 16 (accepted, no matching subscribers). The initially clipped
  feedback was shortened to `ACK: no subscribers`, retested and observed fully
  visible in the final build. No subscriber/device-delivery claim is made.
- Designer saved the final build, then opened that saved file in a fresh process.
  MQTT Version 5.0, broker/port/client ID, topics/QoS, Enable and masked synthetic
  password persisted. Starting emulation automatically reconnected, subscribed
  and received retained data; startup did not publish. The anonymous broker did
  not test password authentication.
- The installed external module was reloaded into the fixture and persisted
  without another changed-module prompt on reopen. This is resource acceptance;
  the separate native require/traffic probe remains specific to 0.1.1 above.

Final source and installed artifact identities:

| Artifact | SHA-256 |
| --- | --- |
| `plugin/MqttClient.qplug` 0.2.0.0 | `ca0cc3fb8a87795746c99219ebcd4acfd0382beeffac1e512a36d6108f27d48d` |
| `module/qsys_mqtt/init.lua` 0.2.0 | `c9b4a0fe0facdcc828ea1602f44871741470b0bfa03aa78f3746c77a64140e38` |
| Designer-saved `MQTT5-Designer-Acceptance.qsys` | `ab498925a9b99632a88ef5a33def85eee5406152f56bdda5f7c7822139501dd4` |

Read-only structural inspection independently confirmed that the saved design
contains the final plugin source hash. That structural report deliberately does
not infer application acceptance; the native observations above supply it.
The fixture and inspection receipt remain under the ignored local validation
folder. Installed 0.1.1 files were backed up outside the Plugins catalog.

Core/TLS, advanced MQTT 5 features listed in README, and the wider application
checks listed above remain pending. Earlier 0.1.1 observations are not implicitly
relabelled as 0.2.0 acceptance. No physical Core was deployed to.

## Shared PEM files and mutual TLS, version 0.3.0, 2026-10-12

The owner requested shared PEM-file configuration and mutual TLS, with local
broker and Designer testing. Module 0.3.0 / plugin 0.3.0.0 retain the existing
plugin identity and prior controls. A final Certificates page adds shared CA,
client certificate and private-key paths; only paths/toggles are saved. The
module additionally permits direct PEM strings. Neither path accesses or
synchronizes Core Manager's certificate store.

| Official source / classification | Implementation | Verification / boundary |
| --- | --- | --- |
| [TcpSocket](https://help.qsys.com/Content/Control_Scripting/Using_Lua_in_Q-Sys/TcpSocket.htm), TLS property API; assignment order shown in example | `client.lua`: optional ClientCertData, ClientKeyData, then CACertData and ValidateCertificate=true before Connect | Native Designer good/unrelated CA comparison below; no documented ordering requirement or internal setter behavior is inferred |
| [10.2 release notes](https://help.qsys.com/q-sys_10.2/Content/Q-Sys_Designer/QDS_Release_Notes.htm), versioned feature announcement | Target remains 10.5; explicit per-socket trust | 10.2 introduced server-certificate validation against trusted CAs; older Help caveats about absent validation are not current guidance |
| [QSC file reading](https://support.qsys.com/application-notes/how-to-read-files-using-scripting) and [JSON file example](https://help.qsys.com/DeveloperHelp/Content/Code_Examples/JSON_Example.htm), documented roots and example/emulation limitation | `tls.lua`: protected binary open/read/close, media/design relative paths, 128 KiB limit, PEM envelope screening, paired identity, reload on each attempt | 13 deterministic groups cover rotation/deletion/read/close failures, redaction and cleanup; Core filesystem deployment remains untested |
| Reserved Functions and [status values](https://help.qsys.com/Content/Control_Scripting/status_overview.htm), API contracts | New declared controls and stable page mapping; Connecting=Initializing (5), local credential/setup errors=Fault (2) | All 52 channel/page combinations checked; native Certificates page and two-line error rendered |
| Plugin Debug / Pcall, recommendations | Fixed error codes; no PEM/key/path/native file error in logs | Malformed/missing/oversized/read/close cases and runtime logging checks; successful file reads deliberately have no trace |

Final source checks passed: 47 existing groups, all 52 layout combinations,
19 MQTT 5 groups, 13 TLS groups, reproducible build, StyLua formatting/AST
verification, and LuaLS Information-level analysis (zero problems in four files).
The new real-broker suite uses disposable seven-day PKI and Mosquitto 2.0.22 on
loopback. Both MQTT versions passed file-backed mTLS CONNECT/QoS1 binary
roundtrip and rejected wrong CA, missing/untrusted client certificate,
mismatched key and wrong hostname. Its TLS transport is Python OpenSSL with
verification enabled, so its hostname result is not a native Q-SYS claim.

Independent fresh-context SDK review retrieved applicable official contracts,
examined source and all old/new page mappings, and exercised additional cleanup,
setter failure, shared-file and status cases. The reviewer identified incorrect
local-error/connecting status codes; the fixes were independently verified.
Final source review then passed 13 TLS groups and an in-memory old-order mutation:
the conservative TLS setter-reset model accepts final code and rejects the
earlier ordering for server-only TLS and mTLS. No scoped source findings remain.
The reviewer did not perform GUI or physical Core tests.

### Designer observations

Q-SYS Designer **10.5.0**, native Lua/TcpSocket/Timer emulation, with a separate
local **Mosquitto 2.0.22 TLS listener at 127.0.0.1:18886**, requiring a trusted
client certificate and mapping its Common Name to the broker username:

- The native file-I/O probe returned `invalid path` for the media-relative path
  and an existing absolute Windows path. QSC's cited JSON file example explicitly
  does not work in emulation. Shared-file access on a Core is therefore pending.
- To isolate native TLS, a local diagnostic copy provided seven-day synthetic
  PEM strings through an `io.open` adapter. The MQTT engine, native TLS socket,
  timers and UI remained real; the adapter and test credentials are absent from
  distributable source and the final clean settings fixture.
- MQTT 5 connected with the expected client identity `qsys-mqtt-test-client`.
  UI QoS1 publish delivered `hello-from-designer` to an independent authenticated
  Paho subscriber. Retained inbound `native-mutual-tls-receive` appeared in the
  plugin with Text format and increasing count; broker ACKs and the visible
  `OK: broker-acknowledged` result were observed. This passed again after the
  final TLS assignment correction.
- Disabling the client identity failed against the requiring broker; Mosquitto
  reported that the peer did not return a certificate. This particular test used
  the first diagnostic build, before the assignment-order correction.
- Native testing exposed an unsafe earlier ordering: enabling validation before
  assigning the CA/client identity allowed an unrelated CA to connect. The final
  order follows the official example: client certificate, key, CA, validation.
  A fresh diagnostic instance confirmed that the actual unrelated CA reached
  the socket, its CA readback matched, and validation read back true (booleans
  only; no PEM logged). Connection then failed, and Mosquitto reported TLS
  `unknown ca`. Changing the UI path to the real CA, committing with Return and
  applying/reconnecting produced a successful connection. This establishes the
  specific comparison, not native setter internals or full TLS conformance.
- The clean production-source fixture opened/compiled, retained Use TLS,
  Use CA file and Use client certificate plus all three paths, and displayed
  red Fault `Reconnecting: ca-file-open-failed` without opening a fallback socket.
  Designer saved that fixture and it was reopened in a fresh process for the
  final persistence check. Source inspection confirmed the final plugin hash,
  the three paths and absence of disposable private-key fragments or adapter.

Shared-file deployment/reload on a Core, native hostname/SNI, expired certificates,
revocation and wider TLS cases remain unaccepted. Native MQTT 3.1.1 mTLS and
0.3 external-module require/traffic were not separately probed; the automated
suite covers both protocols and both packages share the same engine. Previous
version observations remain scoped to their sections above.

| Artifact | SHA-256 |
| --- | --- |
| Final plugin 0.3.0.0 | `c08873cd7031a93146a1842560192f03cbd6fcc3825a34e0c62aa2e11ebc8921` |
| Final module 0.3.0 | `cd5db6c496da3c07989c688885742ecc607ccedb4951b07198dddbae7b4cf8f1` |
| Native ordering diagnostic plugin (local only) | `175244a82514f2499a3c17881d692b55712783894dbdf09ceb80c47e4b930352` |
| Designer-saved clean `MQTT-TLS-Settings-Acceptance.qsys` | `86a14c7cd93b5d96016363edd1e7eb5eae7c9ef68a42d6b586a860ce7c0bff1c` |

The ordering diagnostic's executable transport matches the final candidate;
the final authored source adds an explanatory comment. Local fixtures/PKI and
receipts remain excluded from Git under `.local/mqtt-tls-validation-20261012/`.
Original 0.1.1 and 0.2 accepted fixtures remain hash-preserved. At this milestone,
the installed catalog plugin was independently restyled to 0.2.0.1; its hash guard
prevented replacement. The TLS candidate was initially packaged separately,
preserving that styling work. The owner subsequently authorized combining them;
the following section supersedes that installation status.

## Combined styling and TLS, plugin 0.3.0.1, 2026-10-12

The owner authorized combining the independently installed 0.2.0.1 presentation
with 0.3.0 TLS. The integration preserves that supplied SVG, purple schematic
color, explicit green confirmation LEDs, native button styling, Setup/Channel
titles and failure-status mapping. It extends the same composition to the new
Certificates page. The module/transport engine is byte-identical to 0.3.0.
Source styling was taken from commit `8a984331178a3e9ddc738d0e8a22e5eab858e232`;
no unrelated plugin or house-guide changes were imported.

Independent fresh-context SDK and house-style review retrieved applicable
official contracts and mapped them to metadata/runtime separation, declared
properties and controls, ordered pages, embedded secret storage, explicit
stacking, socket/timer lifecycle, protected errors and metadata-only debugging.
The reviewer verified the exact supplied SVG and the current geometry stated
above: 400x100 logo header, title at (7,106), fields at x=180 with width 200,
labels at x=15 with width 155, Setup panels at y=130/570, channel panels at
y=130/325, Certificates panels at y=130/250, and native footer/button treatment.
TLS ordering and the five certificate controls remain intact. No blocking source
finding remains. This does not resolve the native trust-replacement failure below.

Validation passed: 47 regression groups including all 52 page/channel layouts,
19 MQTT 5 groups, 13 TLS groups, LuaLS Information-level checks (zero problems in
four authored files), StyLua Lua 5.3 AST/format verification (two-space indent,
100 columns), and generated-build consistency. The unchanged engine retains the
version 0.3.0 simulated-host real-broker evidence above; it is not presented as
a new native Core test. The combined reviewer inspected these tests and ran an
additional mocked CA-change lifecycle probe rather than independently rerunning
the complete builder suite.

### Combined Designer observations

Builder-performed tests used Designer 10.5.0 and the existing loopback Mosquitto
2.0.22 mTLS listener at 127.0.0.1:18886:

- Setup, Channel 1, Channel 2 and Certificates rendered with the supplied logo,
  matching titles, native groups and version 0.3.0.1 footer. The diagnostic showed
  green Connected/Subscribed/ReceivedValid indicators and green accepted status;
  the clean fixture showed red Fault for an unreadable CA file. All channel counts
  and dragged controls over a dark background were not visually exercised.
- A separate local diagnostic used an `io.open` adapter for disposable synthetic
  PEM data because the tested certificate-file reads failed in emulation. Native MQTT 5
  mutual TLS connected and received retained `native-mutual-tls-receive`; UI QoS1
  publish reported `OK: broker-acknowledged`, and an independent authenticated
  Paho peer received `hello-from-designer` on `qsys/test/outgoing`.
- The clean production-source fixture compiled and reported
  `Fault - Reconnecting: ca-file-open-failed`. After save and reopen in a fresh
  process, Setup settings, MQTT 5 and both certificate switches/three paths
  persisted. The password field remained masked; this run did not verify the
  underlying secret value. The updated external module was embedded without
  another changed-module prompt. Emulation compiled again and reported the same
  fixed file-read error. The final window was left stopped on Certificates.
- Read-only inspection found the final embedded plugin hash, all three complete
  paths and no diagnostic adapter. It scanned 150 body fragments from the actual
  disposable test private keys and found none. The fixture retains its earlier
  cached panel-caption text `MQTT Client 0.2.0.0` and gray schematic fill from the
  offline source update; the runtime banner/footer and embedded source are 0.3.0.1.
  Those cached fixture properties are not evidence of a catalog insertion check.

### Open native trust-replacement failure

On the final transport ordering, changing a correct CA to an unrelated CA via
the Certificates UI, committing with Return and applying/reconnecting unexpectedly
connected. A fresh diagnostic process starting with the unrelated CA instead
failed repeatedly with `socket-error`. Changing that process to the correct CA
connected; changing back to the unrelated CA connected again. On the latter
attempt at 2026-10-12 14:33:13 UTC, non-secret booleans confirmed that the unrelated
CA was supplied, its socket readback matched the input, and ValidateCertificate
read back true before the accepted connection.

The reviewer traced and mocked correct/wrong/correct/wrong UI changes: each Apply
disposed the prior client and timers, loaded the current PEM, created a fresh
socket and set validation true. No plugin-side stale-option or PEM fallback was
found. The cause of the native behavior is unresolved; session reuse, trust
accumulation or other native mechanisms are hypotheses, not established facts.
Do not rely on Apply / reconnect to remove a previously trusted CA. Fresh-start
rejection is narrower evidence, and no Core restart/rotation procedure has been
validated. This is an acceptance blocker for production TLS use, shared by both
packages' common native transport.

The installed plugin and external module were replaced only after hash-verified
backups outside the Plugins catalog. The prior styled plugin/module remain in
`Plugin Candidates/MQTT-backup-0.2.0.1-before-0.3.0.1`. The combined package and
clean saved fixture are in `Plugin Candidates/MQTT-TLS-0.3.0.1`; diagnostics/PKI
are excluded. The local broker remains available for the owner's further tests.

| Artifact | SHA-256 |
| --- | --- |
| Installed/final plugin 0.3.0.1 | `18182ccc28363e7850e6ff9d25408118df8dfd6ad8a135303dbe06f222b2f149` |
| Installed/final module 0.3.0 | `cd5db6c496da3c07989c688885742ecc607ccedb4951b07198dddbae7b4cf8f1` |
| Designer-saved clean `MQTT-Combined-Acceptance.qsys` | `1a2268fe70ba742819b6f5d727bdc842a45ed1b12b17458bdb6c13885a7a2450` |
| Native combined diagnostic plugin, local only | `defc3660ad3778d74972ce59ecec929aa94e7f402ea201185996aa4a6d681206` |
| CA readback diagnostic plugin, local only | `ff3b2e661253703d60831c76e8ef47d4045e3c12dd2e19821f43be24b984444e` |

Core file provisioning/reload, native hostname/SNI/expiry/revocation and the other
versioned acceptance gaps remain open in issue 35. No physical Core was deployed
to, and no production or Q-SYS Library acceptance is claimed.

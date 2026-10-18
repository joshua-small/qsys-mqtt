# MQTT Client for Q-SYS

Plugin and package version **0.3.1.1**. A self-contained MQTT 3.1.1/5.0 client with publish/subscribe, QoS 0/1, retained messages, Last Will and 1–8 paired channels. No separately installed Lua module is required.

**CA changes require Save to Core & Run.** This version stops connection attempts when its loaded CA changes and displays **CA changed: Save to Core & Run required**. It is an interim guard for Q-SYS 10.5.0 native TLS trust retention, not a complete runtime fix. For emulation, exit and relaunch Designer; stopping emulation or reloading Lua is insufficient.

Physical Core acceptance remains open. Other Lua environments can still add native trust, and a Lua-only restart loses this module's guard while native trust can persist. Coordinate CA changes across the design. See the [open issue](https://github.com/joshua-small/qsys-mqtt/issues/1).

## Install with Q-SYS Library

1. Sign in to [Q-SYS Library](https://library.qsys.com/my-library).
2. Open **My Packages → Add Personal Package**.
3. Enter **MQTT Client (CA restart required)** and this package URL:

   ```text
   https://joshua-small.github.io/qsys-mqtt/registration/joshuasmall.qsys.mqttclient/index.json
   ```

4. In Designer, sign in with the same QSC ID and open **Tools → Show Asset Installer**.
5. Refresh **Available Assets**, select the package and install it.

For manual installation, download `MqttClient.qplug` from [Releases](https://github.com/joshua-small/qsys-mqtt/releases) and place only that file in your Documents folder under `QSC/Q-Sys Designer/Plugins`. Keep backups and support files outside Plugins. Use one installation method to avoid duplicate copies. Refreshing/installing a package does not deploy changes to a Core; update and test the design before **Save to Core & Run**.

## Configure

1. Add **Utilities > MQTT Client** to a test design. Set **Channels** (1–8) and **MQTT Version** (3.1.1 or 5.0) in Properties before running.
2. On Setup, enter the broker address, explicit port, unique client ID and authentication if required. Typical ports are 1883 for TCP and 8883 for TLS.
3. Set subscribe filters and requested QoS on Channel pages. A blank filter disables that subscription.
4. Enable the connection. Use **Apply / reconnect** for ordinary configuration/filter changes. Deploy CA changes with **Save to Core & Run**.
5. Enter a publish topic/payload and trigger **Publish message**. QoS 0 feedback means a socket write; QoS 1 success means broker PUBACK, not subscriber execution.

Incoming ASCII payloads appear as text; other bytes appear as hex. Incoming and outgoing UI payloads are bounded at 2048 bytes; incoming truncation is marked. Message event fires for repeated and empty messages. Received value valid clears on disconnect.

## TLS and certificates

TLS requires an explicit PEM CA with validation enabled. Paste the CA or configure a shared CA file on Certificates. Mutual TLS additionally requires a paired client certificate and unencrypted private key. Prefer separate files beneath `media/TLS_Certificates/` on the Core. Provision and protect them separately: the plugin stores file paths, not loaded private-key contents. Saved passwords are masked, not encrypted in the design.

The first complete credential load pins its CA bytes before native socket setup. A later change, including a file change at the same path, latches the restart requirement and stops retries before creating another socket. Apply, enable toggles, replacing the MQTT client and reverting the file do not clear the latch within that loaded module. Already-connected clients are not immediately revoked; the check occurs on connection attempts. Client certificate/key renewal with unchanged CA remains allowed. Multiple clients sharing the same external module must use the same CA.

Certificate file access in Designer emulation, physical Core acceptance, and native certificate-chain/hostname/SNI behavior remain open.

## Scope and support

Targets Q-SYS Designer/Core 10.5. Clean sessions only; reconnect restores subscriptions but never replays publishes. QoS 2, persistent sessions, offline queues, shared subscriptions, topic aliases and enhanced authentication are unsupported. MQTT 5 implements a bounded profile, not full conformance.

The packet codecs are unmodified MIT-licensed [luamqtt 3.5.0](https://github.com/xHasKx/luamqtt/tree/14ad9be4c327972be68726d3c796c781eb4cc542); attribution is embedded in the plugin and included in LICENSE-luamqtt.

Report bugs through [Issues](https://github.com/joshua-small/qsys-mqtt/issues), including plugin/Q-SYS versions, device/broker model and reproduction steps. Remove credentials from shared logs and designs.

This is an independent personal development package, not a Q-SYS Verified Asset or manufacturer-endorsed release. Existing source attribution is retained.

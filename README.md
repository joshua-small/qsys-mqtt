# MQTT Client (TLS fix pending) for Q-SYS

A self-contained Q-SYS MQTT client with MQTT 3.1.1/5.0, publish/subscribe, QoS 0/1, retained messages, Last Will and 1-8 paired channels. The plugin does not require a separately installed Lua module.

Plugin and package version: **0.3.0.1**.

**Development candidate — TLS CA replacement fix pending.** See the TLS limitation below before use.

## Install with Q-SYS Library

1. Sign in to [Q-SYS Library](https://library.qsys.com/my-library).
2. Open **My Packages → Add Personal Package**.
3. Enter **MQTT Client (TLS fix pending)** and this package URL:

   ```text
   https://joshua-small.github.io/qsys-mqtt/registration/joshuasmall.qsys.mqttclient/index.json
   ```

4. In Designer, sign in with the same QSC ID and open **Tools → Show Asset Installer**.
5. Refresh **Available Assets**, select the package and install it.

For manual installation, download `MqttClient.qplug` from [Releases](https://github.com/joshua-small/qsys-mqtt/releases) and place only that file in your Documents folder under `QSC/Q-Sys Designer/Plugins`. Keep backups and support files outside Plugins. Use one installation method to avoid duplicate copies. Refreshing/installing a package does not deploy changes to a Core; update and test the design before **Save to Core & Run**.

**TLS fix pending:** after a working CA certificate was replaced with an unrelated CA, Designer 10.5 could reconnect unexpectedly. Do not rely on Apply / reconnect to revoke a previously trusted CA. This development package preserves that known issue; publishing it does not fix or validate TLS trust replacement. Use plain TCP only on a network where unencrypted MQTT is appropriate. Track the fix in this repository's Issues.

New native TLS sockets accepted the server while configured with an unrelated CA during full, non-resumed TLS handshakes. Physical Core acceptance remains open. No supported plugin-level trust reset has been established; [issue 1](https://github.com/joshua-small/qsys-mqtt/issues/1) remains open.

## Configure

1. Add **Utilities > MQTT Client** to a test design. Set **Channels** (1-8) and **MQTT Version** (3.1.1 by default, or 5.0) in Properties before running.
2. On Setup, enter the broker address, explicit port and unique client ID. Typical ports are 1883 for TCP and 8883 for TLS. Enter authentication if required.
3. Set subscribe filters and requested QoS on the Channel pages. A blank filter disables that subscription.
4. Enable the connection. Use **Apply / reconnect** after changing configuration or filters.
5. Enter a publish topic and payload, then trigger **Publish message**. QoS 0 feedback means a socket write; QoS 1 success means broker PUBACK, not subscriber execution.

Incoming ASCII payloads appear as text; other bytes appear as hex. The UI retains up to 2048 incoming bytes and marks truncation. Outgoing UI payloads are limited to 2048 bytes. Message event fires for repeated and empty messages. Received value valid clears on disconnect.

## TLS and credentials

TLS requires an explicit PEM CA; there is no verification bypass. Paste a CA or configure a shared CA file on Certificates. Mutual TLS additionally requires a client certificate and unencrypted private key. Prefer separate files beneath `media/TLS_Certificates/` on the Core. Provision and protect these files separately; the plugin stores paths rather than loaded key contents. Certificate file access in Designer emulation is not validated. This store is independent of Core Manager's certificate settings.

Files are reread on connection attempts, but that does not establish removal of native cached trust. CA rotation, native hostname/chain/SNI behavior and Core file-backed credentials need acceptance after the TLS fix. Saved passwords are masked in the UI, not encrypted in the design.

## Scope

Targets Q-SYS Designer/Core 10.5. Clean sessions only; reconnect restores subscriptions but never replays publishes. QoS 2, persistent sessions, offline queues, shared subscriptions, topic aliases and enhanced authentication are unsupported. MQTT 5 implements a bounded feature set, not full MQTT 5 conformance.

Local Designer tests demonstrated MQTT 5 and mutual TLS connection/traffic with the recorded trust-replacement failure. Core hardware acceptance remains open. The unmodified MQTT packet codecs come from MIT-licensed [luamqtt 3.5.0](https://github.com/xHasKx/luamqtt/tree/14ad9be4c327972be68726d3c796c781eb4cc542); its copyright and permission notice are embedded in the plugin and included as LICENSE-luamqtt.

## Support

Report bugs through [Issues](https://github.com/joshua-small/qsys-mqtt/issues), including plugin version, Q-SYS version, device/broker model and firmware, and reproduction steps. Remove credentials from logs and design files before sharing them.

This is an independent personal package, not a Q-SYS Verified Asset or a manufacturer-endorsed release. Manufacturer names and logos identify compatible products. Existing source attribution is retained.

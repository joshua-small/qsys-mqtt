"""Loopback-only disposable native TLS experiment, not an MQTT broker."""
import asyncio
import json
import ssl
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("work", type=Path, help="Disposable output directory from make_probe.py")
ROOT = parser.parse_args().work.resolve()
PKI = ROOT / "pki"

def record(**entry):
    line = json.dumps(entry, sort_keys=True)
    print(line, flush=True)
    with (ROOT / "native-results.jsonl").open("a") as output:
        output.write(line + "\n")

async def tls_peer(reader, writer):
    sock = writer.get_extra_info("ssl_object")
    peer = sock.getpeercert()
    record(kind="handshake", port=writer.get_extra_info("sockname")[1],
           protocol=sock.version(), session_reused=sock.session_reused,
           client_subject=peer.get("subject") if peer else None)
    try:
        data = await asyncio.wait_for(reader.readline(), 5)
        record(kind="payload", port=writer.get_extra_info("sockname")[1],
               label=data.decode("ascii", errors="replace").strip())
        writer.write(b"ACK " + data)
        await writer.drain()
    except (TimeoutError, ConnectionError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except ConnectionError:
            pass

async def reports(reader, writer):
    while data := await reader.readline():
        record(kind="native", message=data.decode("utf-8", errors="replace").strip())
    writer.close()

def context(identity, mutual=False):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(PKI / (identity + ".pem"), PKI / (identity + ".key"))
    ctx.options |= ssl.OP_NO_TICKET
    ctx.num_tickets = 0
    if mutual:
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(PKI / "ca.pem")
    ctx.set_servername_callback(lambda socket, name, initial: record(kind="sni", name=name))
    return ctx

async def main():
    servers = [await asyncio.start_server(reports, "127.0.0.1", 18990)]
    for port, identity, mutual in [(18991,"server",False),(18992,"server",False),
                                    (18993,"wrong-ca",False),(18994,"server",True)]:
        servers.append(await asyncio.start_server(tls_peer, "127.0.0.1", port,
                                                  ssl=context(identity, mutual)))
    record(kind="ready", ports=[18990,18991,18992,18993,18994], tickets=False)
    await asyncio.gather(*(server.serve_forever() for server in servers))

asyncio.run(main())

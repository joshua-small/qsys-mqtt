"""Disposable localhost-only PKI for MQTT tests; never use these identities in production."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import ipaddress
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

def create_pki(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    if any(directory.iterdir()): raise ValueError("PKI output must be empty")
    now=datetime.now(timezone.utc)
    def issue(name,issuer=None,server=False):
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
        builder=(x509.CertificateBuilder().subject_name(subject)
            .issuer_name(issuer[1].subject if issuer else subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1))
            .not_valid_after(now+timedelta(days=7))
            .add_extension(x509.BasicConstraints(ca=issuer is None,path_length=0 if issuer is None else None),critical=True))
        builder=builder.add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()),critical=False)
        builder=builder.add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key((issuer[0] if issuer else key).public_key()),critical=False)
        if issuer:
            builder=builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
            if server:
                builder=builder.add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),critical=False)
        else:
            builder=builder.add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=False,content_commitment=False,data_encipherment=False,key_agreement=False,key_cert_sign=True,crl_sign=True,encipher_only=None,decipher_only=None),critical=True)
        cert=builder.sign(issuer[0] if issuer else key,hashes.SHA256())
        return key,cert
    ca=issue("MQTT local test CA")
    wrong=issue("MQTT unrelated test CA")
    pairs={"ca":ca,"wrong-ca":wrong,"server":issue("localhost",ca,True),
      "client":issue("qsys-mqtt-test-client",ca),"client-renewed":issue("qsys-mqtt-renewed",ca),
      "untrusted-client":issue("qsys-untrusted-client",wrong)}
    for name,(key,cert) in pairs.items():
        path=directory/(name+".key")
        path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        path.chmod(0o600)
        (directory/(name+".pem")).write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return directory

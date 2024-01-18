from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.backends import default_backend
import datetime

# Generate private key
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

timestamp = datetime.datetime.now(datetime.UTC)

# Create a self-signed certificate
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Organization"),
    x509.NameAttribute(NameOID.COMMON_NAME, u"mydomain.com"),
])
certificate = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    private_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.now(timestamp)
).not_valid_after(
    # Certificate valid for 10 year
    timestamp + datetime.timedelta(days=30)
).add_extension(
    x509.BasicConstraints(ca=True, path_length=None), critical=True,
).sign(private_key, hashes.SHA256(), default_backend())

# Write private key to file
with open(f"./config/private_key-{timestamp}.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=NoEncryption()
    ))

# Write certificate to file
with open(f"./config/certificate-{timestamp}.pem", "wb") as f:
    f.write(certificate.public_bytes(Encoding.PEM))

# TODO: generalize this for use with our ArangoDB set-up and installing the
# certificate on the local machine.  This is platform specific.

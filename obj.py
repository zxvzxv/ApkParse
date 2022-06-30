

class ApkInfo:
    name = ''
    version = ''
    package = ''
    cert = None
    main_activity = ''
    services = None
    receivers = None
    providers = None
    activitise = None

    def __init__(self, apk_path) -> None:
        self.apk_path = apk_path


class Cert:
    issuer = ''
    subject = ''
    md5 = ''
    sha1 = ''
    sha256 = ''




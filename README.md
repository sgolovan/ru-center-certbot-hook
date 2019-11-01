[//]: # "Copyright (c) 2018 Sergei Golovan"
[//]: # ""
[//]: # "# See the file LICENSE for information on usage and redistribution"
[//]: # "of this file, and for a DISCLAIMER OF ALL WARRANTIES."

# Certbot Hook for DNS ACME Challenge for RU-CENTER DNS-Master API

This script is intended to be used as a [Certbot](https://certbot.eff.org/) hook
to automatically create `_acme-challenge.` TXT DNS records for domain ownership
proof, and to cleanup them after finishing the verification procedure.

It uses the [RU-CENTER](https://www.nic.ru) API for updating DNS zones, so
it works only if you host your primary DNS server at RU-CENTER.

The script commits changes to the DNS zones, so it might cause data loss if
it's executed during some other manipulations with them.

## System requirements

* Python 3
* requests
* lxml
* dnspython

## Usage

1. Register an application at RU-CENTER.
2. Copy the sample config `config.py.sample` into `config.py`, fill in your
   application ID, secret, and RU-CENTER admin username and password.
3. Start `certbot` with the manual plugin and specify the script for its hooks:

        certbot  certonly --manual --preferred-challenges=dns --manual-auth-hook /path/to/ru-center-certbot-auth-hook --manual-cleanup-hook /path/to/ru-center-certbot-cleanup-hook --manual-public-ip-logging-ok -d secure.example.org

## Links

RU-CENTER DNS-Master API: <https://www.nic.ru/help/upload/file/API_DNS-hosting-en.pdf>

RU-CENTER Application regisration: <https://www.nic.ru/en/manager/oauth.cgi>

## Acknowledgements

The code is based on RU-CENTER DNS-Master backup script <https://github.com/m-messiah/ru-center-backup>
by Maxim Muzafarov.

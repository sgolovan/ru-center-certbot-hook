#!/usr/bin/python3
# coding=utf-8
import xml.etree.ElementTree as Xml
from os import environ, path
from sys import stderr, argv
from io import BytesIO
import lxml.builder    
from base64 import b64encode
from requests import get, post, put, delete
import time

def die(message, code=1):
    stderr.write(message + "\n")
    exit(code)

class RuCenterApi(object):
    def __init__(self, appid, appsecret, user, password):
        try:
            self.url = "https://api.nic.ru/dns-master/"
            key = b64encode(bytearray(appid + ":" + appsecret, 'utf-8')).decode('utf-8')
            token = post(
                "https://api.nic.ru/oauth/token",
                headers={'Authorization': "Basic %s" % key},
                data={'grant_type': 'password',
                      'username': user,
                      'password': password,
                      'scope': '(GET|PUT|POST|DELETE):/dns-master/.+'
                }
            )
            self.token = token.json()['access_token']
            self.zone = None
        except:
            die("Can't fetch token")

    def iter_zones(self):
        try:
            resp = get(self.url + 'zones',
                       headers={'Authorization': "Bearer %s" % self.token})
            data = Xml.fromstring(resp.content).find('data')
            for z in data.findall('zone'):
                if z.get('has-primary') == 'true':
                    yield z.get('service'), z.get('name')
        except GeneratorExit:
            pass
        except:
            die("Can't list zones", code=2)

    def set_zone(self, domain):
        domainList = domain.split(".")
        for zone in self.iter_zones():
            zoneList = zone[1].split(".")
            for i in range(len(domainList)):
                if zoneList == domainList[i:]:
                    self.zone = zone
                    return zone
        die("Can't find zone for domain %s" % domain, code=2)

    def fetch_zone(self):
        if self.zone == None:
            die("Zone isn't set")
        try:
            resp = get(self.url + 'services/%s/zones/%s' % self.zone,
                       headers={'Authorization': "Bearer %s" % self.token})
            if resp.status_code != 200:
                raise Exception
            return resp.text.replace("\r\n", "\n") + "\n"
        except:
            die("Can't fetch zone %s" % self.zone[0], code=3)

    def add_txt_record(self, domain, data):
        if self.zone == None:
            die("Zone isn't set")
        try:
            E = lxml.builder.ElementMaker()
            Xbody = Xml.ElementTree(
                      E("request",
                        E("rr-list",
                          E("rr",
                            E("name", domain),
                            E("type", "TXT"),
                            E("txt",
                              E("string", data))))))
            body = BytesIO()
            Xbody.write(body, encoding="UTF-8", xml_declaration=True)
            resp = put(self.url + 'services/%s/zones/%s/records' % self.zone,
                       headers={'Authorization': "Bearer %s" % self.token},
                       data=body.getvalue())
            body.close()
            if resp.status_code != 200:
                raise Exception
            return Xml.fromstring(resp.content).find('.//rr').get('id')
        except:
            die("Can't update record in zone %s" % self.zone[0], code=3)

    def list_records(self):
        if self.zone == None:
            die("Zone isn't set")
        try:
            resp = get(self.url + 'services/%s/zones/%s/records' % self.zone,
                       headers={'Authorization': "Bearer %s" % self.token})
            if resp.status_code != 200:
                raise Exception
            return Xml.fromstring(resp.content).findall('.//rr')
        except:
            die("Can't fetch records from zone %s" % self.zone[0], code=3)

    def delete_record(self, rid):
        if self.zone == None:
            die("Zone isn't set")
        try:
            service, name = self.zone
            resp = delete(self.url + 'services/%s/zones/%s/records/%s' % (service, name, rid),
                       headers={'Authorization': "Bearer %s" % self.token})
            if resp.status_code != 200:
                raise Exception
            return ""
        except:
            die("Can't delete record in zone %s" % self.zone[0], code=3)

    def commit_changes(self):
        if self.zone == None:
            die("Zone isn't set")
        try:
            resp = post(self.url + 'services/%s/zones/%s/commit' % self.zone,
                       headers={'Authorization': "Bearer %s" % self.token})
            if resp.status_code != 200:
                raise Exception
            return ""
        except:
            die("Can't commit changes for zone %s" % self.zone[0], code=3)

if __name__ == '__main__':

    from config import CONFIG

    try:
        uploader = RuCenterApi(CONFIG['RUC_APPID'],
                               CONFIG['RUC_APPSECRET'],
                               CONFIG['RUC_USER'],
                               CONFIG['RUC_PASS'])
    except KeyError:
        die("CONFIG dictionary isn't properly defined", code=1)

    else:
        zone = uploader.set_zone(environ['CERTBOT_DOMAIN'])

        acmeDomain = "_acme-challenge." + environ['CERTBOT_DOMAIN'] + "."
        acmeVal = environ['CERTBOT_VALIDATION']

        if path.basename(argv[0]) == "ru-center-certbot-auth-hook":
            stderr.write("Creating TXT DNS record for %s\n" % acmeDomain)
            rid = uploader.add_txt_record(acmeDomain, acmeVal)
            uploader.commit_changes()

        elif path.basename(argv[0]) == "ru-center-certbot-cleanup-hook":
            records = uploader.list_records()

            for rr in records:
                try:
                    rid = rr.get('id')
                    name = rr.find('name').text
                    data = rr.find('txt').find('string').text
                except:
                    continue

                if (name == acmeDomain or name + "." + zone[1] + "." == acmeDomain) and (data == acmeVal):
                    stderr.write("Deleting TXT DNS record %s for %s\n" % (rid, acmeDomain))
                    uploader.delete_record(rid)
            uploader.commit_changes()
        else:
            die("Call this script as ru-center-certbot-auth-hook or ru-center-certbot-cleanup-hook", code=1)

from poplib import POP3_SSL
from email.parser import Parser
from StringIO import StringIO
from zipfile import ZipFile
import socket

from python_common.email_address import EmailAddress


def connect_to_mailbox():
    if __debug__ and socket.gethostname() == 'JEREMCLA-LUBUNTU':
        mailbox = POP3_SSL("lpul-pop.ad.selinc.com")
        mailbox.user("emailbot")
        mailbox.pass_("C0llectit!")
    else:
        mailbox = POP3_SSL("my.inbox.com")
        mailbox.user("emailbot")
        mailbox.pass_("dvJ-uCphEc")

    return mailbox


def get_next_message(i=0):
    mailbox = connect_to_mailbox()
    if mailbox.stat()[0] > i:
        parser = Parser()
        msg = mailbox.retr(i+1)[1]
        message = parser.parsestr('\n'.join(msg))
        mailbox.quit()
        return message, i+1
    return None, None


def delete_message(i=1):
    mailbox = connect_to_mailbox()
    mailbox.dele(i)
    mailbox.quit()


def get_proxy_lists():
    num_skip = 0
    while True:
        message, message_id = get_next_message(num_skip)
        if message is None:
            break
        if EmailAddress(message['from']).domain != 'pl.hidemyass.com' or message['subject'] != 'ProxyList for Today':
            num_skip += 1
            continue

        # find the zip file and return it
        for part in message.walk():
            content_disposition = part['Content-Disposition']
            if content_disposition and content_disposition.startswith('attachment'):
                content_type = part['Content-Type']
                if content_type and 'zip' in content_type:
                    attachment = part.get_payload().decode('base64')
                    zip_file = ZipFile(StringIO(attachment))
                    yield zip_file
                    break
        delete_message(message_id)  # This assumes that no other program is messing with the inbox.

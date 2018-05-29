
# from email import encoders
# from email.header import Header
# from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr


import logging
logger = logging.getLogger(__name__)

import smtplib
import email

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# from email.mime.text import MIMEText
from email.header import Header

async def sendmail():

    msg = EMailMessage(host='smtp.163.com', user='tjpuapp@163.com', passwd='tjpu8395Analysis')
    msg.set_from('炼题坊 <tjpuapp@163.com>')
    msg.set_to('lyucg@qq.com')
    msg.set_subject('炼题坊注册邮件确认')

    url = 'http://alchemy.29th.cn/verify_email/dfsd4334344'

    msg.set_text(f'''
        炼题坊注册邮件确认
        {url}
    ''')

    msg.set_html(f'''
    <html><body>
    您好，欢迎注册。 
    
    点击链接(<a href="{url}">{url}</a>)进行确认。
    </body></html>
    ''')

    await msg.send()


class EMailMessage:
    
    def __init__(self, host, user, passwd, port=25):
        self._host = host
        self._port = port
        self._user = user
        self._passwd = passwd

        self._from = None
        self._to = None

        self.subject = None
        
        self._html = None
        self._text = None
    
    def set_from(self, text):
        name, addr = parseaddr(text)
        if name:
            self._from = formataddr((Header(name, 'utf-8').encode(), addr))
        else:
            self._from = addr

    def set_to(self, text):
        name, addr = parseaddr(text)
        if name:
            to = formataddr((Header(name, 'utf-8').encode(), addr))
        else:
            to = addr

        self._to_addr = addr
        self._to = to

    def set_subject(self, text):
        self._subject = text

    def set_text(self, text):
        self._text = text
    
    def set_html(self, html):
        self._html = html
    
    async def send(self):
        # 通过后台工作线程发送邮件
        await loop.run_in_executor(None, self._send_threaded)

    def _send_threaded(self):
        msg = MIMEMultipart('alternative')
        msg['From'] = self._from
        msg['To'] = self._to
        msg['Subject'] = Header(self._subject, 'utf-8').encode()

        if self._text:
            msg.attach(MIMEText(self._text, 'plain', 'utf-8'))
        
        if self._html:
            msg.attach(MIMEText(self._html, 'html', 'utf-8'))

        class MySMTP(smtplib.SMTP):
            def _print_debug(self, *args):
                logger.debug(' '.join(list(str(s) for s in args)))

        smtp = MySMTP(self._host, self._port)
        if logger.isEnabledFor(logging.DEBUG):
            smtp.set_debuglevel(1)

        # assert smtp.has_extn("starttls")
        # smtp.ehlo()
        smtp.starttls() # 启用加密通道
        smtp.login(self._user, self._passwd)
        smtp.sendmail(self._from, [self._to_addr], msg.as_string())
        smtp.quit()


def image_attachement(cid, filename=None):
    """
        cid='image1'
        <img src="cid:image1">
    """
    filename = '1.png'
    with open(filename, 'rb') as fp:
        img = MIMEImage(fp.read(), 'png')
        img.add_header('Content-ID', f'<{cid}>')
        if filename:
            img.add_header('Content-Disposition', 'inline', filename=filename)
        return img

import asyncio


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(sendmail())
    finally:
        loop.close()

from enum import Enum
import socket
import re


class SonicServerError(Exception):
    pass


class ChannelError(Exception):
    pass


COMMON_CMDS = [
    'START',
    'PING',
    'HELP',
    'QUIT'
]

ALL_CMDS = {
    # FIXME: unintialized entry isn't needed anymore.
    'UNINITIALIZED': [
        *COMMON_CMDS,
    ],
    'ingest': [
        *COMMON_CMDS,
        # PUSH <collection> <bucket> <object> "<text>" [LANG(<locale>)]?
        'PUSH',
        'POP',     # POP <collection> <bucket> <object> "<text>"
        'COUNT',   # COUNT <collection> [<bucket> [<object>]?]?
        'FLUSHC',  # FLUSHC <collection>
        'FLUSHB',  # FLUSHB <collection> <bucket>
        'FLUSHO',  # FLUSHO <collection> <bucket> <object>
    ],
    'search': [
        *COMMON_CMDS,
        # QUERY <collection> <bucket> "<terms>" [LIMIT(<count>)]? [OFFSET(<count>)]? [LANG(<locale>)]?
        'QUERY',
        'SUGGEST',  # SUGGEST <collection> <bucket> "<word>" [LIMIT(<count>)]?

    ]

}


def quote_text(text):
    if text is None:
        return ""
    return '"' + text.replace('"', '\\"').replace('\r\n', ' ') + '"'


def is_error(response):
    if response.startswith('ERR '):
        return True
    return False


def raise_for_error(response):
    print("checking for error on response : ", response)
    if is_error(response):
        raise SonicServerError(response)
    return response


def _parse_protocol_version(s):
    """STARTED search protocol(1) buffer(20000)"""
    matches = re.findall("protocol\((\w+)\)", s)
    if not matches:
        raise ValueError("{s} doesn't contain protocol(NUMBER)".format(s))
    return matches[0]


def _parse_buffer_size(s):
    """STARTED search protocol(1) buffer(20000)"""
    matches = re.findall("buffer\((\w+)\)", s)
    if not matches:
        raise ValueError("{s} doesn't contain buffer(NUMBER)".format(s))
    return matches[0]


def _get_async_response_id(s):
    "'PENDING gn4RLF8M\n'"
    s = s.strip()
    matches = re.findall("PENDING (\w+)", s)
    if not matches:
        raise ValueError("{s} doesn't contain async response id")
    return matches[0]


INGEST = 'ingest'
SEARCH = 'search'
CONTROL = 'control'


class SonicClient:
    def __init__(self, host, port, password, channel):
        self.host = host
        self.port = port
        self.password = password
        self.channel = channel  # ingest, search, control
        self._socket = None
        self._reader = None
        self._writer = None
        self.bufsize = 0
        self.protocol = 1

    @property
    def address(self):
        return self.host, self.port

    @property
    def socket(self):
        if self._socket is not None:
            return self._socket
        self._socket = socket.create_connection(self.address)
        print("socket created")
        return self._socket

    @property
    def reader(self):
        if self._reader is not None:
            return self._reader
        self._reader = self.socket.makefile('r')
        return self._reader

    @property
    def writer(self):
        if self._writer is not None:
            return self._writer
        self._writer = self.socket.makefile('w')
        return self._writer

    def connect(self):
        resp = self.reader.readline()
        print(resp)
        if 'CONNECTED' in resp:
            self.connected = True

        resp = self._execute_command("START", self.channel, self.password)
        self.protocol = _parse_protocol_version(resp)
        self.bufsize = _parse_buffer_size(resp)

        return True

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._reader.close()
        self._writer.close()
        self._socket.close()

    def format_command(self, cmd, *args):
        cmd_str = cmd + " "
        cmd_str += " ".join(args)
        cmd_str += "\r\n"  # specs says \n, asonic does \r\n
        return cmd_str

    def _execute_command(self, cmd, *args):
        if cmd not in ALL_CMDS[self.channel]:
            raise ChannelError(
                "command {} isn't allowed in channel {}".format(cmd, self.channel))

        cmd_str = self.format_command(cmd, *args)
        print("sending cmd: >{}<".format(cmd_str))
        self.writer.write(cmd_str)
        self.writer.flush()
        resp = self._get_response()
        return resp

    def _get_response(self):
        return raise_for_error(self.reader.readline())


class CommonCommandsMixin:
    def ping(self):
        return self._execute_command("PING")

    def quit(self):
        return self._execute_command("QUIT")

    # TODO: check help.
    def help(self, *args):
        return self._execute_command("HELP", *args)


class IngestClient(SonicClient, CommonCommandsMixin):
    def __init__(self, host, port, password):
        super().__init__(host, port, password, INGEST)

    def push(self, collection, bucket, object, text, lang=None):
        lang = "LANG({})".format(lang) if lang else ''
        text = quote_text(text)
        return self._execute_command("PUSH", collection, bucket, object, text, lang)

    def pop(self, collection, bucket, object, text):
        text = quote_text(text)
        return self._execute_command("POP", collection, bucket, object, text)

    def count(self, collection, bucket=None, object=None):
        bucket = bucket or ''
        object = object or ''
        return self._execute_command('COUNT', collection, bucket, object)

    def flush_collection(self, collection):
        return self._execute_command('FLUSHC', collection)

    def flush_bucket(self, collection, bucket):
        return self._execute_command('FLUSHB', collection, bucket)

    def flush_object(self, collection, bucket, object):
        return self._execute_command('FLUSHO', collection, bucket, object)

    def flush(self, collection, bucket=None, object=None):
        if not bucket and not object:
            return self.flush_collection(collection)
        elif bucket and not object:
            return self.flush_bucket(collection, bucket)
        elif object and bucket:
            return self.flush_object(collection, bucket, object)


class SearchClient(SonicClient, CommonCommandsMixin):
    def __init__(self, host, port, password):
        super().__init__(host, port, password, SEARCH)

    def query(self, collection, bucket, terms, limit=None, offset=None, lang=None):
        limit = "LIMIT({})".format(limit) if limit else ''
        lang = "LANG({})".format(lang) if lang else ''
        offset = "OFFSET({})".format(offset) if offset else ''

        terms = quote_text(terms)
        resp_query_id = self._execute_command(
            'QUERY', collection, bucket, terms, limit, offset, lang)
        query_id = resp_query_id.split()[-1]
        resp_result = self.reader.readline()
        resp_result.strip()
        print(resp_result)
        return resp_result.split()[3:]

    def suggest(self, collection, bucket, word, limit=None):
        limit = "LIMIT({})".format(limit) if limit else ''
        word = quote_text(word)
        resp_query_id = self._execute_command(
            'SUGGEST', collection, bucket, word, limit)
        resp_result = self.reader.readline()
        resp_result.strip()
        print(resp_result)
        return resp_result.split()[3:]


def test_ingest():
    with IngestClient("127.0.0.1", '1491', 'dmdm') as ingestcl:
        print(ingestcl.ping())
        print(ingestcl.protocol)
        print(ingestcl.bufsize)
        ingestcl.push("wiki", "articles", "article-1",
                      "for the love of god hell")
        ingestcl.push("wiki", "articles", "article-2",
                      "for the love of satan heaven")
        ingestcl.push("wiki", "articles", "article-3",
                      "for the love of lorde hello")
        ingestcl.push("wiki", "articles", "article-4",
                      "for the god of loaf helmet")


def test_search():
    with SearchClient("127.0.0.1", '1491', 'dmdm') as querycl:
        print(querycl.ping())
        print(querycl.query("wiki", "articles", "for"))
        print(querycl.query("wiki", "articles", "love"))
        print(querycl.suggest("wiki", "articles", "hell"))


if __name__ == "__main__":
    test_ingest()
    test_search()

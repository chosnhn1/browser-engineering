import socket
import ssl
import tkinter
import tkinter.font
import gzip

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file"]

        # set up port
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443


        if "/" not in url:
            # think always / exists at the end
            url = url + "/"

        # split host and path:
        # i.e. http://example.org/site
        # host: example.org
        # path: /site/
        self.host, url = url.split("/", 1)
        # parse custom port
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
        self.path = "/" + url

    def request(self):
        # "socket"
        s = socket.socket(family=socket.AF_INET,
                          type=socket.SOCK_STREAM,
                          proto=socket.IPPROTO_TCP,
                          )
        
        s.connect((self.host, self.port))
        # add http with TLS (https) support
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
            # it is hard to implement TLS yourself - learn more

        request = f"GET {self.path} HTTP/1.1\r\n"
        request += f"Host: {self.host}\r\n"
        request += f"Connection: close\r\n"
        request += f"User-Agent: browser.py/0.1 (Windows NT 6.1; Win64; x64) \r\n"
        request += f"Accept-Encoding: gzip \r\n"
        request += "\r\n"
        # why use \r\n for new line?:
        # also, why you pass two new lines at the end?: 

        # passing strings with encoding
        # (so you are passing bytes)
        s.send(request.encode("utf8"))

        # let's work with server response
        # response = s.makefile("r", encoding="utf8", newline="\r\n")
        response = s.makefile("rb", newline="\r\n")


        statusline = response.readline().decode("utf-8")
        version, status, explanation = statusline.split(" ", 2)

        # hold response headers
        response_headers = {}
        while True:
            line = response.readline().decode("utf-8")
            # until there are no more headers
            if line == "\r\n": break
            print(line)
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # assert "transfer-encoding" not in response_headers
        # assert "content-encoding" not in response_headers
        # theses headers are about compressing & chunking pages
        if "content-encoding" in response_headers and response_headers["content-encoding"] == "gzip":
            if "transfer-encoding" in response_headers and response_headers["transfer-encoding"] == "chunked":
                compressed_content = b""
                while True:
                    chunk_size = int(response.readline().decode("utf-8"), 16)
                    if chunk_size == 0:
                        break

                    chunk_data = response.read(chunk_size)
                    compressed_content += chunk_data
                    response.readline()
                while True:
                    trailer_line = response.readline()
                    if not trailer_line or trailer_line == b"\r\n":
                        break

            else:
                compressed_content = response.read()

            content = gzip.decompress(compressed_content).decode("utf-8")
            s.close()
        else:
            # read content and close socket
            content = response.read().decode("utf-8")
            s.close()

        return content

def lex(body):
    out = []
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Element(buffer))
            buffer = ""
        else:
            buffer += c
    
    if not in_tag and buffer:
        out.append(Text(buffer))
    
    return out



class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []

    # implement original lex, but with new tree structure
    # rather than list
    def parse(self):
        text = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if text: self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)
                text = ""
            else:
                text += c
        if not in_tag and text:
            self.add_text(text)
        return self.finish()
    
    def add_text(self, text):
        # side-stepping whitespace
        if text.isspace(): return

        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    # self closing tags who don't use close tags
    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]


    def add_tag(self, tag):
        # get extract attributes from tags
        tag, attributes = self.get_attributes(tag)

        # throw out any tags starts with bang: i.e. doctype, comments
        if tag.startswith("!"): return

        # close tag
        if tag.startswith("/"):
            # for edge case (== the very last tag of the doc)
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        
        # self-closing tags
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)

        # open tag
        else:
            # add None for edge case (== document's the very first tag)
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    

    # handle tags' attributes
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                # handle quoted values
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""

            
        return tag, attributes

    

# tree printer
def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


# global variables for Browser
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18


class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []
        for tok in tokens:
            self.token(tok)
        self.flush()

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4
        elif tok.tag == "br":
            self.flush()
        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP
    
    def word(self, word):
        # font = tkinter.font.Font(
        #     size=self.size,
        #     weight=self.weight,
        #     slant=self.style,
        # )
        font = get_font(self.size, self.weight, self.style)
        # self.display_list.append((self.cursor_x, self.cursor_y, word, font))
        w = font.measure(word)
        # if word overflowed from the line: 
        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()

        self.line.append((self.cursor_x, word, font))   # y will computed later
        # give each word a padding
        self.cursor_x += w + font.measure(" ")

    def flush(self):
        if not self.line : return
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = HSTEP
        self.line = []


# global font dictionary for caching
FONTS = {}

def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

# global variable for scrolling
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
            )
        self.canvas.pack()

        # scroll
        self.scroll = 0
        self.window.bind("<Down>", self.scrolldown)
        self.display_list = []

    def draw(self):
        self.canvas.delete("all")
        for x, y, word, font in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + font.metrics("linespace") < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=word, font=font,
                                    # anchor: northwest corner, not center is the anchor
                                    anchor="nw")
    
    # load given URL instance
    def load(self, url):
        body = url.request()
        # parse response body with lex function
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
        self.draw()

    # scroll down
    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()


class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.children = []
        self.parent = parent
        self.attributes = attributes
    
    def __repr__(self):
        return "<" + self.tag + ">"


if __name__ == "__main__":
    import sys
    # get URL from first argument
    # load(URL(sys.argv[1]))

    # Browser().load(URL(sys.argv[1]))
    # tkinter.mainloop()

    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    print_tree(nodes)
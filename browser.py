import socket
import ssl
import tkinter

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

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
        request += "\r\n"
        # why use \r\n for new line?:
        # also, why you pass two new lines at the end?: 

        # passing strings with encoding
        # (so you are passing bytes)
        s.send(request.encode("utf8"))

        # let's work with server response
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        # hold response headers
        response_headers = {}
        while True:
            line = response.readline()
            # until there are no more headers
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # make sure no weirdos in response
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        # theses headers are about compress chunk pages

        # read content and close socket
        content = response.read()
        s.close()

        return content


def lex(body):
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            text += c
    return text

# global variables for Browser
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP

    return display_list

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

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            self.canvas.create_text(x, y - self.scroll, text=c)
    
    # load given URL instance
    def load(self, url):
        body = url.request()
        # parse response body with lex function
        text = lex(body)
        self.display_list = layout(text)
        self.draw()

    # scroll down
    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()
            

if __name__ == "__main__":
    import sys
    # get URL from first argument
    # load(URL(sys.argv[1]))

    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
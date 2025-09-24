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
    
    # get full url
    def resolve(self, url):
        if "://" in url:
            return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)

            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + ":" + str(self.port) + url)
        

    def __str__(self):
        """URL String representation for address rect, etc."""
        port_part = ":" + str(self.port)
        
        # port number hidden when:
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""

        return self.scheme + "://" + self.host + port_part + self.path
    

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
        self.implicit_tags(None)

        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    # self closing tags who don't use close tags
    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]

    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]


    def add_tag(self, tag):
        # get extract attributes from tags
        tag, attributes = self.get_attributes(tag)

        # throw out any tags starts with bang: i.e. doctype, comments
        if tag.startswith("!"): return
        self.implicit_tags(tag)

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
        if not self.unfinished:
            self.implicit_tags(None)

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
    
    # for handling non-finished and omitted tags
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
        
            # omit html
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            
            # omit head
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")

            # omit /head
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break


# tree printer
def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


# global variables for Browser
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]

class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"        
        else:
            return "block"

    # drawing base from tree(get basics from parent)
    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width

        # location set with previous item
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        
        # get block / inline mode and draw accordingly
        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                # remove header from layout tree
                if child.tag == "head":
                    continue

                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.new_line()
            self.recurse(self.node)

        # recursively draw children items
        for child in self.children:
            child.layout()

        self.height = sum([child.height for child in self.children])
        

    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)

    def paint(self):
        cmds = []

        # CSS processing
        bgcolor = self.node.style.get("background-color", "transparent")
        if bgcolor != "transparent":
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
            
        # if self.layout_mode() == "inline":
        #     for x, y, word, font, color in self.display_list:
        #         cmds.append(DrawText(x, y, word, font, color))

        return cmds

    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)

        else:
            if node.tag == "br":
                self.new_line()

            if node.tag == "li":
                self.cursor_x += HSTEP
                self.word(self.node, "· ")
            
            for child in node.children:
                self.recurse(child)
    
    def word(self, node, word):
        weight = node.style["font-weight"]
        style = node.style["font-style"]

        # code below needed for CSS to Tk conversion:
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)

        w = font.measure(word)
        # if word overflowed from the line: 
        if self.cursor_x + w > self.width:
            # self.flush()
            self.new_line()

        # color = node.style["color"]
        # self.line.append((self.cursor_x, word, font, color))   # y will computed later
        # # give each word a padding
        # self.cursor_x += w + font.measure(" ")

        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)

    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)


    # function processing text and new line
    def flush(self):
        # have no line: return
        if not self.line : return

        # get font metrics from line
        metrics = [font.metrics() for x, word, font, color in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font, color))
        self.cursor_x = 0
        self.line = []
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.color = color
        self.bottom = y1 + font.metrics("linespace")
        self.rect = Rect(x1, y1, x1 + font.measure(text), y1 + font.metrics("linespace"))

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor="nw",
            fill=self.color,
        )
    

class DrawRect:
    """from Rect instance and color string, construct Rectangular drawing cmd object.
    """
    def __init__(self, rect, color):
        self.rect = rect
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            # x0, y0, x1, y1
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=0,
            fill=self.color
        )


def paint_tree(layout_object, display_list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.previous = None
        self.children = []

    def layout(self):
        child = BlockLayout(self.node, self, None)

        self.children.append(child)

        self.width = WIDTH - 2 * HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height

    def paint(self):
        return []

# global font dictionary for caching
FONTS = {}

def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]


class CSSParser:
    def __init__(self, s):
        # i is index
        self.s = s
        self.i = 0

    # doing "recursive descent parsing" for LL language here:
    # eg. {background-color: black; }
    # index i will jump whitespace, read words and make key-value pair, got ";" and pass

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing Error")
        return self.s[start:self.i]
    
    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing Error")
        self.i += 1

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.word()
        return prop.casefold(), val

    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                pairs[prop] = val
                self.whitespace()
                self.literal(";")
                self.whitespace()

            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break

        return pairs
    
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None
    
    def selector(self):
        out = TagSelector(self.word().casefold())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out
    
    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))

            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break

        return rules


class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1

    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag
    

class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority

    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node): return True
            node = node.parent
        return False


INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}

def style(node, rules):
    node.style = {}
    # first inheritance
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value

    # add style applied by selector
    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value

    # inline style
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()

        for property, value in pairs.items():
            node.style[property] = value
    
    # calc percentage font size inheritance
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]

        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"

    # inherit color
    if node.style["color"] == "inherit":
        if node.parent:
            parent_font_color = node.parent.style["color"]
        else:
            parent_font_color = INHERITED_PROPERTIES["color"]
        
        node.style["color"] = parent_font_color

    # rgba: pass (support later)
    if node.style["color"].startswith("rgba"):
        if node.parent:
            parent_font_color = node.parent.style["color"]
        else:
            parent_font_color = INHERITED_PROPERTIES["color"]
        
        node.style["color"] = parent_font_color

    # do this recursively
    for child in node.children:
        style(child, rules)
    

# global variable for scrolling
SCROLL_STEP = 100

# Browser Style Sheet
DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()

# simple tree to list of nodes function
def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list

def cascade_priority(rule):
    selector, body = rule
    return selector.priority


class Tab:
    def __init__(self, tab_height):
        # scroll
        self.scroll = 0
        self.display_list = []
        self.url = None
        self.tab_height = tab_height
        self.history = []

    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)
    
    # load given URL instance
    def load(self, url):
        self.history.append(url)
        self.url = url
        # parse response body
        body = url.request()
        self.nodes = HTMLParser(body).parse()

        # load style
        rules = DEFAULT_STYLE_SHEET.copy()

        # load link
        links = [node.attributes["href"] for node in tree_to_list(self.nodes, [])
                if isinstance(node, Element) and node.tag == "link"
                and node.attributes.get("rel") == "stylesheet"
                and "href" in node.attributes]
        
        # get CSS rules from stylesheet link
        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except:
                continue
            rules.extend(CSSParser(body).parse())

        # do styling
        style(self.nodes, sorted(rules, key=cascade_priority))

        # build layout
        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        # build display list with tree and render
        self.display_list = []
        paint_tree(self.document, self.display_list)
        

    # scroll down
    def scrolldown(self):
        max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        

    def scrollup(self):
        # make sure cannot go up beyond document
        if self.scroll - SCROLL_STEP < 0:
            self.scroll = 0
        else:
            self.scroll -= SCROLL_STEP 
        

    def click(self, x, y):
        # click position is relative to Browser window:
        y += self.scroll

        # get clicked objs (can be more than one)
        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height
                ]
        
        if not objs: return
        elt = objs[-1].node

        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elt = elt.parent

    def go_back(self):
        if len(self.history) > 1:
            # code below will not be appropriate when do back multiple times
            # because it will add urls to history
            # self.load(self.history[-2])

            self.history.pop()
            back = self.history.pop()
            self.load(back)

        
class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white",
        )
        self.canvas.pack()
        self.window.bind("<Up>", self.handle_up)
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Return>", self.handle_enter)
        self.window.bind("<Key>", self.handle_key)
        self.chrome = Chrome(self)

    def handle_down(self, e):
        self.active_tab.scrolldown()
        self.draw()

    def handle_up(self, e):
        self.active_tab.scrollup()
        self.draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.chrome.click(e.x, e.y)
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()

    def handle_enter(self, e):
        self.chrome.enter()
        self.draw()

    def handle_key(self, e):
        # only catch key stroke with character (!== modifier keys)
        if len(e.char) == 0: return

        # only catch ASCII range letters
        if not (0x20 <= ord(e.char) < 0x7f): return

        self.chrome.keypress(e.char)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)

        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)

    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
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

# new layout (chapter 7)
class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()

        # layouting sth have nth
        if not self.children:
            self.height = 0
            return

        max_ascent = max([word.font.metrics("ascent") for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent") for word in self.children])

        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self):
        return []
    

class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
    
    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)

        self.width = self.font.measure(self.word)
        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

    def paint(self):
        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]
    
class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def contains_point(self, x, y):
        """Give point x, y is contained in Rect.
        """
        return x >= self.left and x < self.right and y >= self.top and y < self.bottom

    
class Chrome:
    """The browser wrapper
    """
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, "normal", "roman")
        self.font_height = self.font.metrics("linespace")
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2 * self.padding

        # for drawing new tab button:
        plus_width = self.font.measure("+") + 2 * self.padding
        self.newtab_rect = Rect(
            self.padding, self.padding,
            self.padding + plus_width, self.padding + self.font_height
        )

        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + self.font_height + 2 * self.padding
        self.bottom = self.urlbar_bottom

        back_width = self.font.measure("<") + 2 * self.padding
        self.back_rect = Rect(self.padding, self.urlbar_top + self.padding,
                              self.padding + back_width, self.urlbar_bottom - self.padding)
        self.address_rect = Rect(self.back_rect.top + self.padding, self.urlbar_top + self.padding,
                                 WIDTH - self.padding, self.urlbar_bottom - self.padding)
        
        self.focus = None
        self.address_bar = ""
        
        
    # for drawing tab titles
    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right + self.padding
        # get width from "Tab X" is somewhat arbitrary but will work;
        tab_width = self.font.measure("Tab X") + 2 * self.padding
        return Rect(
            tabs_start + tab_width * i, self.tabbar_top,
            tabs_start + tab_width * (i+1), self.tabbar_bottom
        )
    
    def paint(self):
        # set pending painting command list:
        cmds = []

        # 1. drawing a white rectangle behind the chrome
        cmds.append(DrawRect(Rect(0, 0, WIDTH, self.bottom), "white"))
        cmds.append(DrawLine(0, self.bottom, WIDTH, self.bottom, "black", 1))

        # 2. New Tab Button
        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(
            self.newtab_rect.left + self.padding, self.newtab_rect.top, "+", self.font, "black"
        ))
        
        # 3. drawing tabs
        for i, tab in enumerate(self.browser.tabs):

            # 1) tab bounds
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left, 0, bounds.left, bounds.bottom, "black", 1
            ))
            cmds.append(DrawLine(
                bounds.right, 0, bounds.right, bounds.bottom, "black", 1
            ))

            # 2) Tab title
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding,
                f"Tab {i}", self.font, "black"
            ))


            # 3) additional line for active tab
            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom, bounds.left, bounds.bottom, "black", 1
                ))
                cmds.append(DrawLine(
                    bounds.right, bounds.bottom, WIDTH, bounds.bottom, "black", 1
                ))

        # 4. paint back button
        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(self.back_rect.left + self.padding,
                                self.back_rect.top, "<", self.font, "black"))
            
        # 5. paint address rect
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        url = str(self.browser.active_tab.url)
        cmds.append(DrawText(self.address_rect.left + self.padding,
                                self.address_rect.top, url, self.font, "black"))
            
        if self.focus == "address bar":
            # with focus, draw text with `address_bar` value
            cmds.append(DrawText(
                self.address_rect.left + self.padding, self.address_rect.top,
                self.address_bar, self.font, "black"
            ))

            # also draw cursor
            w = self.font.measure(self.address_bar)
            cmds.append(DrawLine(
                self.address_rect.left + self.padding + w,
                self.address_rect.top,
                self.address_rect.left + self.padding + w,
                self.address_rect.bottom,
                "red", 1
            ))

        else:
            # without focus, draw text with active tab url
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                self.address_rect.left + self.padding, self.address_rect.top,
                url, self.font, "black"
            ))
            
        return cmds
    
    def click(self, x, y):
        # initialize focus
        self.focus = None

        # click new tab
        if self.newtab_rect.contains_point(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))

        # click back button
        elif self.back_rect.contains_point(x, y):
            self.browser.active_tab.go_back()

        # click address bar
        elif self.address_rect.contains_point(x, y):
            self.focus = "address bar"
            self.address_bar = ""

        # click tab
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains_point(x, y):
                    self.browser.active_tab = tab
                    break

    # handle other key strokes in chrome
    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char
        
    # handle Enter key stroke in chrome
    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None


    
class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = Rect(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            fill=self.color, width=self.thickness
        )

class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color
        )

if __name__ == "__main__":
    import sys
    # get URL from first argument
    # load(URL(sys.argv[1]))
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()

    # body = URL(sys.argv[1]).request()
    # nodes = HTMLParser(body).parse()
    # print_tree(nodes)
import requests
import re
import os
import shutil
import datetime
from zipfile import ZipFile
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from readability import Document
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, session, request, send_file
from flask_socketio import SocketIO, emit, disconnect
from binascii import hexlify, b2a_qp
# import socketio from app

async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

def get_socketio():
    socketio = SocketIO(app, async_mode=async_mode)
    return socketio

socketio = get_socketio()

# Global variables
manifest = ''
path = Path.cwd()
# epub_path = path / 'epub'
# epub_path.mkdir(exist_ok=True, parents=True)
# url_file = 'urls.txt'


def make_cover(epub_path, epub_datas, epub_pub):
    title = epub_datas[1]
    description = epub_datas[2]
    author = epub_datas[3]
    bgcolor_cover = 'White'
    # text_bgcolor = 'DarkCyan'
    text_bgcolor = epub_datas[5]
    fontstyle_tit = 'consola'
    fontstyle_des = 'arial'
    fontstyle_aut = 'consola'
    fontcolor_tit = 'white'
    fontcolor_des = 'black'
    fontcolor_aut = '#111111'
    width = 800
    height = int(width * 1.4)
    margin = 0
    bh = 3
    top_block = int(0.2 * height)
    fontsize_tit = min(int(1.5 * (width - margin) / len(title)), 80)
    fontsize_des = int(min(1.5 * (width - margin) /
                           len(description), 0.8 * fontsize_tit))
    fontsize_aut = 60
    # colored block
    block_height = int(bh * (fontsize_tit + fontsize_des))
    im = Image.new('RGBA', (width, height), bgcolor_cover)
    draw = ImageDraw.Draw(im)
    draw.rectangle((margin, top_block, width - margin,
                    top_block + block_height), fill=text_bgcolor)
    # title
    font = ImageFont.truetype(fontstyle_tit + '.ttf', fontsize_tit)
    wt, h = font.getsize(title)
    left_tit = int((width / 2) - (wt / 2))  # centered
    top_tit = int(top_block + 0.2 * block_height)
    draw.text((left_tit, top_tit), title, fill=fontcolor_tit, font=font)
    # description
    font = ImageFont.truetype(fontstyle_des + '.ttf', fontsize_des)
    wd, h = font.getsize(description)
    left_des = int((width / 2) - (wd / 2))  # centered
    top_des = int(top_block + 20 + 0.6 * block_height)
    draw.text((left_des, top_des), description, fill=fontcolor_des, font=font)
    # horizontal line
    left_line = min(left_tit, left_des)
    top_line = int(top_block + 0.55 * block_height)
    draw.rectangle((left_line, top_line, width - left_line,
                    top_line + 1), fill=fontcolor_tit)  # horizontal line
    # author and publication year
    font = ImageFont.truetype(fontstyle_aut + '.ttf', fontsize_aut)
    wa, h = font.getsize(author)
    left_aut = width - margin - wa
    draw.text((left_aut, int(0.8 * height)),
              author, fill=fontcolor_aut, font=font)
    wp, h = font.getsize(epub_pub)  # publication year
    left_pub = width - margin - wp
    draw.text((left_pub, int(0.86 * height)),
              epub_pub, fill=fontcolor_aut, font=font)
    # write file
    img_path = epub_path / 'images'
    img_path.mkdir(exist_ok=True, parents=True)
    cover_file_name = 'cover_' + \
        str(datetime.datetime.now()).replace(':', '') + '.png'
    # img_filepath = img_path / 'cover.png'
    img_filepath = img_path / cover_file_name
    im.save(img_filepath)
    im.close()
    return cover_file_name


def get_img(epub, epub_path, url, img_name):  # activated from clean_html
    # epub = zipfile
    global manifest
    img_path = epub_path / 'images'
    img_path.mkdir(exist_ok=True, parents=True)
    img_filepath = img_path / img_name
    # print('saved: ' + str(img_filepath))
    msg = 'getting image: ' + str(img_name)
    print(msg)
    emit('my_response', 
        {'data': msg, 'count': 7})
    response = requests.get(url)
    if response.status_code == 200:
        # epub.write(response.content, img_filepath)
        with img_filepath.open('wb') as f:
            f.write(response.content)
        epub.write(img_filepath, 'OEBPS/images/' + img_name)
        if img_name[-3:] == 'png':
            manifest += '        <item id="' + img_name + \
                '" href="images/' + img_name + '" media-type="image/png"/>\n'
        else:
            manifest += '        <item id="' + img_name + \
                '" href="images/' + img_name + '" media-type="image/jpeg"/>\n'
    return 'images/' + img_name


def clean_html(epub, epub_path, source_code, url, file_idx):  # activated from fetch_page
    blacklist = ['script', 'style', 'dd', 'em', 'text', 'blockquote']
    graylist = ['div', 'h1', 'h2', 'h3', 'h4', 'h5', 'span']
    doc = Document(source_code.text)
    # or: DefaultExtractor ArticleExtractor ArticleSentencesExtractor KeepEverythingExtractor
    # NumWordsRulesExtractor CanolaExtractor KeepEverythingWithMinKWordsExtractor LargestContentExtractor
    # extractor = Extractor(extractor='KeepEverythingExtractor', url=url)
    # extracted_html = extractor.getHTML()
    # print (source_code.text)
    base_url = '{uri.scheme}://{uri.netloc}'.format(uri=urlparse(url))
    # soup = BeautifulSoup(doc.summary(), "html.parser")
    soup = BeautifulSoup(doc.summary(), "lxml")
    # print(soup)
    # soup = BeautifulSoup(extracted_html, "html.parser")
    for tag in soup.findAll():
        del tag['srcset']
        del tag['align']
        del tag['data-file-height']
        del tag['data-file-width']
        del tag['role']
        id = str(tag.get('id'))
        ch = id.find(':')
        if ch > -1:
            id = id[:ch] + id[ch + 1:]
            tag['id'] = id
            # print(': '+id)
        ch = id.find(',')
        if ch > -1:
            id = id[:ch] + id[ch + 1:]
            tag['id'] = id
            # print(', '+id)
        ch = id.find('.')
        if ch > -1:
            id = id[:ch] + id[ch + 1:]
            tag['id'] = id
            # print('. '+id)
        if tag.name.lower() in blacklist:
            # blacklisted tags are removed in their entirety
            tag.extract()
        elif tag.name.lower() in graylist:
            tag.attrs = []
            # del tag['class']
    for tag in soup.findAll('a'):  # make all external links absolute and complete
        href = str(tag.get('href'))
        if not href:
            if href.startswith('http'):
                pass
            elif href.startswith('//'):
                href = 'http:' + href
            elif href.startswith('/'):
                href = base_url + href
            elif href.startswith('#'):  # relative link to #id
                pass
            else:
                href = url + '/' + href
            tag['href'] = href
    idx = 0
    # for tag in soup.findAll('html'):
    #     tag['xmlns'] = "http://www.w3.org/1999/xhtml"
    for tag in soup.findAll('img'):
        src = tag.get('src')
        ext = src[-3:]
        if ext == 'png' or ext == 'jpg':
            if src.startswith('http'):
                pass
            elif src.startswith('//'):
                src = 'http:' + src
            elif src.startswith('/'):
                src = base_url + src
            else:
                src = url + '/' + src
            img_name = 'img_' + str(file_idx) + '_' + str(idx) + '.' + ext
            # format: images/img_0_0.png
            tag['src'] = '../' + get_img(epub, epub_path, src, img_name)
            del tag['srcset']
            idx += 1
    html = str(soup)
    body = re.compile(r'<body\b[^>]*>', re.I)  # <body attributes>-tag
    html = body.sub('<body><h1>' + doc.title() + '</h1>', html)
    head = re.compile(r'<html\b[^>]*>', re.I)  # <html attributes>-tag
    html = head.sub('<html xmlns="http://www.w3.org/1999/xhtml"><head><title>' + doc.title() +
                    '</title><link href="../css/epub.css" rel="stylesheet" type="text/css"/></head>', html)
    # print(html[:300])

    doctype = '''<?xml version='1.0' encoding='utf-8'?>
        <!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd'>
        '''
    # html = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">' + html
    html = doctype + html
    html = html.encode('utf-8')
    return html, doc.title()


def fetch_page(url):
    if url[-1:] == '/':
        url = url[:-1]
    try:
        source_code = requests.get(url, timeout=5)
        return source_code
    except requests.exceptions.RequestException as e:
        print(e)
    # source_code = requests.get(url)


def remove(path):
    """ param <path> could either be relative or absolute. """
    if os.path.isfile(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains
    else:
        raise ValueError("file {} is not a file or dir.".format(path))


# Main program ######################################

# make_cover(epub_title, epub_description, epub_author)

# Define epub-files

def make_epub_file(epub, epub_path, epub_datas, epub_id, epub_pub, epub_mod, cover_file_name):
    # epub_datas =  array with data from website
    epub_title = epub_datas[1]
    epub_author = epub_datas[3]
    epub_lan = epub_datas[4]
    datalength = int(epub_datas[0]) + 1 # first element of epub_datas indicates number of meta fields
    epub_urls = epub_datas[datalength:]
    # print('datalength: '+str(datalength))
    # print('epub_urls[0]: '+str(epub_urls[0]))
    global manifest
    spine = ''
    toc_item = ''
    toc_page_item = ''
    content_opf = '''<?xml version='1.0' encoding='utf-8'?>
    <package xmlns='http://www.idpf.org/2007/opf' version='2.0' unique-identifier='BookId'>
        <metadata xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:opf='http://www.idpf.org/2007/opf'>
            <dc:title>%(epub_title)s</dc:title>
            <dc:creator opf:role='aut' opf:file-as=''>%(epub_author)s</dc:creator>
            <dc:identifier id='BookId' opf:scheme='URI'>%(epub_id)s</dc:identifier>
            <dc:language>%(epub_lan)s</dc:language>
            <dc:description>Description</dc:description>
            <dc:date opf:event='publication'>%(epub_pub)s</dc:date>
            <dc:date opf:event='modification'>%(epub_mod)s</dc:date>
            <dc:subject>Unknown</dc:subject>
        <meta name="cover" content="cover-image" />
        </metadata>
        <manifest>
            <item id="cover" href="content/cover.xhtml" media-type="application/xhtml+xml"/>
            <item id="cover-image" href="images/cover.png" media-type="image/png"/>
            <item id='ncx' media-type='application/x-dtbncx+xml' href='toc.ncx'/>
            <item id='toc' media-type='application/xhtml+xml' href='content/toc_page.xhtml'/>
            %(manifest)s
            <item id='css' media-type='text/css' href='css/epub.css'/>
        </manifest>
        <spine toc="ncx">
            <itemref idref='cover' linear='yes' />
            <itemref idref='toc'/>
            %(spine)s
        </spine>
        <guide>
            <reference type='toc' title='Contents' href='content/toc_page.xhtml'></reference>
        </guide>
    </package>'''
    cover_html = '''<?xml version='1.0' encoding='utf-8'?>
    <!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd' >
    <html xmlns='http://www.w3.org/1999/xhtml' xml:lang='en'>
    <head>
        <title>%(epub_title)s</title>
        <style type='text/css'>
            body { margin: 0; padding: 0; text-align: center; }
            .cover { margin: 0; padding: 0; }
            img { margin: 0; padding: 0; height: 100%%; }
        </style>
    </head>
    <body>
        <div id="cover-image">
            <div class='cover'><img style='height: 100%%;width: 100%%;' src='../images/cover.png' alt='Cover' /></div>
        </div>
    </body>
    </html>'''
    toc = '''<?xml version='1.0' encoding='UTF-8'?>
    <!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>
    <ncx xmlns='http://www.daisy.org/z3986/2005/ncx/'>
    <head>
        <meta name='dtb:uid' content='''
    toc += "'" + epub_id + "'"
    toc += '''/>
        <meta name='dtb:depth' content='1'/>
        <meta name='dtb:totalPageCount' content='0'/>
        <meta name='dtb:maxPageNumber' content='0'/>
    </head>
    <docTitle><text>%(epub_title)s</text></docTitle>
    <docAuthor><text>%(epub_author)s</text></docAuthor>
    <navMap>
        <navPoint id='cover' playOrder='1'>
            <navLabel><text>Cover</text></navLabel>
            <content src='content/cover.xhtml'/>
        </navPoint>
        <navPoint class='toc_page' id='toc_page' playOrder='2'>
            <navLabel><text>Table of contents</text></navLabel>
            <content src='content/toc_page.xhtml'/>
        </navPoint>
        %(toc_item)s
    </navMap>
    </ncx>'''
    toc_page = '''<?xml version='1.0' encoding='utf-8'?>
    <!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' 'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd' >
    <html xmlns='http://www.w3.org/1999/xhtml'>
        <head>
            <title>%(epub_title)s</title>
            <link rel='stylesheet' type='text/css' href='../css/epub.css' />
        </head>
        <body>
            <h2>Table Of Contents</h2>
            <ol class="toc_page-items">
            %(toc_page_item)s
            </ol>
        </body>
    </html>'''
    css = '''body {
        font-size: medium;
    }
    blockquote {
        font-style: italic;
        border-left: 3px solid black;
        margin-left: 0px;
        padding-left: 10px;
    }
    code {
        font-family: monospace;
        word-wrap: break-word;
    }
    p {
        text-indent: 1em;
    }
    pre > code {
        line-height: 1.5;
    }
    pre {
        border-left: 3px solid black;
        background-color: rgb(240, 240, 240);
        padding-left: 10px;
        text-align: left;
        white-space: pre-wrap;
        font-size: 75%;
    }
    '''
    # fetch webpages and write html-files
    # url_filepath = path / url_file
    # lines = url_filepath.read_text().splitlines()
    # for i, url in enumerate(lines):
    i = 0
    for url in epub_urls:
        msg = 'getting webpage: ' + str(url)
        print(msg)
        emit('my_response', 
            {'data': msg, 'count': 7})
        basename = 'content'
        manifest += '        <item id="s%s" href="%s" media-type="application/xhtml+xml"/>\n' % (
            i+1, basename + '/s' + str(i+1) + '.xhtml')
        spine += '<itemref idref="s%s" />\n' % (i+1)
        # html, title = fetch_page(url, i)
        source_code = fetch_page(url)
        html, title = clean_html(epub, epub_path, source_code, url, i)
        toc_item += '''<navPoint class='section' id='s%s' playOrder='%s'>
        <navLabel><text>%s</text></navLabel>
        <content src='content/s%s.xhtml'/>
        </navPoint>''' % (i+1, i+3, title, i+1)
        toc_page_item += '''<li><a href='s%s.xhtml'>%s</a></li>''' % (
            i+1, title)
        epub.writestr('OEBPS/content/' + 's' + str(i+1) + '.xhtml', html)
        i += 1
    # write mimetype
    epub.writestr("mimetype", "application/epub+zip")
    epub.writestr("META-INF/container.xml", '''<?xml version='1.0' encoding='UTF-8' ?>
    <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
        <rootfiles>
            <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
        </rootfiles>
    </container>''')
    # write container.xml
    epub.writestr('OEBPS/content.opf', content_opf % {
        'manifest': manifest,
        'spine': spine,
        'epub_title': epub_title,
        'epub_author': epub_author,
        'epub_id': epub_id,
        'epub_lan': epub_lan,
        'epub_mod': epub_mod,
        'epub_pub': epub_pub,
    })
    # write cover.xhtml
    epub.writestr('OEBPS/content/cover.xhtml', cover_html % {
        'epub_title': epub_title,
    })
    # write toc.ncx
    epub.writestr('OEBPS/toc.ncx', toc % {
        'epub_title': epub_title,
        'epub_author': epub_author,
        'toc_item': toc_item,
    })
    # write toc_page.xhtml
    epub.writestr('OEBPS/content/toc_page.xhtml', toc_page % {
        'epub_title': epub_title,
        'toc_page_item': toc_page_item,
    })
    # write epub.css
    epub.writestr('OEBPS/css/epub.css', css)
    # write cover.png
    epub.write(epub_path / 'Images' / cover_file_name,
               'OEBPS/images/cover.png')
    epub.close()
    # remove files
    try:
        remove(epub_path)
    except:
        print('Could not remove path:' + str(epub_path))

import random
random = random.SystemRandom()
 
def get_random_string(length=12,
        allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    return ''.join(random.choice(allowed_chars) for i in range(length))


def make_book(datas): # datas is string: 'tit, des, auth, lan, url, ...,'
    stamp = str(datetime.datetime.now()).replace(':', '').replace(
        '-', '').replace(' ', '').replace('.', '')[:12] # datetime string
    stamp += '_' + get_random_string() # and random string
    epub_path = path / 'temp' / stamp
    epub_path.mkdir(exist_ok=True, parents=True)
    zip_file = 'ebook_' + stamp + '.epub'
    zip_file_path = path / 'temp' / zip_file
    epub = ZipFile(zip_file_path, 'w')
    epub_mod = stamp[:12]  # modification date (seconds)
    epub_id = stamp  # can be changed to e.g. ISBN
    epub_pub = str(datetime.datetime.now().year)  # publication year
    epub_datas = datas.split(',') #array
    if not epub_datas[1].strip():
        epub_datas[1] = 'Title'
    if not epub_datas[2].strip():
        epub_datas[2] = 'Subtitle'
    if not epub_datas[3].strip():
        epub_datas[3] = 'Author'
    if not epub_datas[4].strip():
        epub_datas[4] = 'en'
    # First make cover image
    cover_file_name = make_cover(epub_path, epub_datas, epub_pub)
    # Make epub file
    make_epub_file(epub, epub_path, epub_datas, epub_id,
                   epub_pub, epub_mod, cover_file_name)
    return zip_file



@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@app.route("/about")
def about():
    return render_template('about.html', title='About')


@socketio.on('my_event', namespace='/test')
def test_message(message):
    print('Bericht van client: ' + message['data'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})

@socketio.on('make_book', namespace='/test') # we receive the make-command from the website
def start_making_book(message):
    print('message: ' + message['data'])
    # import web2epub
    emit('my_response',
        {'data': 'Start making book', 'count': 6})
    zip_file = str(make_book(message['data'])) # start making book
    zip_file_path = 'temp/' + str(zip_file)
    print('zip_file_path: ' + zip_file_path)
    emit('my_response',
        {'data': 'Book is finished', 'count': 6})
    emit('book_finished',
        {'data': str(zip_file_path), 'count': 6}) # give command to download file

@socketio.on('connect', namespace='/test')
def test_connect():
    print('Connect')
    # emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)

@app.route('/temp/<path:filename>')
def downloadFile(filename):
    # path = "temp/ebook_20181129202707996962.epub"
    path = 'temp/' + filename
    return send_file(path, as_attachment=True)





if __name__ == '__main__':
    socketio.run(app, debug=True)

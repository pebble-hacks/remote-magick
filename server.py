import os
import re
import subprocess
import tempfile

from flask import Flask, redirect, abort
from flask.ext.restful.reqparse import RequestParser
from flask.ext.restful import Api, Resource

from bitmapgen import PebbleBitmap

app = Flask(__name__, static_url_path='/tmp', static_folder='/tmp')
api = Api(app)

parser = RequestParser()
parser.add_argument('image', required=True)
parser.add_argument('size', default='144x152')
parser.add_argument('dither', default='FloydSteinberg')
parser.add_argument('format', default='png')

dithers = ['FloydSteinberg', 'Riemersma']

# where the magick happens
class RemoteMagick(Resource):
    def get(self):
        args = parser.parse_args()

        if re.match('^\d+x\d+$', args['size']) is None:
            abort(400)

        if not args['dither'] in dithers:
            abort(400)

        try:
            _, png = tempfile.mkstemp(suffix='.png')
            subprocess.check_call(['convert', args['image'],
                                   '-type', 'Grayscale',
                                   '-colorspace', 'Gray',
                                   '-resize', args['size'] + '^',
                                   '-gravity', 'center',
                                   '-extent', args['size'],
                                   '-dither', args['dither'],
                                   '-colors', '2',
                                   '-depth', '1',
                                   '-define', 'png:compression-level=9',
                                   '-define', 'png:compression-strategy=0',
                                   '-define', 'png:exclude-chunk=all',
                                   '-define', 'png:bit-depth=1',
                                   '-define', 'png:color-type=0',
                                   'PNG:' + png])
        except subprocess.CalledProcessError:
            abort(400)

        if args['format'] == 'png':
            return redirect(png)

        bmp = PebbleBitmap(png)
        _, out = tempfile.mkstemp(suffix='.' + args['format'])

        if args['format'] == 'pbi':
            bmp.convert_to_pbi(out)
        elif args['format'] == 'h':
            bmp.convert_to_h(out)

        return redirect(out)

api.add_resource(RemoteMagick, '/api')

@app.route('/')
def index():
    return redirect('http://github.com/pebble-hacks/remote-magick')

if __name__ == '__main__':
  app.run()

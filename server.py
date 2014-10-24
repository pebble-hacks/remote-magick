import os
import subprocess
import tempfile

from flask import Flask, redirect, abort
from flask.ext.restful.reqparse import RequestParser
from flask.ext.restful import Api, Resource

app = Flask(__name__,
            static_url_path='/tmp',
            static_folder='/tmp')
api = Api(app)

parser = RequestParser()
parser.add_argument('image', required=True)
parser.add_argument('fullscreen', default=False)
parser.add_argument('dither', default='FloydSteinberg')

dithers = ['FloydSteinberg', 'Riemersma']

# where the magick happens
class RemoteMagick(Resource):
    def get(self):
        args = parser.parse_args()
        original = args['image']
        _, converted = tempfile.mkstemp(suffix='.png')

        if args['fullscreen']:
            size = '144x168'
        else:
            size = '144x152'

        if not args['dither'] in dithers:
            abort(400)

        try:
            subprocess.check_call(['./bin/convert', original,
                             '-type', 'Grayscale',
                             '-colorspace', 'Gray',
                             '-resize', size + '^',
                             '-gravity', 'center',
                             '-extent', size,
                             '-dither', args['dither'],
                             '-colors', '2',
                             '-depth', '1',
                             '-define', 'png:compression-level=9',
                             '-define', 'png:compression-strategy=0',
                             '-define', 'png:exclude-chunk=all',
                             '-define', 'png:bit-depth=1',
                             '-define', 'png:color-type=0',
                             'PNG:' + converted])
        except subprocess.CalledProcessError:
            abort(400)

        return redirect(converted);

api.add_resource(RemoteMagick, '/api')

if __name__ == '__main__':
    port = os.environ.get('PORT', '5000')
    app.run(host='0.0.0.0', port=int(port))

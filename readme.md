# remote-magick

A RESTful API for ImageMagick, based on the [XML-RPC version](https://code.google.com/p/remotemagick/). Tailored for converting images for display on Pebble.

Currently running on EC2 at `ec2-54-191-195-212.us-west-2.compute.amazonaws.com`.

## Parameters

| Name     | Description                 | Example                        | Values                           |
|----------|-----------------------------|--------------------------------|----------------------------------|
| `image`  | url of the image to convert | http://placekitten.com/330/444 | url to any image on the internet |
| `size`   | size to scale the image to  | 144x168                        | matching `^\d+x\d+$`             |
| `dither` | dither method to use        | FloydSteinberg                 | FloydSteinberg, Riemersma        |
| `format` | format of output file       | png                            | png, pbi, h                      |

## Example

`http://ec2-54-191-195-212.us-west-2.compute.amazonaws.com/api?image=http://placekitten.com/330/444&size=144x168&dither=FloydSteinberg&format=png`

| Before                                    | After                                    |
|-------------------------------------------|------------------------------------------|
| ![Before](http://i.imgur.com/uOZPP3X.jpg) | ![After](http://i.imgur.com/zmq9KsV.png) |

[Try it!](http://ec2-54-191-195-212.us-west-2.compute.amazonaws.com/api?image=http://placekitten.com/330/444&size=144x168&dither=FloydSteinberg&format=png)

# remote-magick

A RESTful API for ImageMagick, based on the [XML-RPC version](https://code.google.com/p/remotemagick/). Tailored for converting images for display on Pebble.

Currently running on EC2 at `ec2-54-191-195-212.us-west-2.compute.amazonaws.com`.

## Parameters

|  Name    | Description                 | Example                        |
|----------|------------------------ ----|--------------------------------|
| `image`  | url of the image to convert | http://placekitten.com/330/444 |
| `size`   | size to scale the image to  | 144x168                        |
| `dither` | dither type to use          | FloydSteinberg                 |

## Example

`http://ec2-54-191-195-212.us-west-2.compute.amazonaws.com/api?image=http://placekitten.com/330/444&size=144x168&dither=FloydSteinberg`

[Try it!](http://ec2-54-191-195-212.us-west-2.compute.amazonaws.com/api?image=http://placekitten.com/330/444&size=144x168&dither=FloydSteinberg)

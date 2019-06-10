#!/bin/bash
docker pull asfdaac/apt-insar
docker run -it -v $(pwd):/output --rm --user $(id -u):$(id -g) asfdaac/apt-insar "$@"

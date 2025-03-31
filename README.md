# funet-containerlab

## About

Run [Funet](https://web.archive.org/web/20250114090246/https://netmap.funet.fi/) core in a lab.

## Howto

```
# Install networkx, geopy etc. with mechanism of your choice
cd src
curl https://netmap.funet.fi/ -o input.html
bash coordinates-helper.sh
python3 funet-containerlab.py -o output.yml -d input.html
```

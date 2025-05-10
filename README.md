# funet-containerlab

## About

Run 2020 era [Funet core](https://web.archive.org/web/20250114090246/https://netmap.funet.fi/) in a lab.

## Howto

```
# Install networkx, geopy etc. with mechanism of your choice
cd src
curl https://web.archive.org/web/20250114090246/https://netmap.funet.fi/ -o netmap.html
bash coordinates-helper.sh
python3 funet-containerlab.py netmap.html output.clab.yml
```
